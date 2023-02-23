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

from tacker.tests.functional.sol_kubernetes.vnflcm import base


class VnfLcmKubernetesOidcTest(base.BaseVnfLcmKubernetesTest):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmKubernetesOidcTest, cls).setUpClass()
        vnf_package_id, cls.vnfd_id = \
            cls._create_and_upload_vnf_package(
                cls, cls.tacker_client, "test_cnf_scale",
                {"key": "sample_scale_functional"})
        cls.vnf_package_ids.append(vnf_package_id)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmKubernetesOidcTest, cls).tearDownClass()

    def setUp(self):
        vim_list = self.client.list_vims()
        if not vim_list:
            self.skipTest("Vims are not configured")

        vim_name = 'vim-kubernetes-oidc-auth'
        vim = self.get_vim(vim_list, vim_name)
        if not vim:
            self.skipTest(f"Kubernetes VIM '{vim_name}' is missing")
        self.vim_id = vim['id']
        self.extra = vim['extra']

    def test_basic_lcmsV1_with_oidc_auth(self):
        """Test CNF LCM with OIDC auth

        This test will cover the instantaite, scale, terminate operation
        with OIDC auth.
        """
        vnf_instance_name = "cnf_lcmv1_with_oidc_auth"
        vnf_instance_description = "cnf lcm with oidc auth"
        inst_additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/deployment_scale.yaml"]}
        vnf_instance = self._create_and_instantiate_vnf_instance(
            self.vnfd_id, "scalingsteps", vnf_instance_name,
            vnf_instance_description, inst_additional_param)
        # Use flavour_id scalingsteps that is set to delta_num=1
        self._test_scale_out_and_in(
            vnf_instance, "vdu1_aspect", number_of_steps=1)
        self._terminate_vnf_instance(vnf_instance['id'])
        self._delete_vnf_instance(vnf_instance['id'])
