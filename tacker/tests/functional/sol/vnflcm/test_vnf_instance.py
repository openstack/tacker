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

import os
import random
import time

from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from tacker.common import utils as com_utils
from tacker.objects import fields
from tacker.tests.functional import base
from tacker.tests import utils
from tacker.vnfm.infra_drivers.openstack import constants as infra_cnst

import tacker.conf
CONF = tacker.conf.CONF

VNF_PACKAGE_UPLOAD_TIMEOUT = 300
VNF_INSTANTIATE_TIMEOUT = 600
VNF_TERMINATE_TIMEOUT = 600
VNF_HEAL_TIMEOUT = 600
VNF_CHANGE_EXT_CONN_TIMEOUT = 600
RETRY_WAIT_TIME = 5
WAIT_HEAL = 60  # Time to wait until heal op is completed in sec.
UPDATE_WAIT_TIME = 10


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


def _create_and_upload_vnf_package(tacker_client, csar_package_name,
        user_defined_data):
    # create vnf package
    body = jsonutils.dumps({"userDefinedData": user_defined_data})
    resp, vnf_package = tacker_client.do_request(
        '/vnfpkgm/v1/vnf_packages', "POST", body=body)

    # upload vnf package
    file_path = utils.test_etc_sample("etsi/nfv", csar_package_name)

    # Generating unique vnfd id. This is required when multiple workers
    # are running concurrently. The call below creates a new temporary
    # CSAR with unique vnfd id.
    file_path, uniqueid = utils.create_csar_with_unique_vnfd_id(file_path)

    with open(file_path, 'rb') as file_object:
        resp, resp_body = tacker_client.do_request(
            '/vnfpkgm/v1/vnf_packages/{id}/package_content'.format(
                id=vnf_package['id']),
            "PUT", body=file_object, content_type='application/zip')

    # wait for onboard
    timeout = VNF_PACKAGE_UPLOAD_TIMEOUT
    start_time = int(time.time())
    show_url = os.path.join('/vnfpkgm/v1/vnf_packages', vnf_package['id'])
    vnfd_id = None
    while True:
        resp, body = tacker_client.do_request(show_url, "GET")
        if body['onboardingState'] == "ONBOARDED":
            vnfd_id = body['vnfdId']
            break

        if ((int(time.time()) - start_time) > timeout):
            raise Exception("Failed to onboard vnf package")

        time.sleep(1)

    # remove temporarily created CSAR file
    os.remove(file_path)
    return vnf_package['id'], vnfd_id


