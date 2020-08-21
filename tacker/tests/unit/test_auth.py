# Copyright 2012 OpenStack Foundation
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
from oslo_middleware import request_id
import requests
from requests_mock.contrib import fixture as requests_mock_fixture
from tacker import auth
from tacker.tests import base
import tacker.tests.unit.vnfm.test_nfvo_client as nfvo_client

import threading

from tacker.tests import uuidsentinel

from oslo_log import log as logging
from unittest import mock
import webob

LOG = logging.getLogger(__name__)


class TackerKeystoneContextTestCase(base.BaseTestCase):
    def setUp(self):
        super(TackerKeystoneContextTestCase, self).setUp()

        @webob.dec.wsgify
        def fake_app(req):
            self.context = req.environ['tacker.context']
            return webob.Response()

        self.context = None
        self.middleware = auth.TackerKeystoneContext(fake_app)
        self.request = webob.Request.blank('/')
        self.request.headers['X_AUTH_TOKEN'] = 'testauthtoken'

    def test_no_user_id(self):
        self.request.headers['X_PROJECT_ID'] = 'testtenantid'
        response = self.request.get_response(self.middleware)
        self.assertEqual('401 Unauthorized', response.status)

    def test_with_user_id(self):
        self.request.headers['X_PROJECT_ID'] = 'testtenantid'
        self.request.headers['X_USER_ID'] = 'testuserid'
        response = self.request.get_response(self.middleware)
        self.assertEqual('200 OK', response.status)
        self.assertEqual('testuserid', self.context.user_id)
        self.assertEqual('testuserid', self.context.user)

    def test_with_tenant_id(self):
        self.request.headers['X_PROJECT_ID'] = 'testtenantid'
        self.request.headers['X_USER_ID'] = 'test_user_id'
        response = self.request.get_response(self.middleware)
        self.assertEqual('200 OK', response.status)
        self.assertEqual('testtenantid', self.context.tenant_id)
        self.assertEqual('testtenantid', self.context.tenant)

    def test_roles_no_admin(self):
        self.request.headers['X_PROJECT_ID'] = 'testtenantid'
        self.request.headers['X_USER_ID'] = 'testuserid'
        self.request.headers['X_ROLES'] = 'role1, role2 , role3,role4,role5'
        response = self.request.get_response(self.middleware)
        self.assertEqual('200 OK', response.status)
        self.assertEqual(['role1', 'role2', 'role3', 'role4', 'role5'],
                         self.context.roles)
        self.assertFalse(self.context.is_admin)

    def test_roles_with_admin(self):
        self.request.headers['X_PROJECT_ID'] = 'testtenantid'
        self.request.headers['X_USER_ID'] = 'testuserid'
        self.request.headers['X_ROLES'] = ('role1, role2 , role3,role4,role5,'
                                           'AdMiN')
        response = self.request.get_response(self.middleware)
        self.assertEqual('200 OK', response.status)
        self.assertEqual(['role1', 'role2', 'role3', 'role4', 'role5',
                          'AdMiN'],
                         self.context.roles)
        self.assertTrue(self.context.is_admin)

    def test_with_user_tenant_name(self):
        self.request.headers['X_PROJECT_ID'] = 'testtenantid'
        self.request.headers['X_USER_ID'] = 'testuserid'
        self.request.headers['X_PROJECT_NAME'] = 'testtenantname'
        self.request.headers['X_USER_NAME'] = 'testusername'
        response = self.request.get_response(self.middleware)
        self.assertEqual('200 OK', response.status)
        self.assertEqual('testuserid', self.context.user_id)
        self.assertEqual('testusername', self.context.user_name)
        self.assertEqual('testtenantid', self.context.tenant_id)
        self.assertEqual('testtenantname', self.context.tenant_name)

    def test_request_id_extracted_from_env(self):
        req_id = 'dummy-request-id'
        self.request.headers['X_PROJECT_ID'] = 'testtenantid'
        self.request.headers['X_USER_ID'] = 'testuserid'
        self.request.environ[request_id.ENV_REQUEST_ID] = req_id
        self.request.get_response(self.middleware)
        self.assertEqual(req_id, self.context.request_id)

    def test_with_auth_token(self):
        self.request.headers['X_PROJECT_ID'] = 'testtenantid'
        self.request.headers['X_USER_ID'] = 'testuserid'
        response = self.request.get_response(self.middleware)
        self.assertEqual('200 OK', response.status)
        self.assertEqual('testauthtoken', self.context.auth_token)

    def test_without_auth_token(self):
        self.request.headers['X_PROJECT_ID'] = 'testtenantid'
        self.request.headers['X_USER_ID'] = 'testuserid'
        del self.request.headers['X_AUTH_TOKEN']
        self.request.get_response(self.middleware)
        self.assertIsNone(self.context.auth_token)


@ddt.ddt
class TestAuthManager(base.BaseTestCase):

    def setUp(self):
        super(TestAuthManager, self).setUp()
        self.token_endpoint_url = 'https://oauth2/tokens'
        self.oauth_url = 'https://oauth2'
        self.user_name = 'test_user'
        self.password = 'test_password'
        auth.auth_manager = auth._AuthManager()
        self.requests_mock = self.useFixture(requests_mock_fixture.Fixture())

    def tearDown(self):
        super(TestAuthManager, self).tearDown()
        self.addCleanup(mock.patch.stopall)

    def test_init(self):
        self.assertEqual(None, cfg.CONF.authentication.auth_type)
        self.assertEqual(20, cfg.CONF.authentication.timeout)
        self.assertEqual(None, cfg.CONF.authentication.token_endpoint)
        self.assertEqual(None, cfg.CONF.authentication.client_id)
        self.assertEqual(None, cfg.CONF.authentication.client_password)
        self.assertEqual(None, cfg.CONF.authentication.user_name)
        self.assertEqual(None, cfg.CONF.authentication.password)

    def test_get_auth_client_oauth2_client_credentials_with_local(self):
        cfg.CONF.set_override('auth_type', 'OAUTH2_CLIENT_CREDENTIALS',
                              group='authentication')
        cfg.CONF.set_override('token_endpoint', self.token_endpoint_url,
                              group='authentication')
        cfg.CONF.set_override('client_id', self.user_name,
                              group='authentication')
        cfg.CONF.set_override('client_password', self.password,
                              group='authentication')

        self.requests_mock.register_uri('GET',
            self.token_endpoint_url,
            json={'access_token': 'test_token3', 'token_type': 'bearer'},
            headers={'Content-Type': 'application/json'},
            status_code=200)

        auth.auth_manager = auth._AuthManager()
        client = auth.auth_manager.get_auth_client()

        self.assertIsInstance(client, auth._OAuth2Session)
        self.assertEqual(
            self.user_name,
            client.grant.client_id)
        self.assertEqual(
            self.password,
            client.grant.client_password)
        self.assertEqual(
            self.token_endpoint_url,
            client.grant.token_endpoint)

        history = self.requests_mock.request_history
        req_count = nfvo_client._count_mock_history(history, self.oauth_url)
        self.assertEqual(1, req_count)

    def test_get_auth_client_basic_with_local(self):
        cfg.CONF.set_override('auth_type', 'BASIC',
                              group='authentication')
        cfg.CONF.set_override('user_name', self.user_name,
                              group='authentication')
        cfg.CONF.set_override('password', self.password,
                              group='authentication')

        auth.auth_manager = auth._AuthManager()
        client = auth.auth_manager.get_auth_client()

        self.assertIsInstance(client, auth._BasicAuthSession)
        self.assertEqual(self.user_name, client.user_name)
        self.assertEqual(self.password, client.password)

        history = self.requests_mock.request_history
        req_count = nfvo_client._count_mock_history(history, self.oauth_url)
        self.assertEqual(0, req_count)

    def test_get_auth_client_noauth_with_local(self):
        cfg.CONF.set_override('auth_type', None,
                              group='authentication')

        client = auth.auth_manager.get_auth_client()
        self.assertIsInstance(client, requests.Session)

        history = self.requests_mock.request_history
        req_count = nfvo_client._count_mock_history(history, self.oauth_url)
        self.assertEqual(0, req_count)

    def test_get_auth_client_oauth2_client_credentials_with_subscription(self):
        self.requests_mock.register_uri('GET',
            self.token_endpoint_url,
            json={'access_token': 'test_token', 'token_type': 'bearer'},
            headers={'Content-Type': 'application/json'},
            status_code=200)

        params_oauth2_client_credentials = {
            'clientId': self.user_name,
            'clientPassword': self.password,
            'tokenEndpoint': self.token_endpoint_url}

        auth.auth_manager.set_auth_client(
            id=uuidsentinel.subscription_id,
            auth_type='OAUTH2_CLIENT_CREDENTIALS',
            auth_params=params_oauth2_client_credentials)
        client = auth.auth_manager.get_auth_client(
            id=uuidsentinel.subscription_id)

        self.assertIsInstance(client, auth._OAuth2Session)
        self.assertEqual(
            self.user_name,
            client.grant.client_id)
        self.assertEqual(
            self.password,
            client.grant.client_password)
        self.assertEqual(
            self.token_endpoint_url,
            client.grant.token_endpoint)

        history = self.requests_mock.request_history
        req_count = nfvo_client._count_mock_history(history, self.oauth_url)
        self.assertEqual(1, req_count)

    def test_get_auth_client_basic_with_subscription(self):
        params_basic = {
            'userName': self.user_name,
            'password': self.password}

        auth.auth_manager.set_auth_client(
            id=uuidsentinel.subscription_id,
            auth_type='BASIC',
            auth_params=params_basic)
        client = auth.auth_manager.get_auth_client(
            id=uuidsentinel.subscription_id)

        self.assertIsInstance(client, auth._BasicAuthSession)
        self.assertEqual(self.user_name, client.user_name)
        self.assertEqual(self.password, client.password)

        history = self.requests_mock.request_history
        req_count = nfvo_client._count_mock_history(history, self.oauth_url)
        self.assertEqual(0, req_count)

    def test_set_auth_client_noauth(self):
        auth.auth_manager.set_auth_client(
            id=uuidsentinel.subscription_id,
            auth_type=None,
            auth_params={})

        manages = auth.auth_manager._AuthManager__manages
        self.assertNotIn(uuidsentinel.subscription_id, manages)

    def test_set_auth_client_basic(self):
        params_basic = {
            'userName': self.user_name,
            'password': self.password}

        auth.auth_manager.set_auth_client(
            id=uuidsentinel.subscription_id,
            auth_type='BASIC',
            auth_params=params_basic)

        manages = auth.auth_manager._AuthManager__manages
        self.assertIn(uuidsentinel.subscription_id, manages)

        client = manages.get(uuidsentinel.subscription_id)
        self.assertIsInstance(client, auth._BasicAuthSession)
        self.assertEqual(self.user_name, client.user_name)
        self.assertEqual(self.password, client.password)

    def test_set_auth_client_oauth2_client_credentials(self):
        self.requests_mock.register_uri(
            'GET', self.token_endpoint_url,
            json={
                'access_token': 'test_token', 'token_type': 'bearer'},
            headers={
                'Content-Type': 'application/json'},
            status_code=200)

        params_oauth2_client_credentials = {
            'clientId': self.user_name,
            'clientPassword': self.password,
            'tokenEndpoint': self.token_endpoint_url}

        auth.auth_manager.set_auth_client(
            id=uuidsentinel.subscription_id,
            auth_type='OAUTH2_CLIENT_CREDENTIALS',
            auth_params=params_oauth2_client_credentials)

        manages = auth.auth_manager._AuthManager__manages
        self.assertIn(uuidsentinel.subscription_id, manages)

        client = manages.get(uuidsentinel.subscription_id)
        self.assertIsInstance(client, auth._OAuth2Session)
        self.assertEqual(
            self.user_name,
            client.grant.client_id)
        self.assertEqual(
            self.password,
            client.grant.client_password)
        self.assertEqual(
            self.token_endpoint_url,
            client.grant.token_endpoint)

        history = self.requests_mock.request_history
        req_count = nfvo_client._count_mock_history(history, self.oauth_url)
        self.assertEqual(1, req_count)

    def test_set_auth_client_used_chahe(self):
        params_basic = {
            'userName': self.user_name,
            'password': self.password}

        auth.auth_manager.set_auth_client(
            id=uuidsentinel.subscription_id,
            auth_type='BASIC',
            auth_params=params_basic)

        params_oauth2_client_credentials = {
            'clientId': self.user_name,
            'clientPassword': self.password,
            'tokenEndpoint': self.token_endpoint_url}

        auth.auth_manager.set_auth_client(
            id=uuidsentinel.subscription_id,
            auth_type='OAUTH2_CLIENT_CREDENTIALS',
            auth_params=params_oauth2_client_credentials)

        manages = auth.auth_manager._AuthManager__manages
        self.assertIn(uuidsentinel.subscription_id, manages)

        client = manages.get(uuidsentinel.subscription_id)
        self.assertIsInstance(client, auth._BasicAuthSession)
        self.assertEqual(self.user_name, client.user_name)
        self.assertEqual(self.password, client.password)


