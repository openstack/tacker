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

from oslo_utils import uuidutils

import six
from six.moves import http_client
import webob

from tacker.api.schemas import vnf_lcm
from tacker.api import validation
from tacker.api.views import vnf_lcm as vnf_lcm_view
from tacker.common import exceptions
from tacker.common import utils
from tacker.conductor.conductorrpc import vnf_lcm_rpc
from tacker.extensions import nfvo
from tacker import objects
from tacker.objects import fields
from tacker.policies import vnf_lcm as vnf_lcm_policies
from tacker.vnfm import vim_client
from tacker import wsgi


def check_vnf_state(action, instantiation_state=None, task_state=(None,)):
    """Decorator to check vnf states are valid for particular action.

    If the vnf is in the wrong state, it will raise conflict exception.
    """

    if instantiation_state is not None and not \
            isinstance(instantiation_state, set):
        instantiation_state = set(instantiation_state)
    if task_state is not None and not isinstance(task_state, set):
        task_state = set(task_state)

    def outer(f):
        @six.wraps(f)
        def inner(self, context, vnf_instance, *args, **kw):
            if instantiation_state is not None and \
                    vnf_instance.instantiation_state not in \
                    instantiation_state:
                raise exceptions.VnfInstanceConflictState(
                    attr='instantiation_state',
                    uuid=vnf_instance.id,
                    state=vnf_instance.instantiation_state,
                    action=action)
            if (task_state is not None and
                    vnf_instance.task_state not in task_state):
                raise exceptions.VnfInstanceConflictState(
                    attr='task_state',
                    uuid=vnf_instance.id,
                    state=vnf_instance.task_state,
                    action=action)
            return f(self, context, vnf_instance, *args, **kw)
        return inner
    return outer