class VnfLcmTest(base.BaseTackerTest):

    @classmethod
    def setUpClass(cls):
        cls.tacker_client = base.BaseTackerTest.tacker_http_client()

        cls.vnf_package_1, cls.vnfd_id_1 = _create_and_upload_vnf_package(
            cls.tacker_client, "vnflcm1", {"key": "sample_1_functional"})

        cls.vnf_package_2, cls.vnfd_id_2 = _create_and_upload_vnf_package(
            cls.tacker_client, "vnflcm2", {"key": "sample_2_functional"})

        cls.vnf_package_3, cls.vnfd_id_3 = _create_and_upload_vnf_package(
            cls.tacker_client, "vnflcm3", {"key": "sample_3_functional"})

        super(VnfLcmTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        # Update vnf package operational state to DISABLED
        update_req_body = jsonutils.dumps({
            "operationalState": "DISABLED"})
        base_path = "/vnfpkgm/v1/vnf_packages"
        for package_id in [cls.vnf_package_1, cls.vnf_package_2,
                cls.vnf_package_3]:
            resp, resp_body = cls.tacker_client.do_request(
                '{base_path}/{id}'.format(id=package_id,
                                          base_path=base_path),
                "PATCH", content_type='application/json', body=update_req_body)

            # Delete vnf package
            url = '/vnfpkgm/v1/vnf_packages/%s' % package_id
            cls.tacker_client.do_request(url, "DELETE")

        super(VnfLcmTest, cls).tearDownClass()

    def setUp(self):
        super(VnfLcmTest, self).setUp()
        self.base_url = "/vnflcm/v1/vnf_instances"
        self.base_vnf_lcm_op_occs_url = "/vnflcm/v1/vnf_lcm_op_occs"

        vim_list = self.client.list_vims()
        if not vim_list:
            self.skipTest("Vims are not configured")

        vim_id = 'VIM0'
        vim = self.get_vim(vim_list, vim_id)
        if not vim:
            self.skipTest("Default VIM '%s' is missing" % vim_id)
        self.vim_id = vim['id']

    def _instantiate_vnf_request(self, flavour_id,
            instantiation_level_id=None, vim_id=None, ext_vl=None,
            ext_managed_vl=None):
        request_body = {"flavourId": flavour_id}

        if instantiation_level_id:
            request_body["instantiationLevelId"] = instantiation_level_id

        if ext_managed_vl:
            request_body["extManagedVirtualLinks"] = ext_managed_vl

        if ext_vl:
            request_body["extVirtualLinks"] = ext_vl

        if vim_id:
            request_body["vimConnectionInfo"] = [
                {"id": uuidutils.generate_uuid(),
                 "vimId": vim_id,
                 "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_2"}]

        return request_body

    def _create_vnf_instance(self, vnfd_id, vnf_instance_name=None,
            vnf_instance_description=None):
        request_body = {'vnfdId': vnfd_id}
        if vnf_instance_name:
            request_body['vnfInstanceName'] = vnf_instance_name

        if vnf_instance_description:
            request_body['vnfInstanceDescription'] = vnf_instance_description

        resp, response_body = self.http_client.do_request(
            self.base_url, "POST", body=jsonutils.dumps(request_body))
        return resp, response_body

    def _delete_wait_vnf_instance(self, id):
        timeout = VNF_TERMINATE_TIMEOUT
        url = os.path.join(self.base_url, id)
        start_time = int(time.time())
        while True:
            resp, body = self.http_client.do_request(url, "DELETE")
            if 204 == resp.status_code:
                break

            if ((int(time.time()) - start_time) > timeout):
                error = "Failed to delete vnf instance %s"
                self.fail(error % id)

            time.sleep(RETRY_WAIT_TIME)

    def _delete_vnf_instance(self, id):
        self._delete_wait_vnf_instance(id)

        # verify vnf instance is deleted
        url = os.path.join(self.base_url, id)
        resp, body = self.http_client.do_request(url, "GET")
        self.assertEqual(404, resp.status_code)

    def _show_vnf_instance(self, id, expected_result=None):
        show_url = os.path.join(self.base_url, id)
        resp, vnf_instance = self.http_client.do_request(show_url, "GET")
        self.assertEqual(200, resp.status_code)

        if expected_result:
            self.assertDictSupersetOf(expected_result, vnf_instance)

        return vnf_instance

    def _list_vnf_instances(self):
        resp, vnf_instances = self.http_client.do_request(self.base_url, "GET")
        self.assertEqual(200, resp.status_code)
        return vnf_instances

    def _update_vnf_instance(self, id, request_body):
        url = os.path.join(self.base_url, id)

        resp, response_body = self.http_client.do_request(
            url, "PATCH", body=jsonutils.dumps(request_body))

        # Wait for operation state completed
        time.sleep(UPDATE_WAIT_TIME)

        return resp, response_body

    def _stack_update_wait(self, stack_id, expected_status,
            timeout=VNF_HEAL_TIMEOUT):
        start_time = int(time.time())
        while True:
            stack = self.h_client.stacks.get(stack_id)
            if stack.stack_status == expected_status:
                break

            if ((int(time.time()) - start_time) > timeout):
                error = ("Stack %(id)s status is %(current)s, expected status "
                        "should be %(expected)s")
                self.fail(error % {"id": stack_id, "current": stack.status,
                    "expected": expected_status})

            time.sleep(RETRY_WAIT_TIME)

    def _vnf_instance_wait(self, id,
            instantiation_state=fields.VnfInstanceState.INSTANTIATED,
            timeout=VNF_INSTANTIATE_TIMEOUT):
        show_url = os.path.join(self.base_url, id)
        start_time = int(time.time())
        while True:
            resp, body = self.http_client.do_request(show_url, "GET")
            if body['instantiationState'] == instantiation_state:
                break

            if ((int(time.time()) - start_time) > timeout):
                error = ("Vnf instance %(id)s status is %(current)s, "
                         "expected status should be %(expected)s")
                self.fail(error % {"id": id,
                    "current": body['instantiationState'],
                    "expected": instantiation_state})

            time.sleep(RETRY_WAIT_TIME)

    def _create_network(self, neutron_client, network_name):
        net = neutron_client.create_network(
            {'network': {'name': "network-%s" % uuidutils.generate_uuid()}})
        net_id = net['network']['id']
        self.addCleanup(neutron_client.delete_network, net_id)
        return net_id

    def _create_subnet(self, neutron_client, network_id):
        body = {'subnet': {'network_id': network_id,
                'name': "subnet-%s" % uuidutils.generate_uuid(),
                'cidr': "22.22.0.0/24",
                'ip_version': 4,
                'gateway_ip': '22.22.0.1',
                "enable_dhcp": True}}
        subnet = neutron_client.create_subnet(body=body)["subnet"]
        self.addCleanup(neutron_client.delete_subnet, subnet['id'])
        return subnet['id']

    def _create_port(self, neutron_client, network_id):
        body = {'port': {'network_id': network_id}}
        port = neutron_client.create_port(body=body)["port"]
        self.addCleanup(neutron_client.delete_port, port['id'])
        return port['id']

    def _instantiate_vnf_instance(self, id, request_body):
        url = os.path.join(self.base_url, id, "instantiate")
        resp, body = self.http_client.do_request(url, "POST",
                body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)
        self._vnf_instance_wait(id)

    def _terminate_vnf_instance(self, id, request_body):
        url = os.path.join(self.base_url, id, "terminate")
        resp, body = self.http_client.do_request(url, "POST",
                body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)

        timeout = request_body.get('gracefulTerminationTimeout')
        start_time = int(time.time())

        self._vnf_instance_wait(id,
            instantiation_state=fields.VnfInstanceState.NOT_INSTANTIATED,
            timeout=VNF_TERMINATE_TIMEOUT)

        # If gracefulTerminationTimeout is set, check whether vnf
        # instantiation_state is set to NOT_INSTANTIATED after
        # gracefulTerminationTimeout seconds.
        if timeout and int(time.time()) - start_time < timeout:
            self.fail("Vnf is terminated before graceful termination "
                      "timeout period")

    def _heal_vnf_instance(self, vnf_instance, request_body,
            expected_stack_status=infra_cnst.STACK_UPDATE_COMPLETE):
        url = os.path.join(self.base_url, vnf_instance['id'], "heal")
        resp, body = self.http_client.do_request(url, "POST",
                body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)

        stack = self.h_client.stacks.get(vnf_instance['vnfInstanceName'])
        # Wait until tacker heals the stack resources as requested in
        # in the heal request
        self._stack_update_wait(stack.id, expected_stack_status)

    def _heal_sol_003_vnf_instance(self, vnf_instance, request_body):
        url = os.path.join(self.base_url, vnf_instance['id'], "heal")
        resp, body = self.http_client.do_request(url, "POST",
                body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)

        # If healing is done without vnfc components, it will delete the
        # stack and create a new one. So wait until vnf is deleted and then
        # wait until a new stack is created using vnfInstanceName and once
        # the stack is created, wait until it's status becomes
        # CREATE_COMPLETE.
        stack = self.h_client.stacks.get(vnf_instance['vnfInstanceName'])
        self._stack_update_wait(stack.id, infra_cnst.STACK_DELETE_COMPLETE)
        start_time = int(time.time())
        timeout = VNF_INSTANTIATE_TIMEOUT
        while True:
            try:
                stack = self.h_client.stacks.get(
                    vnf_instance['vnfInstanceName'])
                if stack.stack_status == infra_cnst.STACK_CREATE_COMPLETE:
                    break
            except Exception:
                pass

            if ((int(time.time()) - start_time) > timeout):
                self.fail("Failed to heal vnf during instantiation")

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

    def _change_ext_conn_vnf_instance(self, vnf_instance, request_body,
            expected_stack_status=infra_cnst.STACK_UPDATE_COMPLETE):
        url = os.path.join(self.base_url, vnf_instance['id'],
            "change_ext_conn")
        resp, body = self.http_client.do_request(url, "POST",
            body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)

        stack = self.h_client.stacks.get(vnf_instance['vnfInstanceName'])
        # Wait until tacker changes the stack resources as requested
        # in the change_ext_conn request
        self._stack_update_wait(stack.id, expected_stack_status,
                                VNF_CHANGE_EXT_CONN_TIMEOUT)

    def _get_heat_stack(self, vnf_instance_id, stack_name):
        heatclient = self.heatclient()
        try:
            stacks = heatclient.stacks.list()
        except Exception:
            return None

        target_stakcs = list(
            filter(
                lambda x: x.stack_name == stack_name,
                stacks))

        if len(target_stakcs) == 0:
            return None

        return target_stakcs[0]

    def _get_heat_resource_info(self, stack_id, nested_depth=0,
            resource_name=None):
        heatclient = self.heatclient()
        try:
            if resource_name is None:
                resources = heatclient.resources.list(stack_id,
                                         nested_depth=nested_depth)
            else:
                resources = heatclient.resources.get(stack_id,
                                         resource_name)
        except Exception:
            return None
        return resources

    def _get_fixed_ips(self, vnf_instance, request_body):
        vnf_instance_id = vnf_instance['id']
        vnf_instance_name = vnf_instance['vnfInstanceName']
        res_name = None
        for extvirlink in request_body['extVirtualLinks']:
            if 'extCps' not in extvirlink:
                continue
            for extcps in extvirlink['extCps']:
                if 'cpdId' in extcps:
                    if res_name is None:
                        res_name = list()
                    res_name.append(extcps['cpdId'])
                    break
        if res_name is None:
            return []

        stack = self._get_heat_stack(vnf_instance_id,
                                     vnf_instance_name)
        stack_id = stack.id

        stack_resource = self._get_heat_resource_info(
            stack_id, nested_depth=2)

        releations = dict()
        for elmt in stack_resource:
            if elmt.resource_type != 'OS::Neutron::Port':
                continue
            if elmt.resource_name not in res_name:
                continue
            parent = getattr(elmt, 'parent_resource', None)
            releations[parent] = elmt.resource_name

        details = dict()
        for (parent_name, resource_name) in releations.items():
            for elmt in stack_resource:
                if parent_name is None:
                    detail_stack = self._get_heat_resource_info(
                        stack_id, resource_name=resource_name)
                elif parent_name != elmt.resource_name:
                    continue
                else:
                    detail_stack = self._get_heat_resource_info(
                        elmt.physical_resource_id, resource_name=resource_name)
                details[resource_name] = detail_stack

        ans_list = list()
        for detail in details.values():
            ans_list.append(detail.attributes['fixed_ips'])

        return ans_list

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
        self._show_vnf_instance(vnf_instance['id'], expected_result)

        self._delete_vnf_instance(vnf_instance['id'])

    def test_list_and_show_vnf_instances(self):
        """Test list vnf instances and show a vnf instance"""

        # Create vnf instance 01 and don't instantiate this one.
        vnf_instance_name = "List-VNF-Instance-0"
        resp, vnf_instance_0 = self._create_vnf_instance(self.vnfd_id_1,
            vnf_instance_name=vnf_instance_name)

        self.assertIsNotNone(vnf_instance_0["id"])
        self.assertEqual(201, resp.status_code)

        self.addCleanup(self._delete_vnf_instance, vnf_instance_0["id"])

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
        self._show_vnf_instance(vid, expected_result)

        # Create vnf instance 02 with 'VNF' as name and instantiate this one.
        # We can verify if vnf instance can be created with 'VNF' name itself.
        vnf_instance_name = "VNF"
        resp, vnf_instance_1 = self._create_vnf_instance(self.vnfd_id_1,
            vnf_instance_name=vnf_instance_name)

        self.assertIsNotNone(vnf_instance_1["id"])
        self.assertEqual(201, resp.status_code)

        request_body = self._instantiate_vnf_request("simple",
            vim_id=self.vim_id)

        self._instantiate_vnf_instance(vnf_instance_1["id"], request_body)
        # Terminate vnf gracefully with graceful timeout set to 60
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.GRACEFUL,
            'gracefulTerminationTimeout': 60
        }

        self.addCleanup(self._delete_vnf_instance, vnf_instance_1["id"])
        self.addCleanup(self._terminate_vnf_instance, vnf_instance_1["id"],
                        terminate_req_body)

        # List vnf instances to check if first one is in NOT_INSTANTIATED
        # state and the second one is INSTANTIATED
        vnf_instances = self._list_vnf_instances()
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
        self._show_vnf_instance(vid, expected_result)

    def test_instantiate_vnf_with_flavour(self):
        """Test instantiation and heal API without instantiation level

        This test will instantiate vnf using flavour. Heal API will be invoked
        by passing vnfcInstanceId parameter in the request body as per SOL002
        HealVnfRequest.
        """

        # Create vnf instance
        vnf_instance_name = "vnf_with_flavour-%s" % uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level and no ext vl"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_1,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        request_body = self._instantiate_vnf_request("simple",
            vim_id=self.vim_id)

        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
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

        self._heal_vnf_instance(vnf_instance, heal_request_body)

        # NOTE(tpatil) Wait for sometime as it takes a while to update
        # vnfcResourceInfo after the stack status becomes UPDATE_COMPLETE.
        # There is no intermediate status set to VNF which can be used here
        # to confirm healing action is completed successfully.
        time.sleep(WAIT_HEAL)

        vnf_instance_current = self._show_vnf_instance(vnf_instance['id'])
        self._verify_vnfc_resource_info(vnf_instance, vnf_instance_current, 1)

        # Terminate vnf gracefully with graceful timeout set to 60
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.GRACEFUL,
            'gracefulTerminationTimeout': 60
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)

        self._delete_vnf_instance(vnf_instance['id'])

    def test_instantiate_vnf_without_vim_connection_info(self):
        """Test instantiation API without vimConnectionInfo"""

        # Create vnf instance
        vnf_instance_name = (
            f'vnf_without_vimConnectionInfo-{uuidutils.generate_uuid()}')
        vnf_instance_description = 'vnf without vimConnectionInfo'
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_1,
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        request_body = self._instantiate_vnf_request('simple', vim_id=None)

        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        vdu_count = len(vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        self.assertEqual(1, vdu_count)
        self.assertEqual(self.vim_id, vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'][0]['computeResource']['vimConnectionId'])

        # Terminate vnf gracefully with graceful timeout set to 60
        terminate_req_body = {
            'terminationType': fields.VnfInstanceTerminationType.GRACEFUL,
            'gracefulTerminationTimeout': 60
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)

        self._delete_vnf_instance(vnf_instance['id'])

    def test_instantiate_vnf_with_instantiation_level(self):
        """Test instantiation and heal API with instantiation level

        This test will instantiate vnf with instantiation level. Heal API
        will be invoked by passing vnfcInstanceId parameter in the request
        body as per SOL002 HealVnfRequest.
        """

        # Create vnf instance
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 2"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_2,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        request_body = self._instantiate_vnf_request("simple",
                instantiation_level_id="instantiation_level_2",
                vim_id=self.vim_id)

        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
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

        self._heal_vnf_instance(vnf_instance, heal_request_body)

        # NOTE(tpatil) Wait for sometime as it takes a while to update
        # vnfcResourceInfo after the stack status becomes UPDATE_COMPLETE.
        # There is no intermediate status set to VNF which can be used here
        # to confirm healing action is completed successfully.
        time.sleep(WAIT_HEAL)

        vnf_instance_current = self._show_vnf_instance(vnf_instance['id'])
        self._verify_vnfc_resource_info(vnf_instance, vnf_instance_current, 3)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)

        self._delete_vnf_instance(vnf_instance['id'])

    def test_instantiate_vnf_with_ext_vl_and_ext_managed_vl(self):
        """Test instantiation vnf with external virtual links

        This test will instantiate vnf with external virtual links and
        external managed virtual links. Heal API will be invoked by
        passing vnfcInstanceId parameter in the request body as per SOL002
        HealVnfRequest.
        """

        # Create vnf instance
        vnf_instance_name = "vnf_with_ext_vl_and_ext_managed_vl-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf_with_ext_vl_and_ext_managed_vl"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_3,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

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

        network_uuid = self._create_network(neutron_client,
                                            "external_network")
        self._create_subnet(neutron_client, network_uuid)
        port_uuid = self._create_port(neutron_client, network_uuid)
        ext_vl = get_external_virtual_links(net0_id, net_mgmt_id,
                                            port_uuid)

        request_body = self._instantiate_vnf_request("simple",
            vim_id=self.vim_id, ext_vl=ext_vl, ext_managed_vl=ext_managed_vl)

        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
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

        self._heal_vnf_instance(vnf_instance, heal_request_body)

        # NOTE(tpatil) Wait for sometime as it takes a while to update
        # vnfcResourceInfo after the stack status becomes UPDATE_COMPLETE.
        # There is no intermediate status set to VNF which can be used here
        # to confirm healing action is completed successfully.
        time.sleep(WAIT_HEAL)

        vnf_instance_current = self._show_vnf_instance(vnf_instance['id'])
        self._verify_vnfc_resource_info(vnf_instance, vnf_instance_current, 1)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)

        self._delete_vnf_instance(vnf_instance['id'])

    def test_heal_vnf_sol_003_with_flavour(self):
        """Test heal API as per SOL 003 for VNF created with flavor

        This test will instantiate vnf using flavour. Heal API will be invoked
        as per SOL003 i.e. without passing vnfcInstanceId, so that the entire
        vnf is healed which includes VDU/CP/VL/STORAGE.
        """

        # Create vnf instance
        vnf_instance_name = "heal_vnf_sol_003_with_flavour-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level and no ext vl"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_1,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        request_body = self._instantiate_vnf_request("simple",
            vim_id=self.vim_id)

        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        vdu_count = len(vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        self.assertEqual(1, vdu_count)

        # heal as per SOL003 API check, i.e. without passing vnfcInstanceId in
        # the HealVnfRequest.
        heal_request_body = {
            "cause": "Heal as per SOL003 API check",
        }

        self._heal_sol_003_vnf_instance(vnf_instance, heal_request_body)

        # NOTE(tpatil) Wait for sometime as it takes a while to update
        # vnfcResourceInfo after the stack status becomes UPDATE_COMPLETE.
        # There is no intermediate status set to VNF which can be used here
        # to confirm healing action is completed successfully.
        time.sleep(WAIT_HEAL)

        vnf_instance_current = self._show_vnf_instance(vnf_instance['id'])
        self._verify_vnfc_resource_info(vnf_instance, vnf_instance_current, 1)

        # Terminate vnf gracefully with graceful timeout set to 60
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.GRACEFUL,
            'gracefulTerminationTimeout': 60
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)

        self._delete_vnf_instance(vnf_instance['id'])

    def test_heal_vnf_sol_003_with_instantiation_level(self):
        """Test heal as per SOL003 for VNF created with instantiation level

        This test will instantiate vnf with instantiation level. Heal API will
        be invoked as per SOL003 i.e. without passing vnfcInstanceId, so that
        the entire vnf is healed which includes VDU/CP/VL/STORAGE.
        """

        # Create vnf instance
        vnf_instance_name = "heal_vnf_sol_003_with_instantiation_level-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 2"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_2,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        request_body = self._instantiate_vnf_request("simple",
                instantiation_level_id="instantiation_level_2",
                vim_id=self.vim_id)

        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        vdu_count = len(vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        self.assertEqual(3, vdu_count)

        # heal as per SOL003 API check, i.e. without passing vnfcInstanceId
        # in the HealVnfRequest.
        heal_request_body = {
            "cause": "Heal as per SOL003 API check",
        }

        self._heal_sol_003_vnf_instance(vnf_instance, heal_request_body)

        # NOTE(tpatil) Wait for sometime as it takes a while to update
        # vnfcResourceInfo after the stack status becomes UPDATE_COMPLETE.
        # There is no intermediate status set to VNF which can be used here
        # to confirm healing action is completed successfully.
        time.sleep(WAIT_HEAL)

        vnf_instance_current = self._show_vnf_instance(vnf_instance['id'])
        self._verify_vnfc_resource_info(vnf_instance, vnf_instance_current, 3)

        # Terminate vnf gracefully with graceful timeout set to 60
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.GRACEFUL,
            'gracefulTerminationTimeout': 60
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)

        self._delete_vnf_instance(vnf_instance['id'])

    def test_heal_vnf_sol_003_ext_vl_and_ext_managed_vl(self):
        """Test heal vnf as per SOL003 with vnf created using external vl.

        This test will instantiate vnf with external virtual links and
        external managed virtual links. Heal API will be invoked as per SOL003
        i.e. without passing vnfcInstanceId, so that the entire vnf is healed
        which includes VDU/CP/VL/STORAGE.
        """

        # Create vnf instance
        vnf_instance_name = "vnf_with_ext_vl_and_ext_managed_vl-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf_with_ext_vl_and_ext_managed_vl"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_3,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

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

        network_uuid = self._create_network(neutron_client,
                                            "external_network")
        self._create_subnet(neutron_client, network_uuid)
        port_uuid = self._create_port(neutron_client, network_uuid)
        ext_vl = get_external_virtual_links(net0_id, net_mgmt_id,
                                            port_uuid)

        request_body = self._instantiate_vnf_request("simple",
            vim_id=self.vim_id, ext_vl=ext_vl, ext_managed_vl=ext_managed_vl)

        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        vdu_count = len(vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        self.assertEqual(1, vdu_count)

        # heal as per SOL003 API check, i.e. without passing vnfcInstanceId
        # in the HealVnfRequest.
        heal_request_body = {
            "cause": "Heal as per SOL003 API check",
        }

        self._heal_sol_003_vnf_instance(vnf_instance, heal_request_body)

        # NOTE(tpatil) Wait for sometime as it takes a while to update
        # vnfcResourceInfo after the stack status becomes UPDATE_COMPLETE.
        # There is no intermediate status set to VNF which can be used here
        # to confirm healing action is completed successfully.
        time.sleep(WAIT_HEAL)

        vnf_instance_current = self._show_vnf_instance(vnf_instance['id'])
        self._verify_vnfc_resource_info(vnf_instance, vnf_instance_current, 1)

        # Terminate vnf gracefully with graceful timeout set to 60
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.GRACEFUL,
            'gracefulTerminationTimeout': 60
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)

        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_chgextconn_term(self):
        """Test change external vnf connectivity.

        This test will instantiate vnf with external virtual link and
        change the IP address on virtual link.
        """

        # Create vnf instance
        vnf_instance_name = "vnf_with_ext_vl_and_ext_managed_vl-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf_with_ext_vl_and_ext_managed_vl"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_3,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

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

        network_uuid = self._create_network(neutron_client,
            "external_network")
        subnet_uuid = self._create_subnet(neutron_client, network_uuid)

        # Instantiate vnf
        ext_vl = get_external_virtual_links(
            net0_id, net_mgmt_id, None,
            fixed_addresses=['192.168.120.100'],
            subnet_id=subnet_mgmt_id)

        request_body = self._instantiate_vnf_request("simple",
            vim_id=self.vim_id, ext_vl=ext_vl, ext_managed_vl=ext_managed_vl)

        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        vdu_count = len(vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        self.assertEqual(1, vdu_count)

        # Change external vnf connectivity
        changed_ext_vl = get_external_virtual_links(
            net0_id, network_uuid, None,
            fixed_addresses=['22.22.0.100'],
            subnet_id=subnet_uuid)
        change_ext_conn_req_body = self._change_ext_conn_vnf_request(
            vim_id=self.vim_id, ext_vl=changed_ext_vl)
        before_fixed_ips = self._get_fixed_ips(vnf_instance, request_body)
        self._change_ext_conn_vnf_instance(
            vnf_instance, change_ext_conn_req_body)
        after_fixed_ips = self._get_fixed_ips(vnf_instance, request_body)
        self.assertNotEqual(before_fixed_ips, after_fixed_ips)

        # Get op-occs
        resp, op_occs_info = self._list_op_occs()
        self._assert_occ_list(resp, op_occs_info)

        # Wait for operation state completed
        time.sleep(10)

        # Terminate vnf gracefully with graceful timeout set to 60
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.GRACEFUL,
            'gracefulTerminationTimeout': 60
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)

        self._delete_vnf_instance(vnf_instance['id'])

    def test_update_vnf_instance_not_instantiated(self):
        """Update vnf instance in not_instantiated state."""

        # Create vnf instance
        vnf_instance_name = (
            f"vnf_update_vnf_instance-{uuidutils.generate_uuid()}")
        vnf_instance_description = "vnf_update_vnf_instance"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_1,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance["id"])
        self.assertEqual(201, resp.status_code)

        self.addCleanup(self._delete_vnf_instance, vnf_instance["id"])

        # Update vnf instance
        request_body = {
            "vnfInstanceName": f"{vnf_instance_name}_chg",
            "vnfInstanceDescription":
                f"{vnf_instance_description}_chg",
            "metadata": {"key": "value"}
        }
        resp, _ = self._update_vnf_instance(vnf_instance["id"],
            request_body)

        self.assertEqual(202, resp.status_code)

        expected_result = {
            "instantiationState": fields.VnfInstanceState.NOT_INSTANTIATED,
            "vnfInstanceName": request_body["vnfInstanceName"],
            "vnfInstanceDescription": request_body["vnfInstanceDescription"],
            "metadata": request_body["metadata"]
        }
        self._show_vnf_instance(vnf_instance["id"], expected_result)

    def test_update_vnf_instance_instantiated(self):
        """Update vnf instance in instantiated state."""

        # Create vnf instance
        vnf_instance_name = (
            f"vnf_update_vnf_instance-{uuidutils.generate_uuid()}")
        vnf_instance_description = "vnf_update_vnf_instance"
        resp, vnf_instance = self._create_vnf_instance(self.vnfd_id_1,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self.assertIsNotNone(vnf_instance["id"])
        self.assertEqual(201, resp.status_code)

        self.addCleanup(self._delete_vnf_instance, vnf_instance["id"])

        # Instantiate vnf instance
        request_body = self._instantiate_vnf_request("simple",
            vim_id=self.vim_id)
        self._instantiate_vnf_instance(vnf_instance["id"], request_body)

        # Terminate vnf gracefully with graceful timeout set to 60
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.GRACEFUL,
            "gracefulTerminationTimeout": 60
        }
        self.addCleanup(self._terminate_vnf_instance, vnf_instance["id"],
                        terminate_req_body)

        # Update vnf instance
        vnf_instance = self._show_vnf_instance(vnf_instance["id"])
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

        resp, _ = self._update_vnf_instance(vnf_instance["id"],
            request_body)
        self.assertEqual(202, resp.status_code)

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
        self._show_vnf_instance(vnf_instance["id"], expected_result)
