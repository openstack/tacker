# Copyright (C) 2022 FUJITSU
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

from tacker.tests import base

from tacker import context
from tacker.sol_refactored.common import pm_job_utils
from tacker.sol_refactored.conductor.vnfpm_driver_v2 import VnfPmDriverV2
from tacker.sol_refactored.nfvo.nfvo_client import NfvoClient
from tacker.sol_refactored import objects


class TestVnfPmDriverV2(base.BaseTestCase):

    def setUp(self):
        super(TestVnfPmDriverV2, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()

    @mock.patch.object(NfvoClient, 'send_pm_job_notification')
    @mock.patch.object(pm_job_utils, 'update_report')
    @mock.patch.object(objects.base.TackerPersistentObject, 'update')
    @mock.patch.object(objects.base.TackerPersistentObject, 'create')
    def test_store_job_info(self, mock_create, mock_update, mock_update_report,
                            mock_send):
        mock_create.return_value = None
        mock_update.return_value = None
        pm_job = objects.PmJobV2(
            id='pm_job_1',
            objectTtype='VNF',
            authentication=objects.SubscriptionAuthentication(
                authType=["BASIC"],
                paramsBasic=objects.SubscriptionAuthentication_ParamsBasic(
                    userName='test',
                    password='test'
                ),
            ),
            callbackUri='http://127.0.0.1/callback'
        )
        report = {
            "id": "fake_id",
            "jobId": "fake_job_id",
            "entries": [{
                "objectType": "VNF",
                "objectInstanceId": "instance_id_1",
                "subObjectInstanceId": "subObjectInstanceId_1",
                'performanceValues': [{
                    'timeStamp': "2022-06-21T23:47:36.453Z",
                    'value': "99.0"
                }]
            }]
        }

        mock_update_report.return_value = pm_job
        mock_send.return_value = None
        VnfPmDriverV2().store_job_info(context=self.context,
                                       report=report)

    @mock.patch.object(objects.base.TackerPersistentObject, 'create')
    def test_store_report(self, mock_create):
        mock_create.return_value = None
        report = {
            "id": "fake_id",
            "jobId": "fake_job_id",
            "entries": [{
                "objectType": "VNF",
                "objectInstanceId": "instance_id_1",
                "subObjectInstanceId": "subObjectInstanceId_1",
                'performanceValues': [{
                    'timeStamp': "2022-06-21T23:47:36.453Z",
                    'value': "99.0"
                }]
            }]
        }
        result = VnfPmDriverV2()._store_report(context=self.context,
                                               report=report)
        self.assertEqual('fake_job_id', result.jobId)

    @mock.patch.object(objects.base.TackerPersistentObject, 'update')
    @mock.patch.object(pm_job_utils, 'update_report')
    def test_update_job_reports(self, mock_update_report, mock_update):
        pm_job = objects.PmJobV2(
            id='pm_job_1',
            objectTtype='VNF',
            authentication=objects.SubscriptionAuthentication(
                authType=["BASIC"],
                paramsBasic=objects.SubscriptionAuthentication_ParamsBasic(
                    userName='test',
                    password='test'
                ),
            ),
            callbackUri='http://127.0.0.1/callback'
        )
        mock_update_report.return_value = pm_job
        mock_update.return_value = None
        result = VnfPmDriverV2()._update_job_reports(
            context=self.context, job_id='pm_job_1', report='report',
            timestamp='timestamp')
        self.assertEqual('pm_job_1', result.id)
