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

import os
import re
import time

from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from tacker.objects import fields
from tacker.tests.functional import base
from tacker.tests import utils

VNF_PACKAGE_UPLOAD_TIMEOUT = 300
VNF_INSTANTIATE_TIMEOUT = 600
VNF_TERMINATE_TIMEOUT = 600
VNF_HEAL_TIMEOUT = 600
RETRY_WAIT_TIME = 5


def _create_and_upload_vnf_package(tacker_client, csar_package_name,
                                   user_defined_data):
    # create vnf package
    body = jsonutils.dumps({"userDefinedData": user_defined_data})
    resp, vnf_package = tacker_client.do_request(
        '/vnfpkgm/v1/vnf_packages', "POST", body=body)

    # upload vnf package
    csar_package_path = "../../etc/samples/etsi/nfv/%s" % csar_package_name
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             csar_package_path))

    # Generating unique vnfd id. This is required when multiple workers
    # are running concurrently. The call below creates a new temporary
    # CSAR with unique vnfd id.
    file_path = utils.create_csar_with_unique_artifact(file_path)

    with open(file_path, 'rb') as file_object:
        resp, resp_body = tacker_client.do_request(
            '/vnfpkgm/v1/vnf_packages/{id}/package_content'.format(
                id=vnf_package['id']),
            "PUT", body=file_object, content_type='application/zip')

    # wait for onboard
    timeout = VNF_PACKAGE_UPLOAD_TIMEOUT
    start_time = int(time.time())
    show_url = os.path.join('/vnfpkgm/v1/vnf_packages', vnf_package['id'])
    vnfd_id = None
    while True:
        resp, body = tacker_client.do_request(show_url, "GET")
        if body['onboardingState'] == "ONBOARDED":
            vnfd_id = body['vnfdId']
            break

        if ((int(time.time()) - start_time) > timeout):
            raise Exception("Failed to onboard vnf package")

        time.sleep(1)

    # remove temporarily created CSAR file
    os.remove(file_path)
    return vnf_package['id'], vnfd_id


