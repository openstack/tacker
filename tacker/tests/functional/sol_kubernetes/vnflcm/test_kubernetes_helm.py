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


class VnfLcmKubernetesHelmTest(vnflcm_base.BaseVnfLcmKubernetesTest):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmKubernetesHelmTest, cls).setUpClass()
        vnf_package_id, cls.vnfd_id = \
            cls._create_and_upload_vnf_package(
                cls, cls.tacker_client, "test_cnf_helmchart",
                {"key": "sample_helmchart_functional"})
        cls.vnf_package_ids.append(vnf_package_id)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmKubernetesHelmTest, cls).tearDownClass()

    def _test_scale_cnf(self, vnf_instance, aspect_id):
        """Test scale in/out CNF"""
        scale_level = self._get_scale_level_by_aspect_id(
            vnf_instance, aspect_id)

        # test scale out
        scale_level = self._test_scale(
            vnf_instance['id'], 'SCALE_OUT', aspect_id, scale_level)

        # test scale in
        scale_level = self._test_scale(
            vnf_instance['id'], 'SCALE_IN', aspect_id, scale_level)

    def _test_heal_cnf_with_sol002(self, vnf_instance):
        """Test heal as per SOL002 for CNF"""
        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        before_vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)

        # get vnfc_instance_id of heal target
        before_pod_name = {}
        vnfc_instance_id = []
        for vnfc_rsc in before_vnfc_rscs:
            if vnfc_rsc['vduId'] == "vdu1":
                before_pod_name['vdu1'] = \
                    vnfc_rsc['computeResource']['resourceId']
            elif vnfc_rsc['vduId'] == "vdu2":
                before_pod_name['vdu2'] = \
                    vnfc_rsc['computeResource']['resourceId']
            vnfc_instance_id.append(vnfc_rsc['id'])

        # test heal SOL-002 (partial heal)
        after_vnfc_rscs = self._test_heal(vnf_instance, vnfc_instance_id)
        for vnfc_rsc in after_vnfc_rscs:
            after_pod_name = vnfc_rsc['computeResource']['resourceId']
            if vnfc_rsc['vduId'] == "vdu1":
                # check stored pod name is changed (vdu1)
                compute_resource = vnfc_rsc['computeResource']
                before_pod_name = compute_resource['resourceId']
                self.assertNotEqual(after_pod_name, before_pod_name['vdu1'])
            elif vnfc_rsc['vduId'] == "vdu2":
                # check stored pod name is changed (vdu2)
                compute_resource = vnfc_rsc['computeResource']
                before_pod_name = compute_resource['resourceId']
                self.assertNotEqual(after_pod_name, before_pod_name['vdu2'])

    def _test_heal_cnf_with_sol003(self, vnf_instance):
        """Test heal as per SOL003 for CNF"""
        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        before_vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)

        # test heal SOL-003 (entire heal)
        vnfc_instance_id = []
        after_vnfc_rscs = self._test_heal(vnf_instance, vnfc_instance_id)
        # check id and pod name (as computeResource.resourceId) is changed
        for before_vnfc_rsc in before_vnfc_rscs:
            for after_vnfc_rsc in after_vnfc_rscs:
                self.assertNotEqual(
                    before_vnfc_rsc['id'], after_vnfc_rsc['id'])
                self.assertNotEqual(
                    before_vnfc_rsc['computeResource']['resourceId'],
                    after_vnfc_rsc['computeResource']['resourceId'])

    def test_vnflcm_with_helmchart(self):
        """Test LCM using Helm chart

        This test will instantiate, scale, heal, terminate cnf by using
        local and external Helm charts.
        """
        vnf_instance_name = "cnf_with_helmchart"
        vnf_instance_description = "cnf with helmchart"
        helmchartfile_path = "Files/kubernetes/localhelm-0.1.0.tgz"
        inst_additional_param = {
            "namespace": "default",
            "use_helm": "true",
            "using_helm_install_param": [
                {
                    "exthelmchart": "false",
                    "helmchartfile_path": helmchartfile_path,
                    "helmreleasename": "vdu1",
                    "helmparameter": [
                        "service.port=8081"
                    ]
                },
                {
                    "exthelmchart": "true",
                    "helmreleasename": "vdu2",
                    "helmrepositoryname": "bitnami",
                    "helmchartname": "apache",
                    "exthelmrepo_url": "https://charts.bitnami.com/bitnami"
                }
            ],
            "helm_replica_values": {
                "vdu1_aspect": "replicaCount",
                "vdu2_aspect": "replicaCount"
            }
        }
        vnf_instance = self._create_and_instantiate_vnf_instance(
            self.vnfd_id, "helmchart", vnf_instance_name,
            vnf_instance_description, inst_additional_param)

        self._test_scale_cnf(vnf_instance, aspect_id="vdu1_aspect")
        self._test_scale_cnf(vnf_instance, aspect_id="vdu2_aspect")
        self._test_heal_cnf_with_sol002(vnf_instance)
        self._test_heal_cnf_with_sol003(vnf_instance)

        self._terminate_vnf_instance(vnf_instance['id'])
        self._delete_vnf_instance(vnf_instance['id'])
