#    Copyright 2012 OpenStack Foundation
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

import abc
from oslo_config import cfg
from oslo_log import log as logging
from oslo_middleware import base
import requests
import threading
import webob.dec
import webob.exc

from tacker.common import utils
from tacker import context

LOG = logging.getLogger(__name__)


class TackerKeystoneContext(base.ConfigurableMiddleware):
    """Make a request context from keystone headers."""

    @webob.dec.wsgify
    def __call__(self, req):
        ctx = context.Context.from_environ(req.environ)

        if not ctx.user_id:
            LOG.debug("X_USER_ID is not found in request")
            return webob.exc.HTTPUnauthorized()

        # Inject the context...
        req.environ['tacker.context'] = ctx

        return self.application


class _BearerAuth(requests.auth.AuthBase):
    """Attaches HTTP Bearer Authentication to the given Request object."""

    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["Authorization"] = "Bearer " + self.token
        return r


class _OAuth2GrantBase(metaclass=abc.ABCMeta):
    """Base class that all OAuth2.0 grant type implementations derive from."""

    grant_type = None

    @abc.abstractmethod
    def get_accsess_token(self):
        pass


class _ClientCredentialsGrant(_OAuth2GrantBase):
    """OAuth2.0 grant type ClientCredentials implementation."""

    grant_type = 'client_credentials'

    def __init__(self, token_endpoint, client_id, client_password):
        super(_ClientCredentialsGrant, self).__init__()
        self.token_endpoint = token_endpoint
        self.client_id = client_id
        self.client_password = client_password

    def get_accsess_token(self):
        """Get access token.

        Returns:
            dict: access token response.
        """
        kwargs = {
            'headers': {
                'Connection': 'keep-alive',
                'Content-Type': 'application/x-www-form-urlencoded'},
            'data': {
                'grant_type': self.grant_type},
            'timeout': cfg.CONF.authentication.timeout}

        basic_auth_request = _BasicAuthSession(
            self.client_id, self.client_password)

        LOG.info(
            "Get Access Token, Connecting to <GET:{}>".format(
                self.token_endpoint))
        LOG.info("Request Headers={}".format(kwargs.get('headers')))
        LOG.info("Request Body={}".format(kwargs.get('data')))

        response = basic_auth_request.get(self.token_endpoint, **kwargs)
        response.raise_for_status()

        response_body = response.json()
        LOG.info("[RES] Headers={}".format(response.headers))
        LOG.info("[RES] Body={}".format(response_body))

        return response_body


class _OAuth2Session(requests.Session):
    """Provides OAuth 2.0 authentication."""

    def __init__(self, grant):
        super(_OAuth2Session, self).__init__()
        self.grant = grant
        self.__access_token_info = {}
        self.__lock = threading.RLock()

    def request(self, method, url, **kwargs):
        """Override <requests.Session.request> function."""
        kwargs['auth'] = _BearerAuth(
            self.__access_token_info.get('access_token'))

        response = super().request(method, url, **kwargs)
        if response.status_code == 401:
            LOG.error(
                'Authentication error {}, details={}'.format(
                    response, response.text))
            self.apply_access_token_info()

        return response

    def apply_access_token_info(self):
        """Get access token."""
        try:
            self.__set_access_token_info(self.grant.get_accsess_token())
            self.schedule_refrash_token()
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response:
                LOG.error(
                    "Get Access Token, error details={}".format(
                        e.response.json()))
            LOG.error(e)

    def __set_access_token_info(self, update_dict):
        with self.__lock:
            self.__access_token_info = update_dict

    def schedule_refrash_token(self):
        """expires_in Scheduler registration at expiration."""
        if not ('expires_in' in self.__access_token_info):
            LOG.debug("'expires_in' does not exist in the response body.")
            return

        try:
            expires_in = int(self.__access_token_info.get('expires_in'))
            expires_in_timer = threading.Timer(
                expires_in, self.apply_access_token_info)
            expires_in_timer.start()

            LOG.info(
                "expires_in=<{}> exist, scheduler regist.".format(expires_in))
        except (ValueError, TypeError):
            pass


