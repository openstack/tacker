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

from tacker.tests.functional.sol_kubernetes_v2 import base_v2
from tacker.tests.functional.sol_kubernetes_v2 import paramgen
from tacker.tests import utils


class VnfLcmKubernetesContainerUpdate(base_v2.BaseVnfLcmKubernetesV2Test):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmKubernetesContainerUpdate, cls).setUpClass()
        cur_dir = os.path.dirname(__file__)

        test_cnf_container_update_before_path = utils.test_sample(
            "functional/sol_kubernetes_v2/test_cnf_container_update_before")
        mgmt_driver_path = os.path.join(
            cur_dir,
            "../../../sol_refactored/mgmt_drivers/container_update_mgmt_v2.py")
        cls.vnf_package_id_before, cls.vnfd_id_before = cls.create_vnf_package(
            test_cnf_container_update_before_path,
            mgmt_driver=mgmt_driver_path)

        test_cnf_container_update_after_path = utils.test_sample(
            "functional/sol_kubernetes_v2/test_cnf_container_update_after")
        cls.vnf_package_id_after, cls.vnfd_id_after = cls.create_vnf_package(
            test_cnf_container_update_after_path, mgmt_driver=mgmt_driver_path)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmKubernetesContainerUpdate, cls).tearDownClass()

        cls.delete_vnf_package(cls.vnf_package_id_before)
        cls.delete_vnf_package(cls.vnf_package_id_after)

    def test_container_update_multi_kinds(self):
        """Test CNF update with MgmtDriver

        * About LCM operations:
          This test includes the following operations.
          - 1. Create a new VNF instance resource
          - 2. Instantiate a VNF instance
          - 3. Show VNF instance
          - 4. Update a VNF instance
          - 5. Show VNF instance
          - 6. Terminate a VNF instance
          - 7. Delete a VNF instance
        """

        # 1. Create a new VNF instance resource
        create_req = paramgen.test_cnf_update_create(self.vnfd_id_before)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # 2. Instantiate a VNF instance
        vim_id = self.get_k8s_vim_id()
        instantiate_req = paramgen.test_cnf_update_instantiate(vim_id)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 3. Show VNF instance
        _, vnf_instance_before = self.show_vnf_instance(inst_id)
        before_vnfc_rscs = vnf_instance_before['instantiatedVnfInfo'][
            'vnfcResourceInfo']
        self.assertEqual(8, len(before_vnfc_rscs))

        # 4. Update a VNF instance
        update_req = paramgen.test_cnf_update_modify(self.vnfd_id_after)
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 5. Show VNF instance
        _, vnf_instance_after = self.show_vnf_instance(inst_id)
        after_vnfc_rscs = vnf_instance_after['instantiatedVnfInfo'][
            'vnfcResourceInfo']

        self.assertEqual(8, len(after_vnfc_rscs))

        for after_vnfc_rsc in after_vnfc_rscs:
            for before_vnfc_rsc in before_vnfc_rscs:
                after_resource = after_vnfc_rsc['computeResource']
                before_resource = before_vnfc_rsc['computeResource']
                if after_vnfc_rsc['id'] == before_vnfc_rsc['id']:
                    if (after_resource['vimLevelResourceType'] in
                            ('Deployment', 'ReplicaSet', 'DaemonSet')
                            and after_vnfc_rsc['vduId'] in
                            ('VDU1', 'VDU2', 'VDU5')):
                        # check stored pod name is changed (Deployment)
                        self.assertNotEqual(before_resource['resourceId'],
                                            after_resource['resourceId'])
                    else:
                        # check stored pod name is not changed (other)
                        self.assertEqual(before_resource['resourceId'],
                                         after_resource['resourceId'])

        self.assertEqual(
            self.vnfd_id_after, vnf_instance_after['vnfdId'])
        self.assertEqual(
            'modify_vnf_after', vnf_instance_after['vnfInstanceName'])

        # 6. Terminate a VNF instance
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 7. Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)
