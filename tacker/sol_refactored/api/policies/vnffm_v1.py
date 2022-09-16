# Copyright (C) 2022 Fujitsu
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


POLICY_NAME = 'os_nfv_orchestration_api_v2:vnf_fault_monitor:{}'
RULE_ANY = '@'

V1_PATH = '/vnffm/v1'
ALARMS_PATH = V1_PATH + '/alarms'
ALARMS_ID_PATH = ALARMS_PATH + '/{alarmId}'
SUBSCRIPTIONS_PATH = V1_PATH + '/subscriptions'
SUBSCRIPTIONS_ID_PATH = SUBSCRIPTIONS_PATH + '/{subscriptionId}'

POLICY_NAME_PROM_PLUGIN = 'tacker_PROM_PLUGIN_api:PROM_PLUGIN:{}'
PROM_PLUGIN_FM_PATH = '/alert'

rules = [
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('index'),
        check_str=RULE_ANY,
        description="Query FM alarms.",
        operations=[
            {'method': 'GET',
             'path': ALARMS_PATH}
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('show'),
        check_str=RULE_ANY,
        description="Query an Individual FM alarm.",
        operations=[
            {'method': 'GET',
             'path': ALARMS_ID_PATH}
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('update'),
        check_str=RULE_ANY,
        description="Modify FM alarm information.",
        operations=[
            {'method': 'PATCH',
             'path': ALARMS_ID_PATH}
        ]
    ),
    # NOTE: add when the operation supported
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
        name=POLICY_NAME_PROM_PLUGIN.format('alert'),
        check_str=RULE_ANY,
        description="Receive the alert sent from External Monitoring Tool",
        operations=[
            {'method': 'POST',
             'path': PROM_PLUGIN_FM_PATH}
        ]
    )
]


def list_rules():
    return rules