@ddt.ddt
class TestBasicAuthSession(base.BaseTestCase):

    def setUp(self):
        super(TestBasicAuthSession, self).setUp()
        self.token_endpoint_url = 'https://oauth2/tokens'
        self.nfvo_url = 'http://nfvo.co.jp'
        self.user_name = 'test_user'
        self.password = 'test_password'
        self.requests_mock = self.useFixture(requests_mock_fixture.Fixture())

    def tearDown(self):
        super(TestBasicAuthSession, self).tearDown()
        self.addCleanup(mock.patch.stopall)

    @ddt.data('GET', 'PUT', 'POST', 'DELETE', 'PATCH')
    def test_request(self, http_method):
        client = auth._BasicAuthSession(
            user_name=self.user_name,
            password=self.password)

        self.requests_mock.register_uri(http_method,
            self.nfvo_url,
            headers={'Content-Type': 'application/json'},
            status_code=200)

        if http_method == 'GET':
            response = client.get(
                self.nfvo_url,
                params={
                    'sample_key': 'sample_value'})
        elif http_method == 'PUT':
            response = client.put(
                self.nfvo_url,
                data={
                    'sample_key': 'sample_value'})
        elif http_method == 'POST':
            response = client.post(
                self.nfvo_url,
                data={
                    'sample_key': 'sample_value'})
        elif http_method == 'DELETE':
            response = client.delete(
                self.nfvo_url,
                params={
                    'sample_key': 'sample_value'})
        elif http_method == 'PATCH':
            response = client.patch(
                self.nfvo_url,
                data={
                    'sample_key': 'sample_value'})

        self.assertEqual(200, response.status_code)
        history = self.requests_mock.request_history
        req_count = nfvo_client._count_mock_history(history, self.nfvo_url)
        self.assertEqual(1, req_count)


