# Copyright 2023 OpenStack Foundation
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

"""remove status from Vim

Revision ID: de6bfa5bea46
Revises: de8d835ae776
Create Date: 2023-01-09 11:08:53.597828

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = 'de6bfa5bea46'
down_revision = 'de8d835ae776'

from alembic import op


def upgrade(active_plugins=None, options=None):
    op.drop_column('vims', 'status')
