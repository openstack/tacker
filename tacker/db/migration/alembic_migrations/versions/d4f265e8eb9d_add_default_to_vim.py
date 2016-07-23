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

"""add default to vim

Revision ID: d4f265e8eb9d
Revises: 22f5385a3d3f
Create Date: 2016-07-14 11:07:28.115225

"""

# revision identifiers, used by Alembic.
revision = 'd4f265e8eb9d'
down_revision = '22f5385a3d3f'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql


def upgrade(active_plugins=None, options=None):
    op.add_column('vims', sa.Column('is_default',
                  sa.Boolean(),
                  server_default=sql.false(),
                  nullable=False))
