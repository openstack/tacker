# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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

import ddt
import os
import time

from tacker.tests.functional.sol_v2 import base_v2
from tacker.tests.functional.sol_v2 import paramgen


@ddt.ddt
class VnfLcmTest(base_v2.BaseSolV2Test):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmTest, cls).setUpClass()

        cur_dir = os.path.dirname(__file__)
        # tacker/tests/etc...
        #             /functional/sol_v2
        image_dir = os.path.join(
            cur_dir, "../../etc/samples/etsi/nfv/common/Files/images")
        image_file = "cirros-0.5.2-x86_64-disk.img"
        image_path = os.path.abspath(os.path.join(image_dir, image_file))

        sample1_path = os.path.join(cur_dir, "samples/sample1")
        cls.vnf_pkg_1, cls.vnfd_id_1 = cls.create_vnf_package(
            sample1_path, image_path=image_path)

        sample2_path = os.path.join(cur_dir, "samples/sample2")
        # no image contained
        cls.vnf_pkg_2, cls.vnfd_id_2 = cls.create_vnf_package(sample2_path)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmTest, cls).tearDownClass()

        cls.delete_vnf_package(cls.vnf_pkg_1)
        cls.delete_vnf_package(cls.vnf_pkg_2)

    def setUp(self):
        super(VnfLcmTest, self).setUp()

    def test_api_versions(self):
        """Test version operations

        * About version operations:
          This test includes the following operations.
          - 1. List VNFLCM API versions
          - 2. Show VNFLCM API versions
        """
        path = "/vnflcm/api_versions"
        resp, body = self.tacker_client.do_request(
            path, "GET", version="2.0.0")
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        expected_body = {
            "uriPrefix": "/vnflcm",
            "apiVersions": [
                {'version': '1.3.0', 'isDeprecated': False},
                {'version': '2.0.0', 'isDeprecated': False}
            ]
        }
        self.assertEqual(body, expected_body)

        path = "/vnflcm/v2/api_versions"
        resp, body = self.tacker_client.do_request(
            path, "GET", version="2.0.0")
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        expected_body = {
            "uriPrefix": "/vnflcm/v2",
            "apiVersions": [
                {'version': '2.0.0', 'isDeprecated': False}
            ]
        }
        self.assertEqual(body, expected_body)

    @ddt.data(True, False)
    def test_subscriptions(self, is_all):
        """Test subscription operations

        * About attributes:
          - is_all=True
              All of the following cardinality attributes are set.
              In addition, 0..N or 1..N attributes are set to 2 or more.
              - 0..1 (1)
              - 0..N (2 or more)
              - 1
              - 1..N (2 or more)
          - is_all=False
              Omit except for required attributes.
              Only the following cardinality attributes are set.
              - 1
              - 1..N (1)

        * About subscription operations:
          This test includes the following operations.
          - 0. Pre-setting
          - 1. Create a new subscription
          - 2. Show subscription
          - 3. List subscription with attribute-based filtering
          - 4. Delete a subscription
        """
        # NOTE: Skip notification endpoint testing in subscription creation
        # by setting "v2_nfvo.test_callback_uri = False" to 'tacker.conf'
        # in '.zuul.yaml'.

        # 0. Pre-setting
        sub_req = paramgen.sub2_create()
        if is_all:
            sub_req = paramgen.sub1_create()

        # 1. Create a new subscription
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']

        # 2. Show subscription
        expected_attrs = [
            'id', 'callbackUri', 'verbosity', '_links'
        ]
        if is_all:
            additional_attrs = ['filter']
            expected_attrs.extend(additional_attrs)

        resp, body = self.show_subscription(sub_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 3. List subscription with attribute-based filtering
        filter_expr = {'filter': '(eq,id,%s)' % sub_id}
        resp, body = self.list_subscriptions(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for sbsc in body:
            self.check_resp_body(sbsc, expected_attrs)

        # 4. Delete a subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

    def test_sample1(self):
        """Test LCM operations with all attributes set

        * About attributes:
          All of the following cardinality attributes are set.
          In addition, 0..N or 1..N attributes are set to 2 or more.
          - 0..1 (1)
          - 0..N (2 or more)
          - 1
          - 1..N (2 or more)

        * About LCM operations:
          This test includes the following operations.
          - 0. Pre-setting
          - 1. Create a new VNF instance resource
          - 2. Instantiate a VNF instance
          - 3. Show VNF instance
          - 4. List VNF instance with attribute-based filtering
          - 5. Show VNF LCM operation occurrence
          - 6. List VNF LCM operation occurrence with attribute-based filtering
          - 7. Terminate a VNF instance
          - 8. Delete a VNF instance
        """
        # 0. Pre-setting
        # Create a new network and subnet to check the IP allocation of
        # IPv4 and IPv6
        ft_net0_name = 'ft-net0'
        ft_net0_subs = {
            'ft-ipv4-subnet0': {
                'range': '100.100.100.0/24',
                'ip_version': 4
            },
            'ft-ipv6-subnet0': {
                'range': '1111:2222:3333::/64',
                'ip_version': 6
            }
        }
        ft_net0_id = self.create_network(ft_net0_name)
        self.addCleanup(self.delete_network, ft_net0_id)
        for sub_name, val in ft_net0_subs.items():
            # subnet is automatically deleted with network deletion
            self.create_subnet(
                ft_net0_id, sub_name, val['range'], val['ip_version'])

        net_ids = self.get_network_ids(
            ['net0', 'net1', 'net_mgmt', 'ft-net0'])
        subnet_ids = self.get_subnet_ids(
            ['subnet0', 'subnet1', 'ft-ipv4-subnet0', 'ft-ipv6-subnet0'])

        port_names = ['VDU2_CP1-1', 'VDU2_CP1-2']
        port_ids = {}
        for port_name in port_names:
            port_id = self.create_port(net_ids['net0'], port_name)
            port_ids[port_name] = port_id
            self.addCleanup(self.delete_port, port_id)

        # 1. Create a new VNF instance resource
        # NOTE: extensions and vnfConfigurableProperties are omitted
        # because they are commented out in etsi_nfv_sol001.
        expected_inst_attrs = [
            'id',
            'vnfInstanceName',
            'vnfInstanceDescription',
            'vnfdId',
            'vnfProvider',
            'vnfProductName',
            'vnfSoftwareVersion',
            'vnfdVersion',
            # 'vnfConfigurableProperties', # omitted
            # 'vimConnectionInfo', # omitted
            'instantiationState',
            # 'instantiatedVnfInfo', # omitted
            'metadata',
            # 'extensions', # omitted
            '_links'
        ]
        create_req = paramgen.sample1_create(self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1).get('usageState')
        self.assertEqual('IN_USE', usage_state)

        # 2. Instantiate a VNF instance
        instantiate_req = paramgen.sample1_instantiate(
            net_ids, subnet_ids, port_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check creation of Heat-stack
        stack_name = "vnf-{}".format(inst_id)
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("CREATE_COMPLETE", stack_status)

        # check creation of Glance-image
        image_name_list = ['VDU1-VirtualStorage-image',
                           'VDU2-VirtualStorage-image']
        for image_name in image_name_list:
            image_id = self.get_image_id(image_name)
            self.assertIsNotNone(image_id)

        # check that the servers set in "zone:Affinity" are
        # deployed on 'nova' AZ.
        # NOTE: local_nfvo returns this AZ
        vdu1_details = self.get_server_details('VDU1')
        vdu2_details = self.get_server_details('VDU2')
        vdu1_az = vdu1_details.get('OS-EXT-AZ:availability_zone')
        vdu2_az = vdu2_details.get('OS-EXT-AZ:availability_zone')
        self.assertEqual('nova', vdu1_az)
        self.assertEqual('nova', vdu2_az)

        # 3. Show VNF instance
        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # 4. List VNF instance with attribute-based filtering
        # check attribute-based filtering on VNF instance
        # NOTE: extensions and vnfConfigurableProperties are omitted
        # because they are commented out in etsi_nfv_sol001.
        # * all_fields
        #   -> check the attribute omitted in "exclude_default" is set.
        filter_expr = {'filter': '(eq,id,%s)' % inst_id, 'all_fields': ''}
        resp, body = self.list_vnf_instance(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for inst in body:
            self.assertIsNotNone(inst.get('vnfInstanceName'))
            self.assertIsNotNone(inst.get('vnfInstanceDescription'))
            self.assertIsNotNone(inst.get('vimConnectionInfo'))
            self.assertIsNotNone(inst.get('instantiatedVnfInfo'))
            self.assertIsNotNone(inst.get('metadata'))
        # * fields=<list>
        #   -> check the attribute specified in "fields" is set
        filter_expr = {'filter': '(eq,id,%s)' % inst_id,
                       'fields': 'metadata'}
        resp, body = self.list_vnf_instance(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for inst in body:
            self.assertIsNone(inst.get('vnfInstanceName'))
            self.assertIsNone(inst.get('vnfInstanceDescription'))
            self.assertIsNone(inst.get('vimConnectionInfo'))
            self.assertIsNone(inst.get('instantiatedVnfInfo'))
            self.assertIsNotNone(inst.get('metadata'))
        # * exclude_fields=<list>
        #   -> check the attribute specified in "exclude_fields" is not set
        filter_expr = {'filter': '(eq,id,%s)' % inst_id,
                       'exclude_fields': 'vnfInstanceName'}
        resp, body = self.list_vnf_instance(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for inst in body:
            self.assertIsNone(inst.get('vnfInstanceName'))
            self.assertIsNotNone(inst.get('vnfInstanceDescription'))
            self.assertIsNotNone(inst.get('vimConnectionInfo'))
            self.assertIsNotNone(inst.get('instantiatedVnfInfo'))
            self.assertIsNotNone(inst.get('metadata'))
        # * exclude_default
        #   -> check the attribute omitted in "exclude_default" is not set.
        filter_expr = {'filter': '(eq,id,%s)' % inst_id, 'exclude_default': ''}
        resp, body = self.list_vnf_instance(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for inst in body:
            self.assertIsNotNone(inst.get('vnfInstanceName'))
            self.assertIsNotNone(inst.get('vnfInstanceDescription'))
            self.assertIsNone(inst.get('vimConnectionInfo'))
            self.assertIsNone(inst.get('instantiatedVnfInfo'))
            self.assertIsNone(inst.get('metadata'))

        # 5. Show VNF LCM operation occurrence
        # NOTE: omitted values are not supported at that time
        expected_attrs = [
            'id',
            'operationState',
            'stateEnteredTime',
            'startTime',
            'vnfInstanceId',
            # 'grantId', # omitted
            'operation',
            'isAutomaticInvocation',
            'operationParams',
            'isCancelPending',
            # 'cancelMode', # omitted
            # 'error', # omitted
            'resourceChanges',
            # 'changedInfo', # omitted
            # 'changedExtConnectivity', # omitted
            # 'modificationsTriggeredByVnfPkgChange', # omitted
            # 'vnfSnapshotInfoId', # omitted
            '_links'
        ]
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 6. List VNF LCM operation occurrence with attribute-based filtering
        # check attribute-based filtering on vnf_lcm_op_occs
        # NOTE: error and changedInfo, changedExtConnectivity are omitted
        # because these values are not supported at that time
        # * all_fields
        #   -> check the attribute omitted in "exclude_default" is set.
        filter_expr = {'filter': '(eq,id,%s)' % lcmocc_id, 'all_fields': ''}
        resp, body = self.list_lcmocc(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for lcmocc in body:
            self.assertIsNotNone(lcmocc.get('operationParams'))
            self.assertIsNotNone(lcmocc.get('resourceChanges'))
        # * fields=<list>
        #   -> check the attribute specified in "fields" is set
        filter_expr = {'filter': '(eq,id,%s)' % lcmocc_id,
                       'fields': 'operationParams'}
        resp, body = self.list_lcmocc(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for lcmocc in body:
            self.assertIsNotNone(lcmocc.get('operationParams'))
            self.assertIsNone(lcmocc.get('resourceChanges'))
        # * exclude_fields=<list>
        #   -> check the attribute specified in "exclude_fields" is not set
        filter_expr = {'filter': '(eq,id,%s)' % inst_id,
                       'exclude_fields': 'operationParams'}
        resp, body = self.list_lcmocc(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for lcmocc in body:
            self.assertIsNone(lcmocc.get('operationParams'))
            self.assertIsNotNone(lcmocc.get('resourceChanges'))
        # * exclude_default
        #   -> check the attribute omitted in "exclude_default" is not set.
        filter_expr = {'filter': '(eq,id,%s)' % lcmocc_id,
                       'exclude_default': ''}
        resp, body = self.list_lcmocc(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for lcmocc in body:
            self.assertIsNone(lcmocc.get('operationParams'))
            self.assertIsNone(lcmocc.get('resourceChanges'))

        # 7. Terminate a VNF instance
        terminate_req = paramgen.sample1_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        # check deletion of Heat-stack
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertIsNone(stack_status)

        # check deletion of Glance-image
        for image_name in image_name_list:
            image_id = self.get_image_id(image_name)
            self.assertIsNone(image_id)

        # 8. Delete a VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1).get('usageState')
        self.assertEqual('NOT_IN_USE', usage_state)

    def test_sample2(self):
        """Test LCM operations with omitting except for required attributes

        * About attributes:
          Omit except for required attributes.
          Only the following cardinality attributes are set.
          - 1
          - 1..N (1)

        * About LCM operations:
          This test includes the following operations.
          - 1. Create a new VNF instance resource
          - 2. Instantiate a VNF instance
          - 3. Show VNF instance
          - 4. Terminate a VNF instance
          - 5. Delete a VNF instance
        """
        # 1. Create a new VNF instance resource
        expected_inst_attrs = [
            'id',
            # 'vnfInstanceName', # omitted
            # 'vnfInstanceDescription', # omitted
            'vnfdId',
            'vnfProvider',
            'vnfProductName',
            'vnfSoftwareVersion',
            'vnfdVersion',
            # 'vnfConfigurableProperties', # omitted
            # 'vimConnectionInfo', # omitted
            'instantiationState',
            # 'instantiatedVnfInfo', # omitted
            # 'metadata', # omitted
            # 'extensions', # omitted
            '_links'
        ]
        create_req = paramgen.sample2_create(self.vnfd_id_2)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_2).get('usageState')
        self.assertEqual('IN_USE', usage_state)

        # 2. Instantiate a VNF instance
        instantiate_req = paramgen.sample2_instantiate()
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check creation of Heat-stack
        stack_name = "vnf-{}".format(inst_id)
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("CREATE_COMPLETE", stack_status)

        # check that the servers set in "nfvi_node:Affinity" are
        # deployed on the same host.
        # NOTE: it's up to heat to decide which host to deploy to
        vdu1_details = self.get_server_details('VDU1')
        vdu2_details = self.get_server_details('VDU2')
        vdu1_host = vdu1_details['hostId']
        vdu2_host = vdu2_details['hostId']
        self.assertEqual(vdu1_host, vdu2_host)

        # 3. Show VNF instance
        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # 4. Terminate a VNF instance
        terminate_req = paramgen.sample2_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        # check deletion of Heat-stack
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertIsNone(stack_status)

        # 5. Delete a VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_2).get('usageState')
        self.assertEqual('NOT_IN_USE', usage_state)
