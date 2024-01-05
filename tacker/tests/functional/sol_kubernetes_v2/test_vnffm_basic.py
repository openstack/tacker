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
from tacker.tests import utils

WAIT_NOTIFICATION_TIME = 5


@ddt.ddt
class VnfFmTest(base_v2.BaseVnfLcmKubernetesV2Test):

    @classmethod
    def setUpClass(cls):
        super(VnfFmTest, cls).setUpClass()

        test_instantiate_cnf_resources_path = utils.test_sample(
            "functional/sol_kubernetes_v2/test_instantiate_cnf_resources")
        cls.cnf_pkg, cls.cnf_vnfd_id = cls.create_vnf_package(
            test_instantiate_cnf_resources_path)

    @classmethod
    def tearDownClass(cls):
        super(VnfFmTest, cls).tearDownClass()

        cls.delete_vnf_package(cls.cnf_pkg)

    def setUp(self):
        super(VnfFmTest, self).setUp()

    def test_faultmanagement_interface_min(self):
        """Test FM operations with all attributes set

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
          - 3. Create a new subscription
          - 4. List subscription with attribute-based
          - 5. Show subscription
          - 6. Alert-Event (firing)
          - 7. FM-List-Alarm
          - 8. FM-Show-Alarm
          - 9. FM-Update-Alarm (acknowledged)
          - 10. FM-Show-Alarm
          - 11. FM-Update-Alarm (unacknowledged)
          - 12. FM-Show-Alarm
          - 13. Alert-Event (resolved)
          - 14. FM-Show-Alarm
          - 15. FM-Delete-Subscription: Delete subscription
          - 16. Terminate a VNF instance
          - 17. Delete a VNF instance
        """

        # 1. LCM-Create: Create a new VNF instance resource
        # NOTE: extensions and vnfConfigurableProperties are omitted
        # because they are commented out in etsi_nfv_sol001.
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
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        vnfc_resource_infos = body['instantiatedVnfInfo'].get(
            'vnfcResourceInfo')
        pod_name = [vnfc_info['computeResource']['resourceId']
                    for vnfc_info in vnfc_resource_infos
                    if vnfc_info['vduId'] == 'VDU2'][0]

        # 3. FM-Create-Subscription: Create a new subscription
        expected_inst_attrs = ['id', 'callbackUri', '_links']
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_min(callback_uri)
        resp, body = self.create_fm_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']
        self.check_resp_body(body, expected_inst_attrs)
        # Test notification
        self.assert_notification_get(callback_url)
        self.addCleanup(self.delete_fm_subscription, sub_id)

        # 4. FM-List-Subscription: List subscription with attribute-based
        # filtering
        expected_attrs = ['id', 'callbackUri', '_links']
        resp, body = self.list_fm_subscriptions()
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for sbsc in body:
            self.check_resp_body(sbsc, expected_attrs)

        # 5. FM-Show-Subscription: Show subscription
        resp, body = self.show_fm_subscription(sub_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 6. Alert-Event (firing)
        alert = paramgen.alert_event_firing(inst_id, pod_name)
        resp, body = self.create_fm_alarm(alert)
        self.assertEqual(204, resp.status_code)
        time.sleep(WAIT_NOTIFICATION_TIME)
        self._check_notification(callback_url, 'AlarmNotification')

        # 7. FM-List-Alarm
        alarm_expected_attrs = [
            'id',
            'managedObjectId',
            'alarmRaisedTime',
            'ackState',
            'perceivedSeverity',
            'eventTime',
            'eventType',
            'probableCause',
            'isRootCause',
            '_links'
        ]
        resp, body = self.list_fm_alarm()
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for sbsc in body:
            self.check_resp_body(sbsc, alarm_expected_attrs)

        # 8. FM-Show-Alarm
        filter_expr = {'filter': f'(eq,managedObjectId,{inst_id})'}
        resp, body = self.list_fm_alarm(filter_expr)
        alarm_id = body[0]['id']
        resp, body = self.show_fm_alarm(alarm_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, alarm_expected_attrs)

        # 9. FM-Update-Alarm (acknowledged)
        expected_attrs = [
            'ackState'
        ]
        update_req = paramgen.update_alarm_acknowledged()
        resp, body = self.update_fm_alarm(alarm_id, update_req)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        self.check_resp_body(body, expected_attrs)

        # 10. FM-Show-Alarm
        expected_attrs = [
            'id',
            'managedObjectId',
            'alarmRaisedTime',
            'ackState',
            'alarmAcknowledgedTime',
            'perceivedSeverity',
            'eventTime',
            'eventType',
            'probableCause',
            'isRootCause',
            '_links'
        ]
        resp, body = self.show_fm_alarm(alarm_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 11. FM-Update-Alarm (unacknowledged)
        update_req = paramgen.update_alarm_unacknowledged()
        resp, _ = self.update_fm_alarm(alarm_id, update_req)
        self.assertEqual(200, resp.status_code)

        # 12. FM-Show-Alarm
        resp, body = self.show_fm_alarm(alarm_id)
        self.assertEqual(200, resp.status_code)
        self.assertIsNone(body.get('alarmAcknowledgedTime'))

        # 13. Alert-Event (resolved)
        alert = paramgen.alert_event_resolved(inst_id, pod_name)
        resp, body = self.create_fm_alarm(alert)
        self.assertEqual(204, resp.status_code)
        time.sleep(WAIT_NOTIFICATION_TIME)
        self._check_notification(callback_url, 'AlarmClearedNotification')

        # 14. FM-Show-Alarm
        resp, body = self.show_fm_alarm(alarm_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, alarm_expected_attrs)

        # 15. FM-Delete-Subscription: Delete subscription
        resp, body = self.delete_fm_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 16. LCM-Terminate: Terminate VNF
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 17. LCM-Delete: Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

    def test_faultmanagement_interface_max(self):
        """Test FM operations with all attributes set

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
          - 3. Create a new subscription
          - 4. List subscription with attribute-based
          - 5. Show subscription
          - 6. Alert-Event (firing)
          - 7. FM-List-Alarm
          - 8. FM-Show-Alarm
          - 9. FM-Update-Alarm (acknowledged)
          - 10. FM-Show-Alarm
          - 11. Alert-Event (resolved)
          - 12. FM-Show-Alarm
          - 13. FM-Delete-Subscription: Delete subscription
          - 14. Terminate a VNF instance
          - 15. Delete a VNF instance
        """

        # 1. LCM-Create: Create a new VNF instance resource
        # NOTE: extensions and vnfConfigurableProperties are omitted
        # because they are commented out in etsi_nfv_sol001.
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
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        vnfc_resource_infos = body['instantiatedVnfInfo'].get(
            'vnfcResourceInfo')
        pod_name = [vnfc_info['computeResource']['resourceId']
                    for vnfc_info in vnfc_resource_infos
                    if vnfc_info['vduId'] == 'VDU2'][0]

        # 3. FM-Create-Subscription: Create a new subscription
        expected_inst_attrs = ['id', 'callbackUri', '_links', 'filter']
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        sub_req = paramgen.sub_create_max(
            callback_uri, self.cnf_vnfd_id, inst_id)
        resp, body = self.create_fm_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']
        self.check_resp_body(body, expected_inst_attrs)
        # Test notification
        self.assert_notification_get(callback_url)

        # 4. FM-List-Subscription: List subscription with attribute-based
        # filtering
        expected_attrs = ['id', 'callbackUri', '_links', 'filter']
        filter_expr = {
            'filter': f'(eq,id,{sub_id})'
        }
        resp, body = self.list_fm_subscriptions(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for sbsc in body:
            self.check_resp_body(sbsc, expected_attrs)

        # 5. FM-Show-Subscription: Show subscription
        resp, body = self.show_fm_subscription(sub_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 6. Alert-Event (firing)
        alert = paramgen.alert_event_firing(inst_id, pod_name)
        resp, body = self.create_fm_alarm(alert)
        self.assertEqual(204, resp.status_code)
        time.sleep(WAIT_NOTIFICATION_TIME)
        self._check_notification(callback_url, 'AlarmNotification')

        # 7. FM-List-Alarm
        alarm_expected_attrs = [
            'id',
            'managedObjectId',
            'alarmRaisedTime',
            'ackState',
            'perceivedSeverity',
            'eventTime',
            'eventType',
            'probableCause',
            'isRootCause',
            '_links'
        ]
        filter_expr = {'filter': f'(eq,managedObjectId,{inst_id})'}
        resp, body = self.list_fm_alarm(filter_expr)
        self.assertEqual(200, resp.status_code)
        alarm_id = body[0]['id']
        self.check_resp_headers_in_get(resp)
        for sbsc in body:
            self.check_resp_body(sbsc, alarm_expected_attrs)

        # 8. FM-Show-Alarm
        resp, body = self.show_fm_alarm(alarm_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, alarm_expected_attrs)

        # 9. FM-Update-Alarm (acknowledged)
        expected_attrs = [
            'ackState'
        ]
        update_req = paramgen.update_alarm_acknowledged()
        resp, body = self.update_fm_alarm(alarm_id, update_req)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        self.check_resp_body(body, expected_attrs)

        # 10. FM-Show-Alarm
        expected_attrs = [
            'id',
            'managedObjectId',
            'alarmRaisedTime',
            'ackState',
            'perceivedSeverity',
            'eventTime',
            'eventType',
            'probableCause',
            'isRootCause',
            '_links'
        ]
        resp, body = self.show_fm_alarm(alarm_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 11. Alert-Event (resolved)
        alert = paramgen.alert_event_resolved(inst_id, pod_name)
        resp, body = self.create_fm_alarm(alert)
        self.assertEqual(204, resp.status_code)
        time.sleep(WAIT_NOTIFICATION_TIME)
        self._check_notification(callback_url, 'AlarmClearedNotification')

        # 12. FM-Show-Alarm
        resp, body = self.show_fm_alarm(alarm_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, alarm_expected_attrs)

        # 13. FM-Delete-Subscription: Delete subscription
        resp, body = self.delete_fm_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 14. LCM-Terminate: Terminate VNF
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 15. LCM-Delete: Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)
