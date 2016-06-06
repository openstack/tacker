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

"""audit_support_events

Revision ID: 4ee19c8a6d0a
Revises: acf941e54075
Create Date: 2016-06-07 03:16:53.513392

"""

# revision identifiers, used by Alembic.
revision = '4ee19c8a6d0a'
down_revision = '941b5a6fff9e'

from alembic import op
import sqlalchemy as sa

from tacker.db import types


def upgrade(active_plugins=None, options=None):
    op.create_table('events',
        sa.Column('id', sa.Integer, nullable=False, autoincrement=True),
        sa.Column('resource_id', types.Uuid, nullable=False),
        sa.Column('resource_state', sa.String(64), nullable=False),
        sa.Column('resource_type', sa.String(64), nullable=False),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('event_details', types.Json),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )
