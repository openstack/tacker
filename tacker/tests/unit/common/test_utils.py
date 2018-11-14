# Copyright (c) 2012 OpenStack Foundation.
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

import testtools

from tacker.common import utils
from tacker.tests import base


class TestDict2Tuples(base.BaseTestCase):
    def test_dict(self):
        input_dict = {'foo': 'bar', '42': 'baz', 'aaa': 'zzz'}
        expected = (('42', 'baz'), ('aaa', 'zzz'), ('foo', 'bar'))
        output_tuple = utils.dict2tuple(input_dict)
        self.assertEqual(expected, output_tuple)


class TestChangeMemory(testtools.TestCase):
    def test_change_memory_from_mb_to_gb(self):
        actual_val = utils.change_memory_unit("1024 mb", "GB")
        expected_val = 1
        self.assertEqual(expected_val, actual_val)

    def test_change_memory_from_gb_to_mb(self):
        actual_val = utils.change_memory_unit("1 GB", "MB")
        expected_val = 1024
        self.assertEqual(expected_val, actual_val)
