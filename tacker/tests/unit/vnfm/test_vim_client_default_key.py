# Copyright (C) 2025 KDDI
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
import unittest

from oslo_config import cfg
from tacker.extensions import nfvo
from tacker.vnfm.vim_client import VimClient


class TestVIMClientDefaultKey(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

        g = cfg.OptGroup('vim_keys')
        try:
            cfg.CONF.register_group(g)
        except cfg.DuplicateOptError:
            pass

        opts = [
            cfg.StrOpt('openstack'),
            cfg.StrOpt('default_secret_key', default='default.key'),
        ]
        for opt in opts:
            try:
                cfg.CONF.register_opt(opt, group=g)
            except cfg.DuplicateOptError:
                pass

        cfg.CONF.set_override('openstack', self.tmpdir.name, group='vim_keys')
        cfg.CONF.set_override(
            'default_secret_key', 'default.key', group='vim_keys')
        # create default.key
        with open(os.path.join(self.tmpdir.name, 'default.key'), 'w') as f:
            f.write('DEFAULTKEY==')

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_find_vim_key_prefers_per_vim(self):
        with open(os.path.join(self.tmpdir.name, 'VIM-A'), 'w') as f:
            f.write('PER_VIM_KEY==')
        self.assertEqual('PER_VIM_KEY==', VimClient._find_vim_key('VIM-A'))

    def test_find_vim_key_fallback_to_default(self):
        self.assertEqual('DEFAULTKEY==', VimClient._find_vim_key('VIM-B'))

    def test_find_vim_key_raises_when_missing(self):
        os.remove(os.path.join(self.tmpdir.name, 'default.key'))
        with self.assertRaises(nfvo.VimKeyNotFoundException):
            VimClient._find_vim_key('VIM-C')
