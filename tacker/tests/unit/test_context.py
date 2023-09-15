# Copyright 2012 VMware, Inc.
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

from unittest import mock

from castellan.common.credentials import keystone_password
from oslo_config import cfg
from oslo_context import context as oslo_context
from testtools import matchers

from tacker.common.ext_oauth2_auth import ExtOAuth2Auth
from tacker import context
from tacker.tests import base


def get_mock_conf_key_effect(cfg_keystone_authtoken=None,
                             cfg_ext_oauth2_auth=None):
    def mock_conf_key_effect(name):
        if name == 'keystone_authtoken':
            return MockConfig(name, conf=cfg_keystone_authtoken)
        elif name == 'ext_oauth2_auth':
            return MockConfig(name, conf=cfg_ext_oauth2_auth)
        else:
            return cfg.CONF._get(name)

    return mock_conf_key_effect


class MockConfig(cfg.OptGroup):
    def __init__(self, name, conf=None):
        self.name = name
        self.conf = conf

    def __getattr__(self, name):
        if not self.conf:
            raise cfg.NoSuchOptError('not found %s' % name)
        if name not in self.conf:
            raise cfg.NoSuchOptError('not found %s' % name)
        return self.conf.get(name)

    def __contains__(self, key):
        return key in self.conf


class TestTackerContext(base.BaseTestCase):

    def setUp(self):
        super(TestTackerContext, self).setUp()
        db_api = 'tacker.db.api.get_session'
        self._db_api_session_patcher = mock.patch(db_api)
        self.db_api_session = self._db_api_session_patcher.start()

    def test_tacker_context_create(self):
        ctx = context.Context('user_id', 'tenant_id')
        self.assertEqual('user_id', ctx.user_id)
        self.assertEqual('tenant_id', ctx.project_id)
        self.assertEqual('tenant_id', ctx.tenant_id)
        self.assertThat(ctx.request_id, matchers.StartsWith('req-'))
        self.assertEqual('user_id', ctx.user_id)
        self.assertEqual('tenant_id', ctx.project_id)
        self.assertIsNone(ctx.user_name)
        self.assertIsNone(ctx.tenant_name)

    def test_tacker_context_create_with_name(self):
        ctx = context.Context('user_id', 'tenant_id',
                              tenant_name='tenant_name', user_name='user_name')
        # Check name is set
        self.assertEqual('user_name', ctx.user_name)
        self.assertEqual('tenant_name', ctx.tenant_name)
        # Check user/tenant contains its ID even if user/tenant_name is passed
        self.assertEqual('user_id', ctx.user_id)
        self.assertEqual('tenant_id', ctx.project_id)

    def test_tacker_context_create_with_request_id(self):
        ctx = context.Context('user_id', 'tenant_id', request_id='req_id_xxx')
        self.assertEqual('req_id_xxx', ctx.request_id)

    def test_tacker_context_to_dict(self):
        ctx = context.Context('user_id', 'tenant_id')
        ctx_dict = ctx.to_dict()
        self.assertEqual('user_id', ctx_dict['user_id'])
        self.assertEqual('tenant_id', ctx_dict['project_id'])
        self.assertEqual(ctx.request_id, ctx_dict['request_id'])
        self.assertEqual('user_id', ctx_dict['user_id'])
        self.assertEqual('tenant_id', ctx_dict['project_id'])
        self.assertIsNone(ctx_dict['user_name'])
        self.assertIsNone(ctx_dict['tenant_name'])
        self.assertIsNone(ctx_dict['project_name'])

    def test_tacker_context_to_dict_with_name(self):
        ctx = context.Context('user_id', 'tenant_id',
                              tenant_name='tenant_name', user_name='user_name')
        ctx_dict = ctx.to_dict()
        self.assertEqual('user_name', ctx_dict['user_name'])
        self.assertEqual('tenant_name', ctx_dict['tenant_name'])
        self.assertEqual('tenant_name', ctx_dict['project_name'])

    def test_tacker_context_admin_to_dict(self):
        self.db_api_session.return_value = 'fakesession'
        ctx = context.get_admin_context()
        ctx_dict = ctx.to_dict()
        self.assertIsNone(ctx_dict['user_id'])
        self.assertIsNone(ctx_dict['tenant_id'])
        self.assertIsNotNone(ctx.session)
        self.assertNotIn('session', ctx_dict)

    def test_tacker_context_admin_without_session_to_dict(self):
        ctx = context.get_admin_context_without_session()
        ctx_dict = ctx.to_dict()
        self.assertIsNone(ctx_dict['user_id'])
        self.assertIsNone(ctx_dict['tenant_id'])
        self.assertFalse(hasattr(ctx, 'session'))

    def test_tacker_context_admin_context(self):
        ctx = context.get_admin_context()
        self.assertTrue(ctx.is_admin)
        self.assertFalse(ctx.roles)

    def test_tacker_context_elevated_retains_request_id(self):
        ctx = context.Context('user_id', 'tenant_id')
        self.assertFalse(ctx.is_admin)
        req_id_before = ctx.request_id

        elevated_ctx = ctx.elevated()
        self.assertTrue(elevated_ctx.is_admin)
        self.assertEqual(req_id_before, elevated_ctx.request_id)

    def test_tacker_context_overwrite(self):
        ctx1 = context.Context('user_id', 'tenant_id')
        self.assertEqual(oslo_context.get_current().request_id,
                         ctx1.request_id)

        # If overwrite is not specified, request_id should be updated.
        ctx2 = context.Context('user_id', 'tenant_id')
        self.assertNotEqual(ctx2.request_id, ctx1.request_id)
        self.assertEqual(oslo_context.get_current().request_id,
                         ctx2.request_id)

        # If overwrite is specified, request_id should be kept.
        ctx3 = context.Context('user_id', 'tenant_id', overwrite=False)
        self.assertNotEqual(ctx3.request_id, ctx2.request_id)
        self.assertEqual(oslo_context.get_current().request_id,
                         ctx2.request_id)

    def test_tacker_context_get_admin_context_not_update_local_store(self):
        ctx = context.Context('user_id', 'tenant_id')
        req_id_before = oslo_context.get_current().request_id
        self.assertEqual(req_id_before, ctx.request_id)

        ctx_admin = context.get_admin_context()
        self.assertEqual(req_id_before,
                         oslo_context.get_current().request_id)
        self.assertNotEqual(req_id_before, ctx_admin.request_id)

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_generate_tacker_service_context_keystone(self, mock_get_conf_key):
        password = 'test_password'
        auth_url = 'http://keystone/test/auth_url'
        username = 'test_user_name'
        user_domain_name = 'test_user_domain_name'
        project_name = 'test_project_name'
        project_domain_name = 'test_project_domain_name'
        token_endpoint = 'http://demo/token'
        auth_method = 'client_secret_basic'
        client_id = 'test_client_id'
        client_secret = 'client_secret'
        scope = 'tacker'
        mock_get_conf_key.side_effect = get_mock_conf_key_effect(
            cfg_keystone_authtoken={
                'password': password,
                'auth_url': auth_url,
                'username': username,
                'user_domain_name': user_domain_name,
                'project_name': project_name,
                'project_domain_name': project_domain_name},
            cfg_ext_oauth2_auth={
                'token_endpoint': token_endpoint,
                'auth_method': auth_method,
                'client_id': client_id,
                'client_secret': client_secret,
                'scope': scope,
                'use_ext_oauth2_auth': False}
        )
        auth_context = context.generate_tacker_service_context()
        self.assertIsInstance(auth_context, keystone_password.KeystonePassword)

    @mock.patch('oslo_config.cfg.ConfigOpts.__getattr__')
    def test_generate_tacker_service_context_external(self, mock_get_conf_key):
        password = 'test_password'
        auth_url = 'http://keystone/test/auth_url'
        username = 'test_user_name'
        user_domain_name = 'test_user_domain_name'
        project_name = 'test_project_name'
        project_domain_name = 'test_project_domain_name'
        token_endpoint = 'http://demo/token'
        auth_method = 'client_secret_basic'
        client_id = 'test_client_id'
        client_secret = 'client_secret'
        scope = 'tacker'
        mock_get_conf_key.side_effect = get_mock_conf_key_effect(
            cfg_keystone_authtoken={
                'password': password,
                'auth_url': auth_url,
                'username': username,
                'user_domain_name': user_domain_name,
                'project_name': project_name,
                'project_domain_name': project_domain_name},
            cfg_ext_oauth2_auth={
                'token_endpoint': token_endpoint,
                'auth_method': auth_method,
                'client_id': client_id,
                'client_secret': client_secret,
                'scope': scope,
                'use_ext_oauth2_auth': True})
        auth_context = context.generate_tacker_service_context()
        self.assertIsInstance(auth_context, ExtOAuth2Auth)
