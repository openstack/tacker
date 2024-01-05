# Copyright (C) 2023 Fujitsu
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

from tacker.tests.functional.sol_kubernetes_v2 import base_v2
from tacker.tests.functional.sol_kubernetes_v2 import paramgen
from tacker.tests import utils

# Waiting time to trigger autoheal (unit: second)
WAIT_AUTO_HEAL_TIME = 23

# Waiting time to lcmocc update in DB (unit: second)
WAIT_LCMOCC_UPDATE_TIME = 3


@ddt.ddt
class PromAutoScaleHealTest(base_v2.BaseVnfLcmKubernetesV2Test):

    @classmethod
    def setUpClass(cls):
        super(PromAutoScaleHealTest, cls).setUpClass()

        test_instantiate_cnf_resources_path = utils.test_sample(
            "functional/sol_kubernetes_v2/test_instantiate_cnf_resources")
        cls.cnf_pkg, cls.cnf_vnfd_id = cls.create_vnf_package(
            test_instantiate_cnf_resources_path)

    @classmethod
    def tearDownClass(cls):
        super(PromAutoScaleHealTest, cls).tearDownClass()

        cls.delete_vnf_package(cls.cnf_pkg)

    def setUp(self):
        super(PromAutoScaleHealTest, self).setUp()

    def test_vnfm_auto_heal_cnf(self):
        """Test Prometheus VNFM Auto Healing operations

        * About LCM operations:
          This test includes the following operations.
          - 1. Create a new VNF instance resource
          - 2. Instantiate a VNF instance
          - 3. Show OpOcc
          - 4-5. Receive Alert and Auto Heal
          - 6. Show OpOcc
          - 7. Receive Alert
          - 8-9. Receive Alert and Auto Heal
          - 10. Show OpOcc
          - 11. Terminate a VNF instance
          - 12. Show OpOcc
          - 13. Delete a VNF instance
        """

        # 1. LCM-Create: Create a new VNF instance resource
        create_req = paramgen.instantiate_cnf_resources_create(
            self.cnf_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # 2. LCM-Instantiate: Instantiate a VNF instance
        vim_id = self.get_k8s_vim_id()
        instantiate_req = paramgen.min_sample_instantiate(vim_id)
        instantiate_req['additionalParams'][
            'lcm-kubernetes-def-files'] = ['Files/kubernetes/deployment.yaml']
        instantiate_req['vnfConfigurableProperties'] = {
            'isAutohealEnabled': True}
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 3. LCM-Show-OpOccV2: Show OpOcc
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual('COMPLETED', body['operationState'])
        self.assertEqual('INSTANTIATE', body['operation'])
        self.assertEqual(False, body['isAutomaticInvocation'])

        # 4-5. Send alert and auto heal
        affected_vnfcs = body['resourceChanges']['affectedVnfcs']
        vnfc_info_id = (f"{affected_vnfcs[0]['vduId']}-"
                        f"{affected_vnfcs[0]['id']}")

        alert = paramgen.prometheus_auto_healing_alert(inst_id, vnfc_info_id)
        resp, body = self.prometheus_auto_healing_alert(alert)
        self.assertEqual(204, resp.status_code)

        # Since auto heal takes 20 seconds to trigger,
        # wait 23 seconds here.
        time.sleep(WAIT_AUTO_HEAL_TIME)

        # 6. LCM-Show-OpOccV2: Show-OpOcc
        filter_expr = {'filter': f'(eq,vnfInstanceId,{inst_id})'}
        resp, body = self.list_lcmocc(filter_expr)
        self.assertEqual(200, resp.status_code)

        heal_lcmocc = [
            heal_lcmocc for heal_lcmocc in body
            if heal_lcmocc['startTime'] == max(
                [lcmocc['startTime'] for lcmocc in body])][0]
        lcmocc_id = heal_lcmocc['id']
        self.wait_lcmocc_complete(lcmocc_id)

        resp, body = self.show_lcmocc(lcmocc_id)
        affected_vnfcs = body['resourceChanges']['affectedVnfcs']
        self.assertEqual(200, resp.status_code)
        self.assertEqual('COMPLETED', body['operationState'])
        self.assertEqual('HEAL', body['operation'])
        self.assertEqual(2, len(affected_vnfcs))
        self.assertEqual(True, body['isAutomaticInvocation'])

        added_vnfcs = [
            vnfc for vnfc in affected_vnfcs
            if vnfc['changeType'] == 'ADDED']
        self.assertEqual(1, len(added_vnfcs))

        removed_vnfcs = [
            vnfc for vnfc in affected_vnfcs
            if vnfc['changeType'] == 'REMOVED']
        self.assertEqual(1, len(removed_vnfcs))

        removed_vnfc_info_id = (f"{affected_vnfcs[0]['vduId']}-"
                                f"{affected_vnfcs[0]['id']}")
        self.assertEqual(vnfc_info_id, removed_vnfc_info_id)

        # 7. Send alert
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        vnfc_infos = body['instantiatedVnfInfo']['vnfcInfo']
        vnfc_info_id_1 = vnfc_infos[0]['id']
        alert = paramgen.prometheus_auto_healing_alert(
            inst_id, vnfc_info_id_1)
        resp, body = self.prometheus_auto_healing_alert(alert)
        self.assertEqual(204, resp.status_code)

        # 8-9. Send alert and auto heal
        vnfc_info_id_2 = vnfc_infos[1]['id']
        alert = paramgen.prometheus_auto_healing_alert(
            inst_id, vnfc_info_id_2)
        resp, body = self.prometheus_auto_healing_alert(alert)
        self.assertEqual(204, resp.status_code)

        # Since auto heal takes 20 seconds to trigger,
        # wait 23 seconds here.
        time.sleep(WAIT_AUTO_HEAL_TIME)

        # 10. LCM-Show-OpOccV2: Show-OpOcc
        filter_expr = {'filter': f'(eq,vnfInstanceId,{inst_id})'}
        resp, body = self.list_lcmocc(filter_expr)
        self.assertEqual(200, resp.status_code)

        heal_lcmocc = [
            heal_lcmocc for heal_lcmocc in body
            if heal_lcmocc['startTime'] == max(
                [lcmocc['startTime'] for lcmocc in body])][0]
        lcmocc_id = heal_lcmocc['id']
        self.wait_lcmocc_complete(lcmocc_id)

        resp, body = self.show_lcmocc(lcmocc_id)
        affected_vnfcs = body['resourceChanges']['affectedVnfcs']
        self.assertEqual(200, resp.status_code)
        self.assertEqual('COMPLETED', body['operationState'])
        self.assertEqual('HEAL', body['operation'])
        self.assertEqual(4, len(affected_vnfcs))
        self.assertEqual(True, body['isAutomaticInvocation'])

        added_vnfcs = [
            vnfc for vnfc in affected_vnfcs
            if vnfc['changeType'] == 'ADDED']
        self.assertEqual(2, len(added_vnfcs))

        removed_vnfcs = [
            vnfc for vnfc in affected_vnfcs
            if vnfc['changeType'] == 'REMOVED']
        self.assertEqual(2, len(removed_vnfcs))

        removed_vnfc_info_ids = [
            f"{removed_vnfcs[0]['vduId']}-{removed_vnfcs[0]['id']}",
            f"{removed_vnfcs[1]['vduId']}-{removed_vnfcs[1]['id']}"
        ]
        self.assertCountEqual(
            [vnfc_info_id_1, vnfc_info_id_2], removed_vnfc_info_ids)

        # 11. LCM-Terminate: Terminate VNF
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 12. LCM-Show-OpOccV2: Show OpOcc
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual('COMPLETED', body['operationState'])
        self.assertEqual('TERMINATE', body['operation'])
        self.assertEqual(False, body['isAutomaticInvocation'])

        # 13. LCM-Delete: Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

    def test_vnfm_auto_scale_cnf(self):
        """Test Prometheus VNFM Auto Scaling operations

        * About LCM operations:
          This test includes the following operations.
          - 1. Create a new VNF instance resource
          - 2. Instantiate a VNF instance
          - 3. Show OpOcc
          - 4-5. Receive Alert and Auto Scale out
          - 6. Show OpOcc
          - 7-8. Receive Alert and Auto Scale in
          - 9. Show OpOcc
          - 10. Terminate a VNF instance
          - 11. Show OpOcc
          - 12. Delete a VNF instance
        """

        # 1. LCM-Create: Create a new VNF instance resource
        create_req = paramgen.instantiate_cnf_resources_create(
            self.cnf_vnfd_id)
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

        # 3. LCM-Show-OpOccV2: Show OpOcc
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual('COMPLETED', body['operationState'])
        self.assertEqual('INSTANTIATE', body['operation'])
        self.assertEqual(False, body['isAutomaticInvocation'])

        # 4-5. Send alert and auto-scale out
        alert = paramgen.prometheus_auto_scaling_alert(inst_id)
        resp, body = self.prometheus_auto_scaling_alert(alert)
        self.assertEqual(204, resp.status_code)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and scale completion.
        time.sleep(WAIT_LCMOCC_UPDATE_TIME)

        # 6. LCM-Show-OpOccV2: Show-OpOcc
        filter_expr = {'filter': f'(eq,vnfInstanceId,{inst_id})'}
        resp, body = self.list_lcmocc(filter_expr)
        self.assertEqual(200, resp.status_code)

        scale_lcmocc = [
            scale_lcmocc for scale_lcmocc in body
            if scale_lcmocc['startTime'] == max(
                [lcmocc['startTime'] for lcmocc in body])][0]
        lcmocc_id = scale_lcmocc['id']
        self.wait_lcmocc_complete(lcmocc_id)

        resp, body = self.show_lcmocc(lcmocc_id)
        affected_vnfcs = body['resourceChanges']['affectedVnfcs']
        self.assertEqual(200, resp.status_code)
        self.assertEqual('COMPLETED', body['operationState'])
        self.assertEqual('SCALE', body['operation'])
        self.assertEqual(1, len(affected_vnfcs))
        self.assertEqual('ADDED', affected_vnfcs[0]['changeType'])
        self.assertEqual(
            alert['alerts'][0]['labels']['aspect_id'],
            body['operationParams']['aspectId'])
        self.assertEqual(True, body['isAutomaticInvocation'])

        # 7-8. Send alert and auto-scale in
        alert['alerts'][0]['labels']['auto_scale_type'] = 'SCALE_IN'
        resp, body = self.prometheus_auto_scaling_alert(alert)
        self.assertEqual(204, resp.status_code)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and scale completion.
        time.sleep(WAIT_LCMOCC_UPDATE_TIME)

        # 9. LCM-Show-OpOccV2: Show-OpOcc
        filter_expr = {'filter': f'(eq,vnfInstanceId,{inst_id})'}
        resp, body = self.list_lcmocc(filter_expr)
        self.assertEqual(200, resp.status_code)

        scale_lcmocc = [
            scale_lcmocc for scale_lcmocc in body
            if scale_lcmocc['startTime'] == max(
                [lcmocc['startTime'] for lcmocc in body])][0]
        lcmocc_id = scale_lcmocc['id']
        self.wait_lcmocc_complete(lcmocc_id)

        resp, body = self.show_lcmocc(lcmocc_id)
        affected_vnfcs = body['resourceChanges']['affectedVnfcs']
        self.assertEqual(200, resp.status_code)
        self.assertEqual('COMPLETED', body['operationState'])
        self.assertEqual('SCALE', body['operation'])
        self.assertEqual(1, len(affected_vnfcs))
        self.assertEqual('REMOVED', affected_vnfcs[0]['changeType'])
        self.assertEqual(
            alert['alerts'][0]['labels']['aspect_id'],
            body['operationParams']['aspectId'])
        self.assertEqual(True, body['isAutomaticInvocation'])

        # 10. LCM-Terminate: Terminate VNF
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 11. LCM-Show-OpOccV2: Show OpOcc
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual('COMPLETED', body['operationState'])
        self.assertEqual('TERMINATE', body['operation'])
        self.assertEqual(False, body['isAutomaticInvocation'])

        # 12. LCM-Delete: Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)
