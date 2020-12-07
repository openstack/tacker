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
import unittest

from oslo_serialization import jsonutils
from oslo_utils import uuidutils
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

from tacker.common import exceptions
from tacker import context
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker.objects import fields
from tacker.objects import vnf_lcm_op_occs
from tacker.tests.functional import base
from tacker.tests import utils

VNF_PACKAGE_UPLOAD_TIMEOUT = 300
VNF_INSTANTIATE_TIMEOUT = 600
VNF_TERMINATE_TIMEOUT = 600
VNF_SCALE_TIMEOUT = 600
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


def _delete_wait_vnf_instance(tacker_client, id):
    timeout = VNF_TERMINATE_TIMEOUT
    url = os.path.join("/vnflcm/v1/vnf_instances", id)
    start_time = int(time.time())
    while True:
        resp, body = tacker_client.do_request(url, "DELETE")
        if 204 == resp.status_code:
            break

        if ((int(time.time()) - start_time) > timeout):
            raise Exception("Failed to delete vnf instance")

        time.sleep(RETRY_WAIT_TIME)


def _delete_vnf_instance(tacker_client, id):
    _delete_wait_vnf_instance(tacker_client, id)

    # verify vnf instance is deleted
    url = os.path.join("/vnflcm/v1/vnf_instances", id)
    resp, body = tacker_client.do_request(url, "GET")


def _show_vnf_instance(tacker_client, id):
    show_url = os.path.join("/vnflcm/v1/vnf_instances", id)
    resp, vnf_instance = tacker_client.do_request(show_url, "GET")

    return vnf_instance


def _vnf_instance_wait(
        tacker_client, id,
        instantiation_state=fields.VnfInstanceState.INSTANTIATED,
        timeout=VNF_INSTANTIATE_TIMEOUT):
    show_url = os.path.join("/vnflcm/v1/vnf_instances", id)
    start_time = int(time.time())
    while True:
        resp, body = tacker_client.do_request(show_url, "GET")
        if body['instantiationState'] == instantiation_state:
            break

        if ((int(time.time()) - start_time) > timeout):
            raise Exception("Failed to wait vnf instance")

        time.sleep(RETRY_WAIT_TIME)


def _terminate_vnf_instance(tacker_client, id, request_body):
    url = os.path.join("/vnflcm/v1/vnf_instances", id, "terminate")
    resp, body = tacker_client.do_request(
        url, "POST", body=jsonutils.dumps(request_body))

    timeout = request_body.get('gracefulTerminationTimeout')
    start_time = int(time.time())

    _vnf_instance_wait(
        tacker_client, id,
        instantiation_state=fields.VnfInstanceState.NOT_INSTANTIATED,
        timeout=VNF_TERMINATE_TIMEOUT)

    # If gracefulTerminationTimeout is set, check whether vnf
    # instantiation_state is set to NOT_INSTANTIATED after
    # gracefulTerminationTimeout seconds.
    if timeout and int(time.time()) - start_time < timeout:
        raise Exception("Failed to terminate vnf instance")


