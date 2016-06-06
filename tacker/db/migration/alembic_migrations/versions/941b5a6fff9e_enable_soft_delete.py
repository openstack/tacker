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

"""enable soft delete

Revision ID: 941b5a6fff9e
Revises: 2ff0a0e360f1
Create Date: 2016-06-06 10:12:49.787430

"""

# revision identifiers, used by Alembic.
revision = '941b5a6fff9e'
down_revision = '2ff0a0e360f1'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    for table in ['vims', 'vnf', 'vnfd']:
        op.add_column(table,
                      sa.Column('deleted_at', sa.DateTime(), nullable=True))

    # unique constraint is taken care by the nfvo_db plugin to support
    # soft deletion of vim
    op.drop_index('auth_url', table_name='vimauths')
