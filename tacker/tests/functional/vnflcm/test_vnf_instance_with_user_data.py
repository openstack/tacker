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

from tacker.objects import fields
from tacker.tests.functional.vnflcm import base as vnflcm_base
import time


class VnfLcmWithUserDataTest(vnflcm_base.BaseVnfLcmTest):

    def _vnf_instance_wait_until_fail_detected(self, id,
            instantiation_state=fields.VnfInstanceState.NOT_INSTANTIATED,
            timeout=vnflcm_base.VNF_INSTANTIATE_ERROR_WAIT):
        time.sleep(timeout)
        _, body = self._show_vnf_instance(id)
        if body['instantiationState'] != instantiation_state:
            error = ("Vnf instance %(id)s status is %(current)s, "
                     "expected status should be %(expected)s")
            self.fail(error % {"id": id,
                "current": body['instantiationState'],
                "expected": instantiation_state})

    def _instantiate_vnf_instance_fail(self, id, request_body):
        resp, _ = self._instantiate_vnf_instance(id, request_body)
        self.assertEqual(202, resp.status_code)

        # Confirm that the state doesn't change from NOT_INSTANTIATED.
        self._vnf_instance_wait_until_fail_detected(id)

    def _wait_show_subscription(self, subscription_id):
        # wait for onboard
        timeout = vnflcm_base.VNF_SUBSCRIPTION_TIMEOUT
        start_time = int(time.time())
        while True:
            resp, body = self._show_subscription(subscription_id)
            if resp.ok:
                return resp, body

            if ((int(time.time()) - start_time) > timeout):
                if resp:
                    resp.raise_for_status()
                raise Exception("Failed to show_subscription")

            time.sleep(1)

    def assert_create_vnf(self, resp, vnf_instance, vnf_pkg_id):
        super().assert_create_vnf(resp, vnf_instance)

        resp, vnf_pkg_info = vnflcm_base._show_vnf_package(
            self.tacker_client, vnf_pkg_id)
        self.assert_vnf_package_usage_state(vnf_pkg_info)

    def assert_delete_vnf(self, resp, vnf_instance_id, vnf_pkg_id):
        super().assert_delete_vnf(resp, vnf_instance_id)

        resp, vnf_pkg_info = vnflcm_base._show_vnf_package(
            self.tacker_client, vnf_pkg_id)
        self.assert_vnf_package_usage_state(
            vnf_pkg_info,
            expected_usage_state=fields.PackageUsageStateType.NOT_IN_USE)

    def assert_instantiate_vnf(
            self,
            resp,
            vnf_instance_id,
            vnf_pkg_id):
        super().assert_instantiate_vnf(resp, vnf_instance_id)

        resp, vnf_pkg_info = vnflcm_base._show_vnf_package(
            self.tacker_client, vnf_pkg_id)
        self.assert_vnf_package_usage_state(vnf_pkg_info)

    def assert_heal_vnf(
            self,
            resp,
            vnf_instance_id,
            vnf_pkg_id,
            expected_stack_status='UPDATE_COMPLETE'):
        super().assert_heal_vnf(
            resp, vnf_instance_id, expected_stack_status=expected_stack_status)

        resp, vnf_pkg_info = vnflcm_base._show_vnf_package(
            self.tacker_client, vnf_pkg_id)
        self.assert_vnf_package_usage_state(vnf_pkg_info)

    def assert_terminate_vnf(
            self,
            resp,
            vnf_instance_id,
            stack_id,
            resource_name_list,
            glance_image_id_list,
            vnf_pkg_id):
        super().assert_terminate_vnf(
            resp,
            vnf_instance_id,
            stack_id,
            resource_name_list,
            glance_image_id_list)

        resp, vnf_pkg_info = vnflcm_base._show_vnf_package(
            self.tacker_client, vnf_pkg_id)
        self.assert_vnf_package_usage_state(vnf_pkg_info)

    def assert_vnf_package_usage_state(
            self,
            vnf_package_info,
            expected_usage_state=fields.PackageUsageStateType.IN_USE):
        self.assertEqual(
            expected_usage_state,
            vnf_package_info['usageState'])
