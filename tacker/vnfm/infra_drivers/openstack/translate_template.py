# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import copy

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from six import iteritems
from toscaparser import tosca_template
from toscaparser.utils import yamlparser
from translator.hot import tosca_translator
import yaml

from tacker.common import log
from tacker.extensions import common_services as cs
from tacker.extensions import vnfm
from tacker.vnfm.tosca import utils as toscautils


LOG = logging.getLogger(__name__)
CONF = cfg.CONF

OPTS = [
    cfg.DictOpt('flavor_extra_specs',
               default={},
               help=_("Flavor Extra Specs")),
]

CONF.register_opts(OPTS, group='openstack_vim')

HEAT_VERSION_INCOMPATIBILITY_MAP = {'OS::Neutron::Port': {
    'port_security_enabled': 'value_specs', }, }

HEAT_TEMPLATE_BASE = """
heat_template_version: 2013-05-23
"""

ALARMING_POLICY = 'tosca.policies.tacker.Alarming'
SCALING_POLICY = 'tosca.policies.tacker.Scaling'


def get_scaling_policy_name(action, policy_name):
    return '%s_scale_%s' % (policy_name, action)


class TOSCAToHOT(object):
    """Convert TOSCA template to HOT template."""

    def __init__(self, vnf, heatclient):
        self.vnf = vnf
        self.heatclient = heatclient
        self.attributes = {}
        self.vnfd_yaml = None
        self.unsupported_props = {}
        self.heat_template_yaml = None
        self.monitoring_dict = None
        self.fields = None
        self.STACK_FLAVOR_EXTRA = cfg.CONF.openstack_vim.flavor_extra_specs

    @log.log
    def generate_hot(self):

        self._get_vnfd()
        dev_attrs = self._update_fields()

        vnfd_dict = yamlparser.simple_ordered_parse(self.vnfd_yaml)
        LOG.debug('vnfd_dict %s', vnfd_dict)
        self._get_unsupported_resource_props(self.heatclient)

        is_tosca_format = False
        self._generate_hot_from_tosca(vnfd_dict, dev_attrs)
        is_tosca_format = True

        self.fields['template'] = self.heat_template_yaml
        if is_tosca_format:
            self._handle_policies(vnfd_dict)
        if self.monitoring_dict:
            self.vnf['attributes']['monitoring_policy'] = jsonutils.dumps(
                self.monitoring_dict)

    @log.log
    def _get_vnfd(self):
        self.attributes = self.vnf['vnfd']['attributes'].copy()
        self.vnfd_yaml = self.attributes.pop('vnfd', None)
        if self.vnfd_yaml is None:
            # TODO(kangaraj-manickam) raise user level exception
            LOG.info(_("VNFD is not provided, so no vnf is created !!"))
            return
        LOG.debug('vnfd_yaml %s', self.vnfd_yaml)

    @log.log
    def _update_fields(self):
        attributes = self.attributes
        fields = dict((key, attributes.pop(key)) for key
                      in ('stack_name', 'template_url', 'template')
                      if key in attributes)
        for key in ('files', 'parameters'):
            if key in attributes:
                fields[key] = jsonutils.loads(attributes.pop(key))

        # overwrite parameters with given dev_attrs for vnf creation
        dev_attrs = self.vnf['attributes'].copy()
        fields.update(dict((key, dev_attrs.pop(key)) for key
                      in ('stack_name', 'template_url', 'template')
                      if key in dev_attrs))
        for key in ('files', 'parameters'):
            if key in dev_attrs:
                fields.setdefault(key, {}).update(
                    jsonutils.loads(dev_attrs.pop(key)))

        self.attributes = attributes
        self.fields = fields
        return dev_attrs

    @log.log
    def _handle_policies(self, vnfd_dict):

        vnf = self.vnf
        (is_scaling_needed, scaling_group_names,
         main_dict) = self._generate_hot_scaling(
             vnfd_dict['topology_template'], 'scaling.yaml')
        (is_enabled_alarm, alarm_resource, heat_tpl_yaml) =\
            self._generate_hot_alarm_resource(vnfd_dict['topology_template'])
        if is_enabled_alarm and not is_scaling_needed:
            self.fields['template'] = heat_tpl_yaml

        if is_scaling_needed:
            if is_enabled_alarm:
                main_dict['resources'].update(alarm_resource)
            main_yaml = yaml.dump(main_dict)
            self.fields['template'] = main_yaml
            self.fields['files'] = {'scaling.yaml': self.heat_template_yaml}
            vnf['attributes']['heat_template'] = main_yaml
            # TODO(kanagaraj-manickam) when multiple groups are
            # supported, make this scaling atribute as
            # scaling name vs scaling template map and remove
            # scaling_group_names
            vnf['attributes']['scaling.yaml'] = self.heat_template_yaml
            vnf['attributes']['scaling_group_names'] = jsonutils.dumps(
                scaling_group_names)

        elif not vnf['attributes'].get('heat_template'):
            vnf['attributes']['heat_template'] = self.fields['template']
        self.vnf = vnf

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
                        raise cs.InputValuesMissing(key=key)
                elif 'get_input' in value:
                    if value['get_input'] in paramvalues:
                        original[key] = paramvalues[value['get_input']]
                    else:
                        LOG.debug('Key missing Value: %s', key)
                        raise cs.InputValuesMissing(key=key)
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
            raise cs.ParamYAMLInputMissing()

    @log.log
    def _process_vdu_network_interfaces(self, vdu_id, vdu_dict, properties,
                                        template_dict):

        networks_list = []
        properties['networks'] = networks_list
        for network_param in vdu_dict['network_interfaces'].values():
            port = None
            if 'addresses' in network_param:
                ip_list = network_param.pop('addresses', [])
                if not isinstance(ip_list, list):
                    raise vnfm.IPAddrInvalidInput()
                mgmt_flag = network_param.pop('management', False)
                port, template_dict =\
                    self._handle_port_creation(vdu_id, network_param,
                                               template_dict,
                                               ip_list, mgmt_flag)
            if network_param.pop('management', False):
                port, template_dict = self._handle_port_creation(vdu_id,
                                                                 network_param,
                                                                 template_dict,
                                                                 [], True)
            if port is not None:
                network_param = {
                    'port': {'get_resource': port}
                }
            networks_list.append(dict(network_param))
        return vdu_dict, template_dict

    @log.log
    def _make_port_dict(self):
        port_dict = {'type': 'OS::Neutron::Port'}
        if self.unsupported_props:
            port_dict['properties'] = {
                'value_specs': {
                    'port_security_enabled': False
                }
            }
        else:
            port_dict['properties'] = {
                'port_security_enabled': False
            }
        port_dict['properties'].setdefault('fixed_ips', [])
        return port_dict

    @log.log
    def _make_mgmt_outputs_dict(self, vdu_id, port, template_dict):
        mgmt_ip = 'mgmt_ip-%s' % vdu_id
        outputs_dict = template_dict['outputs']
        outputs_dict[mgmt_ip] = {
            'description': 'management ip address',
            'value': {
                'get_attr': [port, 'fixed_ips', 0, 'ip_address']
            }
        }
        template_dict['outputs'] = outputs_dict
        return template_dict

    @log.log
    def _handle_port_creation(self, vdu_id, network_param,
                              template_dict, ip_list=None,
                              mgmt_flag=False):
        ip_list = ip_list or []
        port = '%s-%s-port' % (vdu_id, network_param['network'])
        port_dict = self._make_port_dict()
        if mgmt_flag:
            template_dict = self._make_mgmt_outputs_dict(vdu_id, port,
                                                         template_dict)
        for ip in ip_list:
            port_dict['properties']['fixed_ips'].append({"ip_address": ip})
        port_dict['properties'].update(network_param)
        template_dict['resources'][port] = port_dict
        return port, template_dict

    @log.log
    def _get_unsupported_resource_props(self, heat_client):
        unsupported_resource_props = {}

        for res, prop_dict in iteritems(HEAT_VERSION_INCOMPATIBILITY_MAP):
            unsupported_props = {}
            for prop, val in iteritems(prop_dict):
                if not heat_client.resource_attr_support(res, prop):
                    unsupported_props.update(prop_dict)
            if unsupported_props:
                unsupported_resource_props[res] = unsupported_props
        self.unsupported_props = unsupported_resource_props

    @log.log
    def _generate_hot_from_tosca(self, vnfd_dict, dev_attrs):
        parsed_params = {}
        if 'param_values' in dev_attrs and dev_attrs['param_values'] != "":
            try:
                parsed_params = yaml.load(dev_attrs['param_values'])
            except Exception as e:
                LOG.debug("Params not Well Formed: %s", str(e))
                raise vnfm.ParamYAMLNotWellFormed(error_msg_details=str(e))

        toscautils.updateimports(vnfd_dict)
        if 'substitution_mappings' in str(vnfd_dict):
            toscautils.check_for_substitution_mappings(vnfd_dict,
                parsed_params)

        try:
            tosca = tosca_template.ToscaTemplate(parsed_params=parsed_params,
                                                 a_file=False,
                                                 yaml_dict_tpl=vnfd_dict)

        except Exception as e:
            LOG.debug("tosca-parser error: %s", str(e))
            raise vnfm.ToscaParserFailed(error_msg_details=str(e))

        metadata = toscautils.get_vdu_metadata(tosca)
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
            heat_template_yaml, mgmt_ports, metadata,
            res_tpl, self.unsupported_props)

        self.heat_template_yaml = heat_template_yaml
        self.monitoring_dict = monitoring_dict
        self.metadata = metadata

    @log.log
    def _generate_hot_scaling(self, vnfd_dict,
                              scale_resource_type="OS::Nova::Server"):
        # Initialize the template
        template_dict = yaml.load(HEAT_TEMPLATE_BASE)
        template_dict['description'] = 'Tacker scaling template'

        parameters = {}
        template_dict['parameters'] = parameters

        # Add scaling related resource defs
        resources = {}
        scaling_group_names = {}
        #   policies:
        #     - SP1:
        #         type: tosca.policies.tacker.Scaling
        if 'policies' in vnfd_dict:
            for policy_dict in vnfd_dict['policies']:
                name, policy = list(policy_dict.items())[0]
                if policy['type'] == SCALING_POLICY:
                    resources, scaling_group_names =\
                        self._convert_to_heat_scaling_policy(
                            policy['properties'], scale_resource_type, name)
                    # TODO(kanagaraj-manickam) only one policy is supported
                    # for all vdus. remove this break, once this limitation
                    # is addressed.
                    break

        template_dict['resources'] = resources

        # First return value helps to check if scaling resources exist
        return ((len(template_dict['resources']) > 0), scaling_group_names,
                template_dict)

    @log.log
    def _convert_to_heat_scaling_group(self, policy_prp, scale_resource_type,
                                       name):
        group_hot = {'type': 'OS::Heat::AutoScalingGroup'}
        properties = {}
        properties['min_size'] = policy_prp['min_instances']
        properties['max_size'] = policy_prp['max_instances']
        properties['desired_capacity'] = policy_prp['default_instances']
        properties['cooldown'] = policy_prp['cooldown']
        properties['resource'] = {}
        # TODO(kanagaraj-manickam) all VDU memebers are considered as 1
        # group now and make it to form the groups based on the VDU
        # list mentioned in the policy's targets
        # scale_resource_type is custome type mapped the HOT template
        # generated for all VDUs in the tosca template
        properties['resource']['type'] = scale_resource_type
        # TODO(kanagraj-manickam) add custom type params here, to
        # support parameterized template
        group_hot['properties'] = properties

        return group_hot

    # TODO(kanagaraj-manickam) now only one group is supported, so name
    # is hard-coded with G1
    @log.log
    def _get_scale_group_name(self, targets):
        return 'G1'

    # tosca policies
    #
    # properties:
    #   adjust_by: 1
    #   cooldown: 120
    #   targets: [G1]
    @log.log
    def _convert_to_heat_scaling_policy(self, policy_prp, scale_resource_type,
                                        name):
        # Add scaling related resource defs
        resources = {}
        scaling_group_names = {}

        # Form the group
        scale_grp = self._get_scale_group_name(policy_prp['targets'])
        scaling_group_names[name] = scale_grp
        resources[scale_grp] = self._convert_to_heat_scaling_group(
            policy_prp, scale_resource_type, scale_grp)

        grp_id = {'get_resource': scale_grp}

        policy_hot = {'type': 'OS::Heat::ScalingPolicy'}
        properties = {}
        properties['adjustment_type'] = 'change_in_capacity'
        properties['cooldown'] = policy_prp['cooldown']
        properties['scaling_adjustment'] = policy_prp['increment']
        properties['auto_scaling_group_id'] = grp_id
        policy_hot['properties'] = properties

        # Add scale_out policy
        policy_rsc_name = get_scaling_policy_name(action='out',
                                                  policy_name=name)
        resources[policy_rsc_name] = policy_hot

        # Add scale_in policy
        in_value = '-%d' % int(policy_prp['increment'])
        policy_hot_in = copy.deepcopy(policy_hot)
        policy_hot_in['properties']['scaling_adjustment'] = in_value
        policy_rsc_name = get_scaling_policy_name(action='in',
                                                  policy_name=name)
        resources[policy_rsc_name] = policy_hot_in
        return resources, scaling_group_names

    @log.log
    def _generate_hot_alarm_resource(self, topology_tpl_dict):
        alarm_resource = dict()
        heat_tpl = self.heat_template_yaml
        heat_dict = yamlparser.simple_ordered_parse(heat_tpl)
        is_enabled_alarm = False

        if 'policies' in topology_tpl_dict:
            for policy_dict in topology_tpl_dict['policies']:
                name, policy_tpl_dict = list(policy_dict.items())[0]
                # need to parse triggers here: scaling in/out, respawn,...
                if policy_tpl_dict['type'] == \
                        'tosca.policies.tacker.Alarming':
                    is_enabled_alarm = True
                    triggers = policy_tpl_dict['triggers']
                    for trigger_name, trigger_dict in triggers.items():
                        alarm_resource[trigger_name] =\
                            self._convert_to_heat_monitoring_resource({
                                trigger_name: trigger_dict}, self.vnf)
            heat_dict['resources'].update(alarm_resource)

        heat_tpl_yaml = yaml.dump(heat_dict)
        return (is_enabled_alarm,
                alarm_resource,
                heat_tpl_yaml
                )

    def _convert_to_heat_monitoring_resource(self, mon_policy, vnf):
        mon_policy_hot = {'type': 'OS::Aodh::Alarm'}
        mon_policy_hot['properties'] = \
            self._convert_to_heat_monitoring_prop(mon_policy, vnf)
        return mon_policy_hot

    def _convert_to_heat_monitoring_prop(self, mon_policy, vnf):
        metadata = self.metadata
        trigger_name, trigger_dict = list(mon_policy.items())[0]
        tpl_condition = trigger_dict['condition']
        properties = dict()
        if not (trigger_dict.get('metadata') and metadata):
            raise vnfm.MetadataNotMatched()
        matching_metadata_dict = dict()
        properties['meter_name'] = trigger_dict['metrics']
        is_matched = False
        for vdu_name, metadata_dict in metadata['vdus'].items():
            if trigger_dict['metadata'] ==\
                    metadata_dict['metering.vnf']:
                is_matched = True
        if not is_matched:
            raise vnfm.MetadataNotMatched()
        matching_metadata_dict['metadata.user_metadata.vnf'] =\
            trigger_dict['metadata']
        properties['matching_metadata'] = \
            matching_metadata_dict
        properties['comparison_operator'] = \
            tpl_condition['comparison_operator']
        properties['period'] = tpl_condition['period']
        properties['evaluation_periods'] = tpl_condition['evaluations']
        properties['statistic'] = tpl_condition['method']
        properties['description'] = tpl_condition['constraint']
        properties['threshold'] = tpl_condition['threshold']
        # alarm url process here
        alarm_url = vnf['attributes'].get(trigger_name)
        if alarm_url:
            alarm_url = str(alarm_url)
            LOG.debug('Alarm url in heat %s', alarm_url)
            properties['alarm_actions'] = [alarm_url]
        return properties
