# Copyright (C) 2023 Fujitsu
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
import copy
import os
from unittest import mock
import uuid

from oslo_config import cfg
from requests_mock.contrib import fixture as rm_fixture

from keystoneauth1 import exceptions as ksa_exceptions

from tacker.common.exceptions import TackerException
from tacker import context
from tacker.tests.unit import base

JWT_KEY_FILE = 'jwt_private.key'


def _get_sample_key(name):
    filename = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "./sample_keys/", name)
    with open(filename, "r") as f:
        content = f.read()
    return content


def get_mock_conf_effect(audience=None, token_endpoint=None,
                    auth_method=None, client_id=None, client_secret=None,
                    scope=None, jwt_key_file=None, jwt_algorithm=None,
                    jwt_bearer_time_out=None, certfile=None, keyfile=None,
                    cafile=None, http_connect_timeout=None, insecure=None):
    def mock_conf_key_effect(name):
        if name == 'keystone_authtoken':
            return MockConfig(conf=None)
        elif name == 'ext_oauth2_auth':
            config = {'use_ext_oauth2_auth': True}
            if audience:
                config['audience'] = audience
            if token_endpoint:
                config['token_endpoint'] = token_endpoint
            if auth_method:
                config['auth_method'] = auth_method
            if client_id:
                config['client_id'] = client_id
            if client_secret:
                config['client_secret'] = client_secret
            if scope:
                config['scope'] = scope
            if jwt_key_file:
                config['jwt_key_file'] = jwt_key_file
            if jwt_algorithm:
                config['jwt_algorithm'] = jwt_algorithm
            if jwt_bearer_time_out:
                config['jwt_bearer_time_out'] = jwt_bearer_time_out
            if certfile:
                config['certfile'] = certfile
            if keyfile:
                config['keyfile'] = keyfile
            if cafile:
                config['cafile'] = cafile
            if cafile:
                config['http_connect_timeout'] = http_connect_timeout
            if cafile:
                config['insecure'] = insecure
            return MockConfig(
                conf=config)
        else:
            return cfg.CONF._get(name)
    return mock_conf_key_effect


class MockConfig(object):
    def __init__(self, conf=None):
        self.conf = conf

    def __getattr__(self, name):
        if not self.conf or name not in self.conf:
            raise cfg.NoSuchOptError(f'not found {name}')
        return self.conf.get(name)

    def __contains__(self, key):
        return key in self.conf


class MockSession(object):
    def __init__(self, ):
        self.auth = None


