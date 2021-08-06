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


import abc

from keystoneauth1 import adapter
from keystoneauth1 import http_basic
from keystoneauth1.identity import v3
from keystoneauth1 import noauth
from keystoneauth1 import plugin
from keystoneauth1 import session
from oslo_log import log as logging
from oslo_serialization import jsonutils

from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.objects import base


LOG = logging.getLogger(__name__)


class HttpClient(object):

    def __init__(self, auth_handle, version=None,
            service_type='nfv-orchestration', connect_retries=None,
            timeout=None):
        self.auth_handle = auth_handle
        self.version = version
        self.service_type = service_type
        # NOTE: these parameters could be used from ex. configuration
        # if a HttpClient user want to use these.
        self.connect_retries = connect_retries
        self.timeout = timeout

    def do_request(self, url, method, context=None, expected_status=[],
                   **kwargs):
        content_type = kwargs.pop('content_type', 'application/json')

        headers = kwargs.setdefault('headers', {})
        headers.setdefault('Accept', content_type)

        body = kwargs.pop('body', None)
        if body is not None:
            if isinstance(body, base.TackerObject):
                body = body.to_dict()
            if isinstance(body, dict):
                body = jsonutils.dumps(body)
            kwargs.setdefault('data', body)
            headers.setdefault('Content-Type', content_type)

        version = kwargs.pop('version', None) or self.version
        if version is not None:
            headers.setdefault('Version', version)

        if self.connect_retries is not None:
            kwargs.setdefault('connect_retries', self.connect_retries)
        if self.timeout is not None:
            kwargs.setdefault('timeout', self.timeout)

        session = self.auth_handle.get_session(
            self.auth_handle.get_auth(context), self.service_type)
        resp = session.request(url, method, raise_exc=False, **kwargs)

        resp_body = self._decode_body(resp)

        if expected_status and resp.status_code not in expected_status:
            self.raise_sol_exception(resp, resp_body)

        return resp, resp_body

    def raise_sol_exception(self, resp, resp_body):
        content_type = resp.headers['Content-Type']
        kwargs = {'sol_status': resp.status_code}
        if content_type == 'application/problem+json':
            kwargs['sol_detail'] = resp_body['detail']
        else:
            kwargs['sol_detail'] = resp.text

        raise sol_ex.SolException(**kwargs)

    def _decode_body(self, resp):
        if resp.status_code == 204:  # no content
            return
        content_type = resp.headers['Content-Type']
        if content_type == 'application/zip':
            return resp.content
        if content_type == 'text/plain':
            return resp.text
        if resp.text:
            return jsonutils.loads(resp.text)
        # otherwise return None


class AuthHandle(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get_auth(self, context=None):
        # returns keystoneauth1 authentication plugin object
        pass

    @abc.abstractmethod
    def get_session(self, auth, service_type):
        # returns keystoneauth1 session object
        pass


class KeystoneTokenAuthHandle(AuthHandle):

    def __init__(self, auth_url, context):
        self.auth_url = auth_url
        self.context = context

    def get_auth(self, context):
        if context is None:
            context = self.context
        return v3.Token(auth_url=self.auth_url,
                        token=context.auth_token,
                        project_id=context.project_id,
                        project_domain_id=context.project_domain_id)

    def get_session(self, auth, service_type):
        _session = session.Session(auth=auth, verify=False)
        return adapter.Adapter(session=_session,
                               service_type=service_type)


class KeystonePasswordAuthHandle(AuthHandle):

    def __init__(self, auth_url, username, password,
            project_name, user_domain_name, project_domain_name):
        self.auth_url = auth_url
        self.username = username
        self.password = password
        self.project_name = project_name
        self.user_domain_name = user_domain_name
        self.project_domain_name = project_domain_name

    def get_auth(self, context=None):
        return v3.Password(auth_url=self.auth_url,
                           username=self.username,
                           password=self.password,
                           project_name=self.project_name,
                           user_domain_name=self.user_domain_name,
                           project_domain_name=self.project_domain_name)

    def get_session(self, auth, service_type):
        _session = session.Session(auth=auth, verify=False)
        return adapter.Adapter(session=_session,
                               service_type=service_type)


class BasicAuthHandle(AuthHandle):

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def get_auth(self, context=None):
        return http_basic.HTTPBasicAuth(username=self.username,
                                        password=self.password)

    def get_session(self, auth, service_type):
        return session.Session(auth=auth, verify=False)


class NoAuthHandle(AuthHandle):

    def __init__(self, endpoint=None):
        self.endpoint = endpoint

    def get_auth(self, context=None):
        return noauth.NoAuth(endpoint=self.endpoint)

    def get_session(self, auth, service_type):
        return session.Session(auth=auth, verify=False)


class Oauth2AuthPlugin(plugin.FixedEndpointPlugin):

    def __init__(self, endpoint, token_endpoint, client_id, client_password):
        super(Oauth2AuthPlugin, self).__init__(endpoint)
        self.token_endpoint = token_endpoint
        self.client_id = client_id
        self.client_password = client_password

    def get_token(self, session, **kwargs):
        auth = BasicAuthHandle(self.client_id,
                               self.client_password)
        client = HttpClient(auth)

        url = self.token_endpoint + '/token'
        data = {'grant_type': 'client_credentials'}

        resp, resp_body = client.do_request(url, "POST",
                data=data, content_type='application/x-www-form-urlencoded')

        if resp.status_code != 200:
            LOG.error("get OAuth2 token failed: %d" % resp.status_code)
            return

        return resp_body['access_token']

    def get_headers(self, session, **kwargs):
        token = self.get_token(session)
        if not token:
            return None
        auth = 'Bearer %s' % token
        return {'Authorization': auth}


class OAuth2AuthHandle(AuthHandle):

    def __init__(self, endpoint, token_endpoint, client_id, client_password):
        self.endpoint = endpoint
        self.token_endpoint = token_endpoint
        self.client_id = client_id
        self.client_password = client_password

    def get_auth(self, context=None):
        return Oauth2AuthPlugin(self.endpoint, self.token_endpoint,
                self.client_id, self.client_password)

    def get_session(self, auth, service_type):
        return session.Session(auth=auth, verify=False)
