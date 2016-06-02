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

"""set-mandatory-columns-not-null

Revision ID: 354de64ba129
Revises: b07673bb8654
Create Date: 2016-06-02 10:05:22.299780

"""

# revision identifiers, used by Alembic.
revision = '354de64ba129'
down_revision = 'b07673bb8654'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    for table in ['devices', 'devicetemplates', 'vims', 'servicetypes']:
        op.alter_column(table,
                        'tenant_id',
                        existing_type=sa.String(64),
                        nullable=False)
