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

from tacker.tests.functional.sol_v2_common import paramgen
from tacker.tests.functional.sol_v2_common import test_vnflcm_basic_common
from tacker.tests import utils


class AzRetryTest(test_vnflcm_basic_common.CommonVnfLcmTest):

    @classmethod
    def setUpClass(cls):
        super(AzRetryTest, cls).setUpClass()
        image_path = utils.test_etc_sample("etsi/nfv/common/Files/images",
            "cirros-0.5.2-x86_64-disk.img")

        # tacker/tests/functional/sol_v2_az_retry(here)
        #       /sol_refactored
        cur_dir = os.path.dirname(__file__)
        userdata_dir = os.path.join(
            cur_dir, "../../../sol_refactored/infra_drivers/openstack")
        userdata_file = "userdata_standard.py"
        userdata_path = os.path.abspath(
            os.path.join(userdata_dir, userdata_file))

        # for update_stack_retry test
        pkg_path_1 = utils.test_sample(
            "functional/sol_v2_common/userdata_standard_az_retry")
        cls.az_retry_pkg, cls.az_retry_vnfd_id = cls.create_vnf_package(
            pkg_path_1, image_path=image_path, userdata_path=userdata_path)

    @classmethod
    def tearDownClass(cls):
        super(AzRetryTest, cls).tearDownClass()
        cls.delete_vnf_package(cls.az_retry_pkg)

    def setUp(self):
        super().setUp()

    def _get_vdu_indexes(self, inst, vdu):
        return {
            vnfc['metadata'].get('vdu_idx')
            for vnfc in inst['instantiatedVnfInfo']['vnfcResourceInfo']
            if vnfc['vduId'] == vdu
        }

    def _get_vnfc_by_vdu_index(self, inst, vdu, index):
        for vnfc in inst['instantiatedVnfInfo']['vnfcResourceInfo']:
            if (vnfc['vduId'] == vdu and
                    vnfc['metadata'].get('vdu_idx') == index):
                return vnfc

    def _get_vnfc_zone(self, inst, vdu, index):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        return vnfc['metadata'].get('zone')

    def test_update_stack_retry(self):
        """Test _update_stack_retry function using StandardUserData

        * Note:
          This test focuses on recreate the vnfc in another AZ
          if the AZ is not available.

        * About LCM operations:
          This test includes the following operations.
          if it the test was successful, do not run any further tests.
          Also, the second case is scale out VNF instances to 4 times
          and checks the availability zone.
          -    Create VNF instance
          - 1. Instantiate VNF instance
          -    Show VNF instance / check
          - 2. Scale out operation
          -    Show VNF instance / check
          -    Terminate VNF instance
          -    Delete VNF instance
        """

        net_ids = self.get_network_ids(['net0', 'net1', 'net_mgmt'])
        subnet_ids = self.get_subnet_ids(['subnet0', 'subnet1'])

        vdu_idx = 0
        expect_vdu_idx_num = {0}
        inst_result = []

        # Set to the maximum number of VNFC instances
        MAX_SCALE_COUNT = 4

        # Create VNF instance
        create_req = paramgen.sample6_create(self.az_retry_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # 1. Instantiate VNF instance
        instantiate_req = paramgen.sample6_instantiate(
            net_ids, subnet_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Show VNF instance
        resp, inst = self.show_vnf_instance(inst_id)
        inst_result.append(inst)
        self.assertEqual(200, resp.status_code)

        # check number of VDUs and indexes
        self.assertEqual(expect_vdu_idx_num,
                         self._get_vdu_indexes(inst_result[vdu_idx], 'VDU1'))

        while (self._get_vnfc_zone(
                inst_result[vdu_idx], 'VDU1', vdu_idx) != 'nova'
               and vdu_idx < MAX_SCALE_COUNT):

            vdu_idx += 1
            expect_vdu_idx_num.add(vdu_idx)

            # 2. Scale out operation
            scale_out_req = paramgen.sample6_scale_out()
            resp, body = self.scale_vnf_instance(inst_id, scale_out_req)
            self.assertEqual(202, resp.status_code)

            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)

            # Show VNF instance
            resp, inst = self.show_vnf_instance(inst_id)
            inst_result.append(inst)
            self.assertEqual(200, resp.status_code)

            # check number of VDUs and indexes
            self.assertEqual(expect_vdu_idx_num,
                self._get_vdu_indexes(inst_result[vdu_idx], 'VDU1'))

        # check zone of VDUs
        self.assertEqual('nova',
            self._get_vnfc_zone(inst_result[vdu_idx], 'VDU1', vdu_idx))

        # Terminate VNF instance
        terminate_req = paramgen.sample6_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Delete VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)
