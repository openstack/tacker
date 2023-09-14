# Copyright (C) 2023 Fujitsu
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

from oslo_config import cfg
from oslo_serialization import jsonutils

from tacker.common import crypt_utils
from tacker.sol_refactored import objects
from tacker.tests import base as tests_base

_string_data = 'string'
_encrypted_data = 'encrypted'
_decrypted_data = 'decrypted'


_criteria = jsonutils.dumps({
    'performanceMetric': None,
    'performanceMetricGroup': None,
    'collectionPeriod': 100,
    'reportingPeriod': 100,
    'reportingBoundary': None,
})
_report = jsonutils.dumps({
    "href": "test_link",
    "readyTime": "2022-08-30T08:02:58Z",
    "expiryTime": None,
    "fileSize": None
})
_reports = f'[{_report}]'
_link = jsonutils.dumps({
    "self": {
        "href": "test_link"
    },
    'objects': []
})


class TestPmJobObject(tests_base.BaseTestCase):

    @mock.patch.object(crypt_utils, 'decrypt')
    def test_from_db_obj(self, mock_decrypt):
        cfg.CONF.set_override('use_credential_encryption', True)
        mock_decrypt.return_value = _decrypted_data

        auth = jsonutils.dumps({
            "paramsBasic": {
                "userName": "test_user",
                "password": _encrypted_data
            },
            "paramsOauth2ClientCredentials": {
                "cliendId": "test_client",
                "clientPassword": _encrypted_data
            }
        })
        metadata = {
            "monitoring": {
                "targetsInfo": [{
                    "authInfo": {
                        "ssh_password": _encrypted_data
                    }
                }]
            }
        }
        pm_job = {
            "id": "test_id",
            "objectType": "Vnf",
            "objectInstanceIds": '["test_inst_id"]',
            "subObjectInstanceIds": None,
            "criteria": _criteria,
            "callbackUri": "testUri",
            "reports": _reports,
            "_links": _link,
            "authentication": auth,
            "metadata__": metadata
        }
        obj = objects.PmJobV2.from_db_obj(pm_job)
        dict_of_auth = {}
        for key, item in obj.authentication.items():
            dict_of_auth[key] = item.to_dict()
        self.assertEqual(
            dict_of_auth["paramsBasic"]["password"],
            _decrypted_data)
        self.assertEqual(
            dict_of_auth["paramsOauth2ClientCredentials"]["clientPassword"],
            _decrypted_data)
        for target_info in obj["metadata"]["monitoring"]["targetsInfo"]:
            self.assertEqual(target_info["authInfo"]["ssh_password"],
                             _decrypted_data)

    def test_from_db_obj_no_encrypt(self):
        cfg.CONF.set_override('use_credential_encryption', False)
        auth = jsonutils.dumps({
            "paramsBasic": {
                "userName": "test_user",
                "password": _string_data
            },
            "paramsOauth2ClientCredentials": {
                "cliendId": "test_client",
                "clientPassword": _string_data
            }
        })
        metadata = {
            "monitoring": {
                "targetsInfo": [{
                    "authInfo": {
                        "ssh_password": _string_data
                    }
                }]
            }
        }
        pm_job = {
            "id": "test_id",
            "objectType": "Vnf",
            "objectInstanceIds": '["test_inst_id"]',
            "subObjectInstanceIds": None,
            "criteria": _criteria,
            "callbackUri": "testUri",
            "reports": _reports,
            "_links": _link,
            "authentication": auth,
            "metadata__": metadata
        }
        obj = objects.PmJobV2.from_db_obj(pm_job)
        dict_of_auth = {}
        for key, item in obj.authentication.items():
            dict_of_auth[key] = item.to_dict()
        self.assertEqual(
            dict_of_auth["paramsBasic"]["password"],
            _string_data)
        self.assertEqual(
            dict_of_auth["paramsOauth2ClientCredentials"]["clientPassword"],
            _string_data)
        for target_info in obj["metadata"]["monitoring"]["targetsInfo"]:
            self.assertEqual(target_info["authInfo"]["ssh_password"],
                             _string_data)

    @mock.patch.object(crypt_utils, 'encrypt')
    def test_to_db_obj(self, mock_encrypt):
        cfg.CONF.set_override('use_credential_encryption', True)
        mock_encrypt.return_value = _encrypted_data

        params_basic = objects.SubscriptionAuthentication_ParamsBasic(
            userName="test_user",
            password=_string_data
        )
        params_oauth2 = objects.SubscriptionAuthentication_ParamsOauth2(
            clientId="test_client",
            clientPassword=_string_data
        )
        auth = objects.SubscriptionAuthentication(
            authType=['BASIC', 'OAUTH2_CLIENT_CREDENTIALS'],
            paramsBasic=params_basic,
            paramsOauth2ClientCredentials=params_oauth2
        )
        metadata = {
            "monitoring": {
                "targetsInfo": [{
                    "authInfo": {
                        "ssh_password": _string_data
                    }
                }]
            }
        }
        pm_job = objects.PmJobV2(
            callbackUri="testUri",
            authentication=auth,
            metadata=metadata
        )
        obj = pm_job.to_db_obj()
        dict_auth = jsonutils.loads(obj["authentication"])
        self.assertEqual(dict_auth["paramsBasic"]["password"], _encrypted_data)
        self.assertEqual(dict_auth["paramsOauth2ClientCredentials"]
                         ["clientPassword"], _encrypted_data)
        for target_info in obj["metadata__"]["monitoring"]["targetsInfo"]:
            self.assertEqual(target_info["authInfo"]["ssh_password"],
                             _encrypted_data)

    def test_to_db_obj_no_encrypt(self):
        cfg.CONF.set_override('use_credential_encryption', False)

        params_basic = objects.SubscriptionAuthentication_ParamsBasic(
            userName="test_user",
            password=_string_data
        )
        params_oauth2 = objects.SubscriptionAuthentication_ParamsOauth2(
            clientId="test_client",
            clientPassword=_string_data
        )
        auth = objects.SubscriptionAuthentication(
            authType=['BASIC', 'OAUTH2_CLIENT_CREDENTIALS'],
            paramsBasic=params_basic,
            paramsOauth2ClientCredentials=params_oauth2
        )
        metadata = {
            "monitoring": {
                "targetsInfo": [{
                    "authInfo": {
                        "ssh_password": _string_data
                    }
                }]
            }
        }
        pm_job = objects.PmJobV2(
            callbackUri="testUri",
            authentication=auth,
            metadata=metadata
        )
        obj = pm_job.to_db_obj()
        dict_auth = jsonutils.loads(obj["authentication"])
        self.assertEqual(dict_auth["paramsBasic"]["password"], _string_data)
        self.assertEqual(dict_auth["paramsOauth2ClientCredentials"]
                         ["clientPassword"], _string_data)
        for target_info in obj["metadata__"]["monitoring"]["targetsInfo"]:
            self.assertEqual(target_info["authInfo"]["ssh_password"],
                             _string_data)
