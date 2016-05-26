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

from keystoneclient import exceptions
import mock
from oslo_config import cfg

from tacker.extensions import nfvo
from tacker.nfvo.drivers.vim import openstack_driver
from tacker.tests.unit import base
from tacker.tests.unit.db import utils

OPTS = [cfg.StrOpt('user_domain_id', default='default', help='User Domain Id'),
        cfg.StrOpt('project_domain_id', default='default', help='Project '
                                                                'Domain Id')]
cfg.CONF.register_opts(OPTS, 'keystone_authtoken')
CONF = cfg.CONF


class FakeKeystone(mock.Mock):
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
        self.openstack_driver = openstack_driver.OpenStack_Driver()
        self.vim_obj = self.get_vim_obj()
        self.auth_obj = utils.get_vim_auth_obj()
        self.addCleanup(mock.patch.stopall)

    def _mock_keystone(self):
        self.keystone = mock.Mock(wraps=FakeKeystone())
        fake_keystone = mock.Mock()
        fake_keystone.return_value = self.keystone
        self._mock(
            'tacker.vm.keystone.Keystone', fake_keystone)

    def get_vim_obj(self):
        return {'id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff', 'type':
                'openstack', 'auth_url': 'http://localhost:5000',
                'auth_cred': {'username': 'test_user', 'password':
                    'test_password'}, 'name': 'VIM0',
                'vim_project': {'name': 'test_project'}}

    def test_register_keystone_v3(self):
        regions = [mock_dict({'id': 'RegionOne'})]
        attrs = {'regions.list.return_value': regions}
        keystone_version = 'v3'
        mock_ks_client = mock.Mock(version=keystone_version, **attrs)
        self.keystone.get_version.return_value = keystone_version
        self._test_register_vim(self.vim_obj, mock_ks_client)
        mock_ks_client.regions.list.assert_called_once_with()
        self.keystone.initialize_client.assert_called_once_with(
            version=keystone_version, **self.auth_obj)

    def test_register_keystone_v2(self):
        services_list = [mock_dict({'type': 'orchestration', 'id':
                         'test_id'})]
        endpoints_regions = mock_dict({'region': 'RegionOne'})
        endpoints_list = [mock_dict({'service_id': 'test_id', 'regions':
                          endpoints_regions})]
        attrs = {'endpoints.list.return_value': endpoints_list,
                 'services.list.return_value': services_list}
        keystone_version = 'v2.0'
        mock_ks_client = mock.Mock(version='v2.0', **attrs)
        self.keystone.get_version.return_value = keystone_version
        auth_obj = {'tenant_name': 'test_project', 'username': 'test_user',
                    'password': 'test_password', 'auth_url':
                    'http://localhost:5000/v2.0', 'tenant_id': None}
        self._test_register_vim(self.vim_obj, mock_ks_client)
        self.keystone.initialize_client.assert_called_once_with(
            version=keystone_version, **auth_obj)

    def _test_register_vim(self, vim_obj, mock_ks_client):
        self.keystone.initialize_client.return_value = mock_ks_client
        fernet_attrs = {'encrypt.return_value': 'encrypted_password'}
        mock_fernet_obj = mock.Mock(**fernet_attrs)
        mock_fernet_key = 'test_fernet_key'
        self.keystone.create_fernet_key.return_value = (mock_fernet_key,
                                                        mock_fernet_obj)
        file_mock = mock.mock_open()
        with mock.patch('six.moves.builtins.open', file_mock, create=True):
            self.openstack_driver.register_vim(vim_obj)
        mock_fernet_obj.encrypt.assert_called_once_with(mock.ANY)
        file_mock().write.assert_called_once_with('test_fernet_key')

    @mock.patch('tacker.nfvo.drivers.vim.openstack_driver.os.remove')
    @mock.patch('tacker.nfvo.drivers.vim.openstack_driver.os.path'
                '.join')
    def test_deregister_vim(self, mock_os_path, mock_os_remove):
        vim_id = 'my_id'
        file_path = CONF.vim_keys.openstack + '/' + vim_id
        mock_os_path.return_value = file_path
        self.openstack_driver.deregister_vim(vim_id)
        mock_os_remove.assert_called_once_with(file_path)

    def test_register_vim_invalid_credentials(self):
        attrs = {'regions.list.side_effect': exceptions.Unauthorized}
        keystone_version = 'v3'
        mock_ks_client = mock.Mock(version=keystone_version, **attrs)
        self.keystone.get_version.return_value = keystone_version
        self.keystone.initialize_client.return_value = mock_ks_client
        self.assertRaises(nfvo.VimUnauthorizedException,
                          self.openstack_driver.register_vim, self.vim_obj)
        mock_ks_client.regions.list.assert_called_once_with()
        self.keystone.initialize_client.assert_called_once_with(
            version=keystone_version, **self.auth_obj)
