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

"""create of Network service tables

Revision ID: 0ad3bbce1c18
Revises: 0ae5b1ce3024
Create Date: 2016-12-17 19:41:01.906138

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = '0ad3bbce1c18'
down_revision = '8f7145914cb0'

from alembic import op
import sqlalchemy as sa

from tacker.db import types


def upgrade(active_plugins=None, options=None):
    op.create_table('nsd',
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('id', types.Uuid(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('vnfds', types.Json, nullable=True),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )
    op.create_table('ns',
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('id', types.Uuid(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('nsd_id', types.Uuid(length=36), nullable=True),
        sa.Column('vim_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('vnf_ids', sa.TEXT(length=65535), nullable=True),
        sa.Column('mgmt_urls', sa.TEXT(length=65535), nullable=True),
        sa.Column('status', sa.String(length=64), nullable=False),
        sa.Column('error_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['nsd_id'], ['nsd.id'], ),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )
    op.create_table('nsd_attribute',
        sa.Column('id', types.Uuid(length=36), nullable=False),
        sa.Column('nsd_id', types.Uuid(length=36), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.TEXT(length=65535), nullable=True),
        sa.ForeignKeyConstraint(['nsd_id'], ['nsd.id'], ),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )
