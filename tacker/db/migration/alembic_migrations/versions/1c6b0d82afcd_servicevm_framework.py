# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2013 Intel Corporation.
# Copyright 2013 Isaku Yamahata <isaku.yamahata at intel com>
#                               <isaku.yamahata at gmail com>
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
# @author: Isaku Yamahata, Intel Corporation.

"""add tables for servicevm framework

Revision ID: 1c6b0d82afcd
Revises: 2db5203cb7a9
Create Date: 2013-11-25 18:06:13.980301

"""

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
        sa.Column('device_driver', sa.String(length=255), nullable=True),
        sa.Column('mgmt_driver', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'servicetypes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=True),
        sa.Column('template_id', sa.String(length=36), nullable=False),
        sa.Column('service_type', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'devicetemplateattributes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('template_id', sa.String(length=36), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['devicetemplates.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'devices',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=True),
        sa.Column('template_id', sa.String(length=36), nullable=True),
        sa.Column('instance_id', sa.String(length=255), nullable=True),
        sa.Column('mgmt_address', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['devicetemplates.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'deviceargs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('device_id', sa.String(length=36)),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'deviceservicecontexts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('device_id', sa.String(length=36)),
        sa.Column('network_id', sa.String(length=36), nullable=True),
        sa.Column('subnet_id', sa.String(length=36), nullable=True),
        sa.Column('port_id', sa.String(length=36), nullable=True),
        sa.Column('router_id', sa.String(length=36), nullable=True),
        sa.Column('role', sa.String(length=256), nullable=True),
        sa.Column('index', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'serviceinstances',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('service_type_id', sa.String(length=36), nullable=True),
        sa.Column('service_table_id', sa.String(length=36), nullable=True),
        sa.Column('managed_by_user', sa.Boolean(), nullable=False),
        sa.Column('mgmt_driver', sa.String(length=255), nullable=True),
        sa.Column('mgmt_address', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['service_type_id'], ['servicetypes.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'servicecontexts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('service_instance_id', sa.String(length=36)),
        sa.Column('network_id', sa.String(length=36), nullable=True),
        sa.Column('subnet_id', sa.String(length=36), nullable=True),
        sa.Column('port_id', sa.String(length=36), nullable=True),
        sa.Column('router_id', sa.String(length=36), nullable=True),
        sa.Column('role', sa.String(length=256), nullable=True),
        sa.Column('index', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'servicedevicebindings',
        sa.Column('service_instance_id', sa.String(length=36), nullable=True),
        sa.Column('device_id', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
        sa.ForeignKeyConstraint(['service_instance_id'],
                                ['serviceinstances.id'], ),
        sa.PrimaryKeyConstraint('service_instance_id'),
        sa.PrimaryKeyConstraint('device_id'),
    )


def downgrade(active_plugins=None, options=None):
    op.drop_table('devicetemplates')
    op.drop_table('servicetypes')
    op.drop_table('devicetemplateattributes')
    op.drop_table('devices')
    op.drop_table('deviceargs')
    op.drop_table('deviceservicecontexts')
    op.drop_table('serviceinstances')
    op.drop_table('servicecontexts')
    op.drop_table('servicedevicebindings')
