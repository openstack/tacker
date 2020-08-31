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

import base64
import ddt
from oslo_config import cfg
from oslo_middleware import request_id
import requests
from requests_mock.contrib import fixture as requests_mock_fixture
import tacker.api.vnflcm.v1.router as vnflcm_router
import tacker.api.vnfpkgm.v1.router as vnfpkgm_router
from tacker import auth
from tacker.tests import base as test_base
from tacker.tests.unit import base as unit_base
from tacker.tests.unit import fake_auth

import threading

from tacker.tests import uuidsentinel

from oslo_log import log as logging
from unittest import mock
import webob

LOG = logging.getLogger(__name__)


def _count_mock_history(history, *url):
    req_count = 0
    for mock_history in history:
        actual_url = '{}://{}'.format(mock_history.scheme,
              mock_history.hostname)
        if actual_url in url:
            req_count += 1
    return req_count


class TackerKeystoneContextTestCase(test_base.BaseTestCase):
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
class TestAuthManager(test_base.BaseTestCase):

    def setUp(self):
        super(TestAuthManager, self).setUp()
        self.url = 'https://oauth2/tokens'
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
        cfg.CONF.set_override('token_endpoint', self.url,
                              group='authentication')
        cfg.CONF.set_override('client_id', self.user_name,
                              group='authentication')
        cfg.CONF.set_override('client_password', self.password,
                              group='authentication')

        self.requests_mock.register_uri('GET',
            self.url,
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
            self.url,
            client.grant.token_endpoint)

        history = self.requests_mock.request_history
        self.assertEqual(1, len(history))

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
        self.assertEqual(0, len(history))

    def test_get_auth_client_noauth_with_local(self):
        cfg.CONF.set_override('auth_type', None,
                              group='authentication')

        client = auth.auth_manager.get_auth_client()
        self.assertIsInstance(client, requests.Session)

        history = self.requests_mock.request_history
        self.assertEqual(0, len(history))

    def test_get_auth_client_oauth2_client_credentials_with_subscription(self):
        self.requests_mock.register_uri('GET',
            self.url,
            json={'access_token': 'test_token', 'token_type': 'bearer'},
            headers={'Content-Type': 'application/json'},
            status_code=200)

        params_oauth2_client_credentials = {
            'clientId': self.user_name,
            'clientPassword': self.password,
            'tokenEndpoint': self.url}

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
            self.url,
            client.grant.token_endpoint)

        history = self.requests_mock.request_history
        self.assertEqual(1, len(history))

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
        self.assertEqual(0, len(history))

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
            'GET', self.url,
            json={
                'access_token': 'test_token', 'token_type': 'bearer'},
            headers={
                'Content-Type': 'application/json'},
            status_code=200)

        params_oauth2_client_credentials = {
            'clientId': self.user_name,
            'clientPassword': self.password,
            'tokenEndpoint': self.url}

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
            self.url,
            client.grant.token_endpoint)

        history = self.requests_mock.request_history
        self.assertEqual(1, len(history))

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
            'tokenEndpoint': self.url}

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
class TestBasicAuthSession(test_base.BaseTestCase):

    def setUp(self):
        super(TestBasicAuthSession, self).setUp()
        self.url = 'https://oauth2/tokens'
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
            'https://nfvo.co.jp',
            headers={'Content-Type': 'application/json'},
            status_code=200)

        if http_method == 'GET':
            response = client.get(
                'https://nfvo.co.jp',
                params={
                    'sample_key': 'sample_value'})
        elif http_method == 'PUT':
            response = client.put(
                'https://nfvo.co.jp',
                data={
                    'sample_key': 'sample_value'})
        elif http_method == 'POST':
            response = client.post(
                'https://nfvo.co.jp',
                data={
                    'sample_key': 'sample_value'})
        elif http_method == 'DELETE':
            response = client.delete(
                'https://nfvo.co.jp',
                params={
                    'sample_key': 'sample_value'})
        elif http_method == 'PATCH':
            response = client.patch(
                'https://nfvo.co.jp',
                data={
                    'sample_key': 'sample_value'})

        self.assertEqual(200, response.status_code)
        history = self.requests_mock.request_history
        self.assertEqual(1, len(history))


