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

import datetime
import requests
import six
import tacker.conf
import webob

from oslo_db.exception import DBDuplicateEntry
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import encodeutils
from oslo_utils import excutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
from sqlalchemy import exc as sqlexc

import ast
import functools
import json
import re
import traceback

from six.moves import http_client
from six.moves.urllib import parse

from tacker._i18n import _
from tacker.api.schemas import vnf_lcm
from tacker.api import validation
from tacker.api.views import vnf_lcm as vnf_lcm_view
from tacker.api.vnflcm.v1 import sync_resource
from tacker.common import exceptions
from tacker.common import utils
from tacker.conductor.conductorrpc import vnf_lcm_rpc
from tacker.db.vnfm import vnfm_db
from tacker.extensions import nfvo
from tacker.extensions import vnfm
from tacker import manager
from tacker import objects
from tacker.objects import fields
from tacker.objects import vnf_lcm_subscriptions as subscription_obj
from tacker.plugins.common import constants
from tacker.policies import vnf_lcm as vnf_lcm_policies
import tacker.vnfm.nfvo_client as nfvo_client
from tacker.vnfm import vim_client
from tacker import wsgi


CONF = tacker.conf.CONF

LOG = logging.getLogger(__name__)


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
        @functools.wraps(f)
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


def check_vnf_status(action, status=None):
    """Decorator to check vnf status are valid for particular action.

    If the vnf is in the wrong state, it will raise conflict exception.
    """

    if status is not None and not isinstance(status, set):
        status = set(status)

    def outer(f):
        @functools.wraps(f)
        def inner(self, context, vnf_instance, vnf, *args, **kw):
            if status is not None and \
                    vnf['status'] not in \
                    status:
                raise exceptions.VnfConflictState(
                    attr='status',
                    uuid=vnf['id'],
                    state=vnf['status'],
                    action=action)
            return f(self, context, vnf_instance, vnf, *args, **kw)
        return inner
    return outer


