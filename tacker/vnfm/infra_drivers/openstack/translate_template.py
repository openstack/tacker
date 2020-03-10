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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import uuidutils
from toscaparser import tosca_template
from toscaparser.utils import yamlparser
from translator.hot import tosca_translator
import yaml

from tacker._i18n import _
from tacker.common import exceptions
from tacker.common import log
from tacker.extensions import common_services as cs
from tacker.extensions import vnfm
from tacker.plugins.common import constants
from tacker.tosca import utils as toscautils


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


class TOSCAToHOT(object):
    """Convert TOSCA template to HOT template."""

    def __init__(self, vnf, heatclient, inst_req_info=None, grant_info=None):
        self.vnf = vnf
        self.heatclient = heatclient
        self.attributes = {}
        self.vnfd_yaml = None
        self.unsupported_props = {}
        self.heat_template_yaml = None
        self.monitoring_dict = None
        self.nested_resources = dict()
        self.fields = None
        self.STACK_FLAVOR_EXTRA = cfg.CONF.openstack_vim.flavor_extra_specs
        self.appmonitoring_dict = None
        self.grant_info = grant_info
        self.inst_req_info = inst_req_info

    @log.log
    def generate_hot(self):

        self._get_vnfd()
        dev_attrs = self._update_fields()
        vnfd_dict = yamlparser.simple_ordered_parse(self.vnfd_yaml)
        LOG.debug('vnfd_dict %s', vnfd_dict)
        self._get_unsupported_resource_props(self.heatclient)

        self._generate_hot_from_tosca(vnfd_dict, dev_attrs,
                                      self.inst_req_info, self.grant_info)
        self.fields['template'] = self.heat_template_yaml
        if not self.vnf['attributes'].get('heat_template'):
            self.vnf['attributes']['heat_template'] = self.fields['template']
        if self.monitoring_dict:
            self.vnf['attributes'][
                'monitoring_policy'] = jsonutils.dump_as_bytes(
                self.monitoring_dict)
        if self.appmonitoring_dict:
            self.vnf['attributes']['app_monitoring_policy'] = \
                jsonutils.dump_as_bytes(self.appmonitoring_dict)

    @log.log
    def _get_vnfd(self):
        self.attributes = self.vnf['vnfd']['attributes'].copy()
        self.vnfd_yaml = self.attributes.pop('vnfd', None)
        if self.vnfd_yaml is None:
            LOG.error("VNFD is not provided, so no vnf is created !!")
            raise exceptions.InvalidInput("VNFD template is None.")
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
    def _update_params(self, original, paramvalues, match=False):
        for key, value in (original).items():
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
                param_vattrs_dict = yaml.safe_load(param_vattrs_yaml)
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

        for res, prop_dict in (HEAT_VERSION_INCOMPATIBILITY_MAP).items():
            unsupported_props = {}
            for prop, val in (prop_dict).items():
                if not heat_client.resource_attr_support(res, prop):
                    unsupported_props.update(prop_dict)
            if unsupported_props:
                unsupported_resource_props[res] = unsupported_props
        self.unsupported_props = unsupported_resource_props

    @log.log
    def _generate_hot_from_tosca(self, vnfd_dict, dev_attrs,
                                 inst_req_info=None,
                                 grant_info=None):
        parsed_params = {}
        if 'param_values' in dev_attrs and dev_attrs['param_values'] != "":
            try:
                parsed_params = yaml.safe_load(dev_attrs['param_values'])
            except Exception as e:
                LOG.debug("Params not Well Formed: %s", str(e))
                raise vnfm.ParamYAMLNotWellFormed(error_msg_details=str(e))

        appmonitoring_dict = \
            toscautils.get_vdu_applicationmonitoring(vnfd_dict)

        block_storage_details = toscautils.get_block_storage_details(
            vnfd_dict)
        toscautils.updateimports(vnfd_dict)
        if 'substitution_mappings' in str(vnfd_dict):
            toscautils.check_for_substitution_mappings(
                vnfd_dict,
                parsed_params
            )

        try:
            tosca = tosca_template.ToscaTemplate(parsed_params=parsed_params,
                                                 a_file=False,
                                                 yaml_dict_tpl=vnfd_dict)

        except Exception as e:
            LOG.debug("tosca-parser error: %s", str(e))
            raise vnfm.ToscaParserFailed(error_msg_details=str(e))

        unique_id = uuidutils.generate_uuid()
        metadata = toscautils.get_vdu_metadata(tosca, unique_id=unique_id)
        for policy in tosca.policies:
            if policy.entity_tpl['type'] == constants.POLICY_RESERVATION:
                metadata = toscautils.get_metadata_for_reservation(
                    tosca, metadata)
                break

        alarm_resources = toscautils.pre_process_alarm_resources(
            self.vnf, tosca, metadata, unique_id=unique_id)
        monitoring_dict = toscautils.get_vdu_monitoring(tosca)
        mgmt_ports = toscautils.get_mgmt_ports(tosca)
        res_tpl = toscautils.get_resources_dict(tosca,
                                                self.STACK_FLAVOR_EXTRA)
        toscautils.post_process_template(tosca)
        scaling_policy_names = toscautils.get_scaling_policy(tosca)
        try:
            translator = tosca_translator.TOSCATranslator(tosca, parsed_params)

            heat_template_yaml = translator.translate()
            nested_resource_names = toscautils.get_nested_resources_name(
                heat_template_yaml)
            if nested_resource_names:
                for nested_resource_name in nested_resource_names:
                    sub_heat_tmpl_name = \
                        toscautils.get_sub_heat_tmpl_name(nested_resource_name)
                    sub_heat_template_yaml =\
                        translator.translate_to_yaml_files_dict(
                            sub_heat_tmpl_name)
                    nested_resource_yaml = \
                        sub_heat_template_yaml[nested_resource_name]
                    LOG.debug("nested_resource_yaml: %s", nested_resource_yaml)
                    self.nested_resources[nested_resource_name] = \
                        nested_resource_yaml

        except Exception as e:
            LOG.debug("heat-translator error: %s", str(e))
            raise vnfm.HeatTranslatorFailed(error_msg_details=str(e))

        if self.nested_resources:
            nested_tpl = toscautils.update_nested_scaling_resources(
                self.nested_resources,
                mgmt_ports, metadata, res_tpl, self.unsupported_props,
                grant_info=grant_info, inst_req_info=inst_req_info)
            self.fields['files'] = nested_tpl
            for nested_resource_name in nested_tpl.keys():
                self.vnf['attributes'][nested_resource_name] =\
                    nested_tpl[nested_resource_name]
            mgmt_ports.clear()

        if scaling_policy_names:
            scaling_group_dict = toscautils.get_scaling_group_dict(
                heat_template_yaml, scaling_policy_names)
            self.vnf['attributes']['scaling_group_names'] =\
                jsonutils.dump_as_bytes(scaling_group_dict)

        if self.vnf['attributes'].get('maintenance', None):
            toscautils.add_maintenance_resources(tosca, res_tpl)

        heat_template_yaml = toscautils.post_process_heat_template(
            heat_template_yaml, mgmt_ports, metadata, alarm_resources,
            res_tpl, block_storage_details, self.unsupported_props,
            unique_id=unique_id, inst_req_info=inst_req_info,
            grant_info=grant_info, tosca=tosca)

        try:
            for nested_resource_name in self.nested_resources.keys():
                self.nested_resources[nested_resource_name] = \
                    toscautils.post_process_heat_template_for_scaling(
                    self.nested_resources[nested_resource_name],
                    mgmt_ports, metadata, alarm_resources,
                    res_tpl, block_storage_details, self.unsupported_props,
                    unique_id=unique_id, inst_req_info=inst_req_info,
                    grant_info=grant_info, tosca=tosca)
        except Exception as e:
            LOG.debug("post_process_heat_template_for_scaling "
                      "error: %s", str(e))
            raise

        self.heat_template_yaml = heat_template_yaml
        self.monitoring_dict = monitoring_dict
        self.metadata = metadata
        self.appmonitoring_dict = appmonitoring_dict

    @log.log
    def represent_odict(self, dump, tag, mapping, flow_style=None):
        value = []
        node = yaml.MappingNode(tag, value, flow_style=flow_style)
        if dump.alias_key is not None:
            dump.represented_objects[dump.alias_key] = node
        best_style = True
        if hasattr(mapping, 'items'):
            mapping = mapping.items()
        for item_key, item_value in mapping:
            node_key = dump.represent_data(item_key)
            node_value = dump.represent_data(item_value)
            if not (isinstance(node_key, yaml.ScalarNode)
                    and not node_key.style):
                best_style = False
            if not (isinstance(node_value, yaml.ScalarNode)
                    and not node_value.style):
                best_style = False
            value.append((node_key, node_value))
        if flow_style is None:
            if dump.default_flow_style is not None:
                node.flow_style = dump.default_flow_style
            else:
                node.flow_style = best_style
        return node
