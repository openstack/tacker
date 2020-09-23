# Copyright (C) 2019 NTT DATA
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


VNFPKGM = 'os_nfv_orchestration_api:vnf_packages:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=VNFPKGM % 'create',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="Creates a vnf package.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnf_packages'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=VNFPKGM % 'show',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="Show a vnf package.",
        operations=[
            {
                'method': 'GET',
                'path': '/vnf_packages/{vnf_package_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=VNFPKGM % 'index',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="List all vnf packages.",
        operations=[
            {
                'method': 'GET',
                'path': '/vnf_packages/'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=VNFPKGM % 'delete',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="Delete a vnf package.",
        operations=[
            {
                'method': 'DELETE',
                'path': '/vnf_packages/{vnf_package_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=VNFPKGM % 'fetch_package_content',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="fetch the contents of an on-boarded VNF Package",
        operations=[
            {
                'method': 'GET',
                'path': '/vnf_packages/{vnf_package_id}/'
                        'package_content'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=VNFPKGM % 'upload_package_content',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="upload a vnf package content.",
        operations=[
            {
                'method': 'PUT',
                'path': '/vnf_packages/{vnf_package_id}/'
                        'package_content'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=VNFPKGM % 'upload_from_uri',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="upload a vnf package content from uri.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnf_packages/{vnf_package_id}/package_content/'
                        'upload_from_uri'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=VNFPKGM % 'patch',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="update information of vnf package.",
        operations=[
            {
                'method': 'PATCH',
                'path': '/vnf_packages/{vnf_package_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=VNFPKGM % 'get_vnf_package_vnfd',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="reads the content of the VNFD within a VNF package.",
        operations=[
            {
                'method': 'GET',
                'path': '/vnf_packages/{vnf_package_id}/vnfd'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=VNFPKGM % 'fetch_artifact',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description="reads the content of the artifact within a VNF package.",
        operations=[
            {
                'method': 'GET',
                'path': '/vnf_packages/{vnfPkgId}/artifacts/{artifactPath}'
            }
        ]),
]


def list_rules():
    return rules
