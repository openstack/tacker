# Copyright 2016 Brocade Communications System, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
from unittest import mock

from keystoneauth1 import exceptions
from oslo_config import cfg

from tacker import context as t_context
from tacker.extensions import nfvo
from tacker.nfvo.drivers.vim import openstack_driver
from tacker.tests.unit import base
from tacker.tests.unit.db import utils

OPTS = [cfg.StrOpt('user_domain_id',
                   default='default',
                   help='User Domain Id'),
        cfg.StrOpt('project_domain_id',
                   default='default',
                   help='Project Domain Id'),
        cfg.StrOpt('password',
                   default='default',
                   help='User Password'),
        cfg.StrOpt('username',
                   default='default',
                   help='User Name'),
        cfg.StrOpt('user_domain_name',
                   default='default',
                   help='Use Domain Name'),
        cfg.StrOpt('project_name',
                   default='default',
                   help='Project Name'),
        cfg.StrOpt('project_domain_name',
                   default='default',
                   help='Project Domain Name'),
        cfg.StrOpt('auth_url',
                   default='http://localhost/identity/v3',
                   help='Keystone endpoint')]

cfg.CONF.register_opts(OPTS, 'keystone_authtoken')
CONF = cfg.CONF


class FakeKeystone(mock.Mock):
    pass


class FakeNeutronClient(mock.Mock):
    pass


class FakeKeymgrAPI(mock.Mock):
    pass


