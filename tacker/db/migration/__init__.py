# Copyright 2012 New Dream Network, LLC (DreamHost)
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

from alembic import op
import contextlib
import sqlalchemy as sa
from sqlalchemy.engine import reflection


def alter_enum(table, column, enum_type, nullable):
    bind = op.get_bind()
    engine = bind.engine
    if engine.name == 'postgresql':
        values = {'table': table,
                  'column': column,
                  'name': enum_type.name}
        op.execute("ALTER TYPE %(name)s RENAME TO old_%(name)s" % values)
        enum_type.create(bind, checkfirst=False)
        op.execute("ALTER TABLE %(table)s RENAME COLUMN %(column)s TO "
                   "old_%(column)s" % values)
        op.add_column(table, sa.Column(column, enum_type, nullable=nullable))
        op.execute("UPDATE %(table)s SET %(column)s = "
                   "old_%(column)s::text::%(name)s" % values)
        op.execute("ALTER TABLE %(table)s DROP COLUMN old_%(column)s" % values)
        op.execute("DROP TYPE old_%(name)s" % values)
    else:
        op.alter_column(table, column, type_=enum_type,
                        existing_nullable=nullable)


def create_foreign_key_constraint(table_name, fk_constraints):
    for fk in fk_constraints:
        op.create_foreign_key(
            constraint_name=fk['name'],
            source_table=table_name,
            referent_table=fk['referred_table'],
            local_cols=fk['constrained_columns'],
            remote_cols=fk['referred_columns'],
            ondelete=fk['options'].get('ondelete')
        )


def drop_foreign_key_constraint(table_name, fk_constraints):
    for fk in fk_constraints:
        op.drop_constraint(
            constraint_name=fk['name'],
            table_name=table_name,
            type_='foreignkey'
        )


@contextlib.contextmanager
def modify_foreign_keys_constraint(table_names):
    inspector = reflection.Inspector.from_engine(op.get_bind())
    try:
        for table in table_names:
            fk_constraints = inspector.get_foreign_keys(table)
            drop_foreign_key_constraint(table, fk_constraints)
        yield
    finally:
        for table in table_names:
            fk_constraints = inspector.get_foreign_keys(table)
            create_foreign_key_constraint(table, fk_constraints)


def modify_foreign_keys_constraint_with_col_change(
        table_name, old_local_col, new_local_col, existing_type,
        nullable=False):
    inspector = reflection.Inspector.from_engine(op.get_bind())
    fk_constraints = inspector.get_foreign_keys(table_name)
    for fk in fk_constraints:
        if old_local_col in fk['constrained_columns']:
            drop_foreign_key_constraint(table_name, [fk])
    op.alter_column(table_name, old_local_col,
                    new_column_name=new_local_col,
                    existing_type=existing_type,
                    nullable=nullable)
    fk_constraints = inspector.get_foreign_keys(table_name)
    for fk in fk_constraints:
        for i in range(len(fk['constrained_columns'])):
            if old_local_col == fk['constrained_columns'][i]:
                fk['constrained_columns'][i] = new_local_col
                create_foreign_key_constraint(table_name, [fk])
                break
