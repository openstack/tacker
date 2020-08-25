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

"""add placement table

Revision ID: 2c5211036579
Revises: ee98bbc0789d
Create Date: 2020-09-11 20:47:46.345771

"""
# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = '2c5211036579'
down_revision = 'ee98bbc0789d'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Boolean

from tacker.db import types


def upgrade(active_plugins=None, options=None):
    op.create_table(
        'placement_constraint',
        sa.Column('id', types.Uuid(length=36), nullable=False),
        sa.Column('vnf_instance_id', types.Uuid(length=36), nullable=False),
        sa.Column('affinity_or_anti_affinity',
                  sa.String(length=255), nullable=False),
        sa.Column('scope',  sa.String(length=255), nullable=False),
        sa.Column('server_group_name',  sa.String(length=255), nullable=False),
        sa.Column('resource', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', Boolean, default=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )
