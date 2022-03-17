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
import time

from tacker.tests.functional.sol_kubernetes_v2 import base_v2
from tacker.tests.functional.sol_kubernetes_v2 import paramgen


@ddt.ddt
class VnfLcmKubernetesChangeVnfpkgTest(base_v2.BaseVnfLcmKubernetesV2Test):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmKubernetesChangeVnfpkgTest, cls).setUpClass()

        cur_dir = os.path.dirname(__file__)

        test_instantiate_cnf_resources_path = os.path.join(
            cur_dir, "samples/test_instantiate_cnf_resources")
        cls.vnf_pkg_1, cls.vnfd_id_1 = cls.create_vnf_package(
            test_instantiate_cnf_resources_path)

        test_change_vnf_pkg_with_deployment_path = os.path.join(
            cur_dir, "samples/test_change_vnf_pkg_with_deployment")
        cls.vnf_pkg_2, cls.vnfd_id_2 = cls.create_vnf_package(
            test_change_vnf_pkg_with_deployment_path)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmKubernetesChangeVnfpkgTest, cls).tearDownClass()

        cls.delete_vnf_package(cls.vnf_pkg_1)
        cls.delete_vnf_package(cls.vnf_pkg_2)

    def setUp(self):
        super(VnfLcmKubernetesChangeVnfpkgTest, self).setUp()

    def test_change_vnfpkg_for_deployment_res_with_all_params(self):
        """Test ChangeCurrentVNFPackage with all attributes set

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
          - 4. Change Current VNF Package
          - 5. Show VNF instance
          - 6. Terminate a VNF instance
          - 7. Delete a VNF instance
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
        instantiate_req = paramgen.change_vnfpkg_instantiate(
            self.auth_url, self.bearer_token)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check vnfc_resource_info
        # TODO()

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

        vnfc_resource_infos = body['instantiatedVnfInfo'].get(
            'vnfcResourceInfo')
        before_resource_ids = [vnfc_info['computeResource']['resourceId']
                            for vnfc_info in vnfc_resource_infos]

        # 4. Change Current VNF Package
        change_vnfpkg_req = paramgen.change_vnfpkg_all_params(self.vnfd_id_2)
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1).get('usageState')
        self.assertEqual('NOT_IN_USE', usage_state)
        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_2).get('usageState')
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

        vnfc_resource_infos = body['instantiatedVnfInfo'].get(
            'vnfcResourceInfo')
        after_resource_ids = [vnfc_info['computeResource']['resourceId']
                              for vnfc_info in vnfc_resource_infos]
        self.assertNotEqual(before_resource_ids, after_resource_ids)

        # 6. Terminate a VNF instance
        terminate_req = paramgen.max_sample_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        # 7. Delete a VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_2).get('usageState')
        self.assertEqual('NOT_IN_USE', usage_state)

    def test_change_vnfpkg_for_deployment_res_with_no_op_params(self):
        """Test ChangeCurrentVNFPackage with no optional attributes

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
          - 4. Change Current VNF Package
          - 5. Show VNF instance
          - 6. Terminate a VNF instance
          - 7. Delete a VNF instance
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
        vim_id = self.get_k8s_vim_id()
        instantiate_req = paramgen.change_vnfpkg_instantiate_min(vim_id)
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

        vnfc_resource_infos = body['instantiatedVnfInfo'].get(
            'vnfcResourceInfo')
        before_resource_ids = [vnfc_info['computeResource']['resourceId']
                            for vnfc_info in vnfc_resource_infos]

        # 4. Change Current VNF Package
        change_vnfpkg_req = paramgen.change_vnfpkg_min(self.vnfd_id_2)
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_1).get('usageState')
        self.assertEqual('NOT_IN_USE', usage_state)
        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_2).get('usageState')
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

        vnfc_resource_infos = body['instantiatedVnfInfo'].get(
            'vnfcResourceInfo')
        after_resource_ids = [vnfc_info['computeResource']['resourceId']
                              for vnfc_info in vnfc_resource_infos]
        self.assertNotEqual(before_resource_ids, after_resource_ids)

        # 6. Terminate a VNF instance
        terminate_req = paramgen.max_sample_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        # 7. Delete a VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

        # check usageState of VNF Package
        usage_state = self.get_vnf_package(self.vnf_pkg_2).get('usageState')
        self.assertEqual('NOT_IN_USE', usage_state)
