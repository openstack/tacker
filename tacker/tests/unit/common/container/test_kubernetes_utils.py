# Copyright (c) 2021 FUJITSU.
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

from cryptography import fernet
from kubernetes import client
from unittest import mock
from unittest import skip

from tacker.common.container import kubernetes_utils
from tacker.tests import base


class TestKubernetesHTTPAPI(base.BaseTestCase):

    def setUp(self):
        super(TestKubernetesHTTPAPI, self).setUp()
        self.kubernetes_http_api = kubernetes_utils.KubernetesHTTPAPI()

    # NOTE(Yao Qibin): This unit test will be executed after __init__.py
    # is added. And this unit test fails because the beta1 api is old
    # and deprecated. To avoid errors, comment out the following test code.
    @skip('Delete deprecated api test')
    def test_get_extension_api_client(self):
        auth = {"auth_url": "auth", 'bearer_token': 'token'}
        extensions_v1_beta1_api = \
            self.kubernetes_http_api.get_extension_api_client(auth)
        self.assertIsInstance(
            extensions_v1_beta1_api,
            client.api.extensions_v1beta1_api.ExtensionsV1beta1Api)

    def test_get_core_api_client(self):
        auth = {"auth_url": "auth", 'bearer_token': 'token'}
        extensions_v1_beta1_api = self.kubernetes_http_api.get_core_api_client(
            auth)
        self.assertIsInstance(extensions_v1_beta1_api,
                              client.api.core_api.CoreApi)

    def create_fernet_key(self):
        fernet_key, fernet_obj = self.kubernetes_http_api.create_fernet_key()
        self.assertEqual(len(fernet_key), 44)
        self.assertIsInstance(fernet_obj, fernet.Fernet)

    @mock.patch('tacker.common.oidc_utils.get_id_token_with_password_grant')
    def test_get_k8s_client_oidc_auth(self, mock_get_token):
        mock_get_token.return_value = 'id_token'

        auth_plugin = {
            'auth_url': 'auth_url',
            'oidc_token_url': 'oidc_token_url',
            'client_id': 'client_id',
            'client_secret': 'client_secret',
            'username': 'username',
            'password': 'password',
            'ca_cert_file': 'ca_cert_file'
        }
        k8s_client = self.kubernetes_http_api.get_k8s_client(auth_plugin)
        k8s_client_config = k8s_client.configuration
        self.assertEqual('auth_url', k8s_client_config.host)
        self.assertDictEqual({'authorization': 'Bearer'},
                             k8s_client_config.api_key_prefix)
        self.assertDictEqual({'authorization': 'id_token'},
                             k8s_client_config.api_key)
        self.assertEqual('ca_cert_file', k8s_client_config.ssl_ca_cert)
        self.assertTrue(k8s_client_config.verify_ssl)

    @mock.patch('tacker.common.oidc_utils.get_id_token_with_password_grant')
    def test_get_k8s_client_oidc_auth_no_cert(self, mock_get_token):
        mock_get_token.return_value = 'id_token'

        auth_plugin = {
            'auth_url': 'auth_url',
            'oidc_token_url': 'oidc_token_url',
            'client_id': 'client_id',
            'client_secret': 'client_secret',
            'username': 'username',
            'password': 'password'
        }
        k8s_client = self.kubernetes_http_api.get_k8s_client(auth_plugin)
        k8s_client_config = k8s_client.configuration
        self.assertEqual('auth_url', k8s_client_config.host)
        self.assertDictEqual({'authorization': 'Bearer'},
                             k8s_client_config.api_key_prefix)
        self.assertDictEqual({'authorization': 'id_token'},
                             k8s_client_config.api_key)
        self.assertFalse(k8s_client_config.verify_ssl)

    def test_get_k8s_client_oidc_auth_id_token_exsits(self):

        auth_plugin = {
            'auth_url': 'auth_url',
            'oidc_token_url': 'oidc_token_url',
            'client_id': 'client_id',
            'client_secret': 'client_secret',
            'username': 'username',
            'password': 'password',
            'ca_cert_file': 'ca_cert_file',
            'id_token': 'id_token'
        }
        k8s_client = self.kubernetes_http_api.get_k8s_client(auth_plugin)
        k8s_client_config = k8s_client.configuration
        self.assertEqual('auth_url', k8s_client_config.host)
        self.assertDictEqual({'authorization': 'Bearer'},
                             k8s_client_config.api_key_prefix)
        self.assertDictEqual({'authorization': 'id_token'},
                             k8s_client_config.api_key)
        self.assertEqual('ca_cert_file', k8s_client_config.ssl_ca_cert)
        self.assertTrue(k8s_client_config.verify_ssl)

    def test_get_k8s_client_service_account_token_auth(self):

        auth_plugin = {
            'auth_url': 'auth_url',
            'bearer_token': 'bearer_token'
        }
        k8s_client = self.kubernetes_http_api.get_k8s_client(auth_plugin)
        k8s_client_config = k8s_client.configuration
        self.assertEqual('auth_url', k8s_client_config.host)
        self.assertDictEqual({'authorization': 'Bearer'},
                             k8s_client_config.api_key_prefix)
        self.assertDictEqual({'authorization': 'bearer_token'},
                             k8s_client_config.api_key)
        self.assertFalse(k8s_client_config.verify_ssl)
