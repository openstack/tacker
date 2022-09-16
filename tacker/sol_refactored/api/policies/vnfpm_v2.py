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


POLICY_NAME = 'os_nfv_orchestration_api_v2:vnf_performance_management:{}'
RULE_ANY = '@'

V2_PATH = '/vnfpm/v2'
PM_JOB_PATH = V2_PATH + '/pm_jobs'
PM_JOB_ID_PATH = PM_JOB_PATH + '/{pmJobId}'
REPORT_GET = '/vnfpm/v2/pm_jobs/{id}/reports/{report_id}'

POLICY_NAME_PROM_PLUGIN = 'tacker_PROM_PLUGIN_api:PROM_PLUGIN:{}'
PROM_PLUGIN_PM_PATH = '/pm_event'
PROM_PLUGIN_AUTO_SCALING_PATH = '/alert/vnf_instances'

rules = [
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('create'),
        check_str=RULE_ANY,
        description="Create a PM job.",
        operations=[
            {
                'method': 'POST',
                'path': PM_JOB_PATH
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('index'),
        check_str=RULE_ANY,
        description="Query PM jobs.",
        operations=[
            {
                'method': 'GET',
                'path': PM_JOB_PATH
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('update'),
        check_str=RULE_ANY,
        description="Update a PM job.",
        operations=[
            {
                'method': 'PATCH',
                'path': PM_JOB_ID_PATH
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('show'),
        check_str=RULE_ANY,
        description="Get an individual PM job.",
        operations=[
            {
                'method': 'GET',
                'path': PM_JOB_ID_PATH
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('delete'),
        check_str=RULE_ANY,
        description="Delete a PM job.",
        operations=[
            {
                'method': 'DELETE',
                'path': PM_JOB_ID_PATH
            }
        ]
    ),
    # Add new Rest API GET /vnfpm/v2/pm_jobs/{id}/reports/{report_id} to
    # get the specified PM report.
    policy.DocumentedRuleDefault(
        name=POLICY_NAME.format('report_get'),
        check_str=RULE_ANY,
        description="Get an individual performance report.",
        operations=[
            {
                'method': 'GET',
                'path': REPORT_GET
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME_PROM_PLUGIN.format('pm_event'),
        check_str=RULE_ANY,
        description="Receive the PM event sent from External Monitoring Tool",
        operations=[
            {'method': 'POST',
             'path': PROM_PLUGIN_PM_PATH}
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME_PROM_PLUGIN.format('auto_scaling'),
        check_str=RULE_ANY,
        description="auto_scaling",
        operations=[
            {'method': 'POST',
             'path': PROM_PLUGIN_AUTO_SCALING_PATH}
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POLICY_NAME_PROM_PLUGIN.format('auto_scaling_id'),
        check_str=RULE_ANY,
        description="auto_scaling_id",
        operations=[
            {'method': 'POST',
             'path': PROM_PLUGIN_AUTO_SCALING_PATH + '/{vnfInstanceId}'}
        ]
    )
]


def list_rules():
    return rules
