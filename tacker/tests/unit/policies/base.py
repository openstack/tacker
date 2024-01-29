# Copyright (C) 2024 NEC, Corp.
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

import copy

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils.fixture import uuidsentinel as uuids

from tacker.common import exceptions
from tacker import context
from tacker import policy
from tacker.tests.unit import base


LOG = logging.getLogger(__name__)


class BasePolicyTest(base.TestCase):
    # NOTE(gmann): Set this flag to True if you would like to tests the
    # new behaviour of policy without deprecated rules.
    # This means you can simulate the phase when policies completely
    # switch to new behaviour by removing the support of old rules.
    enforce_new_defaults = False

    def setUp(self):
        super(BasePolicyTest, self).setUp()
        if self.enforce_new_defaults:
            cfg.CONF.set_override('enforce_new_defaults', True,
                                  group='oslo_policy')
            # NOTE(gmann): oslo policy config option enforce_new_defaults
            # is changed here which is used while loading the rule in
            # oslo_policy.init() method that is why we need to reset the
            # policy and initialize again so that rule will be re-loaded
            # considering the enforce_new_defaults new value.
            policy.reset()
            policy.init()
            self.addCleanup(policy.reset)

        self.admin_project_id = uuids.admin_project_id
        self.project_id = uuids.project_id
        self.other_project_id = uuids.project_id_other

        # Create the user context with implied roles so that we can test
        # each user's context for RBAC permission.
        #
        # Legacy admin user
        self.legacy_admin_context = context.Context(
            user_id="legacy_admin", project_id=self.admin_project_id,
            roles=['admin', 'member', 'reader'])

        # project scoped users
        self.project_admin_context = context.Context(
            user_id="project_admin", project_id=self.project_id,
            roles=['admin', 'member', 'reader'])

        self.project_member_context = context.Context(
            user_id="project_member", project_id=self.project_id,
            roles=['member', 'reader'])

        self.project_reader_context = context.Context(
            user_id="project_reader", project_id=self.project_id,
            roles=['reader'])

        self.project_foo_context = context.Context(
            user_id="project_foo", project_id=self.project_id,
            roles=['foo'])

        self.other_project_member_context = context.Context(
            user_id="other_project_member",
            project_id=self.other_project_id,
            roles=['member', 'reader'])

        self.other_project_reader_context = context.Context(
            user_id="other_project_member",
            project_id=self.other_project_id,
            roles=['reader'])

        # system scoped users to check if system scope tokens are not
        # allowed in new RBAC.
        self.system_admin_context = context.Context(
            user_id="admin", roles=['admin', 'member', 'reader'],
            system_scope='all')

        self.system_member_context = context.Context(
            user_id="member", roles=['member', 'reader'],
            system_scope='all')

        self.system_reader_context = context.Context(
            user_id="reader", roles=['reader'],
            system_scope='all')

        self.system_foo_context = context.Context(
            user_id="foo", roles=['foo'],
            system_scope='all')

        self.all_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.project_foo_context, self.other_project_member_context,
            self.other_project_reader_context
        ]

    def common_policy_check(self, authorized_contexts,
                            unauthorized_contexts, rule_name,
                            func, req, *arg, **kwarg):

        # NOTE(gmann): When fatal=False is passed as a parameter
        # then this function does not raise error instead return
        # the responses for all contexts.
        fatal = kwarg.pop('fatal', True)
        authorized_response = []
        unauthorize_response = []

        def ensure_return(req, *args, **kwargs):
            return func(req, *arg, **kwargs)

        def ensure_raises(req, *args, **kwargs):
            exc = self.assertRaises(
                exceptions.PolicyNotAuthorized, func, req, *arg, **kwarg)
            # NOTE(gmann): In case of multi-policy APIs, PolicyNotAuthorized
            # exception can be raised from either of the policy so checking
            # the error message, which includes the rule name, can mismatch.
            # Tests verifying the multi policy can pass rule_name as None
            # to skip the error message assert.
            if rule_name is not None:
                self.assertEqual(
                    "Policy doesn't allow %s to be performed." %
                    rule_name, exc.format_message())
        # Verify all the context having allowed scope and roles pass
        # the policy check.
        for auth_context in authorized_contexts:
            LOG.info("Testing authorized user: %s", auth_context.user_id)
            req.environ['tacker.context'] = auth_context
            _args = copy.deepcopy(arg)
            _kwargs = copy.deepcopy(kwarg)
            if not fatal:
                authorized_response.append(
                    ensure_return(req, *_args, **_kwargs))
            else:
                func(req, *_args, **_kwargs)

        # Verify all the context not having allowed scope or roles fail
        # the policy check.
        for unauth_context in unauthorized_contexts:
            LOG.info("Testing unauthorized user: %s", unauth_context.user_id)
            req.environ['tacker.context'] = unauth_context
            _args = copy.deepcopy(arg)
            _kwargs = copy.deepcopy(kwarg)
            if not fatal:
                try:
                    unauthorize_response.append(
                        ensure_return(req, *_args, **_kwargs))
                    # NOTE(gmann): We need to ignore the PolicyNotAuthorized
                    # exception here so that we can add the correct response
                    # in unauthorize_response for the case of fatal=False.
                    # This handle the case of multi policy checks where tests
                    # are verifying the second policy via the response of
                    # fatal-False and ignoring the response checks where the
                    # first policy itself fail to pass (even test override the
                    # first policy to allow for everyone but still, scope
                    # checks can leads to PolicyNotAuthorized error).
                    # For example: flavor extra specs policy for GET flavor
                    # API. In that case, flavor extra spec policy is checked
                    # after the GET flavor policy. So any context failing on
                    # GET flavor will raise the  PolicyNotAuthorized and for
                    # that case we do not have any way to verify the flavor
                    # extra specs so skip that context to check in test.
                except exceptions.PolicyNotAuthorized:
                    continue
            else:
                ensure_raises(req, *_args, **_kwargs)

        return authorized_response, unauthorize_response
