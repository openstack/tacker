# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from collections import namedtuple
from unittest import mock

from oslo_config import cfg

from tacker import context as t_context
from tacker.extensions import nfvo
from tacker.nfvo.drivers.vim import kubernetes_driver
from tacker.tests.unit import base


OPTS = [cfg.StrOpt('user_domain_id',
                   default='default',
                   help='User Domain Id'),
        cfg.StrOpt('project_domain_id',
                   default='default',
                   help='Project Domain Id'),
        cfg.StrOpt('password',
                   default='default',
                   help='User Password'),
        cfg.StrOpt('username',
                   default='default',
                   help='User Name'),
        cfg.StrOpt('user_domain_name',
                   default='Default',
                   help='Use Domain Name'),
        cfg.StrOpt('project_name',
                   default='default',
                   help='Project Name'),
        cfg.StrOpt('project_domain_name',
                   default='Default',
                   help='Project Domain Name'),
        cfg.StrOpt('auth_url',
                   default='http://localhost/identity/v3',
                   help='Keystone endpoint')]

cfg.CONF.register_opts(OPTS, 'keystone_authtoken')
CONF = cfg.CONF


def get_mock_conf_key_effect():
    def mock_conf_key_effect(name):
        if name == 'ext_oauth2_auth':
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
                'barbican_version': 'v1',
                'barbican_endpoint': 'http://test/barbican'
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


class FakeKubernetesAPI(mock.Mock):
    pass


class FakeKeymgrAPI(mock.Mock):
    pass


class mock_dict(dict):
    def __getattr__(self, item):
        return self.get(item)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


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


