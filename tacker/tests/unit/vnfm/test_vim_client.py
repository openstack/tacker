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

from sqlalchemy.orm import exc as orm_exc
from unittest import mock

from tacker.extensions import nfvo
from tacker import manager
from tacker.tests.unit import base
from tacker.vnfm import vim_client


class TestVIMClient(base.TestCase):

    def setUp(self):
        super(TestVIMClient, self).setUp()
        self.vim_info = {'id': 'aaaa', 'name': 'VIM0', 'type': 'test_vim',
                         'auth_cred': {'password': '****'},
                         'auth_url': 'http://127.0.0.1/identity/v3',
                         'placement_attr': {'regions': ['TestRegionOne']},
                         'tenant_id': 'test'}
        self.vimclient = vim_client.VimClient()
        self.service_plugins = mock.Mock()
        self.nfvo_plugin = mock.Mock()

    def test_get_vim_without_defined_default_vim(self):
        self.nfvo_plugin.get_default_vim.side_effect = \
            orm_exc.NoResultFound()
        self.service_plugins.get.return_value = self.nfvo_plugin
        with mock.patch.object(manager.TackerManager, 'get_service_plugins',
                               return_value=self.service_plugins):
            self.assertRaises(nfvo.VimDefaultNotDefined,
                              self.vimclient.get_vim, None)

    def test_get_vim_not_found_exception(self):
        vim_id = self.vim_info['id']
        self.nfvo_plugin.get_vim.side_effect = \
            orm_exc.NoResultFound()
        self.service_plugins.get.return_value = self.nfvo_plugin
        with mock.patch.object(manager.TackerManager, 'get_service_plugins',
                               return_value=self.service_plugins):
            self.assertRaises(nfvo.VimNotFoundException,
                              self.vimclient.get_vim, None, vim_id=vim_id)

    def test_get_vim_region_not_found_region_name_invalid(self):
        self.nfvo_plugin.get_vim.return_value = self.vim_info
        self.service_plugins.get.return_value = self.nfvo_plugin
        with mock.patch.object(manager.TackerManager, 'get_service_plugins',
                               return_value=self.service_plugins):
            self.assertRaises(nfvo.VimRegionNotFoundException,
                              self.vimclient.get_vim, None,
                              vim_id=self.vim_info['id'],
                              region_name='Test')

    def test_get_vim(self):
        self.nfvo_plugin.get_vim.return_value = self.vim_info
        self.service_plugins.get.return_value = self.nfvo_plugin
        self.vimclient._build_vim_auth = mock.Mock()
        self.vimclient._build_vim_auth.return_value = {'password': '****'}
        with mock.patch.object(manager.TackerManager, 'get_service_plugins',
                               return_value=self.service_plugins):
            vim_result = self.vimclient.get_vim(None,
                                                vim_id=self.vim_info['id'],
                                                region_name='TestRegionOne')
            vim_expect = {'vim_auth': {'password': '****'}, 'vim_id': 'aaaa',
                          'vim_name': 'VIM0', 'vim_type': 'test_vim',
                          'placement_attr': {'regions': ['TestRegionOne']},
                          'tenant': 'test'}
            self.assertEqual(vim_expect, vim_result)

    def test_get_vim_with_default_name(self):
        self.vim_info.pop('name')
        self.nfvo_plugin.get_vim.return_value = self.vim_info
        self.service_plugins.get.return_value = self.nfvo_plugin
        self.vimclient._build_vim_auth = mock.Mock()
        self.vimclient._build_vim_auth.return_value = {'password': '****'}
        with mock.patch.object(manager.TackerManager, 'get_service_plugins',
                               return_value=self.service_plugins):
            vim_result = self.vimclient.get_vim(None,
                                                vim_id=self.vim_info['id'],
                                                region_name='TestRegionOne')
            vim_expect = {'vim_auth': {'password': '****'}, 'vim_id': 'aaaa',
                          'vim_name': 'aaaa', 'vim_type': 'test_vim',
                          'placement_attr': {'regions': ['TestRegionOne']},
                          'tenant': 'test'}
            self.assertEqual(vim_expect, vim_result)

    def test_find_vim_key_with_key_not_found_exception(self):
        vim_id = self.vim_info['id']
        self.assertRaises(nfvo.VimKeyNotFoundException,
                          self.vimclient._find_vim_key, vim_id)

    def test_region_valid_false(self):
        vim_regions = ['TestRegionOne', 'TestRegionTwo']
        region_name = 'TestRegion'
        self.assertFalse(self.vimclient.region_valid(vim_regions,
                                                     region_name))

    def test_region_valid_true(self):
        vim_regions = ['TestRegionOne', 'TestRegionTwo']
        region_name = 'TestRegionOne'
        self.assertTrue(self.vimclient.region_valid(vim_regions, region_name))
