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


import hashlib
import os

from tacker.tests.functional.sol.vnflcm import base as vnflcm_base
from tacker.tests.functional.sol.vnflcm import fake_vnflcm
from tacker.tests.functional.sol_separated_nfvo.vnflcm import fake_grant
from tacker.tests.functional.sol_separated_nfvo.vnflcm import fake_vnfpkgm


class VnfLcmWithNfvoSeparator(vnflcm_base.BaseVnfLcmTest):

    def _register_vnf_package_mock_response(self, package_dir="functional6"):
        """Prepare VNF package for test.

        Register VNF package response to fake NFVO server and Cleanups.

        Returns:
            Response: VNF Package information
        """
        # Pre Setting: Create vnf package.
        sample_name = package_dir
        csar_package_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../etc/samples/etsi/nfv",
                sample_name))

        # Get VNFD id.
        tempname, vnfd_id = vnflcm_base._create_csar_with_unique_vnfd_id(
            csar_package_path)
        with open(tempname, "rb") as f:
            vnf_package_hash = hashlib.sha256(f.read()).hexdigest()

        vnf_package_info = \
            fake_vnfpkgm.VnfPackage.make_individual_response_body(
                vnfd_id, vnf_package_hash)
        vnf_package_id = vnf_package_info['id']

        # Post Setting: Reserve deleting vnf package.
        self.addCleanup(vnflcm_base._delete_vnf_package, self.tacker_client,
            vnf_package_id)

        # Set "VNF Packages" response
        vnflcm_base.FAKE_SERVER_MANAGER.set_callback('GET',
            fake_vnfpkgm.VnfPackage.VNF_PACKAGE_REQ_PATH, status_code=200,
            response_body=[vnf_package_info])

        # Set "VNF Package content" response
        vnflcm_base.FAKE_SERVER_MANAGER.set_callback('GET',
            os.path.join(
                fake_vnfpkgm.VnfPackage.VNF_PACKAGE_REQ_PATH,
                vnf_package_id,
                'package_content'),
            status_code=200,
            response_headers={"Content-Type": "application/zip"},
            content=tempname)

        # Set "Individual VNF package artifact" response
        vnflcm_base.FAKE_SERVER_MANAGER.set_callback('GET',
            os.path.join(
                fake_vnfpkgm.VnfPackage.VNF_PACKAGE_REQ_PATH,
                vnf_package_id,
                'artifacts',
                vnf_package_info['additionalArtifacts'][0]['artifactPath']),
            status_code=200,
            response_headers={"Content-Type": "application/zip"},
            content=tempname)

        # Set "VNFD of individual VNF package" response
        vnflcm_base.FAKE_SERVER_MANAGER.set_callback('GET',
            os.path.join(
                fake_vnfpkgm.VnfPackage.VNF_PACKAGE_REQ_PATH,
                vnf_package_id,
                'vnfd'),
            status_code=200,
            response_headers={"Content-Type": "application/zip"},
            content=tempname)

        return vnf_package_info

    def test_inst_chgextconn_term(self):
        """Test basic life cycle operations with sample VNFD with UserData.

        In this test case, we do following steps.
            - Create subscription.
            - Test notification.
            - Create VNF instance.
            - Instantiate VNF.
            - List VNF instances.
            - Show VNF instance.
            - Change External VNF Connectivity.
            - Get opOccs information.
            - Terminate VNF.
            - Delete VNF.
            - Delete subscription.
            - Show subscription.
        """
        vnf_package_info = self._register_vnf_package_mock_response()
        glance_image = fake_grant.Grant.get_sw_image()
        flavour_vdu_dict = fake_grant.Grant.get_compute_flavor()
        zone_name_list = []
        availability_zone_info = self._list_zone()
        zone_name_list = list(set(
            [zone.zone for zone in availability_zone_info
             if zone.binary == 'nova-compute']))
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

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance_from_body(
            fake_vnflcm.VnfInstances.make_create_request_body(
                vnf_package_info['vnfdId']))
        vnf_instance_id = vnf_instance.get('id')
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self._assert_create_vnf(resp, vnf_instance)
        vnf_instance_name = vnf_instance['vnfInstanceName']
        self.addCleanup(self._delete_vnf_instance, vnf_instance_id)

        # Set Fake server response for Grant-Req(Instantiate)
        vnflcm_base.FAKE_SERVER_MANAGER.set_callback('POST',
            fake_grant.Grant.GRANT_REQ_PATH, status_code=201,
            callback=lambda req_headers,
            req_body: fake_grant.Grant.make_inst_response_body(
                req_body,
                self.vim['tenant_id'], glance_image,
                flavour_vdu_dict,
                zone_name_list))

        # Instantiate vnf instance
        request_body = fake_vnflcm.VnfInstances.\
            make_inst_request_body_include_num_dynamic(
                self.vim['tenant_id'], self.ext_networks,
                self.ext_mngd_networks, self.ext_link_ports, self.ext_subnets)
        resp, _ = self._instantiate_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self._assert_instantiate_vnf(resp, vnf_instance_id)

        # List vnf instances
        filter_expr = {
            'filter': "(eq,id,{});(eq,vnfInstanceName,{})".format(
                vnf_instance_id, vnf_instance_name)}
        resp, vnf_instances = self._list_vnf_instance(params=filter_expr)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(vnf_instances))

        # Show vnf instance
        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id)
        self.assertEqual(200, resp.status_code)

        # Set Fake server response for Grant-Req(Chnage-ext-conn)
        vnflcm_base.FAKE_SERVER_MANAGER.set_callback(
            'POST',
            fake_grant.Grant.GRANT_REQ_PATH,
            status_code=201,
            callback=lambda req_headers,
            req_body: fake_grant.Grant.make_change_ext_conn_response_body(
                req_body,
                self.vim['tenant_id'],
                zone_name_list))

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
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(
            fake_grant.Grant.GRANT_REQ_PATH)

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

        # occ-show(chgextconn)
        resp, op_occs_info = self._show_op_occs(vnflcm_op_occ_id)
        self._assert_occ_show(resp, op_occs_info)

        # Set Fake server response for Grant-Req(Terminate)
        vnflcm_base.FAKE_SERVER_MANAGER.set_callback('POST',
            fake_grant.Grant.GRANT_REQ_PATH, status_code=201,
            callback=lambda req_headers,
            req_body: fake_grant.Grant.make_term_response_body(req_body))

        # Get stack informations to terminate.
        stack = self._get_heat_stack(vnf_instance_id)
        resources_list = self._get_heat_resource_list(stack.id)
        resource_name_list = [r.resource_name for r in resources_list]
        glance_image_id_list = self._get_glance_image_list_from_stack_resource(
            stack.id, resource_name_list)

        # Terminate VNF
        terminate_req_body = fake_vnflcm.VnfInstances.make_term_request_body()
        resp, _ = self._terminate_vnf_instance(vnf_instance_id,
                terminate_req_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self._assert_terminate_vnf(resp, vnf_instance_id, stack.id,
             resource_name_list, glance_image_id_list)

        # Delete VNF
        resp, _ = self._delete_vnf_instance(vnf_instance_id)
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_delete_vnf(resp, vnf_instance_id)

        # Delete Subscription
        resp, response_body = self._delete_subscription(subscription_id)
        self.assertEqual(204, resp.status_code)

        # Check subscription was deleted
        resp, show_body = self._show_subscription(subscription_id)
        self.assertEqual(404, resp.status_code)

    def test_inst_heal_term(self):
        """Test basic life cycle operations with sample VNFD with UserData.

        In this test case, we do following steps.
            - Create subscription.
            - Create VNF instance.
            - Instantiate VNF.
            - Heal VNF with all VNFc.
            - Terminate VNF
            - Delete VNF
            - Delete subscription
        """
        vnf_package_info = self._register_vnf_package_mock_response()
        glance_image = fake_grant.Grant.get_sw_image()
        flavour_vdu_dict = fake_grant.Grant.get_compute_flavor()
        zone_name_list = []
        availability_zone_info = self._list_zone()
        zone_name_list = list(set(
            [zone.zone for zone in availability_zone_info
             if zone.binary == 'nova-compute']))

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

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance_from_body(
            fake_vnflcm.VnfInstances.make_create_request_body(
                vnf_package_info['vnfdId']))
        vnf_instance_id = vnf_instance.get('id')
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self._assert_create_vnf(resp, vnf_instance)
        self.addCleanup(self._delete_vnf_instance, vnf_instance_id)

        # Set Fake server response for Grant-Req(Instantiate)
        vnflcm_base.FAKE_SERVER_MANAGER.set_callback('POST',
            fake_grant.Grant.GRANT_REQ_PATH, status_code=201,
            callback=lambda req_headers,
            req_body: fake_grant.Grant.make_inst_response_body(
                req_body,
                self.vim['tenant_id'],
                glance_image,
                flavour_vdu_dict,
                zone_name_list))

        # Instantiate vnf instance
        request_body = fake_vnflcm.VnfInstances.\
            make_inst_request_body_include_num_dynamic(
                self.vim['tenant_id'], self.ext_networks,
                self.ext_mngd_networks, self.ext_link_ports, self.ext_subnets)
        resp, _ = self._instantiate_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self._assert_instantiate_vnf(resp, vnf_instance_id)
        self._assert_stack_template(vnf_instance_id)

        # Show vnf instance
        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id)
        self.assertEqual(200, resp.status_code)

        # Set Fake server response for Grant-Req(Heal)
        vnflcm_base.FAKE_SERVER_MANAGER.set_callback('POST',
            fake_grant.Grant.GRANT_REQ_PATH, status_code=201,
            callback=lambda req_headers,
            req_body: fake_grant.Grant.make_heal_response_body(
                req_body,
                self.vim['tenant_id'],
                glance_image,
                flavour_vdu_dict,
                zone_name_list))

        # Heal vnf (exists vnfc_instace_id)
        vnfc_instance_id_list = []

        for vnfc in vnf_instance.get('instantiatedVnfInfo', {}).\
                get('vnfcResourceInfo', []):
            if vnfc.get('vduId') == 'VDU1':
                vnfc_instance_id_list.append(vnfc.get('id'))

        request_body = fake_vnflcm.VnfInstances.make_heal_request_body(
            vnfc_instance_id_list)
        resp, _ = self._heal_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self._assert_heal_vnf(resp, vnf_instance_id)
        self._assert_stack_template(vnf_instance_id)

        # Set Fake server response for Grant-Req(Terminate)
        vnflcm_base.FAKE_SERVER_MANAGER.set_callback('POST',
            fake_grant.Grant.GRANT_REQ_PATH, status_code=201,
            callback=lambda req_headers,
            req_body: fake_grant.Grant.make_term_response_body(req_body))

        # Get stack informations to terminate.
        stack = self._get_heat_stack(vnf_instance_id)
        resources_list = self._get_heat_resource_list(stack.id)
        resource_name_list = [r.resource_name for r in resources_list]
        glance_image_id_list = self._get_glance_image_list_from_stack_resource(
            stack.id, resource_name_list)

        # Terminate VNF
        terminate_req_body = fake_vnflcm.VnfInstances.make_term_request_body()
        resp, _ = self._terminate_vnf_instance(vnf_instance_id,
                terminate_req_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self._assert_terminate_vnf(resp, vnf_instance_id, stack.id,
            resource_name_list, glance_image_id_list)

        # Delete VNF
        resp, _ = self._delete_vnf_instance(vnf_instance_id)
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_delete_vnf(resp, vnf_instance_id)

        # Delete Subscription
        resp, response_body = self._delete_subscription(subscription_id)
        self.assertEqual(204, resp.status_code)

    def test_inst_scale_term(self):
        """Test basic life cycle operations with sample VNFD with UserData.

        In this test case, we do following steps.
            - Create subscription.
            - Create VNF instance.
            - Instantiate VNF.
            - Get VNF informations.
            - Scale-Out VNF
            - Scale-In VNF
            - Terminate VNF
            - Delete VNF
            - Delete subscription
        """
        vnf_package_info = self._register_vnf_package_mock_response(
            package_dir='functional7')
        glance_image = fake_grant.Grant.get_sw_image(
            package_dir='functional7')
        flavour_vdu_dict = fake_grant.Grant.get_compute_flavor(
            package_dir='functional7')
        zone_name_list = []
        availability_zone_info = self._list_zone()
        zone_name_list = list(set(
            [zone.zone for zone in availability_zone_info
             if zone.binary == 'nova-compute']))

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

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance_from_body(
            fake_vnflcm.VnfInstances.make_create_request_body(
                vnf_package_info['vnfdId']))
        vnf_instance_id = vnf_instance.get('id')
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self._assert_create_vnf(resp, vnf_instance)
        self.addCleanup(self._delete_vnf_instance, vnf_instance_id)

        # Set Fake server response for Grant-Req(Instantiate)
        vnflcm_base.FAKE_SERVER_MANAGER.set_callback('POST',
            fake_grant.Grant.GRANT_REQ_PATH, status_code=201,
            callback=lambda req_headers,
            req_body: fake_grant.Grant.make_inst_response_body(
                req_body,
                self.vim['tenant_id'],
                glance_image,
                flavour_vdu_dict,
                zone_name_list))

        # Instantiate vnf instance
        request_body = fake_vnflcm.VnfInstances.\
            make_inst_request_body_include_num_dynamic(
                self.vim['tenant_id'], self.ext_networks,
                self.ext_mngd_networks, self.ext_link_ports, self.ext_subnets)
        resp, _ = self._instantiate_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self._assert_instantiate_vnf(resp, vnf_instance_id)
        self._assert_stack_template_scale(vnf_instance_id)

        # Show vnf instance
        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id)
        self.assertEqual(200, resp.status_code)

        # Set Fake server response for Grant-Req(Scale-out)
        vnflcm_base.FAKE_SERVER_MANAGER.set_callback(
            'POST',
            fake_grant.Grant.GRANT_REQ_PATH, status_code=201,
            callback=lambda req_headers,
            req_body: fake_grant.Grant.make_scale_response_body(
                req_body,
                self.vim['tenant_id'],
                glance_image,
                flavour_vdu_dict,
                zone_name_list))

        # Scale-out vnf instance
        stack = self._get_heat_stack(vnf_instance_id)
        pre_stack_resource_list = self._get_heat_resource_list(stack.id, 2)
        request_body = fake_vnflcm.VnfInstances.\
            make_scale_request_body('SCALE_OUT')
        resp, _ = self._scale_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)

        post_stack_resource_list = self._get_heat_resource_list(stack.id, 2)
        self._assert_scale_vnf(resp, vnf_instance_id,
                               pre_stack_resource_list,
                               post_stack_resource_list,
                               scale_type='SCALE_OUT')

        # Set Fake server response for Grant-Req(Scale-in)
        vnflcm_base.FAKE_SERVER_MANAGER.set_callback(
            'POST',
            fake_grant.Grant.GRANT_REQ_PATH, status_code=201,
            callback=lambda req_headers,
            req_body: fake_grant.Grant.make_scale_response_body(
                req_body,
                self.vim['tenant_id'], glance_image, flavour_vdu_dict,
                zone_name_list))

        # Scale-in vnf instance
        stack = self._get_heat_stack(vnf_instance_id)
        pre_stack_resource_list = self._get_heat_resource_list(stack.id, 2)

        request_body = fake_vnflcm.VnfInstances.make_scale_request_body(
            'SCALE_IN')
        resp, _ = self._scale_vnf_instance(vnf_instance_id, request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)

        post_stack_resource_list = self._get_heat_resource_list(stack.id, 2)
        self._assert_scale_vnf(resp, vnf_instance_id,
                               pre_stack_resource_list,
                               post_stack_resource_list,
                               scale_type='SCALE_IN')

        # Set Fake server response for Grant-Req(Terminate)
        vnflcm_base.FAKE_SERVER_MANAGER.set_callback('POST',
            fake_grant.Grant.GRANT_REQ_PATH, status_code=201,
            callback=lambda req_headers,
            req_body: fake_grant.Grant.make_term_response_body(req_body))

        # Get stack informations to terminate.
        stack = self._get_heat_stack(vnf_instance_id)
        resources_list = self._get_heat_resource_list(stack.id)
        resource_name_list = [r.resource_name for r in resources_list]
        glance_image_id_list = self._get_glance_image_list_from_stack_resource(
            stack.id, resource_name_list)

        # Terminate VNF
        terminate_req_body = fake_vnflcm.VnfInstances.make_term_request_body()
        resp, _ = self._terminate_vnf_instance(vnf_instance_id,
                terminate_req_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_id)
        self._assert_terminate_vnf(resp, vnf_instance_id, stack.id,
            resource_name_list, glance_image_id_list)

        # Delete VNF
        resp, _ = self._delete_vnf_instance(vnf_instance_id)
        self._wait_lcm_done(vnf_instance_id=vnf_instance_id)
        self.assert_delete_vnf(resp, vnf_instance_id)

        # Delete Subscription
        resp, response_body = self._delete_subscription(subscription_id)
        self.assertEqual(204, resp.status_code)

    def _assert_create_vnf(self, resp, vnf_instance):
        """Assert that VNF was created via fake server.

        Args:
            resp (Response): HTTP response object.
            vnf_instance (Dict): VNF instance information.
        """
        super().assert_create_vnf(resp, vnf_instance)

        # FT-checkpoint: VnfPkgId
        vnf_pkg_mock_responses = vnflcm_base.FAKE_SERVER_MANAGER.get_history(
            fake_vnfpkgm.VnfPackage.VNF_PACKAGE_REQ_PATH)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(
            fake_vnfpkgm.VnfPackage.VNF_PACKAGE_REQ_PATH)

        self.assertEqual(1, len(vnf_pkg_mock_responses))
        vnf_pkg_info_list = vnf_pkg_mock_responses[0]
        self.assertEqual(vnf_instance['vnfPkgId'],
            vnf_pkg_info_list.response_body[0]['id'])

    def _assert_instantiate_vnf(self, resp, vnf_instance_id):
        """Assert that VNF was instantiated.

        This method calls same name method of super class and that
        checks heat resource status 'CREATE_COMPLETE', then assert
        notifications of instantiation.
        Then, we check Grant response in this method.

        Args:
            resp (Response): HTTP response object.
            vnf_instance_id (str): VNF instance id.
        """
        super().assert_instantiate_vnf(resp, vnf_instance_id)

        # FT-checkpoint: Grant Response
        grant_mock_responses = vnflcm_base.FAKE_SERVER_MANAGER.get_history(
            fake_grant.Grant.GRANT_REQ_PATH)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(
            fake_grant.Grant.GRANT_REQ_PATH)
        self.assertEqual(1, len(grant_mock_responses))
        self._assert_grant_mock_response(grant_mock_responses[0])

    def _assert_heal_vnf(self, resp, vnf_instance_id,
            expected_stack_status='UPDATE_COMPLETE'):
        """Assert that VNF was healed.

        This method calls same name method of super class and that
        checks heat resource status 'UPDATE_COMPLETE', then assert
        notifications of healing.
        Then, we check Grant response in this method.

        Args:
            resp (Response): HTTP response object.
            vnf_instance_id (str): VNF instance id.
            expected_stack_status (str, optional): self explanatory :)
                                        Defaults to 'UPDATE_COMPLETE'.
        """
        super().assert_heal_vnf(
            resp, vnf_instance_id, expected_stack_status=expected_stack_status)

        # FT-checkpoint: Grant Response
        grant_mock_responses = vnflcm_base.FAKE_SERVER_MANAGER.get_history(
            fake_grant.Grant.GRANT_REQ_PATH)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(
            fake_grant.Grant.GRANT_REQ_PATH)
        self.assertEqual(1, len(grant_mock_responses))
        self._assert_grant_mock_response(grant_mock_responses[0])

    def _assert_scale_vnf(self,
            resp,
            vnf_instance_id,
            pre_stack_resource_list,
            post_stack_resource_list,
            scale_type):
        super().assert_scale_vnf(
            resp,
            vnf_instance_id,
            pre_stack_resource_list,
            post_stack_resource_list,
            scale_type=scale_type)

        # FT-checkpoint: Grant Response
        grant_mock_responses = vnflcm_base.FAKE_SERVER_MANAGER.get_history(
            fake_grant.Grant.GRANT_REQ_PATH)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(
            fake_grant.Grant.GRANT_REQ_PATH)
        self.assertEqual(1, len(grant_mock_responses))
        self._assert_grant_mock_response(grant_mock_responses[0])

    def _assert_terminate_vnf(self, resp, vnf_instance_id, stack_id,
            resource_name_list, glance_image_id_list):
        """Assert that VNF was terminated.

        This method calls same name method of super class to check specified
        VNF instance is 'NOT_INSTANTIATED'
        Then, we check Grant response in this method.

        Args:
            resp (Response): HTTP response object.
            vnf_instance_id (str): VNF instance id.
            stack_id (str): Resource id of heat stack to check.
            resource_name_list (list[str]): List of heat stack resources.
            glance_image_id_list (list[str]): List of glance image ids.
        """
        super().assert_terminate_vnf(resp, vnf_instance_id, stack_id,
            resource_name_list, glance_image_id_list)

        # FT-checkpoint: Grant Response
        grant_mock_responses = vnflcm_base.FAKE_SERVER_MANAGER.get_history(
            fake_grant.Grant.GRANT_REQ_PATH)
        vnflcm_base.FAKE_SERVER_MANAGER.clear_history(
            fake_grant.Grant.GRANT_REQ_PATH)
        self.assertEqual(1, len(grant_mock_responses))
        self._assert_grant_mock_response(grant_mock_responses[0])

    def _assert_grant_mock_response(self, grant_mock_response,
            expected_auth_type=None, expected_token_value=None):
        """Assert that HTTP response code is equal to 201 or not.

        This method checks response code of grant request and
        authorization result.

        Args:
            grant_mock_response (Response): HTTP response object.
            expected_auth_type (str, optional): Authentication type.
                                                Defaults to None.
            expected_token_value ([type], optional): Authentication token.
                                                     Defaults to None.
        """
        self.assertEqual(201, grant_mock_response.status_code)

        actual_auth = grant_mock_response.request_headers.get("Authorization")
        if expected_auth_type is None:
            self.assertIsNone(actual_auth)
            return

        self.assertEqual(
            '{} {}'.format(expected_auth_type, expected_token_value),
            actual_auth)

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
        self.assertTrue(res_name)

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

    def _assert_stack_template(self, vnf_instance_id):
        stack = self._get_heat_stack(vnf_instance_id)
        resources_list\
            = self._get_heat_resource_list(stack.id, nested_depth=2)
        stack_name_wd = vnf_instance_id + "-VDU2"
        physical_resource_id = [r.physical_resource_id for r
        in resources_list if stack_name_wd in r.stack_name]
        template = self._get_heat_stack_template(physical_resource_id[0])
        template_count = str(template).count("flavor")
        self.assertEqual(template_count, 3)

    def _assert_stack_template_scale(self, vnf_instance_id):
        stack = self._get_heat_stack(vnf_instance_id)
        resources_list\
            = self._get_heat_resource_list(stack.id, nested_depth=2)
        stack_name_wd = vnf_instance_id + "-VDU1"
        physical_resource_id = [r.physical_resource_id for r
        in resources_list if stack_name_wd in r.stack_name]
        template = self._get_heat_stack_template(physical_resource_id[0])
        template_count = str(template).count("zone")
        self.assertEqual(template_count, 3)
