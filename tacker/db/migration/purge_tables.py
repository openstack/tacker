# Copyright 2016 OpenStack Foundation.
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

import datetime
import sqlalchemy
from sqlalchemy import and_
from sqlalchemy import create_engine, pool
from sqlalchemy import inspect

from oslo_utils import timeutils

from tacker.common import exceptions


GRANULARITY = {'days': 86400, 'hours': 3600, 'minutes': 60, 'seconds': 1}


def _generate_associated_tables_map(inspector):
    assoc_map = {}
    table_names = inspector.get_table_names()
    for t in table_names:
        fk_list = inspector.get_foreign_keys(t)
        for fk in fk_list:
            k = str(fk['referred_table'])
            v = str(fk['constrained_columns'][0])
            if k not in assoc_map.keys():
                assoc_map[k] = {str(t): v}
            else:
                assoc_map[k][str(t)] = v
    assoc_keys = assoc_map.keys()
    for k, v in assoc_map.items():
        for k1 in v.keys():
            if k1 in assoc_keys:
                del assoc_map[k][k1]
    return assoc_map


def _purge_resource_tables(t, meta, engine, time_line, assoc_map):
    table_load = sqlalchemy.Table(t, meta, autoload=True)
    table_del_query = table_load.delete().where(
        table_load.c.deleted_at <= time_line)
    if t in assoc_map.keys():
        select_id_query = sqlalchemy.select([table_load.c.id]).where(
            table_load.c.deleted_at <= time_line)
        resource_ids = [i[0] for i in list(engine.execute(select_id_query))]
        if resource_ids:
            for key, val in assoc_map[t].items():
                assoc_table_load = sqlalchemy.Table(key, meta, autoload=True)
                assoc_table_del_query = assoc_table_load.delete().where(
                    assoc_table_load.c[val].in_(resource_ids))
                engine.execute(assoc_table_del_query)
    engine.execute(table_del_query)


def _purge_events_table(meta, engine, time_line):
    tname = "events"
    event_table_load = sqlalchemy.Table(tname, meta, autoload=True)
    event_select_query = sqlalchemy.select(
        [event_table_load.c.resource_id]
    ).where(
        and_(event_table_load.c.event_type == 'DELETE',
             event_table_load.c.timestamp <= time_line
             )
    )
    resource_ids = [i[0] for i in list(engine.execute(event_select_query))]
    if resource_ids:
        event_delete_query = event_table_load.delete().where(
            event_table_load.c.resource_id.in_(resource_ids)
        )
        engine.execute(event_delete_query)


def purge_deleted(tacker_config, table_name, age, granularity='days'):
    try:
        age = int(age)
    except ValueError:
        msg = _("'%s' - age should be an integer") % age
        raise exceptions.InvalidInput(error_message=msg)
    if age < 0:
        msg = _("'%s' - age should be a positive integer") % age
        raise exceptions.InvalidInput(error_message=msg)

    if granularity not in GRANULARITY.keys():
        msg = _("'%s' granularity should be days, hours, minutes, "
                "or seconds") % granularity
        raise exceptions.InvalidInput(error_message=msg)

    age *= GRANULARITY[granularity]

    time_line = timeutils.utcnow() - datetime.timedelta(seconds=age)
    engine = get_engine(tacker_config)
    meta = sqlalchemy.MetaData()
    meta.bind = engine
    inspector = inspect(engine)
    assoc_map = _generate_associated_tables_map(inspector)

    if table_name == 'events':
        _purge_events_table(meta, engine, time_line)
    elif table_name == 'all':
        _purge_events_table(meta, engine, time_line)
        for t in ['vnf', 'vnfd', 'vims']:
            _purge_resource_tables(t, meta, engine, time_line, assoc_map)
    else:
        _purge_resource_tables(table_name, meta, engine, time_line, assoc_map)


def get_engine(tacker_config):
    return create_engine(tacker_config.database.connection,
                         poolclass=pool.NullPool)
