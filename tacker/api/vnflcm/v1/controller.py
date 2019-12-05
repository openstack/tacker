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

import six
from six.moves import http_client
import webob

from tacker.api.schemas import vnf_lcm
from tacker.api import validation
from tacker.api.views import vnf_lcm as vnf_lcm_view
from tacker.common import exceptions
from tacker.common import utils
from tacker import objects
from tacker.objects import fields
from tacker.policies import vnf_lcm as vnf_lcm_policies
from tacker import wsgi


class VnfLcmController(wsgi.Controller):

    _view_builder_class = vnf_lcm_view.ViewBuilder

    def _get_vnf_instance_href(self, vnf_instance):
        return '/vnflcm/v1/vnf_instances/%s' % vnf_instance.id

    @wsgi.response(http_client.CREATED)
    @wsgi.expected_errors((http_client.BAD_REQUEST, http_client.FORBIDDEN))
    @validation.schema(vnf_lcm.create)
    def create(self, request, body):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'create')

        req_body = utils.convert_camelcase_to_snakecase(body)
        vnfd_id = req_body.get('vnfd_id')
        try:
            vnfd = objects.VnfPackageVnfd.get_by_id(request.context,
                                                    vnfd_id)
        except exceptions.VnfPackageVnfdNotFound as exc:
            raise webob.exc.HTTPBadRequest(explanation=six.text_type(exc))

        vnf_instance = objects.VnfInstance(
            context=request.context,
            vnf_instance_name=req_body.get('vnf_instance_name'),
            vnf_instance_description=req_body.get(
                'vnf_instance_description'),
            vnfd_id=vnfd_id,
            instantiation_state=fields.VnfInstanceState.NOT_INSTANTIATED,
            vnf_provider=vnfd.vnf_provider,
            vnf_product_name=vnfd.vnf_product_name,
            vnf_software_version=vnfd.vnf_software_version,
            vnfd_version=vnfd.vnfd_version,
            tenant_id=request.context.project_id)

        vnf_instance.create()
        result = self._view_builder.create(vnf_instance)
        headers = {"location": self._get_vnf_instance_href(vnf_instance)}
        return wsgi.ResponseObject(result, headers=headers)

    def show(self, request, id):
        raise webob.exc.HTTPNotImplemented()

    def index(self, request):
        raise webob.exc.HTTPNotImplemented()

    def delete(self, request, id):
        raise webob.exc.HTTPNotImplemented()

    def instantiate(self, request, id, body):
        raise webob.exc.HTTPNotImplemented()

    def terminate(self, request, id, body):
        raise webob.exc.HTTPNotImplemented()

    def heal(self, request, id, body):
        raise webob.exc.HTTPNotImplemented()


def create_resource():
    return wsgi.Resource(VnfLcmController())
