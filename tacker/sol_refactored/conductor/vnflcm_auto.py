# Copyright (C) 2024 Nippon Telegraph and Telephone Corporation
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

from tacker.sol_refactored.common import coordinate
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import lcm_op_occ_utils as lcmocc_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.objects.v2 import fields as v2fields


@coordinate.lock_vnf_instance('{vnf_instance_id}')
def _auto_heal_pre(context, vnf_instance_id, heal_req):
    # NOTE: validation check of heal_req is not necessary since it is
    # made by conductor.
    inst = inst_utils.get_inst(context, vnf_instance_id)

    if inst.instantiationState != 'INSTANTIATED':
        raise sol_ex.VnfInstanceIsNotInstantiated(inst_id=vnf_instance_id)

    lcmocc_utils.check_lcmocc_in_progress(context, vnf_instance_id)

    if 'vnfcInstanceId' in heal_req:
        inst_utils.check_vnfc_ids(inst, heal_req['vnfcInstanceId'])

    lcmocc = lcmocc_utils.new_lcmocc(
        vnf_instance_id, v2fields.LcmOperationType.HEAL, heal_req,
        auto_invocation=True)
    lcmocc.create(context)

    return lcmocc


def auto_heal(context, vnf_instance_id, heal_req, conductor):
    lcmocc = _auto_heal_pre(context, vnf_instance_id, heal_req)
    conductor.start_lcm_op_internal(context, lcmocc)


@coordinate.lock_vnf_instance('{vnf_instance_id}')
def _auto_scale_pre(context, vnf_instance_id, scale_req):
    # NOTE: validation check of scale_req is not necessary since it is
    # made by conductor.
    inst = inst_utils.get_inst(context, vnf_instance_id)

    if inst.instantiationState != 'INSTANTIATED':
        raise sol_ex.VnfInstanceIsNotInstantiated(inst_id=vnf_instance_id)

    lcmocc_utils.check_lcmocc_in_progress(context, vnf_instance_id)

    if 'numberOfSteps' not in scale_req:
        scale_req['numberOfSteps'] = 1
    inst_utils.check_scale_level(inst, scale_req['aspectId'],
                                 scale_req['type'], scale_req['numberOfSteps'])

    lcmocc = lcmocc_utils.new_lcmocc(
        vnf_instance_id, v2fields.LcmOperationType.SCALE, scale_req,
        auto_invocation=True)
    lcmocc.create(context)

    return lcmocc


def auto_scale(context, vnf_instance_id, scale_req, conductor):
    lcmocc = _auto_scale_pre(context, vnf_instance_id, scale_req)
    conductor.start_lcm_op_internal(context, lcmocc)
