# Copyright (C) 2023 Nippon Telegraph and Telephone Corporation
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

import json
import os
import tempfile

from oslo_utils import uuidutils
from unittest import mock

from tacker import context
from tacker.sol_refactored.common import vnfd_utils
from tacker.sol_refactored.infra_drivers.terraform import terraform
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields
from tacker.tests import base

SAMPLE_VNFD_ID = "65b62a2a-c207-423f-9b01-f399c9ab5629"
SAMPLE_FLAVOUR_ID = "simple"

_vim_connection_info_example = {
    "vimId": "terraform_provider_aws_v4_tokyo",
    "vimType": "ETSINFV.TERRAFORM.V_1",
    "interfaceInfo": {
        "providerType": "aws",
        "providerVersion": "4.0"
    },
    "accessInfo": {
        "region": "ap-northeast-1",
        "access_key": "example_access_key",
        "secret_key": "example_secret_key"
    }
}

_instantiate_req_example = {
    # instantiateVnfRequest example
    "flavourId": SAMPLE_FLAVOUR_ID,
    "vimConnectionInfo": {
        "vim1": _vim_connection_info_example
    },
    "additionalParams": {
        "tf_dir_path": "Files/terraform",
        "tf_var_path": "Files/terraform/variables.tf"
    }
}


class TestTerraform(base.BaseTestCase):
    def setUp(self):
        super(TestTerraform, self).setUp()
        objects.register_all()
        self.driver = terraform.Terraform()
        self.context = context.get_admin_context()

        cur_dir = os.path.dirname(__file__)
        sample_dir = os.path.join(cur_dir, "../..", "samples")

        self.vnfd_2 = vnfd_utils.Vnfd(SAMPLE_VNFD_ID)
        self.vnfd_2.init_from_csar_dir(os.path.join(sample_dir, "sample2"))

    @mock.patch.object(terraform.Terraform, '_get_tf_vnfpkg')
    @mock.patch.object(terraform.Terraform, '_generate_provider_tf')
    @mock.patch.object(terraform.Terraform, '_make_instantiated_vnf_info')
    @mock.patch.object(terraform.Terraform, '_instantiate')
    def test_instantiate(self, mock_instantiate,
                         mock_make_instantiated_vnf_info,
                         mock_generate_provider_tf,
                         mock_tf_files):
        '''Verifies instantiate is called once'''

        req = objects.InstantiateVnfRequest.from_dict(_instantiate_req_example)

        inst = objects.VnfInstanceV2(
            # Required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED',
            vimConnectionInfo=req['vimConnectionInfo']
        )

        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE,
            vnfdId=SAMPLE_VNFD_ID
        )

        grant = objects.GrantV1()

        # Set the desired return value for _get_tf_vnfpkg
        mock_tf_files.return_value = f"/var/lib/tacker/terraform/{inst.id}"

        # Execute
        self.driver.instantiate(req, inst, grant_req, grant, self.vnfd_2)

        # TODO(yasufum) Test _instantiate mock subprocess
        # Verify _instantiate is called once
        mock_instantiate.assert_called_once_with(
            req.vimConnectionInfo['vim1'],
            f"/var/lib/tacker/terraform/{inst.id}",
            req.additionalParams.get('tf_var_path'))

    def test_make_instantiated_vnf_info(self):
        '''Verifies instantiated vnf info is correct'''

        req = objects.InstantiateVnfRequest.from_dict(_instantiate_req_example)

        inst = objects.VnfInstanceV2(
            # Required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED',
            vimConnectionInfo=req['vimConnectionInfo']
        )

        grant_req = objects.GrantRequestV1(
            operation='INSTANTIATE'
        )

        grant = objects.GrantV1()

        # Expected results
        _expected_inst_info = {
            "flavourId": "simple",
            "vnfState": "STARTED",
            "vnfcResourceInfo": [
                {
                    "id": "vdu1",
                    "vduId": "VDU1",
                    "computeResource": {
                        "resourceId": "vdu1",
                        "vimLevelResourceType": "aws_instance"
                    },
                    "metadata": {}
                },
                {
                    "id": "vdu2",
                    "vduId": "VDU2",
                    "computeResource": {
                        "resourceId": "vdu2",
                        "vimLevelResourceType": "aws_instance"
                    },
                    "metadata": {}
                }
            ],
            "vnfcInfo": [
                {
                    "id": "VDU1-vdu1",
                    "vduId": "VDU1",
                    "vnfcResourceInfoId": "vdu1",
                    "vnfcState": "STARTED"
                },
                {
                    "id": "VDU2-vdu2",
                    "vduId": "VDU2",
                    "vnfcResourceInfoId": "vdu2",
                    "vnfcState": "STARTED"
                }
            ]
        }

        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create the tfstate content
            provider = "provider[\"registry.terraform.io/hashicorp/aws\"]"
            tfstate_content = {
                "version": 4,
                "terraform_version": "1.4.4",
                "serial": 4,
                "lineage": "5745b992-04a2-5811-2e02-19d64f6f4b44",
                "outputs": {},
                "resources": [
                    {
                        "mode": "managed",
                        "type": "aws_instance",
                        "name": "vdu1",
                        "provider": provider
                    },
                    {
                        "mode": "managed",
                        "type": "aws_instance",
                        "name": "vdu2",
                        "provider": provider
                    },
                    {
                        "mode": "managed",
                        "type": "aws_subnet",
                        "name": "hoge-subnet01",
                        "provider": provider
                    }
                ]
            }

            # Write the tfstate content to a temporary file
            tfstate_file_path = f"{temp_dir}/terraform.tfstate"
            with open(tfstate_file_path, "w") as tfstate_file:
                json.dump(tfstate_content, tfstate_file)

            # Execute the test with the temporary tfstate_file
            self.driver._make_instantiated_vnf_info(req, inst,
                                                    grant_req, grant,
                                                    self.vnfd_2, temp_dir,
                                                    req.additionalParams.get(
                                                        'tf_var_path')
                                                    )

            # check
            result = inst.to_dict()["instantiatedVnfInfo"]
            expected = _expected_inst_info

            # vnfcResourceInfo is sorted by creation_time (reverse)
            self.assertIn("vnfcResourceInfo", result)
            self.assertEqual(expected["vnfcResourceInfo"],
                result["vnfcResourceInfo"])

            # order of vnfcInfo is same as vnfcResourceInfo
            self.assertIn("vnfcInfo", result)
            self.assertEqual(expected["vnfcInfo"], result["vnfcInfo"])
