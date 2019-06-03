# Copyright (C) 2019 NTT DATA
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

from tacker import wsgi


class VnfPkgmController(wsgi.Controller):

    def create(self, request, body):
        raise webob.exc.HTTPNotImplemented()

    def show(self, request, id):
        raise webob.exc.HTTPNotImplemented()

    def index(self, request):
        raise webob.exc.HTTPNotImplemented()

    def delete(self, request, id):
        raise webob.exc.HTTPNotImplemented()

    def upload_vnf_package_content(self, request, id, body):
        raise webob.exc.HTTPNotImplemented()

    def upload_vnf_package_from_uri(self, request, id, body):
        raise webob.exc.HTTPNotImplemented()


def create_resource():
    body_deserializers = {
        'application/zip': wsgi.ZipDeserializer()
    }

    deserializer = wsgi.RequestDeserializer(
        body_deserializers=body_deserializers)
    return wsgi.Resource(VnfPkgmController(), deserializer=deserializer)
