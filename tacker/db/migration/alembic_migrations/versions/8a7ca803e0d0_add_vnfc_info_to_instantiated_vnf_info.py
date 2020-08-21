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

"""add_vnfc_info_to_instantiated_vnf_info

Revision ID: 8a7ca803e0d0
Revises: aaf461c8844c
Create Date: 2020-09-21 15:00:00.004343

"""

# revision identifiers, used by Alembic.
revision = '8a7ca803e0d0'
down_revision = 'aaf461c8844c'

from alembic import op
import sqlalchemy as sa


from tacker.db import migration


def upgrade(active_plugins=None, options=None):
    op.add_column('vnf_instantiated_info',
                  sa.Column('vnfc_info', sa.JSON(), nullable=True))
