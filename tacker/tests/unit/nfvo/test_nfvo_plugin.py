# Copyright 2016 Brocade Communications System, Inc.
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

from oslo_config import cfg
from oslo_utils import uuidutils
from requests_mock.contrib import fixture as rm_fixture

from tacker import context
from tacker.db.nfvo import nfvo_db
from tacker.keymgr import API as KEYMGR_API
from tacker.nfvo import nfvo_plugin
from tacker.tests.unit.db import base as db_base
from tacker.tests.unit.db import utils

SECRET_PASSWORD = '***'


def get_mock_conf_key_effect():
    def mock_conf_key_effect(name):
        if name == 'keystone_authtoken':
            return MockConfig(conf=None)
        elif name == 'ext_oauth2_auth':
            return MockConfig(
                conf={
                    'use_ext_oauth2_auth': True,
                    'token_endpoint': 'http://demo/token_endpoint',
                    'auth_method': 'client_secret_post',
                    'client_id': 'client_id',
                    'client_secret': 'client_secret',
                    'scope': 'client_secret'
                })
        elif name == 'key_manager':
            conf = {
                'api_class': 'tacker.keymgr.barbican_key_manager'
                             '.BarbicanKeyManager',
                'barbican_endpoint': 'http://demo/barbican',
                'barbican_version': 'v1'
            }
            return MockConfig(conf=conf)
        elif name == 'k8s_vim':
            return MockConfig(
                conf={
                    'use_barbican': True
                })
        else:
            return cfg.CONF._get(name)
    return mock_conf_key_effect


class MockConfig(object):
    def __init__(self, conf=None):
        self.conf = conf

    def __getattr__(self, name):
        if not self.conf:
            raise cfg.NoSuchOptError('not found %s' % name)
        if name not in self.conf:
            raise cfg.NoSuchOptError('not found %s' % name)
        return self.conf.get(name)

    def __contains__(self, key):
        return key in self.conf


def dummy_get_vim(*args, **kwargs):
    vim_obj = dict()
    vim_obj['auth_cred'] = utils.get_vim_auth_obj()
    vim_obj['type'] = 'openstack'
    return vim_obj


class FakeDriverManager(mock.Mock):
    def invoke(self, *args, **kwargs):
        if any(x in ['create', 'create_flow_classifier'] for
               x in args):
            return uuidutils.generate_uuid()
        elif 'create_chain' in args:
            return uuidutils.generate_uuid(), uuidutils.generate_uuid()


def get_by_name():
    return False


def dummy_get_vim_auth(*args, **kwargs):
    return {'vim_auth': {'username': 'admin', 'password': 'devstack',
                         'project_name': 'nfv', 'user_id': '',
                         'user_domain_name': 'Default',
                         'auth_url': 'http://10.0.4.207/identity/v3',
                         'project_id': '',
                         'project_domain_name': 'Default'},
            'vim_id': '96025dd5-ca16-49f3-9823-958eb04260c4',
            'vim_type': 'openstack', 'vim_name': 'VIM0'}


