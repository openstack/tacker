# Copyright (C) 2020 NTT DATA
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

# flake8: noqa: E402

"""VNF instance management changes

Revision ID: 985e28392890
Revises: 975e28392888
Create Date: 2019-12-10 02:40:12.966027

"""

# revision identifiers, used by Alembic.
revision = '985e28392890'
down_revision = '975e28392888'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Boolean

from tacker.db import types


def upgrade(active_plugins=None, options=None):
    op.create_table(
        'vnf_instances',
        sa.Column('id', types.Uuid(length=36), nullable=False),
        sa.Column('vnf_instance_name', sa.String(length=255), nullable=True,
            default=""),
        sa.Column('vnf_instance_description',
                  sa.String(length=1024), nullable=True, default=""),
        sa.Column('vnfd_id', types.Uuid(length=36), nullable=False),
        sa.Column('vnf_provider', sa.String(length=255), nullable=False),
        sa.Column('vnf_product_name', sa.String(length=255), nullable=False),
        sa.Column('vnf_software_version', sa.String(length=255),
                  nullable=False),
        sa.Column('vnfd_version', sa.String(length=255), nullable=False),
        sa.Column('instantiation_state',
                  sa.String(length=255), nullable=False),
        sa.Column('task_state',
                  sa.String(length=255), nullable=True),
        sa.Column('vim_connection_info', sa.JSON(), nullable=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.Boolean, default=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )

    op.create_table(
        'vnf_instantiated_info',
        sa.Column('id', sa.Integer, nullable=False, autoincrement=True),
        sa.Column('vnf_instance_id', types.Uuid(length=36), nullable=False),
        sa.Column('flavour_id', sa.String(length=255), nullable=False),
        sa.Column('ext_cp_info', sa.JSON(), nullable=True),
        sa.Column('ext_virtual_link_info', sa.JSON(), nullable=True),
        sa.Column('ext_managed_virtual_link_info', sa.JSON(), nullable=True),
        sa.Column('vnfc_resource_info', sa.JSON(), nullable=True),
        sa.Column('vnf_virtual_link_resource_info', sa.JSON(), nullable=True),
        sa.Column('virtual_storage_resource_info', sa.JSON(), nullable=True),
        sa.Column('vnf_state', sa.String(length=255), nullable=False),
        sa.Column('instance_id', sa.String(length=255), nullable=True),
        sa.Column('instantiation_level_id',
                  sa.String(length=255), nullable=True),
        sa.Column('additional_params', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', Boolean, default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['vnf_instance_id'],
                                ['vnf_instances.id'], ),
        mysql_engine='InnoDB'
    )

    op.create_table(
        'vnf_resources',
        sa.Column('id', types.Uuid(length=36), nullable=False),
        sa.Column('vnf_instance_id', types.Uuid(length=36), nullable=False),
        sa.Column('resource_name', sa.String(length=255), nullable=False),
        sa.Column('resource_type', sa.String(length=255), nullable=False),
        sa.Column('resource_identifier', sa.String(length=255),
                  nullable=False),
        sa.Column('resource_status', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', Boolean, default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['vnf_instance_id'],
                                ['vnf_instances.id'], ),
        mysql_engine='InnoDB'
    )
