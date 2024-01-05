#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os.path
import time

from oslo_serialization import jsonutils

from tacker.tests.functional.base import BaseTackerTest
from tacker.tests.functional.sol_enhanced_policy.base import (
    BaseEnhancedPolicyTest)
from tacker.tests import utils


class BaseVnfPackageAPIsTest(BaseTackerTest, BaseEnhancedPolicyTest):

    VNF_PACKAGE_UPLOAD_TIMEOUT = 300
    base_url = '/vnfpkgm/v1/vnf_packages'
    user_role_map = {
        'user_a': ['VENDOR_company_A', 'manager'],
        'user_b': ['VENDOR_company_B', 'manager'],
        'user_all': ['VENDOR_all', 'manager'],
    }

    @classmethod
    def setUpClass(cls):
        BaseTackerTest.setUpClass()
        BaseEnhancedPolicyTest.setUpClass(cls)

    @classmethod
    def tearDownClass(cls):
        BaseEnhancedPolicyTest.tearDownClass()
        BaseTackerTest.tearDownClass()

    def _step_pkg_create(self, username):
        client = self.get_tk_http_client_by_user(username)

        resp, pkg = client.do_request(
            self.base_url, 'POST',
            body=jsonutils.dumps({"userDefinedData": {"foo": "bar"}}))

        self.assertEqual(201, resp.status_code)
        return pkg

    def _step_pkg_show(self, username, pkg, expected_status_code,
                       expected_vendor=None):
        client = self.get_tk_http_client_by_user(username)
        resp, pkg = client.do_request(
            os.path.join(self.base_url, pkg.get('id')),
            'GET')
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 200 and expected_vendor:
            self.assertEqual(expected_vendor, pkg.get('vnfProvider'))

    def _step_pkg_list(self, username, expected_pkg_list):
        client = self.get_tk_http_client_by_user(username)
        resp, pkgs = client.do_request(self.base_url, 'GET')
        self.assertEqual(200, resp.status_code)
        pkg_ids = set([pkg.get('id') for pkg in pkgs])
        for pkg in expected_pkg_list:
            self.assertIn(pkg.get('id'), pkg_ids)

    def _get_csar_dir_path(self, csar_name):
        return utils.test_etc_sample("etsi/nfv", csar_name)

    def _wait_for_onboard(self, client, package_uuid):
        show_url = os.path.join(self.base_url, package_uuid)
        timeout = self.VNF_PACKAGE_UPLOAD_TIMEOUT
        start_time = int(time.time())
        while True:
            resp, body = client.do_request(show_url, "GET")
            if body['onboardingState'] == "ONBOARDED":
                break

            if (int(time.time()) - start_time) > timeout:
                raise Exception("Failed to onboard vnf package")

            time.sleep(1)

    def _step_pkg_upload_content(self, username, pkg, csar_name, provider,
                                 expected_status_code):
        client = self.get_tk_http_client_by_user(username)
        csar_dir = self._get_csar_dir_path(csar_name)

        file_path, vnfd_id = self.custom_csar(csar_dir, provider)
        self.addCleanup(os.remove, file_path)
        with open(file_path, 'rb') as file_object:
            resp, resp_body = client.do_request(
                '{base_path}/{id}/package_content'.format(
                    id=pkg['id'],
                    base_path=self.base_url),
                "PUT", body=file_object, content_type='application/zip')
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            self._wait_for_onboard(client, pkg['id'])

    def _step_pkg_read_vnfd(self, username, pkg, expected_status_code):
        client = self.get_tk_http_client_by_user(username)
        resp, resp_body = client.do_request(
            '{base_path}/{id}/vnfd'.format(id=pkg['id'],
                                           base_path=self.base_url),
            "GET", content_type='application/zip')
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 200:
            self.assertEqual('application/zip', resp.headers['Content-Type'])
            self.assertIsNotNone(resp.text)

    def _step_pkg_fetch(self, username, pkg, expected_status_code):
        client = self.get_tk_http_client_by_user(username)
        response = client.do_request(
            '{base_path}/{id}/package_content'.format(
                id=pkg['id'], base_path=self.base_url),
            "GET", body={}, headers={})
        self.assertEqual(expected_status_code, response[0].status_code)

    def _step_pkg_update(self, username, pkg, expected_status_code):
        client = self.get_tk_http_client_by_user(username)
        update_req_body = jsonutils.dumps({
            "operationalState": "DISABLED"})

        resp, _ = client.do_request(
            '{base_path}/{id}'.format(id=pkg['id'],
                                      base_path=self.base_url),
            "PATCH", content_type='application/json', body=update_req_body)
        self.assertEqual(expected_status_code, resp.status_code)

    def _step_pkg_delete(self, username, pkg, expected_status_code):
        client = self.get_tk_http_client_by_user(username)
        resp, _ = client.do_request(os.path.join(self.base_url, pkg.get('id')),
                                    'DELETE')
        self.assertEqual(expected_status_code, resp.status_code)

    def _test_vnf_package_apis_enhanced_policy(self, csar_name):
        # step 1 PKG-Create, Resource Group A / User Group A
        pkg_a = self._step_pkg_create('user_a')

        # step 2 PKG-Create, Resource Group B / User Group all
        pkg_b = self._step_pkg_create('user_all')

        # step 3 PKG-Show, Resource Group A / User Group A
        self._step_pkg_show('user_a', pkg_a, 200)

        # step 4 PKG-Show, Resource Group B / User Group A
        self._step_pkg_show('user_a', pkg_b, 200)

        # step 5 PKG-Show, Resource Group A / User Group A
        self._step_pkg_show('user_all', pkg_b, 200)

        # step 6 PKG-List, Resource Group - / User Group A
        self._step_pkg_list('user_a', [pkg_a, pkg_b])

        # step 7 PKG-List, Resource Group - / User Group B
        self._step_pkg_list('user_b', [pkg_a, pkg_b])

        # step 8 PKG-List, Resource Group - / User Group all
        self._step_pkg_list('user_all', [pkg_a, pkg_b])

        # step 9 PKG-Upload-content, Resource Group B / User Group A
        self._step_pkg_upload_content(
            'user_a', pkg_a, csar_name, 'company_B', 403)

        # step 10 PKG-Upload-content, Resource Group A / User Group A
        self._step_pkg_upload_content(
            'user_a', pkg_a, csar_name, 'company_A', 202)

        # step 11 PKG-Upload-content, Resource Group B / User Group all
        self._step_pkg_upload_content(
            'user_all', pkg_b, csar_name, 'company_B', 202)

        # step 12 PKG-Show, Resource Group A / User Group A
        self._step_pkg_show('user_a', pkg_a, 200)

        # step 13 PKG-Show, Resource Group B / User Group A
        self._step_pkg_show('user_a', pkg_b, 403)

        # step 14 PKG-Show, Resource Group A / User Group A
        self._step_pkg_show('user_all', pkg_b, 200)

        # step 15 PKG-List, Resource Group - / User Group A
        self._step_pkg_list('user_a', [pkg_a])

        # step 16 PKG-List, Resource Group - / User Group B
        self._step_pkg_list('user_b', [pkg_b])

        # step 17 PKG-List, Resource Group - / User Group all
        self._step_pkg_list('user_all', [pkg_a, pkg_b])

        # step 18 PKG-Read-vnfd, Resource Group A / User Group A
        self._step_pkg_read_vnfd('user_a', pkg_a, 200)

        # step 19 PKG-Read-vnfd, Resource Group B / User Group A
        self._step_pkg_read_vnfd('user_a', pkg_b, 403)

        # step 20 PKG-Read-vnfd, Resource Group B / User Group all
        self._step_pkg_read_vnfd('user_all', pkg_b, 200)

        # step 21 PKG-Read-vnfd, Resource Group A / User Group A
        self._step_pkg_fetch('user_a', pkg_a, 200)

        # step 22 PKG-Read-vnfd, Resource Group B / User Group A
        self._step_pkg_fetch('user_a', pkg_b, 403)

        # step 23 PKG-Read-vnfd, Resource Group B / User Group all
        self._step_pkg_fetch('user_all', pkg_b, 200)

        # step 24 PKG-Update, Resource Group B / User Group A
        self._step_pkg_update('user_a', pkg_b, 403)

        # step 25 PKG-Update, Resource Group A / User Group A
        self._step_pkg_update('user_a', pkg_a, 200)

        # step 26 PKG-Update, Resource Group B / User Group all
        self._step_pkg_update('user_all', pkg_b, 200)

        # step 27 PKG-Delete, Resource Group A / User Group A
        self._step_pkg_delete('user_a', pkg_a, 204)

        # step 29 PKG-Delete, Resource Group B / User Group all
        self._step_pkg_delete('user_all', pkg_b, 204)


class VnfPackageAPIsTest(BaseVnfPackageAPIsTest):

    def test_vnf_package_apis_enhanced_policy_vnf(self):
        self._test_vnf_package_apis_enhanced_policy('test_enhanced_policy')


class CnfPackageAPIsTest(BaseVnfPackageAPIsTest):

    def test_vnf_package_apis_enhanced_policy_cnf(self):
        self._test_vnf_package_apis_enhanced_policy('test_cnf_scale')