class TestNfvoPlugin(db_base.SqlTestCase):
    def setUp(self):
        super(TestNfvoPlugin, self).setUp()
        self.requests_mock = self.useFixture(rm_fixture.Fixture())
        KEYMGR_API('')
        self.access_token = 'access_token_uuid'
        self.addCleanup(mock.patch.stopall)
        self.context = context.get_admin_context()
        self.nfvo_plugin = nfvo_plugin.NfvoPlugin()

    def _mock_driver_manager(self):
        self._driver_manager = mock.Mock(wraps=FakeDriverManager())
        self._driver_manager.__contains__ = mock.Mock(
            return_value=True)
        fake_driver_manager = mock.Mock()
        fake_driver_manager.return_value = self._driver_manager
        self._mock(
            'tacker.common.driver_manager.DriverManager', fake_driver_manager)

    def _mock_external_token_api(self):
        def mock_token_resp(request, context):
            response = {
                'access_token': self.access_token,
                'expires_in': 1800,
                'refresh_expires_in': 0,
                'token_type': 'Bearer',
                'not-before-policy': 0,
                'scope': 'tacker_api'
            }
            context.status_code = 200
            return response

        self.requests_mock.post('http://demo/token_endpoint',
                                json=mock_token_resp)

    def _insert_dummy_vim(self):
        session = self.context.session
        vim_db = nfvo_db.Vim(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_vim',
            description='fake_vim_description',
            type='openstack',
            deleted_at=datetime.min,
            placement_attr={'regions': ['RegionOne']})
        vim_auth_db = nfvo_db.VimAuth(
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            password='encrypted_pw',
            auth_url='http://localhost/identity',
            vim_project={'name': 'test_project'},
            auth_cred={'username': 'test_user', 'user_domain_id': 'default',
                       'project_domain_id': 'default',
                       'key_type': 'fernet_key'})
        session.add(vim_db)
        session.add(vim_auth_db)
        session.flush()

    def _insert_dummy_vim_barbican(self):
        session = self.context.session
        vim_db = nfvo_db.Vim(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_vim',
            description='fake_vim_description',
            type='openstack',
            deleted_at=datetime.min,
            placement_attr={'regions': ['RegionOne']})
        vim_auth_db = nfvo_db.VimAuth(
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            password='encrypted_pw',
            auth_url='http://localhost/identity',
            vim_project={'name': 'test_project'},
            auth_cred={'username': 'test_user', 'user_domain_id': 'default',
                       'project_domain_id': 'default',
                       'key_type': 'barbican_key',
                       'secret_uuid': 'fake-secret-uuid'})
        session.add(vim_db)
        session.add(vim_auth_db)
        session.flush()

    def _insert_dummy_vim_k8s_user(self):
        session = self.context.session
        vim_db = nfvo_db.Vim(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_vim',
            description='fake_vim_description',
            type='kubernetes',
            deleted_at=datetime.min,
            placement_attr={'regions': ['RegionOne']})
        vim_auth_db = nfvo_db.VimAuth(
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            password='encrypted_pw',
            auth_url='http://localhost:6443',
            vim_project={'name': 'test_project'},
            auth_cred={'username': 'test_user',
                       'key_type': 'barbican_key',
                       'secret_uuid': 'fake-secret-uuid'})
        session.add(vim_db)
        session.add(vim_auth_db)
        session.flush()

    def _insert_dummy_vim_k8s_token(self):
        session = self.context.session
        vim_db = nfvo_db.Vim(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_vim',
            description='fake_vim_description',
            type='kubernetes',
            deleted_at=datetime.min,
            placement_attr={'regions': ['RegionOne']})
        vim_auth_db = nfvo_db.VimAuth(
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            password='encrypted_pw',
            auth_url='http://localhost:6443',
            vim_project={'name': 'test_project'},
            auth_cred={'bearer_token': 'encrypted_token',
                       'key_type': 'barbican_key',
                       'secret_uuid': 'fake-secret-uuid'})
        session.add(vim_db)
        session.add(vim_auth_db)
        session.flush()

    def _insert_dummy_vim_k8s_oidc(self):
        session = self.context.session
        vim_db = nfvo_db.Vim(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_vim',
            description='fake_vim_description',
            type='kubernetes',
            deleted_at=datetime.min,
            placement_attr={'regions': ['RegionOne']})
        vim_auth_db = nfvo_db.VimAuth(
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            password='encrypted_pw',
            auth_url='http://localhost:6443',
            vim_project={'name': 'test_project'},
            auth_cred={'username': 'oidc_user',
                       'oidc_token_url': 'https://localhost:8443',
                       'client_id': 'oidc_client',
                       'client_secret': 'encrypted_secret',
                       'ssl_ca_cert': 'cert_content',
                       'key_type': 'barbican_key',
                       'secret_uuid': 'fake-secret-uuid'})
        session.add(vim_db)
        session.add(vim_auth_db)
        session.flush()

    def test_create_vim(self):
        vim_dict = utils.get_vim_obj()
        vim_type = 'openstack'
        self._mock_driver_manager()
        self.nfvo_plugin = nfvo_plugin.NfvoPlugin()
        res = self.nfvo_plugin.create_vim(self.context, vim_dict)
        self._driver_manager.invoke.assert_any_call(
            vim_type, 'register_vim', vim_obj=vim_dict['vim'])
        self.assertIsNotNone(res)
        self.assertEqual(SECRET_PASSWORD, res['auth_cred']['password'])
        self.assertIn('id', res)
        self.assertIn('placement_attr', res)
        self.assertIn('created_at', res)
        self.assertIn('updated_at', res)
        self.assertEqual(False, res['is_default'])
        self.assertEqual('openstack', res['type'])

    def test_create_vim_k8s_token(self):
        vim_dict = {'vim': {'type': 'kubernetes',
                    'auth_url': 'http://localhost/identity',
                    'vim_project': {'name': 'test_project'},
                    'auth_cred': {'bearer_token': 'test_token'},
                    'name': 'VIM0',
                    'tenant_id': 'test-project'}}
        vim_type = 'kubernetes'
        self._mock_driver_manager()
        self.nfvo_plugin = nfvo_plugin.NfvoPlugin()
        res = self.nfvo_plugin.create_vim(self.context, vim_dict)
        self._driver_manager.invoke.assert_any_call(
            vim_type, 'register_vim', vim_obj=vim_dict['vim'])
        self.assertIsNotNone(res)
        self.assertEqual(SECRET_PASSWORD, res['auth_cred']['bearer_token'])
        self.assertIn('id', res)
        self.assertIn('placement_attr', res)
        self.assertIn('created_at', res)
        self.assertIn('updated_at', res)
        self.assertEqual(False, res['is_default'])
        self.assertEqual(vim_type, res['type'])

    def test_create_vim_k8s_oidc(self):
        vim_dict = {'vim': {'type': 'kubernetes',
                    'auth_url': 'http://localhost/identity',
                    'vim_project': {'name': 'test_project'},
                    'auth_cred': {
                        'username': 'oidc_user',
                        'password': 'oidc_password',
                        'oidc_token_url': 'https://localhost:8443',
                        'client_id': 'oidc_client',
                        'client_secret': 'oidc_secret',
                        'ssl_ca_cert': 'cert_content'},
                    'name': 'VIM0',
                    'tenant_id': 'test-project'}}
        vim_type = 'kubernetes'
        vim_auth_username = vim_dict['vim']['auth_cred']['username']
        vim_auth_client_id = vim_dict['vim']['auth_cred']['client_id']
        vim_auth_oidc_url = vim_dict['vim']['auth_cred']['oidc_token_url']
        vim_auth_cert = vim_dict['vim']['auth_cred']['ssl_ca_cert']
        vim_project = vim_dict['vim']['vim_project']
        self._mock_driver_manager()
        self.nfvo_plugin = nfvo_plugin.NfvoPlugin()
        res = self.nfvo_plugin.create_vim(self.context, vim_dict)
        self._driver_manager.invoke.assert_any_call(
            vim_type, 'register_vim', vim_obj=vim_dict['vim'])
        self.assertIsNotNone(res)
        self.assertEqual(SECRET_PASSWORD, res['auth_cred']['password'])
        self.assertEqual(vim_project, res['vim_project'])
        self.assertEqual(vim_auth_username, res['auth_cred']['username'])
        self.assertEqual(SECRET_PASSWORD, res['auth_cred']['password'])
        self.assertEqual(vim_auth_oidc_url, res['auth_cred']['oidc_token_url'])
        self.assertEqual(vim_auth_client_id, res['auth_cred']['client_id'])
        self.assertEqual(SECRET_PASSWORD, res['auth_cred']['client_secret'])
        self.assertEqual(vim_auth_cert, res['auth_cred']['ssl_ca_cert'])
        self.assertIn('id', res)
        self.assertIn('placement_attr', res)
        self.assertIn('created_at', res)
        self.assertIn('updated_at', res)
        self.assertEqual(False, res['is_default'])
        self.assertEqual(vim_type, res['type'])

    def test_delete_vim(self):
        self._insert_dummy_vim()
        vim_type = 'openstack'
        vim_id = '6261579e-d6f3-49ad-8bc3-a9cb974778ff'
        self.context.tenant_id = 'ad7ebc56538745a08ef7c5e97f8bd437'
        vim_obj = self.nfvo_plugin._get_vim(self.context, vim_id)
        self._mock_driver_manager()
        self.nfvo_plugin = nfvo_plugin.NfvoPlugin()
        self.nfvo_plugin.delete_vim(self.context, vim_id)
        self._driver_manager.invoke.assert_called_once_with(
            vim_type, 'deregister_vim',
            vim_obj=vim_obj)

    def test_update_vim(self):
        vim_dict = {'vim': {'id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                            'vim_project': {'name': 'new_project'},
                            'auth_cred': {'username': 'new_user',
                                          'password': 'new_password'}}}
        vim_type = 'openstack'
        vim_auth_username = vim_dict['vim']['auth_cred']['username']
        vim_project = vim_dict['vim']['vim_project']
        self._insert_dummy_vim()
        self.context.tenant_id = 'ad7ebc56538745a08ef7c5e97f8bd437'
        self._mock_driver_manager()
        self.nfvo_plugin = nfvo_plugin.NfvoPlugin()
        res = self.nfvo_plugin.update_vim(self.context, vim_dict['vim']['id'],
                                          vim_dict)
        vim_obj = self.nfvo_plugin._get_vim(
            self.context, vim_dict['vim']['id'])
        vim_obj['updated_at'] = None
        self._driver_manager.invoke.assert_called_with(
            vim_type, 'register_vim',
            vim_obj=vim_obj)
        self.assertIsNotNone(res)
        self.assertIn('id', res)
        self.assertIn('placement_attr', res)
        self.assertEqual(vim_project, res['vim_project'])
        self.assertEqual(vim_auth_username, res['auth_cred']['username'])
        self.assertEqual(SECRET_PASSWORD, res['auth_cred']['password'])
        self.assertIn('updated_at', res)

    def test_update_vim_barbican(self):
        vim_dict = {'vim': {'id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                            'vim_project': {'name': 'new_project'},
                            'auth_cred': {'username': 'new_user',
                                          'password': 'new_password'}}}
        vim_type = 'openstack'
        vim_auth_username = vim_dict['vim']['auth_cred']['username']
        vim_project = vim_dict['vim']['vim_project']
        self._insert_dummy_vim_barbican()
        self.context.tenant_id = 'ad7ebc56538745a08ef7c5e97f8bd437'
        old_vim_obj = self.nfvo_plugin._get_vim(
            self.context, vim_dict['vim']['id'])
        self._mock_driver_manager()
        self.nfvo_plugin = nfvo_plugin.NfvoPlugin()
        res = self.nfvo_plugin.update_vim(self.context, vim_dict['vim']['id'],
                                          vim_dict)
        vim_obj = self.nfvo_plugin._get_vim(
            self.context, vim_dict['vim']['id'])
        vim_obj['updated_at'] = None
        self._driver_manager.invoke.assert_called_with(
            vim_type, 'delete_vim_auth',
            vim_id=vim_obj['id'],
            auth=old_vim_obj['auth_cred'])
        self.assertIsNotNone(res)
        self.assertIn('id', res)
        self.assertIn('placement_attr', res)
        self.assertEqual(vim_project, res['vim_project'])
        self.assertEqual(vim_auth_username, res['auth_cred']['username'])
        self.assertEqual(SECRET_PASSWORD, res['auth_cred']['password'])
        self.assertIn('updated_at', res)

    def test_update_vim_userpass_to_oidc(self):
        vim_dict = {'vim': {'id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                            'vim_project': {'name': 'new_project'},
                            'auth_cred': {
                                'username': 'oidc_user',
                                'password': 'oidc_password',
                                'oidc_token_url': 'https://localhost:8443',
                                'client_id': 'oidc_client',
                                'client_secret': 'oidc_secret',
                                'ssl_ca_cert': 'cert_content'
                            }}}
        vim_type = 'kubernetes'
        vim_auth_username = vim_dict['vim']['auth_cred']['username']
        vim_auth_client_id = vim_dict['vim']['auth_cred']['client_id']
        vim_auth_oidc_url = vim_dict['vim']['auth_cred']['oidc_token_url']
        vim_auth_cert = vim_dict['vim']['auth_cred']['ssl_ca_cert']
        vim_project = vim_dict['vim']['vim_project']
        self._insert_dummy_vim_k8s_user()
        self.context.tenant_id = 'ad7ebc56538745a08ef7c5e97f8bd437'
        old_vim_obj = self.nfvo_plugin._get_vim(
            self.context, vim_dict['vim']['id'])
        self._mock_driver_manager()
        self.nfvo_plugin = nfvo_plugin.NfvoPlugin()
        res = self.nfvo_plugin.update_vim(self.context, vim_dict['vim']['id'],
                                          vim_dict)
        vim_obj = self.nfvo_plugin._get_vim(
            self.context, vim_dict['vim']['id'])
        vim_obj['updated_at'] = None
        self._driver_manager.invoke.assert_called_with(
            vim_type, 'delete_vim_auth',
            vim_id=vim_obj['id'],
            auth=old_vim_obj['auth_cred'])
        self.assertIsNotNone(res)
        self.assertIn('id', res)
        self.assertIn('placement_attr', res)
        self.assertEqual(vim_project, res['vim_project'])
        self.assertEqual(vim_auth_username, res['auth_cred']['username'])
        self.assertEqual(SECRET_PASSWORD, res['auth_cred']['password'])
        self.assertEqual(vim_auth_oidc_url, res['auth_cred']['oidc_token_url'])
        self.assertEqual(vim_auth_client_id, res['auth_cred']['client_id'])
        self.assertEqual(SECRET_PASSWORD, res['auth_cred']['client_secret'])
        self.assertEqual(vim_auth_cert, res['auth_cred']['ssl_ca_cert'])
        self.assertIn('updated_at', res)

    def test_update_vim_token_to_oidc(self):
        vim_dict = {'vim': {'id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                            'vim_project': {'name': 'new_project'},
                            'auth_cred': {
                                'username': 'oidc_user',
                                'password': 'oidc_password',
                                'oidc_token_url': 'https://localhost:8443',
                                'client_id': 'oidc_client',
                                'client_secret': 'oidc_secret',
                                'ssl_ca_cert': 'cert_content'
                            }}}
        vim_type = 'kubernetes'
        vim_auth_username = vim_dict['vim']['auth_cred']['username']
        vim_auth_client_id = vim_dict['vim']['auth_cred']['client_id']
        vim_auth_oidc_url = vim_dict['vim']['auth_cred']['oidc_token_url']
        vim_auth_cert = vim_dict['vim']['auth_cred']['ssl_ca_cert']
        vim_project = vim_dict['vim']['vim_project']
        self._insert_dummy_vim_k8s_token()
        self.context.tenant_id = 'ad7ebc56538745a08ef7c5e97f8bd437'
        old_vim_obj = self.nfvo_plugin._get_vim(
            self.context, vim_dict['vim']['id'])
        self._mock_driver_manager()
        self.nfvo_plugin = nfvo_plugin.NfvoPlugin()
        res = self.nfvo_plugin.update_vim(self.context, vim_dict['vim']['id'],
                                          vim_dict)
        vim_obj = self.nfvo_plugin._get_vim(
            self.context, vim_dict['vim']['id'])
        vim_obj['updated_at'] = None
        self._driver_manager.invoke.assert_called_with(
            vim_type, 'delete_vim_auth',
            vim_id=vim_obj['id'],
            auth=old_vim_obj['auth_cred'])
        self.assertIsNotNone(res)
        self.assertIn('id', res)
        self.assertIn('placement_attr', res)
        self.assertEqual(vim_project, res['vim_project'])
        self.assertNotIn('bearer_token', res['auth_cred'])
        self.assertEqual(vim_auth_username, res['auth_cred']['username'])
        self.assertEqual(SECRET_PASSWORD, res['auth_cred']['password'])
        self.assertEqual(vim_auth_oidc_url, res['auth_cred']['oidc_token_url'])
        self.assertEqual(vim_auth_client_id, res['auth_cred']['client_id'])
        self.assertEqual(SECRET_PASSWORD, res['auth_cred']['client_secret'])
        self.assertEqual(vim_auth_cert, res['auth_cred']['ssl_ca_cert'])
        self.assertIn('updated_at', res)

    def test_update_vim_oidc_to_token(self):
        vim_dict = {'vim': {'id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                            'vim_project': {'name': 'new_project'},
                            'auth_cred': {
                                'bearer_token': 'bearer_token'
                            }}}
        vim_type = 'kubernetes'
        vim_project = vim_dict['vim']['vim_project']
        self._insert_dummy_vim_k8s_oidc()
        self.context.tenant_id = 'ad7ebc56538745a08ef7c5e97f8bd437'
        old_vim_obj = self.nfvo_plugin._get_vim(
            self.context, vim_dict['vim']['id'])
        self._mock_driver_manager()
        self.nfvo_plugin = nfvo_plugin.NfvoPlugin()
        res = self.nfvo_plugin.update_vim(self.context, vim_dict['vim']['id'],
                                          vim_dict)
        vim_obj = self.nfvo_plugin._get_vim(
            self.context, vim_dict['vim']['id'])
        vim_obj['updated_at'] = None
        self._driver_manager.invoke.assert_called_with(
            vim_type, 'delete_vim_auth',
            vim_id=vim_obj['id'],
            auth=old_vim_obj['auth_cred'])
        self.assertIsNotNone(res)
        self.assertIn('id', res)
        self.assertIn('placement_attr', res)
        self.assertEqual(vim_project, res['vim_project'])
        self.assertEqual(SECRET_PASSWORD, res['auth_cred']['bearer_token'])
        self.assertNotIn('oidc_token_url', res['auth_cred'])
        self.assertNotIn('client_id', res['auth_cred'])
        self.assertNotIn('client_secret', res['auth_cred'])
        self.assertNotIn('username', res['auth_cred'])
        self.assertNotIn('password', res['auth_cred'])
        self.assertIn('updated_at', res)
