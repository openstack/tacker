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

import copy

from tacker import context
from tacker import objects
from tacker.tests.unit import base
from tacker.tests import uuidsentinel


class ChangeExtConnRequestTestCase(base.TestCase):

    def setUp(self):
        super(ChangeExtConnRequestTestCase, self).setUp()
        self.context = context.get_admin_context()

    def _get_change_ext_conn_request(self):
        ext_vl_info = [{
            "id": "external_network",
            "vim_connection_id": "6b0ff598-60d6-49b4-a907-a1111de52d92",
            "resource_id": "dc67ee99-e963-44e2-a152-f0fb492eae76",
            "ext_cps": [{
                "cpd_id": "CP1",
                "cp_config": [{
                    "cp_protocol_data": [{
                        "ip_over_ethernet": {
                            "mac_address": "fa:16:3e:0d:6f:71"},
                        "layer_protocol": "IP_OVER_ETHERNET"}]}]}, {
                "cpd_id": "CP2",
                "cp_config": [{
                    "cp_protocol_data": [{
                        "ip_over_ethernet": {
                            "ipaddresses": [{
                                "type": "IPV4",
                                "fixed_addresses": [
                                    "10.0.0.1"],
                                "subnet_id":
                                    "55f0fb3c-6a70-11eb-9439-0242ac130002"}]},
                        "layer_protocol": "IP_OVER_ETHERNET"}]}]}, {
                "cpd_id": "CP3",
                "cp_config": [{
                    "cp_protocol_data": [{
                        "ip_over_ethernet": {
                            "ipaddresses": [{
                                "type": "IPV4",
                                "num_dynamic_addresses": 1,
                                "subnet_id":
                                    "3a7a37fc-6a92-11eb-9439-0242ac130002"}]},
                        "layer_protocol": "IP_OVER_ETHERNET"}]}]}, {
                "cpd_id": "CP4",
                "cp_config": [{
                    "cp_protocol_data": [{
                        "layer_protocol": "IP_OVER_ETHERNET"}],
                    "link_port_id":
                        "413f4e46-21cf-41b1-be0f-de8d23f76cfe"}]}],
            "ext_link_ports": [{
                "id": "413f4e46-21cf-41b1-be0f-de8d23f76cfe",
                "resource_handle": {
                    "resource_id": "67f7e772-0d31-4087-bf4c-2576fadcbdb7",
                    "vim_connection_id":
                        "6b0ff598-60d6-49b4-a907-a1111de52d92",
                    "vim_level_resource_type": "LINKPORT"}}], }]

        vim_connection_info = [{
            "id": "6b0ff598-60d6-49b4-a907-a1111de52d92",
            "vim_id": uuidsentinel.vim_id,
            "vim_type": "ETSINFV.OPENSTACK_KEYSTONE.v_2",
            "interface_info": {
                "endpoint": "endpoint_value"},
            "access_info": {
                "username": "username_value",
                "password": "password_value",
                "region": "region_value",
                "tenant": "tenant_value"}}]

        change_ext_conn_data = {
            'ext_virtual_links': ext_vl_info,
            'vim_connection_info': vim_connection_info,
            'additional_params': {'key1': 'value1'}}

        return change_ext_conn_data

    def test_obj_from_primitive(self):
        change_ext_conn_data = self._get_change_ext_conn_request()
        change_ext_conn_req = objects.ChangeExtConnRequest.obj_from_primitive(
            copy.deepcopy(change_ext_conn_data), self.context)
        self._check_change_ext_conn_req(change_ext_conn_req,
            change_ext_conn_data)

    def _check_change_ext_conn_req(self, obj, data):

        def _check_vim_connection_info(_obj, _data):
            self.assertEqual(len(_obj), len(_data))
            for obj, data in zip(_obj, _data):
                self.assertIsInstance(obj, objects.VimConnectionInfo)

        def _check_external_virtual_links(_obj, _data):
            self.assertEqual(len(_obj), len(_data))
            for obj, data in zip(_obj, _data):
                self.assertIsInstance(obj, objects.ExtVirtualLinkData)
                self.assertEqual(obj.id, data.get('id'))
                self.assertEqual(obj.vim_connection_id,
                    data.get('vim_connection_id'))
                self.assertEqual(obj.resource_id,
                    data.get('resource_id'))
                _check_ext_cps(obj.ext_cps,
                    data.get('ext_cps', []))
                _check_ext_link_ports(obj.ext_link_ports,
                    data.get('ext_link_ports', []))

        def _check_ext_cps(_obj, _data):
            self.assertEqual(len(_obj), len(_data))
            for obj, data in zip(_obj, _data):
                self.assertIsInstance(obj, objects.VnfExtCpData)
                self.assertEqual(obj.cpd_id, data.get('cpd_id'))
                _check_ext_cp_config(obj.cp_config,
                    data.get('cp_config', []))

        def _check_ext_cp_config(_obj, _data):
            self.assertEqual(len(_obj), len(_data))
            for obj, data in zip(_obj, _data):
                self.assertIsInstance(obj, objects.VnfExtCpConfig)
                self.assertEqual(obj.cp_instance_id,
                    data.get('cp_instance_id'))
                self.assertEqual(obj.link_port_id,
                    data.get('link_port_id'))
                _check_cp_protocol_data(obj.cp_protocol_data,
                    data.get('cp_protocol_data', []))

        def _check_cp_protocol_data(_obj, _data):
            self.assertEqual(len(_obj), len(_data))
            for obj, data in zip(_obj, _data):
                self.assertIsInstance(obj, objects.CpProtocolData)
                self.assertEqual(obj.layer_protocol,
                    data.get('layer_protocol'))
                if obj.ip_over_ethernet or data.get('ip_over_ethernet', None):
                    _check_ip_over_ethernet(obj.ip_over_ethernet,
                        data.get('ip_over_ethernet', None))

        def _check_ip_over_ethernet(obj, data):
            self.assertIsInstance(obj, objects.IpOverEthernetAddressData)
            self.assertEqual(obj.mac_address, data.get('mac_address'))
            _check_ip_addresses(obj.ip_addresses,
                data.get('ip_addressest', []))

        def _check_ip_addresses(_obj, _data):
            self.assertEqual(len(_obj), len(_data))
            for obj, data in zip(_obj, _data):
                self.assertIsInstance(obj, objects.IpAddressReq)
                self.assertEqual(obj.type, data.get('type'))
                self.assertEqual(obj.subnet_id, data.get('subnet_id'))
                self.assertEqual(obj.num_dynamic_addresses,
                    data.get('num_dynamic_addresses'))

        def _check_ext_link_ports(_obj, _data):
            self.assertEqual(len(_obj), len(_data))
            for obj, data in zip(_obj, _data):
                self.assertIsInstance(obj, objects.ExtLinkPortData)
                self.assertEqual(obj.id, data.get('id'))
                self.assertIsInstance(obj.resource_handle,
                    objects.ResourceHandle)

        self.assertIsInstance(obj, objects.ChangeExtConnRequest)
        _check_external_virtual_links(obj.ext_virtual_links,
            data.get('ext_virtual_links'))
        _check_vim_connection_info(obj.vim_connection_info,
            data.get('vim_connection_info'))
