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

import tacker.conf

from tacker.objects import fields
from tacker.tests.functional.sol_terraform_v2 import base_v2
from tacker.tests.functional.sol_terraform_v2 import paramgen as tf_paramgen

CONF = tacker.conf.CONF


class VnfLcmTerraformTest(base_v2.BaseVnfLcmTerraformV2Test):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmTerraformTest, cls).setUpClass()

        cur_dir = os.path.dirname(__file__)
        sample_pkg = "samples/test_terraform_basic"
        pkg_dir_path = os.path.join(cur_dir, sample_pkg)
        cls.basic_pkg, cls.basic_vnfd_id = cls.create_vnf_package(pkg_dir_path)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmTerraformTest, cls).tearDownClass()

        cls.delete_vnf_package(cls.basic_pkg)

    def setUp(self):
        super(VnfLcmTerraformTest, self).setUp()

    def instantiate_vnf_instance(self, inst_id, req_body):
        path = "/vnflcm/v2/vnf_instances/{}/instantiate".format(inst_id)
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def terminate_vnf_instance(self, inst_id, req_body):
        path = "/vnflcm/v2/vnf_instances/{}/terminate".format(inst_id)
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def test_basic_lcms(self):
        self._get_basic_lcms_procedure()

    def _get_basic_lcms_procedure(self, use_register_vim=False):
        """Test basic LCM operations

        * About LCM operations:
          This test includes the following operations.
          - 1. Create VNF instance
          - 2. Instantiate VNF
          - 3. Show VNF instance
          - 4. Terminate VNF
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

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.INSTANTIATED,
                         body['instantiationState'])

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # 4. Terminate VNF instance
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

        # 5. Delete a VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # check deletion of VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(404, resp.status_code)
        self.check_package_usage(self.basic_pkg, state='NOT_IN_USE')

        # TODO(yasufum) consider to add a test for instantiate_rollback here.