class VnfLcmController(wsgi.Controller):

    _view_builder_class = vnf_lcm_view.ViewBuilder

    def __init__(self):
        super(VnfLcmController, self).__init__()
        self.rpc_api = vnf_lcm_rpc.VNFLcmRPCAPI()

    def _get_vnf_instance_href(self, vnf_instance):
        return '/vnflcm/v1/vnf_instances/%s' % vnf_instance.id

    def _get_vnf_instance(self, context, id):
        # check if id is of type uuid format
        if not uuidutils.is_uuid_like(id):
            msg = _("Can not find requested vnf instance: %s") % id
            raise webob.exc.HTTPNotFound(explanation=msg)

        try:
            vnf_instance = objects.VnfInstance.get_by_id(context, id)
        except exceptions.VnfInstanceNotFound:
            msg = _("Can not find requested vnf instance: %s") % id
            raise webob.exc.HTTPNotFound(explanation=msg)

        return vnf_instance

    def _validate_flavour_and_inst_level(self, context, req_body,
                                         vnf_instance):
        inst_levels = {}
        flavour_list = []
        vnf_package_vnfd = objects.VnfPackageVnfd.get_by_id(
            context, vnf_instance.vnfd_id)
        vnf_package = objects.VnfPackage.get_by_id(
            context, vnf_package_vnfd.package_uuid)
        deployment_flavour = vnf_package.vnf_deployment_flavours
        for dep_flavour in deployment_flavour.objects:
            flavour_list.append(dep_flavour.flavour_id)
            if dep_flavour.instantiation_levels:
                inst_levels.update({
                    dep_flavour.flavour_id: dep_flavour.instantiation_levels})

        if req_body['flavour_id'] not in flavour_list:
            raise exceptions.FlavourNotFound(flavour_id=req_body['flavour_id'])

        req_inst_level_id = req_body.get('instantiation_level_id')
        if req_inst_level_id is None:
            return

        if not inst_levels:
            raise exceptions.InstantiationLevelNotFound(
                inst_level_id=req_inst_level_id)

        for flavour, inst_level in inst_levels.items():
            if flavour != req_body['flavour_id']:
                continue

            if req_inst_level_id in inst_level.get('levels').keys():
                # Found instantiation level
                return

        raise exceptions.InstantiationLevelNotFound(
            inst_level_id=req_body['instantiation_level_id'])

    def _validate_vim_connection(self, context, instantiate_vnf_request):
        if instantiate_vnf_request.vim_connection_info:
            vim_id = instantiate_vnf_request.vim_connection_info[0].vim_id
            access_info = \
                instantiate_vnf_request.vim_connection_info[0].access_info
            if access_info:
                region_name = access_info.get('region')
            else:
                region_name = None
        else:
            vim_id = None
            region_name = None

        vim_client_obj = vim_client.VimClient()

        try:
            vim_client_obj.get_vim(
                context, vim_id, region_name=region_name)
        except nfvo.VimDefaultNotDefined as exp:
            raise webob.exc.HTTPBadRequest(explanation=exp.message)
        except nfvo.VimNotFoundException:
            msg = _("VimConnection id is not found: %s")\
                % vim_id
            raise webob.exc.HTTPBadRequest(explanation=msg)
        except nfvo.VimRegionNotFoundException:
            msg = _("Region not found for the VimConnection: %s")\
                % vim_id
            raise webob.exc.HTTPBadRequest(explanation=msg)

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

    @wsgi.response(http_client.OK)
    @wsgi.expected_errors((http_client.FORBIDDEN, http_client.NOT_FOUND))
    def show(self, request, id):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'show')

        vnf_instance = self._get_vnf_instance(context, id)

        return self._view_builder.show(vnf_instance)

    @wsgi.response(http_client.OK)
    @wsgi.expected_errors((http_client.FORBIDDEN))
    def index(self, request):
        context = request.environ['tacker.context']
        vnf_instances = objects.VnfInstanceList.get_all(context)
        return self._view_builder.index(vnf_instances)

    @check_vnf_state(action="delete",
        instantiation_state=[fields.VnfInstanceState.NOT_INSTANTIATED],
        task_state=[None])
    def _delete(self, context, vnf_instance):
        vnf_instance.destroy(context)

    @wsgi.response(http_client.NO_CONTENT)
    @wsgi.expected_errors((http_client.FORBIDDEN, http_client.NOT_FOUND,
                           http_client.CONFLICT))
    def delete(self, request, id):
        context = request.environ['tacker.context']

        vnf_instance = self._get_vnf_instance(context, id)
        self._delete(context, vnf_instance)

    @check_vnf_state(action="instantiate",
        instantiation_state=[fields.VnfInstanceState.NOT_INSTANTIATED],
        task_state=[None])
    def _instantiate(self, context, vnf_instance, request_body):
        req_body = utils.convert_camelcase_to_snakecase(request_body)

        try:
            self._validate_flavour_and_inst_level(context, req_body,
                                                  vnf_instance)
        except exceptions.NotFound as ex:
            raise webob.exc.HTTPBadRequest(explanation=six.text_type(ex))

        instantiate_vnf_request = \
            objects.InstantiateVnfRequest.obj_from_primitive(
                req_body, context=context)

        # validate the vim connection id passed through request is exist or not
        self._validate_vim_connection(context, instantiate_vnf_request)

        vnf_instance.task_state = fields.VnfInstanceTaskState.INSTANTIATING
        vnf_instance.save()

        self.rpc_api.instantiate(context, vnf_instance,
                                 instantiate_vnf_request)

    @wsgi.response(http_client.ACCEPTED)
    @wsgi.expected_errors((http_client.FORBIDDEN, http_client.NOT_FOUND,
                           http_client.CONFLICT, http_client.BAD_REQUEST))
    @validation.schema(vnf_lcm.instantiate)
    def instantiate(self, request, id, body):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'instantiate')

        vnf_instance = self._get_vnf_instance(context, id)

        self._instantiate(context, vnf_instance, body)

    @check_vnf_state(action="terminate",
        instantiation_state=[fields.VnfInstanceState.INSTANTIATED],
        task_state=[None])
    def _terminate(self, context, vnf_instance, request_body):
        req_body = utils.convert_camelcase_to_snakecase(request_body)
        terminate_vnf_req = \
            objects.TerminateVnfRequest.obj_from_primitive(
                req_body, context=context)

        vnf_instance.task_state = fields.VnfInstanceTaskState.TERMINATING
        vnf_instance.save()
        self.rpc_api.terminate(context, vnf_instance, terminate_vnf_req)

    @wsgi.response(http_client.ACCEPTED)
    @wsgi.expected_errors((http_client.BAD_REQUEST, http_client.FORBIDDEN,
                           http_client.NOT_FOUND, http_client.CONFLICT))
    @validation.schema(vnf_lcm.terminate)
    def terminate(self, request, id, body):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'terminate')

        vnf_instance = self._get_vnf_instance(context, id)
        self._terminate(context, vnf_instance, body)

    @check_vnf_state(action="heal",
        instantiation_state=[fields.VnfInstanceState.INSTANTIATED],
        task_state=[None])
    def _heal(self, context, vnf_instance, request_body):
        req_body = utils.convert_camelcase_to_snakecase(request_body)
        heal_vnf_request = objects.HealVnfRequest(context=context, **req_body)
        inst_vnf_info = vnf_instance.instantiated_vnf_info
        vnfc_resource_info_ids = [vnfc_resource_info.id for
            vnfc_resource_info in inst_vnf_info.vnfc_resource_info]

        for vnfc_id in heal_vnf_request.vnfc_instance_id:
            # check if vnfc_id exists in vnfc_resource_info
            if vnfc_id not in vnfc_resource_info_ids:
                msg = _("Vnfc id %(vnfc_id)s not present in vnf instance "
                        "%(id)s")
                raise webob.exc.HTTPBadRequest(
                    explanation=msg % {"vnfc_id": vnfc_id,
                                       "id": vnf_instance.id})

        vnf_instance.task_state = fields.VnfInstanceTaskState.HEALING
        vnf_instance.save()

        self.rpc_api.heal(context, vnf_instance, heal_vnf_request)

    @wsgi.response(http_client.ACCEPTED)
    @wsgi.expected_errors((http_client.BAD_REQUEST, http_client.FORBIDDEN,
                           http_client.NOT_FOUND, http_client.CONFLICT))
    @validation.schema(vnf_lcm.heal)
    def heal(self, request, id, body):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'heal')

        vnf_instance = self._get_vnf_instance(context, id)
        self._heal(context, vnf_instance, body)


def create_resource():
    return wsgi.Resource(VnfLcmController())
