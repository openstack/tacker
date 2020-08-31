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
import base64
from oslo_config import cfg
from oslo_log import log as logging
from oslo_middleware import base
import requests
from tacker.api.vnflcm.v1 import router as vnflcm_router
from tacker.api.vnfpkgm.v1 import router as vnfpkgm_router
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


class _AuthBase(metaclass=abc.ABCMeta):

    def __init__(self, api_name, token_type, token_value):
        self.api_name = api_name
        self.token_type = token_type
        self.token_value = token_value

    @abc.abstractmethod
    def do_auth(self):
        pass

    def _check_token_type(self):
        if self.token_type == cfg.CONF.authentication.token_type:
            return

        msg = ("Auth Scheme is not expected token_type: expect={%s},\
        actual={%s}" % (cfg.CONF.authentication.token_type, self.token_type))
        raise webob.exc.HTTPUnauthorized(msg)


class _AuthValidateIgnore(_AuthBase):
    def __init__(self, api_name, token_type, token_value):
        super().__init__(api_name, token_type, token_value)

    def do_auth(self):
        conf_auth_type = cfg.CONF.authentication.token_type
        if (conf_auth_type is not None and self.token_type is None):
            msg = ("Request header is None but tacker conf\
                has auth information.")
            raise webob.exc.HTTPUnauthorized(msg)

        return None


class _AuthValidateBearer(_AuthBase):

    def __init__(self, application_type, api_name, token_type, token_value):
        super().__init__(api_name, token_type, token_value)
        self.application_type = application_type
        self.expires_in = 0
        self.res_access_token = None
        self.__access_token_info = {}

    def request(self):
        auth_url = cfg.CONF.authentication.auth_url
        response = requests.Session().get(auth_url)
        if response.status_code == 401:
            return None

        return response

    def do_auth(self):
        self._check_token_type()

        if self.res_access_token is None:

            response = self.request()

            if response is None:
                msg = "No responce from Authorization Server."
                raise webob.exc.HTTPUnauthorized(msg)

            response_body = response.json()

            if (response_body.get('access_token') is None or
                    response_body.get('token_type') is None):
                msg = "No access_token or token_type exist."
                raise webob.exc.HTTPUnauthorized(msg)

            if self.token_value != response_body.get('access_token'):
                msg = "access_token is invalid."
                raise webob.exc.HTTPUnauthorized(msg)

            self.expires_in = response_body.get('expires_in')
            self.res_access_token = response_body.get('access_token')

            self._validate_scope(response_body.get('scope'))

            self._scheduler_delete_token(response_body)

    def _scheduler_delete_token(self, response_body):
        if not (response_body.get('expires_in')):
            LOG.debug("'expires_in' does not exist in the response body.")
            return

        try:
            expires_in = int(response_body.get('expires_in'))
            expires_in_timer = threading.Timer(
                expires_in, self._delete_access_token)
            expires_in_timer.start()

            LOG.info(
                "expires_in=<{}> exist, scheduler regist.".format(expires_in))
        except (ValueError, TypeError):
            pass

    def _delete_access_token(self):
        self.access_token = None
        self.expires_in = 0

    def _generate_api_scope_name(self):
        if self.application_type == vnflcm_router.VnflcmAPIRouter:
            scope_prefix = 'vnflcm_'
            return scope_prefix + self.api_name
        elif self.application_type == vnfpkgm_router.VnfpkgmAPIRouter:
            scope_prefix = 'vnfpkgm_'
            return scope_prefix + self.api_name

        return ''

    def _validate_scope(self, res_scope):
        if res_scope is None:
            return

        try:
            api_scope_name = self._generate_api_scope_name() + '_scope'
            scopes = cfg.CONF.authentication.__getitem__(api_scope_name)
        except Exception:
            msg = ("Getting scope error."
                  "api_scope_name={%s}, scopes={%s}",
                  api_scope_name, scopes)
            raise webob.exc.HTTPUnauthorized(msg)

        if len(scopes) == 0:
            return

        if res_scope in scopes:
            return

        raise webob.exc.HTTPForbidden("scope is undefined in tacker.conf")


class _AuthValidateBasic(_AuthBase):

    def __init__(self, api_name, token_type, token_value):
        super().__init__(api_name, token_type, token_value)

    def do_auth(self):
        self._check_token_type()

        base = cfg.CONF.authentication.user_name +\
            cfg.CONF.authentication.password
        base64_encode = base64.b64encode(base.encode())
        if self.token_value != base64_encode:
            msg = "access_token and encoded base64 are not same."
            raise webob.exc.HTTPUnauthorized(msg)


class _AuthValidateManager:

    atuh_opts = [
        cfg.StrOpt('token_type',
                default=None,
                choices=['Bearer', 'Basic'],
                help="authentication type"),
        cfg.StrOpt('user_name',
                default=None,
                help="user_name used in basic authentication"),
        cfg.StrOpt('password',
                default=None,
                help="password used in basic authentication"),
        cfg.StrOpt('auth_url',
                default=None,
                help="URL of the authorization server")
    ]
    cfg.CONF.register_opts(atuh_opts, group='authentication')

    def __init__(self):
        self.__manages = {}
        self.__lock = threading.RLock()

    def __add_manages(self, token_value, auth_obj):
        with self.__lock:
            self.__manages[token_value] = auth_obj

    def _parse_request_header(self, request):
        auth_req = request.headers.get('Authorization')
        if auth_req is None:
            return (None, None)

        auth_req_arry = auth_req.split(' ')
        if len(auth_req_arry) > 3:
            msg = "Invalid Authorization header."
            raise webob.exc.HTTPUnauthorized(msg)
        return (auth_req_arry[0], auth_req_arry[1])

    def _get_auth_type(self, request, application):
        token_type, token_value = self._parse_request_header(request)

        if token_value in self.__manages:
            return self.__manages.get(token_value)

        match = application.map.match(request.path_info)
        api_name = match[0].get("action")

        if token_type == 'Bearer':
            auth_obj = _AuthValidateBearer(
                type(application), api_name, token_type, token_value)
            self.__add_manages(token_value, auth_obj)
            return auth_obj
        elif token_type == 'Basic':
            auth_obj = _AuthValidateBasic(api_name, token_type, token_value)
            self.__add_manages(token_value, auth_obj)
            return auth_obj

        return _AuthValidateIgnore(api_name, token_type, token_value)

    def auth_main(self, request, application):
        auth_validator = self._get_auth_type(request, application)
        if auth_validator:
            auth_validator.do_auth()


class AuthValidatorExecution(base.ConfigurableMiddleware):

    @ webob.dec.wsgify
    def __call__(self, req):
        auth_validator_manager.auth_main(req, self.application)
        return self.application


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
auth_validator_manager = _AuthValidateManager()
