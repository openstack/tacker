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

"""add_vnf_metadata_to_vnflcm_db

Revision ID: 745e3e9fe5e2
Revises: f9bc96967462
Create Date: 2020-08-28 20:21:04.604343

"""

# revision identifiers, used by Alembic.
revision = '745e3e9fe5e2'
down_revision = 'f9bc96967462'

from alembic import op
import sqlalchemy as sa


from tacker.db import migration


def upgrade(active_plugins=None, options=None):
    op.add_column('vnf_instances',
                  sa.Column('vnf_metadata', sa.JSON(), nullable=True))
