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
MIN_VNFD_ID = f"{SUPPORT_STRING_FOR_VNFD_ID}min_vnfd_id"
UPD_NEW_MIN_VNFD_ID = f"{SUPPORT_STRING_FOR_VNFD_ID}upd_new_min_vnfd_id"


class IndividualVnfcMgmtBasicMinTest(base_v2.BaseSolV2Test):

    @classmethod
    def setUpClass(cls):
        super(IndividualVnfcMgmtBasicMinTest, cls).setUpClass()
        image_path = utils.test_etc_sample("etsi/nfv/common/Files/images",
            "cirros-0.5.2-x86_64-disk.img")

        userdata_path = utils.userdata("userdata_standard.py")

        # vnf package for basic lcms tests min pattern
        pkg_path_1 = utils.test_sample("functional/sol_v2_common",
            "basic_lcms_min_individual_vnfc")
        cls.min_pkg, cls.min_vnfd_id = cls.create_vnf_package(
            pkg_path_1, userdata_path=userdata_path,
            vnfd_id=MIN_VNFD_ID)

        # vnf package for change vnf package or update min pattern
        pkg_path_2 = utils.test_sample("functional/sol_v2_common",
            "change_vnfpkg_or_update_min_individual_vnfc")
        cls.upd_new_min_pkg, cls.upd_new_min_vnfd_id = cls.create_vnf_package(
            pkg_path_2, image_path=image_path, userdata_path=userdata_path,
            vnfd_id=UPD_NEW_MIN_VNFD_ID)

    @classmethod
    def tearDownClass(cls):
        super(IndividualVnfcMgmtBasicMinTest, cls).tearDownClass()
        cls.delete_vnf_package(cls.min_pkg)
        cls.delete_vnf_package(cls.upd_new_min_pkg)

    def setUp(self):
        super().setUp()

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

    def _get_vnfc_flavor(self, inst, vdu, index):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        # must exist
        return vnfc['metadata']['flavor']

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

    def test_basic_lcms_min(self):
        """Test LCM operations with omitting except for required attributes

        The change_ext_conn can't be tested here because min pattern VNF
        package 2 don't have external connectivity. So moved it to the
        test_various_lcm_operations_before_and_after().

        * About attributes:
          Omit except for required attributes.
          Only the following cardinality attributes are set.
          - 1
          - 1..N (1)

        * About LCM operations:
          This test includes the following operations.
          - 0. Create VNF
          - 1. Instantiate VNF
          - 2. Show VNF instance(check for instantiate)
          - 3. Heal VNF(all with omit all parameter)
          - 4. Show VNF instance(check for heal)
          - 5. Scale out operation
          - 6. Show VNF instance(check for scale)
          - 7. Update VNF
          - 8. Show VNF instance(check for update)
          - 9. Heal VNF(vnfc)
          - 10. Show VNF instance(check for heal)
          - 11. Scale in operation
          - 12. Show VNF instance(check for scale)
          - 13. Terminate VNF
          - 14. Update VNF again
          - 15. Instantiate VNF again
          - 16. Change current VNF Package
          - 17. Show VNF instance(check for change-vnfpkg)
          - 18. Terminate VNF again
          - 19. Delete VNF
        """
        # 0. Create VNF
        create_req = paramgen.create_vnf_min(self.min_vnfd_id)
        _, body = self.create_vnf_instance(create_req)
        inst_id = body['id']

        # 1. Instantiate VNF
        instantiate_req = paramgen.instantiate_vnf_min()
        self._add_additional_params(instantiate_req)
        resp, body = self.instantiate_vnf_instance(
            inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check that the servers set in "nfvi_node:Affinity" are
        # deployed on the same host.
        # NOTE: it's up to heat to decide which host to deploy to
        vdu1_details = self.get_server_details('VDU1')
        vdu2_details = self.get_server_details('VDU2')
        vdu1_host = vdu1_details['hostId']
        vdu2_host = vdu2_details['hostId']
        self.assertEqual(vdu1_host, vdu2_host)

        # 2. Show VNF instance(check for instantiate)
        expected_inst_attrs = [
            'id',
            # 'vnfInstanceName', # omitted
            # 'vnfInstanceDescription', # omitted
            'vnfdId',
            'vnfProvider',
            'vnfProductName',
            'vnfSoftwareVersion',
            'vnfdVersion',
            # 'vnfConfigurableProperties', # omitted
            'vimConnectionInfo',
            'instantiationState',
            'instantiatedVnfInfo',
            # 'metadata', # omitted
            # 'extensions', # omitted
            '_links'
        ]
        vdu_result = {'VDU1': {0}, 'VDU2': {0}}
        image_result = {'VDU1': {'image-VDU1-0'},
                        'VDU2': {'image-VDU2-0'}}
        inst_2 = self._check_for_show_operation(
            'INSTANTIATE', expected_inst_attrs, inst_id,
            vdu_result, image_result)

        # 3. Heal VNF(all with omit all parameter)
        heal_req = paramgen.heal_vnf_all_min()
        self._add_additional_params(heal_req)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 4. Show VNF instance(check for heal)
        vdu_result = {'VDU1': {0}, 'VDU2': {0}}
        inst_4 = self._check_for_show_operation(
            'HEAL', expected_inst_attrs, inst_id, vdu_result)
        # check all ids of VDU are changed
        self.assertNotEqual(self._get_vnfc_id(inst_2, 'VDU1', 0),
                            self._get_vnfc_id(inst_4, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_id(inst_2, 'VDU2', 0),
                            self._get_vnfc_id(inst_4, 'VDU2', 0))

        # 5. Scale out operation
        scaleout_req = paramgen.scaleout_vnf_min()
        self._add_additional_params(scaleout_req)
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 6. Show VNF instance(check for scale)
        vdu_result = {'VDU1': {0, 1}, 'VDU2': {0}}
        image_result = {'VDU1': {'image-VDU1-0', 'image-VDU1-1'},
                        'VDU2': {'image-VDU2-0'}}
        _ = self._check_for_show_operation(
            'SCALE', expected_inst_attrs, inst_id,
            vdu_result, image_result)

        # 7. Update VNF
        update_req = paramgen.update_vnf_min_with_parameter(
            self.upd_new_min_vnfd_id)
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)
        # check usageState of min pattern VNF Package
        self.check_package_usage(self.min_pkg)
        # check usageState of update or new min pattern VNF Package
        self.check_package_usage(self.upd_new_min_pkg, 'IN_USE')

        # 8. Show VNF instance(check for update)
        inst_8 = self._check_for_show_operation(
            'MODIFY_INFO', expected_inst_attrs, inst_id)
        self.assertEqual(self.upd_new_min_vnfd_id, inst_8['vnfdId'])

        # 9. Heal VNF(vnfc)
        vnfc_info = inst_8['instantiatedVnfInfo']['vnfcInfo']
        vnfc_id = [vnfc['id'] for vnfc in vnfc_info
                   if (vnfc['vnfcResourceInfoId'] ==
                       self._get_vnfc_id(inst_8, 'VDU1', 1))][0]
        heal_req = paramgen.heal_vnf_vnfc_min(vnfc_id)
        self._add_additional_params(heal_req)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 10. Show VNF instance(check for heal)
        vdu_result = {'VDU1': {0, 1}, 'VDU2': {0}}
        inst_10 = self._check_for_show_operation(
            'HEAL', expected_inst_attrs, inst_id, vdu_result)
        # check id of VDU1 with index 1 is changed, with index 0 is not changed
        self.assertNotEqual(self._get_vnfc_id(inst_8, 'VDU1', 1),
                            self._get_vnfc_id(inst_10, 'VDU1', 1))
        self.assertEqual(self._get_vnfc_id(inst_8, 'VDU1', 0),
                         self._get_vnfc_id(inst_10, 'VDU1', 0))
        # check image value of image-VDU1-1 is changed, others are not changed
        self.assertNotEqual(self._get_vnfc_image(inst_8, 'VDU1', 1),
                            self._get_vnfc_image(inst_10, 'VDU1', 1))
        self.assertEqual(self._get_vnfc_image(inst_8, 'VDU1', 0),
                         self._get_vnfc_image(inst_10, 'VDU1', 0))

        # 11. Scale in operation
        scalein_req = paramgen.scalein_vnf_min()
        self._add_additional_params(scalein_req)
        resp, body = self.scale_vnf_instance(inst_id, scalein_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 12. Show VNF instance(check for scale)
        vdu_result = {'VDU1': {0}, 'VDU2': {0}}
        image_result = {'VDU1': {'image-VDU1-0'},
                        'VDU2': {'image-VDU2-0'}}
        _ = self._check_for_show_operation(
            'SCALE', expected_inst_attrs, inst_id,
            vdu_result, image_result)

        # 13. Terminate VNF
        terminate_req = paramgen.terminate_vnf_min()
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

        # 14. Update VNF again
        update_req = paramgen.update_vnf_min_with_parameter(self.min_vnfd_id)
        resp, body = self.exec_lcm_operation(self.update_vnf_instance,
                                      inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)
        # check usageState of min pattern VNF Package
        self.check_package_usage(self.min_pkg, 'IN_USE')
        # check usageState of update or new min pattern VNF Package
        self.check_package_usage(self.upd_new_min_pkg)

        # 15. Instantiate VNF again
        resp, body = self.instantiate_vnf_instance(
            inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)
        inst_15 = self._check_for_show_operation(
            'INSTANTIATE', expected_inst_attrs, inst_id)

        # 16. Change current VNF Package
        change_vnf_pkg_req = paramgen.change_vnf_pkg_individual_vnfc_min(
            self.upd_new_min_vnfd_id)
        resp, body = self.change_vnfpkg(inst_id, change_vnf_pkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 17. Show VNF instance(check for change-vnfpkg)
        # check usageState of min pattern VNF Package
        self.check_package_usage(self.min_pkg)
        # check usageState of update or new min pattern VNF Package
        self.check_package_usage(self.upd_new_min_pkg, 'IN_USE')
        inst_17 = self._check_for_show_operation(
            'CHANGE_VNFPKG', expected_inst_attrs, inst_id)
        # check vnfdId
        self.assertEqual(self.upd_new_min_vnfd_id, inst_17['vnfdId'])
        # check ids of VDU are not changed
        self.assertEqual(self._get_vnfc_id(inst_15, 'VDU1', 0),
                         self._get_vnfc_id(inst_17, 'VDU1', 0))
        self.assertEqual(self._get_vnfc_id(inst_15, 'VDU2', 0),
                         self._get_vnfc_id(inst_17, 'VDU2', 0))
        # check image of VDU1 is changed
        self.assertNotEqual(self._get_vnfc_image(inst_15, 'VDU1', 0),
                            self._get_vnfc_image(inst_17, 'VDU1', 0))
        # check flavors of VDU are not changed
        self.assertEqual(self._get_vnfc_flavor(inst_15, 'VDU1', 0),
                         self._get_vnfc_flavor(inst_17, 'VDU1', 0))
        self.assertEqual(self._get_vnfc_flavor(inst_15, 'VDU2', 0),
                         self._get_vnfc_flavor(inst_17, 'VDU2', 0))

        # 18. Terminate VNF again
        terminate_req = paramgen.terminate_vnf_min()
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

        # 19. Delete VNF
        self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
