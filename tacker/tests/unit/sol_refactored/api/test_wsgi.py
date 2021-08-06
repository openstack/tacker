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

from unittest import mock

from tacker.sol_refactored.api import wsgi as sol_wsgi
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.tests.unit import base


class TestWsgi(base.TestCase):

    def test_response_too_big(self):
        self.config_fixture.config(group='v2_vnfm', max_content_length=20)
        body = {"key": "value0123456789"}
        response = sol_wsgi.SolResponse(200, body)
        self.assertRaises(sol_ex.ResponseTooBig,
            response.serialize, mock.Mock(), 'application/json')

    def test_unknown_error_response(self):
        err_msg = "Test error"
        status = 500
        response = sol_wsgi.SolErrorResponse(Exception(err_msg), mock.Mock())
        problem_details = {
            "status": status,
            "detail": err_msg
        }
        self.assertEqual(status, response.status)
        self.assertEqual(problem_details, response.body)

    def test_check_api_version_no_version(self):
        resource = sol_wsgi.SolResource(mock.Mock())
        request = mock.Mock()
        request.headers = {}
        self.assertRaises(sol_ex.APIVersionMissing,
            resource.check_api_version, request)
