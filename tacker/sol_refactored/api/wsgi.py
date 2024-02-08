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

import routes
import webob

import oslo_i18n as i18n
from oslo_log import log as logging
from oslo_serialization import jsonutils

from tacker.common import exceptions as common_ex
from tacker import context

from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.api.policies.vnflcm_v2 import (
    ENHANCED_POLICY_ACTIONS)
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex


LOG = logging.getLogger(__name__)


class SolRequest(webob.Request):

    def best_match_accept(self, content_types):
        offers = self.accept.acceptable_offers(content_types)
        if not offers:
            raise sol_ex.NotAllowedContentType(header=self.accept.header_value)

        return offers[0][0]

    def best_match_language(self):
        if not self.accept_language:
            return None
        all_languages = i18n.get_available_languages('tacker')
        return self.accept_language.best_match(all_languages)

    @property
    def context(self):
        if 'tacker.context' not in self.environ:
            self.environ['tacker.context'] = context.get_admin_context()
        return self.environ['tacker.context']


class SolResponse(object):

    # SOL013 4.2.3 Response header field
    allowed_headers = ['version', 'location', 'content_type',
            'www_authenticate', 'accept_ranges', 'content_range',
            'retry_after', 'link']

    def __init__(self, status, body, **kwargs):
        self.status = status
        self.body = body
        self.headers = {}
        for hdr in self.allowed_headers:
            if kwargs.get(hdr):
                self.headers[hdr] = kwargs[hdr]

    def serialize(self, content_type):
        self.headers.setdefault('content_type', content_type)
        content_type = self.headers['content_type']
        if self.body is None:
            body = None
        elif content_type == 'text/plain':
            body = self.body
        elif content_type == 'application/zip':
            body = self.body
        else:  # 'application/json'
            body = jsonutils.dump_as_bytes(self.body)
            if len(body) > config.CONF.v2_vnfm.max_content_length:
                raise sol_ex.ResponseTooBig(
                    size=config.CONF.v2_vnfm.max_content_length)
        response = webob.Response(body=body)
        response.status_int = self.status
        for hdr, val in self.headers.items():
            response.headers[hdr.replace('_', '-')] = val
        return response


class SolErrorResponse(SolResponse):

    def __init__(self, ex, user_locale):
        problem_details = {}
        if isinstance(ex, sol_ex.SolException):
            problem_details = ex.make_problem_details()
            # translate detail
            detail = i18n.translate(problem_details['detail'], user_locale)
            problem_details['detail'] = detail
        elif isinstance(ex, (common_ex.TackerException,
                             webob.exc.HTTPException)):
            LOG.warning("legacy Exception used. Use SolException instead.")
            problem_details['status'] = ex.code
            problem_details['detail'] = str(ex)
        else:
            # program bug. it occurs only under development.
            LOG.exception("Unknown error")
            problem_details['status'] = 500
            problem_details['detail'] = str(ex)

        super(SolErrorResponse, self).__init__(problem_details['status'],
                                               problem_details)


