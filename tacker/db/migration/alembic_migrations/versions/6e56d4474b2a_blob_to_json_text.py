# Copyright 2016 OpenStack Foundation
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
#

"""blob-to-json-text

Revision ID: 6e56d4474b2a
Revises: f958f58e5daa
Create Date: 2016-06-01 09:50:46.296206

"""

import json
import pickle

from alembic import op
import sqlalchemy as sa

from tacker.db import types

# revision identifiers, used by Alembic.
revision = '6e56d4474b2a'
down_revision = 'f958f58e5daa'


def _migrate_data(table, column_name):
    meta = sa.MetaData(bind=op.get_bind())
    t = sa.Table(table, meta, autoload=True)

    for r in t.select().execute():
        stmt = t.update().where(t.c.id == r.id).values(
            {column_name: json.dumps(pickle.loads(getattr(r, column_name)))})
        op.execute(stmt)

    op.alter_column(table,
                    column_name,
                    type_=types.Json)


def upgrade(active_plugins=None, options=None):
    _migrate_data('vims', 'placement_attr')
    _migrate_data('vimauths', 'vim_project')
    _migrate_data('vimauths', 'auth_cred')
    _migrate_data('devices', 'placement_attr')
