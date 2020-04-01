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

"""add support vnffg to ns database

Revision ID: 4747cc26b9c6
Revises: 5d490546290c
Create Date: 2018-06-27 03:18:12.227673

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = '4747cc26b9c6'
down_revision = '5d490546290c'

from alembic import op
import sqlalchemy as sa

from tacker.db import types


def upgrade(active_plugins=None, options=None):
    op.add_column('ns', sa.Column(
        'vnffg_ids', sa.TEXT(length=65535), nullable=True))
    op.add_column('vnffgs', sa.Column(
        'ns_id', types.Uuid(length=36), nullable=True))
    op.create_foreign_key('vnffg_foreign_key',
                          'vnffgs', 'ns',
                          ['ns_id'], ['id'])
