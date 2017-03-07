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

"""multisite_vim

Revision ID: 5246a6bd410f
Revises: 24bec5f211c7
Create Date: 2016-03-22 14:05:15.129330

"""

# revision identifiers, used by Alembic.
revision = '5246a6bd410f'
down_revision = '24bec5f211c7'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.create_table('vims',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=255), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('placement_attr', sa.PickleType(), nullable=True),
        sa.Column('shared', sa.Boolean(), server_default=sa.text(u'true'),
                  nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )
    op.create_table('vimauths',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('vim_id', sa.String(length=255), nullable=False),
        sa.Column('password', sa.String(length=128), nullable=False),
        sa.Column('auth_url', sa.String(length=255), nullable=False),
        sa.Column('vim_project', sa.PickleType(), nullable=False),
        sa.Column('auth_cred', sa.PickleType(), nullable=False),
        sa.ForeignKeyConstraint(['vim_id'], ['vims.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('auth_url')
    )
    op.add_column(u'devices', sa.Column('placement_attr', sa.PickleType(),
                                        nullable=True))
    op.add_column(u'devices', sa.Column('vim_id', sa.String(length=36),
                                        nullable=False))
    op.create_foreign_key(None, 'devices', 'vims', ['vim_id'], ['id'])
