# Copyright (C) 2020 NTT DATA
# All Rights Reserved.
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

"""Add unique constraints on vnfd_id,deleted in vnf_package_vnfd

Revision ID: 975e28392888
Revises: abbef484b34c
Create Date: 2019-12-10 02:40:12.966027

"""

# revision identifiers, used by Alembic.
revision = '975e28392888'
down_revision = 'abbef484b34c'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402
from sqlalchemy.engine import reflection  # noqa: E402


def _migrate_duplicate_vnf_package_vnfd_id(table):

    meta = sa.MetaData(bind=op.get_bind())
    t = sa.Table(table, meta, autoload=True)

    session = sa.orm.Session(bind=op.get_bind())
    with session.begin(subtransactions=True):
        dup_vnfd_ids = session.query(t.c.vnfd_id).group_by(
            t.c.vnfd_id).having(sa.func.count() > 1).all()
        if dup_vnfd_ids:
            for vnfd_id in dup_vnfd_ids:
                duplicate_obj_query = session.query(t).filter(
                    t.c.vnfd_id == vnfd_id[0]).all()
                for dup_obj in duplicate_obj_query:
                    if dup_obj.deleted == '1':
                        session.execute(t.update().where(
                            t.c.id == dup_obj.id).values(deleted=dup_obj.id))
    session.commit()

    op.create_unique_constraint(
        constraint_name='uniq_%s0vnfd_id0deleted' % table,
        table_name=table,
        columns=['vnfd_id', 'deleted'])


def upgrade(active_plugins=None, options=None):
    check_constraints = (reflection.Inspector.from_engine(op.get_bind())
                         .get_check_constraints('vnf_package_vnfd'))
    for constraint in check_constraints:
        if '`deleted`' in constraint['sqltext']:
            op.drop_constraint(
                constraint_name=constraint['name'],
                table_name='vnf_package_vnfd',
                type_="check"
            )
            break

    op.alter_column('vnf_package_vnfd',
                    'deleted',
                    type_=sa.String(36), default="0")
    _migrate_duplicate_vnf_package_vnfd_id('vnf_package_vnfd')
