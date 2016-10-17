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
        vimclient = vim_client.VimClient()
        service_plugins = mock.Mock()
        nfvo_plugin = mock.Mock()
        nfvo_plugin.get_default_vim.side_effect = \
            orm_exc.NoResultFound()
        service_plugins.get.return_value = nfvo_plugin
        with mock.patch.object(manager.TackerManager, 'get_service_plugins',
                               return_value=service_plugins):
            self.assertRaises(nfvo.VimDefaultNotDefined,
                              vimclient.get_vim, None)
