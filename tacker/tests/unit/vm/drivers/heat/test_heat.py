# Copyright 2015 Brocade Communications System, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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

import mock
import testtools

from tacker import context
from tacker.tests.unit.db import utils
from tacker.vm.drivers.heat import heat


class FakeHeatClient(mock.Mock):

    class Stack(mock.Mock):
        stack_status = 'CREATE_COMPLETE'
        outputs = [{u'output_value': u'192.168.120.31', u'description':
            u'management ip address', u'output_key': u'mgmt_ip-vdu1'}]

    def create(self, *args, **kwargs):
        return {'stack': {'id': '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}}

    def get(self, id):
        return self.Stack()


class TestDeviceHeat(testtools.TestCase):
    def setUp(self):
        super(TestDeviceHeat, self).setUp()
        self.context = context.get_admin_context()
        self.heat_driver = heat.DeviceHeat()
        self._mock_heat_client()
        self.addCleanup(mock.patch.stopall)

    def _mock_heat_client(self):
        self.heat_client = mock.Mock(wraps=FakeHeatClient())
        fake_heat_client = mock.Mock()
        fake_heat_client.return_value = self.heat_client
        self._mock(
            'tacker.vm.drivers.heat.heat.HeatClient', fake_heat_client)

    def _mock(self, target, new=mock.DEFAULT):
        patcher = mock.patch(target, new)
        return patcher.start()

    def _get_expected_fields(self):
        return {'stack_name': 'tacker.vm.drivers.heat.heat_DeviceHeat-eb84260e'
                              '-5ff7-4332-b032-50a14d6c1123', 'template':
            'description: OpenWRT with services\nheat_template_version: '
            '2013-05-23\noutputs:\n  mgmt_ip-vdu1:\n    description: '
            'management ip address\n    value:\n      get_attr: [vdu1-net_mgmt'
            '-port, fixed_ips, 0, ip_address]\nresources:\n  vdu1:\n    '
            'properties:\n      availability_zone: nova\n      config_drive: '
            'true\n      flavor: m1.tiny\n      image: cirros-0.3.2-x86_64-uec'
            '\n      metadata: {param0: key0, param1: key1}\n      networks:\n'
            '      - port: {get_resource: vdu1-net_mgmt-port}\n      - '
            '{network: net0}\n      - {network: net1}\n    type: OS::Nova::'
            'Server\n  vdu1-net_mgmt-port:\n    properties:\n      fixed_ips: '
            '[]\n      network: net_mgmt\n      port_security_enabled: false\n'
            '    type: OS::Neutron::Port\n'}

    def _get_expected_fields_user_data(self):
        return {'stack_name': 'tacker.vm.drivers.heat.heat_DeviceHeat-18685f68'
                              '-2b2a-4185-8566-74f54e548811', 'template':
            'description: Parameterized VNF descriptor\nheat_template_version:'
            ' 2013-05-23\noutputs:\n  mgmt_ip-vdu1:\n    description: '
            'management ip address\n    value:\n      get_attr: '
            '[vdu1-net_mgmt-port, fixed_ips, 0, ip_address]\nresources:\n  '
            'vdu1:\n    properties:\n      availability_zone: nova\n      '
            'config_drive: true\n      flavor: m1.tiny\n      image: '
            'cirros-0.3.4-x86_64-uec\n      metadata: {param0: key0, param1: '
            'key1}\n      networks:\n      - port: {get_resource: '
            'vdu1-net_mgmt-port}\n      - {network: net0}\n      - '
            '{network: net1}\n      user_data: \'#!/bin/sh\n\n        '
            'echo "my hostname is `hostname`" > /tmp/hostname\n\n        '
            'df -h > /home/cirros/diskinfo\n\n        \'\n      '
            'user_data_format: RAW\n    type: OS::Nova::Server\n  '
            'vdu1-net_mgmt-port:\n    properties:\n      fixed_ips: []\n      '
            'network: net_mgmt\n      port_security_enabled: false\n    '
            'type: OS::Neutron::Port\n'}

    def _get_expected_fields_ipaddr_data(self):
        return {'stack_name': 'tacker.vm.drivers.heat.heat_DeviceHeat-d1337add'
                              '-d5a1-4fd4-9447-bb9243c8460b', 'template':
            'description: Parameterized VNF descriptor for IP addresses\n'
            'heat_template_version: 2013-05-23\noutputs:\n  mgmt_ip-vdu1:\n   '
            ' description: management ip address\n    value:\n      '
            'get_attr: [vdu1-net_mgmt-port, fixed_ips, 0, ip_address]\n'
            'resources:\n  vdu1:\n    properties:\n      availability_zone: '
            'nova\n      config_drive: true\n      flavor: m1.tiny\n      '
            'image: cirros-0.3.4-x86_64-uec\n      metadata: {param0: key0, '
            'param1: key1}\n      networks:\n      - port: {get_resource: '
            'vdu1-net_mgmt-port}\n      - port: {get_resource: vdu1-net0-port}'
            '\n      - port: {get_resource: vdu1-net1-port}\n    type: '
            'OS::Nova::Server\n  vdu1-net0-port:\n    properties:\n      '
            'fixed_ips:\n      - {ip_address: 10.10.0.98}\n      network: net0'
            '\n      port_security_enabled: false\n    type: '
            'OS::Neutron::Port\n  vdu1-net1-port:\n    properties:\n      '
            'fixed_ips:\n      - {ip_address: 10.10.1.98}\n      network: net1'
            '\n      port_security_enabled: false\n    type: '
            'OS::Neutron::Port\n  vdu1-net_mgmt-port:\n    properties:\n      '
            'fixed_ips:\n      - {ip_address: 192.168.120.98}\n      network: '
            'net_mgmt\n      port_security_enabled: false\n    '
            'type: OS::Neutron::Port\n'}

    def _get_expected_device_wait_obj(self):
        return {'status': 'PENDING_CREATE', 'instance_id': None, 'name':
            u'test_openwrt', 'tenant_id':
        u'ad7ebc56538745a08ef7c5e97f8bd437', 'template_id':
        u'eb094833-995e-49f0-a047-dfb56aaf7c4e', 'device_template': {
            'service_types': [{'service_type': u'vnfd', 'id':
            u'4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}], 'description':
            u'OpenWRT with services', 'tenant_id':
            u'ad7ebc56538745a08ef7c5e97f8bd437', 'mgmt_driver': u'openwrt',
            'infra_driver': u'heat', 'attributes': {u'vnfd': u'template_name: '
        u'OpenWRT\r\ndescription: OpenWRT with services\r\n\r\nvdus:\r\n  '
        u'vdu1:\r\n    id: vdu1\r\n    vm_image: cirros-0.3.2-x86_64-uec\r\n  '
        u'  instance_type: m1.tiny\r\n    service_type: firewall\r\n    '
        u'mgmt_driver: openwrt\r\n\r\n    network_interfaces:\r\n      '
        u'management:\r\n        network: net_mgmt\r\n        management: True'
        u'\r\n      pkt_in:\r\n        network: net0\r\n      pkt_out:\r\n    '
        u'    network: net1\r\n\r\n    placement_policy:\r\n      '
        u'availability_zone: nova\r\n\r\n    auto-scaling: noop\r\n\r\n    '
        u'monitoring_policy: noop\r\n    failure_policy: noop\r\n\r\n    '
        u'monitoring_parameter:\r\n      a:\r\n\r\n    config:\r\n      '
        u'param0: key0\r\n      param1: key1\r\n\r\n'}, 'id':
            u'fb048660-dc1b-4f0f-bd89-b023666650ec', 'name':
            u'openwrt_services'}, 'mgmt_url': '{"vdu1": "192.168.120.31"}',
                'service_context': [], 'attributes': {
            u'param_values': u''}, 'id':
            'eb84260e-5ff7-4332-b032-50a14d6c1123', 'description':
            u'OpenWRT with services'}

    def _get_expected_device_update_obj(self):
        return {'status': 'PENDING_CREATE', 'instance_id': None, 'name':
            u'test_openwrt', 'tenant_id':
        u'ad7ebc56538745a08ef7c5e97f8bd437', 'template_id':
        u'eb094833-995e-49f0-a047-dfb56aaf7c4e', 'device_template': {
            'service_types': [{'service_type': u'vnfd', 'id':
            u'4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}], 'description':
            u'OpenWRT with services', 'tenant_id':
            u'ad7ebc56538745a08ef7c5e97f8bd437', 'mgmt_driver': u'openwrt',
            'infra_driver': u'heat', 'attributes': {u'vnfd': u'template_name: '
        u'OpenWRT\r\ndescription: OpenWRT with services\r\n\r\nvdus:\r\n  '
        u'vdu1:\r\n    id: vdu1\r\n    vm_image: cirros-0.3.2-x86_64-uec\r\n  '
        u'  instance_type: m1.tiny\r\n    service_type: firewall\r\n    '
        u'mgmt_driver: openwrt\r\n\r\n    network_interfaces:\r\n      '
        u'management:\r\n        network: net_mgmt\r\n        management: True'
        u'\r\n      pkt_in:\r\n        network: net0\r\n      pkt_out:\r\n    '
        u'    network: net1\r\n\r\n    placement_policy:\r\n      '
        u'availability_zone: nova\r\n\r\n    auto-scaling: noop\r\n\r\n    '
        u'monitoring_policy: noop\r\n    failure_policy: noop\r\n\r\n    '
        u'monitoring_parameter:\r\n      a:\r\n\r\n    config:\r\n      '
        u'param0: key0\r\n      param1: key1\r\n\r\n'}, 'id':
            u'fb048660-dc1b-4f0f-bd89-b023666650ec', 'name':
            u'openwrt_services'}, 'mgmt_url': None, 'service_context': [],
            'attributes': {u'config': 'vdus:\n  vdu1:\n    config: {firewall: '
                                      '"package firewall\\n\\nconfig defaults'
                                      '\\n        option syn_flood\\\n        '
                                      '\\ \'10\'\\n        option input '
                                      '\'REJECT\'\\n        option output '
                                      '\'REJECT\'\\n  \\\n        \\      '
                                      'option forward \'REJECT\'\\n"}\n'},
            'id': 'eb84260e-5ff7-4332-b032-50a14d6c1123', 'description':
                u'OpenWRT with services'}

    def test_create(self):
        device_obj = utils.get_dummy_device_obj()
        expected_result = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        expected_fields = self._get_expected_fields()
        result = self.heat_driver.create(plugin=None, context=self.context,
                                         device=device_obj)
        self.heat_client.create.assert_called_once_with(expected_fields)
        self.assertEqual(expected_result, result)

    def test_create_user_data_param_attr(self):
        device_obj = utils.get_dummy_device_obj_userdata_attr()
        expected_result = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        expected_fields = self._get_expected_fields_user_data()
        result = self.heat_driver.create(plugin=None, context=self.context,
                                         device=device_obj)
        self.heat_client.create.assert_called_once_with(expected_fields)
        self.assertEqual(expected_result, result)

    def test_create_ip_addr_param_attr(self):
        device_obj = utils.get_dummy_device_obj_ipaddr_attr()
        expected_result = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        expected_fields = self._get_expected_fields_ipaddr_data()
        result = self.heat_driver.create(plugin=None, context=self.context,
                                         device=device_obj)
        self.heat_client.create.assert_called_once_with(expected_fields)
        self.assertEqual(expected_result, result)

    def test_create_wait(self):
        device_obj = utils.get_dummy_device_obj()
        expected_result = self._get_expected_device_wait_obj()
        device_id = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        self.heat_driver.create_wait(plugin=None,
                                     context=self.context,
                                     device_dict=device_obj,
                                     device_id=device_id)
        self.assertEqual(device_obj, expected_result)

    def test_delete(self):
        device_id = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        self.heat_driver.delete(plugin=None, context=self.context,
                                device_id=device_id)
        self.heat_client.delete.assert_called_once_with(device_id)

    def test_update(self):
        device_obj = utils.get_dummy_device_obj_config_attr()
        device_config_obj = utils.get_dummy_device_update_config_attr()
        expected_device_update = self._get_expected_device_update_obj()
        device_id = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        self.heat_driver.update(None, self.context,
                                device_id, device_obj,
                                device_config_obj)
        self.assertEqual(device_obj, expected_device_update)
