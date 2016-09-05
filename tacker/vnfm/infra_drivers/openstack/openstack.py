# Copyright 2015 Intel Corporation.
# All Rights Reserved.
#
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import copy
import sys
import time

from heatclient import exc as heatException
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from six import iteritems
from toscaparser import tosca_template
from toscaparser.utils import yamlparser
from translator.hot import tosca_translator
import yaml

from tacker.common import clients
from tacker.common import log
from tacker.extensions import vnfm
from tacker.vnfm.infra_drivers import abstract_driver
from tacker.vnfm.infra_drivers import scale_driver
from tacker.vnfm.tosca import utils as toscautils


LOG = logging.getLogger(__name__)
CONF = cfg.CONF

OPTS = [
    cfg.IntOpt('stack_retries',
               default=60,
               help=_("Number of attempts to retry for stack"
                      " creation/deletion")),
    cfg.IntOpt('stack_retry_wait',
               default=5,
               help=_("Wait time (in seconds) between consecutive stack"
                      " create/delete retries")),
    cfg.DictOpt('flavor_extra_specs',
               default={},
               help=_("Flavor Extra Specs")),
]

CONF.register_opts(OPTS, group='openstack_vim')


def config_opts():
    return [('openstack_vim', OPTS)]


# Global map of individual resource type and
# incompatible properties, alternate properties pair for
# upgrade/downgrade across all Heat template versions (starting Kilo)
#
# Maintains a dictionary of {"resource type": {dict of "incompatible
# property": "alternate_prop"}}

HEAT_VERSION_INCOMPATIBILITY_MAP = {'OS::Neutron::Port': {
    'port_security_enabled': 'value_specs', }, }

HEAT_TEMPLATE_BASE = """
heat_template_version: 2013-05-23
"""

OUTPUT_PREFIX = 'mgmt_ip-'


def get_scaling_policy_name(action, policy_name):
    return '%s_scale_%s' % (policy_name, action)


