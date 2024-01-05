# Copyright (C) 2023 Nippon Telegraph and Telephone Corporation
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

import tacker.conf

from tacker.objects import fields
from tacker.tests.functional.sol_terraform_v2 import base_v2
from tacker.tests.functional.sol_terraform_v2 import paramgen as tf_paramgen
from tacker.tests import utils

CONF = tacker.conf.CONF

WAIT_LCMOCC_UPDATE_TIME = 3


class VnfLcmTerraformTest(base_v2.BaseVnfLcmTerraformV2Test):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmTerraformTest, cls).setUpClass()

        pkg_dir_path = utils.test_sample("functional/sol_terraform_v2",
                                         "test_terraform_basic")
        cls.basic_pkg, cls.basic_vnfd_id = cls.create_vnf_package(pkg_dir_path)

        chg_vnfpkg_dir_path = utils.test_sample("functional/sol_terraform_v2",
            "test_terraform_change_vnf_package")
        cls.new_pkg, cls.new_vnfd_id = cls.create_vnf_package(
            chg_vnfpkg_dir_path)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmTerraformTest, cls).tearDownClass()

        cls.delete_vnf_package(cls.basic_pkg)
        cls.delete_vnf_package(cls.new_pkg)

    def setUp(self):
        super(VnfLcmTerraformTest, self).setUp()

    def test_basic_lcms(self):
        self._get_basic_lcms_procedure()

    def _get_basic_lcms_procedure(self, use_register_vim=False):
        """Test basic LCM operations

        * About LCM operations:
          This test includes the following operations.
          - 1. Create VNF instance
          - 2. Instantiate VNF
          - 3. Show VNF instance
          - 4. Change Current VNF Package
          - 5. Show VNF instance
          - 6. Terminate VNF
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
        create_req = tf_paramgen.create_req_by_vnfd_id(self.basic_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']
        self.check_package_usage(self.basic_pkg, state='IN_USE')

        # 2. Instantiate VNF
        instantiate_req = tf_paramgen.instantiate_req()
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
        self.assertEqual(1, len(before_resource_ids))

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.INSTANTIATED,
                         body['instantiationState'])

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # 4. Change Current VNF Package
        change_vnfpkg_req = tf_paramgen.change_vnfpkg_req(self.new_vnfd_id)
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and change_vnfpkg completion.
        time.sleep(WAIT_LCMOCC_UPDATE_TIME)

        # check usageState of VNF Package
        self.check_package_usage(self.basic_pkg, 'NOT_IN_USE')

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
        self.assertEqual(1, len(after_resource_ids))
        # In other infraDriver, computeResource.resourceId is
        # "assertNotEqual" before and after ChangeCurrentVnfPkg.
        # However, the current Terraform InfraDriver specification
        # sets the same value.
        self.assertEqual(before_resource_ids, after_resource_ids)

        # 6. Terminate VNF instance
        terminate_req = tf_paramgen.terminate_req()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 7. Delete a VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)
        self.check_package_usage(self.basic_pkg, state='NOT_IN_USE')

    def test_change_vnfpkg_rollback(self):
        """Test basic LCM operations

        * About LCM operations:
          This test includes the following operations.
          - 1. Create VNF instance
          - 2. Instantiate VNF
          - 3. Show VNF instance
          - 4. Change Current VNF Package => FAILED_TEMP
          - 5. Rollback Change Current VNF Package
          - 6. Show VNF instance
          - 7. Terminate VNF
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
        create_req = tf_paramgen.create_req_by_vnfd_id(self.basic_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']
        self.check_package_usage(self.basic_pkg, state='IN_USE')

        # 2. Instantiate VNF
        instantiate_req = tf_paramgen.instantiate_req()
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
        self.assertEqual(1, len(before_resource_ids))

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.INSTANTIATED,
                         body['instantiationState'])

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # 4. Change Current VNF Package => FAILED_TEMP
        change_vnfpkg_req = (
            tf_paramgen.change_vnfpkg_fail_req(self.new_vnfd_id))
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
        self.check_package_usage(self.new_pkg, 'NOT_IN_USE')

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
        after_resource_ids = {vnfc_info['computeResource']['resourceId']
                              for vnfc_info in vnfc_resource_infos}
        self.assertEqual(1, len(after_resource_ids))
        self.assertEqual(before_resource_ids, after_resource_ids)

        # 7. Terminate VNF instance
        terminate_req = tf_paramgen.terminate_req()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 8. Delete a VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)
        self.check_package_usage(self.basic_pkg, state='NOT_IN_USE')

    def test_instantiate_rollback(self):
        """Test rollback operation for instantiation.

        * About LCM operations:
          This test includes the following operations.
          - 1. Create VNF instance
          - 2. Instantiate VNF => FAILED_TEMP
          - 3. Show VNF instance
          - 4. Rollback instantiate
          - 5. Show VNF instance
          - 6. Delete a VNF instance
        """

        # 1. Create VNF instance
        create_req = tf_paramgen.create_req_by_vnfd_id(self.basic_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        inst_id = body['id']

        # 2. Instantiate VNF => FAILED_TEMP
        self.put_fail_file('instantiate_end')
        instantiate_req = tf_paramgen.instantiate_req()
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
