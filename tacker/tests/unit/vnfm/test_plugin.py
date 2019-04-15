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

from datetime import datetime

import mock
from mock import patch
from oslo_utils import uuidutils
import yaml

from tacker import context
from tacker.db.common_services import common_services_db_plugin
from tacker.db.nfvo import nfvo_db
from tacker.db.vnfm import vnfm_db
from tacker.extensions import vnfm
from tacker.plugins.common import constants
from tacker.tests.unit.db import base as db_base
from tacker.tests.unit.db import utils
from tacker.vnfm import monitor
from tacker.vnfm import plugin


class FakeDriverManager(mock.Mock):
    def invoke(self, *args, **kwargs):
        if 'create' in args:
            return uuidutils.generate_uuid()

        if 'get_resource_info' in args:
            return {'resources': {'name': 'dummy_vnf',
                                  'type': 'dummy',
                                  'id': uuidutils.generate_uuid()}}


class FakeVNFMonitor(mock.Mock):
    pass


class FakeGreenPool(mock.Mock):
    pass


class FakeVimClient(mock.Mock):
    pass


class TestVNFMPluginMonitor(db_base.SqlTestCase):
    def setUp(self):
        super(TestVNFMPluginMonitor, self).setUp()
        self._mock_vnf_manager()

    def _mock_vnf_manager(self):
        self._vnf_manager = mock.Mock(wraps=FakeDriverManager())
        self._vnf_manager.__contains__ = mock.Mock(
            return_value=True)
        fake_vnf_manager = mock.Mock()
        fake_vnf_manager.return_value = self._vnf_manager
        self._mock(
            'tacker.common.driver_manager.DriverManager', fake_vnf_manager)

    @mock.patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.get_vnfs')
    @mock.patch('tacker.vnfm.monitor.VNFMonitor.__run__')
    def test_init_monitoring(self, mock_run, mock_get_vnfs):
        vnf_id = uuidutils.generate_uuid()
        vnfs = [{
            'id': vnf_id,
            'vnf': {
                'id': vnf_id,
                'status': 'ACTIVE',
                'name': 'fake_vnf',
                'attributes': {
                    'monitoring_policy':
                        '{"vdus": '
                        '{"VDU1": {"ping": {"actions": {"failure": "respawn"},'
                        '"name": "ping", "parameters": {"count": 3,'
                        '"interval": 1, "monitoring_delay": 45, "timeout": 2},'
                        '"monitoring_params": {"count": 3, "interval": 1,'
                        '"monitoring_delay": 45, "timeout": 2}}}}}'}
            },
            'name': 'fake_vnf',
            'tenant_id': 'ad7ebc56538745a08ef7c5e97f8bd437',
            'description': 'fake_vnf_description',
            'instance_id': 'da85ea1a-4ec4-4201-bbb2-8d9249eca7ec',
            'vnfd_id': 'eb094833-995e-49f0-a047-dfb56aaf7c4e',
            'vim_id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            'placement_attr': {'region': 'RegionOne'},
            'status': 'ACTIVE',
            'attributes': {
                    'monitoring_policy':
                        '{"vdus": '
                        '{"VDU1": {"ping": {"actions": {"failure": "respawn"},'
                        '"name": "ping", "parameters": {"count": 3,'
                        '"interval": 1, "monitoring_delay": 45, "timeout": 2},'
                        '"monitoring_params": {"count": 3, "interval": 1,'
                        '"monitoring_delay": 45, "timeout": 2}}}}}'},
            'mgmt_url': '{"VDU1": "a.b.c.d"}',
            'deleted_at': datetime.min,
            'management_ip_addresses': 'a.b.c.d'
        }]

        mock_get_vnfs.return_value = vnfs
        # NOTE(bhagyashris): VNFMonitor class is using a singleton pattern
        # and '_hosting_vnfs' is defined as a class level attribute.
        # If one of the unit test adds a VNF to monitor it will show up here
        # provided both the unit tests runs in the same process.
        # Hence, you must reinitialize '_hosting_vnfs' to empty dict.
        monitor.VNFMonitor._hosting_vnfs = dict()
        vnfm_plugin = plugin.VNFMPlugin()
        hosting_vnfs = vnfm_plugin._vnf_monitor._hosting_vnfs.values()
        hosting_vnfs_list = list(hosting_vnfs)
        hosting_vnf = hosting_vnfs_list[0]['vnf']
        self.assertEqual('{"VDU1": "a.b.c.d"}', hosting_vnf['mgmt_url'])
        self.assertEqual(1, len(hosting_vnfs_list))


