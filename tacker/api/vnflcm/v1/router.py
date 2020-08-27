# Copyright (C) 2020 NTT DATA
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

from oslo_config import cfg
from tacker.api.vnflcm.v1 import controller as vnf_lcm_controller
from tacker import wsgi


class VnflcmAPIRouter(wsgi.Router):
    """Routes requests on the API to the appropriate controller and method."""

    def __init__(self):
        mapper = routes.Mapper()
        super(VnflcmAPIRouter, self).__init__(mapper)

    def _setup_route(self, mapper, url, methods, controller,
                     default_resource):
        all_methods = ['HEAD', 'GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        missing_methods = [m for m in all_methods if m not in methods.keys()]
        allowed_methods_str = ",".join(methods.keys())
        scope_opts = []
        for method, action in methods.items():
            mapper.connect(url,
                           controller=controller,
                           action=action,
                           conditions={'method': [method]})

            add = cfg.ListOpt('vnflcm_' + action + '_scope',
                      default=[],
                      help="OAuth2.0 api token scope for" + action)
            scope_opts.append(add)

        cfg.CONF.register_opts(scope_opts, group='authentication')

        if missing_methods:
            mapper.connect(url,
                           controller=default_resource,
                           action='reject',
                           allowed_methods=allowed_methods_str,
                           conditions={'method': missing_methods})

    def _setup_routes(self, mapper):
        default_resource = wsgi.Resource(wsgi.DefaultMethodController(),
                                         wsgi.RequestDeserializer())

        controller = vnf_lcm_controller.create_resource()

        # Allowed methods on /vnflcm/v1/vnf_instances resource
        methods = {"GET": "index", "POST": "create"}
        self._setup_route(mapper, "/vnf_instances",
                          methods, controller, default_resource)

        # Allowed methods on
        # /vnflcm/v1/vnf_instances/{vnfInstanceId} resource
        methods = {"DELETE": "delete", "GET": "show", "PATCH": "update"}
        self._setup_route(mapper, "/vnf_instances/{id}",
                          methods, controller, default_resource)

        # Allowed methods on
        # /vnflcm/v1/vnf_instances/{vnfInstanceId}/instantiate resource
        methods = {"POST": "instantiate"}
        self._setup_route(mapper,
                "/vnf_instances/{id}/instantiate",
                methods, controller, default_resource)

        # Allowed methods on
        # /vnflcm/v1/vnf_instances/{vnfInstanceId}/heal resource
        methods = {"POST": "heal"}
        self._setup_route(mapper,
                "/vnf_instances/{id}/heal",
                methods, controller, default_resource)

        # Allowed methods on
        # /vnflcm/v1/vnf_lcm_op_occs/{vnfLcmOpOccId} resource
        methods = {"GET": "show_lcm_op_occs"}
        self._setup_route(mapper, "/vnf_lcm_op_occs/{id}",
                          methods, controller, default_resource)

        # Allowed methods on
        # /vnflcm/v1/vnf_instances/{vnfInstanceId}/terminate resource
        methods = {"POST": "terminate"}
        self._setup_route(mapper,
                "/vnf_instances/{id}/terminate",
                methods, controller, default_resource)

        # Allowed methods on
        # /vnflcm/v1/vnf_instances/{vnfInstanceId}/heal resource
        methods = {"POST": "heal"}
        self._setup_route(mapper,
                "/vnf_instances/{id}/heal",
                methods, controller, default_resource)

        # Allowed methods on
        # /vnflcm/v1/vnf_instances/{vnfInstanceId}/scale resource
        methods = {"POST": "scale"}
        self._setup_route(mapper,
                "/vnf_instances/{id}/scale",
                methods, controller, default_resource)

        # Allowed methods on
        # {apiRoot}/vnflcm/v1/vnf_lcm_op_occs/{vnfLcmOpOccId}/rollback resource
        methods = {"POST": "rollback"}
        self._setup_route(mapper,
                "/vnf_lcm_op_occs/{id}/rollback",
                methods, controller, default_resource)

        methods = {"GET": "subscription_list", "POST": "register_subscription"}
        self._setup_route(mapper, "/subscriptions",
                methods, controller, default_resource)

        methods = {"GET": "subscription_show", "DELETE": "delete_subscription"}
        self._setup_route(mapper, "/subscriptions/{subscriptionId}",
                methods, controller, default_resource)