@ddt.ddt
class TestOAuth2Session(base.BaseTestCase):

    class MockThread(threading.Timer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def start(self):
            super().start()
            super().join(60)

    def setUp(self):
        super(TestOAuth2Session, self).setUp()
        self.token_endpoint_url = 'https://oauth2/tokens'
        self.oauth_url = 'https://oauth2'
        self.user_name = 'test_user'
        self.password = 'test_password'
        self.requests_mock = self.useFixture(requests_mock_fixture.Fixture())

    def tearDown(self):
        super(TestOAuth2Session, self).tearDown()
        self.addCleanup(mock.patch.stopall)

    def test_apply_access_token_info(self):
        res_mock = {
            'json': {
                'access_token': 'test_token',
                'token_type': 'bearer',
                'expires_in': '1'},
            'headers': {'Content-Type': 'application/json'},
            'status_code': 200}
        res_mock2 = {
            'json': {
                'access_token': 'test_token2',
                'token_type': 'bearer'},
            'headers': {'Content-Type': 'application/json'},
            'status_code': 200}

        self.requests_mock.register_uri(
            'GET',
            self.token_endpoint_url, [res_mock, res_mock2])

        grant = auth._ClientCredentialsGrant(
            client_id=self.user_name,
            client_password=self.password,
            token_endpoint=self.token_endpoint_url)

        with mock.patch("threading.Timer", side_effect=self.MockThread) as m:
            client = auth._OAuth2Session(grant)
            client.apply_access_token_info()

            history = self.requests_mock.request_history
            req_count = nfvo_client._count_mock_history(history,
                self.oauth_url)
            self.assertEqual(2, req_count)
            self.assertEqual(1, m.call_count)

    def test_apply_access_token_info_fail_error_response(self):
        error_description = """
        Either your username or password is incorrect
        or you are not an active user.
        Please try again or contact your administrator.
        """
        self.requests_mock.register_uri(
            'GET',
            self.token_endpoint_url,
            headers={
                'Content-Type': 'application/json;charset=UTF-8',
                'Cache-Control': 'no-store',
                'Pragma': 'no-store',
                'WWW-Authenticate': 'Basic realm="example"'},
            json={
                'error': 'invalid_client',
                'error_description': error_description},
            status_code=401)

        grant = auth._ClientCredentialsGrant(
            client_id=self.user_name,
            client_password=self.password,
            token_endpoint=self.token_endpoint_url)

        with mock.patch("threading.Timer", side_effect=self.MockThread) as m:
            try:
                client = auth._OAuth2Session(grant)
                client.apply_access_token_info()
            except requests.exceptions.RequestException as e:
                self.assertEqual(401, e.response.status_code)

            history = self.requests_mock.request_history
            req_count = nfvo_client._count_mock_history(history,
                self.oauth_url)
            self.assertEqual(1, req_count)
            self.assertEqual(0, m.call_count)

    def test_apply_access_token_info_fail_timeout(self):
        self.requests_mock.register_uri(
            'GET',
            self.token_endpoint_url,
            exc=requests.exceptions.ConnectTimeout)

        grant = auth._ClientCredentialsGrant(
            client_id=self.user_name,
            client_password=self.password,
            token_endpoint=self.token_endpoint_url)

        with mock.patch("threading.Timer", side_effect=self.MockThread) as m:
            try:
                client = auth._OAuth2Session(grant)
                client.apply_access_token_info()
            except requests.exceptions.RequestException as e:
                self.assertIsNone(e.response)

            history = self.requests_mock.request_history
            req_count = nfvo_client._count_mock_history(history,
                self.oauth_url)
            self.assertEqual(1, req_count)
            self.assertEqual(0, m.call_count)

    def test_schedule_refrash_token_expaire(self):
        self.requests_mock.register_uri(
            'GET',
            self.token_endpoint_url,
            headers={'Content-Type': 'application/json'},
            json={
                'access_token': 'test_token',
                'token_type': 'bearer'},
            status_code=200)

        grant = auth._ClientCredentialsGrant(
            client_id=self.user_name,
            client_password=self.password,
            token_endpoint=self.token_endpoint_url)

        with mock.patch("threading.Timer", side_effect=self.MockThread) as m:
            client = auth._OAuth2Session(grant)
            client._OAuth2Session__access_token_info.update({
                'access_token': 'test_token',
                'token_type': 'bearer',
                'expires_in': '1'})
            client.schedule_refrash_token()

            history = self.requests_mock.request_history
            req_count = nfvo_client._count_mock_history(history,
                self.oauth_url)
            self.assertEqual(1, req_count)
            self.assertEqual(1, m.call_count)

    def test_schedule_refrash_token_non_expaire(self):
        grant = auth._ClientCredentialsGrant(
            client_id=self.user_name,
            client_password=self.password,
            token_endpoint=self.token_endpoint_url)

        with mock.patch("threading.Timer", side_effect=self.MockThread) as m:
            client = auth._OAuth2Session(grant)
            client._OAuth2Session__access_token_info.update({
                'access_token': 'test_token',
                'token_type': 'bearer'})
            client.schedule_refrash_token()

            history = self.requests_mock.request_history
            req_count = nfvo_client._count_mock_history(history,
                self.oauth_url)
            self.assertEqual(0, req_count)
            self.assertEqual(0, m.call_count)

    @ddt.data(None, "")
    def test_schedule_refrash_token_invalid_value(self, invalid_value):
        grant = auth._ClientCredentialsGrant(
            client_id=self.user_name,
            client_password=self.password,
            token_endpoint=self.token_endpoint_url)

        with mock.patch("threading.Timer", side_effect=self.MockThread) as m:
            client = auth._OAuth2Session(grant)
            client._OAuth2Session__access_token_info.update({
                'access_token': 'test_token',
                'token_type': 'bearer',
                'expires_in': invalid_value})
            client.schedule_refrash_token()

            history = self.requests_mock.request_history
            req_count = nfvo_client._count_mock_history(history,
                self.oauth_url)
            self.assertEqual(0, req_count)
            self.assertEqual(0, m.call_count)

    @ddt.data('GET', 'PUT', 'POST', 'DELETE', 'PATCH')
    def test_request_client_credentials(self, http_method):
        self.requests_mock.register_uri('GET',
            self.token_endpoint_url,
            json={'access_token': 'test_token3', 'token_type': 'bearer'},
            headers={'Content-Type': 'application/json'},
            status_code=200)

        grant = auth._ClientCredentialsGrant(
            client_id=self.user_name,
            client_password=self.password,
            token_endpoint=self.token_endpoint_url)
        client = auth._OAuth2Session(grant)
        client.apply_access_token_info()

        self.requests_mock.register_uri(http_method,
            self.oauth_url,
            headers={'Content-Type': 'application/json'},
            status_code=200)

        if http_method == 'GET':
            response = client.get(
                self.oauth_url,
                params={
                    'sample_key': 'sample_value'})
        elif http_method == 'PUT':
            response = client.put(
                self.oauth_url,
                data={
                    'sample_key': 'sample_value'})
        elif http_method == 'POST':
            response = client.post(
                self.oauth_url,
                data={
                    'sample_key': 'sample_value'})
        elif http_method == 'DELETE':
            response = client.delete(
                self.oauth_url,
                params={
                    'sample_key': 'sample_value'})
        elif http_method == 'PATCH':
            response = client.patch(
                self.oauth_url,
                data={
                    'sample_key': 'sample_value'})

        self.assertEqual(200, response.status_code)
        history = self.requests_mock.request_history
        req_count = nfvo_client._count_mock_history(history, self.oauth_url)
        self.assertEqual(2, req_count)

    def test_request_client_credentials_auth_error(self):
        self.requests_mock.register_uri('GET',
            self.token_endpoint_url,
            json={'access_token': 'test_token3', 'token_type': 'bearer'},
            headers={'Content-Type': 'application/json'},
            status_code=200)

        self.requests_mock.register_uri('GET',
            "https://nfvo.co.jp",
            text="error.",
            status_code=401)

        grant = auth._ClientCredentialsGrant(
            client_id=self.user_name,
            client_password=self.password,
            token_endpoint=self.token_endpoint_url)
        client = auth._OAuth2Session(grant)
        client.apply_access_token_info()

        response = client.get('https://nfvo.co.jp')

        self.assertEqual(401, response.status_code)
        history = self.requests_mock.request_history
        req_count = nfvo_client._count_mock_history(
            history, self.oauth_url, 'https://nfvo.co.jp')
        self.assertEqual(3, req_count)
