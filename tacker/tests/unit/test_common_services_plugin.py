# Copyright 2016 Brocade Communications System, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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

import mock

from oslo_utils import timeutils

from tacker import context
from tacker.db.common_services import common_services_db_plugin
from tacker.extensions import common_services
from tacker.plugins.common_services import common_services_plugin
from tacker.tests.unit.db import base as db_base


class TestCommonServicesPlugin(db_base.SqlTestCase):
    def setUp(self):
        super(TestCommonServicesPlugin, self).setUp()
        self.addCleanup(mock.patch.stopall)
        self.context = context.get_admin_context()
        self.event_db_plugin =\
            common_services_db_plugin.CommonServicesPluginDb()
        self.coreutil_plugin = common_services_plugin.CommonServicesPlugin()

    def _get_dummy_event_obj(self):
        return {
            'resource_id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            'resource_state': 'ACTIVE',
            'resource_type': 'VNF',
            'event_details': '',
            'event_type': 'scale_up',
            'timestamp': timeutils.parse_strtime('2016-07-20T05:43:52.765172')
        }

    def test_create_event(self):
        evt_obj = self._get_dummy_event_obj()
        result = self.event_db_plugin.create_event(self.context,
                                                   evt_obj['resource_id'],
                                                   evt_obj['resource_type'],
                                                   evt_obj['resource_state'],
                                                   evt_obj['event_type'],
                                                   evt_obj['timestamp'],
                                                   evt_obj['event_details'])
        self.assertIsNotNone(result)
        self.assertIn('id', result)
        self.assertIn('resource_id', result)
        self.assertIn('resource_state', result)
        self.assertIn('resource_type', result)
        self.assertIn('event_type', result)
        self.assertIn('event_details', result)
        self.assertIn('timestamp', result)

    def test_event_not_found(self):
        self.assertRaises(common_services.EventNotFoundException,
                          self.coreutil_plugin.get_event, self.context, '99')

    def test_InvalidModelInputExceptionNotThrown(self):
        evt_obj = self._get_dummy_event_obj()
        result = self.event_db_plugin.create_event(self.context,
                                                   evt_obj['resource_id'],
                                                   evt_obj['resource_type'],
                                                   evt_obj['resource_state'],
                                                   evt_obj['event_type'],
                                                   evt_obj['timestamp'],
                                                   evt_obj['event_details'])
        try:
            self.coreutil_plugin.get_event(self, context, str(result['id']))
        except common_services.InvalidModelException:
            self.assertTrue(False)
        except Exception:
            self.assertTrue(True)

    def test_get_event_by_id(self):
        evt_obj = self._get_dummy_event_obj()
        evt_created = self.event_db_plugin.create_event(
            self.context, evt_obj['resource_id'],
            evt_obj['resource_type'],
            evt_obj['resource_state'],
            evt_obj['event_type'],
            evt_obj['timestamp'],
            evt_obj['event_details'])
        self.assertIsNotNone(evt_created)
        evt_get = self.coreutil_plugin.get_event(self.context,
                                                 evt_created['id'])
        self.assertEqual(evt_created['resource_id'], evt_get['resource_id'])
        self.assertEqual(evt_created['resource_state'],
                         evt_get['resource_state'])
        self.assertEqual(evt_created['resource_type'],
                         evt_get['resource_type'])
        self.assertEqual(evt_created['event_type'], evt_get['event_type'])
        self.assertEqual(evt_created['event_details'],
                         evt_get['event_details'])
        self.assertEqual(evt_created['timestamp'], evt_get['timestamp'])

    def test_get_events(self):
        evt_obj = self._get_dummy_event_obj()
        self.event_db_plugin.create_event(self.context,
                                          evt_obj['resource_id'],
                                          evt_obj['resource_type'],
                                          evt_obj['resource_state'],
                                          evt_obj['event_type'],
                                          evt_obj['timestamp'],
                                          evt_obj['event_details'])
        result = self.coreutil_plugin.get_events(self.context)
        self.assertTrue(len(result))

    def test_get_events_filtered_invalid_id(self):
        evt_obj = self._get_dummy_event_obj()
        self.event_db_plugin.create_event(self.context,
                                          evt_obj['resource_id'],
                                          evt_obj['resource_type'],
                                          evt_obj['resource_state'],
                                          evt_obj['event_type'],
                                          evt_obj['timestamp'],
                                          evt_obj['event_details'])
        result = self.coreutil_plugin.get_events(self.context, {'id': 'xyz'})
        self.assertFalse(len(result))

    def test_get_events_filtered_valid_id(self):
        evt_obj = self._get_dummy_event_obj()
        self.event_db_plugin.create_event(self.context,
                                          evt_obj['resource_id'],
                                          evt_obj['resource_type'],
                                          evt_obj['resource_state'],
                                          evt_obj['event_type'],
                                          evt_obj['timestamp'],
                                          evt_obj['event_details'])
        result = self.coreutil_plugin.get_events(self.context, {'id': '1'})
        self.assertTrue(len(result))

    def test_get_events_valid_fields(self):
        evt_obj = self._get_dummy_event_obj()
        self.event_db_plugin.create_event(self.context,
                                          evt_obj['resource_id'],
                                          evt_obj['resource_type'],
                                          evt_obj['resource_state'],
                                          evt_obj['event_type'],
                                          evt_obj['timestamp'],
                                          evt_obj['event_details'])
        result = self.coreutil_plugin.get_events(self.context, {'id': '1'},
                                            ['id', 'event_type'])
        self.assertTrue(len(result))
        self.assertIn('id', result[0])
        self.assertNotIn('resource_id', result[0])
        self.assertNotIn('resource_state', result[0])
        self.assertNotIn('resource_type', result[0])
        self.assertIn('event_type', result[0])
        self.assertNotIn('event_details', result[0])
        self.assertNotIn('timestamp', result[0])