class TestVNFMPlugin(db_base.SqlTestCase):
    def setUp(self):
        super(TestVNFMPlugin, self).setUp()
        self.addCleanup(mock.patch.stopall)
        self.context = context.get_admin_context()
        self._mock_vim_client()
        self._stub_get_vim()
        self._mock_device_manager()
        self._mock_vnf_monitor()
        self._mock_vnf_alarm_monitor()
        self._mock_green_pool()
        self._insert_dummy_vim()
        self.vnfm_plugin = plugin.VNFMPlugin()
        mock.patch('tacker.db.common_services.common_services_db_plugin.'
                   'CommonServicesPluginDb.create_event'
                   ).start()
        self._cos_db_plugin =\
            common_services_db_plugin.CommonServicesPluginDb()

    def _mock_device_manager(self):
        self._device_manager = mock.Mock(wraps=FakeDriverManager())
        self._device_manager.__contains__ = mock.Mock(
            return_value=True)
        fake_device_manager = mock.Mock()
        fake_device_manager.return_value = self._device_manager
        self._mock(
            'tacker.common.driver_manager.DriverManager', fake_device_manager)

    def _mock_vim_client(self):
        self.vim_client = mock.Mock(wraps=FakeVimClient())
        fake_vim_client = mock.Mock()
        fake_vim_client.return_value = self.vim_client
        self._mock(
            'tacker.vnfm.vim_client.VimClient', fake_vim_client)

    def _stub_get_vim(self):
        vim_obj = {'vim_id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                   'vim_name': 'fake_vim', 'vim_auth':
                   {'auth_url': 'http://localhost:5000', 'password':
                       'test_pw', 'username': 'test_user', 'project_name':
                       'test_project'}, 'vim_type': 'test_vim'}
        self.vim_client.get_vim.return_value = vim_obj

    def _mock_green_pool(self):
        self._pool = mock.Mock(wraps=FakeGreenPool())
        fake_green_pool = mock.Mock()
        fake_green_pool.return_value = self._pool
        self._mock(
            'eventlet.GreenPool', fake_green_pool)

    def _mock_vnf_monitor(self):
        self._vnf_monitor = mock.Mock(wraps=FakeVNFMonitor())
        fake_vnf_monitor = mock.Mock()
        fake_vnf_monitor.return_value = self._vnf_monitor
        self._mock(
            'tacker.vnfm.monitor.VNFMonitor', fake_vnf_monitor)

    def _mock_vnf_alarm_monitor(self):
        self._vnf_alarm_monitor = mock.Mock(wraps=FakeVNFMonitor())
        fake_vnf_alarm_monitor = mock.Mock()
        fake_vnf_alarm_monitor.return_value = self._vnf_alarm_monitor
        self._mock(
            'tacker.vnfm.monitor.VNFAlarmMonitor', fake_vnf_alarm_monitor)

    def _insert_dummy_device_template(self):
        session = self.context.session
        device_template = vnfm_db.VNFD(
            id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_template',
            description='fake_template_description',
            template_source='onboarded',
            deleted_at=datetime.min)
        session.add(device_template)
        session.flush()
        return device_template

    def _insert_dummy_device_template_inline(self):
        session = self.context.session
        device_template = vnfm_db.VNFD(
            id='d58bcc4e-d0cf-11e6-bf26-cec0c932ce01',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='tmpl-koeak4tqgoqo8cr4-dummy_inline_vnf',
            description='inline_fake_template_description',
            deleted_at=datetime.min,
            template_source='inline')
        session.add(device_template)
        session.flush()
        return device_template

    def _insert_dummy_vnfd_attributes(self, template):
        session = self.context.session
        vnfd_attr = vnfm_db.VNFDAttribute(
            id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            vnfd_id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            key='vnfd',
            value=template)
        session.add(vnfd_attr)
        session.flush()
        return vnfd_attr

    def _insert_dummy_device(self):
        session = self.context.session
        device_db = vnfm_db.VNF(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778fe',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_device',
            description='fake_device_description',
            instance_id='da85ea1a-4ec4-4201-bbb2-8d9249eca7ec',
            vnfd_id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            placement_attr={'region': 'RegionOne'},
            status='ACTIVE',
            deleted_at=datetime.min)
        session.add(device_db)
        session.flush()
        return device_db

    def _insert_scaling_attributes_vnf(self):
        session = self.context.session
        vnf_attributes = vnfm_db.VNFAttribute(
            id='7800cb81-7ed1-4cf6-8387-746468522651',
            vnf_id='6261579e-d6f3-49ad-8bc3-a9cb974778fe',
            key='scaling_group_names',
            value='{"SP1": "G1"}'
        )
        session.add(vnf_attributes)
        session.flush()
        return vnf_attributes

    def _insert_scaling_attributes_vnfd(self):
        session = self.context.session
        vnfd_attributes = vnfm_db.VNFDAttribute(
            id='7800cb81-7ed1-4cf6-8387-746468522650',
            vnfd_id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            key='vnfd',
            value=utils.vnfd_scale_tosca_template
        )
        session.add(vnfd_attributes)
        session.flush()
        return vnfd_attributes

    def _insert_dummy_vim(self):
        session = self.context.session
        vim_db = nfvo_db.Vim(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_vim',
            description='fake_vim_description',
            type='test_vim',
            status='Active',
            deleted_at=datetime.min,
            placement_attr={'regions': ['RegionOne']})
        vim_auth_db = nfvo_db.VimAuth(
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            password='encrypted_pw',
            auth_url='http://localhost:5000',
            vim_project={'name': 'test_project'},
            auth_cred={'username': 'test_user', 'user_domain_id': 'default',
                       'project_domain_id': 'default'})
        session.add(vim_db)
        session.add(vim_auth_db)
        session.flush()

    @mock.patch('tacker.vnfm.plugin.toscautils.updateimports')
    @mock.patch('tacker.vnfm.plugin.ToscaTemplate')
    @mock.patch('tacker.vnfm.plugin.toscautils.get_mgmt_driver')
    def test_create_vnfd(self, mock_get_mgmt_driver, mock_tosca_template,
                        mock_update_imports):
        mock_get_mgmt_driver.return_value = 'dummy_mgmt_driver'
        mock_tosca_template.return_value = mock.ANY

        vnfd_obj = utils.get_dummy_vnfd_obj()
        result = self.vnfm_plugin.create_vnfd(self.context, vnfd_obj)
        self.assertIsNotNone(result)
        self.assertIn('id', result)
        self.assertEqual('dummy_vnfd', result['name'])
        self.assertEqual('dummy_vnfd_description', result['description'])
        self.assertEqual('dummy_mgmt_driver', result['mgmt_driver'])
        self.assertIn('service_types', result)
        self.assertIn('attributes', result)
        self.assertIn('created_at', result)
        self.assertIn('updated_at', result)
        self.assertIn('template_source', result)
        yaml_dict = yaml.safe_load(utils.tosca_vnfd_openwrt)
        mock_tosca_template.assert_called_once_with(
            a_file=False, yaml_dict_tpl=yaml_dict)
        mock_get_mgmt_driver.assert_called_once_with(mock.ANY)
        mock_update_imports.assert_called_once_with(yaml_dict)
        self._cos_db_plugin.create_event.assert_called_once_with(
            self.context, evt_type=constants.RES_EVT_CREATE, res_id=mock.ANY,
            res_state=constants.RES_EVT_ONBOARDED,
            res_type=constants.RES_TYPE_VNFD, tstamp=mock.ANY)

    def test_create_vnfd_no_service_types(self):
        vnfd_obj = utils.get_dummy_vnfd_obj()
        vnfd_obj['vnfd'].pop('service_types')
        self.assertRaises(vnfm.ServiceTypesNotSpecified,
                          self.vnfm_plugin.create_vnfd,
                          self.context, vnfd_obj)

    def test_create_vnf_with_vnfd(self):
        self._insert_dummy_device_template()
        vnf_obj = utils.get_dummy_vnf_obj()
        result = self.vnfm_plugin.create_vnf(self.context, vnf_obj)
        self.assertIsNotNone(result)
        self.assertIn('id', result)
        self.assertIn('instance_id', result)
        self.assertIn('status', result)
        self.assertIn('attributes', result)
        self.assertIn('mgmt_url', result)
        self.assertIn('created_at', result)
        self.assertIn('updated_at', result)
        self._device_manager.invoke.assert_called_with('test_vim',
                                                       'create',
                                                       plugin=mock.ANY,
                                                       context=mock.ANY,
                                                       vnf=mock.ANY,
                                                       auth_attr=mock.ANY)
        self._pool.spawn_n.assert_called_once_with(mock.ANY)
        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_CREATE, res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VNF,
            tstamp=mock.ANY, details=mock.ANY)

    @mock.patch('tacker.vnfm.plugin.VNFMPlugin.create_vnfd')
    def test_create_vnf_from_template(self, mock_create_vnfd):
        self._insert_dummy_device_template_inline()
        mock_create_vnfd.return_value = {'id':
                'd58bcc4e-d0cf-11e6-bf26-cec0c932ce01'}
        vnf_obj = utils.get_dummy_inline_vnf_obj()
        result = self.vnfm_plugin.create_vnf(self.context, vnf_obj)
        self.assertIsNotNone(result)
        self.assertIn('id', result)
        self.assertIn('instance_id', result)
        self.assertIn('status', result)
        self.assertIn('attributes', result)
        self.assertIn('mgmt_url', result)
        self.assertIn('created_at', result)
        self.assertIn('updated_at', result)
        mock_create_vnfd.assert_called_once_with(mock.ANY, mock.ANY)
        self._device_manager.invoke.assert_called_with('test_vim',
                                                       'create',
                                                       plugin=mock.ANY,
                                                       context=mock.ANY,
                                                       vnf=mock.ANY,
                                                       auth_attr=mock.ANY)
        self._pool.spawn_n.assert_called_once_with(mock.ANY)
        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_CREATE,
            res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VNF,
            tstamp=mock.ANY, details=mock.ANY)

    def test_show_vnf_details_vnf_inactive(self):
        self._insert_dummy_device_template()
        vnf_obj = utils.get_dummy_vnf_obj()
        result = self.vnfm_plugin.create_vnf(self.context, vnf_obj)
        self.assertRaises(vnfm.VNFInactive, self.vnfm_plugin.get_vnf_resources,
                          self.context, result['id'])

    def test_show_vnf_details_vnf_active(self):
        self._insert_dummy_device_template()
        active_vnf = self._insert_dummy_device()
        resources = self.vnfm_plugin.get_vnf_resources(self.context,
                                                       active_vnf['id'])[0]
        self.assertIn('name', resources)
        self.assertIn('type', resources)
        self.assertIn('id', resources)

    def test_delete_vnf(self):
        self._insert_dummy_device_template()
        dummy_device_obj = self._insert_dummy_device()
        self.vnfm_plugin.delete_vnf(self.context, dummy_device_obj[
            'id'])
        self._device_manager.invoke.assert_called_with('test_vim', 'delete',
                                                       plugin=mock.ANY,
                                                       context=mock.ANY,
                                                       vnf_id=mock.ANY,
                                                       auth_attr=mock.ANY,
                                                       region_name=mock.ANY)
        self._vnf_monitor.delete_hosting_vnf.assert_called_with(mock.ANY)
        self._pool.spawn_n.assert_called_once_with(mock.ANY, mock.ANY,
                                                   mock.ANY, mock.ANY,
                                                   mock.ANY)
        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_DELETE, res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VNF,
            tstamp=mock.ANY, details=mock.ANY)

    def test_update_vnf(self):
        self._insert_dummy_device_template()
        dummy_device_obj = self._insert_dummy_device()
        vnf_config_obj = utils.get_dummy_vnf_config_obj()
        result = self.vnfm_plugin.update_vnf(self.context, dummy_device_obj[
            'id'], vnf_config_obj)
        self.assertIsNotNone(result)
        self.assertEqual(dummy_device_obj['id'], result['id'])
        self.assertIn('instance_id', result)
        self.assertIn('status', result)
        self.assertIn('attributes', result)
        self.assertIn('mgmt_url', result)
        self.assertIn('updated_at', result)
        self._pool.spawn_n.assert_called_once_with(mock.ANY, mock.ANY,
                                                   mock.ANY, mock.ANY,
                                                   mock.ANY)
        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_UPDATE, res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VNF,
            tstamp=mock.ANY)

    def _get_dummy_scaling_policy(self, type):
        vnf_scale = {}
        vnf_scale['scale'] = {}
        vnf_scale['scale']['type'] = type
        vnf_scale['scale']['policy'] = 'SP1'
        return vnf_scale

    def _test_scale_vnf(self, type, scale_state):
        # create vnfd
        self._insert_dummy_device_template()
        self._insert_scaling_attributes_vnfd()

        # create vnf
        dummy_device_obj = self._insert_dummy_device()
        self._insert_scaling_attributes_vnf()

        # scale vnf
        vnf_scale = self._get_dummy_scaling_policy(type)
        self.vnfm_plugin.create_vnf_scale(
            self.context,
            dummy_device_obj['id'],
            vnf_scale)

        # validate
        self._device_manager.invoke.assert_called_once_with(
            mock.ANY,
            'scale',
            plugin=mock.ANY,
            context=mock.ANY,
            auth_attr=mock.ANY,
            policy=mock.ANY,
            region_name=mock.ANY
        )

        self._pool.spawn_n.assert_called_once_with(mock.ANY)

        self._cos_db_plugin.create_event.assert_called_with(
            self.context,
            evt_type=constants.RES_EVT_SCALE,
            res_id='6261579e-d6f3-49ad-8bc3-a9cb974778fe',
            res_state=scale_state,
            res_type=constants.RES_TYPE_VNF,
            tstamp=mock.ANY)

    def test_scale_vnf_out(self):
        self._test_scale_vnf('out', constants.PENDING_SCALE_OUT)

    def test_scale_vnf_in(self):
        self._test_scale_vnf('in', constants.PENDING_SCALE_IN)

    def _get_dummy_active_vnf(self, vnfd_template):
        dummy_vnf = utils.get_dummy_device_obj()
        dummy_vnf['vnfd']['attributes']['vnfd'] = vnfd_template
        dummy_vnf['status'] = 'ACTIVE'
        dummy_vnf['instance_id'] = '4c00108e-c69d-4624-842d-389c77311c1d'
        dummy_vnf['vim_id'] = '437ac8ef-a8fb-4b6e-8d8a-a5e86a376e8b'
        return dummy_vnf

    def _test_create_vnf_trigger(self, policy_name, action_value):
        vnf_id = "6261579e-d6f3-49ad-8bc3-a9cb974778fe"
        trigger_request = {"trigger": {"action_name": action_value, "params": {
            "credential": "026kll6n", "data": {"current": "alarm",
                                               'alarm_id':
                                    "b7fa9ffd-0a4f-4165-954b-5a8d0672a35f"}},
            "policy_name": policy_name}}
        expected_result = {"action_name": action_value, "params": {
            "credential": "026kll6n", "data": {"current": "alarm",
            "alarm_id": "b7fa9ffd-0a4f-4165-954b-5a8d0672a35f"}},
            "policy_name": policy_name}
        self._vnf_alarm_monitor.process_alarm_for_vnf.return_value = True
        trigger_result = self.vnfm_plugin.create_vnf_trigger(
            self.context, vnf_id, trigger_request)
        self.assertEqual(expected_result, trigger_result)

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.get_vnf')
    def test_create_vnf_trigger_respawn(self, mock_get_vnf):
        dummy_vnf = self._get_dummy_active_vnf(
            utils.vnfd_alarm_respawn_tosca_template)
        mock_get_vnf.return_value = dummy_vnf
        self._test_create_vnf_trigger(policy_name="vdu_hcpu_usage_respawning",
                                      action_value="respawn")

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.get_vnf')
    def test_create_vnf_trigger_scale(self, mock_get_vnf):
        dummy_vnf = self._get_dummy_active_vnf(
            utils.vnfd_alarm_scale_tosca_template)
        mock_get_vnf.return_value = dummy_vnf
        self._test_create_vnf_trigger(policy_name="vdu_hcpu_usage_scaling_out",
                                      action_value="SP1-out")

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.get_vnf')
    def test_create_vnf_trigger_multi_actions(self, mock_get_vnf):
        dummy_vnf = self._get_dummy_active_vnf(
            utils.vnfd_alarm_multi_actions_tosca_template)
        mock_get_vnf.return_value = dummy_vnf
        self._test_create_vnf_trigger(policy_name="mon_policy_multi_actions",
                                      action_value="respawn&log")

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.get_vnf')
    def test_get_vnf_policies(self, mock_get_vnf):
        vnf_id = "6261579e-d6f3-49ad-8bc3-a9cb974778fe"
        dummy_vnf = self._get_dummy_active_vnf(
            utils.vnfd_alarm_respawn_tosca_template)
        mock_get_vnf.return_value = dummy_vnf
        policies = self.vnfm_plugin.get_vnf_policies(self.context, vnf_id,
            filters={'name': 'vdu1_cpu_usage_monitoring_policy'})
        self.assertEqual(1, len(policies))
