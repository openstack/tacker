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
"""
Auth for External Server OAuth2.0 authentication
"""
import time
import uuid

import jwt.utils
from oslo_config import cfg
from oslo_log import log as logging
import requests.auth

from keystoneauth1 import exceptions as ksa_exceptions
from keystoneauth1.loading import session as session_loading

from tacker._i18n import _
from tacker.common.exceptions import TackerException

LOG = logging.getLogger(__name__)
_EXT_AUTH_CONFIG_GROUP_NAME = 'ext_oauth2_auth'
_EXTERNAL_AUTH2_OPTS = [
    cfg.BoolOpt('use_ext_oauth2_auth', default=False,
                help='Set True to use external Oauth2.0 auth server.'),
    cfg.StrOpt('token_endpoint',
               help='The endpoint for access token API.'),
    cfg.StrOpt('scope',
               help='The scope that the access token can access.'),
]
_EXTERNAL_AUTH2_KEYSTONE_MIDDLEWARE_OPTS = [
    cfg.StrOpt('certfile',
               help='Required if identity server requires client '
                    'certificate.'),
    cfg.StrOpt('keyfile',
               help='Required if identity server requires client '
                    'private key.'),
    cfg.StrOpt('cafile',
               help='A PEM encoded Certificate Authority to use when '
                    'verifying HTTPs connections. Defaults to system CAs.'),
    cfg.BoolOpt('insecure', default=False, help='Verify HTTPS connections.'),
    cfg.IntOpt('http_connect_timeout',
               help='Request timeout value for communicating with Identity '
                    'API server.'),
    cfg.StrOpt('audience',
               help='The Audience should be the URL of the Authorization '
                    "Server's Token Endpoint. The Authorization Server will "
                    'verify that it is an intended audience for the token.'),
    cfg.StrOpt('auth_method',
               default='client_secret_basic',
               choices=('client_secret_basic', 'client_secret_post',
                        'tls_client_auth', 'private_key_jwt',
                        'client_secret_jwt'),
               help='The auth_method must use the authentication method '
                    'specified by the Authorization Server.'),
    cfg.StrOpt('client_id',
               help='The OAuth 2.0 Client Identifier valid at the '
                    'Authorization Server.'),
    cfg.StrOpt('client_secret',
               help='The OAuth 2.0 client secret. When the auth_method is '
                    'client_secret_basic, client_secret_post, or '
                    'client_secret_jwt, the value is used, and otherwise the '
                    'value is ignored.'),
    cfg.StrOpt('jwt_key_file',
               help='The jwt_key_file must use the certificate key file which '
                    'has been registered with the Authorization Server. '
                    'When the auth_method is private_key_jwt, the value is '
                    'used, and otherwise the value is ignored.'),
    cfg.StrOpt('jwt_algorithm',
               help='The jwt_algorithm must use the algorithm specified by '
                    'the Authorization Server. When the auth_method is '
                    'client_secret_jwt, this value is often set to HS256,'
                    'when the auth_method is private_key_jwt, the value is '
                    'often set to RS256, and otherwise the value is ignored.'),
    cfg.IntOpt('jwt_bearer_time_out', default=3600,
               help='This value is used to calculate the expiration time. If '
                    'after the expiration time, the access token cannot be '
                    'accepted. When the auth_method is client_secret_jwt or '
                    'private_key_jwt, the value is used, and otherwise the '
                    'value is ignored.'),
]


def config_opts():
    return [(_EXT_AUTH_CONFIG_GROUP_NAME,
             _EXTERNAL_AUTH2_OPTS + _EXTERNAL_AUTH2_KEYSTONE_MIDDLEWARE_OPTS)]


cfg.CONF.register_opts(_EXTERNAL_AUTH2_OPTS,
                       group=_EXT_AUTH_CONFIG_GROUP_NAME)


