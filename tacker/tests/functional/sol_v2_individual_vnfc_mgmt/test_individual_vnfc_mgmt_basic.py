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
MIN_VNFD_ID = f"{SUPPORT_STRING_FOR_VNFD_ID}min_vnfd_id"
UPD_MAX_VNFD_ID = f"{SUPPORT_STRING_FOR_VNFD_ID}upd_max_vnfd_id"
NEW_MAX_VNFD_ID = f"{SUPPORT_STRING_FOR_VNFD_ID}new_max_vnfd_id"
UPD_NEW_MIN_VNFD_ID = f"{SUPPORT_STRING_FOR_VNFD_ID}upd_new_min_vnfd_id"


class IndividualVnfcMgmtBasicTest(base_v2.BaseSolV2Test):

    @classmethod
    def setUpClass(cls):
        super(IndividualVnfcMgmtBasicTest, cls).setUpClass()
        cur_dir = os.path.dirname(__file__)
        image_path = utils.test_etc_sample("etsi/nfv/common/Files/images",
            "cirros-0.5.2-x86_64-disk.img")

        # tacker/tests/functional/sol_v2_individual_vnfc_mgmt(here)
        #       /sol_refactored
        userdata_dir = os.path.join(
            cur_dir, "../../../sol_refactored/infra_drivers/openstack")
        userdata_file = "userdata_standard.py"
        userdata_path = os.path.abspath(
            os.path.join(userdata_dir, userdata_file))

        # vnf package for basic lcms tests max pattern
        pkg_path_1 = utils.test_sample("functional/sol_v2_common",
            "basic_lcms_max_individual_vnfc")
        cls.max_pkg, cls.max_vnfd_id = cls.create_vnf_package(
            pkg_path_1, image_path=image_path,
            userdata_path=userdata_path, vnfd_id=MAX_VNFD_ID)

        # vnf package for basic lcms tests min pattern
        pkg_path_2 = utils.test_sample("functional/sol_v2_common",
            "basic_lcms_min_individual_vnfc")
        cls.min_pkg, cls.min_vnfd_id = cls.create_vnf_package(
            pkg_path_2, userdata_path=userdata_path,
            vnfd_id=MIN_VNFD_ID)

        # vnf package for update vnf max pattern
        pkg_path_3 = utils.test_sample("functional/sol_v2_common",
            "update_vnf_max_individual_vnfc")
        cls.upd_max_pkg, cls.upd_max_vnfd_id = cls.create_vnf_package(
            pkg_path_3, image_path=image_path,
            userdata_path=userdata_path, vnfd_id=UPD_MAX_VNFD_ID)

        # vnf package for change vnf package max pattern
        pkg_path_4 = utils.test_sample("functional/sol_v2_common",
            "change_vnfpkg_max_individual_vnfc")
        cls.new_max_pkg, cls.new_max_vnfd_id = cls.create_vnf_package(
            pkg_path_4, userdata_path=userdata_path,
            vnfd_id=NEW_MAX_VNFD_ID)

        # vnf package for change vnf package or update min pattern
        pkg_path_5 = utils.test_sample("functional/sol_v2_common",
            "change_vnfpkg_or_update_min_individual_vnfc")
        cls.upd_new_min_pkg, cls.upd_new_min_vnfd_id = cls.create_vnf_package(
            pkg_path_5, image_path=image_path, userdata_path=userdata_path,
            vnfd_id=UPD_NEW_MIN_VNFD_ID)

        cls.expected_list_attrs = [
            'id',
            'operationState',
            'stateEnteredTime',
            'startTime',
            'vnfInstanceId',
            # 'grantId', # omitted
            'operation',
            'isAutomaticInvocation',
            # 'operationParams', # omitted
            'isCancelPending',
            # 'cancelMode', # omitted
            # 'error', # omitted
            # 'resourceChanges', # omitted
            # 'changedInfo', # omitted
            # 'changedExtConnectivity', # omitted
            # 'modificationsTriggeredByVnfPkgChange', # omitted
            # 'vnfSnapshotInfoId', # omitted
            '_links'
        ]

        cls._pre_setting()

    @classmethod
    def tearDownClass(cls):
        super(IndividualVnfcMgmtBasicTest, cls).tearDownClass()
        cls.delete_vnf_package(cls.max_pkg)
        cls.delete_vnf_package(cls.min_pkg)
        cls.delete_vnf_package(cls.upd_max_pkg)
        cls.delete_vnf_package(cls.new_max_pkg)
        cls.delete_vnf_package(cls.upd_new_min_pkg)

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

    def _get_vnfc_flavor(self, inst, vdu, index):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        # must exist
        return vnfc['metadata']['flavor']

    def _get_vnfc_cps(self, inst, vdu, index):
        vnfc = self._get_vnfc_by_vdu_index(inst, vdu, index)
        return {cp_info['cpdId'] for cp_info in vnfc['vnfcCpInfo']}

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

    def test_basic_lcms_max(self):
        """Test LCM operations for individual vnfc mgmt with all attributes set

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
          - 2. Show VNF instance(check for instantiate)
          - 3. List VNF instance with attribute-based filtering
          - 4. Show VNF LCM operation occurrence
          - 5. Heal VNF(all with omit all parameter)
          - 6. Show VNF instance(check for heal)
          - 7. List VNF LCM operation occurrence with attribute-based
               filtering
          - 8. Heal VNF(all with all=True parameter)
          - 9. Show VNF instance(check for heal)
          - 10. Scale out operation
          - 11. Show VNF instance(check for scale)
          - 12. Scale in operation
          - 13. Show VNF instance(check for scale)
          - 14. Heal VNF(vnfc)
          - 15. Show VNF instance(check for heal)
          - 16. Change external connectivity
          - 17. Show VNF instance(check for change-ext-conn)
          - 18. Heal VNF(vnfc with omit all parameter)
          - 19. Show VNF instance(check for heal)
          - 20. Heal VNF(vnfc with all=False parameter)
          - 21. Show VNF instance(check for heal)
          - 22. Heal VNF(vnfc with all=True parameter)
          - 23. Show VNF instance(check for heal)
          - 24. Update VNF
          - 25. Show VNF instance(check for update)
          - 26. Update VNF(again)
          - 27. Change current VNF Package
          - 28. Show VNF instance(check for change-vnfpkg)
          - 29. Terminate VNF
          - 30. Delete VNF
        """
        # 0. Create VNF
        create_req = paramgen.create_vnf_max(
            self.max_vnfd_id,
            description="test for basic_lcms_max_individual_vnfc")
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

        # check that the servers set in "zone:Affinity" are
        # deployed on 'nova' AZ.
        # NOTE: local_nfvo returns this AZ
        vdu1_details = self.get_server_details('VDU1')
        vdu2_details = self.get_server_details('VDU2')
        vdu1_az = vdu1_details.get('OS-EXT-AZ:availability_zone')
        vdu2_az = vdu2_details.get('OS-EXT-AZ:availability_zone')
        self.assertEqual('nova', vdu1_az)
        self.assertEqual('nova', vdu2_az)

        # 2. Show VNF instance(check for instantiate)
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
        inst_2 = self._check_for_show_operation(
            'INSTANTIATE', expected_inst_attrs, inst_id,
            vdu_result, image_result)

        # 3. List VNF instance with attribute-based filtering
        # check Link in 'list_vnf_instance'
        # The Response Header will contain a 'Link' Header only when there
        # are at least two vnf instance data in the database, so it needs to
        # create an unused data.
        create_req = paramgen.create_vnf_min(self.min_vnfd_id)
        _, tmp_body = self.create_vnf_instance(create_req)
        resp, body = self.list_vnf_instance()
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_index(resp)
        # * all_fields
        #   -> check the attribute omitted in "exclude_default" is set.
        filter_expr = {'filter': f'(eq,id,{inst_id})', 'all_fields': ''}
        resp, body = self.list_vnf_instance(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for inst in body:
            self.assertIn('vnfInstanceName', inst)
            self.assertIn('vnfInstanceDescription', inst)
            self.assertIn('vimConnectionInfo', inst)
            self.assertIn('instantiatedVnfInfo', inst)
            self.assertIn('metadata', inst)
        # * fields=<list>
        #   -> check the attribute specified in "fields" is set
        filter_expr = {'filter': f'(eq,id,{inst_id})',
                       'fields': 'metadata'}
        resp, body = self.list_vnf_instance(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for inst in body:
            self.assertNotIn('vnfInstanceName', inst)
            self.assertNotIn('vnfInstanceDescription', inst)
            self.assertNotIn('vimConnectionInfo', inst)
            self.assertNotIn('instantiatedVnfInfo', inst)
            self.assertIn('metadata', inst)
        # * exclude_fields=<list>
        #   -> check the attribute specified in "exclude_fields" is not set
        filter_expr = {'filter': f'(eq,id,{inst_id})',
                       'exclude_fields': 'vnfInstanceName'}
        resp, body = self.list_vnf_instance(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for inst in body:
            self.assertNotIn('vnfInstanceName', inst)
            self.assertIn('vnfInstanceDescription', inst)
            self.assertIn('vimConnectionInfo', inst)
            self.assertIn('instantiatedVnfInfo', inst)
            self.assertIn('metadata', inst)
        # * exclude_default
        #   -> check the attribute omitted in "exclude_default" is not set.
        filter_expr = {'filter': f'(eq,id,{inst_id})',
                       'exclude_default': ''}
        resp, body = self.list_vnf_instance(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for inst in body:
            self.assertIn('vnfInstanceName', inst)
            self.assertIn('vnfInstanceDescription', inst)
            self.assertNotIn('vimConnectionInfo', inst)
            self.assertNotIn('instantiatedVnfInfo', inst)
            self.assertNotIn('metadata', inst)
        self.delete_vnf_instance(tmp_body['id'])

        # 4. Show VNF LCM operation occurrence
        expected_attrs = [
            'id',
            'operationState',
            'stateEnteredTime',
            'startTime',
            'vnfInstanceId',
            'grantId',
            'operation',
            'isAutomaticInvocation',
            'operationParams',
            'isCancelPending',
            # 'cancelMode', # omitted
            # 'error', # omitted
            'resourceChanges',
            # 'changedInfo', # omitted
            # 'changedExtConnectivity', # omitted
            # 'modificationsTriggeredByVnfPkgChange', # omitted
            # 'vnfSnapshotInfoId', # omitted
            '_links'
        ]
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 5. Heal VNF(all with omit all parameter)
        heal_req = paramgen.heal_vnf_all_max_with_parameter()
        self._add_additional_params(heal_req)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 6. Show VNF instance(check for heal)
        vdu_result = {'VDU1': {0}, 'VDU2': {0}}
        inst_6 = self._check_for_show_operation(
            'HEAL', expected_inst_attrs, inst_id, vdu_result)
        # check ids of VDU are changed
        self.assertNotEqual(self._get_vnfc_id(inst_2, 'VDU1', 0),
                            self._get_vnfc_id(inst_6, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_id(inst_2, 'VDU2', 0),
                            self._get_vnfc_id(inst_6, 'VDU2', 0))
        # check images are not changed
        self.assertEqual(self._get_vnfc_image(inst_2, 'VDU1', 0),
                         self._get_vnfc_image(inst_6, 'VDU1', 0))
        self.assertEqual(self._get_vnfc_image(inst_2, 'VDU2', 0),
                         self._get_vnfc_image(inst_6, 'VDU2', 0))

        # 7. List VNF LCM operation occurrence with attribute-based filtering
        # * all_fields
        #   -> check the attribute omitted in "exclude_default" is set.
        resp, body = self.list_lcmocc()
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_index(resp)
        filter_expr = {'filter': f'(eq,id,{lcmocc_id})', 'all_fields': ''}
        resp, body = self.list_lcmocc(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for lcmocc in body:
            self.assertIn('operationParams', lcmocc)
            self.assertIn('resourceChanges', lcmocc)
        # * fields=<list>
        #   -> check the attribute specified in "fields" is set
        filter_expr = {'filter': f'(eq,id,{lcmocc_id})',
                       'fields': 'operationParams'}
        resp, body = self.list_lcmocc(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for lcmocc in body:
            self.assertIn('operationParams', lcmocc)
            self.assertNotIn('resourceChanges', lcmocc)
        # * exclude_fields=<list>
        #   -> check the attribute specified in "exclude_fields" is not set
        filter_expr = {'filter': f'(eq,id,{lcmocc_id})',
                       'exclude_fields': 'operationParams'}
        resp, body = self.list_lcmocc(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for lcmocc in body:
            self.assertNotIn('operationParams', lcmocc)
            self.assertIn('resourceChanges', lcmocc)
        # * exclude_default
        #   -> check the attribute omitted in "exclude_default" is not set.
        filter_expr = {'filter': f'(eq,id,{lcmocc_id})',
                       'exclude_default': ''}
        resp, body = self.list_lcmocc(filter_expr)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        for lcmocc in body:
            self.assertNotIn('operationParams', lcmocc)
            self.assertNotIn('resourceChanges', lcmocc)

        # 8. Heal VNF(all with all=True parameter)
        heal_req = paramgen.heal_vnf_all_max_with_parameter(True)
        self._add_additional_params(heal_req)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 9. Show VNF instance(check for heal)
        vdu_result = {'VDU1': {0}, 'VDU2': {0}}
        inst_9 = self._check_for_show_operation(
            'HEAL', expected_inst_attrs, inst_id, vdu_result)
        # check all ids of VDU are changed
        self.assertNotEqual(self._get_vnfc_id(inst_6, 'VDU1', 0),
                            self._get_vnfc_id(inst_9, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_id(inst_6, 'VDU2', 0),
                            self._get_vnfc_id(inst_9, 'VDU2', 0))
        # check storage ids are changed
        self.assertNotEqual(self._get_vnfc_storage_ids(inst_6, 'VDU1', 0),
                            self._get_vnfc_storage_ids(inst_9, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_storage_ids(inst_6, 'VDU2', 0),
                            self._get_vnfc_storage_ids(inst_9, 'VDU2', 0))
        # check cps are changed
        for cp_1 in ['VDU1_CP1', 'VDU1_CP2', 'VDU2_CP2']:
            self.assertNotEqual(
                self._get_vnf_ext_cp_id(inst_6, cp_1.split('_')[0], 0, cp_1),
                self._get_vnf_ext_cp_id(inst_9, cp_1.split('_')[0], 0, cp_1))
        for cp_2 in ['VDU1_CP3', 'VDU1_CP4', 'VDU1_CP5',
                     'VDU2_CP3', 'VDU2_CP4', 'VDU2_CP5']:
            self.assertNotEqual(
                self._get_vnf_link_port_id(inst_6,
                                           cp_2.split('_')[0], 0, cp_2),
                self._get_vnf_link_port_id(inst_9,
                                           cp_2.split('_')[0], 0, cp_2))

        # 10. Scale out operation
        scaleout_req = paramgen.scaleout_vnf_max()
        self._add_additional_params(scaleout_req)
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 11. Show VNF instance(check for scale)
        vdu_result = {'VDU1': {0, 1}, 'VDU2': {0}}
        image_result = {'VDU1': {'image-VDU1-VirtualStorage-0',
                                 'image-VDU1-VirtualStorage-1'},
                        'VDU2': {'image-VDU2-VirtualStorage-0'}}
        _ = self._check_for_show_operation(
            'SCALE', expected_inst_attrs, inst_id,
            vdu_result, image_result)

        # 12. Scale in operation
        scalein_req = paramgen.scalein_vnf_max()
        self._add_additional_params(scalein_req)
        resp, body = self.scale_vnf_instance(inst_id, scalein_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 13. Show VNF instance(check for scale)
        vdu_result = {'VDU1': {0}, 'VDU2': {0}}
        image_result = {'VDU1': {'image-VDU1-VirtualStorage-0'},
                        'VDU2': {'image-VDU2-VirtualStorage-0'}}
        inst_13 = self._check_for_show_operation(
            'SCALE', expected_inst_attrs, inst_id,
            vdu_result, image_result)

        # 14. Heal VNF(vnfc)
        vnfc_info = inst_13['instantiatedVnfInfo']['vnfcInfo']
        vnfc_id = [vnfc['id'] for vnfc in vnfc_info
                   if ("VDU2" == vnfc['vduId'])][0]
        heal_req = paramgen.heal_vnf_vnfc_max(vnfc_id)
        self._add_additional_params(heal_req)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 15. Show VNF instance(check for heal)
        vdu_result = {'VDU1': {0}, 'VDU2': {0}}
        inst_15 = self._check_for_show_operation(
            'HEAL', expected_inst_attrs, inst_id, vdu_result)
        # check id of VDU2 is changed
        self.assertNotEqual(self._get_vnfc_id(inst_13, 'VDU2', 0),
                            self._get_vnfc_id(inst_15, 'VDU2', 0))
        # check image of VDU2 is not changed
        self.assertEqual(self._get_vnfc_image(inst_13, 'VDU2', 0),
                         self._get_vnfc_image(inst_15, 'VDU2', 0))

        # 16. Change external connectivity
        change_ext_conn_req = paramgen.change_ext_conn_max(
            self.net_ids, self.subnet_ids, self.auth_url)
        self._add_additional_params(change_ext_conn_req)
        resp, body = self.change_ext_conn(inst_id, change_ext_conn_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 17. Show VNF instance(check for change-ext-conn)
        vdu_result = {'VDU1': {0}, 'VDU2': {0}}
        inst_17 = self._check_for_show_operation(
            'CHANGE_EXT_CONN', expected_inst_attrs, inst_id, vdu_result)
        # check vnfExtCPIds of VDU are changed
        for ext_cp in ['VDU1_CP1', 'VDU2_CP2']:
            self.assertNotEqual(
                self._get_vnf_ext_cp_id(
                    inst_15, ext_cp.split('_')[0], 0, ext_cp),
                self._get_vnf_ext_cp_id(
                    inst_17, ext_cp.split('_')[0], 0, ext_cp))

        # 18. Heal VNF(vnfc with omit all parameter)
        vnfc_info = inst_17['instantiatedVnfInfo']['vnfcInfo']
        vnfc_ids = [vnfc['id'] for vnfc in vnfc_info]
        heal_req = paramgen.heal_vnf_vnfc_max_with_parameter(vnfc_ids)
        self._add_additional_params(heal_req)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 19. Show VNF instance(check for heal)
        vdu_result = {'VDU1': {0}, 'VDU2': {0}}
        inst_19 = self._check_for_show_operation(
            'HEAL', expected_inst_attrs, inst_id, vdu_result)
        # check all ids of VDU are changed
        self.assertNotEqual(self._get_vnfc_id(inst_17, 'VDU1', 0),
                            self._get_vnfc_id(inst_19, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_id(inst_17, 'VDU2', 0),
                            self._get_vnfc_id(inst_19, 'VDU2', 0))
        # check images are not changed
        self.assertEqual(self._get_vnfc_image(inst_17, 'VDU1', 0),
                         self._get_vnfc_image(inst_19, 'VDU1', 0))
        self.assertEqual(self._get_vnfc_image(inst_17, 'VDU2', 0),
                         self._get_vnfc_image(inst_19, 'VDU2', 0))

        # 20. Heal VNF(vnfc with all=False parameter)
        vnfc_info = inst_19['instantiatedVnfInfo']['vnfcInfo']
        vnfc_ids = [vnfc['id'] for vnfc in vnfc_info]
        heal_req = paramgen.heal_vnf_vnfc_max_with_parameter(vnfc_ids, False)
        self._add_additional_params(heal_req)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 21. Show VNF instance(check for heal)
        vdu_result = {'VDU1': {0}, 'VDU2': {0}}
        inst_21 = self._check_for_show_operation(
            'HEAL', expected_inst_attrs, inst_id, vdu_result)
        # check all ids of VDU are changed
        self.assertNotEqual(self._get_vnfc_id(inst_19, 'VDU1', 0),
                            self._get_vnfc_id(inst_21, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_id(inst_19, 'VDU2', 0),
                            self._get_vnfc_id(inst_21, 'VDU2', 0))
        # check images are not changed
        self.assertEqual(self._get_vnfc_image(inst_19, 'VDU1', 0),
                         self._get_vnfc_image(inst_21, 'VDU1', 0))
        self.assertEqual(self._get_vnfc_image(inst_19, 'VDU2', 0),
                         self._get_vnfc_image(inst_21, 'VDU2', 0))

        # 22. Heal VNF(vnfc with all=True parameter)
        vnfc_info = inst_21['instantiatedVnfInfo']['vnfcInfo']
        vnfc_ids = [vnfc['id'] for vnfc in vnfc_info]
        heal_req = paramgen.heal_vnf_vnfc_max_with_parameter(vnfc_ids, True)
        self._add_additional_params(heal_req)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 23. Show VNF instance(check for heal)
        vdu_result = {'VDU1': {0}, 'VDU2': {0}}
        inst_23 = self._check_for_show_operation(
            'HEAL', expected_inst_attrs, inst_id, vdu_result)
        # check all ids of VDU are changed
        self.assertNotEqual(self._get_vnfc_id(inst_21, 'VDU1', 0),
                            self._get_vnfc_id(inst_23, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_id(inst_21, 'VDU2', 0),
                            self._get_vnfc_id(inst_23, 'VDU2', 0))
        # check storage ids are changed
        self.assertNotEqual(self._get_vnfc_storage_ids(inst_21, 'VDU1', 0),
                            self._get_vnfc_storage_ids(inst_23, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_storage_ids(inst_21, 'VDU2', 0),
                            self._get_vnfc_storage_ids(inst_23, 'VDU2', 0))
        # 24. Update VNF
        # check attribute value before update VNF
        # check usageState of max pattern VNF Package
        self.check_package_usage(self.max_pkg, 'IN_USE')
        # check usageState of update VNF Package
        self.check_package_usage(self.upd_max_pkg)
        # check vnfd id
        self.assertEqual(self.max_vnfd_id, inst_23['vnfdId'])

        vnfc_info = inst_23['instantiatedVnfInfo']['vnfcInfo']
        vnfc_ids = [vnfc['id'] for vnfc in vnfc_info]
        update_req = paramgen.update_vnf_max(self.upd_max_vnfd_id, vnfc_ids)
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 25. Show VNF instance(check for update)
        vdu_result = {'VDU1': {0}, 'VDU2': {0}}
        inst_25 = self._check_for_show_operation(
            'MODIFY_INFO', expected_inst_attrs, inst_id, vdu_result)
        # check usageState of max pattern VNF Package
        self.check_package_usage(self.max_pkg)
        # check usageState of update max pattern VNF Package
        self.check_package_usage(self.upd_max_pkg, 'IN_USE')
        self.assertEqual(self.upd_max_vnfd_id, inst_25['vnfdId'])
        self.assertEqual('new name', inst_25['vnfInstanceName'])
        self.assertEqual('new description', inst_25['vnfInstanceDescription'])
        dummy_key_value = {'dummy-key': 'dummy-value'}
        self.assertEqual(dummy_key_value, inst_25['metadata'])
        self.assertEqual(dummy_key_value, inst_25['extensions'])
        self.assertEqual(dummy_key_value, inst_25['vnfConfigurableProperties'])

        # 26. Update VNF(again)
        # check usageState of max pattern VNF Package
        self.check_package_usage(self.max_pkg)
        # check usageState of update max pattern VNF Package
        self.check_package_usage(self.upd_max_pkg, 'IN_USE')
        # check vnfd id
        self.assertEqual(self.upd_max_vnfd_id, inst_25['vnfdId'])

        update_req = paramgen.update_vnf_min_with_parameter(self.max_vnfd_id)
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 27. Change current VNF Package
        # check usageState of max pattern VNF Package
        self.check_package_usage(self.max_pkg, 'IN_USE')
        # check usageState of update max pattern VNF Package
        self.check_package_usage(self.upd_max_pkg)
        # check usageState of new max pattern VNF Package
        self.check_package_usage(self.new_max_pkg)
        change_vnf_pkg_req = paramgen.change_vnf_pkg_individual_vnfc_max(
            self.new_max_vnfd_id, self.net_ids, self.subnet_ids)
        resp, body = self.change_vnfpkg(inst_id, change_vnf_pkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 28. Show VNF instance(check for change-vnfpkg)
        # check usageState of max pattern VNF Package
        self.check_package_usage(self.max_pkg)
        # check usageState of new max pattern VNF Package
        self.check_package_usage(self.new_max_pkg, 'IN_USE')
        vdu_result = {'VDU1': {0}, 'VDU2': {0}}
        inst_28 = self._check_for_show_operation(
            'CHANGE_VNFPKG', expected_inst_attrs, inst_id, vdu_result)
        # check vnfdId
        self.assertEqual(self.new_max_vnfd_id, inst_28['vnfdId'])
        # check all ids of VDU are changed
        self.assertNotEqual(self._get_vnfc_id(inst_25, 'VDU1', 0),
                            self._get_vnfc_id(inst_28, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_id(inst_25, 'VDU2', 0),
                            self._get_vnfc_id(inst_28, 'VDU2', 0))
        # check images of VDU are changed
        self.assertNotEqual(self._get_vnfc_image(inst_25, 'VDU1', 0),
                            self._get_vnfc_image(inst_28, 'VDU1', 0))
        self.assertNotEqual(self._get_vnfc_image(inst_25, 'VDU2', 0),
                            self._get_vnfc_image(inst_28, 'VDU2', 0))
        self.assertEqual('cirros-0.5.2-x86_64-disk',
                         self._get_vnfc_image(inst_28, 'VDU1', 0))
        self.assertEqual('cirros-0.5.2-x86_64-disk',
                         self._get_vnfc_image(inst_28, 'VDU2', 0))
        # check flavor is changed (VDU2 only)
        self.assertNotEqual(self._get_vnfc_flavor(inst_25, 'VDU2', 0),
                            self._get_vnfc_flavor(inst_28, 'VDU2', 0))
        # check vnfExtCPId of VDU1_CP1 is changed
        self.assertNotEqual(
            self._get_vnf_ext_cp_id(inst_25, 'VDU1', 0, 'VDU1_CP1'),
            self._get_vnf_ext_cp_id(inst_28, 'VDU1', 0, 'VDU1_CP1'))
        # check external CPs, VDU1_CP6 and VDU2_CP6 are added
        self.assertFalse('VDU1_CP6' in self._get_vnfc_cps(inst_25, 'VDU1', 0))
        self.assertFalse('VDU2_CP6' in self._get_vnfc_cps(inst_25, 'VDU2', 0))
        self.assertTrue('VDU1_CP6' in self._get_vnfc_cps(inst_28, 'VDU1', 0))
        self.assertTrue('VDU2_CP6' in self._get_vnfc_cps(inst_28, 'VDU2', 0))
        # check internal CPs, VDU1_CP5 and VDU2_CP5 are changed
        self.assertEqual("internalVL3", self._get_vnfc_cp_net_name(
            inst_25, 'VDU1', 0, 'VDU1_CP5'))
        self.assertEqual("internalVL3", self._get_vnfc_cp_net_name(
            inst_25, 'VDU2', 0, 'VDU2_CP5'))
        self.assertEqual("internalVL4", self._get_vnfc_cp_net_name(
            inst_28, 'VDU1', 0, 'VDU1_CP5'))
        self.assertEqual("internalVL4", self._get_vnfc_cp_net_name(
            inst_28, 'VDU2', 0, 'VDU2_CP5'))

        # 29. Terminate VNF
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

        # 30. Delete VNF
        self.exec_lcm_operation(self.delete_vnf_instance, inst_id)

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

    def test_retry_rollback_scale_out(self):
        """Test retry and rollback scale out operations

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
          - 3. Scale out operation(will fail)
          - 4. Show VNF instance
          - 5. Retry operation
          - 6. Rollback scale out operation
          - 7. Show VNF LCM operation occurrence
          - 8. List VNF LCM operation occurrence
          - 9. Terminate VNF
          - 10. Delete VNF
        """
        # 0. Create VNF
        create_req = paramgen.create_vnf_max(
            self.max_vnfd_id,
            description="test for retry and rollback scale out")
        _, body = self.create_vnf_instance(create_req)
        inst_id = body['id']

        # 1. Instantiate VNF instance
        instantiate_req = paramgen.instantiate_vnf_max(
            self.net_ids, self.subnet_ids, None, self.auth_url,
            user_data=True)
        resp, body = self.instantiate_vnf_instance(
            inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 2. Show VNF instance(check for instantiate)
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
        _ = self._check_for_show_operation(
            'INSTANTIATE', expected_inst_attrs, inst_id)

        # 3. Scale out operation(will fail)
        self.put_fail_file('scale_end')
        scaleout_req = paramgen.scaleout_vnf_max()
        self._add_additional_params(scaleout_req)
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)

        # 4. Show VNF instance
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # 5. Retry scale out operation
        resp, body = self.retry_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        self.wait_lcmocc_failed_temp(lcmocc_id)
        self.rm_fail_file('scale_end')

        # 6. Rollback scale out operation
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # 7. Show VNF LCM operation occurrence
        expected_attrs = [
            'id',
            'operationState',
            'stateEnteredTime',
            'startTime',
            'vnfInstanceId',
            'grantId',
            'operation',
            'isAutomaticInvocation',
            'operationParams',
            'isCancelPending',
            # 'cancelMode', # omitted
            'error',
            # 'resourceChanges', # omitted
            # 'changedInfo', # omitted
            # 'changedExtConnectivity', # omitted
            # 'modificationsTriggeredByVnfPkgChange', # omitted
            # 'vnfSnapshotInfoId', # omitted
            '_links'
        ]
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 8. List VNF LCM operation occurrence
        resp, body = self.list_lcmocc()
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_index(resp)
        for lcmocc in body:
            self.check_resp_body(lcmocc, self.expected_list_attrs)

        # 9. Terminate VNF instance
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
                         body.get('instantiationState'))

        # 10. Delete VNF
        self.exec_lcm_operation(self.delete_vnf_instance, inst_id)

    def test_rollback_instantiate(self):
        """Test rollback instantiate operation

        * About attributes:
          Omit except for required attributes.
          Only the following cardinality attributes are set.
          - 1
          - 1..N (1)

        * About LCM operations:
          This test includes the following operations.
          - 0. Create VNF
          - 1. Instantiate VNF(will fail)
          - 2. Show VNF instance
          - 3. Rollback instantiation operation
          - 4. Show VNF LCM operation occurrence
          - 5. List VNF LCM operation occurrence
          - 6. Delete VNF
        """
        # 0. Create VNF
        create_req = paramgen.create_vnf_min(self.min_vnfd_id)
        _, body = self.create_vnf_instance(create_req)
        inst_id = body['id']

        # 1. Instantiate VNF(will fail)
        self.put_fail_file('instantiate_end')
        instantiate_req = paramgen.instantiate_vnf_min()
        self._add_additional_params(instantiate_req)
        resp, body = self.instantiate_vnf_instance(
            inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)
        self.rm_fail_file('instantiate_end')

        # 2. Show VNF instance
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
            # 'vimConnectionInfo', # omitted
            'instantiationState',
            # 'instantiatedVnfInfo', # omitted
            # 'metadata', # omitted
            # 'extensions', # omitted
            '_links'
        ]
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body.get('instantiationState'))

        # 3. Rollback instantiation operation
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # 4. Show VNF LCM operation occurrence
        expected_attrs = [
            'id',
            'operationState',
            'stateEnteredTime',
            'startTime',
            'vnfInstanceId',
            'grantId',
            'operation',
            'isAutomaticInvocation',
            'operationParams',
            'isCancelPending',
            # 'cancelMode', # omitted
            'error',
            # 'resourceChanges', # omitted
            # 'changedInfo', # omitted
            # 'changedExtConnectivity', # omitted
            # 'modificationsTriggeredByVnfPkgChange', # omitted
            # 'vnfSnapshotInfoId', # omitted
            '_links'
        ]
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 5. List VNF LCM operation occurrence
        resp, body = self.list_lcmocc()
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_index(resp)
        for lcmocc in body:
            self.check_resp_body(lcmocc, self.expected_list_attrs)

        # 6. Delete VNF
        self.exec_lcm_operation(self.delete_vnf_instance, inst_id)

    def test_rollback_chgextconn_and_update(self):
        """Test rollback change_ext_conn and update operation

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
          - 3. Change external connectivity(will fail)
          - 4. Rollback change_ext_conn operation
          - 5. Show VNF LCM operation occurrence
          - 6. List VNF LCM operation occurrence
          - 7. Update VNF(will fail)
          - 8. Rollback update operation
          - 9. Show VNF LCM operation occurrence
          - 10. List VNF LCM operation occurrence
          - 11. Terminate VNF
          - 12. Delete VNF
        """
        # 0. Create VNF
        create_req = paramgen.create_vnf_max(self.max_vnfd_id)
        _, body = self.create_vnf_instance(create_req)
        inst_id = body['id']

        # 1. Instantiate VNF
        instantiate_req = paramgen.instantiate_vnf_max(
            self.net_ids, self.subnet_ids, None, self.auth_url,
            user_data=True)
        self._add_additional_params(instantiate_req)
        resp, body = self.instantiate_vnf_instance(
            inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 2. Show VNF instance
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
        _ = self._check_for_show_operation(
            'INSTANTIATE', expected_inst_attrs, inst_id)

        # 3. Change external connectivity(will fail)
        self.put_fail_file('change_external_connectivity_end')
        change_ext_conn_req = paramgen.change_ext_conn_min(
            self.net_ids, self.subnet_ids)
        self._add_additional_params(change_ext_conn_req)
        resp, body = self.change_ext_conn(inst_id, change_ext_conn_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)
        self.rm_fail_file('change_external_connectivity_end')

        # 4. Rollback change_ext_conn operation
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # 5. Show VNF LCM operation occurrence
        expected_attrs = [
            'id',
            'operationState',
            'stateEnteredTime',
            'startTime',
            'vnfInstanceId',
            'grantId',
            'operation',
            'isAutomaticInvocation',
            'operationParams',
            'isCancelPending',
            # 'cancelMode', # omitted
            'error',
            # 'resourceChanges', # omitted
            # 'changedInfo', # omitted
            # 'changedExtConnectivity', # omitted
            # 'modificationsTriggeredByVnfPkgChange', # omitted
            # 'vnfSnapshotInfoId', # omitted
            '_links'
        ]
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # Confirm that the operation failed in change_ext_conn_end after
        # change_ext_conn.
        self.assertIn(
            'change_external_connectivity_end failed', body['error']['detail'])

        # 6. List VNF LCM operation occurrence
        resp, body = self.list_lcmocc()
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_index(resp)
        for lcmocc in body:
            self.check_resp_body(lcmocc, self.expected_list_attrs)

        # 7. Update VNF(will fail)
        self.put_fail_file('modify_information_start')
        update_req = paramgen.update_vnf_min()
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)
        self.rm_fail_file('modify_information_start')

        # 8. Rollback update operation
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # 9. Show VNF LCM operation occurrence
        expected_attrs = [
            'id',
            'operationState',
            'stateEnteredTime',
            'startTime',
            'vnfInstanceId',
            # 'grantId', # omitted
            'operation',
            'isAutomaticInvocation',
            'operationParams',
            'isCancelPending',
            # 'cancelMode', # omitted
            'error',
            # 'resourceChanges', # omitted
            # 'changedInfo', # omitted
            # 'changedExtConnectivity', # omitted
            # 'modificationsTriggeredByVnfPkgChange', # omitted
            # 'vnfSnapshotInfoId', # omitted
            '_links'
        ]
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 10. List VNF LCM operation occurrence
        resp, body = self.list_lcmocc()
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_index(resp)
        for lcmocc in body:
            self.check_resp_body(lcmocc, self.expected_list_attrs)

        # 11. Terminate VNF
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

        # 12. Delete VNF
        self.exec_lcm_operation(self.delete_vnf_instance, inst_id)

    def test_rollback_change_vnfpkg(self):
        """Test rollback change_vnfpkg operation

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
          - 3. Change Current VNF Package(will fail)
          - 4. Rollback change_vnfpkg operation
          - 5. Show VNF LCM operation occurrence
          - 6. Show VNF instance
          - 7. Change Current VNF Package(will fail)
          - 8. Rollback change_vnfpkg operation
          - 9. Show VNF LCM operation occurrence
          - 10. List VNF LCM operation occurrence
          - 11. Show VNF instance
          - 12. Terminate VNF
          - 13. Delete VNF
        """
        # 0. Create VNF
        create_req = paramgen.create_vnf_max(
            self.max_vnfd_id,
            description="test for rollback change vnf package")
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

        # 2. Show VNF instance(check for instantiate)
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
        inst_2 = self._check_for_show_operation(
            'INSTANTIATE', expected_inst_attrs, inst_id)

        # 3. Change Current VNF Package(will fail)
        self.put_fail_file('change_vnfpkg')
        change_vnf_pkg_req = paramgen.change_vnf_pkg_individual_vnfc_max(
            self.new_max_vnfd_id, self.net_ids, self.subnet_ids)
        resp, body = self.change_vnfpkg(inst_id, change_vnf_pkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)
        self.rm_fail_file('change_vnfpkg')

        # 4. Rollback change_vnfpkg operation
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # 5. Show VNF LCM operation occurrence
        expected_attrs = [
            'id',
            'operationState',
            'stateEnteredTime',
            'startTime',
            'vnfInstanceId',
            'grantId',
            'operation',
            'isAutomaticInvocation',
            'operationParams',
            'isCancelPending',
            # 'cancelMode', # omitted
            'error',
            # 'resourceChanges', # omitted
            # 'changedInfo', # omitted
            # 'changedExtConnectivity', # omitted
            # 'modificationsTriggeredByVnfPkgChange', # omitted
            # 'vnfSnapshotInfoId', # omitted
            '_links'
        ]
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # 6. Show VNF instance
        _, inst_6 = self.show_vnf_instance(inst_id)
        # check vnfdId
        self.assertEqual(self.max_vnfd_id, inst_6['vnfdId'])
        # check images of VDU are not changed
        self.assertEqual(self._get_vnfc_image(inst_2, 'VDU1', 0),
                         self._get_vnfc_image(inst_6, 'VDU1', 0))
        self.assertEqual(self._get_vnfc_image(inst_2, 'VDU2', 0),
                         self._get_vnfc_image(inst_6, 'VDU2', 0))
        # check flavor of VDU2 is not changed
        self.assertEqual(self._get_vnfc_flavor(inst_2, 'VDU2', 0),
                         self._get_vnfc_flavor(inst_6, 'VDU2', 0))
        # check external CPs, VDU1_CP6 and VDU2_CP6 are not added
        self.assertFalse('VDU1_CP6' in self._get_vnfc_cps(inst_2, 'VDU1', 0))
        self.assertFalse('VDU2_CP6' in self._get_vnfc_cps(inst_2, 'VDU2', 0))
        self.assertFalse('VDU1_CP6' in self._get_vnfc_cps(inst_6, 'VDU1', 0))
        self.assertFalse('VDU2_CP6' in self._get_vnfc_cps(inst_6, 'VDU2', 0))
        # check internal CPs, VDU1_CP5 and VDU2_CP5 are not changed
        self.assertEqual("internalVL3", self._get_vnfc_cp_net_name(
            inst_2, 'VDU1', 0, 'VDU1_CP5'))
        self.assertEqual("internalVL3", self._get_vnfc_cp_net_name(
            inst_2, 'VDU2', 0, 'VDU2_CP5'))
        self.assertEqual("internalVL3", self._get_vnfc_cp_net_name(
            inst_6, 'VDU1', 0, 'VDU1_CP5'))
        self.assertEqual("internalVL3", self._get_vnfc_cp_net_name(
            inst_6, 'VDU2', 0, 'VDU2_CP5'))

        # 7. Change Current VNF Package(will fail)
        # This operation intentionally performs an operation outside the
        # supported range, making it in the FAILED_TEMP state to test the
        # rollback operation in this case.
        # supported cases:
        #   1. change VM created by image to VM created by new image
        #   2. change VM created by volume to VM created by new volume
        change_vnf_pkg_req = paramgen.change_vnf_pkg_individual_vnfc_min(
            self.upd_new_min_vnfd_id, vdu2_old_vnfc='VDU2_CP2')
        resp, body = self.change_vnfpkg(inst_id, change_vnf_pkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)

        # 8. Rollback change_vnfpkg operation
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_delete(resp)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # 9. Show VNF LCM operation occurrence
        expected_attrs = [
            'id',
            'operationState',
            'stateEnteredTime',
            'startTime',
            'vnfInstanceId',
            'grantId',
            'operation',
            'isAutomaticInvocation',
            'operationParams',
            'isCancelPending',
            # 'cancelMode', # omitted
            'error',
            # 'resourceChanges', # omitted
            # 'changedInfo', # omitted
            # 'changedExtConnectivity', # omitted
            # 'modificationsTriggeredByVnfPkgChange', # omitted
            # 'vnfSnapshotInfoId', # omitted
            '_links'
        ]
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_attrs)

        # Confirm that the operation failed in change vnf package progress
        # while executing update_stack operation

        self.assertIn('StackValidationFailed', body['error']['detail'])

        # 10. List VNF LCM operation occurrence
        resp, body = self.list_lcmocc()
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_index(resp)
        for lcmocc in body:
            self.check_resp_body(lcmocc, self.expected_list_attrs)

        # 11. Show VNF instance
        _, inst_11 = self.show_vnf_instance(inst_id)
        # check vnfdId
        self.assertEqual(self.max_vnfd_id, inst_11['vnfdId'])
        # check images of VDU are not changed
        self.assertEqual(self._get_vnfc_image(inst_2, 'VDU1', 0),
                         self._get_vnfc_image(inst_11, 'VDU1', 0))
        self.assertEqual(self._get_vnfc_image(inst_2, 'VDU2', 0),
                         self._get_vnfc_image(inst_11, 'VDU2', 0))

        # 12. Terminate VNF
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

        # 13. Delete VNF
        self.exec_lcm_operation(self.delete_vnf_instance, inst_id)

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