class VnfLcmController(wsgi.Controller):

    notification_type_list = ['VnfLcmOperationOccurrenceNotification',
                          'VnfIdentifierCreationNotification',
                          'VnfIdentifierDeletionNotification']
    operation_type_list = ['INSTANTIATE',
                       'SCALE',
                       'SCALE_TO_LEVEL',
                       'CHANGE_FLAVOUR',
                       'TERMINATE',
                       'HEAL',
                       'OPERATE',
                       'CHANGE_EXT_CONN',
                       'MODIFY_INFO']
    operation_state_list = ['STARTING',
                        'PROCESSING',
                        'COMPLETED',
                        'FAILED_TEMP',
                        'FAILED',
                        'ROLLING_BACK',
                        'ROLLED_BACK']

    _view_builder_class = vnf_lcm_view.ViewBuilder

    def __init__(self):
        super(VnfLcmController, self).__init__()
        self.rpc_api = vnf_lcm_rpc.VNFLcmRPCAPI()
        self._vnfm_plugin = manager.TackerManager.get_service_plugins()['VNFM']

    def _get_vnf_instance_href(self, vnf_instance):
        return '/vnflcm/v1/vnf_instances/%s' % vnf_instance.id

    def _get_vnf_lcm_op_occs_href(self, vnf_lcm_op_occs_id):
        return '/vnflcm/v1/vnf_lcm_op_occs/%s' % vnf_lcm_op_occs_id

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

    def _get_vnf(self, context, id):
        # check if id is of type uuid format
        if not uuidutils.is_uuid_like(id):
            msg = _("Can not find requested vnf: %s") % id
            raise webob.exc.HTTPNotFound(explanation=msg)

        try:
            vnf = self._vnfm_plugin.get_vnf(context, id)
        except vnfm.VNFNotFound:
            msg = _("Can not find requested vnf: %s") % id
            raise webob.exc.HTTPNotFound(explanation=msg)
        except Exception as exc:
            msg = _("Encountered error while fetching vnf: %s") % id
            LOG.debug("{}: {}".format(msg, six.text_type(exc)))
            raise webob.exc.HTTPInternalServerError(explanation=six.
                                                    text_type(exc))
        return vnf

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

    def _notification_process(self, context, vnf_instance,
                              lcm_operation, request, is_auto=False):
        vnf_lcm_op_occs_id = uuidutils.generate_uuid()
        error_point = 0
        if lcm_operation == fields.LcmOccsOperationType.HEAL:
            request_dict = {
                'vnfc_instance_id': request.vnfc_instance_id,
                'cause': request.cause
            }
            operation_params = str(request_dict)
        else:
            # lcm is instantiation by default
            operation_params = str(request.additional_params)
        try:
            # call create lcm op occs here
            LOG.debug('Create LCM OP OCCS')
            vnf_lcm_op_occs = objects.VnfLcmOpOcc(
                context=context,
                id=vnf_lcm_op_occs_id,
                operation_state=fields.LcmOccsOperationState.STARTING,
                start_time=timeutils.utcnow(),
                state_entered_time=timeutils.utcnow(),
                vnf_instance_id=vnf_instance.id,
                is_cancel_pending=is_auto,
                operation=lcm_operation,
                is_automatic_invocation=is_auto,
                operation_params=operation_params,
                error_point=error_point)
            vnf_lcm_op_occs.create()
        except Exception:
            msg = _("Failed to create LCM occurrence")
            raise webob.exc.HTTPInternalServerError(explanation=msg)

        vnf_lcm_url = self._get_vnf_lcm_op_occs_href(vnf_lcm_op_occs_id)
        notification = {
            'notificationType':
                fields.LcmOccsNotificationType.VNF_OP_OCC_NOTIFICATION,
            'notificationStatus': fields.LcmOccsNotificationStatus.START,
            'operationState': fields.LcmOccsOperationState.STARTING,
            'vnfInstanceId': vnf_instance.id,
            'operation': lcm_operation,
            'isAutomaticInvocation': is_auto,
            'vnfLcmOpOccId': vnf_lcm_op_occs_id,
            '_links': {
                'vnfInstance': {
                    'href': self._get_vnf_instance_href(vnf_instance)},
                'vnfLcmOpOcc': {
                    'href': vnf_lcm_url}}}

        # call send notification
        try:
            self.rpc_api.send_notification(context, notification)
        except Exception as ex:
            LOG.error(
                "Encoutered problem sending notification {}".format(
                    encodeutils.exception_to_unicode(ex)))

        return vnf_lcm_op_occs_id

    def _create_vnf(self, context, vnf_instance, default_vim, attributes=None):
        tenant_id = vnf_instance.tenant_id
        vnfd_id = vnf_instance.vnfd_id
        name = vnf_instance.vnf_instance_name
        description = vnf_instance.vnf_instance_description
        vnf_id = vnf_instance.id
        vim_id = default_vim.get('vim_id')
        placement_attr = default_vim.get('placement_attr', {})

        try:
            with context.session.begin(subtransactions=True):
                vnf_db = vnfm_db.VNF(id=vnf_id,
                             tenant_id=tenant_id,
                             name=name,
                             description=description,
                             instance_id=None,
                             vnfd_id=vnfd_id,
                             vim_id=vim_id,
                             placement_attr=placement_attr,
                             status=constants.INACTIVE,
                             error_reason=None,
                             deleted_at=datetime.min)
                context.session.add(vnf_db)
                for key, value in attributes.items():
                    arg = vnfm_db.VNFAttribute(
                        id=uuidutils.generate_uuid(), vnf_id=vnf_id,
                        key=key, value=str(value))
                    context.session.add(arg)
        except DBDuplicateEntry as e:
            raise exceptions.DuplicateEntity(
                _type="vnf",
                entry=e.columns)

    def _destroy_vnf(self, context, vnf_instance):
        with context.session.begin(subtransactions=True):
            if vnf_instance.id:
                now = timeutils.utcnow()
                updated_values = {'deleted_at': now, 'status':
                    'PENDING_DELETE'}
                context.session.query(vnfm_db.VNFAttribute).filter_by(
                    vnf_id=vnf_instance.id).delete()
                context.session.query(vnfm_db.VNF).filter_by(
                    id=vnf_instance.id).update(updated_values)

    def _update_package_usage_state(self, context, vnf_package):
        """Update vnf package usage state to IN_USE/NOT_IN_USE

        If vnf package is not used by any of the vnf instances, it's usage
        state should be set to NOT_IN_USE otherwise it should be set to
        IN_USE.
        """
        result = vnf_package.is_package_in_use(context)
        if result:
            vnf_package.usage_state = fields.PackageUsageStateType.IN_USE
        else:
            vnf_package.usage_state = fields.PackageUsageStateType.NOT_IN_USE

        vnf_package.save()

    @wsgi.response(http_client.CREATED)
    @wsgi.expected_errors((http_client.BAD_REQUEST, http_client.FORBIDDEN))
    @validation.schema(vnf_lcm.create)
    def create(self, request, body):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'create')
        try:
            req_body = utils.convert_camelcase_to_snakecase(body)
            vnfd_id = req_body.get('vnfd_id')
            vnfd = objects.VnfPackageVnfd.get_by_id(request.context,
                                                    vnfd_id)
        except exceptions.VnfPackageVnfdNotFound:
            vnf_package_info = self._find_vnf_package_info('vnfdId',
                vnfd_id)
            if not vnf_package_info:
                msg = (
                    _("Can not find requested to NFVO, \
                        vnf package info: vnfdId=[%s]") %
                    vnfd_id)
                return self._make_problem_detail(
                    msg, 404, title='Not Found')

            vnfd = sync_resource.SyncVnfPackage.create_package(
                context,
                vnf_package_info)
            if not vnfd:
                msg = (
                    _("Can not find requested to NFVO, \
                        vnf package vnfd: %s") %
                    vnfd_id)
                return self._make_problem_detail(
                    msg, 500, 'Internal Server Error')
        try:
            # get default vim information
            vim_client_obj = vim_client.VimClient()
            default_vim = vim_client_obj.get_vim(context)

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
                tenant_id=request.context.project_id,
                vnf_metadata=req_body.get('metadata'))

            try:
                vnf_instance.create()

                # create entry to 'vnf' table and 'vnf_attribute' table
                attributes = {'placement_attr': default_vim.
                    get('placement_attr', {})}
                self._create_vnf(context, vnf_instance,
                                 default_vim, attributes)
                # get vnf package
                vnf_package = objects.VnfPackage.get_by_id(context,
                vnfd.package_uuid, expected_attrs=['vnfd'])
                # Update VNF Package to IN_USE
                self._update_package_usage_state(context, vnf_package)
            except Exception:
                with excutils.save_and_reraise_exception():
                    # roll back db changes
                    self._destroy_vnf(context, vnf_instance)
                    vnf_instance.destroy(context)
                    self._update_package_usage_state(context, vnf_package)

            # create notification data
            notification = {
                'notificationType':
                fields.LcmOccsNotificationType.VNF_ID_CREATION_NOTIFICATION,
                'vnfInstanceId': vnf_instance.id,
                'links': {
                    'vnfInstance': {
                        'href': self._get_vnf_instance_href(vnf_instance)}}}

            # call send_notification
            self.rpc_api.send_notification(context, notification)

            result = self._view_builder.create(vnf_instance)
            headers = {"location": self._get_vnf_instance_href(vnf_instance)}
            return wsgi.ResponseObject(result, headers=headers)

        except nfvo.VimDefaultNotDefined as exc:
            raise webob.exc.HTTPBadRequest(explanation=six.text_type(exc))
        except(sqlexc.SQLAlchemyError, Exception)\
                as exc:
            raise webob.exc.HTTPInternalServerError(
                explanation=six.text_type(exc))
        except webob.exc.HTTPNotFound as e:
            return self._make_problem_detail(str(e), 404,
                'Not Found')
        except webob.exc.HTTPInternalServerError as e:
            return self._make_problem_detail(str(e), 500,
                'Internal Server Error')
        except Exception as e:
            return self._make_problem_detail(str(e), 500,
                'Internal Server Error')

    def _find_vnf_package_info(self, filter_key, filter_val):
        try:
            vnf_package_info_res = \
                nfvo_client.VnfPackageRequest.index(params={
                    "filter":
                    "(eq,{},{})".format(filter_key, filter_val)
                })
        except requests.exceptions.RequestException as e:
            LOG.exception(e)
            return None

        if not vnf_package_info_res.ok:
            return None

        vnf_package_info = vnf_package_info_res.json()
        if (not vnf_package_info or len(vnf_package_info) == 0):
            return None

        return vnf_package_info[0]

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
        context.can(vnf_lcm_policies.VNFLCM % 'index')

        filters = request.GET.get('filter')
        filters = self._view_builder.validate_filter(filters)

        vnf_instances = objects.VnfInstanceList.get_by_filters(
            request.context, filters=filters)

        return self._view_builder.index(vnf_instances)

    @check_vnf_state(action="delete",
        instantiation_state=[fields.VnfInstanceState.NOT_INSTANTIATED],
        task_state=[None])
    @check_vnf_status(action="delete",
        status=[constants.INACTIVE])
    def _delete(self, context, vnf_instance, vnf):
        vnf_package_vnfd = objects.VnfPackageVnfd.get_by_id(context,
                vnf_instance.vnfd_id)
        vnf_instance.destroy(context)
        self._destroy_vnf(context, vnf_instance)
        vnf_package = objects.VnfPackage.get_by_id(context,
                vnf_package_vnfd.package_uuid, expected_attrs=['vnfd'])
        self._update_package_usage_state(context, vnf_package)

    @wsgi.response(http_client.NO_CONTENT)
    @wsgi.expected_errors((http_client.FORBIDDEN, http_client.NOT_FOUND,
                           http_client.CONFLICT))
    def delete(self, request, id):
        context = request.environ['tacker.context']

        vnf_instance = self._get_vnf_instance(context, id)
        vnf = self._get_vnf(context, id)
        self._delete(context, vnf_instance, vnf)

        notification = {
            "notificationType": "VnfIdentifierDeletionNotification",
            "vnfInstanceId": vnf_instance.id,
            "links": {
                "vnfInstance":
                    "href:{apiRoot}/vnflcm/v1/vnf_instances/{vnfInstanceId}"}}
        # send notification
        self.rpc_api.send_notification(context, notification)

    @check_vnf_state(action="instantiate",
        instantiation_state=[fields.VnfInstanceState.NOT_INSTANTIATED],
        task_state=[None])
    @check_vnf_status(action="instantiate",
        status=[constants.INACTIVE])
    def _instantiate(self, context, vnf_instance, vnf, request_body):
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

        # lcm op process
        vnf_lcm_op_occs_id = \
            self._notification_process(context, vnf_instance,
                                       fields.LcmOccsOperationType.INSTANTIATE,
                                       instantiate_vnf_request)
        self.rpc_api.instantiate(context, vnf_instance, vnf,
                                 instantiate_vnf_request, vnf_lcm_op_occs_id)

    @wsgi.response(http_client.ACCEPTED)
    @wsgi.expected_errors((http_client.FORBIDDEN, http_client.NOT_FOUND,
                           http_client.CONFLICT, http_client.BAD_REQUEST))
    @validation.schema(vnf_lcm.instantiate)
    def instantiate(self, request, id, body):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'instantiate')

        vnf = self._get_vnf(context, id)
        vnf_instance = self._get_vnf_instance(context, id)

        self._instantiate(context, vnf_instance, vnf, body)

    @check_vnf_state(action="terminate",
                     instantiation_state=[
                         fields.VnfInstanceState.INSTANTIATED],
                     task_state=[None])
    def _terminate(self, context, vnf_instance, request_body, vnf):
        req_body = utils.convert_camelcase_to_snakecase(request_body)
        terminate_vnf_req = \
            objects.TerminateVnfRequest.obj_from_primitive(
                req_body, context=context)

        vnf_instance.task_state = fields.VnfInstanceTaskState.TERMINATING
        vnf_instance.save()

        # lcm op process
        vnf_lcm_op_occs_id = \
            self._notification_process(context, vnf_instance,
                                       fields.LcmOccsOperationType.TERMINATE,
                                       terminate_vnf_req)

        self.rpc_api.terminate(context, vnf_instance, vnf,
                               terminate_vnf_req, vnf_lcm_op_occs_id)

    @wsgi.response(http_client.ACCEPTED)
    @wsgi.expected_errors((http_client.BAD_REQUEST, http_client.FORBIDDEN,
                           http_client.NOT_FOUND, http_client.CONFLICT))
    @validation.schema(vnf_lcm.terminate)
    def terminate(self, request, id, body):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'terminate')

        vnf = self._get_vnf(context, id)
        vnf_instance = self._get_vnf_instance(context, id)
        self._terminate(context, vnf_instance, body, vnf)

    @check_vnf_state(action="heal",
        instantiation_state=[fields.VnfInstanceState.INSTANTIATED],
        task_state=[None])
    @check_vnf_status(action="heal",
        status=[constants.ACTIVE])
    def _heal(self, context, vnf_instance, vnf_dict, request_body):
        req_body = utils.convert_camelcase_to_snakecase(request_body)
        heal_vnf_request = objects.HealVnfRequest(context=context, **req_body)
        inst_vnf_info = vnf_instance.instantiated_vnf_info
        vnfc_resource_info_ids = [
            vnfc_resource_info.id for vnfc_resource_info in
            inst_vnf_info.vnfc_resource_info]

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

        # call notification process
        vnf_lcm_op_occs_id = \
            self._notification_process(context, vnf_instance,
                                       fields.LcmOccsOperationType.HEAL,
                                       heal_vnf_request)

        self.rpc_api.heal(context, vnf_instance, vnf_dict, heal_vnf_request,
                          vnf_lcm_op_occs_id)

    @wsgi.response(http_client.ACCEPTED)
    @wsgi.expected_errors((http_client.BAD_REQUEST, http_client.FORBIDDEN,
                           http_client.NOT_FOUND, http_client.CONFLICT))
    @validation.schema(vnf_lcm.heal)
    def heal(self, request, id, body):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'heal')

        vnf = self._get_vnf(context, id)
        vnf_instance = self._get_vnf_instance(context, id)
        self._heal(context, vnf_instance, vnf, body)

    @wsgi.response(http_client.OK)
    @wsgi.expected_errors((http_client.FORBIDDEN, http_client.NOT_FOUND))
    def show_lcm_op_occs(self, request, id):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'show_lcm_op_occs')

        try:
            vnf_lcm_op_occs = objects.VnfLcmOpOcc.get_by_id(context, id)
        except exceptions.NotFound as occ_e:
            return self._make_problem_detail(str(occ_e),
                404, title='VnfLcmOpOcc NOT FOUND')
        except Exception as e:
            LOG.error(traceback.format_exc())
            return self._make_problem_detail(str(e),
                500, title='Internal Server Error')

        return self._view_builder.show_lcm_op_occs(vnf_lcm_op_occs)

    @wsgi.response(http_client.OK)
    @wsgi.expected_errors((http_client.FORBIDDEN, http_client.NOT_FOUND))
    def update(self, request, id, body):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'update_vnf')

        # get body
        body_data = {}
        body_data['vnf_instance_name'] = body.get('vnfInstanceName')
        body_data['vnf_instance_description'] = body.get(
            'vnfInstanceDescription')
        body_data['vnfd_id'] = body.get('vnfdId')
        if (body.get('vnfdId') is None and body.get('vnfPkgId')):
            body_data['vnf_pkg_id'] = body.get('vnfPkgId')

        # According to the ETSI NFV SOL document,
        # there is no API request/response
        # specification for Etag yet,
        # and transactions using Etag are not defined
        # by standardization. Therefore, the Victoria release does not support
        # `Error Code: 412 Precondition Failed`. Once a standard specification
        # for this is established, it will be installed on the tacker.

        # Confirmation of update target
        try:
            vnf_data = objects.VNF.vnf_index_list(id, context)
            if not vnf_data:
                msg = _("Can not find requested vnf data: %s") % id
                return self._make_problem_detail(msg, 404, title='Not Found')
        except Exception as e:
            return self._make_problem_detail(
                str(e), 500, 'Internal Server Error')

        if (vnf_data.get("status") != fields.VnfStatus.ACTIVE and
                vnf_data.get("status") != fields.VnfStatus.INACTIVE):
            msg = _("VNF %(id)s status is %(state)s")
            return self._make_problem_detail(
                msg % {
                    "id": id,
                    "state": vnf_data.get("status")},
                409,
                'Conflict')

        try:
            vnf_instance_data = objects.VnfInstanceList.vnf_instance_list(
                vnf_data.get('vnfd_id'), context)
            if not vnf_instance_data:
                msg = _("Can not find requested vnf instance data: %s") \
                    % vnf_data.get('vnfd_id')
                return self._make_problem_detail(msg, 404, title='Not Found')
        except Exception as e:
            return self._make_problem_detail(
                str(e), 500, 'Internal Server Error')

        vnfd_pkg_data = {}
        if (body_data.get('vnfd_id') or body_data.get('vnf_pkg_id')):
            pkg_obj = objects.VnfPackageVnfd(context=context)
            try:
                if (body.get('vnfdId')):
                    input_id = 'vnfd_id'
                    filter_id = 'vnfdId'
                    vnfd_pkg = pkg_obj.get_vnf_package_vnfd(
                        body_data[input_id])
                elif (body_data.get('vnf_pkg_id')):
                    input_id = 'vnf_pkg_id'
                    filter_id = 'id'
                    vnfd_pkg = pkg_obj.get_vnf_package_vnfd(
                        body_data[input_id], package_uuid=True)
            except exceptions.VnfPackageVnfdNotFound:
                vnf_package_info = self._find_vnf_package_info(filter_id,
                    body_data[input_id])
                if not vnf_package_info:
                    msg = _(
                        "Can not find requested vnf package vnfd: %s") %\
                        body_data[input_id]
                    return self._make_problem_detail(msg, 400,
                    'Bad Request')

                vnfd_pkg = sync_resource.SyncVnfPackage.create_package(
                    context, vnf_package_info)

                if not vnfd_pkg:
                    msg = (
                        _("Can not find requested to NFVO,\
                        vnf package vnfd: %s") %
                        body_data[input_id])
                    return self._make_problem_detail(
                        msg, 500, 'Internal Server Error')
            vnfd_pkg_data['vnf_provider'] = vnfd_pkg.get('vnf_provider')
            vnfd_pkg_data['vnf_product_name'] = vnfd_pkg.get(
                'vnf_product_name')
            vnfd_pkg_data['vnf_software_version'] = vnfd_pkg.get(
                'vnf_software_version')
            vnfd_pkg_data['vnfd_version'] = vnfd_pkg.get('vnfd_version')
            vnfd_pkg_data['package_uuid'] = vnfd_pkg.get('package_uuid')
            vnfd_pkg_data['vnfd_id'] = vnfd_pkg.get('vnfd_id')

        # make op_occs_uuid
        op_occs_uuid = uuidutils.generate_uuid()

        # process vnf
        vnf_lcm_opoccs = {
            'vnf_instance_id': id,
            'id': op_occs_uuid,
            'state_entered_time': vnf_data.get('updated_at'),
            'operationParams': str(body)}

        self.rpc_api.update(
            context,
            vnf_lcm_opoccs,
            body_data,
            vnfd_pkg_data,
            vnf_data.get('vnfd_id'))

        # make response
        res = webob.Response(content_type='application/json')
        res.status_int = 202
        loc_url = CONF.vnf_lcm.endpoint_url + \
            '/vnflcm/v1/vnf_lcm_op_occs/' + op_occs_uuid
        location = ('Location', loc_url)
        res.headerlist.append(location)

        return res

    @wsgi.response(http_client.CREATED)
    @validation.schema(vnf_lcm.register_subscription)
    def register_subscription(self, request, body):
        subscription_request_data = body
        if subscription_request_data.get('filter'):
            # notificationTypes check
            notification_types = subscription_request_data.get(
                "filter").get("notificationTypes")
            for notification_type in notification_types:
                if notification_type not in self.notification_type_list:
                    msg = (
                        _("notificationTypes value mismatch: %s") %
                        notification_type)
                    return self._make_problem_detail(
                        msg, 400, title='Bad Request')

            # operationTypes check
            operation_types = subscription_request_data.get(
                "filter").get("operationTypes")
            for operation_type in operation_types:
                if operation_type not in self.operation_type_list:
                    msg = (
                        _("operationTypes value mismatch: %s") %
                        operation_type)
                    return self._make_problem_detail(
                        msg, 400, title='Bad Request')

        subscription_id = uuidutils.generate_uuid()

        vnf_lcm_subscription = subscription_obj.LccnSubscriptionRequest(
            context=request.context)
        vnf_lcm_subscription.id = subscription_id
        vnf_lcm_subscription.callback_uri = subscription_request_data.get(
            'callbackUri')
        vnf_lcm_subscription.subscription_authentication = \
            subscription_request_data.get('subscriptionAuthentication')
        LOG.debug("filter %s " % subscription_request_data.get('filter'))
        LOG.debug(
            "filter type %s " %
            type(
                subscription_request_data.get('filter')))
        filter_uni = subscription_request_data.get('filter')
        filter = ast.literal_eval(str(filter_uni).replace("u'", "'"))

        try:
            vnf_lcm_subscription = vnf_lcm_subscription.create(filter)
            LOG.debug("vnf_lcm_subscription %s" % vnf_lcm_subscription)
        except exceptions.SeeOther as e:
            if re.search("^303", str(e)):
                res = self._make_problem_detail(
                    "See Other", 303, title='See Other')
                link = (
                    'LINK',
                    CONF.vnf_lcm.endpoint_url +
                    "/vnflcm/v1/subscriptions/" +
                    str(e)[
                        3:])
                res.headerlist.append(link)
                return res
            else:
                LOG.error(traceback.format_exc())
                return self._make_problem_detail(
                    str(e), 500, title='Internal Server Error')

        result = self._view_builder.subscription_create(vnf_lcm_subscription,
                                                        filter)
        location = result.get('_links', {}).get('self', {}).get('href')
        headers = {"location": location}
        return wsgi.ResponseObject(result, headers=headers)

    @wsgi.response(http_client.OK)
    def subscription_show(self, request, subscriptionId):
        try:
            vnf_lcm_subscriptions = (
                subscription_obj.LccnSubscriptionRequest.
                vnf_lcm_subscriptions_show(request.context, subscriptionId))
            if not vnf_lcm_subscriptions:
                msg = (
                    _("Can not find requested vnf lcm subscriptions: %s") %
                    subscriptionId)
                return self._make_problem_detail(msg, 404, title='Not Found')
        except Exception as e:
            return self._make_problem_detail(
                str(e), 500, title='Internal Server Error')

        return self._view_builder.subscription_show(vnf_lcm_subscriptions)

    @wsgi.response(http_client.OK)
    def subscription_list(self, request):
        nextpage_opaque_marker = ""
        paging = 1

        re_url = request.path_url
        query_params = request.query_string
        if query_params:
            query_params = parse.unquote(query_params)
        LOG.debug("query_params %s" % query_params)
        if query_params:
            query_param_list = query_params.split('&')
            for query_param in query_param_list:
                query_param_key_value = query_param.split('=')
                if len(query_param_key_value) != 2:
                    msg = _("Request query parameter error")
                    return self._make_problem_detail(
                        msg, 400, title='Bad Request')
                if query_param_key_value[0] == 'nextpage_opaque_marker':
                    nextpage_opaque_marker = query_param_key_value[1]
                if query_param_key_value[0] == 'page':
                    paging = int(query_param_key_value[1])

        try:
            vnf_lcm_subscriptions = (
                subscription_obj.LccnSubscriptionRequest.
                vnf_lcm_subscriptions_list(request.context))
            LOG.debug("vnf_lcm_subscriptions %s" % vnf_lcm_subscriptions)
            subscription_data, last = self._view_builder.subscription_list(
                vnf_lcm_subscriptions, nextpage_opaque_marker, paging)
            LOG.debug("last %s" % last)
        except Exception as e:
            LOG.error(traceback.format_exc())
            return self._make_problem_detail(
                str(e), 500, title='Internal Server Error')

        if subscription_data == 400:
            msg = _("Number of records exceeds nextpage_opaque_marker")
            return self._make_problem_detail(msg, 400, title='Bad Request')

        # make response
        res = webob.Response(content_type='application/json')
        res.body = jsonutils.dump_as_bytes(subscription_data)
        res.status_int = 200
        if nextpage_opaque_marker:
            if not last:
                ln = '<%s?page=%s>;rel="next"; title*="next chapter"' % (
                    re_url, paging + 1)
                # Regarding the setting in http header related to
                # nextpage control, RFC8288 and NFV-SOL013
                # specifications have not been confirmed.
                # Therefore, it is implemented by setting "page",
                # which is a general control method of WebAPI,
                # as "URI-Reference" of Link header.

                links = ('Link', ln)
                res.headerlist.append(links)
        LOG.debug("subscription_list res %s" % res)

        return res

    @wsgi.response(http_client.NO_CONTENT)
    def delete_subscription(self, request, subscriptionId):
        try:
            vnf_lcm_subscription = \
                subscription_obj.LccnSubscriptionRequest.destroy(
                    request.context, subscriptionId)
            if vnf_lcm_subscription == 404:
                msg = (
                    _("Can not find requested vnf lcm subscription: %s") %
                    subscriptionId)
                return self._make_problem_detail(msg, 404, title='Not Found')
        except Exception as e:
            return self._make_problem_detail(
                str(e), 500, title='Internal Server Error')

    def _scale(self, context, vnf_info, vnf_instance, request_body):
        req_body = utils.convert_camelcase_to_snakecase(request_body)
        scale_vnf_request = objects.ScaleVnfRequest.obj_from_primitive(
            req_body, context=context)
        inst_vnf_info = vnf_instance.instantiated_vnf_info

        aspect = False
        current_level = 0
        for scale in inst_vnf_info.scale_status:
            if scale_vnf_request.aspect_id == scale.aspect_id:
                aspect = True
                current_level = scale.scale_level
                break
        if not aspect:
            return self._make_problem_detail(
                'aspectId not in ScaleStatus',
                400,
                title='aspectId not in ScaleStatus')
        if not scale_vnf_request.number_of_steps:
            scale_vnf_request.number_of_steps = 1
        if not scale_vnf_request.additional_params:
            scale_vnf_request.additional_params = {"is_reverse": "False",
                                                   "is_auto": "False"}
        if not scale_vnf_request.additional_params.get('is_reverse'):
            scale_vnf_request.additional_params['is_reverse'] = "False"
        if not scale_vnf_request.additional_params.get('is_auto'):
            scale_vnf_request.additional_params['is_auto'] = "False"

        if scale_vnf_request.type == 'SCALE_IN':
            if current_level == 0 or\
               current_level < scale_vnf_request.number_of_steps:
                return self._make_problem_detail(
                    'can not scale_in', 400, title='can not scale_in')
            scale_level = current_level - scale_vnf_request.number_of_steps

        elif scale_vnf_request.type == 'SCALE_OUT':
            scaleGroupDict = jsonutils.loads(
                vnf_info['attributes']['scale_group'])
            max_level = (scaleGroupDict['scaleGroupDict']
                [scale_vnf_request.aspect_id]['maxLevel'])
            scale_level = current_level + scale_vnf_request.number_of_steps
            if max_level < scale_level:
                return self._make_problem_detail(
                    'can not scale_out', 400, title='can not scale_out')

        vnf_lcm_op_occs_id = uuidutils.generate_uuid()
        timestamp = datetime.datetime.utcnow()
        operation_params = {
            'type': scale_vnf_request.type,
            'aspect_id': scale_vnf_request.aspect_id,
            'number_of_steps': scale_vnf_request.number_of_steps,
            'additional_params': scale_vnf_request.additional_params}
        vnf_lcm_op_occ = objects.VnfLcmOpOcc(
            context=context,
            id=vnf_lcm_op_occs_id,
            operation_state='STARTING',
            state_entered_time=timestamp,
            start_time=timestamp,
            vnf_instance_id=inst_vnf_info.vnf_instance_id,
            operation='SCALE',
            is_automatic_invocation=scale_vnf_request.additional_params.get('\
                is_auto'),
            operation_params=json.dumps(operation_params),
            error_point=1)
        vnf_lcm_op_occ.create()

        vnflcm_url = CONF.vnf_lcm.endpoint_url + \
            "/vnflcm/v1/vnf_lcm_op_occs/" + vnf_lcm_op_occs_id
        insta_url = CONF.vnf_lcm.endpoint_url + \
            "/vnflcm/v1/vnf_instances/" + inst_vnf_info.vnf_instance_id

        vnf_info['vnflcm_id'] = vnf_lcm_op_occs_id
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occ
        vnf_info['after_scale_level'] = scale_level
        vnf_info['scale_level'] = current_level

        self.rpc_api.scale(context, vnf_info, vnf_instance, scale_vnf_request)

        notification = {}
        notification['notificationType'] = \
            'VnfLcmOperationOccurrenceNotification'
        notification['vnfInstanceId'] = inst_vnf_info.vnf_instance_id
        notification['notificationStatus'] = 'START'
        notification['operation'] = 'SCALE'
        notification['operationState'] = 'STARTING'
        notification['isAutomaticInvocation'] = \
            scale_vnf_request.additional_params.get('is_auto')
        notification['vnfLcmOpOccId'] = vnf_lcm_op_occs_id
        notification['_links'] = {}
        notification['_links']['vnfInstance'] = {}
        notification['_links']['vnfInstance']['href'] = insta_url
        notification['_links']['vnfLcmOpOcc'] = {}
        notification['_links']['vnfLcmOpOcc']['href'] = vnflcm_url
        self.rpc_api.send_notification(context, notification)

        vnf_info['notification'] = notification

        res = webob.Response()
        res.status_int = 202
        location = ('Location', vnflcm_url)
        res.headerlist.append(location)
        return res

    @validation.schema(vnf_lcm.scale)
    @wsgi.response(http_client.ACCEPTED)
    @wsgi.expected_errors((http_client.BAD_REQUEST, http_client.FORBIDDEN,
                           http_client.NOT_FOUND, http_client.CONFLICT))
    def scale(self, request, id, body):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'scale')

        try:
            vnf_info = self._vnfm_plugin.get_vnf(context, id)
            if vnf_info['status'] != constants.ACTIVE:
                return self._make_problem_detail(
                    'VNF IS NOT ACTIVE', 409, title='VNF IS NOT ACTIVE')
            vnf_instance = self._get_vnf_instance(context, id)
            if not vnf_instance.instantiated_vnf_info.scale_status:
                return self._make_problem_detail(
                    'NOT SCALE VNF', 409, title='NOT SCALE VNF')
            return self._scale(context, vnf_info, vnf_instance, body)
        except vnfm.VNFNotFound as vnf_e:
            return self._make_problem_detail(
                str(vnf_e), 404, title='VNF NOT FOUND')
        except webob.exc.HTTPNotFound as inst_e:
            return self._make_problem_detail(
                str(inst_e), 404, title='VNF NOT FOUND')
        except Exception as e:
            LOG.error(traceback.format_exc())
            return self._make_problem_detail(
                str(e), 500, title='Internal Server Error')

    def _rollback(
            self,
            context,
            vnf_info,
            vnf_instance,
            vnf_lcm_op_occs,
            operation_params):

        self.rpc_api.rollback(
            context,
            vnf_info,
            vnf_instance,
            operation_params)
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs

        vnflcm_url = CONF.vnf_lcm.endpoint_url + \
            "/vnflcm/v1/vnf_lcm_op_occs/" + vnf_lcm_op_occs.id
        res = webob.Response()
        res.status_int = 202
        location = ('Location', vnflcm_url)
        res.headerlist.append(location)
        return res

    def _get_rollback_vnf(self, context, vnf_instance_id):
        return self._vnfm_plugin.get_vnf(context, vnf_instance_id)

    @wsgi.response(http_client.ACCEPTED)
    @wsgi.expected_errors((http_client.BAD_REQUEST, http_client.FORBIDDEN,
                           http_client.NOT_FOUND, http_client.CONFLICT))
    def rollback(self, request, id):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'rollback')

        try:
            vnf_lcm_op_occs = objects.VnfLcmOpOcc.get_by_id(context, id)
            if vnf_lcm_op_occs.operation_state != 'FAILED_TEMP':
                return self._make_problem_detail(
                    'OperationState IS NOT FAILED_TEMP',
                    409,
                    title='OperationState IS NOT FAILED_TEMP')

            if vnf_lcm_op_occs.operation != 'INSTANTIATION' \
                    and vnf_lcm_op_occs.operation != 'SCALE':
                return self._make_problem_detail(
                    'OPERATION IS NOT INSTANTIATION/SCALE',
                    409,
                    title='OPERATION IS NOT INSTANTIATION/SCALE')

            operation_params = jsonutils.loads(
                vnf_lcm_op_occs.operation_params)

            if vnf_lcm_op_occs.operation == 'SCALE' \
                    and operation_params['type'] == 'SCALE_IN':
                return self._make_problem_detail(
                    'SCALE_IN CAN NOT ROLLBACK', 409,
                    title='SCALE_IN CAN NOT ROLLBACK')

            vnf_info = self._get_rollback_vnf(
                context, vnf_lcm_op_occs.vnf_instance_id)
            vnf_instance = self._get_vnf_instance(
                context, vnf_lcm_op_occs.vnf_instance_id)

            vnf_lcm_op_occs.changed_info = None
            vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
            return self._rollback(
                context,
                vnf_info,
                vnf_instance,
                vnf_lcm_op_occs,
                operation_params)
        except vnfm.VNFNotFound as vnf_e:
            return self._make_problem_detail(
                str(vnf_e), 404, title='VNF NOT FOUND')
        except exceptions.NotFound as occ_e:
            return self._make_problem_detail(
                str(occ_e), 404, title='VNF NOT FOUND')
        except webob.exc.HTTPNotFound as inst_e:
            return self._make_problem_detail(
                str(inst_e), 404, title='VNF NOT FOUND')
        except Exception as e:
            LOG.error(traceback.format_exc())
            return self._make_problem_detail(
                str(e), 500, title='Internal Server Error')

    def _make_problem_detail(
            self,
            detail,
            status,
            title=None,
            type=None,
            instance=None):
        '''This process returns the problem_detail to the caller'''
        LOG.error(detail)
        res = webob.Response(content_type='application/problem+json')
        problem_details = {}
        if type:
            problem_details['type'] = type
        if title:
            problem_details['title'] = title
        problem_details['detail'] = detail
        problem_details['status'] = status
        if instance:
            problem_details['instance'] = instance
        res.text = json.dumps(problem_details)
        res.status_int = status
        return res


def create_resource():
    return wsgi.Resource(VnfLcmController())