class SolResource(object):

    def __init__(self, controller, policy_name=None):
        self.controller = controller
        self.policy_name = policy_name

    @webob.dec.wsgify(RequestClass=SolRequest)
    def __call__(self, request):
        LOG.info("%(method)s %(url)s", {"method": request.method,
                                        "url": request.url})
        try:
            action, args, accept = self._deserialize_request(request)
            self._check_api_version(request, action)
            self._check_policy(request, action)
            result = self._dispatch(request, action, args)
            self.controller.set_default_to_response(result, action)
            response = result.serialize(accept)
        except Exception as ex:
            result = SolErrorResponse(ex, request.best_match_language())
            self.controller.set_default_to_response(result, action)
            try:
                response = result.serialize('application/problem+json')
            except Exception:
                LOG.exception("Unknown error")
                return webob.exc.HTTPBadRequest(explanation="Unknown error")

        LOG.info("%(url)s returned with HTTP %(status)d",
                 {"url": request.url, "status": response.status_int})

        return response

    def _check_api_version(self, request, action):
        # check and set api_version
        ver = request.headers.get("Version")
        request.context.api_version = api_version.APIVersion(
            ver, self.controller.supported_api_versions(action))

    def _check_policy(self, request, action):
        if self.policy_name is None:
            return
        if action == 'reject':
            return
        if not (self.policy_name.format(action) in ENHANCED_POLICY_ACTIONS
                and config.CONF.oslo_policy.enhanced_tacker_policy):
            request.context.can(self.policy_name.format(action))

    def _dispatch(self, request, action, action_args):
        controller_method = getattr(self.controller, action)
        return controller_method(request=request, **action_args)

    def _deserialize_request(self, request):
        action_args = request.environ['wsgiorg.routing_args'][1].copy()
        action = action_args.pop('action', None)
        action_args.pop('controller', None)

        body = self._deserialize_body(request, action)
        if body is not None:
            action_args.update({'body': body})

        accept = request.best_match_accept(
            self.controller.allowed_accept(action))

        return (action, action_args, accept)

    def _deserialize_body(self, request, action):
        if request.method not in ('POST', 'PATCH', 'PUT'):
            return

        if not request.body:
            LOG.debug("Empty body provided in request")
            return

        content_type = request.content_type
        allowed_content_types = self.controller.allowed_content_types(action)
        if not content_type:
            content_type = allowed_content_types[0]
        elif content_type not in allowed_content_types:
            raise sol_ex.NotSupportedContentType(header=content_type)

        if content_type == 'application/zip':
            return request.body_file
        else:
            # assume json format
            # ex. 'application/json', 'application/merge-patch+json'
            try:
                return request.json
            except Exception:
                raise sol_ex.MalformedRequestBody()


class SolAPIRouter(object):
    """WSGI middleware that maps incoming requests to WSGI apps."""

    controller = None
    route_list = {}

    @classmethod
    def factory(cls, global_config, **local_config):
        """Return an instance of the WSGI Router class."""
        return cls()

    def __init__(self):
        mapper = routes.Mapper()
        self._setup_routes(mapper)
        self._router = routes.middleware.RoutesMiddleware(self._dispatch,
                                                          mapper)

    @webob.dec.wsgify
    def __call__(self, req):
        return self._router

    def _setup_routes(self, mapper):
        for path, methods in self.route_list:
            self._setup_route(mapper, path, methods)

    def _setup_route(self, mapper, path, methods):

        for method, action in methods.items():
            mapper.connect(path,
                           controller=self.controller,
                           action=action,
                           conditions={'method': [method]})

        all_methods = ['HEAD', 'GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        missing_methods = [m for m in all_methods if m not in methods]
        if missing_methods:
            mapper.connect(path,
                           controller=self.controller,
                           action='reject',
                           conditions={'method': missing_methods})

    @staticmethod
    @webob.dec.wsgify(RequestClass=SolRequest)
    def _dispatch(req):
        """Dispatch a Request.

        Called by self._router after matching the incoming request to a route
        and putting the information into req.environ. Either returns 404
        or the routed WSGI app's response.
        """
        match = req.environ['wsgiorg.routing_args'][1]
        if not match:
            language = req.best_match_language()
            msg = 'The resource could not be found.'
            msg = i18n.translate(msg, language)
            return webob.exc.HTTPNotFound(explanation=msg)
        app = match['controller']
        return app


class SolAPIController(object):

    def reject(self, request, **kwargs):
        raise sol_ex.MethodNotAllowed(method=request.method)

    def supported_api_versions(self, action):
        # NOTE: if a contorller supports versions header, override
        # this method in the subclass. return None means version is
        # not checked.
        return None

    def allowed_content_types(self, action):
        # NOTE: if other than 'application/json' is expected depending
        # on action, override this method in the subclass.
        # NOTE: 'text/plain' is allowed for backward compatibility.
        # the body is assumed as json.
        return ['application/json', 'text/plain']

    def allowed_accept(self, action):
        # NOTE: if other than 'application/json' is expected depending
        # on action, override this method in the subclass.
        return ['application/json']

    def set_default_to_response(self, result, action):
        pass
