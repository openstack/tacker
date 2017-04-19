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

"""add unique constraint on deleted_at

Revision ID: e7993093baf1
Revises: c256228ed37c
Create Date: 2017-04-19 10:57:22.157326

"""

# revision identifiers, used by Alembic.
revision = 'e7993093baf1'
down_revision = 'c256228ed37c'

from alembic import op


def _drop_unique_constraint(table):
    op.drop_constraint(
        constraint_name='uniq_%s0tenant_id0name' % table,
        table_name=table, type_='unique')


def _add_unique_constraint(table):
    op.create_unique_constraint(
        constraint_name='uniq_%s0tenant_id0name0deleted_at' % table,
        table_name=table,
        columns=['tenant_id', 'name', 'deleted_at'])


def upgrade(active_plugins=None, options=None):
    for table in ['vnf', 'vnfd', 'vims', 'ns', 'nsd']:
        _drop_unique_constraint(table)
        _add_unique_constraint(table)
