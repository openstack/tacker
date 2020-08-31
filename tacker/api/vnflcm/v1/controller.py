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

from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import encodeutils
from oslo_utils import timeutils
from oslo_utils import uuidutils

import ast
import functools
import json
import re
import traceback

import six
from six.moves import http_client
from six.moves.urllib import parse
import webob


from tacker._i18n import _
from tacker.api.schemas import vnf_lcm
from tacker.api import validation
from tacker.api.views import vnf_lcm as vnf_lcm_view
from tacker.common import exceptions
from tacker.common import utils
from tacker.conductor.conductorrpc import vnf_lcm_rpc
import tacker.conf
from tacker.extensions import nfvo
from tacker.extensions import vnfm
from tacker import manager
from tacker import objects
from tacker.objects import fields
from tacker.objects import vnf_lcm_subscriptions as subscription_obj
from tacker.plugins.common import constants
from tacker.policies import vnf_lcm as vnf_lcm_policies
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

        # get default vim information
        vim_client_obj = vim_client.VimClient()
        default_vim = vim_client_obj.get_vim(context)

        # set vim_connection_info
        access_info = {
            'username': default_vim.get('vim_auth', {}).get('username'),
            'password': default_vim.get('vim_auth', {}).get('password'),
            'region': default_vim.get('placement_attr', {}).get('region'),
            'tenant': default_vim.get('tenant')
        }
        vim_con_info = objects.VimConnectionInfo(id=default_vim.get('vim_id'),
                            vim_id=default_vim.get('vim_id'),
                            vim_type=default_vim.get('vim_type'),
                            access_info=access_info)

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

        vnf_instance.create()

        # add default vim to vim_connection_info
        setattr(vnf_instance, 'vim_connection_info', [vim_con_info])

        # create notification data
        notification = {
            'notificationType':
                fields.LcmOccsNotificationType.VNF_ID_CREATION_NOTIFICATION,
            'vnfInstanceId': vnf_instance.id,
            'links': {
                'vnfInstance': {
                    'href': self._get_vnf_instance_href(vnf_instance)}}}

        # call send nootification
        self.rpc_api.send_notification(context, notification)
        vnf_instance.save()

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
        context.can(vnf_lcm_policies.VNFLCM % 'index')

        filters = request.GET.get('filter')
        filters = self._view_builder.validate_filter(filters)

        vnf_instances = objects.VnfInstanceList.get_by_filters(
            request.context, filters=filters)

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
        instantiation_state=[fields.VnfInstanceState.INSTANTIATED],
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

    # Generate a response when an error occurs as a problem_detail object
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
