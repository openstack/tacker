# Copyright 2016 Brocade Communications System, Inc.
# All Rights Reserved.
#
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

import sqlalchemy as sa
from sqlalchemy.orm import exc as orm_exc

from oslo_log import log as logging

from tacker.common import log
from tacker.db import db_base
from tacker.db import model_base
from tacker.db import types
from tacker.extensions import common_services
from tacker import manager


LOG = logging.getLogger(__name__)

EVENT_ATTRIBUTES = ('id', 'resource_id', 'resource_type', 'resource_state',
                    'timestamp', 'event_type', 'event_details')


class Event(model_base.BASE):
    id = sa.Column(sa.Integer, primary_key=True, nullable=False,
                   autoincrement=True)
    resource_id = sa.Column(types.Uuid, nullable=False)
    resource_state = sa.Column(sa.String(64), nullable=False)
    resource_type = sa.Column(sa.String(64), nullable=False)
    timestamp = sa.Column(sa.DateTime, nullable=False)
    event_type = sa.Column(sa.String(64), nullable=False)
    event_details = sa.Column(types.Json)


class CommonServicesPluginDb(common_services.CommonServicesPluginBase,
                             db_base.CommonDbMixin):

    def __init__(self):
        super(CommonServicesPluginDb, self).__init__()

    @property
    def _core_plugin(self):
        return manager.TackerManager.get_plugin()

    def _make_event_dict(self, event_db, fields=None):
        res = dict((key, event_db[key]) for key in EVENT_ATTRIBUTES)
        return self._fields(res, fields)

    def _fields(self, resource, fields):
        if fields:
            return dict(((key, item) for key, item in resource.items()
                         if key in fields))
        return resource

    @log.log
    def create_event(self, context, res_id, res_type, res_state, evt_type,
                     tstamp, details=""):
        try:
            with context.session.begin(subtransactions=True):
                event_db = Event(
                    resource_id=res_id,
                    resource_type=res_type,
                    resource_state=res_state,
                    event_details=details,
                    event_type=evt_type,
                    timestamp=tstamp)
                context.session.add(event_db)
        except Exception as e:
            LOG.exception(_("create event error: %s"), str(e))
            raise common_services.EventCreationFailureException(
                error_str=str(e))
        return self._make_event_dict(event_db)

    @log.log
    def get_event(self, context, event_id, fields=None):
        try:
            events_db = self._get_by_id(context, Event, event_id)
        except orm_exc.NoResultFound:
            raise common_services.EventNotFoundException(evt_id=event_id)
        return self._make_event_dict(events_db, fields)

    @log.log
    def get_events(self, context, filters=None, fields=None, sorts=None,
                   limit=None, marker_obj=None, page_reverse=False):
        return self._get_collection(context, Event, self._make_event_dict,
                                    filters, fields, sorts, limit,
                                    marker_obj, page_reverse)
