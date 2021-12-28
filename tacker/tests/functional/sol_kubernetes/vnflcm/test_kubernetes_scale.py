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
import unittest

from tacker.tests.functional.sol_kubernetes.vnflcm import base as vnflcm_base


class VnfLcmKubernetesScaleTest(vnflcm_base.BaseVnfLcmKubernetesTest):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmKubernetesScaleTest, cls).setUpClass()
        vnf_package_id, cls.vnfd_id = \
            cls._create_and_upload_vnf_package(
                cls, cls.tacker_client, "test_cnf_scale",
                {"key": "sample_scale_functional"})
        cls.vnf_package_ids.append(vnf_package_id)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmKubernetesScaleTest, cls).tearDownClass()

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

    def test_scale_cnf_with_statefulset(self):
        """Test scale for CNF (StatefulSet)

        This test will instantiate cnf with StatefulSet and scale replicas.
        """
        vnf_instance_name = "cnf_scale_with_statefulset"
        vnf_instance_description = "cnf scale with statefulset"
        inst_additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/statefulset_scale.yaml"]}
        vnf_instance = self._create_and_instantiate_vnf_instance(
            self.vnfd_id, "simple", vnf_instance_name,
            vnf_instance_description, inst_additional_param)
        self._test_cnf_scale(vnf_instance, "vdu1_aspect")
        self._terminate_vnf_instance(vnf_instance['id'])
        self._delete_vnf_instance(vnf_instance['id'])

    def test_scale_cnf_with_replicaset(self):
        """Test scale for CNF (ReplicaSet)

        This test will instantiate cnf with ReplicaSet and scale replicas.
        """
        vnf_instance_name = "cnf_scale_with_replicaset"
        vnf_instance_description = "cnf scale with replicaset"
        inst_additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/replicaset_scale.yaml"]}
        vnf_instance = self._create_and_instantiate_vnf_instance(
            self.vnfd_id, "simple", vnf_instance_name,
            vnf_instance_description, inst_additional_param)
        self._test_cnf_scale(vnf_instance, "vdu1_aspect")
        self._terminate_vnf_instance(vnf_instance['id'])
        self._delete_vnf_instance(vnf_instance['id'])

    def test_scale_cnf_deployment_with_scaling_and_delta_two(self):
        """Test scale for CNF (Deployment)

        This test will instantiate cnf with Deployment and scale replicas.
        And scaling steps of ScaleVnfRequest set to two and scaling deltas that
        defined in VNFD set to two.
        """
        vnf_instance_name = "cnf_scale_with_scaling_and_delta_two"
        vnf_instance_description = "cnf scale with scaling and delta two"
        inst_additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/deployment_scale.yaml"]}
        vnf_instance = self._create_and_instantiate_vnf_instance(
            self.vnfd_id, "scalingsteps", vnf_instance_name,
            vnf_instance_description, inst_additional_param)
        # Use flavour_id scalingsteps that is set to delta_num=2
        self._test_cnf_scale(vnf_instance, "vdu1_aspect", number_of_steps=2)
        self._terminate_vnf_instance(vnf_instance['id'])
        self._delete_vnf_instance(vnf_instance['id'])

    @unittest.skip("Reduce test time")
    def test_scale_out_cnf_rollback(self):
        """Test rollback after scaling failure for CNF

        This test will rollback after failing scale out operation.
        """
        vnf_instance_name = "cnf_rollback_after_scale_out_fail"
        vnf_instance_description = "cnf rollback after scale out fail"
        inst_additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/statefulset_scale.yaml"]}
        vnf_instance = self._create_and_instantiate_vnf_instance(
            self.vnfd_id, "simple", vnf_instance_name,
            vnf_instance_description, inst_additional_param)
        # fail scale out for rollback
        aspect_id = "vdu1_aspect"
        previous_level = self._test_cnf_scale(vnf_instance, aspect_id,
                                              number_of_steps=2, error=True)
        # test rollback
        self._test_rollback_cnf_scale(
            vnf_instance['id'], aspect_id, previous_level)
        self._terminate_vnf_instance(vnf_instance['id'])
        self._delete_vnf_instance(vnf_instance['id'])
