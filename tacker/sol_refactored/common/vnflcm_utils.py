# Copyright (C) 2023 Fujitsu
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

from oslo_utils import uuidutils

from tacker.sol_refactored.common import coordinate
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import lcm_op_occ_utils as lcmocc_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.conductor import conductor_rpc_v2
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields as v2fields


# TODO(fengyi): The code of this function is all copied from the
#  controller, which is not friendly to future development and
#  maintenance, and may be refactored in the future. After
#  refactoring, only the validation of the req body is left,
#  and the creation of lcmocc and the call to start_lcm_op are
#  all executed by the controller, notification driver, etc.
@coordinate.lock_vnf_instance('{vnf_instance_id}')
def heal(context, vnf_instance_id, body, inst=None, auto_invocation=False):
    if not inst:
        inst = inst_utils.get_inst(context, vnf_instance_id)

    if inst.instantiationState != 'INSTANTIATED':
        raise sol_ex.VnfInstanceIsNotInstantiated(inst_id=vnf_instance_id)

    lcmocc_utils.check_lcmocc_in_progress(context, vnf_instance_id)

    # check parameter for later use
    is_all = body.get('additionalParams', {}).get('all', False)
    if not isinstance(is_all, bool):
        raise sol_ex.SolValidationError(
            detail="additionalParams['all'] must be bool.")

    if 'vnfcInstanceId' in body:
        inst_info = inst.instantiatedVnfInfo
        vnfc_id = []
        if inst_info.obj_attr_is_set('vnfcInfo'):
            vnfc_id = [vnfc.id for vnfc in inst_info.vnfcInfo]
        for req_vnfc_id in body['vnfcInstanceId']:
            if req_vnfc_id not in vnfc_id:
                raise sol_ex.SolValidationError(
                    detail="vnfcInstanceId(%s) does not exist."
                           % req_vnfc_id)

    lcmocc = new_lcmocc(vnf_instance_id, v2fields.LcmOperationType.HEAL, body,
                        auto_invocation=auto_invocation)
    lcmocc.create(context)

    rpc = conductor_rpc_v2.VnfLcmRpcApiV2()
    rpc.start_lcm_op(context, lcmocc.id)
    return lcmocc


# TODO(fengyi): The code of this function is all copied from the
#  controller, which is not friendly to future development and
#  maintenance, and may be refactored in the future. After
#  refactoring, only the validation of the req body is left,
#  and the creation of lcmocc and the call to start_lcm_op are
#  all executed by the controller, notification driver, etc.
@coordinate.lock_vnf_instance('{vnf_instance_id}')
def scale(context, vnf_instance_id, body, inst=None, auto_invocation=False):
    if not inst:
        inst = inst_utils.get_inst(context, vnf_instance_id)

    if inst.instantiationState != 'INSTANTIATED':
        raise sol_ex.VnfInstanceIsNotInstantiated(inst_id=vnf_instance_id)

    lcmocc_utils.check_lcmocc_in_progress(context, vnf_instance_id)

    # check parameters
    aspect_id = body['aspectId']
    if 'numberOfSteps' not in body:
        # set default value (1) defined by SOL specification for
        # the convenience of the following methods.
        body['numberOfSteps'] = 1

    scale_level = _get_current_scale_level(inst, aspect_id)
    max_scale_level = _get_max_scale_level(inst, aspect_id)
    if scale_level is None or max_scale_level is None:
        raise sol_ex.InvalidScaleAspectId(aspect_id=aspect_id)

    num_steps = body['numberOfSteps']
    if body['type'] == 'SCALE_IN':
        num_steps *= -1
    scale_level += num_steps
    if scale_level < 0 or scale_level > max_scale_level:
        raise sol_ex.InvalidScaleNumberOfSteps(
            num_steps=body['numberOfSteps'])

    lcmocc = new_lcmocc(vnf_instance_id, v2fields.LcmOperationType.SCALE, body,
                        auto_invocation=auto_invocation)
    lcmocc.create(context)

    rpc = conductor_rpc_v2.VnfLcmRpcApiV2()
    rpc.start_lcm_op(context, lcmocc.id)
    return lcmocc


def _get_current_scale_level(inst, aspect_id):
    if (inst.obj_attr_is_set('instantiatedVnfInfo') and
            inst.instantiatedVnfInfo.obj_attr_is_set('scaleStatus')):
        for scale_info in inst.instantiatedVnfInfo.scaleStatus:
            if scale_info.aspectId == aspect_id:
                return scale_info.scaleLevel


def _get_max_scale_level(inst, aspect_id):
    if (inst.obj_attr_is_set('instantiatedVnfInfo') and
            inst.instantiatedVnfInfo.obj_attr_is_set('maxScaleLevels')):
        for scale_info in inst.instantiatedVnfInfo.maxScaleLevels:
            if scale_info.aspectId == aspect_id:
                return scale_info.scaleLevel


def new_lcmocc(inst_id, operation, req_body,
               op_state=v2fields.LcmOperationStateType.STARTING,
               auto_invocation=False):
    now = datetime.utcnow()
    lcmocc = objects.VnfLcmOpOccV2(
        id=uuidutils.generate_uuid(),
        operationState=op_state,
        stateEnteredTime=now,
        startTime=now,
        vnfInstanceId=inst_id,
        operation=operation,
        isAutomaticInvocation=auto_invocation,
        isCancelPending=False,
        operationParams=req_body)

    return lcmocc