class mock_dict(dict):
    def __getattr__(self, item):
        return self.get(item)

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class TestOpenstack_Driver(base.TestCase):
    def setUp(self):
        super(TestOpenstack_Driver, self).setUp()
        self._mock_keystone()
        self.keystone.create_key_dir.return_value = 'test_keys'
        self.config_fixture.config(group='vim_keys', openstack='/tmp/')
        self.config_fixture.config(group='vim_keys', use_barbican=False)
        self.openstack_driver = openstack_driver.OpenStack_Driver()
        self.vim_obj = self.get_vim_obj()
        self.auth_obj = utils.get_vim_auth_obj()
        self.addCleanup(mock.patch.stopall)
        self._mock_keymgr()

    def _mock_keystone(self):
        self.keystone = mock.Mock(wraps=FakeKeystone())
        fake_keystone = mock.Mock()
        fake_keystone.return_value = self.keystone
        self._mock(
            'tacker.vnfm.keystone.Keystone', fake_keystone)

    def _mock_keymgr(self):
        self.keymgr = mock.Mock(wraps=FakeKeymgrAPI())
        fake_keymgr = mock.Mock()
        fake_keymgr.return_value = self.keymgr
        self._mock(
            'tacker.keymgr.barbican_key_manager.BarbicanKeyManager',
            fake_keymgr)

    def get_vim_obj(self):
        return {'id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff', 'type':
                'openstack', 'auth_url': 'http://localhost/identity',
                'auth_cred': {'username': 'test_user',
                              'password': 'test_password',
                              'user_domain_name': 'default',
                              'cert_verify': 'True',
                              'auth_url': 'http://localhost/identity'},
                'name': 'VIM0',
                'vim_project': {'name': 'test_project',
                                'project_domain_name': 'default'}}

    def get_vim_obj_barbican(self):
        return {'id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff', 'type':
                'openstack', 'auth_url': 'http://localhost/identity',
                'auth_cred': {'username': 'test_user',
                              'password': 'test_password',
                              'user_domain_name': 'default',
                              'key_type': 'barbican_key',
                              'secret_uuid': 'fake-secret-uuid',
                              'cert_verify': 'True',
                              'auth_url': 'http://localhost/identity'},
                'name': 'VIM0',
                'vim_project': {'name': 'test_project',
                                'project_domain_name': 'default'}}

    def test_register_keystone_v3(self):
        regions = [mock_dict({'id': 'RegionOne'})]
        attrs = {'regions.list.return_value': regions}
        keystone_version = 'v3'
        mock_ks_client = mock.Mock(**attrs)
        self.keystone.get_version.return_value = keystone_version
        self._test_register_vim(self.vim_obj, mock_ks_client)
        mock_ks_client.regions.list.assert_called_once_with()
        self.keystone.initialize_client.assert_called_once_with(
            **self.auth_obj)

    def _test_register_vim(self, vim_obj, mock_ks_client):
        self.keystone.initialize_client.return_value = mock_ks_client
        fernet_attrs = {'encrypt.return_value': 'encrypted_password'}
        mock_fernet_obj = mock.Mock(**fernet_attrs)
        mock_fernet_key = b'test_fernet_key'
        self.keystone.create_fernet_key.return_value = (mock_fernet_key,
                                                        mock_fernet_obj)
        self.openstack_driver.register_vim(vim_obj)
        with open('/tmp/' + vim_obj['id'], 'r') as f:
            # asserting that file has been written correctly.
            self.assertEqual('test_fernet_key', f.read())
        mock_fernet_obj.encrypt.assert_called_once_with(mock.ANY)
        os.remove('/tmp/' + vim_obj['id'])

    @mock.patch('tacker.nfvo.drivers.vim.openstack_driver.os.remove')
    @mock.patch('tacker.nfvo.drivers.vim.openstack_driver.os.path'
                '.join')
    def test_deregister_vim(self, mock_os_path, mock_os_remove):
        vim_obj = self.get_vim_obj()
        vim_id = 'my_id'
        vim_obj['id'] = vim_id
        file_path = CONF.vim_keys.openstack + '/' + vim_id
        mock_os_path.return_value = file_path
        self.openstack_driver.deregister_vim(vim_obj)
        mock_os_remove.assert_called_once_with(file_path)

    def test_deregister_vim_barbican(self):
        self.keymgr.delete.return_value = None
        vim_obj = self.get_vim_obj_barbican()
        self.openstack_driver.deregister_vim(vim_obj)
        self.keymgr.delete.assert_called_once_with(
            t_context.generate_tacker_service_context(), 'fake-secret-uuid')

    def test_encode_vim_auth_barbican(self):
        self.config_fixture.config(group='vim_keys',
                                   use_barbican=True)
        fernet_attrs = {'encrypt.return_value': 'encrypted_password'}
        mock_fernet_obj = mock.Mock(**fernet_attrs)
        mock_fernet_key = 'test_fernet_key'
        self.keymgr.store.return_value = 'fake-secret-uuid'
        self.keystone.create_fernet_key.return_value = (mock_fernet_key,
                                                        mock_fernet_obj)

        vim_obj = self.get_vim_obj()
        self.openstack_driver.encode_vim_auth(
            vim_obj['id'], vim_obj['auth_cred'])

        self.keymgr.store.assert_called_once_with(
            t_context.generate_tacker_service_context(), 'test_fernet_key')
        mock_fernet_obj.encrypt.assert_called_once_with(mock.ANY)
        self.assertEqual(vim_obj['auth_cred']['key_type'],
                         'barbican_key')
        self.assertEqual(vim_obj['auth_cred']['secret_uuid'],
                         'fake-secret-uuid')

    def test_register_vim_invalid_auth(self):
        attrs = {'regions.list.side_effect': exceptions.Unauthorized}
        self._test_register_vim_auth(attrs)

    def test_register_vim_missing_auth(self):
        attrs = {'regions.list.side_effect': exceptions.BadRequest}
        self._test_register_vim_auth(attrs)

    def _test_register_vim_auth(self, attrs):
        keystone_version = 'v3'
        self.keystone.get_version.return_value = keystone_version
        mock_ks_client = mock.Mock(**attrs)
        self.keystone.initialize_client.return_value = mock_ks_client
        self.assertRaises(nfvo.VimUnauthorizedException,
                          self.openstack_driver.register_vim,
                          self.vim_obj)
        mock_ks_client.regions.list.assert_called_once_with()
        self.keystone.initialize_client.assert_called_once_with(
            **self.auth_obj)

    def test_get_vim_resource_id(self):
        resource_type = 'network'
        resource_name = 'net0'
        fake_networks = {'networks': [{'id': 'fake-uuid', 'name': 'net0'}]}
        fake_neutron_client = FakeNeutronClient()
        fake_neutron_client.list_networks.return_value = fake_networks
        self.openstack_driver._get_client = mock.Mock(
            return_value=fake_neutron_client)

        self.openstack_driver.get_vim_resource_id(
            self.vim_obj, resource_type, resource_name)

        self.openstack_driver._get_client.assert_called_once_with(
            self.vim_obj, mock.ANY)
        fake_neutron_client.list_networks.assert_called_once_with(
            **{'name': 'net0'})

    def test_get_vim_resource_id_name_not_unique(self):
        resource_type = 'network'
        resource_name = 'net0'
        fake_networks = {'networks': [{'id': 'fake-uuid-1', 'name': 'net0'},
                                      {'id': 'fake-uuid-2', 'name': 'net0'}]}
        fake_neutron_client = FakeNeutronClient()
        fake_neutron_client.list_networks.return_value = fake_networks
        self.openstack_driver._get_client = mock.Mock(
            return_value=fake_neutron_client)

        self.assertRaises(nfvo.VimGetResourceNameNotUnique,
                          self.openstack_driver.get_vim_resource_id,
                          self.vim_obj, resource_type, resource_name)

    def test_get_vim_resource_id_name_not_exist(self):
        resource_type = 'network'
        resource_name = 'net0'
        fake_networks = {'networks': []}
        fake_neutron_client = FakeNeutronClient()
        fake_neutron_client.list_networks.return_value = fake_networks
        self.openstack_driver._get_client = mock.Mock(
            return_value=fake_neutron_client)

        self.assertRaises(nfvo.VimGetResourceNotFoundException,
                          self.openstack_driver.get_vim_resource_id,
                          self.vim_obj, resource_type, resource_name)
