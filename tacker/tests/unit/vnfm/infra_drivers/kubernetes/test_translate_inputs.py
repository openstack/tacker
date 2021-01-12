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

from tacker.tests.unit import base
from tacker.tests.unit.vnfm.infra_drivers.kubernetes import fakes
from tacker.vnfm.infra_drivers.kubernetes.k8s import translate_inputs


class TestParser(base.TestCase):
    def setUp(self):
        super(TestParser, self).setUp()
        self.k8s_client_dict = fakes.fake_k8s_client_dict()
        self.vnfd_path = '../../../../etc/samples/sample_tosca_vnfc.yaml'
        self.yaml_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            self.vnfd_path)
        self.vnfd_dict = {
            "tosca_definitions_version": "tosca_simple_profile_for_nfv_1_0_0",
            "description": "Demo example",
            "metadata": {
                "template_name": "sample-tosca-vnfd"},
            "topology_template": {
                "node_templates": {
                    "VDU1": {
                        "type": "tosca.nodes.nfv.VDU.Tacker",
                        "capabilities": {
                            "nfv_compute": {
                                "properties": {
                                    "num_cpus": 1,
                                    "mem_size": "512 MB",
                                    "disk_size": "1 GB"}}},
                        "properties": {
                            "vnfcs": {
                                "web_server": {
                                    "mem_size": "100 MB",
                                    "config": "config"
                                }
                            },
                            "labels": [
                                "label1:1", "label2:2"
                            ]
                        }
                    },
                    "CP1": {
                        "type": "tosca.nodes.nfv.CP.Tacker",
                        "properties": {
                            "order": 0,
                            "management": True,
                            "anti_spoofing_protection": False},
                        "requirements": [
                            {"virtualLink": {
                                "node": "VL1"}},
                            {"virtualBinding": {
                                "node": "VDU1"}}]},
                    "VL1": {
                        "type": "tosca.nodes.nfv.VL",
                        "properties": {
                            "vendor": "Tacker",
                            "network_name": "net_mgmt"}}
                }
            }
        }
        self.parser = translate_inputs.Parser(self.vnfd_dict)

    def test_loader(self):
        tosca_kube_object = self.parser.loader()
        self.assertEqual(tosca_kube_object[0].name[:8], "svc-VDU1")
        self.assertEqual(tosca_kube_object[0].containers[0].name, "web_server")
        self.assertEqual(
            tosca_kube_object[0].containers[0].mem_size,
            100000000)
        self.assertEqual(
            tosca_kube_object[0].labels, {
                'label1': '1', 'label2': '2'})
