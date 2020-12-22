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

"""change type for instance_id of vnf table

Revision ID: 7186440a306b
Revises: df26c5871f3c
Create Date: 2020-12-21 16:08:23.438871

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7186440a306b'
down_revision = 'df26c5871f3c'


def upgrade(active_plugins=None, options=None):
    op.alter_column('vnf',
                    'instance_id',
                    type_=sa.String(length=12800),
                    nullable=True)
