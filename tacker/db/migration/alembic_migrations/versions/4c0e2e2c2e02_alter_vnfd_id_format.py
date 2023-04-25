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

"""alter_vnfd_id_format

Revision ID: 4c0e2e2c2e02
Revises: 34cfceb25a49
Create Date: 2023-04-28 08:05:13.246214

"""

# revision identifiers, used by Alembic.
revision = '4c0e2e2c2e02'
down_revision = '34cfceb25a49'

from alembic import op
import sqlalchemy as sa

# flake8: noqa: E402

def upgrade(active_plugins=None, options=None):
    bind = op.get_bind()
    engine = bind.engine

    fk_tables = ('servicetypes', 'vnf', 'vnfd_attribute')
    fk_prefixes = {"servicetypes":"servicetypes", "vnf":"devices",
                   "vnfd_attribute":"devicetemplateattributes"}
    for table in fk_tables:
        if engine.name == 'postgresql':
            alter_sql_drop_foreign_key = f"ALTER TABLE {table} \
                DROP CONSTRAINT {fk_prefixes[table]}_template_id_fkey;"
        else:
            alter_sql_drop_foreign_key = f"ALTER TABLE {table} \
                DROP FOREIGN KEY {table}_ibfk_1;"
        op.execute(alter_sql_drop_foreign_key)

    op.alter_column('vnfd', 'id', type_=sa.String(255),
                    existing_type=sa.String(36), nullable=False)

    vnfd_id_tables = ('servicetypes', 'vnf', 'vnfd_attribute',
                      'vnf_instances', 'vnf_package_vnfd')
    for table in vnfd_id_tables:
        op.alter_column(table, 'vnfd_id', type_=sa.String(255),
                        existing_type=sa.String(36), nullable=False)

    for table in fk_tables:
        if engine.name == 'postgresql':
            foreign_key = f"{fk_prefixes[table]}_template_id_fkey"
        else:
            foreign_key = f"{table}_ibfk_1"
        op.create_foreign_key(foreign_key, table, 'vnfd', ['vnfd_id'],
                              ['id'])
