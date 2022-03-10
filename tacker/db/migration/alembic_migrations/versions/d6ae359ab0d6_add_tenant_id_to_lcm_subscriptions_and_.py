# Copyright 2022 OpenStack Foundation
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

"""add tenant_id to lcm_subscriptions and lcm_op_occs

Revision ID: d6ae359ab0d6
Revises: 3ff50553e9d3
Create Date: 2022-01-06 13:35:53.868106

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd6ae359ab0d6'
down_revision = '3ff50553e9d3'


def upgrade(active_plugins=None, options=None):
    op.add_column('vnf_lcm_subscriptions',
                  sa.Column('tenant_id', sa.String(length=64),
                  nullable=False))

    op.add_column('vnf_lcm_op_occs',
                  sa.Column('tenant_id', sa.String(length=64),
                  nullable=False))

    op.add_column('vnf_resources',
                  sa.Column('tenant_id', sa.String(length=64),
                  nullable=False))