class ExtOAuth2Auth(object):
    """Construct an Auth to fetch an access token for HTTP access."""

    def __init__(self):
        self._conf = cfg.CONF.ext_oauth2_auth
        # Check whether the configuration parameter has been registered
        if 'auth_method' not in self._conf:
            LOG.debug('The relevant config parameters are not registered '
                      'and need to be registered before they can be used.')
            cfg.CONF.register_opts(_EXTERNAL_AUTH2_KEYSTONE_MIDDLEWARE_OPTS,
                                   group=_EXT_AUTH_CONFIG_GROUP_NAME)
        self.token_endpoint = self._get_config_option(
            'token_endpoint', is_required=True)
        self.auth_method = self._get_config_option(
            'auth_method', is_required=True)
        self.client_id = self._get_config_option(
            'client_id', is_required=True)
        self.scope = self._get_config_option(
            'scope', is_required=True)
        self.access_token = None

    def _get_config_option(self, key, is_required):
        """Read the value from config file by the config key."""
        try:
            value = getattr(self._conf, key)
        except cfg.NoSuchOptError:
            value = None
        if not value:
            if is_required:
                LOG.error('The value is required for option %s '
                          'in group [%s]' % (key,
                                             _EXT_AUTH_CONFIG_GROUP_NAME))
                raise TackerException(
                    _('Configuration error. The parameter '
                      'is not set for "%s" in group [%s].') % (
                        key, _EXT_AUTH_CONFIG_GROUP_NAME))
            else:
                return None
        else:
            return value

    def create_session(self, **kwargs):
        """Create session for HTTP access."""
        kwargs.setdefault('cert', self._get_config_option(
            'certfile', is_required=False))
        kwargs.setdefault('key', self._get_config_option(
            'keyfile', is_required=False))
        kwargs.setdefault('cacert', self._get_config_option(
            'cafile', is_required=False))
        kwargs.setdefault('insecure', self._get_config_option(
            'insecure', is_required=False))
        kwargs.setdefault('timeout', self._get_config_option(
            'http_connect_timeout', is_required=False))
        kwargs.setdefault('user_agent', 'tacker service')
        sess = session_loading.Session().load_from_options(**kwargs)
        sess.auth = self
        return sess

    def get_connection_params(self, session, **kwargs):
        """Get connection params for HTTP access."""
        return {}

    def invalidate(self):
        """Invalidate the current authentication data."""
        self.access_token = None
        return True

    def _get_token_by_client_secret_basic(self, session):
        """Access the access token API.

        Access the access token API to get an access token by
        the auth method 'client_secret_basic'.
        """
        para = {
            'scope': self.scope,
            'grant_type': 'client_credentials'
        }
        auth = requests.auth.HTTPBasicAuth(
            self.client_id, self._get_config_option(
                'client_secret', is_required=True))
        http_response = session.request(
            self.token_endpoint,
            'POST',
            authenticated=False,
            data=para,
            requests_auth=auth)
        return http_response

    def _get_token_by_client_secret_post(self, session):
        """Access the access token API.

        Access the access token API to get an access token by
        the auth method 'client_secret_post'.
        """
        para = {
            'client_id': self.client_id,
            'client_secret': self._get_config_option(
                'client_secret', is_required=True),
            'scope': self.scope,
            'grant_type': 'client_credentials'
        }
        http_response = session.request(
            self.token_endpoint,
            'POST',
            authenticated=False,
            data=para)
        return http_response

    def _get_token_by_tls_client_auth(self, session):
        """Access the access token API.

        Access the access token API to get an access token by
        the auth method 'tls_client_auth'.
        """
        para = {
            'client_id': self.client_id,
            'scope': self.scope,
            'grant_type': 'client_credentials'
        }
        http_response = session.request(
            self.token_endpoint,
            'POST',
            authenticated=False,
            data=para)
        return http_response

    def _get_token_by_private_key_jwt(self, session):
        """Access the access token API.

        Access the access token API to get an access token by
        the auth method 'private_key_jwt'.
        """
        jwt_key_file = self._get_config_option(
            'jwt_key_file', is_required=True)
        with open(jwt_key_file, 'r') as jwt_file:
            jwt_key = jwt_file.read()
        ita = round(time.time())
        exp = ita + self._get_config_option(
            'jwt_bearer_time_out', is_required=True)
        alg = self._get_config_option('jwt_algorithm', is_required=True)
        client_assertion = jwt.encode(
            payload={
                'jti': str(uuid.uuid4()),
                'iat': str(ita),
                'exp': str(exp),
                'iss': self.client_id,
                'sub': self.client_id,
                'aud': self._get_config_option('audience', is_required=True)},
            headers={
                'typ': 'JWT',
                'alg': alg},
            key=jwt_key,
            algorithm=alg)
        para = {
            'client_id': self.client_id,
            'client_assertion_type':
                'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
            'client_assertion': client_assertion,
            'scope': self.scope,
            'grant_type': 'client_credentials'
        }
        http_response = session.request(
            self.token_endpoint,
            'POST',
            authenticated=False,
            data=para)
        return http_response

    def _get_token_by_client_secret_jwt(self, session):
        """Access the access token API.

        Access the access token API to get an access token by
        the auth method 'client_secret_jwt'.
        """
        ita = round(time.time())
        exp = ita + self._get_config_option(
            'jwt_bearer_time_out', is_required=True)
        alg = self._get_config_option('jwt_algorithm', is_required=True)
        client_secret = self._get_config_option(
            'client_secret', is_required=True)
        client_assertion = jwt.encode(
            payload={
                'jti': str(uuid.uuid4()),
                'iat': str(ita),
                'exp': str(exp),
                'iss': self.client_id,
                'sub': self.client_id,
                'aud': self._get_config_option('audience', is_required=True)},
            headers={
                'typ': 'JWT',
                'alg': alg},
            key=client_secret,
            algorithm=alg)

        para = {
            'client_id': self.client_id,
            'client_secret': client_secret,
            'client_assertion_type':
                'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
            'client_assertion': client_assertion,
            'scope': self.scope,
            'grant_type': 'client_credentials'
        }
        http_response = session.request(
            self.token_endpoint,
            'POST',
            authenticated=False,
            data=para)
        return http_response

    def get_headers(self, session, **kwargs):
        """Get an access token and add to request header for HTTP access."""
        if not self.access_token:
            try:
                if self.auth_method == 'tls_client_auth':
                    http_response = self._get_token_by_tls_client_auth(session)
                elif self.auth_method == 'client_secret_post':
                    http_response = self._get_token_by_client_secret_post(
                        session)
                elif self.auth_method == 'client_secret_basic':
                    http_response = self._get_token_by_client_secret_basic(
                        session)
                elif self.auth_method == 'private_key_jwt':
                    http_response = self._get_token_by_private_key_jwt(
                        session)
                elif self.auth_method == 'client_secret_jwt':
                    http_response = self._get_token_by_client_secret_jwt(
                        session)
                else:
                    LOG.error('The value is incorrect for option '
                              'auth_method in group [%s]' %
                              _EXT_AUTH_CONFIG_GROUP_NAME)
                    raise TackerException(
                        _('The configuration parameter for '
                          'key "auth_method" in group [%s] is incorrect.') %
                        _EXT_AUTH_CONFIG_GROUP_NAME)
                LOG.debug(http_response.text)
                if http_response.status_code != 200:
                    LOG.error('The OAuth2.0 access token API returns an '
                              'incorrect response. '
                              'response_status: %s, response_text: %s' %
                              (http_response.status_code,
                               http_response.text))
                    raise TackerException(_('Failed to get an access token.'))

                access_token = http_response.json().get('access_token')
                if not access_token:
                    LOG.error('Failed to get an access token: %s',
                              http_response.text)
                    raise TackerException(_('Failed to get an access token.'))
                self.access_token = access_token
            except (ksa_exceptions.ConnectFailure,
                    ksa_exceptions.DiscoveryFailure,
                    ksa_exceptions.RequestTimeout) as error:
                LOG.error('Unable to get an access token: %s', error)
                raise TackerException(
                    _('The OAuth2.0 access token API service is '
                      'temporarily unavailable.'))
            except TackerException:
                raise
            except Exception as error:
                LOG.error('Unable to get an access token: %s', error)
                raise TackerException(
                    _('An exception occurred during the processing '
                      'of getting an access token'))
        header = {'Authorization': f'Bearer {self.access_token}'}
        return header
