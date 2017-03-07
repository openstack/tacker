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

"""Add error_reason to device

Revision ID: acf941e54075
Revises: 5246a6bd410f
Create Date: 2016-04-07 23:53:56.623647

"""

# revision identifiers, used by Alembic.
revision = 'acf941e54075'
down_revision = '5246a6bd410f'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.add_column('devices', sa.Column('error_reason',
        sa.Text(), nullable=True))
