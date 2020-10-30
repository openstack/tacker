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

# flake8: noqa: E402

"""mod_vnflcm_subscription

Revision ID: d25c7c865ce8
Revises: 2c5211036579
Create Date: 2020-10-15 14:27:04.946002

"""

# revision identifiers, used by Alembic.
revision = 'd25c7c865ce8'
down_revision = '2c5211036579'

from alembic import op
import sqlalchemy as sa
from tacker.db import types

from tacker.db import migration

def upgrade(active_plugins=None, options=None):

    op.alter_column('vnf_lcm_filters', 'subscription_uuid',
        type_=types.Uuid(length=36), existing_type=sa.String(length=255),
        nullable=False)

    sta_str = "json_unquote(json_extract('filter','$.operationTypes'))"
    op.add_column(
        'vnf_lcm_filters',
        sa.Column('operation_types',
                  sa.LargeBinary(length=65536),
                  sa.Computed(sta_str)))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column('operation_types_len',
                  sa.Integer,
                  sa.Computed("ifnull(json_length('operation_types'),0)")))

    op.drop_column('vnf_lcm_filters', 'operation_states')
    op.drop_column('vnf_lcm_filters', 'operation_states_len')

    op.alter_column('vnf_lcm_op_occs', 'operation_state',
       type_=sa.String(length=16), existing_type=sa.String(length=255))

    op.alter_column('vnf_lcm_op_occs', 'operation',
        type_=sa.String(length=16),existing_type=sa.String(length=255))

    op.add_column('vnf_lcm_op_occs',
        sa.Column('is_cancel_pending', sa.Boolean, nullable=False)),

    op.add_column('vnf_lcm_op_occs',
        sa.Column('resource_changes', sa.JSON(), nullable=True))

    op.add_column('vnf_lcm_op_occs',
        sa.Column('error_point', sa.Integer, nullable=True))

    op.add_column('vnf_lcm_op_occs',
        sa.Column('changed_info', sa.JSON(), nullable=True))

    op.add_column('vnf_lcm_op_occs',
        sa.Column('created_at', sa.DateTime(), nullable=False))

    op.add_column('vnf_lcm_op_occs',
        sa.Column('updated_at', sa.DateTime(), nullable=True))

    op.add_column('vnf_lcm_op_occs',
        sa.Column('deleted_at', sa.DateTime(), nullable=True))
