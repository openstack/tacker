# Copyright (c) 2019 NTT DATA.
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
import testtools

from tacker.common import exceptions
from tacker import context
from tacker.glance_store import store
from tacker.tests import constants


class TestStore(testtools.TestCase):

    def setUp(self):
        super(TestStore, self).setUp()
        self.context = context.get_admin_context()
        self.base_path = os.path.dirname(os.path.abspath(__file__))

    def test_get_csar_size_invalid_path(self):
        self.assertRaises(
            exceptions.VnfPackageLocationInvalid, store.get_csar_size,
            constants.UUID, 'Invalid/path')

    def test_load_csar_iter_invalid_path(self):
        self.assertRaises(
            exceptions.VnfPackageLocationInvalid, store.load_csar_iter,
            constants.UUID, 'Invalid/path')
