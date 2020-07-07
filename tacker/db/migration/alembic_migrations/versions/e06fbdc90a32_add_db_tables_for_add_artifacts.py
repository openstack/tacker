# Copyright (C) 2020 FUJITSU DATA
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
#

"""add db tables for add artifacts

Revision ID: e06fbdc90a32
Revises: d2e39e01d540
Create Date: 2020-09-17 02:52:41.435112

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = 'e06fbdc90a32'
down_revision = 'd2e39e01d540'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Boolean

from tacker.db import types


def upgrade(active_plugins=None, options=None):
    op.create_table(
        'vnf_artifacts',
        sa.Column('id', types.Uuid(length=36), nullable=False),
        sa.Column('package_uuid', types.Uuid(length=36), nullable=False),
        sa.Column('artifact_path', sa.Text(), nullable=False),
        sa.Column('algorithm', sa.String(64), nullable=False),
        sa.Column('hash', sa.String(128), nullable=False),
        sa.Column('_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', Boolean, default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['package_uuid'],
                                ['vnf_packages.id'], ),
        mysql_engine='InnoDB'
    )
