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

import copy
import datetime
import requests
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
from toscaparser import tosca_template

import ast
import functools
import json
import re
import traceback

from http import client as http_client
from urllib import parse

from tacker._i18n import _
from tacker.api import api_common
from tacker.api.schemas import vnf_lcm
from tacker.api import validation
from tacker.api.views import vnf_lcm as vnf_lcm_view
from tacker.api.views import vnf_lcm_op_occs as vnf_op_occs_view
from tacker.api.views import vnf_subscriptions as vnf_subscription_view
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
from tacker.objects.fields import ErrorPoint as EP
from tacker.objects import vnf_lcm_op_occs as vnf_lcm_op_occs_obj
from tacker.objects import vnf_lcm_subscriptions as subscription_obj
from tacker.plugins.common import constants
from tacker.policies import vnf_lcm as vnf_lcm_policies
from tacker.tosca import utils as toscautils
from tacker.vnflcm import utils as vnflcm_utils
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


def check_vnf_status_and_error_point(action, status=None):
    """Decorator to check vnf status are valid for particular action.

    If the vnf has the wrong status with the wrong error point,
    it will raise conflict exception.
    """

    if status is not None and not isinstance(status, set):
        status = set(status)

    def outer(f):
        @functools.wraps(f)
        def inner(self, context, vnf_instance, vnf, *args, **kw):
            vnf['current_error_point'] = fields.ErrorPoint.INITIAL

            if 'before_error_point' not in vnf:
                vnf['before_error_point'] = fields.ErrorPoint.INITIAL

            if status is not None and vnf['status'] not in status and \
                    vnf['before_error_point'] == fields.ErrorPoint.INITIAL:
                raise exceptions.VnfConflictStateWithErrorPoint(
                    uuid=vnf['id'],
                    state=vnf['status'],
                    action=action,
                    error_point=vnf['before_error_point'])
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
        self._view_builder_op_occ = vnf_op_occs_view.ViewBuilder()
        self._view_builder_subscription = vnf_subscription_view.ViewBuilder()
        self._nextpages_vnf_instances = {}
        self._nextpages_lcm_op_occs = {}
        self._nextpages_subscriptions = {}

    def _get_vnf_instance_href(self, vnf_instance):
        return '{}vnflcm/v1/vnf_instances/{}'.format(
            CONF.vnf_lcm.endpoint_url, vnf_instance.id)

    def _get_vnf_lcm_op_occs_href(self, vnf_lcm_op_occs_id):
        return '{}vnflcm/v1/vnf_lcm_op_occs/{}'.format(
            CONF.vnf_lcm.endpoint_url, vnf_lcm_op_occs_id)

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
            LOG.debug("{}: {}".format(msg, str(exc)))
            raise webob.exc.HTTPInternalServerError(explanation=str(exc))
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

    def _notification_process(
            self, context, vnf_instance, lcm_operation, request, body,
            operation_state, notification_status, vnf_lcm_op_occs=None,
            affected_resources=None, is_auto=False):
        LOG.debug('START NOTIFICATION PROCESS')
        vnf_url = self._get_vnf_instance_href(vnf_instance)

        notification = {
            'notificationType':
                fields.LcmOccsNotificationType.VNF_OP_OCC_NOTIFICATION,
            'notificationStatus': notification_status,
            'operationState': operation_state,
            'vnfInstanceId': vnf_instance.id,
            'operation': lcm_operation,
            'isAutomaticInvocation': is_auto,
            '_links': {
                'vnfInstance': {
                    'href': vnf_url},
                'vnfLcmOpOcc': {}}}

        # TODO(h-asahina): notification and VnfLcmOpOcc should be created
        #  independently
        if operation_state in (fields.LcmOccsOperationState.FAILED,
                               fields.LcmOccsOperationState.FAILED_TEMP):
            vnf_lcm_op_occs_id = vnf_lcm_op_occs.id

            notification['affectedVnfcs'] = affected_resources.get(
                'affectedVnfcs', [])
            notification['affectedVirtualLinks'] = affected_resources.get(
                'affectedVirtualLinks', [])
            notification['affectedVirtualStorages'] = affected_resources.get(
                'affectedVirtualStorages', [])
            notification['error'] = str(vnf_lcm_op_occs.error)

        else:
            vnf_lcm_op_occs_id = uuidutils.generate_uuid()
            error_point = 0
            operation_params = jsonutils.dumps(body)
            try:
                # call create lcm op occs here
                LOG.debug('Create LCM OP OCCS')
                vnf_lcm_op_occs = objects.VnfLcmOpOcc(
                    context=context,
                    id=vnf_lcm_op_occs_id,
                    operation_state=operation_state,
                    start_time=timeutils.utcnow(),
                    state_entered_time=timeutils.utcnow(),
                    vnf_instance_id=vnf_instance.id,
                    is_cancel_pending=is_auto,
                    operation=lcm_operation,
                    is_automatic_invocation=is_auto,
                    operation_params=operation_params,
                    error_point=error_point,
                    tenant_id=context.tenant_id)
                vnf_lcm_op_occs.create()
            except Exception:
                msg = _("Failed to create LCM occurrence")
                raise webob.exc.HTTPInternalServerError(explanation=msg)

        vnf_lcm_url = self._get_vnf_lcm_op_occs_href(vnf_lcm_op_occs_id)
        notification['vnfLcmOpOccId'] = vnf_lcm_op_occs_id
        notification['_links']['vnfLcmOpOcc']['href'] = vnf_lcm_url
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
                             deleted_at=datetime.datetime.min)
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
                vnf_pkg_id=vnfd.package_uuid,
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
                    if 'vnf_package' not in locals():
                        LOG.error("vnf_package is not assigned")
                    else:
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
            raise webob.exc.HTTPBadRequest(explanation=str(exc))
        except(sqlexc.SQLAlchemyError, Exception) as exc:
            raise webob.exc.HTTPInternalServerError(
                explanation=str(exc))
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

    def _delete_expired_nextpages(self, nextpages):
        for k, v in list(nextpages.items()):
            if timeutils.is_older_than(v['created_time'],
                    CONF.vnf_lcm.nextpage_expiration_time):
                LOG.debug('Old nextpages are deleted. id: %s' % k)
                nextpages.pop(k)

    @wsgi.response(http_client.OK)
    @wsgi.expected_errors((http_client.FORBIDDEN, http_client.NOT_FOUND))
    def show(self, request, id):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'show')
        vnf_instance = self._get_vnf_instance(context, id)

        return self._view_builder.show(vnf_instance)

    @wsgi.response(http_client.OK)
    def api_versions(self, request):
        return {'uriPrefix': '/vnflcm/v1',
                'apiVersions': [{'version': '1.3.0', 'isDeprecated': False}]}

    @wsgi.response(http_client.OK)
    @wsgi.expected_errors((http_client.FORBIDDEN, http_client.BAD_REQUEST))
    @api_common.validate_supported_params({'filter', 'nextpage_opaque_marker',
                                           'all_records'})
    def index(self, request):
        if 'tacker.context' in request.environ:
            context = request.environ['tacker.context']
            context.can(vnf_lcm_policies.VNFLCM % 'index')

        filters = request.GET.get('filter')
        filters = self._view_builder.validate_filter(filters)

        nextpage = request.GET.get('nextpage_opaque_marker')
        allrecords = request.GET.get('all_records')

        result = []

        if allrecords != 'yes' and nextpage:
            self._delete_expired_nextpages(self._nextpages_vnf_instances)

            if nextpage in self._nextpages_vnf_instances:
                result = self._nextpages_vnf_instances.pop(
                    nextpage)['nextpage']
        else:
            vnf_instances = objects.VnfInstanceList.get_by_filters(
                request.context, filters=filters)

            result = self._view_builder.index(vnf_instances)

        res = webob.Response(content_type='application/json')
        res.status_int = 200

        if (allrecords != 'yes' and
                len(result) > CONF.vnf_lcm.vnf_instance_num):
            nextpageid = uuidutils.generate_uuid()
            links = ('Link', '<%s?nextpage_opaque_marker=%s>; rel="next"' % (
                request.path_url, nextpageid))
            res.headerlist.append(links)
            res.body = jsonutils.dump_as_bytes(
                result[: CONF.vnf_lcm.vnf_instance_num])

            self._delete_expired_nextpages(self._nextpages_vnf_instances)

            remain = result[CONF.vnf_lcm.vnf_instance_num:]
            self._nextpages_vnf_instances.update({nextpageid:
                {'created_time': timeutils.utcnow(), 'nextpage': remain}})
        else:
            res.body = jsonutils.dump_as_bytes(result)

        return res

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
    @check_vnf_status_and_error_point(action="instantiate",
        status=[constants.INACTIVE])
    def _instantiate(self, context, vnf_instance, vnf, request_body):
        req_body = utils.convert_camelcase_to_snakecase(request_body)

        vnf_lcm_op_occs_id = vnf.get('vnf_lcm_op_occs_id')

        try:
            self._validate_flavour_and_inst_level(context, req_body,
                                                  vnf_instance)
        except exceptions.NotFound as ex:
            raise webob.exc.HTTPBadRequest(explanation=str(ex))

        instantiate_vnf_request = \
            objects.InstantiateVnfRequest.obj_from_primitive(
                req_body, context=context)

        # validate the vim connection id passed through request is exist or not
        self._validate_vim_connection(context, instantiate_vnf_request)

        vnf_instance.task_state = fields.VnfInstanceTaskState.INSTANTIATING
        vnf_instance.save()

        # lcm op process
        if vnf['before_error_point'] == fields.ErrorPoint.INITIAL:
            vnf_lcm_op_occs_id = self._notification_process(
                context, vnf_instance,
                fields.LcmOccsOperationType.INSTANTIATE,
                instantiate_vnf_request, request_body,
                operation_state=fields.LcmOccsOperationState.STARTING,
                notification_status=fields.LcmOccsNotificationStatus.START)

        if vnf_lcm_op_occs_id:
            self.rpc_api.instantiate(context, vnf_instance, vnf,
                                    instantiate_vnf_request,
                                    vnf_lcm_op_occs_id)
        # set response header
        res = webob.Response()
        res.status_int = 202
        location = ('Location',
                self._get_vnf_lcm_op_occs_href(vnf_lcm_op_occs_id))
        res.headerlist.append(location)
        return res

    @wsgi.response(http_client.ACCEPTED)
    @wsgi.expected_errors((http_client.FORBIDDEN, http_client.NOT_FOUND,
                           http_client.CONFLICT, http_client.BAD_REQUEST))
    @validation.schema(vnf_lcm.instantiate)
    def instantiate(self, request, id, body):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'instantiate')

        vnf = self._get_vnf(context, id)
        vnf_instance = self._get_vnf_instance(context, id)

        return self._instantiate(context, vnf_instance, vnf, body)

    @check_vnf_state(action="terminate",
                     instantiation_state=[
                         fields.VnfInstanceState.INSTANTIATED,
                         fields.VnfInstanceState.NOT_INSTANTIATED],
                     task_state=[None])
    @check_vnf_status_and_error_point(action="terminate",
        status=[constants.ACTIVE])
    def _terminate(self, context, vnf_instance, vnf, request_body):
        req_body = utils.convert_camelcase_to_snakecase(request_body)
        terminate_vnf_req = \
            objects.TerminateVnfRequest.obj_from_primitive(
                req_body, context=context)

        vnf_instance.task_state = fields.VnfInstanceTaskState.TERMINATING
        vnf_instance.save()

        vnf_lcm_op_occs_id = vnf.get('vnf_lcm_op_occs_id')

        # lcm op process
        if vnf['before_error_point'] == fields.ErrorPoint.INITIAL:
            vnf_lcm_op_occs_id = self._notification_process(
                context, vnf_instance,
                fields.LcmOccsOperationType.TERMINATE, terminate_vnf_req,
                request_body,
                operation_state=fields.LcmOccsOperationState.STARTING,
                notification_status=fields.LcmOccsNotificationStatus.START)

        if vnf_lcm_op_occs_id:
            self.rpc_api.terminate(context, vnf_instance, vnf,
                                terminate_vnf_req, vnf_lcm_op_occs_id)
        # set response header
        res = webob.Response()
        res.status_int = 202
        location = ('Location',
                self._get_vnf_lcm_op_occs_href(vnf_lcm_op_occs_id))
        res.headerlist.append(location)
        return res

    @wsgi.response(http_client.ACCEPTED)
    @wsgi.expected_errors((http_client.BAD_REQUEST, http_client.FORBIDDEN,
                           http_client.NOT_FOUND, http_client.CONFLICT))
    @validation.schema(vnf_lcm.terminate)
    def terminate(self, request, id, body):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'terminate')

        vnf = self._get_vnf(context, id)
        vnf_instance = self._get_vnf_instance(context, id)
        return self._terminate(context, vnf_instance, vnf, body)

    @check_vnf_status_and_error_point(action="heal",
        status=[constants.ACTIVE])
    def _heal(self, context, vnf_instance, vnf_dict, request_body):
        req_body = utils.convert_camelcase_to_snakecase(request_body)
        heal_vnf_request = objects.HealVnfRequest(context=context, **req_body)
        inst_vnf_info = vnf_instance.instantiated_vnf_info
        vnfc_resource_info_ids = [
            vnfc_resource_info.id for vnfc_resource_info in
            inst_vnf_info.vnfc_resource_info]

        vnf_lcm_op_occs_id = vnf_dict.get('vnf_lcm_op_occs_id')

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
        if vnf_dict['before_error_point'] == fields.ErrorPoint.INITIAL:
            vnf_lcm_op_occs_id = self._notification_process(
                context, vnf_instance, fields.LcmOccsOperationType.HEAL,
                heal_vnf_request, request_body,
                operation_state=fields.LcmOccsOperationState.STARTING,
                notification_status=fields.LcmOccsNotificationStatus.START)

        if vnf_lcm_op_occs_id:
            self.rpc_api.heal(context, vnf_instance, vnf_dict,
                            heal_vnf_request, vnf_lcm_op_occs_id)

        # set response header
        res = webob.Response()
        res.status_int = 202
        location = ('Location',
                self._get_vnf_lcm_op_occs_href(vnf_lcm_op_occs_id))
        res.headerlist.append(location)
        return res

    @wsgi.response(http_client.ACCEPTED)
    @wsgi.expected_errors((http_client.BAD_REQUEST, http_client.FORBIDDEN,
                           http_client.NOT_FOUND, http_client.CONFLICT))
    @validation.schema(vnf_lcm.heal)
    def heal(self, request, id, body):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'heal')

        vnf = self._get_vnf(context, id)
        vnf_instance = self._get_vnf_instance(context, id)

        if vnf_instance.instantiation_state not in \
           [fields.VnfInstanceState.INSTANTIATED]:
            raise exceptions.VnfInstanceConflictState(
                attr='instantiation_state',
                uuid=vnf_instance.id,
                state=vnf_instance.instantiation_state,
                action='heal')
        if vnf_instance.task_state not in [None]:
            raise exceptions.VnfInstanceConflictState(
                attr='task_state',
                uuid=vnf_instance.id,
                state=vnf_instance.task_state,
                action='heal')

        return self._heal(context, vnf_instance, vnf, body)

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

    @wsgi.response(http_client.ACCEPTED)
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
            'state_entered_time': timeutils.utcnow(),
            'operationParams': str(body),
            'tenant_id': request.context.project_id}

        self.rpc_api.update(
            context,
            vnf_lcm_opoccs,
            body_data,
            vnfd_pkg_data,
            vnf_data.get('vnfd_id'))

        # make response
        res = webob.Response(content_type='application/json')
        res.status_int = 202
        loc_url = CONF.vnf_lcm.endpoint_url.rstrip("/") + \
            '/vnflcm/v1/vnf_lcm_op_occs/' + op_occs_uuid
        location = ('Location', loc_url)
        res.headerlist.append(location)

        return res

    @wsgi.response(http_client.CREATED)
    @validation.schema(vnf_lcm.register_subscription)
    def register_subscription(self, request, body):
        subscription_request_data = body

        subscription_id = uuidutils.generate_uuid()

        vnf_lcm_subscription = subscription_obj.LccnSubscriptionRequest(
            context=request.context)
        vnf_lcm_subscription.id = subscription_id
        vnf_lcm_subscription.callback_uri = subscription_request_data.get(
            'callbackUri')
        if 'authentication' in subscription_request_data:
            vnf_lcm_subscription.authentication = jsonutils.dumps(
                subscription_request_data.get('authentication'))
        vnf_lcm_subscription.tenant_id = request.context.tenant_id
        LOG.debug("filter %s " % subscription_request_data.get('filter'))
        LOG.debug(
            "filter type %s " %
            type(
                subscription_request_data.get('filter')))
        filter_uni = subscription_request_data.get('filter')
        filter = ast.literal_eval(str(filter_uni).replace("'", "'"))

        if CONF.vnf_lcm.test_callback_uri:
            resp = self._test_notification(request.context,
                vnf_lcm_subscription)
            if resp == -1:
                LOG.exception(traceback.format_exc())
                return self._make_problem_detail(
                    'Failed to Test Notification', 400,
                    title='Bad Request')

        try:
            vnf_lcm_subscription = vnf_lcm_subscription.create(filter)
            LOG.debug("vnf_lcm_subscription %s" % vnf_lcm_subscription)
        except exceptions.SeeOther as e:
            res = webob.Response(content_type='application/json')
            res.status_int = http_client.SEE_OTHER.value
            location = (
                'Location',
                CONF.vnf_lcm.endpoint_url.rstrip("/") +
                "/vnflcm/v1/subscriptions/" + str(e))
            res.headerlist.append(location)
            return res

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
        nextpage_opaque_marker = None
        paging = 1
        filter_string = ""
        ignore_nextpages = False
        subscription_data = []

        query_params = request.query_string

        allrecords = request.GET.get('all_records')

        if query_params:
            query_params = parse.unquote(query_params)
            query_param_list = query_params.split('&')
            for query_param in query_param_list:
                query_param_key_value = query_param.split('=')
                if len(query_param_key_value) != 2:
                    msg = _("Request query parameter error")
                    return self._make_problem_detail(
                        msg, 400, title='Bad Request')
                if query_param_key_value[0] == 'filter':
                    filter_string = query_param_key_value[1]
                if query_param_key_value[0] == 'nextpage_opaque_marker':
                    nextpage_opaque_marker = query_param_key_value[1]
                if query_param_key_value[0] == 'page':
                    paging = int(query_param_key_value[1])
                    ignore_nextpages = True

            if filter_string:
                # check enumerations columns
                for filter_segment in filter_string.split(';'):
                    filter_segment = re.sub(
                        r'\(|\)|\'', '', filter_segment)
                    filter_name = filter_segment.split(',')[1]
                    filter_value = filter_segment.split(',')[2]
                    if filter_name == 'notificationTypes':
                        if filter_value not in self.notification_type_list:
                            msg = (_("notificationTypes value mismatch: %s")
                                % filter_value)
                            return self._make_problem_detail(msg, 400,
                                title='Bad Request')
                    elif filter_name == 'operationTypes':
                        if filter_value not in self.operation_type_list:
                            msg = (_("operationTypes value mismatch: %s")
                                % filter_value)
                            return self._make_problem_detail(msg, 400,
                                title='Bad Request')
                    elif filter_name == 'operationStates':
                        if filter_value not in self.operation_state_list:
                            msg = (_("operationStates value mismatch: %s")
                                % filter_value)
                            return self._make_problem_detail(msg, 400,
                                title='Bad Request')

        nextpage = nextpage_opaque_marker
        if allrecords != 'yes' and not ignore_nextpages and nextpage:
            self._delete_expired_nextpages(self._nextpages_subscriptions)

            if nextpage in self._nextpages_subscriptions:
                subscription_data = self._nextpages_subscriptions.pop(
                    nextpage)['nextpage']
        else:
            try:
                filter_string_parsed = self._view_builder_subscription. \
                    validate_filter(filter_string)
                if nextpage_opaque_marker:
                    start_index = paging - 1
                else:
                    start_index = None

                vnf_lcm_subscriptions = (
                    subscription_obj.LccnSubscriptionList.
                    get_by_filters(request.context,
                                read_deleted='no',
                                filters=filter_string_parsed,
                                nextpage_opaque_marker=start_index))

                LOG.debug("vnf_lcm_subscriptions %s" % vnf_lcm_subscriptions)
                subscription_data = self._view_builder_subscription. \
                    subscription_list(vnf_lcm_subscriptions)
            except Exception as e:
                LOG.error(traceback.format_exc())
                return self._make_problem_detail(
                    str(e), 500, title='Internal Server Error')

        # make response
        res = webob.Response(content_type='application/json')
        res.status_int = 200

        if (allrecords != 'yes' and not ignore_nextpages and
                len(subscription_data) > CONF.vnf_lcm.subscription_num):
            nextpageid = uuidutils.generate_uuid()
            links = ('Link', '<%s?nextpage_opaque_marker=%s>; rel="next"' % (
                request.path_url, nextpageid))
            res.headerlist.append(links)

            remain = subscription_data[CONF.vnf_lcm.subscription_num:]
            subscription_data = (
                subscription_data[: CONF.vnf_lcm.subscription_num])

            self._delete_expired_nextpages(self._nextpages_subscriptions)
            self._nextpages_subscriptions.update({nextpageid:
                {'created_time': timeutils.utcnow(), 'nextpage': remain}})

        res.body = jsonutils.dump_as_bytes(subscription_data)

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

    def _get_scale_max_level_from_vnfd(self, context, vnf_instance, aspect_id):
        vnfd_dict = vnflcm_utils._get_vnfd_dict(context,
            vnf_instance.vnfd_id,
            vnf_instance.instantiated_vnf_info.flavour_id)
        tosca = tosca_template.ToscaTemplate(parsed_params={}, a_file=False,
                                             yaml_dict_tpl=vnfd_dict)
        tosca_policies = tosca.topology_template.policies

        aspect_max_level_dict = {}
        toscautils._extract_policy_info(
            tosca_policies, {}, {}, {}, {}, {}, aspect_max_level_dict)

        return aspect_max_level_dict.get(aspect_id)

    @check_vnf_state(action="scale",
        instantiation_state=[fields.VnfInstanceState.INSTANTIATED],
        task_state=[None])
    @check_vnf_status_and_error_point(action="scale",
        status=[constants.ACTIVE])
    def _scale(self, context, vnf_instance, vnf_info, request_body):
        req_body = utils.convert_camelcase_to_snakecase(request_body)
        scale_vnf_request = objects.ScaleVnfRequest.obj_from_primitive(
            req_body, context=context)
        inst_vnf_info = vnf_instance.instantiated_vnf_info

        if 'vnf_lcm_op_occs_id' in vnf_info:
            vnf_lcm_op_occs_id = vnf_info['vnf_lcm_op_occs_id']

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

        vim_type = vnf_instance.vim_connection_info[0].vim_type
        if scale_vnf_request.type == 'SCALE_IN':
            if current_level == 0 or\
               current_level < scale_vnf_request.number_of_steps:
                return self._make_problem_detail(
                    'can not scale_in', 400, title='can not scale_in')
            if vim_type == "kubernetes" and\
               scale_vnf_request.additional_params['is_reverse'] == "True":
                return self._make_problem_detail(
                    'is_reverse option is not supported when Kubernetes '
                    'scale operation',
                    400,
                    title='is_reverse option is not supported when Kubernetes '
                    'scale operation')
            scale_level = current_level - scale_vnf_request.number_of_steps

        elif scale_vnf_request.type == 'SCALE_OUT':
            if vim_type == "kubernetes":
                max_level = self._get_scale_max_level_from_vnfd(
                    context=context,
                    vnf_instance=vnf_instance,
                    aspect_id=scale_vnf_request.aspect_id)
            else:
                scaleGroupDict = jsonutils.loads(
                    vnf_info['attributes']['scale_group'])
                max_level = (scaleGroupDict['scaleGroupDict']
                    [scale_vnf_request.aspect_id]['maxLevel'])

            scale_level = current_level + scale_vnf_request.number_of_steps
            if max_level < scale_level:
                return self._make_problem_detail(
                    'can not scale_out', 400, title='can not scale_out')
            if 'vnf_lcm_op_occs_id' in vnf_info and vim_type != "kubernetes":
                num = (scaleGroupDict['scaleGroupDict']
                    [scale_vnf_request.aspect_id]['num'])
                default = (scaleGroupDict['scaleGroupDict']
                    [scale_vnf_request.aspect_id]['default'])
                vnf_info['res_num'] = (num *
                    scale_vnf_request.number_of_steps + default)

        if vnf_info['before_error_point'] == fields.ErrorPoint.INITIAL:
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
                error_point=1,
                tenant_id=vnf_instance.tenant_id)
            vnf_lcm_op_occ.create()
        else:
            try:
                vnf_lcm_op_occ = objects.VnfLcmOpOcc.get_by_id(
                    context, vnf_lcm_op_occs_id)
            except exceptions.NotFound as lcm_e:
                return self._make_problem_detail(str(lcm_e),
                    404, title='Not Found')
            except (sqlexc.SQLAlchemyError, Exception) as exc:
                LOG.exception(exc)
                return self._make_problem_detail(str(exc),
                    500, title='Internal Server Error')

        vnf_instance.task_state = fields.VnfInstanceTaskState.SCALING
        vnf_instance.save()

        vnflcm_url = CONF.vnf_lcm.endpoint_url.rstrip("/") + \
            "/vnflcm/v1/vnf_lcm_op_occs/" + vnf_lcm_op_occs_id
        insta_url = CONF.vnf_lcm.endpoint_url.rstrip("/") + \
            "/vnflcm/v1/vnf_instances/" + inst_vnf_info.vnf_instance_id

        vnf_info['vnflcm_id'] = vnf_lcm_op_occs_id
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occ
        vnf_info['after_scale_level'] = scale_level
        vnf_info['scale_level'] = current_level
        vnf_info['instance_id'] = inst_vnf_info.instance_id

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
        vnf_info['notification'] = notification

        if vnf_info['before_error_point'] == fields.ErrorPoint.INITIAL:
            self.rpc_api.send_notification(context, notification)
        self.rpc_api.scale(context, vnf_info, vnf_instance, scale_vnf_request)

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
            return self._scale(context, vnf_instance, vnf_info, body)
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

        vnflcm_url = CONF.vnf_lcm.endpoint_url.rstrip("/") + \
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

            if vnf_lcm_op_occs.operation != 'INSTANTIATE' \
                    and vnf_lcm_op_occs.operation != 'SCALE':
                return self._make_problem_detail(
                    'OPERATION IS NOT INSTANTIATE/SCALE',
                    409,
                    title='OPERATION IS NOT INSTANTIATE/SCALE')

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

            inst_vnf_info = vnf_instance.instantiated_vnf_info
            if inst_vnf_info is not None:
                vnf_info['instance_id'] = inst_vnf_info.instance_id

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

    # TODO(esto-aln): For adding it to make it consistent
    # We change vnf status here. In near future, we plan to
    # delete this method.
    def _update_vnf_fail_status(self, context, vnf_instance_id,
            new_status):
        self._vnfm_plugin.update_vnf_fail_status(
            context, vnf_instance_id, new_status)

    @wsgi.response(http_client.ACCEPTED)
    @wsgi.expected_errors((http_client.BAD_REQUEST, http_client.FORBIDDEN,
                           http_client.NOT_FOUND, http_client.CONFLICT))
    @validation.schema(vnf_lcm.cancel)
    def cancel(self, request, id, body):
        """SOL003 v3.5.1 5.4.17 Resource: Cancel operation task

        @param request: A request object
        @param id: Identifier of a VNF lifecycle management operation
        occurrence to be cancelled.
        @param body: the content of the request body
        @return: A response object

        NOTE(h-asahina):
        This API is a hotfix for a bug:
        https://bugs.launchpad.net/tacker/+bug/1924917
        Thus, the API doesn't support the following features.
        - The transitions from the STARTING state and ROLLING_BACK state
        - 5.5.4.6 CancelModeType (the parameter is available, but it doesn't
        affect an actual operation)
        """

        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'cancel')
        req_body = utils.convert_camelcase_to_snakecase(body)
        _ = objects.CancelMode(context=context, **req_body)

        try:
            vnf_lcm_op_occs = objects.VnfLcmOpOcc.get_by_id(context, id)
            vnf_instance = self._get_vnf_instance(
                context, vnf_lcm_op_occs.vnf_instance_id)
        except (webob.exc.HTTPNotFound, exceptions.NotFound) as e:
            return self._make_problem_detail(
                str(e), 404, title='VNF NOT FOUND')
        except Exception as e:
            LOG.error(traceback.format_exc())
            return self._make_problem_detail(
                str(e), 500, title='Internal Server Error')

        if (vnf_lcm_op_occs.operation_state
                != fields.LcmOccsOperationState.PROCESSING):
            error_msg = ('Cancel operation in state %s is not allowed' %
                         vnf_lcm_op_occs.operation_state)
            return self._make_problem_detail(error_msg, 409, title='Conflict')

        timeout = (vnf_lcm_op_occs.state_entered_time +
                   datetime.timedelta(seconds=CONF.vnf_lcm.operation_timeout))
        if timeutils.is_newer_than(timeout, seconds=0):
            error_msg = 'Cancel operation is not allowed until %s' % timeout
            return self._make_problem_detail(error_msg, 409, title='Conflict')

        try:
            vnf_lcm_op_occs.operation_state = (
                fields.LcmOccsOperationState.FAILED_TEMP)
            vnf_lcm_op_occs.state_entered_time = timeutils.utcnow().isoformat()
            vnf_lcm_op_occs.updated_at = vnf_lcm_op_occs.state_entered_time
            vnf_lcm_op_occs.error = objects.ProblemDetails(
                context=context,
                status=500,
                detail=str(vnf_lcm_op_occs.error))

            old_vnf_instance = copy.deepcopy(vnf_instance)
            self._vnfm_plugin.update_vnf_cancel_status(
                context=context,
                vnf_id=vnf_lcm_op_occs.vnf_instance_id,
                status=constants.ERROR)
            vnf_instance.task_state = None
            vnf_instance.save()

            affected_resources = vnflcm_utils._get_affected_resources(
                old_vnf_instance=old_vnf_instance,
                new_vnf_instance=vnf_instance)
            resource_change_obj = jsonutils.dumps(
                utils.convert_camelcase_to_snakecase(affected_resources))
            changed_resource = objects.ResourceChanges.obj_from_primitive(
                resource_change_obj, context)
            vnf_lcm_op_occs.resource_changes = changed_resource
            vnf_lcm_op_occs.save()
        except Exception as e:
            error_msg = (
                'Error in VNF Cancel for vnf %s because %s' %
                (vnf_instance.id, encodeutils.exception_to_unicode(e)))
            LOG.error(error_msg)
            raise exceptions.TackerException(message=error_msg)

        self._notification_process(
            context, vnf_instance, vnf_lcm_op_occs.operation, {}, {},
            vnf_lcm_op_occs=vnf_lcm_op_occs,
            operation_state=fields.LcmOccsOperationState.FAILED_TEMP,
            notification_status=fields.LcmOccsNotificationStatus.RESULT,
            affected_resources=affected_resources)

        vnflcm_url = '%s/vnflcm/v1/vnf_lcm_op_occs/%s' % (
            CONF.vnf_lcm.endpoint_url.rstrip('/'), vnf_lcm_op_occs.id)
        return webob.Response(status=202,
                              headerlist=[('Location', vnflcm_url)])

    @wsgi.response(http_client.OK)
    @wsgi.expected_errors((http_client.BAD_REQUEST, http_client.FORBIDDEN,
                           http_client.NOT_FOUND))
    def fail(self, request, id):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'fail')

        try:
            vnf_lcm_op_occs = objects.VnfLcmOpOcc.get_by_id(context, id)
            operation = vnf_lcm_op_occs.operation

            if (vnf_lcm_op_occs.operation_state
                    != fields.LcmOccsOperationState.FAILED_TEMP):
                return self._make_problem_detail(
                    'Transitions to FAIL from state %s is not allowed' %
                    vnf_lcm_op_occs.operation_state, 409, title='Conflict')

            vnf_instance_id = vnf_lcm_op_occs.vnf_instance_id
            vnf_instance = self._get_vnf_instance(context, vnf_instance_id)
        except webob.exc.HTTPNotFound as e:
            return self._make_problem_detail(
                str(e), 404, title='VNF NOT FOUND')
        except exceptions.NotFound as e:
            return self._make_problem_detail(
                str(e), 404, title='VNF LCM NOT FOUND')
        except Exception as e:
            LOG.error(traceback.format_exc())
            return self._make_problem_detail(
                str(e), 500, title='Internal Server Error')

        try:
            old_vnf_instance = copy.deepcopy(vnf_instance)

            vnf_lcm_op_occs.operation_state = "FAILED"
            vnf_lcm_op_occs.state_entered_time = \
                datetime.datetime.utcnow().isoformat()
            vnf_lcm_op_occs.updated_at = vnf_lcm_op_occs.state_entered_time

            error_details = objects.ProblemDetails(
                context=context,
                status=500,
                detail=str(vnf_lcm_op_occs.error)
            )
            vnf_lcm_op_occs.error = error_details

            # TODO(esto-aln): For adding it to make it consistent
            # We change vnf status here. In near future, we plan to
            # delete this branch.
            if vnf_instance.instantiation_state == \
                    fields.VnfInstanceState.INSTANTIATED:
                new_status = constants.ACTIVE
            else:
                new_status = constants.INACTIVE

            self._update_vnf_fail_status(context, vnf_instance.id,
                new_status)
            vnf_instance.task_state = None
            vnf_instance.save()

            affected_resources = vnflcm_utils._get_affected_resources(
                old_vnf_instance=old_vnf_instance,
                new_vnf_instance=vnf_instance)
            resource_change_obj = jsonutils.dumps(
                utils.convert_camelcase_to_snakecase(affected_resources))
            changed_resource = objects.ResourceChanges.obj_from_primitive(
                resource_change_obj, context)
            vnf_lcm_op_occs.resource_changes = changed_resource
            vnf_lcm_op_occs.save()
        except Exception as ex:
            error_msg = "Error in VNF Fail for vnf {} because {}".format(
                vnf_instance.id, encodeutils.exception_to_unicode(ex))
            LOG.error(error_msg)
            raise exceptions.TackerException(message=error_msg)

        return self._fail(context, vnf_instance, vnf_lcm_op_occs,
                          operation, affected_resources)

    def _fail(self, context, vnf_instance, vnf_lcm_op_occs,
              operation, affected_resources):

        self._notification_process(
            context, vnf_instance, operation, {}, {},
            vnf_lcm_op_occs=vnf_lcm_op_occs,
            operation_state=fields.LcmOccsOperationState.FAILED,
            notification_status=fields.LcmOccsNotificationStatus.RESULT,
            affected_resources=affected_resources)

        return self._view_builder.show_lcm_op_occs(vnf_lcm_op_occs)

    @wsgi.response(http_client.ACCEPTED)
    @wsgi.expected_errors((http_client.BAD_REQUEST, http_client.FORBIDDEN,
                           http_client.NOT_FOUND, http_client.CONFLICT))
    def retry(self, request, id):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'retry')

        try:
            vnf_lcm_op_occs = objects.VnfLcmOpOcc.get_by_id(context, id)
        except exceptions.NotFound as lcm_e:
            return self._make_problem_detail(str(lcm_e),
                404, title='Not Found')
        except (sqlexc.SQLAlchemyError, Exception) as exc:
            LOG.exception(exc)
            return self._make_problem_detail(str(exc),
                500, title='Internal Server Error')

        # operation state checking
        if vnf_lcm_op_occs.operation_state != \
           fields.LcmOccsOperationState.FAILED_TEMP:
            error_msg = ('Cannot proceed with operation_state %s'
                % vnf_lcm_op_occs.operation_state)
            return self._make_problem_detail(error_msg,
                409, title='Conflict')

        # get vnf
        try:
            vnf = self._get_vnf(context, vnf_lcm_op_occs.vnf_instance_id)
        except webob.exc.HTTPNotFound as lcm_e:
            return self._make_problem_detail(str(lcm_e),
                404, title='Not Found')
        except Exception as exc:
            LOG.exception(exc)
            return self._make_problem_detail(str(exc),
                500, title='Internal Server Error')

        # get vnf instance
        try:
            vnf_instance = objects.VnfInstance.get_by_id(
                context, vnf_lcm_op_occs.vnf_instance_id)
        except exceptions.VnfInstanceNotFound:
            msg = (_("Can not find requested vnf instance: %s")
                % vnf_lcm_op_occs.vnf_instance_id)
            return self._make_problem_detail(msg,
                404, title='Not Found')
        except Exception as exc:
            LOG.exception(exc)
            return self._make_problem_detail(str(exc),
                500, title='Internal Server Error')

        operation = vnf_lcm_op_occs.operation
        body = jsonutils.loads(vnf_lcm_op_occs.operation_params)
        vnf['before_error_point'] = vnf_lcm_op_occs.error_point
        vnf['vnf_lcm_op_occs_id'] = id
        if operation == fields.LcmOccsOperationType.INSTANTIATE:
            self._instantiate(context, vnf_instance, vnf, body)
        elif operation == fields.LcmOccsOperationType.TERMINATE:
            self._terminate(context, vnf_instance, vnf, body)
        elif operation == fields.LcmOccsOperationType.HEAL:
            self._heal(context, vnf_instance, vnf, body)
        elif operation == fields.LcmOccsOperationType.SCALE:
            self._scale(context, vnf_instance, vnf, body)
        elif operation == fields.LcmOccsOperationType.CHANGE_EXT_CONN:
            self._change_ext_conn(context, vnf_instance, vnf, body)
        else:
            error_msg = 'Operation type %s is inavalid' % operation
            return self._make_problem_detail(error_msg,
                500, title='Internal Server Error')

    @wsgi.response(http_client.OK)
    @wsgi.expected_errors((http_client.FORBIDDEN, http_client.BAD_REQUEST))
    def list_lcm_op_occs(self, request):
        if 'tacker.context' in request.environ:
            context = request.environ['tacker.context']
            context.can(vnf_lcm_policies.VNFLCM % 'list_lcm_op_occs')

        all_fields = request.GET.get('all_fields')
        exclude_default = request.GET.get('exclude_default')
        fields = request.GET.get('fields')
        exclude_fields = request.GET.get('exclude_fields')
        filters = request.GET.get('filter')
        if not (all_fields or fields or exclude_fields):
            exclude_default = True

        nextpage = request.GET.get('nextpage_opaque_marker')
        allrecords = request.GET.get('all_records')

        result = []

        if allrecords != 'yes' and nextpage:
            self._delete_expired_nextpages(self._nextpages_lcm_op_occs)

            if nextpage in self._nextpages_lcm_op_occs:
                result = self._nextpages_lcm_op_occs.pop(nextpage)['nextpage']
        else:
            self._view_builder_op_occ.validate_attribute_fields(
                all_fields=all_fields, fields=fields,
                exclude_fields=exclude_fields,
                exclude_default=exclude_default)

            filters = self._view_builder_op_occ.validate_filter(filters)

            try:
                vnf_lcm_op_occs = (
                    vnf_lcm_op_occs_obj.VnfLcmOpOccList.get_by_filters(
                        request.context, read_deleted='no', filters=filters))
            except Exception as e:
                LOG.exception(traceback.format_exc())
                return self._make_problem_detail(
                    str(e), 500, title='Internal Server Error')

            result = self._view_builder_op_occ.index(request, vnf_lcm_op_occs,
                    all_fields=all_fields, exclude_fields=exclude_fields,
                    fields=fields, exclude_default=exclude_default)

        res = webob.Response(content_type='application/json')
        res.status_int = 200

        if allrecords != 'yes' and len(result) > CONF.vnf_lcm.lcm_op_occ_num:
            nextpageid = uuidutils.generate_uuid()
            links = ('Link', '<%s?nextpage_opaque_marker=%s>; rel="next"' % (
                request.path_url, nextpageid))
            res.headerlist.append(links)
            res.body = jsonutils.dump_as_bytes(
                result[: CONF.vnf_lcm.lcm_op_occ_num])

            self._delete_expired_nextpages(self._nextpages_lcm_op_occs)

            remain = result[CONF.vnf_lcm.lcm_op_occ_num:]
            self._nextpages_lcm_op_occs.update({nextpageid:
                {'created_time': timeutils.utcnow(), 'nextpage': remain}})
        else:
            res.body = jsonutils.dump_as_bytes(result)

        return res

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

    def _test_notification(self, context, vnf_lcm_subscription):
        resp = self.rpc_api.test_notification(context,
            vnf_lcm_subscription, cast=False)
        return resp

    @wsgi.response(http_client.ACCEPTED)
    @wsgi.expected_errors((http_client.BAD_REQUEST, http_client.FORBIDDEN,
                           http_client.NOT_FOUND, http_client.CONFLICT))
    @validation.schema(vnf_lcm.change_ext_conn)
    def change_ext_conn(self, request, id, body):
        context = request.environ['tacker.context']
        context.can(vnf_lcm_policies.VNFLCM % 'change_ext_conn')

        vnf = self._get_vnf(context, id)
        vnf_instance = self._get_vnf_instance(context, id)
        if (vnf_instance.instantiation_state !=
                fields.VnfInstanceState.INSTANTIATED):
            return self._make_problem_detail(
                'VNF is not instantiated',
                409,
                title='VNF IS NOT INSTANTIATED')
        vnf['before_error_point'] = EP.INITIAL
        self._change_ext_conn(context, vnf_instance, vnf, body)

    def _change_ext_conn(self, context, vnf_instance, vnf, request_body):
        req_body = utils.convert_camelcase_to_snakecase(request_body)
        change_ext_conn_req = objects.ChangeExtConnRequest.obj_from_primitive(
            req_body, context)

        # call notification process
        if vnf['before_error_point'] == EP.INITIAL:
            vnf_lcm_op_occs_id = self._notification_process(
                context, vnf_instance,
                fields.LcmOccsOperationType.CHANGE_EXT_CONN,
                change_ext_conn_req, request_body,
                operation_state=fields.LcmOccsOperationState.STARTING,
                notification_status=fields.LcmOccsNotificationStatus.START)
        else:
            vnf_lcm_op_occs_id = vnf['vnf_lcm_op_occs_id']

        # Call Conductor server.
        self.rpc_api.change_ext_conn(
            context,
            vnf_instance,
            vnf,
            change_ext_conn_req,
            vnf_lcm_op_occs_id)


def create_resource():
    return wsgi.Resource(VnfLcmController())
