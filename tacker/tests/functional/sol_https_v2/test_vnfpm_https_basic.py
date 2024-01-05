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

from tacker.common import rpc
from tacker import context
from tacker.sol_refactored.common import config
from tacker.sol_refactored.conductor import conductor_rpc_v2
from tacker.tests.functional.sol_https_v2 import paramgen
from tacker.tests.functional.sol_separated_nfvo_v2 import fake_grant_v2
from tacker.tests.functional.sol_v2_common import test_vnflcm_basic_common
from tacker.tests import utils

CONF = config.CONF

VNFPM_V2_VERSION = "2.1.0"
WAIT_NOTIFICATION_TIME = 5


@ddt.ddt
class VnfPmWithHttpsRequestTest(test_vnflcm_basic_common.CommonVnfLcmTest):

    @classmethod
    def setUpClass(cls):
        cls.is_https = True
        super(VnfPmWithHttpsRequestTest, cls).setUpClass()
        cls.fake_prometheus_ip = cls._get_controller_tacker_ip(cls)
        rpc.init(CONF)

    @classmethod
    def tearDownClass(cls):
        super(VnfPmWithHttpsRequestTest, cls).tearDownClass()

    def setUp(self):
        super(VnfPmWithHttpsRequestTest, self).setUp()
        self.set_server_callback(
            'PUT', "/-/reload", status_code=202,
            response_headers={"Content-Type": "text/plain"})

    def _get_controller_tacker_ip(cls):
        cur_dir = os.path.dirname(__file__)
        script_path = os.path.join(
            cur_dir, "../tools/test-setup-fake-prometheus-server.sh")
        with open(script_path, 'r') as f_obj:
            content = f_obj.read()
        ip = content.split('TEST_REMOTE_URI')[1].split(
            'http://')[1].split('"')[0]
        return ip

    def _create_pm_job(self, req_body):
        path = "/vnfpm/v2/pm_jobs"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version=VNFPM_V2_VERSION)

    def _create_pm_event(self, req_body):
        path = "/pm_event"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version=VNFPM_V2_VERSION)

    def _delete_pm_job(self, pm_job_id):
        path = f"/vnfpm/v2/pm_jobs/{pm_job_id}"
        return self.tacker_client.do_request(
            path, "DELETE", version=VNFPM_V2_VERSION)

    def test_pm_notification_over_https_no_auth(self):
        """Test PM operations over https with no auth

        * About attributes:
          Omit except for required attributes.
          Only the following cardinality attributes are set.
          - 1
          - 1..N (1)

        * About LCM operations:
          This test includes the following operations.
          - 1. Create VNF instance
          - 2. Instantiate VNF
          - 3. PMJob-Create
          - 4. PM-Event
          - 5. PMJob-Delete
          - 6. Terminate VNF
          - 7. Delete VNF instance
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

        # 1. LCM-Create
        self._set_grant_response(
            True, 'INSTANTIATE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
        create_req = paramgen.create_vnf_min(min_vnfd_id)
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
        callback_uri = ('https://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        sub_req = paramgen.pm_job_https_no_auth(
            callback_uri, inst_id, self.fake_prometheus_ip)
        resp, body = self._create_pm_job(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, pm_expected_attrs)
        # Test notification
        self.assert_notification_get(callback_url)
        pm_job_id = body.get('id')

        # 4. PM-Event
        r = conductor_rpc_v2.PrometheusPluginConductor()
        ctx = context.get_admin_context()
        entries = paramgen.entries(body, inst_id)
        r.store_job_info(ctx, entries)
        time.sleep(WAIT_NOTIFICATION_TIME)
        self._check_notification(
            callback_url, 'PerformanceInformationAvailableNotification')

        # 5. PMJob-Delete
        resp, body = self._delete_pm_job(pm_job_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

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

    def test_pm_notification_over_https_basic_auth(self):
        """Test PM operations over https with basic auth

        * About attributes:
          Omit except for required attributes.
          Only the following cardinality attributes are set.
          - 1
          - 1..N (1)

        * About LCM operations:
          This test includes the following operations.
          - 1. Create VNF instance
          - 2. Instantiate VNF
          - 3. PMJob-Create
          - 4. PM-Event
          - 5. PMJob-Delete
          - 6. Terminate VNF
          - 7. Delete VNF instance
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

        # 1. LCM-Create
        create_req = paramgen.create_vnf_min(min_vnfd_id)
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
        callback_uri = ('https://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        sub_req = paramgen.pm_job_https_basic_auth(
            callback_uri, inst_id, self.fake_prometheus_ip)
        resp, body = self._create_pm_job(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, pm_expected_attrs)
        # Test notification
        self.assert_notification_get(callback_url)
        pm_job_id = body.get('id')

        # 4. PM-Event
        r = conductor_rpc_v2.PrometheusPluginConductor()
        ctx = context.get_admin_context()
        entries = paramgen.entries(body, inst_id)
        r.store_job_info(ctx, entries)
        time.sleep(WAIT_NOTIFICATION_TIME)
        self._check_notification(
            callback_url, 'PerformanceInformationAvailableNotification')

        # 5. PMJob-Delete
        resp, body = self._delete_pm_job(pm_job_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)
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

    def test_pm_notification_over_https_oauth2_cred_auth(self):
        """Test PM operations over https with oauth2 auth

        * About attributes:
          Omit except for required attributes.
          Only the following cardinality attributes are set.
          - 1
          - 1..N (1)

        * About LCM operations:
          This test includes the following operations.
          - 1. Create VNF instance
          - 2. Instantiate VNF
          - 3. PMJob-Create
          - 4. PM-Event
          - 5. PMJob-Delete
          - 6. Terminate VNF
          - 7. Delete VNF instance
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

        # 1. LCM-Create
        self._set_grant_response(
            True, 'INSTANTIATE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
        create_req = paramgen.create_vnf_min(min_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']
        # 2. LCM-Instantiate
        instantiate_req = paramgen.instantiate_vnf_min()
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
        callback_uri = ('https://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        sub_req = paramgen.pm_job_https_oauth2_auth(
            callback_uri, inst_id, self.fake_prometheus_ip)
        resp, body = self._create_pm_job(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, pm_expected_attrs)
        # Test notification
        self.assert_notification_get(callback_url)
        pm_job_id = body.get('id')

        # 4. PM-Event
        r = conductor_rpc_v2.PrometheusPluginConductor()
        ctx = context.get_admin_context()
        entries = paramgen.entries(body, inst_id)
        r.store_job_info(ctx, entries)
        time.sleep(WAIT_NOTIFICATION_TIME)
        self._check_notification(
            callback_url, 'PerformanceInformationAvailableNotification')

        # 5. PMJob-Delete
        resp, body = self._delete_pm_job(pm_job_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

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
