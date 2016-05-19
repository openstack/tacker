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

"""make VNFD/VNF/VIM name mandatory

Revision ID: 5f88e86b35c7
Revises: 354de64ba129
Create Date: 2016-06-14 11:16:16.303343

"""

# revision identifiers, used by Alembic.
revision = '5f88e86b35c7'
down_revision = '354de64ba129'

from alembic import op
from sqlalchemy.dialects import mysql


def upgrade(active_plugins=None, options=None):
    op.alter_column('devices', 'name',
               existing_type=mysql.VARCHAR(length=255),
               nullable=False)
    op.alter_column('devicetemplates', 'name',
               existing_type=mysql.VARCHAR(length=255),
               nullable=False)
    op.alter_column('vims', 'name',
               existing_type=mysql.VARCHAR(length=255),
               nullable=False)
