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


class TestCamelToSnakeCase(testtools.TestCase):
    def test_convert_camelcase_to_snakecase_dict(self):
        """Only the dict keys should be converted to snakecase"""
        actual_val = utils.convert_camelcase_to_snakecase(
            {"camelCaseKey": "camelCaseValue"})
        expected_val = {"camel_case_key": "camelCaseValue"}
        self.assertEqual(expected_val, actual_val)

    def test_convert_camelcase_to_snakecase_list_with_dict_items(self):
        """Only the dict keys from list should be converted to snakecase"""
        data = [{"camelCaseKey": "camelCaseValue"}]
        actual_val = utils.convert_camelcase_to_snakecase(data)
        expected_val = [{"camel_case_key": "camelCaseValue"}]
        self.assertEqual(expected_val, actual_val)

    def test_convert_camelcase_to_snakecase_list_with_string_items(self):
        """Conversion of camelcase to snakecase should be ignored.

        For simple list with string items, the elements which are actual
        values should be ignored during conversion
        """
        data = ["camelCaseValue1", "camelCaseValue2"]
        actual_val = utils.convert_snakecase_to_camelcase(data)
        expected_val = ["camelCaseValue1", "camelCaseValue2"]
        self.assertEqual(expected_val, actual_val)


class TestSnakeToCamelCase(testtools.TestCase):
    def test_convert_snakecase_to_camelcase_dict(self):
        """Only the dict keys from list should be converted to camelcase"""
        actual_val = utils.convert_snakecase_to_camelcase(
            {"snake_case_key": "snake_case_value"})
        expected_val = {"snakeCaseKey": "snake_case_value"}
        self.assertEqual(expected_val, actual_val)

    def test_convert_snakecase_to_camelcase_list_with_dict_items(self):
        """Only the dict keys from list should be converted to camelcase"""
        data = [{"snake_case_key": "snake_case_value"}]
        actual_val = utils.convert_snakecase_to_camelcase(data)
        expected_val = [{"snakeCaseKey": "snake_case_value"}]
        self.assertEqual(expected_val, actual_val)

    def test_convert_snakecase_to_camelcase_list_with_string_items(self):
        """Conversion of snakecase to camelcase should be ignored.

        For simple list with string items, the elements which are actual
        values should be ignored during conversion
        """
        data = ["snake_case_value1", "snake_case_value2"]
        actual_val = utils.convert_snakecase_to_camelcase(data)
        expected_val = ["snake_case_value1", "snake_case_value2"]
        self.assertEqual(expected_val, actual_val)


class TestValidateUrl(testtools.TestCase):
    def test_valid_url(self):
        result = utils.is_valid_url("https://10.10.10.10/test.zip")
        self.assertTrue(result)

    def test_no_scheme(self):
        result = utils.is_valid_url("//10.10.10.10/test.zip")
        self.assertFalse(result)

    def test_invalid_scheme(self):
        result = utils.is_valid_url("invalid://10.10.10.10/test.zip")
        self.assertFalse(result)

    def test_no_path_in_url(self):
        # The specified url `https://10.10.10.10` is valid but in context with
        # the functionality implemented, expecting csar file in `path` as
        # mandatory parameter.
        result = utils.is_valid_url("https://10.10.10.10")
        self.assertFalse(result)
