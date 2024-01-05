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

from oslo_log import log as logging

from tacker import context
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import fm_subscription_utils as subsc_utils
from tacker.sol_refactored import objects
from tacker.tests import base
from tacker.tests.unit.sol_refactored.common import fakes_for_fm


LOG = logging.getLogger(__name__)


class TestFmSubscriptionUtils(base.BaseTestCase):
    def setUp(self):
        super(TestFmSubscriptionUtils, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_get_subsc(self, mock_subsc):
        mock_subsc.return_value = objects.FmSubscriptionV1.from_dict(
            fakes_for_fm.fm_subsc_example)

        result = subsc_utils.get_subsc(
            context, fakes_for_fm.fm_subsc_example['id'])
        self.assertEqual(fakes_for_fm.fm_subsc_example['id'], result.id)

        mock_subsc.return_value = None
        self.assertRaises(
            sol_ex.FmSubscriptionNotFound,
            subsc_utils.get_subsc, context, 'subsc-1')

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_all')
    def test_get_subsc_all(self, mock_subsc):
        mock_subsc.return_value = [objects.FmSubscriptionV1.from_dict(
            fakes_for_fm.fm_subsc_example)]

        result = subsc_utils.get_subsc_all(context)
        self.assertEqual(fakes_for_fm.fm_subsc_example['id'], result[0].id)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_all')
    def test_get_matched_subscs(self, mock_subscs):
        inst = objects.VnfInstanceV2(id='test-instance', vnfProvider='company')
        notif_type = 'AlarmClearedNotification'
        new_alarm_example = copy.deepcopy(fakes_for_fm.alarm_example)
        new_alarm_example['perceivedSeverity'] = 'CRITICAL'
        new_alarm_example['eventType'] = 'COMMUNICATIONS_ALARM'
        alarm = objects.AlarmV1.from_dict(new_alarm_example)

        subscs_no_fileter = objects.FmSubscriptionV1(id='subsc-1')

        products_vnfproducts_no_exist = objects._VnfProductsFromProviders(
            vnfProvider='company')
        inst_filter_match_products = objects.VnfInstanceSubscriptionFilter(
            vnfProductsFromProviders=[products_vnfproducts_no_exist])
        subscs_filter_match = objects.FmSubscriptionV1(
            id='subsc-2',
            filter=objects.FmNotificationsFilterV1(
                vnfInstanceSubscriptionFilter=inst_filter_match_products))

        products_mismatch = objects._VnfProductsFromProviders(
            vnfProvider='test')
        inst_filter_mismatch_products = objects.VnfInstanceSubscriptionFilter(
            vnfProductsFromProviders=[products_mismatch])
        subscs_filter_mismatch = objects.FmSubscriptionV1(
            id='subsc-3',
            filter=objects.FmNotificationsFilterV1(
                vnfInstanceSubscriptionFilter=inst_filter_mismatch_products))

        subscs_noti_type_match = objects.FmSubscriptionV1(
            id='subsc-4', filter=objects.FmNotificationsFilterV1(
                notificationTypes=['AlarmClearedNotification']))
        subscs_noti_type_mismatch = objects.FmSubscriptionV1(
            id='subsc-5', filter=objects.FmNotificationsFilterV1(
                notificationTypes=['AlarmNotification']))

        subscs_faulty_res_type_match = objects.FmSubscriptionV1(
            id='subsc-6', filter=objects.FmNotificationsFilterV1(
                faultyResourceTypes=['COMPUTE']))
        subscs_faulty_res_type_mismatch = objects.FmSubscriptionV1(
            id='subsc-7', filter=objects.FmNotificationsFilterV1(
                faultyResourceTypes=['STORAGE']))

        subscs_per_sev_match = objects.FmSubscriptionV1(
            id='subsc-8', filter=objects.FmNotificationsFilterV1(
                perceivedSeverities=['CRITICAL']))
        subscs_per_sev_mismatch = objects.FmSubscriptionV1(
            id='subsc-9', filter=objects.FmNotificationsFilterV1(
                perceivedSeverities=['MAJOR']))

        subscs_event_type_match = objects.FmSubscriptionV1(
            id='subsc-10', filter=objects.FmNotificationsFilterV1(
                eventTypes=['COMMUNICATIONS_ALARM']))
        subscs_event_type_mismatch = objects.FmSubscriptionV1(
            id='subsc-11', filter=objects.FmNotificationsFilterV1(
                eventTypes=['PROCESSING_ERROR_ALARM']))

        subscs_probable_cause_match = objects.FmSubscriptionV1(
            id='subsc-12', filter=objects.FmNotificationsFilterV1(
                probableCauses=['The server cannot be connected.']))
        subscs_probable_cause_mismatch = objects.FmSubscriptionV1(
            id='subsc-13', filter=objects.FmNotificationsFilterV1(
                probableCauses=['The server is invalid.']))

        mock_subscs.return_value = [
            subscs_no_fileter, subscs_filter_match, subscs_filter_mismatch,
            subscs_noti_type_match, subscs_noti_type_mismatch,
            subscs_faulty_res_type_match, subscs_faulty_res_type_mismatch,
            subscs_per_sev_match, subscs_per_sev_mismatch,
            subscs_event_type_match, subscs_event_type_mismatch,
            subscs_probable_cause_match, subscs_probable_cause_mismatch]

        result = subsc_utils.get_matched_subscs(
            context, inst, notif_type, alarm)

        expected_ids = ['subsc-1', 'subsc-2', 'subsc-4', 'subsc-6',
                        'subsc-8', 'subsc-10', 'subsc-12']

        result_ids = [sub.id for sub in result]
        self.assertEqual(expected_ids, result_ids)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_all')
    def test_get_alarm_subscs(self, mock_subscs):
        inst = objects.VnfInstanceV2(
            id='dummy-vnfInstanceId-1', vnfdId='dummy-vnfdId-1',
            vnfProvider='dummy-vnfProvider-1',
            vnfProductName='dummy-vnfProductName-1-1',
            vnfSoftwareVersion='1.0', vnfdVersion='1.0',
            vnfInstanceName='dummy-vnfInstanceName-1')
        alarm = objects.AlarmV1.from_dict(fakes_for_fm.alarm_example)
        mock_subscs.return_value = [objects.FmSubscriptionV1.from_dict(
            fakes_for_fm.fm_subsc_example)]
        result = subsc_utils.get_alarm_subscs(context, alarm, inst)
        self.assertEqual(fakes_for_fm.fm_subsc_example['id'], result[0].id)

        alarm_clear = copy.deepcopy(fakes_for_fm.alarm_example)
        del alarm_clear['alarmClearedTime']
        alarm = objects.AlarmV1.from_dict(alarm_clear)
        result = subsc_utils.get_alarm_subscs(context, alarm, inst)

        self.assertEqual(fakes_for_fm.fm_subsc_example['id'], result[0].id)
