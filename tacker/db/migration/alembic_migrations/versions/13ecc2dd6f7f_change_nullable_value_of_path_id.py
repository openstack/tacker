# Copyright 2018 OpenStack Foundation
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

"""Change nullable value of path_id

Revision ID: 13ecc2dd6f7f
Revises: 4747cc26b9c6
Create Date: 2018-07-24 16:47:01.378226

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = '13ecc2dd6f7f'
down_revision = '4747cc26b9c6'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.alter_column('vnffgchains', 'path_id',
               existing_type=sa.String(length=255),
               nullable=True)
    op.alter_column('vnffgnfps', 'path_id',
               existing_type=sa.String(length=255),
               nullable=True)