class OpenStack(abstract_driver.DeviceAbstractDriver,
                scale_driver.VnfScaleAbstractDriver):
    """Openstack infra driver for hosting vnfs"""

    def __init__(self):
        super(OpenStack, self).__init__()
        self.STACK_RETRIES = cfg.CONF.openstack_vim.stack_retries
        self.STACK_RETRY_WAIT = cfg.CONF.openstack_vim.stack_retry_wait
        self.STACK_FLAVOR_EXTRA = cfg.CONF.openstack_vim.flavor_extra_specs

    def get_type(self):
        return 'openstack'

    def get_name(self):
        return 'openstack'

    def get_description(self):
        return 'Openstack infra driver'

    @log.log
    def _update_params(self, original, paramvalues, match=False):
        for key, value in iteritems(original):
            if not isinstance(value, dict) or 'get_input' not in str(value):
                pass
            elif isinstance(value, dict):
                if not match:
                    if key in paramvalues and 'param' in paramvalues[key]:
                        self._update_params(value, paramvalues[key]['param'],
                                            True)
                    elif key in paramvalues:
                        self._update_params(value, paramvalues[key], False)
                    else:
                        LOG.debug('Key missing Value: %s', key)
                        raise vnfm.InputValuesMissing(key=key)
                elif 'get_input' in value:
                    if value['get_input'] in paramvalues:
                        original[key] = paramvalues[value['get_input']]
                    else:
                        LOG.debug('Key missing Value: %s', key)
                        raise vnfm.InputValuesMissing(key=key)
                else:
                    self._update_params(value, paramvalues, True)

    @log.log
    def _process_parameterized_input(self, dev_attrs, vnfd_dict):
        param_vattrs_yaml = dev_attrs.pop('param_values', None)
        if param_vattrs_yaml:
            try:
                param_vattrs_dict = yaml.load(param_vattrs_yaml)
                LOG.debug('param_vattrs_yaml', param_vattrs_dict)
            except Exception as e:
                LOG.debug("Not Well Formed: %s", str(e))
                raise vnfm.ParamYAMLNotWellFormed(
                    error_msg_details=str(e))
            else:
                self._update_params(vnfd_dict, param_vattrs_dict)
        else:
            raise vnfm.ParamYAMLInputMissing()

    @log.log
    def _process_vdu_network_interfaces(self, vdu_id, vdu_dict, properties,
                                        template_dict,
                                        unsupported_res_prop=None):

        def make_port_dict():
            port_dict = {'type': 'OS::Neutron::Port'}
            port_dict['properties'] = {'value_specs': {
                'port_security_enabled': False}} if unsupported_res_prop \
                else {'port_security_enabled': False}
            port_dict['properties'].setdefault('fixed_ips', [])
            return port_dict

        def make_mgmt_outputs_dict(port):
            mgmt_ip = 'mgmt_ip-%s' % vdu_id
            outputs_dict[mgmt_ip] = {
                'description': 'management ip address',
                'value': {
                    'get_attr': [port, 'fixed_ips',
                                 0, 'ip_address']
                }
            }

        def handle_port_creation(network_param, ip_list=None,
                                 mgmt_port=False):
            ip_list = ip_list or []
            port = '%s-%s-port' % (vdu_id, network_param['network'])
            port_dict = make_port_dict()
            if mgmt_port:
                make_mgmt_outputs_dict(port)
            for ip in ip_list:
                port_dict['properties']['fixed_ips'].append({"ip_address": ip})
            port_dict['properties'].update(network_param)
            template_dict['resources'][port] = port_dict
            return port

        networks_list = []
        outputs_dict = template_dict['outputs']
        properties['networks'] = networks_list
        for network_param in vdu_dict[
                'network_interfaces'].values():
            port = None
            if 'addresses' in network_param:
                ip_list = network_param.pop('addresses', [])
                if not isinstance(ip_list, list):
                    raise vnfm.IPAddrInvalidInput()
                mgmt_flag = network_param.pop('management', False)
                port = handle_port_creation(network_param, ip_list, mgmt_flag)
            if network_param.pop('management', False):
                port = handle_port_creation(network_param, [], True)
            if port is not None:
                network_param = {
                    'port': {'get_resource': port}
                }
            networks_list.append(dict(network_param))

    def fetch_unsupported_resource_prop(self, heat_client):
        unsupported_resource_prop = {}

        for res, prop_dict in iteritems(HEAT_VERSION_INCOMPATIBILITY_MAP):
            unsupported_prop = {}
            for prop, val in iteritems(prop_dict):
                if not heat_client.resource_attr_support(res, prop):
                    unsupported_prop.update(prop_dict)
            if unsupported_prop:
                unsupported_resource_prop[res] = unsupported_prop
        return unsupported_resource_prop

    @log.log
    def create(self, plugin, context, vnf, auth_attr):
        LOG.debug(_('vnf %s'), vnf)

        attributes = vnf['vnfd']['attributes'].copy()

        vnfd_yaml = attributes.pop('vnfd', None)
        if vnfd_yaml is None:
            # TODO(kangaraj-manickam) raise user level exception
            LOG.info(_("VNFD is not provided, so no vnf is created !!"))
            return

        LOG.debug('vnfd_yaml %s', vnfd_yaml)

        def update_fields():
            fields = dict((key, attributes.pop(key)) for key
                          in ('stack_name', 'template_url', 'template')
                          if key in attributes)
            for key in ('files', 'parameters'):
                if key in attributes:
                    fields[key] = jsonutils.loads(attributes.pop(key))

            # overwrite parameters with given dev_attrs for vnf creation
            dev_attrs = vnf['attributes'].copy()
            fields.update(dict((key, dev_attrs.pop(key)) for key
                          in ('stack_name', 'template_url', 'template')
                          if key in dev_attrs))
            for key in ('files', 'parameters'):
                if key in dev_attrs:
                    fields.setdefault(key, {}).update(
                        jsonutils.loads(dev_attrs.pop(key)))

            return fields, dev_attrs

        fields, dev_attrs = update_fields()

        region_name = vnf.get('placement_attr', {}).get('region_name', None)
        heatclient_ = HeatClient(auth_attr, region_name)
        unsupported_res_prop = self.fetch_unsupported_resource_prop(
            heatclient_)

        def generate_hot_from_tosca(vnfd_dict):
            parsed_params = {}
            if ('param_values' in dev_attrs and
                    dev_attrs['param_values'] != ""):
                try:
                    parsed_params = yaml.load(dev_attrs['param_values'])
                except Exception as e:
                    LOG.debug("Params not Well Formed: %s", str(e))
                    raise vnfm.ParamYAMLNotWellFormed(
                        error_msg_details=str(e))

            toscautils.updateimports(vnfd_dict)

            try:
                tosca = tosca_template.ToscaTemplate(
                    parsed_params=parsed_params, a_file=False,
                    yaml_dict_tpl=vnfd_dict)

            except Exception as e:
                LOG.debug("tosca-parser error: %s", str(e))
                raise vnfm.ToscaParserFailed(error_msg_details=str(e))

            monitoring_dict = toscautils.get_vdu_monitoring(tosca)
            mgmt_ports = toscautils.get_mgmt_ports(tosca)
            res_tpl = toscautils.get_resources_dict(tosca,
                                                    self.STACK_FLAVOR_EXTRA)
            toscautils.post_process_template(tosca)
            try:
                translator = tosca_translator.TOSCATranslator(tosca,
                                                              parsed_params)
                heat_template_yaml = translator.translate()
            except Exception as e:
                LOG.debug("heat-translator error: %s", str(e))
                raise vnfm.HeatTranslatorFailed(error_msg_details=str(e))
            heat_template_yaml = toscautils.post_process_heat_template(
                heat_template_yaml, mgmt_ports, res_tpl,
                unsupported_res_prop)

            return heat_template_yaml, monitoring_dict

        def generate_hot_scaling(vnfd_dict,
                                 scale_resource_type="OS::Nova::Server"):
            # Initialize the template
            template_dict = yaml.load(HEAT_TEMPLATE_BASE)
            template_dict['description'] = 'Tacker scaling template'

            parameters = {}
            template_dict['parameters'] = parameters

            # Add scaling related resource defs
            resources = {}
            scaling_group_names = {}

            # TODO(kanagaraj-manickam) now only one group is supported, so name
            # is hard-coded with G1
            def _get_scale_group_name(targets):
                return 'G1'

            def _convert_to_heat_scaling_group(policy_prp,
                                               scale_resource_type,
                                               name):
                group_hot = {'type': 'OS::Heat::AutoScalingGroup'}
                properties = {}
                properties['min_size'] = policy_prp['min_instances']
                properties['max_size'] = policy_prp['max_instances']
                properties['desired_capacity'] = policy_prp[
                    'default_instances']
                properties['cooldown'] = policy_prp['cooldown']
                properties['resource'] = {}
                # TODO(kanagaraj-manickam) all VDU memebers are considered as 1
                # group now and make it to form the groups based on the VDU
                # list mentioned in the policy's targets
                # scale_resource_type is custome type mapped the HOT template
                # generated for all VDUs in the tosca template
                properties['resource']['type'] = scale_resource_type
                # support monitoring
                if 'policies' in vnfd_dict:
                    for policies in vnfd_dict['policies']:
                        policy_name, policy_dt = list(policies.items())[0]
                        if policy_dt['type'] ==\
                                'tosca.polices.tacker.Alarming':
                            metadata_dict = dict()
                            metadata_dict['metering.vnf_id'] = vnf['id']
                            properties['resource']['metadata'] = metadata_dict
                            break
                # TODO(kanagraj-manickam) add custom type params here, to
                # support parameterized template
                group_hot['properties'] = properties

                return group_hot

            # tosca policies
            #
            # properties:
            #   adjust_by: 1
            #   cooldown: 120
            #   targets: [G1]
            def _convert_to_heat_scaling_policy(policy_prp, name):
                # Form the group
                scale_grp = _get_scale_group_name(policy_prp['targets'])
                scaling_group_names[name] = scale_grp
                resources[scale_grp] = _convert_to_heat_scaling_group(
                    policy_prp,
                    scale_resource_type,
                    scale_grp)

                grp_id = {'get_resource': scale_grp}

                policy_hot = {'type': 'OS::Heat::ScalingPolicy'}
                properties = {}
                properties['adjustment_type'] = 'change_in_capacity'
                properties['cooldown'] = policy_prp['cooldown']
                properties['scaling_adjustment'] = policy_prp['increment']
                properties['auto_scaling_group_id'] = grp_id
                policy_hot['properties'] = properties

                # Add scale_out policy
                policy_rsc_name = get_scaling_policy_name(
                    action='out',
                    policy_name=name
                )
                resources[policy_rsc_name] = policy_hot

                # Add scale_in policy
                in_value = '-%d' % int(policy_prp['increment'])
                policy_hot_in = copy.deepcopy(policy_hot)
                policy_hot_in['properties'][
                    'scaling_adjustment'] = in_value
                policy_rsc_name = get_scaling_policy_name(
                    action='in',
                    policy_name=name
                )
                resources[policy_rsc_name] = policy_hot_in

            #   policies:
            #     - SP1:
            #         type: tosca.policy.tacker.Scaling
            if 'policies' in vnfd_dict:
                for policy_dict in vnfd_dict['policies']:
                    name, policy = list(policy_dict.items())[0]
                    if policy['type'] == 'tosca.policy.tacker.Scaling':
                        _convert_to_heat_scaling_policy(policy['properties'],
                                                        name)
                        # TODO(kanagaraj-manickam) only one policy is supported
                        # for all vdus. remove this break, once this limitation
                        # is addressed.
                        break

            template_dict['resources'] = resources

            # First return value helps to check if scaling resources exist
            return ((len(template_dict['resources']) > 0),
                    scaling_group_names,
                    template_dict)

        def generate_hot_alarm_resource(topology_tpl_dict, heat_tpl):
            alarm_resource = dict()
            heat_dict = yamlparser.simple_ordered_parse(heat_tpl)
            is_enabled_alarm = False

            def _convert_to_heat_monitoring_prop(mon_policy):
                name, mon_policy_dict = list(mon_policy.items())[0]
                tpl_trigger_name = \
                    mon_policy_dict['triggers']['resize_compute']
                tpl_condition = tpl_trigger_name['condition']
                properties = {}
                properties['meter_name'] = tpl_trigger_name['metrics']
                properties['comparison_operator'] = \
                    tpl_condition['comparison_operator']
                properties['period'] = tpl_condition['period']
                properties['evaluation_periods'] = tpl_condition['evaluations']
                properties['statistic'] = tpl_condition['method']
                properties['description'] = tpl_condition['constraint']
                properties['threshold'] = tpl_condition['threshold']
                # alarm url process here
                alarm_url = str(vnf['attributes'].get('alarm_url'))
                if alarm_url:
                    LOG.debug('Alarm url in heat %s', alarm_url)
                    properties['alarm_actions'] = [alarm_url]
                return properties

            def _convert_to_heat_monitoring_resource(mon_policy):
                mon_policy_hot = {'type': 'OS::Aodh::Alarm'}
                mon_policy_hot['properties'] = \
                    _convert_to_heat_monitoring_prop(mon_policy)

                if 'policies' in topology_tpl_dict:
                    for policies in topology_tpl_dict['policies']:
                        policy_name, policy_dt = list(policies.items())[0]
                        if policy_dt['type'] == \
                                'tosca.policy.tacker.Scaling':
                            metadata_dict = dict()
                            metadata_dict['metadata.user_metadata.vnf_id'] =\
                                vnf['id']
                            mon_policy_hot['properties']['matching_metadata'] =\
                                metadata_dict
                            break
                return mon_policy_hot

            if 'policies' in topology_tpl_dict:
                for policy_dict in topology_tpl_dict['policies']:
                    name, policy_tpl_dict = list(policy_dict.items())[0]
                    if policy_tpl_dict['type'] == \
                            'tosca.policies.tacker.Alarming':
                        is_enabled_alarm = True
                        alarm_resource[name] =\
                            _convert_to_heat_monitoring_resource(policy_dict)
                        heat_dict['resources'].update(alarm_resource)
                        break

            heat_tpl_yaml = yaml.dump(heat_dict)
            return (is_enabled_alarm,
                    alarm_resource,
                    heat_tpl_yaml)

        def generate_hot_from_legacy(vnfd_dict):
            assert 'template' not in fields
            assert 'template_url' not in fields

            monitoring_dict = {}

            template_dict = yaml.load(HEAT_TEMPLATE_BASE)
            outputs_dict = {}
            template_dict['outputs'] = outputs_dict

            if 'get_input' in vnfd_yaml:
                self._process_parameterized_input(dev_attrs, vnfd_dict)

            KEY_LIST = (('description', 'description'), )
            for (key, vnfd_key) in KEY_LIST:
                if vnfd_key in vnfd_dict:
                    template_dict[key] = vnfd_dict[vnfd_key]

            for vdu_id, vdu_dict in vnfd_dict.get('vdus', {}).items():
                template_dict.setdefault('resources', {})[vdu_id] = {
                    "type": "OS::Nova::Server"
                }
                resource_dict = template_dict['resources'][vdu_id]
                KEY_LIST = (('image', 'vm_image'),
                            ('flavor', 'instance_type'))
                resource_dict['properties'] = {}
                properties = resource_dict['properties']
                for (key, vdu_key) in KEY_LIST:
                    properties[key] = vdu_dict[vdu_key]
                if 'network_interfaces' in vdu_dict:
                    self._process_vdu_network_interfaces(vdu_id,
                     vdu_dict, properties, template_dict,
                     unsupported_res_prop)
                if ('user_data' in vdu_dict and
                        'user_data_format' in vdu_dict):
                    properties['user_data_format'] = vdu_dict[
                        'user_data_format']
                    properties['user_data'] = vdu_dict['user_data']
                elif ('user_data' in vdu_dict or
                        'user_data_format' in vdu_dict):
                    raise vnfm.UserDataFormatNotFound()
                if 'placement_policy' in vdu_dict:
                    if 'availability_zone' in vdu_dict['placement_policy']:
                        properties['availability_zone'] = vdu_dict[
                            'placement_policy']['availability_zone']
                if 'config' in vdu_dict:
                    properties['config_drive'] = True
                    metadata = properties.setdefault('metadata', {})
                    metadata.update(vdu_dict['config'])
                    for key, value in metadata.items():
                        metadata[key] = value[:255]
                if 'key_name' in vdu_dict:
                        properties['key_name'] = vdu_dict['key_name']

                monitoring_policy = vdu_dict.get('monitoring_policy',
                                                 'noop')
                failure_policy = vdu_dict.get('failure_policy', 'noop')

                # Convert the old monitoring specification to the new
                # network.  This should be removed after Mitaka
                if (monitoring_policy == 'ping' and
                        failure_policy == 'respawn'):
                    vdu_dict['monitoring_policy'] = {
                        'ping': {'actions': {'failure': 'respawn'}}}
                    vdu_dict.pop('failure_policy')

                if monitoring_policy != 'noop':
                    monitoring_dict['vdus'] = {}
                    monitoring_dict['vdus'][vdu_id] = \
                        vdu_dict['monitoring_policy']

                # to pass necessary parameters to plugin upwards.
                for key in ('service_type',):
                    if key in vdu_dict:
                        vnf.setdefault(
                            'attributes', {})[vdu_id] = jsonutils.dumps(
                                {key: vdu_dict[key]})

                heat_template_yaml = yaml.dump(template_dict)

            return heat_template_yaml, monitoring_dict

        def generate_hot():
            vnfd_dict = yamlparser.simple_ordered_parse(vnfd_yaml)
            LOG.debug('vnfd_dict %s', vnfd_dict)

            is_tosca_format = False
            if 'tosca_definitions_version' in vnfd_dict:
                (heat_template_yaml,
                 monitoring_dict) = generate_hot_from_tosca(vnfd_dict)
                is_tosca_format = True
            else:
                (heat_template_yaml,
                 monitoring_dict) = generate_hot_from_legacy(vnfd_dict)

            fields['template'] = heat_template_yaml
            if is_tosca_format:
                (is_scaling_needed, scaling_group_names,
                 main_dict) = generate_hot_scaling(
                    vnfd_dict['topology_template'],
                    'scaling.yaml')
                (is_enabled_alarm, alarm_resource,
                 heat_tpl_yaml) = generate_hot_alarm_resource(
                    vnfd_dict['topology_template'],
                    heat_template_yaml)
                if is_enabled_alarm and not is_scaling_needed:
                    heat_template_yaml = heat_tpl_yaml
                    fields['template'] = heat_template_yaml

                if is_scaling_needed:
                    if is_enabled_alarm:
                        main_dict['resources'].update(alarm_resource)
                    main_yaml = yaml.dump(main_dict)
                    fields['template'] = main_yaml
                    fields['files'] = {'scaling.yaml': heat_template_yaml}
                    vnf['attributes']['heat_template'] = main_yaml
                    # TODO(kanagaraj-manickam) when multiple groups are
                    # supported, make this scaling atribute as
                    # scaling name vs scaling template map and remove
                    # scaling_group_names
                    vnf['attributes']['scaling.yaml'] = heat_template_yaml
                    vnf['attributes'][
                        'scaling_group_names'] = jsonutils.dumps(
                        scaling_group_names
                    )

                elif not is_scaling_needed:
                    if not vnf['attributes'].get('heat_template'):
                        vnf['attributes'][
                            'heat_template'] = fields['template']

            if monitoring_dict:
                    vnf['attributes']['monitoring_policy'] = \
                        jsonutils.dumps(monitoring_dict)

        generate_hot()

        def create_stack():
            if 'stack_name' not in fields:
                name = (__name__ + '_' + self.__class__.__name__ + '-' +
                        vnf['id'])
                if vnf['attributes'].get('failure_count'):
                    name += ('-RESPAWN-%s') % str(vnf['attributes'][
                        'failure_count'])
                fields['stack_name'] = name

            # service context is ignored
            LOG.debug(_('service_context: %s'),
                      vnf.get('service_context', []))
            LOG.debug(_('fields: %s'), fields)
            LOG.debug(_('template: %s'), fields['template'])
            stack = heatclient_.create(fields)

            return stack

        stack = create_stack()
        return stack['stack']['id']

    def create_wait(self, plugin, context, vnf_dict, vnf_id, auth_attr):
        region_name = vnf_dict.get('placement_attr', {}).get(
            'region_name', None)
        heatclient_ = HeatClient(auth_attr, region_name)

        stack = heatclient_.get(vnf_id)
        status = stack.stack_status
        stack_retries = self.STACK_RETRIES
        error_reason = None
        while status == 'CREATE_IN_PROGRESS' and stack_retries > 0:
            time.sleep(self.STACK_RETRY_WAIT)
            try:
                stack = heatclient_.get(vnf_id)
            except Exception:
                LOG.exception(_("VNF Instance cleanup may not have "
                                "happened because Heat API request failed "
                                "while waiting for the stack %(stack)s to be "
                                "deleted"), {'stack': vnf_id})
                break
            status = stack.stack_status
            LOG.debug(_('status: %s'), status)
            stack_retries = stack_retries - 1

        LOG.debug(_('stack status: %(stack)s %(status)s'),
                  {'stack': str(stack), 'status': status})
        if stack_retries == 0 and status != 'CREATE_COMPLETE':
            error_reason = _("Resource creation is not completed within"
                           " {wait} seconds as creation of stack {stack}"
                           " is not completed").format(
                               wait=(self.STACK_RETRIES *
                                     self.STACK_RETRY_WAIT),
                               stack=vnf_id)
            LOG.warning(_("VNF Creation failed: %(reason)s"),
                    {'reason': error_reason})
            raise vnfm.VNFCreateWaitFailed(vnf_id=vnf_id,
                                           reason=error_reason)

        elif stack_retries != 0 and status != 'CREATE_COMPLETE':
            error_reason = stack.stack_status_reason
            raise vnfm.VNFCreateWaitFailed(vnf_id=vnf_id,
                                           reason=error_reason)

        def _find_mgmt_ips(outputs):
            LOG.debug(_('outputs %s'), outputs)
            mgmt_ips = dict((output['output_key'][len(OUTPUT_PREFIX):],
                             output['output_value'])
                            for output in outputs
                            if output.get('output_key',
                                          '').startswith(OUTPUT_PREFIX))
            return mgmt_ips

        # scaling enabled
        if vnf_dict['attributes'].get('scaling_group_names'):
            group_names = jsonutils.loads(
                vnf_dict['attributes'].get('scaling_group_names')).values()
            mgmt_ips = self._find_mgmt_ips_from_groups(heatclient_,
                                                       vnf_id,
                                                       group_names)
        else:
            mgmt_ips = _find_mgmt_ips(stack.outputs)

        if mgmt_ips:
            vnf_dict['mgmt_url'] = jsonutils.dumps(mgmt_ips)

    @log.log
    def update(self, plugin, context, vnf_id, vnf_dict, vnf,
               auth_attr):
        region_name = vnf_dict.get('placement_attr', {}).get(
            'region_name', None)
        heatclient_ = HeatClient(auth_attr, region_name)
        heatclient_.get(vnf_id)

        # update config attribute
        config_yaml = vnf_dict.get('attributes', {}).get('config', '')
        update_yaml = vnf['vnf'].get('attributes', {}).get('config', '')
        LOG.debug('yaml orig %(orig)s update %(update)s',
                  {'orig': config_yaml, 'update': update_yaml})

        # If config_yaml is None, yaml.load() will raise Attribute Error.
        # So set config_yaml to {}, if it is None.
        if not config_yaml:
            config_dict = {}
        else:
            config_dict = yaml.load(config_yaml) or {}
        update_dict = yaml.load(update_yaml)
        if not update_dict:
            return

        @log.log
        def deep_update(orig_dict, new_dict):
            for key, value in new_dict.items():
                if isinstance(value, dict):
                    if key in orig_dict and isinstance(orig_dict[key], dict):
                        deep_update(orig_dict[key], value)
                        continue

                orig_dict[key] = value

        LOG.debug('dict orig %(orig)s update %(update)s',
                  {'orig': config_dict, 'update': update_dict})
        deep_update(config_dict, update_dict)
        LOG.debug('dict new %(new)s update %(update)s',
                  {'new': config_dict, 'update': update_dict})
        new_yaml = yaml.dump(config_dict)
        vnf_dict.setdefault('attributes', {})['config'] = new_yaml

    def update_wait(self, plugin, context, vnf_id, auth_attr,
                    region_name=None):
        # do nothing but checking if the stack exists at the moment
        heatclient_ = HeatClient(auth_attr, region_name)
        heatclient_.get(vnf_id)

    def delete(self, plugin, context, vnf_id, auth_attr, region_name=None):
        heatclient_ = HeatClient(auth_attr, region_name)
        heatclient_.delete(vnf_id)

    @log.log
    def delete_wait(self, plugin, context, vnf_id, auth_attr,
                    region_name=None):
        heatclient_ = HeatClient(auth_attr, region_name)

        stack = heatclient_.get(vnf_id)
        status = stack.stack_status
        error_reason = None
        stack_retries = self.STACK_RETRIES
        while (status == 'DELETE_IN_PROGRESS' and stack_retries > 0):
            time.sleep(self.STACK_RETRY_WAIT)
            try:
                stack = heatclient_.get(vnf_id)
            except heatException.HTTPNotFound:
                return
            except Exception:
                LOG.exception(_("VNF Instance cleanup may not have "
                                "happened because Heat API request failed "
                                "while waiting for the stack %(stack)s to be "
                                "deleted"), {'stack': vnf_id})
                break
            status = stack.stack_status
            stack_retries = stack_retries - 1

        if stack_retries == 0 and status != 'DELETE_COMPLETE':
            error_reason = _("Resource cleanup for vnf is"
                             " not completed within {wait} seconds as "
                             "deletion of Stack {stack} is "
                             "not completed").format(stack=vnf_id,
                             wait=(self.STACK_RETRIES * self.STACK_RETRY_WAIT))
            LOG.warning(error_reason)
            raise vnfm.VNFCreateWaitFailed(vnf_id=vnf_id,
                                           reason=error_reason)

        if stack_retries != 0 and status != 'DELETE_COMPLETE':
            error_reason = _("vnf {vnf_id} deletion is not completed. "
                            "{stack_status}").format(vnf_id=vnf_id,
                            stack_status=status)
            LOG.warning(error_reason)
            raise vnfm.VNFCreateWaitFailed(vnf_id=vnf_id,
                                           eason=error_reason)

    @classmethod
    def _find_mgmt_ips_from_groups(cls,
                                   heat_client,
                                   instance_id,
                                   group_names):

        def _find_mgmt_ips(attributes):
            mgmt_ips = {}
            for k, v in attributes.items():
                if k.startswith(OUTPUT_PREFIX):
                    mgmt_ips[k.replace(OUTPUT_PREFIX, '')] = v

            return mgmt_ips

        mgmt_ips = {}
        for group_name in group_names:
            # Get scale group
            grp = heat_client.resource_get(instance_id,
                                           group_name)
            for rsc in heat_client.resource_get_list(
                    grp.physical_resource_id):
                # Get list of resources in scale group
                scale_rsc = heat_client.resource_get(
                    grp.physical_resource_id,
                    rsc.resource_name)

                # findout the mgmt ips from attributes
                for k, v in _find_mgmt_ips(scale_rsc.attributes).items():
                    if k not in mgmt_ips:
                        mgmt_ips[k] = [v]
                    else:
                        mgmt_ips[k].append(v)

        return mgmt_ips

    @log.log
    def scale(self,
              context,
              plugin,
              auth_attr,
              policy,
              region_name):
        heatclient_ = HeatClient(auth_attr, region_name)
        policy_rsc = get_scaling_policy_name(
            policy_name=policy['id'],
            action=policy['action']
        )
        events = heatclient_.resource_event_list(
            policy['instance_id'],
            policy_rsc,
            limit=1,
            sort_dir='desc',
            sort_keys='event_time'
        )

        heatclient_.resource_signal(policy['instance_id'],
                                    policy_rsc)
        return events[0].id

    @log.log
    def scale_wait(self,
                   context,
                   plugin,
                   auth_attr,
                   policy,
                   region_name,
                   last_event_id):
        heatclient_ = HeatClient(auth_attr, region_name)

        # TODO(kanagaraj-manickam) make wait logic into separate utility method
        # and make use of it here and other actions like create and delete
        stack_retries = self.STACK_RETRIES
        while (True):
            try:
                time.sleep(self.STACK_RETRY_WAIT)
                stack_id = policy['instance_id']
                policy_name = get_scaling_policy_name(
                    policy_name=policy['id'],
                    action=policy['action'])
                events = heatclient_.resource_event_list(
                    stack_id,
                    policy_name,
                    limit=1,
                    sort_dir='desc',
                    sort_keys='event_time')

                if events[0].id != last_event_id:
                    if events[0].resource_status == 'SIGNAL_COMPLETE':
                        break
            except Exception as e:
                error_reason = _("VNF scaling failed for stack %(stack)s with "
                                 "error %(error)s") % {
                    'stack': policy['instance_id'],
                    'error': e.message
                }
                LOG.warning(error_reason)
                raise vnfm.VNFScaleWaitFailed(
                    vnf_id=policy['vnf']['id'],
                    reason=error_reason)

            if stack_retries == 0:
                metadata = heatclient_.resource_metadata(stack_id, policy_name)
                if not metadata['scaling_in_progress']:
                    error_reason = _('when signal occurred within cool down '
                                     'window, no events generated from heat, '
                                     'so ignore it')
                    LOG.warning(error_reason)
                    break
                error_reason = _(
                    "VNF scaling failed to complete within %{wait}s seconds "
                    "while waiting for the stack %(stack)s to be "
                    "scaled.") % {'stack': stack_id,
                                  'wait': self.STACK_RETRIES *
                                  self.STACK_RETRY_WAIT}
                LOG.warning(error_reason)
                raise vnfm.VNFScaleWaitFailed(
                    vnf_id=policy['vnf']['id'],
                    reason=error_reason)
            stack_retries -= 1

        def _fill_scaling_group_name():
            vnf = policy['vnf']
            scaling_group_names = vnf['attributes']['scaling_group_names']
            policy['group_name'] = jsonutils.loads(
                scaling_group_names)[policy['name']]

        _fill_scaling_group_name()

        mgmt_ips = self._find_mgmt_ips_from_groups(
            heatclient_,
            policy['instance_id'],
            [policy['group_name']])

        return jsonutils.dumps(mgmt_ips)

    def get_resource_info(self, plugin, context, vnf_info, auth_attr,
                          region_name=None):
        stack_id = vnf_info['instance_id']
        heatclient_ = HeatClient(auth_attr, region_name)
        try:
            resources_ids = heatclient_.resource_get_list(stack_id)
            details_dict = {resource.resource_name:
                           {"id": resource.physical_resource_id,
                           "type": resource.resource_type}
                           for resource in resources_ids}
            return details_dict
        # Raise exception when Heat API service is not available
        except Exception:
            raise vnfm.InfraDriverUnreachable(service="Heat API service")