class TestExtOAuth2Auth(base.TestCase):

    def setUp(self):
        super(TestExtOAuth2Auth, self).setUp()
        self.requests_mock = self.useFixture(rm_fixture.Fixture())
        self.token_endpoint = 'http://demo/token_endpoint'
        self.auth_method = 'client_secret_post'
        self.client_id = 'test_client_id'
        self.client_secret = 'test_client_secret'
        self.scope = 'tacker_api'
        self.access_token = f'access_token_{str(uuid.uuid4())}'
        self.audience = 'http://demo/audience'
        self.jwt_bearer_time_out = 2800
        self.addCleanup(mock.patch.stopall)

    def _get_access_token_response(self, request, context,
                                   auth_method=None,
                                   client_id=None,
                                   client_secret=None,
                                   scope=None,
                                   access_token=None,
                                   status_code=200,
                                   raise_error=None,
                                   resp=None
                                   ):
        if raise_error:
            raise raise_error
        if auth_method == 'tls_client_auth':
            body = (f'client_id={client_id}&scope={scope}'
                    f'&grant_type=client_credentials')
            self.assertEqual(request.text, body)
        elif auth_method == 'client_secret_post':
            body = (f'client_id={client_id}&client_secret={client_secret}'
                    f'&scope={scope}&grant_type=client_credentials')
            self.assertEqual(request.text, body)
        elif auth_method == 'client_secret_basic':
            body = f'scope={scope}&grant_type=client_credentials'
            self.assertEqual(request.text, body)
            auth_basic = request._request.headers.get('Authorization')
            self.assertIsNotNone(auth_basic)

            auth = 'Basic ' + base64.standard_b64encode(
                f'{client_id}:{client_secret}'.encode('ascii')).decode('ascii')
            self.assertEqual(auth_basic, auth)
        elif auth_method == 'private_key_jwt':
            self.assertIn(f'client_id={client_id}', request.text)
            self.assertIn(('client_assertion_type=urn%3Aietf%3Aparams%3A'
                           'oauth%3Aclient-assertion-type%3Ajwt-bearer'),
                          request.text)
            self.assertIn('client_assertion=', request.text)
            self.assertIn(f'scope={scope}', request.text)
            self.assertIn('grant_type=client_credentials', request.text)
        elif auth_method == 'client_secret_jwt':
            self.assertIn(f'client_id={client_id}', request.text)
            self.assertIn(('client_assertion_type=urn%3Aietf%3Aparams%3A'
                           'oauth%3Aclient-assertion-type%3Ajwt-bearer'),
                          request.text)
            self.assertIn('client_assertion=', request.text)
            self.assertIn(f'scope={scope}', request.text)
            self.assertIn('grant_type=client_credentials', request.text)
        if not access_token:
            access_token = f'access_token{str(uuid.uuid4())}'
        if not resp:
            if status_code == 200:
                response = {
                    'access_token': access_token,
                    'expires_in': 1800,
                    'refresh_expires_in': 0,
                    'token_type': 'Bearer',
                    'not-before-policy': 0,
                    'scope': scope
                }
            else:
                response = {'error': 'error_title',
                            'error_description': 'error message'}
        else:
            response = copy.deepcopy(resp)
        context.status_code = status_code
        return response

    def _get_default_mock_conf_effect(self):
        return get_mock_conf_effect(
            token_endpoint=self.token_endpoint,
            auth_method=self.auth_method,
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope=self.scope)

    def _check_authorization_header(self):
        auth_context = context.generate_tacker_service_context()
        session = auth_context.create_session()
        headers = auth_context.get_headers(session)
        bearer = f'Bearer {self.access_token}'
        self.assertIn('Authorization', headers)
        self.assertEqual(bearer, headers.get('Authorization'))
        return auth_context

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_init_without_token_endpoint(self, mock_get_conf_key):
        mock_get_conf_key.side_effect = get_mock_conf_effect(
            token_endpoint='',
            auth_method=self.auth_method,
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope=self.scope
        )
        self.assertRaises(TackerException,
                          context.generate_tacker_service_context)

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_init_without_scope(self, mock_get_conf_key):
        mock_get_conf_key.side_effect = get_mock_conf_effect(
            token_endpoint=self.token_endpoint,
            auth_method=self.auth_method,
            client_id=self.client_id,
            client_secret=self.client_secret)
        self.assertRaises(TackerException,
                          context.generate_tacker_service_context)

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_init_without_keystone_middleware_opts(self, mock_get_conf_key):
        mock_get_conf_key.side_effect = get_mock_conf_effect(
            token_endpoint=self.token_endpoint,
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope=self.scope)
        self.assertRaises(TackerException,
                          context.generate_tacker_service_context)

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    @mock.patch('keystoneauth1.loading.session.Session.load_from_options')
    def test_create_session(self, mock_load_from_options, mock_get_conf_key):
        certfile = f'/demo/certfile{str(uuid.uuid4())}'
        keyfile = f'/demo/keyfile{str(uuid.uuid4())}'
        cafile = f'/demo/cafile{str(uuid.uuid4())}'
        conf_insecure = True
        http_connect_timeout = 1000

        def load_side_effect(**kwargs):
            self.assertEqual(conf_insecure, kwargs.get('insecure'))
            self.assertEqual(cafile, kwargs.get('cacert'))
            self.assertEqual(certfile, kwargs.get('cert'))
            self.assertEqual(keyfile, kwargs.get('key'))
            self.assertEqual(http_connect_timeout, kwargs.get('timeout'))
            return MockSession()
        mock_load_from_options.side_effect = load_side_effect
        mock_get_conf_key.side_effect = get_mock_conf_effect(
            token_endpoint=self.token_endpoint,
            auth_method='tls_client_auth',
            client_id=self.client_id,
            scope=self.scope,
            certfile=certfile,
            keyfile=keyfile,
            cafile=cafile,
            insecure=conf_insecure,
            http_connect_timeout=http_connect_timeout)
        auth_context = context.generate_tacker_service_context()
        auth_context.create_session()

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_get_connection_params(self, mock_get_conf_key):
        mock_get_conf_key.side_effect = self._get_default_mock_conf_effect()
        auth_context = context.generate_tacker_service_context()
        session = auth_context.create_session()
        params = auth_context.get_connection_params(session)
        self.assertDictEqual(params, {})

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_get_headers_tls_client_auth(self, mock_get_conf_key):
        def mock_resp(request, context):
            return self._get_access_token_response(
                request, context,
                auth_method='tls_client_auth',
                client_id=self.client_id,
                scope=self.scope,
                access_token=self.access_token)
        self.requests_mock.post(self.token_endpoint, json=mock_resp)
        mock_get_conf_key.side_effect = get_mock_conf_effect(
            token_endpoint=self.token_endpoint,
            auth_method='tls_client_auth',
            client_id=self.client_id,
            scope=self.scope)
        auth_context = self._check_authorization_header()
        result = auth_context.invalidate()
        self.assertEqual(True, result)
        self.assertIsNone(auth_context.access_token)

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_get_headers_client_secret_post(self, mock_get_conf_key):
        def mock_resp(request, context):
            return self._get_access_token_response(
                request, context,
                auth_method='client_secret_post',
                client_id=self.client_id,
                client_secret=self.client_secret,
                scope=self.scope,
                access_token=self.access_token
            )
        self.requests_mock.post(self.token_endpoint, json=mock_resp)
        mock_get_conf_key.side_effect = get_mock_conf_effect(
            token_endpoint=self.token_endpoint,
            auth_method='client_secret_post',
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope=self.scope)
        self._check_authorization_header()

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_get_headers_client_secret_basic(self, mock_get_conf_key):
        def mock_resp(request, context):
            return self._get_access_token_response(
                request, context,
                auth_method='client_secret_basic',
                client_id=self.client_id,
                client_secret=self.client_secret,
                scope=self.scope,
                access_token=self.access_token)
        self.requests_mock.post(self.token_endpoint, json=mock_resp)
        mock_get_conf_key.side_effect = get_mock_conf_effect(
            token_endpoint=self.token_endpoint,
            auth_method='client_secret_basic',
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope=self.scope)
        self._check_authorization_header()

    @mock.patch('builtins.open', mock.mock_open(read_data=_get_sample_key(
        JWT_KEY_FILE)))
    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_get_headers_private_key_jwt(self, mock_get_conf_key):
        def mock_resp(request, context):
            return self._get_access_token_response(
                request, context,
                auth_method='private_key_jwt',
                client_id=self.client_id,
                scope=self.scope,
                access_token=self.access_token)
        self.requests_mock.post(self.token_endpoint, json=mock_resp)
        mock_get_conf_key.side_effect = get_mock_conf_effect(
            token_endpoint=self.token_endpoint,
            auth_method='private_key_jwt',
            client_id=self.client_id,
            audience=self.audience,
            jwt_key_file=f'/demo/jwt_key_file{str(uuid.uuid4())}',
            jwt_algorithm='RS256',
            jwt_bearer_time_out=self.jwt_bearer_time_out,
            scope=self.scope)
        self._check_authorization_header()

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_get_headers_client_secret_jwt(self, mock_get_conf_key):
        def mock_resp(request, context):
            return self._get_access_token_response(
                request, context,
                auth_method='client_secret_jwt',
                client_id=self.client_id,
                client_secret=self.client_secret,
                scope=self.scope,
                access_token=self.access_token)
        self.requests_mock.post(self.token_endpoint, json=mock_resp)
        mock_get_conf_key.side_effect = get_mock_conf_effect(
            token_endpoint=self.token_endpoint,
            auth_method='client_secret_jwt',
            client_id=self.client_id,
            audience=self.audience,
            client_secret=self.client_secret,
            jwt_algorithm='HS256',
            jwt_bearer_time_out=self.jwt_bearer_time_out,
            scope=self.scope)
        self._check_authorization_header()

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_get_headers_invalid_auth_method(self, mock_get_conf_key):
        mock_get_conf_key.side_effect = get_mock_conf_effect(
            token_endpoint=self.token_endpoint,
            auth_method='client_secret_other',
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope=self.scope
        )
        auth_context = context.generate_tacker_service_context()
        session = auth_context.create_session()
        self.assertRaises(TackerException, auth_context.get_headers, session)

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_get_headers_connect_fail(self, mock_get_conf_key):
        def mock_resp(request, context):
            return self._get_access_token_response(
                request, context,
                auth_method=self.auth_method,
                client_id=self.client_id,
                client_secret=self.client_secret,
                scope=self.scope,
                access_token=self.access_token,
                raise_error=ksa_exceptions.RequestTimeout('connect time out.'))
        self.requests_mock.post(self.token_endpoint, json=mock_resp)
        mock_get_conf_key.side_effect = self._get_default_mock_conf_effect()
        auth_context = context.generate_tacker_service_context()
        session = auth_context.create_session()
        self.assertRaises(TackerException, auth_context.get_headers, session)

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_get_headers_is_not_200(self, mock_get_conf_key):
        def mock_resp(request, context):
            return self._get_access_token_response(
                request, context,
                auth_method=self.auth_method,
                client_id=self.client_id,
                client_secret=self.client_secret,
                scope=self.scope,
                access_token=self.access_token,
                status_code=201)
        self.requests_mock.post(self.token_endpoint, json=mock_resp)
        mock_get_conf_key.side_effect = self._get_default_mock_conf_effect()
        auth_context = context.generate_tacker_service_context()
        session = auth_context.create_session()
        self.assertRaises(TackerException, auth_context.get_headers, session)

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_get_headers_not_include_access_token(self, mock_get_conf_key):
        def mock_resp(request, context):
            return self._get_access_token_response(
                request, context,
                auth_method=self.auth_method,
                client_id=self.client_id,
                client_secret=self.client_secret,
                scope=self.scope,
                access_token=self.access_token,
                status_code=200,
                resp={'error': 'invalid_client',
                      'error_description': 'The client is not found.'})
        self.requests_mock.post(self.token_endpoint, json=mock_resp)
        mock_get_conf_key.side_effect = self._get_default_mock_conf_effect()
        auth_context = context.generate_tacker_service_context()
        session = auth_context.create_session()
        self.assertRaises(TackerException, auth_context.get_headers, session)

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_get_headers_unknown_error(self, mock_get_conf_key):
        def mock_resp(request, context):
            return self._get_access_token_response(
                request, context,
                auth_method=self.auth_method,
                client_id=self.client_id,
                client_secret=self.client_secret,
                scope=self.scope,
                access_token=self.access_token,
                raise_error=Exception('unknown error occurred.'))
        self.requests_mock.post(self.token_endpoint, json=mock_resp)
        mock_get_conf_key.side_effect = self._get_default_mock_conf_effect()
        auth_context = context.generate_tacker_service_context()
        session = auth_context.create_session()
        self.assertRaises(TackerException, auth_context.get_headers, session)
