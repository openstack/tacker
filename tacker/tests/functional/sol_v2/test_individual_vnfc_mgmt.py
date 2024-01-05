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
import subprocess

import tacker.conf
from tacker.tests.functional.sol_v2_common import paramgen
from tacker.tests.functional.sol_v2_common import test_vnflcm_basic_common
from tacker.tests import utils


CONF = tacker.conf.CONF


def _create_coordinate_response(req_header, req_body):

    resp_body = {
        'id': 'aeca5328-085c-4cd6-a6f4-c010e9082528',
        'coordinationResult': 'CONTINUE',
        'vnfInstanceId': req_body.get('vnfInstanceId'),
        'vnfLcmOpOccId': req_body.get('vnfLcmOpOccId'),
        'lcmOperationType': req_body.get('lcmOperationType'),
        'coordinationActionName': req_body.get('coordinationActionName'),
        '_links': req_body.get('_links')
    }

    return resp_body


class IndividualVnfcMgmtTest(test_vnflcm_basic_common.CommonVnfLcmTest):

    @classmethod
    def setUpClass(cls):
        super(IndividualVnfcMgmtTest, cls).setUpClass()
        image_path = utils.test_etc_sample("etsi/nfv/common/Files/images",
            "cirros-0.5.2-x86_64-disk.img")

        # tacker/tests/functional/sol_v2(here)
        #       /sol_refactored
        cur_dir = os.path.dirname(__file__)
        userdata_dir = os.path.join(
            cur_dir, "../../../sol_refactored/infra_drivers/openstack")
        userdata_file = "userdata_standard.py"
        userdata_path = os.path.abspath(
            os.path.join(userdata_dir, userdata_file))

        # main vnf package for StandardUserData test
        pkg_path_1 = utils.test_sample("functional/sol_v2_common",
                                       "userdata_standard")
        cls.standard_pkg, cls.standard_vnfd_id = cls.create_vnf_package(
            pkg_path_1, image_path=image_path, userdata_path=userdata_path)

        # for change_vnfpkg test
        pkg_path_2 = utils.test_sample("functional/sol_v2_common",
            "userdata_standard_change_vnfpkg")
        cls.new_pkg, cls.new_vnfd_id = cls.create_vnf_package(
            pkg_path_2, image_path=image_path, userdata_path=userdata_path)
        # Currently, the vnfpkgm v1 API does not support mgmt_driver_script
        # in change_vnfpkg. Replace with sample file for FT to run
        # mgmt_driver_script in change_vnfpkg.
        csar_dir = os.path.join(CONF.vnf_package.vnf_package_csar_path,
                                cls.new_pkg)
        source_path = "contents/Scripts/v2_sample4_df_simple.yaml"
        dest_path = "Definitions/v2_sample4_df_simple.yaml"
        # use of sudo is a temporary for FT
        subprocess.run(["sudo", "cp", os.path.join(pkg_path_2, source_path),
                        os.path.join(csar_dir, dest_path)])

        # for change_vnfpkg network/flavor change test
        pkg_path_3 = utils.test_sample("functional/sol_v2_common",
            "userdata_standard_change_vnfpkg_nw")
        cls.new_nw_pkg, cls.new_nw_vnfd_id = cls.create_vnf_package(
            pkg_path_3, image_path=image_path, userdata_path=userdata_path)

        # for attach non-boot volume to VDU test
        pkg_path_4 = utils.test_sample("functional/sol_v2_common",
            "userdata_standard_with_non_boot_volume")
        cls.non_boot_volume_pkg, cls.non_boot_volume_vnfd_id = (
            cls.create_vnf_package(pkg_path_4, image_path=image_path,
                                   userdata_path=userdata_path))

    @classmethod
    def tearDownClass(cls):
        super(IndividualVnfcMgmtTest, cls).tearDownClass()
        cls.delete_vnf_package(cls.standard_pkg)
        cls.delete_vnf_package(cls.new_pkg)
        cls.delete_vnf_package(cls.new_nw_pkg)
        cls.delete_vnf_package(cls.non_boot_volume_pkg)

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

    def _get_vnfc_id(self, inst, vdu, index):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        return vnfc['id']

    def _get_vnfc_info_id(self, inst, vdu, index):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        for vnfc_info in inst['instantiatedVnfInfo']['vnfcInfo']:
            if vnfc_info['vnfcResourceInfoId'] == vnfc['id']:
                return vnfc_info['id']

    def _get_vnfc_cps(self, inst, vdu, index):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        return {cp_info['cpdId'] for cp_info in vnfc['vnfcCpInfo']}

    def _get_vnfc_cp_net_id(self, inst, vdu, index, cp):
        # this is for external CPs
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

    def _get_vnfc_cp_net_name(self, inst, vdu, index, cp):
        # this is for internal CPs
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        for cp_info in vnfc['vnfcCpInfo']:
            if cp_info['cpdId'] == cp:
                # must be found
                link_port_id = cp_info['vnfLinkPortId']
                break
        for vl in inst['instantiatedVnfInfo']['vnfVirtualLinkResourceInfo']:
            for port in vl['vnfLinkPorts']:
                if port['id'] == link_port_id:
                    # must be found
                    return vl['vnfVirtualLinkDescId']

    def _get_vnfc_image(self, inst, vdu, index):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        for key, value in vnfc['metadata'].items():
            if key.startswith('image-'):
                # must be found
                return value

    def _get_vnfc_flavor(self, inst, vdu, index):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        # must exist
        return vnfc['metadata']['flavor']

    def _get_vnfc_storage_ids(self, inst, vdu, index):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        storage_res_ids = vnfc.get('storageResourceIds', [])
        return sorted(storage_res_ids)

    def _get_server_name(self, inst, vdu, index):
        for vnfc in inst['instantiatedVnfInfo']['vnfcResourceInfo']:
            if (vnfc['vduId'] == vdu and
                    vnfc['metadata'].get('vdu_idx') == index):
                # must be found
                server_id = vnfc['computeResource']['resourceId']
                break
        server_details = self.get_server_details_by_id(server_id)
        return server_details.get('name')

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
        create_req = paramgen.sample3_create(self.standard_vnfd_id)
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
        # check vnfcInfo ids
        self.assertEqual('a-001', self._get_vnfc_info_id(inst_1, 'VDU1', 0))
        self.assertEqual('b-000', self._get_vnfc_info_id(inst_1, 'VDU2', 0))
        # check server name
        self.assertEqual('VDU1-a-001-instantiate',
                         self._get_server_name(inst_1, 'VDU1', 0))

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
        # check vnfcInfo ids
        self.assertEqual('a-010', self._get_vnfc_info_id(inst_2, 'VDU1', 1))
        self.assertEqual('a-011', self._get_vnfc_info_id(inst_2, 'VDU1', 2))
        # check server names
        self.assertEqual('VDU1-a-010-scale_out',
                         self._get_server_name(inst_2, 'VDU1', 1))
        self.assertEqual('VDU1-a-011-instantiate',
                         self._get_server_name(inst_2, 'VDU1', 2))

        # 3. Heal operation
        heal_req = paramgen.sample3_heal()
        # pick up VDU1-1 to heal
        vnfc_info_id = self._get_vnfc_info_id(inst_2, 'VDU1', 1)  # 'a-010'
        heal_req['vnfcInstanceId'] = [vnfc_info_id]
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
        # check vnfcInfo id of VDU1-1 is not changed.
        self.assertEqual('a-010', self._get_vnfc_info_id(inst_3, 'VDU1', 1))
        # check server name
        self.assertEqual('VDU1-a-010-heal',
                         self._get_server_name(inst_3, 'VDU1', 1))

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

        # check server names
        self.assertEqual('VDU1-a-001-change_ext_conn',
                         self._get_server_name(inst_5, 'VDU1', 0))
        self.assertEqual('VDU1-a-010-change_ext_conn',
                         self._get_server_name(inst_5, 'VDU1', 1))

        # 6. Change_vnfpkg operation
        change_vnfpkg_req = paramgen.sample4_change_vnfpkg(self.new_vnfd_id,
            net_ids, subnet_ids)

        for vdu_param in change_vnfpkg_req['additionalParams']['vdu_params']:
            vdu_param['new_vnfc_param']['endpoint'] = (
                f'http://localhost:{self.get_server_port()}')

        # Prepare coordination
        self.set_server_callback(
            'POST',
            '/lcmcoord/v1/coordinations',
            status_code=201,
            response_headers={"Content-Type": "application/json"},
            callback=_create_coordinate_response
        )

        with open('/tmp/change_vnfpkg_coordination', 'w'):
            pass

        # execute Change_vnfpkg operation
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        os.remove('/tmp/change_vnfpkg_coordination')

        # Show VNF instance
        resp, inst_6 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check vnfdId is changed
        self.assertEqual(self.new_vnfd_id, inst_6['vnfdId'])
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
        # check all vnfcInfo ids are not changed.
        self.assertEqual('a-001', self._get_vnfc_info_id(inst_6, 'VDU1', 0))
        self.assertEqual('a-010', self._get_vnfc_info_id(inst_6, 'VDU1', 1))
        self.assertEqual('b-000', self._get_vnfc_info_id(inst_6, 'VDU2', 0))
        # check server names
        self.assertEqual('VDU1-a-001-change_vnfpkg',
                         self._get_server_name(inst_6, 'VDU1', 0))
        self.assertEqual('VDU1-a-010-change_vnfpkg',
                         self._get_server_name(inst_6, 'VDU1', 1))

        # Terminate VNF instance
        terminate_req = paramgen.sample4_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Delete VNF instance
        self.exec_lcm_operation(self.delete_vnf_instance, inst_id)

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
        create_req = paramgen.sample3_create(self.standard_vnfd_id)
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
        self.put_fail_file('scale_end')
        scale_out_req = paramgen.sample3_scale_out()
        resp, body = self.scale_vnf_instance(inst_id, scale_out_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)
        self.rm_fail_file('scale_end')

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
        self.put_fail_file('change_external_connectivity_end')
        change_ext_conn_req = paramgen.sample3_change_ext_conn(net_ids)
        resp, body = self.change_ext_conn(inst_id, change_ext_conn_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)
        self.rm_fail_file('change_external_connectivity_end')

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
        # check server name is not changed
        self.assertEqual('VDU1-a-001-instantiate',
                         self._get_server_name(inst_2, 'VDU1', 0))

        # 3. Change_vnfpkg operation
        self.put_fail_file('change_vnfpkg')
        with open('/tmp/change_vnfpkg_coordination', 'w'):
            pass

        change_vnfpkg_req = paramgen.sample4_change_vnfpkg(self.new_vnfd_id,
            net_ids, subnet_ids)
        for vdu_param in change_vnfpkg_req['additionalParams']['vdu_params']:
            vdu_param['old_vnfc_param']['endpoint'] = (
                f'http://localhost:{self.get_server_port()}')

        # Prepare coordination
        self.set_server_callback(
            'POST',
            '/lcmcoord/v1/coordinations',
            status_code=201,
            response_headers={"Content-Type": "application/json"},
            callback=_create_coordinate_response
        )

        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)
        self.rm_fail_file('change_vnfpkg')

        # Rollback
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        os.remove('/tmp/change_vnfpkg_coordination')

        # Show VNF instance
        resp, inst_3 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check vnfdId is not changed
        self.assertEqual(self.standard_vnfd_id, inst_3['vnfdId'])
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
        # check server name is not changed
        self.assertEqual('VDU1-a-001-instantiate',
                         self._get_server_name(inst_3, 'VDU1', 0))

        # Terminate VNF instance
        terminate_req = paramgen.sample3_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Delete VNF instance
        self.exec_lcm_operation(self.delete_vnf_instance, inst_id)

    def test_heal_vnfc_after_image_change(self):
        """Test heal operation after image change using StandardUserData

        * Note:
          This test focuses on checking changed image when Heal operation
          run after the vnfdId is changed by modify operation.

        * About LCM operations:
          This test includes the following operations.
          -    Create VNF instance
          - 1. Instantiate VNF instance
          -    Show VNF instance / check
          - 2. Update VNF instance
          -    Show VNF instance / check
          - 3. Heal operation
          -    Show VNF instance / check
          -    Terminate VNF instance
          -    Delete VNF instance
        """

        net_ids = self.get_network_ids(['net0', 'net1', 'net_mgmt'])
        subnet_ids = self.get_subnet_ids(['subnet0', 'subnet1'])

        # Create VNF instance
        create_req = paramgen.sample3_create(self.standard_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # 1. Instantiate VNF instance
        instantiate_req = paramgen.sample3_instantiate(
            net_ids, subnet_ids, self.auth_url)
        instantiate_req['instantiationLevelId'] = 'instantiation_level_2'
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Show VNF instance
        resp, inst_1 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check number of VDUs and indexes
        self.assertEqual({0, 1}, self._get_vdu_indexes(inst_1, 'VDU1'))
        self.assertEqual({0}, self._get_vdu_indexes(inst_1, 'VDU2'))

        # 2. Update VNF instance
        update_req = paramgen.sample3_update_vnf_vnfd_id(self.new_vnfd_id)
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Show VNF instance
        resp, inst_2 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check number of VDUs and indexes
        self.assertEqual({0, 1}, self._get_vdu_indexes(inst_2, 'VDU1'))
        self.assertEqual({0}, self._get_vdu_indexes(inst_2, 'VDU2'))

        # check vnfdId is changed
        self.assertEqual(self.new_vnfd_id, inst_2['vnfdId'])

        # 3. Heal operation
        heal_req = paramgen.sample3_heal()
        # pick up VDU1-1 to heal
        vnfc_info_id = self._get_vnfc_info_id(inst_2, 'VDU1', 1)
        heal_req['vnfcInstanceId'] = [vnfc_info_id]
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
        self.assertEqual(self._get_vnfc_id(inst_2, 'VDU2', 0),
                         self._get_vnfc_id(inst_3, 'VDU2', 0))

        # check image of VDU1-1 is changed and other are not.
        self.assertEqual(self._get_vnfc_image(inst_2, 'VDU1', 0),
                         self._get_vnfc_image(inst_3, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_image(inst_2, 'VDU1', 1),
                            self._get_vnfc_image(inst_3, 'VDU1', 1))
        self.assertEqual(self._get_vnfc_image(inst_2, 'VDU2', 0),
                         self._get_vnfc_image(inst_3, 'VDU2', 0))

        # Terminate VNF instance
        terminate_req = paramgen.sample3_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Delete VNF instance
        self.exec_lcm_operation(self.delete_vnf_instance, inst_id)

    def test_change_vnfpkg_nw(self):
        """Test change_vnfpkg with additional functions

        * Note:
          This test focuses change_vnfpkg with the following changes.
          - adding external CP
          - change internal network
          - change flavor

          TODO: add anoter patterns (ex. change extMgdVLs)

        * About LCM operations:
          This test includes the following operations.
          -    Create VNF instance
          - 1. Instantiate VNF instance
          -    Show VNF instance / check
          - 2. Change_vnfpkg operation
          -    Show VNF instance / check
          -    Terminate VNF instance
          -    Delete VNF instance
        """

        net_ids = self.get_network_ids(['net0', 'net1', 'net_mgmt'])
        subnet_ids = self.get_subnet_ids(['subnet0', 'subnet1'])

        # Create VNF instance
        create_req = paramgen.sample3_create(self.standard_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # 1. Instantiate VNF instance
        instantiate_req = paramgen.sample3_instantiate(
            net_ids, subnet_ids, self.auth_url)
        instantiate_req['instantiationLevelId'] = "instantiation_level_2"
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Show VNF instance
        resp, inst_1 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check number of VDUs and indexes
        self.assertEqual({0, 1}, self._get_vdu_indexes(inst_1, 'VDU1'))
        self.assertEqual({0}, self._get_vdu_indexes(inst_1, 'VDU2'))

        # 2. Change_vnfpkg operation
        change_vnfpkg_req = paramgen.sample5_change_vnfpkg(self.new_nw_vnfd_id,
            net_ids, subnet_ids)
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Show VNF instance
        resp, inst_2 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check vnfdId is changed
        self.assertEqual(self.new_nw_vnfd_id, inst_2['vnfdId'])
        # check images are changed
        self.assertNotEqual(self._get_vnfc_image(inst_1, 'VDU1', 0),
                            self._get_vnfc_image(inst_2, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_image(inst_1, 'VDU1', 1),
                            self._get_vnfc_image(inst_2, 'VDU1', 1))
        self.assertNotEqual(self._get_vnfc_image(inst_1, 'VDU2', 0),
                            self._get_vnfc_image(inst_2, 'VDU2', 0))
        # check flavor is changed (VDU2 only)
        self.assertNotEqual(self._get_vnfc_flavor(inst_1, 'VDU2', 0),
                            self._get_vnfc_flavor(inst_2, 'VDU2', 0))
        # check external CPs; VDU1_CP4 and VDU2_CP4 are added
        self.assertFalse('VDU1_CP4' in self._get_vnfc_cps(inst_1, 'VDU1', 0))
        self.assertFalse('VDU1_CP4' in self._get_vnfc_cps(inst_1, 'VDU1', 1))
        self.assertFalse('VDU2_CP4' in self._get_vnfc_cps(inst_1, 'VDU2', 0))
        self.assertTrue('VDU1_CP4' in self._get_vnfc_cps(inst_2, 'VDU1', 0))
        self.assertTrue('VDU1_CP4' in self._get_vnfc_cps(inst_2, 'VDU1', 1))
        self.assertTrue('VDU2_CP4' in self._get_vnfc_cps(inst_2, 'VDU2', 0))
        self.assertEqual(net_ids['net0'],
            self._get_vnfc_cp_net_id(inst_2, 'VDU1', 0, 'VDU1_CP4'))
        self.assertEqual(net_ids['net0'],
            self._get_vnfc_cp_net_id(inst_2, 'VDU1', 1, 'VDU1_CP4'))
        self.assertEqual(net_ids['net0'],
            self._get_vnfc_cp_net_id(inst_2, 'VDU2', 0, 'VDU2_CP4'))
        # check internal CPs; VDU1_CP3 and VDU2_CP3 are changed
        self.assertEqual("internalVL2",
            self._get_vnfc_cp_net_name(inst_1, 'VDU1', 0, 'VDU1_CP3'))
        self.assertEqual("internalVL2",
            self._get_vnfc_cp_net_name(inst_1, 'VDU1', 1, 'VDU1_CP3'))
        self.assertEqual("internalVL2",
            self._get_vnfc_cp_net_name(inst_1, 'VDU2', 0, 'VDU2_CP3'))
        self.assertEqual("internalVL3",
            self._get_vnfc_cp_net_name(inst_2, 'VDU1', 0, 'VDU1_CP3'))
        self.assertEqual("internalVL3",
            self._get_vnfc_cp_net_name(inst_2, 'VDU1', 1, 'VDU1_CP3'))
        self.assertEqual("internalVL3",
            self._get_vnfc_cp_net_name(inst_2, 'VDU2', 0, 'VDU2_CP3'))

        # Terminate VNF instance
        terminate_req = paramgen.sample5_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Delete VNF instance
        self.exec_lcm_operation(self.delete_vnf_instance, inst_id)

    def test_change_vnfpkg_nw_rollback(self):
        """Test rollback of change_vnfpkg with additional functions

        * Note:
          This test focuses rollback of change_vnfpkg with the following
          changes.
          - adding external CP
          - change internal network
          - change flavor

          TODO: add anoter patterns (ex. change extMgdVLs)

        * About LCM operations:
          This test includes the following operations.
          -    Create VNF instance
          - 1. Instantiate VNF instance
          -    Show VNF instance / check
          - 2. Change_vnfpkg operation => FAILED_TEMP
          -    Rollback
          -    Show VNF instance / check
          -    Terminate VNF instance
          -    Delete VNF instance
        """

        net_ids = self.get_network_ids(['net0', 'net1', 'net_mgmt'])
        subnet_ids = self.get_subnet_ids(['subnet0', 'subnet1'])

        # Create VNF instance
        create_req = paramgen.sample3_create(self.standard_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # 1. Instantiate VNF instance
        instantiate_req = paramgen.sample3_instantiate(
            net_ids, subnet_ids, self.auth_url)
        instantiate_req['instantiationLevelId'] = "instantiation_level_2"
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Show VNF instance
        resp, inst_1 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check number of VDUs and indexes
        self.assertEqual({0, 1}, self._get_vdu_indexes(inst_1, 'VDU1'))
        self.assertEqual({0}, self._get_vdu_indexes(inst_1, 'VDU2'))

        # 2. Change_vnfpkg operation
        self.put_fail_file('change_vnfpkg')
        change_vnfpkg_req = paramgen.sample5_change_vnfpkg(self.new_nw_vnfd_id,
            net_ids, subnet_ids)
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)
        self.rm_fail_file('change_vnfpkg')

        # Rollback
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # Show VNF instance
        resp, inst_2 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check vnfdId is not changed
        self.assertEqual(self.standard_vnfd_id, inst_2['vnfdId'])
        # check images are not changed
        self.assertEqual(self._get_vnfc_image(inst_1, 'VDU1', 0),
                         self._get_vnfc_image(inst_2, 'VDU1', 0))
        self.assertEqual(self._get_vnfc_image(inst_1, 'VDU1', 1),
                         self._get_vnfc_image(inst_2, 'VDU1', 1))
        self.assertEqual(self._get_vnfc_image(inst_1, 'VDU2', 0),
                         self._get_vnfc_image(inst_2, 'VDU2', 0))
        # check flavor is not changed (VDU2 only)
        self.assertEqual(self._get_vnfc_flavor(inst_1, 'VDU2', 0),
                         self._get_vnfc_flavor(inst_2, 'VDU2', 0))
        # check external CPs; VDU1_CP4 and VDU2_CP4 are not added
        self.assertFalse('VDU1_CP4' in self._get_vnfc_cps(inst_2, 'VDU1', 0))
        self.assertFalse('VDU1_CP4' in self._get_vnfc_cps(inst_2, 'VDU1', 1))
        self.assertFalse('VDU2_CP4' in self._get_vnfc_cps(inst_2, 'VDU2', 0))
        # check internal CPs; VDU1_CP3 and VDU2_CP3 are not changed
        self.assertEqual(
            self._get_vnfc_cp_net_name(inst_1, 'VDU1', 0, 'VDU1_CP3'),
            self._get_vnfc_cp_net_name(inst_2, 'VDU1', 0, 'VDU1_CP3'))
        self.assertEqual(
            self._get_vnfc_cp_net_name(inst_1, 'VDU1', 1, 'VDU1_CP3'),
            self._get_vnfc_cp_net_name(inst_2, 'VDU1', 1, 'VDU1_CP3'))
        self.assertEqual(
            self._get_vnfc_cp_net_name(inst_1, 'VDU2', 0, 'VDU2_CP3'),
            self._get_vnfc_cp_net_name(inst_2, 'VDU2', 0, 'VDU2_CP3'))

        # Terminate VNF instance
        terminate_req = paramgen.sample3_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Delete VNF instance
        self.exec_lcm_operation(self.delete_vnf_instance, inst_id)

    def test_instantiate_attach_non_boot_volume(self):
        """Test Instantiate with non-boot volume attached to VDU

        * Note:
          This test focuses on the non-boot volume attached by
          OS::Cinder::VolumeAttachment in HOT being registered to
          storageResourceIds.

        * About LCM operations:
          This test includes the following operations.
          -    Create VNF instance
          - 1. Instantiate VNF instance
          -    Show VNF instance / check
          - 2. Heal operation("all"=True)
          -    Show VNF instance / check
          - 3. Heal operation("all" is not specified)
          -    Show VNF instance / check
          -    Terminate VNF instance
          -    Delete VNF instance
        """

        net_ids = self.get_network_ids(['net0', 'net1', 'net_mgmt'])
        subnet_ids = self.get_subnet_ids(['subnet0', 'subnet1'])

        # Create VNF instance
        create_req = paramgen.sample7_create(self.non_boot_volume_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # 1. Instantiate VNF instance
        instantiate_req = paramgen.sample7_instantiate(
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

        # check storageResourceIds of attached non-boot volume
        self.assertNotEqual([], self._get_vnfc_storage_ids(inst_1, 'VDU1', 0))

        # 2. Heal operation("all"=True)
        # VDU1-0 to heal
        heal_req = paramgen.sample7_heal('a-001')
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Show VNF instance
        resp, inst_2 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check id of VDU1-0 is changed
        self.assertNotEqual(self._get_vnfc_id(inst_1, 'VDU1', 0),
                            self._get_vnfc_id(inst_2, 'VDU1', 0))

        # check storageResourceIds of VDU1-0 is changed
        self.assertNotEqual([], self._get_vnfc_storage_ids(inst_2, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_storage_ids(inst_1, 'VDU1', 0),
                            self._get_vnfc_storage_ids(inst_2, 'VDU1', 0))

        # 3. Heal operation("all" is not specified)
        # VDU1-0 to heal
        heal_req['vnfcInstanceId'] = ['a-001']
        del heal_req['additionalParams']['all']
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Show VNF instance
        resp, inst_3 = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)

        # check id of VDU1-0 is changed
        self.assertNotEqual(self._get_vnfc_id(inst_2, 'VDU1', 0),
                            self._get_vnfc_id(inst_3, 'VDU1', 0))

        # check storageResourceIds of VDU1-0 is not changed
        self.assertEqual(self._get_vnfc_storage_ids(inst_2, 'VDU1', 0),
                         self._get_vnfc_storage_ids(inst_3, 'VDU1', 0))

        # Terminate VNF instance
        terminate_req = paramgen.sample7_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # Delete VNF instance
        self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
