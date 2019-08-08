# Copyright (C) 2019 NTT DATA
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
import time

from oslo_serialization import jsonutils

from tacker.tests.functional import base


class VnfPackageTest(base.BaseTackerTest):

    VNF_PACKAGE_DELETE_TIMEOUT = 120
    VNF_PACKAGE_UPLOAD_TIMEOUT = 300

    def setUp(self):
        super(VnfPackageTest, self).setUp()
        self.base_url = "/vnfpkgm/v1/vnf_packages"

    def _wait_for_delete(self, package_uuid):
        show_url = self.base_url + "/" + package_uuid
        timeout = self.VNF_PACKAGE_DELETE_TIMEOUT
        start_time = int(time.time())
        while True:
            resp, body = self.http_client.do_request(show_url, "GET")
            if (404 == resp.status_code):
                break
            if (int(time.time()) - start_time) > timeout:
                raise Exception("Failed to delete package")
            time.sleep(1)

    def _wait_for_onboard(self, package_uuid):
        show_url = self.base_url + "/" + package_uuid
        timeout = self.VNF_PACKAGE_UPLOAD_TIMEOUT
        start_time = int(time.time())
        while True:
            resp, body = self.http_client.do_request(show_url, "GET")
            if body['onboardingState'] == "ONBOARDED":
                break

            if ((int(time.time()) - start_time) > timeout):
                raise Exception("Failed to onboard vnf package")

            time.sleep(1)

    def _create_vnf_package(self, body):
        resp, response_body = self.http_client.do_request(self.base_url,
                                                   "POST", body=body)
        self.assertIsNotNone(response_body['id'])
        self.assertEqual(201, resp.status_code)
        return response_body

    def _delete_vnf_package(self, package_uuid):
        url = self.base_url + "/" + package_uuid
        resp, body = self.http_client.do_request(url, "DELETE")
        self.assertEqual(204, resp.status_code)

    def test_create_show_delete_vnf_package(self):
        """Creates and deletes a vnf package."""

        # Create vnf package
        body = jsonutils.dumps({"userDefinedData": {"foo": "bar"}})
        vnf_package = self._create_vnf_package(body)
        package_uuid = vnf_package['id']

        # show vnf package
        show_url = self.base_url + "/" + package_uuid
        resp, body = self.http_client.do_request(show_url, "GET")
        self.assertEqual(200, resp.status_code)

        # Delete vnf package
        self._delete_vnf_package(package_uuid)
        self._wait_for_delete(package_uuid)

        # show vnf package should fail as it's deleted
        resp, body = self.http_client.do_request(show_url, "GET")
        self.assertEqual(404, resp.status_code)

    def test_list(self):
        vnf_package_list = []
        body = jsonutils.dumps({"userDefinedData": {"foo": "bar"}})

        # create two vnf packages
        vnf_package = self._create_vnf_package(body)
        self.addCleanup(self._delete_vnf_package, vnf_package['id'])
        vnf_package_list.append(vnf_package['id'])

        vnf_package = self._create_vnf_package(body)
        vnf_package_list.append(vnf_package['id'])
        self.addCleanup(self._delete_vnf_package, vnf_package['id'])

        # list vnf package
        resp, body = self.http_client.do_request(self.base_url, "GET")
        self.assertEqual(200, resp.status_code)

        package_uuids = [obj['id'] for obj in body['vnf_packages']]
        self.assertIn(vnf_package_list[0], package_uuids)
        self.assertIn(vnf_package_list[1], package_uuids)

    def _get_csar_file_path(self, file_name):
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                    '../../etc/samples/' + file_name))
        return file_path

    def test_upload_from_file_and_delete(self):
        body = jsonutils.dumps({"userDefinedData": {"foo": "bar"}})
        vnf_package = self._create_vnf_package(body)
        file_path = self._get_csar_file_path("sample_vnf_package_csar.zip")
        with open(file_path, 'r') as file_object:
            resp, resp_body = self.http_client.do_request(
                '{base_path}/{id}/package_content'.format(
                    id=vnf_package['id'],
                    base_path=self.base_url),
                "PUT", body=file_object, content_type='application/zip')

        self.assertEqual(202, resp.status_code)

        self._wait_for_onboard(vnf_package['id'])

        self._delete_vnf_package(vnf_package['id'])
        self._wait_for_delete(vnf_package['id'])
