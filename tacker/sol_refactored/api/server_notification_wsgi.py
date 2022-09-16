# Copyright (C) 2022 Fujitsu
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

import webob

from oslo_log import log as logging
from tacker.sol_refactored.api import wsgi as sol_wsgi

LOG = logging.getLogger(__name__)


class ServerNotificationResponse(sol_wsgi.SolResponse):
    allowed_headers = ['content_type']

    def __init__(self, status, body, **kwargs):
        self.status = status
        self.body = body
        self.headers = {}
        for hdr in self.allowed_headers:
            if hdr in kwargs:
                self.headers[hdr] = kwargs[hdr]


class ServerNotificationErrorResponse(ServerNotificationResponse):
    def __init__(self, ex, _):
        status = ex.status if hasattr(ex, 'status') else 'error'
        detail = ex.status if hasattr(ex, 'detail') else 'error'
        problem_details = {'status': status, 'detail': detail}
        if hasattr(ex, 'title'):
            problem_details['title'] = ex.title

        super(ServerNotificationErrorResponse, self).__init__(
            problem_details['status'], problem_details)


class ServerNotificationResource(sol_wsgi.SolResource):
    def __init__(self, controller, policy_name=None):
        super(ServerNotificationResource, self).__init__(
            controller, policy_name=policy_name
        )

    @webob.dec.wsgify(RequestClass=sol_wsgi.SolRequest)
    def __call__(self, request):
        LOG.info("%(method)s %(url)s", {"method": request.method,
                                        "url": request.url})
        try:
            action, args, accept = self._deserialize_request(request)
            self._check_policy(request, action)
            result = self._dispatch(request, action, args)
            response = result.serialize(accept)
        except Exception as ex:
            result = ServerNotificationErrorResponse(ex, request)
            try:
                response = result.serialize('application/problem+json')
            except Exception:
                LOG.exception("Unknown error")
                return webob.exc.HTTPBadRequest(explanation="Unknown error")

        LOG.info("%(url)s returned with HTTP %(status)d",
                 {"url": request.url, "status": response.status_int})

        return response


class ServerNotificationAPIRouter(sol_wsgi.SolAPIRouter):
    pass


class ServerNotificationAPIController(sol_wsgi.SolAPIController):
    pass
