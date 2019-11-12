# Copyright (C) 2019 NTT DATA
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

"""add db tables for vnf packages

Revision ID: 9d425296f2c3
Revises: cd04a8335c18
Create Date: 2019-06-03 08:37:05.095587

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = '9d425296f2c3'
down_revision = 'cd04a8335c18'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Boolean

from tacker.db import types


def upgrade(active_plugins=None, options=None):
    op.create_table(
        'vnf_packages',
        sa.Column('id', types.Uuid(length=36), nullable=False),
        sa.Column('onboarding_state', sa.String(length=255), nullable=False),
        sa.Column('operational_state', sa.String(length=255), nullable=False),
        sa.Column('usage_state', sa.String(length=255), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('algorithm', sa.String(length=64), nullable=True),
        sa.Column('hash', sa.String(length=128), nullable=True),
        sa.Column('location_glance_store', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', Boolean, default=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )
    op.create_table(
        'vnf_packages_user_data',
        sa.Column('id', sa.Integer, nullable=False, autoincrement=True),
        sa.Column('package_uuid', types.Uuid(length=36), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', Boolean, default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['package_uuid'],
                                ['vnf_packages.id'], ),
        sa.Index('vnf_packages_user_data_key_idx', 'key'),
        sa.Index('vnf_packages_user_data_value_idx', 'value'),
        sa.UniqueConstraint('id', 'key', 'deleted',
                name='uniq_vnf_packages_user_data0idid0key0deleted'),
        mysql_engine='InnoDB'
    )
    op.create_table(
        'vnf_package_vnfd',
        sa.Column('id', types.Uuid(length=36), nullable=False),
        sa.Column('package_uuid', types.Uuid(length=36), nullable=False),
        sa.Column('vnfd_id', types.Uuid(length=36), nullable=False),
        sa.Column('vnf_provider', sa.String(length=255), nullable=False),
        sa.Column('vnf_product_name', sa.String(length=255), nullable=False),
        sa.Column('vnf_software_version', sa.String(length=255),
                  nullable=False),
        sa.Column('vnfd_version', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', Boolean, default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['package_uuid'],
                                ['vnf_packages.id'], ),
        mysql_engine='InnoDB'
    )
    op.create_table(
        'vnf_deployment_flavours',
        sa.Column('id', types.Uuid(length=36), nullable=False),
        sa.Column('package_uuid', types.Uuid(length=36), nullable=False),
        sa.Column('flavour_id', sa.String(length=255), nullable=False),
        sa.Column('flavour_description', sa.Text(), nullable=False),
        sa.Column('instantiation_levels', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', Boolean, default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['package_uuid'],
                                ['vnf_packages.id'], ),
        mysql_engine='InnoDB'
    )
    op.create_table(
        'vnf_software_images',
        sa.Column('id', types.Uuid(length=36), nullable=False),
        sa.Column('software_image_id', sa.String(length=255), nullable=False),
        sa.Column('flavour_uuid', types.Uuid(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=255), nullable=False),
        sa.Column('version', sa.String(length=255), nullable=False),
        sa.Column('algorithm', sa.String(length=64), nullable=False),
        sa.Column('hash', sa.String(length=128), nullable=False),
        sa.Column('container_format', sa.String(length=20), nullable=False),
        sa.Column('disk_format', sa.String(length=20), nullable=False),
        sa.Column('min_disk', sa.Integer, nullable=False),
        sa.Column('min_ram', sa.Integer, nullable=False),
        sa.Column('size', sa.BigInteger, nullable=False),
        sa.Column('image_path', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', Boolean, default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['flavour_uuid'],
                                ['vnf_deployment_flavours.id'], ),
        mysql_engine='InnoDB'
    )
    op.create_table(
        'vnf_software_image_metadata',
        sa.Column('id', sa.Integer, nullable=False, autoincrement=True),
        sa.Column('image_uuid', types.Uuid(length=36), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', Boolean, default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['image_uuid'],
                                ['vnf_software_images.id'], ),
        sa.Index('vnf_software_image_metadata_key_idx', 'key'),
        sa.Index('vnf_software_image_metadata_value_idx', 'value'),
        sa.UniqueConstraint('id', 'key', 'deleted',
                name='uniq_vnf_software_image_metadata0idid0key0deleted'),
        mysql_engine='InnoDB'
    )
