# Copyright (c) 2020 NTT DATA
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from tacker import context
from tacker import objects
from tacker.objects import fields
from tacker.tests.unit import base
from tacker.tests import uuidsentinel


def get_instantiated_info_dict_for_ext_links_and_flavour_id():
    return {"instantiated_vnf_info": {
        "additional_params": {'key1': 'value1'},
        "vnfc_resource_info": [{
            "vdu_id": "VDU1",
            "vnfc_cp_info": [{
                "cp_protocol_info": [{
                    "ip_over_ethernet": {
                        "mac_address": "fa:16:3e:0d:6f:71"},
                    "layer_protocol": "IP_OVER_ETHERNET"}],
                "vnf_ext_cp_id": None,
                "cpd_id": "CP1",
                "vnf_link_port_id": "a41417d8-5cba-4256-aa4a-c68b79bb2dc2",
                "id": "350ab5d7-7cf0-4d24-aa2f-ec7e51149d56"}, {
                "cp_protocol_info": [{
                    "layer_protocol": "IP_OVER_ETHERNET"}],
                "vnf_ext_cp_id": "413f4e46-21cf-41b1-be0f-de8d23f76cfe",
                "cpd_id": "CP2",
                "vnf_link_port_id": "b5f67448-87ee-4250-ad8b-514bc693f6c4",
                "id": "2cab54a3-8ac5-4338-b586-b12e4ff1a89f"}, {
                "vnf_link_port_id": "124f1923-9de1-4729-8d4e-bc0613066dc4",
                "id": "b3341e7b-20bb-4ae5-8be9-b00cf79a9395",
                "vnf_ext_cp_id": None,
                "cpd_id": "CP3"}],
            "compute_resource": {
                "vim_level_resource_type": "OS::Nova::Server",
                "resource_id": "c83ac219-376a-4016-b8b2-50c3707f71c4"},
            "id": "0688be82-05a6-4b00-b869-d4719baf4f42",
            "storage_resource_ids": [],
            "metadata": {}}],
        "ext_virtual_link_info": [{
            "resource_handle": {
                "vim_level_resource_type": None,
                "resource_id": "7ec01a11-e584-404a-88bd-39a56b63e29c"},
            "id": "net0"}, {
            "resource_handle": {
                "vim_level_resource_type": None,
                "resource_id": "dc67ee99-e963-44e2-a152-f0fb492eae76"},
            "id": "external_network",
            "ext_link_ports": [{
                "cp_instance_id": "f47a9e33-b31a-4290-828a-c7569c52bd0e",
                "resource_handle": {
                    "vim_level_resource_type": "LINKPORT",
                    "resource_id": "67f7e772-0d31-4087-bf4c-2576fadcbdb7"},
                "id": "413f4e46-21cf-41b1-be0f-de8d23f76cfe"}]}],
        "vnf_virtual_link_resource_info": [{
            "vnf_link_ports": [{
                "cp_instance_id": "b3341e7b-20bb-4ae5-8be9-b00cf79a9395",
                "resource_handle": {
                    "vim_level_resource_type": "OS::Neutron::Port",
                    "resource_id": "87b567a0-783a-4c06-b0d8-cdafd40c51e3"},
                "id": "124f1923-9de1-4729-8d4e-bc0613066dc4"}],
            "network_resource": {
                "vim_level_resource_type": "OS::Neutron::Net",
                "resource_id": "413f4e46-21cf-41b1-be0f-de8d23f76cfd"},
            "vnf_virtual_link_desc_id": "VL3",
            "id": "84ffa547-1164-4e60-863d-c7dac770f824"}, {
            "vnf_link_ports": [{
                "cp_instance_id": "2cab54a3-8ac5-4338-b586-b12e4ff1a89f",
                "resource_handle": {
                    "vim_level_resource_type": "OS::Neutron::Port",
                    "resource_id": "413f4e46-21cf-41b1-be0f-de8d23f76cfe"},
                "id": "b5f67448-87ee-4250-ad8b-514bc693f6c4"}],
            "network_resource": {
                "vim_level_resource_type": "OS::Neutron::Net",
                "resource_id": "dc67ee99-e963-44e2-a152-f0fb492eae76"},
            "vnf_virtual_link_desc_id": "external_network",
            "id": "1050cce6-27ca-40df-b66e-160113fc4826"}, {
            "vnf_link_ports": [{
                "cp_instance_id": "350ab5d7-7cf0-4d24-aa2f-ec7e51149d56",
                "resource_handle": {
                    "vim_level_resource_type": "OS::Neutron::Port",
                    "resource_id": "2bca5538-edd6-4590-ab1a-552ae7d0f81b"},
                "id": "a41417d8-5cba-4256-aa4a-c68b79bb2dc2"}],
            "network_resource": {
                "vim_level_resource_type": "OS::Neutron::Net",
                "resource_id": "7ec01a11-e584-404a-88bd-39a56b63e29c"},
            "vnf_virtual_link_desc_id": "net0",
            "id": "5ad98d4d-4b81-4b1b-a88b-1f64b66e151b"}],
        "ext_managed_virtual_link_info": [{
            "network_resource": {
                "vim_level_resource_type": "OS::Neutron::Net",
                "resource_id": "413f4e46-21cf-41b1-be0f-de8d23f76cfd"},
            "id": "net1",
            "vnf_link_ports": [{
                "cp_instance_id": "b3341e7b-20bb-4ae5-8be9-b00cf79a9395",
                "resource_handle": {
                    "vim_level_resource_type": "OS::Neutron::Port",
                    "resource_id": "87b567a0-783a-4c06-b0d8-cdafd40c51e3"},
                "id": "124f1923-9de1-4729-8d4e-bc0613066dc4"}],
            "vnf_virtual_link_desc_id": "VL3"}],
        "flavour_id": "simple",
        "vnf_state": "STARTED",
        "ext_cp_info": [{
            "cp_protocol_info": [{
                "ip_over_ethernet": {
                    "mac_address": "fa:16:3e:0d:6f:71"},
                "layer_protocol": "IP_OVER_ETHERNET"}],
            "cpd_id": "CP1",
            "id": "19f0aa71-9376-43dc-8e13-5e76e4bdc8bf",
            "ext_link_port_id": None,
            "associated_vnfc_cp_id": "dc67ee99-e963-44e2-a152-f0fb492eae76"}, {
            "cp_protocol_info": [{
                "layer_protocol": "IP_OVER_ETHERNET"}],
            "cpd_id": "CP2",
            "id": "f47a9e33-b31a-4290-828a-c7569c52bd0e",
            "ext_link_port_id": None,
            "associated_vnfc_cp_id": "7ec01a11-e584-404a-88bd-39a56b63e29c"}]
    }
    }


