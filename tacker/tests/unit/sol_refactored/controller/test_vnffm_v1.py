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


import requests
from unittest import mock

from tacker import context
from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import fm_alarm_utils as alarm_utils
from tacker.sol_refactored.common import fm_subscription_utils\
    as fm_subsc_utils
from tacker.sol_refactored.common import subscription_utils as subsc_utils
from tacker.sol_refactored.controller import vnffm_v1
from tacker.sol_refactored import objects
from tacker.tests import base
from tacker.tests.unit.sol_refactored.common import fakes_for_fm
from tacker.tests import utils

SAMPLE_INST_ID = 'c61314d0-f583-4ab3-a457-46426bce02d3'
SAMPLE_ALARM_ID = '78a39661-60a8-4824-b989-88c1b0c3534a'
SAMPLE_SUBSC_ID = '78a39661-60a8-4824-b989-88c1b0c3534a'

CONF = config.CONF


class TestVnffmV1(base.BaseTestCase):

    def setUp(self):
        super(TestVnffmV1, self).setUp()
        objects.register_all()
        self.controller = vnffm_v1.VnfFmControllerV1()
        self.context = context.get_admin_context()
        self.context.api_version = api_version.APIVersion("1.3.0")
        self.request = mock.Mock()
        self.request.context = self.context

    def test_supported_api_versions(self):
        result = self.controller.supported_api_versions('show')

        self.assertEqual(['1.3.0'], result)

    def test_allowed_content_types(self):
        result = self.controller.allowed_content_types('show')
        self.assertEqual(['application/json', 'text/plain'], result)

        result = self.controller.allowed_content_types('update')
        self.assertEqual(['application/merge-patch+json', 'application/json',
                          'text/plain'], result)

    @mock.patch.object(alarm_utils, 'get_alarms_all')
    def test_index(self, mock_alarms):
        request = requests.Request()
        request.context = self.context
        request.GET = {'filter': f'(eq,managedObjectId,{SAMPLE_INST_ID})'}
        mock_alarms.return_value = [objects.AlarmV1.from_dict(
            fakes_for_fm.alarm_example), objects.AlarmV1(
            id='test-1', managedObjectId='inst-1')]

        result = self.controller.index(request)
        self.assertEqual(200, result.status)
        self.assertEqual([fakes_for_fm.alarm_example], result.body)
        self.assertEqual('1.3.0', result.headers['version'])

        # no filter
        request.GET = {}
        result = self.controller.index(request)
        self.assertEqual(200, result.status)
        self.assertEqual(2, len(result.body))
        self.assertEqual('1.3.0', result.headers['version'])

    @mock.patch.object(alarm_utils, 'get_alarm')
    def test_show(self, mock_alarm):
        request = requests.Request()
        request.context = self.context
        mock_alarm.return_value = objects.AlarmV1.from_dict(
            fakes_for_fm.alarm_example)
        result = self.controller.show(request, SAMPLE_ALARM_ID)
        self.assertEqual(200, result.status)
        self.assertEqual(fakes_for_fm.alarm_example, result.body)
        self.assertEqual('1.3.0', result.headers['version'])

    @mock.patch.object(objects.base.TackerPersistentObject, 'update')
    @mock.patch.object(alarm_utils, 'get_alarm')
    def test_update(self, mock_alarm, mock_update):
        mock_alarm.return_value = objects.AlarmV1.from_dict(
            fakes_for_fm.alarm_example)
        body = {"ackState": "ACKNOWLEDGED"}
        result = self.controller.update(
            request=self.request, id=SAMPLE_ALARM_ID, body=body)
        self.assertEqual(200, result.status)
        self.assertEqual('1.3.0', result.headers['version'])
        self.assertEqual(body, result.body)

        body = {"ackState": "UNACKNOWLEDGED"}
        result = self.controller.update(
            request=self.request, id=SAMPLE_ALARM_ID, body=body)
        self.assertEqual(body, result.body)

    @mock.patch.object(alarm_utils, 'get_alarm')
    def test_update_invalid_body(self, mock_alarm):
        mock_alarm.return_value = objects.AlarmV1.from_dict(
            fakes_for_fm.alarm_example)
        body = {"ackState": "UNACKNOWLEDGED"}
        self.assertRaises(sol_ex.AckStateInvalid, self.controller.update,
                          request=self.request, id=SAMPLE_ALARM_ID, body=body)

    @mock.patch.object(objects.base.TackerPersistentObject, 'create')
    @mock.patch.object(subsc_utils, 'test_notification')
    def test_subscription_create(self, mock_test, mock_create):
        sample_cert = utils.test_sample(
            "unit/sol_refactored/samples/sample_cert",
            "notification_client_cert.pem")
        CONF.v2_vnfm.notification_mtls_client_cert_file = sample_cert
        body_1 = {
            "callbackUri": "http://127.0.0.1:6789/notification",
            "authentication": {
                "authType": ["BASIC", "OAUTH2_CLIENT_CREDENTIALS",
                             "OAUTH2_CLIENT_CERT"],
                "paramsBasic": {
                    "userName": "test",
                    "password": "test"
                },
                "paramsOauth2ClientCredentials": {
                    "clientId": "test",
                    "clientPassword": "test",
                    "tokenEndpoint": "https://127.0.0.1/token"
                },
                "paramsOauth2ClientCert": {
                    "clientId": "test",
                    "certificateRef": {
                        "type": "x5t#S256",
                        "value": "8Shbulz8zlFdKG-iMCUz5CCv0A7q0k6X7wL3NcZpshM"
                    },
                    "tokenEndpoint": "https://127.0.0.1/token"
                }
            },
            "filter": fakes_for_fm.fm_subsc_example['filter']
        }
        result = self.controller.subscription_create(
            request=self.request, body=body_1)
        self.assertEqual(201, result.status)
        self.assertEqual(body_1['callbackUri'], result.body['callbackUri'])
        self.assertEqual(body_1['filter'], result.body['filter'])
        self.assertIsNone(result.body.get('authentication'))

        body_2 = {
            "callbackUri": "http://127.0.0.1:6789/notification",
            "authentication": {
                "authType": ["BASIC"],
                "paramsBasic": {
                    "userName": "test",
                    "password": "test"
                }
            },
            "filter": fakes_for_fm.fm_subsc_example['filter']
        }
        result = self.controller.subscription_create(
            request=self.request, body=body_2)
        self.assertEqual(201, result.status)
        self.assertEqual(body_2['callbackUri'], result.body['callbackUri'])
        self.assertEqual(body_2['filter'], result.body['filter'])
        self.assertIsNone(result.body.get('authentication'))

        body_3 = {
            "callbackUri": "http://127.0.0.1:6789/notification",
            "authentication": {
                "authType": ["OAUTH2_CLIENT_CREDENTIALS"],
                "paramsOauth2ClientCredentials": {
                    "clientId": "test",
                    "clientPassword": "test",
                    "tokenEndpoint": "https://127.0.0.1/token"
                }
            },
            "filter": fakes_for_fm.fm_subsc_example['filter']
        }
        result = self.controller.subscription_create(
            request=self.request, body=body_3)
        self.assertEqual(201, result.status)
        self.assertEqual(body_3['callbackUri'], result.body['callbackUri'])
        self.assertEqual(body_3['filter'], result.body['filter'])
        self.assertIsNone(result.body.get('authentication'))

        body_4 = {
            "callbackUri": "http://127.0.0.1:6789/notification",
            "authentication": {
                "authType": ["OAUTH2_CLIENT_CERT"],
                "paramsOauth2ClientCert": {
                    "clientId": "test",
                    "certificateRef": {
                        "type": "x5t#S256",
                        "value": "8Shbulz8zlFdKG-iMCUz5CCv0A7q0k6X7wL3NcZpshM"
                    },
                    "tokenEndpoint": "https://127.0.0.1/token"
                }
            },
            "filter": fakes_for_fm.fm_subsc_example['filter']
        }
        result = self.controller.subscription_create(
            request=self.request, body=body_4)
        self.assertEqual(201, result.status)
        self.assertEqual(body_4['callbackUri'], result.body['callbackUri'])
        self.assertEqual(body_4['filter'], result.body['filter'])
        self.assertIsNone(result.body.get('authentication'))

    def test_invalid_subscripion(self):
        body = {
            "callbackUri": "http://127.0.0.1:6789/notification",
            "authentication": {
                "authType": ["BASIC"]
            }
        }
        ex = self.assertRaises(sol_ex.InvalidSubscription,
            self.controller.subscription_create, request=self.request,
            body=body)
        self.assertEqual("paramsBasic must be specified.", ex.detail)

        body = {
            "callbackUri": "http://127.0.0.1:6789/notification",
            "authentication": {
                "authType": ["OAUTH2_CLIENT_CREDENTIALS"]
            }
        }
        ex = self.assertRaises(sol_ex.InvalidSubscription,
            self.controller.subscription_create, request=self.request,
            body=body)
        self.assertEqual("paramsOauth2ClientCredentials must be specified.",
                         ex.detail)

        body = {
            "callbackUri": "http://127.0.0.1:6789/notification",
            "authentication": {
                "authType": ["OAUTH2_CLIENT_CERT"]
            }
        }
        ex = self.assertRaises(sol_ex.InvalidSubscription,
            self.controller.subscription_create, request=self.request,
            body=body)
        self.assertEqual("paramsOauth2ClientCert must be specified.",
                         ex.detail)

    @mock.patch.object(fm_subsc_utils, 'get_subsc_all')
    def test_subscription_list(self, mock_subsc):
        request = requests.Request()
        request.context = self.context
        request.GET = {
            'filter': '(eq,callbackUri,/nfvo/notify/alarm)'}
        mock_subsc.return_value = [
            objects.FmSubscriptionV1.from_dict(fakes_for_fm.fm_subsc_example)]

        result = self.controller.subscription_list(request)
        self.assertEqual(200, result.status)

        # no filter
        request.GET = {}
        result = self.controller.subscription_list(request)
        self.assertEqual(200, result.status)

    @mock.patch.object(fm_subsc_utils, 'get_subsc')
    def test_subscription_show(self, mock_subsc):
        mock_subsc.return_value = objects.FmSubscriptionV1.from_dict(
            fakes_for_fm.fm_subsc_example)
        result = self.controller.subscription_show(
            request=self.request, id=SAMPLE_SUBSC_ID)
        self.assertEqual(200, result.status)

    @mock.patch.object(fm_subsc_utils, 'get_subsc')
    @mock.patch.object(objects.base.TackerPersistentObject, 'delete')
    def test_subscription_delete(self, mock_delete, mock_subsc):
        mock_subsc.return_value = objects.FmSubscriptionV1.from_dict(
            fakes_for_fm.fm_subsc_example)
        result = self.controller.subscription_delete(
            request=self.request, id=SAMPLE_SUBSC_ID)
        self.assertEqual(204, result.status)
