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

import uuid

import mock

from tacker import context
from tacker.db.nfvo import nfvo_db
from tacker.db.vm import vm_db
from tacker.extensions import vnfm
from tacker.tests.unit.db import base as db_base
from tacker.tests.unit.db import utils
from tacker.vm import plugin


class FakeDriverManager(mock.Mock):
    def invoke(self, *args, **kwargs):
        if 'create' in args:
            return str(uuid.uuid4())


class FakeVNFMonitor(mock.Mock):
    pass


class FakeGreenPool(mock.Mock):
    pass


class FakeVimClient(mock.Mock):
    pass


class TestVNFMPlugin(db_base.SqlTestCase):
    def setUp(self):
        super(TestVNFMPlugin, self).setUp()
        self.addCleanup(mock.patch.stopall)
        self.context = context.get_admin_context()
        self._mock_vim_client()
        self._stub_get_vim()
        self._mock_device_manager()
        self._mock_vnf_monitor()
        self._mock_green_pool()
        self._insert_dummy_vim()
        self.vnfm_plugin = plugin.VNFMPlugin()

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
            'tacker.vm.vim_client.VimClient', fake_vim_client)

    def _stub_get_vim(self):
        vim_obj = {'vim_id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                   'vim_name': 'fake_vim', 'vim_auth':
                   {'auth_url': 'http://localhost:5000', 'password':
                       'test_pw', 'username': 'test_user', 'project_name':
                       'test_project'}}
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
            'tacker.vm.monitor.VNFMonitor', fake_vnf_monitor)

    def _insert_dummy_device_template(self):
        session = self.context.session
        device_template = vm_db.DeviceTemplate(
            id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_template',
            description='fake_template_description',
            infra_driver='fake_driver',
            mgmt_driver='fake_mgmt_driver')
        session.add(device_template)
        session.flush()
        return device_template

    def _insert_dummy_device(self):
        session = self.context.session
        device_db = vm_db.Device(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_device',
            description='fake_device_description',
            instance_id='da85ea1a-4ec4-4201-bbb2-8d9249eca7ec',
            template_id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            placement_attr={'region': 'RegionOne'},
            status='ACTIVE')
        session.add(device_db)
        session.flush()
        return device_db

    def _insert_dummy_vim(self):
        session = self.context.session
        vim_db = nfvo_db.Vim(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_vim',
            description='fake_vim_description',
            type='openstack',
            placement_attr={'regions': ['RegionOne']})
        vim_auth_db = nfvo_db.VimAuth(
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            password='encrypted_pw',
            auth_url='http://localhost:5000',
            vim_project={'name': 'test_project'},
            auth_cred={'username': 'test_user', 'user_domain_id': 'default',
                       'project_domain_d': 'default'})
        session.add(vim_db)
        session.add(vim_auth_db)
        session.flush()

    def test_create_vnfd(self):
        vnfd_obj = utils.get_dummy_vnfd_obj()
        result = self.vnfm_plugin.create_vnfd(self.context, vnfd_obj)
        self.assertIsNotNone(result)
        self.assertIn('id', result)
        self.assertIn('service_types', result)
        self.assertIn('attributes', result)
        self._device_manager.invoke.assert_called_once_with(
            mock.ANY,
            mock.ANY,
            plugin=mock.ANY,
            context=mock.ANY,
            device_template=mock.ANY)

    def test_create_vnfd_no_service_types(self):
        vnfd_obj = utils.get_dummy_vnfd_obj()
        vnfd_obj['vnfd'].pop('service_types')
        self.assertRaises(vnfm.ServiceTypesNotSpecified,
                          self.vnfm_plugin.create_vnfd,
                          self.context, vnfd_obj)

    def test_create_vnfd_no_mgmt_driver(self):
        vnfd_obj = utils.get_dummy_vnfd_obj()
        vnfd_obj['vnfd'].pop('mgmt_driver')
        self.assertRaises(vnfm.MGMTDriverNotSpecified,
                          self.vnfm_plugin.create_vnfd,
                          self.context, vnfd_obj)

    def test_create_vnf(self):
        self._insert_dummy_device_template()
        vnf_obj = utils.get_dummy_vnf_obj()
        result = self.vnfm_plugin.create_vnf(self.context, vnf_obj)
        self.assertIsNotNone(result)
        self.assertIn('id', result)
        self.assertIn('instance_id', result)
        self.assertIn('status', result)
        self.assertIn('attributes', result)
        self.assertIn('mgmt_url', result)
        self._device_manager.invoke.assert_called_with(mock.ANY, mock.ANY,
                                                       plugin=mock.ANY,
                                                       context=mock.ANY,
                                                       device=mock.ANY,
                                                       auth_attr=mock.ANY)
        self._pool.spawn_n.assert_called_once_with(mock.ANY)

    def test_delete_vnf(self):
        self._insert_dummy_device_template()
        dummy_device_obj = self._insert_dummy_device()
        self.vnfm_plugin.delete_vnf(self.context, dummy_device_obj[
            'id'])
        self._device_manager.invoke.assert_called_with(mock.ANY, mock.ANY,
                                                       plugin=mock.ANY,
                                                       context=mock.ANY,
                                                       device_id=mock.ANY,
                                                       auth_attr=mock.ANY,
                                                       region_name=mock.ANY)
        self._vnf_monitor.delete_hosting_vnf.assert_called_with(mock.ANY)
        self._pool.spawn_n.assert_called_once_with(mock.ANY, mock.ANY,
                                                   mock.ANY, mock.ANY)

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
        self._pool.spawn_n.assert_called_once_with(mock.ANY, mock.ANY,
                                                   mock.ANY, mock.ANY)
