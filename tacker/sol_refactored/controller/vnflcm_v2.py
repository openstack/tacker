# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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


from datetime import datetime

from oslo_log import log as logging
from oslo_utils import uuidutils

from tacker.sol_refactored.api.api_version import supported_versions_v2
from tacker.sol_refactored.api.schemas import vnflcm_v2 as schema
from tacker.sol_refactored.api import validator
from tacker.sol_refactored.api import wsgi as sol_wsgi
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import coordinate
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import lcm_op_occ_utils as lcmocc_utils
from tacker.sol_refactored.common import subscription_utils as subsc_utils
from tacker.sol_refactored.common import vim_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.conductor import conductor_rpc_v2
from tacker.sol_refactored.controller import vnflcm_view
from tacker.sol_refactored.nfvo import nfvo_client
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields as v2fields


LOG = logging.getLogger(__name__)  # NOTE: unused at the moment

CONF = config.CONF


class VnfLcmControllerV2(sol_wsgi.SolAPIController):

    def __init__(self):
        self.nfvo_client = nfvo_client.NfvoClient()
        self.endpoint = CONF.v2_vnfm.endpoint
        self.conductor_rpc = conductor_rpc_v2.VnfLcmRpcApiV2()
        self._inst_view = vnflcm_view.InstanceViewBuilder(self.endpoint)
        self._lcmocc_view = vnflcm_view.LcmOpOccViewBuilder(self.endpoint)
        self._subsc_view = vnflcm_view.SubscriptionViewBuilder(self.endpoint)

    def api_versions(self, request):
        return sol_wsgi.SolResponse(200, supported_versions_v2)

    @validator.schema(schema.CreateVnfRequest_V200, '2.0.0')
    def create(self, request, body):
        context = request.context
        vnfd_id = body['vnfdId']

        pkg_info = self.nfvo_client.get_vnf_package_info_vnfd(
            context, vnfd_id)
        if pkg_info.operationalState != "ENABLED":
            raise sol_ex.VnfdIdNotEnabled(vnfd_id=vnfd_id)

        vnfd = self.nfvo_client.get_vnfd(context, vnfd_id)
        vnfd_prop = vnfd.get_vnfd_properties()

        metadata = vnfd_prop['metadata']
        if 'metadata' in body:
            metadata = inst_utils.json_merge_patch(metadata, body['metadata'])

        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=vnfd_id,
            vnfProvider=pkg_info.vnfProvider,
            vnfProductName=pkg_info.vnfProductName,
            vnfSoftwareVersion=pkg_info.vnfSoftwareVersion,
            vnfdVersion=pkg_info.vnfdVersion,
            instantiationState='NOT_INSTANTIATED',
            # optional fields
            # NOTE: it is OK to absent but fill empty value to make them
            # handle easy.
            vnfInstanceName=body.get('vnfInstanceName', ""),
            vnfInstanceDescription=body.get('vnfInstanceDescription', ""),
            vnfConfigurableProperties=vnfd_prop['vnfConfigurableProperties'],
            metadata=metadata,
            extensions=vnfd_prop['extensions']
            # not set at the moment. will be set when instantiate.
            # vimConnectionInfo
            # instantiatedVnfInfo
        )

        inst.create(context)

        self.nfvo_client.send_inst_create_notification(context, inst,
                                                       self.endpoint)
        resp_body = self._inst_view.detail(inst)
        location = inst_utils.inst_href(inst.id, self.endpoint)

        return sol_wsgi.SolResponse(201, resp_body, location=location)

    def index(self, request):
        filter_param = request.GET.get('filter')
        if filter_param is not None:
            filters = self._inst_view.parse_filter(filter_param)
        else:
            filters = None
        # validate_filter

        selector = self._inst_view.parse_selector(request.GET)

        insts = inst_utils.get_inst_all(request.context)

        resp_body = self._inst_view.detail_list(insts, filters, selector)

        return sol_wsgi.SolResponse(200, resp_body)

    def show(self, request, id):
        inst = inst_utils.get_inst(request.context, id)

        resp_body = self._inst_view.detail(inst)

        return sol_wsgi.SolResponse(200, resp_body)

    @coordinate.lock_vnf_instance('{id}')
    def delete(self, request, id):
        context = request.context
        inst = inst_utils.get_inst(request.context, id)

        if inst.instantiationState != 'NOT_INSTANTIATED':
            raise sol_ex.VnfInstanceIsInstantiated(inst_id=id)

        inst.delete(context)

        # NOTE: inst record in DB deleted but inst object still
        # can be accessed.
        self.nfvo_client.send_inst_delete_notification(context, inst,
                                                       self.endpoint)
        return sol_wsgi.SolResponse(204, None)

    @validator.schema(schema.InstantiateVnfRequest_V200, '2.0.0')
    @coordinate.lock_vnf_instance('{id}')
    def instantiate(self, request, id, body):
        context = request.context
        inst = inst_utils.get_inst(context, id)

        if inst.instantiationState != 'NOT_INSTANTIATED':
            raise sol_ex.VnfInstanceIsInstantiated(inst_id=id)

        now = datetime.utcnow()
        lcmocc = objects.VnfLcmOpOccV2(
            id=uuidutils.generate_uuid(),
            operationState=v2fields.LcmOperationStateType.STARTING,
            stateEnteredTime=now,
            startTime=now,
            vnfInstanceId=id,
            operation=v2fields.LcmOperationType.INSTANTIATE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=body)

        req_param = lcmocc.operationParams
        # if there is partial vimConnectionInfo check and fulfill here.
        if req_param.obj_attr_is_set('vimConnectionInfo'):
            # if accessInfo or interfaceInfo is not specified, get from
            # VIM DB. vimId must be in VIM DB.
            req_vim_infos = req_param.vimConnectionInfo
            for key, req_vim_info in req_vim_infos.items():
                if not (req_vim_info.obj_attr_is_set('accessInfo') and
                        req_vim_info.obj_attr_is_set('interfaceInfo')):
                    vim_info = vim_utils.get_vim(context, req_vim_info.vimId)
                    req_vim_infos[key] = vim_info

        lcmocc.create(context)

        self.conductor_rpc.start_lcm_op(context, lcmocc.id)

        location = lcmocc_utils.lcmocc_href(lcmocc.id, self.endpoint)

        return sol_wsgi.SolResponse(202, None, location=location)

    @validator.schema(schema.TerminateVnfRequest_V200, '2.0.0')
    @coordinate.lock_vnf_instance('{id}')
    def terminate(self, request, id, body):
        context = request.context
        inst = inst_utils.get_inst(context, id)

        if inst.instantiationState != 'INSTANTIATED':
            raise sol_ex.VnfInstanceIsNotInstantiated(inst_id=id)

        now = datetime.utcnow()
        lcmocc = objects.VnfLcmOpOccV2(
            id=uuidutils.generate_uuid(),
            operationState=v2fields.LcmOperationStateType.STARTING,
            stateEnteredTime=now,
            startTime=now,
            vnfInstanceId=id,
            operation=v2fields.LcmOperationType.TERMINATE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=body)

        lcmocc.create(context)

        self.conductor_rpc.start_lcm_op(context, lcmocc.id)

        location = lcmocc_utils.lcmocc_href(lcmocc.id, self.endpoint)

        return sol_wsgi.SolResponse(202, None, location=location)

    @validator.schema(schema.LccnSubscriptionRequest_V200, '2.0.0')
    def subscription_create(self, request, body):
        context = request.context
        subsc = objects.LccnSubscriptionV2(
            id=uuidutils.generate_uuid(),
            callbackUri=body['callbackUri'],
            verbosity=body.get('verbosity', 'FULL')  # default is 'FULL'
        )

        if body.get('filter'):
            subsc.filter = (
                objects.LifecycleChangeNotificationsFilterV2.from_dict(
                    body['filter'])
            )

        auth_req = body.get('authentication')
        if auth_req:
            auth = objects.SubscriptionAuthentication(
                authType=auth_req['authType']
            )
            if 'BASIC' in auth.authType:
                basic_req = auth_req.get('paramsBasic')
                if basic_req is None:
                    msg = "ParmasBasic must be specified."
                    raise sol_ex.InvalidSubscription(sol_detail=msg)
                auth.paramsBasic = (
                    objects.SubscriptionAuthentication_ParamsBasic(
                        userName=basic_req.get('userName'),
                        password=basic_req.get('password')
                    )
                )

            if 'OAUTH2_CLIENT_CREDENTIALS' in auth.authType:
                oauth2_req = auth_req.get('paramsOauth2ClientCredentials')
                if oauth2_req is None:
                    msg = "paramsOauth2ClientCredentials must be specified."
                    raise sol_ex.InvalidSubscription(sol_detail=msg)
                auth.paramsOauth2ClientCredentials = (
                    objects.SubscriptionAuthentication_ParamsOauth2(
                        clientId=oauth2_req.get('clientId'),
                        clientPassword=oauth2_req.get('clientPassword'),
                        tokenEndpoint=oauth2_req.get('tokenEndpoint')
                    )
                )

            if 'TLS_CERT' in auth.authType:
                msg = "'TLS_CERT' is not supported at the moment."
                raise sol_ex.InvalidSubscription(sol_detail=msg)

            subsc.authentication = auth

        if CONF.v2_nfvo.test_callback_uri:
            subsc_utils.test_notification(subsc)

        subsc.create(context)

        resp_body = self._subsc_view.detail(subsc)
        self_href = subsc_utils.subsc_href(subsc.id, self.endpoint)

        return sol_wsgi.SolResponse(201, resp_body, location=self_href)

    def subscription_list(self, request):
        filter_param = request.GET.get('filter')
        if filter_param is not None:
            filters = self._subsc_view.parse_filter(filter_param)
        else:
            filters = None

        subscs = subsc_utils.get_subsc_all(request.context)

        resp_body = self._subsc_view.detail_list(subscs, filters)

        return sol_wsgi.SolResponse(200, resp_body)

    def subscription_show(self, request, id):
        subsc = subsc_utils.get_subsc(request.context, id)

        resp_body = self._subsc_view.detail(subsc)

        return sol_wsgi.SolResponse(200, resp_body)

    def subscription_delete(self, request, id):
        context = request.context
        subsc = subsc_utils.get_subsc(request.context, id)

        subsc.delete(context)

        return sol_wsgi.SolResponse(204, None)

    def lcm_op_occ_list(self, request):
        filter_param = request.GET.get('filter')
        if filter_param is not None:
            filters = self._lcmocc_view.parse_filter(filter_param)
        else:
            filters = None

        selector = self._lcmocc_view.parse_selector(request.GET)

        lcmoccs = lcmocc_utils.get_lcmocc_all(request.context)

        resp_body = self._lcmocc_view.detail_list(lcmoccs, filters, selector)

        return sol_wsgi.SolResponse(200, resp_body)

    def lcm_op_occ_show(self, request, id):
        lcmocc = lcmocc_utils.get_lcmocc(request.context, id)

        resp_body = self._lcmocc_view.detail(lcmocc)

        return sol_wsgi.SolResponse(200, resp_body)

    def lcm_op_occ_delete(self, request, id):
        # not allowed to delete on the specification
        if not CONF.v2_vnfm.test_enable_lcm_op_occ_delete:
            raise sol_ex.MethodNotAllowed(method='DELETE')

        # NOTE: This is for test use since it is inconvenient not to be
        # able to delete.
        context = request.context
        lcmocc = lcmocc_utils.get_lcmocc(context, id)

        lcmocc.delete(context)

        return sol_wsgi.SolResponse(204, None)