class HeatClient(object):
    def __init__(self, auth_attr, region_name=None):
        # context, password are unused
        self.heat = clients.OpenstackClients(auth_attr, region_name).heat
        self.stacks = self.heat.stacks
        self.resource_types = self.heat.resource_types
        self.resources = self.heat.resources

    def create(self, fields):
        fields = fields.copy()
        fields.update({
            'timeout_mins': 10,
            'disable_rollback': True})
        if 'password' in fields.get('template', {}):
            fields['password'] = fields['template']['password']

        try:
            return self.stacks.create(**fields)
        except heatException.HTTPException:
            type_, value, tb = sys.exc_info()
            raise vnfm.HeatClientException(msg=value)

    def delete(self, stack_id):
        try:
            self.stacks.delete(stack_id)
        except heatException.HTTPNotFound:
            LOG.warning(_("Stack %(stack)s created by service chain driver is "
                          "not found at cleanup"), {'stack': stack_id})

    def get(self, stack_id):
        return self.stacks.get(stack_id)

    def resource_attr_support(self, resource_name, property_name):
        resource = self.resource_types.get(resource_name)
        return property_name in resource['attributes']

    def resource_get_list(self, stack_id, nested_depth=0):
        return self.heat.resources.list(stack_id,
                                        nested_depth=nested_depth)

    def resource_signal(self, stack_id, rsc_name):
        return self.heat.resources.signal(stack_id, rsc_name)

    def resource_get(self, stack_id, rsc_name):
        return self.heat.resources.get(stack_id, rsc_name)

    def resource_event_list(self, stack_id, rsc_name, **kwargs):
        return self.heat.events.list(stack_id, rsc_name, **kwargs)

    def resource_metadata(self, stack_id, rsc_name):
        return self.heat.resources.metadata(stack_id, rsc_name)
