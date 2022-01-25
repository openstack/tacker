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

from tacker.objects import fields
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

        # for basic lcms tests max pattern
        basic_lcms_max_path = os.path.join(cur_dir, "samples/basic_lcms_max")
        cls.vnf_pkg_1, cls.vnfd_id_1 = cls.create_vnf_package(
            basic_lcms_max_path, image_path=image_path)

        # for basic lcms tests min pattern
        basic_lcms_min_path = os.path.join(cur_dir, "samples/basic_lcms_min")
        # no image contained
        cls.vnf_pkg_2, cls.vnfd_id_2 = cls.create_vnf_package(
            basic_lcms_min_path)

        # for update vnf test
        update_vnf_path = os.path.join(cur_dir, "samples/update_vnf")
        # no image contained
        cls.vnf_pkg_3, cls.vnfd_id_3 = cls.create_vnf_package(update_vnf_path)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmTest, cls).tearDownClass()

        cls.delete_vnf_package(cls.vnf_pkg_1)
        cls.delete_vnf_package(cls.vnf_pkg_2)
        cls.delete_vnf_package(cls.vnf_pkg_3)

    def setUp(self):
        super().setUp()

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
              0..1 is set to 1.
              - 0..1 (1)
              - 0..N (2 or more)
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

        # 0. Pre-setting
        callback_url = os.path.join(base_v2.MOCK_NOTIFY_CALLBACK_URL,
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{base_v2.FAKE_SERVER_MANAGER.SERVER_PORT}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_min(callback_uri)
        if is_all:
            sub_req = paramgen.sub_create_max(callback_uri)

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

    def test_basic_lcms_max(self):
        """Test LCM operations with all attributes set

        * About attributes:
          All of the following cardinality attributes are set.
          In addition, 0..N or 1..N attributes are set to 2 or more.
          0..1 is set to 1.
          - 0..1 (1)
          - 0..N (2 or more)
          - 1..N (2 or more)

        * About LCM operations:
          This test includes the following operations.
          - 0. Pre-setting
          - 1. Create subscription
          - 2. Test notification
          - 3. Show subscription
          - 4. List subscriptions with attribute-based filtering
          - 5. Create VNF instance
          - 6. Instantiate VNF
          - 7. Show VNF instance
          - 8. List VNF instance with attribute-based filtering
          - 9. Show VNF LCM operation occurrence
          - 10. List VNF LCM operation occurrence with attribute-based
                filtering
          - 11. Heal VNF(all with omit all parameter)
          - 12. Heal VNF(all with all=True parameter)
          - 13. Scale out operation
          - 14. Show VNF instance
          - 15. Scale in operation
          - 16. Show VNF instance
          - 17. Heal VNF(vnfc)
          - 18. Change external connectivity
          - 19. Show VNF LCM operation occurrence
          - 20. Heal VNF(vnfc with omit all parameter)
          - 21. Heal VNF(vnfc with all=False parameter)
          - 22. Heal VNF(vnfc with all=True parameter)
          - 23. Update VNF
          - 24. Show VNF instance
          - 25. Terminate VNF
          - 26. Delete VNF instance
          - 27. Show VNF instance
          - 28. Delete subscription
          - 29. Show subscription
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

        # Create a new network for change external connectivity
        ft_net1_name = 'ft-net1'
        ft_net1_subs = {
            'ft-ipv4-subnet1': {
                'range': '22.22.22.0/24',
                'ip_version': 4
            },
            'ft-ipv6-subnet1': {
                'range': '1111:2222:4444::/64',
                'ip_version': 6
            }
        }
        ft_net1_id = self.create_network(ft_net1_name)
        self.addCleanup(self.delete_network, ft_net1_id)
        for sub_name, val in ft_net1_subs.items():
            # subnet is automatically deleted with network deletion
            self.create_subnet(
                ft_net1_id, sub_name, val['range'], val['ip_version'])

        net_ids = self.get_network_ids(
            ['net0', 'net1', 'net_mgmt', 'ft-net0', 'ft-net1'])
        subnet_ids = self.get_subnet_ids(
            ['subnet0', 'subnet1', 'ft-ipv4-subnet0', 'ft-ipv6-subnet0',
             'ft-ipv4-subnet1', 'ft-ipv6-subnet1'])

        port_names = ['VDU2_CP1-1', 'VDU2_CP1-2']
        port_ids = {}
        for port_name in port_names:
            port_id = self.create_port(net_ids['net0'], port_name)
            port_ids[port_name] = port_id
            self.addCleanup(self.delete_port, port_id)

        # 1. Create subscription
        callback_url = os.path.join(base_v2.MOCK_NOTIFY_CALLBACK_URL,
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{base_v2.FAKE_SERVER_MANAGER.SERVER_PORT}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_max(callback_uri)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']

        # 2. Test notification
        self.assert_notification_get(callback_url)
        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

        # 3. Show subscription
        expected_attrs = [
            'id', 'callbackUri', 'verbosity', '_links', 'filter'
        ]

        resp, body = self.show_subscription(sub_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 4. List subscription with attribute-based filtering
        filter_expr = {'filter': f'(eq,id,{sub_id})'}
        resp, body = self.list_subscriptions(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for sbsc in body:
            self.check_resp_body(sbsc, expected_attrs)

        # 5. Create VNF instance
        # ETSI NFV SOL003 v3.3.1 5.5.2.2 VnfInstance
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
        create_req = paramgen.create_vnf_max(self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 6. Instantiate VNF instance
        instantiate_req = paramgen.instantiate_vnf_max(
            net_ids, subnet_ids, port_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 7. Show VNF instance
        # check creation of Heat-stack
        stack_name = f'vnf-{inst_id}'
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

        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.INSTANTIATED,
                         body['instantiationState'])

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # 8. List VNF instance with attribute-based filtering
        # check attribute-based filtering on VNF instance
        # NOTE: extensions and vnfConfigurableProperties are omitted
        # because they are commented out in etsi_nfv_sol001.
        # * all_fields
        #   -> check the attribute omitted in "exclude_default" is set.
        filter_expr = {'filter': f'(eq,id,{inst_id})', 'all_fields': ''}
        resp, body = self.list_vnf_instance(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for inst in body:
            self.assertIn('vnfInstanceName', inst)
            self.assertIn('vnfInstanceDescription', inst)
            self.assertIn('vimConnectionInfo', inst)
            self.assertIn('instantiatedVnfInfo', inst)
            self.assertIn('metadata', inst)
        # * fields=<list>
        #   -> check the attribute specified in "fields" is set
        filter_expr = {'filter': f'(eq,id,{inst_id})',
                       'fields': 'metadata'}
        resp, body = self.list_vnf_instance(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for inst in body:
            self.assertNotIn('vnfInstanceName', inst)
            self.assertNotIn('vnfInstanceDescription', inst)
            self.assertNotIn('vimConnectionInfo', inst)
            self.assertNotIn('instantiatedVnfInfo', inst)
            self.assertIn('metadata', inst)
        # * exclude_fields=<list>
        #   -> check the attribute specified in "exclude_fields" is not set
        filter_expr = {'filter': f'(eq,id,{inst_id})',
                       'exclude_fields': 'vnfInstanceName'}
        resp, body = self.list_vnf_instance(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for inst in body:
            self.assertNotIn('vnfInstanceName', inst)
            self.assertIn('vnfInstanceDescription', inst)
            self.assertIn('vimConnectionInfo', inst)
            self.assertIn('instantiatedVnfInfo', inst)
            self.assertIn('metadata', inst)
        # * exclude_default
        #   -> check the attribute omitted in "exclude_default" is not set.
        filter_expr = {'filter': f'(eq,id,{inst_id})', 'exclude_default': ''}
        resp, body = self.list_vnf_instance(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for inst in body:
            self.assertIn('vnfInstanceName', inst)
            self.assertIn('vnfInstanceDescription', inst)
            self.assertNotIn('vimConnectionInfo', inst)
            self.assertNotIn('instantiatedVnfInfo', inst)
            self.assertNotIn('metadata', inst)

        # 9. Show VNF LCM operation occurrence
        # ETSI NFV SOL003 v3.3.1 5.5.2.13 VnfLcmOpOcc
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

        # 10. List VNF LCM operation occurrence with attribute-based filtering
        # check attribute-based filtering on vnf_lcm_op_occs
        # NOTE: error and changedInfo, changedExtConnectivity are omitted
        # because these values are not supported at that time
        # * all_fields
        #   -> check the attribute omitted in "exclude_default" is set.
        filter_expr = {'filter': f'(eq,id,{lcmocc_id})', 'all_fields': ''}
        resp, body = self.list_lcmocc(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for lcmocc in body:
            self.assertIn('operationParams', lcmocc)
            self.assertIn('resourceChanges', lcmocc)
        # * fields=<list>
        #   -> check the attribute specified in "fields" is set
        filter_expr = {'filter': f'(eq,id,{lcmocc_id})',
                       'fields': 'operationParams'}
        resp, body = self.list_lcmocc(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for lcmocc in body:
            self.assertIn('operationParams', lcmocc)
            self.assertNotIn('resourceChanges', lcmocc)
        # * exclude_fields=<list>
        #   -> check the attribute specified in "exclude_fields" is not set
        filter_expr = {'filter': f'(eq,id,{inst_id})',
                       'exclude_fields': 'operationParams'}
        resp, body = self.list_lcmocc(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for lcmocc in body:
            self.assertNotIn('operationParams', lcmocc)
            self.assertIn('resourceChanges', lcmocc)
        # * exclude_default
        #   -> check the attribute omitted in "exclude_default" is not set.
        filter_expr = {'filter': f'(eq,id,{lcmocc_id})',
                       'exclude_default': ''}
        resp, body = self.list_lcmocc(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for lcmocc in body:
            self.assertNotIn('operationParams', lcmocc)
            self.assertNotIn('resourceChanges', lcmocc)

        # 11. Heal VNF(all with omit all parameter)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2'])]
        vdu1_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]

        heal_req = paramgen.heal_vnf_all_max_with_parameter()
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2'])]
        vdu1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]

        self.assertEqual("CREATE_COMPLETE",
            vdu1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            vdu2_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu1_stack_before_heal['physical_resource_id'],
            vdu1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(vdu2_stack_before_heal['physical_resource_id'],
            vdu2_stack_after_heal['physical_resource_id'])

        # 12. Heal VNF(all with all=True parameter)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2', 'VDU1-VirtualStorage',
            'VDU2-VirtualStorage', 'internalVL3'])]
        vdu1_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]
        storage1_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1-VirtualStorage')][0]
        storage2_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2-VirtualStorage')][0]
        network_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'internalVL3')][0]

        stack_id_before_heal = self.heat_client.get_stack_resource(stack_name)[
            'stack']['id']
        heal_req = paramgen.heal_vnf_all_max_with_parameter(True)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_id_after_heal = self.heat_client.get_stack_resource(stack_name)[
            'stack']['id']
        self.assertNotEqual(stack_id_before_heal, stack_id_after_heal)
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("CREATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2', 'VDU1-VirtualStorage',
            'VDU2-VirtualStorage', 'internalVL3'])]
        vdu1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]
        storage1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1-VirtualStorage')][0]
        storage2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2-VirtualStorage')][0]
        network_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'internalVL3')][0]

        self.assertEqual("CREATE_COMPLETE",
            vdu1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            vdu2_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            storage1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            storage2_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            network_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu1_stack_before_heal['physical_resource_id'],
            vdu1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(vdu2_stack_before_heal['physical_resource_id'],
            vdu2_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(storage1_stack_before_heal['physical_resource_id'],
            storage1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(storage2_stack_before_heal['physical_resource_id'],
            storage2_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(network_stack_before_heal['physical_resource_id'],
            network_stack_after_heal['physical_resource_id'])

        # 13. Scale out operation
        # get nested stack count before scale out
        nested_stacks = self.heat_client.get_resources(stack_name)
        count_before_scaleout = len(nested_stacks)
        scaleout_req = paramgen.scaleout_vnf_max()
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 14. Show VNF instance
        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # check scaleStatus
        scale_status = body['instantiatedVnfInfo']['scaleStatus']
        self.assertGreater(len(scale_status), 0)
        for status in scale_status:
            self.assertIn('aspectId', status)
            self.assertIn('scaleLevel', status)

        # check creation of Heat-stack
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        # get nested stack count after scale out
        nested_stacks = self.heat_client.get_resources(stack_name)
        count_after_scaleout = len(nested_stacks)
        # check nested stack was created
        # 9 was the sum of 1 VM, 1 Volume, 1 VolumeType, 5 CPs,
        # 1 stack(VDU1.yaml)
        self.assertEqual(9, count_after_scaleout - count_before_scaleout)

        # 15. Scale in operation
        scalein_req = paramgen.scalein_vnf_max()
        resp, body = self.scale_vnf_instance(inst_id, scalein_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 16. Show VNF instance
        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # check scaleStatus
        scale_status = body['instantiatedVnfInfo']['scaleStatus']
        self.assertGreater(len(scale_status), 0)
        for status in scale_status:
            self.assertIn('aspectId', status)
            self.assertIn('scaleLevel', status)

        # check creation of Heat-stack
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        # get nested stack count after scale in
        nested_stacks = self.heat_client.get_resources(stack_name)
        count_after_scalein = len(nested_stacks)
        # check nested stack was deleted
        # 9 was the sum of 1 VM, 1 Volume, 1 VolumeType, 5 CPs,
        # 1 stack(VDU1.yaml)
        self.assertEqual(9, count_after_scaleout - count_after_scalein)

        # 17. Heal VNF(vnfc)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] == 'VDU2')]
        vdu2_stack_before_heal = temp_stacks[0]

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        vnfc_info = body['instantiatedVnfInfo']['vnfcInfo']
        self.assertGreater(len(vnfc_info), 1)
        vnfc_id = [vnfc['id'] for vnfc in vnfc_info if (
            "VDU2" == vnfc['vduId'])][0]
        self.assertIsNotNone(vnfc_id)

        heal_req = paramgen.heal_vnf_vnfc_max(vnfc_id)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check stack info
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] == 'VDU2')]
        vdu2_stack_after_heal = temp_stacks[0]

        self.assertEqual("CREATE_COMPLETE",
            vdu2_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu2_stack_before_heal['physical_resource_id'],
            vdu2_stack_after_heal['physical_resource_id'])

        # 18. Change external connectivity
        nested_stacks = self.heat_client.get_resources(stack_name)
        for stack in nested_stacks:
            if stack['resource_type'] == 'VDU1.yaml':
                stack_id_1 = stack['physical_resource_id']
            if stack['resource_name'] == 'VDU1_CP1':
                links = stack['links']
                for link in links:
                    if link['rel'] == 'self':
                        href = link['href']
                        stack_name_1 = href.split("/")[7]
                        break

        port_info = self.heat_client.get_resource_info(
            f"{stack_name_1}/{stack_id_1}", 'VDU1_CP1')
        before_physical_resource_id_1 = port_info['physical_resource_id']
        before_fixed_ips_1 = port_info['attributes']['fixed_ips']

        stack_id_2 = self.heat_client.get_stack_resource(stack_name)['stack'][
            'id']
        port_info = self.heat_client.get_resource_info(
            f"{stack_name}/{stack_id_2}", 'VDU2_CP2')
        before_physical_resource_id_2 = port_info['physical_resource_id']
        before_fixed_ips_2 = port_info['attributes']['fixed_ips']

        change_ext_conn_req = paramgen.change_ext_conn_max(net_ids, subnet_ids,
            self.auth_url)
        resp, body = self.change_ext_conn(inst_id, change_ext_conn_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        port_info = self.heat_client.get_resource_info(
            f"{stack_name_1}/{stack_id_1}", 'VDU1_CP1')
        after_physical_resource_id_1 = port_info['physical_resource_id']
        after_fixed_ips_1 = port_info['attributes']['fixed_ips']

        stack_id_2 = self.heat_client.get_stack_resource(stack_name)['stack'][
            'id']
        port_info = self.heat_client.get_resource_info(
            f"{stack_name}/{stack_id_2}", 'VDU2_CP2')
        after_physical_resource_id_2 = port_info['physical_resource_id']
        after_fixed_ips_2 = port_info['attributes']['fixed_ips']

        self.assertNotEqual(before_physical_resource_id_1,
            after_physical_resource_id_1)
        self.assertNotEqual(before_fixed_ips_1, after_fixed_ips_1)
        self.assertNotEqual(before_physical_resource_id_2,
            after_physical_resource_id_2)
        self.assertNotEqual(before_fixed_ips_2, after_fixed_ips_2)

        # 19. Show VNF LCM operation occurrence
        # ETSI NFV SOL003 v3.3.1 5.5.2.13 VnfLcmOpOcc
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

        # 20. Heal VNF(vnfc with omit all parameter)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2'])]
        vdu1_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        vnfc_info = body['instantiatedVnfInfo']['vnfcInfo']
        self.assertGreater(len(vnfc_info), 1)
        vnfc_ids = [vnfc['id'] for vnfc in vnfc_info]

        heal_req = paramgen.heal_vnf_vnfc_max_with_parameter(vnfc_ids)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check stack info
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2'])]
        vdu1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]

        self.assertEqual("CREATE_COMPLETE",
            vdu1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            vdu2_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu1_stack_before_heal['physical_resource_id'],
            vdu1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(vdu2_stack_before_heal['physical_resource_id'],
            vdu2_stack_after_heal['physical_resource_id'])

        # 21. Heal VNF(vnfc with all=False parameter)
        vdu1_stack_before_heal = vdu1_stack_after_heal
        vdu2_stack_before_heal = vdu2_stack_after_heal
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        vnfc_info = body['instantiatedVnfInfo']['vnfcInfo']
        self.assertGreater(len(vnfc_info), 1)
        vnfc_ids = [vnfc['id'] for vnfc in vnfc_info]

        heal_req = paramgen.heal_vnf_vnfc_max_with_parameter(vnfc_ids, False)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check stack info
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2'])]
        vdu1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]

        self.assertEqual("CREATE_COMPLETE",
            vdu1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            vdu2_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu1_stack_before_heal['physical_resource_id'],
            vdu1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(vdu2_stack_before_heal['physical_resource_id'],
            vdu2_stack_after_heal['physical_resource_id'])

        # 22. Heal VNF(vnfc with all=True parameter)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2', 'VDU1-VirtualStorage',
            'VDU2-VirtualStorage'])]
        vdu1_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]
        storage1_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1-VirtualStorage')][0]
        storage2_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2-VirtualStorage')][0]

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        vnfc_info = body['instantiatedVnfInfo']['vnfcInfo']
        self.assertGreater(len(vnfc_info), 1)
        vnfc_ids = [vnfc['id'] for vnfc in vnfc_info]

        heal_req = paramgen.heal_vnf_vnfc_max_with_parameter(vnfc_ids, True)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check stack info
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2', 'VDU1-VirtualStorage',
            'VDU2-VirtualStorage'])]
        vdu1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]
        storage1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1-VirtualStorage')][0]
        storage2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2-VirtualStorage')][0]

        self.assertEqual("CREATE_COMPLETE",
            vdu1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            vdu2_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            storage1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            storage2_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu1_stack_before_heal['physical_resource_id'],
            vdu1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(vdu2_stack_before_heal['physical_resource_id'],
            vdu2_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(storage1_stack_before_heal['physical_resource_id'],
            storage1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(storage2_stack_before_heal['physical_resource_id'],
            storage2_stack_after_heal['physical_resource_id'])

        # 23. Update VNF
        # check attribute value before update VNF
        # check usageState of VNF Package 1
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check usageState of VNF Package 3
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

        # check vnfd id
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(self.vnfd_id_1, body['vnfdId'])

        # check vnfc info
        vnfc_info = body['instantiatedVnfInfo']['vnfcInfo']
        self.assertGreater(len(vnfc_info), 1)
        vnfc_ids = [vnfc['id'] for vnfc in vnfc_info]
        for vnfc in vnfc_info:
            self.assertIn('id', vnfc)
            self.assertIn('vduId', vnfc)
            self.assertIsNotNone(vnfc.get('vnfcState'))
            self.assertIsNone(vnfc.get('vnfcConfigurableProperties'))

        update_req = paramgen.update_vnf_max(self.vnfd_id_3, vnfc_ids)
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 24. Show VNF instance
        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # check usageState of VNF Package 1
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

        # check usageState of VNF Package 3
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check the specified attribute after update VNF
        self.assertEqual(self.vnfd_id_3, body['vnfdId'])
        self.assertEqual('new name', body['vnfInstanceName'])
        self.assertEqual('new description', body['vnfInstanceDescription'])
        dummy_key_value = {'dummy-key': 'dummy-value'}
        self.assertEqual(dummy_key_value, body['metadata'])
        self.assertEqual(dummy_key_value, body['extensions'])
        self.assertEqual(dummy_key_value, body['vnfConfigurableProperties'])
        vim_connection_info = {
            "vim2": {
                "vimId": "ac2d2ece-5e49-4b15-b92d-b681e9c096d8",
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                "interfaceInfo": {
                    "endpoint": "http://127.0.0.1/identity/v3"
                },
                "accessInfo": {
                    "username": "dummy_user",
                    "region": "RegionOne",
                    "project": "dummy_project",
                    "projectDomain": "Default",
                    "userDomain": "Default"
                },
                "extra": {
                    "dummy-key": "dummy-val"
                }
            }
        }
        self.assertEqual(vim_connection_info['vim2'],
            body['vimConnectionInfo']['vim2'])

        # check vnfc info
        vnfc_info = body['instantiatedVnfInfo']['vnfcInfo']
        self.assertEqual(vnfc_ids[0], vnfc_info[0]['id'])
        self.assertEqual(vnfc_ids[1], vnfc_info[1]['id'])
        self.assertEqual(dummy_key_value,
            vnfc_info[0]['vnfcConfigurableProperties'])
        self.assertEqual(dummy_key_value,
            vnfc_info[1]['vnfcConfigurableProperties'])

        # 25. Terminate VNF
        terminate_req = paramgen.terminate_vnf_max()
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

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 26. Delete VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 27. Show VNF instance
        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

        # 28. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 29. Show subscription
        resp, body = self.show_subscription(sub_id)
        self.assertEqual(404, resp.status_code)

    def test_basic_lcms_min(self):
        """Test LCM operations with omitting except for required attributes

        The change_ext_conn can't be tested here because VNF package 2 don't
        have external connectivity. So moved it to the test_scale_other_lcm().

        * About attributes:
          Omit except for required attributes.
          Only the following cardinality attributes are set.
          - 1
          - 1..N (1)

        * About LCM operations:
          This test includes the following operations.
          - 1. Create subscription
          - 2. Test notification
          - 3. Create VNF instance
          - 4. Instantiate VNF
          - 5. Show VNF instance
          - 6. Heal VNF(all with omit all parameter)
          - 7. Show VNF instance
          - 8. Update VNF
          - 9. Heal VNF(vnfc)
          - 10. Show VNF instance
          - 11. Scale out operation
          - 12. Show VNF instance
          - 13. Scale in operation
          - 14. Terminate VNF
          - 15. Delete VNF instance
          - 16. Delete subscription
          - 17. Show subscription
        """
        # 1. Create subscription
        callback_url = os.path.join(base_v2.MOCK_NOTIFY_CALLBACK_URL,
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{base_v2.FAKE_SERVER_MANAGER.SERVER_PORT}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_min(callback_uri)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']

        # 2. Test notification
        self.assert_notification_get(callback_url)
        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_2)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

        # 3. Create VNF instance
        # ETSI NFV SOL003 v3.3.1 5.5.2.2 VnfInstance
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
        create_req = paramgen.create_vnf_min(self.vnfd_id_2)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_2)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 4. Instantiate VNF
        instantiate_req = paramgen.instantiate_vnf_min()
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check creation of Heat-stack
        stack_name = f'vnf-{inst_id}'
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

        # 5. Show VNF instance
        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.INSTANTIATED,
                         body['instantiationState'])

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # 6. Heal VNF(all with omit all parameter)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2'])]
        vdu1_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]

        heal_req = paramgen.heal_vnf_all_min()
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2'])]
        vdu1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]

        self.assertEqual("CREATE_COMPLETE",
            vdu1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            vdu2_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu1_stack_before_heal['physical_resource_id'],
            vdu1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(vdu2_stack_before_heal['physical_resource_id'],
            vdu2_stack_after_heal['physical_resource_id'])

        # 7. Show VNF instance
        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.INSTANTIATED,
                         body['instantiationState'])

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # check usageState of VNF Package 2
        usage_state = self.get_vnf_package(self.vnf_pkg_2)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check usageState of VNF Package 3
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

        # check vnfd id
        self.assertEqual(self.vnfd_id_2, body['vnfdId'])

        # 8. Update VNF
        update_req = paramgen.update_vnf_min_with_parameter(self.vnfd_id_3)
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check usageState of VNF Package 2
        usage_state = self.get_vnf_package(self.vnf_pkg_2)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

        # check usageState of VNF Package 3
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check vnfd id
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(self.vnfd_id_3, body['vnfdId'])

        # 9. Heal VNF(vnfc)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] == 'VDU2')]
        vdu2_stack_before_heal = temp_stacks[0]

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        vnfc_info = body['instantiatedVnfInfo']['vnfcInfo']
        self.assertGreater(len(vnfc_info), 1)
        vnfc_id = [vnfc['id'] for vnfc in vnfc_info if (
            "VDU2" == vnfc['vduId'])][0]
        self.assertIsNotNone(vnfc_id)

        heal_req = paramgen.heal_vnf_vnfc_min(vnfc_id)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] == 'VDU2')]
        vdu2_stack_after_heal = temp_stacks[0]

        self.assertEqual("CREATE_COMPLETE",
            vdu2_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu2_stack_before_heal['physical_resource_id'],
            vdu2_stack_after_heal['physical_resource_id'])

        # 10. Show VNF instance
        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # check usageState of VNF Package 3
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # 11. Scale out operation
        # get nested stack count before scaleout
        nested_stacks = self.heat_client.get_resources(stack_name)
        count_before_scaleout = len(nested_stacks)
        scaleout_req = paramgen.scaleout_vnf_min()
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 12. Show VNF instance
        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # get nested stack count after scale out
        nested_stacks = self.heat_client.get_resources(stack_name)
        count_after_scaleout = len(nested_stacks)
        # check nested stack was created
        # 3 was the sum of 1 VM, 1 CP, 1 stack(VDU1.yaml)
        self.assertEqual(3, count_after_scaleout - count_before_scaleout)

        # 13. Scale in operation
        scalein_req = paramgen.scalein_vnf_min()
        resp, body = self.scale_vnf_instance(inst_id, scalein_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # get nested stack count after scale in
        nested_stacks = self.heat_client.get_resources(stack_name)
        count_after_scalein = len(nested_stacks)
        # check nested stack was deleted
        # 3 was the sum of 1 VM, 1 CP, 1 stack(VDU1.yaml)
        self.assertEqual(3, count_after_scaleout - count_after_scalein)

        # 14. Terminate a VNF instance
        terminate_req = paramgen.terminate_vnf_min()
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

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 15. Delete a VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

        # 16. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 17. Show subscription
        resp, body = self.show_subscription(sub_id)
        self.assertEqual(404, resp.status_code)

    def test_update_scale_lcm(self):
        """Test the sequence of update VNF and scale out

        * About attributes:
          All of the following cardinality attributes are set.
          In addition, 0..N or 1..N attributes are set to 2 or more.
          0..1 is set to 1.
          - 0..1 (1)
          - 0..N (2 or more)
          - 1..N (2 or more)

        * About LCM operations:
          This test includes the following operations.
          - 0. Pre-setting
          - 1. Create subscription
          - 2. Create VNF instance
          - 3. Instantiate VNF
          - 4. Show VNF instance
          - 5. Update VNF
          - 6. Show VNF instance
          - 7. Scale out operation
          - 8. Terminate VNF
          - 9. Delete VNF instance
          - 10. Delete subscription
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

        # 1. Create subscription
        callback_url = os.path.join(base_v2.MOCK_NOTIFY_CALLBACK_URL,
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{base_v2.FAKE_SERVER_MANAGER.SERVER_PORT}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_max(callback_uri)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']

        # 2. Create VNF instance
        # ETSI NFV SOL003 v3.3.1 5.5.2.2 VnfInstance
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
        create_req = paramgen.create_vnf_max(self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 3. Instantiate VNF instance
        instantiate_req = paramgen.instantiate_vnf_max(
            net_ids, subnet_ids, port_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 4. Show VNF instance
        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.INSTANTIATED,
                         body['instantiationState'])

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # 5. Update VNF
        # check attribute value before update VNF
        # check usageState of VNF Package 1
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check usageState of VNF Package 3
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

        # check vnfd id
        self.assertEqual(self.vnfd_id_1, body['vnfdId'])

        # check vnfc info
        vnfc_info = body['instantiatedVnfInfo']['vnfcInfo']
        self.assertGreater(len(vnfc_info), 1)
        vnfc_ids = [vnfc['id'] for vnfc in vnfc_info]
        for vnfc in vnfc_info:
            self.assertIn('id', vnfc)
            self.assertIn('vduId', vnfc)
            self.assertIsNotNone(vnfc.get('vnfcState'))
            self.assertIsNone(vnfc.get('vnfcConfigurableProperties'))

        update_req = paramgen.update_vnf_max(self.vnfd_id_3, vnfc_ids)
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 6. Show VNF instance
        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # check usageState of VNF Package 1
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

        # check usageState of VNF Package 3
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check the specified attribute after update VNF
        self.assertEqual(self.vnfd_id_3, body['vnfdId'])
        self.assertEqual('new name', body['vnfInstanceName'])
        self.assertEqual('new description', body['vnfInstanceDescription'])
        dummy_key_value = {'dummy-key': 'dummy-value'}
        self.assertEqual(dummy_key_value, body['metadata'])
        self.assertEqual(dummy_key_value, body['extensions'])
        self.assertEqual(dummy_key_value, body['vnfConfigurableProperties'])
        vim_connection_info = {
            "vim2": {
                "vimId": "ac2d2ece-5e49-4b15-b92d-b681e9c096d8",
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                "interfaceInfo": {
                    "endpoint": "http://127.0.0.1/identity/v3"
                },
                "accessInfo": {
                    "username": "dummy_user",
                    "region": "RegionOne",
                    "project": "dummy_project",
                    "projectDomain": "Default",
                    "userDomain": "Default"
                },
                "extra": {
                    "dummy-key": "dummy-val"
                }
            }
        }
        self.assertEqual(vim_connection_info['vim2'],
            body['vimConnectionInfo']['vim2'])

        # check vnfc info
        vnfc_info = body['instantiatedVnfInfo']['vnfcInfo']
        self.assertEqual(vnfc_ids[0], vnfc_info[0]['id'])
        self.assertEqual(vnfc_ids[1], vnfc_info[1]['id'])
        self.assertEqual(dummy_key_value,
            vnfc_info[0]['vnfcConfigurableProperties'])
        self.assertEqual(dummy_key_value,
            vnfc_info[1]['vnfcConfigurableProperties'])

        # 7. Scale out operation
        scaleout_req = paramgen.scaleout_vnf_max()
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 8. Terminate a VNF instance
        terminate_req = paramgen.terminate_vnf_max()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 9. Delete a VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 10. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

    def test_update_heal_lcm(self):
        """Test the sequence of update VNF and heal VNF

        * About attributes:
          All of the following cardinality attributes are set.
          In addition, 0..N or 1..N attributes are set to 2 or more.
          0..1 is set to 1.
          - 0..1 (1)
          - 0..N (2 or more)
          - 1..N (2 or more)

        * About LCM operations:
          This test includes the following operations.
          - 0. Pre-setting
          - 1. Create subscription
          - 2. Create VNF instance
          - 3. Instantiate VNF
          - 4. Show VNF instance
          - 5. Update VNF
          - 6. Show VNF instance
          - 7. Heal VNF(all with omit all parameter)
          - 8. Heal VNF(all with all=False parameter)
          - 9. Heal VNF(all with all=True parameter)
          - 10. Terminate VNF
          - 11. Delete VNF instance
          - 12. Delete subscription
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

        # 1. Create subscription
        callback_url = os.path.join(base_v2.MOCK_NOTIFY_CALLBACK_URL,
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{base_v2.FAKE_SERVER_MANAGER.SERVER_PORT}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_max(callback_uri)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']

        # 2. Create VNF instance
        # ETSI NFV SOL003 v3.3.1 5.5.2.2 VnfInstance
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
        create_req = paramgen.create_vnf_max(self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 3. Instantiate VNF instance
        instantiate_req = paramgen.instantiate_vnf_max(
            net_ids, subnet_ids, port_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 4. Show VNF instance
        # check creation of Heat-stack
        stack_name = f'vnf-{inst_id}'
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("CREATE_COMPLETE", stack_status)

        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.INSTANTIATED,
                         body['instantiationState'])

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # 5. Update VNF
        # check attribute value before update VNF
        # check usageState of VNF Package 1
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check usageState of VNF Package 3
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

        # check vnfd id
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(self.vnfd_id_1, body['vnfdId'])

        # check vnfc info
        vnfc_info = body['instantiatedVnfInfo']['vnfcInfo']
        self.assertGreater(len(vnfc_info), 1)
        vnfc_ids = [vnfc['id'] for vnfc in vnfc_info]
        for vnfc in vnfc_info:
            self.assertIn('id', vnfc)
            self.assertIn('vduId', vnfc)
            self.assertIsNotNone(vnfc.get('vnfcState'))
            self.assertIsNone(vnfc.get('vnfcConfigurableProperties'))

        update_req = paramgen.update_vnf_max(self.vnfd_id_3, vnfc_ids)
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 6. Show VNF instance
        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # check usageState of VNF Package 1
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

        # check usageState of VNF Package 3
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check the specified attribute after update VNF
        self.assertEqual(self.vnfd_id_3, body['vnfdId'])
        self.assertEqual('new name', body['vnfInstanceName'])
        self.assertEqual('new description', body['vnfInstanceDescription'])
        dummy_key_value = {'dummy-key': 'dummy-value'}
        self.assertEqual(dummy_key_value, body['metadata'])
        self.assertEqual(dummy_key_value, body['extensions'])
        self.assertEqual(dummy_key_value, body['vnfConfigurableProperties'])
        vim_connection_info = {
            "vim2": {
                "vimId": "ac2d2ece-5e49-4b15-b92d-b681e9c096d8",
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                "interfaceInfo": {
                    "endpoint": "http://127.0.0.1/identity/v3"
                },
                "accessInfo": {
                    "username": "dummy_user",
                    "region": "RegionOne",
                    "project": "dummy_project",
                    "projectDomain": "Default",
                    "userDomain": "Default"
                },
                "extra": {
                    "dummy-key": "dummy-val"
                }
            }
        }
        self.assertEqual(vim_connection_info['vim2'],
            body['vimConnectionInfo']['vim2'])

        # check vnfc info
        vnfc_info = body['instantiatedVnfInfo']['vnfcInfo']
        self.assertEqual(vnfc_ids[0], vnfc_info[0]['id'])
        self.assertEqual(vnfc_ids[1], vnfc_info[1]['id'])
        self.assertEqual(dummy_key_value,
            vnfc_info[0]['vnfcConfigurableProperties'])
        self.assertEqual(dummy_key_value,
            vnfc_info[1]['vnfcConfigurableProperties'])

        # 7. Heal VNF(all with omit all parameter)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2'])]
        vdu1_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]
        heal_req = paramgen.heal_vnf_all_max_with_parameter()
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2'])]
        vdu1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]

        self.assertEqual("CREATE_COMPLETE",
            vdu1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            vdu2_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu1_stack_before_heal['physical_resource_id'],
            vdu1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(vdu2_stack_before_heal['physical_resource_id'],
            vdu2_stack_after_heal['physical_resource_id'])

        # 8. Heal VNF(all with all=False parameter)
        vdu1_stack_before_heal = vdu1_stack_after_heal
        vdu2_stack_before_heal = vdu2_stack_after_heal
        heal_req = paramgen.heal_vnf_all_max_with_parameter(False)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2'])]
        vdu1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]

        self.assertEqual("CREATE_COMPLETE",
            vdu1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            vdu2_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu1_stack_before_heal['physical_resource_id'],
            vdu1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(vdu2_stack_before_heal['physical_resource_id'],
            vdu2_stack_after_heal['physical_resource_id'])

        # 9. Heal VNF(all with all=True parameter)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2', 'VDU1-VirtualStorage',
            'VDU2-VirtualStorage', 'internalVL3'])]
        vdu1_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]
        storage1_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1-VirtualStorage')][0]
        storage2_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2-VirtualStorage')][0]
        network_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'internalVL3')][0]

        stack_id_before_heal = self.heat_client.get_stack_resource(stack_name)[
            'stack']['id']
        heal_req = paramgen.heal_vnf_all_max_with_parameter(True)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_id_after_heal = self.heat_client.get_stack_resource(stack_name)[
            'stack']['id']
        self.assertNotEqual(stack_id_before_heal, stack_id_after_heal)
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("CREATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2', 'VDU1-VirtualStorage',
            'VDU2-VirtualStorage', 'internalVL3'])]
        vdu1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]
        storage1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1-VirtualStorage')][0]
        storage2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2-VirtualStorage')][0]
        network_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'internalVL3')][0]

        self.assertEqual("CREATE_COMPLETE",
            vdu1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            vdu2_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            storage1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            storage2_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            network_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu1_stack_before_heal['physical_resource_id'],
            vdu1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(vdu2_stack_before_heal['physical_resource_id'],
            vdu2_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(storage1_stack_before_heal['physical_resource_id'],
            storage1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(storage2_stack_before_heal['physical_resource_id'],
            storage2_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(network_stack_before_heal['physical_resource_id'],
            network_stack_after_heal['physical_resource_id'])

        # 10. Terminate VNF
        terminate_req = paramgen.terminate_vnf_max()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 11. Delete VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 12. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

    def test_scale_heal_lcm(self):
        """Test the sequence of scale out/in and heal VNF

        * About attributes:
          All of the following cardinality attributes are set.
          In addition, 0..N or 1..N attributes are set to 2 or more.
          0..1 is set to 1.
          - 0..1 (1)
          - 0..N (2 or more)
          - 1..N (2 or more)

        * About LCM operations:
          This test includes the following operations.
          - 0. Pre-setting
          - 1. Create subscription
          - 2. Create VNF instance
          - 3. Instantiate VNF
          - 4. Show VNF instance
          - 5. Scale out operation
          - 6. Heal VNF(vnfc)
          - 7. Scale out operation
          - 8. Scale in operation
          - 9. Scale in operation
          - 10. Heal VNF(vnfc)
          - 11. Terminate VNF
          - 12. Delete VNF instance
          - 13. Delete subscription
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

        # 1. Create subscription
        callback_url = os.path.join(base_v2.MOCK_NOTIFY_CALLBACK_URL,
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{base_v2.FAKE_SERVER_MANAGER.SERVER_PORT}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_max(callback_uri)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']

        # 2. Create VNF instance
        # ETSI NFV SOL003 v3.3.1 5.5.2.2 VnfInstance
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
        create_req = paramgen.create_vnf_max(self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 3. Instantiate VNF instance
        instantiate_req = paramgen.instantiate_vnf_max(
            net_ids, subnet_ids, port_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 4. Show VNF instance
        # check creation of Heat-stack
        stack_name = f'vnf-{inst_id}'
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("CREATE_COMPLETE", stack_status)

        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo',
            'extensions',
            'vnfConfigurableProperties'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.INSTANTIATED,
                         body['instantiationState'])

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # 5. Scale out operation
        scaleout_req = paramgen.scaleout_vnf_max()
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 6. Heal VNF(vnfc)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] == 'VDU1')]
        vdu1_stack_before_heal = temp_stacks[0]

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        # There was 2 VDU1 because scale out
        vnfc_id = f'VDU1-{vdu1_stack_before_heal["physical_resource_id"]}'

        heal_req = paramgen.heal_vnf_vnfc_max(vnfc_id)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] == 'VDU1')]
        vdu1_stack_after_heal = temp_stacks[0]

        self.assertEqual("CREATE_COMPLETE",
            vdu1_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu1_stack_before_heal['physical_resource_id'],
            vdu1_stack_after_heal['physical_resource_id'])

        # 7. Scale out operation
        scaleout_req = paramgen.scaleout_vnf_max()
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 8. Scale in operation
        scalein_req = paramgen.scalein_vnf_max()
        resp, body = self.scale_vnf_instance(inst_id, scalein_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 9. Scale in operation
        scalein_req = paramgen.scalein_vnf_max()
        resp, body = self.scale_vnf_instance(inst_id, scalein_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 10. Heal VNF(vnfc)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] == 'VDU1')]
        vdu1_stack_before_heal = temp_stacks[0]

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        vnfc_info = body['instantiatedVnfInfo']['vnfcInfo']
        self.assertGreater(len(vnfc_info), 1)
        vnfc_id = [vnfc['id'] for vnfc in vnfc_info if (
            "VDU1" == vnfc['vduId'])][0]
        self.assertIsNotNone(vnfc_id)

        heal_req = paramgen.heal_vnf_vnfc_max(vnfc_id)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] == 'VDU1')]
        vdu1_stack_after_heal = temp_stacks[0]

        self.assertEqual("CREATE_COMPLETE",
            vdu1_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu1_stack_before_heal['physical_resource_id'],
            vdu1_stack_after_heal['physical_resource_id'])

        # 11. Terminate VNF
        terminate_req = paramgen.terminate_vnf_max()
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

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 12. Delete VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 13. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

    def test_scale_other_lcm(self):
        """Test the sequence of scale out/in and the other LCM operations

        The change_ext_conn can't be tested in test_basic_lcms_min method
        because VNF package 2 don't have external connectivity.
        So moved it here to test min pattern change_ext_conn.

        * About attributes:
          All of the following cardinality attributes are set.
          In addition, 0..N or 1..N attributes are set to 2 or more.
          0..1 is set to 1.
          - 0..1 (1)
          - 0..N (2 or more)
          - 1..N (2 or more)

        * About LCM operations:
          This test includes the following operations.
          - 0. Pre-setting
          - 1. Create subscription
          - 2. Create VNF instance
          - 3. Instantiate VNF
          - 4. Show VNF instance
          - 5. Scale out operation
          - 6. Scale out operation
          - 7. Show VNF instance
          - 8. Scale in operation
          - 9. Show VNF instance
          - 10. Heal VNF(all with all=True parameter)
          - 11. Scale in operation
          - 12. Scale out operation
          - 13. Heal VNF(all with all=True parameter)
          - 14. Change external connectivity
          - 15. Show VNF LCM operation occurrence
          - 16. Terminate VNF
          - 17. Delete VNF instance
          - 18. Delete subscription
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

        # Create a new network for change external connectivity
        ft_net1_name = 'ft-net1'
        ft_net1_subs = {
            'ft-ipv4-subnet1': {
                'range': '22.22.22.0/24',
                'ip_version': 4
            },
            'ft-ipv6-subnet1': {
                'range': '1111:2222:4444::/64',
                'ip_version': 6
            }
        }
        ft_net1_id = self.create_network(ft_net1_name)
        self.addCleanup(self.delete_network, ft_net1_id)
        for sub_name, val in ft_net1_subs.items():
            # subnet is automatically deleted with network deletion
            self.create_subnet(
                ft_net1_id, sub_name, val['range'], val['ip_version'])

        net_ids = self.get_network_ids(
            ['net0', 'net1', 'net_mgmt', 'ft-net0', 'ft-net1'])
        subnet_ids = self.get_subnet_ids(
            ['subnet0', 'subnet1', 'ft-ipv4-subnet0', 'ft-ipv6-subnet0',
             'ft-ipv4-subnet1', 'ft-ipv6-subnet1'])

        port_names = ['VDU2_CP1-1', 'VDU2_CP1-2']
        port_ids = {}
        for port_name in port_names:
            port_id = self.create_port(net_ids['net0'], port_name)
            port_ids[port_name] = port_id
            self.addCleanup(self.delete_port, port_id)

        # 1. Create subscription
        callback_url = os.path.join(base_v2.MOCK_NOTIFY_CALLBACK_URL,
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{base_v2.FAKE_SERVER_MANAGER.SERVER_PORT}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_max(callback_uri)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']

        # 2. Create VNF instance
        # ETSI NFV SOL003 v3.3.1 5.5.2.2 VnfInstance
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
        create_req = paramgen.create_vnf_max(self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 3. Instantiate VNF instance
        instantiate_req = paramgen.instantiate_vnf_max(
            net_ids, subnet_ids, port_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 4. Show VNF instance
        # check creation of Heat-stack
        stack_name = f'vnf-{inst_id}'
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("CREATE_COMPLETE", stack_status)

        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo',
            'extensions',
            'vnfConfigurableProperties'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.INSTANTIATED,
                         body['instantiationState'])

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # 5. Scale out operation
        scaleout_req = paramgen.scaleout_vnf_max()
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 6. Scale out operation
        # get nested stack count before scale out
        nested_stacks = self.heat_client.get_resources(stack_name)
        count_before_scaleout = len(nested_stacks)
        scaleout_req = paramgen.scaleout_vnf_max()
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 7. Show VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check scaleStatus
        scale_status = body['instantiatedVnfInfo']['scaleStatus']
        self.assertGreater(len(scale_status), 0)
        for status in scale_status:
            self.assertIn('aspectId', status)
            self.assertIn('scaleLevel', status)

        # check creation of Heat-stack
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        # get nested stack count after scale out
        nested_stacks = self.heat_client.get_resources(stack_name)
        count_after_scaleout = len(nested_stacks)
        # check nested stack was created
        # 9 was the sum of 1 VM, 1 Volume, 1 VolumeType, 5 CPs,
        # 1 stack(VDU1.yaml)
        self.assertEqual(9, count_after_scaleout - count_before_scaleout)

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # 8. Scale in operation
        scalein_req = paramgen.scalein_vnf_max()
        resp, body = self.scale_vnf_instance(inst_id, scalein_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 9. Show VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # check scaleStatus
        scale_status = body['instantiatedVnfInfo']['scaleStatus']
        self.assertGreater(len(scale_status), 0)
        for status in scale_status:
            self.assertIn('aspectId', status)
            self.assertIn('scaleLevel', status)

        # check creation of Heat-stack
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        # get nested stack count after scale in
        nested_stacks = self.heat_client.get_resources(stack_name)
        count_after_scalein = len(nested_stacks)
        # check nested stack was deleted
        # 9 was the sum of 1 VM, 1 Volume, 1 VolumeType, 5 CPs,
        # 1 stack(VDU1.yaml)
        self.assertEqual(9, count_after_scaleout - count_after_scalein)

        # 10. Heal VNF(all with all=True parameter))
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2', 'VDU1-VirtualStorage',
            'VDU2-VirtualStorage', 'internalVL3'])]
        vdu1_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]
        storage1_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1-VirtualStorage')][0]
        storage2_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2-VirtualStorage')][0]
        network_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'internalVL3')][0]

        stack_id_before_heal = self.heat_client.get_stack_resource(stack_name)[
            'stack']['id']
        heal_req = paramgen.heal_vnf_all_max_with_parameter(True)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_id_after_heal = self.heat_client.get_stack_resource(stack_name)[
            'stack']['id']
        self.assertNotEqual(stack_id_before_heal, stack_id_after_heal)
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("CREATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2', 'VDU1-VirtualStorage',
            'VDU2-VirtualStorage', 'internalVL3'])]
        vdu1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]
        storage1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1-VirtualStorage')][0]
        storage2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2-VirtualStorage')][0]
        network_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'internalVL3')][0]

        self.assertEqual("CREATE_COMPLETE",
            vdu1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            vdu2_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            storage1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            storage2_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            network_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu1_stack_before_heal['physical_resource_id'],
            vdu1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(vdu2_stack_before_heal['physical_resource_id'],
            vdu2_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(storage1_stack_before_heal['physical_resource_id'],
            storage1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(storage2_stack_before_heal['physical_resource_id'],
            storage2_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(network_stack_before_heal['physical_resource_id'],
            network_stack_after_heal['physical_resource_id'])

        # 11. Scale in operation
        scalein_req = paramgen.scalein_vnf_max()
        resp, body = self.scale_vnf_instance(inst_id, scalein_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 12. Scale out operation
        scaleout_req = paramgen.scaleout_vnf_max()
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 13. Heal VNF(all with all=True parameter)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2', 'VDU1-VirtualStorage',
            'VDU2-VirtualStorage', 'internalVL3'])]
        vdu1_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]
        storage1_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1-VirtualStorage')][0]
        storage2_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2-VirtualStorage')][0]
        network_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'internalVL3')][0]

        stack_id_before_heal = self.heat_client.get_stack_resource(stack_name)[
            'stack']['id']
        heal_req = paramgen.heal_vnf_all_max_with_parameter(True)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_id_after_heal = self.heat_client.get_stack_resource(stack_name)[
            'stack']['id']
        self.assertNotEqual(stack_id_before_heal, stack_id_after_heal)
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("CREATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2', 'VDU1-VirtualStorage',
            'VDU2-VirtualStorage', 'internalVL3'])]
        vdu1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]
        storage1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1-VirtualStorage')][0]
        storage2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2-VirtualStorage')][0]
        network_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'internalVL3')][0]

        self.assertEqual("CREATE_COMPLETE",
            vdu1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            vdu2_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            storage1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            storage2_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            network_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu1_stack_before_heal['physical_resource_id'],
            vdu1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(vdu2_stack_before_heal['physical_resource_id'],
            vdu2_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(storage1_stack_before_heal['physical_resource_id'],
            storage1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(storage2_stack_before_heal['physical_resource_id'],
            storage2_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(network_stack_before_heal['physical_resource_id'],
            network_stack_after_heal['physical_resource_id'])

        # 14. Change external connectivity
        stack_id = self.heat_client.get_stack_resource(stack_name)['stack'][
            'id']
        port_info = self.heat_client.get_resource_info(
            f"{stack_name}/{stack_id}", 'VDU2_CP2')
        before_physical_resource_id = port_info['physical_resource_id']
        before_fixed_ips = port_info['attributes']['fixed_ips']

        change_ext_conn_req = paramgen.change_ext_conn_min(net_ids, subnet_ids)
        resp, body = self.change_ext_conn(inst_id, change_ext_conn_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        port_info = self.heat_client.get_resource_info(
            f"{stack_name}/{stack_id}", 'VDU2_CP2')
        after_physical_resource_id = port_info['physical_resource_id']
        after_fixed_ips = port_info['attributes']['fixed_ips']

        self.assertNotEqual(before_physical_resource_id,
            after_physical_resource_id)
        self.assertNotEqual(before_fixed_ips, after_fixed_ips)

        # 15. Show VNF LCM operation occurrence
        # ETSI NFV SOL003 v3.3.1 5.5.2.13 VnfLcmOpOcc
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

        # 16. Terminate VNF
        terminate_req = paramgen.terminate_vnf_max()
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

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 17. Delete VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 18. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)
