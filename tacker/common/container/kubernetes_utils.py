# All Rights Reserved.
#
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

import os
import re
import six
import tempfile

from cryptography import fernet
from kubernetes import client
from kubernetes.client import api_client
from oslo_config import cfg
from oslo_log import log as logging

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class KubernetesHTTPAPI(object):

    def get_k8s_client(self, auth_plugin):
        config = client.Configuration()
        config.host = auth_plugin['auth_url']
        if ('username' in auth_plugin) and ('password' in auth_plugin)\
                and (auth_plugin['password'] is not None):
            config.username = auth_plugin['username']
            config.password = auth_plugin['password']
            basic_token = config.get_basic_auth_token()
            config.api_key['authorization'] = basic_token
        if 'bearer_token' in auth_plugin:
            config.api_key_prefix['authorization'] = 'Bearer'
            config.api_key['authorization'] = auth_plugin['bearer_token']
        ca_cert_file = auth_plugin.get('ca_cert_file')
        if ca_cert_file is not None:
            config.ssl_ca_cert = ca_cert_file
            config.verify_ssl = True
        else:
            config.verify_ssl = False
        k8s_client = api_client.ApiClient(configuration=config)
        return k8s_client

    def get_k8s_client_dict(self, auth):
        k8s_client_dict = {
            'v1': self.get_core_v1_api_client(auth),
            'apiregistration.k8s.io/v1':
            self.get_api_registration_v1_api_client(auth),
            'apps/v1': self.get_app_v1_api_client(auth),
            'authentication.k8s.io/v1':
            self.get_authentication_v1_api_client(auth),
            'authorization.k8s.io/v1':
            self.get_authorization_v1_api_client(auth),
            'autoscaling/v1': self.get_scaling_api_client(auth),
            'batch/v1': self.get_batch_v1_api_client(auth),
            'coordination.k8s.io/v1':
            self.get_coordination_v1_api_client(auth),
            'networking.k8s.io/v1':
            self.get_networking_v1_api_client(auth),
            'rbac.authorization.k8s.io/v1':
            self.get_rbac_authorization_v1_api_client(auth),
            'scheduling.k8s.io/v1':
            self.get_scheduling_v1_api_client(auth),
            'storage.k8s.io/v1':
            self.get_storage_v1_api_client(auth)
        }
        return k8s_client_dict

    def get_extension_api_client(self, auth):
        k8s_client = self.get_k8s_client(auth_plugin=auth)
        return client.ExtensionsV1beta1Api(api_client=k8s_client)

    def get_core_v1_api_client(self, auth):
        k8s_client = self.get_k8s_client(auth_plugin=auth)
        return client.CoreV1Api(api_client=k8s_client)

    def get_core_api_client(self, auth):
        k8s_client = self.get_k8s_client(auth_plugin=auth)
        return client.CoreApi(api_client=k8s_client)

    def get_scaling_api_client(self, auth):
        k8s_client = self.get_k8s_client(auth_plugin=auth)
        return client.AutoscalingV1Api(api_client=k8s_client)

    def get_app_v1_api_client(self, auth):
        k8s_client = self.get_k8s_client(auth_plugin=auth)
        return client.AppsV1Api(api_client=k8s_client)

    def get_api_registration_v1_api_client(self, auth):
        k8s_client = self.get_k8s_client(auth_plugin=auth)
        return client.ApiregistrationV1Api(api_client=k8s_client)

    def get_authentication_v1_api_client(self, auth):
        k8s_client = self.get_k8s_client(auth_plugin=auth)
        return client.AuthenticationV1Api(api_client=k8s_client)

    def get_authorization_v1_api_client(self, auth):
        k8s_client = self.get_k8s_client(auth_plugin=auth)
        return client.AuthorizationV1Api(api_client=k8s_client)

    def get_batch_v1_api_client(self, auth):
        k8s_client = self.get_k8s_client(auth_plugin=auth)
        return client.BatchV1Api(api_client=k8s_client)

    def get_coordination_v1_api_client(self, auth):
        k8s_client = self.get_k8s_client(auth_plugin=auth)
        return client.CoordinationV1Api(api_client=k8s_client)

    def get_networking_v1_api_client(self, auth):
        k8s_client = self.get_k8s_client(auth_plugin=auth)
        return client.NetworkingV1Api(api_client=k8s_client)

    def get_rbac_authorization_v1_api_client(self, auth):
        k8s_client = self.get_k8s_client(auth_plugin=auth)
        return client.RbacAuthorizationV1Api(api_client=k8s_client)

    def get_scheduling_v1_api_client(self, auth):
        k8s_client = self.get_k8s_client(auth_plugin=auth)
        return client.SchedulingV1Api(api_client=k8s_client)

    def get_storage_v1_api_client(self, auth):
        k8s_client = self.get_k8s_client(auth_plugin=auth)
        return client.StorageV1Api(api_client=k8s_client)

    @staticmethod
    def create_ca_cert_tmp_file(ca_cert):
        file_descriptor, file_path = tempfile.mkstemp()
        ca_cert = re.sub(r'\s', '\n', ca_cert)
        ca_cert = re.sub(r'BEGIN\nCERT', r'BEGIN CERT', ca_cert)
        ca_cert = re.sub(r'END\nCERT', r'END CERT', ca_cert)
        try:
            with open(file_path, 'w') as f:
                if six.PY2:
                    f.write(ca_cert.decode('utf-8'))
                else:
                    f.write(ca_cert)
                LOG.debug('ca cert temp file successfully stored in %s',
                          file_path)
        except IOError:
            raise Exception('Failed to create %s file', file_path)
        return file_descriptor, file_path

    @staticmethod
    def close_tmp_file(file_descriptor, file_path):
        os.close(file_descriptor)
        os.remove(file_path)

    def create_fernet_key(self):
        fernet_key = fernet.Fernet.generate_key()
        fernet_obj = fernet.Fernet(fernet_key)
        return fernet_key, fernet_obj
