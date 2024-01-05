# Copyright (C) 2022 Fujitsu
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
import copy
from unittest import mock

from tacker import context
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import fm_alarm_utils as alarm_utils
from tacker.sol_refactored import objects
from tacker.tests import base
from tacker.tests.unit.sol_refactored.common import fakes_for_fm


class TestFmAlarmUtils(base.BaseTestCase):
    def setUp(self):
        super(TestFmAlarmUtils, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_get_alarm(self, mock_alarm):
        mock_alarm.return_value = objects.AlarmV1.from_dict(
            fakes_for_fm.alarm_example)

        result = alarm_utils.get_alarm(
            context, fakes_for_fm.alarm_example['id'])
        self.assertEqual(fakes_for_fm.alarm_example['id'], result.id)

        mock_alarm.return_value = None
        self.assertRaises(
            sol_ex.AlarmNotFound,
            alarm_utils.get_alarm, context, fakes_for_fm.alarm_example['id'])

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_all')
    def test_get_alarms_all(self, mock_alarms):
        mock_alarms.return_value = [objects.AlarmV1.from_dict(
            fakes_for_fm.alarm_example)]

        result = alarm_utils.get_alarms_all(context)
        self.assertEqual(fakes_for_fm.alarm_example['id'], result[0].id)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_filter')
    def test_get_not_cleared_alarms(self, mock_alarms):
        mock_alarms.return_value = [objects.AlarmV1.from_dict(
            fakes_for_fm.alarm_example)]

        result = alarm_utils.get_not_cleared_alarms(
            context, fakes_for_fm.alarm_example['managedObjectId'])
        self.assertEqual(fakes_for_fm.alarm_example['id'], result[0].id)

    def test_make_alarm_links(self):
        alarm = objects.AlarmV1.from_dict(fakes_for_fm.alarm_example)
        endpoint = 'http://127.0.0.1:9890'

        expected_result = objects.AlarmV1_Links()
        expected_result.self = objects.Link(
            href=f'{endpoint}/vnffm/v1/alarms/{alarm.id}')
        expected_result.objectInstance = objects.Link(
            href=f'{endpoint}/vnflcm/v2/vnf_instances/{alarm.managedObjectId}')

        result = alarm_utils.make_alarm_links(alarm, endpoint)
        self.assertEqual(expected_result.self.href, result.self.href)
        self.assertEqual(expected_result.objectInstance.href,
                         result.objectInstance.href)

    def test_make_alarm_notif_data(self):
        subsc = objects.FmSubscriptionV1.from_dict(
            fakes_for_fm.fm_subsc_example)
        alarm = objects.AlarmV1.from_dict(fakes_for_fm.alarm_example)
        endpoint = 'http://127.0.0.1:9890'

        # execute alarm_cleared
        alarm_cleared_result = alarm_utils.make_alarm_notif_data(
            subsc, alarm, endpoint)

        # execute alarm
        alarm_clear = copy.deepcopy(fakes_for_fm.alarm_example)
        del alarm_clear['alarmClearedTime']
        alarm = objects.AlarmV1.from_dict(alarm_clear)
        alarm_result = alarm_utils.make_alarm_notif_data(
            subsc, alarm, endpoint)

        self.assertEqual('AlarmClearedNotificationV1',
                         type(alarm_cleared_result).__name__)
        self.assertEqual('AlarmClearedNotification',
                         alarm_cleared_result.notificationType)
        self.assertEqual('AlarmNotificationV1', type(alarm_result).__name__)
        self.assertEqual('AlarmNotification',
                         alarm_result.notificationType)
        self.assertEqual(alarm_clear, alarm_result.alarm.to_dict())
