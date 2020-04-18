# Copyright (c) 2012 OpenStack Foundation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from unittest import mock

from oslo_config import cfg

from tacker.common import config
from tacker.tests import base


class ConfigurationTest(base.BaseTestCase):

    def test_defaults(self):
        self.assertEqual('0.0.0.0', cfg.CONF.bind_host)
        self.assertEqual(9890, cfg.CONF.bind_port)
        self.assertEqual('api-paste.ini.test', cfg.CONF.api_paste_config)
        self.assertEqual('unit/extensions', cfg.CONF.api_extensions_path)
        self.assertEqual('keystone', cfg.CONF.auth_strategy)
        self.assertTrue(cfg.CONF.allow_bulk)
        self.assertFalse(cfg.CONF.allow_pagination)
        self.assertFalse(cfg.CONF.allow_sorting)
        self.assertEqual('-1', cfg.CONF.pagination_max_limit)
        relative_dir = os.path.join(os.path.dirname(__file__),
                                    '..', '..', '..', '..')
        absolute_dir = os.path.abspath(relative_dir)
        self.assertEqual(absolute_dir, cfg.CONF.state_path)
        self.assertEqual('tacker', cfg.CONF.control_exchange)
        self.assertEqual('sqlite://', cfg.CONF.database.connection)

    def test_load_paste_app_not_found(self):
        self.config(api_paste_config='no_such_file.conf')
        with mock.patch.object(cfg.CONF, 'find_file', return_value=None) as ff:
            e = self.assertRaises(cfg.ConfigFilesNotFoundError,
                                  config.load_paste_app, 'app')
            ff.assert_called_once_with('no_such_file.conf')
            self.assertEqual(['no_such_file.conf'], e.config_files)

    @mock.patch('paste.deploy.loadapp')
    def test_load_paste_app(self, mock_deploy):
        mock_deploy.return_value = 'test'
        self.config(api_paste_config='api-paste.ini.test')
        config.load_paste_app('tacker')
        config_path = os.path.abspath(cfg.CONF.find_file(
            cfg.CONF.api_paste_config))
        mock_deploy.assert_called_once_with('config:%s' % config_path,
                                            name='tacker')

    def test_load_paste_app_runtime_error(self):
        self.config(api_paste_config='api-paste.ini.test')
        from paste import deploy
        with mock.patch.object(deploy, 'loadapp', side_effect=RuntimeError):
            self.assertRaises(RuntimeError, config.load_paste_app, 'tacker')
