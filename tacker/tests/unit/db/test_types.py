# Copyright (C) 2026 NTT
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

from sqlalchemy.dialects.mysql import pymysql
from sqlalchemy.dialects.postgresql import psycopg2
from sqlalchemy.dialects.sqlite import pysqlite

from tacker.db import types
from tacker.tests import base


class TestJson(base.BaseTestCase):

    DIALECTS = (pymysql.dialect(), psycopg2.dialect(), pysqlite.dialect())

    def test_process_bind_param_returns_str(self):
        value = {'regions': ['RegionOne'], 'key': None}
        for dialect in self.DIALECTS:
            with self.subTest(dialect=dialect.name):
                result = types.Json().process_bind_param(value, dialect)
                self.assertIsInstance(result, str)
                self.assertEqual(
                    value,
                    types.Json().process_result_value(result, dialect))

    def test_process_result_value(self):
        dialect = pymysql.dialect()
        self.assertIsNone(types.Json().process_result_value(None, dialect))
        self.assertEqual({'a': 1},
                         types.Json().process_result_value({'a': 1}, dialect))
        self.assertEqual({'a': 1},
                         types.Json().process_result_value(b'{"a": 1}',
                                                           dialect))
