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
import mock

from oslo_config import cfg

from sqlalchemy.orm import exc as orm_exc

from tacker.extensions import nfvo
from tacker import manager
from tacker.tests.unit import base
from tacker.vnfm import vim_client


class TestVIMClient(base.TestCase):

    def setUp(self):
        super(TestVIMClient, self).setUp()
        self.vim_info = {'id': 'aaaa', 'name': 'VIM0',
                         'auth_cred': {'password': '****'}, 'type': 'test_vim'}

    def test_get_vim_without_defined_default_vim(self):
        cfg.CONF.set_override(
            'default_vim', '', 'nfvo_vim', enforce_type=True)
        vimclient = vim_client.VimClient()
        service_plugins = mock.Mock()
        nfvo_plugin = mock.Mock()
        nfvo_plugin.get_default_vim.side_effect = \
            orm_exc.NoResultFound()
        service_plugins.get.return_value = nfvo_plugin
        with mock.patch.object(manager.TackerManager, 'get_service_plugins',
                               return_value=service_plugins):
            self.assertRaises(nfvo.VimDefaultNameNotDefined,
                              vimclient.get_vim, None)

    def test_get_vim_without_defined_default_vim_in_db(self):
        cfg.CONF.set_override(
            'default_vim', 'VIM0', 'nfvo_vim', enforce_type=True)
        vimclient = vim_client.VimClient()
        service_plugins = mock.Mock()
        nfvo_plugin = mock.Mock()
        nfvo_plugin.get_default_vim.side_effect = \
            orm_exc.NoResultFound()
        service_plugins.get.return_value = nfvo_plugin
        with mock.patch.object(manager.TackerManager, 'get_service_plugins',
                               return_value=service_plugins):
            get_vim_by_name = \
                mock.patch.object(vimclient,
                                  '_get_default_vim_by_name').start()
            get_vim_by_name.return_value = self.vim_info
            build_vim_auth = \
                mock.patch.object(vimclient,
                                  '_build_vim_auth').start()
            build_vim_auth.return_value = mock.Mock()
            vimclient.get_vim(None)
            vimclient._get_default_vim_by_name.\
                assert_called_once_with(mock.ANY, mock.ANY, 'VIM0')
