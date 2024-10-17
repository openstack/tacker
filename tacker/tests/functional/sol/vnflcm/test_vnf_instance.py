# Copyright (C) 2020 NTT DATA
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

import random

from oslo_utils import uuidutils

from tacker.common import utils as com_utils
from tacker.objects import fields
from tacker.tests.functional import base
from tacker.tests.functional.sol.vnflcm import base as vnflcm_base
from tacker.tests import utils
from tacker.vnfm.infra_drivers.openstack import constants as infra_cnst

import tacker.conf
CONF = tacker.conf.CONF


def get_ext_managed_virtual_link(id, vl_desc_id, resource_id):
    return [{"id": id, "vnfVirtualLinkDescId": vl_desc_id,
            "resourceId": resource_id}]


def generate_mac_address():
    """Generate an Ethernet MAC address."""
    mac = [0xfa, 0x16, 0x3e,
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff)]
    return ':'.join(map(lambda x: "%02x" % x, mac))


def generate_ip_addresses(
        type_='IPV4',
        fixed_addresses=None,
        subnet_id=None):
    if fixed_addresses:
        ip_addr = {
            'type': type_,
            'fixedAddresses': fixed_addresses
        }
        if subnet_id:
            ip_addr.update({'subnetId': subnet_id})
    return [ip_addr]


def get_ext_cp_with_external_link_port(nw_resource_id, port_uuid):
    ext_cp = {
        "id": "external_network",
        "resourceId": nw_resource_id,
        "extCps": [{
            "cpdId": "CP2",
            "cpConfig": [{
                "linkPortId": "413f4e46-21cf-41b1-be0f-de8d23f76cfe",
                "cpProtocolData": [{
                    "layerProtocol": "IP_OVER_ETHERNET"
                }]
            }]
        }],
        "extLinkPorts": [{
            "id": "413f4e46-21cf-41b1-be0f-de8d23f76cfe",
            "resourceHandle": {
                "resourceId": port_uuid,
                "vimLevelResourceType": "LINKPORT"
            }
        }]
    }
    return ext_cp


def get_ext_cp_with_fixed_address(nw_resource_id, fixed_addresses, subnet_id):
    ext_cp = {
        "id": "external_network",
        "resourceId": nw_resource_id,
        "extCps": [{
            "cpdId": "CP2",
            "cpConfig": [{
                "cpProtocolData": [{
                    "layerProtocol": "IP_OVER_ETHERNET",
                    "ipOverEthernet": {
                        "ipAddresses": generate_ip_addresses(
                            fixed_addresses=fixed_addresses,
                            subnet_id=subnet_id)
                    }
                }]
            }]
        }]
    }
    return ext_cp


def get_external_virtual_links(net_0_resource_id, net_mgmt_resource_id,
        port_uuid, fixed_addresses=None, subnet_id=None):
    ext_vl = [
        {
            "id": "net0",
            "resourceId": net_0_resource_id,
            "extCps": [{
                "cpdId": "CP1",
                "cpConfig": [{
                    "cpProtocolData": [{
                        "layerProtocol": "IP_OVER_ETHERNET",
                        "ipOverEthernet": {
                            "macAddress": generate_mac_address()
                        }
                    }]
                }]
            }]
        }
    ]
    if fixed_addresses:
        ext_cp = get_ext_cp_with_fixed_address(
            net_mgmt_resource_id, fixed_addresses, subnet_id)
    else:
        ext_cp = get_ext_cp_with_external_link_port(
            net_mgmt_resource_id, port_uuid)
    ext_vl.append(ext_cp)

    return ext_vl