class InstantiateVnfRequestTestCase(base.TestCase):

    def setUp(self):
        super(InstantiateVnfRequestTestCase, self).setUp()
        self.context = context.get_admin_context()

    def _create_vim_connection_info(self, **kwargs):
        vim_connection_info = objects.VimConnectionInfo(**kwargs)
        return [vim_connection_info]

    def _create_vnf_instance(self, vim_connection_info=None):
        vnf_instance = objects.VnfInstance(
            context=self.context,
            vnf_instance_name="Sample vnf instance name",
            vnf_instance_description="Sample vnf instance description",
            vnfd_id=uuidsentinel.vnfd_id,
            instantiation_state=fields.VnfInstanceState.INSTANTIATED,
            vnf_provider='Company',
            vnf_product_name='Sample VNF',
            vnf_software_version='1.0',
            vnfd_version='1.0',
            tenant_id=uuidsentinel.tenant_id)

        if vim_connection_info:
            vnf_instance.vim_connection_info = vim_connection_info

        return vnf_instance

    def test_from_vnf_instance_with_flavour(self):
        """Map flavour id"""

        inst_vnf_request = objects.InstantiateVnfRequest(flavour_id="simple")

        instantiated_vnf_info = objects.InstantiatedVnfInfo(
            flavour_id="simple")

        vnf_instance = self._create_vnf_instance()
        vnf_instance.instantiated_vnf_info = instantiated_vnf_info

        inst_vnf_request_actual = objects.InstantiateVnfRequest.\
            from_vnf_instance(vnf_instance)

        self.compare_obj(inst_vnf_request, inst_vnf_request_actual)

    def test_from_vnf_instance_with_flavour_and_instantiation_level(self):
        """Map flavour id and instantiation level"""

        inst_vnf_request = objects.InstantiateVnfRequest(flavour_id="simple",
            instantiation_level_id="instantiation_level_1")

        instantiated_vnf_info = objects.InstantiatedVnfInfo(
            flavour_id="simple",
            instantiation_level_id="instantiation_level_1")

        vnf_instance = self._create_vnf_instance()
        vnf_instance.instantiated_vnf_info = instantiated_vnf_info

        inst_vnf_request_actual = objects.InstantiateVnfRequest.\
            from_vnf_instance(vnf_instance)

        self.compare_obj(inst_vnf_request, inst_vnf_request_actual)

    def test_from_vnf_instance_with_ext_vl_and_ext_managed_vl(self):
        """Map external and internal network information.

        Map following information:
        a) ext_virtual_link_info
        b) ext_managed_virtual_link_info
        """

        ext_vl_info = [{
            "ext_cps": [{
                "cp_config": [{
                    "cp_protocol_data": [{
                        "ip_over_ethernet": {
                            "mac_address": "fa:16:3e:0d:6f:71"},
                        "layer_protocol": "IP_OVER_ETHERNET"}]}],
                "cpd_id": "CP1"}],
            "id": "net0",
            "resource_id": "7ec01a11-e584-404a-88bd-39a56b63e29c"}, {
            "ext_cps": [{
                "cp_config": [{
                    "cp_protocol_data": [{
                        "layer_protocol": "IP_OVER_ETHERNET"}],
                    "link_port_id": "413f4e46-21cf-41b1-be0f-de8d23f76cfe"}],
                "cpd_id": "CP2"}],
            "ext_link_ports": [{
                "id": "413f4e46-21cf-41b1-be0f-de8d23f76cfe",
                "resource_handle": {
                    "resource_id": "67f7e772-0d31-4087-bf4c-2576fadcbdb7",
                    "vim_level_resource_type": "LINKPORT"}}],
            "id": "external_network",
            "resource_id": "dc67ee99-e963-44e2-a152-f0fb492eae76"}]

        ext_mg_vl = {"id": "net1",
            "resource_id": "413f4e46-21cf-41b1-be0f-de8d23f76cfd",
            "vnf_virtual_link_desc_id": "VL3"}

        vim_connection_info = [{
            "id": "6b0ff598-60d6-49b4-a907-a1111de52d92",
            "vim_id": uuidsentinel.vim_id,
            "vim_type": "ETSINFV.OPENSTACK_KEYSTONE.v_2",
            "access_info": {}}]

        vnf_info_data = {'ext_managed_virtual_links': [ext_mg_vl],
            'ext_virtual_links': ext_vl_info,
            'vim_connection_info': vim_connection_info,
            'flavour_id': 'simple',
            'additional_params': {'key1': 'value1'}}

        inst_vnf_request = objects.InstantiateVnfRequest.obj_from_primitive(
            vnf_info_data, self.context)

        response = get_instantiated_info_dict_for_ext_links_and_flavour_id()

        instantiated_vnf_info_dict = response.get('instantiated_vnf_info')

        instantiated_vnf_info = objects.InstantiatedVnfInfo.obj_from_primitive(
            instantiated_vnf_info_dict, self.context)

        vnf_instance = self._create_vnf_instance(
            self._create_vim_connection_info(**vim_connection_info[0]))
        vnf_instance.instantiated_vnf_info = instantiated_vnf_info

        inst_vnf_req_actual = objects.InstantiateVnfRequest.from_vnf_instance(
            vnf_instance)

        self.assertEqual(inst_vnf_request.flavour_id,
            inst_vnf_req_actual.flavour_id)

        self.assertEqual(inst_vnf_request.instantiation_level_id,
            inst_vnf_req_actual.instantiation_level_id)

        self.assertEqual(inst_vnf_request.additional_params,
            inst_vnf_req_actual.additional_params)

        for expected, actual in zip(inst_vnf_request.ext_managed_virtual_links,
                inst_vnf_req_actual.ext_managed_virtual_links):
            self.compare_obj(expected, actual)

        for expected, actual in zip(inst_vnf_request.ext_virtual_links,
                inst_vnf_req_actual.ext_virtual_links):
            self.assertEqual(expected.id, actual.id)
            self.assertEqual(expected.resource_id, actual.resource_id)

        for expected, actual in zip(inst_vnf_request.vim_connection_info,
                inst_vnf_req_actual.vim_connection_info):
            self.assertEqual(expected.id, actual.id)
            self.assertEqual(expected.vim_id, actual.vim_id)
            self.assertEqual(expected.vim_type, actual.vim_type)
