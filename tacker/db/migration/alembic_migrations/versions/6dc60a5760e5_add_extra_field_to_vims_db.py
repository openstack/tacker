# Copyright 2021 OpenStack Foundation
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

# flake8: noqa: E402

"""add extra field to vims db

Revision ID: 6dc60a5760e5
Revises: c31f65e0d099
Create Date: 2021-07-26 12:28:13.797458

"""

# revision identifiers, used by Alembic.
revision = '6dc60a5760e5'
down_revision = 'c31f65e0d099'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.add_column('vims',
                  sa.Column('extra', sa.JSON(), nullable=True))
