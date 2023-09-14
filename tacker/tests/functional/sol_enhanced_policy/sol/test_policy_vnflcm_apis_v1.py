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

from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from tacker.tests.functional.sol.vnflcm import fake_vnflcm
from tacker.tests.functional.sol.vnflcm.test_vnf_instance import (
    get_external_virtual_links)
from tacker.tests.functional.sol_enhanced_policy.base import (
    VnflcmAPIsV1Base)


class VnflcmAPIsV1Test(VnflcmAPIsV1Base):

    user_role_map = {
        'user_a': ['VENDOR_company_A', 'AREA_area_A@region_A',
                   'TENANT_tenant_A', 'manager'],
        'user_a_1': ['VENDOR_company_A', 'manager'],
        'user_b': ['VENDOR_company_B', 'AREA_area_B@region_B',
                   'TENANT_tenant_B', 'manager'],
        'user_c': ['VENDOR_company_C', 'AREA_area_C@region_C',
                   'TENANT_tenant_C', 'manager'],
        'user_all': ['VENDOR_all', 'AREA_all@all',
                     'TENANT_all', 'manager'],
        'user_admin': ['admin']
    }
    vim_user_project_map = {
        'user_a': 'tenant_A',
        'user_b': 'tenant_B',
        'user_c': 'tenant_C'
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.create_vim_user()

        vim_type = 'openstack'

        local_vim = 'local-vim.yaml'

        cls.vim_a = cls._step_vim_register(
            'user_a', vim_type, local_vim, 'vim_a', 'area_A@region_A',
            tenant='tenant_A')

        cls.vim_a_1 = cls._step_vim_register(
            'user_a', vim_type, local_vim, 'vim_a_1', 'area_A@region_A',
            tenant='tenant_A')

        cls.vim_b = cls._step_vim_register(
            'user_b', vim_type, local_vim, 'vim_b', 'area_B@region_B',
            tenant='tenant_B')

        cls.vim_b_1 = cls._step_vim_register(
            'user_b', vim_type, local_vim, 'vim_b_1', 'area_B@region_B',
            tenant='tenant_B')

        cls.vim_c = cls._step_vim_register(
            'user_c', vim_type, local_vim, 'vim_c', None,
            tenant='tenant_C')

        cls.vim_c_1 = cls._step_vim_register(
            'user_c', vim_type, local_vim, 'vim_c_1', None,
            tenant='tenant_C')

        cls.pkg_a = cls._step_pkg_create('user_a')

        cls.vnfd_id_a = cls._step_pkg_upload_content(
            'user_a', cls.pkg_a, 'test_enhanced_policy', 'company_A')

        cls.pkg_b = cls._step_pkg_create('user_b')

        cls.vnfd_id_b = cls._step_pkg_upload_content(
            'user_b', cls.pkg_b, 'test_enhanced_policy', 'company_B')

        cls.pkg_c = cls._step_pkg_create('user_c')

        cls.vnfd_id_c = cls._step_pkg_upload_content(
            'user_c', cls.pkg_c, 'test_enhanced_policy', 'company_C')

    @classmethod
    def tearDownClass(cls):

        cls._step_pkg_disable('user_a', cls.pkg_a,)
        cls._step_pkg_disable('user_b', cls.pkg_b,)
        cls._step_pkg_disable('user_c', cls.pkg_c,)
        cls._step_pkg_delete('user_a', cls.pkg_a)
        cls._step_pkg_delete('user_b', cls.pkg_b)
        cls._step_pkg_delete('user_c', cls.pkg_c)

        cls._step_vim_delete('user_a', cls.vim_a)
        cls._step_vim_delete('user_a', cls.vim_a_1)
        cls._step_vim_delete('user_b', cls.vim_b)
        cls._step_vim_delete('user_b', cls.vim_b_1)
        cls._step_vim_delete('user_admin', cls.vim_c)
        cls._step_vim_delete('user_admin', cls.vim_c_1)

        super().tearDownClass()

    def _instantiate_vnf_request(self, flavour_id,
            instantiation_level_id=None, vim_id=None, ext_vl=None,
            ext_managed_vl=None):
        request_body = {
            "flavourId": flavour_id,
            "additionalParams": {
                "lcm-operation-user-data": "./UserData/lcm_user_data.py",
                "lcm-operation-user-data-class": "SampleUserData"
            }
        }

        if instantiation_level_id:
            request_body["instantiationLevelId"] = instantiation_level_id

        if ext_managed_vl:
            request_body["extManagedVirtualLinks"] = ext_managed_vl

        if ext_vl:
            request_body["extVirtualLinks"] = ext_vl

        if vim_id:
            request_body["vimConnectionInfo"] = [
                {"id": uuidutils.generate_uuid(),
                 "vimId": vim_id,
                 "vimType": "ETSINFV.OPENSTACK_KEYSTONE.v_2"}]

        return request_body

    def _step_lcm_instantiate(
            self, username, inst_id, vim_id, expected_status_code):
        neutron_client = self.neutronclient()
        net = neutron_client.list_networks()
        networks = {}
        for network in net['networks']:
            networks[network['name']] = network['id']
        net0_id = networks.get('net0')
        if not net0_id:
            self.fail("net0 network is not available")
        net_mgmt_id = networks.get('net_mgmt')
        if not net_mgmt_id:
            self.fail("net_mgmt network is not available")
        network_uuid = self.create_network(neutron_client,
            "external_network")
        port_uuid = self.create_port(neutron_client, network_uuid)
        ext_vl = get_external_virtual_links(net0_id, net_mgmt_id,
                                            port_uuid)
        self.create_image()
        request_body = self._instantiate_vnf_request(
            "simple", vim_id=vim_id, ext_vl=ext_vl)

        self._lcm_instantiate(
            username, inst_id, request_body, expected_status_code)

    def _step_lcm_scale_out(self, username, inst_id, expected_status_code):
        request_body = fake_vnflcm.VnfInstances.make_scale_request_body(
            'SCALE_OUT')
        self._step_lcm_scale(
            username, inst_id, request_body, expected_status_code)

    def _step_lcm_scale_in(self, username, inst_id, expected_status_code):
        request_body = fake_vnflcm.VnfInstances.make_scale_request_body(
            'SCALE_IN')
        self._step_lcm_scale(
            username, inst_id, request_body, expected_status_code)

    def _change_ext_conn_vnf_request(self, vim_id=None, ext_vl=None,
                                    vim_type="ETSINFV.OPENSTACK_KEYSTONE.v_2"):
        request_body = {}
        if ext_vl:
            request_body["extVirtualLinks"] = ext_vl

        if vim_id:
            request_body["vimConnectionInfo"] = [
                {"id": uuidutils.generate_uuid(),
                 "vimId": vim_id,
                 "vimType": vim_type}]

        return request_body

    def _step_lcm_change_connectivity(self, username, inst_id, new_vim_id,
                                      expected_status_code):
        client = self.get_tk_http_client_by_user(username)

        neutron_client = self.neutronclient()
        net = neutron_client.list_networks()
        networks = {}
        for network in net['networks']:
            networks[network['name']] = network['id']
        net0_id = networks.get('net0')
        if not net0_id:
            self.fail("net0 network is not available")
        net_mgmt_id = networks.get('net_mgmt')
        if not net_mgmt_id:
            self.fail("net_mgmt network is not available")
        network_uuid = self.create_network(neutron_client,
                                           "external_network")
        port_uuid = self.create_port(neutron_client, network_uuid)
        ext_vl = get_external_virtual_links(net0_id, net_mgmt_id,
                                            port_uuid)
        change_ext_conn_req_body = self._change_ext_conn_vnf_request(
            vim_id=new_vim_id, ext_vl=ext_vl)
        url = os.path.join(
            self.base_vnf_instances_url,
            inst_id,
            "change_ext_conn")
        resp, body = client.do_request(url, "POST",
                                body=jsonutils.dumps(change_ext_conn_req_body))
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            self._wait_lcm_done(
                operation='CHANGE_EXT_CONN',
                expected_operation_status='COMPLETED',
                vnf_instance_id=inst_id)

    def test_vnflcm_apis_vnf_instance_with_area_vnf(self):
        self.register_subscription()

        inst_id_a, inst_id_b = self.steps_lcm_create_and_get_with_area()

        # step 12 LCM-Instantiate, Resource Group A / User Group A
        self._step_lcm_instantiate('user_a', inst_id_a, self.vim_a['id'], 202)

        # step 13 LCM-Instantiate, Resource Group B / User Group A
        self._step_lcm_instantiate('user_a', inst_id_b, self.vim_b['id'], 403)

        # step 14 LCM-Instantiate, Resource Group B / User Group all
        self._step_lcm_instantiate(
            'user_all', inst_id_b, self.vim_b['id'], 202)

        self.steps_lcm_get_scale_heal_modify_with_area(inst_id_a, inst_id_b)

        # step 34 LCM-Change-Connectivity, Resource Group A / User Group A
        self._step_lcm_change_connectivity(
            'user_a', inst_id_a, self.vim_a_1['id'], 202)

        # step 35 LCM-Change-Connectivity, Resource Group B / User Group A
        self._step_lcm_change_connectivity(
            'user_a', inst_id_b, self.vim_b_1['id'], 403)

        # step 36 LCM-Change-Connectivity, Resource Group B / User Group all
        self._step_lcm_change_connectivity(
            'user_all', inst_id_b, self.vim_b_1['id'], 202)

        self.steps_lcm_terminate_delete_with_area(inst_id_a, inst_id_b)

    def test_vnflcm_apis_vnf_instance_without_area_vnf(self):
        self.register_subscription()

        inst_id_c = self.steps_lcm_create_and_get_without_area()

        # step 8 LCM-Instantiate, Resource Group C / User Group C
        self._step_lcm_instantiate('user_c', inst_id_c, self.vim_c['id'], 202)

        self.steps_lcm_get_scale_heal_modify_without_area(inst_id_c)

        # step 27 LCM-Change-Connectivity, Resource Group C / User Group C
        self._step_lcm_change_connectivity(
            'user_c', inst_id_c, self.vim_c_1['id'], 403)

        # step 28 LCM-Change-Connectivity, Resource Group C / User Group all
        self._step_lcm_change_connectivity(
            'user_all', inst_id_c, self.vim_c_1['id'], 403)

        # step 29 LCM-Change-Connectivity, Resource Group C / User Group admin
        self._step_lcm_change_connectivity(
            'user_admin', inst_id_c, self.vim_c_1['id'], 202)

        self.steps_lcm_terminate_delete_without_area(inst_id_c)
