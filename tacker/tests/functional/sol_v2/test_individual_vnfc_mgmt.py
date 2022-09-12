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

from tacker.tests.functional.sol_v2_common import paramgen
from tacker.tests.functional.sol_v2_common import test_vnflcm_basic_common


class IndividualVnfcMgmtTest(test_vnflcm_basic_common.CommonVnfLcmTest):

    @classmethod
    def setUpClass(cls):
        super(IndividualVnfcMgmtTest, cls).setUpClass()
        cur_dir = os.path.dirname(__file__)
        # tacker/tests/functional/sol_v2(here)
        #             /etc
        image_dir = os.path.join(
            cur_dir, "../../etc/samples/etsi/nfv/common/Files/images")
        image_file = "cirros-0.5.2-x86_64-disk.img"
        image_path = os.path.abspath(os.path.join(image_dir, image_file))

        # tacker/tests/functional/sol_v2(here)
        #       /sol_refactored
        userdata_dir = os.path.join(
            cur_dir, "../../../sol_refactored/infra_drivers/openstack")
        userdata_file = "userdata_standard.py"
        userdata_path = os.path.abspath(
            os.path.join(userdata_dir, userdata_file))

        # main vnf package for StandardUserData test
        pkg_path_1 = os.path.join(cur_dir,
            "../sol_v2_common/samples/userdata_standard")
        cls.vnf_pkg_1, cls.vnfd_id_1 = cls.create_vnf_package(
            pkg_path_1, image_path=image_path, userdata_path=userdata_path)

        # for change_vnfpkg test
        pkg_path_2 = os.path.join(cur_dir,
            "../sol_v2_common/samples/userdata_standard_change_vnfpkg")
        cls.vnf_pkg_2, cls.vnfd_id_2 = cls.create_vnf_package(
            pkg_path_2, image_path=image_path, userdata_path=userdata_path)

    @classmethod
    def tearDownClass(cls):
        super(IndividualVnfcMgmtTest, cls).tearDownClass()
        cls.delete_vnf_package(cls.vnf_pkg_1)
        cls.delete_vnf_package(cls.vnf_pkg_2)

    def setUp(self):
        super().setUp()

    def _put_fail_file(self, operation):
        with open(f'/tmp/{operation}', 'w'):
            pass

    def _rm_fail_file(self, operation):
        os.remove(f'/tmp/{operation}')

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

    def _get_vnfc_id(self, inst, vdu, index):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        return vnfc['id']

    def _get_vnfc_cp_net_id(self, inst, vdu, index, cp):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        for cp_info in vnfc['vnfcCpInfo']:
            if cp_info['cpdId'] == cp:
                # must be found
                ext_cp_id = cp_info['vnfExtCpId']
                break
        for ext_vl in inst['instantiatedVnfInfo']['extVirtualLinkInfo']:
            for port in ext_vl['extLinkPorts']:
                if port['cpInstanceId'] == ext_cp_id:
                    # must be found
                    return ext_vl['resourceHandle']['resourceId']

    def _get_vnfc_image(self, inst, vdu, index):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        for key, value in vnfc['metadata'].items():
            if key.startswith('image-'):
                # must be found
                return value

    def _delete_instance(self, inst_id):
        for _ in range(3):
            resp, body = self.delete_vnf_instance(inst_id)
            if resp.status_code == 204:  # OK
                return
            elif resp.status_code == 409:
                # may happen. there is a bit time between lcmocc become
                # COMPLETED and lock of terminate is freed.
                time.sleep(3)
            else:
                break
        self.assertTrue(False)

    def test_basic_operations(self):
        """Test basic operations using StandardUserData

        * Note:
          This test focuses whether StandardUserData works well.
          This test does not check overall items of APIs at all.

        * About LCM operations:
          This test includes the following operations.
          -    Create VNF instance
          - 1. Instantiate VNF instance
          -    Show VNF instance / check
          - 2. Scale out operation
          -    Show VNF instance / check
          - 3. Heal operation
          -    Show VNF instance / check
          - 4. Scale in operation
          -    Show VNF instance / check
          - 5. Change_ext_conn operation
          -    Show VNF instance / check
          - 6. Change_vnfpkg operation
          -    Show VNF instance / check
          -    Terminate VNF instance
          -    Delete VNF instance
        """

        net_ids = self.get_network_ids(['net0', 'net1', 'net_mgmt'])
        subnet_ids = self.get_subnet_ids(['subnet0', 'subnet1'])

        # Create VNF instance
        create_req = paramgen.sample3_create(self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # 1. Instantiate VNF instance
        instantiate_req = paramgen.sample3_instantiate(
            net_ids, subnet_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Show VNF instance
        resp, inst_1 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check number of VDUs and indexes
        self.assertEqual({0}, self._get_vdu_indexes(inst_1, 'VDU1'))
        self.assertEqual({0}, self._get_vdu_indexes(inst_1, 'VDU2'))

        # 2. Scale out operation
        scale_out_req = paramgen.sample3_scale_out()
        resp, body = self.scale_vnf_instance(inst_id, scale_out_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Show VNF instance
        resp, inst_2 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check number of VDUs and indexes
        self.assertEqual({0, 1, 2}, self._get_vdu_indexes(inst_2, 'VDU1'))
        self.assertEqual({0}, self._get_vdu_indexes(inst_2, 'VDU2'))

        # 3. Heal operation
        heal_req = paramgen.sample3_heal()
        # pick up VDU1-1 to heal
        vnfc_id = self._get_vnfc_id(inst_2, 'VDU1', 1)
        heal_req['vnfcInstanceId'] = [f'VDU1-{vnfc_id}']
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Show VNF instance
        resp, inst_3 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check id of VDU1-1 is changed and other are not.
        self.assertEqual(self._get_vnfc_id(inst_2, 'VDU1', 0),
                         self._get_vnfc_id(inst_3, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_id(inst_2, 'VDU1', 1),
                            self._get_vnfc_id(inst_3, 'VDU1', 1))
        self.assertEqual(self._get_vnfc_id(inst_2, 'VDU1', 2),
                         self._get_vnfc_id(inst_3, 'VDU1', 2))
        self.assertEqual(self._get_vnfc_id(inst_2, 'VDU2', 0),
                         self._get_vnfc_id(inst_3, 'VDU2', 0))

        # 4. Scale in operation
        scale_in_req = paramgen.sample3_scale_in()
        resp, body = self.scale_vnf_instance(inst_id, scale_in_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Show VNF instance
        resp, inst_4 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check VDU1-2 is removed. other are not changed.
        self.assertEqual({0, 1}, self._get_vdu_indexes(inst_4, 'VDU1'))
        self.assertEqual({0}, self._get_vdu_indexes(inst_4, 'VDU2'))
        self.assertEqual(self._get_vnfc_id(inst_3, 'VDU1', 0),
                         self._get_vnfc_id(inst_4, 'VDU1', 0))
        self.assertEqual(self._get_vnfc_id(inst_3, 'VDU1', 1),
                         self._get_vnfc_id(inst_4, 'VDU1', 1))
        self.assertEqual(self._get_vnfc_id(inst_3, 'VDU2', 0),
                         self._get_vnfc_id(inst_4, 'VDU2', 0))

        # 5. Change_ext_conn operation
        change_ext_conn_req = paramgen.sample3_change_ext_conn(net_ids)
        resp, body = self.change_ext_conn(inst_id, change_ext_conn_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Show VNF instance
        resp, inst_5 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check VDU1_CP1 is changed to net0 from net1. other are not changed.
        self.assertEqual(net_ids['net1'],
            self._get_vnfc_cp_net_id(inst_4, 'VDU1', 0, 'VDU1_CP1'))
        self.assertEqual(net_ids['net1'],
            self._get_vnfc_cp_net_id(inst_4, 'VDU1', 1, 'VDU1_CP1'))
        self.assertEqual(net_ids['net1'],
            self._get_vnfc_cp_net_id(inst_4, 'VDU2', 0, 'VDU2_CP1'))
        self.assertEqual(net_ids['net0'],
            self._get_vnfc_cp_net_id(inst_5, 'VDU1', 0, 'VDU1_CP1'))
        self.assertEqual(net_ids['net0'],
            self._get_vnfc_cp_net_id(inst_5, 'VDU1', 1, 'VDU1_CP1'))
        self.assertEqual(net_ids['net1'],
            self._get_vnfc_cp_net_id(inst_5, 'VDU2', 0, 'VDU2_CP1'))

        # 6. Change_vnfpkg operation
        change_vnfpkg_req = paramgen.sample4_change_vnfpkg(self.vnfd_id_2,
            net_ids, subnet_ids)
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Show VNF instance
        resp, inst_6 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check vnfdId is changed
        self.assertEqual(self.vnfd_id_2, inst_6['vnfdId'])
        # check images are changed
        self.assertNotEqual(self._get_vnfc_image(inst_5, 'VDU1', 0),
                            self._get_vnfc_image(inst_6, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_image(inst_5, 'VDU1', 1),
                            self._get_vnfc_image(inst_6, 'VDU1', 1))
        self.assertNotEqual(self._get_vnfc_image(inst_5, 'VDU2', 0),
                            self._get_vnfc_image(inst_6, 'VDU2', 0))
        # check VDU2_CP1 is changed to net0 from net1. other are not changed.
        self.assertEqual(net_ids['net0'],
            self._get_vnfc_cp_net_id(inst_5, 'VDU1', 0, 'VDU1_CP1'))
        self.assertEqual(net_ids['net0'],
            self._get_vnfc_cp_net_id(inst_5, 'VDU1', 1, 'VDU1_CP1'))
        self.assertEqual(net_ids['net1'],
            self._get_vnfc_cp_net_id(inst_5, 'VDU2', 0, 'VDU2_CP1'))
        self.assertEqual(net_ids['net0'],
            self._get_vnfc_cp_net_id(inst_6, 'VDU1', 0, 'VDU1_CP1'))
        self.assertEqual(net_ids['net0'],
            self._get_vnfc_cp_net_id(inst_6, 'VDU1', 1, 'VDU1_CP1'))
        self.assertEqual(net_ids['net0'],
            self._get_vnfc_cp_net_id(inst_6, 'VDU2', 0, 'VDU2_CP1'))

        # Terminate VNF instance
        terminate_req = paramgen.sample4_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Delete VNF instance
        self._delete_instance(inst_id)

    def test_rollback_operations(self):
        """Test rollback operations using StandardUserData

        * Note:
          This test focuses whether StandardUserData works well.
          This test does not check overall items of APIs at all.

        * About LCM operations:
          This test includes the following operations.
          -    Create VNF instance
          -    Instantiate VNF instance
          -    Show VNF instance
          - 1. Scale out operation => FAILED_TEMP
          -    Rollback
          -    Show VNF instance / check
          - 2. Change_ext_conn operation => FAILED_TEMP
          -    Rollback
          -    Show VNF instance / check
          - 3. Change_vnfpkg operation => FAILED_TEMP
          -    Rollback
          -    Show VNF instance / check
          -    Terminate VNF instance
          -    Delete VNF instance
        """

        net_ids = self.get_network_ids(['net0', 'net1', 'net_mgmt'])
        subnet_ids = self.get_subnet_ids(['subnet0', 'subnet1'])

        # Create VNF instance
        create_req = paramgen.sample3_create(self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # Instantiate VNF instance
        instantiate_req = paramgen.sample3_instantiate(
            net_ids, subnet_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Show VNF instance
        resp, inst_0 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # 1. Scale out operation
        self._put_fail_file('scale_end')
        scale_out_req = paramgen.sample3_scale_out()
        resp, body = self.scale_vnf_instance(inst_id, scale_out_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)
        self._rm_fail_file('scale_end')

        # Rollback
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # Show VNF instance
        resp, inst_1 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check number of vnfc and its id are not changed.
        self.assertEqual(self._get_vdu_indexes(inst_0, 'VDU1'),
                         self._get_vdu_indexes(inst_1, 'VDU1'))
        self.assertEqual(self._get_vdu_indexes(inst_0, 'VDU2'),
                         self._get_vdu_indexes(inst_1, 'VDU2'))
        self.assertEqual(self._get_vnfc_id(inst_0, 'VDU1', 0),
                         self._get_vnfc_id(inst_1, 'VDU1', 0))
        self.assertEqual(self._get_vnfc_id(inst_0, 'VDU2', 0),
                         self._get_vnfc_id(inst_1, 'VDU2', 0))

        # 2. Change_ext_conn operation
        self._put_fail_file('change_external_connectivity_end')
        change_ext_conn_req = paramgen.sample3_change_ext_conn(net_ids)
        resp, body = self.change_ext_conn(inst_id, change_ext_conn_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)
        self._rm_fail_file('change_external_connectivity_end')

        # Rollback
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # Show VNF instance
        resp, inst_2 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check network of extVL cps are not changed. (i.e. net1)
        self.assertEqual(net_ids['net1'],
            self._get_vnfc_cp_net_id(inst_2, 'VDU1', 0, 'VDU1_CP1'))
        self.assertEqual(net_ids['net1'],
            self._get_vnfc_cp_net_id(inst_2, 'VDU2', 0, 'VDU2_CP1'))

        # 3. Change_vnfpkg operation
        self._put_fail_file('change_vnfpkg')
        change_vnfpkg_req = paramgen.sample4_change_vnfpkg(self.vnfd_id_2,
            net_ids, subnet_ids)
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)
        self._rm_fail_file('change_vnfpkg')

        # Rollback
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # Show VNF instance
        resp, inst_3 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check vnfdId is not changed
        self.assertEqual(self.vnfd_id_1, inst_3['vnfdId'])
        # check images are not changed
        self.assertEqual(self._get_vnfc_image(inst_2, 'VDU1', 0),
                         self._get_vnfc_image(inst_3, 'VDU1', 0))
        self.assertEqual(self._get_vnfc_image(inst_2, 'VDU2', 0),
                         self._get_vnfc_image(inst_3, 'VDU2', 0))
        # check network of extVL cps are not changed. (i.e. net1)
        self.assertEqual(net_ids['net1'],
            self._get_vnfc_cp_net_id(inst_3, 'VDU1', 0, 'VDU1_CP1'))
        self.assertEqual(net_ids['net1'],
            self._get_vnfc_cp_net_id(inst_3, 'VDU2', 0, 'VDU2_CP1'))

        # Terminate VNF instance
        terminate_req = paramgen.sample3_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Delete VNF instance
        self._delete_instance(inst_id)
