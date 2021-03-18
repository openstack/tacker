# Copyright (C) 2021 FUJITSU
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

from kubernetes import client
from unittest import mock


from tacker.tests.unit import base
from tacker.vnfm.infra_drivers.kubernetes.k8s import translate_outputs
from tacker.vnfm.infra_drivers.kubernetes import translate_template


class TestTOSCAToKubernetes(base.TestCase):
    def setUp(self):
        super(TestTOSCAToKubernetes, self).setUp()
        self.vnf = {
            "vnfd": {
                "service_types": [
                    {
                        "service_type": "vnfd",
                        "id": "ca0d8667-ce35-4f7a-9744-ac4bc7d5579d"
                    }
                ],
                "description": "Sample",
                "tenant_id": "689708956a2d4ae0a27120d3aca6a560",
                "created_at": "2016-10-20 07:38:54",
                "updated_at": None,
                "attributes": {
                    "vnfd":
                    "description: "
                    "Demo example\nmetadata: "
                    "{template_name: sample-tosca-vnfd}\n"
                    "topology_template:\n  "
                    "node_templates:\n    CP1:\n      "
                    "properties: {anti_spoofing_protection: "
                    "false, management: true, order: 0}\n      "
                    "requirements:\n      "
                    "- virtualLink: {node: VL1}\n      "
                    "- virtualBinding: {node: VDU1}\n      "
                    "type: tosca.nodes.nfv.CP.Tacker\n    "
                    "VDU1:\n      "
                    "capabilities:\n        "
                    "nfv_compute:\n          "
                    "properties: {disk_size: 1 GB, "
                    "mem_size: 512 MB, num_cpus: 1}\n      "
                    "properties: {mapping_ports: [80:80] , "
                    "vnfcs: {web:{mem_size: 100 MB, "
                    "config: param0:key1}}}\n      "
                    "type: tosca.nodes.nfv.VDU.Tacker\n    "
                    "VL1:\n      properties: {network_name: "
                    "net_mgmt, vendor: Tacker}\n      "
                    "type: tosca.nodes.nfv.VL\ntosca_definitions_version: "
                    "tosca_simple_profile_for_nfv_1_0_0\n"
                },
                "id": "0fb827e7-32b0-4e5b-b300-e1b1dce8a831",
                "name": "vnfd-sample",
                "template_source": "onboarded or inline"
            }
        }

        self.core_v1_api_client = client.CoreV1Api
        self.app_v1_api_client = client.AppsV1Api
        self.scaling_api_client = client.AutoscalingApi
        self.tosca_to_kubernetes_object = translate_template.TOSCAToKubernetes(
            self.vnf, self.core_v1_api_client, self.app_v1_api_client,
            self.scaling_api_client)

    def test_generate_tosca_kube_objects(self):
        result = self.tosca_to_kubernetes_object.generate_tosca_kube_objects()
        self.assertEqual(result[0].name[:8], "svc-VDU1")
        self.assertEqual(result[0].containers[0].name, "web")
        self.assertEqual(result[0].containers[0].mem_size, 100000000)

    @mock.patch.object(translate_outputs.Transformer, 'deploy')
    def test_deploy_kuberentes_objects(self, mock_deploy):
        mock_deploy.return_value = "name, namespace"
        self.tosca_to_kubernetes_object.deploy_kubernetes_objects()
