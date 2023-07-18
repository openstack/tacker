# Copyright (C) 2023 NEC, Corp.
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

from tacker.tests import uuidsentinel


def get_vnf_instance_data_without_vnf_desc():
    return {
        "vnf_software_version": "1.0",
        "vnf_product_name": "Sample VNF",
        "vnf_instance_name": 'Sample VNF Instance',
        "vnf_instance_description": None,
        "instantiation_state": "NOT_INSTANTIATED",
        "vnf_provider": "test vnf provider",
        "vnfd_id": uuidsentinel.vnfd_id,
        "vnfd_version": "1.0",
        "tenant_id": uuidsentinel.tenant_id,
        "vnf_pkg_id": uuidsentinel.vnf_pkg_id,
        "vnf_metadata": {"key": "value"},
    }


def get_vnf_instance_data_with_vnf_desc():
    return {
        "vnf_software_version": "1.0",
        "vnf_product_name": "Sample VNF",
        "vnf_instance_name": 'Sample VNF Instance',
        "vnf_instance_description": 'Sample Description',
        "instantiation_state": "NOT_INSTANTIATED",
        "vnf_provider": "test vnf provider",
        "vnfd_id": uuidsentinel.vnfd_id,
        "vnfd_version": "1.0",
        "tenant_id": uuidsentinel.tenant_id,
        "vnf_pkg_id": uuidsentinel.vnf_pkg_id,
        "vnf_metadata": {"key": "value"},
    }
