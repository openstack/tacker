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


from oslo_policy import policy


POLICY_NAME = 'os_nfv_orchestration_api_v2:vnf_instances:{}'
RULE_ANY = '@'

V2_PATH = '/vnflcm/v2'
API_VERSIONS_PATH = V2_PATH + '/api_versions'
VNF_INSTANCES_PATH = V2_PATH + '/vnf_instances'
VNF_INSTANCES_ID_PATH = VNF_INSTANCES_PATH + '/{vnfInstanceId}'
SUBSCRIPTIONS_PATH = V2_PATH + '/subscriptions'
SUBSCRIPTIONS_ID_PATH = VNF_INSTANCES_PATH + '/{subscriptionId}'
VNF_LCM_OP_OCCS_PATH = V2_PATH + '/vnf_lcm_op_occs'
VNF_LCM_OP_OCCS_ID_PATH = VNF_LCM_OP_OCCS_PATH + '/{vnfLcmOpOccId}'

rules = [
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('api_versions'),
        check_str=RULE_ANY,
        description="Get API Versions.",
        operations=[
            {'method': 'GET',
             'path': API_VERSIONS_PATH}
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('create'),
        check_str=RULE_ANY,
        description="Creates vnf instance.",
        operations=[
            {'method': 'POST',
             'path': VNF_INSTANCES_PATH}
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('index'),
        check_str=RULE_ANY,
        description="Query VNF instances.",
        operations=[
            {'method': 'GET',
             'path': VNF_INSTANCES_PATH}
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('show'),
        check_str=RULE_ANY,
        description="Query an Individual VNF instance.",
        operations=[
            {'method': 'GET',
             'path': VNF_INSTANCES_ID_PATH}
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('delete'),
        check_str=RULE_ANY,
        description="Delete an Individual VNF instance.",
        operations=[
            {'method': 'DELETE',
             'path': VNF_INSTANCES_ID_PATH}
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('instantiate'),
        check_str=RULE_ANY,
        description="Instantiate vnf instance.",
        operations=[
            {'method': 'POST',
             'path': VNF_INSTANCES_ID_PATH + '/instantiate'}
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('terminate'),
        check_str=RULE_ANY,
        description="Terminate vnf instance.",
        operations=[
            {'method': 'POST',
             'path': VNF_INSTANCES_ID_PATH + '/terminate'}
        ]
    ),

    # TODO(oda-g): add more lcm operations etc when implemented.

    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('subscription_create'),
        check_str=RULE_ANY,
        description="Create subscription.",
        operations=[
            {'method': 'POST',
             'path': SUBSCRIPTIONS_PATH}
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('subscription_list'),
        check_str=RULE_ANY,
        description="List subscription.",
        operations=[
            {'method': 'GET',
             'path': SUBSCRIPTIONS_PATH}
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('subscription_show'),
        check_str=RULE_ANY,
        description="Show subscription.",
        operations=[
            {'method': 'GET',
             'path': SUBSCRIPTIONS_ID_PATH}
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('subscription_delete'),
        check_str=RULE_ANY,
        description="Delete subscription.",
        operations=[
            {'method': 'DELETE',
             'path': SUBSCRIPTIONS_ID_PATH}
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('lcm_op_occ_list'),
        check_str=RULE_ANY,
        description="List VnfLcmOpOcc.",
        operations=[
            {'method': 'GET',
             'path': VNF_LCM_OP_OCCS_PATH}
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('lcm_op_occ_show'),
        check_str=RULE_ANY,
        description="Show VnfLcmOpOcc.",
        operations=[
            {'method': 'GET',
             'path': VNF_LCM_OP_OCCS_ID_PATH}
        ]
    ),
    # NOTE: 'DELETE' is not defined in the specification. It is for test
    # use since it is convenient to be able to delete under development.
    # It is available when config parameter
    # v2_vnfm.test_enable_lcm_op_occ_delete set to True.
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('lcm_op_occ_delete'),
        check_str=RULE_ANY,
        description="Delete VnfLcmOpOcc.",
        operations=[
            {'method': 'DELETE',
             'path': VNF_LCM_OP_OCCS_ID_PATH}
        ]
    ),
]


def list_rules():
    return rules
