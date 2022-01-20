# Copyright (C) 2020 FUJITSU
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


class VnfLcmKubernetesHealTest(vnflcm_base.BaseVnfLcmKubernetesTest):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmKubernetesHealTest, cls).setUpClass()
        vnf_package_id, cls.vnfd_id = \
            cls._create_and_upload_vnf_package(
                cls, cls.tacker_client, "test_cnf_heal",
                {"key": "sample_heal_functional"})
        cls.vnf_package_ids.append(vnf_package_id)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmKubernetesHealTest, cls).tearDownClass()

    def test_heal_cnf_with_sol002(self):
        """Test heal as per SOL002 for CNF

        This test will instantiate cnf. Heal API will be invoked as per SOL002
        i.e. with vnfcInstanceId, so that the specified vnfc instance is healed
        which includes Kubernetes resources (Pod and Deployment).
        """
        vnf_instance_name = "cnf_heal_with_sol002"
        vnf_instance_description = "cnf heal with sol002"
        # use def-files of singleton Pod and Deployment (replicas=2)
        inst_additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/deployment_heal_complex.yaml",
                "Files/kubernetes/pod_heal.yaml"]}
        vnf_instance = self._create_and_instantiate_vnf_instance(
            self.vnfd_id, "complex", vnf_instance_name,
            vnf_instance_description, inst_additional_param)
        before_vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)

        # get vnfc_instance_id of heal target
        deployment_target_vnfc = None
        for vnfc_rsc in before_vnfc_rscs:
            compute_resource = vnfc_rsc['computeResource']
            rsc_kind = compute_resource['vimLevelResourceType']
            if rsc_kind == 'Pod':
                # target 1: Singleton Pod
                pod_target_vnfc = vnfc_rsc
            elif not deployment_target_vnfc:
                # target 2: Deployment's Pod
                deployment_target_vnfc = vnfc_rsc
            else:
                # not target: Deployment's remianing one
                deployment_not_target_vnfc = vnfc_rsc

        # test heal SOL-002 (partial heal)
        vnfc_instance_id = \
            [pod_target_vnfc['id'], deployment_target_vnfc['id']]
        after_vnfc_rscs = self._test_heal(vnf_instance, vnfc_instance_id)
        for vnfc_rsc in after_vnfc_rscs:
            after_pod_name = vnfc_rsc['computeResource']['resourceId']
            if vnfc_rsc['id'] == pod_target_vnfc['id']:
                # check stored pod name is not changed (Pod)
                after_resource = pod_target_vnfc
                compute_resource = after_resource['computeResource']
                before_pod_name = compute_resource['resourceId']
                self.assertEqual(after_pod_name, before_pod_name)
            elif vnfc_rsc['id'] == deployment_target_vnfc['id']:
                # check stored pod name is changed (Deployment)
                after_resource = deployment_target_vnfc
                compute_resource = after_resource['computeResource']
                before_pod_name = compute_resource['resourceId']
                self.assertNotEqual(after_pod_name, before_pod_name)
            else:
                # check stored pod name is not changed (not target)
                after_resource = deployment_not_target_vnfc
                compute_resource = after_resource['computeResource']
                before_pod_name = compute_resource['resourceId']
                self.assertEqual(after_pod_name, before_pod_name)
        self._terminate_vnf_instance(vnf_instance['id'])
        self._delete_vnf_instance(vnf_instance['id'])

    def test_heal_cnf_with_sol003(self):
        """Test heal as per SOL003 for CNF

        This test will instantiate cnf. Heal API will be invoked as per SOL003
        i.e. without passing vnfcInstanceId, so that the entire vnf is healed
        which includes Kubernetes resource (Deployment).
        """
        vnf_instance_name = "cnf_heal_with_sol003"
        vnf_instance_description = "cnf heal with sol003"
        # use def-files of Deployment (replicas=2)
        inst_additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/deployment_heal_simple.yaml"]}
        vnf_instance = self._create_and_instantiate_vnf_instance(
            self.vnfd_id, "simple", vnf_instance_name,
            vnf_instance_description, inst_additional_param)
        before_vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)

        # test heal SOL-003 (entire heal)
        vnfc_instance_id = []
        after_vnfc_rscs = self._test_heal(vnf_instance, vnfc_instance_id)
        self.assertEqual(len(before_vnfc_rscs), len(after_vnfc_rscs))
        # check id and pod name (as computeResource.resourceId) is changed
        for before_vnfc_rsc in before_vnfc_rscs:
            for after_vnfc_rsc in after_vnfc_rscs:
                self.assertNotEqual(
                    before_vnfc_rsc['id'], after_vnfc_rsc['id'])
                self.assertNotEqual(
                    before_vnfc_rsc['computeResource']['resourceId'],
                    after_vnfc_rsc['computeResource']['resourceId'])
        # terminate vnf instance
        self._terminate_vnf_instance(vnf_instance['id'])
        self._delete_vnf_instance(vnf_instance['id'])
