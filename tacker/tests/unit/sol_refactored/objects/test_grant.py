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
from tacker.tests import base as tests_base

_string_data = 'string'
_encrypted_data = 'encrypted'
_decrypted_data = 'decrypted'

_inst_cnf_req_example = {
    "flavourId": "simple",
    "additionalParams": {
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
    }
}
_link = jsonutils.dumps({
    "self": {
        "href": "test_link"
    },
    'objects': []
})


class TestGrantObject(tests_base.BaseTestCase):

    @mock.patch.object(crypt_utils, 'decrypt')
    def test_from_db_obj(self, mock_decrypt):
        cfg.CONF.set_override('use_credential_encryption', True)
        mock_decrypt.return_value = _decrypted_data

        vim_infos = jsonutils.dumps({
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
        })
        dict_grant = {
            "id": "test_id",
            "vnfInstanceId": "test_inst_id",
            "vnfLcmOpOccId": "test_op_id",
            "vimConnectionInfo": vim_infos,
            "zones": None,
            "zoneGroups": None,
            "addResources": None,
            "tempResources": None,
            "removeResources": None,
            "updateResources": None,
            "vimAssets": None,
            "extVirtualLinks": None,
            "extManagedVirtualLinks": None,
            "additionalParams": None,
            "_links": _link
        }
        obj = objects.GrantV1.from_db_obj(dict_grant)
        dict_of_objects = {}
        for key, item in obj.vimConnectionInfo.items():
            dict_of_objects[key] = item.to_dict()
        self.assertEqual(
            dict_of_objects["vim1"]["accessInfo"]["password"],
            _decrypted_data)
        self.assertEqual(
            dict_of_objects["vim1"]["accessInfo"]["bearer_token"],
            _decrypted_data)
        self.assertEqual(
            dict_of_objects["vim1"]["accessInfo"]["client_secret"],
            _decrypted_data)

    def test_from_db_obj_no_encrypt(self):
        cfg.CONF.set_override('use_credential_encryption', False)

        vim_infos = jsonutils.dumps({
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
        })
        dict_grant = {
            "id": "test_id",
            "vnfInstanceId": "test_inst_id",
            "vnfLcmOpOccId": "test_op_id",
            "vimConnectionInfo": vim_infos,
            "zones": None,
            "zoneGroups": None,
            "addResources": None,
            "tempResources": None,
            "removeResources": None,
            "updateResources": None,
            "vimAssets": None,
            "extVirtualLinks": None,
            "extManagedVirtualLinks": None,
            "additionalParams": None,
            "_links": _link
        }
        obj = objects.GrantV1.from_db_obj(dict_grant)
        dict_of_objects = {}
        for key, item in obj.vimConnectionInfo.items():
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
    def test_to_db_obj(self, mock_encrypt):
        cfg.CONF.set_override('use_credential_encryption', True)
        mock_encrypt.return_value = _encrypted_data

        req_inst = objects.InstantiateVnfRequest.from_dict(
            _inst_cnf_req_example)
        grant = objects.GrantV1(
            vimConnectionInfo=req_inst.vimConnectionInfo,
        )
        obj = grant.to_db_obj()
        o_dict = jsonutils.loads(obj['vimConnectionInfo'])
        self.assertEqual(
            o_dict["vim1"]["accessInfo"]["password"],
            _encrypted_data)
        self.assertEqual(
            o_dict["vim1"]["accessInfo"]["bearer_token"],
            _encrypted_data)
        self.assertEqual(
            o_dict["vim1"]["accessInfo"]["client_secret"],
            _encrypted_data)

    def test_to_db_obj_no_encrypt(self):
        cfg.CONF.set_override('use_credential_encryption', False)

        req_inst = objects.InstantiateVnfRequest.from_dict(
            _inst_cnf_req_example)
        grant = objects.GrantV1(
            vimConnectionInfo=req_inst.vimConnectionInfo,
        )
        obj = grant.to_db_obj()
        o_dict = jsonutils.loads(obj['vimConnectionInfo'])
        self.assertEqual(
            o_dict["vim1"]["accessInfo"]["password"],
            _string_data)
        self.assertEqual(
            o_dict["vim1"]["accessInfo"]["bearer_token"],
            _string_data)
        self.assertEqual(
            o_dict["vim1"]["accessInfo"]["client_secret"],
            _string_data)
