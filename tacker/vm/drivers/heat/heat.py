# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2015 Intel Corporation.
# Copyright 2015 Isaku Yamahata <isaku.yamahata at intel com>
#                               <isaku.yamahata at gmail com>
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
#
# @author: Isaku Yamahata, Intel Corporation.
# shamelessly many codes are stolen from gbp simplechain_driver.py

import time
import yaml

from heatclient import client as heat_client
from heatclient import exc as heatException
from oslo_config import cfg

from tacker.common import log
from tacker.openstack.common import jsonutils
from tacker.openstack.common import log as logging
from tacker.vm.drivers import abstract_driver


LOG = logging.getLogger(__name__)
CONF = cfg.CONF
OPTS = [
    cfg.StrOpt('heat_uri',
               default='http://localhost:8004/v1',
               help=_("Heat server address to create services "
                      "specified in the service chain.")),
    cfg.IntOpt('stack_retries',
               default=10,
               help=_("Number of attempts to retry for stack deletion")),
    cfg.IntOpt('stack_retry_wait',
               default=5,
               help=_("Wait time between two successive stack delete "
                      "retries")),
]
CONF.register_opts(OPTS, group='servicevm_heat')
STACK_RETRIES = cfg.CONF.servicevm_heat.stack_retries
STACK_RETRY_WAIT = cfg.CONF.servicevm_heat.stack_retry_wait

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
    def create(self, plugin, context, device):
        LOG.debug(_('device %s'), device)
        heatclient_ = HeatClient(context)
        attributes = device['device_template']['attributes'].copy()
        vnfd_yaml = attributes.pop('vnfd', None)
        fields = dict((key, attributes.pop(key)) for key
                      in ('stack_name', 'template_url', 'template')
                      if key in attributes)
        for key in ('files', 'parameters'):
            if key in attributes:
                fields[key] = jsonutils.loads(attributes.pop(key))
        fields.setdefault('parameters', {}).update(attributes)

        # overwrite parameters with given dev_attrs for device creation
        dev_attrs = device['attributes'].copy()
        config_yaml = dev_attrs.pop('config', None)
        fields.update(dict((key, dev_attrs.pop(key)) for key
                      in ('stack_name', 'template_url', 'template')
                      if key in dev_attrs))
        for key in ('files', 'parameters'):
            if key in dev_attrs:
                dev_attrs[key] = dev_attrs.pop(key)
        fields['parameters'].update(dev_attrs)
        LOG.debug('vnfd_yaml %s', vnfd_yaml)
        if vnfd_yaml is not None:
            assert 'template' not in fields
            assert 'template_url' not in fields
            template_dict = yaml.load(HEAT_TEMPLATE_BASE)
            outputs_dict = {}
            template_dict['outputs'] = outputs_dict

            vnfd_dict = yaml.load(vnfd_yaml)
            LOG.debug('vnfd_dict %s', vnfd_dict)
            KEY_LIST = (('description', 'description'),
                        )
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
                    # properties['networks'] = (
                    #     vdu_dict['network_interfaces'].values())
                    networks_list = []
                    properties['networks'] = networks_list
                    for network_param in vdu_dict[
                            'network_interfaces'].values():
                        if network_param.pop('management', False):
                            MGMT_PORT = 'mgmt_port'
                            mgmt_port_dict = {
                                'type': 'OS::Neutron::Port',
                                'properties': {
                                    'port_security_enabled': False,
                                }
                            }
                            mgmt_port_dict['properties'].update(network_param)
                            template_dict['resources'][
                                MGMT_PORT] = mgmt_port_dict
                            network_param = {
                                'port': {'get_resource': MGMT_PORT}
                            }
                            outputs_dict['mgmt_ip'] = {
                                'description': 'management ip address',
                                'value': {
                                    'get_attr': [MGMT_PORT, 'fixed_ips',
                                                 0, 'ip_address']
                                }
                            }
                        networks_list.append(network_param)
                if ('placement_policy' in vdu_dict and
                    'availability_zone' in vdu_dict['placement_policy']):
                    properties['availability_zone'] = vdu_dict[
                        'placement_policy']['availability_zone']
                if 'config' in vdu_dict:
                    properties['config_drive'] = True
                    properties.setdefault('metadata', {}).update(
                        vdu_dict['config'])

                # monitoring_policy = vdu_dict.get('monitoring_policy', None)
                # failure_policy = vdu_dict.get('failure_policy', None)

                # to pass necessary parameters to plugin upwards.
                for key in ('monitoring_policy', 'failure_policy'):
                    if key in vdu_dict:
                        device.setdefault(
                            'attributes', {})[key] = vdu_dict[key]

            if config_yaml is not None:
                config_dict = yaml.load(config_yaml)
                resources = template_dict.setdefault('resources', {})
                for vdu_id, vdu_dict in config_dict.get('vdus', {}).items():
                    if vdu_id not in resources:
                        continue
                    config = vdu_dict.get('config', None)
                    if not config:
                        continue
                    properties = resources[vdu_id].setdefault('properties', {})
                    properties['config_drive'] = True
                    properties.setdefault('metadata', {}).update(config)

            fields['template'] = yaml.dump(template_dict)

        if 'stack_name' not in fields:
            name = (__name__ + '_' + self.__class__.__name__ + '-' +
                    device['id'])
            fields['stack_name'] = name

        # service context is ignored
        LOG.debug(_('service_context: %s'), device.get('service_context', []))

        LOG.debug(_('fields: %s'), fields)
        LOG.debug(_('template: %s'), fields['template'])
        stack = heatclient_.create(fields)
        return stack['stack']['id']

    def create_wait(self, plugin, context, device_dict, device_id):
        heatclient_ = HeatClient(context)

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
                  {'stack': stack, 'status': status})
        if stack_retries == 0:
            LOG.warn(_("Resource creation is"
                       " not completed within %(wait)s seconds as "
                       "creation of Stack %(stack)s is not completed"),
                     {'wait': (STACK_RETRIES * STACK_RETRY_WAIT),
                      'stack': device_id})
        if status != 'CREATE_COMPLETE':
            raise RuntimeError(_("creation of server %s faild") % device_id)
        outputs = stack.outputs
        LOG.debug(_('outputs %s'), outputs)
        mgmt_ip = [output['output_value'] for output in outputs if
                   output.get('output_key', None) == 'mgmt_ip']
        if mgmt_ip:
            device_dict['mgmt_url'] = mgmt_ip[0]

    def update(self, plugin, context, device):
        # do nothing but checking if the stack exists at the moment
        heatclient_ = HeatClient(context)
        heatclient_.get(device['id'])

    def update_wait(self, plugin, context, device_id):
        # do nothing but checking if the stack exists at the moment
        heatclient_ = HeatClient(context)
        heatclient_.get(device_id)

    def delete(self, plugin, context, device_id):
        heatclient_ = HeatClient(context)
        heatclient_.delete(device_id)

    @log.log
    def delete_wait(self, plugin, context, device_id):
        heatclient_ = HeatClient(context)

        stack = heatclient_.get(device_id)
        status = stack.satck_status
        stack_retries = STACK_RETRIES
        while (status == 'DELETE_IN_PROGRESS' and stack_retries > 0):
            time.sleep(STACK_RETRY_WAIT)
            try:
                stack = heatclient_.get(device_id)
            except Exception:
                LOG.exception(_("Device Instance cleanup may not have "
                                "happened because Heat API request failed "
                                "while waiting for the stack %(stack)s to be "
                                "deleted"), {'stack': device_id})
                break
            status = stack.satck_status
            stack_retries = stack_retries - 1

        if stack_retries == 0:
            LOG.warn(_("Resource cleanup for device is"
                       " not completed within %(wait)s seconds as "
                       "deletion of Stack %(stack)s is not completed"),
                     {'wait': (STACK_RETRIES * STACK_RETRY_WAIT),
                      'stack': device_id})
        if status != 'DELETE_COMPLETE':
            LOG.warn(_("device (%(device_id)d) deletion is not completed. "
                       "%(stack_status)s"),
                     {'device_id': device_id, 'stack_status': status})

    @log.log
    def attach_interface(self, plugin, context, device_id, port_id):
        raise NotImplementedError()

    @log.log
    def dettach_interface(self, plugin, context, device_id, port_id):
        raise NotImplementedError()


class HeatClient:
    def __init__(self, context, password=None):
        api_version = "1"
        endpoint = "%s/%s" % (cfg.CONF.servicevm_heat.heat_uri, context.tenant)
        kwargs = {
            'token': context.auth_token,
            'username': context.user_name,
            'password': password
        }
        self.client = heat_client.Client(api_version, endpoint, **kwargs)
        self.stacks = self.client.stacks

    def create(self, fields):
        fields = fields.copy()
        fields.update({
            'timeout_mins': 10,
            'disable_rollback': True})
        if 'password' in fields.get('template', {}):
            fields['password'] = fields['template']['password']
        return self.stacks.create(**fields)

    def delete(self, stack_id):
        try:
            self.stacks.delete(stack_id)
        except heatException.HTTPNotFound:
            LOG.warn(_("Stack %(stack)s created by service chain driver is "
                       "not found at cleanup"), {'stack': stack_id})

    def get(self, stack_id):
        return self.stacks.get(stack_id)
