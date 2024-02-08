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
from oslo_config import cfg
from unittest import mock

from tacker import context
from tacker.sol_refactored.api.policies.vnflcm_v2 import POLICY_NAME
from tacker.sol_refactored.api import wsgi as sol_wsgi
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.tests.unit import base


@ddt.ddt
class TestWsgi(base.TestCase):

    def test_response_too_big(self):
        self.config_fixture.config(group='v2_vnfm', max_content_length=20)
        body = {"key": "value0123456789"}
        response = sol_wsgi.SolResponse(200, body)
        self.assertRaises(sol_ex.ResponseTooBig,
            response.serialize, 'application/json')

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
        controller = sol_wsgi.SolAPIController()
        controller.supported_api_versions = mock.Mock(return_value=['1.0'])
        resource = sol_wsgi.SolResource(controller)
        request = mock.Mock()
        request.headers = {}
        self.assertRaises(sol_ex.APIVersionMissing,
            resource._check_api_version, request, 'action')

    @mock.patch.object(context.Context, 'can')
    def test_enhanced_policy_action(self, mock_can):
        cfg.CONF.set_override(
            "enhanced_tacker_policy", True, group='oslo_policy')
        resource = sol_wsgi.SolResource(sol_wsgi.SolAPIController(),
                                        policy_name=POLICY_NAME)
        request = mock.Mock()
        request.context = context.Context()
        request.headers = {}
        enhanced_policy_actions = [
            'create',
            'index',
            'show',
            'delete',
            'update',
            'instantiate',
            'terminate',
            'scale',
            'heal',
            'change_ext_conn',
            'change_vnfpkg'
        ]
        for action in enhanced_policy_actions:
            resource._check_policy(request, action)
            mock_can.assert_not_called()

    @ddt.data('api_versions',
              'subscription_create',
              'subscription_list',
              'subscription_show',
              'subscription_delete',
              'lcm_op_occ_list',
              'lcm_op_occ_show',
              'lcm_op_occ_retry',
              'lcm_op_occ_rollback',
              'lcm_op_occ_fail',
              'lcm_op_occ_delete')
    @mock.patch.object(context.Context, 'can')
    def test_not_enhanced_policy_action(self, action, mock_can):
        cfg.CONF.set_override(
            "enhanced_tacker_policy", True, group='oslo_policy')
        resource = sol_wsgi.SolResource(sol_wsgi.SolAPIController(),
                                        policy_name=POLICY_NAME)
        request = mock.Mock()
        request.context = context.Context()
        request.headers = {}

        resource._check_policy(request, action)
        mock_can.assert_called_once()

    @ddt.data('create',
              'index',
              'show',
              'delete',
              'update',
              'instantiate',
              'terminate',
              'scale',
              'heal',
              'change_ext_conn',
              'change_vnfpkg',
              'api_versions',
              'subscription_create',
              'subscription_list',
              'subscription_show',
              'subscription_delete',
              'lcm_op_occ_list',
              'lcm_op_occ_show',
              'lcm_op_occ_retry',
              'lcm_op_occ_rollback',
              'lcm_op_occ_fail',
              'lcm_op_occ_delete')
    @mock.patch.object(context.Context, 'can')
    def test_enhanced_policy_is_false(self, action, mock_can):
        cfg.CONF.set_override(
            "enhanced_tacker_policy", False, group='oslo_policy')
        resource = sol_wsgi.SolResource(sol_wsgi.SolAPIController(),
                                        policy_name=POLICY_NAME)
        request = mock.Mock()
        request.context = context.Context()
        request.headers = {}

        resource._check_policy(request, action)
        mock_can.assert_called_once()
