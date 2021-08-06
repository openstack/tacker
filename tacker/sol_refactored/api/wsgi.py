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

from tacker.common import exceptions as common_ex
from tacker import wsgi

from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex


LOG = logging.getLogger(__name__)


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
            if hdr in kwargs:
                self.headers[hdr] = kwargs[hdr]
        self.headers.setdefault('version', api_version.CURRENT_VERSION)
        self.headers.setdefault('accept-ranges', 'none')

    def serialize(self, request, content_type):
        self.headers.setdefault('content_type', content_type)
        content_type = self.headers['content_type']
        if self.body is None:
            body = None
        elif content_type == 'text/plain':
            body = self.body
        elif content_type == 'application/zip':
            body = self.body
        else:  # 'application/json'
            serializer = wsgi.JSONDictSerializer()
            body = serializer.serialize(self.body)
            if len(body) > config.CONF.v2_vnfm.max_content_length:
                raise sol_ex.ResponseTooBig(
                    size=config.CONF.v2_vnfm.max_content_length)
        response = webob.Response(body=body)
        response.status_int = self.status
        for hdr, val in self.headers.items():
            response.headers[hdr.replace('_', '-')] = val
        return response


class SolErrorResponse(SolResponse):

    def __init__(self, ex, req):
        user_locale = req.best_match_language()
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


class SolResource(wsgi.Application):

    def __init__(self, controller, policy_name=None):
        self.controller = controller
        self.policy_name = policy_name
        self.deserializer = wsgi.RequestDeserializer()

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, request):
        LOG.info("%(method)s %(url)s", {"method": request.method,
                                        "url": request.url})
        try:
            action, args, accept = self.deserializer.deserialize(request)
            self.check_api_version(request)
            self.check_policy(request, action)
            result = self.dispatch(request, action, args)
            response = result.serialize(request, accept)
        except Exception as ex:
            result = SolErrorResponse(ex, request)
            try:
                response = result.serialize(request,
                                            'application/problem+json')
            except Exception:
                LOG.exception("Unknown error")
                return webob.exc.HTTPBadRequest(explanation="Unknown error")

        LOG.info("%(url)s returned with HTTP %(status)d",
                 {"url": request.url, "status": response.status_int})

        return response

    def check_api_version(self, request):
        # check and set api_version
        ver = request.headers.get("Version")
        if ver is None:
            LOG.info("Version missing")
            raise sol_ex.APIVersionMissing()
        request.context.api_version = api_version.APIVersion(ver)

    def check_policy(self, request, action):
        if self.policy_name is None:
            return
        if action == 'reject':
            return
        request.context.can(self.policy_name.format(action))

    def dispatch(self, request, action, action_args):
        controller_method = getattr(self.controller, action)
        return controller_method(request=request, **action_args)


class SolAPIRouter(wsgi.Router):

    controller = None
    route_list = {}

    def __init__(self):
        super(SolAPIRouter, self).__init__(routes.Mapper())

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


class SolAPIController(object):

    def reject(self, request, **kwargs):
        raise sol_ex.MethodNotAllowed(method=request.method)
