# Copyright (C) 2023 Fujitsu
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
import string

from tacker.objects import fields
from tacker.tests.functional.sol_v2_common import base_v2
from tacker.tests.functional.sol_v2_common import paramgen
from tacker.tests import utils

SUPPORT_STRING_FOR_VNFD_ID = f"{string.ascii_letters}{string.digits}-._ "
MAX_VNFD_ID = f"{SUPPORT_STRING_FOR_VNFD_ID}max_vnfd_id"
UPD_MAX_VNFD_ID = f"{SUPPORT_STRING_FOR_VNFD_ID}upd_max_vnfd_id"


class IndividualVnfcMgmtVariousLcmTest(base_v2.BaseSolV2Test):

    @classmethod
    def setUpClass(cls):
        super(IndividualVnfcMgmtVariousLcmTest, cls).setUpClass()
        image_path = utils.test_etc_sample("etsi/nfv/common/Files/images",
            "cirros-0.5.2-x86_64-disk.img")

        userdata_path = utils.userdata("userdata_standard.py")

        # vnf package for basic lcms tests max pattern
        pkg_path_1 = utils.test_sample("functional/sol_v2_common",
            "basic_lcms_max_individual_vnfc")
        cls.max_pkg, cls.max_vnfd_id = cls.create_vnf_package(
            pkg_path_1, image_path=image_path,
            userdata_path=userdata_path, vnfd_id=MAX_VNFD_ID)

        # vnf package for update vnf max pattern
        pkg_path_2 = utils.test_sample("functional/sol_v2_common",
            "update_vnf_max_individual_vnfc")
        cls.upd_max_pkg, cls.upd_max_vnfd_id = cls.create_vnf_package(
            pkg_path_2, image_path=image_path,
            userdata_path=userdata_path, vnfd_id=UPD_MAX_VNFD_ID)

        cls._pre_setting()

    @classmethod
    def tearDownClass(cls):
        super(IndividualVnfcMgmtVariousLcmTest, cls).tearDownClass()
        cls.delete_vnf_package(cls.max_pkg)
        cls.delete_vnf_package(cls.upd_max_pkg)

    def setUp(self):
        super().setUp()

    @classmethod
    def _pre_setting(cls):
        # Create a new network and subnet to check the IP allocation of
        # IPv4 and IPv6
        ft_net0_name = 'ft-net0'
        ft_net0_subs = {
            'ft-ipv4-subnet0': {
                'range': '100.100.100.0/24',
                'ip_version': 4
            },
            'ft-ipv6-subnet0': {
                'range': '1111:2222:3333::/64',
                'ip_version': 6
            }
        }
        ft_net0_id = cls.create_network(cls, ft_net0_name)
        cls.addClassCleanup(cls.delete_network, cls, ft_net0_id)
        for sub_name, val in ft_net0_subs.items():
            # subnet is automatically deleted with network deletion
            cls.create_subnet(
                cls, ft_net0_id, sub_name, val['range'], val['ip_version'])

        # Create a new network for change external connectivity
        ft_net1_name = 'ft-net1'
        ft_net1_subs = {
            'ft-ipv4-subnet1': {
                'range': '22.22.22.0/24',
                'ip_version': 4
            },
            'ft-ipv6-subnet1': {
                'range': '1111:2222:4444::/64',
                'ip_version': 6
            }
        }
        ft_net1_id = cls.create_network(cls, ft_net1_name)
        cls.addClassCleanup(cls.delete_network, cls, ft_net1_id)
        for sub_name, val in ft_net1_subs.items():
            # subnet is automatically deleted with network deletion
            cls.create_subnet(
                cls, ft_net1_id, sub_name, val['range'], val['ip_version'])

        cls.net_ids = cls.get_network_ids(
            cls, ['net0', 'net1', 'net_mgmt', 'ft-net0', 'ft-net1'])
        cls.subnet_ids = cls.get_subnet_ids(
            cls, ['subnet0', 'subnet1', 'ft-ipv4-subnet0', 'ft-ipv6-subnet0',
             'ft-ipv4-subnet1', 'ft-ipv6-subnet1'])

    def _get_vdu_indexes(self, inst, vdu):
        return {
            vnfc['metadata'].get('vdu_idx')
            for vnfc in inst['instantiatedVnfInfo']['vnfcResourceInfo']
            if vnfc['vduId'] == vdu
        }

    def _get_vnfc_metadata_keys(self, inst, vdu):
        vnfc_metadata_keys = set()
        for vnfc in inst['instantiatedVnfInfo']['vnfcResourceInfo']:
            if vnfc['vduId'] == vdu:
                vnfc_metadata_keys.update(set(vnfc['metadata'].keys()))
        return vnfc_metadata_keys

    def _add_additional_params(self, req):
        if not req.get('additionalParams'):
            req['additionalParams'] = {}
        req['additionalParams']['lcm-operation-user-data'] = (
            './UserData/userdata_standard.py')
        req['additionalParams']['lcm-operation-user-data-class'] = (
            'StandardUserData')

    def _get_vnfc_by_vdu_index(self, inst, vdu, index):
        for vnfc in inst['instantiatedVnfInfo']['vnfcResourceInfo']:
            if (vnfc['vduId'] == vdu and
                    vnfc['metadata'].get('vdu_idx') == index):
                return vnfc

    def _get_vnfc_id(self, inst, vdu, index):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        return vnfc['id']

    def _get_vnfc_image(self, inst, vdu, index):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        for key, value in vnfc['metadata'].items():
            if key.startswith('image-'):
                # must be found
                return value

    def _get_vnfc_storage_ids(self, inst, vdu, index):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        return vnfc['storageResourceIds']

    def _get_vnf_ext_cp_id(self, inst, vdu, index, cp):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        for cp_info in vnfc['vnfcCpInfo']:
            if cp_info['cpdId'] == cp:
                # must be found
                ext_cp_id = cp_info['vnfExtCpId']
                break
        return ext_cp_id

    def _get_vnf_link_port_id(self, inst, vdu, index, cp):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        for cp_info in vnfc['vnfcCpInfo']:
            if cp_info['cpdId'] == cp:
                # must be found
                link_port_id = cp_info['vnfLinkPortId']
                break
        return link_port_id

    def _check_for_show_operation(
            self, operation, expected_inst_attrs, inst_id,
            vdu_result=None, image_result=None):
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        if operation == 'INSTANTIATE':
            # check instantiationState of VNF
            self.assertEqual(fields.VnfInstanceState.INSTANTIATED,
                             body['instantiationState'])

        if operation == 'SCALE':
            # check scaleStatus
            scale_status = body['instantiatedVnfInfo']['scaleStatus']
            self.assertGreater(len(scale_status), 0)
            for status in scale_status:
                self.assertIn('aspectId', status)
                self.assertIn('scaleLevel', status)

        # check instantiatedVnfInfo's information
        # check number of VDU, and index
        if vdu_result:
            self.assertEqual(vdu_result['VDU1'],
                             self._get_vdu_indexes(body, 'VDU1'))
            self.assertEqual(vdu_result['VDU2'],
                             self._get_vdu_indexes(body, 'VDU2'))
        # check exist of VDU-image
        if image_result:
            for result_1 in image_result['VDU1']:
                self.assertIn(
                    result_1,
                    self._get_vnfc_metadata_keys(body, 'VDU1'))
            for result_2 in image_result['VDU2']:
                self.assertIn(
                    result_2,
                    self._get_vnfc_metadata_keys(body, 'VDU2'))

        return body

    def test_various_lcm_operations_before_and_after(self):
        """Test various vnflcm operations before and after

        * About attributes:
          All of the following cardinality attributes are set.
          In addition, 0..N or 1..N attributes are set to 2 or more.
          0..1 is set to 1.
          - 0..1 (1)
          - 0..N (2 or more)
          - 1..N (2 or more)

        * About LCM operations:
          This test includes the following operations.
          - 0. Create VNF
          - 1. Instantiate VNF
          - 2. Show VNF instance
          - 3. Scale out operation
          - 4. Show VNF instance(check for scale)
          - 5. Heal VNF(vnfc)
          - 6. Show VNF instance(check for heal)
          - 7. Scale out operation
          - 8. Show VNF instance(check for scale)
          - 9. Scale in operation
          - 10. Show VNF instance(check for scale)
          - 11. Heal VNF(all with all=True parameter)
          - 12. Show VNF instance(check for heal)
          - 13. Scale in operation
          - 14. Show VNF instance(check for scale)
          - 15. Heal VNF(vnfc)
          - 16. Show VNF instance(check for heal)
          - 17. Scale out operation
          - 18. Show VNF instance(check for scale)
          - 19. Heal VNF(all with all=True parameter)
          - 20. Show VNF instance(check for heal)
          - 21. Change external connectivity
          - 22. Show VNF instance(check for change-ext-conn)
          - 23. Scale in operation
          - 24. Show VNF instance(check for scale)
          - 25. Update VNF
          - 26. Show VNF instance(check for update)
          - 27. Scale out operation
          - 28. Heal VNF(all with omit all parameter)
          - 29. Heal VNF(all with all=False parameter)
          - 30. Heal VNF(all with all=True parameter)
          - 31. Terminate VNF
          - 32. Delete VNF
        """
        # 0. Create VNF
        create_req = paramgen.create_vnf_max(
            self.max_vnfd_id, description="test for various lcm operations")
        _, body = self.create_vnf_instance(create_req)
        inst_id = body['id']

        # 1. Instantiate VNF
        instantiate_req = paramgen.instantiate_vnf_max(
            self.net_ids, self.subnet_ids, None, self.auth_url,
            user_data=True)
        resp, body = self.instantiate_vnf_instance(
            inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 2. Show VNF instance
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
            'vimConnectionInfo',
            'instantiationState',
            'instantiatedVnfInfo',
            'metadata',
            # 'extensions', # omitted
            '_links'
        ]
        vdu_result = {'VDU1': {0}, 'VDU2': {0}}
        image_result = {'VDU1': {'image-VDU1-VirtualStorage-0'},
                        'VDU2': {'image-VDU2-VirtualStorage-0'}}
        _ = self._check_for_show_operation(
            'INSTANTIATE', expected_inst_attrs, inst_id,
            vdu_result, image_result)

        # 3. Scale out operation
        scaleout_req = paramgen.scaleout_vnf_max()
        self._add_additional_params(scaleout_req)
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 4. Show VNF instance(check for scale)
        vdu_result = {'VDU1': {0, 1}, 'VDU2': {0}}
        image_result = {'VDU1': {'image-VDU1-VirtualStorage-0',
                                 'image-VDU1-VirtualStorage-1'},
                        'VDU2': {'image-VDU2-VirtualStorage-0'}}
        inst_4 = self._check_for_show_operation(
            'SCALE', expected_inst_attrs, inst_id,
            vdu_result, image_result)

        # 5. Heal VNF(vnfc)
        vnfc_info = inst_4['instantiatedVnfInfo']['vnfcInfo']
        vnfc_id = [vnfc['id'] for vnfc in vnfc_info
                   if (vnfc['vnfcResourceInfoId'] ==
                       self._get_vnfc_id(inst_4, 'VDU1', 1))][0]
        heal_req = paramgen.heal_vnf_vnfc_max(vnfc_id)
        self._add_additional_params(heal_req)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 6. Show VNF instance(check for heal)
        inst_6 = self._check_for_show_operation(
            'HEAL', expected_inst_attrs, inst_id)

        # check id of VDU1 with index 1 is changed
        self.assertNotEqual(self._get_vnfc_id(inst_4, 'VDU1', 1),
                            self._get_vnfc_id(inst_6, 'VDU1', 1))
        # check image of VDU1 with index 1 is not changed
        self.assertEqual(self._get_vnfc_image(inst_4, 'VDU1', 1),
                         self._get_vnfc_image(inst_6, 'VDU1', 1))

        # 7. Scale out operation
        scaleout_req = paramgen.scaleout_vnf_max()
        self._add_additional_params(scaleout_req)
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 8. Show VNF instance(check for scale)
        vdu_result = {'VDU1': {0, 1, 2}, 'VDU2': {0}}
        image_result = {'VDU1': {'image-VDU1-VirtualStorage-0',
                                 'image-VDU1-VirtualStorage-1',
                                 'image-VDU1-VirtualStorage-2'},
                        'VDU2': {'image-VDU2-VirtualStorage-0'}}
        _ = self._check_for_show_operation(
            'SCALE', expected_inst_attrs, inst_id,
            vdu_result, image_result)

        # 9. Scale in operation
        scalein_req = paramgen.scalein_vnf_max()
        self._add_additional_params(scalein_req)
        resp, body = self.scale_vnf_instance(inst_id, scalein_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 10. Show VNF instance(check for scale)
        vdu_result = {'VDU1': {0, 1}, 'VDU2': {0}}
        image_result = {'VDU1': {'image-VDU1-VirtualStorage-0',
                                 'image-VDU1-VirtualStorage-1'},
                        'VDU2': {'image-VDU2-VirtualStorage-0'}}
        inst_10 = self._check_for_show_operation(
            'SCALE', expected_inst_attrs, inst_id,
            vdu_result, image_result)

        # 11. Heal VNF(all with all=True parameter)
        heal_req = paramgen.heal_vnf_all_max_with_parameter(True)
        self._add_additional_params(heal_req)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 12. Show VNF instance(check for heal)
        vdu_result = {'VDU1': {0, 1}, 'VDU2': {0}}
        inst_12 = self._check_for_show_operation(
            'HEAL', expected_inst_attrs, inst_id, vdu_result)
        # check all ids of VDU are changed
        self.assertNotEqual(self._get_vnfc_id(inst_10, 'VDU1', 0),
                            self._get_vnfc_id(inst_12, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_id(inst_10, 'VDU1', 1),
                            self._get_vnfc_id(inst_12, 'VDU1', 1))
        self.assertNotEqual(self._get_vnfc_id(inst_10, 'VDU2', 0),
                            self._get_vnfc_id(inst_12, 'VDU2', 0))
        # check storage ids are changed
        self.assertNotEqual(self._get_vnfc_storage_ids(inst_10, 'VDU1', 0),
                            self._get_vnfc_storage_ids(inst_12, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_storage_ids(inst_10, 'VDU1', 1),
                            self._get_vnfc_storage_ids(inst_12, 'VDU1', 1))
        self.assertNotEqual(self._get_vnfc_storage_ids(inst_10, 'VDU2', 0),
                            self._get_vnfc_storage_ids(inst_12, 'VDU2', 0))
        # check cps are changed
        for cp_1 in ['VDU1_CP1', 'VDU1_CP2', 'VDU2_CP2']:
            self.assertNotEqual(
                self._get_vnf_ext_cp_id(inst_10, cp_1.split('_')[0], 0, cp_1),
                self._get_vnf_ext_cp_id(inst_12, cp_1.split('_')[0], 0, cp_1))
        for cp_2 in ['VDU1_CP3', 'VDU1_CP4', 'VDU1_CP5',
                     'VDU2_CP3', 'VDU2_CP4', 'VDU2_CP5']:
            self.assertNotEqual(
                self._get_vnf_link_port_id(inst_10,
                                           cp_2.split('_')[0], 0, cp_2),
                self._get_vnf_link_port_id(inst_12,
                                           cp_2.split('_')[0], 0, cp_2))
        for ext_cp in ['VDU1_CP1', 'VDU1_CP2']:
            self.assertNotEqual(
                self._get_vnf_ext_cp_id(
                    inst_10, ext_cp.split('_')[0], 1, ext_cp),
                self._get_vnf_ext_cp_id(
                    inst_12, ext_cp.split('_')[0], 1, ext_cp))
        for link_port_cp in ['VDU1_CP3', 'VDU1_CP4', 'VDU1_CP5']:
            self.assertNotEqual(
                self._get_vnf_link_port_id(
                    inst_10, link_port_cp.split('_')[0], 1, link_port_cp),
                self._get_vnf_link_port_id(
                    inst_12, link_port_cp.split('_')[0], 1, link_port_cp))

        # 13. Scale in operation
        scalein_req = paramgen.scalein_vnf_max()
        self._add_additional_params(scalein_req)
        resp, body = self.scale_vnf_instance(inst_id, scalein_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 14. Show VNF instance(check for scale)
        vdu_result = {'VDU1': {0}, 'VDU2': {0}}
        image_result = {'VDU1': {'image-VDU1-VirtualStorage-0'},
                        'VDU2': {'image-VDU2-VirtualStorage-0'}}
        inst_14 = self._check_for_show_operation(
            'SCALE', expected_inst_attrs, inst_id,
            vdu_result, image_result)

        # 15. Heal VNF(vnfc)
        vnfc_info = inst_14['instantiatedVnfInfo']['vnfcInfo']
        vnfc_id = [vnfc['id'] for vnfc in vnfc_info
                   if (vnfc['vnfcResourceInfoId'] ==
                       self._get_vnfc_id(inst_14, 'VDU1', 0))][0]
        heal_req = paramgen.heal_vnf_vnfc_max(vnfc_id)
        self._add_additional_params(heal_req)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 16. Show VNF instance(check for heal)
        inst_16 = self._check_for_show_operation(
            'HEAL', expected_inst_attrs, inst_id)

        # check id of VDU1 with index 0 is changed
        self.assertNotEqual(self._get_vnfc_id(inst_14, 'VDU1', 0),
                            self._get_vnfc_id(inst_16, 'VDU1', 0))
        # check image of VDU1 with index 0 is not changed
        self.assertEqual(self._get_vnfc_image(inst_14, 'VDU1', 0),
                         self._get_vnfc_image(inst_16, 'VDU1', 0))

        # 17. Scale out operation
        scaleout_req = paramgen.scaleout_vnf_max()
        self._add_additional_params(scaleout_req)
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 18. Show VNF instance(check for scale)
        vdu_result = {'VDU1': {0, 1}, 'VDU2': {0}}
        image_result = {'VDU1': {'image-VDU1-VirtualStorage-0',
                                 'image-VDU1-VirtualStorage-1'},
                        'VDU2': {'image-VDU2-VirtualStorage-0'}}
        inst_18 = self._check_for_show_operation(
            'SCALE', expected_inst_attrs, inst_id,
            vdu_result, image_result)

        # 19. Heal VNF(all with all=True parameter)
        heal_req = paramgen.heal_vnf_all_max_with_parameter(True)
        self._add_additional_params(heal_req)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 20. Show VNF instance(check for heal)
        vdu_result = {'VDU1': {0, 1}, 'VDU2': {0}}
        inst_20 = self._check_for_show_operation(
            'HEAL', expected_inst_attrs, inst_id, vdu_result)
        # check all ids of VDU are changed
        self.assertNotEqual(self._get_vnfc_id(inst_18, 'VDU1', 0),
                            self._get_vnfc_id(inst_20, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_id(inst_18, 'VDU1', 1),
                            self._get_vnfc_id(inst_20, 'VDU1', 1))
        self.assertNotEqual(self._get_vnfc_id(inst_18, 'VDU2', 0),
                            self._get_vnfc_id(inst_20, 'VDU2', 0))
        # check storage ids are changed
        self.assertNotEqual(self._get_vnfc_storage_ids(inst_18, 'VDU1', 0),
                            self._get_vnfc_storage_ids(inst_20, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_storage_ids(inst_18, 'VDU1', 1),
                            self._get_vnfc_storage_ids(inst_20, 'VDU1', 1))
        self.assertNotEqual(self._get_vnfc_storage_ids(inst_18, 'VDU2', 0),
                            self._get_vnfc_storage_ids(inst_20, 'VDU2', 0))
        # check cps are changed
        for cp_1 in ['VDU1_CP1', 'VDU1_CP2', 'VDU2_CP2']:
            self.assertNotEqual(
                self._get_vnf_ext_cp_id(inst_18, cp_1.split('_')[0], 0, cp_1),
                self._get_vnf_ext_cp_id(inst_20, cp_1.split('_')[0], 0, cp_1))
        for cp_2 in ['VDU1_CP3', 'VDU1_CP4', 'VDU1_CP5',
                     'VDU2_CP3', 'VDU2_CP4', 'VDU2_CP5']:
            self.assertNotEqual(
                self._get_vnf_link_port_id(inst_18,
                                           cp_2.split('_')[0], 0, cp_2),
                self._get_vnf_link_port_id(inst_20,
                                           cp_2.split('_')[0], 0, cp_2))
        for ext_cp in ['VDU1_CP1', 'VDU1_CP2']:
            self.assertNotEqual(
                self._get_vnf_ext_cp_id(
                    inst_10, ext_cp.split('_')[0], 1, ext_cp),
                self._get_vnf_ext_cp_id(
                    inst_12, ext_cp.split('_')[0], 1, ext_cp))
        for link_port_cp in ['VDU1_CP3', 'VDU1_CP4', 'VDU1_CP5']:
            self.assertNotEqual(
                self._get_vnf_link_port_id(
                    inst_10, link_port_cp.split('_')[0], 1, link_port_cp),
                self._get_vnf_link_port_id(
                    inst_12, link_port_cp.split('_')[0], 1, link_port_cp))

        # 21. Change external connectivity
        change_ext_conn_req = paramgen.change_ext_conn_max(
            self.net_ids, self.subnet_ids, self.auth_url)
        self._add_additional_params(change_ext_conn_req)
        resp, body = self.change_ext_conn(inst_id, change_ext_conn_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 22. Show VNF instance(check for change-ext-conn)
        inst_22 = self._check_for_show_operation(
            'CHANGE_EXT_CONN', expected_inst_attrs, inst_id)
        # check vnfExtCPIds of VDU are changed
        for ext_cp in ['VDU1_CP1', 'VDU2_CP2']:
            self.assertNotEqual(
                self._get_vnf_ext_cp_id(
                    inst_20, ext_cp.split('_')[0], 0, ext_cp),
                self._get_vnf_ext_cp_id(
                    inst_22, ext_cp.split('_')[0], 0, ext_cp))
            if ext_cp.split('_')[0] == 'VDU1':
                self.assertNotEqual(
                    self._get_vnf_ext_cp_id(
                        inst_20, ext_cp.split('_')[0], 1, ext_cp),
                    self._get_vnf_ext_cp_id(
                        inst_22, ext_cp.split('_')[0], 1, ext_cp))

        # 23. Scale in operation
        scalein_req = paramgen.scalein_vnf_max()
        self._add_additional_params(scalein_req)
        resp, body = self.scale_vnf_instance(inst_id, scalein_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 24. Show VNF instance(check for scale)
        vdu_result = {'VDU1': {0}, 'VDU2': {0}}
        image_result = {'VDU1': {'image-VDU1-VirtualStorage-0'},
                        'VDU2': {'image-VDU2-VirtualStorage-0'}}
        inst_24 = self._check_for_show_operation(
            'SCALE', expected_inst_attrs, inst_id,
            vdu_result, image_result)

        # 25. Update VNF
        # check attribute value before update VNF
        # check usageState of max pattern VNF Package
        self.check_package_usage(self.max_pkg, 'IN_USE')
        # check usageState of update max pattern VNF Package
        self.check_package_usage(self.upd_max_pkg)
        # check vnfd id
        self.assertEqual(self.max_vnfd_id, inst_24['vnfdId'])
        # check vnfc info
        vnfc_info = inst_24['instantiatedVnfInfo']['vnfcInfo']
        self.assertGreater(len(vnfc_info), 1)
        vnfc_ids = [vnfc['id'] for vnfc in vnfc_info]
        for vnfc in vnfc_info:
            self.assertIn('id', vnfc)
            self.assertIn('vduId', vnfc)
            self.assertIsNotNone(vnfc.get('vnfcState'))
            self.assertIsNone(vnfc.get('vnfcConfigurableProperties'))

        update_req = paramgen.update_vnf_max(self.upd_max_vnfd_id, vnfc_ids)
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 26. Show VNF instance(check for update)
        vdu_result = {'VDU1': {0}, 'VDU2': {0}}
        inst_26 = self._check_for_show_operation(
            'MODIFY_INFO', expected_inst_attrs, inst_id, vdu_result)
        # check usageState of max pattern VNF Package
        self.check_package_usage(self.max_pkg)
        # check usageState of update max pattern VNF Package
        self.check_package_usage(self.upd_max_pkg, 'IN_USE')
        self.assertEqual(self.upd_max_vnfd_id, inst_26['vnfdId'])
        self.assertEqual('new name', inst_26['vnfInstanceName'])
        self.assertEqual('new description', inst_26['vnfInstanceDescription'])
        dummy_key_value = {'dummy-key': 'dummy-value'}
        self.assertEqual(dummy_key_value, inst_26['metadata'])
        self.assertEqual(dummy_key_value, inst_26['extensions'])
        self.assertEqual(dummy_key_value, inst_26['vnfConfigurableProperties'])
        vim_connection_info = {
            "vim2": {
                "vimId": "ac2d2ece-5e49-4b15-b92d-b681e9c096d8",
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                "interfaceInfo": {
                    "endpoint": "http://127.0.0.1/identity/v3"
                },
                "accessInfo": {
                    "username": "dummy_user",
                    "region": "RegionOne",
                    "project": "dummy_project",
                    "projectDomain": "Default",
                    "userDomain": "Default"
                },
                "extra": {
                    "dummy-key": "dummy-val"
                }
            }
        }
        self.assertEqual(vim_connection_info['vim2'],
                         inst_26['vimConnectionInfo']['vim2'])

        # check vnfc info
        vnfc_info = inst_26['instantiatedVnfInfo']['vnfcInfo']
        self.assertEqual(vnfc_ids[0], vnfc_info[0]['id'])
        self.assertEqual(vnfc_ids[1], vnfc_info[1]['id'])
        self.assertEqual(dummy_key_value,
                         vnfc_info[0]['vnfcConfigurableProperties'])
        self.assertEqual(dummy_key_value,
                         vnfc_info[1]['vnfcConfigurableProperties'])

        # 27. Scale out operation
        scaleout_req = paramgen.scaleout_vnf_max()
        self._add_additional_params(scaleout_req)
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 28. Heal VNF(all with omit all parameter)
        heal_req = paramgen.heal_vnf_all_max_with_parameter()
        self._add_additional_params(heal_req)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_name = f'vnf-{inst_id}'
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
                       (stack['resource_name'] in ['VDU1', 'VDU2'])]
        vdu1_0_stack_after_heal = [stack for stack in temp_stacks if
                                 (stack['resource_name'] == 'VDU1')][0]
        vdu1_1_stack_after_heal = [stack for stack in temp_stacks if
                                   (stack['resource_name'] == 'VDU1')][1]
        vdu2_stack_after_heal = [stack for stack in temp_stacks if
                                 (stack['resource_name'] == 'VDU2')][0]

        self.assertEqual("CREATE_COMPLETE",
                         vdu1_0_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
                         vdu1_1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
                         vdu2_stack_after_heal['resource_status'])

        # 29. Heal VNF(all with all=False parameter)
        heal_req = paramgen.heal_vnf_all_max_with_parameter(False)
        self._add_additional_params(heal_req)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
                       (stack['resource_name'] in ['VDU1', 'VDU2'])]
        vdu1_0_stack_after_heal = [stack for stack in temp_stacks if
                                 (stack['resource_name'] == 'VDU1')][0]
        vdu1_1_stack_after_heal = [stack for stack in temp_stacks if
                                   (stack['resource_name'] == 'VDU1')][1]
        vdu2_stack_after_heal = [stack for stack in temp_stacks if
                                 (stack['resource_name'] == 'VDU2')][0]

        self.assertEqual("CREATE_COMPLETE",
                         vdu1_0_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
                         vdu1_1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
                         vdu2_stack_after_heal['resource_status'])

        # 30. Heal VNF(all with all=True parameter)
        heal_req = paramgen.heal_vnf_all_max_with_parameter(True)
        self._add_additional_params(heal_req)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("CREATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [
            stack for stack in nested_stacks
            if (stack['resource_name'] in
                ['VDU1', 'VDU2', 'VDU1-VirtualStorage',
                 'VDU2-VirtualStorage', 'internalVL3'])]
        vdu1_0_stack_after_heal = [stack for stack in temp_stacks if
                                 (stack['resource_name'] == 'VDU1')][0]
        vdu1_1_stack_after_heal = [stack for stack in temp_stacks if
                                   (stack['resource_name'] == 'VDU1')][1]
        vdu2_stack_after_heal = [stack for stack in temp_stacks if
                                 (stack['resource_name'] == 'VDU2')][0]
        storage1_0_stack_after_heal = [
            stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1-VirtualStorage')][0]
        storage1_1_stack_after_heal = [
            stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1-VirtualStorage')][1]
        storage2_stack_after_heal = [
            stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2-VirtualStorage')][0]
        network_stack_after_heal = [
            stack for stack in temp_stacks if
            (stack['resource_name'] == 'internalVL3')][0]

        self.assertEqual("CREATE_COMPLETE",
                         vdu1_0_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
                         vdu1_1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
                         vdu2_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
                         storage1_0_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
                         storage1_1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
                         storage2_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
                         network_stack_after_heal['resource_status'])

        # 31. Terminate VNF
        terminate_req = paramgen.terminate_vnf_max()
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

        # 32. Delete VNF
        self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
