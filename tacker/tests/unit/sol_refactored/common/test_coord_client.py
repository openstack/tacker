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
import requests
from unittest import mock

from tacker.sol_refactored.common import common_script_utils
from tacker.sol_refactored.common import coord_client
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import http_client
from tacker.tests import base


ENDPOINT = 'http://127.0.0.1:6789'
TIMEOUT = 30

coord_req_example = {
    'vnfInstanceId': 'b18a8a15-8973-4202-a2f0-a67a109fc461',
    'vnfLcmOpOccId': '2cae986e-7fea-4aeb-9b22-f81b35800838',
    'lcmOperationType': 'CHANGE_VNFPKG',
    '_links': {
        'vnfLcmOpOcc': {'href': 'http://127.0.0.1:9890/vnflcm/v2/'
                                'vnf_lcm_op_occs/'
                                '2cae986e-7fea-4aeb-9b22-f81b35800838'},
        'vnfInstance': {'href': 'http://127.0.0.1:9890/vnflcm/v2/'
                                'vnf_instances/'
                                'b18a8a15-8973-4202-a2f0-a67a109fc461'}
    },
    'coordinationActionName': 'prv.tacker_organization.coordination_test'
}

resp_body = {
    'id': '2e11d0cb-8cb1-4418-926c-5e31f0a2538b',
    'coordinationResult': 'CONTINUE',
    'vnfInstanceId': 'b18a8a15-8973-4202-a2f0-a67a109fc461',
    'vnfLcmOpOccId': '2cae986e-7fea-4aeb-9b22-f81b35800838',
    'lcmOperationType': 'CHANGE_VNFPKG',
    'coordinationActionName': 'prv.tacker_organization.coordination_test',
    '_links': {
        'vnfLcmOpOcc': {'href': 'http://127.0.0.1:9890/vnflcm/v2/'
                                'vnf_lcm_op_occs/'
                                '2cae986e-7fea-4aeb-9b22-f81b35800838'},
        'vnfInstance': {'href': 'http://127.0.0.1:9890/vnflcm/v2/'
                                'vnf_instances/'
                                'b18a8a15-8973-4202-a2f0-a67a109fc461'}
    }
}


