# Copyright (c) 2012 OpenStack Foundation.
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

import json
import requests
from unittest import mock

from tacker.common import oidc_utils
from tacker.extensions.vnfm import OIDCAuthFailed
from tacker.tests import base


class FakeResponse:

    def __init__(self, status_code, body, headers=None):
        self.status_code = status_code
        self.headers = headers
        self.text = body

    def json(self):
        return json.loads(self.text)


class TestOidcUtils(base.BaseTestCase):

    @mock.patch('requests.post')
    def test_get_id_token_with_password_grant(self, mock_post):
        mock_post.return_value = FakeResponse(
            200,
            '{"id_token": "id token"}',
            headers={'Content-Type': 'application/json'}
        )
        id_token = oidc_utils.get_id_token_with_password_grant(
            'oidc_token_url',
            'username',
            'password',
            'client_id',
            client_secret='client_secret',
            ssl_ca_cert='ssl_ca_cert'
        )
        self.assertEqual(id_token, 'id token')

    @mock.patch('requests.post')
    def test_get_id_token_with_password_grant_no_option_param(self, mock_post):
        mock_post.return_value = FakeResponse(
            200,
            '{"id_token": "id token"}',
            headers={'Content-Type': 'application/json'}
        )
        id_token = oidc_utils.get_id_token_with_password_grant(
            'oidc_token_url',
            'username',
            'password',
            'client_id'
        )
        self.assertEqual(id_token, 'id token')

    def test_get_id_token_with_password_grant_required_param_is_none(self):
        exc = self.assertRaises(
            OIDCAuthFailed,
            oidc_utils.get_id_token_with_password_grant,
            'oidc_token_url',
            'username',
            'password',
            None)

        detail = ('token_endpoint, username, password,'
                  ' client_id can not be empty.')
        msg = f'OIDC authentication and authorization failed. Detail: {detail}'
        self.assertEqual(msg, exc.format_message())

    @mock.patch('requests.post')
    def test_get_id_token_with_password_grant_401(self, mock_post):
        mock_post.return_value = FakeResponse(
            401,
            '{"error": "invalid_grant", '
            'error_description": "Invalid user credentials"}'
        )
        exc = self.assertRaises(
            OIDCAuthFailed,
            oidc_utils.get_id_token_with_password_grant,
            'oidc_token_url',
            'username',
            'password',
            'client_id',
            client_secret='client_secret',
            ssl_ca_cert='ssl_ca_cert')

        detail = ('response code: 401, body: {"error": "invalid_grant", '
                  'error_description": "Invalid user credentials"}')
        msg = f'OIDC authentication and authorization failed. Detail: {detail}'
        self.assertEqual(msg, exc.format_message())

    @mock.patch('requests.post')
    def test_get_id_token_with_password_grant_request_exception(
            self, mock_post):
        mock_post.side_effect = requests.exceptions.RequestException(
            'Connection refused'
        )
        exc = self.assertRaises(
            OIDCAuthFailed,
            oidc_utils.get_id_token_with_password_grant,
            'oidc_token_url',
            'username',
            'password',
            'client_id',
            client_secret='client_secret',
            ssl_ca_cert='ssl_ca_cert')

        detail = 'Connection refused'
        msg = f'OIDC authentication and authorization failed. Detail: {detail}'
        self.assertEqual(msg, exc.format_message())
