# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

import sys
import time

from heatclient import exc as heatException
from oslo_config import cfg
from toscaparser.tosca_template import ToscaTemplate
from toscaparser.utils import yamlparser
from translator.hot.tosca_translator import TOSCATranslator
import yaml

from tacker.common import clients
from tacker.common import log
from tacker.extensions import vnfm
from tacker.openstack.common import jsonutils
from tacker.openstack.common import log as logging
from tacker.vm.infra_drivers import abstract_driver
from tacker.vm.tosca import utils as toscautils


LOG = logging.getLogger(__name__)
CONF = cfg.CONF
OPTS = [
    cfg.IntOpt('stack_retries',
               default=60,
               help=_("Number of attempts to retry for stack"
                      "creation/deletion")),
    cfg.IntOpt('stack_retry_wait',
               default=5,
               help=_("Wait time between two successive stack"
                      "create/delete retries")),
    cfg.DictOpt('flavor_extra_specs',
               default={},
               help=_("Flavor Extra Specs")),
]
CONF.register_opts(OPTS, group='tacker_heat')
STACK_RETRIES = cfg.CONF.tacker_heat.stack_retries
STACK_RETRY_WAIT = cfg.CONF.tacker_heat.stack_retry_wait
STACK_FLAVOR_EXTRA = cfg.CONF.tacker_heat.flavor_extra_specs

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


