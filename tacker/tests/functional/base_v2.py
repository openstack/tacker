# Copyright (C) 2023 Nippon Telegraph and Telephone Corporation
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

import os
import shutil
import tempfile
import time
import urllib
import yaml

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils
from tempest.lib import base

from tacker.sol_refactored.common import http_client
from tacker.sol_refactored import objects
from tacker.tests.functional.common.fake_server import FakeServerManager
from tacker.tests.functional.sol_v2_common import utils
from tacker.tests import utils as base_utils
from tacker import version

FAKE_SERVER_MANAGER = FakeServerManager()
MOCK_NOTIFY_CALLBACK_URL = '/notification/callback'

RETRY_WAIT_TIME = 3
VNF_PACKAGE_UPLOAD_TIMEOUT = 300

VNFLCM_V2_VERSION = "2.0.0"
VNFPM_V2_VERSION = "2.1.0"
VNFFM_V1_VERSION = "1.3.0"

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class BaseTackerTestV2(base.BaseTestCase):
    """Base test case class for SOL v2 functional tests."""

    @classmethod
    def setUpClass(cls):
        super(BaseTackerTestV2, cls).setUpClass()

        FAKE_SERVER_MANAGER.prepare_http_server()
        if getattr(cls, 'is_https', False):
            FAKE_SERVER_MANAGER.set_https_server()
        FAKE_SERVER_MANAGER.start_server()

        cfg.CONF(args=['--config-file', '/etc/tacker/tacker.conf'],
                 project='tacker',
                 version=f'%%prog {version.version_info.release_string()}')
        objects.register_all()

        vim_info = cls.get_vim_info()
        cls.auth_handle = http_client.KeystonePasswordAuthHandle(
            auth_url=vim_info.interfaceInfo['endpoint'],
            username=vim_info.accessInfo['username'],
            password=vim_info.accessInfo['password'],
            project_name=vim_info.accessInfo['project'],
            user_domain_name=vim_info.accessInfo['userDomain'],
            project_domain_name=vim_info.accessInfo['projectDomain']
        )
        cls.tacker_client = http_client.HttpClient(cls.auth_handle)

    @classmethod
    def tearDownClass(cls):
        super(BaseTackerTestV2, cls).tearDownClass()
        FAKE_SERVER_MANAGER.stop_server()

    @classmethod
    def get_vim_info(cls):
        vim_params = yaml.safe_load(base_utils.read_file('local-vim.yaml'))
        vim_params['auth_url'] = f"{vim_params['auth_url']}/v3"

        vim_info = objects.VimConnectionInfo(
            interfaceInfo={'endpoint': vim_params['auth_url']},
            accessInfo={
                'region': 'RegionOne',
                'project': vim_params['project_name'],
                'username': vim_params['username'],
                'password': vim_params['password'],
                'userDomain': vim_params['user_domain_name'],
                'projectDomain': vim_params['project_domain_name']
            }
        )

        return vim_info

    def setUp(self):
        super().setUp()

        callback_url = os.path.join(
            MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        FAKE_SERVER_MANAGER.clear_history(callback_url)
        FAKE_SERVER_MANAGER.set_callback('POST', callback_url, status_code=204)
        FAKE_SERVER_MANAGER.set_callback('GET', callback_url, status_code=204)

    def get_notify_callback_url(self):
        return MOCK_NOTIFY_CALLBACK_URL

    def get_server_port(self):
        return FAKE_SERVER_MANAGER.SERVER_PORT

    def set_server_callback(self, method, uri, **kwargs):
        FAKE_SERVER_MANAGER.set_callback(method, uri, **kwargs)

    @classmethod
    def create_vnf_package(cls, sample_path, user_data={},
                           image_path=None, nfvo=False, userdata_path=None,
                           provider=None, namespace=None, vnfd_id=None,
                           mgmt_driver=None):
        if vnfd_id is None:
            vnfd_id = uuidutils.generate_uuid()

        tmp_dir = tempfile.mkdtemp()

        utils.make_zip(sample_path, tmp_dir, vnfd_id, image_path,
                       userdata_path, provider, namespace, mgmt_driver)

        zip_file_name = f"{os.path.basename(os.path.abspath(sample_path))}.zip"
        zip_file_path = os.path.join(tmp_dir, zip_file_name)

        if nfvo:
            return zip_file_path, vnfd_id

        path = "/vnfpkgm/v1/vnf_packages"
        req_body = {'userDefinedData': user_data}
        resp, body = cls.tacker_client.do_request(
            path, "POST", expected_status=[201], body=req_body)

        pkg_id = body['id']

        with open(zip_file_path, 'rb') as fp:
            path = f"/vnfpkgm/v1/vnf_packages/{pkg_id}/package_content"
            resp, body = cls.tacker_client.do_request(
                path, "PUT", body=fp, content_type='application/zip',
                expected_status=[202])

        # wait for onboard
        timeout = VNF_PACKAGE_UPLOAD_TIMEOUT
        start_time = int(time.time())
        path = f"/vnfpkgm/v1/vnf_packages/{pkg_id}"
        while True:
            resp, body = cls.tacker_client.do_request(
                path, "GET", expected_status=[200])
            if body['onboardingState'] == "ONBOARDED":
                break

            if int(time.time()) - start_time > timeout:
                raise Exception("Failed to onboard vnf package")

            time.sleep(RETRY_WAIT_TIME)

        shutil.rmtree(tmp_dir)

        return pkg_id, vnfd_id

    def get_vnf_package(self, pkg_id):
        path = f"/vnfpkgm/v1/vnf_packages/{pkg_id}"
        resp, body = self.tacker_client.do_request(path, "GET")
        return body

    @classmethod
    def delete_vnf_package(cls, pkg_id):
        path = f"/vnfpkgm/v1/vnf_packages/{pkg_id}"
        req_body = {"operationalState": "DISABLED"}
        resp, _ = cls.tacker_client.do_request(
            path, "PATCH", body=req_body)
        if resp.status_code != 200:
            LOG.error("failed to set operationalState to DISABLED")
            return

        cls.tacker_client.do_request(path, "DELETE")

    def create_vnf_instance(self, req_body):
        path = "/vnflcm/v2/vnf_instances"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version=VNFLCM_V2_VERSION)

    def instantiate_vnf_instance(self, inst_id, req_body):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}/instantiate"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version=VNFLCM_V2_VERSION)

    def terminate_vnf_instance(self, inst_id, req_body):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}/terminate"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version=VNFLCM_V2_VERSION)

    def heal_vnf_instance(self, inst_id, req_body):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}/heal"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version=VNFLCM_V2_VERSION)

    def delete_vnf_instance(self, inst_id):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}"
        return self.tacker_client.do_request(
            path, "DELETE", version=VNFLCM_V2_VERSION)

    def show_vnf_instance(self, inst_id):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}"
        return self.tacker_client.do_request(
            path, "GET", version=VNFLCM_V2_VERSION)

    def list_vnf_instance(self, filter_expr=None):
        path = "/vnflcm/v2/vnf_instances"
        if filter_expr:
            path = "{}?{}".format(path, urllib.parse.urlencode(filter_expr))
        return self.tacker_client.do_request(
            path, "GET", version=VNFLCM_V2_VERSION)

    def scale_vnf_instance(self, inst_id, req_body):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}/scale"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version=VNFLCM_V2_VERSION)

    def update_vnf_instance(self, inst_id, req_body):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}"
        return self.tacker_client.do_request(
            path, "PATCH", body=req_body, version=VNFLCM_V2_VERSION)

    def change_vnfpkg(self, inst_id, req_body):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}/change_vnfpkg"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version=VNFLCM_V2_VERSION)

    def show_lcmocc(self, lcmocc_id):
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}"
        return self.tacker_client.do_request(
            path, "GET", version=VNFLCM_V2_VERSION)

    def list_lcmocc(self, filter_expr=None):
        path = "/vnflcm/v2/vnf_lcm_op_occs"
        if filter_expr:
            path = "{}?{}".format(path, urllib.parse.urlencode(filter_expr))
        return self.tacker_client.do_request(
            path, "GET", version=VNFLCM_V2_VERSION)

    def retry_lcmocc(self, lcmocc_id):
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}/retry"
        return self.tacker_client.do_request(
            path, "POST", version=VNFLCM_V2_VERSION)

    def fail_lcmocc(self, lcmocc_id):
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}/fail"
        return self.tacker_client.do_request(
            path, "POST", version=VNFLCM_V2_VERSION)

    def rollback_lcmocc(self, lcmocc_id):
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}/rollback"
        return self.tacker_client.do_request(
            path, "POST", version=VNFLCM_V2_VERSION)

    def create_subscription(self, req_body):
        path = "/vnflcm/v2/subscriptions"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version=VNFLCM_V2_VERSION)

    def delete_subscription(self, sub_id):
        path = f"/vnflcm/v2/subscriptions/{sub_id}"
        return self.tacker_client.do_request(
            path, "DELETE", version=VNFLCM_V2_VERSION)

    def show_subscription(self, sub_id):
        path = f"/vnflcm/v2/subscriptions/{sub_id}"
        return self.tacker_client.do_request(
            path, "GET", version=VNFLCM_V2_VERSION)

    def list_subscriptions(self, filter_expr=None):
        path = "/vnflcm/v2/subscriptions"
        if filter_expr:
            path = "{}?{}".format(path, urllib.parse.urlencode(filter_expr))
        return self.tacker_client.do_request(
            path, "GET", version=VNFLCM_V2_VERSION)

    def create_fm_subscription(self, req_body):
        path = "/vnffm/v1/subscriptions"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version=VNFFM_V1_VERSION)

    def show_fm_subscription(self, subscription_id):
        path = f"/vnffm/v1/subscriptions/{subscription_id}"
        return self.tacker_client.do_request(
            path, "GET", version=VNFFM_V1_VERSION)

    def delete_fm_subscription(self, subscription_id):
        path = f"/vnffm/v1/subscriptions/{subscription_id}"
        return self.tacker_client.do_request(
            path, "DELETE", version=VNFFM_V1_VERSION)

    def create_pm_job(self, req_body):
        path = "/vnfpm/v2/pm_jobs"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version=VNFPM_V2_VERSION)

    def show_pm_job(self, pm_job_id):
        path = f"/vnfpm/v2/pm_jobs/{pm_job_id}"
        return self.tacker_client.do_request(
            path, "GET", version=VNFPM_V2_VERSION)

    def delete_pm_job(self, pm_job_id):
        path = f"/vnfpm/v2/pm_jobs/{pm_job_id}"
        return self.tacker_client.do_request(
            path, "DELETE", version=VNFPM_V2_VERSION)

    def create_pm_threshold(self, req_body):
        path = "/vnfpm/v2/thresholds"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version=VNFPM_V2_VERSION)

    def show_pm_threshold(self, pm_threshold_id):
        path = f"/vnfpm/v2/thresholds/{pm_threshold_id}"
        return self.tacker_client.do_request(
            path, "GET", version=VNFPM_V2_VERSION)

    def delete_pm_threshold(self, pm_threshold_id):
        path = f"/vnfpm/v2/thresholds/{pm_threshold_id}"
        return self.tacker_client.do_request(
            path, "DELETE", version=VNFPM_V2_VERSION)

    def exec_lcm_operation(self, func, *args):
        for _ in range(3):
            resp, body = func(*args)
            if resp.status_code == 409:
                # may happen. there is a bit time between lcmocc become
                # COMPLETED and lock of terminate is freed.
                time.sleep(RETRY_WAIT_TIME)
            else:
                return resp, body
        self.fail()

    def wait_lcmocc_complete(self, lcmocc_id):
        # NOTE: It is not necessary to set timeout because the operation
        # itself set timeout and the state will become 'FAILED_TEMP'.
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}"
        while True:
            time.sleep(RETRY_WAIT_TIME)
            _, body = self.tacker_client.do_request(
                path, "GET", expected_status=[200], version=VNFLCM_V2_VERSION)
            state = body['operationState']
            if state == 'COMPLETED':
                return
            elif state in ['STARTING', 'PROCESSING']:
                continue
            else:  # FAILED_TEMP or ROLLED_BACK
                raise Exception(f"Operation failed. state: {state}")

    def wait_lcmocc_failed_temp(self, lcmocc_id):
        # NOTE: It is not necessary to set timeout because the operation
        # itself set timeout and the state will become 'FAILED_TEMP'.
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}"
        while True:
            time.sleep(RETRY_WAIT_TIME)
            _, body = self.tacker_client.do_request(
                path, "GET", expected_status=[200], version=VNFLCM_V2_VERSION)
            state = body['operationState']
            if state == 'FAILED_TEMP':
                return
            elif state in ['STARTING', 'PROCESSING']:
                continue
            elif state == 'COMPLETED':
                raise Exception("Operation unexpected COMPLETED.")
            else:  # ROLLED_BACK
                raise Exception(f"Operation failed. state: {state}")

    def wait_lcmocc_rolled_back(self, lcmocc_id):
        # NOTE: It is not necessary to set timeout because the operation
        # itself set timeout and the state will become 'FAILED_TEMP'.
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}"
        while True:
            time.sleep(RETRY_WAIT_TIME)
            _, body = self.tacker_client.do_request(
                path, "GET", expected_status=[200], version=VNFLCM_V2_VERSION)
            state = body['operationState']
            if state == 'ROLLED_BACK':
                return
            if state == 'ROLLING_BACK':
                continue

            raise Exception(f"Operation failed. state: {state}")

    def put_fail_file(self, operation):
        with open(f'/tmp/{operation}', 'w'):
            pass

    def rm_fail_file(self, operation):
        os.remove(f'/tmp/{operation}')

    def assert_notification_get(self, callback_url):
        notify_mock_responses = FAKE_SERVER_MANAGER.get_history(
            callback_url)
        FAKE_SERVER_MANAGER.clear_history(
            callback_url)
        self.assertEqual(1, len(notify_mock_responses))
        self.assertEqual(204, notify_mock_responses[0].status_code)

    def _check_notification(self, callback_url, notify_type):
        notify_mock_responses = FAKE_SERVER_MANAGER.get_history(
            callback_url)
        FAKE_SERVER_MANAGER.clear_history(
            callback_url)
        self.assertEqual(1, len(notify_mock_responses))
        self.assertEqual(204, notify_mock_responses[0].status_code)
        self.assertEqual(notify_type, notify_mock_responses[0].request_body[
            'notificationType'])

    def _check_no_notification(self, callback_url):
        notify_mock_responses = FAKE_SERVER_MANAGER.get_history(
            callback_url)
        self.assertEqual(0, len(notify_mock_responses))

    def _get_crossing_direction(self, callback_url):
        notify_mock_responses = FAKE_SERVER_MANAGER.get_history(
            callback_url)
        return notify_mock_responses[0].request_body['crossingDirection']

    def prometheus_auto_scaling_alert(self, req_body):
        path = "/alert/auto_scaling"
        return self.tacker_client.do_request(
            path, "POST", body=req_body)

    def prometheus_auto_healing_alert(self, req_body):
        path = "/alert/auto_healing"
        return self.tacker_client.do_request(
            path, "POST", body=req_body)

    def check_resp_headers_in_create(self, resp):
        # includes location header and response body
        supported_headers = ['Version', 'Location', 'Content-Type',
                             'Accept-Ranges']
        self._check_resp_headers(resp, supported_headers)

    def check_resp_headers_in_operation_task(self, resp):
        # includes location header and no response body
        supported_headers = ['Version', 'Location']
        self._check_resp_headers(resp, supported_headers)

    def check_resp_headers_in_get(self, resp):
        # includes a single data in response body and no location header
        supported_headers = ['Version', 'Content-Type',
                             'Accept-Ranges']
        self._check_resp_headers(resp, supported_headers)

    def check_resp_headers_in_index(self, resp):
        # includes some data in response body and no location header
        supported_headers = ['Version', 'Content-Type',
                             'Accept-Ranges', 'Link']
        self._check_resp_headers(resp, supported_headers)

    def check_resp_headers_in_delete(self, resp):
        # no location header and response body
        supported_headers = ['Version']
        self._check_resp_headers(resp, supported_headers)

    def check_resp_body(self, body, expected_attrs):
        for attr in expected_attrs:
            if attr not in body:
                raise Exception(f"Expected attribute doesn't exist: {attr}")

    def _check_resp_headers(self, resp, supported_headers):
        unsupported_headers = ['Retry-After',
                               'Content-Range', 'WWW-Authenticate']
        for s in supported_headers:
            if s not in resp.headers:
                raise Exception(f"Supported header doesn't exist: {s}")
        for u in unsupported_headers:
            if u in resp.headers:
                raise Exception(f"Unsupported header exist: {u}")

    def check_package_usage(self, package_id, state='NOT_IN_USE',
                            is_nfvo=False):
        if not is_nfvo:
            usage_state = self.get_vnf_package(package_id)['usageState']
            self.assertEqual(state, usage_state)
