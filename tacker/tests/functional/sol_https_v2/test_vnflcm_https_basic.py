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

from tacker.sol_refactored.common import config

from tacker.objects import fields
from tacker.tests.functional.sol_https_v2 import paramgen
from tacker.tests.functional.sol_separated_nfvo_v2 import fake_grant_v2
from tacker.tests.functional.sol_v2_common import test_vnflcm_basic_common
from tacker.tests import utils

CONF = config.CONF


@ddt.ddt
class VnfLcmWithHttpsRequest(test_vnflcm_basic_common.CommonVnfLcmTest):
    @classmethod
    def setUpClass(cls):
        cls.is_https = True
        super(VnfLcmWithHttpsRequest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmWithHttpsRequest, cls).tearDownClass()

    def setUp(self):
        super().setUp()

    def test_vnflcm_over_https_no_auth(self):
        """Test LCM operations over https with no auth

        * About attributes:
          Omit except for required attributes.
          Only the following cardinality attributes are set.
          - 1
          - 1..N (1)

        * About LCM operations:
          This test includes the following operations.
          - 1. Create subscription
          - 2. Show subscription
          - 3. Create VNF instance
          - 4. Instantiate VNF
          - 5. Show VNF instance
          - 6. Terminate VNF
          - 7. Delete VNF instance
          - 8. Delete subscription
          - 9. Show subscription
        """
        # setup
        basic_lcms_min_path = utils.test_sample("functional/sol_v2_common",
                                                "basic_lcms_min")
        min_zip_path, min_vnfd_id = self.create_vnf_package(
            basic_lcms_min_path, nfvo=True)

        vnfd_path = "contents/Definitions/v2_sample2_df_simple.yaml"
        self._register_vnf_package_mock_response(min_vnfd_id,
                                                 min_zip_path)

        glance_image = fake_grant_v2.GrantV2.get_sw_image(
            basic_lcms_min_path, vnfd_path)
        flavour_vdu_dict = fake_grant_v2.GrantV2.get_compute_flavor(
            basic_lcms_min_path, vnfd_path)

        zone_name_list = self.get_zone_list()
        create_req = paramgen.create_vnf_min(min_vnfd_id)

        # 1. LCM-Create-Subscription
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('https://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_https_no_auth(callback_uri)

        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']
        self.assert_notification_get(callback_url)

        # 2. LCM-Show-Subscription
        resp, body = self.show_subscription(sub_id)
        self.assertEqual(200, resp.status_code)

        # 3. LCM-Create
        expected_inst_attrs = [
            'id',
            # 'vnfInstanceName', # omitted
            # 'vnfInstanceDescription', # omitted
            'vnfdId',
            'vnfProvider',
            'vnfProductName',
            'vnfSoftwareVersion',
            'vnfdVersion',
            # 'vnfConfigurableProperties', # omitted
            # 'vimConnectionInfo', # omitted
            'instantiationState',
            # 'instantiatedVnfInfo', # omitted
            # 'metadata', # omitted
            # 'extensions', # omitted
            '_links'
        ]
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # 4. LCM-Instantiate
        self._set_grant_response(
            True, 'INSTANTIATE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
        instantiate_req = paramgen.instantiate_vnf_min()
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)
        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.INSTANTIATED,
                         body['instantiationState'])

        # 5. LCM-Show
        self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # 6. LCM-Terminate
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check deletion of Heat-stack
        stack_name = "vnf-{}".format(inst_id)
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertIsNone(stack_status)

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # 7. LCM-Delete
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

        # 8. LCM-Delete-subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 9. LCM-Show-Subscription
        resp, body = self.show_subscription(sub_id)
        self.assertEqual(404, resp.status_code)

    def test_vnflcm_over_https_basic_auth(self, is_nfvo=False):
        """Test LCM operations over https with basic auth

        * About attributes:
          Omit except for required attributes.
          Only the following cardinality attributes are set.
          - 1
          - 1..N (1)

        * About LCM operations:
          This test includes the following operations.
          - 1. Create subscription
          - 2. Show subscription
          - 3. Create VNF instance
          - 4. Instantiate VNF
          - 5. Show VNF instance
          - 6. Terminate VNF
          - 7. Delete VNF instance
          - 8. Delete subscription
          - 9. Show subscription
        """
        # setup
        basic_lcms_min_path = utils.test_sample("functional/sol_v2_common",
                                                "basic_lcms_min")
        min_zip_path, min_vnfd_id = self.create_vnf_package(
            basic_lcms_min_path, nfvo=True)

        vnfd_path = "contents/Definitions/v2_sample2_df_simple.yaml"
        self._register_vnf_package_mock_response(min_vnfd_id,
                                                 min_zip_path)

        glance_image = fake_grant_v2.GrantV2.get_sw_image(
            basic_lcms_min_path, vnfd_path)
        flavour_vdu_dict = fake_grant_v2.GrantV2.get_compute_flavor(
            basic_lcms_min_path, vnfd_path)

        zone_name_list = self.get_zone_list()
        create_req = paramgen.create_vnf_min(min_vnfd_id)

        # 1. LCM-Create-Subscription
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('https://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        sub_req = paramgen.sub_create_https_basic_auth(callback_uri)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']
        self.assert_notification_get(callback_url)

        # 2. LCM-Show-Subscription
        resp, body = self.show_subscription(sub_id)
        self.assertEqual(200, resp.status_code)

        # 3. LCM-Create
        expected_inst_attrs = [
            'id',
            # 'vnfInstanceName', # omitted
            # 'vnfInstanceDescription', # omitted
            'vnfdId',
            'vnfProvider',
            'vnfProductName',
            'vnfSoftwareVersion',
            'vnfdVersion',
            # 'vnfConfigurableProperties', # omitted
            # 'vimConnectionInfo', # omitted
            'instantiationState',
            # 'instantiatedVnfInfo', # omitted
            # 'metadata', # omitted
            # 'extensions', # omitted
            '_links'
        ]
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # 4. LCM-Instantiate
        self._set_grant_response(
            True, 'INSTANTIATE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
        instantiate_req = paramgen.instantiate_vnf_min()
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)
        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.INSTANTIATED,
                         body['instantiationState'])

        # 5. LCM-Show
        self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # 6. LCM-Terminate
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check deletion of Heat-stack
        stack_name = "vnf-{}".format(inst_id)
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertIsNone(stack_status)

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # 7. LCM-Delete
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

        # 8. LCM-Delete-subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 9. LCM-Show-Subscription
        resp, body = self.show_subscription(sub_id)
        self.assertEqual(404, resp.status_code)

    def test_vnflcm_over_https_oauth2_cred_auth(self, is_nfvo=False):
        """Test LCM operations over https with oauth2 auth

        * About attributes:
          Omit except for required attributes.
          Only the following cardinality attributes are set.
          - 1
          - 1..N (1)

        * About LCM operations:
          This test includes the following operations.
          - 1. Create subscription
          - 2. Show subscription
          - 3. Create VNF instance
          - 4. Instantiate VNF
          - 5. Show VNF instance
          - 6. Terminate VNF
          - 7. Delete VNF instance
          - 8. Delete subscription
          - 9. Show subscription
        """
        # setup
        basic_lcms_min_path = utils.test_sample("functional/sol_v2_common",
                                                "basic_lcms_min")
        min_zip_path, min_vnfd_id = self.create_vnf_package(
            basic_lcms_min_path, nfvo=True)

        vnfd_path = "contents/Definitions/v2_sample2_df_simple.yaml"
        self._register_vnf_package_mock_response(min_vnfd_id,
                                                 min_zip_path)

        glance_image = fake_grant_v2.GrantV2.get_sw_image(
            basic_lcms_min_path, vnfd_path)
        flavour_vdu_dict = fake_grant_v2.GrantV2.get_compute_flavor(
            basic_lcms_min_path, vnfd_path)

        zone_name_list = self.get_zone_list()
        create_req = paramgen.create_vnf_min(min_vnfd_id)

        # 1. LCM-Create-Subscription
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('https://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        sub_req = paramgen.sub_create_https_oauth2_auth(callback_uri)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']
        self.assert_notification_get(callback_url)

        # 2. LCM-Show-Subscription
        resp, body = self.show_subscription(sub_id)
        self.assertEqual(200, resp.status_code)

        # 3. LCM-Create
        expected_inst_attrs = [
            'id',
            # 'vnfInstanceName', # omitted
            # 'vnfInstanceDescription', # omitted
            'vnfdId',
            'vnfProvider',
            'vnfProductName',
            'vnfSoftwareVersion',
            'vnfdVersion',
            # 'vnfConfigurableProperties', # omitted
            # 'vimConnectionInfo', # omitted
            'instantiationState',
            # 'instantiatedVnfInfo', # omitted
            # 'metadata', # omitted
            # 'extensions', # omitted
            '_links'
        ]
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # 4. LCM-Instantiate
        self._set_grant_response(
            True, 'INSTANTIATE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
        instantiate_req = paramgen.instantiate_vnf_min()
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)
        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.INSTANTIATED,
                         body['instantiationState'])

        # 5. LCM-Show
        self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # 6. LCM-Terminate
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check deletion of Heat-stack
        stack_name = "vnf-{}".format(inst_id)
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertIsNone(stack_status)

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # 7. LCM-Delete
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

        # 8. LCM-Delete-subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 9. LCM-Show-Subscription
        resp, body = self.show_subscription(sub_id)
        self.assertEqual(404, resp.status_code)
