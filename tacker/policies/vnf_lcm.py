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


from oslo_policy import policy

from tacker.policies import base


VNFLCM = 'os_nfv_orchestration_api:vnf_instances:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'create',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="Creates vnf instance.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnflcm/v1/vnf_instances'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'instantiate',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="Instantiate vnf instance.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}/instantiate'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'show',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="Query an Individual VNF instance.",
        operations=[
            {
                'method': 'GET',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'terminate',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="Terminate a VNF instance.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}/terminate'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'heal',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="Heal a VNF instance.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}/heal'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'scale',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="Scale a VNF instance.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}/scale'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'show_lcm_op_occs',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="Query an Individual VNF LCM operation occurrence",
        operations=[
            {
                'method': 'GET',
                'path': '/vnflcm/v1/vnf_lcm_op_occs/{vnfLcmOpOccId}'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'index',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="Query VNF instances.",
        operations=[
            {
                'method': 'GET',
                'path': '/vnflcm/v1/vnf_instances'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'delete',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="Delete an Individual VNF instance.",
        operations=[
            {
                'method': 'DELETE',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'update_vnf',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="Update an Individual VNF instance.",
        operations=[
            {
                'method': 'PATCH',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'rollback',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="Rollback a VNF instance.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnflcm/v1/vnf_lcm_op_occs/{vnfLcmOpOccId}/rollback'
            }
        ]
    ),
]


def list_rules():
    return rules
