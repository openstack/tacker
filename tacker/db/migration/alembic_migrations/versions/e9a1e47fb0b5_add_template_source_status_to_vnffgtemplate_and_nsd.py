# Copyright 2017 OpenStack Foundation
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

"""add onboarded status for vnffgd and nsd

Revision ID: e9a1e47fb0b5
Revises: f5c1c3b0f6b4
Create Date: 2017-07-17 10:02:37.572587

"""

# revision identifiers, used by Alembic.
revision = 'e9a1e47fb0b5'
down_revision = 'f5c1c3b0f6b4'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.add_column('vnffgtemplates',
                  sa.Column('template_source',
                            sa.String(length=255),
                            server_default='onboarded'))
    op.execute("UPDATE vnffgtemplates set template_source='onboarded'"
        " WHERE template_source is NULL")

    op.add_column('nsd',
                  sa.Column('template_source',
                            sa.String(length=255),
                            server_default='onboarded'))
    op.execute("UPDATE nsd set template_source='onboarded'"
        " WHERE template_source is NULL")
