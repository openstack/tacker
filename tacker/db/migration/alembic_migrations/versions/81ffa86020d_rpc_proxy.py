# Copyright 2014 OpenStack Foundation
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

"""rpc_proxy

Revision ID: 81ffa86020d
Revises: 1c6b0d82afcd
Create Date: 2014-03-19 15:50:11.712686

"""

# revision identifiers, used by Alembic.
revision = '81ffa86020d'
down_revision = '1c6b0d82afcd'

# Change to ['*'] if this migration applies to all plugins

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.create_table(
        'proxymgmtports',
        sa.Column('device_id', sa.String(255)),
        sa.Column('port_id', sa.String(36), nullable=False),
        sa.Column('dst_transport_url', sa.String(255)),
        sa.Column('svr_proxy_id', sa.String(36)),
        sa.Column('svr_ns_proxy_id', sa.String(36)),
        sa.Column('clt_proxy_id', sa.String(36)),
        sa.Column('clt_ns_proxy_id', sa.String(36)),
        sa.PrimaryKeyConstraint('device_id'),
    )
    op.create_table(
        'proxyserviceports',
        sa.Column('service_instance_id', sa.String(255)),
        sa.Column('svr_proxy_id', sa.String(36)),
        sa.Column('svr_ns_proxy_id', sa.String(36)),
        sa.Column('clt_proxy_id', sa.String(36)),
        sa.Column('clt_ns_proxy_id', sa.String(36)),
        sa.PrimaryKeyConstraint('service_instance_id'),
    )