@ddt.ddt
class TestOAuth2Session(test_base.BaseTestCase):

    class MockThread(threading.Timer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def start(self):
            super().start()
            super().join(60)

    def setUp(self):
        super(TestOAuth2Session, self).setUp()
        self.url = 'https://oauth2/tokens'
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
            self.url, [res_mock, res_mock2])

        grant = auth._ClientCredentialsGrant(
            client_id=self.user_name,
            client_password=self.password,
            token_endpoint=self.url)

        with mock.patch("threading.Timer", side_effect=self.MockThread) as m:
            client = auth._OAuth2Session(grant)
            client.apply_access_token_info()

            history = self.requests_mock.request_history
            self.assertEqual(2, len(history))
            self.assertEqual(1, m.call_count)

    def test_apply_access_token_info_fail_error_response(self):
        error_description = """
        Either your username or password is incorrect
        or you are not an active user.
        Please try again or contact your administrator.
        """
        self.requests_mock.register_uri(
            'GET',
            self.url,
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
            token_endpoint=self.url)

        with mock.patch("threading.Timer", side_effect=self.MockThread) as m:
            try:
                client = auth._OAuth2Session(grant)
                client.apply_access_token_info()
            except requests.exceptions.RequestException as e:
                self.assertEqual(401, e.response.status_code)

            history = self.requests_mock.request_history
            self.assertEqual(1, len(history))
            self.assertEqual(0, m.call_count)

    def test_apply_access_token_info_fail_timeout(self):
        self.requests_mock.register_uri(
            'GET',
            self.url,
            exc=requests.exceptions.ConnectTimeout)

        grant = auth._ClientCredentialsGrant(
            client_id=self.user_name,
            client_password=self.password,
            token_endpoint=self.url)

        with mock.patch("threading.Timer", side_effect=self.MockThread) as m:
            try:
                client = auth._OAuth2Session(grant)
                client.apply_access_token_info()
            except requests.exceptions.RequestException as e:
                self.assertIsNone(e.response)

            history = self.requests_mock.request_history
            self.assertEqual(1, len(history))
            self.assertEqual(0, m.call_count)

    def test_schedule_refrash_token_expaire(self):
        self.requests_mock.register_uri(
            'GET',
            self.url,
            headers={'Content-Type': 'application/json'},
            json={
                'access_token': 'test_token',
                'token_type': 'bearer'},
            status_code=200)

        grant = auth._ClientCredentialsGrant(
            client_id=self.user_name,
            client_password=self.password,
            token_endpoint=self.url)

        with mock.patch("threading.Timer", side_effect=self.MockThread) as m:
            client = auth._OAuth2Session(grant)
            client._OAuth2Session__access_token_info.update({
                'access_token': 'test_token',
                'token_type': 'bearer',
                'expires_in': '1'})
            client.schedule_refrash_token()

            history = self.requests_mock.request_history
            self.assertEqual(1, len(history))
            self.assertEqual(1, m.call_count)

    def test_schedule_refrash_token_non_expaire(self):
        grant = auth._ClientCredentialsGrant(
            client_id=self.user_name,
            client_password=self.password,
            token_endpoint=self.url)

        with mock.patch("threading.Timer", side_effect=self.MockThread) as m:
            client = auth._OAuth2Session(grant)
            client._OAuth2Session__access_token_info.update({
                'access_token': 'test_token',
                'token_type': 'bearer'})
            client.schedule_refrash_token()

            history = self.requests_mock.request_history
            self.assertEqual(0, len(history))
            self.assertEqual(0, m.call_count)

    @ddt.data(None, "")
    def test_schedule_refrash_token_invalid_value(self, invalid_value):
        grant = auth._ClientCredentialsGrant(
            client_id=self.user_name,
            client_password=self.password,
            token_endpoint=self.url)

        with mock.patch("threading.Timer", side_effect=self.MockThread) as m:
            client = auth._OAuth2Session(grant)
            client._OAuth2Session__access_token_info.update({
                'access_token': 'test_token',
                'token_type': 'bearer',
                'expires_in': invalid_value})
            client.schedule_refrash_token()

            history = self.requests_mock.request_history
            self.assertEqual(0, len(history))
            self.assertEqual(0, m.call_count)

    @ddt.data('GET', 'PUT', 'POST', 'DELETE', 'PATCH')
    def test_request_client_credentials(self, http_method):
        self.requests_mock.register_uri('GET',
            self.url,
            json={'access_token': 'test_token3', 'token_type': 'bearer'},
            headers={'Content-Type': 'application/json'},
            status_code=200)

        grant = auth._ClientCredentialsGrant(
            client_id=self.user_name,
            client_password=self.password,
            token_endpoint=self.url)
        client = auth._OAuth2Session(grant)
        client.apply_access_token_info()

        self.requests_mock.register_uri(http_method,
            'https://nfvo.co.jp',
            headers={'Content-Type': 'application/json'},
            status_code=200)

        if http_method == 'GET':
            response = client.get(
                'https://nfvo.co.jp',
                params={
                    'sample_key': 'sample_value'})
        elif http_method == 'PUT':
            response = client.put(
                'https://nfvo.co.jp',
                data={
                    'sample_key': 'sample_value'})
        elif http_method == 'POST':
            response = client.post(
                'https://nfvo.co.jp',
                data={
                    'sample_key': 'sample_value'})
        elif http_method == 'DELETE':
            response = client.delete(
                'https://nfvo.co.jp',
                params={
                    'sample_key': 'sample_value'})
        elif http_method == 'PATCH':
            response = client.patch(
                'https://nfvo.co.jp',
                data={
                    'sample_key': 'sample_value'})

        self.assertEqual(200, response.status_code)
        history = self.requests_mock.request_history
        self.assertEqual(2, len(history))

    def test_request_client_credentials_auth_error(self):
        self.requests_mock.register_uri('GET',
            self.url,
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
            token_endpoint=self.url)
        client = auth._OAuth2Session(grant)
        client.apply_access_token_info()

        response = client.get('https://nfvo.co.jp')

        self.assertEqual(401, response.status_code)
        history = self.requests_mock.request_history
        self.assertEqual(3, len(history))


