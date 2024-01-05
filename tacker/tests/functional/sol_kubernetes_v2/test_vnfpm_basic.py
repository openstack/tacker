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
class VnfPmTest(base_v2.BaseVnfLcmKubernetesV2Test):

    @classmethod
    def setUpClass(cls):
        super(VnfPmTest, cls).setUpClass()

        test_instantiate_cnf_resources_path = utils.test_sample(
            "functional/sol_kubernetes_v2/test_instantiate_cnf_resources")
        cls.cnf_pkg, cls.cnf_vnfd_id = cls.create_vnf_package(
            test_instantiate_cnf_resources_path)

    @classmethod
    def tearDownClass(cls):
        super(VnfPmTest, cls).tearDownClass()
        cls.delete_vnf_package(cls.cnf_pkg)

    def setUp(self):
        super(VnfPmTest, self).setUp()
        self.set_server_callback(
            'PUT', "/-/reload", status_code=202,
            response_headers={"Content-Type": "text/plain"})

    def test_performancemanagement_interface_min(self):
        """Test PM operations with all attributes set

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
          - 3. PMJob-Create
          - 4. PMJob-Update
          - 5. PM-Event
          - 6. PMJob-List
          - 7. PMJob-Show
          - 8. PMJob-Report-Show
          - 9. PMJob-Delete
          - 10. Terminate a VNF instance
          - 11. Delete a VNF instance
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

        # 3. PMJob-Create
        pm_expected_attrs = [
            'id',
            'objectType',
            'objectInstanceIds',
            'criteria',
            'callbackUri',
            '_links'
        ]
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        sub_req = paramgen.pm_job_min(
            callback_uri, inst_id, self.fake_prometheus_ip)
        resp, body = self.create_pm_job(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, pm_expected_attrs)
        # Test notification
        self.assert_notification_get(callback_url)
        pm_job_id = body.get('id')

        # 4. PMJob-Update
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_url = f"{callback_url}_1"
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        self.set_server_callback('GET', callback_url, status_code=204)
        self.set_server_callback('POST', callback_url, status_code=204)
        update_req = paramgen.update_pm_job(callback_uri)
        resp, body = self.update_pm_job(pm_job_id, update_req)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        # Test notification
        self.assert_notification_get(callback_url)

        # 5. PMJob-Event
        sub_req = paramgen.pm_event(pm_job_id, inst_id)
        resp, body = self.create_pm_event(sub_req)
        self.assertEqual(204, resp.status_code)
        time.sleep(WAIT_NOTIFICATION_TIME)
        self._check_notification(
            callback_url, 'PerformanceInformationAvailableNotification')

        # 6. PMJob-List
        resp, body = self.list_pm_job()
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for sbsc in body:
            self.check_resp_body(sbsc, pm_expected_attrs)

        # 7. PMJob-Show
        resp, body = self.show_pm_job(pm_job_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, pm_expected_attrs)
        reports = body['reports']
        href = reports[0]['href']
        report_id = href.split('/')[-1]

        # 8. PMJob-Report-Show
        expected_attrs = ['entries']
        resp, body = self.show_pm_job_report(pm_job_id, report_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 9. PMJob-Delete
        resp, body = self.delete_pm_job(pm_job_id)
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
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 11. LCM-Delete: Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

    def test_performancemanagement_interface_max(self):
        """Test PM operations with all attributes set

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
          - 3. PMJob-Create
          - 4. PMJob-Update
          - 5. PM-Event
          - 6. PMJob-List
          - 7. PMJob-Show
          - 8. PMJob-Report-Show
          - 9. PMJob-Delete
          - 10. Terminate a VNF instance
          - 11. Delete a VNF instance
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

        # 3. PMJob-Create
        pm_expected_attrs = [
            'id',
            'objectType',
            'objectInstanceIds',
            'criteria',
            'callbackUri',
            '_links'
        ]
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        sub_req = paramgen.pm_job_max(
            callback_uri, inst_id, self.fake_prometheus_ip)
        resp, body = self.create_pm_job(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, pm_expected_attrs)
        # Test notification
        self.assert_notification_get(callback_url)
        pm_job_id = body.get('id')

        # 4. PMJob-Update
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_url = f"{callback_url}_1"
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        self.set_server_callback('GET', callback_url, status_code=204)
        self.set_server_callback('POST', callback_url, status_code=204)
        update_req = paramgen.update_pm_job(callback_uri)
        resp, body = self.update_pm_job(pm_job_id, update_req)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        # Test notification
        self.assert_notification_get(callback_url)

        # 5. PMJob-Event
        sub_req = paramgen.pm_event(pm_job_id, inst_id)
        resp, body = self.create_pm_event(sub_req)
        self.assertEqual(204, resp.status_code)
        time.sleep(WAIT_NOTIFICATION_TIME)
        self._check_notification(
            callback_url, 'PerformanceInformationAvailableNotification')

        # 6. PMJob-List
        filter_expr = {'filter': '(eq,objectType,VirtualCompute)'}
        resp, body = self.list_pm_job(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for sbsc in body:
            self.check_resp_body(sbsc, pm_expected_attrs)

        # 7. PMJob-Show
        resp, body = self.show_pm_job(pm_job_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, pm_expected_attrs)
        reports = body['reports']
        href = reports[0]['href']
        report_id = href.split('/')[-1]

        # 8. PMJob-Show-Report
        expected_attrs = ['entries']
        resp, body = self.show_pm_job_report(pm_job_id, report_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 9. PMJob-Delete
        resp, body = self.delete_pm_job(pm_job_id)
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
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 11. LCM-Delete: Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

    def test_prometheus_plugin_external_data(self):
        """Test PM operations with all performanceMetric

        * About PM operations:
          This test includes the following operations.
          - 1. Create a new VNF instance resource
          - 2. Instantiate a VNF instance
          (loop for each performanceMetric)
            - 3. PMJob-Create
            - 4. PMJob-Delete
          - 5. Terminate a VNF instance
          - 6. Delete a VNF instance
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

        pm_expected_attrs = [
            'id',
            'objectType',
            'objectInstanceIds',
            'criteria',
            'callbackUri',
            '_links'
        ]
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        pm_job_list = paramgen.pm_job_external(
            callback_uri, inst_id, self.fake_prometheus_ip, rsc)

        for job in pm_job_list:
            print(f"{job['criteria']['performanceMetric'][0]}")
            # 3. PMJob-Create
            resp, body = self.create_pm_job(job)
            self.assertEqual(201, resp.status_code)
            self.check_resp_headers_in_create(resp)
            self.check_resp_body(body, pm_expected_attrs)
            pm_job_id = body.get('id')

            # 4. PMJob-Delete
            resp, body = self.delete_pm_job(pm_job_id)
            self.assertEqual(204, resp.status_code)
            self.check_resp_headers_in_delete(resp)

        # 5. LCM-Terminate: Terminate VNF
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

        # 6. LCM-Delete: Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)
