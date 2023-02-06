# Copyright 2023 OpenStack Foundation
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

"""add_pm_threshold_table

Revision ID: 2531c976c0f1
Revises: de6bfa5bea46
Create Date: 2023-02-01 07:10:06.910825

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = '2531c976c0f1'
down_revision = 'de6bfa5bea46'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.create_table('ThresholdV2',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('objectType', sa.String(length=32), nullable=False),
        sa.Column('objectInstanceId', sa.String(length=255), nullable=False),
        sa.Column('subObjectInstanceIds', sa.JSON(), nullable=True),
        sa.Column('criteria', sa.JSON(), nullable=False),
        sa.Column('callbackUri', sa.String(length=255), nullable=False),
        sa.Column('authentication', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )
