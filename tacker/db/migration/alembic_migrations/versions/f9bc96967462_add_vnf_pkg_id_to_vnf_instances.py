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

"""add_vnf_pkg_id_to_vnf_instances

Revision ID: f9bc96967462
Revises: e06fbdc90a32
Create Date: 2020-09-11 22:41:25.799693

"""

# revision identifiers, used by Alembic.
revision = 'f9bc96967462'
down_revision = 'e06fbdc90a32'

from alembic import op
import sqlalchemy as sa


from tacker.db import migration
from tacker.db import types


def upgrade(active_plugins=None, options=None):
    op.add_column('vnf_instances', sa.Column('vnf_pkg_id',
        types.Uuid(length=36), nullable=False))
