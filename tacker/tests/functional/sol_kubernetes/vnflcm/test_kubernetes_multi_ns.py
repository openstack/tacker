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

from tacker.tests.functional.sol_kubernetes.vnflcm import base as vnflcm_base


class VnfLcmKubernetesMultiNsTest(vnflcm_base.BaseVnfLcmKubernetesTest):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmKubernetesMultiNsTest, cls).setUpClass()
        vnf_package_id, cls.vnfd_id = cls._create_and_upload_vnf_package(
            cls, cls.tacker_client, "test_cnf_multi_ns",
            {"key": "sample_multi_ns_functional"})
        cls.vnf_package_ids.append(vnf_package_id)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmKubernetesMultiNsTest, cls).tearDownClass()

    def _test_cnf_scale(self, vnf_instance, aspect_id,
                        number_of_steps=1, error=False):
        scale_level = self._get_scale_level_by_aspect_id(
            vnf_instance, aspect_id)

        # test scale out
        scale_level = self._test_scale(
            vnf_instance['id'], 'SCALE_OUT', aspect_id, scale_level,
            number_of_steps, error)
        if error:
            return scale_level

        # test scale in
        scale_level = self._test_scale(
            vnf_instance['id'], 'SCALE_IN', aspect_id, scale_level,
            number_of_steps)

        return scale_level

    def test_multi_tenant_k8s_additional_params(self):
        vnf_instance_name = "multi_tenant_k8s_additional_params"
        vnf_instance_description = "multi tenant k8s additional params"
        files = ["Files/kubernetes/deployment_has_namespace.yaml",
                 "Files/kubernetes/namespace01.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files,
            "namespace": "multi-namespace01"}
        # instantiate
        vnf_instance = self._create_and_instantiate_vnf_instance(
            self.vnfd_id, "simple", vnf_instance_name,
            vnf_instance_description, additional_param)
        # scale
        self._test_cnf_scale(vnf_instance, "vdu1_aspect", number_of_steps=1)

        before_vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)
        deployment_target_vnfc = [vnfc_rsc for vnfc_rsc in before_vnfc_rscs if
                                  vnfc_rsc['vduId'] == 'VDU1'][0]
        vnfc_instance_id = [deployment_target_vnfc['id']]
        # heal
        after_vnfc_rscs = self._test_heal(vnf_instance, vnfc_instance_id)
        for vnfc_rsc in after_vnfc_rscs:
            after_pod_name = vnfc_rsc['computeResource']['resourceId']
            if vnfc_rsc['id'] == deployment_target_vnfc['id']:
                after_resource = deployment_target_vnfc
                compute_resource = after_resource['computeResource']
                before_pod_name = compute_resource['resourceId']
                self.assertNotEqual(after_pod_name, before_pod_name)
        # terminate
        self._terminate_vnf_instance(vnf_instance['id'])
        self._delete_vnf_instance(vnf_instance['id'])

    def test_multi_tenant_k8s_manifest(self):
        vnf_instance_name = "multi_tenant_k8s_manifest"
        vnf_instance_description = "multi tenant k8s manifest"
        files = ["Files/kubernetes/deployment_has_namespace.yaml",
                 "Files/kubernetes/namespace02.yaml"]
        additional_param = {"lcm-kubernetes-def-files": files}
        # instantiate
        vnf_instance = self._create_and_instantiate_vnf_instance(
            self.vnfd_id, "simple", vnf_instance_name,
            vnf_instance_description, additional_param)
        # scale
        self._test_cnf_scale(vnf_instance, "vdu1_aspect", number_of_steps=1)

        before_vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)
        deployment_target_vnfc = [vnfc_rsc for vnfc_rsc in before_vnfc_rscs if
                                  vnfc_rsc['vduId'] == 'VDU1'][0]
        vnfc_instance_id = [deployment_target_vnfc['id']]
        # heal
        after_vnfc_rscs = self._test_heal(vnf_instance, vnfc_instance_id)
        for vnfc_rsc in after_vnfc_rscs:
            after_pod_name = vnfc_rsc['computeResource']['resourceId']
            if vnfc_rsc['id'] == deployment_target_vnfc['id']:
                after_resource = deployment_target_vnfc
                compute_resource = after_resource['computeResource']
                before_pod_name = compute_resource['resourceId']
                self.assertNotEqual(after_pod_name, before_pod_name)
        # terminate
        self._terminate_vnf_instance(vnf_instance['id'])
        self._delete_vnf_instance(vnf_instance['id'])

    def test_multi_tenant_k8s_default(self):
        vnf_instance_name = "multi_tenant_k8s_default"
        vnf_instance_description = "multi tenant k8s default"
        files = ["Files/kubernetes/deployment_no_namespace.yaml"]
        additional_param = {"lcm-kubernetes-def-files": files}
        # instantiate
        vnf_instance = self._create_and_instantiate_vnf_instance(
            self.vnfd_id, "simple", vnf_instance_name,
            vnf_instance_description, additional_param)
        # scale
        self._test_cnf_scale(vnf_instance, "vdu2_aspect", number_of_steps=1)

        before_vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)
        deployment_target_vnfc = [vnfc_rsc for vnfc_rsc in before_vnfc_rscs if
                                  vnfc_rsc['vduId'] == 'VDU2'][0]
        vnfc_instance_id = [deployment_target_vnfc['id']]
        # heal
        after_vnfc_rscs = self._test_heal(vnf_instance, vnfc_instance_id)
        for vnfc_rsc in after_vnfc_rscs:
            after_pod_name = vnfc_rsc['computeResource']['resourceId']
            if vnfc_rsc['id'] == deployment_target_vnfc['id']:
                after_resource = deployment_target_vnfc
                compute_resource = after_resource['computeResource']
                before_pod_name = compute_resource['resourceId']
                self.assertNotEqual(after_pod_name, before_pod_name)
        # terminate
        self._terminate_vnf_instance(vnf_instance['id'])
        self._delete_vnf_instance(vnf_instance['id'])
