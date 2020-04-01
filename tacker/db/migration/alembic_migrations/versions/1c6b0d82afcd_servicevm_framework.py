# Copyright 2013 Intel Corporation.
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

"""add tables for tacker framework

Revision ID: 1c6b0d82afcd
Revises: 2db5203cb7a9
Create Date: 2013-11-25 18:06:13.980301

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = '1c6b0d82afcd'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.create_table(
        'devicetemplates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('infra_driver', sa.String(length=255), nullable=True),
        sa.Column('mgmt_driver', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'devicetemplateattributes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('template_id', sa.String(length=36), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.String(length=4096), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['devicetemplates.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'devices',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('template_id', sa.String(length=36), nullable=True),
        sa.Column('instance_id', sa.String(length=255), nullable=True),
        sa.Column('mgmt_url', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['devicetemplates.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'deviceattributes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('device_id', sa.String(length=255)),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.String(length=4096), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
