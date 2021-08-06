# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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

from tacker.tests.functional.sol_v2 import base_v2
from tacker.tests.functional.sol_v2 import paramgen


class VnfLcmTest(base_v2.BaseSolV2Test):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmTest, cls).setUpClass()

        cur_dir = os.path.dirname(__file__)
        # tacker/tests/etc...
        #             /functional/sol_v2
        image_dir = os.path.join(
            cur_dir, "../../etc/samples/etsi/nfv/common/Files/images")
        image_file = "cirros-0.5.2-x86_64-disk.img"
        image_path = os.path.abspath(os.path.join(image_dir, image_file))

        sample1_path = os.path.join(cur_dir, "samples/sample1")
        cls.vnf_pkg_1, cls.vnfd_id_1 = cls.create_vnf_package(
            sample1_path, image_path=image_path)

        sample2_path = os.path.join(cur_dir, "samples/sample2")
        # no image contained
        cls.vnf_pkg_2, cls.vnfd_id_2 = cls.create_vnf_package(sample2_path)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmTest, cls).tearDownClass()

        cls.delete_vnf_package(cls.vnf_pkg_1)
        cls.delete_vnf_package(cls.vnf_pkg_2)

    def setUp(self):
        super(VnfLcmTest, self).setUp()

    def test_api_versions(self):
        path = "/vnflcm/api_versions"
        resp, body = self.tacker_client.do_request(
            path, "GET", version="2.0.0")
        self.assertEqual(200, resp.status_code)
        expected_body = {
            "uriPrefix": "/vnflcm",
            "apiVersions": [
                {'version': '1.3.0', 'isDeprecated': False},
                {'version': '2.0.0', 'isDeprecated': False}
            ]
        }
        self.assertEqual(body, expected_body)

        path = "/vnflcm/v2/api_versions"
        resp, body = self.tacker_client.do_request(
            path, "GET", version="2.0.0")
        self.assertEqual(200, resp.status_code)
        expected_body = {
            "uriPrefix": "/vnflcm/v2",
            "apiVersions": [
                {'version': '2.0.0', 'isDeprecated': False}
            ]
        }
        self.assertEqual(body, expected_body)

    def test_sample1(self):
        create_req = paramgen.sample1_create(self.vnfd_id_1)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        net_ids = self.get_network_ids(['net0', 'net1', 'net_mgmt'])
        subnet_ids = self.get_subnet_ids(['subnet0', 'subnet1'])
        instantiate_req = paramgen.sample1_instantiate(
            net_ids, subnet_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        # TODO(oda-g): check body

        terminate_req = paramgen.sample1_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)

    def test_sample2(self):
        create_req = paramgen.sample2_create(self.vnfd_id_2)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        net_ids = self.get_network_ids(['net0', 'net1', 'net_mgmt'])
        subnet_ids = self.get_subnet_ids(['subnet0', 'subnet1'])
        instantiate_req = paramgen.sample2_instantiate(
            net_ids, subnet_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        # TODO(oda-g): check body

        terminate_req = paramgen.sample2_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # wait a bit because there is a bit time lag between lcmocc DB
        # update and terminate completion.
        time.sleep(10)

        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
