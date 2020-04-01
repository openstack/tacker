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

"""set default value for deleted_at

Revision ID: f5c1c3b0f6b4
Revises: 31acbaeb8299
Create Date: 2017-06-23 03:03:12.200270

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = 'f5c1c3b0f6b4'
down_revision = '31acbaeb8299'

from alembic import op
from datetime import datetime


def upgrade(active_plugins=None, options=None):
    op.execute(("UPDATE vnfd set deleted_at='%s'"
       " WHERE deleted_at is NULL") % datetime.min)

    op.execute(("UPDATE vnf set deleted_at='%s'"
       " WHERE deleted_at is NULL") % datetime.min)

    op.execute(("UPDATE vims set deleted_at='%s'"
       " WHERE deleted_at is NULL") % datetime.min)

    op.execute(("UPDATE ns set deleted_at='%s'"
       " WHERE deleted_at is NULL") % datetime.min)

    op.execute(("UPDATE nsd set deleted_at='%s'"
       " WHERE deleted_at is NULL") % datetime.min)
