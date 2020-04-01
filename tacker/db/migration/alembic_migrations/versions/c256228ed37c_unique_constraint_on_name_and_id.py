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

"""unique constraint on name and id

Revision ID: c256228ed37c
Revises: 8f7145914cb0
Create Date: 2017-03-01 12:28:58.467900

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = 'c256228ed37c'
down_revision = 'ef14f8026327'

from alembic import op


def _add_unique_constraint(table):
    op.create_unique_constraint(
        constraint_name='uniq_%s0tenant_id0name' % table,
        table_name=table,
        columns=['tenant_id', 'name'])


def upgrade(active_plugins=None, options=None):
    for table in ['vnf', 'vnfd', 'vims', 'ns', 'nsd']:
        _add_unique_constraint(table)
