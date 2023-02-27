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

"""Alter value in deviceattributes

Revision ID: 24bec5f211c7
Revises: 2774a42c7163
Create Date: 2016-01-24 19:21:03.410029

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = '24bec5f211c7'
down_revision = '2774a42c7163'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    bind = op.get_bind()
    engine = bind.engine
    if engine.name == 'postgresql':
        text_type_maxlen = sa.VARCHAR(length=65535)
    else:
        text_type_maxlen = sa.TEXT(length=65535)

    op.alter_column('deviceattributes',
        'value', type_=text_type_maxlen, nullable=True)
