# Copyright (c) 2019 OpenStack Foundation
#
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
from tacker.api.vnfpkgm.v1 import controller as vnf_pkgm_controller
from tacker import wsgi


class VnfpkgmAPIRouter(wsgi.Router):
    """Routes requests on the API to the appropriate controller and method."""

    def __init__(self):
        mapper = routes.Mapper()
        super(VnfpkgmAPIRouter, self).__init__(mapper)

    def _setup_route(self, mapper, url, methods, controller, default_resource):
        all_methods = ['HEAD', 'GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        missing_methods = [m for m in all_methods if m not in methods]
        allowed_methods_str = ",".join(methods.keys())
        scope_opts = []
        for method, action in methods.items():
            mapper.connect(url,
                controller=controller,
                action=action,
                conditions={'method': [method]})

            add = cfg.ListOpt('vnfpkgm_'
            + action + '_scope',
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

        controller = vnf_pkgm_controller.create_resource()

        # Allowed methods on /vnf_packages resource
        methods = {"GET": "index", "POST": "create"}
        self._setup_route(mapper, "/vnf_packages",
                methods, controller, default_resource)

        # Allowed methods on /vnf_packages/{id} resource
        methods = {"DELETE": "delete", "GET": "show",
                   "PATCH": "patch"}
        self._setup_route(mapper, "/vnf_packages/{id}",
                methods, controller, default_resource)

        # Allowed methods on /vnf_packages/{id}/package_content resource
        methods = {"PUT": "upload_vnf_package_content",
                   "GET": "fetch_vnf_package_content"}
        self._setup_route(mapper, "/vnf_packages/{id}/package_content",
                methods, controller, default_resource)

        # Allowed methods on
        # /vnf_packages/{id}/package_content/upload_from_uri resource
        methods = {"POST": "upload_vnf_package_from_uri"}
        self._setup_route(mapper,
                "/vnf_packages/{id}/package_content/upload_from_uri",
                methods, controller, default_resource)

        # Allowed methods on /vnf_packages/{id}/vnfd
        methods = {"GET": "get_vnf_package_vnfd"}
        self._setup_route(mapper,
                          "/vnf_packages/{id}/vnfd",
                          methods, controller, default_resource)

        # Allowed methods on /vnf_packages/{id}/artifacts/{artifact_path}
        methods = {"GET": "fetch_vnf_package_artifacts"}
        self._setup_route(mapper,
                          "/vnf_packages/{id}/artifacts/"
                          "{artifact_path:.*?/*.*?}",
                          methods, controller, default_resource)
