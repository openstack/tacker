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

from copy import deepcopy
import ddt
import os
from six.moves import urllib
import tempfile
import time
import zipfile

from oslo_serialization import jsonutils

import tacker.conf
from tacker.tests.functional import base
from tacker.tests import utils


CONF = tacker.conf.CONF


@ddt.ddt
class VnfPackageTest(base.BaseTackerTest):

    VNF_PACKAGE_DELETE_TIMEOUT = 120
    VNF_PACKAGE_UPLOAD_TIMEOUT = 300

    def setUp(self):
        super(VnfPackageTest, self).setUp()
        self.base_url = "/vnfpkgm/v1/vnf_packages"
        # Here we create and upload vnf package. Also get 'show' api response
        # as reference data for attribute filter tests
        self.package_id1 = self._create_and_upload_vnf("vnfpkgm1")
        show_url = self.base_url + "/" + self.package_id1
        resp, self.package1 = self.http_client.do_request(show_url, "GET")
        self.assertEqual(200, resp.status_code)

        self.package_id2 = self._create_and_upload_vnf("vnfpkgm2")
        show_url = self.base_url + "/" + self.package_id2
        resp, self.package2 = self.http_client.do_request(show_url, "GET")
        self.assertEqual(200, resp.status_code)

        self.package_id3 = self._create_and_upload_vnf("vnfpkgm3")
        show_url = self.base_url + "/" + self.package_id3
        resp, self.package3 = self.http_client.do_request(show_url, "GET")
        self.assertEqual(200, resp.status_code)

    def tearDown(self):
        for package_id in [self.package_id1, self.package_id2,
                           self.package_id3]:
            self._disable_operational_state(package_id)
            self._delete_vnf_package(package_id)
            self._wait_for_delete(package_id)

        super(VnfPackageTest, self).tearDown()

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
        vnf_package_id = self._create_and_upload_vnf('vnfpkgm1')

        # show vnf package
        show_url = self.base_url + "/" + vnf_package_id
        resp, body = self.http_client.do_request(show_url, "GET")
        self.assertEqual(200, resp.status_code)

        # update vnf package
        self._disable_operational_state(vnf_package_id)

        # Delete vnf package
        self._delete_vnf_package(vnf_package_id)
        self._wait_for_delete(vnf_package_id)

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

        package_uuids = [obj['id'] for obj in body]
        self.assertIn(vnf_package_list[0], package_uuids)
        self.assertIn(vnf_package_list[1], package_uuids)

    def _get_csar_dir_path(self, csar_name):
        csar_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   "../../etc/samples/etsi/nfv", csar_name))
        return csar_dir

    def _create_and_upload_vnf(self, sample_name):
        body = jsonutils.dumps({"userDefinedData": {"foo": "bar"}})
        vnf_package = self._create_vnf_package(body)
        csar_dir = self._get_csar_dir_path(sample_name)
        if os.path.exists(os.path.join(csar_dir, 'TOSCA-Metadata')) and \
                sample_name != 'vnfpkgm2':
            file_path = utils.create_csar_with_unique_artifact(
                csar_dir)
        else:
            file_path, vnfd_id = utils.create_csar_with_unique_vnfd_id(
                csar_dir)
        self.addCleanup(os.remove, file_path)

        with open(file_path, 'rb') as file_object:
            resp, resp_body = self.http_client.do_request(
                '{base_path}/{id}/package_content'.format(
                    id=vnf_package['id'],
                    base_path=self.base_url),
                "PUT", body=file_object, content_type='application/zip')

        self.assertEqual(202, resp.status_code)

        self._wait_for_onboard(vnf_package['id'])

        return vnf_package['id']

    def test_upload_from_uri_without_auth_and_delete(self):
        csar_dir = self._get_csar_dir_path("sample_vnfpkg_no_meta_single_vnfd")
        file_path, vnfd_id = utils.create_csar_with_unique_vnfd_id(csar_dir)
        self.addCleanup(os.remove, file_path)

        cls_obj = utils.StaticHttpFileHandler(os.path.dirname(file_path))
        self.addCleanup(cls_obj.stop)

        body = jsonutils.dumps({"userDefinedData": {"foo": "bar"}})
        vnf_package = self._create_vnf_package(body)
        csar_file_uri = 'http://localhost:{port}/{filename}'.format(
            port=cls_obj.port, filename=os.path.basename(file_path))

        body = jsonutils.dumps({"addressInformation": csar_file_uri})
        resp, resp_body = self.http_client.do_request(
            '{base_path}/{id}/package_content/upload_from_uri'.format(
                id=vnf_package['id'],
                base_path=self.base_url),
            "POST", body=body)
        self.assertEqual(202, resp.status_code)

        self._wait_for_onboard(vnf_package['id'])

        self._disable_operational_state(vnf_package['id'])
        self._delete_vnf_package(vnf_package['id'])
        self._wait_for_delete(vnf_package['id'])

    def test_upload_from_uri_with_auth_and_delete(self):
        csar_dir = self._get_csar_dir_path("sample_vnfpkg_no_meta_single_vnfd")
        file_path, vnfd_id = utils.create_csar_with_unique_vnfd_id(csar_dir)
        self.addCleanup(os.remove, file_path)

        cls_obj = utils.StaticHttpFileHandler(os.path.dirname(file_path))
        self.addCleanup(cls_obj.stop)

        body = jsonutils.dumps({"userDefinedData": {"foo": "bar"}})
        vnf_package = self._create_vnf_package(body)
        csar_file_uri = 'http://localhost:{port}/{filename}'.format(
            port=cls_obj.port, filename=os.path.basename(file_path))
        body = jsonutils.dumps({"addressInformation": csar_file_uri,
                                "userName": "username",
                                "password": "password"})
        resp, resp_body = self.http_client.do_request(
            '{base_path}/{id}/package_content/upload_from_uri'.format(
                id=vnf_package['id'],
                base_path=self.base_url),
            "POST", body=body)
        self.assertEqual(202, resp.status_code)

        self._wait_for_onboard(vnf_package['id'])

        self._disable_operational_state(vnf_package['id'])
        self._delete_vnf_package(vnf_package['id'])
        self._wait_for_delete(vnf_package['id'])

    def test_patch_in_onboarded_state(self):
        user_data = jsonutils.dumps(
            {"userDefinedData": {"key1": "val1", "key2": "val2",
                                 "key3": "val3"}})
        vnf_package = self._create_vnf_package(user_data)

        update_req_body = jsonutils.dumps(
            {"operationalState": "DISABLED",
             "userDefinedData": {"key1": "changed_val1",
                                 "key2": "val2", "new_key": "new_val"}})

        expected_result = {"operationalState": "DISABLED",
                           "userDefinedData": {
                               "key1": "changed_val1", "new_key": "new_val"}}

        csar_dir = self._get_csar_dir_path("vnfpkgm1")
        file_path = utils.create_csar_with_unique_artifact(csar_dir)
        self.addCleanup(os.remove, file_path)
        with open(file_path, 'rb') as file_object:
            resp, resp_body = self.http_client.do_request(
                '{base_path}/{id}/package_content'.format(
                    id=vnf_package['id'],
                    base_path=self.base_url),
                "PUT", body=file_object, content_type='application/zip')

        self.assertEqual(202, resp.status_code)
        self._wait_for_onboard(vnf_package['id'])

        # Update vnf package which is onboarded
        resp, resp_body = self.http_client.do_request(
            '{base_path}/{id}'.format(id=vnf_package['id'],
                                      base_path=self.base_url),
            "PATCH", content_type='application/json', body=update_req_body)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected_result, resp_body)
        self._delete_vnf_package(vnf_package['id'])
        self._wait_for_delete(vnf_package['id'])

    def test_index_attribute_filter(self):
        filter_expr = {
            'filter': "(gt,softwareImages/minDisk,7);"
            "(eq,onboardingState,ONBOARDED);"
            "(eq,softwareImages/checksum/algorithm,'sha-512');"
            "(eq,additionalArtifacts/checksum/algorithm,'sha-256')"
        }
        filter_url = self.base_url + "?" + urllib.parse.urlencode(filter_expr)
        resp, body = self.http_client.do_request(filter_url, "GET")
        package = deepcopy(self.package2)
        for attr in ['softwareImages', 'checksum', 'userDefinedData',
                     'additionalArtifacts']:
            package.pop(attr, None)
        expected_result = [package]
        self.assertEqual(expected_result, body)

    def test_index_attribute_selector_all_fields(self):
        """Test for attribute selector 'all_fields'

        We intentionally use attribute filter along with attribute selector.
        It is because when these tests run with concurrency > 1, there will
        be multiple sample packages present at a time. Hence attribute
        selector will be applied on all of them. It will be difficult to
        predict the expected result. Hence we are limiting the result set by
        filtering one of the vnf package which was created for this speific
        test.
        """
        filter_expr = {'filter': '(eq,id,%s)' % self.package_id1,
            'all_fields': ''}
        filter_url = self.base_url + "?" + urllib.parse.urlencode(filter_expr)
        resp, body = self.http_client.do_request(filter_url, "GET")
        expected_result = [self.package1]
        self.assertEqual(expected_result, body)

    def test_index_attribute_selector_exclude_default(self):
        filter_expr = {'filter': '(eq,id,%s)' % self.package_id2,
            'exclude_default': ''}
        filter_url = self.base_url + "?" + urllib.parse.urlencode(filter_expr)
        resp, body = self.http_client.do_request(filter_url, "GET")
        package2 = deepcopy(self.package2)
        for attr in ['softwareImages', 'checksum', 'userDefinedData',
                     'additionalArtifacts']:
            package2.pop(attr, None)
        expected_result = [package2]
        self.assertEqual(expected_result, body)

    def test_index_attribute_selector_exclude_fields(self):
        filter_expr = {
            'filter': '(eq,id,%s)' % self.package_id2,
            'exclude_fields': 'checksum,softwareImages/checksum,'
                              'additionalArtifacts/checksum'}
        filter_url = self.base_url + "?" + urllib.parse.urlencode(filter_expr)
        resp, body = self.http_client.do_request(filter_url, "GET")
        package2 = deepcopy(self.package2)
        for software_image in package2['softwareImages']:
            software_image.pop('checksum', None)
        for artifact in package2['additionalArtifacts']:
            artifact.pop('checksum', None)
        package2.pop('checksum', None)
        expected_result = [package2]
        self.assertEqual(expected_result, body)

    def test_index_attribute_selector_fields(self):
        filter_expr = {'filter': '(eq,id,%s)' % self.package_id1,
            'fields': 'softwareImages/checksum/hash,'
            'softwareImages/containerFormat,softwareImages/name,'
            'userDefinedData,additionalArtifacts/checksum/hash,'
            'additionalArtifacts/artifactPath'}
        filter_url = self.base_url + "?" + urllib.parse.urlencode(filter_expr)
        resp, body = self.http_client.do_request(filter_url, "GET")
        package1 = deepcopy(self.package1)

        # Prepare expected result
        for software_image in package1['softwareImages']:
            software_image['checksum'].pop('algorithm', None)
            for attr in ['createdAt', 'diskFormat', 'id', 'imagePath',
                    'minDisk', 'minRam', 'provider', 'size', 'userMetadata',
                    'version']:
                software_image.pop(attr, None)
        for artifact in package1['additionalArtifacts']:
            artifact['checksum'].pop('algorithm', None)
            artifact.pop('metadata', None)
        package1.pop('checksum', None)
        expected_result = [package1]
        self.assertEqual(expected_result, body)

    def test_get_vnfd_from_onboarded_vnf_package_for_content_type_zip(self):
        resp, resp_body = self.http_client.do_request(
            '{base_path}/{id}/vnfd'.format(id=self.package_id1,
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
        single_yaml_csar_dir = "sample_vnfpkg_no_meta_single_vnfd"
        vnf_package_id = self._create_and_upload_vnf(
            single_yaml_csar_dir)
        self.addCleanup(self._delete_vnf_package, vnf_package_id)
        self.addCleanup(self._disable_operational_state, vnf_package_id)
        resp, resp_body = self.http_client.do_request(
            '{base_path}/{id}/vnfd'.format(id=vnf_package_id,
                                           base_path=self.base_url),
            "GET", content_type=accept_header)
        self.assertEqual(200, resp.status_code)
        self.assertEqual('text/plain', resp.headers['Content-Type'])
        self.assertIsNotNone(resp.text)

    def test_fetch_vnf_package_content_partial_download_using_range(self):
        """Test partial download using 'Range' requests for csar zip"""
        # test for success on satisfiable Range request.
        range_ = 'bytes=3-8'
        headers = {'Range': range_}
        response = self.http_client.do_request(
            '{base_path}/{id}/package_content'.format(
                id=self.package_id1, base_path=self.base_url),
            "GET", body={}, headers=headers)
        self.assertEqual(206, response[0].status_code)
        self.assertEqual(
            '\x04\x14\x00\x00\x00\x00', response[0].content.decode(
                'utf-8', 'ignore'))
        self.assertEqual('6', response[0].headers['Content-Length'])

    def test_fetch_vnf_package_content_full_download(self):
        """Test full download for csar zip"""
        response = self.http_client.do_request(
            '{base_path}/{id}/package_content'.format(
                id=self.package_id1, base_path=self.base_url),
            "GET", body={}, headers={})
        self.assertEqual(200, response[0].status_code)
        self.assertEqual('12804503', response[0].headers['Content-Length'])

    def test_fetch_vnf_package_content_combined_download(self):
        """Combine two partial downloads using 'Range' requests for csar zip"""

        zip_file_path = tempfile.NamedTemporaryFile(delete=True)
        zipf = zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_STORED)

        # Partial download 1
        range_ = 'bytes=0-10'
        headers = {'Range': range_}
        response_1 = self.http_client.do_request(
            '{base_path}/{id}/package_content'.format(
                id=self.package_id1, base_path=self.base_url),
            "GET", body={}, headers=headers)
        size_1 = int(response_1[0].headers['Content-Length'])
        data = response_1[0].content
        file_path = self._get_csar_dir_path("data.txt")
        zipf.writestr(file_path, data)

        # Partial download 2
        range_ = 'bytes=11-12804503'
        headers = {'Range': range_}
        response_2 = self.http_client.do_request(
            '{base_path}/{id}/package_content'.format(
                id=self.package_id1, base_path=self.base_url),
            "GET", body={}, headers=headers)

        data = response_2[0].content
        zipf.writestr(file_path, data)
        zipf.close()
        size_2 = int(response_2[0].headers['Content-Length'])
        total_size = size_1 + size_2
        self.assertEqual(True, zipfile.is_zipfile(zip_file_path))
        self.assertEqual(12804503, total_size)
        zip_file_path.close()

    def test_fetch_vnf_package_artifacts(self):
        # run download api
        response1 = self.http_client.do_request(
            '{base_path}/{id}/artifacts/{artifact_path}'.format(
                base_path=self.base_url, id=self.package_id1,
                artifact_path='Scripts/install.sh'),
            "GET", body={}, headers={})

        response2 = self.http_client.do_request(
            '{base_path}/{id}/artifacts/{artifact_path}'.format(
                base_path=self.base_url, id=self.package_id2,
                artifact_path='Scripts/install.sh'),
            "GET", body={}, headers={})

        response3 = self.http_client.do_request(
            '{base_path}/{id}/artifacts/{artifact_path}'.format(
                base_path=self.base_url, id=self.package_id3,
                artifact_path='Scripts/install.sh'),
            "GET", body={}, headers={})
        # verification
        self.assertEqual(200, response1[0].status_code)
        self.assertEqual('33', response1[0].headers['Content-Length'])
        self.assertIsNotNone(response1[1])
        self.assertEqual(200, response2[0].status_code)
        self.assertEqual('33', response2[0].headers['Content-Length'])
        self.assertIsNotNone(response2[1])
        self.assertEqual(200, response3[0].status_code)
        self.assertEqual('33', response3[0].headers['Content-Length'])
        self.assertIsNotNone(response3[1])

    def test_fetch_vnf_package_artifacts_partial_download_using_range(self):
        # get range
        range_ = 'bytes=3-8'
        # get headers
        headers = {'Range': range_}
        # request download api
        response = self.http_client.do_request(
            '{base_path}/{id}/artifacts/{artifact_path}'.format(
                base_path=self.base_url, id=self.package_id1,
                artifact_path='Scripts/install.sh'),
            "GET", body={}, headers=headers)
        # verification
        self.assertEqual(206, response[0].status_code)
        self.assertEqual('6', response[0].headers['Content-Length'])
        self.assertIsNotNone(response[1])
