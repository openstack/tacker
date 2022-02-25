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
import time

from oslo_serialization import jsonutils

from tacker.objects import fields
from tacker.tests.functional import base
from tacker.tests.functional.common.fake_server import FakeServerManager
from tacker.tests.functional.sol.vnflcm import base as vnflcm_base
from tacker.tests import utils

FAKE_SERVER_MANAGER_T1 = FakeServerManager()
FAKE_SERVER_PORT_T1 = 9995
FAKE_SERVER_MANAGER_T2 = FakeServerManager()
FAKE_SERVER_PORT_T2 = 9996
VNF_PACKAGE_UPLOAD_TIMEOUT = 300
WAIT_TIMEOUT_ERR_MSG = ("Failed to %(action)s, process could not be completed"
                        " within %(timeout)s seconds")
RETRY_WAIT_TIME = 5


class BaseVnfLcmKubernetesMultiTenantTest(vnflcm_base.BaseVnfLcmTest):

    prepare_fake_server = False

    @classmethod
    def setUpClass(cls):
        super(BaseVnfLcmKubernetesMultiTenantTest, cls).setUpClass()
        cls.tacker_client_tenant1 = base.BaseTackerTest.tacker_http_client(
            'local-tenant1-vim.yaml')
        cls.tacker_client_tenant2 = base.BaseTackerTest.tacker_http_client(
            'local-tenant2-vim.yaml')

        cls.base_subscriptions_url = "/vnflcm/v1/subscriptions"
        cls.base_vnf_instances_url = "/vnflcm/v1/vnf_instances"
        cls.base_vnf_package_url = "/vnfpkgm/v1/vnf_packages"
        cls.base_vnf_lcm_op_occs_url = "/vnflcm/v1/vnf_lcm_op_occs"

        # Set up fake NFVO server for tenant1 and tenant2
        cls.servers = {FAKE_SERVER_PORT_T1: FAKE_SERVER_MANAGER_T1,
                       FAKE_SERVER_PORT_T2: FAKE_SERVER_MANAGER_T2}
        # NOTE: Create both server in parallel, otherwise they can
        # cause (especially server start) job timeout.
        for port, manager in cls.servers.items():
            cls._prepare_start_fake_server(manager, port)

    @classmethod
    def tearDownClass(cls):
        super(BaseVnfLcmKubernetesMultiTenantTest, cls).tearDownClass()
        for _, manager in cls.servers.items():
            manager.stop_server()

    def setUp(self):
        super(BaseVnfLcmKubernetesMultiTenantTest, self).setUp()

        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL, self._testMethodName)
        self._clear_history_and_set_callback(
            FAKE_SERVER_MANAGER_T1, callback_url)
        self._clear_history_and_set_callback(
            FAKE_SERVER_MANAGER_T2, callback_url)

        vim_list = self.client.list_vims()
        vim_name_t1 = 'vim-kubernetes-t1'
        self.vim_tenant1 = self.get_vim(vim_list, vim_name_t1)
        vim_name_t2 = 'vim-kubernetes-t2'
        self.vim_tenant2 = self.get_vim(vim_list, vim_name_t2)

    def create_and_upload_vnf_package(
            self, tacker_client, csar_package_name, user_defined_data):
        # create vnf package
        body = jsonutils.dumps({"userDefinedData": user_defined_data})
        _, vnf_package = tacker_client.do_request(
            self.base_vnf_package_url, "POST", body=body)
        vnf_pkg_id = vnf_package['id']

        # upload vnf package
        csar_package_path = ("../../../etc/samples/etsi/nfv/"
                             f"{csar_package_name}")
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                 csar_package_path))

        # Generating unique vnfd id. This is required when multiple workers
        # are running concurrently. The call below creates a new temporary
        # CSAR with unique vnfd id.
        file_path, _ = utils.create_csar_with_unique_vnfd_id(file_path)

        with open(file_path, 'rb') as file_object:
            tacker_client.do_request(
                f"{self.base_vnf_package_url}/{vnf_pkg_id}/package_content",
                "PUT", body=file_object, content_type='application/zip')

        # wait for onboard
        start_time = int(time.time())
        show_url = os.path.join(self.base_vnf_package_url, vnf_pkg_id)
        while True:
            _, body = tacker_client.do_request(show_url, "GET")
            if body['onboardingState'] == "ONBOARDED":
                vnfd_id = body['vnfdId']
                break

            if (int(time.time()) - start_time) > VNF_PACKAGE_UPLOAD_TIMEOUT:
                raise Exception(
                    WAIT_TIMEOUT_ERR_MSG %
                    {
                        "action": "onboard vnf package",
                        "timeout": VNF_PACKAGE_UPLOAD_TIMEOUT
                    }
                )

            time.sleep(RETRY_WAIT_TIME)

        # remove temporarily created CSAR file
        os.remove(file_path)
        return vnf_package['id'], vnfd_id

    def _filter_notify_history(self, callback_url, vnf_instance_id,
                               fake_server_manager=None, clear=True):
        notify_histories = fake_server_manager.get_history(
            callback_url)
        if clear:
            fake_server_manager.clear_history(callback_url)

        return [
            h for h in notify_histories
            if h.request_body.get('vnfInstanceId') == vnf_instance_id]

    def assert_instantiate(
            self, resp, vnf_instance_id, http_client, fake_server_manager):
        self.assertEqual(202, resp.status_code)
        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id,
                                                     http_client)
        self.assert_vnf_state(vnf_instance)

        # FT-checkpoint: Notification
        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = self._filter_notify_history(
            callback_url, vnf_instance_id,
            fake_server_manager=fake_server_manager, clear=False)

        self.assertEqual(3, len(notify_mock_responses))
        self.assert_notification_mock_response(
            notify_mock_responses[0],
            'VnfLcmOperationOccurrenceNotification',
            'STARTING')

        self.assert_notification_mock_response(
            notify_mock_responses[1],
            'VnfLcmOperationOccurrenceNotification',
            'PROCESSING')

        self.assert_notification_mock_response(
            notify_mock_responses[2],
            'VnfLcmOperationOccurrenceNotification',
            'COMPLETED')

    def assert_terminate(self, resp, vnf_instance_id,
                         http_client=None, fake_server_manager=None):
        self.assertEqual(202, resp.status_code)

        resp, vnf_instance = self._show_vnf_instance(
            vnf_instance_id, http_client)
        self.assert_instantiation_state(
            vnf_instance,
            fields.VnfInstanceState.NOT_INSTANTIATED)

        # FT-checkpoint: Notification
        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL, self._testMethodName)
        notify_mock_responses = self._filter_notify_history(
            callback_url, vnf_instance_id,
            fake_server_manager=fake_server_manager, clear=False)

        self.assertEqual(3, len(notify_mock_responses))
        self.assert_notification_mock_response(
            notify_mock_responses[0],
            'VnfLcmOperationOccurrenceNotification',
            'STARTING')

        self.assert_notification_mock_response(
            notify_mock_responses[1],
            'VnfLcmOperationOccurrenceNotification',
            'PROCESSING')

        self.assert_notification_mock_response(
            notify_mock_responses[2],
            'VnfLcmOperationOccurrenceNotification',
            'COMPLETED')

    def delete_vnf_package(self, tacker_client, vnf_package_id):
        url = f'/vnfpkgm/v1/vnf_packages/{vnf_package_id}'

        # Update vnf package before delete
        req_body = jsonutils.dumps({"operationalState": "DISABLED"})
        tacker_client.do_request(url, "PATCH", body=req_body)

        # Delete vnf package before delete
        tacker_client.do_request(url, "DELETE")

    def assert_occ_show(
            self, resp, op_occs_info, http_code, vnf_instance_id, operation):
        self.assertEqual(http_code, resp.status_code)

        if http_code == 200:
            self.assertEqual(
                vnf_instance_id, op_occs_info.get('vnfInstanceId'))
            self.assertEqual(
                operation, op_occs_info.get('operation'))

    def assert_occ_only_one_vnf(
            self, vnf_instance_id_t1, op_occs_info, vnf_instance_id_t2):
        for op_occ in op_occs_info:
            if vnf_instance_id_t1 != op_occ.get('vnfInstanceId'):
                self.assertNotEqual(
                    vnf_instance_id_t2, op_occ.get('vnfInstanceId'))
