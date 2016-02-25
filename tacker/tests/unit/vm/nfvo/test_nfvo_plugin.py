# Copyright 2016 Brocade Communications System, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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

import uuid

import mock

from tacker import context
from tacker.db.nfvo import nfvo_db
from tacker.nfvo import nfvo_plugin
from tacker.tests.unit.db import base as db_base


class FakeDriverManager(mock.Mock):
    def invoke(self, *args, **kwargs):
        if 'create' in args:
            return str(uuid.uuid4())


class TestNfvoPlugin(db_base.SqlTestCase):
    def setUp(self):
        super(TestNfvoPlugin, self).setUp()
        self.addCleanup(mock.patch.stopall)
        self.context = context.get_admin_context()
        self._mock_driver_manager()
        self.nfvo_plugin = nfvo_plugin.NfvoPlugin()

    def _mock_driver_manager(self):
        self._driver_manager = mock.Mock(wraps=FakeDriverManager())
        self._driver_manager.__contains__ = mock.Mock(
            return_value=True)
        fake_driver_manager = mock.Mock()
        fake_driver_manager.return_value = self._driver_manager
        self._mock(
            'tacker.common.driver_manager.DriverManager', fake_driver_manager)

    def _insert_dummy_vim(self):
        session = self.context.session
        vim_db = nfvo_db.Vim(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_vim',
            description='fake_vim_description',
            type='openstack',
            placement_attr={'regions': ['RegionOne']})
        vim_auth_db = nfvo_db.VimAuth(
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            password='encrypted_pw',
            auth_url='http://localhost:5000',
            vim_project={'name': 'test_project'},
            auth_cred={'username': 'test_user', 'user_domain_id': 'default',
                       'project_domain_d': 'default'})
        session.add(vim_db)
        session.add(vim_auth_db)
        session.flush()

    def test_create_vim(self):
        vim_dict = {'vim': {'type': 'openstack', 'auth_url':
                    'http://localhost:5000', 'vim_project': {'name':
                    'test_project'}, 'auth_cred': {'username': 'test_user',
                                                   'password':
                                                       'test_password'},
                            'name': 'VIM0'}}
        vim_type = 'openstack'
        res = self.nfvo_plugin.create_vim(self.context, vim_dict)
        self._driver_manager.invoke.assert_called_once_with(vim_type,
                                                            'register_vim',
                                                            vim_obj=vim_dict[
                                                                'vim'])
        self.assertIsNotNone(res)
        self.assertIn('id', res)
        self.assertIn('placement_attr', res)

    def test_delete_vim(self):
        self._insert_dummy_vim()
        vim_type = 'openstack'
        vim_id = '6261579e-d6f3-49ad-8bc3-a9cb974778ff'
        self.nfvo_plugin.delete_vim(self.context, vim_id)
        self._driver_manager.invoke.assert_called_once_with(vim_type,
                                                            'deregister_vim',
                                                            vim_id=vim_id)

    def test_update_vim(self):
        vim_dict = {'vim': {'id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                            'vim_project': {'name': 'new_project'},
                            'auth_cred': {'username': 'new_user',
                                          'password': 'new_password'}}}
        vim_type = 'openstack'
        vim_auth_username = vim_dict['vim']['auth_cred']['username']
        vim_auth_password = vim_dict['vim']['auth_cred']['password']
        vim_project = vim_dict['vim']['vim_project']
        self._insert_dummy_vim()
        res = self.nfvo_plugin.update_vim(self.context, vim_dict['vim']['id'],
                                          vim_dict)
        self._driver_manager.invoke.assert_called_once_with(vim_type,
                                                            'register_vim',
                                                            vim_obj=mock.ANY)
        self.assertIsNotNone(res)
        self.assertIn('id', res)
        self.assertIn('placement_attr', res)
        self.assertEqual(vim_project, res['vim_project'])
        self.assertEqual(vim_auth_username, res['auth_cred']['username'])
        self.assertEqual(vim_auth_password, res['auth_cred']['password'])
