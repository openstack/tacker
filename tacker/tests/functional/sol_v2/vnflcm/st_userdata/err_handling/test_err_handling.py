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
NEW_MAX_VNFD_ID = f"{SUPPORT_STRING_FOR_VNFD_ID}new_max_vnfd_id"
UPD_NEW_MIN_VNFD_ID = f"{SUPPORT_STRING_FOR_VNFD_ID}upd_new_min_vnfd_id"


class IndividualVnfcMgmtErrorHandlingTest(base_v2.BaseSolV2Test):

    @classmethod
    def setUpClass(cls):
        super(IndividualVnfcMgmtErrorHandlingTest, cls).setUpClass()
        image_path = utils.test_etc_sample("etsi/nfv/common/Files/images",
            "cirros-0.5.2-x86_64-disk.img")

        userdata_path = utils.userdata("userdata_standard.py")

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

        # vnf package for change vnf package max pattern
        pkg_path_3 = utils.test_sample("functional/sol_v2_common",
            "change_vnfpkg_max_individual_vnfc")
        cls.new_max_pkg, cls.new_max_vnfd_id = cls.create_vnf_package(
            pkg_path_3, userdata_path=userdata_path,
            vnfd_id=NEW_MAX_VNFD_ID)

        # vnf package for change vnf package or update min pattern
        pkg_path_4 = utils.test_sample("functional/sol_v2_common",
            "change_vnfpkg_or_update_min_individual_vnfc")
        cls.upd_new_min_pkg, cls.upd_new_min_vnfd_id = cls.create_vnf_package(
            pkg_path_4, image_path=image_path, userdata_path=userdata_path,
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
        super(IndividualVnfcMgmtErrorHandlingTest, cls).tearDownClass()
        cls.delete_vnf_package(cls.max_pkg)
        cls.delete_vnf_package(cls.min_pkg)
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
        # NOTE: The Link header may not be included depending on
        # the execution order, so the headers check is commented out.
        # self.check_resp_headers_in_index(resp)
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
