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
        name=VNFLCM % 'api_versions',
        check_str=base.RULE_ANY,
        description="Get API Versions.",
        operations=[
            {
                'method': 'GET',
                'path': '/vnflcm/v1/api_versions'
            }
        ],
        scope_types=['project'],
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'create',
        check_str=base.RULE_PROJECT_MEMBER_OR_ADMIN,
        description="Creates vnf instance.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnflcm/v1/vnf_instances'
            }
        ],
        scope_types=['project'],
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'instantiate',
        check_str=base.RULE_PROJECT_MEMBER_OR_ADMIN,
        description="Instantiate vnf instance.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}/instantiate'
            }
        ],
        scope_types=['project'],
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'show',
        check_str=base.RULE_PROJECT_READER_OR_ADMIN,
        description="Query an Individual VNF instance.",
        operations=[
            {
                'method': 'GET',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}'
            }
        ],
        scope_types=['project'],
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'terminate',
        check_str=base.RULE_PROJECT_MEMBER_OR_ADMIN,
        description="Terminate a VNF instance.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}/terminate'
            }
        ],
        scope_types=['project'],
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'heal',
        check_str=base.RULE_PROJECT_MEMBER_OR_ADMIN,
        description="Heal a VNF instance.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}/heal'
            }
        ],
        scope_types=['project'],
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'scale',
        check_str=base.RULE_PROJECT_MEMBER_OR_ADMIN,
        description="Scale a VNF instance.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}/scale'
            }
        ],
        scope_types=['project'],
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'show_lcm_op_occs',
        check_str=base.RULE_PROJECT_READER_OR_ADMIN,
        description="Query an Individual VNF LCM operation occurrence",
        operations=[
            {
                'method': 'GET',
                'path': '/vnflcm/v1/vnf_lcm_op_occs/{vnfLcmOpOccId}'
            }
        ],
        scope_types=['project'],
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'list_lcm_op_occs',
        check_str=base.RULE_PROJECT_READER_OR_ADMIN,
        description="Query VNF LCM operation occurrence",
        operations=[
            {
                'method': 'GET',
                'path': '/vnflcm/v1/vnf_lcm_op_occs'
            }
        ],
        scope_types=['project'],
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'index',
        check_str=base.RULE_PROJECT_READER_OR_ADMIN,
        description="Query VNF instances.",
        operations=[
            {
                'method': 'GET',
                'path': '/vnflcm/v1/vnf_instances'
            }
        ],
        scope_types=['project'],
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'delete',
        check_str=base.RULE_PROJECT_MEMBER_OR_ADMIN,
        description="Delete an Individual VNF instance.",
        operations=[
            {
                'method': 'DELETE',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}'
            }
        ],
        scope_types=['project'],
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'update_vnf',
        check_str=base.RULE_PROJECT_MEMBER_OR_ADMIN,
        description="Update an Individual VNF instance.",
        operations=[
            {
                'method': 'PATCH',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}'
            }
        ],
        scope_types=['project'],
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'rollback',
        check_str=base.RULE_PROJECT_MEMBER_OR_ADMIN,
        description="Rollback a VNF instance.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnflcm/v1/vnf_lcm_op_occs/{vnfLcmOpOccId}/rollback'
            }
        ],
        scope_types=['project'],
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'cancel',
        check_str=base.RULE_PROJECT_MEMBER_OR_ADMIN,
        description="Cancel a VNF instance.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnflcm/v1/vnf_lcm_op_occs/{vnfLcmOpOccId}/cancel'
            }
        ],
        scope_types=['project'],
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'fail',
        check_str=base.RULE_PROJECT_MEMBER_OR_ADMIN,
        description="Fail a VNF instance.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnflcm/v1/vnf_lcm_op_occs/{vnfLcmOpOccId}/fail'
            }
        ],
        scope_types=['project'],
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'retry',
        check_str=base.RULE_PROJECT_MEMBER_OR_ADMIN,
        description="Retry a VNF instance.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnflcm/v1/vnf_lcm_op_occs/{vnfLcmOpOccId}/retry'
            }
        ],
        scope_types=['project'],
    ),
    policy.DocumentedRuleDefault(
        name=VNFLCM % 'change_ext_conn',
        check_str=base.RULE_PROJECT_MEMBER_OR_ADMIN,
        description="Change external VNF connectivity.",
        operations=[
            {
                'method': 'POST',
                'path':
                    '/vnflcm/v1/vnf_instances/{vnfInstanceId}/change_ext_conn'
            }
        ],
        scope_types=['project'],
    ),
]


def list_rules():
    return rules
