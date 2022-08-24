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

from oslo_log import log as logging
from tacker.sol_refactored.api import wsgi as sol_wsgi
import webob

LOG = logging.getLogger(__name__)


class PrometheusPluginResponse(sol_wsgi.SolResponse):
    allowed_headers = ['content_type']

    def __init__(self, status, body, **kwargs):
        self.status = status
        self.body = body
        self.headers = {}
        for hdr in self.allowed_headers:
            if hdr in kwargs:
                self.headers[hdr] = kwargs[hdr]


class PrometheusPluginErrorResponse(sol_wsgi.SolErrorResponse):
    pass


class PrometheusPluginResource(sol_wsgi.SolResource):
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
            result = PrometheusPluginErrorResponse(ex, request)
            try:
                response = result.serialize('application/problem+json')
            except Exception:
                LOG.exception("Unknown error")
                return webob.exc.HTTPBadRequest(explanation="Unknown error")

        LOG.info("%(url)s returned with HTTP %(status)d",
                 {"url": request.url, "status": response.status_int})

        return response


class PrometheusPluginAPIRouter(sol_wsgi.SolAPIRouter):
    pass


class PrometheusPluginAPIController(sol_wsgi.SolAPIController):
    pass
