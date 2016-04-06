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

from tacker.extensions import nfvo
from tacker import manager
from tacker.tests.unit import base
from tacker.vm import vim_client


class TestVIMClient(base.TestCase):

    def test_get_vim_without_defined_default_vim(self):
        cfg.CONF.set_override(
            'default_vim', '', 'nfvo_vim', enforce_type=True)
        vimclient = vim_client.VimClient()
        service_plugins = mock.Mock()
        with mock.patch.object(manager.TackerManager, 'get_service_plugins',
                               return_value=service_plugins):
            self.assertRaises(nfvo.VimDefaultNameNotDefined,
                              vimclient.get_vim, None)
