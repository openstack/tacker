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

import os
import re
import unittest

from tacker.objects import fields
from tacker.tests.functional.sol_kubernetes.vnflcm import base as vnflcm_base
from tacker.tests import utils


class VnfLcmKubernetesTest(vnflcm_base.BaseVnfLcmKubernetesTest):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmKubernetesTest, cls).setUpClass()
        vnf_package_id, cls.vnfd_id = cls._create_and_upload_vnf_package(
            cls, cls.tacker_client, "test_cnf",
            {"key": "resource_functional_common"})
        cls.vnf_package_ids.append(vnf_package_id)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmKubernetesTest, cls).tearDownClass()

    @classmethod
    def _update_source_path(cls, meta_dir, meta_name, port):
        meta_path = os.path.join(meta_dir, meta_name)
        with open(file=meta_path, mode='r', encoding='UTF8') as f:
            meta_content = f.read()
        new_meta_content = re.sub(
            r':(\d{5})', ':' + str(port), meta_content)
        with open(meta_path, 'w', encoding='utf-8') as f:
            f.write(new_meta_content)

    def _test_inst_term_from_manifest(self, inst_name, inst_desc,
                                      additional_param, flavour_id="simple",
                                      vnfd_id=None):
        # Create and instantiate vnf instance
        if vnfd_id is None:
            vnfd_id = self.vnfd_id
        vnf_instance = self._create_and_instantiate_vnf_instance(
            vnfd_id, flavour_id, inst_name, inst_desc, additional_param)
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }
        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)
        self._delete_vnf_instance(vnf_instance['id'])

    # The same problem as
    # https://github.com/kubernetes-client/python/issues/547,
    # after fixing this bug, the bindings test items can pass normally.
    # def test_inst_term_cnf_with_binding(self):
    #     vnf_instance_name = "cnf_with_binding"
    #     vnf_instance_description = "cnf with binding"
    #     files = ["Files/kubernetes/bindings.yaml"]
    #     self._test_inst_term_from_manifest(
    #         vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_with_clusterrole_clusterrolebinding_SA(self):
        vnf_instance_name = "cnf_with_clusterrole_clusterrolebinding_SA"
        vnf_instance_description = "cnf with clusterRole/clusterRoleBinding/SA"
        files = ["Files/kubernetes/clusterrole_clusterrolebinding_SA.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_with_config_map(self):
        vnf_instance_name = "cnf_with_configMap"
        vnf_instance_description = "cnf with configMap"
        files = ["Files/kubernetes/config-map.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    @unittest.skip("Until BUG 1910327")
    def test_inst_term_cnf_with_controller_revision(self):
        vnf_instance_name = "cnf_with_controller_revision"
        vnf_instance_description = "cnf with controllerRevision"
        files = ["Files/kubernetes/controller-revision.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_with_daemon_set(self):
        vnf_instance_name = "cnf_with_daemon_set"
        vnf_instance_description = "cnf with daemonSet"
        files = ["Files/kubernetes/daemon-set.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_with_deployment(self):
        vnf_instance_name = "cnf_with_deployment"
        vnf_instance_description = "cnf with deployment"
        files = ["Files/kubernetes/deployment.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_with_horizontal_pod_autoscaler(self):
        vnf_instance_name = "cnf_with_horizontal_pod_autoscaler"
        vnf_instance_description = "cnf with horizontalPodAutoscaler"
        files = ["Files/kubernetes/horizontal-pod-autoscaler.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_with_job(self):
        vnf_instance_name = "cnf_with_job"
        vnf_instance_description = "cnf with job"
        files = ["Files/kubernetes/job.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_with_limit_range(self):
        vnf_instance_name = "cnf_with_limit_range"
        vnf_instance_description = "cnf with limitRange"
        files = ["Files/kubernetes/limit-range.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_with_namespace(self):
        vnf_instance_name = "cnf_with_namespae"
        vnf_instance_description = "cnf with namespace"
        files = ["Files/kubernetes/namespace.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_with_pod(self):
        vnf_instance_name = "cnf_with_pod"
        vnf_instance_description = "cnf with pod"
        files = ["Files/kubernetes/pod.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_with_pod_template(self):
        vnf_instance_name = "cnf_with_pod_template"
        vnf_instance_description = "cnf with podTemplate"
        files = ["Files/kubernetes/pod-template.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_with_resource_quota(self):
        vnf_instance_name = "cnf_with_resource_quota"
        vnf_instance_description = "cnf with resourceQuota"
        files = ["Files/kubernetes/resource-quota.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_with_role_rolebinding_SA(self):
        vnf_instance_name = "cnf_with_role_rolebinding_SA"
        vnf_instance_description = "cnf with role/roleBinding/SA"
        files = ["Files/kubernetes/role_rolebinding_SA.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_with_subject_access_review(self):
        vnf_instance_name = "cnf_with_subject_access_review"
        vnf_instance_description = "cnf with subjectAccessReview"
        files = ["Files/kubernetes/subject-access-review.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_with_token_review(self):
        vnf_instance_name = "cnf_with_token_review"
        vnf_instance_description = "cnf with tokenReview"
        files = ["Files/kubernetes/token-review.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_with_ext_artifact(self):
        # Setup http server
        instance_file_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '../../../etc/samples/etsi/nfv/test_cnf_ext_artifact')
        artifact_file_dir = os.path.join(
            instance_file_dir, 'Files/kubernetes')
        http_handler = utils.StaticHttpFileHandler(artifact_file_dir)
        self.addCleanup(http_handler.stop)
        artifact_file_url = (f"http://127.0.0.1:{http_handler.port}/"
                             "storage-class-url.yaml")
        meta_dir = os.path.join(instance_file_dir, 'TOSCA-Metadata')
        self._update_source_path(meta_dir, 'TOSCA.meta', http_handler.port)

        # Create and update vnf package
        vnf_package_id, vnfd_id = self._create_and_upload_vnf_package(
            self.tacker_client, "test_cnf_ext_artifact",
            {"key": "resource_functional_external_artifact"})
        self.vnf_package_ids.append(vnf_package_id)

        vnf_instance_name = "cnf_with_ext_artifact"
        vnf_instance_description = "cnf with ext artifact"
        files = [artifact_file_url]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param,
            vnfd_id=vnfd_id)

    def test_inst_term_cnf_in_multiple_yaml_with_single_resource(self):
        vnf_instance_name = "cnf_in_multiple_yaml_with_single_resource"
        vnf_instance_description = "cnf in multiple yaml with single resource"
        files = ["Files/kubernetes/replicaset_service_secret.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_in_single_yaml_with_multiple_resources(self):
        vnf_instance_name = "cnf_in_single_yaml_with_multiple_resources"
        vnf_instance_description = "cnf in single yaml with multiple resources"
        files = ["Files/kubernetes/multiple_yaml_priority-class.yaml",
                 "Files/kubernetes/multiple_yaml_lease.yaml",
                 "Files/kubernetes/multiple_yaml_network-policy.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_with_multi_yaml_and_resources_no_dep(self):
        vnf_instance_name = "cnf_multi_yaml_and_resources_no_dep"
        vnf_instance_description = "cnf multi yaml and resources no dep"
        files = ["Files/kubernetes/local-subject-access-review.yaml",
                 "Files/kubernetes/self-subject-access-review_"
                 "and_self-subject-rule-review.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_inst_term_cnf_with_multi_yaml_and_resources_dep_and_sort(self):
        vnf_instance_name = "cnf_multi_yaml_and_resources_dep_and_sort"
        vnf_instance_description = "cnf multi yaml and resources dep and sort"
        files = ["Files/kubernetes/storage-class.yaml",
                 "Files/kubernetes/persistent-volume-0.yaml",
                 "Files/kubernetes/persistent-volume-1.yaml",
                 "Files/kubernetes/statefulset.yaml",
                 "Files/kubernetes/storage-class_pv_pvc.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files}
        self._test_inst_term_from_manifest(
            vnf_instance_name, vnf_instance_description, additional_param)

    def test_rollback_cnf_after_instantiate_fail(self):
        vnf_instance_name = "vnf_rollback_cnf_after_instantiate_fail"
        vnf_instance_description = "vnf rollback cnf after instantiate fail"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id,
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)
        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/statefulset_fail.yaml",
            ]
        }
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)
        self._instantiate_vnf_instance(
            vnf_instance['id'], request_body, wait_state="FAILED_TEMP")
        self._test_rollback_cnf_instantiate(vnf_instance['id'])
        self._delete_vnf_instance(vnf_instance['id'])