class TestKubernetes_Driver(base.TestCase):
    def setUp(self):
        super(TestKubernetes_Driver, self).setUp()
        self._mock_kubernetes()
        self.config_fixture.config(group='k8s_vim', use_barbican=True)
        self.kubernetes_driver = kubernetes_driver.Kubernetes_Driver()
        self.vim_obj = self.get_vim_obj()
        self.addCleanup(mock.patch.stopall)
        self._mock_keymgr()

    def _mock_kubernetes(self):
        self.kubernetes_api = mock.Mock(wraps=FakeKubernetesAPI())
        fake_kubernetes_api = mock.Mock()
        fake_kubernetes_api.return_value = self.kubernetes_api
        self._mock('tacker.common.container.kubernetes_utils.'
                   'KubernetesHTTPAPI', fake_kubernetes_api)

    def _mock_keymgr(self):
        self.keymgr = mock.Mock(wraps=FakeKeymgrAPI())
        fake_keymgr = mock.Mock()
        fake_keymgr.return_value = self.keymgr
        self._mock(
            'tacker.keymgr.barbican_key_manager.BarbicanKeyManager',
            fake_keymgr)

    def get_vim_obj(self):
        return {'id': '647a91c3-d436-43e6-a1e8-71118dde84ce',
                'type': 'kubernetes',
                'auth_url': 'https://localhost:6443',
                'auth_cred': {'username': 'test_user',
                              'password': 'test_password',
                              'ssl_ca_cert': 'None'},
                'name': 'vim-kubernetes',
                'vim_project': {'name': 'default'}}

    def get_vim_obj_barbican(self):
        return {'id': '647a91c3-d436-43e6-a1e8-71118dde84ce',
                'type': 'kubernetes',
                'auth_url': 'https://localhost:6443',
                'auth_cred': {'username': 'test_user',
                              'password': 'test_password',
                              'ssl_ca_cert': 'abcxyz',
                              'key_type': 'barbican_key',
                              'secret_uuid': 'fake-secret-uuid'},
                'name': 'vim-kubernetes',
                'vim_project': {'name': 'default'}}

    def test_register_k8sclient(self):
        dict = {'name': 'default'}
        name = namedtuple("name", dict.keys())(*dict.values())
        dict = {'metadata': name}
        metadata = namedtuple("metadata", dict.keys())(*dict.values())
        dict = {'items': [metadata]}
        namespaces = namedtuple("namespace", dict.keys())(*dict.values())
        attrs = {'list_namespace.return_value': namespaces}
        mock_k8s_client = mock.Mock()
        mock_k8s_coreV1Client = mock.Mock(**attrs)
        auth_obj = {'username': 'test_user',
                    'password': 'test_password',
                    'ssl_ca_cert': 'None',
                    'auth_url': 'https://localhost:6443'}
        self._test_register_vim(self.vim_obj, mock_k8s_client,
                                mock_k8s_coreV1Client)
        mock_k8s_coreV1Client.list_namespace.assert_called_once_with()
        self.kubernetes_api. \
            get_core_api_client.assert_called_once_with(auth_obj)

    def _test_register_vim(self, vim_obj, mock_k8s_client,
                           mock_k8s_coreV1Client,
                           fernet_obj_encrypt_called_count=1):
        self.kubernetes_api. \
            get_core_api_client.return_value = mock_k8s_client
        self.kubernetes_api. \
            get_core_v1_api_client.return_value = mock_k8s_coreV1Client
        fernet_attrs = {'encrypt.return_value': 'encrypted_password'}
        mock_fernet_obj = mock.Mock(**fernet_attrs)
        mock_fernet_key = 'test_fernet_key'
        self.kubernetes_api.create_fernet_key.return_value = (mock_fernet_key,
                                                              mock_fernet_obj)
        self.kubernetes_api.create_ca_cert_tmp_file.\
            return_value = ('file_descriptor', 'file_path')
        self.kubernetes_driver.register_vim(vim_obj)
        self.assertEqual(mock_fernet_obj.encrypt.call_count,
                         fernet_obj_encrypt_called_count)

    def test_deregister_vim_barbican(self):
        self.keymgr.delete.return_value = None
        vim_obj = self.get_vim_obj_barbican()
        self.kubernetes_driver.deregister_vim(vim_obj)
        self.keymgr.delete.assert_called_once_with(
            t_context.generate_tacker_service_context(), 'fake-secret-uuid')

    def test_encode_vim_auth_barbican(self):
        self.config_fixture.config(group='k8s_vim',
                                   use_barbican=True)
        fernet_attrs = {'encrypt.return_value': 'encrypted_password'}
        mock_fernet_obj = mock.Mock(**fernet_attrs)
        mock_fernet_key = 'test_fernet_key'
        self.keymgr.store.return_value = 'fake-secret-uuid'
        self.kubernetes_api.create_fernet_key.return_value = (mock_fernet_key,
                                                              mock_fernet_obj)

        vim_obj = self.get_vim_obj()
        self.kubernetes_driver.encode_vim_auth(
            vim_obj['id'], vim_obj['auth_cred'])

        self.keymgr.store.assert_called_once_with(
            t_context.generate_tacker_service_context(), 'test_fernet_key')
        mock_fernet_obj.encrypt.assert_called_once_with(mock.ANY)
        self.assertEqual(vim_obj['auth_cred']['key_type'],
                         'barbican_key')
        self.assertEqual(vim_obj['auth_cred']['secret_uuid'],
                         'fake-secret-uuid')

    def test_register_vim_with_use_helm_parameter(self):
        name_value = {'name': 'default'}
        name = namedtuple("name", name_value.keys())(*name_value.values())
        metadata_value = {'metadata': name}
        metadata = namedtuple(
            "metadata", metadata_value.keys())(*metadata_value.values())
        items_value = {'items': [metadata]}
        namespaces = namedtuple(
            "namespace", items_value.keys())(*items_value.values())
        attrs = {'list_namespace.return_value': namespaces}
        mock_k8s_client = mock.Mock()
        mock_k8s_coreV1Client = mock.Mock(**attrs)
        auth_obj = {'username': 'test_user',
                    'password': 'test_password',
                    'ssl_ca_cert': 'ABC',
                    'ca_cert_file': 'file_path',
                    'auth_url': 'https://localhost:6443'}
        self.vim_obj['extra'] = {'use_helm': True}
        self.vim_obj['auth_cred']['ssl_ca_cert'] = 'ABC'
        self._test_register_vim(self.vim_obj, mock_k8s_client,
                                mock_k8s_coreV1Client,
                                fernet_obj_encrypt_called_count=2)
        mock_k8s_coreV1Client.list_namespace.assert_called_once_with()
        self.kubernetes_api. \
            get_core_api_client.assert_called_once_with(auth_obj)

    def test_register_vim_with_use_helm_parameter_and_not_set_ssl_ca_cert(
            self):
        self.vim_obj['extra'] = {'use_helm': True}
        del self.vim_obj['auth_cred']['ssl_ca_cert']
        self.assertRaises(nfvo.VimUnauthorizedException,
                          self.kubernetes_driver.register_vim, self.vim_obj)

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_deregister_vim_barbican_ext_oauth2_auth(self, mock_get_conf_key):
        mock_get_conf_key.side_effect = get_mock_conf_key_effect()
        self.keymgr.delete.return_value = None
        vim_obj = self.get_vim_obj_barbican()
        self.kubernetes_driver.deregister_vim(vim_obj)

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_encode_vim_auth_barbican_ext_oauth2_auth(self, mock_get_conf_key):
        mock_get_conf_key.side_effect = get_mock_conf_key_effect()
        self.config_fixture.config(group='k8s_vim',
                                   use_barbican=True)
        fernet_attrs = {'encrypt.return_value': 'encrypted_password'}
        mock_fernet_obj = mock.Mock(**fernet_attrs)
        mock_fernet_key = 'test_fernet_key'
        self.keymgr.store.return_value = 'fake-secret-uuid'
        self.kubernetes_api.create_fernet_key.return_value = (mock_fernet_key,
                                                              mock_fernet_obj)

        vim_obj = self.get_vim_obj()
        self.kubernetes_driver.encode_vim_auth(
            vim_obj['id'], vim_obj['auth_cred'])

        mock_fernet_obj.encrypt.assert_called_once_with(mock.ANY)
        self.assertEqual(vim_obj['auth_cred']['key_type'],
                         'barbican_key')
        self.assertEqual(vim_obj['auth_cred']['secret_uuid'],
                         'fake-secret-uuid')
