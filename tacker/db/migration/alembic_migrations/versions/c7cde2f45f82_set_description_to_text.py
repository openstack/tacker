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

"""set-description-to-text

Revision ID: c7cde2f45f82
Revises: 6e56d4474b2a
Create Date: 2016-06-01 10:58:43.022668

"""

# revision identifiers, used by Alembic.
revision = 'c7cde2f45f82'
down_revision = '6e56d4474b2a'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.alter_column('vims',
                    'description',
                    type_=sa.Text)
    op.alter_column('devices',
                    'description',
                    type_=sa.Text)
    op.alter_column('devicetemplates',
                    'description',
                    type_=sa.Text)
