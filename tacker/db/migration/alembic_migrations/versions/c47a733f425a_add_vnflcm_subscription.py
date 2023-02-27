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

"""add_vnflcm_subscription

Revision ID: c47a733f425a
Revises: 8a7ca803e0d0 
Create Date: 2020-08-27 14:18:43.907565

"""

# revision identifiers, used by Alembic.
revision = 'c47a733f425a'
down_revision = '8a7ca803e0d0'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Boolean

from tacker.db import types


def upgrade(active_plugins=None, options=None):

    bind = op.get_bind()
    engine = bind.engine
    if engine.name == 'postgresql':
        deleted_type = sa.SmallInteger
        notif_type = "decode(filter->>'$.notificationTypes','escape')"
        notif_type_len = "coalesce \
                (json_array_length(filter->'$.notificationTypes'),0)"
        op_state = "decode(filter->>'$.operationStates','escape')"
        op_state_len = "coalesce \
                (json_array_length(filter->'$.operationStates'),0)"

    else:
        deleted_type = Boolean
        notif_type = "json_unquote \
                (json_extract('filter','$.notificationTypes'))"
        notif_type_len = "ifnull(json_length('notification_types'),0)"
        op_state = "json_unquote(json_extract('filter','$.operationStates'))"
        op_state_len = "ifnull(json_length('operation_states'),0)"

    op.create_table(
        'vnf_lcm_subscriptions',
        sa.Column('id', types.Uuid(length=36), nullable=False),
        sa.Column('callback_uri', sa.String(length=255), nullable=False),
        sa.Column('subscription_authentication', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', deleted_type, default=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )

    op.create_table(
        'vnf_lcm_filters',
        sa.Column('id', sa.Integer, autoincrement=True, nullable=False),
        sa.Column('subscription_uuid', sa.String(length=36), nullable=False),
        sa.Column('filter', sa.JSON(), nullable=False),
        sa.Column('notification_types',
                  sa.LargeBinary(length=65536),
                  sa.Computed(notif_type)),
        sa.Column('notification_types_len',
                  sa.Integer,
                  sa.Computed(notif_type_len)),
        sa.Column('operation_states',
                  sa.LargeBinary(length=65536),
                  sa.Computed(op_state)),
        sa.Column('operation_states_len',
                  sa.Integer,
                  sa.Computed(op_state_len)),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['subscription_uuid'],
                                ['vnf_lcm_subscriptions.id'], ),
        mysql_engine='InnoDB'
    )

    op.create_table(
        'vnf_lcm_op_occs',
        sa.Column('id', types.Uuid(length=36), nullable=False),
        sa.Column('operation_state', sa.String(length=255), nullable=False),
        sa.Column('state_entered_time',  sa.DateTime(), nullable=False),
        sa.Column('start_time',  sa.DateTime(), nullable=False),
        sa.Column('vnf_instance_id', types.Uuid(length=36), nullable=False),
        sa.Column('operation', sa.String(length=255), nullable=False),
        sa.Column('is_automatic_invocation', deleted_type, nullable=False),
        sa.Column('operation_params', sa.JSON(), nullable=True),
        sa.Column('error', sa.JSON(), nullable=True),
        sa.Column('deleted', deleted_type, default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['vnf_instance_id'],
                                ['vnf_instances.id'], ),
        mysql_engine='InnoDB'
    )
