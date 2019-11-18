# Copyright 2019 OpenStack Foundation
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

"""add size column to vnf_packages table

Revision ID: d2e39e01d540
Revises: 985e28392890
Create Date: 2019-11-27 13:30:23.599865

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd2e39e01d540'
down_revision = '985e28392890'


# Added 'size' column to an existing table. Server_default bit will make
# existing rows 0 for that column
def upgrade(active_plugins=None, options=None):
    op.add_column('vnf_packages', sa.Column('size', sa.BigInteger,
                                           nullable=False,
                                           server_default='0'))
