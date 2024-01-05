# Copyright (C) 2022 Fujitsu
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
from tacker.tests.functional.sol_separated_nfvo_v2 import fake_grant_v2
from tacker.tests.functional.sol_separated_nfvo_v2 import fake_vnfpkgm_v2
from tacker.tests.functional.sol_v2_common import base_v2
from tacker.tests.functional.sol_v2_common import paramgen
from tacker.tests import utils

WAIT_LCMOCC_UPDATE_TIME = 10


@ddt.ddt
class CommonVnfLcmTest(base_v2.BaseSolV2Test):
    @classmethod
    def setUpClass(cls):
        super(CommonVnfLcmTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(CommonVnfLcmTest, cls).tearDownClass()

    def setUp(self):
        super().setUp()

    def _sample_path(self, *p):
        return utils.test_sample("functional/sol_v2_common", *p)

    def _register_vnf_package_mock_response(self, vnfd_id, package_path):
        """Prepare VNF package for test.

        Register VNF package response to fake NFVO server and Cleanups.

        Returns:
            Response: VNF Package information
        """
        # Set Token
        self.set_server_callback(
            'POST', fake_grant_v2.GrantV2.TOKEN,
            status_code=200,
            response_headers={"Content-Type": "application/json"},
            response_body={"access_token": 'test-token'}
        )

        # Set "VNF Package content" response
        self.set_server_callback(
            'GET',
            os.path.join(
                '/vnfpkgm/v2/onboarded_vnf_packages',
                vnfd_id, 'package_content'),
            status_code=200,
            response_headers={"Content-Type": "application/zip"},
            content=package_path
        )

        # Set "Individual VNF package" response
        self.set_server_callback(
            'GET',
            os.path.join(
                '/vnfpkgm/v2/onboarded_vnf_packages',
                vnfd_id),
            status_code=200,
            response_headers={"Content-Type": "application/json"},
            response_body=(
                fake_vnfpkgm_v2.VnfPackage.make_get_vnf_pkg_info_resp(vnfd_id))
        )

        # Set "VNFD of individual VNF package" response
        self.set_server_callback(
            'GET',
            os.path.join(
                '/vnfpkgm/v2/onboarded_vnf_packages',
                vnfd_id, 'vnfd'),
            status_code=200,
            response_headers={"Content-Type": "application/zip"},
            content=package_path
        )

    def _set_grant_response(self, is_nfvo, operation, glance_image=None,
                            flavour_vdu_dict=None, zone_name_list=None,
                            password=None):
        if is_nfvo:
            if operation == 'INSTANTIATE':
                # Set Fake server response for Grant-Req(Instantiate)
                self.set_server_callback(
                    'POST', fake_grant_v2.GrantV2.GRANT_REQ_PATH,
                    status_code=201,
                    response_headers={"Content-Type": "application/json"},
                    callback=lambda req_headers,
                    req_body: fake_grant_v2.GrantV2.make_inst_response_body(
                        req_body, glance_image, flavour_vdu_dict,
                        zone_name_list, password=password))
            elif operation == 'TERMINATE':
                # Set Fake server response for Grant-Req(Terminate)
                self.set_server_callback(
                    'POST',
                    fake_grant_v2.GrantV2.GRANT_REQ_PATH,
                    status_code=201,
                    response_headers={"Content-Type": "application/json"},
                    callback=lambda req_headers,
                    req_body: fake_grant_v2.GrantV2.make_term_response_body(
                        req_body))
            elif operation == 'SCALE':
                # Set Fake server response for Grant-Req(Scale)
                self.set_server_callback(
                    'POST',
                    fake_grant_v2.GrantV2.GRANT_REQ_PATH, status_code=201,
                    response_headers={"Content-Type": "application/json"},
                    callback=lambda req_headers,
                    req_body: fake_grant_v2.GrantV2.make_scale_response_body(
                        req_body, glance_image,
                        flavour_vdu_dict, zone_name_list))
            elif operation == 'HEAL':
                # Set Fake server response for Grant-Req(Heal)
                self.set_server_callback(
                    'POST',
                    fake_grant_v2.GrantV2.GRANT_REQ_PATH, status_code=201,
                    response_headers={"Content-Type": "application/json"},
                    callback=lambda req_headers,
                    req_body: fake_grant_v2.GrantV2.make_heal_response_body(
                        req_body, glance_image,
                        flavour_vdu_dict, zone_name_list))
            elif operation == 'CHANGE_EXT_CONN':
                # Set Fake server response for Grant-Req(change_ext_conn)
                self.set_server_callback(
                    'POST',
                    fake_grant_v2.GrantV2.GRANT_REQ_PATH, status_code=201,
                    response_headers={"Content-Type": "application/json"},
                    callback=lambda req_headers, req_body:
                    fake_grant_v2.GrantV2.make_change_ext_conn_response_body(
                        req_body, zone_name_list))
            elif operation == 'CHANGE_VNFPKG':
                # Set Fake server response for Grant-Req(Change_vnfpkg)
                self.set_server_callback(
                    'POST',
                    fake_grant_v2.GrantV2.GRANT_REQ_PATH,
                    status_code=201,
                    response_headers={"Content-Type": "application/json"},
                    callback=lambda req_headers, req_body:
                    fake_grant_v2.GrantV2.make_change_vnfpkg_response_body(
                        req_body, glance_image, flavour_vdu_dict))
            else:
                raise Exception

    def basic_lcms_max_common_test(self, is_nfvo=False):
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
              - 12. Heal VNF(all with all=true parameter)
              - 13. Scale out operation
              - 14. Show VNF instance
              - 15. Scale in operation
              - 16. Show VNF instance
              - 17. Heal VNF(vnfc)
              - 18. Change external connectivity
              - 19. Show VNF LCM operation occurrence
              - 20. Heal VNF(vnfc with omit all parameter)
              - 21. Heal VNF(vnfc with all=false parameter)
              - 22. Heal VNF(vnfc with all=true parameter)
              - 23. Update VNF
              - 24. Show VNF instance
              - 25. Terminate VNF
              - 26. Update VNF
              - 27. Instantiate VNF again
              - 28. Terminate VNF again
              - 29. Delete VNF instance
              - 30. Show VNF instance
              - 31. Delete subscription
              - 32. Show subscription
            """
        # 0. Pre-setting
        # nfvo-pre
        if is_nfvo:
            image_path = utils.test_etc_sample("etsi/nfv/common/Files/images",
                "cirros-0.5.2-x86_64-disk.img")
            basic_lcms_max_path = self._sample_path("basic_lcms_max")
            update_vnf_path = self._sample_path("update_vnf")
            vnfd_path = "contents/Definitions/v2_sample1_df_simple.yaml"
            max_zip_path, max_vnfd_id = self.create_vnf_package(
                basic_lcms_max_path, image_path=image_path, nfvo=True)
            upd_zip_path, upd_vnfd_id = self.create_vnf_package(
                update_vnf_path, nfvo=True)

            self._register_vnf_package_mock_response(max_vnfd_id,
                                                     max_zip_path)
            self._register_vnf_package_mock_response(upd_vnfd_id,
                                                     upd_zip_path)
            glance_image = fake_grant_v2.GrantV2.get_sw_image(
                basic_lcms_max_path, vnfd_path)
            flavour_vdu_dict = fake_grant_v2.GrantV2.get_compute_flavor(
                basic_lcms_max_path, vnfd_path)
            zone_name_list = self.get_zone_list()
            sw_data = fake_grant_v2.GrantV2.get_sw_data(
                basic_lcms_max_path, vnfd_path)
            create_req = paramgen.create_vnf_max(max_vnfd_id)
            self.max_pkg = None
            self.upd_pkg = None
        else:
            glance_image = None
            flavour_vdu_dict = None
            zone_name_list = None
            create_req = paramgen.create_vnf_max(self.max_vnfd_id)
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
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_max(callback_uri)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']

        # 2. Test notification
        self.assert_notification_get(callback_url)

        # check usageState of VNF Package
        self.check_package_usage(self.max_pkg, is_nfvo=is_nfvo)

        # 3. Show subscription
        expected_attrs = [
            'id', 'callbackUri', 'verbosity', '_links', 'filter'
        ]

        resp, body = self.show_subscription(sub_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 4. List subscription with attribute-based filtering
        if not is_nfvo:
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
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        self.check_package_usage(self.max_pkg, 'IN_USE', is_nfvo)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 6. Instantiate VNF instance
        instantiate_req = paramgen.instantiate_vnf_max(
            net_ids, subnet_ids, port_ids, self.auth_url)
        if is_nfvo:
            image_1_id, image_2_id = self.glance_create_image(
                instantiate_req.get("vimConnectionInfo").get("vim1"),
                image_path, sw_data, inst_id, num_vdu=2)
            glance_image['VDU1-VirtualStorage'] = image_1_id
            glance_image['VDU2-VirtualStorage'] = image_2_id
            time.sleep(WAIT_LCMOCC_UPDATE_TIME)

        self._set_grant_response(
            is_nfvo, 'INSTANTIATE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
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
        filter_expr = {'filter': f'(eq,id,{inst_id})',
                       'exclude_default': ''}
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
        self._set_grant_response(
            is_nfvo, 'HEAL', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
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

        # 12. Heal VNF(all with all=true parameter)
        self._set_grant_response(
            is_nfvo, 'HEAL', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
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

        stack_id_before_heal = self.heat_client.get_stack_id(stack_name)
        heal_req = paramgen.heal_vnf_all_max_with_parameter(True)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_id_after_heal = self.heat_client.get_stack_id(stack_name)
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
        self._set_grant_response(
            is_nfvo, 'SCALE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
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
        # 8 was the sum of 1 VM, 1 Volume, 5 CPs, 1 stack(VDU1.yaml)
        self.assertEqual(8, count_after_scaleout - count_before_scaleout)

        # 15. Scale in operation
        self._set_grant_response(
            is_nfvo, 'SCALE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
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
        # 8 was the sum of 1 VM, 1 Volume, 5 CPs, 1 stack(VDU1.yaml)
        self.assertEqual(8, count_after_scaleout - count_after_scalein)

        # 17. Heal VNF(vnfc)
        self._set_grant_response(
            is_nfvo, 'HEAL', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
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
        self.check_package_usage(self.max_pkg, 'IN_USE', is_nfvo)

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
        self._set_grant_response(
            is_nfvo, 'CHANGE_EXT_CONN', zone_name_list=zone_name_list)
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

        stack_id_2 = self.heat_client.get_stack_id(stack_name)
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

        stack_id_2 = self.heat_client.get_stack_id(stack_name)
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
        self._set_grant_response(
            is_nfvo, 'HEAL', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
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
        self.check_package_usage(self.max_pkg, 'IN_USE', is_nfvo)

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

        # 21. Heal VNF(vnfc with all=false parameter)
        self._set_grant_response(
            is_nfvo, 'HEAL', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
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
        self.check_package_usage(self.max_pkg, 'IN_USE', is_nfvo)

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

        # 22. Heal VNF(vnfc with all=true parameter)
        self._set_grant_response(
            is_nfvo, 'HEAL', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
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
        self.check_package_usage(self.max_pkg, 'IN_USE', is_nfvo)

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
        # check usageState of max pattern VNF Package
        self.check_package_usage(self.max_pkg, 'IN_USE', is_nfvo)

        # check usageState of update VNF Package
        self.check_package_usage(self.upd_pkg, is_nfvo=is_nfvo)

        # check vnfd id
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        if not is_nfvo:
            self.assertEqual(self.max_vnfd_id, body['vnfdId'])
        else:
            self.assertEqual(max_vnfd_id, body['vnfdId'])

        # check vnfc info
        vnfc_info = body['instantiatedVnfInfo']['vnfcInfo']
        self.assertGreater(len(vnfc_info), 1)
        vnfc_ids = [vnfc['id'] for vnfc in vnfc_info]
        for vnfc in vnfc_info:
            self.assertIn('id', vnfc)
            self.assertIn('vduId', vnfc)
            self.assertIsNotNone(vnfc.get('vnfcState'))
            self.assertIsNone(vnfc.get('vnfcConfigurableProperties'))

        if not is_nfvo:
            update_req = paramgen.update_vnf_max(self.upd_vnfd_id, vnfc_ids)
        else:
            update_req = paramgen.update_vnf_max(upd_vnfd_id, vnfc_ids)
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

        # check usageState of max pattern VNF Package
        self.check_package_usage(self.max_pkg, is_nfvo=is_nfvo)

        # check usageState of update VNF Package
        self.check_package_usage(self.upd_pkg, 'IN_USE', is_nfvo)

        if not is_nfvo:
            # check the specified attribute after update VNF
            self.assertEqual(self.upd_vnfd_id, body['vnfdId'])
        else:
            self.assertEqual(upd_vnfd_id, body['vnfdId'])
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
        self._set_grant_response(is_nfvo, 'TERMINATE')
        terminate_req = paramgen.terminate_vnf_max()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(WAIT_LCMOCC_UPDATE_TIME)

        # check deletion of Heat-stack
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertIsNone(stack_status)

        if not is_nfvo:
            # check deletion of Glance-image
            for image_name in image_name_list:
                image_id = self.get_image_id(image_name)
                self.assertIsNone(image_id)

        # check usageState of VNF Package
        self.check_package_usage(self.upd_pkg, 'IN_USE', is_nfvo)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 26. Update vnf
        # In the previous operation, "update VNF" changed vnfd_id,
        # which caused the failure of re-instantiate using the original
        # instantiate_request. To make the re-instantiate successful,
        # execute "update vnf" again to update the vnfd_id to the
        # original vnfd_id
        if not is_nfvo:
            update_req = paramgen.update_vnf_min_with_parameter(
                self.max_vnfd_id)
        else:
            update_req = paramgen.update_vnf_min_with_parameter(max_vnfd_id)
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 27. Instantiate VNF again
        # Confirm Re-Instantiation of a VNF that has been terminated
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 28. Terminate VNF again
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 29. Delete VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 30. Show VNF instance
        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

        self.check_package_usage(self.upd_pkg, is_nfvo=is_nfvo)

        # 31. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 32. Show subscription
        resp, body = self.show_subscription(sub_id)
        self.assertEqual(404, resp.status_code)

        if is_nfvo:
            image_ids = [image_1_id, image_2_id]
            self.glance_delete_image(
                instantiate_req.get("vimConnectionInfo").get("vim1"),
                image_ids)

    def basic_lcms_min_common_test(self, is_nfvo=False):
        """Test LCM operations with omitting except for required attributes

        The change_ext_conn can't be tested here because min pattern VNF
        package don't have external connectivity. So moved it to
        the test_scale_other_lcm().

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
          - 15. Update VNF
          - 16. Instantiate VNF again
          - 17. Terminate VNF again
          - 18. Delete VNF instance
          - 19. Delete subscription
          - 20. Show subscription
        """
        # 0. Pre setting
        if is_nfvo:
            # for basic lcms tests min pattern
            basic_lcms_min_path = self._sample_path("basic_lcms_min")
            min_zip_path, min_vnfd_id = self.create_vnf_package(
                basic_lcms_min_path, nfvo=True)
            update_vnf_path = self._sample_path("update_vnf")
            vnfd_path = "contents/Definitions/v2_sample2_df_simple.yaml"
            upd_zip_path, upd_vnfd_id = self.create_vnf_package(
                update_vnf_path, nfvo=True)
            self._register_vnf_package_mock_response(
                min_vnfd_id, min_zip_path)
            self._register_vnf_package_mock_response(
                upd_vnfd_id, upd_zip_path)
            glance_image = fake_grant_v2.GrantV2.get_sw_image(
                basic_lcms_min_path, vnfd_path)
            flavour_vdu_dict = fake_grant_v2.GrantV2.get_compute_flavor(
                basic_lcms_min_path, vnfd_path)
            zone_name_list = self.get_zone_list()
            create_req = paramgen.create_vnf_min(min_vnfd_id)
            update_req = paramgen.update_vnf_min_with_parameter(upd_vnfd_id)
            self.min_pkg = None
            self.upd_pkg = None
        else:
            glance_image = None
            flavour_vdu_dict = None
            zone_name_list = None
            create_req = paramgen.create_vnf_min(self.min_vnfd_id)
            update_req = paramgen.update_vnf_min_with_parameter(
                self.upd_vnfd_id)

        # 1. Create subscription
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_min(callback_uri)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']

        # 2. Test notification
        self.assert_notification_get(callback_url)
        # check usageState of VNF Package
        self.check_package_usage(self.min_pkg, is_nfvo=is_nfvo)

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
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        self.check_package_usage(self.min_pkg, 'IN_USE', is_nfvo)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 4. Instantiate VNF
        self._set_grant_response(
            is_nfvo, 'INSTANTIATE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
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
        self._set_grant_response(
            is_nfvo, 'HEAL', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
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

        # check usageState of min pattern VNF Package
        self.check_package_usage(self.min_pkg, 'IN_USE', is_nfvo)

        # check usageState of update VNF Package
        self.check_package_usage(self.upd_pkg, is_nfvo=is_nfvo)

        if not is_nfvo:
            # check vnfd id
            self.assertEqual(self.min_vnfd_id, body['vnfdId'])
        else:
            # check vnfd id
            self.assertEqual(min_vnfd_id, body['vnfdId'])

        # 8. Update VNF
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check usageState of min pattern VNF Package
        self.check_package_usage(self.min_pkg, is_nfvo=is_nfvo)

        # check usageState of update VNF Package
        self.check_package_usage(self.upd_pkg, 'IN_USE', is_nfvo)
        if not is_nfvo:
            # check vnfd id
            resp, body = self.show_vnf_instance(inst_id)
            self.assertEqual(200, resp.status_code)
            self.assertEqual(self.upd_vnfd_id, body['vnfdId'])
        else:
            # check vnfd id
            resp, body = self.show_vnf_instance(inst_id)
            self.assertEqual(200, resp.status_code)
            self.assertEqual(upd_vnfd_id, body['vnfdId'])

        # 9. Heal VNF(vnfc)
        self._set_grant_response(
            is_nfvo, 'HEAL', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
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

        # check usageState of update VNF Package
        self.check_package_usage(self.upd_pkg, 'IN_USE', is_nfvo)

        # 11. Scale out operation
        self._set_grant_response(
            is_nfvo, 'SCALE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
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
        self._set_grant_response(
            is_nfvo, 'SCALE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
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
        self._set_grant_response(is_nfvo, 'TERMINATE')
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check deletion of Heat-stack
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertIsNone(stack_status)

        # check usageState of VNF Package
        self.check_package_usage(self.upd_pkg, 'IN_USE', is_nfvo)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 15. Update VNF
        # In the previous operation, "update VNF" changed vnfd_id,
        # which caused the failure of re-instantiate using the original
        # instantiate_request. To make the re-instantiate successful,
        # execute "update vnf" again to update the vnfd_id to the
        # original vnfd_id
        if not is_nfvo:
            update_req = paramgen.update_vnf_min_with_parameter(
                self.min_vnfd_id)
        else:
            update_req = paramgen.update_vnf_min_with_parameter(min_vnfd_id)
        resp, body = self.exec_lcm_operation(self.update_vnf_instance,
                                      inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 16. Instantiate VNF again
        # Confirm Re-Instantiation of a VNF that has been terminated
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 17. Terminate VNF again
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 18. Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

        # check usageState of VNF Package
        self.check_package_usage(self.upd_pkg, is_nfvo=is_nfvo)

        # 19. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 20. Show subscription
        resp, body = self.show_subscription(sub_id)
        self.assertEqual(404, resp.status_code)

    def _get_vnfc_cp_net_id(self, inst, vdu, cp):
        for vnfc in inst['instantiatedVnfInfo']['vnfcResourceInfo']:
            if vnfc['vduId'] == vdu:
                for cp_info in vnfc['vnfcCpInfo']:
                    if cp_info['cpdId'] == cp:
                        # must be found
                        ext_cp_id = cp_info['vnfExtCpId']
                        break
                break
        for ext_vl in inst['instantiatedVnfInfo']['extVirtualLinkInfo']:
            for port in ext_vl['extLinkPorts']:
                if port['cpInstanceId'] == ext_cp_id:
                    # must be found
                    return ext_vl['resourceHandle']['resourceId']

    def change_vnfpkg_from_image_to_image_common_test(self, is_nfvo=False):
        """Test ChangeCurrentVNFPackage from image to image

        * About attributes:
          All of the following cardinality attributes are set.
          In addition, 0..N or 1..N attributes are set to 2 or more.
          - 0..1 (1)
          - 0..N (2 or more)
          - 1
          - 1..N (2 or more)

        * About LCM operations:
          This test includes the following operations.
          - 1. Create VNF instance
          - 2. Instantiate VNF
          - 3. Show VNF instance
          - 4. Change Current VNF Package
          - 5. Show VNF instance
          - 6. Terminate VNF
          - 7. Delete VNF instance
        """
        # 0. Pre-setting
        if is_nfvo:
            change_vnfpkg_from_image_to_image_path = self._sample_path(
                "test_instantiate_vnf_with_old_image_or_volume")
            old_zip_path, old_vnfd_id = self.create_vnf_package(
                change_vnfpkg_from_image_to_image_path, nfvo=True)
            change_vnfpkg_from_image_to_image_path_2 = self._sample_path(
                "test_change_vnf_pkg_with_new_image")
            image_path = utils.test_etc_sample("etsi/nfv/common/Files/images",
                "cirros-0.5.2-x86_64-disk.img")
            new_image_zip_path, new_image_vnfd_id = self.create_vnf_package(
                change_vnfpkg_from_image_to_image_path_2,
                image_path=image_path, nfvo=True)
            package_dir = self._sample_path(
                "test_instantiate_vnf_with_old_image_or_volume")
            vnfd_path = (
                "contents/Definitions/change_vnf_pkg_old_image_df_simple.yaml")

            change_package_dir = self._sample_path(
                "test_change_vnf_pkg_with_new_image")
            change_vnfd_path = (
                "contents/Definitions/"
                "change_vnf_pkg_new_image_df_simple.yaml")
            sw_data = fake_grant_v2.GrantV2.get_sw_data(
                change_package_dir, change_vnfd_path)
            glance_image = fake_grant_v2.GrantV2.get_sw_image(
                package_dir, vnfd_path)
            flavour_vdu_dict = fake_grant_v2.GrantV2.get_compute_flavor(
                package_dir, vnfd_path)
            zone_name_list = self.get_zone_list()
            self._register_vnf_package_mock_response(
                old_vnfd_id, old_zip_path)
            create_req = paramgen.change_vnfpkg_create(old_vnfd_id)
            change_vnfpkg_req = paramgen.change_vnfpkg_with_ext_vl(
                new_image_vnfd_id, self.get_network_ids(['net1']))
        else:
            glance_image = None
            flavour_vdu_dict = None
            zone_name_list = None
            create_req = paramgen.change_vnfpkg_create(self.old_vnfd_id)
            change_vnfpkg_req = paramgen.change_vnfpkg_with_ext_vl(
                self.new_image_vnfd_id, self.get_network_ids(['net1']))

        # 1. Create VNF instance
        resp, body = self.create_vnf_instance(create_req)
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
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # 2. Instantiate VNF
        self._set_grant_response(
            is_nfvo, 'INSTANTIATE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
        net_ids = self.get_network_ids(['net0', 'net1', 'net_mgmt'])
        subnet_ids = self.get_subnet_ids(['subnet0', 'subnet1'])
        instantiate_req = paramgen.change_vnfpkg_instantiate(
            net_ids, subnet_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)

        # 3. Show VNF instance
        resp_1, body_1 = self.show_vnf_instance(inst_id)
        stack_name = "vnf-{}".format(inst_id)
        stack_id = self.heat_client.get_stack_id(stack_name)
        image_id_1 = self.get_current_vdu_image(stack_id, stack_name, 'VDU2')

        self.assertEqual(200, resp_1.status_code)
        self.check_resp_headers_in_get(resp_1)
        self.check_resp_body(body_1, expected_inst_attrs)

        vdu1_cp1_net_id = self._get_vnfc_cp_net_id(body_1, 'VDU1', 'VDU1_CP1')
        self.assertEqual(net_ids['net0'], vdu1_cp1_net_id)

        # 4. Change Current VNF Package
        if is_nfvo:
            self._register_vnf_package_mock_response(
                new_image_vnfd_id, new_image_zip_path)
            g_image_id_1, g_image_id_2 = self.glance_create_image(
                instantiate_req.get("vimConnectionInfo").get("vim1"),
                image_path, sw_data, inst_id, num_vdu=2)
            glance_image['VDU1'] = g_image_id_1
            glance_image['VDU2'] = g_image_id_2
        self._set_grant_response(is_nfvo, 'CHANGE_VNFPKG',
            glance_image=glance_image, flavour_vdu_dict=flavour_vdu_dict)
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 5. Show VNF instance
        resp_2, body_2 = self.show_vnf_instance(inst_id)
        image_id_2 = self.get_current_vdu_image(stack_id, stack_name, 'VDU2')
        self.assertNotEqual(image_id_1, image_id_2)

        self.assertEqual(200, resp_2.status_code)
        self.check_resp_headers_in_get(resp_2)
        self.check_resp_body(body_2, expected_inst_attrs)

        vdu1_cp1_net_id = self._get_vnfc_cp_net_id(body_2, 'VDU1', 'VDU1_CP1')
        # changed from net0 to net1
        self.assertEqual(net_ids['net1'], vdu1_cp1_net_id)

        # 6. Terminate VNF
        self._set_grant_response(is_nfvo, 'TERMINATE')
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 7. Delete VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        if is_nfvo:
            self.glance_delete_image(
                instantiate_req.get("vimConnectionInfo").get("vim1"),
                [g_image_id_1, g_image_id_2])

    def retry_rollback_scale_out_common_test(self, is_nfvo=False):
        """Test retry and rollback scale out operations

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
          - 3. Create VNF instance
          - 4. Instantiate VNF
          - 5. Show VNF instance
          - 6. Scale out operation(will fail)
          - 7. Show VNF instance
          - 8. Retry operation
          - 9. Rollback scale out operation
          - 10. Show VNF LCM operation occurrence
          - 11. List VNF LCM operation occurrence
          - 12. Terminate VNF
          - 13. Delete VNF instance
          - 14. Delete subscription
          - 15. Show subscription
        """
        # 0. Pre-setting
        if is_nfvo:
            image_path = utils.test_etc_sample("etsi/nfv/common/Files/images",
                "cirros-0.5.2-x86_64-disk.img")

            # Scale operation will fail
            scale_ng_path = self._sample_path("scale_ng")
            scale_ng_zip_path, scale_ng_vnfd_id = self.create_vnf_package(
                scale_ng_path, image_path=image_path, nfvo=True)
            vnfd_path = "contents/Definitions/v2_sample1_df_simple.yaml"
            glance_image = fake_grant_v2.GrantV2.get_sw_image(
                scale_ng_path, vnfd_path)
            flavour_vdu_dict = fake_grant_v2.GrantV2.get_compute_flavor(
                scale_ng_path, vnfd_path)
            zone_name_list = self.get_zone_list()
            sw_data = fake_grant_v2.GrantV2.get_sw_data(scale_ng_path,
                                                        vnfd_path)
            self._register_vnf_package_mock_response(
                scale_ng_vnfd_id, scale_ng_zip_path)
            create_req = paramgen.create_vnf_max(scale_ng_vnfd_id)
            self.scale_ng_pkg = None
        else:
            glance_image = None
            flavour_vdu_dict = None
            zone_name_list = None
            create_req = paramgen.create_vnf_max(self.scale_ng_vnfd_id)
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
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_max(callback_uri)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']

        # 2. Test notification
        self.assert_notification_get(callback_url)
        # check usageState of VNF Package
        self.check_package_usage(self.scale_ng_pkg, is_nfvo=is_nfvo)

        # 3. Create VNF instance
        # ETSI NFV SOL003 v3.3.1 5.5.2.2 VnfInstance
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
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        self.check_package_usage(self.scale_ng_pkg, 'IN_USE', is_nfvo)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 4. Instantiate VNF
        instantiate_req = paramgen.instantiate_vnf_max(
            net_ids, subnet_ids, port_ids, self.auth_url)
        if is_nfvo:
            image_1_id, image_2_id = self.glance_create_image(
                instantiate_req.get("vimConnectionInfo").get("vim1"),
                image_path, sw_data, inst_id, num_vdu=2)
            glance_image['VDU1-VirtualStorage'] = image_1_id
            glance_image['VDU2-VirtualStorage'] = image_2_id
            time.sleep(WAIT_LCMOCC_UPDATE_TIME)

        self._set_grant_response(
            is_nfvo, 'INSTANTIATE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check usageState of VNF Package
        self.check_package_usage(self.scale_ng_pkg, 'IN_USE', is_nfvo)

        # 5. Show VNF instance
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
                         body.get('instantiationState'))

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # 6. Scale out operation(will fail)
        self._set_grant_response(
            is_nfvo, 'SCALE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
        scaleout_req = paramgen.scaleout_vnf_max()
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)

        # check usageState of VNF Package
        self.check_package_usage(self.scale_ng_pkg, 'IN_USE', is_nfvo)

        # 7. Show VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # 8. Retry scale out operation
        resp, body = self.retry_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        self.wait_lcmocc_failed_temp(lcmocc_id)

        # 9. Rollback scale out operation
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # 10. Show VNF LCM operation occurrence
        # ETSI NFV SOL003 v3.3.1 5.5.2.13 VnfLcmOpOcc
        # NOTE: omitted values are not supported at that time
        expected_attrs = [
            'id',
            'operationState',
            'stateEnteredTime',
            'startTime',
            'vnfInstanceId',
            'grantId',
            'operation',
            'isAutomaticInvocation',
            'operationParams',
            'isCancelPending',
            # 'cancelMode', # omitted
            'error',
            # 'resourceChanges', # omitted
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

        # 11. List VNF LCM operation occurrence
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
            # 'operationParams', # omitted
            'isCancelPending',
            # 'cancelMode', # omitted
            # 'error', # omitted
            # 'resourceChanges', # omitted
            # 'changedInfo', # omitted
            # 'changedExtConnectivity', # omitted
            # 'modificationsTriggeredByVnfPkgChange', # omitted
            # 'vnfSnapshotInfoId', # omitted
            '_links'
        ]
        resp, body = self.list_lcmocc()
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for lcmocc in body:
            self.check_resp_body(lcmocc, expected_attrs)

        # 12. Terminate VNF instance
        self._set_grant_response(is_nfvo, 'TERMINATE')
        terminate_req = paramgen.terminate_vnf_max()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check usageState of VNF Package
        self.check_package_usage(self.scale_ng_pkg, 'IN_USE', is_nfvo)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body.get('instantiationState'))

        # 13. Delete VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check usageState of VNF Package
        self.check_package_usage(self.scale_ng_pkg, is_nfvo=is_nfvo)

        # 14. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 15. Show subscription
        resp, body = self.show_subscription(sub_id)
        self.assertEqual(404, resp.status_code)
        self.check_resp_headers_in_get(resp)

        if is_nfvo:
            self.glance_delete_image(
                instantiate_req.get("vimConnectionInfo").get("vim1"),
                [image_1_id, image_2_id])

    def fail_instantiate_common_test(self, is_nfvo=False):
        """Test fail instantiate operation

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
          - 4. Instantiate VNF(will fail)
          - 5. Show VNF instance
          - 6. Fail instantiation operation
          - 7. Show VNF LCM operation occurrence
          - 8. List VNF LCM operation occurrence
          - 9. Delete VNF instance
          - 10. Delete subscription
        """
        if is_nfvo:
            # Instantiate VNF will fail
            error_network_path = self._sample_path("error_network")
            # no image contained
            err_nw_zip_path, err_nw_vnfd_id = self.create_vnf_package(
                error_network_path, nfvo=True)
            vnfd_path = "contents/Definitions/v2_sample2_df_simple.yaml"
            glance_image = fake_grant_v2.GrantV2.get_sw_image(
                error_network_path, vnfd_path)
            flavour_vdu_dict = fake_grant_v2.GrantV2.get_compute_flavor(
                error_network_path, vnfd_path)
            zone_name_list = self.get_zone_list()
            self._register_vnf_package_mock_response(
                err_nw_vnfd_id, err_nw_zip_path)
            create_req = paramgen.create_vnf_min(err_nw_vnfd_id)
            self.err_nw_pkg = None
        else:
            glance_image = None
            flavour_vdu_dict = None
            zone_name_list = None
            create_req = paramgen.create_vnf_min(self.err_nw_vnfd_id)
        # 1. Create subscription
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_min(callback_uri)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']

        # 2. Test notification
        self.assert_notification_get(callback_url)
        # check usageState of VNF Package
        self.check_package_usage(self.err_nw_pkg, is_nfvo=is_nfvo)

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
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        self.check_package_usage(self.err_nw_pkg, 'IN_USE', is_nfvo)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body.get('instantiationState'))

        # 4. Instantiate VNF(will fail)
        self._set_grant_response(
            is_nfvo, 'INSTANTIATE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
        instantiate_req = paramgen.instantiate_vnf_min()
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)

        # check usageState of VNF Package
        self.check_package_usage(self.err_nw_pkg, 'IN_USE', is_nfvo)

        # 5. Show VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body.get('instantiationState'))

        # 6. Fail instantiation operation
        expected_attrs = [
            'id',
            'operationState',
            'stateEnteredTime',
            'startTime',
            'vnfInstanceId',
            'grantId',
            'operation',
            'isAutomaticInvocation',
            'operationParams',
            'isCancelPending',
            # 'cancelMode', # omitted
            'error',
            # 'resourceChanges', # omitted
            # 'changedInfo', # omitted
            # 'changedExtConnectivity', # omitted
            # 'modificationTriggeredByVnfPkgChange', # omitted
            # 'vnfSnapshotInfoId', # omitted
            '_links'
        ]
        resp, body = self.fail_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)
        self.assertEqual('FAILED', body['operationState'])

        # 7. Show VNF LCM operation occurrence
        # ETSI NFV SOL003 v3.3.1 5.5.2.13 VnfLcmOpOcc
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 8. List VNF LCM operation occurrence
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
            # 'operationParams', # omitted
            'isCancelPending',
            # 'cancelMode', # omitted
            # 'error', # omitted
            # 'resourceChanges', # omitted
            # 'changedInfo', # omitted
            # 'changedExtConnectivity', # omitted
            # 'modificationsTriggeredByVnfPkgChange', # omitted
            # 'vnfSnapshotInfoId', # omitted
            '_links'
        ]
        resp, body = self.list_lcmocc()
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for lcmocc in body:
            self.check_resp_body(lcmocc, expected_attrs)

        # 9. Delete VNF instance
        # Delete Stack
        stack_id = self.heat_client.get_stack_id(f'vnf-{inst_id}')
        self.heat_client.delete_stack(f'vnf-{inst_id}/{stack_id}')

        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check usageState of VNF Package
        self.check_package_usage(self.err_nw_pkg, 'NOT_IN_USE', is_nfvo)

        # 10. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)
