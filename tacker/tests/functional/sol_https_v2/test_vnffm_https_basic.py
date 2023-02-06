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

from tacker.common import rpc
from tacker import context
from tacker.objects import fields
from tacker.sol_refactored.common import config
from tacker.sol_refactored.conductor import conductor_rpc_v2
from tacker.tests.functional.sol_https_v2 import paramgen
from tacker.tests.functional.sol_separated_nfvo_v2 import fake_grant_v2
from tacker.tests.functional.sol_v2_common import base_v2
from tacker.tests.functional.sol_v2_common import test_vnflcm_basic_common

CONF = config.CONF


@ddt.ddt
class VnfFmWithHttpsRequestTest(test_vnflcm_basic_common.CommonVnfLcmTest):

    @classmethod
    def setUpClass(cls):
        cls.is_https = True
        super(VnfFmWithHttpsRequestTest, cls).setUpClass()
        rpc.init(CONF)

    @classmethod
    def tearDownClass(cls):
        super(VnfFmWithHttpsRequestTest, cls).tearDownClass()

    def setUp(self):
        super(VnfFmWithHttpsRequestTest, self).setUp()

    def _create_fm_subscription(self, req_body):
        path = "/vnffm/v1/subscriptions"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="1.3.0")

    def _delete_fm_subscription(self, sub_id):
        path = "/vnffm/v1/subscriptions/{}".format(sub_id)
        return self.tacker_client.do_request(
            path, "DELETE", version="1.3.0")

    def _create_fm_alarm(self, req_body):
        path = "/alert"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="1.3.0")

    def _check_notification(self, callback_url, notify_type):
        notify_mock_responses = base_v2.FAKE_SERVER_MANAGER.get_history(
            callback_url)
        base_v2.FAKE_SERVER_MANAGER.clear_history(
            callback_url)
        self.assertEqual(1, len(notify_mock_responses))
        self.assertEqual(204, notify_mock_responses[0].status_code)
        self.assertEqual(notify_type, notify_mock_responses[0].request_body[
            'notificationType'])

    def test_fm_notification_over_https_no_auth(self):
        """Test FM operations over https with no auth

        * About attributes:
          Omit except for required attributes.
          Only the following cardinality attributes are set.
          - 1
          - 1..N (1)

        * About LCM operations:
          This test includes the following operations.
          - 1. Create VNF instance
          - 2. Instantiate VNF
          - 3. Create FM subscription
          - 4. Alert-Event (firing)
          - 5. FM-Delete-Subscription
          - 6. Terminate VNF
          - 7. Delete VNF instance
        """

        # setup
        cur_dir = os.path.dirname(__file__)
        basic_lcms_min_path = os.path.join(
            cur_dir, "../sol_v2_common/samples/basic_lcms_min")
        zip_path_file_1, vnfd_id_1 = self.create_vnf_package(
            basic_lcms_min_path, nfvo=True)
        vnfd_path = "contents/Definitions/v2_sample2_df_simple.yaml"
        self._register_vnf_package_mock_response(vnfd_id_1,
                                                 zip_path_file_1)
        glance_image = fake_grant_v2.GrantV2.get_sw_image(
            basic_lcms_min_path, vnfd_path)
        flavour_vdu_dict = fake_grant_v2.GrantV2.get_compute_flavor(
            basic_lcms_min_path, vnfd_path)
        zone_name_list = self.get_zone_list()

        # 1. LCM-Create
        create_req = paramgen.create_vnf_min(vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # 2. LCM-Instantiate
        self._set_grant_response(
            True, 'INSTANTIATE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
        instantiate_req = paramgen.instantiate_vnf_min()
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 3. FM-Create-Subscription
        expected_inst_attrs = ['id', 'callbackUri', '_links']
        callback_url = os.path.join(base_v2.MOCK_NOTIFY_CALLBACK_URL,
                                    self._testMethodName)
        callback_uri = ('https://localhost:'
                        f'{base_v2.FAKE_SERVER_MANAGER.SERVER_PORT}'
                        f'{callback_url}')
        sub_req = paramgen.sub_create_https_no_auth(callback_uri)
        resp, body = self._create_fm_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']
        self.check_resp_body(body, expected_inst_attrs)
        # Test notification
        self.assert_notification_get(callback_url)

        # 4. Alert-Event (firing)
        r = conductor_rpc_v2.PrometheusPluginConductor()
        ctx = context.get_admin_context()
        alarm = paramgen.alarm(inst_id)
        r.store_alarm_info(ctx, alarm)
        time.sleep(5)
        self._check_notification(callback_url, 'AlarmNotification')

        # 5. FM-Delete-Subscription
        resp, body = self._delete_fm_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 6. LCM-Terminate
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 7. LCM-Delete
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

    def test_fm_notification_over_https_basic_auth(self):
        """Test FM operations over https with basic auth

        * About attributes:
          Omit except for required attributes.
          Only the following cardinality attributes are set.
          - 1
          - 1..N (1)

        * About LCM operations:
          This test includes the following operations.
          - 1. Create VNF instance
          - 2. Instantiate VNF
          - 3. Create FM subscription
          - 4. Alert-Event (firing)
          - 5. FM-Delete-Subscription
          - 6. Terminate VNF
          - 7. Delete VNF instance
        """
        # setup
        cur_dir = os.path.dirname(__file__)
        basic_lcms_min_path = os.path.join(
            cur_dir, "../sol_v2_common/samples/basic_lcms_min")
        zip_path_file_1, vnfd_id_1 = self.create_vnf_package(
            basic_lcms_min_path, nfvo=True)
        vnfd_path = "contents/Definitions/v2_sample2_df_simple.yaml"
        self._register_vnf_package_mock_response(vnfd_id_1,
                                                 zip_path_file_1)
        glance_image = fake_grant_v2.GrantV2.get_sw_image(
            basic_lcms_min_path, vnfd_path)
        flavour_vdu_dict = fake_grant_v2.GrantV2.get_compute_flavor(
            basic_lcms_min_path, vnfd_path)
        zone_name_list = self.get_zone_list()

        # 1. LCM-Create
        create_req = paramgen.create_vnf_min(vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']
        # 2. LCM-Instantiate
        self._set_grant_response(
            True, 'INSTANTIATE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
        instantiate_req = paramgen.instantiate_vnf_min()
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # 3. FM-Create-Subscription
        expected_inst_attrs = ['id', 'callbackUri', '_links']
        callback_url = os.path.join(base_v2.MOCK_NOTIFY_CALLBACK_URL,
                                    self._testMethodName)
        callback_uri = ('https://localhost:'
                        f'{base_v2.FAKE_SERVER_MANAGER.SERVER_PORT}'
                        f'{callback_url}')
        sub_req = paramgen.sub_create_https_basic_auth(
            callback_uri)
        resp, body = self._create_fm_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']
        self.check_resp_body(body, expected_inst_attrs)
        # Test notification
        self.assert_notification_get(callback_url)

        # 4. Alert-Event (firing)
        r = conductor_rpc_v2.PrometheusPluginConductor()
        ctx = context.get_admin_context()
        alarm = paramgen.alarm(inst_id)
        r.store_alarm_info(ctx, alarm)
        time.sleep(5)
        self._check_notification(callback_url, 'AlarmNotification')

        # 5. FM-Delete-Subscription
        resp, body = self._delete_fm_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 6. LCM-Terminate
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 7. LCM-Delete
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

    def test_fm_notification_over_https_oauth2_cred_auth(self):
        """Test FM operations over https with oauth2 auth

        * About attributes:
          Omit except for required attributes.
          Only the following cardinality attributes are set.
          - 1
          - 1..N (1)

        * About LCM operations:
          This test includes the following operations.
          - 1. Create VNF instance
          - 2. Instantiate VNF
          - 3. Create FM subscription
          - 4. Alert-Event (firing)
          - 5. FM-Delete-Subscription
          - 6. Terminate VNF
          - 7. Delete VNF instance
        """
        # setup
        cur_dir = os.path.dirname(__file__)
        basic_lcms_min_path = os.path.join(
            cur_dir, "../sol_v2_common/samples/basic_lcms_min")
        zip_path_file_1, vnfd_id_1 = self.create_vnf_package(
            basic_lcms_min_path, nfvo=True)
        vnfd_path = "contents/Definitions/v2_sample2_df_simple.yaml"
        self._register_vnf_package_mock_response(vnfd_id_1,
                                                 zip_path_file_1)
        glance_image = fake_grant_v2.GrantV2.get_sw_image(
            basic_lcms_min_path, vnfd_path)
        flavour_vdu_dict = fake_grant_v2.GrantV2.get_compute_flavor(
            basic_lcms_min_path, vnfd_path)
        zone_name_list = self.get_zone_list()

        # 1. LCM-Create
        create_req = paramgen.create_vnf_min(vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # 2. LCM-Instantiate
        self._set_grant_response(
            True, 'INSTANTIATE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
        instantiate_req = paramgen.instantiate_vnf_min()
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # 3. FM-Create-Subscription
        expected_inst_attrs = ['id', 'callbackUri', '_links']
        callback_url = os.path.join(base_v2.MOCK_NOTIFY_CALLBACK_URL,
                                    self._testMethodName)
        callback_uri = ('https://localhost:'
                        f'{base_v2.FAKE_SERVER_MANAGER.SERVER_PORT}'
                        f'{callback_url}')
        sub_req = paramgen.sub_create_https_oauth2_auth(
            callback_uri)
        resp, body = self._create_fm_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']
        self.check_resp_body(body, expected_inst_attrs)
        time.sleep(10)
        # Test notification
        self.assert_notification_get(callback_url)

        # 4. Alert-Event (firing)
        r = conductor_rpc_v2.PrometheusPluginConductor()
        ctx = context.get_admin_context()
        alarm = paramgen.alarm(inst_id)
        r.store_alarm_info(ctx, alarm)
        time.sleep(5)
        self._check_notification(callback_url, 'AlarmNotification')

        # 5. FM-Delete-Subscription
        resp, body = self._delete_fm_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 6. LCM-Terminate
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 7. LCM-Delete
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)
