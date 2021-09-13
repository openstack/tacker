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
import time

from oslo_serialization import jsonutils
from oslo_utils import uuidutils
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

from tacker.common import exceptions
from tacker import context as t_context
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker.objects import fields
from tacker.tests.functional import base
from tacker.tests import utils

VNF_PACKAGE_UPLOAD_TIMEOUT = 300
VNF_INSTANTIATE_TIMEOUT = 600
VNF_TERMINATE_TIMEOUT = 600
RETRY_WAIT_TIME = 5


def _create_and_upload_vnf_package(tacker_client, csar_package_name,
                                   user_defined_data):
    # create vnf package
    body = jsonutils.dumps({"userDefinedData": user_defined_data})
    resp, vnf_package = tacker_client.do_request(
        '/vnfpkgm/v1/vnf_packages', "POST", body=body)

    # upload vnf package
    csar_package_path = "../../../etc/samples/etsi/nfv/%s" % csar_package_name
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             csar_package_path))

    # Generating unique vnfd id. This is required when multiple workers
    # are running concurrently. The call below creates a new temporary
    # CSAR with unique vnfd id.
    file_path, uniqueid = utils.create_csar_with_unique_vnfd_id(file_path)

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

        cls.vnf_package, cls.vnfd_id = \
            _create_and_upload_vnf_package(
                cls.tacker_client, "test_inst_terminate_vnf_with_vnflcmnoop",
                {"key": "file_functional"})

        super(VnfLcmTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        # Update vnf package operational state to DISABLED
        update_req_body = jsonutils.dumps({
            "operationalState": "DISABLED"})
        base_path = "/vnfpkgm/v1/vnf_packages"
        for package_id in [cls.vnf_package]:
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
        self.context = t_context.get_admin_context()

        vim_list = self.client.list_vims()
        if not vim_list:
            self.skipTest("Vims are not configured")

        vim_id = 'VIM0'
        vim = self.get_vim(vim_list, vim_id)
        if not vim:
            self.skipTest("Openstack VIM '%s' is missing" % vim_id)
        self.vim_id = vim['id']

    def _instantiate_vnf_instance_request(
            self, flavour_id, vim_id=None, additional_param=None):
        request_body = {"flavourId": flavour_id}

        if vim_id:
            request_body["vimConnectionInfo"] = [
                {"id": uuidutils.generate_uuid(),
                 "vimId": vim_id,
                 "vimType": "openstack"}]

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

    @db_api.context_manager.reader
    def _vnf_notify_get_by_id(self, context, vnf_instance_id,
                              columns_to_join=None):
        query = api.model_query(
            context, models.VnfLcmOpOccs,
            read_deleted="no", project_only=True).filter_by(
            vnf_instance_id=vnf_instance_id).order_by(
            desc("created_at"))

        if columns_to_join:
            for column in columns_to_join:
                query = query.options(joinedload(column))

        result = query.first()

        if not result:
            raise exceptions.VnfInstanceNotFound(id=vnf_instance_id)

        return result

    def _wait_vnflcm_op_occs(
            self, context, vnf_instance_id, type, timeout,
            operation_state='COMPLETED'):
        start_time = int(time.time())
        while True:
            vnflcm_op_occ = self._vnf_notify_get_by_id(
                context, vnf_instance_id)

            if vnflcm_op_occ.operation_state == operation_state:
                break

            if ((int(time.time()) - start_time) > timeout):
                raise Exception("Failed to wait {} instance".format(type))

            time.sleep(RETRY_WAIT_TIME)

    def test_instantiate_terminate_vnf_with_vnflcmnoop(self):
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
        request_body = self._instantiate_vnf_instance_request(
            "simple", vim_id=self.vim_id)
        self._instantiate_vnf_instance(vnf_instance['id'], request_body)
        self._wait_vnflcm_op_occs(self.context, vnf_instance['id'],
                                  'instantiate', VNF_INSTANTIATE_TIMEOUT)
        # show vnf instance
        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        self.assertEqual(vnf_instance['instantiationState'], 'INSTANTIATED')
        vnflcm_op_occ_ins = self._vnf_notify_get_by_id(
            self.context, vnf_instance['id'], columns_to_join=None)
        self.assertEqual(vnflcm_op_occ_ins.operation, 'INSTANTIATE')
        # terminate vnf instance
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }
        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)
        self._wait_vnflcm_op_occs(self.context, vnf_instance['id'],
                                  'terminate', VNF_TERMINATE_TIMEOUT)
        vnflcm_op_occ_term = self._vnf_notify_get_by_id(
            self.context, vnf_instance['id'], columns_to_join=None)
        self.assertEqual(vnflcm_op_occ_term.operation, 'TERMINATE')
        # delete vnf instance
        self._delete_vnf_instance(vnf_instance['id'])