class TestCoordClient(base.BaseTestCase):

    @mock.patch.object(common_script_utils, 'check_subsc_auth')
    @mock.patch.object(common_script_utils, 'get_http_auth_handle')
    @mock.patch.object(http_client.HttpClient, 'do_request')
    def test_create_coordination_synchronous(self, mock_resp,
            mock_auth_handle, mock_check_auth):

        resp = requests.Response()
        resp.status_code = 201
        mock_resp.return_value = (resp, resp_body)

        body = coord_client.create_coordination(ENDPOINT, mock.Mock(),
            coord_req_example, TIMEOUT)
        self.assertEqual(resp_body, body)

    @mock.patch.object(common_script_utils, 'check_subsc_auth')
    @mock.patch.object(common_script_utils, 'get_http_auth_handle')
    @mock.patch.object(http_client.HttpClient, 'do_request')
    def test_create_coordination_synchronous_retry(self, mock_resp,
            mock_auth_handle, mock_check_auth):

        resp_1 = requests.Response()
        resp_1.status_code = 503
        resp_1.headers['Retry-After'] = "1"

        resp_2 = requests.Response()
        resp_2.status_code = 201

        mock_resp.side_effect = [(resp_1, None), (resp_2, resp_body)]
        body = coord_client.create_coordination(ENDPOINT, mock.Mock(),
            coord_req_example, TIMEOUT)

        self.assertEqual(2, mock_resp.call_count)
        self.assertEqual(resp_body, body)

    @mock.patch.object(common_script_utils, 'check_subsc_auth')
    @mock.patch.object(common_script_utils, 'get_http_auth_handle')
    @mock.patch.object(http_client.HttpClient, 'do_request')
    def test_create_coordination_asynchronous(self, mock_resp,
            mock_auth_handle, mock_check_auth):

        resp_1 = requests.Response()
        resp_1.status_code = 202
        resp_1.headers['Location'] = ("http://127.0.0.1:6789/"
                                      "lcmcoord/v1/coordinations/"
                                      "b18a8a15-8973-4202-a2f0-a67a109fc461")

        resp_2 = requests.Response()
        resp_2.status_code = 202
        resp_2.headers['Location'] = ("http://127.0.0.1:6789/"
                                      "lcmcoord/v1/coordinations/"
                                      "b18a8a15-8973-4202-a2f0-a67a109fc461")
        resp_2.headers['Retry-After'] = "1"

        resp_3 = requests.Response()
        resp_3.status_code = 200

        mock_resp.side_effect = [(resp_1, None), (resp_2, None),
                                 (resp_3, resp_body)]
        body = coord_client.create_coordination(ENDPOINT, mock.Mock(),
            coord_req_example, TIMEOUT)

        self.assertEqual(3, mock_resp.call_count)
        self.assertEqual(resp_body, body)

    @mock.patch.object(common_script_utils, 'check_subsc_auth')
    @mock.patch.object(common_script_utils, 'get_http_auth_handle')
    @mock.patch.object(http_client.HttpClient, 'do_request')
    def test_create_coordination_no_location_header(self, mock_resp,
            mock_auth_handle, mock_check_auth):

        resp = requests.Response()
        resp.status_code = 202
        mock_resp.return_value = (resp, None)

        ex = self.assertRaises(sol_ex.SolException,
            coord_client.create_coordination, ENDPOINT, mock.Mock(),
            coord_req_example, TIMEOUT)
        expected_message = "Location header not included in response."
        self.assertEqual(expected_message, ex.detail)

    @mock.patch.object(common_script_utils, 'check_subsc_auth')
    @mock.patch.object(common_script_utils, 'get_http_auth_handle')
    @mock.patch.object(http_client.HttpClient, 'do_request')
    def test_create_coordination_timeout(self, mock_resp,
            mock_auth_handle, mock_check_auth):
        TIMEOUT = 5

        resp = requests.Response()
        resp.status_code = 503
        resp.headers['Retry-After'] = "2"
        mock_resp.return_value = (resp, None)

        ex = self.assertRaises(sol_ex.SolException,
            coord_client.create_coordination, ENDPOINT, mock.Mock(),
            coord_req_example, TIMEOUT)
        self.assertEqual(3, mock_resp.call_count)
        expected_message = ("coordinationVNF script did not complete within "
                            "the timeout period.")
        self.assertEqual(expected_message, ex.detail)

    @mock.patch.object(common_script_utils, 'check_subsc_auth')
    @mock.patch.object(common_script_utils, 'get_http_auth_handle')
    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch('tacker.sol_refactored.common.coord_client.DEFAULT_TIMEOUT', 3)
    def test_create_coordination_check_timeout_value(self, mock_resp,
            mock_auth_handle, mock_check_auth):
        resp = requests.Response()
        resp.status_code = 503
        resp.headers['Retry-After'] = "2"
        mock_resp.return_value = (resp, None)

        # Check timeout value is None
        TIMEOUT = None
        ex = self.assertRaises(sol_ex.SolException,
            coord_client.create_coordination, ENDPOINT, mock.Mock(),
            coord_req_example, TIMEOUT)
        self.assertEqual(2, mock_resp.call_count)
        expected_message = ("coordinationVNF script did not complete within "
                            "the timeout period.")
        self.assertEqual(expected_message, ex.detail)

        # Check timeout value is string
        mock_resp.reset_mock()
        TIMEOUT = "test"
        ex = self.assertRaises(sol_ex.SolException,
            coord_client.create_coordination, ENDPOINT, mock.Mock(),
            coord_req_example, TIMEOUT)
        self.assertEqual(2, mock_resp.call_count)
        expected_message = ("coordinationVNF script did not complete within "
                            "the timeout period.")
        self.assertEqual(expected_message, ex.detail)

    @mock.patch.object(common_script_utils, 'check_subsc_auth')
    @mock.patch.object(common_script_utils, 'get_http_auth_handle')
    @mock.patch.object(http_client.HttpClient, 'do_request')
    def test_create_coordination_check_retry_after(self, mock_resp,
            mock_auth_handle, mock_check_auth):
        TIMEOUT = 5

        resp = requests.Response()
        resp.status_code = 503

        # Check DEFAULT_INTERVAL is used if Retry-After value is
        # HTTP-date format.(DEFAULT_INTERVAL = 5)
        resp.headers['Retry-After'] = "Mon, 28 Aug 2023 12:00:00 GMT"
        mock_resp.return_value = (resp, None)

        ex = self.assertRaises(sol_ex.SolException,
            coord_client.create_coordination, ENDPOINT, mock.Mock(),
            coord_req_example, TIMEOUT)
        self.assertEqual(2, mock_resp.call_count)
        expected_message = ("coordinationVNF script did not complete within "
                            "the timeout period.")
        self.assertEqual(expected_message, ex.detail)

        # Check DEFAULT_INTERVAL is used if Retry-After value is
        # a negative number.(DEFAULT_INTERVAL = 5)
        mock_resp.reset_mock()
        resp.headers['Retry-After'] = "-3"
        mock_resp.return_value = (resp, None)

        ex = self.assertRaises(sol_ex.SolException,
            coord_client.create_coordination, ENDPOINT, mock.Mock(),
            coord_req_example, TIMEOUT)
        self.assertEqual(2, mock_resp.call_count)
        expected_message = ("coordinationVNF script did not complete within "
                            "the timeout period.")
        self.assertEqual(expected_message, ex.detail)
