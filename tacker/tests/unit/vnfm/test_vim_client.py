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

from sqlalchemy.orm import exc as orm_exc
from unittest import mock

from oslo_config import cfg
from requests_mock.contrib import fixture as rm_fixture

from tacker.extensions import nfvo
from tacker.keymgr import API as KEYMGR_API
from tacker import manager
from tacker.tests.unit import base
from tacker.vnfm import vim_client


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


class TestVIMClient(base.TestCase):

    def setUp(self):
        super(TestVIMClient, self).setUp()
        self.requests_mock = self.useFixture(rm_fixture.Fixture())
        KEYMGR_API('')
        self.access_token = 'access_token_uuid'
        self.vim_info = {'id': 'aaaa', 'name': 'VIM0', 'type': 'test_vim',
                         'auth_cred': {'password': '****'},
                         'auth_url': 'http://127.0.0.1/identity/v3',
                         'placement_attr': {'regions': ['TestRegionOne']},
                         'tenant_id': 'test'}
        self.vimclient = vim_client.VimClient()
        self.service_plugins = mock.Mock()
        self.nfvo_plugin = mock.Mock()

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

    def test_get_vim_without_defined_default_vim(self):
        self.nfvo_plugin.get_default_vim.side_effect = \
            orm_exc.NoResultFound()
        self.service_plugins.get.return_value = self.nfvo_plugin
        with mock.patch.object(manager.TackerManager, 'get_service_plugins',
                               return_value=self.service_plugins):
            self.assertRaises(nfvo.VimDefaultNotDefined,
                              self.vimclient.get_vim, None)

    def test_get_vim_not_found_exception(self):
        vim_id = self.vim_info['id']
        self.nfvo_plugin.get_vim.side_effect = \
            orm_exc.NoResultFound()
        self.service_plugins.get.return_value = self.nfvo_plugin
        with mock.patch.object(manager.TackerManager, 'get_service_plugins',
                               return_value=self.service_plugins):
            self.assertRaises(nfvo.VimNotFoundException,
                              self.vimclient.get_vim, None, vim_id=vim_id)

    def test_get_vim_region_not_found_region_name_invalid(self):
        self.nfvo_plugin.get_vim.return_value = self.vim_info
        self.service_plugins.get.return_value = self.nfvo_plugin
        with mock.patch.object(manager.TackerManager, 'get_service_plugins',
                               return_value=self.service_plugins):
            self.assertRaises(nfvo.VimRegionNotFoundException,
                              self.vimclient.get_vim, None,
                              vim_id=self.vim_info['id'],
                              region_name='Test')

    def test_get_vim(self):
        self.nfvo_plugin.get_vim.return_value = self.vim_info
        self.service_plugins.get.return_value = self.nfvo_plugin
        self.vimclient._build_vim_auth = mock.Mock()
        self.vimclient._build_vim_auth.return_value = {'password': '****'}
        with mock.patch.object(manager.TackerManager, 'get_service_plugins',
                               return_value=self.service_plugins):
            vim_result = self.vimclient.get_vim(None,
                                                vim_id=self.vim_info['id'],
                                                region_name='TestRegionOne')
            vim_expect = {'vim_auth': {'password': '****'}, 'vim_id': 'aaaa',
                          'vim_name': 'VIM0', 'vim_type': 'test_vim',
                          'placement_attr': {'regions': ['TestRegionOne']},
                          'tenant': 'test', 'extra': {}}
            self.assertEqual(vim_expect, vim_result)

    def test_get_vim_oidc_auth(self):
        self.nfvo_plugin.get_vim.return_value = {
            'id': 'aaaa', 'name': 'VIM0', 'type': 'test_vim',
            'auth_cred': {'password': '****',
                          'client_secret': '****',
                          'ssl_ca_cert': '****'},
            'auth_url': 'http://127.0.0.1/identity/v3',
            'placement_attr': {'regions': ['TestRegionOne']},
            'tenant_id': 'test'}
        self.service_plugins.get.return_value = self.nfvo_plugin
        self.vimclient._build_vim_auth = mock.Mock()
        self.vimclient._build_vim_auth.return_value = {
            'password': '****',
            'client_secret': '****',
            'ssl_ca_cert': '****'}
        with mock.patch.object(manager.TackerManager, 'get_service_plugins',
                               return_value=self.service_plugins):
            vim_result = self.vimclient.get_vim(None,
                                                vim_id=self.vim_info['id'],
                                                region_name='TestRegionOne')
            vim_expect = {'vim_auth': {'password': '****',
                                       'client_secret': '****',
                                       'ssl_ca_cert': '****'},
                          'vim_id': 'aaaa',
                          'vim_name': 'VIM0', 'vim_type': 'test_vim',
                          'placement_attr': {'regions': ['TestRegionOne']},
                          'tenant': 'test', 'extra': {}}
            self.assertEqual(vim_expect, vim_result)

    def test_get_vim_with_default_name(self):
        self.vim_info.pop('name')
        self.nfvo_plugin.get_vim.return_value = self.vim_info
        self.service_plugins.get.return_value = self.nfvo_plugin
        self.vimclient._build_vim_auth = mock.Mock()
        self.vimclient._build_vim_auth.return_value = {'password': '****'}
        with mock.patch.object(manager.TackerManager, 'get_service_plugins',
                               return_value=self.service_plugins):
            vim_result = self.vimclient.get_vim(None,
                                                vim_id=self.vim_info['id'],
                                                region_name='TestRegionOne')
            vim_expect = {'vim_auth': {'password': '****'}, 'vim_id': 'aaaa',
                          'vim_name': 'aaaa', 'vim_type': 'test_vim',
                          'placement_attr': {'regions': ['TestRegionOne']},
                          'tenant': 'test', 'extra': {}}
            self.assertEqual(vim_expect, vim_result)

    def test_find_vim_key_with_key_not_found_exception(self):
        vim_id = self.vim_info['id']
        self.assertRaises(nfvo.VimKeyNotFoundException,
                          self.vimclient._find_vim_key, vim_id)

    def test_region_valid_false(self):
        vim_regions = ['TestRegionOne', 'TestRegionTwo']
        region_name = 'TestRegion'
        self.assertFalse(self.vimclient.region_valid(vim_regions,
                                                     region_name))

    def test_region_valid_true(self):
        vim_regions = ['TestRegionOne', 'TestRegionTwo']
        region_name = 'TestRegionOne'
        self.assertTrue(self.vimclient.region_valid(vim_regions, region_name))

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    @mock.patch('barbicanclient.base.validate_ref_and_return_uuid')
    @mock.patch('cryptography.fernet.Fernet.decrypt')
    def test_get_vim_extenal(self, mock_decrypt, mock_validate,
                             mock_get_conf_key):
        mock_get_conf_key.side_effect = get_mock_conf_key_effect()
        self._mock_external_token_api()
        barbican_uuid = 'test_uuid'
        mock_validate.return_value = barbican_uuid
        vim_info = {'id': 'aaaa', 'name': 'VIM0', 'type': 'test_vim',
                    'auth_cred': {'username': 'test',
                                  'user_domain_name': 'test',
                                  'cert_verify': 'True',
                                  'project_id': 'test',
                                  'project_name': 'test',
                                  'project_domain_name': 'test',
                                  'auth_url': 'http://test/identity/v3',
                                  'key_type': 'barbican_key',
                                  'secret_uuid': '***',
                                  'password': '***'},
                    'auth_url': 'http://127.0.0.1/identity/v3',
                    'placement_attr': {'regions': ['TestRegionOne']},
                    'tenant_id': 'test'}
        self.nfvo_plugin.get_vim.return_value = vim_info
        self.service_plugins.get.return_value = self.nfvo_plugin

        def mock_barbican_resp(request, context):
            auth_value = 'Bearer %s' % self.access_token
            req_auth = request._request.headers.get('Authorization')
            self.assertEqual(auth_value, req_auth)
            response = {
                'name': 'AES key',
                'expiration': '2023-01-13T19:14:44.180394',
                'algorithm': 'aes',
                'bit_length': 256,
                'mode': 'cbc',
                'payload': 'YmVlcg==',
                'payload_content_type': 'application/octet-stream',
                'payload_content_encoding': 'base64'
            }
            context.status_code = 200
            return response
        self.requests_mock.get('http://demo/barbican/v1/secrets/%s' %
                               barbican_uuid,
                               json=mock_barbican_resp)

        def mock_barbican_payload_resp(request, context):
            auth_value = 'Bearer %s' % self.access_token
            req_auth = request._request.headers.get('Authorization')
            self.assertEqual(auth_value, req_auth)
            response = '5cJeztZKzISf1JAt73oBeTPPCrymn96A3wqG96F4RxU='
            context.status_code = 200
            return response

        def mock_get_barbican_resp(request, context):
            auth_value = 'Bearer %s' % self.access_token
            req_auth = request._request.headers.get('Authorization')
            self.assertEqual(auth_value, req_auth)
            context.status_code = 200
            response = {
                "versions": {
                    "values": [
                        {
                            "id": "v1",
                            "status": "stable",
                            "links": [
                                {
                                    "rel": "self",
                                    "href": "http://demo/barbican/v1/"
                                },
                                {
                                    "rel": "describedby",
                                    "type": "text/html",
                                    "href": "https://docs.openstack.org/"}
                            ],
                            "media-types": [
                                {
                                    "base": "application/json",
                                    "type": "application/"
                                            "vnd.openstack.key-manager-v1+json"
                                }
                            ]
                        }
                    ]
                }
            }
            return response

        self.requests_mock.get('http://demo/barbican/v1/secrets/%s/payload' %
                               barbican_uuid,
                               json=mock_barbican_payload_resp)
        self.requests_mock.get('http://demo/barbican',
                               json=mock_get_barbican_resp)
        mock_decrypt.return_value = 'test'.encode('utf-8')
        with mock.patch.object(manager.TackerManager, 'get_service_plugins',
                               return_value=self.service_plugins):
            self.vimclient.get_vim(None,
                                   vim_id=self.vim_info['id'],
                                   region_name='TestRegionOne')
