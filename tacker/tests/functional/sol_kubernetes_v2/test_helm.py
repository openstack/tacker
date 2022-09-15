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

import os
import time

from tacker.tests.functional.sol_kubernetes_v2 import base_v2
from tacker.tests.functional.sol_kubernetes_v2 import paramgen


class VnfLcmHelmTest(base_v2.BaseVnfLcmKubernetesV2Test):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmHelmTest, cls).setUpClass()

        cur_dir = os.path.dirname(__file__)

        test_helm_instantiate_path = os.path.join(
            cur_dir, "samples/test_helm_instantiate")
        cls.vnf_pkg_1, cls.vnfd_id_1 = cls.create_vnf_package(
            test_helm_instantiate_path)

        test_helm_change_vnf_pkg_path = os.path.join(
            cur_dir, "samples/test_helm_change_vnf_pkg")
        cls.vnf_pkg_2, cls.vnfd_id_2 = cls.create_vnf_package(
            test_helm_change_vnf_pkg_path)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmHelmTest, cls).tearDownClass()

        cls.delete_vnf_package(cls.vnf_pkg_1)
        cls.delete_vnf_package(cls.vnf_pkg_2)

    def setUp(self):
        super(VnfLcmHelmTest, self).setUp()

    def test_basic_lcms(self):
        """Test basic LCM operations

        * About LCM operations:
          This test includes the following operations.
          - 1. Create a new VNF instance resource
          - 2. Instantiate a VNF instance
          - 3. Show VNF instance
          - 4. Scale out a VNF instance
          - 5. Show VNF instance
          - 6. Scale in a VNF instance
          - 7. Show VNF instance
          - 8. Heal in a VNF instance
          - 9. Show VNF instance
          - 10. Change Current VNF Package
          - 11. Show VNF instance
          - 12. Terminate a VNF instance
          - 13. Delete a VNF instance
        """

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
        create_req = paramgen.test_helm_instantiate_create(
            self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # 2. Instantiate a VNF instance
        instantiate_req = paramgen.helm_instantiate(
            self.auth_url, self.bearer_token, self.ssl_ca_cert)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

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

        # check vnfc_resource_info
        vnfc_resource_infos = body['instantiatedVnfInfo']['vnfcResourceInfo']
        vdu_nums = {'VDU1': 0, 'VDU2': 0}
        for vnfc_info in vnfc_resource_infos:
            if vnfc_info['vduId'] == 'VDU1':
                self.assertEqual('Deployment', vnfc_info[
                    'computeResource']['vimLevelResourceType'])
                vdu_nums['VDU1'] += 1
            elif vnfc_info['vduId'] == 'VDU2':
                self.assertEqual('Deployment', vnfc_info[
                    'computeResource']['vimLevelResourceType'])
                vdu_nums['VDU2'] += 1
        expected = {'VDU1': 1, 'VDU2': 1}
        self.assertEqual(expected, vdu_nums)

        # 4. Scale out a VNF instance
        scale_out_req = paramgen.helm_scale_out()
        resp, body = self.scale_vnf_instance(inst_id, scale_out_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 5. Show VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)

        # check vnfc_resource_info
        vnfc_resource_infos = body['instantiatedVnfInfo']['vnfcResourceInfo']
        vdu2_infos = [vnfc_info for vnfc_info in vnfc_resource_infos
                if vnfc_info['vduId'] == 'VDU2']
        self.assertEqual(3, len(vdu2_infos))

        # 6. Scale in a VNF instance
        scale_in_req = paramgen.helm_scale_in()
        resp, body = self.scale_vnf_instance(inst_id, scale_in_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 7. Show VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)

        # check vnfc_resource_info
        vnfc_resource_infos = body['instantiatedVnfInfo']['vnfcResourceInfo']
        vdu2_infos = [vnfc_info for vnfc_info in vnfc_resource_infos
                if vnfc_info['vduId'] == 'VDU2']
        self.assertEqual(2, len(vdu2_infos))

        # 8. Heal a VNF instance
        vnfc_infos = body['instantiatedVnfInfo']['vnfcInfo']
        vdu2_ids = [vnfc_info['id'] for vnfc_info in vnfc_infos
            if vnfc_info['vduId'] == 'VDU2']
        target = [vdu2_ids[0]]
        heal_req = paramgen.helm_heal(target)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 9. Show VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)

        # check vnfc_resource_info
        vnfc_infos = body['instantiatedVnfInfo']['vnfcInfo']
        result_vdu2_ids = [vnfc_info['id'] for vnfc_info in vnfc_infos
            if vnfc_info['vduId'] == 'VDU2']
        self.assertEqual(2, len(result_vdu2_ids))
        self.assertNotIn(vdu2_ids[0], result_vdu2_ids)
        self.assertIn(vdu2_ids[1], result_vdu2_ids)

        # 10. Change Current VNF Package
        vnfc_resource_infos = body['instantiatedVnfInfo']['vnfcResourceInfo']
        before_vdu2_ids = [vnfc_info['id'] for vnfc_info in vnfc_resource_infos
                           if vnfc_info['vduId'] == 'VDU2']
        change_vnfpkg_req = paramgen.helm_change_vnfpkg(self.vnfd_id_2)
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)
        time.sleep(3)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1).get('usageState')
        self.assertEqual('NOT_IN_USE', usage_state)
        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_2).get('usageState')
        self.assertEqual('IN_USE', usage_state)

        # 11. Show VNF instance
        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        vnfc_resource_infos = body['instantiatedVnfInfo']['vnfcResourceInfo']
        after_vdu2_ids = [vnfc_info['id'] for vnfc_info in vnfc_resource_infos
                         if vnfc_info['vduId'] == 'VDU2']
        self.assertEqual(2, len(after_vdu2_ids))
        self.assertNotEqual(before_vdu2_ids, after_vdu2_ids)

        # 12. Terminate a VNF instance
        terminate_req = paramgen.helm_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(3)

        # 13. Delete a VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1).get('usageState')
        self.assertEqual('NOT_IN_USE', usage_state)

    def _put_fail_file(self, operation):
        with open(f'/tmp/{operation}', 'w'):
            pass

    def _rm_fail_file(self, operation):
        os.remove(f'/tmp/{operation}')

    def test_instantiate_rollback(self):
        """Test LCM operations with all attributes set

        * About LCM operations:
          This test includes the following operations.
          - 1. Create a new VNF instance resource
          - 2. Instantiate a VNF instance => FAILED_TEMP
          - 3. Show VNF instance
          - 4. Rollback instantiate
          - 5. Show VNF instance
          - 6. Delete a VNF instance
        """

        # 1. Create a new VNF instance resource
        create_req = paramgen.test_helm_instantiate_create(
            self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        inst_id = body['id']

        # 2. Instantiate a VNF instance => FAILED_TEMP
        self._put_fail_file('instantiate_end')
        instantiate_req = paramgen.helm_instantiate(
            self.auth_url, self.bearer_token, self.ssl_ca_cert)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)
        self._rm_fail_file('instantiate_end')

        # 3. Show VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.assertEqual('NOT_INSTANTIATED', body['instantiationState'])

        # 4. Rollback instantiate
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # 5. Show VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.assertEqual('NOT_INSTANTIATED', body['instantiationState'])

        # 6. Delete a VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

    def test_scale_out_rollback(self):
        """Test LCM operations with all attributes set

        * About LCM operations:
          This test includes the following operations.
          - 1. Create a new VNF instance resource
          - 2. Instantiate a VNF instance
          - 3. Show VNF instance
          - 4. Scale out a VNF instance => FAILED_TEMP
          - 5. Rollback scale out
          - 6. Show VNF instance
          - 7. Terminate a VNF instance
          - 8. Delete a VNF instance
        """

        # 1. Create a new VNF instance resource
        create_req = paramgen.test_helm_instantiate_create(
            self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        inst_id = body['id']

        # 2. Instantiate a VNF instance
        instantiate_req = paramgen.helm_instantiate(
            self.auth_url, self.bearer_token, self.ssl_ca_cert)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 3. Show VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)

        vnfc_resource_infos = body['instantiatedVnfInfo']['vnfcResourceInfo']
        vdu2_ids_0 = {vnfc_info['id'] for vnfc_info in vnfc_resource_infos
                      if vnfc_info['vduId'] == 'VDU2'}
        self.assertEqual(1, len(vdu2_ids_0))

        # 4. Scale out a VNF instance => FAILED_TEMP
        self._put_fail_file('scale_end')
        scale_out_req = paramgen.helm_scale_out()
        resp, body = self.scale_vnf_instance(inst_id, scale_out_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)
        self._rm_fail_file('scale_end')

        # 5. Rollback scale out
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # 6. Show VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)

        vnfc_resource_infos = body['instantiatedVnfInfo']['vnfcResourceInfo']
        vdu2_ids_1 = {vnfc_info['id'] for vnfc_info in vnfc_resource_infos
                      if vnfc_info['vduId'] == 'VDU2'}
        self.assertEqual(vdu2_ids_0, vdu2_ids_1)

        # 7. Terminate a VNF instance
        terminate_req = paramgen.helm_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(3)

        # 8. Delete a VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

    def test_change_vnfpkg_rollback(self):
        """Test LCM operations error handing

        * About LCM operations:
          This test includes the following operations.
          - 1. Create a new VNF instance resource
          - 2. Instantiate a VNF instance
          - 3. Show VNF instance
          - 4. Change Current VNF Package => FAILED_TEMP
          - 5. Rollback Change Current VNF Package
          - 6. Show VNF instance
          - 7. Terminate a VNF instance
          - 8. Delete a VNF instance
        """

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
        create_req = paramgen.test_helm_instantiate_create(
            self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1)['usageState']
        self.assertEqual('IN_USE', usage_state)

        # 2. Instantiate a VNF instance
        instantiate_req = paramgen.helm_instantiate(
            self.auth_url, self.bearer_token, self.ssl_ca_cert)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

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

        vnfc_resource_infos = body['instantiatedVnfInfo']['vnfcResourceInfo']
        before_vdu2_ids = [vnfc_info['id'] for vnfc_info in vnfc_resource_infos
                           if vnfc_info['vduId'] == 'VDU2']

        # 4. Change Current VNF Package => FAILED_TEMP
        change_vnfpkg_req = paramgen.helm_error_handling_change_vnfpkg(
            self.vnfd_id_2)
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)

        # 5. Rollback Change Current VNF Package
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_2).get('usageState')
        self.assertEqual('NOT_IN_USE', usage_state)

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

        vnfc_resource_infos = body['instantiatedVnfInfo']['vnfcResourceInfo']
        after_vdu2_ids = [vnfc_info['id'] for vnfc_info in vnfc_resource_infos
                          if vnfc_info['vduId'] == 'VDU2']
        self.assertEqual(before_vdu2_ids, after_vdu2_ids)

        # 7. Terminate a VNF instance
        terminate_req = paramgen.helm_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(3)

        # 8. Delete a VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)
