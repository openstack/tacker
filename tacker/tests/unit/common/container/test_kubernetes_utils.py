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

import cryptography.fernet as fernet
from kubernetes import client

from tacker.common.container import kubernetes_utils
from tacker.tests import base


class TestKubernetesHTTPAPI(base.BaseTestCase):

    def setUp(self):
        super(TestKubernetesHTTPAPI, self).setUp()
        self.kubernetes_http_api = kubernetes_utils.KubernetesHTTPAPI()

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
