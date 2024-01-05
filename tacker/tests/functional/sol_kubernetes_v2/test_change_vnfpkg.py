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

import os
import time

from tacker.tests.functional.sol_kubernetes_v2 import base_v2
from tacker.tests.functional.sol_kubernetes_v2 import paramgen
from tacker.tests import utils

WAIT_LCMOCC_UPDATE_TIME = 3


class VnfLcmKubernetesChangeVnfpkgTest(base_v2.BaseVnfLcmKubernetesV2Test):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmKubernetesChangeVnfpkgTest, cls).setUpClass()

        test_instantiate_cnf_resources_path = utils.test_sample(
            "functional/sol_kubernetes_v2/test_instantiate_cnf_resources")
        cls.old_pkg, cls.old_vnfd_id = cls.create_vnf_package(
            test_instantiate_cnf_resources_path)

        test_change_vnf_pkg_with_deployment_path = utils.test_sample(
            "functional/sol_kubernetes_v2/test_change_vnf_pkg_with_deployment")
        cls.new_pkg, cls.new_vnfd_id = cls.create_vnf_package(
            test_change_vnf_pkg_with_deployment_path)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmKubernetesChangeVnfpkgTest, cls).tearDownClass()

        cls.delete_vnf_package(cls.old_pkg)
        cls.delete_vnf_package(cls.new_pkg)

    def setUp(self):
        super(VnfLcmKubernetesChangeVnfpkgTest, self).setUp()

    def test_change_vnfpkg_for_deployment_res(self):
        """Test ChangeCurrentVNFPackage

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
            self.old_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        self.check_package_usage(self.old_pkg, 'IN_USE')

        # 2. Instantiate a VNF instance
        instantiate_req = paramgen.change_vnfpkg_instantiate(
            self.auth_url, self.bearer_token)
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
        before_resource_ids = {vnfc_info['computeResource']['resourceId']
                               for vnfc_info in vnfc_resource_infos}
        self.assertEqual(2, len(before_resource_ids))

        # 4. Change Current VNF Package
        change_vnfpkg_req = paramgen.change_vnfpkg(self.new_vnfd_id)
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)
        time.sleep(WAIT_LCMOCC_UPDATE_TIME)

        # check usageState of VNF Package
        self.check_package_usage(self.old_pkg, 'NOT_IN_USE')

        # check usageState of VNF Package
        self.check_package_usage(self.new_pkg, 'IN_USE')

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

        vnfc_resource_infos = body['instantiatedVnfInfo']['vnfcResourceInfo']
        after_resource_ids = {vnfc_info['computeResource']['resourceId']
                              for vnfc_info in vnfc_resource_infos}
        self.assertEqual(2, len(after_resource_ids))
        self.assertNotEqual(before_resource_ids, after_resource_ids)

        # 6. Terminate a VNF instance
        terminate_req = paramgen.change_vnfpkg_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 7. Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

        # check usageState of VNF Package
        self.check_package_usage(self.new_pkg, 'NOT_IN_USE')

    def test_change_vnfpkg_failed_and_rollback(self):
        """Test LCM operations error handing

        * About LCM operations:
          This test includes the following operations.
          - 1. Create a new VNF instance resource
          - 2. Instantiate a VNF instance
          - 3. Show VNF instance
          - 4. Change Current VNF Package
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
        create_req = paramgen.test_instantiate_cnf_resources_create(
            self.old_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        self.check_package_usage(self.old_pkg, 'IN_USE')

        # 2. Instantiate a VNF instance
        instantiate_req = paramgen.change_vnfpkg_instantiate(
            self.auth_url, self.bearer_token)
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
        before_resource_ids = [vnfc_info['computeResource']['resourceId']
                            for vnfc_info in vnfc_resource_infos]

        # 4. Change Current VNF Package (will fail)
        change_vnfpkg_req = paramgen.change_vnfpkg_error(self.new_vnfd_id)
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)

        # 5. Rollback Change Current VNF Package operation
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        self.wait_lcmocc_rolled_back(lcmocc_id)

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
        after_resource_ids = [vnfc_info['computeResource']['resourceId']
                              for vnfc_info in vnfc_resource_infos]
        self.assertEqual(before_resource_ids, after_resource_ids)

        # 7. Terminate a VNF instance
        terminate_req = paramgen.change_vnfpkg_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 8. Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)

        # check usageState of VNF Package
        self.check_package_usage(self.new_pkg, 'NOT_IN_USE')
