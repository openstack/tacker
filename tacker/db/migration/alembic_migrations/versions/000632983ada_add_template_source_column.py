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

"""add template_source column

Revision ID: 000632983ada
Revises: 0ae5b1ce3024
Create Date: 2016-12-22 20:30:03.931290

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = '000632983ada'
down_revision = '0ad3bbce1c19'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.add_column('vnfd', sa.Column('template_source', sa.String(length=255)))
