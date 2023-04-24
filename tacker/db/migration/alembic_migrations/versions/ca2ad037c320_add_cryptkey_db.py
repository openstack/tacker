# Copyright 2023 Fujitsu
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

"""add db tables for crypt key

Revision ID: ca2ad037c320
Revises: 4c0e2e2c2e02
Create Date: 2023-04-13 05:41:47.422051

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Boolean

from tacker.db import types

# revision identifiers, used by Alembic.
revision = 'ca2ad037c320'
down_revision = '4c0e2e2c2e02'


def upgrade(active_plugins=None, options=None):
    op.create_table(
        'CryptKey',
        sa.Column('id', types.Uuid(length=36), nullable=False),
        sa.Column('secretUuid', sa.String(36), nullable=True),
        sa.Column('encryptedKey', sa.String(255), nullable=False),
        sa.Column('keyType', sa.String(36), nullable=False),
        sa.Column('inUse', Boolean, nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )
