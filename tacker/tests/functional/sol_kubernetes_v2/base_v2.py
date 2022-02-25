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

from oslo_config import cfg
from oslo_utils import uuidutils
from tempest.lib import base
import yaml

from tacker.sol_refactored.common import http_client
from tacker.sol_refactored import objects
from tacker.tests.functional.sol_v2 import utils
from tacker.tests import utils as base_utils
from tacker import version

VNF_PACKAGE_UPLOAD_TIMEOUT = 300
VNF_INSTANTIATE_TIMEOUT = 600
VNF_TERMINATE_TIMEOUT = 600
RETRY_WAIT_TIME = 5


class BaseVnfLcmKubernetesV2Test(base.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseVnfLcmKubernetesV2Test, cls).setUpClass()
        """Base test case class for SOL v2 kubernetes functional tests."""

        cfg.CONF(args=['--config-file', '/etc/tacker/tacker.conf'],
                 project='tacker',
                 version='%%prog %s' % version.version_info.release_string())
        objects.register_all()

        k8s_vim_info = cls.get_k8s_vim_info()
        cls.auth_url = k8s_vim_info.interfaceInfo['endpoint']
        cls.bearer_token = k8s_vim_info.accessInfo['bearer_token']

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
            interfaceInfo={'endpoint': vim_params['auth_url']},
            accessInfo={
                'region': 'RegionOne',
                'bearer_token': vim_params['bearer_token']
            }
        )
        return vim_info

    @classmethod
    def get_k8s_vim_id(cls):
        vim_list = cls.list_vims(cls)
        if len(vim_list.values()) == 0:
            assert False, "vim_list is Empty: Default VIM is missing"

        for vim_list in vim_list.values():
            for vim in vim_list:
                if vim['name'] == 'vim-kubernetes':
                    return vim['id']
        return None

    @classmethod
    def create_vnf_package(cls, sample_path, user_data={}, image_path=None):
        vnfd_id = uuidutils.generate_uuid()
        tmp_dir = tempfile.mkdtemp()

        utils.make_zip(sample_path, tmp_dir, vnfd_id, image_path)

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
