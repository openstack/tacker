# Copyright (C) 2022 Fujitsu
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

from oslo_config import cfg
import yaml

from tacker.sol_refactored.common import http_client
from tacker.sol_refactored import objects
from tacker.tests.functional.sol_kubernetes_v2 import base_v2
from tacker.tests import utils as base_utils
from tacker import version

VNF_PACKAGE_UPLOAD_TIMEOUT = 300
VNF_INSTANTIATE_TIMEOUT = 600
VNF_TERMINATE_TIMEOUT = 600
RETRY_WAIT_TIME = 5


class BaseVnfLcmKubernetesV2OidcTest(base_v2.BaseVnfLcmKubernetesV2Test):

    @classmethod
    def setUpClass(cls):
        super(base_v2.BaseVnfLcmKubernetesV2Test, cls).setUpClass()
        """Base test case class for SOL v2 kubernetes Oidc functional tests."""

        cfg.CONF(args=['--config-file', '/etc/tacker/tacker.conf'],
                 project='tacker',
                 version='%%prog %s' % version.version_info.release_string())
        objects.register_all()

        cls.k8s_vim_info = cls.get_k8s_vim_info()

        vim_info = cls.get_vim_info()
        auth = http_client.KeystonePasswordAuthHandle(
            auth_url=vim_info.interfaceInfo['endpoint'],
            username=vim_info.accessInfo['username'],
            password=vim_info.accessInfo['password'],
            project_name=vim_info.accessInfo['project'],
            user_domain_name=vim_info.accessInfo['userDomain'],
            project_domain_name=vim_info.accessInfo['projectDomain']
        )
        cls.tacker_client = http_client.HttpClient(auth)

    @classmethod
    def tearDownClass(cls):
        super(base_v2.BaseVnfLcmKubernetesV2Test, cls).tearDownClass()

    @classmethod
    def get_k8s_vim_info(cls):
        vim_params = yaml.safe_load(
            base_utils.read_file('local-k8s-vim-oidc.yaml'))

        vim_info = objects.VimConnectionInfo(
            interfaceInfo={'endpoint': vim_params['auth_url']},
            accessInfo={
                'oidc_token_url': vim_params['oidc_token_url'],
                'username': vim_params['username'],
                'password': vim_params['password'],
                'client_id': vim_params['client_id'],
            }
        )
        # if ssl_ca_cert is set, add it to vim_info.interfaceInfo
        if vim_params.get('ssl_ca_cert'):
            vim_info.interfaceInfo['ssl_ca_cert'] = vim_params['ssl_ca_cert']
        # if client_secret is set, add it to vim_info.accessInfo
        if vim_params.get('client_secret'):
            vim_info.accessInfo['client_secret'] = vim_params['client_secret']

        return vim_info

    @classmethod
    def get_k8s_vim_id(cls):
        vim_list = cls.list_vims(cls)
        if len(vim_list.values()) == 0:
            assert False, "vim_list is Empty: Default VIM is missing"

        for vim_list in vim_list.values():
            for vim in vim_list:
                if vim['name'] == 'vim-kubernetes-oidc':
                    return vim['id']
        return None
