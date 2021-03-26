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

"""add_column_to_vnf_lcm_op_occs

Revision ID: 3adac34764da
Revises: 62d18199909e
Create Date: 2021-02-16 16:19:12.100380

"""

# revision identifiers, used by Alembic.
revision = '3adac34764da'
down_revision = '7186440a306b'

from alembic import op

import sqlalchemy as sa
from tacker.db import migration


def upgrade(active_plugins=None, options=None):
    op.add_column('vnf_lcm_op_occs',
        sa.Column('grant_id', sa.VARCHAR(length=36), nullable=True))
    op.add_column('vnf_lcm_op_occs',
        sa.Column('changed_ext_connectivity', sa.JSON(), nullable=True))
