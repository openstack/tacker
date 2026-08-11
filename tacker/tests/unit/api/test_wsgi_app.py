# Copyright (C) 2026 Nippon Telegraph and Telephone Corporation
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

import os
import tempfile
from unittest import mock

from tacker.api import wsgi_app
from tacker.tests import base


class TestWsgiApp(base.BaseTestCase):

    def test_get_config_files_default_dir_missing(self):
        env = {'OS_TACKER_CONFIG_DIR': '/nonexistent-tacker-conf-dir'}
        self.assertEqual([], wsgi_app._get_config_files(env))

    def test_get_config_files_from_env(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in wsgi_app.CONFIG_FILES:
                with open(os.path.join(tmpdir, name), 'w') as f:
                    f.write('')
            env = {'OS_TACKER_CONFIG_DIR': tmpdir}
            self.assertEqual(
                [os.path.join(tmpdir, name)
                 for name in wsgi_app.CONFIG_FILES],
                wsgi_app._get_config_files(env))

    @mock.patch.object(wsgi_app.config, 'load_paste_app')
    @mock.patch.object(wsgi_app.sol_objects, 'register_all')
    @mock.patch.object(wsgi_app.objects, 'register_all')
    @mock.patch.object(wsgi_app.config, 'setup_logging')
    @mock.patch.object(wsgi_app.config, 'init')
    def test_init_application(self, mock_init, mock_logging,
                              mock_register, mock_sol_register,
                              mock_load_paste_app):
        wsgi_app.init_application()
        mock_init.assert_called_once()
        mock_register.assert_called_once_with()
        mock_sol_register.assert_called_once_with()
        mock_load_paste_app.assert_called_once_with('tacker')
