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

"""audit support

Revision ID: 2ff0a0e360f1
Revises: 22f5385a3d50
Create Date: 2016-06-02 15:14:31.888078

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = '2ff0a0e360f1'
down_revision = '22f5385a3d50'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    for table in ['vims', 'vnf', 'vnfd']:
        op.add_column(table,
                      sa.Column('created_at', sa.DateTime(), nullable=True))
        op.add_column(table,
                      sa.Column('updated_at', sa.DateTime(), nullable=True))
