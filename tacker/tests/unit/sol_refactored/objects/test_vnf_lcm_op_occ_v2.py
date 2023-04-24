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
from oslo_utils import uuidutils

from tacker.common import crypt_utils
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields
from tacker.tests import base as tests_base


_string_data = 'string'
_encrypted_data = 'encrypted'
_decrypted_data = 'decrypted'

_change_pkg_req_example = {
    "additionalParams": {
        "vdu_params": [{
            "old_vnfc_param": {
                "password": _string_data,
                "authentication": {
                    "paramsBasic": {
                        "password": _string_data
                    },
                    "paramsOauth2ClientCredentials": {
                        "clientPassword": _string_data
                    }
                }
            },
            "new_vnfc_param": {
                "password": _string_data,
                "authentication": {
                    "paramsBasic": {
                        "password": _string_data
                    },
                    "paramsOauth2ClientCredentials": {
                        "clientPassword": _string_data
                    }
                }
            }
        }],
        "lcm-kubernetes-def-files": [
            "Files/kubernetes/deployment.yaml",
            "Files/kubernetes/namespace.yaml",
            "Files/kubernetes/pod.yaml",
        ],
        "namespace": "curry"
    },
    "vimConnectionInfo": {
        "vim1": {
            "vimType": "ETSINFV.KUBERNETES.V_1",
            "vimId": uuidutils.generate_uuid(),
            "interfaceInfo": {"endpoint": "https://127.0.0.1:6443"},
            "accessInfo": {
                "password": _string_data,
                "bearer_token": _string_data,
                "client_secret": _string_data,
                "region": "RegionOne"
            }
        }
    },
}
_link = jsonutils.dumps({
    "self": {
        "href": "test_link"
    },
    'objects': []
})