class VnfLcmKubernetesScaleTest(base.BaseTackerTest):

    @classmethod
    def setUpClass(cls):
        cls.tacker_client = base.BaseTackerTest.tacker_http_client()
        cls.vnf_package_resource, cls.vnfd_id_resource = \
            _create_and_upload_vnf_package(
                cls.tacker_client, "test_cnf_scale",
                {"key": "sample_scale_functional"})
        cls.vnf_instance_ids = []
        super(VnfLcmKubernetesScaleTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }
        for id in cls.vnf_instance_ids:
            _terminate_vnf_instance(cls.tacker_client, id,
                terminate_req_body)
            _delete_vnf_instance(cls.tacker_client, id)

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

        super(VnfLcmKubernetesScaleTest, cls).tearDownClass()

    def setUp(self):
        super(VnfLcmKubernetesScaleTest, self).setUp()
        self.base_vnf_instances_url = "/vnflcm/v1/vnf_instances"
        self.base_vnf_lcm_op_occs_url = "/vnflcm/v1/vnf_lcm_op_occs"
        self.context = context.get_admin_context()
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
            self.base_vnf_instances_url, "POST",
            body=jsonutils.dumps(request_body))
        return resp, response_body

    def _instantiate_vnf_instance(self, id, request_body):
        url = os.path.join(self.base_vnf_instances_url, id, "instantiate")
        resp, body = self.http_client.do_request(
            url, "POST", body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)
        _vnf_instance_wait(self.tacker_client, id)

    def _create_and_instantiate_vnf_instance(self, flavour_id,
                                             additional_params):
        # create vnf instance
        vnf_instance_name = "test_vnf_instance_for_cnf_scale-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf instance for cnf scale testing"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource, vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        # instantiate vnf instance
        additional_param = additional_params
        request_body = self._instantiate_vnf_instance_request(
            flavour_id, vim_id=self.vim_id, additional_param=additional_param)

        self._instantiate_vnf_instance(vnf_instance['id'], request_body)
        vnf_instance = _show_vnf_instance(
            self.tacker_client, vnf_instance['id'])
        self.vnf_instance_ids.append(vnf_instance['id'])

        return vnf_instance

    def _scale_vnf_instance(self, id, type, aspect_id,
                            number_of_steps=1):
        url = os.path.join(self.base_vnf_instances_url, id, "scale")
        # generate body
        request_body = {
            "type": type,
            "aspectId": aspect_id,
            "numberOfSteps": number_of_steps}
        resp, body = self.http_client.do_request(
            url, "POST", body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)

    def _test_scale_cnf(self, id, type, aspect_id, previous_level,
                        delta_num=1, number_of_steps=1):
        # scale operation
        self._scale_vnf_instance(id, type, aspect_id, number_of_steps)
        # wait vnflcm_op_occs.operation_state become COMPLETE
        self._wait_vnflcm_op_occs(self.context, id)
        # check scaleStatus after scale operation
        vnf_instance = _show_vnf_instance(
            self.tacker_client, id)
        scale_status_after = \
            vnf_instance['instantiatedVnfInfo']['scaleStatus']
        if type == 'SCALE_OUT':
            expected_level = previous_level + number_of_steps
        else:
            expected_level = previous_level - number_of_steps
        for status in scale_status_after:
            if status.get('aspectId') == aspect_id:
                self.assertEqual(status.get('scaleLevel'), expected_level)
                previous_level = status.get('scaleLevel')

        return previous_level

    def _test_scale_cnf_fail(self, id, type, aspect_id, previous_level,
                             delta_num=1, number_of_steps=1):
        # scale operation
        self._scale_vnf_instance(id, type, aspect_id, number_of_steps)
        # wait vnflcm_op_occs.operation_state become FAILED_TEMP
        self._wait_vnflcm_op_occs(self.context, id, "FAILED_TEMP")
        # check scaleStatus after scale operation
        vnf_instance = _show_vnf_instance(
            self.tacker_client, id)
        scale_status_after = \
            vnf_instance['instantiatedVnfInfo']['scaleStatus']
        expected_level = previous_level
        for status in scale_status_after:
            if status.get('aspectId') == aspect_id:
                self.assertEqual(status.get('scaleLevel'), expected_level)
                previous_level = status.get('scaleLevel')

        return previous_level

    def _rollback_vnf_instance(self, vnf_lcm_op_occ_id):
        url = os.path.join(
            self.base_vnf_lcm_op_occs_url, vnf_lcm_op_occ_id, "rollback")
        # generate body
        resp, body = self.http_client.do_request(url, "POST")
        self.assertEqual(202, resp.status_code)

    def _test_rollback_cnf(self, id, aspect_id, previous_level,
                           delta_num=1, number_of_steps=1):
        # get vnflcm_op_occ id for rollback
        vnflcm_op_occ = self._vnf_notify_get_by_id(self.context, id)
        vnf_lcm_op_occ_id = vnflcm_op_occ.id

        # rollback operation
        self._rollback_vnf_instance(vnf_lcm_op_occ_id)
        # wait vnflcm_op_occs.operation_state become ROLLED_BACK
        self._wait_vnflcm_op_occs(self.context, id, "ROLLED_BACK")
        # check scaleStatus after scale operation
        vnf_instance = _show_vnf_instance(
            self.tacker_client, id)
        scale_status_after = \
            vnf_instance['instantiatedVnfInfo']['scaleStatus']
        expected_level = previous_level
        for status in scale_status_after:
            if status.get('aspectId') == aspect_id:
                self.assertEqual(status.get('scaleLevel'), expected_level)
                previous_level = status.get('scaleLevel')

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

        db_vnflcm_op_occ = query.first()

        if not db_vnflcm_op_occ:
            raise exceptions.VnfInstanceNotFound(id=vnf_instance_id)

        vnflcm_op_occ = vnf_lcm_op_occs.VnfLcmOpOcc.obj_from_db_obj(
            context, db_vnflcm_op_occ)
        return vnflcm_op_occ

    def _wait_vnflcm_op_occs(
            self, context, vnf_instance_id,
            operation_state='COMPLETED'):
        timeout = VNF_SCALE_TIMEOUT
        start_time = int(time.time())
        while True:
            vnflcm_op_occ = self._vnf_notify_get_by_id(
                context, vnf_instance_id)

            if vnflcm_op_occ.operation_state == operation_state:
                break

            if ((int(time.time()) - start_time) > timeout):
                raise Exception("Failed to wait scale instance")

            time.sleep(RETRY_WAIT_TIME)

    def test_scale_cnf_with_statefulset(self):
        inst_additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/statefulset_scale.yaml"]}
        vnf_instance = self._create_and_instantiate_vnf_instance(
            "simple", inst_additional_param)
        aspect_id = "vdu1_aspect"
        scale_status_initial = \
            vnf_instance['instantiatedVnfInfo']['scaleStatus']
        self.assertTrue(len(scale_status_initial) > 0)
        for status in scale_status_initial:
            self.assertIsNotNone(status.get('aspectId'))
            self.assertIsNotNone(status.get('scaleLevel'))
            if status.get('aspectId') == aspect_id:
                previous_level = status.get('scaleLevel')

        # test scale out
        previous_level = self._test_scale_cnf(
            vnf_instance['id'], 'SCALE_OUT', aspect_id, previous_level)

        # test scale in
        previous_level = self._test_scale_cnf(
            vnf_instance['id'], 'SCALE_IN', aspect_id, previous_level)

    def test_scale_cnf_with_replicaset(self):
        inst_additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/replicaset_scale.yaml"]}
        vnf_instance = self._create_and_instantiate_vnf_instance(
            "simple", inst_additional_param)
        aspect_id = "vdu1_aspect"
        scale_status_initial = \
            vnf_instance['instantiatedVnfInfo']['scaleStatus']
        self.assertTrue(len(scale_status_initial) > 0)
        for status in scale_status_initial:
            self.assertIsNotNone(status.get('aspectId'))
            self.assertIsNotNone(status.get('scaleLevel'))
            if status.get('aspectId') == aspect_id:
                previous_level = status.get('scaleLevel')

        # test scale out
        previous_level = self._test_scale_cnf(
            vnf_instance['id'], 'SCALE_OUT', aspect_id, previous_level)

        # test scale in
        previous_level = self._test_scale_cnf(
            vnf_instance['id'], 'SCALE_IN', aspect_id, previous_level)

    def test_scale_cnf_deployment_with_scaling_and_delta_two(self):
        inst_additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/deployment_scale.yaml"]}
        # Use flavour_id scalingsteps that is set to delta_num=2
        vnf_instance = self._create_and_instantiate_vnf_instance(
            "scalingsteps", inst_additional_param)
        aspect_id = "vdu1_aspect"
        scale_status_initial = \
            vnf_instance['instantiatedVnfInfo']['scaleStatus']
        self.assertTrue(len(scale_status_initial) > 0)
        for status in scale_status_initial:
            self.assertIsNotNone(status.get('aspectId'))
            self.assertIsNotNone(status.get('scaleLevel'))
            if status.get('aspectId') == aspect_id:
                previous_level = status.get('scaleLevel')

        # test scale out (test for delta_num=2 and number_of_steps=2)
        previous_level = self._test_scale_cnf(
            vnf_instance['id'], 'SCALE_OUT', aspect_id, previous_level,
            delta_num=2, number_of_steps=2)

        # test scale in (test for delta_num=2 and number_of_steps=2)
        previous_level = self._test_scale_cnf(
            vnf_instance['id'], 'SCALE_IN', aspect_id, previous_level,
            delta_num=2, number_of_steps=2)

    @unittest.skip("Reduce test time")
    def test_scale_out_cnf_rollback(self):
        inst_additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/statefulset_scale.yaml"]}
        vnf_instance = self._create_and_instantiate_vnf_instance(
            "simple", inst_additional_param)
        aspect_id = "vdu1_aspect"
        scale_status_initial = \
            vnf_instance['instantiatedVnfInfo']['scaleStatus']
        self.assertTrue(len(scale_status_initial) > 0)
        for status in scale_status_initial:
            self.assertIsNotNone(status.get('aspectId'))
            self.assertIsNotNone(status.get('scaleLevel'))
            if status.get('aspectId') == aspect_id:
                previous_level = status.get('scaleLevel')

        # fail scale out for rollback
        previous_level = self._test_scale_cnf_fail(
            vnf_instance['id'], 'SCALE_OUT', aspect_id, previous_level,
            number_of_steps=2)

        # test rollback
        self._test_rollback_cnf(vnf_instance['id'], aspect_id, previous_level)
