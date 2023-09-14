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

from oslo_utils import uuidutils

from tacker import context
from tacker.tests.functional.sol_enhanced_policy.base import (
    VnflcmAPIsV1Base)


class VnflcmAPIsV1CNFTest(VnflcmAPIsV1Base):

    user_role_map = {
        'user_a': ['VENDOR_company_A', 'AREA_area_A@region_A',
                   'TENANT_namespace-a', 'manager'],
        'user_a_1': ['VENDOR_company_A', 'manager'],
        'user_b': ['VENDOR_company_B', 'AREA_area_B@region_B',
                   'TENANT_namespace-b', 'manager'],
        'user_c': ['VENDOR_company_C', 'AREA_area_C@region_C',
                   'TENANT_namespace-c', 'manager'],
        'user_all': ['VENDOR_all', 'AREA_all@all', 'TENANT_all', 'manager'],
        'user_admin': ['admin']
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.client = cls.tackerclient(cls.local_vim_conf_file)

        # In the setUp of the parent class, it will be confirmed whether there
        # is a default vim named "VIM0". Here, it is confirmed in advance. If
        # it does not exist, it will be created to avoid the parent class
        # throwing an exception.
        cls.if_not_vim_create()

        local_k8s_vim = 'local-k8s-vim.yaml'
        vim_type = 'kubernetes'

        cls.vim_a = cls._step_vim_register(
            'user_a', vim_type, local_k8s_vim, 'vim_a', 'area_A@region_A')

        cls.vim_a_1 = cls._step_vim_register(
            'user_a', vim_type, local_k8s_vim, 'vim_a_1', 'area_A@region_A')

        cls.vim_b = cls._step_vim_register(
            'user_b', vim_type, local_k8s_vim, 'vim_b', 'area_B@region_B')

        cls.vim_b_1 = cls._step_vim_register(
            'user_b', vim_type, local_k8s_vim, 'vim_b_1', 'area_B@region_B')

        cls.vim_c = cls._step_vim_register(
            'user_c', vim_type, local_k8s_vim, 'vim_c', None)

        cls.vim_c_1 = cls._step_vim_register(
            'user_c', vim_type, local_k8s_vim, 'vim_c_1', None)

        cls.pkg_a = cls._step_pkg_create('user_a')

        cls.vnfd_id_a = cls._step_pkg_upload_content(
            'user_a', cls.pkg_a, 'test_cnf', 'company_A',
            namespace='namespace-a')

        cls.pkg_b = cls._step_pkg_create('user_b')

        cls.vnfd_id_b = cls._step_pkg_upload_content(
            'user_b', cls.pkg_b, 'test_cnf', 'company_B',
            namespace='namespace-b')

        cls.pkg_c = cls._step_pkg_create('user_c')

        cls.vnfd_id_c = cls._step_pkg_upload_content(
            'user_c', cls.pkg_c, 'test_cnf', 'company_C',
            namespace='namespace-c')

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

    @classmethod
    def get_vim(cls, vim_list, vim_name):
        if len(vim_list.values()) == 0:
            assert False, "vim_list is Empty: Default VIM is missing"

        for vim_list in vim_list.values():
            for vim in vim_list:
                if vim['name'] == vim_name:
                    return vim
        return None

    @classmethod
    def if_not_vim_create(cls):
        cls.context = context.get_admin_context()
        vim_list = cls.client.list_vims()
        vim_name = 'VIM0'
        if not vim_list:
            cls.vim_k8s = cls._step_vim_register(
                'user_all', 'kubernetes', 'local-k8s-vim.yaml',
                vim_name, None)

        vim = cls.get_vim(vim_list, vim_name)
        if not vim:

            vim_k8s = cls._step_vim_register(
                'user_all', 'kubernetes', 'local-k8s-vim.yaml',
                vim_name, None)

            cls.vim_k8s_id = vim_k8s.get('id')
        else:
            cls.vim_k8s_id = vim.get('id')

    @classmethod
    def _instantiate_vnf_instance_request(
            cls, flavour_id, vim_id=None, additional_param=None,
            extra_param=None):
        request_body = {"flavourId": flavour_id}

        if vim_id:
            request_body["vimConnectionInfo"] = [
                {"id": uuidutils.generate_uuid(),
                 "vimId": vim_id,
                 "vimType": "kubernetes"}]

            if extra_param:
                request_body["vimConnectionInfo"][0]["extra"] = extra_param

        if additional_param:
            request_body["additionalParams"] = additional_param

        return request_body

    def _step_lcm_instantiate(self, username, inst_id, vim_id, namespace,
                              expected_status_code):
        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/deployment.yaml",
                "Files/kubernetes/namespace.yaml"
            ],
            "namespace": namespace
        }
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id, additional_param=additional_param)
        self._lcm_instantiate(
            username, inst_id, request_body, expected_status_code)

    def _step_lcm_scale_out(self, username, inst_id, expected_status_code):
        scale_out_req = {
            "type": "SCALE_OUT",
            "aspectId": "vdu2_aspect",
            "numberOfSteps": 1
        }
        self._step_lcm_scale(
            username, inst_id, scale_out_req, expected_status_code)

    def _step_lcm_scale_in(self, username, inst_id, expected_status_code):
        scale_in_req = {
            "type": "SCALE_IN",
            "aspectId": "vdu2_aspect",
            "numberOfSteps": 1
        }
        self._step_lcm_scale(
            username, inst_id, scale_in_req, expected_status_code)

    def test_vnflcm_apis_vnf_instance_with_area_cnf(self):

        self.register_subscription()

        inst_id_a, inst_id_b = self.steps_lcm_create_and_get_with_area()

        # step 12 LCM-Instantiate, Resource Group A / User Group A
        self._step_lcm_instantiate(
            'user_a', inst_id_a, self.vim_a['id'], 'namespace-a', 202)

        # step 13 LCM-Instantiate, Resource Group B / User Group A
        self._step_lcm_instantiate(
            'user_a', inst_id_b, self.vim_b['id'], 'namespace-b', 403)

        # step 14 LCM-Instantiate, Resource Group B / User Group all
        self._step_lcm_instantiate(
            'user_all', inst_id_b, self.vim_b['id'], 'namespace-b', 202)

        self.steps_lcm_get_scale_heal_modify_with_area(inst_id_a, inst_id_b)

        # NOTE: CNF has no LCM-Change-Connectivity
        # step 34 LCM-Change-Connectivity, Resource Group A / User Group A
        # step 35 LCM-Change-Connectivity, Resource Group b / User Group A
        # step 36 LCM-Change-Connectivity, Resource Group B / User Group all

        self.steps_lcm_terminate_delete_with_area(inst_id_a, inst_id_b)

    def test_vnflcm_apis_vnf_instance_without_area_cnf(self):

        self.register_subscription()

        inst_id_c = self.steps_lcm_create_and_get_without_area()

        # step 8 LCM-Instantiate, Resource Group C / User Group C
        self._step_lcm_instantiate(
            'user_c', inst_id_c, self.vim_c['id'], 'namespace-c', 202)

        self.steps_lcm_get_scale_heal_modify_without_area(inst_id_c)

        # NOTE: CNF has no LCM-Change-Connectivity
        # step 27 LCM-Change-Connectivity, Resource Group C / User Group C
        # step 28 LCM-Change-Connectivity, Resource Group C / User Group all
        # step 29 LCM-Change-Connectivity, Resource Group C / User Group admin

        self.steps_lcm_terminate_delete_without_area(inst_id_c)
