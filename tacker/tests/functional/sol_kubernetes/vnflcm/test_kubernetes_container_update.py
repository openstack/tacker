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


class VnfLcmKubernetesContainerUpdate(vnflcm_base.BaseVnfLcmKubernetesTest):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmKubernetesContainerUpdate, cls).setUpClass()
        mgmt_rela_path = ("../../../../../samples/mgmt_driver/kubernetes/"
                          "container_update/container_update_mgmt.py")
        vnf_package_id_before, cls.vnfd_id_before = (
            cls._create_and_upload_vnf_package_add_mgmt(
                cls, cls.tacker_client, "test_cnf_container_update_before",
                {"key": "sample_container_update_before_functional"},
                mgmt_rela_path))
        cls.vnf_package_ids.append(vnf_package_id_before)

        vnf_package_id_after, cls.vnfd_id_after = (
            cls._create_and_upload_vnf_package_add_mgmt(
                cls, cls.tacker_client, "test_cnf_container_update_after",
                {"key": "sample_container_update_after_functional"},
                mgmt_rela_path))
        cls.vnf_package_ids.append(vnf_package_id_after)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmKubernetesContainerUpdate, cls).tearDownClass()

    def test_container_update_multi_kinds(self):
        vnf_instance_name = "container_update_multi_kinds"
        vnf_instance_description = "container update multi kinds"
        files = ["Files/kubernetes/configmap_1.yaml",
                 "Files/kubernetes/deployment.yaml",
                 "Files/kubernetes/pod_env.yaml",
                 "Files/kubernetes/pod_volume.yaml",
                 "Files/kubernetes/replicaset.yaml",
                 "Files/kubernetes/secret_1.yaml"]
        additional_param = {
            "lcm-kubernetes-def-files": files,
            "namespace": "default"}

        # instantiate
        vnf_instance = self._create_and_instantiate_vnf_instance(
            self.vnfd_id_before, "simple", vnf_instance_name,
            vnf_instance_description, additional_param)

        before_vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)
        self.assertEqual(4, len(before_vnfc_rscs))

        # modify
        vnf_instance_name = "modify_vnf_after"
        configmap_secret_paths = [
            "Files/kubernetes/configmap_2.yaml",
            "Files/kubernetes/secret_2.yaml"]
        metadata = {"configmap_secret_paths": configmap_secret_paths}
        modify_request_body = {
            "vnfdId": self.vnfd_id_after,
            "vnfInstanceName": vnf_instance_name,
            "metadata": metadata
        }

        vnf_instance_after, after_vnfc_rscs = self._modify_vnf_instance(
            vnf_instance['id'], modify_request_body)

        self.assertEqual(4, len(after_vnfc_rscs))

        for after_vnfc_rsc in after_vnfc_rscs:
            for before_vnfc_rsc in before_vnfc_rscs:
                after_resource = after_vnfc_rsc['computeResource']
                before_resource = before_vnfc_rsc['computeResource']
                if after_vnfc_rsc['id'] == before_vnfc_rsc['id']:
                    if after_resource['vimLevelResourceType'] == 'Deployment':
                        # check stored pod name is changed (Deployment)
                        self.assertNotEqual(before_resource['resourceId'],
                                            after_resource['resourceId'])
                    else:
                        # check stored pod name is not changed (other)
                        self.assertEqual(before_resource['resourceId'],
                                         after_resource['resourceId'])

        self.assertEqual(
            self.vnfd_id_after, vnf_instance_after['vnfdId'])
        self.assertEqual(
            vnf_instance_name, vnf_instance_after['vnfInstanceName'])

        # terminate
        self._terminate_vnf_instance(vnf_instance['id'])
        self._delete_vnf_instance(vnf_instance['id'])