class _BasicAuthSession(requests.Session):
    """Provide Basic authentication."""

    def __init__(self, user_name, password):
        super(_BasicAuthSession, self).__init__()
        self.user_name = user_name
        self.password = password
        self.auth = requests.auth.HTTPBasicAuth(
            self.user_name, self.password)

    def request(self, method, url, **kwargs):
        """Override <requests.Session.request> function."""
        kwargs['auth'] = self.auth
        return super().request(method, url, **kwargs)


class _AuthManager:

    OPTS = [
        cfg.StrOpt('auth_type',
                default=None,
                choices=['BASIC', 'OAUTH2_CLIENT_CREDENTIALS'],
                help="auth_type used for external connection"),
        cfg.IntOpt('timeout',
                default=20,
                help="timeout used for external connection"),
        cfg.StrOpt('token_endpoint',
                default=None,
                help="token_endpoint used to get the oauth2 token"),
        cfg.StrOpt('client_id',
                   default=None,
                   help="client_id used to get the oauth2 token"),
        cfg.StrOpt('client_password',
                default=None,
                help="client_password used to get the oauth2 token"),
        cfg.StrOpt('user_name',
                default=None,
                help="user_name used in basic authentication"),
        cfg.StrOpt('password',
                default=None,
                help="password used in basic authentication")
    ]
    cfg.CONF.register_opts(OPTS, group='authentication')

    __DEFAULT_CLIENT = requests.Session()

    def __init__(self):
        self.__manages = {}
        self.__lock = threading.RLock()

        # local auth setting.
        self.set_auth_client(
            auth_type=cfg.CONF.authentication.auth_type,
            auth_params={'client_id': cfg.CONF.authentication.client_id,
            'client_password': cfg.CONF.authentication.client_password,
            'token_endpoint': cfg.CONF.authentication.token_endpoint,
            'user_name': cfg.CONF.authentication.user_name,
            'password': cfg.CONF.authentication.password})

    def __empty(self, val):
        if val is None:
            return True
        elif isinstance(val, str):
            return val.strip() == ''

        return len(val) == 0

    def set_auth_client(self, id='local', auth_type=None, auth_params=None):
        """Set up an Auth client.

        Args:
            id (str, optional): Management ID
            auth_type (str, optional): Authentication type.
            auth_params (dict, optional): Authentication information.
        """
        snakecase_auth_params = utils.convert_camelcase_to_snakecase(
            auth_params)
        if self.__empty(auth_type) or self.__empty(snakecase_auth_params):
            return

        if id in self.__manages:
            LOG.debug("Use cache, Auth Managed Id=<{}>".format(id))
            return

        client = self.__DEFAULT_CLIENT
        if auth_type == 'BASIC':
            client = _BasicAuthSession(
                user_name=snakecase_auth_params.get('user_name'),
                password=snakecase_auth_params.get('password'))
        elif (auth_type == 'OAUTH2_CLIENT_CREDENTIALS' and
                not self.__empty(snakecase_auth_params.get('token_endpoint'))):
            grant = _ClientCredentialsGrant(
                client_id=snakecase_auth_params.get('client_id'),
                client_password=snakecase_auth_params.get('client_password'),
                token_endpoint=snakecase_auth_params.get('token_endpoint'))
            client = _OAuth2Session(grant)
            client.apply_access_token_info()

        LOG.info(
            "Add to Auth management, id=<{}>, type=<{}>, class=<{}>".format(
                id, auth_type, client.__class__.__name__))

        self.__add_manages(id, client)

    def __add_manages(self, id, client):
        with self.__lock:
            self.__manages[id] = client

    def get_auth_client(self, id="local"):
        """Get the Auth client.

        Args:
            id (str, optional): Management ID

        Returns:
            based on <requests.Session> class.
        """
        return self.__manages.get(id, self.__DEFAULT_CLIENT)


def pipeline_factory(loader, global_conf, **local_conf):
    """Create a paste pipeline based on the 'auth_strategy' config option."""
    pipeline = local_conf[cfg.CONF.auth_strategy]
    pipeline = pipeline.split()
    filters = [loader.get_filter(n) for n in pipeline[:-1]]
    app = loader.get_app(pipeline[-1])
    filters.reverse()
    for f in filters:
        app = f(app)
    return app


auth_manager = _AuthManager()
