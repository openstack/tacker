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

from tacker.objects import fields
from tacker.tests.functional.sol_kubernetes_v2 import base_v2
from tacker.tests.functional.sol_kubernetes_v2 import paramgen
from tacker.tests import utils

WAIT_CREATE_THRESHOLD_TIME = 5


@ddt.ddt
class VnfPmThresholdTest(base_v2.BaseVnfLcmKubernetesV2Test):

    @classmethod
    def setUpClass(cls):
        super(VnfPmThresholdTest, cls).setUpClass()

        test_instantiate_cnf_resources_path = utils.test_sample(
            "functional/sol_kubernetes_v2/test_instantiate_cnf_resources")
        cls.cnf_pkg, cls.cnf_vnfd_id = cls.create_vnf_package(
            test_instantiate_cnf_resources_path)

    @classmethod
    def tearDownClass(cls):
        super(VnfPmThresholdTest, cls).tearDownClass()
        cls.delete_vnf_package(cls.cnf_pkg)

    def setUp(self):
        super(VnfPmThresholdTest, self).setUp()
        self.set_server_callback(
            'PUT', "/-/reload", status_code=202,
            response_headers={"Content-Type": "text/plain"})

    def test_pm_threshold_autoscaling_min(self):
        """Test PM Threshold operations with omitting except for required attributes

        * About attributes:
          Omit except for required attributes.
          Only the following cardinality attributes are set.
          - 1
          - 1..N (1)

        * About LCM operations:
          This test includes the following operations.
          - 1. Create a new VNF instance resource
          - 2. Instantiate a VNF instance
          - 3. PMThreshold-Create 1
          - 4. PM-Threshold 1
          - 5. LCM-Scale
          - 6. PMThreshold-Create 2
          - 7. PM-Threshold 2
          - 8. PMThreshold-Create 3
          - 9. PM-Threshold 3
          - 10. PMThreshold-Create 4
          - 11. PM-Threshold 4
          - 12. Terminate a VNF instance
          - 13. Delete a VNF instance

        * About PMThreshold-Create 1-4/PM-Threshold 1-4:
          PMThreshold-Create 1:
              "objectType": "vnf"
              no "subObjectInstanceIds"
              "performanceMetric": "VCpuUsageMeanVnf.{inst_id}"
          PMThreshold-Create 2:
              "objectType": "Vnfc"
              "subObjectInstanceIds": {rsc}
              "performanceMetric": "VCpuUsageMeanVnf.{inst_id}"
          PMThreshold-Create 3:
              "objectType": "VnfIntCp"
              "subObjectInstanceIds": "eth0"
              "performanceMetric": "ByteIncomingVnfIntCp"
          PMThreshold-Create 4:
              "objectType": "VnfExtCp",
              "subObjectInstanceIds": "eth0"
              "performanceMetric": "ByteIncomingVnfExtCp"
          PMThreshold-Create 1-4 uses different types of "objectType".

          PM-Threshold 1:
              "metric": "VCpuUsageMeanVnf.{inst_id}"
              no "sub_object_instance_id"
          PM-Threshold 2:
              "metric": "VCpuUsageMeanVnf.{inst_id}"
              "sub_object_instance_id": {rsc}
          PM-Threshold 3:
              "metric": "ByteIncomingVnfIntCp"
              "sub_object_instance_id": "eth0",
          PM-Threshold 4:
              "metric": "ByteIncomingVnfExtCp"
              "sub_object_instance_id": "eth0"
        """
        # 1. LCM-Create: Create a new VNF instance resource
        create_req = paramgen.pm_instantiate_cnf_resources_create(
            self.cnf_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # 2. LCM-Instantiate: Instantiate a VNF instance
        vim_id = self.get_k8s_vim_id()
        instantiate_req = paramgen.min_sample_instantiate(vim_id)
        instantiate_req['additionalParams'][
            'lcm-kubernetes-def-files'] = ['Files/kubernetes/deployment.yaml']
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        rsc = body['instantiatedVnfInfo']['vnfcInfo'][0]['id']

        # 3. PMThreshold-Create 1
        pm_expected_attrs = [
            'id',
            'objectType',
            'objectInstanceId',
            'criteria',
            'callbackUri',
            '_links'
        ]
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        sub_req = paramgen.pm_threshold_min(
            callback_uri, inst_id, self.fake_prometheus_ip
        )
        resp, body = self.create_pm_threshold(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, pm_expected_attrs)
        # Test notification
        self.assert_notification_get(callback_url)
        pm_threshold_id_1 = body.get('id')

        # 4. PM-Threshold 1
        sub_req = paramgen.pm_threshold(pm_threshold_id_1, inst_id)
        resp, body = self.pm_threshold(sub_req)
        self.assertEqual(204, resp.status_code)
        # The creation of "pm_threshold" will be asynchronous
        # and wait for the creation to end
        time.sleep(WAIT_CREATE_THRESHOLD_TIME)
        self.assertEqual('UP', self._get_crossing_direction(callback_url))
        self._check_notification(
            callback_url, 'ThresholdCrossedNotification')

        # 5. LCM-Scale
        # Scale out a VNF instance
        scale_out_req = paramgen.scale_out()
        resp, body = self.scale_vnf_instance(inst_id, scale_out_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 6. PMThreshold-Create 2
        pm_expected_attrs_sub = [
            'id',
            'objectType',
            'objectInstanceId',
            'subObjectInstanceIds',
            'criteria',
            'callbackUri',
            '_links'
        ]
        sub_req = paramgen.pm_threshold_min(
            callback_uri, inst_id, self.fake_prometheus_ip,
            objectType="Vnfc",
            sub_object_instance_id=rsc
        )
        resp, body = self.create_pm_threshold(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, pm_expected_attrs_sub)
        self.assert_notification_get(callback_url)
        pm_threshold_id_2 = body.get('id')

        # 7. PM-Threshold 2
        sub_req = paramgen.pm_threshold(
            pm_threshold_id_2, inst_id,
            sub_inst_id=rsc,
        )
        resp, body = self.pm_threshold(sub_req)
        self.assertEqual(204, resp.status_code)
        # The creation of "pm_threshold" will be asynchronous
        # and wait for the creation to end
        time.sleep(WAIT_CREATE_THRESHOLD_TIME)
        self.assertEqual('UP', self._get_crossing_direction(callback_url))
        self._check_notification(
            callback_url, 'ThresholdCrossedNotification')

        # 8. PMThreshold-Create 3
        sub_req = paramgen.pm_threshold_min(
            callback_uri, inst_id, self.fake_prometheus_ip,
            objectType="VnfIntCp",
            sub_object_instance_id="eth0",
            p_metric="ByteIncomingVnfIntCp"
        )
        resp, body = self.create_pm_threshold(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, pm_expected_attrs_sub)
        self.assert_notification_get(callback_url)
        pm_threshold_id_3 = body.get('id')

        # 9. PM-Threshold 3
        sub_req = paramgen.pm_threshold(
            pm_threshold_id_3, inst_id,
            sub_inst_id="eth0",
            p_metric="ByteIncomingVnfIntCp"
        )
        resp, body = self.pm_threshold(sub_req)
        self.assertEqual(204, resp.status_code)
        # The creation of "pm_threshold" will be asynchronous
        # and wait for the creation to end
        time.sleep(WAIT_CREATE_THRESHOLD_TIME)
        self.assertEqual('UP', self._get_crossing_direction(callback_url))
        self._check_notification(
            callback_url, 'ThresholdCrossedNotification')

        # 10. PMThreshold-Create 4
        sub_req = paramgen.pm_threshold_min(
            callback_uri, inst_id, self.fake_prometheus_ip,
            objectType="VnfExtCp",
            sub_object_instance_id="eth0",
            p_metric="ByteIncomingVnfExtCp"
        )
        resp, body = self.create_pm_threshold(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, pm_expected_attrs_sub)
        self.assert_notification_get(callback_url)
        pm_threshold_id_4 = body.get('id')

        # 11. PM-Threshold 4
        sub_req = paramgen.pm_threshold(
            pm_threshold_id_4, inst_id,
            sub_inst_id="eth0",
            p_metric="ByteIncomingVnfExtCp"
        )
        resp, body = self.pm_threshold(sub_req)
        self.assertEqual(204, resp.status_code)
        # The creation of "pm_threshold" will be asynchronous
        # and wait for the creation to end
        time.sleep(WAIT_CREATE_THRESHOLD_TIME)
        self.assertEqual('UP', self._get_crossing_direction(callback_url))
        self._check_notification(
            callback_url, 'ThresholdCrossedNotification')

        resp, body = self.delete_pm_threshold(pm_threshold_id_1)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        resp, body = self.delete_pm_threshold(pm_threshold_id_2)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        resp, body = self.delete_pm_threshold(pm_threshold_id_3)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        resp, body = self.delete_pm_threshold(pm_threshold_id_4)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 12. LCM-Terminate: Terminate VNF
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(
            fields.VnfInstanceState.NOT_INSTANTIATED,
            body['instantiationState'])

        # 13. LCM-Delete: Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

    def test_pm_threshold_autoscaling_max(self):
        """Test PM Threshold operations with all attributes set

        * About attributes:
          All of the following cardinality attributes are set.
          In addition, 0..N or 1..N attributes are set to 2 or more.
          - 0..1 (1)
          - 0..N (2 or more)
          - 1
          - 1..N (2 or more)

        * About LCM operations:
          This test includes the following operations.
          - 1. Create a new VNF instance resource
          - 2. Instantiate a VNF instance
          - 3. PMThreshold-Create 1
          - 4. PM-Threshold 1
          - 5. LCM-Scale
          - 6. PMThreshold-Create 2
          - 7. PM-Threshold 2
          - 8. PMThreshold-Create 3
          - 9. PM-Threshold 3
          - 10. PMThreshold-Create 4
          - 11. PM-Threshold 4
          - 12. Terminate a VNF instance
          - 13. Delete a VNF instance

        * About PMThreshold-Create 1-4/PM-Threshold 1-4:
          PMThreshold-Create 1:
              "objectType": "vnf"
              no "subObjectInstanceIds"
              "performanceMetric": "VCpuUsageMeanVnf.{inst_id}"
          PMThreshold-Create 2:
              "objectType": "Vnfc"
              "subObjectInstanceIds": {rsc}
              "performanceMetric": "VCpuUsageMeanVnf.{inst_id}"
          PMThreshold-Create 3:
              "objectType": "VnfIntCp"
              "subObjectInstanceIds": "eth0"
              "performanceMetric": "ByteIncomingVnfIntCp"
          PMThreshold-Create 4:
              "objectType": "VnfExtCp",
              "subObjectInstanceIds": "eth0"
              "performanceMetric": "ByteIncomingVnfExtCp"
          PMThreshold-Create 1-4 uses different types of "objectType".

          PM-Threshold 1:
              "metric": "VCpuUsageMeanVnf.{inst_id}"
              no "sub_object_instance_id"
          PM-Threshold 2:
              "metric": "VCpuUsageMeanVnf.{inst_id}"
              "sub_object_instance_id": {rsc}
          PM-Threshold 3:
              "metric": "ByteIncomingVnfIntCp"
              "sub_object_instance_id": "eth0",
          PM-Threshold 4:
              "metric": "ByteIncomingVnfExtCp"
              "sub_object_instance_id": "eth0"
        """
        # 1. LCM-Create: Create a new VNF instance resource
        # NOTE: extensions and vnfConfigurableProperties are omitted
        # because they are commented out in etsi_nfv_sol001.
        create_req = paramgen.pm_instantiate_cnf_resources_create(
            self.cnf_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # 2. LCM-Instantiate: Instantiate a VNF instance
        vim_id = self.get_k8s_vim_id()
        instantiate_req = paramgen.min_sample_instantiate(vim_id)
        instantiate_req['additionalParams'][
            'lcm-kubernetes-def-files'] = ['Files/kubernetes/deployment.yaml']
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        rsc = body['instantiatedVnfInfo']['vnfcInfo'][0]['id']

        # 3. PMThreshold-Create 1
        pm_expected_attrs = [
            'id',
            'objectType',
            'objectInstanceId',
            'criteria',
            'callbackUri',
            '_links'
        ]
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        sub_req = paramgen.pm_threshold_max(
            callback_uri, inst_id, self.fake_prometheus_ip)
        resp, body = self.create_pm_threshold(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, pm_expected_attrs)
        # Test notification
        self.assert_notification_get(callback_url)
        pm_threshold_id_1 = body.get('id')

        # 4. PM-Threshold 1
        sub_req = paramgen.pm_threshold(pm_threshold_id_1, inst_id)
        resp, body = self.pm_threshold(sub_req)
        self.assertEqual(204, resp.status_code)
        # The creation of "pm_threshold" will be asynchronous
        # and wait for the creation to end
        time.sleep(WAIT_CREATE_THRESHOLD_TIME)
        self.assertEqual('UP', self._get_crossing_direction(callback_url))
        self._check_notification(
            callback_url, 'ThresholdCrossedNotification')

        # 5. LCM-Scale
        # Scale out a VNF instance
        scale_out_req = paramgen.scale_out()
        resp, body = self.scale_vnf_instance(inst_id, scale_out_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 6. PMThreshold-Create 2
        pm_expected_attrs_sub = [
            'id',
            'objectType',
            'objectInstanceId',
            'subObjectInstanceIds',
            'criteria',
            'callbackUri',
            '_links'
        ]
        sub_req = paramgen.pm_threshold_max(
            callback_uri, inst_id, self.fake_prometheus_ip,
            objectType="Vnfc",
            sub_object_instance_id=rsc
        )
        resp, body = self.create_pm_threshold(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, pm_expected_attrs_sub)
        # Test notification
        self.assert_notification_get(callback_url)
        pm_threshold_id_2 = body.get('id')

        # 7. PM-Threshold 2
        sub_req = paramgen.pm_threshold(
            pm_threshold_id_2, inst_id,
            sub_inst_id=rsc,
        )
        resp, body = self.pm_threshold(sub_req)
        self.assertEqual(204, resp.status_code)
        # The creation of "pm_threshold" will be asynchronous
        # and wait for the creation to end
        time.sleep(WAIT_CREATE_THRESHOLD_TIME)
        self.assertEqual('UP', self._get_crossing_direction(callback_url))
        self._check_notification(
            callback_url, 'ThresholdCrossedNotification')

        # 8. PMThreshold-Create 3
        sub_req = paramgen.pm_threshold_max(
            callback_uri, inst_id, self.fake_prometheus_ip,
            objectType="VnfIntCp",
            sub_object_instance_id="eth0",
            p_metric="ByteIncomingVnfIntCp"
        )
        resp, body = self.create_pm_threshold(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, pm_expected_attrs_sub)
        # Test notification
        self.assert_notification_get(callback_url)
        pm_threshold_id_3 = body.get('id')

        # 9. PM-Threshold 3
        sub_req = paramgen.pm_threshold(
            pm_threshold_id_3, inst_id,
            sub_inst_id="eth0",
            p_metric="ByteIncomingVnfIntCp"
        )
        resp, body = self.pm_threshold(sub_req)
        self.assertEqual(204, resp.status_code)
        # The creation of "pm_threshold" will be asynchronous
        # and wait for the creation to end
        time.sleep(WAIT_CREATE_THRESHOLD_TIME)
        self.assertEqual('UP', self._get_crossing_direction(callback_url))
        self._check_notification(
            callback_url, 'ThresholdCrossedNotification')

        # 10. PMThreshold-Create 4
        sub_req = paramgen.pm_threshold_max(
            callback_uri, inst_id, self.fake_prometheus_ip,
            objectType="VnfExtCp",
            sub_object_instance_id="eth0",
            p_metric="ByteIncomingVnfExtCp"
        )
        resp, body = self.create_pm_threshold(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, pm_expected_attrs_sub)
        # Test notification
        self.assert_notification_get(callback_url)
        pm_threshold_id_4 = body.get('id')

        # 11. PM-Threshold 4
        sub_req = paramgen.pm_threshold(
            pm_threshold_id_4, inst_id,
            sub_inst_id="eth0",
            p_metric="ByteIncomingVnfExtCp"
        )
        resp, body = self.pm_threshold(sub_req)
        self.assertEqual(204, resp.status_code)
        # The creation of "pm_threshold" will be asynchronous
        # and wait for the creation to end
        time.sleep(WAIT_CREATE_THRESHOLD_TIME)
        self.assertEqual('UP', self._get_crossing_direction(callback_url))
        self._check_notification(
            callback_url, 'ThresholdCrossedNotification')

        resp, body = self.delete_pm_threshold(pm_threshold_id_1)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        resp, body = self.delete_pm_threshold(pm_threshold_id_2)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        resp, body = self.delete_pm_threshold(pm_threshold_id_3)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        resp, body = self.delete_pm_threshold(pm_threshold_id_4)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 12. LCM-Terminate: Terminate VNF
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(
            fields.VnfInstanceState.NOT_INSTANTIATED,
            body['instantiationState']
        )

        # 13. LCM-Delete: Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

    def test_pm_threshold_with_all_attributes(self):
        """Test PM Threshold operations with all attributes set

        * About attributes:
          All of the following cardinality attributes are set.
          In addition, 0..N or 1..N attributes are set to 2 or more.
          - 0..1 (1)
          - 0..N (2 or more)
          - 1
          - 1..N (2 or more)

        * About LCM operations:
          This test includes the following operations.
          - 1. Create a new VNF instance resource
          - 2. Instantiate a VNF instance
          - 3. PMThreshold-Create 5
          - 4. PM-Threshold 5-1
          - 5. PM-Threshold 5-2
          - 6. PM-Threshold 5-3
          - 7. PM-Threshold 5-4
          - 8. PM-Threshold 5-5
          - 9. PM-Threshold 5-6
          - 10. Terminate a VNF instance
          - 11. Delete a VNF instance

        * About PMThreshold-Create 5/PM-Threshold 5:
          PMThreshold-Create 5:
              "objectType": "vnf"
              no "subObjectInstanceIds"
              "performanceMetric": "VCpuUsageMeanVnf.{inst_id}"
          This is a mediocre threshold.

          PM-Threshold 5-1:
              "value": 99
          PM-Threshold 5-2:
              "value": 105
          PM-Threshold 5-3:
              "value": 80
          PM-Threshold 5-4:
              "value": 40
          PM-Threshold 5-5:
              "value": 20
          PM-Threshold 5-6:
              "value": 10
          At PM-Threshold 5-1 PM-Threshold 5-5, the notification will be
          triggered.
        """
        # 1. LCM-Create: Create a new VNF instance resource
        # NOTE: extensions and vnfConfigurableProperties are omitted
        # because they are commented out in etsi_nfv_sol001.
        create_req = paramgen.pm_instantiate_cnf_resources_create(
            self.cnf_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # 2. LCM-Instantiate: Instantiate a VNF instance
        vim_id = self.get_k8s_vim_id()
        instantiate_req = paramgen.min_sample_instantiate(vim_id)
        instantiate_req['additionalParams'][
            'lcm-kubernetes-def-files'] = ['Files/kubernetes/deployment.yaml']
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # 3. PMThreshold-Create 5
        pm_expected_attrs = [
            'id',
            'objectType',
            'objectInstanceId',
            'criteria',
            'callbackUri',
            '_links'
        ]
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        sub_req = paramgen.pm_threshold_max(
            callback_uri, inst_id, self.fake_prometheus_ip
        )
        resp, body = self.create_pm_threshold(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, pm_expected_attrs)
        # Test notification
        self.assert_notification_get(callback_url)
        pm_threshold_id_5 = body.get('id')

        # 4. PM-Threshold 5-1
        sub_req = paramgen.pm_threshold(pm_threshold_id_5, inst_id)
        resp, body = self.pm_threshold(sub_req)
        self.assertEqual(204, resp.status_code)
        # The creation of "pm_threshold" will be asynchronous
        # and wait for the creation to end
        time.sleep(WAIT_CREATE_THRESHOLD_TIME)
        self.assertEqual('UP', self._get_crossing_direction(callback_url))
        self._check_notification(
            callback_url, 'ThresholdCrossedNotification')

        # 5. PM-Threshold 5-2
        sub_req = paramgen.pm_threshold(
            pm_threshold_id_5, inst_id,
            value=105,
        )
        resp, body = self.pm_threshold(sub_req)
        self.assertEqual(204, resp.status_code)
        # The creation of "pm_threshold" will be asynchronous
        # and wait for the creation to end
        time.sleep(WAIT_CREATE_THRESHOLD_TIME)
        self._check_no_notification(callback_url)

        # 6. PM-Threshold 5-3
        sub_req = paramgen.pm_threshold(
            pm_threshold_id_5, inst_id,
            value=80
        )
        resp, body = self.pm_threshold(sub_req)
        self.assertEqual(204, resp.status_code)
        # The creation of "pm_threshold" will be asynchronous
        # and wait for the creation to end
        time.sleep(WAIT_CREATE_THRESHOLD_TIME)
        self._check_no_notification(callback_url)

        # 7. PM-Threshold 5-4
        sub_req = paramgen.pm_threshold(
            pm_threshold_id_5, inst_id,
            value=40
        )
        resp, body = self.pm_threshold(sub_req)
        self.assertEqual(204, resp.status_code)
        # The creation of "pm_threshold" will be asynchronous
        # and wait for the creation to end
        time.sleep(WAIT_CREATE_THRESHOLD_TIME)
        self._check_no_notification(callback_url)

        # 8. PM-Threshold 5-5
        sub_req = paramgen.pm_threshold(
            pm_threshold_id_5, inst_id,
            value=20
        )
        resp, body = self.pm_threshold(sub_req)
        self.assertEqual(204, resp.status_code)
        # The creation of "pm_threshold" will be asynchronous
        # and wait for the creation to end
        time.sleep(WAIT_CREATE_THRESHOLD_TIME)
        self.assertEqual('DOWN', self._get_crossing_direction(callback_url))
        self._check_notification(
            callback_url, 'ThresholdCrossedNotification')

        # 9. PM-Threshold 5-6
        sub_req = paramgen.pm_threshold(
            pm_threshold_id_5, inst_id,
            value=10
        )
        resp, body = self.pm_threshold(sub_req)
        self.assertEqual(204, resp.status_code)
        # The creation of "pm_threshold" will be asynchronous
        # and wait for the creation to end
        time.sleep(WAIT_CREATE_THRESHOLD_TIME)
        self._check_no_notification(callback_url)

        resp, body = self.delete_pm_threshold(pm_threshold_id_5)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 10. LCM-Terminate: Terminate VNF
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(
            fields.VnfInstanceState.NOT_INSTANTIATED,
            body['instantiationState']
        )

        # 11. LCM-Delete: Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)
