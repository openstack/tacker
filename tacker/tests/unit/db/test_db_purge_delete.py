# Copyright 2016 Brocade Communications System, Inc.
# All Rights Reserved.
#
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


from tacker.common import exceptions
from tacker import context
from tacker.db.migration import purge_tables
from tacker.tests.unit.db import base as db_base


class FakeConfig(mock.Mock):
    pass


class TestDbPurgeDelete(db_base.SqlTestCase):
    def setUp(self):
        super(TestDbPurgeDelete, self).setUp()
        self.addCleanup(mock.patch.stopall)
        self.context = context.get_admin_context()
        self._mock_config()
        mock.patch('sqlalchemy.Table').start()
        mock.patch('tacker.db.migration.purge_tables._purge_resource_tables'
                   ).start()
        mock.patch('tacker.db.migration.purge_tables._purge_events_table',
                   ).start()
        mock.patch('tacker.db.migration.purge_tables.'
                   '_generate_associated_tables_map').start()
        mock.patch('tacker.db.migration.purge_tables.get_engine').start()

    def _mock_config(self):
        self.config = mock.Mock(wraps=FakeConfig())
        fake_config = mock.Mock()
        fake_config.return_value = self.config
        self._mock(
            'alembic.config.__init__', fake_config)

    def test_age_not_integer_input(self):
        self.assertRaises(exceptions.InvalidInput, purge_tables.purge_deleted,
                          self.config, 'invalid', 'abc')

    def test_age_negative_integer_input(self):
        self.assertRaises(exceptions.InvalidInput, purge_tables.purge_deleted,
                          self.config, 'invalid', '-90')

    def test_invalid_granularity_input(self):
        self.assertRaises(exceptions.InvalidInput, purge_tables.purge_deleted,
                          self.config, 'vnf', '90', 'decade')

    def test_purge_delete_call_vnf(self):
        purge_tables.purge_deleted(self.config, 'vnf', '90', 'days')
        purge_tables._purge_resource_tables.assert_called_once_with(
            mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY)

    def test_purge_delete_call_vnfd(self):
        purge_tables.purge_deleted(self.config, 'vnfd', '90', 'days')
        purge_tables._purge_resource_tables.assert_called_once_with(
            mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY)

    def test_purge_delete_call_vim(self):
        purge_tables.purge_deleted(self.config, 'vims', '90', 'days')
        purge_tables._purge_resource_tables.assert_called_once_with(
            mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY)

    def test_purge_delete_call_events(self):
        purge_tables.purge_deleted(self.config, 'events', '90', 'days')
        purge_tables._purge_events_table.assert_called_once_with(
            mock.ANY, mock.ANY, mock.ANY)
