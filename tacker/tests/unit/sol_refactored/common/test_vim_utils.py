# Copyright (C) 2022 FUJITSU
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

from tacker import context
from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import vim_utils
from tacker.sol_refactored import objects
from tacker.tests import base
from tacker.vnfm import vim_client

_vim_openstack = {
    "placement_attr": {
        "regions": ['RegionOne']
    },
    "vim_auth": {
        "username": "nfv_user",
        "password": "devstack",
        "project_name": "nfv",
        "project_domain_name": "Default",
        "user_domain_name": "Default",
        "auth_url": "http://127.0.0.1/identity"
    },
    "vim_type": "openstack",
    "vim_id": "openstack-1"
}
_vim_kubernetes_bearer_token = {
    "placement_attr": {
        "regions": ['RegionOne']
    },
    "vim_auth": {
        "username": None,
        "password": None,
        "bearer_token": "test_token",
        "auth_url": "https://127.0.0.1:6443",
        "ssl_ca_cert": "test_ssl"
    },
    "vim_type": "kubernetes",
    "vim_id": "kubernetes-1"
}
_vim_kubernetes_user = {
    "vim_auth": {
        "username": "admin",
        "password": "admin",
        "auth_url": "https://127.0.0.1:6443"
    },
    "vim_type": "kubernetes",
    "vim_id": "kubernetes-2"
}
_vim_kubernetes_oidc = {
    "vim_auth": {
        "username": "admin",
        "password": "admin",
        "auth_url": "https://127.0.0.1:6443",
        "oidc_token_url": "https://127.0.0.1:8443",
        "client_id": "tacker",
        "client_secret": "K0Zp5dvdOFhZ7W9PVNZn14omW9NmCQvQ",
    },
    "vim_type": "kubernetes",
    "vim_id": "kubernetes-3"
}


class TestVimUtils(base.BaseTestCase):

    def setUp(self):
        super(TestVimUtils, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.context.api_version = api_version.APIVersion('2.0.0')

    @mock.patch.object(vim_client.VimClient, 'get_vim')
    def test_get_default_vim(self, mock_vim):
        mock_vim.return_value = _vim_openstack
        result = vim_utils.get_default_vim(context)

        self.assertEqual('openstack-1', result.vimId)

    @mock.patch.object(vim_client.VimClient, 'get_vim')
    def test_get_default_vim_error(self, mock_vim):
        mock_vim.return_value = Exception
        vim_utils.get_default_vim(context)

    @mock.patch.object(vim_client.VimClient, 'get_vim')
    def test_get_vim(self, mock_vim):
        mock_vim.return_value = _vim_kubernetes_bearer_token
        result = vim_utils.get_vim(context, 'kubernetes-1')

        self.assertEqual('kubernetes-1', result.vimId)

    @mock.patch.object(vim_client.VimClient, 'get_vim')
    def test_get_vim_error(self, mock_vim):
        mock_vim.return_value = Exception
        self.assertRaises(
            sol_ex.VimNotFound, vim_utils.get_vim, context, 'test')

    def test_vim_to_conn_info(self):
        vim_openstack = _vim_openstack
        vim_kubernetes_1 = _vim_kubernetes_bearer_token
        vim_kubernetes_2 = _vim_kubernetes_user
        vim_kubernetes_3 = _vim_kubernetes_oidc

        result_1 = vim_utils.vim_to_conn_info(vim_openstack)
        self.assertEqual('openstack-1', result_1.vimId)

        result_2 = vim_utils.vim_to_conn_info(vim_kubernetes_1)
        self.assertEqual('kubernetes-1', result_2.vimId)

        result_3 = vim_utils.vim_to_conn_info(vim_kubernetes_2)
        self.assertEqual('kubernetes-2', result_3.vimId)

        result_4 = vim_utils.vim_to_conn_info(vim_kubernetes_3)
        self.assertEqual('kubernetes-3', result_4.vimId)

        self.assertRaises(
            sol_ex.SolException, vim_utils.vim_to_conn_info,
            {'vim_type': 'test', 'vim_auth': 'test'})
