# Copyright 2015 OpenStack Foundation
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

"""modify datatype of value

Revision ID: 5958429bcb3c
Revises: 13c0e0661015
Create Date: 2015-10-05 17:09:24.710961

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = '5958429bcb3c'
down_revision = '13c0e0661015'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.alter_column('devicetemplateattributes',
                    'value', type_=sa.TEXT(65535), nullable=True)
