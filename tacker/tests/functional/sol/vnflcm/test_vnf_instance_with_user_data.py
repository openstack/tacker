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
from oslo_utils import uuidutils
from tacker.objects import fields
from tacker.tests.functional.sol.vnflcm import base as vnflcm_base
from tacker.tests.functional.sol.vnflcm import fake_vnflcm
from tacker.vnfm.infra_drivers.openstack import constants as infra_cnst
import tempfile
import time


class VnfLcmWithUserDataTest(vnflcm_base.BaseVnfLcmTest):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmWithUserDataTest, cls).setUpClass()
        images = cls._list_glance_image()
        if len(images) == 0:
            cls.is_setup_error = True
            return

        # ModifyVNF specific image create.
        for image in images:
            specific_image_name = image.name + '2'
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

                _, body = cls.glance_client.http_client.get(
                    cls.glance_client.http_client.get_endpoint() + image.file)

                with tempfile.TemporaryFile('w+b') as f:
                    for content in body:
                        f.write(content)
                    cls._create_glance_image(image_data, f.read())
            except Exception as e:
                print("Fail, Modify-VNF specific image create.", e, flush=True)
                cls.is_setup_error = True
                return

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
                raise TimeoutError("Failed to show_subscription")

            time.sleep(1)

    def test_inst_scaling_term(self):
        """Test basic life cycle operations with sample VNFD.

        In this test case, we do following steps.
            - Create subscription.
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF.
            - Get VNF informations.
            - Scale-Out VNF
            - Scale-In VNF
            - Terminate VNF
            - Delete VNF
            - Delete subscription
        """
        # Create subscription and register it.
        callback_url = os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        request_body = fake_vnflcm.Subscription.make_create_request_body(
            'http://localhost:{}{}'.format(
                vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                callback_url))
        resp, response_body = self._register_subscription(request_body)
        self.assertEqual(201, resp.status_code)
        self.assert_http_header_location_for_subscription(resp.headers)
        self.assert_notification_get(callback_url)
        subscription_id = response_body.get('id')
        self.addCleanup(
            self._delete_subscription,
            subscription_id)

        # Pre Setting: Create vnf package.
        sample_name = 'functional5'
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Post Setting: Reserve deleting vnf package.
        self.addCleanup(vnflcm_base._delete_vnf_package, self.tacker_client,
            vnf_package_id)

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance_from_body(
            fake_vnflcm.VnfInstances.make_create_request_body(vnfd_id))
        vnf_instance_id = vnf_instance['id']
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_create_vnf(resp, vnf_instance, vnf_package_id)
        self.addCleanup(self._delete_vnf_instance, vnf_instance_id)

        # Instantiate vnf instance
        request_body = fake_vnflcm.VnfInstances.\
            make_inst_request_body_include_num_dynamic(
                self.vim['tenant_id'], self.ext_networks,
                self.ext_mngd_networks, self.ext_link_ports, self.ext_subnets)
        resp, _ = self._instantiate_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_instantiate_vnf(resp, vnf_instance_id, vnf_package_id)

        # Show vnf instance
        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id)
        self.assertEqual(200, resp.status_code)

        # Scale-out vnf instance
        stack = self._get_heat_stack(vnf_instance_id)
        pre_stack_resource_list = self._get_heat_resource_list(stack.id, 2)

        request_body = fake_vnflcm.VnfInstances.make_scale_request_body(
            'SCALE_OUT')
        resp, _ = self._scale_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)

        post_stack_resource_list = self._get_heat_resource_list(stack.id, 2)
        self._assert_scale_vnf(resp, vnf_instance_id, vnf_package_id,
            pre_stack_resource_list, post_stack_resource_list,
            scale_type='SCALE_OUT', expected_stack_status='CREATE_COMPLETE')

        # Scale-in vnf instance
        stack = self._get_heat_stack(vnf_instance_id)
        pre_stack_resource_list = self._get_heat_resource_list(stack.id, 2)

        request_body = (fake_vnflcm.VnfInstances
                        .make_reverse_scale_request_body('SCALE_IN'))
        resp, _ = self._scale_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)

        post_stack_resource_list = self._get_heat_resource_list(stack.id, 2)
        self._assert_scale_vnf(resp, vnf_instance_id, vnf_package_id,
            pre_stack_resource_list, post_stack_resource_list,
            scale_type='SCALE_IN', expected_stack_status='UPDATE_COMPLETE')

        # Terminate VNF
        stack = self._get_heat_stack(vnf_instance_id)
        resources_list = self._get_heat_resource_list(stack.id)
        resource_name_list = [r.resource_name for r in resources_list]
        glance_image_id_list = self._get_glance_image_list_from_stack_resource(
            stack.id, resource_name_list)

        terminate_req_body = fake_vnflcm.VnfInstances.make_term_request_body()
        resp, _ = self._terminate_vnf_instance(
            vnf_instance_id, terminate_req_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_terminate_vnf(resp, vnf_instance_id, stack.id,
            resource_name_list, glance_image_id_list, vnf_package_id)

        # Delete VNF
        resp, _ = self._delete_vnf_instance(vnf_instance_id)
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_delete_vnf(resp, vnf_instance_id, vnf_package_id)

        # Subscription delete
        resp, response_body = self._delete_subscription(subscription_id)
        self.assertEqual(204, resp.status_code)

        resp, _ = self._show_subscription(subscription_id)
        self.assertEqual(404, resp.status_code)

    def test_stack_update_in_scaling(self):
        """Test basic life cycle operations with sample VNFD.

        In this test case, we do following steps.
            - Create subscription.
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF.
            - Get VNF informations.
            - Scale-Out VNF
            - Scale-In VNF
            - Terminate VNF
            - Delete VNF
            - Delete subscription
        """
        # Create subscription and register it.
        callback_url = os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        request_body = fake_vnflcm.Subscription.make_create_request_body(
            'http://localhost:{}{}'.format(
                vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                callback_url))
        resp, response_body = self._register_subscription(request_body)
        self.assertEqual(201, resp.status_code)
        self.assert_http_header_location_for_subscription(resp.headers)
        self.assert_notification_get(callback_url)
        subscription_id = response_body.get('id')
        self.addCleanup(
            self._delete_subscription,
            subscription_id)

        # Pre Setting: Create vnf package.
        sample_name = 'stack_update_in_scale'
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Post Setting: Reserve deleting vnf package.
        self.addCleanup(vnflcm_base._delete_vnf_package, self.tacker_client,
            vnf_package_id)

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance_from_body(
            fake_vnflcm.VnfInstances.make_create_request_body(vnfd_id))
        vnf_instance_id = vnf_instance['id']
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_create_vnf(resp, vnf_instance, vnf_package_id)
        self.addCleanup(self._delete_vnf_instance, vnf_instance_id)

        # Instantiate vnf instance
        request_body = (fake_vnflcm.VnfInstances.
                        make_inst_request_body_include_num_dynamic(
                            self.vim['tenant_id'], self.ext_networks,
                            self.ext_mngd_networks,
                            self.ext_link_ports, self.ext_subnets))
        resp, _ = self._instantiate_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_instantiate_vnf(resp, vnf_instance_id, vnf_package_id)

        # Show vnf instance
        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id)
        self.assertEqual(200, resp.status_code)

        # Scale-out vnf instance
        stack = self._get_heat_stack(vnf_instance_id)
        pre_stack_resource_list = self._get_heat_resource_list(stack.id, 2)

        request_body = fake_vnflcm.VnfInstances.make_scale_request_body(
            'SCALE_OUT')
        resp, _ = self._scale_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)

        post_stack_resource_list = self._get_heat_resource_list(stack.id, 2)
        self._assert_scale_vnf(resp, vnf_instance_id, vnf_package_id,
            pre_stack_resource_list, post_stack_resource_list,
            scale_type='SCALE_OUT', expected_stack_status='CREATE_COMPLETE')

        # Scale-in vnf instance

        stack = self._get_heat_stack(vnf_instance_id)
        pre_stack_resource_list = self._get_heat_resource_list(stack.id, 2)

        request_body = (fake_vnflcm.VnfInstances
                        .make_reverse_scale_request_body('SCALE_IN'))
        resp, _ = self._scale_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)

        post_stack_resource_list = self._get_heat_resource_list(stack.id, 2)
        self._assert_scale_vnf(resp, vnf_instance_id, vnf_package_id,
            pre_stack_resource_list, post_stack_resource_list,
            scale_type='SCALE_IN', expected_stack_status='UPDATE_COMPLETE')

        # Terminate VNF
        stack = self._get_heat_stack(vnf_instance_id)
        resources_list = self._get_heat_resource_list(stack.id)
        resource_name_list = [r.resource_name for r in resources_list]
        glance_image_id_list = self._get_glance_image_list_from_stack_resource(
            stack.id, resource_name_list)

        terminate_req_body = fake_vnflcm.VnfInstances.make_term_request_body()
        resp, _ = self._terminate_vnf_instance(
            vnf_instance_id, terminate_req_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_terminate_vnf(resp, vnf_instance_id, stack.id,
            resource_name_list, glance_image_id_list, vnf_package_id)

        # Delete VNF
        resp, _ = self._delete_vnf_instance(vnf_instance_id)
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_delete_vnf(resp, vnf_instance_id, vnf_package_id)

        # Subscription delete
        resp, response_body = self._delete_subscription(subscription_id)
        self.assertEqual(204, resp.status_code)

        resp, _ = self._show_subscription(subscription_id)
        self.assertEqual(404, resp.status_code)

    def test_inst_update_heal_term(self):
        """Test basic life cycle operations.

        In this test case, we do following steps.
            - Create subscription.
            - Get subscription informations.
            - Get list of subscriptions
            - Get list of subscriptions with filter
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF.
            - Get list of VNF instances.
            - Get information of instantiated VNF.
            - Heal VNF.
            - Create new VNF package for update.
            - Upload new VNF package.
            - Update VNF with new package.
            - Terminate VNF.
            - Delete subscription.
        """
        # Create subscription and register it.
        callback_url = os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        request_body = fake_vnflcm.Subscription.make_create_request_body(
            'http://localhost:{}{}'.format(
                vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                callback_url))
        resp, response_body = self._register_subscription(request_body)
        self.assertEqual(201, resp.status_code)
        self.assert_http_header_location_for_subscription(resp.headers)
        self.assert_notification_get(callback_url)
        subscription_id = response_body.get('id')
        self.addCleanup(self._delete_subscription, subscription_id)

        # Subscription show
        resp, body = self._wait_show_subscription(subscription_id)
        self.assert_subscription_show(resp, body)

        # Subscription list
        resp, _ = self._list_subscription()
        self.assertEqual(200, resp.status_code)

        # Subscription list filter 1
        filter_expr = {
            'filter': "filter=(eq,id,{})".format(body.get('id'))}
        resp, subscription_body = self._list_subscription_filter(
            params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(subscription_body))

        # Subscription list filter 2
        filter_expr = {
            'filter': "filter=(neq,callbackUri,{})".format(
                'http://localhost:{}{}'.format(
                    vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                    os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
                        self._testMethodName)))}
        resp, subscription_body = self._list_subscription_filter(
            params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(0, len(subscription_body))

        # Subscription list filter 3
        filter_expr = {
            'filter': "filter=(neq,id,{})".format(body.get('id'))}
        resp, subscription_body = self._list_subscription_filter(
            params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(0, len(subscription_body))

        # Subscription list filter 4
        filter_expr = {
            'filter': "filter=(eq,callbackUri,{})".format(
                'http://localhost:{}{}'.format(
                    vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                    os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
                        self._testMethodName)))}
        resp, subscription_body = self._list_subscription_filter(
            params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(subscription_body))

        # Subscription list filter 5
        filter_expr = {
            'filter': "filter=(in,operationTypes,{})".format("sample")}
        resp, subscription_body = self._list_subscription_filter(
            params=filter_expr)
        self.assertEqual(400, resp.status_code)
        self.assertEqual(3, len(subscription_body))

        # Subscription list filter 6
        filter_expr = {
            'filter': "filter=(eq,vnfSoftwareVersion,{})".format('1.0')}
        resp, subscription_body = self._list_subscription_filter(
            params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(subscription_body))

        # Subscription list filter 7
        filter_expr = {
            'filter': "filter=(eq,operationTypes,{})".format(
                "SCALE_TO_LEVEL")}
        resp, subscription_body = self._list_subscription_filter(
            params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(0, len(subscription_body))

        # Pre Setting: Create vnf package.
        sample_name = 'functional'
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Post Setting: Reserve deleting vnf package.
        self.addCleanup(vnflcm_base._delete_vnf_package, self.tacker_client,
            vnf_package_id)

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance_from_body(
            fake_vnflcm.VnfInstances.make_create_request_body(vnfd_id))
        vnf_instance_id = vnf_instance['id']
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_create_vnf(resp, vnf_instance, vnf_package_id)
        vnf_instance_name = vnf_instance['vnfInstanceName']
        self.addCleanup(self._delete_vnf_instance, vnf_instance_id)

        # Instantiate vnf instance
        request_body = fake_vnflcm.VnfInstances.make_inst_request_body(
            self.vim['tenant_id'], self.ext_networks, self.ext_mngd_networks,
            self.ext_link_ports, self.ext_subnets)
        resp, _ = self._instantiate_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_instantiate_vnf(resp, vnf_instance_id, vnf_package_id)

        # List vnf instance
        filter_expr = {
            'filter': "(eq,id,{});(eq,vnfInstanceName,{})".format(
                vnf_instance_id, vnf_instance_name)}
        resp, vnf_instances = self._list_vnf_instance(params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(vnf_instances))

        # Show vnf instance
        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id)
        self.assertEqual(200, resp.status_code)

        # Get VNF image after instantiate VDU2
        image_before_update = self._get_heat_stack_show(
            vnf_instance_id, 'VDU2')
        self.assertIsNotNone(
            image_before_update,
            "failed to retrieve image")

        # Update vnf (vnfdId)
        sample_name = 'functional2'
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)
        # upload vnf package
        update_vnf_package_id, update_vnfd_id = \
            vnflcm_base._create_and_upload_vnf_package(
                self.tacker_client,
                user_defined_data={"key": sample_name},
                temp_csar_path=tempname)

        request_body = fake_vnflcm.VnfInstances.make_update_request_body(
            vnfd_id=update_vnfd_id)
        resp, _ = self._update_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_update_vnf(resp, vnf_instance_id,
            after_id=request_body['vnfdId'], old_id=vnfd_id)
        vnf_package_id = update_vnf_package_id

        # Heal vnf (exists vnfc_instace_id)
        vnfc_instance_id_list = [
            vnfc.get('id') for vnfc in vnf_instance.get(
                'instantiatedVnfInfo', {}).get(
                'vnfcResourceInfo', [])]
        request_body = fake_vnflcm.VnfInstances.make_heal_request_body(
            [vnfc_instance_id_list[1]])
        resp, _ = self._heal_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_heal_vnf(resp, vnf_instance_id, vnf_package_id)

        # Check of Image changes after heal
        image_after_heal = self._get_heat_stack_show(vnf_instance_id, 'VDU2')
        self.assertIsNotNone(
            image_after_heal, "failed to retrieve image")
        self.assertNotEqual(image_before_update, image_after_heal)

        # Terminate VNF
        stack = self._get_heat_stack(vnf_instance_id)
        resources_list = self._get_heat_resource_list(stack.id)
        resource_name_list = [r.resource_name for r in resources_list]
        glance_image_id_list = self._get_glance_image_list_from_stack_resource(
            stack.id,
            resource_name_list)

        terminate_req_body = fake_vnflcm.VnfInstances.make_term_request_body()
        resp, _ = self._terminate_vnf_instance(
            vnf_instance_id, terminate_req_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_terminate_vnf(
            resp,
            vnf_instance_id,
            stack.id,
            resource_name_list,
            glance_image_id_list,
            vnf_package_id)

        # Delete VNF
        resp, _ = self._delete_vnf_instance(vnf_instance_id)
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_delete_vnf(resp, vnf_instance_id, vnf_package_id)

        # Subscription delete
        resp, response_body = self._delete_subscription(subscription_id)
        self.assertEqual(204, resp.status_code)

        resp, show_body = self._show_subscription(subscription_id)
        self.assertEqual(404, resp.status_code)

    def test_stack_param_heal_term(self):
        """Test basic life cycle operations.

        In this test case, we do following steps.
            - Create subscription.
            - Get subscription information.
            - Get list of subscriptions
            - Get list of subscriptions with filter
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF.
            - Get list of VNF instances.
            - Get information of instantiated VNF.
            - Heal VNF.
            - Create new VNF package for update.
            - Upload new VNF package.
            - Update VNF with new package.
            - Validate stack parameters for values from package
            - Terminate VNF.
            - Delete subscription.
        """
        # Create subscription and register it.
        callback_url = os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        request_body = fake_vnflcm.Subscription.make_create_request_body(
            'http://localhost:{}{}'.format(
                vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                callback_url))
        resp, response_body = self._register_subscription(request_body)
        self.assertEqual(201, resp.status_code)
        self.assert_http_header_location_for_subscription(resp.headers)
        self.assert_notification_get(callback_url)
        subscription_id = response_body.get('id')
        self.addCleanup(self._delete_subscription, subscription_id)

        # Subscription show
        resp, body = self._wait_show_subscription(subscription_id)
        self.assert_subscription_show(resp, body)

        # Subscription list
        resp, _ = self._list_subscription()
        self.assertEqual(200, resp.status_code)

        # Subscription list filter 1
        filter_expr = {
            'filter': "filter=(eq,id,{})".format(body.get('id'))}
        resp, subscription_body = self._list_subscription_filter(
            params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(subscription_body))

        # Subscription list filter 2
        filter_expr = {
            'filter': "filter=(neq,callbackUri,{})".format(
                'http://localhost:{}{}'.format(
                    vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                    os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
                        self._testMethodName)))}
        resp, subscription_body = self._list_subscription_filter(
            params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(0, len(subscription_body))

        # Subscription list filter 3
        filter_expr = {
            'filter': "filter=(neq,id,{})".format(body.get('id'))}
        resp, subscription_body = self._list_subscription_filter(
            params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(0, len(subscription_body))

        # Subscription list filter 4
        filter_expr = {
            'filter': "filter=(eq,callbackUri,{})".format(
                'http://localhost:{}{}'.format(
                    vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                    os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
                        self._testMethodName)))}
        resp, subscription_body = self._list_subscription_filter(
            params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(subscription_body))

        # Subscription list filter 5
        filter_expr = {
            'filter': "filter=(in,operationTypes,{})".format("sample")}
        resp, subscription_body = self._list_subscription_filter(
            params=filter_expr)
        self.assertEqual(400, resp.status_code)
        self.assertEqual(3, len(subscription_body))

        # Subscription list filter 6
        filter_expr = {
            'filter': "filter=(eq,vnfSoftwareVersion,{})".format('1.0')}
        resp, subscription_body = self._list_subscription_filter(
            params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(subscription_body))

        # Subscription list filter 7
        filter_expr = {
            'filter': "filter=(eq,operationTypes,{})".format(
                "SCALE_TO_LEVEL")}
        resp, subscription_body = self._list_subscription_filter(
            params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(0, len(subscription_body))

        # Pre Setting: Create vnf package.
        sample_name = 'functional'
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Post Setting: Reserve deleting vnf package.
        self.addCleanup(vnflcm_base._delete_vnf_package, self.tacker_client,
            vnf_package_id)

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance_from_body(
            fake_vnflcm.VnfInstances.make_create_request_body(vnfd_id))
        vnf_instance_id = vnf_instance['id']
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_create_vnf(resp, vnf_instance, vnf_package_id)
        vnf_instance_name = vnf_instance['vnfInstanceName']
        self.addCleanup(self._delete_vnf_instance, vnf_instance_id)

        # Instantiate vnf instance
        request_body = fake_vnflcm.VnfInstances.make_inst_request_body(
            self.vim['tenant_id'], self.ext_networks, self.ext_mngd_networks,
            self.ext_link_ports, self.ext_subnets)
        resp, _ = self._instantiate_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_instantiate_vnf(resp, vnf_instance_id, vnf_package_id)

        # List vnf instance
        filter_expr = {
            'filter': "(eq,id,{});(eq,vnfInstanceName,{})".format(
                vnf_instance_id, vnf_instance_name)}
        resp, vnf_instances = self._list_vnf_instance(params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(vnf_instances))

        # Show vnf instance
        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id)
        self.assertEqual(200, resp.status_code)

        # Update vnf (vnfdId)
        sample_name = 'stack_update_in_heal'
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)
        # upload vnf package
        update_vnf_package_id, update_vnfd_id = (vnflcm_base
            ._create_and_upload_vnf_package(
                self.tacker_client,
                user_defined_data={"key": sample_name},
                temp_csar_path=tempname))

        request_body = fake_vnflcm.VnfInstances.make_update_request_body(
            vnfd_id=update_vnfd_id)
        resp, _ = self._update_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_update_vnf(resp, vnf_instance_id,
            after_id=request_body['vnfdId'], old_id=vnfd_id)
        vnf_package_id = update_vnf_package_id

        # Heal vnf (exists vnfc_instace_id)
        vnfc_instance_id_list = [
            vnfc.get('id') for vnfc in vnf_instance.get(
                'instantiatedVnfInfo', {}).get(
                'vnfcResourceInfo', [])]
        request_body = fake_vnflcm.VnfInstances.make_heal_request_body(
            [vnfc_instance_id_list[1]])
        resp, _ = self._heal_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_heal_vnf(resp, vnf_instance_id, vnf_package_id)

        # Check of stack param desired_capacity existence in stack
        stack_after_heal = self._get_heat_stack_show(vnf_instance_id)
        self.assertIsNotNone(
            stack_after_heal, "failed to retrieve stack")
        self.assertIsNotNone(stack_after_heal.get('desired_capacity'))

        # Terminate VNF
        stack = self._get_heat_stack(vnf_instance_id)
        resources_list = self._get_heat_resource_list(stack.id)
        resource_name_list = [r.resource_name for r in resources_list]
        glance_image_id_list = self._get_glance_image_list_from_stack_resource(
            stack.id,
            resource_name_list)

        terminate_req_body = fake_vnflcm.VnfInstances.make_term_request_body()
        resp, _ = self._terminate_vnf_instance(
            vnf_instance_id, terminate_req_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_terminate_vnf(
            resp,
            vnf_instance_id,
            stack.id,
            resource_name_list,
            glance_image_id_list,
            vnf_package_id)

        # Delete VNF
        resp, _ = self._delete_vnf_instance(vnf_instance_id)
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_delete_vnf(resp, vnf_instance_id, vnf_package_id)

        # Subscription delete
        resp, response_body = self._delete_subscription(subscription_id)
        self.assertEqual(204, resp.status_code)

        resp, show_body = self._show_subscription(subscription_id)
        self.assertEqual(404, resp.status_code)

    def test_inst_update_pkgid_heal_all(self):
        """Test basic life cycle operations with pkg update.

        In this test case, we do following steps.
            - Create subscription.
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF
            - Heal VNF
            - Create new VNF package for update.
            - Upload new VNF package.
            - Update VNF with new package.
            - Terminate VNF.
            - Delete VNF.
            - Delete subscription.
        """
        # Create subscription and register it.
        callback_url = os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        request_body = fake_vnflcm.Subscription.make_create_request_body(
            'http://localhost:{}{}'.format(
                vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                callback_url))
        resp, response_body = self._register_subscription(request_body)
        self.assertEqual(201, resp.status_code)
        self.assert_http_header_location_for_subscription(resp.headers)
        self.assert_notification_get(callback_url)
        subscription_id = response_body.get('id')
        self.addCleanup(self._delete_subscription, subscription_id)

        # Pre Setting: Create vnf package.
        sample_name = 'functional'
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Post Setting: Reserve deleting vnf package.
        self.addCleanup(vnflcm_base._delete_vnf_package, self.tacker_client,
            vnf_package_id)

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance_from_body(
            fake_vnflcm.VnfInstances.make_create_request_body(vnfd_id))
        vnf_instance_id = vnf_instance['id']
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_create_vnf(resp, vnf_instance, vnf_package_id)
        self.addCleanup(self._delete_vnf_instance, vnf_instance_id)

        # Instantiate vnf instance
        request_body = fake_vnflcm.VnfInstances.make_inst_request_body(
            self.vim['tenant_id'], self.ext_networks, self.ext_mngd_networks,
            self.ext_link_ports, self.ext_subnets)
        resp, _ = self._instantiate_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_instantiate_vnf(resp, vnf_instance_id, vnf_package_id)

        # Heal vnf (do not specify vnfc_instace_id)
        # pre check heat status.
        self.assert_heat_stack_status(vnf_instance_id)

        request_body = fake_vnflcm.VnfInstances.make_heal_request_body()
        resp, _ = self._heal_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)

        # post check heat status.
        self.assert_heal_vnf(
            resp,
            vnf_instance_id,
            vnf_package_id,
            expected_stack_status='CREATE_COMPLETE')

        # Update vnf (vnfPkgId)
        sample_name = 'functional2'
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)
        # upload vnf package
        update_vnf_package_id, _ = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        request_body = fake_vnflcm.VnfInstances.make_update_request_body(
            vnf_package_id=update_vnf_package_id)
        resp, _ = self._update_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_update_vnf(resp, vnf_instance_id, is_vnfd=False,
            after_id=request_body['vnfPkgId'], old_id=vnf_package_id)
        vnf_package_id = update_vnf_package_id

        # Terminate VNF
        stack = self._get_heat_stack(vnf_instance_id)
        resources_list = self._get_heat_resource_list(stack.id)
        resource_name_list = [r.resource_name for r in resources_list]
        glance_image_id_list = self._get_glance_image_list_from_stack_resource(
            stack.id,
            resource_name_list)

        terminate_req_body = fake_vnflcm.VnfInstances.make_term_request_body()
        resp, _ = self._terminate_vnf_instance(
            vnf_instance_id, terminate_req_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_terminate_vnf(
            resp,
            vnf_instance_id,
            stack.id,
            resource_name_list,
            glance_image_id_list,
            vnf_package_id)

        # Delete VNF
        resp, _ = self._delete_vnf_instance(vnf_instance_id)
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_delete_vnf(resp, vnf_instance_id, vnf_package_id)

        # Subscription delete
        resp, response_body = self._delete_subscription(subscription_id)
        self.assertEqual(204, resp.status_code)

    def test_instantiate_vnf_basehot_invalid(self):
        """Test instantiation operation with invalid HOT data.

        In this test case, we do following steps.
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF
        """
        # Pre Setting: Create vnf package.
        sample_name = "user_data_sample_basehot_invalid"
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_user_data_common(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Reserve deleting vnf package
        self.addCleanup(vnflcm_base._delete_vnf_package, self.tacker_client,
            vnf_package_id)

        # Settings
        vnf_instance_name = "vnf_with_user_data-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf_with_user_data_basehot_invalid"
        add_params = {
            "lcm-operation-user-data": "./UserData/lcm_user_data.py",
            "lcm-operation-user-data-class": "SampleUserData"}

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance(vnfd_id,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # Reserve deleting vnf instance
        self.addCleanup(self._delete_vnf_instance, vnf_instance['id'])

        request_body = vnflcm_base._create_instantiate_vnf_request_body(
            "simple", vim_id=self.vim['id'], ext_vl=self.ext_vl,
            add_params=add_params)

        self._instantiate_vnf_instance_fail(vnf_instance['id'], request_body)

    def test_instantiate_vnf_userdata_timeout(self):
        """Test instantiation operation timeout with long-running script.

        In this test case, we do following steps.
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF
        """
        # Pre Setting: Create vnf package.
        sample_name = "user_data_sample_userdata_timeout"
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_user_data_common(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Reserve deleting vnf package
        self.addCleanup(vnflcm_base._delete_vnf_package, self.tacker_client,
            vnf_package_id)

        # Settings
        vnf_instance_name = "vnf_with_user_data-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf_with_user_data_timeout"
        add_params = {
            "lcm-operation-user-data": "./UserData/lcm_user_data_sleeping.py",
            "lcm-operation-user-data-class": "SampleUserData"}

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance(vnfd_id,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # Reserve deleting vnf instance
        self.addCleanup(self._delete_vnf_instance, vnf_instance['id'])

        request_body = \
            vnflcm_base._create_instantiate_vnf_request_body("simple",
                vim_id=self.vim['id'],
                ext_vl=self.ext_vl,
                add_params=add_params)

        self._instantiate_vnf_instance_fail(vnf_instance['id'], request_body)

    def test_instantiate_vnf_userdata_invalid_hot_param(self):
        """Test instantiation operation with invalid HOT and user data.

        In this test case, we do following steps.
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF
        """
        # Pre Setting: Create vnf package.
        sample_name = "user_data_sample_userdata_invalid_hot_param"
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_user_data_common(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Reserve deleting vnf package
        self.addCleanup(vnflcm_base._delete_vnf_package, self.tacker_client,
            vnf_package_id)

        # Settings
        vnf_instance_name = "vnf_with_user_data-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf_with_user_data_timeout"
        add_params = {
            "lcm-operation-user-data": "./UserData/"
            "lcm_user_data_invalid_hot_param.py",
            "lcm-operation-user-data-class": "SampleUserData"}

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance(vnfd_id,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # Reserve deleting vnf instance
        self.addCleanup(self._delete_vnf_instance, vnf_instance['id'])

        request_body = \
            vnflcm_base._create_instantiate_vnf_request_body("simple",
                vim_id=self.vim['id'],
                ext_vl=self.ext_vl,
                add_params=add_params)

        self._instantiate_vnf_instance_fail(vnf_instance['id'], request_body)

    def test_instantiate_vnf_userdata_none(self):
        """Test instantiation operation timeout with none user data.

        In this test case, we do following steps.
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF
        """
        # Pre Setting: Create vnf package.
        sample_name = "user_data_sample_userdata_none"
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_user_data_common(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Reserve deleting vnf package
        self.addCleanup(
            vnflcm_base._delete_vnf_package,
            self.tacker_client,
            vnf_package_id)

        # Settings
        vnf_instance_name = "vnf_with_user_data-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf_with_user_data_timeout"
        add_params = {
            "lcm-operation-user-data": "./UserData/lcm_user_data.py",
            "lcm-operation-user-data-class": "SampleUserData"}

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance(vnfd_id,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # Reserve deleting vnf instance
        self.addCleanup(self._delete_vnf_instance, vnf_instance['id'])

        request_body = \
            vnflcm_base._create_instantiate_vnf_request_body("simple",
                vim_id=self.vim['id'],
                ext_vl=self.ext_vl,
                add_params=add_params)

        self._instantiate_vnf_instance_fail(vnf_instance['id'], request_body)

    def test_instantiate_vnf_userdata_invalid_script(self):
        """Test instantiation operation with invalid user script.

        In this test case, we do following steps.
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF
        """
        # Pre Setting: Create vnf package.
        sample_name = "user_data_sample_userdata_invalid_script"
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_user_data_common(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Reserve deleting vnf package
        self.addCleanup(
            vnflcm_base._delete_vnf_package,
            self.tacker_client,
            vnf_package_id)

        # Settings
        vnf_instance_name = "vnf_with_user_data-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf_with_user_data_timeout"
        add_params = {
            "lcm-operation-user-data": "./UserData/"
            "lcm_user_data_invalid_script.py",
            "lcm-operation-user-data-class": "SampleUserData"}

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance(vnfd_id,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # Reserve deleting vnf instance
        self.addCleanup(self._delete_vnf_instance, vnf_instance['id'])

        request_body = vnflcm_base._create_instantiate_vnf_request_body(
            "simple", vim_id=self.vim['id'], ext_vl=self.ext_vl,
            add_params=add_params)

        self._instantiate_vnf_instance_fail(vnf_instance['id'], request_body)

    def test_retry_instantiate(self):
        """Test retry operation for instantiation.

        In this test case, we do following steps.
            - Create subscription.
            - Test notification.
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF(Will fail).
            - Get vnflcmOpOccId to retry.
            - Retry instantiation operation.
            - Get opOccs information.
            - Get opOccs list.
            - Delete VNF instance.
            - Delete subscription.
        """
        # Create subscription and register it.
        callback_url = os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        request_body = fake_vnflcm.Subscription.make_create_request_body(
            'http://localhost:{}{}'.format(
                vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                callback_url))
        resp, response_body = self._register_subscription(request_body)
        self.assertEqual(201, resp.status_code)
        self.assert_http_header_location_for_subscription(resp.headers)
        subscription_id = response_body.get('id')
        self.addCleanup(self._delete_subscription, subscription_id)

        # Test notification
        self.assert_notification_get(callback_url)

        # Pre Setting: Create vnf package.
        sample_name = 'functional3'
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Post Setting: Reserve deleting vnf package.
        self.addCleanup(
            vnflcm_base._delete_vnf_package,
            self.tacker_client,
            vnf_package_id)

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance_from_body(
            fake_vnflcm.VnfInstances.make_create_request_body(vnfd_id))
        vnf_instance_id = vnf_instance['id']
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_create_vnf(resp, vnf_instance, vnf_package_id)
        self.addCleanup(self._delete_vnf_instance, vnf_instance_id)

        # Failed instantiate VNF
        request_body = fake_vnflcm.VnfInstances.make_inst_request_body(
            self.vim['tenant_id'], self.ext_networks, self.ext_mngd_networks,
            self.ext_link_ports, self.ext_subnets)
        resp, _ = self._instantiate_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('FAILED_TEMP', vnf_instance_id=vnf_instance_id)

        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = vnflcm_base.FAKE_SERVER_MANAGER.get_history(
            callback_url)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(
            callback_url)

        # get vnflcm_op_occ_id
        vnflcm_op_occ_id = notify_mock_responses[0].request_body.get(
            'vnfLcmOpOccId')
        self.assertIsNotNone(vnflcm_op_occ_id)

        # retry
        resp, _ = self._retry_op_occs(vnflcm_op_occ_id)
        self._wait_lcm_done('FAILED_TEMP', vnf_instance_id=vnf_instance_id)
        self.assert_retry_vnf(resp, vnf_instance_id)

        # rollback (Execute because it's needed to delete VNF)
        resp, _ = self._rollback_op_occs(vnflcm_op_occ_id)
        self._wait_lcm_done('ROLLING_BACK', vnf_instance_id=vnf_instance_id)
        self._wait_lcm_done('ROLLED_BACK', vnf_instance_id=vnf_instance_id)
        self.assert_rollback_vnf(resp, vnf_instance_id)

        # occ-show
        resp, op_occs_info = self._show_op_occs(vnflcm_op_occ_id)
        self._assert_occ_show(resp, op_occs_info)

        # occ-list
        resp, op_occs_info = self._list_op_occs()
        self._assert_occ_list(resp, op_occs_info)

        # Delete VNF
        resp, _ = self._delete_vnf_instance(vnf_instance_id)
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_delete_vnf(resp, vnf_instance_id, vnf_package_id)

        # Subscription delete
        resp, response_body = self._delete_subscription(subscription_id)
        self.assertEqual(204, resp.status_code)

    def test_retry_scale_out(self):
        """Test retry operation for Scale-Out operation.

        In this test case, we do following steps.
            - Create subscription.
            - Test notification.
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF.
            - Scale-Out(Will fail).
            - Get vnfcmOpOccId to retry.
            - Retry Scale-Out operation.
            - Get opOccs information.
            - Get opOccs list.
            - Terminate VNF instance.
            - Delete VNF instance.
            - Delete subscription.
        """
        # Create subscription and register it.
        callback_url = os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        request_body = fake_vnflcm.Subscription.make_create_request_body(
            'http://localhost:{}{}'.format(
                vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                callback_url))
        resp, response_body = self._register_subscription(request_body)
        self.assertEqual(201, resp.status_code)
        self.assert_http_header_location_for_subscription(resp.headers)
        subscription_id = response_body.get('id')
        self.addCleanup(self._delete_subscription, subscription_id)

        # Test notification
        self.assert_notification_get(callback_url)

        # Pre Setting: Create vnf package.
        sample_name = 'functional4'
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Post Setting: Reserve deleting vnf package.
        self.addCleanup(
            vnflcm_base._delete_vnf_package,
            self.tacker_client,
            vnf_package_id)

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance_from_body(
            fake_vnflcm.VnfInstances.make_create_request_body(vnfd_id))
        vnf_instance_id = vnf_instance['id']
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_create_vnf(resp, vnf_instance, vnf_package_id)
        self.addCleanup(self._delete_vnf_instance, vnf_instance_id)

        # instantiate VNF
        request_body = fake_vnflcm.VnfInstances.make_inst_request_body(
            self.vim['tenant_id'], self.ext_networks, self.ext_mngd_networks,
            self.ext_link_ports, self.ext_subnets)
        self._instantiate_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(
            os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
                self._testMethodName))

        # Fail Scale-out vnf instance
        request_body = fake_vnflcm.VnfInstances.make_scale_request_body(
            'SCALE_OUT')
        resp, _ = self._scale_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('FAILED_TEMP', vnf_instance_id=vnf_instance_id)

        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = vnflcm_base.FAKE_SERVER_MANAGER.get_history(
            callback_url)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(
            callback_url)

        # get vnflcm_op_occ_id
        vnflcm_op_occ_id = notify_mock_responses[0].request_body.get(
            'vnfLcmOpOccId')
        self.assertIsNotNone(vnflcm_op_occ_id)

        # retry
        resp, _ = self._retry_op_occs(vnflcm_op_occ_id)
        self._wait_lcm_done('FAILED_TEMP', vnf_instance_id=vnf_instance_id)
        self.assert_retry_vnf(resp, vnf_instance_id)

        # rollback (Execute because it's needed to delete VNF)
        resp, _ = self._rollback_op_occs(vnflcm_op_occ_id)
        self._wait_lcm_done('ROLLING_BACK', vnf_instance_id=vnf_instance_id)
        self._wait_lcm_done('ROLLED_BACK', vnf_instance_id=vnf_instance_id)
        self.assert_rollback_vnf(resp, vnf_instance_id)

        # occ-show
        resp, op_occs_info = self._show_op_occs(vnflcm_op_occ_id)
        self._assert_occ_show(resp, op_occs_info)

        # occ-list
        resp, op_occs_info = self._list_op_occs()
        self._assert_occ_list(resp, op_occs_info)

        # Terminate VNF
        stack = self._get_heat_stack(vnf_instance_id)
        resources_list = self._get_heat_resource_list(stack.id)
        resource_name_list = [r.resource_name for r in resources_list]
        glance_image_id_list = self._get_glance_image_list_from_stack_resource(
            stack.id,
            resource_name_list)

        terminate_req_body = fake_vnflcm.VnfInstances.make_term_request_body()
        resp, _ = self._terminate_vnf_instance(vnf_instance_id,
            terminate_req_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_terminate_vnf(resp, vnf_instance_id, stack.id,
            resource_name_list, glance_image_id_list, vnf_package_id)

        # Delete VNF
        resp, _ = self._delete_vnf_instance(vnf_instance_id)
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_delete_vnf(resp, vnf_instance_id, vnf_package_id)

        # Subscription delete
        resp, response_body = self._delete_subscription(subscription_id)
        self.assertEqual(204, resp.status_code)

    def test_rollback_instantiate(self):
        """Test rollback operation for instantiation.

        In this test case, we do following steps.
            - Create subscription.
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF(Will fail).
            - Get vnflcmOpOccId to rollback.
            - Rollback instantiation operation.
            - Get opOccs information.
            - Get opOccs list
            - Delete subscription.
        """
        # Create subscription and register it.
        callback_url = os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        request_body = fake_vnflcm.Subscription.make_create_request_body(
            'http://localhost:{}{}'.format(
                vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                callback_url))
        resp, response_body = self._register_subscription(request_body)
        self.assertEqual(201, resp.status_code)
        self.assert_http_header_location_for_subscription(resp.headers)
        self.assert_notification_get(callback_url)
        subscription_id = response_body.get('id')
        self.addCleanup(self._delete_subscription, subscription_id)

        # Pre Setting: Create vnf package.
        sample_name = 'functional3'
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Post Setting: Reserve deleting vnf package.
        self.addCleanup(
            vnflcm_base._delete_vnf_package,
            self.tacker_client,
            vnf_package_id)

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance_from_body(
            fake_vnflcm.VnfInstances.make_create_request_body(vnfd_id))
        vnf_instance_id = vnf_instance['id']
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_create_vnf(resp, vnf_instance, vnf_package_id)
        self.addCleanup(self._delete_vnf_instance, vnf_instance_id)

        # Failed instantiate VNF
        request_body = fake_vnflcm.VnfInstances.make_inst_request_body(
            self.vim['tenant_id'], self.ext_networks, self.ext_mngd_networks,
            self.ext_link_ports, self.ext_subnets)
        resp, _ = self._instantiate_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('FAILED_TEMP', vnf_instance_id=vnf_instance_id)

        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = vnflcm_base.FAKE_SERVER_MANAGER.get_history(
            callback_url)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(
            callback_url)

        # get vnflcm_op_occ_id
        vnflcm_op_occ_id = notify_mock_responses[0].request_body.get(
            'vnfLcmOpOccId')
        self.assertIsNotNone(vnflcm_op_occ_id)

        # rollback
        resp, _ = self._rollback_op_occs(vnflcm_op_occ_id)
        self._wait_lcm_done('ROLLING_BACK', vnf_instance_id=vnf_instance_id)
        self._wait_lcm_done('ROLLED_BACK', vnf_instance_id=vnf_instance_id)
        self.assert_rollback_vnf(resp, vnf_instance_id)

        # occ-show
        resp, op_occs_info = self._show_op_occs(vnflcm_op_occ_id)
        self._assert_occ_show(resp, op_occs_info)

        # occ-list
        resp, op_occs_info = self._list_op_occs()
        self._assert_occ_list(resp, op_occs_info)

        # Delete VNF
        resp, _ = self._delete_vnf_instance(vnf_instance_id)
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_delete_vnf(resp, vnf_instance_id, vnf_package_id)

        # Subscription delete
        resp, response_body = self._delete_subscription(subscription_id)
        self.assertEqual(204, resp.status_code)

    def test_rollback_scale_out(self):
        """Test rollback operation for Scale-Out operation.

        In this test case, we do following steps.
            - Create subscription.
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF.
            - Scale-Out(Will fail).
            - Get vnfcmOpOccId to rollback.
            - Rollback Scale-Out operation.
            - Get opOccs information.
            - get opOccs List.
            - Terminate VNF.
            - Delete subscription.
        """
        # Create subscription and register it.
        callback_url = os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        request_body = fake_vnflcm.Subscription.make_create_request_body(
            'http://localhost:{}{}'.format(
                vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                callback_url))
        resp, response_body = self._register_subscription(request_body)
        self.assertEqual(201, resp.status_code)
        self.assert_http_header_location_for_subscription(resp.headers)
        self.assert_notification_get(callback_url)
        subscription_id = response_body.get('id')
        self.addCleanup(self._delete_subscription, subscription_id)

        # Pre Setting: Create vnf package.
        sample_name = 'functional4'
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Post Setting: Reserve deleting vnf package.
        self.addCleanup(
            vnflcm_base._delete_vnf_package,
            self.tacker_client,
            vnf_package_id)

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance_from_body(
            fake_vnflcm.VnfInstances.make_create_request_body(vnfd_id))
        vnf_instance_id = vnf_instance['id']
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_create_vnf(resp, vnf_instance, vnf_package_id)
        self.addCleanup(self._delete_vnf_instance, vnf_instance_id)

        # instantiate VNF
        request_body = fake_vnflcm.VnfInstances.make_inst_request_body(
            self.vim['tenant_id'], self.ext_networks, self.ext_mngd_networks,
            self.ext_link_ports, self.ext_subnets)
        self._instantiate_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(
            os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
                self._testMethodName))

        # Fail Scale-out vnf instance
        request_body = fake_vnflcm.VnfInstances.make_scale_request_body(
            'SCALE_OUT')
        resp, _ = self._scale_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('FAILED_TEMP', vnf_instance_id=vnf_instance_id)

        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = vnflcm_base.FAKE_SERVER_MANAGER.get_history(
            callback_url)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(
            callback_url)

        # get vnflcm_op_occ_id
        vnflcm_op_occ_id = notify_mock_responses[0].request_body.get(
            'vnfLcmOpOccId')
        self.assertIsNotNone(vnflcm_op_occ_id)

        # rollback
        resp, _ = self._rollback_op_occs(vnflcm_op_occ_id)
        self._wait_lcm_done('ROLLING_BACK', vnf_instance_id=vnf_instance_id)
        self._wait_lcm_done('ROLLED_BACK', vnf_instance_id=vnf_instance_id)
        self.assert_rollback_vnf(resp, vnf_instance_id)

        # occ-show
        resp, op_occs_info = self._show_op_occs(vnflcm_op_occ_id)
        self._assert_occ_show(resp, op_occs_info)

        # occ-list
        resp, op_occs_info = self._list_op_occs()
        self._assert_occ_list(resp, op_occs_info)

        # Terminate VNF
        stack = self._get_heat_stack(vnf_instance_id)
        resources_list = self._get_heat_resource_list(stack.id)
        resource_name_list = [r.resource_name for r in resources_list]
        glance_image_id_list = self._get_glance_image_list_from_stack_resource(
            stack.id,
            resource_name_list)

        terminate_req_body = fake_vnflcm.VnfInstances.make_term_request_body()
        resp, _ = self._terminate_vnf_instance(vnf_instance_id,
            terminate_req_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_terminate_vnf(resp, vnf_instance_id, stack.id,
            resource_name_list, glance_image_id_list, vnf_package_id)

        # Delete VNF
        resp, _ = self._delete_vnf_instance(vnf_instance_id)
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_delete_vnf(resp, vnf_instance_id, vnf_package_id)

        # Subscription delete
        resp, response_body = self._delete_subscription(subscription_id)
        self.assertEqual(204, resp.status_code)

    def test_fail_instantiate(self):
        """Test fail operation for instantiation.

        In this test case, we do following steps.
            - Create subscription.
            - Test notification.
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF(Will fail).
            - Get vnflcmOpOccId to fail.
            - Fail instantiation operation.
            - Get opOccs information.
            - Delete subscription.
        """
        # Create subscription and register it.
        request_body = fake_vnflcm.Subscription.make_create_request_body(
            'http://localhost:{}{}'.format(
                vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
                    self._testMethodName)))
        resp, response_body = self._register_subscription(request_body)
        self.assertEqual(201, resp.status_code)
        self.assert_http_header_location_for_subscription(resp.headers)
        subscription_id = response_body.get('id')
        self.addCleanup(self._delete_subscription, subscription_id)

        self.assert_notification_get(
            os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName))

        # Pre Setting: Create vnf package.
        sample_name = 'functional3'
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Post Setting: Reserve deleting vnf package.
        self.addCleanup(
            vnflcm_base._delete_vnf_package,
            self.tacker_client,
            vnf_package_id)

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance_from_body(
            fake_vnflcm.VnfInstances.make_create_request_body(vnfd_id))
        vnf_instance_id = vnf_instance['id']
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_create_vnf(resp, vnf_instance, vnf_package_id)
        self.addCleanup(self._delete_vnf_instance, vnf_instance_id)

        # Failed instantiate VNF
        request_body = fake_vnflcm.VnfInstances.make_inst_request_body(
            self.vim['tenant_id'], self.ext_networks, self.ext_mngd_networks,
            self.ext_link_ports, self.ext_subnets)
        resp, _ = self._instantiate_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('FAILED_TEMP', vnf_instance_id=vnf_instance_id)

        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = vnflcm_base.FAKE_SERVER_MANAGER.get_history(
            callback_url)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(
            callback_url)

        # get vnflcm_op_occ_id
        vnflcm_op_occ_id = notify_mock_responses[0].request_body.get(
            'vnfLcmOpOccId')
        self.assertIsNotNone(vnflcm_op_occ_id)

        # fail
        resp, _ = self._fail_op_occs(vnflcm_op_occ_id)
        self._wait_lcm_done('FAILED', vnf_instance_id=vnf_instance_id)
        self.assert_fail_vnf(resp, vnf_instance_id)
        self._assert_fail_vnf_response(_)

        # occ-show
        resp, op_occs_info = self._show_op_occs(vnflcm_op_occ_id)
        self._assert_occ_show(resp, op_occs_info)

        # occ-list
        resp, op_occs_info = self._list_op_occs()
        self._assert_occ_list(resp, op_occs_info)

        # Delete Stack
        stack = self._get_heat_stack(vnf_instance_id)
        self._delete_heat_stack(stack.id)
        self._wait_until_stack_ready(
            stack.id, infra_cnst.STACK_DELETE_COMPLETE)

        # Delete VNF
        resp, _ = self._delete_vnf_instance(vnf_instance_id)
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_delete_vnf(resp, vnf_instance_id, vnf_package_id)

        # Subscription delete
        resp, response_body = self._delete_subscription(subscription_id)
        self.assertEqual(204, resp.status_code)

    def test_fail_scale_out(self):
        """Test fail operation for Scale-Out operation.

        In this test case, we do following steps.
            - Create subscription.
            - Test notification.
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF.
            - Scale-Out(Will fail).
            - Get vnfcmOpOccId to fail.
            - Fail Scale-Out operation.
            - Get opOccs information.
            - Terminate VNF.
            - Delete subscription.
        """
        # Create subscription and register it.
        request_body = fake_vnflcm.Subscription.make_create_request_body(
            'http://localhost:{}{}'.format(
                vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
                             self._testMethodName)))
        resp, response_body = self._register_subscription(request_body)
        self.assertEqual(201, resp.status_code)
        self.assert_http_header_location_for_subscription(resp.headers)
        subscription_id = response_body.get('id')
        self.addCleanup(self._delete_subscription, subscription_id)

        self.assert_notification_get(
            os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName))

        # Pre Setting: Create vnf package.
        sample_name = 'functional4'
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Post Setting: Reserve deleting vnf package.
        self.addCleanup(
            vnflcm_base._delete_vnf_package,
            self.tacker_client,
            vnf_package_id)

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance_from_body(
            fake_vnflcm.VnfInstances.make_create_request_body(vnfd_id))
        vnf_instance_id = vnf_instance['id']
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_create_vnf(resp, vnf_instance, vnf_package_id)
        self.addCleanup(self._delete_vnf_instance, vnf_instance_id)

        # instantiate VNF
        request_body = fake_vnflcm.VnfInstances.make_inst_request_body(
            self.vim['tenant_id'], self.ext_networks, self.ext_mngd_networks,
            self.ext_link_ports, self.ext_subnets)
        self._instantiate_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(
            os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
                self._testMethodName))

        # Fail Scale-out vnf instance
        request_body = fake_vnflcm.VnfInstances.make_scale_request_body(
            'SCALE_OUT')
        resp, _ = self._scale_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('FAILED_TEMP', vnf_instance_id=vnf_instance_id)

        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL, self._testMethodName)
        notify_mock_responses = vnflcm_base.FAKE_SERVER_MANAGER.get_history(
            callback_url)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(
            callback_url)

        # get vnflcm_op_occ_id
        vnflcm_op_occ_id = notify_mock_responses[0].request_body.get(
            'vnfLcmOpOccId')
        self.assertIsNotNone(vnflcm_op_occ_id)

        # fail
        resp, _ = self._fail_op_occs(vnflcm_op_occ_id)
        self._wait_lcm_done('FAILED', vnf_instance_id=vnf_instance_id)
        self.assert_fail_vnf(resp, vnf_instance_id)
        self._assert_fail_vnf_response(_)

        # occ-show
        resp, op_occs_info = self._show_op_occs(vnflcm_op_occ_id)
        self._assert_occ_show(resp, op_occs_info)

        # occ-list
        resp, op_occs_info = self._list_op_occs()
        self._assert_occ_list(resp, op_occs_info)

        # Terminate VNF
        stack = self._get_heat_stack(vnf_instance_id)
        resources_list = self._get_heat_resource_list(stack.id)
        resource_name_list = [r.resource_name for r in resources_list]
        glance_image_id_list = self._get_glance_image_list_from_stack_resource(
            stack.id, resource_name_list)

        terminate_req_body = fake_vnflcm.VnfInstances.make_term_request_body()
        resp, _ = self._terminate_vnf_instance(vnf_instance_id,
            terminate_req_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_terminate_vnf(resp, vnf_instance_id, stack.id,
            resource_name_list, glance_image_id_list, vnf_package_id)

        # Delete VNF
        resp, _ = self._delete_vnf_instance(vnf_instance_id)
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_delete_vnf(resp, vnf_instance_id, vnf_package_id)

        # Subscription delete
        resp, response_body = self._delete_subscription(subscription_id)
        self.assertEqual(204, resp.status_code)

    def test_retry_chgextconn(self):
        """Test retry operation for instantiation.

        In this test case, we do following steps.
            - Create subscription.
            - Test notification.
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF.
            - Change External VNF Connectivity(Will fail).
            - Get vnflcmOpOccId to retry.
            - Get opOccs information.
            - Retry Change External VNF Connectivity operation.
            - Delete subscription.
        """
        # Create subscription and register it.
        callback_url = os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        request_body = fake_vnflcm.Subscription.make_create_request_body(
            'http://localhost:{}{}'.format(
                vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                callback_url))
        resp, response_body = self._register_subscription(request_body)
        self.assertEqual(201, resp.status_code)
        self.assert_http_header_location_for_subscription(resp.headers)
        subscription_id = response_body.get('id')
        self.addCleanup(self._delete_subscription, subscription_id)

        # Test notification
        self.assert_notification_get(callback_url)

        # Pre Setting: Create vnf package.
        sample_name = 'functional4'
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Post Setting: Reserve deleting vnf package.
        self.addCleanup(
            vnflcm_base._delete_vnf_package,
            self.tacker_client,
            vnf_package_id)

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance_from_body(
            fake_vnflcm.VnfInstances.make_create_request_body(vnfd_id))
        vnf_instance_id = vnf_instance['id']
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_create_vnf(resp, vnf_instance, vnf_package_id)
        self.addCleanup(self._delete_vnf_instance, vnf_instance_id)

        # Instantiate vnf instance
        request_body = fake_vnflcm.VnfInstances.make_inst_request_body(
            self.vim['tenant_id'], self.ext_networks, self.ext_mngd_networks,
            self.ext_link_ports, self.ext_subnets)
        resp, _ = self._instantiate_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_instantiate_vnf(resp, vnf_instance_id, vnf_package_id)

        # Show vnf instance
        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id)
        self.assertEqual(200, resp.status_code)

        # Delete StacK
        stack = self._get_heat_stack(vnf_instance_id)
        self._delete_heat_stack(stack.id)
        self._wait_until_stack_ready(stack.id,
                infra_cnst.STACK_DELETE_COMPLETE)

        # Change external connectivity
        request_body = \
            fake_vnflcm.VnfInstances.make_change_ext_conn_request_body(
                self.vim['tenant_id'], self.changed_ext_networks,
                self.changed_ext_subnets)
        resp, _ = \
            self._change_ext_conn_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('FAILED_TEMP', vnf_instance_id=vnf_instance_id)

        # get vnflcm_op_occ_id
        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = vnflcm_base.FAKE_SERVER_MANAGER.get_history(
            callback_url)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(
            callback_url)
        vnflcm_op_occ_id = notify_mock_responses[0].request_body.get(
            'vnfLcmOpOccId')
        self.assertIsNotNone(vnflcm_op_occ_id)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(callback_url)

        # occ-show(chgextconn)
        resp, op_occs_info = self._show_op_occs(vnflcm_op_occ_id)
        self._assert_occ_show(resp, op_occs_info)

        # retry
        resp, _ = self._retry_op_occs(vnflcm_op_occ_id)
        self._wait_lcm_done('FAILED_TEMP', vnf_instance_id=vnf_instance_id)
        self.assert_retry_vnf(resp, vnf_instance_id)

        # Subscription delete
        resp, response_body = self._delete_subscription(subscription_id)
        self.assertEqual(204, resp.status_code)

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

    def _assert_scale_vnf(
            self,
            resp,
            vnf_instance_id,
            vnf_pkg_id,
            pre_stack_resource_list,
            post_stack_resource_list,
            scale_type, expected_stack_status):
        super().assert_scale_vnf(
            resp,
            vnf_instance_id,
            pre_stack_resource_list,
            post_stack_resource_list,
            scale_type=scale_type, expected_stack_status=expected_stack_status)

        resp, vnf_pkg_info = vnflcm_base._show_vnf_package(
            self.tacker_client, vnf_pkg_id)
        self.assert_vnf_package_usage_state(vnf_pkg_info)

    def assert_update_vnf(self, resp, vnf_instance_id, is_vnfd=True,
            after_id=None, old_id=None,
            expected_stack_status='CREATE_COMPLETE'):
        """Assert that VNF was updated.

        This method checks if a VNF was really updated or not.
        We use the same name method of super class to check
        lifecycle event(e.g. LcmOpOccs, heat stack status).
        And then, in this method, it gets vnf package info from tacker.
        We confirm that the old package status is 'NOT_IN_USE' and also
        a new package status is the same as expected.

        Args:
            resp (Response): Response headers for HTTP requests.
            vnf_instance_id (str): Self explanatly
            is_vnfd (bool, optional): Specify target VNF is VNFD or
                                      not. Defaults to True.
            after_id (str): Updated VNF id. It should be id of VNFD
                            or VNF Package. Defaults to None.
            old_id (str): Present VNF id. Defaults to None.
            expected_stack_status (str, optional): The expected status
                        of updated VNF. Defaults to 'CREATE_COMPLETE'.
        """
        super().assert_update_vnf(
            resp, vnf_instance_id, expected_stack_status=expected_stack_status)

        if is_vnfd:
            after_filter_attr = {'filter': "(eq,vnfdId,{})".format(after_id)}
            old_filter_attr = {'filter': "(eq,vnfdId,{})".format(old_id)}
        else:
            after_filter_attr = {'filter': "(eq,id,{})".format(after_id)}
            old_filter_attr = {'filter': "(eq,id,{})".format(old_id)}

        # assert old/new package status.
        resp, after_vnf_pkg_info = vnflcm_base._list_vnf_package(
            self.tacker_client, params=after_filter_attr)
        self.assert_vnf_package_usage_state(after_vnf_pkg_info[0])

        resp, old_vnf_pkg_info = vnflcm_base._list_vnf_package(
            self.tacker_client, params=old_filter_attr)
        self.assert_vnf_package_usage_state(old_vnf_pkg_info[0],
            expected_usage_state=fields.PackageUsageStateType.NOT_IN_USE)

    def assert_vnf_package_usage_state(
            self,
            vnf_package_info,
            expected_usage_state=fields.PackageUsageStateType.IN_USE):
        self.assertEqual(
            expected_usage_state,
            vnf_package_info['usageState'])

    def _get_fixed_ips(self, vnf_instance_id, request_body):
        res_name = None
        for extvirlink in request_body['extVirtualLinks']:
            if 'extCps' not in extvirlink:
                continue
            for extcps in extvirlink['extCps']:
                if 'cpdId' in extcps:
                    if res_name is None:
                        res_name = list()
                    res_name.append(extcps['cpdId'])
                    break
        if res_name is None:
            return []

        stack = self._get_heat_stack(vnf_instance_id)
        stack_id = stack.id

        stack_resource = self._get_heat_resource_list(stack_id, nested_depth=2)

        releations = dict()
        for elmt in stack_resource:
            if elmt.resource_type != 'OS::Neutron::Port':
                continue
            if elmt.resource_name not in res_name:
                continue
            releations[elmt.parent_resource] = elmt.resource_name

        details = list()
        for (parent_name, resource_name) in releations.items():
            for elmt in stack_resource:
                if parent_name != elmt.resource_name:
                    continue
                detail_stack = self._get_heat_resource(
                    elmt.physical_resource_id, resource_name)
                details.append(detail_stack)

        ans_list = list()
        for detail in details:
            ans_list.append(detail.attributes['fixed_ips'])

        return ans_list

    def _assert_occ_show(self, resp, op_occs_info):
        self.assertEqual(200, resp.status_code)

        # Only check required parameters.
        self.assertIsNotNone(op_occs_info.get('id'))
        self.assertIsNotNone(op_occs_info.get('operationState'))
        self.assertIsNotNone(op_occs_info.get('stateEnteredTime'))
        self.assertIsNotNone(op_occs_info.get('vnfInstanceId'))
        self.assertIsNotNone(op_occs_info.get('operation'))
        self.assertIsNotNone(op_occs_info.get('isAutomaticInvocation'))
        self.assertIsNotNone(op_occs_info.get('isCancelPending'))

        _links = op_occs_info.get('_links')
        self.assertIsNotNone(_links.get('self'))
        self.assertIsNotNone(_links.get('self').get('href'))
        self.assertIsNotNone(_links.get('vnfInstance'))
        self.assertIsNotNone(_links.get('vnfInstance').get('href'))
        self.assertIsNotNone(_links.get('grant'))
        self.assertIsNotNone(_links.get('grant').get('href'))

    def _assert_fail_vnf_response(self, fail_response):

        # Only check parameters with cardinality = 1
        self.assertIsNotNone(fail_response.get('id'))
        self.assertIsNotNone(fail_response.get('operationState'))
        self.assertIsNotNone(fail_response.get('stateEnteredTime'))
        self.assertIsNotNone(fail_response.get('startTime'))
        self.assertIsNotNone(fail_response.get('vnfInstanceId'))
        self.assertIsNotNone(fail_response.get('operation'))
        self.assertIsNotNone(fail_response.get('isAutomaticInvocation'))
        self.assertIsNotNone(fail_response.get('isCancelPending'))

        changed_ext_connectivity = fail_response.get(
            'changedExtConnectivity', None)
        if changed_ext_connectivity is not None:
            self.assertIsNotNone(
                changed_ext_connectivity._get_changed_ext_connectivity('id'))
            resource_handle = \
                changed_ext_connectivity._get_changed_ext_connectivity(
                    'resourceHandle')
            self.assertIsNotNone(resource_handle)
            self.assertIsNotNone(resource_handle.get('resourceId'))
            ext_link_ports = \
                changed_ext_connectivity._get_changed_ext_connectivity(
                    'extLinkPorts', None)
            if ext_link_ports is not None:
                self.assertIsNotNone(ext_link_ports.get('id'))
                ext_link_ports_resource_handle = ext_link_ports.get(
                    'resourceHandle')
                self.assertIsNotNone(ext_link_ports_resource_handle)
                self.assertIsNotNone(ext_link_ports_resource_handle.get(
                    'resourceId'))
                self.assertIsNotNone(ext_link_ports.get('cpInstanceId'))

        _links = fail_response.get('_links')
        self.assertIsNotNone(_links.get('self'))
        self.assertIsNotNone(_links.get('self').get('href'))
        self.assertIsNotNone(_links.get('vnfInstance'))
        self.assertIsNotNone(_links.get('vnfInstance').get('href'))
        if _links.get('retry') is not None:
            self.assertIsNotNone(_links.get('retry').get('href'))
        if _links.get('fail') is not None:
            self.assertIsNotNone(_links.get('fail').get('href'))
        if _links.get('rollback') is not None:
            self.assertIsNotNone(_links.get('rollback').get('href'))
        if _links.get('grant') is not None:
            self.assertIsNotNone(_links.get('grant').get('href'))

    def test_inst_chgextconn_term(self):
        """Test basic life cycle operations with sample VNFD.

        In this test case, we do following steps.
            - Create subscription.
            - Test notification.
            - Show subscriptions.
            - Get list of subscriptions.
            - Create VNF package.
            - Upload VNF package.
            - Create VNF instance.
            - Instantiate VNF.
            - Get list of VNF instances.
            - Get VNF informations.
            - Change External VNF Connectivity.
            - Get opOccs informations.
            - Terminate VNF
            - Delete VNF
            - Delete subscription
        """
        # Create subscription and register it.
        callback_url = os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        request_body = fake_vnflcm.Subscription.make_create_request_body(
            'http://localhost:{}{}'.format(
                vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                callback_url))
        resp, response_body = self._register_subscription(request_body)
        self.assertEqual(201, resp.status_code)
        self.assert_http_header_location_for_subscription(resp.headers)
        subscription_id = response_body.get('id')
        self.addCleanup(
            self._delete_subscription,
            subscription_id)

        # Test notification
        self.assert_notification_get(callback_url)

        # Subscription show
        resp, body = self._wait_show_subscription(subscription_id)
        self.assert_subscription_show(resp, body)

        # Subscription list
        resp, _ = self._list_subscription()
        self.assertEqual(200, resp.status_code)

        # Pre Setting: Create vnf package.
        sample_name = 'functional5'
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))
        tempname, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)
        # upload vnf package
        vnf_package_id, vnfd_id = vnflcm_base._create_and_upload_vnf_package(
            self.tacker_client, user_defined_data={
                "key": sample_name}, temp_csar_path=tempname)

        # Post Setting: Reserve deleting vnf package.
        self.addCleanup(vnflcm_base._delete_vnf_package, self.tacker_client,
            vnf_package_id)

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance_from_body(
            fake_vnflcm.VnfInstances.make_create_request_body(vnfd_id))
        vnf_instance_id = vnf_instance['id']
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_create_vnf(resp, vnf_instance, vnf_package_id)
        vnf_instance_name = vnf_instance['vnfInstanceName']
        self.addCleanup(self._delete_vnf_instance, vnf_instance_id)

        # Instantiate vnf instance
        request_body = fake_vnflcm.VnfInstances.make_inst_request_body(
            self.vim['tenant_id'], self.ext_networks, self.ext_mngd_networks,
            self.ext_link_ports, self.ext_subnets)
        resp, _ = self._instantiate_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_instantiate_vnf(resp, vnf_instance_id, vnf_package_id)

        # List vnf instance
        filter_expr = {
            'filter': "(eq,id,{});(eq,vnfInstanceName,{})".format(
                vnf_instance_id, vnf_instance_name)}
        resp, vnf_instances = self._list_vnf_instance(params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(vnf_instances))

        # Show vnf instance
        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id)
        self.assertEqual(200, resp.status_code)

        # Change external connectivity
        request_body = \
            fake_vnflcm.VnfInstances.make_change_ext_conn_request_body(
                self.vim['tenant_id'], self.changed_ext_networks,
                self.changed_ext_subnets)
        before_fixed_ips = self._get_fixed_ips(vnf_instance_id, request_body)
        resp, _ = \
            self._change_ext_conn_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        after_fixed_ips = self._get_fixed_ips(vnf_instance_id, request_body)
        self.assertNotEqual(before_fixed_ips, after_fixed_ips)

        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = vnflcm_base.FAKE_SERVER_MANAGER.get_history(
            callback_url)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(
            callback_url)
        vnflcm_op_occ_id = notify_mock_responses[0].request_body.get(
            'vnfLcmOpOccId')
        self.assertIsNotNone(vnflcm_op_occ_id)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(callback_url)

        # occ-show(chgextconn)
        resp, op_occs_info = self._show_op_occs(vnflcm_op_occ_id)
        self._assert_occ_show(resp, op_occs_info)

        # Terminate VNF
        stack = self._get_heat_stack(vnf_instance_id)
        resources_list = self._get_heat_resource_list(stack.id)
        resource_name_list = [r.resource_name for r in resources_list]
        glance_image_id_list = \
            self._get_glance_image_list_from_stack_resource(
                stack.id, resource_name_list)

        terminate_req_body = fake_vnflcm.VnfInstances.make_term_request_body()
        resp, _ = self._terminate_vnf_instance(
            vnf_instance_id, terminate_req_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self.assert_terminate_vnf(resp, vnf_instance_id, stack.id,
            resource_name_list, glance_image_id_list, vnf_package_id)

        # Delete VNF
        resp, _ = self._delete_vnf_instance(vnf_instance_id)
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_delete_vnf(resp, vnf_instance_id, vnf_package_id)

        # Subscription delete
        resp, response_body = self._delete_subscription(subscription_id)
        self.assertEqual(204, resp.status_code)

        resp, _ = self._show_subscription(subscription_id)
        self.assertEqual(404, resp.status_code)
