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

import ddt
import os
import tempfile
import time
import zipfile

from oslo_serialization import jsonutils

import tacker.conf
from tacker.tests.functional import base


CONF = tacker.conf.CONF


@ddt.ddt
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

    def _disable_operational_state(self, package_uuid):
        update_req_body = jsonutils.dumps({
            "operationalState": "DISABLED"})

        resp, resp_body = self.http_client.do_request(
            '{base_path}/{id}'.format(id=package_uuid,
                                      base_path=self.base_url),
            "PATCH", content_type='application/json', body=update_req_body)
        self.assertEqual(200, resp.status_code)

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

    def test_upload_from_file_update_show_and_delete(self):
        """This method tests multiple operations on vnf package.

        - upload package from file
        - update the package state to DISABLED.
        - show the package
        - delete the package
        """
        user_data = jsonutils.dumps(
            {"userDefinedData": {"key1": "val1", "key2": "val2",
                                 "key3": "val3"}})
        vnf_package = self._create_vnf_package(user_data)

        file_path = self._get_csar_file_path("sample_vnf_package_csar.zip")
        upload_url = "{base_path}/{id}/package_content".format(
            base_path=self.base_url, id=vnf_package['id'])
        with open(file_path, 'rb') as file_object:
            resp, resp_body = self.http_client.do_request(upload_url,
                "PUT", body=file_object, content_type='application/zip')

        self.assertEqual(202, resp.status_code)
        self._wait_for_onboard(vnf_package['id'])

        update_req_body = jsonutils.dumps(
            {"operationalState": "DISABLED",
             "userDefinedData": {"key1": "changed_val1",
                                 "key2": "val2", "new_key": "new_val"}})

        operational_state = "DISABLED"
        user_defined_data = {"key1": "changed_val1", "new_key": "new_val"}
        expected_result = {"operationalState": operational_state,
                           "userDefinedData": user_defined_data}

        # Update vnf package which is onboarded
        resp, resp_body = self.http_client.do_request(
            '{base_path}/{id}'.format(id=vnf_package['id'],
                                      base_path=self.base_url),
            "PATCH", content_type='application/json', body=update_req_body)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected_result, resp_body)

        # Show vnf package and verify whether the userDefinedData
        # and operationalState parameters are updated correctly.
        show_url = self.base_url + "/" + vnf_package['id']
        resp, body = self.http_client.do_request(show_url, "GET")
        self.assertEqual(200, resp.status_code)
        self.assertEqual(operational_state, body['operationalState'])
        expected_user_defined_data = {'key1': 'changed_val1', 'key2': 'val2',
                                      'key3': 'val3', 'new_key': 'new_val'}
        self.assertEqual(expected_user_defined_data, body['userDefinedData'])

        self._delete_vnf_package(vnf_package['id'])
        self._wait_for_delete(vnf_package['id'])

    def _create_and_onboard_vnf_package(self, file_name=None):
        body = jsonutils.dumps({"userDefinedData": {"foo": "bar"}})
        vnf_package = self._create_vnf_package(body)
        if file_name is None:
            file_name = "sample_vnf_package_csar.zip"
        file_path = self._get_csar_file_path(file_name)
        with open(file_path, 'rb') as file_object:
            resp, resp_body = self.http_client.do_request(
                '{base_path}/{id}/package_content'.format(
                    id=vnf_package['id'],
                    base_path=self.base_url),
                "PUT", body=file_object, content_type='application/zip')
        self.assertEqual(202, resp.status_code)
        self._wait_for_onboard(vnf_package['id'])

        return vnf_package['id']

    def test_get_vnfd_from_onboarded_vnf_package_for_content_type_zip(self):
        vnf_package_id = self._create_and_onboard_vnf_package()
        self.addCleanup(self._delete_vnf_package, vnf_package_id)
        self.addCleanup(self._disable_operational_state, vnf_package_id)
        resp, resp_body = self.http_client.do_request(
            '{base_path}/{id}/vnfd'.format(id=vnf_package_id,
                                           base_path=self.base_url),
            "GET", content_type='application/zip')
        self.assertEqual(200, resp.status_code)
        self.assertEqual('application/zip', resp.headers['Content-Type'])
        self.assert_resp_contents(resp)

    def assert_resp_contents(self, resp):
        expected_file_list = ['Definitions/helloworld3_top.vnfd.yaml',
                              'Definitions/helloworld3_df_simple.yaml',
                              'Definitions/etsi_nfv_sol001_vnfd_types.yaml',
                              'Definitions/etsi_nfv_sol001_common_types.yaml',
                              'Definitions/helloworld3_types.yaml',
                              'TOSCA-Metadata/TOSCA.meta']

        tmp = tempfile.NamedTemporaryFile(delete=False)
        try:
            tmp.write(resp.content)
        finally:
            # checking response.content is valid zip file
            self.assertTrue(zipfile.is_zipfile(tmp))
            with zipfile.ZipFile(tmp, 'r') as zipObj:
                # Get list of files names in zip
                actual_file_list = zipObj.namelist()
            self.assertCountEqual(expected_file_list, actual_file_list)

            tmp.close()

    @ddt.data('text/plain', 'application/zip,text/plain')
    def test_get_vnfd_from_onboarded_vnf_package_for_content_type_text(
            self, accept_header):
        # Uploading vnf package with single yaml file csar.
        single_yaml_csar = "sample_vnfpkg_no_meta_single_vnfd.zip"
        vnf_package_id = self._create_and_onboard_vnf_package(
            single_yaml_csar)
        self.addCleanup(self._delete_vnf_package, vnf_package_id)
        self.addCleanup(self._disable_operational_state, vnf_package_id)
        resp, resp_body = self.http_client.do_request(
            '{base_path}/{id}/vnfd'.format(id=vnf_package_id,
                                           base_path=self.base_url),
            "GET", content_type=accept_header)
        self.assertEqual(200, resp.status_code)
        self.assertEqual('text/plain', resp.headers['Content-Type'])
        self.assertIsNotNone(resp.text)
