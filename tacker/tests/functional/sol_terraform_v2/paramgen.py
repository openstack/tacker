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

from oslo_utils import uuidutils


def create_req_by_vnfd_id(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "vnfInstanceName": "test_terraform_instantiate",
        "vnfInstanceDescription": "test_terraform_instantiate",
        "metadata": {"dummy-key": "dummy-val"}
    }


def instantiate_req():
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    auth_url = "http://localhost:4566"

    vim = {
        "vimId": uuidutils.generate_uuid(),
        "vimType": "TERRAFORM.V1",
        "interfaceInfo": {
            "providerType": "aws",
            "providerVersion": "4.0"
        },
        "accessInfo": {
            "region": "ap-northeast-1",
            "access_key": "mock_access_key",
            "secret_key": "mock_secret_key",
            "skip_credentials_validation": "true",
            "skip_metadata_api_check": "true",
            "skip_requesting_account_id": "true",
            "endpoints": {
                "ec2": auth_url
            }
        }
    }

    return {
        "flavourId": "simple",
        "vimConnectionInfo": {
            "vim1": vim
        },
        "additionalParams": {"tf_dir_path": "Files/terraform"}
    }


def terminate_req():
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    return {
        "terminationType": "GRACEFUL",
        "gracefulTerminationTimeout": 5,
        "additionalParams": {"dummy-key": "dummy-val"}
    }


def change_vnfpkg_req(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "additionalParams": {
            "upgrade_type": "RollingUpdate",
            "tf_dir_path": "Files/terraform",
            "vdu_params": [{
                "vdu_id": "VDU1"
            }]
        }
    }


def change_vnfpkg_fail_req(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "additionalParams": {
            "upgrade_type": "RollingUpdate",
            "tf_dir_path": "Files/terraform",
            "tf_var_path": "Files/terraform/test-tf-fail.tfvars",
            "vdu_params": [{
                "vdu_id": "VDU1"
            }]
        }
    }
