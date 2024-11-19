# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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

from tacker.tests.functional.sol_v2_common import paramgen
from tacker.tests.functional.sol_v2_common import test_vnflcm_basic_common
from tacker.tests import utils


@ddt.ddt
class VnfLcmMinTest(test_vnflcm_basic_common.CommonVnfLcmTest):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmMinTest, cls).setUpClass()

        # for basic lcms tests min pattern
        basic_lcms_min_path = utils.test_sample("functional/sol_v2_common",
                                                "basic_lcms_min")
        # no image contained
        cls.min_pkg, cls.min_vnfd_id = cls.create_vnf_package(
            basic_lcms_min_path)

        # for update vnf test
        update_vnf_path = utils.test_sample("functional/sol_v2_common",
                                            "update_vnf")
        # no image contained
        cls.upd_pkg, cls.upd_vnfd_id = cls.create_vnf_package(update_vnf_path)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmMinTest, cls).tearDownClass()
        cls.delete_vnf_package(cls.min_pkg)
        cls.delete_vnf_package(cls.upd_pkg)

    def setUp(self):
        super().setUp()

    def test_api_versions(self):
        """Test version operations

        * About version operations:
          This test includes the following operations.
          - 1. List VNFLCM API versions
          - 2. Show VNFLCM API versions
        """
        path = "/vnflcm/api_versions"
        resp, body = self.tacker_client.do_request(path, "GET")
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        expected_body = {
            "uriPrefix": "/vnflcm",
            "apiVersions": [
                {'version': '1.3.0', 'isDeprecated': False},
                {'version': '2.0.0', 'isDeprecated': False}
            ]
        }
        self.assertEqual(body, expected_body)

        path = "/vnflcm/v2/api_versions"
        resp, body = self.tacker_client.do_request(path, "GET")
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        expected_body = {
            "uriPrefix": "/vnflcm/v2",
            "apiVersions": [
                {'version': '2.0.0', 'isDeprecated': False}
            ]
        }
        self.assertEqual(body, expected_body)

    @ddt.data(True, False)
    def test_subscriptions(self, is_all):
        """Test subscription operations

        * About attributes:
          - is_all=True
              All of the following cardinality attributes are set.
              In addition, 0..N or 1..N attributes are set to 2 or more.
              0..1 is set to 1.
              - 0..1 (1)
              - 0..N (2 or more)
              - 1..N (2 or more)
          - is_all=False
              Omit except for required attributes.
              Only the following cardinality attributes are set.
              - 1
              - 1..N (1)

        * About subscription operations:
          This test includes the following operations.
          - 0. Pre-setting
          - 1. Create a new subscription
          - 2. Show subscription
          - 3. List subscription with attribute-based filtering
          - 4. Delete a subscription
        """

        # 0. Pre-setting
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_min(callback_uri)
        if is_all:
            sub_req = paramgen.sub_create_max(callback_uri)

        # 1. Create a new subscription
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']

        # 2. Show subscription
        expected_attrs = [
            'id', 'callbackUri', 'verbosity', '_links'
        ]
        if is_all:
            additional_attrs = ['filter']
            expected_attrs.extend(additional_attrs)

        resp, body = self.show_subscription(sub_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 3. List subscription with attribute-based filtering
        filter_expr = {'filter': '(eq,id,%s)' % sub_id}
        resp, body = self.list_subscriptions(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for sbsc in body:
            self.check_resp_body(sbsc, expected_attrs)

        # 4. Delete a subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

    def test_basic_lcms_min(self):
        self.basic_lcms_min_common_test()
