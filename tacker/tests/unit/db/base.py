# Copyright 2015 Brocade Communications System, Inc.
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

import fixtures

from tacker.common import config
from tacker.db import api as db_api
from tacker.db import model_base
from tacker.tests.unit import base


class SqlFixture(fixtures.Fixture):

    # flag to indicate that the models have been loaded
    _TABLES_ESTABLISHED = False

    def setUp(self):
        super(SqlFixture, self).setUp()
        # Register all data models
        engine = db_api.get_engine()
        if not SqlFixture._TABLES_ESTABLISHED:
            model_base.BASE.metadata.create_all(engine)
            SqlFixture._TABLES_ESTABLISHED = True

        def clear_tables():
            with engine.begin() as conn:
                for table in reversed(
                        model_base.BASE.metadata.sorted_tables):
                    conn.execute(table.delete())

        self.addCleanup(clear_tables)


class SqlTestCase(base.TestCase):

    def setUp(self):
        config.set_db_defaults()
        super(SqlTestCase, self).setUp()
        self.useFixture(SqlFixture())
