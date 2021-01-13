# Copyright 2017 OpenStack Foundation
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
#

from tacker.tests import constants
from tacker.tests.functional import base


class VnfTestToscaFloatingIp(base.BaseTackerTest):

    def get_heat_stack_resource(self, stack_id, resource_name):
        resource_types = self.h_client.resources
        resource_details = resource_types.get(stack_id=stack_id,
                                              resource_name=resource_name)
        resource_dict = resource_details.to_dict()
        return resource_dict

    def connect_public_and_private_nw_with_router(self):
        public_nw = 'public'
        private_nw = 'net_mgmt'
        private_nw_subnet = 'subnet_mgmt'
        public_nw_id = None
        private_nw_id = None
        private_nw_subnet_id = None
        neutronclient = self.neutronclient()
        networks = neutronclient.list_networks()['networks']
        for nw in networks:
            if nw['name'] == public_nw:
                public_nw_id = nw['id']
            if nw['name'] == private_nw:
                private_nw_id = nw['id']
            if public_nw_id and private_nw_id:
                break
        self.assertIsNotNone(public_nw_id)
        self.assertIsNotNone(private_nw_id)
        subnets = neutronclient.list_subnets()['subnets']
        for subnet in subnets:
            if subnet['network_id'] == private_nw_id\
                    and subnet['name'] == private_nw_subnet:
                private_nw_subnet_id = subnet['id']
                break
        self.assertIsNotNone(private_nw_subnet_id)
        router_id = neutronclient.create_router(
            {'router': {'name': 'fip_test_router'}})['router']['id']
        self.assertIsNotNone(router_id)
        self.addCleanup(self.neutronclient().delete_router, router_id)
        rt_gw_id = neutronclient.add_gateway_router(
            router_id, {'network_id': public_nw_id})['router']['id']
        self.assertIsNotNone(rt_gw_id)
        self.addCleanup(self.neutronclient().remove_gateway_router,
            router_id)
        rt_int = neutronclient.add_interface_router(
            router_id, {'subnet_id': private_nw_subnet_id})['id']
        self.assertIsNotNone(rt_int)
        self.addCleanup(self.neutronclient().remove_interface_router,
            router_id, {'subnet_id': private_nw_subnet_id})

    def test_assign_floatingip_to_vdu(self):
        vnfd_file = 'sample_tosca_assign_floatingip_to_vdu.yaml'
        vnf_name = 'Assign Floating IP to VDU'
        self.connect_public_and_private_nw_with_router()
        vnfd_instance, vnf_instance, tosca_dict = self.vnfd_and_vnf_create(
            vnfd_file, vnf_name)
        vnf_id = vnf_instance['vnf']['id']
        self.addCleanup(self.wait_until_vnf_delete, vnf_id,
                        constants.VNF_CIRROS_DELETE_TIMEOUT)
        self.addCleanup(self.client.delete_vnf, vnf_id)
        self.wait_until_vnf_active(
            vnf_id,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)
        vnf_show_out = self.client.show_vnf(vnf_id)['vnf']
        self.assertIsNotNone(vnf_show_out['mgmt_ip_address'])

        stack_id = vnf_show_out['instance_id']
        fip_res = self.get_heat_stack_resource(stack_id, 'FIP1')
        floating_ip_address = fip_res['attributes']['floating_ip_address']
        self.assertIsNotNone(floating_ip_address)
        fip_port_id = fip_res['attributes']['port_id']
        port_res = self.get_heat_stack_resource(stack_id, 'CP1')
        port_id = port_res['attributes']['id']
        self.assertEqual(fip_port_id, port_id)
