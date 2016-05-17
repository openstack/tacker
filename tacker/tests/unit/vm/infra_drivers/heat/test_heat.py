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

import codecs
import mock
import os
import yaml

from tacker import context
from tacker.tests.unit import base
from tacker.tests.unit.db import utils
from tacker.vm.infra_drivers.heat import heat


class FakeHeatClient(mock.Mock):

    class Stack(mock.Mock):
        stack_status = 'CREATE_COMPLETE'
        outputs = [{u'output_value': u'192.168.120.31', u'description':
            u'management ip address', u'output_key': u'mgmt_ip-vdu1'}]

    def create(self, *args, **kwargs):
        return {'stack': {'id': '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}}

    def get(self, id):
        return self.Stack()


def _get_template(name):
    filename = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data/", name)
    f = codecs.open(filename, encoding='utf-8', errors='strict')
    return f.read()


class TestDeviceHeat(base.TestCase):
    hot_template = _get_template('hot_openwrt.yaml')
    hot_param_template = _get_template('hot_openwrt_params.yaml')
    hot_ipparam_template = _get_template('hot_openwrt_ipparams.yaml')
    vnfd_openwrt = _get_template('openwrt.yaml')
    config_data = _get_template('config_data.yaml')

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
            'tacker.vm.infra_drivers.heat.heat.HeatClient', fake_heat_client)

    def _mock(self, target, new=mock.DEFAULT):
        patcher = mock.patch(target, new)
        return patcher.start()

    def _get_device_template(self, template):
        return {'device_template': {'attributes': {'vnfd': template}}}

    def _get_expected_device_template(self, template):
        return {'device_template': {'attributes': {'vnfd': template},
                                    'description': 'OpenWRT with services',
                                    'mgmt_driver': 'openwrt',
                                    'name': 'OpenWRT'}}

    def _get_expected_fields(self):
        return {'stack_name':
                'tacker.vm.infra_drivers.heat.heat_DeviceHeat-eb84260e'
                '-5ff7-4332-b032-50a14d6c1123', 'template': self.hot_template}

    def _get_expected_fields_user_data(self):
        return {'stack_name':
                'tacker.vm.infra_drivers.heat.heat_DeviceHeat-18685f68'
                '-2b2a-4185-8566-74f54e548811',
                'template': self.hot_param_template}

    def _get_expected_fields_ipaddr_data(self):
        return {'stack_name':
                'tacker.vm.infra_drivers.heat.heat_DeviceHeat-d1337add'
                '-d5a1-4fd4-9447-bb9243c8460b',
                'template': self.hot_ipparam_template}

    def _get_expected_device_wait_obj(self):
        return {'status': 'PENDING_CREATE', 'instance_id': None, 'name':
            u'test_openwrt', 'tenant_id':
        u'ad7ebc56538745a08ef7c5e97f8bd437', 'template_id':
        u'eb094833-995e-49f0-a047-dfb56aaf7c4e', 'device_template': {
            'service_types': [{'service_type': u'vnfd', 'id':
            u'4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}], 'description':
            u'OpenWRT with services', 'tenant_id':
            u'ad7ebc56538745a08ef7c5e97f8bd437', 'mgmt_driver': u'openwrt',
            'infra_driver': u'heat',
            'attributes': {u'vnfd': self.vnfd_openwrt},
            'id': u'fb048660-dc1b-4f0f-bd89-b023666650ec', 'name':
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
            'infra_driver': u'heat',
            'attributes': {u'vnfd': self.vnfd_openwrt},
            'id': u'fb048660-dc1b-4f0f-bd89-b023666650ec', 'name':
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
                                         device=device_obj,
                                         auth_attr=utils.get_vim_auth_obj())
        self.heat_client.create.assert_called_once_with(expected_fields)
        self.assertEqual(expected_result, result)

    def test_create_user_data_param_attr(self):
        device_obj = utils.get_dummy_device_obj_userdata_attr()
        expected_result = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        expected_fields = self._get_expected_fields_user_data()
        result = self.heat_driver.create(plugin=None, context=self.context,
                                         device=device_obj,
                                         auth_attr=utils.get_vim_auth_obj())
        self.heat_client.create.assert_called_once_with(expected_fields)
        self.assertEqual(expected_result, result)

    def test_create_ip_addr_param_attr(self):
        device_obj = utils.get_dummy_device_obj_ipaddr_attr()
        expected_result = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        expected_fields = self._get_expected_fields_ipaddr_data()
        result = self.heat_driver.create(plugin=None, context=self.context,
                                         device=device_obj,
                                         auth_attr=utils.get_vim_auth_obj())
        self.heat_client.create.assert_called_once_with(expected_fields)
        self.assertEqual(expected_result, result)

    def test_create_wait(self):
        device_obj = utils.get_dummy_device_obj()
        expected_result = self._get_expected_device_wait_obj()
        device_id = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        self.heat_driver.create_wait(plugin=None,
                                     context=self.context,
                                     device_dict=device_obj,
                                     device_id=device_id,
                                     auth_attr=utils.get_vim_auth_obj())
        self.assertEqual(device_obj, expected_result)

    def test_delete(self):
        device_id = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        self.heat_driver.delete(plugin=None, context=self.context,
                                device_id=device_id,
                                auth_attr=utils.get_vim_auth_obj())
        self.heat_client.delete.assert_called_once_with(device_id)

    def test_update(self):
        device_obj = utils.get_dummy_device_obj_config_attr()
        device_config_obj = utils.get_dummy_device_update_config_attr()
        expected_device_update = self._get_expected_device_update_obj()
        device_id = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        self.heat_driver.update(plugin=None, context=self.context,
                                device_id=device_id, device_dict=device_obj,
                                device=device_config_obj,
                                auth_attr=utils.get_vim_auth_obj())
        self.assertEqual(device_obj, expected_device_update)

    def test_create_device_template_pre_tosca(self):
        tosca_tpl = _get_template('test_tosca_openwrt.yaml')
        dtemplate = self._get_device_template(tosca_tpl)
        exp_tmpl = self._get_expected_device_template(tosca_tpl)
        self.heat_driver.create_device_template_pre(None, None, dtemplate)
        self.assertEqual(dtemplate, exp_tmpl)

    def _get_expected_fields_tosca(self, template):
        return {'stack_name':
                'tacker.vm.infra_drivers.heat.heat_DeviceHeat-eb84260e'
                '-5ff7-4332-b032-50a14d6c1123',
                'template': _get_template(template)}

    def _get_expected_tosca_device(self, tosca_tpl_name, hot_tpl_name):
        tosca_tpl = _get_template(tosca_tpl_name)
        exp_tmpl = self._get_expected_device_template(tosca_tpl)
        tosca_hw_dict = yaml.safe_load(_get_template(hot_tpl_name))
        return {'device_template': exp_tmpl['device_template'],
                'description': u'OpenWRT with services',
                'attributes': {'heat_template': tosca_hw_dict,
                               'monitoring_policy': '{"vdus": {"VDU1":'
                               ' {"ping": {"name": "ping",'
                               ' "actions": {"failure": "respawn"},'
                               ' "parameters": {"count": 3, "interval": 10'
                               '}, "monitoring_params": {"count": 3, '
                               '"interval": 10}}}}}',
                               'param_values': ''},
                'id': 'eb84260e-5ff7-4332-b032-50a14d6c1123',
                'instance_id': None, 'mgmt_url': None, 'name': u'test_openwrt',
                'service_context': [], 'status': 'PENDING_CREATE',
                'template_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
                'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437'}

    def _get_dummy_tosca_device(self, template):
        tosca_template = _get_template(template)
        device = utils.get_dummy_device_obj()
        dtemplate = self._get_expected_device_template(tosca_template)
        dtemplate['service_types'] = [{'service_type': 'vnfd', 'id':
            '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}]
        dtemplate['tenant_id'] = 'ad7ebc56538745a08ef7c5e97f8bd437'
        device['device_template'] = dtemplate['device_template']
        return device

    def _test_assert_equal_for_tosca_templates(self, tosca_tpl_name,
                                               hot_tpl_name):
        device = self._get_dummy_tosca_device(tosca_tpl_name)
        expected_result = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        expected_fields = self._get_expected_fields_tosca(hot_tpl_name)
        expected_device = self._get_expected_tosca_device(tosca_tpl_name,
                                                          hot_tpl_name)
        result = self.heat_driver.create(plugin=None, context=self.context,
                                         device=device,
                                         auth_attr=utils.get_vim_auth_obj())
        actual_fields = self.heat_client.create.call_args[0][0]
        actual_fields["template"] = yaml.safe_load(actual_fields["template"])
        expected_fields["template"] = \
            yaml.safe_load(expected_fields["template"])
        self.assertEqual(actual_fields, expected_fields)
        device["attributes"]["heat_template"] = yaml.safe_load(
            device["attributes"]["heat_template"])
        self.heat_client.create.assert_called_once_with(expected_fields)
        self.assertEqual(expected_result, result)
        self.assertEqual(device, expected_device)

    def test_create_tosca(self):
        # self.skipTest("Not ready yet")
        self._test_assert_equal_for_tosca_templates('test_tosca_openwrt.yaml',
            'hot_tosca_openwrt.yaml')

    def test_create_tosca_with_userdata(self):
        self._test_assert_equal_for_tosca_templates(
            'test_tosca_openwrt_userdata.yaml',
            'hot_tosca_openwrt_userdata.yaml')

    def test_create_tosca_with_new_flavor(self):
        self._test_assert_equal_for_tosca_templates('test_tosca_flavor.yaml',
            'hot_flavor.yaml')

    def test_create_tosca_with_new_flavor_with_defaults(self):
        self._test_assert_equal_for_tosca_templates(
            'test_tosca_flavor_defaults.yaml',
            'hot_flavor_defaults.yaml')

    def test_create_tosca_with_flavor_and_capabilities(self):
        self._test_assert_equal_for_tosca_templates(
            'test_tosca_flavor_and_capabilities.yaml',
            'hot_flavor_and_capabilities.yaml')

    def test_create_tosca_with_flavor_no_units(self):
        self._test_assert_equal_for_tosca_templates(
            'test_tosca_flavor_no_units.yaml',
            'hot_flavor_no_units.yaml')

    def test_create_tosca_with_flavor_extra_specs_all_numa_count(self):
        self._test_assert_equal_for_tosca_templates(
            'tosca_flavor_all_numa_count.yaml',
            'hot_tosca_flavor_all_numa_count.yaml')

    def test_create_tosca_with_flavor_extra_specs_all_numa_nodes(self):
        self._test_assert_equal_for_tosca_templates(
            'tosca_flavor_all_numa_nodes.yaml',
            'hot_tosca_flavor_all_numa_nodes.yaml')

    def test_create_tosca_with_flavor_extra_specs_numa_node_count_trumps(self):
        self._test_assert_equal_for_tosca_templates(
            'tosca_flavor_numa_nodes_count.yaml',
            'hot_tosca_flavor_numa_nodes_count.yaml')

    def test_create_tosca_with_flavor_extra_specs_huge_pages(self):
        self._test_assert_equal_for_tosca_templates(
            'tosca_flavor_huge_pages.yaml',
            'hot_tosca_flavor_huge_pages.yaml')

    def test_create_tosca_with_flavor_extra_specs_cpu_allocations(self):
        self._test_assert_equal_for_tosca_templates(
            'tosca_flavor_cpu_allocations.yaml',
            'hot_tosca_flavor_cpu_allocations.yaml')

    def test_create_tosca_with_flavor_extra_specs_numa_nodes(self):
        self._test_assert_equal_for_tosca_templates(
            'tosca_flavor_numa_nodes.yaml',
            'hot_tosca_flavor_numa_nodes.yaml')

    def test_create_tosca_with_new_image(self):
        self._test_assert_equal_for_tosca_templates('test_tosca_image.yaml',
            'hot_tosca_image.yaml')
