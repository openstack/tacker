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

"""unique_constraint_name

Revision ID: 0ae5b1ce3024
Revises: 507122918800
Create Date: 2016-09-15 16:27:08.736673

"""

# revision identifiers, used by Alembic.
revision = '0ae5b1ce3024'
down_revision = '507122918800'

from alembic import op
import sqlalchemy as sa


def _migrate_duplicate_names(table):

    meta = sa.MetaData(bind=op.get_bind())
    t = sa.Table(table, meta, autoload=True)

    session = sa.orm.Session(bind=op.get_bind())
    with session.begin(subtransactions=True):
        dup_names = session.query(t.c.name).group_by(
            t.c.name).having(sa.func.count() > 1).all()
        if dup_names:
            for name in dup_names:
                duplicate_obj_query = session.query(t).filter(t.c.name == name[
                    0]).all()
                for dup_obj in duplicate_obj_query:
                    name = dup_obj.name[:242] if dup_obj.name > 242 else \
                        dup_obj.name
                    new_name = '{0}-{1}'.format(name, dup_obj.id[-12:])
                    session.execute(t.update().where(
                        t.c.id == dup_obj.id).values(name=new_name))
    session.commit()


def upgrade(active_plugins=None, options=None):

    _migrate_duplicate_names('vnf')
    _migrate_duplicate_names('vnfd')
    _migrate_duplicate_names('vims')
