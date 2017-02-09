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

"""add default onboarded template source

Revision ID: ef14f8026327
Revises: e8918cda6433
Create Date: 2017-02-10 12:10:09.606460

"""

# revision identifiers, used by Alembic.
revision = 'ef14f8026327'
down_revision = 'e8918cda6433'

from alembic import op


def upgrade(active_plugins=None, options=None):
    op.alter_column('vnfd', 'template_source',
                    server_default="onboarded")

    op.execute("UPDATE vnfd set template_source='onboarded'"
       " WHERE template_source is NULL")
