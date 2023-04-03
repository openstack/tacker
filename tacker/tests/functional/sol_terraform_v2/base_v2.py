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

from oslo_config import cfg
from oslo_utils import uuidutils

from tacker.sol_refactored.common import http_client
from tacker.sol_refactored import objects
from tacker.tests.functional import base_v2
from tacker.tests.functional.common.fake_server import FakeServerManager
from tacker.tests.functional.sol_v2_common import utils
from tacker import version

FAKE_SERVER_MANAGER = FakeServerManager()

VNF_PACKAGE_UPLOAD_TIMEOUT = 300


class BaseVnfLcmTerraformV2Test(base_v2.BaseTackerTestV2):

    @classmethod
    def setUpClass(cls):
        super(BaseVnfLcmTerraformV2Test, cls).setUpClass()
        """Base test case class for SOL v2 terraform functional tests."""

        cfg.CONF(args=['--config-file', '/etc/tacker/tacker.conf'],
                 project='tacker',
                 version='%%prog %s' % version.version_info.release_string())
        objects.register_all()

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

    @classmethod
    def create_vnf_package(cls, sample_path, user_data=None, image_path=None):
        vnfd_id = uuidutils.generate_uuid()
        tmp_dir = tempfile.mkdtemp()

        utils.make_zip(sample_path, tmp_dir, vnfd_id, image_path)

        zip_file_name = os.path.basename(os.path.abspath(sample_path)) + ".zip"
        zip_file_path = os.path.join(tmp_dir, zip_file_name)

        path = "/vnfpkgm/v1/vnf_packages"
        if user_data is not None:
            req_body = {'userDefinedData': user_data}
        else:
            req_body = {}
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

            if (int(time.time()) - start_time) > timeout:
                raise Exception("Failed to onboard vnf package")

            time.sleep(5)

        shutil.rmtree(tmp_dir)

        return pkg_id, vnfd_id
