# Copyright (C) 2023 FUJITSU
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

from tacker import context
from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.common import pm_threshold_utils
from tacker.sol_refactored import objects
from tacker.tests import base


class TestPmThresholdUtils(base.BaseTestCase):

    def setUp(self):
        super(TestPmThresholdUtils, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.context.api_version = api_version.APIVersion('2.1.0')

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_all')
    def test_get_pm_threshold_all(self, mock_pm):
        mock_pm.return_value = [objects.ThresholdV2(id='pm_threshold_1')]

        result = pm_threshold_utils.get_pm_threshold_all(self.context)
        self.assertEqual('pm_threshold_1', result[0].id)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_get_pm_threshold(self, mock_pm):
        mock_pm.return_value = objects.ThresholdV2(id='pm_threshold_1')

        result = pm_threshold_utils.get_pm_threshold(
            self.context, 'pm_threshold_1')
        self.assertEqual('pm_threshold_1', result.id)

    def test_get_pm_threshold_state(self):
        pm_threshold = objects.ThresholdV2(id='pm_threshold_1')

        result = pm_threshold_utils.get_pm_threshold_state(
            pm_threshold, 'subObjectInstanceId')
        self.assertIsNone(result)

    def test_get_pm_threshold_state_with_empty_metadata(self):
        pm_threshold = objects.ThresholdV2(
            id='pm_threshold_1',
            metadata={})

        result = pm_threshold_utils.get_pm_threshold_state(
            pm_threshold, 'subObjectInstanceId')
        self.assertIsNone(result)

    def test_get_pm_threshold_state_with_metadata(self):
        pm_threshold = objects.ThresholdV2(
            id='pm_threshold_1',
            metadata={
                'thresholdState': [{
                    'subObjectInstanceId': 'subObjectInstanceId',
                    'performanceValue': 200,
                    'metrics': 'metrics',
                    'crossingDirection': 'crossingDirection'
                }]
            }
        )

        result = pm_threshold_utils.get_pm_threshold_state(
            pm_threshold, 'subObjectInstanceId')
        self.assertEqual(200, result['performanceValue'])

    def test_pm_threshold_href(self):
        result = pm_threshold_utils.pm_threshold_href(
            'pm_threshold_1', 'endpoint')
        self.assertEqual('endpoint/vnfpm/v2/thresholds/pm_threshold_1', result)

    def test_pm_threshold_links(self):
        pm_threshold = objects.ThresholdV2(
            id='pm_threshold_1',
            objectInstanceId="id_1")
        result = pm_threshold_utils.make_pm_threshold_links(
            pm_threshold, 'endpoint')
        href = result.self.href
        self.assertEqual('endpoint/vnfpm/v2/thresholds/pm_threshold_1', href)

    @mock.patch.object(objects.base.TackerPersistentObject, 'update')
    @mock.patch.object(objects.base.TackerPersistentObject, 'create')
    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_update_threshold_state_data(
            self, mock_pms, mock_create, mock_update):
        mock_pms.return_value = objects.ThresholdV2(
            id='pm_threshold_1')
        mock_create.return_value = None
        mock_update.return_value = None
        pm_threshold_state_1 = {
            'thresholdId': 'pm_threshold_1',
            'subObjectInstanceId': 'sub_id_1',
            'performanceValue': '200.5',
            'metrics': 'VCpuUsageMeanVnf.VNF',
            'crossingDirection': 'UP'
        }
        update_threshold_state_data = {
            'subObjectInstanceId': pm_threshold_state_1[
                'subObjectInstanceId'],
            'performanceValue': pm_threshold_state_1['performanceValue'],
            'metrics': pm_threshold_state_1['metrics'],
            'crossingDirection': pm_threshold_state_1['crossingDirection']
        }
        pm_threshold_utils.update_threshold_state_data(
            self.context,
            pm_threshold_state_1['thresholdId'],
            update_threshold_state_data)
