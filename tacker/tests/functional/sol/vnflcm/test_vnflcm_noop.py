# Copyright (C) 2020 FUJITSU
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

from oslo_utils import uuidutils

from tacker.objects import fields
from tacker.tests.functional import base
from tacker.tests.functional.sol.vnflcm import base as vnflcm_base
from tacker.tests import utils


class VnfLcmTestNoop(vnflcm_base.BaseVnfLcmTest):

    prepare_network = False

    @classmethod
    def setUpClass(cls):
        cls.tacker_client = base.BaseTackerTest.tacker_http_client()

        csar_path, _ = vnflcm_base._create_csar_with_unique_vnfd_id(
            utils.test_etc_sample("etsi/nfv",
                                  "test_inst_terminate_vnf_with_vnflcmnoop"))
        cls.vnf_package, cls.vnfd_id = (
            vnflcm_base._create_and_upload_vnf_package(
                cls.tacker_client, {"key": "file_functional"},
                csar_path))

        super(VnfLcmTestNoop, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        # Update operational state to DISABLED and delete vnf package
        for package_id in [cls.vnf_package]:
            vnflcm_base._delete_vnf_package(cls.tacker_client, package_id)

        super(VnfLcmTestNoop, cls).tearDownClass()

    def setUp(self):
        super(VnfLcmTestNoop, self).setUp()

    def test_instantiate_terminate_vnf_with_vnflcmnoop(self):
        # Create subscription and register it.
        subscription_id = self.register_subscription()
        self.addCleanup(self._delete_subscription, subscription_id)

        # create vnf instance
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 1"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id,
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)
        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)
        # instantiate vnf instance
        request_body = vnflcm_base._create_instantiate_vnf_request_body(
            "simple", vim_id=self.vim['id'])
        resp, _ = self._instantiate_vnf_instance(vnf_instance["id"],
                                                 request_body)
        self.assertEqual(202, resp.status_code)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance["id"])

        # show vnf instance
        _, vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        # terminate vnf instance
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }
        resp, _ = self._terminate_vnf_instance(
            vnf_instance['id'], terminate_req_body)
        self.assertEqual(202, resp.status_code)
        self._wait_lcm_done('COMPLETED', vnf_instance_id=vnf_instance["id"])

        # delete vnf instance
        self._delete_vnf_instance(vnf_instance['id'])
