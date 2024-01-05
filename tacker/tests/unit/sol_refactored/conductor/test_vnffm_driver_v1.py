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

from unittest import mock

from oslo_utils import uuidutils

from tacker import context
from tacker.sol_refactored.common import fm_subscription_utils
from tacker.sol_refactored.common import subscription_utils as subsc_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.conductor import vnffm_driver_v1
from tacker.sol_refactored import objects
from tacker.tests import base
from tacker.tests.unit.sol_refactored.common import fakes_for_fm


class TestVnffmDriverV1(base.BaseTestCase):

    def setUp(self):
        super(TestVnffmDriverV1, self).setUp()
        objects.register_all()
        self.driver = vnffm_driver_v1.VnfFmDriverV1()
        self.context = context.get_admin_context()

    @mock.patch.object(subsc_utils, 'send_notification')
    @mock.patch.object(fm_subscription_utils, 'get_alarm_subscs')
    @mock.patch.object(objects.base.TackerPersistentObject, 'create')
    @mock.patch.object(objects.base.TackerPersistentObject, 'update')
    @mock.patch.object(inst_utils, 'get_inst')
    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_store_alarm_info(self, mock_alarm, mock_inst, mock_update,
                              mock_create, mock_subscs, mock_send_notif):
        alarm = objects.AlarmV1.from_dict(fakes_for_fm.alarm_example)
        mock_alarm.return_value = objects.AlarmV1.from_dict(
            fakes_for_fm.alarm_example)
        mock_inst.return_value = objects.VnfInstanceV2(
            # required fields
            id=fakes_for_fm.alarm_example['managedObjectId'],
            vnfdId=uuidutils.generate_uuid(),
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        mock_subscs.return_value = [objects.FmSubscriptionV1.from_dict(
            fakes_for_fm.fm_subsc_example)]
        self.driver.store_alarm_info(self.context, alarm)
        self.assertEqual(0, mock_create.call_count)
        self.assertEqual(1, mock_update.call_count)
        self.assertEqual(1, mock_send_notif.call_count)

        mock_alarm.return_value = None
        self.driver.store_alarm_info(self.context, alarm)
        self.assertEqual(1, mock_create.call_count)
        self.assertEqual(1, mock_update.call_count)
        self.assertEqual(2, mock_send_notif.call_count)
