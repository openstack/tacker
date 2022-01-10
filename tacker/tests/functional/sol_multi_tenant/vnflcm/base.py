#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import os

from tacker.tests.functional import base
from tacker.tests.functional.common.fake_server import FakeServerManager
from tacker.tests.functional.sol.vnflcm import base as vnflcm_base


FAKE_SERVER_MANAGER_T1 = FakeServerManager()
FAKE_SERVER_PORT_T1 = 9995
FAKE_SERVER_MANAGER_T2 = FakeServerManager()
FAKE_SERVER_PORT_T2 = 9996


class BaseVnfLcmMultiTenantTest(vnflcm_base.BaseVnfLcmTest):

    prepare_fake_server = False

    @classmethod
    def setUpClass(cls):
        super(BaseVnfLcmMultiTenantTest, cls).setUpClass()

        result = cls.get_openstack_client_session(
            vim_conf_file='local-tenant1-vim.yaml')
        cls.client_tenant1 = result.get('client')
        cls.http_client_tenant1 = result.get('http_client')
        cls.h_client_tenant1 = result.get('h_client')
        cls.glance_client_tenant1 = result.get('glance_client')

        result = cls.get_openstack_client_session(
            vim_conf_file='local-tenant2-vim.yaml')
        cls.client_tenant2 = result.get('client')
        cls.http_client_tenant2 = result.get('http_client')
        cls.h_client_tenant2 = result.get('h_client')
        cls.glance_client_tenant2 = result.get('glance_client')

        cls.tacker_client_t1 = base.BaseTackerTest.tacker_http_client(
            'local-tenant1-vim.yaml')
        cls.tacker_client_t2 = base.BaseTackerTest.tacker_http_client(
            'local-tenant2-vim.yaml')

        # Set up fake NFVO server for tenant1 and tenant2
        cls.servers = {FAKE_SERVER_PORT_T1: FAKE_SERVER_MANAGER_T1,
                       FAKE_SERVER_PORT_T2: FAKE_SERVER_MANAGER_T2}
        # NOTE: Create both server in parallel, otherwise they can
        # cause (especially server start) job timeout.
        for port, manager in cls.servers.items():
            cls._prepare_start_fake_server(manager, port)

    @classmethod
    def tearDownClass(cls):
        super(BaseVnfLcmMultiTenantTest, cls).tearDownClass()
        for _, manager in cls.servers.items():
            manager.stop_server()

    def setUp(self):
        super(BaseVnfLcmMultiTenantTest, self).setUp()
        self.base_url = "/vnfpkgm/v1/vnf_packages"

        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        self._clear_history_and_set_callback(FAKE_SERVER_MANAGER_T1,
            callback_url)
        self._clear_history_and_set_callback(FAKE_SERVER_MANAGER_T2,
            callback_url)

        vim_list = self.client.list_vims()
        self.vim_tenant1 = self.get_vim(vim_list, 'VIM_TEST')
        if not self.vim_tenant1:
            assert False, "vim_list is Empty: Tenant VIM is missing"
        self.vim_tenant2 = self.get_vim(vim_list, 'VIM_DEMO')
        if not self.vim_tenant2:
            assert False, "vim_list is Empty: Tenant VIM is missing"

        result = self._create_network_settings()
        self.ext_networks_tenant1 = result.get('ext_networks')
        self.ext_vl_tenant1 = result.get('ext_vl')
        self.ext_mngd_networks_tenant1 = result.get('ext_mngd_networks')
        self.ext_link_ports_tenant1 = result.get('ext_link_ports')
        self.ext_subnets_tenant1 = result.get('ext_subnets')
        self.changed_ext_networks_tenant1 = result.get(
            'changed_ext_networks')
        self.changed_ext_subnets_tenant1 = result.get(
            'changed_ext_subnets')

        result = self._create_network_settings()
        self.ext_networks_tenant2 = result.get('ext_networks')
        self.ext_vl_tenant2 = result.get('ext_vl')
        self.ext_mngd_networks_tenant2 = result.get('ext_mngd_networks')
        self.ext_link_ports_tenant2 = result.get('ext_link_ports')
        self.ext_subnets_tenant2 = result.get('ext_subnets')
        self.changed_ext_networks_tenant2 = result.get(
            'changed_ext_networks')
        self.changed_ext_subnets_tenant2 = result.get(
            'changed_ext_subnets')

    @classmethod
    def get_openstack_client_session(cls, vim_conf_file):
        client = base.BaseTackerTest.tackerclient(vim_conf_file)
        http_client = base.BaseTackerTest.tacker_http_client(vim_conf_file)
        h_client = base.BaseTackerTest.heatclient(vim_conf_file)
        glance_client = base.BaseTackerTest.glanceclient(vim_conf_file)
        return {'client': client,
                'http_client': http_client,
                'h_client': h_client,
                'glance_client': glance_client}
