#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os

from tacker.tests.functional.sol.vnflcm import base as vnflcm_base
from tacker.tests.functional.sol_kubernetes_multi_tenant.vnflcm import (
    fake_vnflcm)
from tacker.tests.functional.sol_kubernetes_multi_tenant.vnflcm import base


class VnfLcmKubernetesWithMultiTenant(base.
                                      BaseVnfLcmKubernetesMultiTenantTest):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmKubernetesWithMultiTenant, cls).setUpClass()

    def test_lcm_functionality(self):
        """Test CNF instantiate and terminate with member role users.

        In this test case, we do following steps.
        Note: User A belongs to Tenant 1.
              User B belongs to Tenant 2.
            - Create subscription.
              - User A registers Subscription A(Notification Server A).
              - User B registers Subscription B(Notification Server B).
            - Create and Upload VNF Package
              - User A creates and uploads VNF Package A.
              - User B creates and uploads VNF Package B.
            - Create VNF Instance
              - User A creates VNF Instance A using VNF Package A.
              - User B creates VNF Instance B using VNF Package B.
            - Instantiate VNF
              - User A fails to instantiate VNF Instance B.
              - User B fails to instantiate VNF Instance A.
              - User A instantiates VNF Instance A.
              - User B instantiates VNF Instance B.
            - List LCM operation occurrence
              - User A only sees lcm_op_occ of VNF Instance A.
              - User B only sees lcm_op_occ of VNF Instance B.
            - Show VNF LCM operation occurrence
              - User A succeeds to show lcm_op_occ of VNF Instance A.
              - User A fails to show lcm_op_occ of VNF Instance B.
              - User B succeeds to show lcm_op_occ of VNF Instance B.
              - User B fails to show lcm_op_occ of VNF Instance A.
            - Terminate VNF
              - User A fails to terminate VNF Instance B.
              - User B fails to terminate VNF Instance A.
              - User A succeeds to terminate VNF Instance A.
              - User B succeeds to terminate VNF Instance B.
            - List LCM operation occurrence
              - User A only sees lcm_op_occ of VNF Instance A.
              - User B only sees lcm_op_occ of VNF Instance B.
            - Show VNF LCM operation occurrence
              - User A succeeds to show lcm_op_occ of VNF Instance A.
              - User A fails to show lcm_op_occ of VNF Instance B.
              - User B succeeds to show lcm_op_occ of VNF Instance B.
              - User B fails to show lcm_op_occ of VNF Instance A.
            - Delete VNF Instance
              - User A deletes VNF Instance A.
              - User B deletes VNF Instance B.
            - Delete VNF Package
              - User A deletes VNF Package A.
              - User B deletes VNF Package B.
        """

        # Pre-Setting
        # User A registers Subscription A.
        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        req_body = fake_vnflcm.Subscription.make_create_request_body(
            f'http://localhost:'
            f'{base.FAKE_SERVER_MANAGER_T1.SERVER_PORT_T1}'
            f'{callback_url}')
        resp_t1, resp_body_t1 = self._register_subscription(
            req_body, self.tacker_client_tenant1)
        self.assertEqual(201, resp_t1.status_code)
        self.assert_http_header_location_for_subscription(resp_t1.headers)
        self.assert_notification_get(
            callback_url, base.FAKE_SERVER_MANAGER_T1)
        subscription_id_t1 = resp_body_t1.get('id')
        self.addCleanup(self._delete_subscription, subscription_id_t1,
                        self.tacker_client_tenant1)

        # User B registers Subscription B.
        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL, self._testMethodName)
        req_body_t2 = fake_vnflcm.Subscription.make_create_request_body(
            f'http://localhost:'
            f'{base.FAKE_SERVER_MANAGER_T1.SERVER_PORT_T2}'
            f'{callback_url}')
        resp_t2, resp_body_t2 = self._register_subscription(
            req_body_t2, self.tacker_client_tenant2)
        self.assertEqual(201, resp_t2.status_code)
        self.assert_http_header_location_for_subscription(resp_t2.headers)
        self.assert_notification_get(
            callback_url, base.FAKE_SERVER_MANAGER_T2)
        subscription_id_t2 = resp_body_t2.get('id')
        self.addCleanup(self._delete_subscription, subscription_id_t2,
                        self.tacker_client_tenant2)

        # User A Create and Upload VNF Package A
        sample_name_t1 = 'test_cnf_multi_ns'
        vnf_package_id_t1, vnfd_id_t1 = self.create_and_upload_vnf_package(
            self.tacker_client_tenant1, sample_name_t1,
            {"key": "multi_tenant_t1_functional"})

        # User B Create and Upload VNF Package B
        sample_name_t2 = 'test_cnf_multi_ns'
        vnf_package_id_t2, vnfd_id_t2 = self.create_and_upload_vnf_package(
            self.tacker_client_tenant2, sample_name_t2,
            {"key": "multi_tenant_t2_functional"})

        # Create VNF Instance
        # User A creates VNF Instance A using VNF Package A
        vnf_instance_name_t1 = "multi_tenant_cnf_t1"
        vnf_instance_description_t1 = "multi tenant cnf t1"
        resp_t1, vnf_instance_t1 = self._create_vnf_instance(
            vnfd_id_t1, vnf_instance_name_t1,
            vnf_instance_description_t1, self.tacker_client_tenant1)
        vnf_instance_id_t1 = vnf_instance_t1.get('id')
        self._wait_lcm_done(
            vnf_instance_id=vnf_instance_id_t1,
            fake_server_manager=base.FAKE_SERVER_MANAGER_T1)
        self.assert_create_vnf(
            resp_t1, vnf_instance_t1, base.FAKE_SERVER_MANAGER_T1)

        # User B creates VNF Instance B using VNF Package B
        vnf_instance_name_t2 = "multi_tenant_cnf_t2"
        vnf_instance_description_t2 = "multi tenant cnf t2"
        resp_t2, vnf_instance_t2 = self._create_vnf_instance(
            vnfd_id_t2, vnf_instance_name_t2,
            vnf_instance_description_t2, self.tacker_client_tenant2)
        vnf_instance_id_t2 = vnf_instance_t2.get('id')
        self._wait_lcm_done(
            vnf_instance_id=vnf_instance_id_t2,
            fake_server_manager=base.FAKE_SERVER_MANAGER_T2)
        self.assert_create_vnf(
            resp_t2, vnf_instance_t2, base.FAKE_SERVER_MANAGER_T2)

        # Instantiate vnf instance
        # User A unable to instantiate VNF Instance B
        additional_params_t1 = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/deployment_has_namespace.yaml",
                "Files/kubernetes/namespace01.yaml"
            ],
            "namespace": "multi-namespace01"
        }
        inst_req_body_t1 = fake_vnflcm.VnfInstances.make_inst_request_body(
            self.vim_tenant1['id'], additional_params_t1)
        resp, _ = self._instantiate_vnf_instance(
            vnf_instance_id_t2, inst_req_body_t1, self.tacker_client_tenant1)
        self.assertEqual(404, resp.status_code)

        # User B unable to instantiate VNF Instance A
        additional_params_t2 = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/deployment_has_namespace.yaml",
                "Files/kubernetes/namespace02.yaml"
            ],
            "namespace": "multi-namespace02"
        }
        inst_req_body_t2 = fake_vnflcm.VnfInstances.make_inst_request_body(
            self.vim_tenant2['id'], additional_params_t2)
        resp, _ = self._instantiate_vnf_instance(
            vnf_instance_id_t1, inst_req_body_t2, self.tacker_client_tenant2)
        self.assertEqual(404, resp.status_code)

        # User A instantiate VNF Instance A
        resp, _ = self._instantiate_vnf_instance(
            vnf_instance_id_t1, inst_req_body_t1, self.tacker_client_tenant1)

        self._wait_lcm_done(
            'COMPLETED', vnf_instance_id=vnf_instance_id_t1,
            fake_server_manager=base.FAKE_SERVER_MANAGER_T1)
        self.assert_instantiate(
            resp, vnf_instance_id_t1, self.tacker_client_tenant1,
            base.FAKE_SERVER_MANAGER_T1)

        # User B instantiate VNF Instance B
        resp, _ = self._instantiate_vnf_instance(
            vnf_instance_id_t2, inst_req_body_t2, self.tacker_client_tenant2)
        self._wait_lcm_done(
            'COMPLETED', vnf_instance_id=vnf_instance_id_t2,
            fake_server_manager=base.FAKE_SERVER_MANAGER_T2)
        self.assert_instantiate(
            resp, vnf_instance_id_t2, self.tacker_client_tenant2,
            base.FAKE_SERVER_MANAGER_T2)

        # get vnflcm_op_occ_id for User A
        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL, self._testMethodName)
        notify_mock_responses = (base.FAKE_SERVER_MANAGER_T1.
                                 get_history(callback_url))
        base.FAKE_SERVER_MANAGER_T1.clear_history(callback_url)
        vnflcm_op_occ_id_t1 = notify_mock_responses[0].request_body.get(
            'vnfLcmOpOccId')
        self.assertIsNotNone(vnflcm_op_occ_id_t1)

        # get vnflcm_op_occ_id for User B
        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL, self._testMethodName)
        notify_mock_responses = (base.FAKE_SERVER_MANAGER_T2.
                                 get_history(callback_url))
        base.FAKE_SERVER_MANAGER_T2.clear_history(callback_url)
        vnflcm_op_occ_id_t2 = notify_mock_responses[0].request_body.get(
            'vnfLcmOpOccId')
        self.assertIsNotNone(vnflcm_op_occ_id_t2)

        # List LcmOpOccs
        # User A gets LcmOpOccs List, and should get LcmOpOccs of
        # VNF Instance A
        resp, op_occs_info = self._list_op_occs(
            filter_string='', http_client=self.tacker_client_tenant1)
        self._assert_occ_list(resp, op_occs_info)
        self.assert_occ_only_one_vnf(
            vnf_instance_id_t1, op_occs_info, vnf_instance_id_t2)

        # User B gets LcmOpOccs List, and should get LcmOpOccs of
        # VNF Instance B
        resp, op_occs_info = self._list_op_occs(
            filter_string='', http_client=self.tacker_client_tenant2)
        self._assert_occ_list(resp, op_occs_info)
        self.assert_occ_only_one_vnf(
            vnf_instance_id_t2, op_occs_info, vnf_instance_id_t1)

        # Show LcmOpOccs
        # User A able to show LcmOpOccs List of VNF Instance A
        resp, op_occs_info = self._show_op_occs(
            vnflcm_op_occ_id_t1, self.tacker_client_tenant1)
        self.assert_occ_show(
            resp, op_occs_info, 200, vnf_instance_id_t1, 'INSTANTIATE')

        # User A unable to show LcmOpOccs List of VNF Instance B
        resp, op_occs_info = self._show_op_occs(
            vnflcm_op_occ_id_t2, self.tacker_client_tenant1)
        self.assert_occ_show(resp, op_occs_info, 404, None, None)

        # User B able to show LcmOpOccs List of VNF Instance B
        resp, op_occs_info = self._show_op_occs(
            vnflcm_op_occ_id_t2, self.tacker_client_tenant2)
        self.assert_occ_show(
            resp, op_occs_info, 200, vnf_instance_id_t2, 'INSTANTIATE')

        # User B unable to show LcmOpOccs List of VNF Instance A
        resp, op_occs_info = self._show_op_occs(
            vnflcm_op_occ_id_t1, self.tacker_client_tenant2)
        self.assert_occ_show(resp, op_occs_info, 404, None, None)

        # Terminate VNF
        # User A unable to terminate VNF B
        terminate_req_body_t1 = (fake_vnflcm.VnfInstances
                                 .make_term_request_body())
        resp, _ = self._terminate_vnf_instance(
            vnf_instance_id_t2, terminate_req_body_t1,
            self.tacker_client_tenant1)
        self.assertEqual(404, resp.status_code)

        # User B unable to terminate VNF A
        terminate_req_body_t2 = (fake_vnflcm.VnfInstances
                                 .make_term_request_body())
        resp, _ = self._terminate_vnf_instance(
            vnf_instance_id_t1, terminate_req_body_t2,
            self.tacker_client_tenant2)
        self.assertEqual(404, resp.status_code)

        # User A terminates VNF A
        resp, _ = self._terminate_vnf_instance(
            vnf_instance_id_t1, terminate_req_body_t1,
            self.tacker_client_tenant1)
        self._wait_lcm_done(
            'COMPLETED', vnf_instance_id=vnf_instance_id_t1,
            fake_server_manager=base.FAKE_SERVER_MANAGER_T1)
        self.assert_terminate(
            resp, vnf_instance_id_t1, self.tacker_client_tenant1,
            fake_server_manager=base.FAKE_SERVER_MANAGER_T1)

        # User B terminates VNF B
        resp, _ = self._terminate_vnf_instance(
            vnf_instance_id_t2, terminate_req_body_t2,
            self.tacker_client_tenant2)
        self._wait_lcm_done(
            'COMPLETED', vnf_instance_id=vnf_instance_id_t2,
            fake_server_manager=base.FAKE_SERVER_MANAGER_T2)
        self.assert_terminate(
            resp, vnf_instance_id_t2, self.tacker_client_tenant2,
            fake_server_manager=base.FAKE_SERVER_MANAGER_T2)

        # get vnflcm_op_occ_id for User A
        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL, self._testMethodName)
        notify_mock_responses = (base.FAKE_SERVER_MANAGER_T1.
                                 get_history(callback_url))
        base.FAKE_SERVER_MANAGER_T1.clear_history(callback_url)
        vnflcm_op_occ_id_t1 = notify_mock_responses[0].request_body.get(
            'vnfLcmOpOccId')
        self.assertIsNotNone(vnflcm_op_occ_id_t1)

        # get vnflcm_op_occ_id for User B
        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL, self._testMethodName)
        notify_mock_responses = (base.FAKE_SERVER_MANAGER_T2.
                                 get_history(callback_url))
        base.FAKE_SERVER_MANAGER_T2.clear_history(callback_url)
        vnflcm_op_occ_id_t2 = notify_mock_responses[0].request_body.get(
            'vnfLcmOpOccId')
        self.assertIsNotNone(vnflcm_op_occ_id_t2)

        # List LcmOpOccs
        # User A gets LcmOpOccs List, and should get LcmOpOccs of
        # VNF Instance A
        resp, op_occs_info = self._list_op_occs(
            filter_string='', http_client=self.tacker_client_tenant1)
        self._assert_occ_list(resp, op_occs_info)
        self.assert_occ_only_one_vnf(
            vnf_instance_id_t1, op_occs_info, vnf_instance_id_t2)

        # User B gets LcmOpOccs List, and should get LcmOpOccs of
        # VNF Instance B
        resp, op_occs_info = self._list_op_occs(
            filter_string='', http_client=self.tacker_client_tenant2)
        self._assert_occ_list(resp, op_occs_info)
        self.assert_occ_only_one_vnf(
            vnf_instance_id_t2, op_occs_info, vnf_instance_id_t1)

        # Show LcmOpOccs
        # User A able to show LcmOpOccs List of VNF Instance A
        resp, op_occs_info = self._show_op_occs(
            vnflcm_op_occ_id_t1, self.tacker_client_tenant1)
        self.assert_occ_show(
            resp, op_occs_info, 200, vnf_instance_id_t1, 'TERMINATE')

        # User A unable to show LcmOpOccs List of VNF Instance B
        resp, op_occs_info = self._show_op_occs(
            vnflcm_op_occ_id_t2, self.tacker_client_tenant1)
        self.assert_occ_show(resp, op_occs_info, 404, None, None)

        # User B able to show LcmOpOccs List of VNF Instance B
        resp, op_occs_info = self._show_op_occs(
            vnflcm_op_occ_id_t2, self.tacker_client_tenant2)
        self.assert_occ_show(
            resp, op_occs_info, 200, vnf_instance_id_t2, 'TERMINATE')

        # User B unable to show LcmOpOccs List of VNF Instance A
        resp, op_occs_info = self._show_op_occs(
            vnflcm_op_occ_id_t1, self.tacker_client_tenant2)
        self.assert_occ_show(resp, op_occs_info, 404, None, None)

        # Delete VNF
        # User A deletes VNF Instance A
        resp, _ = self._delete_vnf_instance(
            vnf_instance_id_t1, self.tacker_client_tenant1)
        self.assertEqual(vnf_instance_t1['id'], vnf_instance_id_t1)

        # User B deletes VNF Instance B
        resp, _ = self._delete_vnf_instance(
            vnf_instance_id_t2, self.tacker_client_tenant2)
        self.assertEqual(vnf_instance_t2['id'], vnf_instance_id_t2)

        # Deleting vnf package.
        self.delete_vnf_package(self.tacker_client_tenant1, vnf_package_id_t1)
        self.delete_vnf_package(self.tacker_client_tenant2, vnf_package_id_t2)
