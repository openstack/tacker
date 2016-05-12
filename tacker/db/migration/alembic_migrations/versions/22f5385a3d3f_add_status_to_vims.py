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

"""Add status to vims

Revision ID: 22f5385a3d3f
Revises: 5246a6bd410f
Create Date: 2016-05-12 13:29:30.615609

"""

# revision identifiers, used by Alembic.
revision = '22f5385a3d3f'
down_revision = '5f88e86b35c7'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.add_column('vims',
                  sa.Column('status', sa.String(255),
                            nullable=False, server_default=''))
