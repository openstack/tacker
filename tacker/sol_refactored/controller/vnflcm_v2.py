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


from oslo_log import log as logging
from oslo_utils import uuidutils

from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.api.policies.vnflcm_v2 import POLICY_NAME
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
from tacker.sol_refactored.common import vnflcm_utils
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
        return sol_wsgi.SolResponse(200, api_version.supported_versions_v2)

    @validator.schema(schema.CreateVnfRequest_V200, '2.0.0')
    def create(self, request, body):
        context = request.context
        vnfd_id = body['vnfdId']

        pkg_info = self.nfvo_client.get_vnf_package_info_vnfd(
            context, vnfd_id)
        if config.CONF.oslo_policy.enhanced_tacker_policy:
            context.can(POLICY_NAME.format('create'),
                        target={'vendor': pkg_info.vnfProvider})

        if pkg_info.operationalState != "ENABLED":
            raise sol_ex.VnfdIdNotEnabled(vnfd_id=vnfd_id)

        vnfd = self.nfvo_client.get_vnfd(context, vnfd_id)
        vnfd_prop = vnfd.get_vnfd_properties()

        metadata = vnfd_prop['metadata']
        if 'metadata' in body:
            metadata = inst_utils.json_merge_patch(metadata, body['metadata'])
            inst_utils.check_metadata_format(metadata)

        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=vnfd_id,
            vnfProvider=pkg_info.vnfProvider,
            vnfProductName=pkg_info.vnfProductName,
            vnfSoftwareVersion=pkg_info.vnfSoftwareVersion,
            vnfdVersion=pkg_info.vnfdVersion,
            instantiationState='NOT_INSTANTIATED',
            # not set at the moment. will be set when instantiate.
            # vimConnectionInfo
            # instantiatedVnfInfo
        )

        # set optional fields
        if body.get('vnfInstanceName'):
            inst.vnfInstanceName = body['vnfInstanceName']
        if body.get('vnfInstanceDescription'):
            inst.vnfInstanceDescription = body['vnfInstanceDescription']
        if vnfd_prop.get('vnfConfigurableProperties'):
            inst.vnfConfigurableProperties = vnfd_prop[
                'vnfConfigurableProperties']
        if metadata:
            inst.metadata = metadata
        if vnfd_prop.get('extensions'):
            inst.extensions = vnfd_prop['extensions']

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

        pager = self._inst_view.parse_pager(request)

        insts = inst_utils.get_inst_all(request.context,
                                        marker=pager.marker)
        if config.CONF.oslo_policy.enhanced_tacker_policy:
            insts = [inst for inst in insts if request.context.can(
                POLICY_NAME.format('index'),
                target=self._get_policy_target(inst),
                fatal=False)]

        resp_body = self._inst_view.detail_list(insts, filters,
                                                selector, pager)

        return sol_wsgi.SolResponse(200, resp_body, link=pager.get_link())

    def show(self, request, id):
        inst = inst_utils.get_inst(request.context, id)
        if config.CONF.oslo_policy.enhanced_tacker_policy:
            request.context.can(POLICY_NAME.format('show'),
                                target=self._get_policy_target(inst))
        resp_body = self._inst_view.detail(inst)

        return sol_wsgi.SolResponse(200, resp_body)

    @coordinate.lock_vnf_instance('{id}')
    def delete(self, request, id):
        context = request.context
        inst = inst_utils.get_inst(context, id)
        if config.CONF.oslo_policy.enhanced_tacker_policy:
            context.can(POLICY_NAME.format('delete'),
                        target=self._get_policy_target(inst))
        if inst.instantiationState != 'NOT_INSTANTIATED':
            raise sol_ex.VnfInstanceIsInstantiated(inst_id=id)

        lcmocc_utils.check_lcmocc_in_progress(context, id)

        inst.delete(context)

        # NOTE: inst record in DB deleted but inst object still
        # can be accessed.
        self.nfvo_client.send_inst_delete_notification(context, inst,
                                                       self.endpoint)
        return sol_wsgi.SolResponse(204, None)

    @validator.schema(schema.VnfInfoModificationRequest_V200, '2.0.0')
    @coordinate.lock_vnf_instance('{id}')
    def update(self, request, id, body):
        context = request.context
        inst = inst_utils.get_inst(context, id)
        if config.CONF.oslo_policy.enhanced_tacker_policy:
            context.can(POLICY_NAME.format('update'),
                        target=self._get_policy_target(inst))
        lcmocc_utils.check_lcmocc_in_progress(context, id)
        if (inst.instantiationState == 'NOT_INSTANTIATED'
                and 'vimConnectionInfo' in body):
            msg = 'vimConnectionInfo cannot be modified in NOT_INSTANTIATED.'
            raise sol_ex.SolValidationError(detail=msg)

        # check vnf package operational state
        if 'vnfdId' in body and body['vnfdId'] != inst.vnfdId:
            req_vnfd_id = body['vnfdId']
            pkg_info = self.nfvo_client.get_vnf_package_info_vnfd(
                context, req_vnfd_id)
            if pkg_info.operationalState != "ENABLED":
                # NOTE: Response code 422 is not specified in SOL003,
                # but 422 will be returned here. This is because
                # instance create returns 422 for the same reason.
                # In addition, SOL013 defines 422 as common error situations.
                raise sol_ex.VnfdIdNotEnabled(vnfd_id=req_vnfd_id)

        if 'vnfcInfoModifications' in body:
            vnfc_id = []
            if inst.obj_attr_is_set('instantiatedVnfInfo'):
                inst_info = inst.instantiatedVnfInfo
                if inst_info.obj_attr_is_set('vnfcInfo'):
                    vnfc_id = [vnfc.id for vnfc in inst_info.vnfcInfo]
            for vnfc_mod in body['vnfcInfoModifications']:
                if vnfc_mod['id'] not in vnfc_id:
                    raise sol_ex.SolValidationError(
                        detail="vnfcInstanceId(%s) does not exist."
                        % vnfc_mod['id'])

        lcmocc = vnflcm_utils.new_lcmocc(
            id, v2fields.LcmOperationType.MODIFY_INFO,
            body, v2fields.LcmOperationStateType.PROCESSING)
        lcmocc.create(context)

        self.conductor_rpc.modify_vnfinfo(context, lcmocc.id)

        location = lcmocc_utils.lcmocc_href(lcmocc.id, self.endpoint)

        return sol_wsgi.SolResponse(202, None, location=location)

    def _get_policy_target(self, vnf_instance):
        vendor = vnf_instance.vnfProvider

        if vnf_instance.instantiationState == 'NOT_INSTANTIATED':
            area = '*'
            tenant = '*'
        else:
            vim_type = None
            area = None
            if vnf_instance.obj_attr_is_set('vimConnectionInfo'):
                for _, vim_conn_info in vnf_instance.vimConnectionInfo.items():
                    area = vim_conn_info.get('extra', {}).get('area')
                    vim_type = vim_conn_info.vimType
                    if area and vim_type:
                        break

            tenant = None
            if (vnf_instance.obj_attr_is_set('instantiatedVnfInfo') and
                    vnf_instance.instantiatedVnfInfo.obj_attr_is_set(
                        'metadata')):
                tenant = (vnf_instance.instantiatedVnfInfo
                          .metadata.get('tenant'))

        target = {
            'vendor': vendor,
            'area': area,
            'tenant': tenant
        }

        target = {k: v for k, v in target.items() if v is not None}

        return target

    @validator.schema(schema.InstantiateVnfRequest_V200, '2.0.0')
    @coordinate.lock_vnf_instance('{id}')
    def instantiate(self, request, id, body):
        context = request.context
        inst = inst_utils.get_inst(context, id)
        if config.CONF.oslo_policy.enhanced_tacker_policy:
            context.can(POLICY_NAME.format('instantiate'),
                        target=self._get_policy_target(inst))

        if inst.instantiationState != 'NOT_INSTANTIATED':
            raise sol_ex.VnfInstanceIsInstantiated(inst_id=id)

        lcmocc_utils.check_lcmocc_in_progress(context, id)

        lcmocc = vnflcm_utils.new_lcmocc(
            id, v2fields.LcmOperationType.INSTANTIATE, body)

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
        if config.CONF.oslo_policy.enhanced_tacker_policy:
            context.can(POLICY_NAME.format('terminate'),
                        target=self._get_policy_target(inst))

        if inst.instantiationState != 'INSTANTIATED':
            raise sol_ex.VnfInstanceIsNotInstantiated(inst_id=id)

        lcmocc_utils.check_lcmocc_in_progress(context, id)

        lcmocc = vnflcm_utils.new_lcmocc(
            id, v2fields.LcmOperationType.TERMINATE, body)
        lcmocc.create(context)

        self.conductor_rpc.start_lcm_op(context, lcmocc.id)

        location = lcmocc_utils.lcmocc_href(lcmocc.id, self.endpoint)

        return sol_wsgi.SolResponse(202, None, location=location)

    @validator.schema(schema.ScaleVnfRequest_V200, '2.0.0')
    def scale(self, request, id, body):
        context = request.context
        inst = inst_utils.get_inst(context, id)
        if config.CONF.oslo_policy.enhanced_tacker_policy:
            context.can(POLICY_NAME.format('scale'),
                        target=self._get_policy_target(inst))

        lcmocc = vnflcm_utils.scale(context, id, body, inst=inst)

        location = lcmocc_utils.lcmocc_href(lcmocc.id, self.endpoint)

        return sol_wsgi.SolResponse(202, None, location=location)

    @validator.schema(schema.HealVnfRequest_V200, '2.0.0')
    def heal(self, request, id, body):
        context = request.context
        inst = inst_utils.get_inst(context, id)
        if config.CONF.oslo_policy.enhanced_tacker_policy:
            context.can(POLICY_NAME.format('heal'),
                        target=self._get_policy_target(inst))

        lcmocc = vnflcm_utils.heal(context, id, body, inst=inst)

        location = lcmocc_utils.lcmocc_href(lcmocc.id, self.endpoint)

        return sol_wsgi.SolResponse(202, None, location=location)

    @validator.schema(schema.ChangeExtVnfConnectivityRequest_V200, '2.0.0')
    @coordinate.lock_vnf_instance('{id}')
    def change_ext_conn(self, request, id, body):
        context = request.context
        inst = inst_utils.get_inst(context, id)
        if config.CONF.oslo_policy.enhanced_tacker_policy:
            context.can(POLICY_NAME.format('change_ext_conn'),
                        target=self._get_policy_target(inst))

        if inst.instantiationState != 'INSTANTIATED':
            raise sol_ex.VnfInstanceIsNotInstantiated(inst_id=id)

        lcmocc_utils.check_lcmocc_in_progress(context, id)

        lcmocc = vnflcm_utils.new_lcmocc(
            id, v2fields.LcmOperationType.CHANGE_EXT_CONN, body)
        lcmocc.create(context)

        self.conductor_rpc.start_lcm_op(context, lcmocc.id)

        location = lcmocc_utils.lcmocc_href(lcmocc.id, self.endpoint)

        return sol_wsgi.SolResponse(202, None, location=location)

    def _check_vdu_params(self, inst, vdu_params, vim_type, new_script,
            old_script):
        inst_vdu_ids = []
        if inst.instantiatedVnfInfo.obj_attr_is_set('vnfcResourceInfo'):
            inst_vdu_ids = [inst_vnfc.vduId
                for inst_vnfc in inst.instantiatedVnfInfo.vnfcResourceInfo]

        for vdu_param in vdu_params:
            if 'vdu_id' not in vdu_param:
                raise sol_ex.SolValidationError(
                    detail="If you set vdu_params in additionalParams, you"
                           "must set vdu_id for each element.")
            if vdu_param['vdu_id'] not in inst_vdu_ids:
                raise sol_ex.SolValidationError(
                    detail="vdu_id '%s' does not exist." % vdu_param['vdu_id'])

            def _check_vnfc_param(attr):
                for key in ['cp_name', 'username', 'password']:
                    if key not in vdu_param[attr]:
                        raise sol_ex.SolValidationError(
                            detail=f"If you set {attr} in "
                                   f"vdu_param, you must set"
                                   f" 'cp_name', 'username' and"
                                   f" 'password'")

            if vim_type == 'ETSINFV.OPENSTACK_KEYSTONE.V_3' and new_script:
                if 'new_vnfc_param' not in vdu_param:
                    raise sol_ex.SolValidationError(
                        detail="'new_vnfc_param' must exist in vdu_param")
                _check_vnfc_param('new_vnfc_param')

            if vim_type == 'ETSINFV.OPENSTACK_KEYSTONE.V_3' and old_script:
                if 'old_vnfc_param' not in vdu_param:
                    raise sol_ex.SolValidationError(
                        detail="'old_vnfc_param' must exist in vdu_param")
                _check_vnfc_param('old_vnfc_param')

    @validator.schema(schema.ChangeCurrentVnfPkgRequest_V200, '2.0.0')
    @coordinate.lock_vnf_instance('{id}')
    def change_vnfpkg(self, request, id, body):
        context = request.context
        inst = inst_utils.get_inst(context, id)
        if config.CONF.oslo_policy.enhanced_tacker_policy:
            context.can(POLICY_NAME.format('change_vnfpkg'),
                        target=self._get_policy_target(inst))
        vnfd_id = body['vnfdId']

        if inst.instantiationState != 'INSTANTIATED':
            raise sol_ex.VnfInstanceIsNotInstantiated(inst_id=id)

        lcmocc_utils.check_lcmocc_in_progress(context, id)

        pkg_info = self.nfvo_client.get_vnf_package_info_vnfd(
            context, vnfd_id)
        if pkg_info.operationalState != "ENABLED":
            raise sol_ex.VnfdIdNotEnabled(vnfd_id=vnfd_id)

        additional_params = body.get('additionalParams')
        if additional_params is None:
            raise sol_ex.SolValidationError(
                detail="Change Current VNF Package "
                       "operation must have 'additionalParams'")
        upgrade_type = additional_params.get('upgrade_type', '')
        if upgrade_type != 'RollingUpdate':
            raise sol_ex.NotSupportUpgradeType(upgrade_type=upgrade_type)
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        vdu_params = additional_params.get('vdu_params')
        if vdu_params is None:
            raise sol_ex.SolValidationError(
                detail="'vdu_params' must exist in additionalParams")
        self._check_vdu_params(inst, vdu_params, vim_info.vimType,
            additional_params.get('lcm-operation-coordinate-new-vnf'),
            additional_params.get('lcm-operation-coordinate-old-vnf'))
        if (vim_info.vimType == 'ETSINFV.KUBERNETES.V_1' and
                not additional_params.get('lcm-kubernetes-def-files')):
            raise sol_ex.SolValidationError(
                detail="'lcm-kubernetes-def-files' must be specified")

        lcmocc = vnflcm_utils.new_lcmocc(
            id, v2fields.LcmOperationType.CHANGE_VNFPKG, body)

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
            subsc.authentication = subsc_utils.get_subsc_auth(auth_req)

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

        pager = self._subsc_view.parse_pager(request)

        subscs = subsc_utils.get_subsc_all(request.context,
                                           marker=pager.marker)

        resp_body = self._subsc_view.detail_list(subscs, filters, pager)

        return sol_wsgi.SolResponse(200, resp_body, link=pager.get_link())

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

        pager = self._lcmocc_view.parse_pager(request)

        lcmoccs = lcmocc_utils.get_lcmocc_all(request.context,
                                              marker=pager.marker)

        resp_body = self._lcmocc_view.detail_list(lcmoccs, filters,
                                                  selector, pager)

        return sol_wsgi.SolResponse(200, resp_body, link=pager.get_link())

    def lcm_op_occ_show(self, request, id):
        lcmocc = lcmocc_utils.get_lcmocc(request.context, id)

        resp_body = self._lcmocc_view.detail(lcmocc)

        return sol_wsgi.SolResponse(200, resp_body)

    def lcm_op_occ_retry(self, request, id):
        context = request.context
        lcmocc = lcmocc_utils.get_lcmocc(context, id)

        return self._lcm_op_occ_retry(context, lcmocc)

    @coordinate.lock_vnf_instance('{lcmocc.vnfInstanceId}')
    def _lcm_op_occ_retry(self, context, lcmocc):
        if lcmocc.operationState != v2fields.LcmOperationStateType.FAILED_TEMP:
            raise sol_ex.LcmOpOccNotFailedTemp(lcmocc_id=lcmocc.id)

        # TODO(YiFeng) support retry operation for CNF instantiate
        # At present, the retry operation will fail for instantiate with
        # kubernetes vim.
        if lcmocc.operation == v2fields.LcmOperationType.INSTANTIATE:
            if lcmocc.operationParams.obj_attr_is_set('vimConnectionInfo'):
                vim_infos = lcmocc.operationParams.vimConnectionInfo
            else:
                vim_info = vim_utils.get_default_vim(context)
                vim_infos = {"default": vim_info}
        else:
            inst = inst_utils.get_inst(context, lcmocc.vnfInstanceId)
            vim_infos = inst.vimConnectionInfo
        vim_info = inst_utils.select_vim_info(vim_infos)

        self.conductor_rpc.retry_lcm_op(context, lcmocc.id)

        return sol_wsgi.SolResponse(202, None)

    def lcm_op_occ_rollback(self, request, id):
        context = request.context
        lcmocc = lcmocc_utils.get_lcmocc(context, id)

        return self._lcm_op_occ_rollback(context, lcmocc)

    @coordinate.lock_vnf_instance('{lcmocc.vnfInstanceId}')
    def _lcm_op_occ_rollback(self, context, lcmocc):
        if lcmocc.operationState != v2fields.LcmOperationStateType.FAILED_TEMP:
            raise sol_ex.LcmOpOccNotFailedTemp(lcmocc_id=lcmocc.id)

        # TODO(YiFeng) support rollback operation for CNF instantiate
        # At present, the rollback operation will fail for instantiate with
        # kubernetes vim.
        if lcmocc.operation == v2fields.LcmOperationType.INSTANTIATE:
            if lcmocc.operationParams.obj_attr_is_set('vimConnectionInfo'):
                vim_infos = lcmocc.operationParams.vimConnectionInfo
            else:
                vim_info = vim_utils.get_default_vim(context)
                vim_infos = {"default": vim_info}
        else:
            inst = inst_utils.get_inst(context, lcmocc.vnfInstanceId)
            vim_infos = inst.vimConnectionInfo
        vim_info = inst_utils.select_vim_info(vim_infos)

        self.conductor_rpc.rollback_lcm_op(context, lcmocc.id)

        return sol_wsgi.SolResponse(202, None)

    def lcm_op_occ_fail(self, request, id):
        context = request.context
        lcmocc = lcmocc_utils.get_lcmocc(context, id)

        return self._lcm_op_occ_fail(context, lcmocc)

    @coordinate.lock_vnf_instance('{lcmocc.vnfInstanceId}')
    def _lcm_op_occ_fail(self, context, lcmocc):
        if lcmocc.operationState != v2fields.LcmOperationStateType.FAILED_TEMP:
            raise sol_ex.LcmOpOccNotFailedTemp(lcmocc_id=lcmocc.id)

        inst = inst_utils.get_inst(context, lcmocc.vnfInstanceId)
        grant_req, grant = lcmocc_utils.get_grant_req_and_grant(context,
                                                                lcmocc)

        lcmocc_utils.update_lcmocc_status(
            lcmocc, v2fields.LcmOperationStateType.FAILED)
        with context.session.begin(subtransactions=True):
            lcmocc.update(context)
            if grant_req is not None:
                grant_req.delete(context)
                grant.delete(context)

        # send notification FAILED
        self.nfvo_client.send_lcmocc_notification(context, lcmocc, inst,
                                                  self.endpoint)

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

    def supported_api_versions(self, action):
        if action == 'api_versions':
            # support all versions and it is OK there is no Version header.
            return None
        else:
            return api_version.v2_versions

    def allowed_content_types(self, action):
        if action == 'update':
            # Content-Type of Modify request shall be
            # 'application/merge-patch+json' according to SOL spec.
            # But 'application/json' and 'text/plain' is OK for backward
            # compatibility.
            return ['application/merge-patch+json', 'application/json',
                    'text/plain']
        else:
            return ['application/json', 'text/plain']

    def set_default_to_response(self, result, action):
        result.headers.setdefault('version', api_version.CURRENT_VERSION)
        result.headers.setdefault('accept-ranges', 'none')