class VnfLcmTest(base.BaseTackerTest):

    @classmethod
    def setUpClass(cls):
        cls.tacker_client = base.BaseTackerTest.tacker_http_client()

        cls.vnf_package_resource, cls.vnfd_id_resource = \
            _create_and_upload_vnf_package(
                cls.tacker_client, "test_create_vnf_instance_and_instantiate_"
                                   "and_terminate_cnf_resources",
                {"key": "resource_functional"})

        super(VnfLcmTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        # Update vnf package operational state to DISABLED
        update_req_body = jsonutils.dumps({
            "operationalState": "DISABLED"})
        base_path = "/vnfpkgm/v1/vnf_packages"
        for package_id in [cls.vnf_package_resource]:
            resp, resp_body = cls.tacker_client.do_request(
                '{base_path}/{id}'.format(id=package_id,
                                          base_path=base_path),
                "PATCH", content_type='application/json',
                body=update_req_body)

            # Delete vnf package
            url = '/vnfpkgm/v1/vnf_packages/%s' % package_id
            cls.tacker_client.do_request(url, "DELETE")

        super(VnfLcmTest, cls).tearDownClass()

    def setUp(self):
        super(VnfLcmTest, self).setUp()
        self.base_url = "/vnflcm/v1/vnf_instances"

        vim_list = self.client.list_vims()
        if not vim_list:
            self.skipTest("Vims are not configured")

        vim_id = 'vim-kubernetes'
        vim = self.get_vim(vim_list, vim_id)
        if not vim:
            self.skipTest("Kubernetes VIM '%s' is missing" % vim_id)
        self.vim_id = vim['id']

    def _instantiate_vnf_instance_request(
            self, flavour_id, vim_id=None, additional_param=None):
        request_body = {"flavourId": flavour_id}

        if vim_id:
            request_body["vimConnectionInfo"] = [
                {"id": uuidutils.generate_uuid(),
                 "vimId": vim_id,
                 "vimType": "kubernetes"}]

        if additional_param:
            request_body["additionalParams"] = additional_param

        return request_body

    def _create_vnf_instance(self, vnfd_id, vnf_instance_name=None,
                             vnf_instance_description=None):
        request_body = {'vnfdId': vnfd_id}
        if vnf_instance_name:
            request_body['vnfInstanceName'] = vnf_instance_name

        if vnf_instance_description:
            request_body['vnfInstanceDescription'] = vnf_instance_description

        resp, response_body = self.http_client.do_request(
            self.base_url, "POST", body=jsonutils.dumps(request_body))
        return resp, response_body

    def _delete_wait_vnf_instance(self, id):
        timeout = VNF_TERMINATE_TIMEOUT
        url = os.path.join(self.base_url, id)
        start_time = int(time.time())
        while True:
            resp, body = self.http_client.do_request(url, "DELETE")
            if 204 == resp.status_code:
                break

            if ((int(time.time()) - start_time) > timeout):
                error = "Failed to delete vnf instance %s"
                self.fail(error % id)

            time.sleep(RETRY_WAIT_TIME)

    def _delete_vnf_instance(self, id):
        self._delete_wait_vnf_instance(id)

        # verify vnf instance is deleted
        url = os.path.join(self.base_url, id)
        resp, body = self.http_client.do_request(url, "GET")
        self.assertEqual(404, resp.status_code)

    def _show_vnf_instance(self, id, expected_result=None):
        show_url = os.path.join(self.base_url, id)
        resp, vnf_instance = self.http_client.do_request(show_url, "GET")
        self.assertEqual(200, resp.status_code)

        if expected_result:
            self.assertDictSupersetOf(expected_result, vnf_instance)

        return vnf_instance

    def _vnf_instance_wait(
            self, id,
            instantiation_state=fields.VnfInstanceState.INSTANTIATED,
            timeout=VNF_INSTANTIATE_TIMEOUT):
        show_url = os.path.join(self.base_url, id)
        start_time = int(time.time())
        while True:
            resp, body = self.http_client.do_request(show_url, "GET")
            if body['instantiationState'] == instantiation_state:
                break

            if ((int(time.time()) - start_time) > timeout):
                error = ("Vnf instance %(id)s status is %(current)s, "
                         "expected status should be %(expected)s")
                self.fail(error % {"id": id,
                                   "current": body['instantiationState'],
                                   "expected": instantiation_state})

            time.sleep(RETRY_WAIT_TIME)

    def _instantiate_vnf_instance(self, id, request_body):
        url = os.path.join(self.base_url, id, "instantiate")
        resp, body = self.http_client.do_request(
            url, "POST", body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)
        self._vnf_instance_wait(id)

    def _terminate_vnf_instance(self, id, request_body):
        url = os.path.join(self.base_url, id, "terminate")
        resp, body = self.http_client.do_request(
            url, "POST", body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)

        timeout = request_body.get('gracefulTerminationTimeout')
        start_time = int(time.time())

        self._vnf_instance_wait(
            id, instantiation_state=fields.VnfInstanceState.NOT_INSTANTIATED,
            timeout=VNF_TERMINATE_TIMEOUT)

        # If gracefulTerminationTimeout is set, check whether vnf
        # instantiation_state is set to NOT_INSTANTIATED after
        # gracefulTerminationTimeout seconds.
        if timeout and int(time.time()) - start_time < timeout:
            self.fail("Vnf is terminated before graceful termination "
                      "timeout period")

    def _get_server(self, server_id):
        try:
            self.novaclient().servers.get(server_id)
        except Exception:
            self.fail("Failed to get vdu resource %s id" % server_id)

    def _update_source_path(self, meta_dir, meta_name, port):
        meta_path = os.path.join(meta_dir, meta_name)
        with open(meta_path, 'r') as f:
            meta_content = f.read()
        new_meta_content = re.sub(
            r':(\d{5})', ':' + str(port), meta_content)
        with open(meta_path, 'w', encoding='utf-8') as f:
            f.write(new_meta_content)

    # The same problem as
    # https://github.com/kubernetes-client/python/issues/547,
    # after fixing this bug, the bindings test items can pass normally.
    # def test_inst_term_cnf_with_binding(self):
    #     vnf_instance_name = "vnf_with_instantiation_level-%s" % \
    #                         uuidutils.generate_uuid()
    #     vnf_instance_description = "vnf with instantiation level 1"
    #     resp, vnf_instance = self._create_vnf_instance(
    #         self.vnfd_id_resource,
    #         vnf_instance_name=vnf_instance_name,
    #         vnf_instance_description=vnf_instance_description)
    #
    #     self.assertIsNotNone(vnf_instance['id'])
    #     self.assertEqual(201, resp.status_code)
    #
    #     # generate body
    #     additional_param = {
    #         "lcm-kubernetes-def-files": [
    #             "Files/kubernetes/bindings.yaml"]}
    #     request_body = self._instantiate_vnf_instance_request(
    #         "simple", vim_id=self.vim_id, additional_param=additional_param)
    #
    #     # send request
    #     self._instantiate_vnf_instance(vnf_instance['id'], request_body)
    #
    #     vnf_instance = self._show_vnf_instance(vnf_instance['id'])
    #     self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')
    #
    #     time.sleep(20)
    #
    #     # Terminate vnf forcefully
    #     terminate_req_body = {
    #         "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
    #     }
    #
    #     self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)
    #     self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_with_clusterrole_clusterrolebinding_SA(self):
        # Create vnf instance
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 2"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource,
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # generate body
        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/clusterrole_clusterrolebinding_SA.yaml"]}
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        # send request
        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)
        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_with_config_map(self):
        # Create vnf instance
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 4"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource,
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # generate body
        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/config-map.yaml"]}
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        # send request
        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)
        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_with_controller_revision(self):
        # Create vnf instance
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 5"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource,
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # generate body
        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/controller-revision.yaml"]}
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        # send request
        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)
        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_with_daemon_set(self):
        # Create vnf instance
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 6"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource,
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # generate body
        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/daemon-set.yaml"]}
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        # send request
        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)
        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_with_deployment(self):
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 7"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource, vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # generate body
        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/deployment.yaml"]}
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        # send request
        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)
        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_with_horizontal_pod_autoscaler(self):
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 8"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource,
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # generate body
        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/horizontal-pod-autoscaler.yaml"]}
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        # send request
        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)
        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_with_job(self):
        # Create vnf instance
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 9"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource,
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # generate body
        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/job.yaml"]}
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        # send request
        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)
        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_with_limit_range(self):
        # Create vnf instance
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 10"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource,
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # generate body
        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/limit-range.yaml"]}
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        # send request
        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)
        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_with_namespace(self):
        # Create vnf instance
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 11"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource, vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # generate body
        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/namespace.yaml"]}
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        # send request
        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)

        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_with_pod(self):
        # Create vnf instance
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 13"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource, vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # generate body
        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/pod.yaml"]}
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        # send request
        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        # send request
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)

        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_with_pod_template(self):
        # Create vnf instance
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 14"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource, vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # generate body
        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/pod-template.yaml"]}
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        # send request
        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)

        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_with_resource_quota(self):
        # Create vnf instance
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 15"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource, vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # generate body
        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/resource-quota.yaml"]}
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        # send request
        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)

        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_with_role_rolebinding_SA(self):
        # Create vnf instance
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 16"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource, vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # generate body
        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/role_rolebinding_SA.yaml"]}
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        # send request
        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)

        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_with_subject_access_review(self):
        # Create vnf instance
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 19"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource,
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # generate body
        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/subject-access-review.yaml"]}
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        # send request
        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)

        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_with_token_review(self):
        # Create vnf instance
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 20"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource, vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # generate body
        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/token-review.yaml"]}
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        # send request
        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)

        self._delete_vnf_instance(vnf_instance['id'])

    # resource is not created normally.
    def test_inst_term_cnf_with_artifact_is_url(
            self):
        instance_file_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '../../etc/samples/etsi/nfv/test_create_vnf_instance_'
            'and_instantiate_and_terminate_cnf_with_artifact_is_url/'
        )
        artifact_file_dir = os.path.join(
            instance_file_dir, 'Files/kubernetes')
        cls_obj = utils.StaticHttpFileHandler(artifact_file_dir)
        self.addCleanup(cls_obj.stop)

        artifact_file_url = 'http://127.0.0.1:{port}/{filename}'.format(
            port=cls_obj.port, filename='storage-class-url.yaml')

        mate_dir = os.path.join(instance_file_dir, 'TOSCA-Metadata')
        self._update_source_path(mate_dir, 'TOSCA.meta', cls_obj.port)

        # upload vnf_package
        vnf_package_artifact_url, vnfd_id_url_artifact_url = \
            _create_and_upload_vnf_package(
                self.tacker_client, "test_create_vnf_instance_and_"
                                    "instantiate_and_terminate_cnf_"
                                    "with_artifact_is_url",
                {"key": "artifact_url_functional"})

        # Create vnf instance
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 22"
        resp, vnf_instance = self._create_vnf_instance(
            vnfd_id_url_artifact_url,
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        additional_param = {
            "lcm-kubernetes-def-files": [artifact_file_url]}
        # generate body
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        # send request
        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)

        self._delete_vnf_instance(vnf_instance['id'])

        # update vnf_package state
        update_req_body = jsonutils.dumps({
            "operationalState": "DISABLED"})
        base_path = "/vnfpkgm/v1/vnf_packages"

        resp, resp_body = self.tacker_client.do_request(
            '{base_path}/{id}'.format(id=vnf_package_artifact_url,
                                      base_path=base_path),
            "PATCH", content_type='application/json',
            body=update_req_body)

        # Delete vnf package
        url = '/vnfpkgm/v1/vnf_packages/%s' % vnf_package_artifact_url
        self.tacker_client.do_request(url, "DELETE")

    def test_inst_term_cnf_in_multiple_yaml_with_single_resource(
            self):
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 23"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource,
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/replicaset_service_secret.yaml"]}
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)
        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_in_single_yaml_with_multiple_resources(
            self):
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 24"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource,
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/multiple_yaml_priority-class.yaml",
                "Files/kubernetes/multiple_yaml_lease.yaml",
                "Files/kubernetes/multiple_yaml_network-policy.yaml"
            ]
        }
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)
        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_with_multi_yaml_and_resources_no_dep(
            self):
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 25"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource,
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/local-subject-access-review.yaml",
                "Files/kubernetes/self-subject-access-review_"
                "and_self-subject-rule-review.yaml"
            ]
        }
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)
        self._delete_vnf_instance(vnf_instance['id'])

    def test_inst_term_cnf_with_multi_yaml_and_resources_dep_and_sort(
            self):
        vnf_instance_name = "vnf_with_instantiation_level-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf with instantiation level 26"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource,
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/storage-class.yaml",
                "Files/kubernetes/persistent-volume-0.yaml",
                "Files/kubernetes/persistent-volume-1.yaml",
                "Files/kubernetes/statefulset.yaml",
                "Files/kubernetes/storage-class_pv_pvc.yaml"
            ]
        }
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id, additional_param=additional_param)

        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')

        time.sleep(20)

        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)
        self._delete_vnf_instance(vnf_instance['id'])
