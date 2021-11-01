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

"""add grant and grant request

Revision ID: 3ff50553e9d3
Revises: 70df18f71ba2
Create Date: 2021-10-07 03:57:25.430532

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = '3ff50553e9d3'
down_revision = '70df18f71ba2'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.create_table('GrantV1',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('vnfInstanceId', sa.String(length=255), nullable=False),
        sa.Column('vnfLcmOpOccId', sa.String(length=255), nullable=False),
        sa.Column('vimConnectionInfo', sa.JSON(), nullable=True),
        sa.Column('zones', sa.JSON(), nullable=True),
        sa.Column('zoneGroups', sa.JSON(), nullable=True),
        sa.Column('addResources', sa.JSON(), nullable=True),
        sa.Column('tempResources', sa.JSON(), nullable=True),
        sa.Column('removeResources', sa.JSON(), nullable=True),
        sa.Column('updateResources', sa.JSON(), nullable=True),
        sa.Column('vimAssets', sa.JSON(), nullable=True),
        sa.Column('extVirtualLinks', sa.JSON(), nullable=True),
        sa.Column('extManagedVirtualLinks', sa.JSON(), nullable=True),
        sa.Column('additionalParams', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )

    op.create_table('GrantRequestV1',
        sa.Column('vnfInstanceId', sa.String(length=255), nullable=False),
        sa.Column('vnfLcmOpOccId', sa.String(length=255), nullable=False),
        sa.Column('vnfdId', sa.String(length=255), nullable=False),
        sa.Column('dstVnfdId', sa.String(length=255), nullable=True),
        sa.Column('flavourId', sa.String(length=255), nullable=True),
        sa.Column('operation',
                  sa.Enum('INSTANTIATE', 'SCALE', 'SCALE_TO_LEVEL',
                          'CHANGE_FLAVOUR', 'TERMINATE', 'HEAL', 'OPERATE',
                          'CHANGE_EXT_CONN', 'CREATE_SNAPSHOT',
                          'REVERT_TO_SNAPSHOT', 'CHANGE_VNFPKG'),
                  nullable=False),
        sa.Column('isAutomaticInvocation', sa.Boolean(), nullable=False),
        sa.Column('instantiationLevelId', sa.String(length=255),
                  nullable=True),
        sa.Column('addResources', sa.JSON(), nullable=True),
        sa.Column('tempResources', sa.JSON(), nullable=True),
        sa.Column('removeResources', sa.JSON(), nullable=True),
        sa.Column('updateResources', sa.JSON(), nullable=True),
        sa.Column('placementConstraints', sa.JSON(), nullable=True),
        sa.Column('vimConstraints', sa.JSON(), nullable=True),
        sa.Column('additionalParams', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('vnfLcmOpOccId'),
        mysql_engine='InnoDB'
    )
