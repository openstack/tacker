# Copyright (C) 2022 Fujitsu
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
import ddt
import os
import time

from tacker.objects import fields
from tacker.tests.functional.sol_kubernetes_v2 import base_v2
from tacker.tests.functional.sol_kubernetes_v2 import paramgen


@ddt.ddt
class PrometheusAutoScalingTest(base_v2.BaseVnfLcmKubernetesV2Test):

    @classmethod
    def setUpClass(cls):
        super(PrometheusAutoScalingTest, cls).setUpClass()

        cur_dir = os.path.dirname(__file__)

        test_instantiate_cnf_resources_path = os.path.join(
            cur_dir, "samples/test_instantiate_cnf_resources")
        cls.vnf_pkg_1, cls.vnfd_id_1 = cls.create_vnf_package(
            test_instantiate_cnf_resources_path)

    @classmethod
    def tearDownClass(cls):
        super(PrometheusAutoScalingTest, cls).tearDownClass()

        cls.delete_vnf_package(cls.vnf_pkg_1)

    def setUp(self):
        super(PrometheusAutoScalingTest, self).setUp()

    def test_prometheus_auto_scaling_basic(self):
        """Test Prometheus Auto Scaling operations with all attributes set

        * About LCM operations:
          This test includes the following operations.
          - 1. Create a new VNF instance resource
          - 2. Instantiate a VNF instance
          - 3. Prometheus Auto Scaling alert.
          - 4. Terminate a VNF instance
          - 5. Delete a VNF instance
        """

        # 1. LCM-Create: Create a new VNF instance resource
        # NOTE: extensions and vnfConfigurableProperties are omitted
        # because they are commented out in etsi_nfv_sol001.
        create_req = paramgen.instantiate_cnf_resources_create(self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # 2. LCM-Instantiate: Instantiate a VNF instance
        vim_id = self.get_k8s_vim_id()
        instantiate_req = paramgen.min_sample_instantiate(vim_id)
        instantiate_req['additionalParams'][
            'lcm-kubernetes-def-files'] = ['Files/kubernetes/deployment.yaml']
        instantiate_req['vnfConfigurableProperties'] = {
            'isAutoscaleEnabled': True}
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # 3. Send Auto-Healing alert
        alert = paramgen.prometheus_auto_scaling_alert(inst_id)
        # CNF scale is not integrated yet. use this value for now.
        alert['alerts'][0]['labels']['aspect_id'] = 'invalid_id'
        resp, body = self.prometheus_auto_scaling_alert(alert)
        self.assertEqual(204, resp.status_code)
        time.sleep(5)

        # 4. LCM-Terminate: Terminate VNF
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 5. LCM-Delete: Delete a VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)
