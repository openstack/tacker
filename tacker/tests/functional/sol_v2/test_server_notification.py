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
from tacker.tests.functional.sol_v2_common import paramgen
from tacker.tests.functional.sol_v2_common import test_vnflcm_basic_common

TEST_COUNT = 0
RETRY_LIMIT = 10
RETRY_TIMEOUT = 3
WAIT_AUTO_HEAL_TIME = 60
SERVER_NOTIFICATION_INTERVAL = 1


def _make_alarm_id(header, body):
    from tacker.tests.functional.sol_v2 import test_server_notification
    id = f"alarm_id_{test_server_notification.TEST_COUNT}"
    return {'alarm_id': id}


@ddt.ddt
class ServerNotificationTest(test_vnflcm_basic_common.CommonVnfLcmTest):
    @classmethod
    def setUpClass(cls):
        super(ServerNotificationTest, cls).setUpClass()
        cur_dir = os.path.dirname(__file__)
        # tacker/tests/etc...
        #             /functional/sol_v2
        image_dir = os.path.join(
            cur_dir, "../../etc/samples/etsi/nfv/common/Files/images")
        image_file = "cirros-0.5.2-x86_64-disk.img"
        image_path = os.path.abspath(os.path.join(image_dir, image_file))

        # for basic lcms tests max pattern
        basic_lcms_max_path = os.path.join(cur_dir, "../sol_v2_common/"
                                                    "samples/basic_lcms_max")
        cls.max_pkg, cls.max_vnfd_id = cls.create_vnf_package(
            basic_lcms_max_path, image_path=image_path)

        # for basic lcms tests min pattern
        basic_lcms_min_path = os.path.join(cur_dir, "../sol_v2_common/"
                                                    "samples/basic_lcms_min")
        # no image contained
        cls.min_pkg, cls.min_vnfd_id = cls.create_vnf_package(
            basic_lcms_min_path)

        # for update vnf test
        update_vnf_path = os.path.join(cur_dir, "../sol_v2_common/"
                                                "samples/update_vnf")
        # no image contained
        cls.upd_pkg, cls.upd_vnfd_id = cls.create_vnf_package(
            update_vnf_path)

        # for server_notification test
        server_notification_path = os.path.join(
            cur_dir, "../sol_v2_common/samples/server_notification")
        # no image contained
        cls.svn_pkg, cls.svn_id = cls.create_vnf_package(
            server_notification_path)

    @classmethod
    def tearDownClass(cls):
        super(ServerNotificationTest, cls).tearDownClass()
        cls.delete_vnf_package(cls.max_pkg)
        cls.delete_vnf_package(cls.min_pkg)
        cls.delete_vnf_package(cls.upd_pkg)
        cls.delete_vnf_package(cls.svn_pkg)

    def setUp(self):
        super().setUp()

    def fault_notification_queueing_test(self):
        """Test Fault Notification with queueing

        * About Test operations:
          This test includes the following operations.
          - 1. LCM-Create
          - 2. LCM-Instantiate
          - 3. ServerNotifier-Notify (multiple times)
          - 4. LCM-Heal
          - 5. LCM-Scale (SCALE_OUT)
          - 6. LCM-Scale (SCALE_IN)
          - 7. LCM-Terminate
          - 8. LCM-Delete
        """
        self.fault_notification_basic_test(repeat=3)

    def fault_notification_autoheal_disabled_test(self):
        """Test Fault Notification isAutohealEnabled=False

        * About Test operations:
          This test includes the following operations.
          - 1. LCM-Create
          - 2. LCM-Instantiate (isAutohealEnabled=False)
          - 3. ServerNotifier-Notify
          - 4. LCM-Terminate
          - 5. LCM-Delete
          When isAutohealEnabled=False, ServerNotifier-Notify is ignored.
          LCM-Heal and LCM-Scale are skipped for time-saving of FT.
        """
        self.fault_notification_basic_test(is_autoheal_enabled=False)

    def fault_notification_basic_test(
            self, repeat=1, is_autoheal_enabled=True):
        """Test Fault Notification basic

        * About Test operations:
          This test includes the following operations.
          - 1. LCM-Create
          - 2. LCM-Instantiate
          - 3. ServerNotifier-Notify
          - 4. LCM-Heal
          - 5. LCM-Scale (SCALE_OUT)
          - 6. LCM-Scale (SCALE_IN)
          - 7. LCM-Terminate
          - 8. LCM-Delete
        """

        # Retrying LCM function in case that
        # the lcmocc is completed but the lock is still remaining.
        def _lcm_retry(func, *args):
            retry = RETRY_LIMIT
            while retry > 0:
                resp, body = func(*args)
                if 409 != resp.status_code:
                    break
                time.sleep(RETRY_TIMEOUT)
                retry -= 1
            return resp, body

        is_nfvo = False
        # 0. Pre setting
        create_req = paramgen.create_vnf_min(self.svn_id)

        # Create subscription
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        server_notification_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        '/server_notification')

        self.set_server_callback(
            'POST',
            '/server_notification',
            status_code=200,
            response_headers={"Content-Type": "application/json"},
            callback=_make_alarm_id
        )

        sub_req = paramgen.sub_create_min(callback_uri)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']

        # Test notification
        self.assert_notification_get(callback_url)

        # 1. LCM-Create
        # ETSI NFV SOL003 v3.3.1 5.5.2.2 VnfInstance
        expected_inst_attrs = [
            'id',
            'vnfdId',
            'vnfProvider',
            'vnfProductName',
            'vnfSoftwareVersion',
            'vnfdVersion',
            'instantiationState',
            '_links'
        ]
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        self.check_package_usage(self.svn_pkg, 'IN_USE', is_nfvo)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 2. LCM-Instantiate
        instantiate_req = paramgen.instantiate_vnf_min()
        instantiate_req['additionalParams'] = {
            'ServerNotifierUri': server_notification_uri,
            'ServerNotifierFaultID': ['1111', '1234']
        }
        instantiate_req['vnfConfigurableProperties'] = {
            'isAutohealEnabled': is_autoheal_enabled
        }

        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)
        lcmocc_resp, lcmocc_body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, lcmocc_resp.status_code)
        self.assertEqual('COMPLETED', lcmocc_body['operationState'])
        self.assertEqual('INSTANTIATE', lcmocc_body['operation'])
        self.assertEqual(False, lcmocc_body['isAutomaticInvocation'])

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

        # Show VNF instance
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

        # 3. ServerNotifier-Notify
        for i in range(repeat):
            alarm_id = 'alarm_id_0'
            fault_notification_param = paramgen.server_notification(alarm_id)
            resp, body = self.server_notification(
                inst_id, 'server_id', fault_notification_param)
            self.assertTrue(resp.status_code == 204 or resp.status_code == 404)
            time.sleep(SERVER_NOTIFICATION_INTERVAL)

        if is_autoheal_enabled:
            # waiting for auto healing process complete after packing timer.
            time.sleep(WAIT_AUTO_HEAL_TIME)

            # List-OpOcc
            filter_expr = {'filter': f'(eq,vnfInstanceId,{inst_id})'}
            resp, body = self.list_lcmocc(filter_expr)
            self.assertEqual(200, resp.status_code)

            heal_lcmocc = [
                heal_lcmocc for heal_lcmocc in body
                if heal_lcmocc['startTime'] == max(
                    [lcmocc['startTime'] for lcmocc in body])][0]
            lcmocc_id = heal_lcmocc['id']
            self.wait_lcmocc_complete(lcmocc_id)

            # Show-OpOcc
            resp, body = self.show_lcmocc(lcmocc_id)
            self.assertEqual(200, resp.status_code)
            self.assertEqual('COMPLETED', body['operationState'])
            self.assertEqual('HEAL', body['operation'])
            self.assertEqual(True, body['isAutomaticInvocation'])

            # 4. LCM-Heal
            nested_stacks = self.heat_client.get_resources(stack_name)
            temp_stacks = [stack for stack in nested_stacks if
                (stack['resource_name'] in ['VDU1', 'VDU2'])]
            vdu1_stack_before_heal = [stack for stack in temp_stacks if
                (stack['resource_name'] == 'VDU1')][0]
            vdu2_stack_before_heal = [stack for stack in temp_stacks if
                (stack['resource_name'] == 'VDU2')][0]

            heal_req = paramgen.heal_vnf_all_min()
            resp, body = _lcm_retry(self.heal_vnf_instance, inst_id, heal_req)
            self.assertEqual(202, resp.status_code)
            self.check_resp_headers_in_operation_task(resp)
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)
            lcmocc_resp, lcmocc_body = self.show_lcmocc(lcmocc_id)
            self.assertEqual(200, lcmocc_resp.status_code)
            self.assertEqual('COMPLETED', lcmocc_body['operationState'])
            self.assertEqual('HEAL', lcmocc_body['operation'])
            self.assertEqual(False, lcmocc_body['isAutomaticInvocation'])

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

            self.assertNotEqual(
                vdu1_stack_before_heal['physical_resource_id'],
                vdu1_stack_after_heal['physical_resource_id'])
            self.assertNotEqual(
                vdu2_stack_before_heal['physical_resource_id'],
                vdu2_stack_after_heal['physical_resource_id'])

            # Show VNF instance
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

            # check usageState of server notification VNF Package
            self.check_package_usage(self.svn_pkg, 'IN_USE', is_nfvo)

            self.assertEqual(self.svn_id, body['vnfdId'])

            # Heal VNF(vnfc)
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
            resp, body = _lcm_retry(self.heal_vnf_instance, inst_id, heal_req)
            self.assertEqual(202, resp.status_code)
            self.check_resp_headers_in_operation_task(resp)
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)
            lcmocc_resp, lcmocc_body = self.show_lcmocc(lcmocc_id)
            self.assertEqual(200, lcmocc_resp.status_code)
            self.assertEqual('COMPLETED', lcmocc_body['operationState'])
            self.assertEqual('HEAL', lcmocc_body['operation'])
            self.assertEqual(False, lcmocc_body['isAutomaticInvocation'])

            # check stack info
            stack_status, _ = self.heat_client.get_status(stack_name)
            self.assertEqual("UPDATE_COMPLETE", stack_status)
            nested_stacks = self.heat_client.get_resources(stack_name)
            temp_stacks = [stack for stack in nested_stacks if
                (stack['resource_name'] == 'VDU2')]
            vdu2_stack_after_heal = temp_stacks[0]

            self.assertEqual("CREATE_COMPLETE",
                vdu2_stack_after_heal['resource_status'])

            self.assertNotEqual(
                vdu2_stack_before_heal['physical_resource_id'],
                vdu2_stack_after_heal['physical_resource_id'])

            # Show VNF instance
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

            # 5. LCM-Scale (SCALE_OUT)
            # get nested stack count before scaleout
            nested_stacks = self.heat_client.get_resources(stack_name)
            count_before_scaleout = len(nested_stacks)
            scaleout_req = paramgen.scaleout_vnf_min()
            resp, body = _lcm_retry(
                self.scale_vnf_instance, inst_id, scaleout_req)
            self.assertEqual(202, resp.status_code)
            self.check_resp_headers_in_operation_task(resp)
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)
            lcmocc_resp, lcmocc_body = self.show_lcmocc(lcmocc_id)
            self.assertEqual(200, lcmocc_resp.status_code)
            self.assertEqual('COMPLETED', lcmocc_body['operationState'])
            self.assertEqual('SCALE', lcmocc_body['operation'])
            self.assertEqual(False, lcmocc_body['isAutomaticInvocation'])

            # Show VNF instance
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

            # 6. LCM-Scale (SCALE_IN)
            scalein_req = paramgen.scalein_vnf_min()
            resp, body = _lcm_retry(
                self.scale_vnf_instance, inst_id, scalein_req)
            self.assertEqual(202, resp.status_code)
            self.check_resp_headers_in_operation_task(resp)
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)
            lcmocc_resp, lcmocc_body = self.show_lcmocc(lcmocc_id)
            self.assertEqual(200, lcmocc_resp.status_code)
            self.assertEqual('COMPLETED', lcmocc_body['operationState'])
            self.assertEqual('SCALE', lcmocc_body['operation'])
            self.assertEqual(False, lcmocc_body['isAutomaticInvocation'])

            # get nested stack count after scale in
            nested_stacks = self.heat_client.get_resources(stack_name)
            count_after_scalein = len(nested_stacks)
            # check nested stack was deleted
            # 3 was the sum of 1 VM, 1 CP, 1 stack(VDU1.yaml)
            self.assertEqual(3, count_after_scaleout - count_after_scalein)

        # 7. LCM-Terminate
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = _lcm_retry(
            self.terminate_vnf_instance, inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)
        lcmocc_resp, lcmocc_body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, lcmocc_resp.status_code)
        self.assertEqual('COMPLETED', lcmocc_body['operationState'])
        self.assertEqual('TERMINATE', lcmocc_body['operation'])
        self.assertEqual(False, lcmocc_body['isAutomaticInvocation'])

        # check deletion of Heat-stack
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertIsNone(stack_status)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 8. LCM-Delete
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

        # Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # Show subscription
        resp, body = self.show_subscription(sub_id)
        self.assertEqual(404, resp.status_code)

    def test_fault_notification_basic(self):
        self.fault_notification_basic_test()

    def test_fault_notification_queueing(self):
        self.fault_notification_queueing_test()

    def test_fault_notification_disabled(self):
        self.fault_notification_autoheal_disabled_test()
