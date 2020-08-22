# Copyright 2020 OpenStack Foundation
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

"""add scale column

Revision ID: ee98bbc0789d
Revises: c47a733f425a
Create Date: 2020-09-11 16:39:04.039173

"""
# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = 'ee98bbc0789d'
down_revision = 'c47a733f425a'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.add_column('vnf_instantiated_info',
                  sa.Column('scale_status', sa.JSON(), nullable=True))
