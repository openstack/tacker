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

"""adds_VNFFG

Revision ID: 507122918800
Revises: 4ee19c8a6d0a
Create Date: 2016-07-29 21:48:18.816277

"""

# revision identifiers, used by Alembic.
revision = '507122918800'
down_revision = '4ee19c8a6d0a'

import sqlalchemy as sa

from alembic import op
from tacker.db.types import Json


def upgrade(active_plugins=None, options=None):

    op.create_table(
        'vnffgtemplates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('template', Json),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )

    op.create_table(
        'vnffgs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('vnffgd_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=255), nullable=False),
        sa.Column('vnf_mapping', Json),
        sa.ForeignKeyConstraint(['vnffgd_id'], ['vnffgtemplates.id'], ),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )

    op.create_table(
        'vnffgnfps',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('vnffg_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=255), nullable=False),
        sa.Column('path_id', sa.String(length=255), nullable=False),
        sa.Column('symmetrical', sa.Boolean, default=False),
        sa.ForeignKeyConstraint(['vnffg_id'], ['vnffgs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )

    op.create_table(
        'vnffgchains',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('instance_id', sa.String(length=255), nullable=True),
        sa.Column('nfp_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=255), nullable=False),
        sa.Column('path_id', sa.String(length=255), nullable=False),
        sa.Column('symmetrical', sa.Boolean, default=False),
        sa.Column('chain', Json),
        sa.ForeignKeyConstraint(['nfp_id'], ['vnffgnfps.id'], ),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )

    op.create_table(
        'vnffgclassifiers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('nfp_id', sa.String(length=36), nullable=False),
        sa.Column('instance_id', sa.String(length=255), nullable=True),
        sa.Column('chain_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['nfp_id'], ['vnffgnfps.id'], ),
        sa.ForeignKeyConstraint(['chain_id'], ['vnffgchains.id'], ),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )

    op.create_table(
        'aclmatchcriterias',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('vnffgc_id', sa.String(length=36), nullable=False),
        sa.Column('eth_src', sa.String(length=36), nullable=True),
        sa.Column('eth_dst', sa.String(length=36), nullable=True),
        sa.Column('eth_type', sa.String(length=36), nullable=True),
        sa.Column('vlan_id', sa.Integer, nullable=True),
        sa.Column('vlan_pcp', sa.Integer, nullable=True),
        sa.Column('mpls_label', sa.Integer, nullable=True),
        sa.Column('mpls_tc', sa.Integer, nullable=True),
        sa.Column('ip_dscp', sa.Integer, nullable=True),
        sa.Column('ip_ecn', sa.Integer, nullable=True),
        sa.Column('ip_src_prefix', sa.String(length=36), nullable=True),
        sa.Column('ip_dst_prefix', sa.String(length=36), nullable=True),
        sa.Column('source_port_min', sa.Integer, nullable=True),
        sa.Column('source_port_max', sa.Integer, nullable=True),
        sa.Column('destination_port_min', sa.Integer, nullable=True),
        sa.Column('destination_port_max', sa.Integer, nullable=True),
        sa.Column('ip_proto', sa.Integer, nullable=True),
        sa.Column('network_id', sa.String(length=36), nullable=True),
        sa.Column('network_src_port_id', sa.String(length=36), nullable=True),
        sa.Column('network_dst_port_id', sa.String(length=36), nullable=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=True),
        sa.Column('icmpv4_type', sa.Integer, nullable=True),
        sa.Column('icmpv4_code', sa.Integer, nullable=True),
        sa.Column('arp_op', sa.Integer, nullable=True),
        sa.Column('arp_spa', sa.Integer, nullable=True),
        sa.Column('arp_tpa', sa.Integer, nullable=True),
        sa.Column('arp_sha', sa.Integer, nullable=True),
        sa.Column('arp_tha', sa.Integer, nullable=True),
        sa.Column('ipv6_src', sa.String(36), nullable=True),
        sa.Column('ipv6_dst', sa.String(36), nullable=True),
        sa.Column('ipv6_flabel', sa.Integer, nullable=True),
        sa.Column('icmpv6_type', sa.Integer, nullable=True),
        sa.Column('icmpv6_code', sa.Integer, nullable=True),
        sa.Column('ipv6_nd_target', sa.String(36), nullable=True),
        sa.Column('ipv6_nd_sll', sa.String(36), nullable=True),
        sa.Column('ipv6_nd_tll', sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(['vnffgc_id'], ['vnffgclassifiers.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