class VnfLcmTest(vnflcm_base.BaseVnfLcmTest):

    prepare_network = False

    @classmethod
    def setUpClass(cls):
        cls.tacker_client = base.BaseTackerTest.tacker_http_client()

        csar_path_1, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            utils.test_etc_sample("etsi/nfv", "vnflcm1"))
        cls.vnf_package_1, cls.vnfd_id_1 = (
            vnflcm_base._create_and_upload_vnf_package(
                cls.tacker_client, {"key": "sample_1_functional"},
                csar_path_1))

        csar_path_2, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            utils.test_etc_sample("etsi/nfv", "vnflcm2"))
        cls.vnf_package_2, cls.vnfd_id_2 = (
            vnflcm_base._create_and_upload_vnf_package(
                cls.tacker_client, {"key": "sample_2_functional"},
                csar_path_2))

        csar_path_3, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            utils.test_etc_sample("etsi/nfv", "vnflcm3"))
        cls.vnf_package_3, cls.vnfd_id_3 = (
            vnflcm_base._create_and_upload_vnf_package(
                cls.tacker_client, {"key": "sample_3_functional"},
                csar_path_3))

        super(VnfLcmTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        # Update operational state to DISABLED and delete vnf packages
        for package_id in [cls.vnf_package_1, cls.vnf_package_2,
                cls.vnf_package_3]:
            vnflcm_base._delete_vnf_package(cls.tacker_client, package_id)

        super(VnfLcmTest, cls).tearDownClass()

    def setUp(self):
        super(VnfLcmTest, self).setUp()

    def _get_server(self, server_id):
        try:
            self.novaclient().servers.get(server_id)
        except Exception:
            self.fail("Failed to get vdu resource %s id" % server_id)

    def _verify_vnfc_resource_info(self, vnf_instance_old,
            vnf_instance_current, vdu_count):
        vnfc_resource_info_old = (vnf_instance_old['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        vnfc_resource_info_current = (vnf_instance_current
            ['instantiatedVnfInfo']['vnfcResourceInfo'])
        for index in range(vdu_count):
            # compare computeResource resourceId is different
            vdu_resource_id_old = (vnfc_resource_info_old[index]
                ['computeResource']['resourceId'])
            vdu_resource_id_current = (vnfc_resource_info_current[index]
                ['computeResource']['resourceId'])
            self.assertNotEqual(vdu_resource_id_old, vdu_resource_id_current)

            # Now check whether vdus are healed properly and servers exists
            # in nova.
            self._get_server(vdu_resource_id_current)

    def _change_ext_conn_vnf_request(self, vim_id=None, ext_vl=None):
        request_body = {}
        if ext_vl:
            request_body["extVirtualLinks"] = ext_vl

        if vim_id:
            request_body["vimConnectionInfo"] = [
                {"id": uuidutils.generate_uuid(),
                 "vimId": vim_id,
                 "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_2"}]

        return request_body

    def _get_heat_stack(self, vnf_instance, h_client=None,
            prefix_id='vnflcm_'):
        # override to use vnfInstanceName as stack_name
        if h_client is None:
            h_client = self.h_client
        try:
            stacks = h_client.stacks.list()
        except Exception:
            return None

        target_stack_name = vnf_instance['vnfInstanceName']
        target_stacks = list(
            filter(
                lambda x: x.stack_name == target_stack_name,
                stacks))

        if len(target_stacks) == 0:
            return None

        return target_stacks[0]

    def test_create_show_delete_vnf_instance(self):
        """Create, show and delete a vnf instance."""

        # Create vnf instance
        vnf_instance_name = "Test-VNf-Instance"
        vnf_instance_description = "Sample VNF for LCM Testing"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_1,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        expected_result = {
            "instantiationState": fields.VnfInstanceState.NOT_INSTANTIATED,
            "vnfInstanceName": vnf_instance_name,
            "vnfInstanceDescription": vnf_instance_description
        }
        self._show_vnf_instance(vnf_instance['id'],
                                expected_result=expected_result)

        resp, _ = self._delete_vnf_instance(vnf_instance['id'])
        self.assertEqual(204, resp.status_code)

    def test_list_and_show_vnf_instances(self):
        """Test list vnf instances and show a vnf instance"""

        # Create subscription and register it.
        subscription_id = self.register_subscription()
        self.addCleanup(self._delete_subscription, subscription_id)

        # Create vnf instance 0 and don't instantiate this one.
        vnf_instance_name = "List-VNF-Instance-0"
        resp, vnf_instance_0 = self._create_vnf_instance(self.vnfd_id_1,
            vnf_instance_name=vnf_instance_name)
        self._wait_lcm_done(vnf_instance_id=vnf_instance_0['id'])
        self.assert_create_vnf(resp, vnf_instance_0)

        endpoint = CONF.vnf_lcm.endpoint_url.rstrip("/")
        vid = vnf_instance_0["id"]
        links = {
            "self": {"href":
                f"{endpoint}/vnflcm/v1/vnf_instances/{vid}"},
            "instantiate": {"href":
                f"{endpoint}/vnflcm/v1/vnf_instances/{vid}/instantiate"}
        }
        # Show vnf instance to check each parameter
        expected_result = {
            "instantiationState": fields.VnfInstanceState.NOT_INSTANTIATED,
            "vnfInstanceName": vnf_instance_name, "_links": links
        }
        self._show_vnf_instance(vid, expected_result=expected_result)

        # Create vnf instance 1 with 'VNF' as name and instantiate this one.
        # We can verify if vnf instance can be created with 'VNF' name itself.
        vnf_instance_name = "VNF"
        resp, vnf_instance_1 = self._create_vnf_instance(self.vnfd_id_1,
            vnf_instance_name=vnf_instance_name)
        self._wait_lcm_done(vnf_instance_id=vnf_instance_1['id'])
        self.assert_create_vnf(resp, vnf_instance_1)

        request_body = vnflcm_base._create_instantiate_vnf_request_body(
            "simple", vim_id=self.vim['id'])
        resp, _ = self._instantiate_vnf_instance(
            vnf_instance_1['id'], request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_1['id'])
        self.assert_instantiate_vnf(resp, vnf_instance_1['id'])

        # List vnf instances to check if first one is in NOT_INSTANTIATED
        # state and the second one is INSTANTIATED
        _, vnf_instances = self._list_vnf_instance()
        for vnf_instance in vnf_instances:
            if vnf_instance["id"] == vnf_instance_0["id"]:
                self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                    vnf_instance["instantiationState"])
            elif vnf_instance["id"] == vnf_instance_1["id"]:
                self.assertEqual(fields.VnfInstanceState.INSTANTIATED,
                    vnf_instance["instantiationState"])

        vid = vnf_instance_1["id"]
        links = {
            "self": {"href":
                f"{endpoint}/vnflcm/v1/vnf_instances/{vid}"},
            "terminate": {"href":
                f"{endpoint}/vnflcm/v1/vnf_instances/{vid}/terminate"},
            "scale": {"href":
                f"{endpoint}/vnflcm/v1/vnf_instances/{vid}/scale"},
            "heal": {"href":
                f"{endpoint}/vnflcm/v1/vnf_instances/{vid}/heal"},
            "changeExtConn": {"href":
                f"{endpoint}/vnflcm/v1/vnf_instances/{vid}/change_ext_conn"}
        }
        # Show vnf instance to check each parameter
        expected_result = {
            "instantiationState": fields.VnfInstanceState.INSTANTIATED,
            "vnfInstanceName": vnf_instance_name,
            "_links": links
        }
        self._show_vnf_instance(vid, expected_result=expected_result)

        # Terminate vnf gracefully with graceful timeout set to 60
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.GRACEFUL,
            'gracefulTerminationTimeout': 60
        }

        resp, _ = self._terminate_vnf_instance(
            vnf_instance_1['id'], terminate_req_body)
        self.assertEqual(202, resp.status_code)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance_1['id'])

        resp, _ = self._delete_vnf_instance(vnf_instance_0['id'])
        self.assertEqual(204, resp.status_code)
        resp, _ = self._delete_vnf_instance(vnf_instance_1['id'])
        self.assertEqual(204, resp.status_code)

    def test_instantiate_vnf_with_flavour(self):
        """Test instantiation and heal API without instantiation level

        This test will instantiate vnf using flavour. Heal API will be invoked
        by passing vnfcInstanceId parameter in the request body as per SOL002
        HealVnfRequest.
        """

        # Create subscription and register it.
        subscription_id = self.register_subscription()
        self.addCleanup(self._delete_subscription, subscription_id)

        # Create vnf instance
        vnf_instance_name = "vnf_with_flavour-%s" % uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level and no ext vl"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_1,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self._wait_lcm_done(vnf_instance_id=vnf_instance['id'])
        self.assert_create_vnf(resp, vnf_instance)

        request_body = vnflcm_base._create_instantiate_vnf_request_body(
            "simple", vim_id=self.vim['id'])

        resp, _ = self._instantiate_vnf_instance(
            vnf_instance['id'], request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])
        self.assert_instantiate_vnf(resp, vnf_instance['id'])

        _, vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        vdu_count = len(vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        self.assertEqual(1, vdu_count)

        # heal as per SOL002 API check, i.e. pass vnfcInstanceId in the
        # HealVnfRequest.
        vnfc_resource_info = (vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        vnfInstanceIds = [vnfc_res_info['id'] for vnfc_res_info in
            vnfc_resource_info]

        heal_request_body = {
            "cause": "Heal as per SOL002 API check",
            "vnfcInstanceId": vnfInstanceIds
        }

        resp, _ = self._heal_vnf_instance(vnf_instance['id'],
                                          heal_request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])
        self.assert_heal_vnf(resp, vnf_instance['id'])

        _, vnf_instance_current = self._show_vnf_instance(vnf_instance['id'])
        self._verify_vnfc_resource_info(vnf_instance, vnf_instance_current, 1)

        # Terminate vnf gracefully with graceful timeout set to 60
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.GRACEFUL,
            'gracefulTerminationTimeout': 60
        }

        resp, _ = self._terminate_vnf_instance(
            vnf_instance['id'], terminate_req_body)
        self.assertEqual(202, resp.status_code)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])

        resp, _ = self._delete_vnf_instance(vnf_instance['id'])
        self.assertEqual(204, resp.status_code)

    def test_instantiate_vnf_without_vim_connection_info(self):
        """Test instantiation API without vimConnectionInfo"""

        # Create subscription and register it.
        subscription_id = self.register_subscription()
        self.addCleanup(self._delete_subscription, subscription_id)

        # Create vnf instance
        vnf_instance_name = (
            f'vnf_without_vimConnectionInfo-{uuidutils.generate_uuid()}')
        vnf_instance_description = 'vnf without vimConnectionInfo'
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_1,
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)
        self._wait_lcm_done(vnf_instance_id=vnf_instance['id'])
        self.assert_create_vnf(resp, vnf_instance)

        request_body = vnflcm_base._create_instantiate_vnf_request_body(
            'simple', vim_id=None)

        resp, _ = self._instantiate_vnf_instance(
            vnf_instance['id'], request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])
        self.assert_instantiate_vnf(resp, vnf_instance['id'])

        _, vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        vdu_count = len(vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        self.assertEqual(1, vdu_count)
        self.assertEqual(self.vim['id'], vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'][0]['computeResource']['vimConnectionId'])

        # Terminate vnf gracefully with graceful timeout set to 60
        terminate_req_body = {
            'terminationType': fields.VnfInstanceTerminationType.GRACEFUL,
            'gracefulTerminationTimeout': 60
        }

        resp, _ = self._terminate_vnf_instance(
            vnf_instance['id'], terminate_req_body)
        self.assertEqual(202, resp.status_code)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])

        resp, _ = self._delete_vnf_instance(vnf_instance['id'])
        self.assertEqual(204, resp.status_code)

    def test_instantiate_vnf_with_instantiation_level(self):
        """Test instantiation and heal API with instantiation level

        This test will instantiate vnf with instantiation level. Heal API
        will be invoked by passing vnfcInstanceId parameter in the request
        body as per SOL002 HealVnfRequest.
        """

        # Create subscription and register it.
        subscription_id = self.register_subscription()
        self.addCleanup(self._delete_subscription, subscription_id)

        # Create vnf instance
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 2"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_2,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self._wait_lcm_done(vnf_instance_id=vnf_instance['id'])
        self.assert_create_vnf(resp, vnf_instance)

        request_body = vnflcm_base._create_instantiate_vnf_request_body(
            "simple", instantiation_level_id="instantiation_level_2",
            vim_id=self.vim['id'])

        resp, _ = self._instantiate_vnf_instance(
            vnf_instance['id'], request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])
        self.assert_instantiate_vnf(resp, vnf_instance['id'])

        _, vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        vdu_count = len(vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        self.assertEqual(3, vdu_count)

        # heal as per SOL002 API check, i.e.vnfcInstanceId is passed in
        # the HealVnfRequest.
        vnfc_resource_info = (vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        vnfInstanceIds = [vnfc_res_info['id'] for vnfc_res_info in
            vnfc_resource_info]

        heal_request_body = {
            "cause": "Heal as per SOL002 API check",
            "vnfcInstanceId": vnfInstanceIds
        }

        resp, _ = self._heal_vnf_instance(vnf_instance['id'],
                                          heal_request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])
        self.assert_heal_vnf(resp, vnf_instance['id'])

        _, vnf_instance_current = self._show_vnf_instance(vnf_instance['id'])
        self._verify_vnfc_resource_info(vnf_instance, vnf_instance_current, 3)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL
        }

        resp, _ = self._terminate_vnf_instance(
            vnf_instance['id'], terminate_req_body)
        self.assertEqual(202, resp.status_code)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])

        resp, _ = self._delete_vnf_instance(vnf_instance['id'])
        self.assertEqual(204, resp.status_code)

    def test_instantiate_vnf_with_ext_vl_and_ext_managed_vl(self):
        """Test instantiation vnf with external virtual links

        This test will instantiate vnf with external virtual links and
        external managed virtual links. Heal API will be invoked by
        passing vnfcInstanceId parameter in the request body as per SOL002
        HealVnfRequest.
        """

        # Create subscription and register it.
        subscription_id = self.register_subscription()
        self.addCleanup(self._delete_subscription, subscription_id)

        # Create vnf instance
        vnf_instance_name = "vnf_with_ext_vl_and_ext_managed_vl-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf_with_ext_vl_and_ext_managed_vl"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_3,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self._wait_lcm_done(vnf_instance_id=vnf_instance['id'])
        self.assert_create_vnf(resp, vnf_instance)

        neutron_client = self.neutronclient()
        net = neutron_client.list_networks()
        networks = {}
        for network in net['networks']:
            networks[network['name']] = network['id']

        net1_id = networks.get('net1')
        if not net1_id:
            self.fail("net1 network is not available")

        net0_id = networks.get('net0')
        if not net0_id:
            self.fail("net0 network is not available")

        net_mgmt_id = networks.get('net_mgmt')
        if not net_mgmt_id:
            self.fail("net_mgmt network is not available")

        ext_managed_vl = get_ext_managed_virtual_link("net1", "VL3",
            net1_id)

        net_ext = {}
        net_ext['id'], _ = self._create_network("external_network",
                                                neutron_client)
        self._create_subnet(net_ext, "22.22.0.0/24", "22.22.0.1",
                            neutron_client=neutron_client)
        port_uuid = self._create_port(net_ext['id'],
                                      neutron_client=neutron_client)
        ext_vl = get_external_virtual_links(net0_id, net_mgmt_id,
                                            port_uuid)

        request_body = vnflcm_base._create_instantiate_vnf_request_body(
            "simple", vim_id=self.vim['id'], ext_vl=ext_vl,
            ext_managed_vl=ext_managed_vl)

        resp, _ = self._instantiate_vnf_instance(
            vnf_instance['id'], request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])
        self.assert_instantiate_vnf(resp, vnf_instance['id'])

        _, vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        vdu_count = len(vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        self.assertEqual(1, vdu_count)

        # heal as per SOL002 API check, i.e.vnfcInstanceId is passed in
        # the HealVnfRequest.
        vnfc_resource_info = (vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        vnfInstanceIds = [vnfc_res_info['id'] for vnfc_res_info in
            vnfc_resource_info]

        heal_request_body = {
            "cause": "Heal as per SOL002 API check",
            "vnfcInstanceId": vnfInstanceIds
        }

        resp, _ = self._heal_vnf_instance(vnf_instance['id'],
                                          heal_request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])
        self.assert_heal_vnf(resp, vnf_instance['id'])

        _, vnf_instance_current = self._show_vnf_instance(vnf_instance['id'])
        self._verify_vnfc_resource_info(vnf_instance, vnf_instance_current, 1)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL
        }

        resp, _ = self._terminate_vnf_instance(
            vnf_instance['id'], terminate_req_body)
        self.assertEqual(202, resp.status_code)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])

        resp, _ = self._delete_vnf_instance(vnf_instance['id'])
        self.assertEqual(204, resp.status_code)

    def test_heal_vnf_sol_003_with_flavour(self):
        """Test heal API as per SOL 003 for VNF created with flavor

        This test will instantiate vnf using flavour. Heal API will be invoked
        as per SOL003 i.e. without passing vnfcInstanceId, so that the entire
        vnf is healed which includes VDU/CP/VL/STORAGE.
        """

        # Create subscription and register it.
        subscription_id = self.register_subscription()
        self.addCleanup(self._delete_subscription, subscription_id)

        # Create vnf instance
        vnf_instance_name = "heal_vnf_sol_003_with_flavour-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level and no ext vl"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_1,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self._wait_lcm_done(vnf_instance_id=vnf_instance['id'])
        self.assert_create_vnf(resp, vnf_instance)

        request_body = vnflcm_base._create_instantiate_vnf_request_body(
            "simple", vim_id=self.vim['id'])

        resp, _ = self._instantiate_vnf_instance(
            vnf_instance['id'], request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])
        self.assert_instantiate_vnf(resp, vnf_instance['id'])

        _, vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        vdu_count = len(vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        self.assertEqual(1, vdu_count)

        # heal as per SOL003 API check, i.e. without passing vnfcInstanceId in
        # the HealVnfRequest.
        heal_request_body = {
            "cause": "Heal as per SOL003 API check",
        }

        resp, _ = self._heal_vnf_instance(vnf_instance['id'],
                                          heal_request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])
        self.assert_heal_vnf(
            resp, vnf_instance['id'],
            expected_stack_status=infra_cnst.STACK_CREATE_COMPLETE)

        _, vnf_instance_current = self._show_vnf_instance(vnf_instance['id'])
        self._verify_vnfc_resource_info(vnf_instance, vnf_instance_current, 1)

        # Terminate vnf gracefully with graceful timeout set to 60
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.GRACEFUL,
            'gracefulTerminationTimeout': 60
        }

        resp, _ = self._terminate_vnf_instance(
            vnf_instance['id'], terminate_req_body)
        self.assertEqual(202, resp.status_code)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])

        resp, _ = self._delete_vnf_instance(vnf_instance['id'])
        self.assertEqual(204, resp.status_code)

    def test_heal_vnf_sol_003_with_instantiation_level(self):
        """Test heal as per SOL003 for VNF created with instantiation level

        This test will instantiate vnf with instantiation level. Heal API will
        be invoked as per SOL003 i.e. without passing vnfcInstanceId, so that
        the entire vnf is healed which includes VDU/CP/VL/STORAGE.
        """

        # Create subscription and register it.
        subscription_id = self.register_subscription()
        self.addCleanup(self._delete_subscription, subscription_id)

        # Create vnf instance
        vnf_instance_name = "heal_vnf_sol_003_with_instantiation_level-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 2"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_2,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self._wait_lcm_done(vnf_instance_id=vnf_instance['id'])
        self.assert_create_vnf(resp, vnf_instance)

        request_body = vnflcm_base._create_instantiate_vnf_request_body(
            "simple", instantiation_level_id="instantiation_level_2",
            vim_id=self.vim['id'])

        resp, _ = self._instantiate_vnf_instance(
            vnf_instance['id'], request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])
        self.assert_instantiate_vnf(resp, vnf_instance['id'])

        _, vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        vdu_count = len(vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        self.assertEqual(3, vdu_count)

        # heal as per SOL003 API check, i.e. without passing vnfcInstanceId
        # in the HealVnfRequest.
        heal_request_body = {
            "cause": "Heal as per SOL003 API check",
        }

        resp, _ = self._heal_vnf_instance(vnf_instance['id'],
                                          heal_request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])
        self.assert_heal_vnf(
            resp, vnf_instance['id'],
            expected_stack_status=infra_cnst.STACK_CREATE_COMPLETE)

        _, vnf_instance_current = self._show_vnf_instance(vnf_instance['id'])
        self._verify_vnfc_resource_info(vnf_instance, vnf_instance_current, 3)

        # Terminate vnf gracefully with graceful timeout set to 60
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.GRACEFUL,
            'gracefulTerminationTimeout': 60
        }

        resp, _ = self._terminate_vnf_instance(
            vnf_instance['id'], terminate_req_body)
        self.assertEqual(202, resp.status_code)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])

        resp, _ = self._delete_vnf_instance(vnf_instance['id'])
        self.assertEqual(204, resp.status_code)

    def test_heal_vnf_sol_003_ext_vl_and_ext_managed_vl(self):
        """Test heal vnf as per SOL003 with vnf created using external vl.

        This test will instantiate vnf with external virtual links and
        external managed virtual links. Heal API will be invoked as per SOL003
        i.e. without passing vnfcInstanceId, so that the entire vnf is healed
        which includes VDU/CP/VL/STORAGE.
        """

        # Create subscription and register it.
        subscription_id = self.register_subscription()
        self.addCleanup(self._delete_subscription, subscription_id)

        # Create vnf instance
        vnf_instance_name = "vnf_with_ext_vl_and_ext_managed_vl-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf_with_ext_vl_and_ext_managed_vl"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_3,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self._wait_lcm_done(vnf_instance_id=vnf_instance['id'])
        self.assert_create_vnf(resp, vnf_instance)

        neutron_client = self.neutronclient()
        net = neutron_client.list_networks()
        networks = {}
        for network in net['networks']:
            networks[network['name']] = network['id']

        net1_id = networks.get('net1')
        if not net1_id:
            self.fail("net1 network is not available")

        net0_id = networks.get('net0')
        if not net0_id:
            self.fail("net0 network is not available")

        net_mgmt_id = networks.get('net_mgmt')
        if not net_mgmt_id:
            self.fail("net_mgmt network is not available")

        ext_managed_vl = get_ext_managed_virtual_link("net1", "VL3",
            net1_id)

        net_ext = {}
        net_ext['id'], _ = self._create_network("external_network",
                                                neutron_client)
        self._create_subnet(net_ext, "22.22.0.0/24", "22.22.0.1",
                            neutron_client=neutron_client)
        port_uuid = self._create_port(net_ext['id'],
                                      neutron_client=neutron_client)
        ext_vl = get_external_virtual_links(net0_id, net_mgmt_id,
                                            port_uuid)

        request_body = vnflcm_base._create_instantiate_vnf_request_body(
            "simple", vim_id=self.vim['id'], ext_vl=ext_vl,
            ext_managed_vl=ext_managed_vl)

        resp, _ = self._instantiate_vnf_instance(
            vnf_instance['id'], request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])
        self.assert_instantiate_vnf(resp, vnf_instance['id'])

        _, vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        vdu_count = len(vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        self.assertEqual(1, vdu_count)

        # heal as per SOL003 API check, i.e. without passing vnfcInstanceId
        # in the HealVnfRequest.
        heal_request_body = {
            "cause": "Heal as per SOL003 API check",
        }
        resp, _ = self._heal_vnf_instance(vnf_instance['id'],
                                          heal_request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])
        self.assert_heal_vnf(
            resp, vnf_instance['id'],
            expected_stack_status=infra_cnst.STACK_CREATE_COMPLETE)

        _, vnf_instance_current = self._show_vnf_instance(vnf_instance['id'])
        self._verify_vnfc_resource_info(vnf_instance, vnf_instance_current, 1)

        # Terminate vnf gracefully with graceful timeout set to 60
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.GRACEFUL,
            'gracefulTerminationTimeout': 60
        }

        resp, _ = self._terminate_vnf_instance(
            vnf_instance['id'], terminate_req_body)
        self.assertEqual(202, resp.status_code)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])

        resp, _ = self._delete_vnf_instance(vnf_instance['id'])
        self.assertEqual(204, resp.status_code)

    def test_inst_chgextconn_term(self):
        """Test change external vnf connectivity.

        This test will instantiate vnf with external virtual link and
        change the IP address on virtual link.
        """

        # Create subscription and register it.
        subscription_id = self.register_subscription()
        self.addCleanup(self._delete_subscription, subscription_id)

        # Create vnf instance
        vnf_instance_name = "vnf_with_ext_vl_and_ext_managed_vl-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf_with_ext_vl_and_ext_managed_vl"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_3,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self._wait_lcm_done(vnf_instance_id=vnf_instance['id'])
        self.assert_create_vnf(resp, vnf_instance)

        neutron_client = self.neutronclient()
        net = neutron_client.list_networks()
        networks = {}
        for network in net['networks']:
            networks[network['name']] = network['id']
        subnet_list = neutron_client.list_subnets()
        subnets = {}
        for subnet in subnet_list['subnets']:
            subnets[subnet['name']] = subnet['id']

        net1_id = networks.get('net1')
        if not net1_id:
            self.fail("net1 network is not available")

        net0_id = networks.get('net0')
        if not net0_id:
            self.fail("net0 network is not available")

        net_mgmt_id = networks.get('net_mgmt')
        if not net_mgmt_id:
            self.fail("net_mgmt network is not available")

        subnet_mgmt_id = subnets.get('subnet_mgmt')
        if not subnet_mgmt_id:
            self.fail("subnet_mgmt subnet is not available")

        ext_managed_vl = get_ext_managed_virtual_link("net1", "VL3",
            net1_id)

        net_ext = {}
        net_ext['id'], _ = self._create_network("external_network",
                                                neutron_client)
        subnet_uuid = self._create_subnet(net_ext, "22.22.0.0/24", "22.22.0.1",
                                          neutron_client=neutron_client)

        # Instantiate vnf
        ext_vl = get_external_virtual_links(
            net0_id, net_mgmt_id, None,
            fixed_addresses=['192.168.120.100'],
            subnet_id=subnet_mgmt_id)

        request_body = vnflcm_base._create_instantiate_vnf_request_body(
            "simple", vim_id=self.vim['id'], ext_vl=ext_vl,
            ext_managed_vl=ext_managed_vl)

        resp, _ = self._instantiate_vnf_instance(
            vnf_instance['id'], request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])
        self.assert_instantiate_vnf(resp, vnf_instance['id'])

        _, vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        vdu_count = len(vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        self.assertEqual(1, vdu_count)

        # Change external vnf connectivity
        changed_ext_vl = get_external_virtual_links(
            net0_id, net_ext['id'], None,
            fixed_addresses=['22.22.0.100'],
            subnet_id=subnet_uuid)
        change_ext_conn_req_body = self._change_ext_conn_vnf_request(
            vim_id=self.vim['id'], ext_vl=changed_ext_vl)
        before_fixed_ips = self._get_fixed_ips(vnf_instance, request_body)
        resp, _ = self._change_ext_conn_vnf_instance(
            vnf_instance['id'], change_ext_conn_req_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])
        self.assert_change_ext_conn_vnf(resp, request_body, vnf_instance['id'],
                                        before_fixed_ips=before_fixed_ips)

        # Terminate vnf gracefully with graceful timeout set to 60
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.GRACEFUL,
            'gracefulTerminationTimeout': 60
        }

        resp, _ = self._terminate_vnf_instance(
            vnf_instance['id'], terminate_req_body)
        self.assertEqual(202, resp.status_code)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])

        resp, _ = self._delete_vnf_instance(vnf_instance['id'])
        self.assertEqual(204, resp.status_code)

    def test_update_vnf_instance_not_instantiated(self):
        """Update vnf instance in not_instantiated state."""

        # Create subscription and register it.
        subscription_id = self.register_subscription()
        self.addCleanup(self._delete_subscription, subscription_id)

        # Create vnf instance
        vnf_instance_name = (
            f"vnf_update_vnf_instance-{uuidutils.generate_uuid()}")
        vnf_instance_description = "vnf_update_vnf_instance"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_1,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self._wait_lcm_done(vnf_instance_id=vnf_instance['id'])
        self.assert_create_vnf(resp, vnf_instance)

        # Update vnf instance
        request_body = {
            "vnfInstanceName": f"{vnf_instance_name}_chg",
            "vnfInstanceDescription":
                f"{vnf_instance_description}_chg",
            "metadata": {"key": "value"}
        }
        resp, _ = self._update_vnf_instance(vnf_instance['id'],
            request_body)

        self.assertEqual(202, resp.status_code)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])

        expected_result = {
            "instantiationState": fields.VnfInstanceState.NOT_INSTANTIATED,
            "vnfInstanceName": request_body["vnfInstanceName"],
            "vnfInstanceDescription": request_body["vnfInstanceDescription"],
            "metadata": request_body["metadata"]
        }
        self._show_vnf_instance(vnf_instance['id'],
                                expected_result=expected_result)

        resp, _ = self._delete_vnf_instance(vnf_instance['id'])
        self.assertEqual(204, resp.status_code)

    def test_update_vnf_instance_instantiated(self):
        """Update vnf instance in instantiated state."""

        # Create subscription and register it.
        subscription_id = self.register_subscription()
        self.addCleanup(self._delete_subscription, subscription_id)

        # Create vnf instance
        vnf_instance_name = (
            f"vnf_update_vnf_instance-{uuidutils.generate_uuid()}")
        vnf_instance_description = "vnf_update_vnf_instance"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_1,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self._wait_lcm_done(vnf_instance_id=vnf_instance['id'])
        self.assert_create_vnf(resp, vnf_instance)

        # Instantiate vnf instance
        request_body = vnflcm_base._create_instantiate_vnf_request_body(
            "simple", vim_id=self.vim['id'])
        resp, _ = self._instantiate_vnf_instance(
            vnf_instance['id'], request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])
        self.assert_instantiate_vnf(resp, vnf_instance['id'])

        # Update vnf instance
        _, vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        vim_connection_info_add = {
            "id": "11112222-3333-4444-5555-666677778888",
            "vim_id": vnf_instance["vimConnectionInfo"][0]["vimId"],
            "vim_type": "openstack",
            "interface_info": {},
            "access_info": {},
            "extra": {}
        }
        vnf_instance["vimConnectionInfo"][0]["extra"] = {"key": "value"}
        vim_connection_info_chg = vnf_instance["vimConnectionInfo"][0]

        request_body = {
            "vnfInstanceName": f"{vnf_instance_name}_chg",
            "vnfInstanceDescription":
                f"{vnf_instance_description}_chg",
            "metadata": {"key": "value"},
            "vimConnectionInfo": [
                vim_connection_info_add,
                com_utils.convert_camelcase_to_snakecase(
                    vim_connection_info_chg)
            ]
        }

        resp, _ = self._update_vnf_instance(vnf_instance['id'],
            request_body)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])
        # set expected_stack_status=None in order not to check the stack status
        self.assert_update_vnf(resp, vnf_instance['id'],
                               expected_stack_status=None)

        expected_result = {
            "instantiationState": fields.VnfInstanceState.INSTANTIATED,
            "vnfInstanceName": request_body["vnfInstanceName"],
            "vnfInstanceDescription": request_body["vnfInstanceDescription"],
            "metadata": {
                **vnf_instance["metadata"],
                **request_body["metadata"]
            },
            "vimConnectionInfo": [
                com_utils.convert_snakecase_to_camelcase(
                    vim_connection_info_add),
                vim_connection_info_chg,
                vnf_instance["vimConnectionInfo"][1]
            ]
        }
        self._show_vnf_instance(vnf_instance['id'],
                                expected_result=expected_result)

        # Terminate vnf gracefully with graceful timeout set to 60
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.GRACEFUL,
            "gracefulTerminationTimeout": 60
        }

        resp, _ = self._terminate_vnf_instance(
            vnf_instance['id'], terminate_req_body)
        self.assertEqual(202, resp.status_code)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance['id'])

        resp, _ = self._delete_vnf_instance(vnf_instance['id'])
        self.assertEqual(204, resp.status_code)
