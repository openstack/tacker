# Copyright 2015 OpenStack Foundation
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

"""add description to vnf

Revision ID: 13c0e0661015
Revises: 4c31092895b8
Create Date: 2015-05-18 18:47:22.180962

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = '13c0e0661015'
down_revision = '4c31092895b8'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.add_column('devices',
                  sa.Column('description', sa.String(255),
                            nullable=True, server_default=''))