class TestAuthValidateBearer(unit_base.FixturedTestCase):

    def setUp(self):
        super(TestAuthValidateBearer, self).setUp()
        token_type = 'Bearer'
        api_name = 'dummy'
        token_value = 'SampleAccessToken'
        application_type = vnflcm_router.VnflcmAPIRouter
        self.auth_opts = [cfg.ListOpt('vnflcm_dummy_scope',
                        default='test_api',
                        help="OAuth2.0 api token scope for create")]
        cfg.CONF.register_opts(self.auth_opts, group='authentication')
        self.requests_mock = self.useFixture(requests_mock_fixture.Fixture())
        self.url = 'http://auth/authorize/'
        self.auth_bearer = auth._AuthValidateBearer(
            application_type, api_name, token_type, token_value)
        auth._AuthValidateManager()

    def tearDown(self):
        super(TestAuthValidateBearer, self).tearDown()

    @mock.patch.object(auth._AuthValidateBearer, 'request')
    def test_do_auth_no_response(self, mock_request):
        cfg.CONF.set_override('token_type', 'Bearer',
                              group='authentication')
        mock_request.return_value = None
        self.assertRaises(webob.exc.HTTPUnauthorized, self.auth_bearer.do_auth)

    def test_do_auth_no_token_value_in_response(self):
        cfg.CONF.set_override('token_type', 'Bearer',
                              group='authentication')
        cfg.CONF.set_override('auth_url', 'http://auth/authorize/',
                              group='authentication')
        update = {'access_token': None}
        json = fake_auth.fake_response(**update)
        self.requests_mock.register_uri('GET',
            self.url,
            json=json,
            headers={'Content-Type': 'application/json'},
            status_code=200)
        self.assertRaises(webob.exc.HTTPUnauthorized, self.auth_bearer.do_auth)
        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, 'http://auth')
        self.assertEqual(1, req_count)

    def test_do_auth_no_token_type_in_response(self):
        cfg.CONF.set_override('token_type', 'Bearer',
                              group='authentication')
        cfg.CONF.set_override('auth_url', 'http://auth/authorize/',
                              group='authentication')
        update = {'token_type': None}
        json = fake_auth.fake_response(**update)
        self.requests_mock.register_uri('GET',
            self.url,
            json=json,
            headers={'Content-Type': 'application/json'},
            status_code=200)
        self.assertRaises(webob.exc.HTTPUnauthorized, self.auth_bearer.do_auth)
        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, 'http://auth')
        self.assertEqual(1, req_count)

    def test_do_auth_invalid_token_value(self):
        cfg.CONF.set_override('token_type', 'Bearer',
                              group='authentication')
        cfg.CONF.set_override('auth_url', 'http://auth/authorize/',
                              group='authentication')
        update = {'access_token': 'Test'}
        json = fake_auth.fake_response(**update)
        self.requests_mock.register_uri('GET',
            self.url,
            json=json,
            headers={'Content-Type': 'application/json'},
            status_code=200)
        self.assertRaises(webob.exc.HTTPUnauthorized, self.auth_bearer.do_auth)
        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, 'http://auth')
        self.assertEqual(1, req_count)

    def test_do_auth_invalid_scope(self):
        cfg.CONF.set_override('token_type', 'Bearer',
                              group='authentication')
        cfg.CONF.set_override('auth_url', 'http://auth/authorize/',
                              group='authentication')
        json = fake_auth.fake_response()
        self.requests_mock.register_uri('GET',
            self.url,
            json=json,
            headers={'Content-Type': 'application/json'},
            status_code=200)

        self.assertRaises(webob.exc.HTTPForbidden, self.auth_bearer.do_auth)
        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, 'http://auth')
        self.assertEqual(1, req_count)