class DeviceHeat(abstract_driver.DeviceAbstractDriver):

    """Heat driver of hosting device."""

    def __init__(self):
        super(DeviceHeat, self).__init__()

    def get_type(self):
        return 'heat'

    def get_name(self):
        return 'heat'

    def get_description(self):
        return 'Heat infra driver'

    @log.log
    def create_device_template_pre(self, plugin, context, device_template):
        device_template_dict = device_template['device_template']
        vnfd_yaml = device_template_dict['attributes'].get('vnfd')
        if vnfd_yaml is None:
            return

        vnfd_dict = yaml.load(vnfd_yaml)
        LOG.debug(_('vnfd_dict: %s'), vnfd_dict)

        if 'tosca_definitions_version' in vnfd_dict:
            # Prepend the tacker_defs.yaml import file with the full
            # path to the file
            toscautils.updateimports(vnfd_dict)

            try:
                tosca = ToscaTemplate(a_file=False, yaml_dict_tpl=vnfd_dict)
            except Exception as e:
                LOG.exception(_("tosca-parser error: %s"), str(e))
                raise vnfm.ToscaParserFailed(error_msg_details=str(e))

            if ('description' not in device_template_dict or
                    device_template_dict['description'] == ''):
                device_template_dict['description'] = vnfd_dict.get(
                    'description', '')
            if (('name' not in device_template_dict or
                    not len(device_template_dict['name'])) and
                    'metadata' in vnfd_dict):
                device_template_dict['name'] = vnfd_dict['metadata'].get(
                    'template_name', '')

            device_template_dict['mgmt_driver'] = toscautils.get_mgmt_driver(
                tosca)
        else:
            KEY_LIST = (('name', 'template_name'),
                        ('description', 'description'))

            device_template_dict.update(
                dict((key, vnfd_dict[vnfd_key]) for (key, vnfd_key) in KEY_LIST
                     if ((key not in device_template_dict or
                          device_template_dict[key] == '') and
                         vnfd_key in vnfd_dict and
                         vnfd_dict[vnfd_key] != '')))

            service_types = vnfd_dict.get('service_properties', {}).get('type',
                                                                        [])
            if service_types:
                device_template_dict.setdefault('service_types', []).extend(
                    [{'service_type': service_type}
                    for service_type in service_types])
            # TODO(anyone)  - this code assumes one mgmt_driver per VNFD???
            for vdu in vnfd_dict.get('vdus', {}).values():
                mgmt_driver = vdu.get('mgmt_driver')
                if mgmt_driver:
                    device_template_dict['mgmt_driver'] = mgmt_driver
        LOG.debug(_('device_template %s'), device_template)

    @log.log
    def _update_params(self, original, paramvalues, match=False):
        for key, value in original.iteritems():
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
            if ip_list is None:
                ip_list = []
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

        for res, prop_dict in HEAT_VERSION_INCOMPATIBILITY_MAP.iteritems():
            unsupported_prop = {}
            for prop, val in prop_dict.iteritems():
                if not heat_client.resource_attr_support(res, prop):
                    unsupported_prop.update(prop_dict)
            if unsupported_prop:
                unsupported_resource_prop[res] = unsupported_prop
        return unsupported_resource_prop

    @log.log
    def create(self, plugin, context, device, auth_attr):
        LOG.debug(_('device %s'), device)
        attributes = device['device_template']['attributes'].copy()
        vnfd_yaml = attributes.pop('vnfd', None)
        fields = dict((key, attributes.pop(key)) for key
                      in ('stack_name', 'template_url', 'template')
                      if key in attributes)
        for key in ('files', 'parameters'):
            if key in attributes:
                fields[key] = jsonutils.loads(attributes.pop(key))

        # overwrite parameters with given dev_attrs for device creation
        dev_attrs = device['attributes'].copy()
        fields.update(dict((key, dev_attrs.pop(key)) for key
                      in ('stack_name', 'template_url', 'template')
                      if key in dev_attrs))
        for key in ('files', 'parameters'):
            if key in dev_attrs:
                fields.setdefault(key, {}).update(
                    jsonutils.loads(dev_attrs.pop(key)))

        region_name = device.get('placement_attr', {}).get('region_name', None)
        heatclient_ = HeatClient(auth_attr, region_name)
        unsupported_res_prop = self.fetch_unsupported_resource_prop(
            heatclient_)

        LOG.debug('vnfd_yaml %s', vnfd_yaml)
        if vnfd_yaml is not None:
            vnfd_dict = yamlparser.simple_ordered_parse(vnfd_yaml)
            LOG.debug('vnfd_dict %s', vnfd_dict)

            monitoring_dict = {'vdus': {}}

            if 'tosca_definitions_version' in vnfd_dict:
                parsed_params = dev_attrs.pop('param_values', {})

                toscautils.updateimports(vnfd_dict)

                try:
                    tosca = ToscaTemplate(parsed_params=parsed_params,
                                      a_file=False, yaml_dict_tpl=vnfd_dict)

                except Exception as e:
                    LOG.debug("tosca-parser error: %s", str(e))
                    raise vnfm.ToscaParserFailed(error_msg_details=str(e))

                monitoring_dict = toscautils.get_vdu_monitoring(tosca)
                mgmt_ports = toscautils.get_mgmt_ports(tosca)
                res_tpl = toscautils.get_resources_dict(tosca,
                                                        STACK_FLAVOR_EXTRA)
                toscautils.post_process_template(tosca)
                try:
                    translator = TOSCATranslator(tosca, parsed_params)
                    heat_template_yaml = translator.translate()
                except Exception as e:
                    LOG.debug("heat-translator error: %s", str(e))
                    raise vnfm.HeatTranslatorFailed(error_msg_details=str(e))
                heat_template_yaml = toscautils.post_process_heat_template(
                    heat_template_yaml, mgmt_ports, res_tpl,
                    unsupported_res_prop)
            else:
                assert 'template' not in fields
                assert 'template_url' not in fields
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
                        monitoring_dict['vdus'][vdu_id] = \
                            vdu_dict['monitoring_policy']

                    # to pass necessary parameters to plugin upwards.
                    for key in ('service_type',):
                        if key in vdu_dict:
                            device.setdefault(
                                'attributes', {})[vdu_id] = jsonutils.dumps(
                                    {key: vdu_dict[key]})

                    heat_template_yaml = yaml.dump(template_dict)

            fields['template'] = heat_template_yaml
            if not device['attributes'].get('heat_template'):
                device['attributes']['heat_template'] = \
                    heat_template_yaml

            if monitoring_dict.keys():
                    device['attributes']['monitoring_policy'] = \
                        jsonutils.dumps(monitoring_dict)

        if 'stack_name' not in fields:
            name = (__name__ + '_' + self.__class__.__name__ + '-' +
                    device['id'])
            if device['attributes'].get('failure_count'):
                name += ('-%s') % str(device['attributes']['failure_count'])
            fields['stack_name'] = name

        # service context is ignored
        LOG.debug(_('service_context: %s'), device.get('service_context', []))

        LOG.debug(_('fields: %s'), fields)
        LOG.debug(_('template: %s'), fields['template'])
        stack = heatclient_.create(fields)
        return stack['stack']['id']

    def create_wait(self, plugin, context, device_dict, device_id, auth_attr):
        region_name = device_dict.get('placement_attr', {}).get(
            'region_name', None)
        heatclient_ = HeatClient(auth_attr, region_name)

        stack = heatclient_.get(device_id)
        status = stack.stack_status
        stack_retries = STACK_RETRIES
        while status == 'CREATE_IN_PROGRESS' and stack_retries > 0:
            time.sleep(STACK_RETRY_WAIT)
            try:
                stack = heatclient_.get(device_id)
            except Exception:
                LOG.exception(_("Device Instance cleanup may not have "
                                "happened because Heat API request failed "
                                "while waiting for the stack %(stack)s to be "
                                "deleted"), {'stack': device_id})
                break
            status = stack.stack_status
            LOG.debug(_('status: %s'), status)
            stack_retries = stack_retries - 1

        LOG.debug(_('stack status: %(stack)s %(status)s'),
                  {'stack': str(stack), 'status': status})
        if stack_retries == 0:
            LOG.warning(_("Resource creation is"
                          " not completed within %(wait)s seconds as "
                          "creation of Stack %(stack)s is not completed"),
                        {'wait': (STACK_RETRIES * STACK_RETRY_WAIT),
                         'stack': device_id})
        if status != 'CREATE_COMPLETE':
            raise vnfm.DeviceCreateWaitFailed(device_id=device_id)
        outputs = stack.outputs
        LOG.debug(_('outputs %s'), outputs)
        PREFIX = 'mgmt_ip-'
        mgmt_ips = dict((output['output_key'][len(PREFIX):],
                         output['output_value'])
                        for output in outputs
                        if output.get('output_key', '').startswith(PREFIX))
        if mgmt_ips:
            device_dict['mgmt_url'] = jsonutils.dumps(mgmt_ips)

    @log.log
    def update(self, plugin, context, device_id, device_dict, device,
               auth_attr):
        region_name = device_dict.get('placement_attr', {}).get(
            'region_name', None)
        heatclient_ = HeatClient(auth_attr, region_name)
        heatclient_.get(device_id)

        # update config attribute
        config_yaml = device_dict.get('attributes', {}).get('config', '')
        update_yaml = device['device'].get('attributes', {}).get('config', '')
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
        device_dict.setdefault('attributes', {})['config'] = new_yaml

    def update_wait(self, plugin, context, device_id, auth_attr,
                    region_name=None):
        # do nothing but checking if the stack exists at the moment
        heatclient_ = HeatClient(auth_attr, region_name)
        heatclient_.get(device_id)

    def delete(self, plugin, context, device_id, auth_attr, region_name=None):
        heatclient_ = HeatClient(auth_attr, region_name)
        heatclient_.delete(device_id)

    @log.log
    def delete_wait(self, plugin, context, device_id, auth_attr,
                    region_name=None):
        heatclient_ = HeatClient(auth_attr, region_name)

        stack = heatclient_.get(device_id)
        status = stack.stack_status
        stack_retries = STACK_RETRIES
        while (status == 'DELETE_IN_PROGRESS' and stack_retries > 0):
            time.sleep(STACK_RETRY_WAIT)
            try:
                stack = heatclient_.get(device_id)
            except heatException.HTTPNotFound:
                return
            except Exception:
                LOG.exception(_("Device Instance cleanup may not have "
                                "happened because Heat API request failed "
                                "while waiting for the stack %(stack)s to be "
                                "deleted"), {'stack': device_id})
                break
            status = stack.stack_status
            stack_retries = stack_retries - 1

        if stack_retries == 0:
            LOG.warning(_("Resource cleanup for device is"
                          " not completed within %(wait)s seconds as "
                          "deletion of Stack %(stack)s is not completed"),
                        {'wait': (STACK_RETRIES * STACK_RETRY_WAIT),
                         'stack': device_id})
        if status != 'DELETE_COMPLETE':
            LOG.warning(_("device (%(device_id)d) deletion is not completed. "
                          "%(stack_status)s"),
                        {'device_id': device_id, 'stack_status': status})


class HeatClient(object):
    def __init__(self, auth_attr, region_name=None):
        # context, password are unused
        self.heat = clients.OpenstackClients(auth_attr, region_name).heat
        self.stacks = self.heat.stacks
        self.resource_types = self.heat.resource_types

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
