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
import os
import shutil
import tempfile
import time
import urllib

from oslo_config import cfg
from oslo_utils import uuidutils
from tempest.lib import base
import yaml

from tacker.sol_refactored.common import http_client
from tacker.sol_refactored import objects
from tacker.tests.functional.common.fake_server import FakeServerManager
from tacker.tests.functional.sol_v2_common import utils
from tacker.tests import utils as base_utils
from tacker import version

FAKE_SERVER_MANAGER = FakeServerManager()
MOCK_NOTIFY_CALLBACK_URL = '/notification/callback'

VNF_PACKAGE_UPLOAD_TIMEOUT = 300
VNF_INSTANTIATE_TIMEOUT = 600
VNF_TERMINATE_TIMEOUT = 600
RETRY_WAIT_TIME = 5


class BaseVnfLcmKubernetesV2Test(base.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseVnfLcmKubernetesV2Test, cls).setUpClass()
        """Base test case class for SOL v2 kubernetes functional tests."""

        FAKE_SERVER_MANAGER.prepare_http_server()
        FAKE_SERVER_MANAGER.start_server()

        cfg.CONF(args=['--config-file', '/etc/tacker/tacker.conf'],
                 project='tacker',
                 version='%%prog %s' % version.version_info.release_string())
        objects.register_all()

        k8s_vim_info = cls.get_k8s_vim_info()
        cls.auth_url = k8s_vim_info.interfaceInfo['endpoint']
        cls.bearer_token = k8s_vim_info.accessInfo['bearer_token']
        cls.ssl_ca_cert = k8s_vim_info.interfaceInfo['ssl_ca_cert']

        vim_info = cls.get_vim_info()
        auth = http_client.KeystonePasswordAuthHandle(
            auth_url=vim_info.interfaceInfo['endpoint'],
            username=vim_info.accessInfo['username'],
            password=vim_info.accessInfo['password'],
            project_name=vim_info.accessInfo['project'],
            user_domain_name=vim_info.accessInfo['userDomain'],
            project_domain_name=vim_info.accessInfo['projectDomain']
        )
        cls.tacker_client = http_client.HttpClient(auth)
        cls.fake_prometheus_ip = cls.get_controller_tacker_ip()

    @classmethod
    def tearDownClass(cls):
        super(BaseVnfLcmKubernetesV2Test, cls).tearDownClass()
        FAKE_SERVER_MANAGER.stop_server()

    def setUp(self):
        super().setUp()

        callback_url = os.path.join(
            MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        FAKE_SERVER_MANAGER.clear_history(callback_url)
        FAKE_SERVER_MANAGER.set_callback('POST', callback_url, status_code=204)
        FAKE_SERVER_MANAGER.set_callback('GET', callback_url, status_code=204)

    @classmethod
    def get_vim_info(cls):
        vim_params = yaml.safe_load(base_utils.read_file('local-vim.yaml'))
        vim_params['auth_url'] += '/v3'

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

    @classmethod
    def get_k8s_vim_info(cls):
        vim_params = yaml.safe_load(base_utils.read_file('local-k8s-vim.yaml'))

        vim_info = objects.VimConnectionInfo(
            interfaceInfo={
                'endpoint': vim_params['auth_url'],
                'ssl_ca_cert': vim_params.get('ssl_ca_cert')
            },
            accessInfo={
                'region': 'RegionOne',
                'bearer_token': vim_params['bearer_token']
            }
        )
        return vim_info

    @classmethod
    def get_k8s_vim_id(cls, use_helm=False):
        vim_list = cls.list_vims(cls)
        if len(vim_list.values()) == 0:
            assert False, "vim_list is Empty: Default VIM is missing"

        for vim_list in vim_list.values():
            for vim in vim_list:
                if vim['name'] == 'vim-kubernetes' and not use_helm:
                    return vim['id']
                if vim['name'] == 'vim-kubernetes-helm' and use_helm:
                    return vim['id']
        return None

    @classmethod
    def create_vnf_package(cls, sample_path, user_data={}, image_path=None,
                           provider=None, namespace=None):
        vnfd_id = uuidutils.generate_uuid()
        tmp_dir = tempfile.mkdtemp()

        utils.make_zip(sample_path, tmp_dir, vnfd_id, image_path,
                       provider=provider, namespace=namespace)

        zip_file_name = os.path.basename(os.path.abspath(sample_path)) + ".zip"
        zip_file_path = os.path.join(tmp_dir, zip_file_name)

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

            if ((int(time.time()) - start_time) > timeout):
                raise Exception("Failed to onboard vnf package")

            time.sleep(5)

        shutil.rmtree(tmp_dir)

        return pkg_id, vnfd_id

    @classmethod
    def get_controller_tacker_ip(cls):
        cur_dir = os.path.dirname(__file__)
        script_path = os.path.join(
            cur_dir, "../../../../tools/test-setup-fake-prometheus-server.sh")
        with open(script_path, 'r') as f_obj:
            content = f_obj.read()
        ip = content.split('TEST_REMOTE_URI')[1].split(
            'http://')[1].split('"')[0]
        return ip

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

    @classmethod
    def delete_vnf_package(cls, pkg_id):
        path = f"/vnfpkgm/v1/vnf_packages/{pkg_id}"
        req_body = {"operationalState": "DISABLED"}
        resp, _ = cls.tacker_client.do_request(
            path, "PATCH", body=req_body)
        if resp.status_code != 200:
            print("failed to set operationalState to DISABLED")
            return

        cls.tacker_client.do_request(path, "DELETE")

    def list_vims(self):
        path = "/v1.0/vims.json"
        resp, body = self.tacker_client.do_request(path, "GET")
        return body

    def get_vnf_package(self, pkg_id):
        path = f"/vnfpkgm/v1/vnf_packages/{pkg_id}"
        resp, body = self.tacker_client.do_request(path, "GET")
        return body

    def create_vnf_instance(self, req_body):
        path = "/vnflcm/v2/vnf_instances"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def delete_vnf_instance(self, inst_id):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}"
        return self.tacker_client.do_request(
            path, "DELETE", version="2.0.0")

    def show_vnf_instance(self, inst_id):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}"
        return self.tacker_client.do_request(
            path, "GET", version="2.0.0")

    def instantiate_vnf_instance(self, inst_id, req_body):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}/instantiate"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def scale_vnf_instance(self, inst_id, req_body):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}/scale"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def heal_vnf_instance(self, inst_id, req_body):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}/heal"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def change_vnfpkg(self, inst_id, req_body):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}/change_vnfpkg"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def terminate_vnf_instance(self, inst_id, req_body):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}/terminate"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def rollback_lcmocc(self, lcmocc_id):
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}/rollback"
        return self.tacker_client.do_request(
            path, "POST", version="2.0.0")

    def retry_lcmocc(self, lcmocc_id):
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}/retry"
        return self.tacker_client.do_request(
            path, "POST", version="2.0.0")

    def fail_lcmocc(self, lcmocc_id):
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}/fail"
        return self.tacker_client.do_request(
            path, "POST", version="2.0.0")

    def show_lcmocc(self, lcmocc_id):
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}"
        return self.tacker_client.do_request(
            path, "GET", version="2.0.0")

    def list_lcmocc(self, filter_expr=None):
        path = "/vnflcm/v2/vnf_lcm_op_occs"
        if filter_expr:
            path = "{}?{}".format(path, urllib.parse.urlencode(filter_expr))
        return self.tacker_client.do_request(
            path, "GET", version="2.0.0")

    def create_subscription(self, req_body):
        path = "/vnffm/v1/subscriptions"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="1.3.0")

    def list_subscriptions(self, filter_expr=None):
        path = "/vnffm/v1/subscriptions"
        if filter_expr:
            path = "{}?{}".format(path, urllib.parse.urlencode(filter_expr))
        return self.tacker_client.do_request(
            path, "GET", version="1.3.0")

    def show_subscription(self, subscription_id):
        path = f"/vnffm/v1/subscriptions/{subscription_id}"
        return self.tacker_client.do_request(
            path, "GET", version="1.3.0")

    def delete_subscription(self, subscription_id):
        path = f"/vnffm/v1/subscriptions/{subscription_id}"
        return self.tacker_client.do_request(
            path, "DELETE", version="1.3.0")

    def create_fm_alarm(self, req_body):
        path = "/alert"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="1.3.0")

    def list_fm_alarm(self, filter_expr=None):
        path = "/vnffm/v1/alarms"
        if filter_expr:
            path = "{}?{}".format(path, urllib.parse.urlencode(filter_expr))
        return self.tacker_client.do_request(
            path, "GET", version="1.3.0")

    def show_fm_alarm(self, alarm_id):
        path = f"/vnffm/v1/alarms/{alarm_id}"
        return self.tacker_client.do_request(
            path, "GET", version="1.3.0")

    def update_fm_alarm(self, alarm_id, req_body):
        path = f"/vnffm/v1/alarms/{alarm_id}"
        return self.tacker_client.do_request(
            path, "PATCH", body=req_body, version="1.3.0")

    def create_pm_job(self, req_body):
        path = "/vnfpm/v2/pm_jobs"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.1.0")

    def update_pm_job(self, pm_job_id, req_body):
        path = f"/vnfpm/v2/pm_jobs/{pm_job_id}"
        return self.tacker_client.do_request(
            path, "PATCH", body=req_body, version="2.1.0")

    def create_pm_event(self, req_body):
        path = "/pm_event"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.1.0")

    def list_pm_job(self, filter_expr=None):
        path = "/vnfpm/v2/pm_jobs"
        if filter_expr:
            path = "{}?{}".format(path, urllib.parse.urlencode(filter_expr))
        return self.tacker_client.do_request(
            path, "GET", version="2.1.0")

    def show_pm_job(self, pm_job_id):
        path = f"/vnfpm/v2/pm_jobs/{pm_job_id}"
        return self.tacker_client.do_request(
            path, "GET", version="2.1.0")

    def show_pm_job_report(self, pm_job_id, report_id):
        path = f"/vnfpm/v2/pm_jobs/{pm_job_id}/reports/{report_id}"
        return self.tacker_client.do_request(
            path, "GET", version="2.1.0")

    def delete_pm_job(self, pm_job_id):
        path = f"/vnfpm/v2/pm_jobs/{pm_job_id}"
        return self.tacker_client.do_request(
            path, "DELETE", version="2.1.0")

    def create_pm_threshold(self, req_body):
        path = "/vnfpm/v2/thresholds"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.1.0")

    def update_pm_threshold(self, pm_threshold_id, req_body):
        path = f"/vnfpm/v2/thresholds/{pm_threshold_id}"
        return self.tacker_client.do_request(
            path, "PATCH", body=req_body, version="2.1.0",
            content_type="application/mergepatch+json")

    def pm_threshold(self, req_body):
        path = "/pm_threshold"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.1.0")

    def list_pm_threshold(self, filter_expr=None):
        path = "/vnfpm/v2/thresholds"
        if filter_expr:
            path = "{}?{}".format(path, urllib.parse.urlencode(filter_expr))
        return self.tacker_client.do_request(
            path, "GET", version="2.1.0")

    def show_pm_threshold(self, pm_threshold_id):
        path = f"/vnfpm/v2/thresholds/{pm_threshold_id}"
        return self.tacker_client.do_request(
            path, "GET", version="2.1.0")

    def delete_pm_threshold(self, pm_threshold_id):
        path = f"/vnfpm/v2/thresholds/{pm_threshold_id}"
        return self.tacker_client.do_request(
            path, "DELETE", version="2.1.0")

    def prometheus_auto_scaling_alert(self, req_body):
        path = "/alert/auto_scaling"
        return self.tacker_client.do_request(
            path, "POST", body=req_body)

    def prometheus_auto_healing_alert(self, req_body):
        path = "/alert/auto_healing"
        return self.tacker_client.do_request(
            path, "POST", body=req_body)

    def _check_resp_headers(self, resp, supported_headers):
        unsupported_headers = ['Link', 'Retry-After',
                               'Content-Range', 'WWW-Authenticate']
        for s in supported_headers:
            if s not in resp.headers:
                raise Exception("Supported header doesn't exist: %s" % s)
        for u in unsupported_headers:
            if u in resp.headers:
                raise Exception("Unsupported header exist: %s" % u)

    def check_resp_headers_in_create(self, resp):
        # includes location header and response body
        supported_headers = ['Version', 'Location', 'Content-Type',
                             'Accept-Ranges']
        self._check_resp_headers(resp, supported_headers)

    def check_resp_body(self, body, expected_attrs):
        for attr in expected_attrs:
            if attr not in body:
                raise Exception("Expected attribute doesn't exist: %s" % attr)

    def check_resp_headers_in_operation_task(self, resp):
        # includes location header and no response body
        supported_headers = ['Version', 'Location']
        self._check_resp_headers(resp, supported_headers)

    def check_resp_headers_in_get(self, resp):
        # includes response body and no location header
        supported_headers = ['Version', 'Content-Type',
                             'Accept-Ranges']
        self._check_resp_headers(resp, supported_headers)

    def check_resp_headers_in_delete(self, resp):
        # no location header and response body
        supported_headers = ['Version']
        self._check_resp_headers(resp, supported_headers)

    def wait_lcmocc_complete(self, lcmocc_id):
        # NOTE: It is not necessary to set timeout because the operation
        # itself set timeout and the state will become 'FAILED_TEMP'.
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}"
        while True:
            time.sleep(5)
            _, body = self.tacker_client.do_request(
                path, "GET", expected_status=[200], version="2.0.0")
            state = body['operationState']
            if state == 'COMPLETED':
                return
            elif state in ['STARTING', 'PROCESSING']:
                continue
            else:  # FAILED_TEMP or ROLLED_BACK
                raise Exception("Operation failed. state: %s" % state)

    def wait_lcmocc_failed_temp(self, lcmocc_id):
        # NOTE: It is not necessary to set timeout because the operation
        # itself set timeout and the state will become 'FAILED_TEMP'.
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}"
        while True:
            time.sleep(5)
            _, body = self.tacker_client.do_request(
                path, "GET", expected_status=[200], version="2.0.0")
            state = body['operationState']
            if state == 'FAILED_TEMP':
                return
            elif state in ['STARTING', 'PROCESSING']:
                continue
            elif state == 'COMPLETED':
                raise Exception("Operation unexpected COMPLETED.")
            else:  # ROLLED_BACK
                raise Exception("Operation failed. state: %s" % state)

    def wait_lcmocc_rolled_back(self, lcmocc_id):
        # NOTE: It is not necessary to set timeout because the operation
        # itself set timeout and the state will become 'FAILED_TEMP'.
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}"
        while True:
            time.sleep(5)
            _, body = self.tacker_client.do_request(
                path, "GET", expected_status=[200], version="2.0.0")
            state = body['operationState']
            if state == 'ROLLED_BACK':
                return
            if state in ['ROLLING_BACK']:
                continue

            raise Exception(f"Operation failed. state: {state}")
