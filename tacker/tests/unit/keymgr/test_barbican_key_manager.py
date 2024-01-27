# Copyright (C) 2023 Fujitsu
# All Rights Reserved.
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

from unittest import mock
import uuid

from oslo_config import cfg
from requests_mock.contrib import fixture as rm_fixture

from tacker import context as t_context
from tacker.keymgr.barbican_key_manager import BarbicanKeyManager
from tacker.keymgr import exception
from tacker.tests.unit import base


def get_mock_conf_key_effect(barbican_endpoint=None):
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
                'barbican_endpoint': barbican_endpoint
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
        if not self.conf and name not in self.conf:
            raise cfg.NoSuchOptError(f'not found {name}')
        return self.conf.get(name)

    def __contains__(self, key):
        return key in self.conf


class TestBarbicanKeyManager(base.TestCase):

    def setUp(self):
        super(TestBarbicanKeyManager, self).setUp()
        self.requests_mock = self.useFixture(rm_fixture.Fixture())
        self.token_endpoint = 'http://demo/token_endpoint'
        self.auth_method = 'client_secret_post'
        self.client_id = 'test_client_id'
        self.client_secret = 'test_client_secret'
        self.scope = 'tacker_api'
        self.access_token = f'access_token_{str(uuid.uuid4())}'
        self.audience = 'http://demo/audience'
        self.jwt_bearer_time_out = 2800
        self.addCleanup(mock.patch.stopall)

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

    def _mock_barbican_get_version_resp(self):
        def mock_barbican_get_resp(request, context):
            auth_value = f'Bearer {self.access_token}'
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
        return mock_barbican_get_resp

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    @mock.patch('barbicanclient.base.validate_ref_and_return_uuid')
    def test_delete_ext_oauth2_auth(self, mock_validate, mock_get_conf_key):
        mock_get_conf_key.side_effect = get_mock_conf_key_effect(
            barbican_endpoint='http://demo/barbican/')
        self._mock_external_token_api()
        mock_validate.return_value = True

        def mock_barbican_delete_resp(request, context):
            auth_value = f'Bearer {self.access_token}'
            req_auth = request._request.headers.get('Authorization')
            self.assertEqual(auth_value, req_auth)
            context.status_code = 204
            return ''

        def mock_barbican_get_for_check_resp(request, context):
            auth_value = f'Bearer {self.access_token}'
            req_auth = request._request.headers.get('Authorization')
            self.assertEqual(auth_value, req_auth)
            context.status_code = 200
            return {}

        self.requests_mock.get(
            'http://demo/barbican',
            json=self._mock_barbican_get_version_resp())

        self.requests_mock.delete(
            'http://demo/barbican/v1/secrets/True',
            json=mock_barbican_delete_resp)

        self.requests_mock.get(
            'http://demo/barbican/v1/secrets/True',
            json=mock_barbican_get_for_check_resp)

        auth = t_context.generate_tacker_service_context()
        keymgr = BarbicanKeyManager(auth.token_endpoint)
        keymgr.delete(auth, 'test')

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    @mock.patch('tacker.keymgr.barbican_key_manager.'
                'BarbicanKeyManager._retrieve_secret_uuid')
    def test_store_ext_oauth2_auth(self, mock_secret_uuid,
                                   mock_get_conf_key):
        mock_get_conf_key.side_effect = get_mock_conf_key_effect(
            barbican_endpoint='http://demo/barbican')
        secret_id = 'store_secret_uuid'
        mock_secret_uuid.return_value = secret_id
        self._mock_external_token_api()

        def mock_barbican_post_resp(request, context):
            auth_value = f'Bearer {self.access_token}'
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
            context.status_code = 201
            return response

        self.requests_mock.get(
            'http://demo/barbican',
            json=self._mock_barbican_get_version_resp())

        self.requests_mock.post('http://demo/barbican/v1/secrets/',
                                json=mock_barbican_post_resp)

        auth = t_context.generate_tacker_service_context()
        keymgr = BarbicanKeyManager(auth.token_endpoint)
        result = keymgr.store(auth, 'test')
        self.assertEqual(result, secret_id)

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    @mock.patch('barbicanclient.base.validate_ref_and_return_uuid')
    def test_get_ext_oauth2_auth(self, mock_validate, mock_get_conf_key):
        mock_get_conf_key.side_effect = get_mock_conf_key_effect(
            barbican_endpoint='http://demo/barbican/')
        self._mock_external_token_api()
        mock_validate.return_value = True

        def mock_barbican_get_resp(request, context):
            auth_value = f'Bearer {self.access_token}'
            req_auth = request._request.headers.get('Authorization')
            self.assertEqual(auth_value, req_auth)
            context.status_code = 200
            response = {
                'id': 'test001'
            }
            return response

        self.requests_mock.get(
            'http://demo/barbican',
            json=self._mock_barbican_get_version_resp())
        self.requests_mock.get(
            'http://demo/barbican/v1/secrets/True',
            json=mock_barbican_get_resp)

        auth = t_context.generate_tacker_service_context()
        keymgr = BarbicanKeyManager(auth.token_endpoint)
        result = keymgr.get(auth, 'test001')
        self.assertEqual(result.secret_ref,
                         'http://demo/barbican/v1/secrets/test001')

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_get_ext_oauth2_auth_no_endpoint(self, mock_get_conf_key):
        mock_get_conf_key.side_effect = get_mock_conf_key_effect(
            barbican_endpoint='')
        self._mock_external_token_api()
        auth = t_context.generate_tacker_service_context()
        keymgr = BarbicanKeyManager(auth.token_endpoint)
        self.assertRaises(exception.KeyManagerError, keymgr.get, auth, 'test')
