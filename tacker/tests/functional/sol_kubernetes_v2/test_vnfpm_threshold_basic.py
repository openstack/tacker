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

WAIT_NOTIFICATION_TIME = 5


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

    def test_pm_threshold_interface_min(self):
        """Test PM Threshold operations with all attributes set

        * About attributes:
          Omit except for required attributes.
          Only the following cardinality attributes are set.
          - 1
          - 1..N (1)

        * About LCM operations:
          This test includes the following operations.
          - 1. Create a new VNF instance resource
          - 2. Instantiate a VNF instance
          - 3. PMThreshold-Create
          - 4. PMThreshold-Update
          - 5. PM-Threshold
          - 6. PMThreshold-List
          - 7. PMThreshold-Show
          - 8. PMThreshold-Delete
          - 9. Terminate a VNF instance
          - 10. Delete a VNF instance
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

        # 3. PMThreshold-Create
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
        pm_threshold_id = body.get('id')

        # 4. PMThreshold-Update
        callback_url = os.path.join(
            self.get_notify_callback_url(),
            self._testMethodName
        )
        callback_url = f'{callback_url}_1'
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        # Because the update of the threshold is executed, the 'callback_url'
        # is updated, so the url of the fake server needs to be modified.
        self.set_server_callback('GET', callback_url, status_code=204)
        self.set_server_callback('POST', callback_url, status_code=204)
        update_req = paramgen.update_pm_threshold(callback_uri)
        resp, body = self.update_pm_threshold(pm_threshold_id, update_req)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, ['callbackUri'])
        # Test notification
        self.assert_notification_get(callback_url)

        # 5. PM-Threshold
        sub_req = paramgen.pm_threshold(pm_threshold_id, inst_id)
        resp, body = self.pm_threshold(sub_req)
        self.assertEqual(204, resp.status_code)
        time.sleep(WAIT_NOTIFICATION_TIME)
        self._check_notification(
            callback_url, 'ThresholdCrossedNotification')

        # 6. PMThreshold-List
        resp, body = self.list_pm_threshold()
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for sbsc in body:
            self.check_resp_body(sbsc, pm_expected_attrs)

        # 7. PMThreshold-Show
        resp, body = self.show_pm_threshold(pm_threshold_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, pm_expected_attrs)

        # 8. PMThreshold-Delete
        resp, body = self.delete_pm_threshold(pm_threshold_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 9. LCM-Terminate: Terminate VNF
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

        # 10. LCM-Delete: Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

    def test_pm_threshold_interface_max(self):
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
          - 3. PMThreshold-Create
          - 4. PMThreshold-Update
          - 5. PM-Threshold
          - 6. PMThreshold-List
          - 7. PMThreshold-Show
          - 8. PMThreshold-Delete
          - 9. Terminate a VNF instance
          - 10. Delete a VNF instance
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

        # 3. PMThreshold-Create
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
        pm_threshold_id = body.get('id')

        # 4. PMThreshold-Update
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_url = f'{callback_url}_1'
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        # Because the update of the threshold is executed, the 'callback_url'
        # is updated, so the url of the fake server needs to be modified.
        self.set_server_callback('GET', callback_url, status_code=204)
        self.set_server_callback('POST', callback_url, status_code=204)
        update_req = paramgen.update_pm_threshold(callback_uri)
        resp, body = self.update_pm_threshold(pm_threshold_id, update_req)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, ['callbackUri'])
        # Test notification
        self.assert_notification_get(callback_url)

        # 5. PM-Threshold
        sub_req = paramgen.pm_threshold(pm_threshold_id, inst_id)
        resp, body = self.pm_threshold(sub_req)
        self.assertEqual(204, resp.status_code)
        time.sleep(WAIT_NOTIFICATION_TIME)
        self._check_notification(
            callback_url, 'ThresholdCrossedNotification')

        # 6. PMThreshold-List
        filter_expr = {'filter': '(eq,objectType,VirtualCompute)'}
        resp, body = self.list_pm_threshold(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for sbsc in body:
            self.check_resp_body(sbsc, pm_expected_attrs)

        # 7. PMThreshold-Show
        resp, body = self.show_pm_threshold(pm_threshold_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, pm_expected_attrs)

        # 8. PMThreshold-Delete
        resp, body = self.delete_pm_threshold(pm_threshold_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 9. LCM-Terminate: Terminate VNF
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

        # 10. LCM-Delete: Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)
