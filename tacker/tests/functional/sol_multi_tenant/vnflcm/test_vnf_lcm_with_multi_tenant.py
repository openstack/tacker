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

from oslo_serialization import jsonutils

from tacker.objects import fields
from tacker.tests.functional.sol.vnflcm import base as vnflcm_base
from tacker.tests.functional.sol_multi_tenant.vnflcm import base
from tacker.tests.functional.sol_multi_tenant.vnflcm import fake_vnflcm
import tempfile
import time


class VnfLcmWithMultiTenant(base.BaseVnfLcmMultiTenantTest):

    VNF_PACKAGE_DELETE_TIMEOUT = 120

    @classmethod
    def setUpClass(cls):
        super(VnfLcmWithMultiTenant, cls).setUpClass()

        # ModifyVNF specific image create.
        is_setup_error_tenant1 = cls._modify_vnf_specific_image_create(
            cls.glance_client_tenant1)
        if is_setup_error_tenant1:
            cls.is_setup_error = True
            return

        is_setup_error_tenant2 = cls._modify_vnf_specific_image_create(
            cls.glance_client_tenant2)
        if is_setup_error_tenant2:
            cls.is_setup_error = True
            return

    @classmethod
    def _modify_vnf_specific_image_create(cls, glance_clt):
        is_setup_error = False
        images = cls._list_glance_image()
        if len(images) == 0:
            is_setup_error = True
            return is_setup_error

        for image in images:
            specific_image_name = f'{image.name}{2}'
            image_data = {
                "min_disk": image.min_disk,
                "min_ram": image.min_ram,
                "disk_format": image.disk_format,
                "container_format": image.container_format,
                "visibility": image.visibility,
                "name": specific_image_name}

            try:
                images = cls._list_glance_image(specific_image_name)
                if len(images) == 1:
                    break

                _, body = glance_clt.http_client.get(
                    f'{glance_clt.http_client.get_endpoint()}{image.file}')

                with tempfile.TemporaryFile('w+b') as f:
                    for content in body:
                        f.write(content)
                    cls._create_glance_image(image_data, f.read())
            except Exception as e:
                print("Fail, Modify-VNF specific image create.", e, flush=True)
                is_setup_error = True
                return is_setup_error

            return is_setup_error

    def _wait_show_subscription(self, subscription_id, tacker_client):
        # wait for subscription creation
        timeout = vnflcm_base.VNF_SUBSCRIPTION_TIMEOUT
        start_time = int(time.time())
        while True:
            resp, body = self._show_subscription(subscription_id,
                    tacker_client)
            if resp.ok or resp.status_code == 404:
                return resp, body

            if ((int(time.time()) - start_time) > timeout):
                if resp:
                    resp.raise_for_status()
                raise TimeoutError("Failed to show_subscription")

            time.sleep(1)

    def _delete_vnf_package(self, package_uuid, http_client):
        url = os.path.join(self.base_url, package_uuid)
        resp, _ = http_client.do_request(url, "DELETE")
        self.assertEqual(204, resp.status_code)

    def _wait_for_delete(self, package_uuid, http_client):
        show_url = os.path.join(self.base_url, package_uuid)
        timeout = self.VNF_PACKAGE_DELETE_TIMEOUT
        start_time = int(time.time())
        while True:
            resp, body = http_client.do_request(show_url, "GET")
            if (404 == resp.status_code):
                return resp, body

            if (int(time.time()) - start_time) > timeout:
                raise Exception("Failed to delete package")
            time.sleep(1)

    def _disable_operational_state(self, package_uuid, http_client):
        update_req_body = jsonutils.dumps({
            "operationalState": "DISABLED"})

        resp, _ = http_client.do_request(
            '{base_path}/{id}'.format(id=package_uuid,
                                      base_path=self.base_url),
            "PATCH", content_type='application/json',
            body=update_req_body)
        self.assertEqual(200, resp.status_code)

    def assert_vnf_package_usage_state(
            self,
            vnf_package_info,
            expected_usage_state=fields.PackageUsageStateType.IN_USE):
        self.assertEqual(
            expected_usage_state,
            vnf_package_info['usageState'])

    def assert_create_vnf(self, resp, vnf_instance, vnf_pkg_id,
            tacker_client, fake_server_manager):
        super().assert_create_vnf(resp, vnf_instance,
            fake_server_manager)

        resp, vnf_pkg_info = vnflcm_base._show_vnf_package(
            tacker_client, vnf_pkg_id)
        self.assert_vnf_package_usage_state(vnf_pkg_info)

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

    def test_subscription_functionality(self):
        """Test subscription operations with member role users.

        In this test case, we do following steps.
        Note: User A belongs to Tenant 1(t1).
              User B belongs to Tenant 2(t2).
            - Create subscription.
              - User A registers Subscription A(Notification Server A).
              - User B registers Subscription B(Notification Server B).
            - Show Subscription
              - User A only gets information about Subscription A.
              - User B only gets information about Subscription B.
            - List Subscription
              - User A gets subscription list and confirms only
                Subscription A is output.
              - User B gets subscription list and confirms only
                Subscription B is output.
            - Delete Subscription
              - User A deletes Subscription A.
              - User B deletes Subscription B.
        TODO(manpreetk): Only positive test cases are validated in
        Y-release.
        Negative test cases
              - User A fails to delete Subscription B.
              - User B fails to delete Subscription A.
        Validation of negative test cases would require design changes
        in Fake NFVO server, which could be implemented in the upcoming
        cycle.
        """
        # Create subscription
        # User A registers Subscription A.
        callback_url = os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        req_body = fake_vnflcm.Subscription.make_create_request_body(
            'http://localhost:{}{}'.format(
                base.FAKE_SERVER_MANAGER_T1.SERVER_PORT_T1,
                callback_url))
        resp_t1, resp_body_t1 = self._register_subscription(req_body,
            self.http_client_tenant1)
        self.assertEqual(201, resp_t1.status_code)
        self.assert_http_header_location_for_subscription(
            resp_t1.headers)
        self.assert_notification_get(callback_url,
            base.FAKE_SERVER_MANAGER_T1)
        subscription_id_t1 = resp_body_t1.get('id')

        # User B registers Subscription B
        callback_url = os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        req_body_t2 = fake_vnflcm.Subscription.make_create_request_body(
            'http://localhost:{}{}'.format(
                base.FAKE_SERVER_MANAGER_T2.SERVER_PORT_T2,
                callback_url))
        resp_t2, resp_body_t2 = self._register_subscription(
            req_body_t2, self.http_client_tenant2)
        self.assertEqual(201, resp_t2.status_code)
        self.assert_http_header_location_for_subscription(
            resp_t2.headers)
        self.assert_notification_get(callback_url,
            base.FAKE_SERVER_MANAGER_T2)
        subscription_id_t2 = resp_body_t2.get('id')

        # Show Subscription
        # User A gets information for Subscription A
        resp_t1, resp_body_show_t1 = self._wait_show_subscription(
            subscription_id_t1, self.tacker_client_t1)
        self.assert_subscription_show(resp_t1, resp_body_show_t1)

        # User B gets information for Subscription B
        resp_t2, resp_body_show_t2 = self._wait_show_subscription(
            subscription_id_t2, self.tacker_client_t2)
        self.assert_subscription_show(resp_t2, resp_body_show_t2)

        # List Subscription
        # User A gets subscription list
        resp, _ = self._list_subscription(self.tacker_client_t1)
        self.assertEqual(200, resp_t1.status_code)

        # Confirm subscription A
        filter_expr = {
            'filter': "filter=(eq,id,{})".format(
                resp_body_show_t1.get('id'))}
        resp, subscription_body_t1 = self._list_subscription_filter(
            self.http_client_tenant1,
            params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(subscription_body_t1))

        # User B gets subscription list
        resp_t2, _ = self._list_subscription(
            self.tacker_client_t2)
        self.assertEqual(200, resp_t2.status_code)

        # Confirm subscription B
        filter_expr = {
            'filter': "filter=(eq,id,{})".format(
                resp_body_show_t2.get('id'))}
        resp, subscription_body_t2 = self._list_subscription_filter(
            self.http_client_tenant2,
            params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(subscription_body_t2))

        # Delete subscription
        # User A deletes Subscription A
        self.addCleanup(self._delete_subscription,
            subscription_id_t1, self.tacker_client_t1)

        # User B deletes Subscription B
        self.addCleanup(self._delete_subscription,
            subscription_id_t2, self.tacker_client_t2)

    def test_vnf_package_functionality(self):
        """Test VNF package operations with member role users.

        In this test case, we do following steps.
        Note: User A belongs to Tenant 1.
              User B belongs to Tenant 2.
            - Create and Upload VNF Package
              - User A creates VNF Package A.
              - User A uploads VNF Package A.
              - User B creates VNF Package B.
              - User B uploads VNF Package B.
            - List VNF Package
              - User A gets VNF package list and confirms only
                VNF Package A is output.
              - User B gets VNF package list and confirms only
                VNF Package B is output.
            - Show VNF Package
              - User A only gets information about VNF Package A.
              - User B only gets information about VNF Package B.
            - Delete VNF Package
              - User A deletes VNF Package A.
              - User B deletes VNF Package B.
        TODO(manpreetk): Only positive test cases are validated in
        Y-release.
        Negative test cases
              - User A fails to delete VNF Package B.
              - User B fails to delete VNF Package A.
        Validation of negative test cases would require design changes
        in Fake NFVO server, which could be implemented in the upcoming
        cycle.
        """
        # Create and Upload VNF Package
        # User A creates VNF Package A
        sample_name = 'mt_functional1'
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)

        # User A uploads VNF Package A
        vnf_pkg_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client_t1, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # User B creates VNF Package B
        sample_name_t2 = 'mt_functional1'
        csar_package_path_t2 = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name_t2))
        tempname_t2, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path_t2)

        # User B uploads VNF Package B
        vnf_pkg_id2, vnfd_id2 = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client_t2, user_defined_data={
                "key": sample_name_t2}, temp_csar_path=tempname_t2)

        # List VNF Package
        # User A gets VNF package list and confirms only VNF Package A
        # is output.
        resp, body = self.http_client_tenant1.do_request(
            self.base_url, "GET")
        self.assertEqual(200, resp.status_code)

        package_id = [obj['id'] for obj in body]
        self.assertIn(vnf_pkg_id, package_id)

        # User B gets VNF package list and confirms only VNF Package B
        # is output.
        resp_t2, body_t2 = self.http_client_tenant2.do_request(
            self.base_url, "GET")
        self.assertEqual(200, resp_t2.status_code)

        package_id = [obj['id'] for obj in body_t2]
        self.assertIn(vnf_pkg_id2, package_id)

        # Show VNF Package
        # User A only gets information about VNF Package A
        show_url = os.path.join(self.base_url, vnf_pkg_id)
        resp, body = self.http_client_tenant1.do_request(
            show_url, "GET")
        self.assertEqual(200, resp.status_code)

        # User B only gets information about VNF Package B
        show_url_t2 = os.path.join(self.base_url, vnf_pkg_id2)
        resp_t2, body_t2 = self.http_client_tenant2.do_request(
            show_url_t2, "GET")
        self.assertEqual(200, resp_t2.status_code)

        # Delete VNF Package
        # User A deletes VNF Package A
        self._disable_operational_state(vnf_pkg_id,
            self.http_client_tenant1)
        self._delete_vnf_package(vnf_pkg_id, self.http_client_tenant1)
        self._wait_for_delete(vnf_pkg_id, self.http_client_tenant1)

        # User B deletes VNF Package B
        self._disable_operational_state(vnf_pkg_id2,
            self.http_client_tenant2)
        self._delete_vnf_package(vnf_pkg_id2, self.http_client_tenant2)
        self._wait_for_delete(vnf_pkg_id2, self.http_client_tenant2)

    def test_vnf_instantiation_by_vim_of_different_tenant_and_role(self):
        """Test VNF instantiation by VIM of differnt tenant.

        In this test case, we do following steps.
        Note: User A is an admin role user belongs to Tenant 1.
              User B is a non-admin role user belongs to Tenant 2.
            - Create VNF Instance
              - User B creates VNF Instance B using VNF Package B.
            - Instantiate VNF
              - User A fails to instantiates VNF Instance B, both
                VNF and VIM belong to different tenant.
        """
        # Pre-Setting
        # User B registers Subscription B.
        callback_url = os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        req_body_t2 = fake_vnflcm.Subscription.make_create_request_body(
            'http://localhost:{}{}'.format(
                base.FAKE_SERVER_MANAGER_T2.SERVER_PORT_T2,
                callback_url))
        resp_t2, resp_body_t2 = self._register_subscription(
            req_body_t2, self.http_client_tenant2)
        self.assertEqual(201, resp_t2.status_code)
        self.assert_http_header_location_for_subscription(
            resp_t2.headers)
        self.assert_notification_get(callback_url,
            base.FAKE_SERVER_MANAGER_T2)
        subscription_id_t2 = resp_body_t2.get('id')
        self.addCleanup(
            self._delete_subscription,
            subscription_id_t2,
            self.tacker_client_t2)

        # Create and Upload VNF Package
        # User B creates VNF Package B
        sample_name_t2 = 'mt_functional1'
        csar_package_path_t2 = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name_t2))
        tempname_t2, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path_t2)

        # User B uploads VNF Package B
        vnf_pkg_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client_t2, user_defined_data={
                "key": sample_name_t2}, temp_csar_path=tempname_t2)

        # Post Setting: Reserve deleting VNF package.
        self.addCleanup(vnflcm_base._delete_vnf_package,
            self.tacker_client_t2, vnf_pkg_id)

        # Create VNF Instance
        # User B creates VNF Instance B using VNF Package B
        resp_t2, vnf_instance_t2 = self._create_vnf_instance_from_body(
            fake_vnflcm.VnfInstances.make_create_request_body(vnfd_id),
            self.http_client_tenant2)
        vnf_instance_id_t2 = vnf_instance_t2.get('id')
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id_t2,
            fake_server_manager=base.FAKE_SERVER_MANAGER_T2)
        self.assert_create_vnf(resp_t2, vnf_instance_t2,
            vnf_pkg_id,
            self.tacker_client_t2,
            base.FAKE_SERVER_MANAGER_T2)

        # Instantiate VNF instance
        # User A fails to instantiate VNF Instance B as both VIM and VNF
        # belongs to differernt tenants
        request_body = fake_vnflcm.VnfInstances.make_inst_request_body(
            'nfv_user',
            self.vim['tenant_id'], self.ext_networks,
            self.ext_mngd_networks,
            self.ext_link_ports, self.ext_subnets)
        resp, _ = self._instantiate_vnf_instance(vnf_instance_id_t2,
            request_body, self.http_client)
        self.assertEqual(202, resp.status_code)
        self._vnf_instance_wait_until_fail_detected(vnf_instance_id_t2)