class TestVnfLcmOpOccObject(tests_base.BaseTestCase):

    @mock.patch.object(crypt_utils, 'decrypt')
    def test_from_db_obj(self, mock_decrypt):
        cfg.CONF.set_override('use_credential_encryption', True)
        mock_decrypt.return_value = _decrypted_data

        vim_infos_example = {
            "vim1": {
                "vimType": "ETSINFV.KUBERNETES.V_1",
                "interfaceInfo": {
                    "endpoint": "http://localhost/identity/v3"
                },
                "accessInfo": {
                    "password": _encrypted_data,
                    "bearer_token": _encrypted_data,
                    "client_secret": _encrypted_data,
                    "username": "nfv_user"
                }
            }
        }
        changed_info = jsonutils.dumps(
            {"vimConnectionInfo": vim_infos_example})
        additional_params_example = {
            'vdu_params': [{
                'old_vnfc_param': {
                    'password': _encrypted_data,
                    'authentication': {
                        'paramsBasic': {
                            'password': _encrypted_data
                        },
                        'paramsOauth2ClientCredentials': {
                            'clientPassword': _encrypted_data
                        }
                    }
                },
                'new_vnfc_param': {
                    'password': _encrypted_data,
                    'authentication': {
                        'paramsBasic': {
                            'password': _encrypted_data
                        },
                        'paramsOauth2ClientCredentials': {
                            'clientPassword': _encrypted_data
                        }
                    }
                }
            }]
        }
        dict_lcmocc = {
            "id": "test_id",
            "operationState": "STARTING",
            "stateEnteredTime": "2022-08-30T08:02:58Z",
            "startTime": "2022-08-30T08:02:58Z",
            "vnfInstanceId": "test_inst_id",
            "grantId": None,
            "operation": fields.LcmOperationType.CHANGE_VNFPKG,
            "isAutomaticInvocation": False,
            "operationParams": {
                "vimConnectionInfo": vim_infos_example,
                "additionalParams": additional_params_example
            },
            "isCancelPending": False,
            "cancelMode": None,
            "error": None,
            "resourceChanges": None,
            "changedInfo": changed_info,
            "changedExtConnectivity": None,
            "modificationsTriggeredByVnfPkgChange": None,
            "vnfSnapshotInfoId": None,
            "_links": _link
        }
        obj = objects.VnfLcmOpOccV2.from_db_obj(dict_lcmocc)
        dict_of_vim_infos = {}
        for key, item in obj.operationParams.vimConnectionInfo.items():
            dict_of_vim_infos[key] = item.to_dict()
        self.assertEqual(
            dict_of_vim_infos["vim1"]["accessInfo"]["password"],
            _decrypted_data)
        self.assertEqual(
            dict_of_vim_infos["vim1"]["accessInfo"]["bearer_token"],
            _decrypted_data)
        self.assertEqual(
            dict_of_vim_infos["vim1"]["accessInfo"]["client_secret"],
            _decrypted_data)
        self.assertEqual(
            obj.operationParams.additionalParams["vdu_params"][0]
            ["old_vnfc_param"]["password"], _decrypted_data)
        self.assertEqual(
            obj.operationParams.additionalParams["vdu_params"][0]
            ["old_vnfc_param"]["authentication"]["paramsBasic"]
            ["password"], _decrypted_data)
        self.assertEqual(
            obj.operationParams.additionalParams["vdu_params"][0]
            ["old_vnfc_param"]["authentication"]
            ["paramsOauth2ClientCredentials"]["clientPassword"],
            _decrypted_data)
        self.assertEqual(
            obj.operationParams.additionalParams["vdu_params"][0]
            ["new_vnfc_param"]["password"], _decrypted_data)
        self.assertEqual(
            obj.operationParams.additionalParams["vdu_params"][0]
            ["new_vnfc_param"]["authentication"]["paramsBasic"]
            ["password"], _decrypted_data)
        self.assertEqual(
            obj.operationParams.additionalParams["vdu_params"][0]
            ["new_vnfc_param"]["authentication"]
            ["paramsOauth2ClientCredentials"]["clientPassword"],
            _decrypted_data)
        dict_of_vim_infos = {}
        for key, item in obj.changedInfo.vimConnectionInfo.items():
            dict_of_vim_infos[key] = item.to_dict()
        self.assertEqual(
            dict_of_vim_infos["vim1"]["accessInfo"]["password"],
            _decrypted_data)
        self.assertEqual(
            dict_of_vim_infos["vim1"]["accessInfo"]["bearer_token"],
            _decrypted_data)
        self.assertEqual(
            dict_of_vim_infos["vim1"]["accessInfo"]["client_secret"],
            _decrypted_data)

    def test_from_db_obj_no_encrypt(self):
        cfg.CONF.set_override('use_credential_encryption', False)

        vim_infos_example = {
            "vim1": {
                "vimType": "ETSINFV.KUBERNETES.V_1",
                "interfaceInfo": {
                    "endpoint": "http://localhost/identity/v3"
                },
                "accessInfo": {
                    "password": _string_data,
                    "bearer_token": _string_data,
                    "client_secret": _string_data,
                    "username": "nfv_user"
                }
            }
        }
        changed_info = jsonutils.dumps(
            {"vimConnectionInfo": vim_infos_example})
        additional_params_example = {
            'vdu_params': {
                'old_vnfc_param': {
                    'password': _string_data,
                    'authentication': {
                        'paramsBasic': {
                            'password': _string_data
                        },
                        'paramsOauth2ClientCredentials': {
                            'clientPassword': _string_data
                        }
                    }
                },
                'new_vnfc_param': {
                    'password': _string_data,
                    'authentication': {
                        'paramsBasic': {
                            'password': _string_data
                        },
                        'paramsOauth2ClientCredentials': {
                            'clientPassword': _string_data
                        }
                    }
                }
            }
        }
        dict_lcmocc = {
            "id": "test_id",
            "operationState": "STARTING",
            "stateEnteredTime": "2022-08-30T08:02:58Z",
            "startTime": "2022-08-30T08:02:58Z",
            "vnfInstanceId": "test_inst_id",
            "grantId": None,
            "operation": fields.LcmOperationType.CHANGE_VNFPKG,
            "isAutomaticInvocation": False,
            "operationParams": {
                "vimConnectionInfo": vim_infos_example,
                "additionalParams": additional_params_example
            },
            "isCancelPending": False,
            "cancelMode": None,
            "error": None,
            "resourceChanges": None,
            "changedInfo": changed_info,
            "changedExtConnectivity": None,
            "modificationsTriggeredByVnfPkgChange": None,
            "vnfSnapshotInfoId": None,
            "_links": _link
        }
        obj = objects.VnfLcmOpOccV2.from_db_obj(dict_lcmocc)
        dict_of_objects = {}
        for key, item in obj.operationParams.vimConnectionInfo.items():
            dict_of_objects[key] = item.to_dict()
        self.assertEqual(
            dict_of_objects["vim1"]["accessInfo"]["password"],
            _string_data)
        self.assertEqual(
            dict_of_objects["vim1"]["accessInfo"]["bearer_token"],
            _string_data)
        self.assertEqual(
            dict_of_objects["vim1"]["accessInfo"]["client_secret"],
            _string_data)

    @mock.patch.object(crypt_utils, 'encrypt')
    def test_to_db_obj_terminal(self, mock_encrypt):
        cfg.CONF.set_override('use_credential_encryption', True)

        mock_encrypt.return_value = _encrypted_data
        req = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_pkg_req_example)
        vim_info = objects.VimConnectionInfo(
            accessInfo={
                "password": _string_data,
                "bearer_token": _string_data,
                "client_secret": _string_data,
                "username": "nfv_user"
            }
        )
        chg_info = objects.VnfInfoModificationsV2(
            vimConnectionInfo={
                "vim1": vim_info
            }
        )
        lcmocc = objects.VnfLcmOpOccV2(
            # only set used members in the method
            operation=fields.LcmOperationType.CHANGE_VNFPKG,
            operationState=fields.LcmOperationStateType.COMPLETED,
            operationParams=req,
            changedInfo=chg_info
        )
        obj = lcmocc.to_db_obj()
        vim_infos = obj["operationParams"]['vimConnectionInfo']
        acc_info = vim_infos["vim1"]["accessInfo"]
        self.assertIsNone(acc_info.get("password", None))
        self.assertIsNone(acc_info.get("bearer_token", None))
        self.assertIsNone(acc_info.get("client_secret", None))
        add_param = obj["operationParams"]["additionalParams"]
        old_vnfc_param = add_param["vdu_params"][0]["old_vnfc_param"]
        new_vnfc_param = add_param["vdu_params"][0]["new_vnfc_param"]
        self.assertIsNone(old_vnfc_param.get("password", None))
        self.assertIsNone(old_vnfc_param["authentication"]["paramsBasic"].get(
            "password", None))
        self.assertIsNone(old_vnfc_param["authentication"]
                          ["paramsOauth2ClientCredentials"].get(
                          "clientPassword", None))
        self.assertIsNone(new_vnfc_param.get("password", None))
        self.assertIsNone(new_vnfc_param["authentication"]["paramsBasic"].get(
            "password", None))
        self.assertIsNone(new_vnfc_param["authentication"]
                          ["paramsOauth2ClientCredentials"].get(
                          "clientPassword", None))
        dict_chg_info = jsonutils.loads(obj["changedInfo"])
        chg_acc_info = dict_chg_info["vimConnectionInfo"]["vim1"]["accessInfo"]
        self.assertIsNone(chg_acc_info.get("password", None))
        self.assertIsNone(chg_acc_info.get("bearer_token", None))
        self.assertIsNone(chg_acc_info.get("client_secret", None))

    @mock.patch.object(crypt_utils, 'encrypt')
    def test_to_db_obj_not_terminal(self, mock_encrypt):
        cfg.CONF.set_override('use_credential_encryption', True)
        mock_encrypt.return_value = _encrypted_data

        req = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_pkg_req_example)
        vim_info = objects.VimConnectionInfo(
            accessInfo={
                "password": _string_data,
                "bearer_token": _string_data,
                "client_secret": _string_data,
                "username": "nfv_user"
            }
        )
        chg_info = objects.VnfInfoModificationsV2(
            vimConnectionInfo={
                "vim1": vim_info
            }
        )
        lcmocc = objects.VnfLcmOpOccV2(
            # only set used members in the method
            operation=fields.LcmOperationType.CHANGE_VNFPKG,
            operationState=fields.LcmOperationStateType.FAILED_TEMP,
            operationParams=req,
            changedInfo=chg_info)
        obj = lcmocc.to_db_obj()
        vim_infos = obj["operationParams"]['vimConnectionInfo']
        acc_info = vim_infos["vim1"]["accessInfo"]
        self.assertEqual(acc_info["password"], _encrypted_data)
        self.assertEqual(acc_info["bearer_token"], _encrypted_data)
        self.assertEqual(acc_info["client_secret"], _encrypted_data)
        add_param = obj["operationParams"]["additionalParams"]
        old_vnfc_param = add_param["vdu_params"][0]["old_vnfc_param"]
        new_vnfc_param = add_param["vdu_params"][0]["new_vnfc_param"]
        self.assertEqual(old_vnfc_param["password"], _encrypted_data)
        self.assertEqual(old_vnfc_param["authentication"]["paramsBasic"]
                         ["password"], _encrypted_data)
        self.assertEqual(old_vnfc_param["authentication"]
                         ["paramsOauth2ClientCredentials"]["clientPassword"],
                         _encrypted_data)
        self.assertEqual(new_vnfc_param["password"], _encrypted_data)
        self.assertEqual(new_vnfc_param["authentication"]["paramsBasic"]
                         ["password"], _encrypted_data)
        self.assertEqual(new_vnfc_param["authentication"]
                         ["paramsOauth2ClientCredentials"]["clientPassword"],
                         _encrypted_data)
        dict_chg_info = jsonutils.loads(obj["changedInfo"])
        chg_acc_info = dict_chg_info["vimConnectionInfo"]["vim1"]["accessInfo"]
        self.assertEqual(chg_acc_info["password"], _encrypted_data)
        self.assertEqual(chg_acc_info["bearer_token"], _encrypted_data)
        self.assertEqual(chg_acc_info["client_secret"], _encrypted_data)

    def test_to_db_obj_no_encrypt(self):
        cfg.CONF.set_override('use_credential_encryption', False)

        req = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_pkg_req_example)
        vim_info = objects.VimConnectionInfo(
            accessInfo={
                "password": _string_data,
                "bearer_token": _string_data,
                "client_secret": _string_data,
                "username": "nfv_user"
            }
        )
        chg_info = objects.VnfInfoModificationsV2(
            vimConnectionInfo={
                "vim1": vim_info
            }
        )
        lcmocc = objects.VnfLcmOpOccV2(
            # only set used members in the method
            operation=fields.LcmOperationType.CHANGE_VNFPKG,
            operationState=fields.LcmOperationStateType.COMPLETED,
            operationParams=req,
            changedInfo=chg_info)

        obj = lcmocc.to_db_obj()
        vim_infos = obj["operationParams"]['vimConnectionInfo']
        acc_info = vim_infos["vim1"]["accessInfo"]
        self.assertEqual(acc_info["password"], _string_data)
        self.assertEqual(acc_info["bearer_token"], _string_data)
        self.assertEqual(acc_info["client_secret"], _string_data)
        add_param = obj["operationParams"]["additionalParams"]
        old_vnfc_param = add_param["vdu_params"][0]["old_vnfc_param"]
        new_vnfc_param = add_param["vdu_params"][0]["new_vnfc_param"]
        self.assertEqual(old_vnfc_param["password"], _string_data)
        self.assertEqual(old_vnfc_param["authentication"]["paramsBasic"]
                         ["password"], _string_data)
        self.assertEqual(old_vnfc_param["authentication"]
                         ["paramsOauth2ClientCredentials"]["clientPassword"],
                         _string_data)
        self.assertEqual(new_vnfc_param["password"], _string_data)
        self.assertEqual(new_vnfc_param["authentication"]["paramsBasic"]
                         ["password"], _string_data)
        self.assertEqual(new_vnfc_param["authentication"]
                         ["paramsOauth2ClientCredentials"]["clientPassword"],
                         _string_data)
        dict_chg_info = jsonutils.loads(obj["changedInfo"])
        chg_acc_info = dict_chg_info["vimConnectionInfo"]["vim1"]["accessInfo"]
        self.assertEqual(chg_acc_info["password"], _string_data)
        self.assertEqual(chg_acc_info["bearer_token"], _string_data)
        self.assertEqual(chg_acc_info["client_secret"], _string_data)
