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
from unittest import mock

from oslo_utils import uuidutils

from tacker import context
from tacker.db.common_services import common_services_db_plugin
from tacker.db.nfvo import nfvo_db
from tacker.db.vnfm import vnfm_db
from tacker.plugins.common import constants
from tacker.tests.unit.db import base as db_base
from tacker.tests.unit.db import utils
from tacker.vnfm import plugin


class FakeCVNFMonitor(mock.Mock):
    pass


class FakePlugin(mock.Mock):
    pass


class FakeK8SVimClient(mock.Mock):
    pass


class TestCVNFMPlugin(db_base.SqlTestCase):
    def setUp(self):
        super(TestCVNFMPlugin, self).setUp()
        self.addCleanup(mock.patch.stopall)
        self.context = context.get_admin_context()
        self._mock_vim_client()
        self._stub_get_vim()
        self._mock_vnf_monitor()
        self._mock_vnf_maintenance_monitor()
        self._mock_vnf_maintenance_plugin()
        self._insert_dummy_vim()
        self.vnfm_plugin = plugin.VNFMPlugin()
        mock.patch('tacker.db.common_services.common_services_db_plugin.'
                   'CommonServicesPluginDb.create_event'
                   ).start()
        mock.patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb._mgmt_driver_name',
                   return_value='noop').start()
        self.create = mock.patch('tacker.vnfm.infra_drivers.kubernetes.'
                                 'kubernetes_driver.Kubernetes.create',
                                 return_value=uuidutils.
                                 generate_uuid()).start()
        self.create_wait = mock.patch('tacker.vnfm.infra_drivers.kubernetes.'
                                      'kubernetes_driver.Kubernetes.'
                                      'create_wait').start()
        self.update = mock.patch('tacker.vnfm.infra_drivers.kubernetes.'
                                 'kubernetes_driver.Kubernetes.update').start()
        self.update_wait = mock.patch('tacker.vnfm.infra_drivers.kubernetes.'
                                      'kubernetes_driver.Kubernetes.'
                                      'update_wait').start()
        self.delete = mock.patch('tacker.vnfm.infra_drivers.kubernetes.'
                                 'kubernetes_driver.Kubernetes.delete').start()
        self.delete_wait = mock.patch('tacker.vnfm.infra_drivers.kubernetes.'
                                      'kubernetes_driver.Kubernetes.'
                                      'delete_wait').start()
        self.scale = mock.patch('tacker.vnfm.infra_drivers.kubernetes.'
                                'kubernetes_driver.Kubernetes.scale',
                                return_value=uuidutils.generate_uuid()).start()
        self.scale_wait = mock.patch('tacker.vnfm.infra_drivers.kubernetes.'
                                     'kubernetes_driver.Kubernetes.scale_wait',
                                     return_value=uuidutils.
                                     generate_uuid()).start()

        def _fake_spawn(func, *args, **kwargs):
            func(*args, **kwargs)

        mock.patch.object(self.vnfm_plugin, 'spawn_n',
                          _fake_spawn).start()
        self._cos_db_plugin =\
            common_services_db_plugin.CommonServicesPluginDb()

    def _mock_vim_client(self):
        self.vim_client = mock.Mock(wraps=FakeK8SVimClient())
        fake_vim_client = mock.Mock()
        fake_vim_client.return_value = self.vim_client
        self._mock(
            'tacker.vnfm.vim_client.VimClient', fake_vim_client)

    def _stub_get_vim(self):
        vim_obj = {'vim_id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                   'vim_name': 'fake_vim',
                   'vim_auth': {'auth_url': 'http://localhost:6443',
                                'password': 'test_pw', 'username': 'test_user',
                                'project_name': 'test_project',
                                'ssl_ca_cert': None},
                   'vim_type': 'kubernetes'}
        self.vim_client.get_vim.return_value = vim_obj

    def _mock_vnf_monitor(self):
        self._vnf_monitor = mock.Mock(wraps=FakeCVNFMonitor())
        fake_vnf_monitor = mock.Mock()
        fake_vnf_monitor.return_value = self._vnf_monitor
        self._mock(
            'tacker.vnfm.monitor.VNFMonitor', fake_vnf_monitor)

    def _mock_vnf_maintenance_monitor(self):
        self._vnf_maintenance_mon = mock.Mock(wraps=FakeCVNFMonitor())
        fake_vnf_maintenance_monitor = mock.Mock()
        fake_vnf_maintenance_monitor.return_value = self._vnf_maintenance_mon
        self._mock(
            'tacker.vnfm.monitor.VNFMaintenanceAlarmMonitor',
            fake_vnf_maintenance_monitor)

    def _mock_vnf_maintenance_plugin(self):
        self._vnf_maintenance_plugin = mock.Mock(wraps=FakePlugin())
        fake_vnf_maintenance_plugin = mock.Mock()
        fake_vnf_maintenance_plugin.return_value = self._vnf_maintenance_plugin
        self._mock(
            'tacker.plugins.fenix.FenixPlugin',
            fake_vnf_maintenance_plugin)

    def _insert_dummy_vnf_template(self):
        session = self.context.session
        vnf_template = vnfm_db.VNFD(
            id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_template',
            description='fake_template_description',
            template_source='onboarded',
            deleted_at=datetime.min)
        session.add(vnf_template)
        session.flush()
        return vnf_template

    def _insert_dummy_vnf_template_inline(self):
        session = self.context.session
        vnf_template = vnfm_db.VNFD(
            id='d58bcc4e-d0cf-11e6-bf26-cec0c932ce01',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='tmpl-koeak4tqgoqo8cr4-dummy_inline_vnf',
            description='inline_fake_template_description',
            deleted_at=datetime.min,
            template_source='inline')
        session.add(vnf_template)
        session.flush()
        return vnf_template

    def _insert_dummy_vim(self):
        pass
        session = self.context.session
        vim_db = nfvo_db.Vim(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_vim',
            description='fake_vim_description',
            type='kubernetes',
            status='Active',
            deleted_at=datetime.min,
            placement_attr={'regions': ['default', 'kube-public',
                                        'kube-system']})
        vim_auth_db = nfvo_db.VimAuth(
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            password='encrypted_pw',
            auth_url='http://localhost:6443',
            vim_project={'name': 'test_project'},
            auth_cred={'auth_url': 'https://localhost:6443',
                       'username': 'admin',
                       'bearer_token': None,
                       'ssl_ca_cert': 'test',
                       'project_name': 'default',
                       'type': 'kubernetes'})
        session.add(vim_db)
        session.add(vim_auth_db)
        session.flush()

    def test_create_cvnf_with_vnfd(self):
        self._insert_dummy_vnf_template()
        vnf_obj = utils.get_dummy_vnf_obj()
        result = self.vnfm_plugin.create_vnf(self.context, vnf_obj)
        self.assertIsNotNone(result)
        self.assertIn('id', result)
        self.assertIn('instance_id', result)
        self.assertIn('status', result)
        self.assertIn('attributes', result)
        self.assertIn('mgmt_ip_address', result)
        self.assertIn('created_at', result)
        self.assertIn('updated_at', result)
        self.assertEqual('ACTIVE', result['status'])
        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_CREATE, res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VNF,
            tstamp=mock.ANY, details=mock.ANY)

    @mock.patch('tacker.vnfm.plugin.VNFMPlugin.create_vnfd')
    def test_create_cvnf_from_template(self, mock_create_vnfd):
        self._insert_dummy_vnf_template_inline()
        mock_create_vnfd.return_value = {'id':
                                         'd58bcc4e-d0cf-11e6-bf26'
                                         '-cec0c932ce01'}
        vnf_obj = utils.get_dummy_inline_cvnf_obj()
        result = self.vnfm_plugin.create_vnf(self.context, vnf_obj)
        self.assertIsNotNone(result)
        self.assertIn('id', result)
        self.assertIn('instance_id', result)
        self.assertIn('status', result)
        self.assertIn('attributes', result)
        self.assertIn('mgmt_ip_address', result)
        self.assertIn('created_at', result)
        self.assertIn('updated_at', result)
        self.assertEqual('ACTIVE', result['status'])
        mock_create_vnfd.assert_called_once_with(mock.ANY, mock.ANY)
        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_CREATE,
            res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VNF,
            tstamp=mock.ANY, details=mock.ANY)

    def test_delete_vnf(self):
        pass

    def test_update_vnf(self):
        pass

    def _test_scale_vnf(self, type):
        pass

    def test_scale_vnf_out(self):
        pass

    def test_scale_vnf_in(self):
        pass
