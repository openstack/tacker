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

"""set-status-type-tenant-id-length

Revision ID: b07673bb8654
Revises: c7cde2f45f82
Create Date: 2016-06-01 12:46:07.499279

"""

# revision identifiers, used by Alembic.
revision = 'b07673bb8654'
down_revision = 'c7cde2f45f82'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    for table in ['devices', 'devicetemplates', 'vims', 'servicetypes']:
        op.alter_column(table,
                        'tenant_id',
                        type_=sa.String(64), nullable=False)
    op.alter_column('vims',
                    'type',
                    type_=sa.String(64))
    op.alter_column('devices',
                    'instance_id',
                    type_=sa.String(64), nullable=True)
    op.alter_column('devices',
                    'status',
                    type_=sa.String(64))
    op.alter_column('proxymgmtports',
                    'device_id',
                    type_=sa.String(64), nullable=False)
    op.alter_column('proxyserviceports',
                    'service_instance_id',
                    type_=sa.String(64), nullable=False)
    op.alter_column('servicetypes',
                    'service_type',
                    type_=sa.String(64))
