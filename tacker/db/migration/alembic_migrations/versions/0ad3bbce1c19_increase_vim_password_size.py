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

"""increase_vim_password_size

Revision ID: 0ad3bbce1c19
Revises: 0ad3bbce1c19
Create Date: 2017-01-17 09:50:46.296206

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0ad3bbce1c19'
down_revision = '0ad3bbce1c18'


def upgrade(active_plugins=None, options=None):
    op.alter_column('vimauths',
                    'password',
                    type_=sa.String(length=255))
