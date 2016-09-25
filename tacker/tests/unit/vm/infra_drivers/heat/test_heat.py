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
import json
import mock
import os
import yaml

from tacker import context
from tacker.extensions import vnfm
from tacker.tests.unit import base
from tacker.tests.unit.db import utils
from tacker.vnfm.infra_drivers.heat import heat


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
        os.path.dirname(os.path.abspath(__file__)), "../openstack/data/", name)
    f = codecs.open(filename, encoding='utf-8', errors='strict')
    return f.read()


class TestDeviceHeat(base.TestCase):
    hot_template = _get_template('hot_openwrt.yaml')
    hot_param_template = _get_template('hot_openwrt_params.yaml')
    hot_ipparam_template = _get_template('hot_openwrt_ipparams.yaml')
    tosca_vnfd_openwrt = _get_template('test_tosca_openwrt.yaml')
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
            'tacker.vnfm.infra_drivers.openstack.openstack.HeatClient',
            fake_heat_client)

    def _mock(self, target, new=mock.DEFAULT):
        patcher = mock.patch(target, new)
        return patcher.start()

    def _get_vnfd(self, template):
        return {'vnfd': {'attributes': {'vnfd': template}}}

    def _get_expected_vnfd(self, template):
        return {'attributes': {'vnfd': template},
                'description': 'OpenWRT with services',
                'mgmt_driver': 'openwrt', 'name': 'OpenWRT',
                'service_types': [{'service_type': 'vnfd',
                'id': '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}],
                'tenant_id': 'ad7ebc56538745a08ef7c5e97f8bd437',
                'id': 'fb048660-dc1b-4f0f-bd89-b023666650ec'}

    def _get_expected_fields(self):
        return {'stack_name':
                'tacker.vnfm.infra_drivers.openstack.openstack_DeviceHeat'
                '-eb84260e-5ff7-4332-b032-50a14d6c1123',
                'template': self.hot_template}

    def _get_expected_fields_user_data(self):
        return {'stack_name':
                'tacker.vnfm.infra_drivers.openstack.openstack_DeviceHeat'
                '-18685f68-2b2a-4185-8566-74f54e548811',
                'template': self.hot_param_template}

    def _get_expected_fields_ipaddr_data(self):
        return {'stack_name':
                'tacker.vnfm.infra_drivers.openstack.openstack_DeviceHeat'
                '-d1337add-d5a1-4fd4-9447-bb9243c8460b',
                'template': self.hot_ipparam_template}

    def _get_expected_vnf_wait_obj(self, param_values=''):
        return {'status': 'PENDING_CREATE',
                'instance_id': None,
                'name': u'test_openwrt',
                'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                'vnfd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
                'vnfd': {
                    'service_types': [{
                        'service_type': u'vnfd',
                        'id': u'4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}],
                    'description': u'OpenWRT with services',
                    'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                    'mgmt_driver': u'openwrt',
                    'attributes': {u'vnfd': self.tosca_vnfd_openwrt},
                    'id': u'fb048660-dc1b-4f0f-bd89-b023666650ec',
                    'name': u'OpenWRT'},
                'mgmt_url': '{"vdu1": "192.168.120.31"}',
                'service_context': [],
                'attributes': {u'param_values': param_values},
                'id': 'eb84260e-5ff7-4332-b032-50a14d6c1123',
                'description': u'OpenWRT with services'}

    def _get_expected_vnf_update_obj(self):
        return {'status': 'PENDING_CREATE', 'instance_id': None, 'name':
            u'test_openwrt', 'tenant_id':
        u'ad7ebc56538745a08ef7c5e97f8bd437', 'vnfd_id':
        u'eb094833-995e-49f0-a047-dfb56aaf7c4e', 'vnfd': {
            'service_types': [{'service_type': u'vnfd', 'id':
            u'4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}], 'description':
            u'OpenWRT with services', 'tenant_id':
            u'ad7ebc56538745a08ef7c5e97f8bd437', 'mgmt_driver': u'openwrt',
            'attributes': {u'vnfd': self.tosca_vnfd_openwrt},
            'id': u'fb048660-dc1b-4f0f-bd89-b023666650ec', 'name':
            u'openwrt_services'}, 'mgmt_url': None, 'service_context': [],
            'attributes': {'config': utils.update_config_data},
            'id': 'eb84260e-5ff7-4332-b032-50a14d6c1123', 'description':
                u'OpenWRT with services'}

    def _get_expected_active_vnf(self):
        return {'status': 'ACTIVE',
                'instance_id': None,
                'name': u'test_openwrt',
                'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                'vnfd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
                'vnfd': {
                    'service_types': [{
                        'service_type': u'vnfd',
                        'id': u'4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}],
                    'description': u'OpenWRT with services',
                    'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                    'mgmt_driver': u'openwrt',
                    'infra_driver': u'heat',
                    'attributes': {u'vnfd': self.tosca_vnfd_openwrt},
                    'id': u'fb048660-dc1b-4f0f-bd89-b023666650ec',
                    'name': u'openwrt_services'},
                'mgmt_url': '{"vdu1": "192.168.120.31"}',
                'service_context': [],
                'id': 'eb84260e-5ff7-4332-b032-50a14d6c1123',
                'description': u'OpenWRT with services'}

    def _assert_create_result_old_template(self, expected_fields,
                                           actual_fields, expected_result,
                                           result):
        actual_fields["template"] = yaml.safe_load(actual_fields["template"])
        expected_fields["template"] = \
            yaml.safe_load(expected_fields["template"])
        self.assertEqual(expected_fields, actual_fields)
        self.heat_client.create.assert_called_once_with(expected_fields)
        self.assertEqual(expected_result, result)

    def test_create(self):
        vnf_obj = utils.get_dummy_device_obj()
        expected_result = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        expected_fields = self._get_expected_fields()
        result = self.heat_driver.create(plugin=None, context=self.context,
                                         vnf=vnf_obj,
                                         auth_attr=utils.get_vim_auth_obj())
        actual_fields = self.heat_client.create.call_args[0][0]
        self._assert_create_result_old_template(expected_fields, actual_fields,
                                   expected_result, result)

    def test_create_user_data_param_attr(self):
        vnf_obj = utils.get_dummy_device_obj_userdata_attr()
        expected_result = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        expected_fields = self._get_expected_fields_user_data()
        result = self.heat_driver.create(plugin=None, context=self.context,
                                         vnf=vnf_obj,
                                         auth_attr=utils.get_vim_auth_obj())
        actual_fields = self.heat_client.create.call_args[0][0]
        self._assert_create_result_old_template(expected_fields, actual_fields,
                                   expected_result, result)

    def test_create_ip_addr_param_attr(self):
        vnf_obj = utils.get_dummy_device_obj_ipaddr_attr()
        expected_result = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        expected_fields = self._get_expected_fields_ipaddr_data()
        result = self.heat_driver.create(plugin=None, context=self.context,
                                         vnf=vnf_obj,
                                         auth_attr=utils.get_vim_auth_obj())
        actual_fields = self.heat_client.create.call_args[0][0]
        self._assert_create_result_old_template(expected_fields, actual_fields,
                                   expected_result, result)

    def test_create_wait(self):
        vnf_obj = self._get_dummy_tosca_vnf('test_tosca_openwrt.yaml')
        expected_result = self._get_expected_vnf_wait_obj()
        vnf_id = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        self.heat_driver.create_wait(plugin=None,
                                     context=self.context,
                                     vnf_dict=vnf_obj,
                                     vnf_id=vnf_id,
                                     auth_attr=utils.get_vim_auth_obj())
        self.assertEqual(expected_result, vnf_obj)

    def test_delete(self):
        vnf_id = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        self.heat_driver.delete(plugin=None, context=self.context,
                                vnf_id=vnf_id,
                                auth_attr=utils.get_vim_auth_obj())
        self.heat_client.delete.assert_called_once_with(vnf_id)

    def test_update(self):
        vnf_obj = utils.get_dummy_vnf_config_attr()
        vnf_config_obj = utils.get_dummy_vnf_update_config()
        expected_vnf_update = self._get_expected_vnf_update_obj()
        vnf_id = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        self.heat_driver.update(plugin=None, context=self.context,
                                vnf_id=vnf_id, vnf_dict=vnf_obj,
                                vnf=vnf_config_obj,
                                auth_attr=utils.get_vim_auth_obj())
        expected_vnf_update['attributes']['config'] = yaml.load(
            expected_vnf_update['attributes']['config'])
        vnf_obj['attributes']['config'] = yaml.load(vnf_obj['attributes'][
            'config'])
        self.assertEqual(expected_vnf_update, vnf_obj)

    def _get_expected_fields_tosca(self, template):
        return {'stack_name':
                'tacker.vnfm.infra_drivers.openstack.openstack_DeviceHeat'
                '-eb84260e'
                '-5ff7-4332-b032-50a14d6c1123',
                'template': _get_template(template)}

    def _get_expected_tosca_vnf(self,
                                tosca_tpl_name,
                                hot_tpl_name,
                                param_values='',
                                is_monitor=True,
                                is_alarm=False):
        tosca_tpl = _get_template(tosca_tpl_name)
        exp_tmpl = self._get_expected_vnfd(tosca_tpl)
        tosca_hw_dict = yaml.safe_load(_get_template(hot_tpl_name))
        dvc = {
            'vnfd': exp_tmpl,
            'description': u'OpenWRT with services',
            'attributes': {
                'heat_template': tosca_hw_dict,
                'param_values': param_values
            },
            'id': 'eb84260e-5ff7-4332-b032-50a14d6c1123',
            'instance_id': None,
            'mgmt_url': None,
            'name': u'test_openwrt',
            'service_context': [],
            'status': 'PENDING_CREATE',
            'vnfd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
            'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437'
        }
        # Add montitoring attributes for those yaml, which are having it
        if is_monitor:
            dvc['attributes'].update(
                {'monitoring_policy': '{"vdus": {"VDU1": {"ping": {"name": '
                                      '"ping", "actions": {"failure": '
                                      '"respawn"}, "parameters": {"count": 3, '
                                      '"interval": 10}, "monitoring_params": '
                                      '{"count": 3, "interval": 10}}}}}'})
        if is_alarm:
            dvc['attributes'].update({'alarm_url': ''})
        return dvc

    def _get_dummy_tosca_vnf(self, template, input_params='', is_alarm=False):

        tosca_template = _get_template(template)
        vnf = utils.get_dummy_device_obj()
        dtemplate = self._get_expected_vnfd(tosca_template)

        vnf['vnfd'] = dtemplate
        vnf['attributes'] = {}
        vnf['attributes']['param_values'] = input_params
        if is_alarm:
            vnf['attributes']['alarm_url'] = ''
        return vnf

    def _test_assert_equal_for_tosca_templates(self, tosca_tpl_name,
                                               hot_tpl_name,
                                               input_params='',
                                               files=None,
                                               is_monitor=True,
                                               is_alarm=False):
        vnf = self._get_dummy_tosca_vnf(tosca_tpl_name, input_params, is_alarm)
        expected_result = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        expected_fields = self._get_expected_fields_tosca(hot_tpl_name)
        expected_vnf = self._get_expected_tosca_vnf(tosca_tpl_name,
                                                    hot_tpl_name,
                                                    input_params,
                                                    is_monitor,
                                                    is_alarm)
        result = self.heat_driver.create(plugin=None, context=self.context,
                                         vnf=vnf,
                                         auth_attr=utils.get_vim_auth_obj())
        actual_fields = self.heat_client.create.call_args[0][0]
        actual_fields["template"] = yaml.safe_load(actual_fields["template"])
        expected_fields["template"] = \
            yaml.safe_load(expected_fields["template"])

        if files:
            for k, v in actual_fields["files"].items():
                actual_fields["files"][k] = yaml.safe_load(v)

            expected_fields["files"] = {}
            for k, v in files.items():
                expected_fields["files"][k] = yaml.safe_load(_get_template(v))

        self.assertEqual(expected_fields, actual_fields)
        vnf["attributes"]["heat_template"] = yaml.safe_load(
            vnf["attributes"]["heat_template"])
        self.heat_client.create.assert_called_once_with(expected_fields)
        self.assertEqual(expected_result, result)

        if files:
            expected_fields["files"] = {}
            for k, v in files.items():
                expected_vnf["attributes"][k] = yaml.safe_load(
                    _get_template(v))
                vnf["attributes"][k] = yaml.safe_load(
                    vnf["attributes"][k])
            expected_vnf["attributes"]['scaling_group_names'] = {
                'SP1': 'G1'}
            vnf["attributes"]['scaling_group_names'] = json.loads(
                vnf["attributes"]['scaling_group_names']
            )
        self.assertEqual(expected_vnf, vnf)

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

    def test_create_tosca_sriov(self):
        self._test_assert_equal_for_tosca_templates(
            'tosca_sriov.yaml',
            'hot_tosca_sriov.yaml'
        )

    def test_create_tosca_vnic_normal(self):
        self._test_assert_equal_for_tosca_templates(
            'tosca_vnic_port.yaml',
            'hot_tosca_vnic_normal.yaml'
        )

    def test_create_tosca_mgmt_sriov_port(self):
        self._test_assert_equal_for_tosca_templates(
            'tosca_mgmt_sriov.yaml',
            'hot_tosca_mgmt_sriov.yaml'
        )

    def test_tosca_params(self):
        input_params = 'image: cirros\nflavor: m1.large'
        self._test_assert_equal_for_tosca_templates(
            'tosca_generic_vnfd_params.yaml',
            'hot_tosca_generic_vnfd_params.yaml',
            input_params
        )

    def test_create_tosca_scale(self):
        self._test_assert_equal_for_tosca_templates(
            'tosca_scale.yaml',
            'hot_scale_main.yaml',
            files={'scaling.yaml': 'hot_scale_custom.yaml'},
            is_monitor=False
        )

    def test_get_resource_info(self):
        vnf_obj = self._get_expected_active_vnf()
        self.assertRaises(vnfm.InfraDriverUnreachable,
                          self.heat_driver.get_resource_info,
                          plugin=None, context=self.context, vnf_info=vnf_obj,
                          auth_attr=utils.get_vim_auth_obj(),
                          region_name=None)

    def test_create_port_with_security_groups(self):
        self._test_assert_equal_for_tosca_templates(
            'test_tosca_security_groups.yaml',
            'hot_tosca_security_groups.yaml'
        )

    def test_create_tosca_with_alarm_monitoring(self):
        self._test_assert_equal_for_tosca_templates(
            'tosca_alarm.yaml',
            'hot_tosca_alarm.yaml',
            is_monitor=False,
            is_alarm=True
        )
