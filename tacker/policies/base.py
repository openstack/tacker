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

TACKER_API = 'os_nfv_orchestration_api'

RULE_ADMIN_OR_OWNER = 'rule:admin_or_owner'
RULE_ADMIN_API = 'rule:admin_only'
RULE_ANY = '@'


DEPRECATED_REASON = """
Tacker API policies are introducing new default roles with scope_type
capabilities. Old policies are deprecated and silently going to be ignored
in future.
"""

DEPRECATED_ADMIN_POLICY = policy.DeprecatedRule(
    name=RULE_ADMIN_API,
    check_str='is_admin:True',
    deprecated_reason=DEPRECATED_REASON,
    deprecated_since='11.0.0'
)

DEPRECATED_ADMIN_OR_OWNER_POLICY = policy.DeprecatedRule(
    name=RULE_ADMIN_OR_OWNER,
    check_str='is_admin:True or project_id:%(project_id)s',
    deprecated_reason=DEPRECATED_REASON,
    deprecated_since='11.0.0'
)

RULE_PROJECT_MEMBER = 'rule:project_member'
RULE_PROJECT_READER = 'rule:project_reader'
# NOTE(gmann): or_admin in below rules make sure that legacy (existing) admin
# continue working in same way as currently.
RULE_PROJECT_MEMBER_OR_ADMIN = 'rule:project_member_or_admin'
RULE_PROJECT_READER_OR_ADMIN = 'rule:project_reader_or_admin'

# NOTE: Below is the mapping of new defaults with legacy defaults::
# Legacy Defaults    |New Defaults               |Operation       |scope_type|
# -------------------+---------------------------+----------------+-----------
# RULE_ADMIN_API     |-> ADMIN                   |Global resource | [project]
#                    |                           |Write & Read    |
# -------------------+---------------------------+----------------+-----------
#                    |-> ADMIN                   |Project admin   | [project]
#                    |                           |level operation |
# RULE_ADMIN_OR_OWNER|-> PROJECT_MEMBER_OR_ADMIN |Project resource| [project]
#                    |                           |Write           |
#                    |-> PROJECT_READER_OR_ADMIN |Project resource| [project]
#                    |                           |Read            |

# NOTE(gmann): The OpenStack Keystone already supports implied roles which
# means the assignment of one role implies the assignment of another.
# The new default roles reader and member also have been added in bootstrap.
# If the bootstrap process is re-run, and a reader, member or admin role
# already exists, a role implication chain will be created: `admin` implies
# `member` implies `reader`.
# For example: If we give access to 'reader' it means the 'admin' and
# 'member' also gets the access.
rules = [
    policy.RuleDefault(
        "context_is_admin",
        "role:admin",
        "Decides what is required for the 'is_admin:True' check to succeed.",
        deprecated_rule=DEPRECATED_ADMIN_POLICY),
    policy.RuleDefault(
        "admin_or_owner",
        "is_admin:True or project_id:%(project_id)s",
        "Default rule for most non-Admin APIs.",
        deprecated_for_removal=True,
        deprecated_reason=DEPRECATED_REASON,
        deprecated_since='11.0.0'),
    policy.RuleDefault(
        "admin_only",
        "is_admin:True",
        "Default rule for most Admin APIs.",
        deprecated_for_removal=True,
        deprecated_reason=DEPRECATED_REASON,
        deprecated_since='11.0.0'),
    policy.RuleDefault(
        "shared",
        "field:vims:shared=True",
        "Default rule for sharing vims."),
    policy.RuleDefault(
        "project_member",
        "role:member and project_id:%(project_id)s",
        "Default rule for Project level non admin APIs.",
        deprecated_rule=DEPRECATED_ADMIN_OR_OWNER_POLICY),
    policy.RuleDefault(
        "project_member_or_admin",
        "rule:project_member or rule:context_is_admin",
        "Default rule for Project Member or admin APIs.",
        deprecated_rule=DEPRECATED_ADMIN_OR_OWNER_POLICY),
    policy.RuleDefault(
        "project_reader",
        "role:reader and project_id:%(project_id)s",
        "Default rule for Project level read only APIs.",
        deprecated_rule=DEPRECATED_ADMIN_OR_OWNER_POLICY),
    policy.RuleDefault(
        "project_reader_or_admin",
        "rule:project_reader or rule:context_is_admin",
        "Default rule for Project reader or admin APIs.",
        deprecated_rule=DEPRECATED_ADMIN_OR_OWNER_POLICY),
    policy.RuleDefault(
        "default",
        "rule:project_member_or_admin",
        "Default rule for most non-Admin APIs.",
        deprecated_rule=DEPRECATED_ADMIN_OR_OWNER_POLICY)
]


def list_rules():
    return rules
