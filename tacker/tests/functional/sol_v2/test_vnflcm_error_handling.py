# Copyright (C) 2022 Nippon Telegraph and Telephone Corporation
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
class VnfLcmErrorHandlingTest(base_v2.BaseSolV2Test):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmErrorHandlingTest, cls).setUpClass()

        cur_dir = os.path.dirname(__file__)
        # tacker/tests/etc...
        #             /functional/sol_v2
        image_dir = os.path.join(
            cur_dir, "../../etc/samples/etsi/nfv/common/Files/images")
        image_file = "cirros-0.5.2-x86_64-disk.img"
        image_path = os.path.abspath(os.path.join(image_dir, image_file))

        # Scale operation will fail
        scale_ng_path = os.path.join(cur_dir, "samples/scale_ng")
        cls.vnf_pkg_1, cls.vnfd_id_1 = cls.create_vnf_package(
            scale_ng_path, image_path=image_path)

        # Instantiate VNF will fail
        error_network_path = os.path.join(cur_dir, "samples/error_network")
        # no image contained
        cls.vnf_pkg_2, cls.vnfd_id_2 = cls.create_vnf_package(
            error_network_path)

        # update VNF or change external VNF connectivity will fail
        update_change_ng_path = os.path.join(cur_dir,
                                             "samples/basic_lcms_min")
        # no image contained
        cls.vnf_pkg_3, cls.vnfd_id_3 = cls.create_vnf_package(
            update_change_ng_path)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmErrorHandlingTest, cls).tearDownClass()

        cls.delete_vnf_package(cls.vnf_pkg_1)
        cls.delete_vnf_package(cls.vnf_pkg_2)
        cls.delete_vnf_package(cls.vnf_pkg_3)

    def setUp(self):
        super().setUp()

    def test_retry_rollback_scale_out(self):
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

        # 2. Test notification
        self.assert_notification_get(callback_url)
        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

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

        # 4. Instantiate VNF
        instantiate_req = paramgen.instantiate_vnf_max(
            net_ids, subnet_ids, port_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('IN_USE', usage_state)

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
        scaleout_req = paramgen.scaleout_vnf_max()
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('IN_USE', usage_state)

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
        terminate_req = paramgen.terminate_vnf_max()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body.get('instantiationState'))

        # wait a bit because there is a bit time lag between vnf instance DB
        # terminate and delete completion.
        time.sleep(5)

        # 13. Delete VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

        # 14. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 15. Show subscription
        resp, body = self.show_subscription(sub_id)
        self.assertEqual(404, resp.status_code)
        self.check_resp_headers_in_get(resp)

    def test_rollback_instantiate(self):
        """Test rollback instantiate operation

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
          - 6. Rollback instantiation operation
          - 7. Show VNF LCM operation occurrence
          - 8. List VNF LCM operation occurrence
          - 9. Delete VNF instance
          - 10. Delete subscription
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
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body.get('instantiationState'))

        # 4. Instantiate VNF(will fail)
        instantiate_req = paramgen.instantiate_vnf_min()
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_2)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # 5. Show VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body.get('instantiationState'))

        # 6. Rollback instantiation operation
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # 7. Show VNF LCM operation occurrence
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
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_2)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

        # 10. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

    def test_fail_instantiate(self):
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
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body.get('instantiationState'))

        # 4. Instantiate VNF(will fail)
        instantiate_req = paramgen.instantiate_vnf_min()
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_2)['usageState']
        self.assertEqual('IN_USE', usage_state)

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
        self.heat_client.delete_stack(f'vnf-{inst_id}')

        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_2)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

        # 10. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

    def test_rollback_update(self):
        """Test rollback update VNF operation

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
          - 6. Update VNF(will fail)
          - 7. Rollback update operation
          - 8. Show VNF LCM operation occurrence
          - 9. List VNF LCM operation occurrence
          - 10. Terminate VNF
          - 11. Delete VNF instance
          - 12. Delete subscription
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
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
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
        create_req = paramgen.create_vnf_min(self.vnfd_id_3)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 4. Instantiate VNF
        instantiate_req = paramgen.instantiate_vnf_min()
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('IN_USE', usage_state)

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

        # 6. Update VNF(will fail)
        # NOTE: Create a file so that an error occurs in mgmtDriver
        path = '/tmp/modify_information_start'
        with open(path, 'w', encoding='utf-8') as f:
            f.write('')
        self.addCleanup(os.remove, path)
        update_req = paramgen.update_vnf_min()
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)

        # 7. Rollback update operation
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # 8. Show VNF LCM operation occurrence
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
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 9. List VNF LCM operation occurrence
        resp, body = self.list_lcmocc()
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for lcmocc in body:
            self.check_resp_body(lcmocc, expected_attrs)

        # 10. Terminate a VNF instance
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 11. Delete VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

        # 12. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

    def test_rollback_chgextconn(self):
        """Test rollback change_ext_conn operation

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
          - 6. Change external connectivity(will fail)
          - 7. Rollback change_ext_conn operation
          - 8. Show VNF LCM operation occurrence
          - 9. List VNF LCM operation occurrence
          - 10. Terminate VNF
          - 11. Delete VNF instance
          - 12. Delete subscription
        """
        # 0. Pre-setting
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

        net_ids = self.get_network_ids(['ft-net1'])
        subnet_ids = self.get_subnet_ids(['ft-ipv4-subnet1',
            'ft-ipv6-subnet1'])

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
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
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
        create_req = paramgen.create_vnf_min(self.vnfd_id_3)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 4. Instantiate VNF
        instantiate_req = paramgen.instantiate_vnf_min()
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('IN_USE', usage_state)

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

        # 6. Change external connectivity(will fail)
        # NOTE: Create a file so that an error occurs in mgmtDriver
        path = '/tmp/change_external_connectivity_start'
        with open(path, 'w', encoding='utf-8') as f:
            f.write('')
        self.addCleanup(os.remove, path)
        change_ext_conn_req = paramgen.change_ext_conn_min(net_ids, subnet_ids)
        resp, body = self.change_ext_conn(inst_id, change_ext_conn_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)

        # 7. Rollback change_ext_conn operation
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # 8. Show VNF LCM operation occurrence
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
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 9. List VNF LCM operation occurrence
        resp, body = self.list_lcmocc()
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for lcmocc in body:
            self.check_resp_body(lcmocc, expected_attrs)

        # 10. Terminate VNF
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 11. Delete VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_3)['usageState']
        self.assertEqual('NOT_IN_USE', usage_state)

        # 12. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)
