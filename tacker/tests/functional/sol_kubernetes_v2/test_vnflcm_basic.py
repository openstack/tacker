# Copyright (C) 2022 FUJITSU
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

from tacker.tests.functional.sol_kubernetes_v2 import base_v2
from tacker.tests.functional.sol_kubernetes_v2 import paramgen
from tacker.tests import utils


@ddt.ddt
class VnfLcmKubernetesTest(base_v2.BaseVnfLcmKubernetesV2Test):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmKubernetesTest, cls).setUpClass()

        test_instantiate_cnf_resources_path = utils.test_sample(
            "functional/sol_kubernetes_v2/test_instantiate_cnf_resources")
        cls.cnf_pkg, cls.cnf_vnfd_id = cls.create_vnf_package(
            test_instantiate_cnf_resources_path)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmKubernetesTest, cls).tearDownClass()

        cls.delete_vnf_package(cls.cnf_pkg)

    def setUp(self):
        super(VnfLcmKubernetesTest, self).setUp()

    def _get_vdu_label(self, inst_vnf_info, vdu_id):
        vdu_reses = inst_vnf_info['metadata']['vdu_reses']
        return vdu_reses[vdu_id]['metadata'].get(
            'labels', {}).get('tacker_vnf_instance_id')

    def test_basic_lcms_max(self):
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
          - 1. Create a new VNF instance resource
          - 2. Instantiate a VNF instance
          - 3. Show VNF instance
          - 4. Scale out a VNF instance
          - 5. Show VNF instance
          - 6. Scale in a VNF instance
          - 7. Show VNF instance
          - 8. Heal in a VNF instance
          - 9. Show VNF instance
          - 10. Terminate a VNF instance
          - 11. Delete a VNF instance
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
        create_req = paramgen.test_instantiate_cnf_resources_create(
            self.cnf_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        self.check_package_usage(self.cnf_pkg, 'IN_USE')

        # 2. Instantiate a VNF instance
        instantiate_req = paramgen.max_sample_instantiate(
            self.auth_url, self.bearer_token, ssl_ca_cert=self.ssl_ca_cert)
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
        vdu_nums = {'VDU1': 0, 'VDU2': 0, 'VDU3': 0, 'VDU5': 0, 'VDU6': 0}
        for vnfc_info in vnfc_resource_infos:
            if vnfc_info['vduId'] == 'VDU1':
                self.assertEqual('Pod', vnfc_info[
                    'computeResource']['vimLevelResourceType'])
                vdu_nums['VDU1'] += 1
            elif vnfc_info['vduId'] == 'VDU2':
                self.assertEqual('Deployment', vnfc_info[
                    'computeResource']['vimLevelResourceType'])
                vdu_nums['VDU2'] += 1
            elif vnfc_info['vduId'] == 'VDU3':
                self.assertEqual('ReplicaSet', vnfc_info[
                    'computeResource']['vimLevelResourceType'])
                vdu_nums['VDU3'] += 1
            elif vnfc_info['vduId'] == 'VDU5':
                self.assertEqual('StatefulSet', vnfc_info[
                    'computeResource']['vimLevelResourceType'])
                vdu_nums['VDU5'] += 1
            elif vnfc_info['vduId'] == 'VDU6':
                self.assertEqual('DaemonSet', vnfc_info[
                    'computeResource']['vimLevelResourceType'])
                vdu_nums['VDU6'] += 1
        expected = {'VDU1': 1, 'VDU2': 2, 'VDU3': 1, 'VDU5': 1, 'VDU6': 1}
        self.assertEqual(expected, vdu_nums)

        # check VDU label
        inst_vnf_info = body['instantiatedVnfInfo']
        self.assertEqual(inst_id, self._get_vdu_label(inst_vnf_info, 'VDU1'))
        self.assertEqual(inst_id, self._get_vdu_label(inst_vnf_info, 'VDU2'))
        self.assertEqual(inst_id, self._get_vdu_label(inst_vnf_info, 'VDU3'))
        self.assertEqual(inst_id, self._get_vdu_label(inst_vnf_info, 'VDU5'))
        self.assertEqual(inst_id, self._get_vdu_label(inst_vnf_info, 'VDU6'))

        # 4. Scale out a VNF instance
        scale_out_req = paramgen.max_sample_scale_out()
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
        vdu3_infos = [vnfc_info for vnfc_info in vnfc_resource_infos
                if vnfc_info['vduId'] == 'VDU3']
        self.assertEqual(3, len(vdu3_infos))

        # 6. Scale in a VNF instance
        scale_in_req = paramgen.max_sample_scale_in()
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
        vdu3_infos = [vnfc_info for vnfc_info in vnfc_resource_infos
                if vnfc_info['vduId'] == 'VDU3']
        self.assertEqual(2, len(vdu3_infos))

        # 8. Heal a VNF instance
        vnfc_infos = body['instantiatedVnfInfo']['vnfcInfo']
        vdu2_ids = [vnfc_info['id'] for vnfc_info in vnfc_infos
            if vnfc_info['vduId'] == 'VDU2']
        target = [vdu2_ids[0]]
        heal_req = paramgen.max_sample_heal(target)
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

        # 10. Terminate a VNF instance
        terminate_req = paramgen.max_sample_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 11. Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

        # check usageState of VNF Package
        self.check_package_usage(self.cnf_pkg, 'NOT_IN_USE')

    def test_basic_lcms_min(self):
        """Test LCM operations with all attributes set

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
        create_req = paramgen.test_instantiate_cnf_resources_create(
            self.cnf_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        self.check_package_usage(self.cnf_pkg, 'IN_USE')

        # 2. Instantiate a VNF instance
        vim_id = self.get_k8s_vim_id()
        instantiate_req = paramgen.min_sample_instantiate(vim_id)
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
        vnfc_resource_infos = body['instantiatedVnfInfo'].get(
            'vnfcResourceInfo')
        self.assertEqual(1, len(vnfc_resource_infos))

        # 4. Terminate a VNF instance
        terminate_req = paramgen.max_sample_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 5. Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

        # check usageState of VNF Package
        self.check_package_usage(self.cnf_pkg, 'NOT_IN_USE')

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
        create_req = paramgen.test_instantiate_cnf_resources_create(
            self.cnf_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        inst_id = body['id']

        # 2. Instantiate a VNF instance
        self.put_fail_file('instantiate_end')
        instantiate_req = paramgen.error_handling_instantiate(
            self.auth_url, self.bearer_token)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)
        self.rm_fail_file('instantiate_end')

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
          - 4. Scale out ==> FAILED_TEMP
          - 5. Rollback
          - 5. Show VNF instance
          - 6. Terminate a VNF instance
          - 7. Delete a VNF instance
        """

        # 1. Create a new VNF instance resource
        create_req = paramgen.test_instantiate_cnf_resources_create(
            self.cnf_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        inst_id = body['id']

        # 2. Instantiate a VNF instance
        instantiate_req = paramgen.error_handling_instantiate(
            self.auth_url, self.bearer_token)
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
        self.assertEqual(2, len(vdu2_ids_0))

        # 4. Scale out a VNF instance
        self.put_fail_file('scale_end')
        scale_out_req = paramgen.error_handling_scale_out()
        resp, body = self.scale_vnf_instance(inst_id, scale_out_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)
        self.rm_fail_file('scale_end')

        # 5. Rollback instantiate
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
        terminate_req = paramgen.error_handling_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 8. Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)