class TestAuthValidateBasic(unit_base.FixturedTestCase):
    def setUp(self):
        super(TestAuthValidateBasic, self).setUp()
        self.api_name = 'test'
        self.user_name = 'test_user'
        self.password = 'test_pass'
        self.token_type = 'Basic'
        self.token_value = self._encode_base64(self.user_name + self.password)
        self.auth_basic = auth._AuthValidateBasic(
            self.api_name, self.token_type, self.token_value)
        auth._AuthValidateManager()

    def _encode_base64(self, info):
        encode = base64.b64encode(info.encode())
        return encode

    def test_do_auth(self):
        cfg.CONF.set_override('token_type', 'Basic',
                              group='authentication')
        cfg.CONF.set_override('user_name', self.user_name,
                              group='authentication')
        cfg.CONF.set_override('password', self.password,
                              group='authentication')
        auth._AuthValidateBasic(self.api_name, self.token_type,
        self.token_value)

        self.auth_basic.do_auth()

    def test_do_auth_invalid_token_value(self):
        cfg.CONF.set_override('token_type', 'Basic',
                              group='authentication')
        cfg.CONF.set_override('user_name', 'test',
                              group='authentication')
        cfg.CONF.set_override('password', self.password,
                              group='authentication')
        auth._AuthValidateBasic(
            self.api_name,
            self.token_type,
            self.token_value)

        self.assertRaises(webob.exc.HTTPUnauthorized, self.auth_basic.do_auth)

    def test_do_auth_invalid_token_type(self):
        cfg.CONF.set_override('token_type', 'Basic',
                              group='authentication')
        self.auth_basic = auth._AuthValidateBasic(
            'test', 'test_type', 'test_val')
        self.assertRaises(webob.exc.HTTPUnauthorized, self.auth_basic.do_auth)


@ddt.ddt
class TestAuthValidateManager(unit_base.FixturedTestCase):

    def setUp(self):
        super(TestAuthValidateManager, self).setUp()
        self.auth_validate = auth._AuthValidateManager()

    @ddt.data(vnflcm_router.VnflcmAPIRouter, vnfpkgm_router.VnfpkgmAPIRouter)
    def test_auth_main_bearer(self, obj):
        mock_response = mock.MagicMock()
        mock_response.request = mock.MagicMock()
        mock_response.request.headers = {
            'Authorization': 'Bearer 123456abc'}
        mock_response.application.return_value = obj

        ret = self.auth_validate._get_auth_type(
            mock_response.request, mock_response.application)
        self.assertIsInstance(ret, auth._AuthValidateBearer)

    def test_auth_main_basic(self):
        mock_response = mock.MagicMock()
        mock_response.request = mock.MagicMock()
        mock_response.request.headers = {
            'Authorization': 'Basic 123456abc'}

        mock_response.application = mock.MagicMock()
        mock_response.application.return_value = vnflcm_router.VnflcmAPIRouter

        ret = self.auth_validate._get_auth_type(
            mock_response.request, mock_response.application)
        self.assertIsInstance(ret, auth._AuthValidateBasic)

    def test_auth_main_none(self):
        mock_response = mock.MagicMock()
        mock_response.request = mock.MagicMock()
        mock_response.request.headers = {
            'Authorization': 'Test 123456abc'}
        mock_response.application.return_value = vnflcm_router.VnflcmAPIRouter

        ret = self.auth_validate._get_auth_type(
            mock_response.request, mock_response.application)
        self.assertIsInstance(ret, auth._AuthValidateIgnore)


class TestAuthValidatorExecution(test_base.BaseTestCase):
    def setUp(self):
        super(TestAuthValidatorExecution, self).setUp()

        @webob.dec.wsgify
        def fake_app(req):
            # self.context = req.environ['tacker.context']
            return webob.Response()

        self.context = None
        self.middleware = auth.AuthValidatorExecution(fake_app)
        self.request = webob.Request.blank('/')
        self.request.headers['X_AUTH_TOKEN'] = 'testauthtoken'

    @mock.patch.object(auth.auth_validator_manager, "auth_main")
    def test_called(self, mock_auth_main):
        response = self.request.get_response(self.middleware)
        self.assertEqual('200 OK', response.status)
