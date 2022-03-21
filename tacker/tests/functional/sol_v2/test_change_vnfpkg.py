# Copyright (C) 2022 Fujitsu
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

import ddt
import os
import time

from tacker.tests.functional.sol_v2 import base_v2
from tacker.tests.functional.sol_v2 import paramgen


@ddt.ddt
class ChangeVnfPkgVnfLcmTest(base_v2.BaseSolV2Test):

    @classmethod
    def setUpClass(cls):
        super(ChangeVnfPkgVnfLcmTest, cls).setUpClass()

        cur_dir = os.path.dirname(__file__)
        # tacker/tests/etc...
        #             /functional/sol_v2
        image_dir = os.path.join(
            cur_dir, "../../etc/samples/etsi/nfv/common/Files/images")
        image_file = "cirros-0.5.2-x86_64-disk.img"
        image_path = os.path.abspath(os.path.join(image_dir, image_file))

        change_vnfpkg_from_image_to_image_path = os.path.join(
            cur_dir, "samples/test_instantiate_vnf_with_old_image_or_volume")
        cls.vnf_pkg_1, cls.vnfd_id_1 = cls.create_vnf_package(
            change_vnfpkg_from_image_to_image_path)

        change_vnfpkg_from_image_to_image_path_2 = os.path.join(
            cur_dir, "samples/test_change_vnf_pkg_with_new_image")
        cls.vnf_pkg_2, cls.vnfd_id_2 = cls.create_vnf_package(
            change_vnfpkg_from_image_to_image_path_2, image_path=image_path)

        change_vnfpkg_from_image_to_volume_path = os.path.join(
            cur_dir, "samples/test_change_vnf_pkg_with_new_volume")
        cls.vnf_pkg_3, cls.vnfd_id_3 = cls.create_vnf_package(
            change_vnfpkg_from_image_to_volume_path, image_path=image_path)

        change_vnfpkg_failed_in_update_path = os.path.join(
            cur_dir, "samples/test_change_vnf_pkg_with_update_failed")
        cls.vnf_pkg_4, cls.vnfd_id_4 = cls.create_vnf_package(
            change_vnfpkg_failed_in_update_path, image_path=image_path)

    @classmethod
    def tearDownClass(cls):
        super(ChangeVnfPkgVnfLcmTest, cls).tearDownClass()

        cls.delete_vnf_package(cls.vnf_pkg_1)
        cls.delete_vnf_package(cls.vnf_pkg_2)
        cls.delete_vnf_package(cls.vnf_pkg_3)
        cls.delete_vnf_package(cls.vnf_pkg_4)

    def setUp(self):
        super(ChangeVnfPkgVnfLcmTest, self).setUp()

    def test_change_vnfpkg_from_image_to_image(self):
        create_req = paramgen.change_vnfpkg_create(self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
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
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        net_ids = self.get_network_ids(['net0', 'net1', 'net_mgmt'])
        subnet_ids = self.get_subnet_ids(['subnet0', 'subnet1'])
        instantiate_req = paramgen.change_vnfpkg_instantiate(
            net_ids, subnet_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp_1, body_1 = self.show_vnf_instance(inst_id)
        stack_name = "vnf-{}".format(inst_id)
        stack_id = self.heat_client.get_stack_resource(stack_name)['stack'][
            'id']
        image_id_1 = self.get_current_vdu_image(stack_id, stack_name, 'VDU2')
        old_vnfd_id = body_1['vnfdId']

        self.assertEqual(200, resp_1.status_code)
        self.check_resp_headers_in_get(resp_1)
        self.check_resp_body(body_1, expected_inst_attrs)

        change_vnfpkg_req = paramgen.change_vnfpkg(self.vnfd_id_2)
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        resp_2, body_2 = self.show_vnf_instance(inst_id)
        image_id_2 = self.get_current_vdu_image(stack_id, stack_name, 'VDU2')
        self.assertNotEqual(image_id_1, image_id_2)

        self.assertEqual(200, resp_2.status_code)
        self.check_resp_headers_in_get(resp_2)
        self.check_resp_body(body_2, expected_inst_attrs)
        new_vnfd_id = [obj['metadata']['current_vnfd_id'] for obj in body_2[
            'instantiatedVnfInfo']['vnfcResourceInfo']][0]

        self.assertNotEqual(old_vnfd_id, new_vnfd_id)

        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

    def test_change_vnfpkg_from_image_to_volume(self):
        create_req = paramgen.change_vnfpkg_create(self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
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
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        net_ids = self.get_network_ids(['net0', 'net1', 'net_mgmt'])
        subnet_ids = self.get_subnet_ids(['subnet0', 'subnet1'])
        instantiate_req = paramgen.change_vnfpkg_instantiate(
            net_ids, subnet_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp_1, body_1 = self.show_vnf_instance(inst_id)
        stack_name = "vnf-{}".format(inst_id)
        stack_id = self.heat_client.get_stack_resource(stack_name)['stack'][
            'id']
        image_id_1 = self.get_current_vdu_image(stack_id, stack_name, 'VDU2')

        self.assertEqual(200, resp_1.status_code)
        self.check_resp_headers_in_get(resp_1)
        self.check_resp_body(body_1, expected_inst_attrs)
        resource_ids_1 = [obj['id'] for obj in body_1[
            'instantiatedVnfInfo']['vnfcResourceInfo'] if obj[
            'vduId'] == 'VDU2'][0]

        change_vnfpkg_req = paramgen.change_vnfpkg(self.vnfd_id_3)
        del change_vnfpkg_req['additionalParams']['vdu_params'][0]
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        resp_2, body_2 = self.show_vnf_instance(inst_id)
        image_id_2 = self.get_current_vdu_image(stack_id, stack_name, 'VDU2')
        storageResourceIds = [obj.get('storageResourceIds') for obj in body_2[
            'instantiatedVnfInfo']['vnfcResourceInfo'] if obj[
            'vduId'] == 'VDU2']
        self.assertIsNotNone(storageResourceIds)
        resource_ids_2 = [obj['id'] for obj in body_2[
            'instantiatedVnfInfo']['vnfcResourceInfo'] if obj[
            'vduId'] == 'VDU2'][0]
        self.assertNotEqual(resource_ids_1, resource_ids_2)
        self.assertNotEqual(image_id_1, image_id_2)

        self.assertEqual(200, resp_2.status_code)
        self.check_resp_headers_in_get(resp_2)
        self.check_resp_body(body_2, expected_inst_attrs)

        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

    def test_change_vnfpkg_from_volume_to_image(self):
        create_req = paramgen.change_vnfpkg_create(self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
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
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        net_ids = self.get_network_ids(['net0', 'net1', 'net_mgmt'])
        subnet_ids = self.get_subnet_ids(['subnet0', 'subnet1'])
        instantiate_req = paramgen.change_vnfpkg_instantiate(
            net_ids, subnet_ids, self.auth_url, flavor_id='volume')
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp_1, body_1 = self.show_vnf_instance(inst_id)
        stack_name = "vnf-{}".format(inst_id)
        stack_id = self.heat_client.get_stack_resource(stack_name)['stack'][
            'id']
        image_id_1 = self.get_current_vdu_image(stack_id, stack_name, 'VDU2')
        storageResourceIds_1 = [
            obj.get('storageResourceIds') for obj in body_1[
                'instantiatedVnfInfo']['vnfcResourceInfo']
            if obj['vduId'] == 'VDU2']
        resource_ids_1 = [obj['id'] for obj in body_1[
            'instantiatedVnfInfo']['vnfcResourceInfo'] if obj[
            'vduId'] == 'VDU2'][0]
        self.assertIsNotNone(storageResourceIds_1)

        self.assertEqual(200, resp_1.status_code)
        self.check_resp_headers_in_get(resp_1)
        self.check_resp_body(body_1, expected_inst_attrs)

        change_vnfpkg_req = paramgen.change_vnfpkg(self.vnfd_id_2)
        del change_vnfpkg_req['additionalParams']['vdu_params'][0]
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        resp_2, body_2 = self.show_vnf_instance(inst_id)
        image_id_2 = self.get_current_vdu_image(stack_id, stack_name, 'VDU2')
        storageResourceIds_2 = [
            obj.get('storageResourceIds') for obj in body_2[
                'instantiatedVnfInfo']['vnfcResourceInfo']
            if obj['vduId'] == 'VDU2']
        resource_ids_2 = [obj['id'] for obj in body_2[
            'instantiatedVnfInfo']['vnfcResourceInfo'] if obj[
            'vduId'] == 'VDU2'][0]
        self.assertIsNone(storageResourceIds_2[0])
        self.assertNotEqual(image_id_1, image_id_2)
        self.assertNotEqual(resource_ids_1, resource_ids_2)

        self.assertEqual(200, resp_2.status_code)
        self.check_resp_headers_in_get(resp_2)
        self.check_resp_body(body_2, expected_inst_attrs)

        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

    def test_change_vnfpkg_from_volume_to_volume(self):
        create_req = paramgen.change_vnfpkg_create(self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
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
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        net_ids = self.get_network_ids(['net0', 'net1', 'net_mgmt'])
        subnet_ids = self.get_subnet_ids(['subnet0', 'subnet1'])
        instantiate_req = paramgen.change_vnfpkg_instantiate(
            net_ids, subnet_ids, self.auth_url, flavor_id='volume')
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp_1, body_1 = self.show_vnf_instance(inst_id)
        stack_name = "vnf-{}".format(inst_id)
        stack_id = self.heat_client.get_stack_resource(stack_name)['stack'][
            'id']
        image_id_1 = self.get_current_vdu_image(stack_id, stack_name, 'VDU2')
        storageResourceId_1 = [
            obj.get('storageResourceIds') for obj in body_1[
                'instantiatedVnfInfo']['vnfcResourceInfo']
            if obj['vduId'] == 'VDU2']
        resource_ids_1 = [obj['id'] for obj in body_1[
            'instantiatedVnfInfo']['vnfcResourceInfo'] if obj[
            'vduId'] == 'VDU2'][0]

        self.assertEqual(200, resp_1.status_code)
        self.check_resp_headers_in_get(resp_1)
        self.check_resp_body(body_1, expected_inst_attrs)

        change_vnfpkg_req = paramgen.change_vnfpkg(self.vnfd_id_3)
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        resp_2, body_2 = self.show_vnf_instance(inst_id)
        image_id_2 = self.get_current_vdu_image(stack_id, stack_name, 'VDU2')
        storageResourceId_2 = [
            obj.get('storageResourceIds') for obj in body_2[
                'instantiatedVnfInfo']['vnfcResourceInfo']
            if obj['vduId'] == 'VDU2']
        resource_ids_2 = [obj['id'] for obj in body_2[
            'instantiatedVnfInfo']['vnfcResourceInfo'] if obj[
            'vduId'] == 'VDU2'][0]
        self.assertNotEqual(image_id_1, image_id_2)
        self.assertNotEqual(storageResourceId_1, storageResourceId_2)
        self.assertNotEqual(resource_ids_1, resource_ids_2)

        self.assertEqual(200, resp_2.status_code)
        self.check_resp_headers_in_get(resp_2)
        self.check_resp_body(body_2, expected_inst_attrs)

        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

    def test_change_vnfpkg_failed_in_update(self):
        create_req = paramgen.change_vnfpkg_create(self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
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
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        net_ids = self.get_network_ids(['net0', 'net1', 'net_mgmt'])
        subnet_ids = self.get_subnet_ids(['subnet0', 'subnet1'])
        instantiate_req = paramgen.change_vnfpkg_instantiate(
            net_ids, subnet_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp_1, body_1 = self.show_vnf_instance(inst_id)
        old_vnfd_id = body_1['vnfdId']

        self.assertEqual(200, resp_1.status_code)
        self.check_resp_headers_in_get(resp_1)
        self.check_resp_body(body_1, expected_inst_attrs)

        change_vnfpkg_req = paramgen.change_vnfpkg(self.vnfd_id_4)
        del change_vnfpkg_req['additionalParams']['vdu_params'][1]
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)

        resp, body = self.rollback(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        resp_2, body_2 = self.show_vnf_instance(inst_id)
        new_vnfd_id = [
            obj['metadata'].get('current_vnfd_id') for obj in body_2[
                'instantiatedVnfInfo']['vnfcResourceInfo']
            if obj['metadata'].get('current_vnfd_id')][0]
        self.assertEqual(old_vnfd_id, new_vnfd_id)

        self.assertEqual(200, resp_2.status_code)
        self.check_resp_headers_in_get(resp_2)
        self.check_resp_body(body_2, expected_inst_attrs)

        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

    def test_change_vnfpkg_failed_with_error_coordinate_vnf(self):
        create_req = paramgen.change_vnfpkg_create(self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
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
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        net_ids = self.get_network_ids(['net0', 'net1', 'net_mgmt'])
        subnet_ids = self.get_subnet_ids(['subnet0', 'subnet1'])
        instantiate_req = paramgen.change_vnfpkg_instantiate(
            net_ids, subnet_ids, self.auth_url, flavor_id='volume')
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp_1, body_1 = self.show_vnf_instance(inst_id)
        storageResourceId_1 = [
            obj.get('storageResourceIds') for obj in body_1[
                'instantiatedVnfInfo']['vnfcResourceInfo']
            if obj['vduId'] == 'VDU2']
        resource_ids_1 = [obj['id'] for obj in body_1[
            'instantiatedVnfInfo']['vnfcResourceInfo'] if obj[
            'vduId'] == 'VDU2'][0]

        self.assertEqual(200, resp_1.status_code)
        self.check_resp_headers_in_get(resp_1)
        self.check_resp_body(body_1, expected_inst_attrs)

        change_vnfpkg_req = paramgen.change_vnfpkg(self.vnfd_id_3)
        change_vnfpkg_req['additionalParams'][
            'lcm-operation-coordinate-new-vnf'
        ] = "./Scripts/error_coordinate_new_vnf.py"
        change_vnfpkg_req['additionalParams'][
            'lcm-operation-coordinate-new-vnf-class'
        ] = "ErrorCoordinateNewVnf"
        del change_vnfpkg_req['additionalParams']['vdu_params'][0]
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)

        resp, body = self.rollback(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        resp_2, body_2 = self.show_vnf_instance(inst_id)
        storageResourceId_2 = [
            obj.get('storageResourceIds') for obj in body_2[
                'instantiatedVnfInfo']['vnfcResourceInfo']
            if obj['vduId'] == 'VDU2']
        resource_ids_2 = [obj['id'] for obj in body_2[
            'instantiatedVnfInfo']['vnfcResourceInfo'] if obj[
            'vduId'] == 'VDU2'][0]

        self.assertEqual(200, resp_2.status_code)
        self.check_resp_headers_in_get(resp_2)
        self.check_resp_body(body_2, expected_inst_attrs)
        self.assertNotEqual(storageResourceId_1, storageResourceId_2)
        self.assertNotEqual(resource_ids_1, resource_ids_2)

        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)
