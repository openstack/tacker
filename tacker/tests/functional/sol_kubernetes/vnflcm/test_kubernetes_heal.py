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
VNF_HEAL_TIMEOUT = 600
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
    start_time = int(time.time())
    show_url = os.path.join('/vnfpkgm/v1/vnf_packages', vnf_package['id'])
    vnfd_id = None
    while True:
        resp, body = tacker_client.do_request(show_url, "GET")
        if body['onboardingState'] == "ONBOARDED":
            vnfd_id = body['vnfdId']
            break

        if ((int(time.time()) - start_time) > VNF_PACKAGE_UPLOAD_TIMEOUT):
            raise Exception("Failed to onboard vnf package, process could not"
                " be completed within %d seconds", VNF_PACKAGE_UPLOAD_TIMEOUT)

        time.sleep(RETRY_WAIT_TIME)

    # remove temporarily created CSAR file
    os.remove(file_path)
    return vnf_package['id'], vnfd_id


def _delete_wait_vnf_instance(tacker_client, id):
    url = os.path.join("/vnflcm/v1/vnf_instances", id)
    start_time = int(time.time())
    while True:
        resp, body = tacker_client.do_request(url, "DELETE")
        if 204 == resp.status_code:
            break

        if ((int(time.time()) - start_time) > VNF_TERMINATE_TIMEOUT):
            raise Exception("Failed to delete vnf instance, process could not"
                " be completed within %d seconds", VNF_TERMINATE_TIMEOUT)

        time.sleep(RETRY_WAIT_TIME)


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
            raise Exception("Failed to wait vnf instance, process could not"
                " be completed within %d seconds", timeout)

        time.sleep(RETRY_WAIT_TIME)


class VnfLcmKubernetesHealTest(base.BaseTackerTest):

    @classmethod
    def setUpClass(cls):
        cls.tacker_client = base.BaseTackerTest.tacker_http_client()
        cls.vnf_package_resource, cls.vnfd_id_resource = \
            _create_and_upload_vnf_package(
                cls.tacker_client, "test_cnf_heal",
                {"key": "sample_heal_functional"})
        cls.vnf_instance_ids = []
        super(VnfLcmKubernetesHealTest, cls).setUpClass()

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

        super(VnfLcmKubernetesHealTest, cls).tearDownClass()

    def setUp(self):
        super(VnfLcmKubernetesHealTest, self).setUp()
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
        vnf_instance_name = "test_vnf_instance_for_cnf_heal-%s" % \
                            uuidutils.generate_uuid()
        vnf_instance_description = "vnf instance for cnf heal testing"
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

    def _terminate_vnf_instance(self, id):
        # Terminate vnf forcefully
        request_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
        }
        url = os.path.join(self.base_vnf_instances_url, id, "terminate")
        resp, body = self.http_client.do_request(
            url, "POST", body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)
        _vnf_instance_wait(
            self.tacker_client, id,
            instantiation_state=fields.VnfInstanceState.NOT_INSTANTIATED,
            timeout=VNF_TERMINATE_TIMEOUT)

    def _delete_vnf_instance(self, id):
        _delete_wait_vnf_instance(self.tacker_client, id)

        # verify vnf instance is deleted
        url = os.path.join(self.base_vnf_instances_url, id)
        resp, body = self.http_client.do_request(url, "GET")
        self.assertEqual(404, resp.status_code)

    def _heal_vnf_instance(self, id, vnfc_instance_id):
        url = os.path.join(self.base_vnf_instances_url, id, "heal")
        # generate body
        request_body = {
            "vnfcInstanceId": vnfc_instance_id}
        resp, body = self.http_client.do_request(
            url, "POST", body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)

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
        start_time = int(time.time())
        while True:
            vnflcm_op_occ = self._vnf_notify_get_by_id(
                context, vnf_instance_id)

            if vnflcm_op_occ.operation_state == operation_state:
                break

            if ((int(time.time()) - start_time) > VNF_HEAL_TIMEOUT):
                raise Exception("Failed to wait heal instance")

            time.sleep(RETRY_WAIT_TIME)

    def _get_vnfc_resource_info(self, vnf_instance):
        inst_vnf_info = vnf_instance['instantiatedVnfInfo']
        vnfc_resource_info = inst_vnf_info['vnfcResourceInfo']
        return vnfc_resource_info

    def test_heal_cnf_with_sol002(self):
        """Test heal as per SOL002 for CNF

        This test will instantiate cnf. Heal API will be invoked as per SOL002
        i.e. with vnfcInstanceId, so that the specified vnfc instance is healed
        which includes Kubernetes resources (Pod and Deployment).
        """
        # use def-files of singleton Pod and Deployment (replicas=2)
        inst_additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/deployment_heal_complex.yaml",
                "Files/kubernetes/pod_heal.yaml"]}
        vnf_instance = self._create_and_instantiate_vnf_instance(
            "complex", inst_additional_param)
        before_vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)

        # get vnfc_instance_id of heal target
        deployment_target_vnfc = None
        for vnfc_rsc in before_vnfc_rscs:
            compute_resource = vnfc_rsc['computeResource']
            rsc_kind = compute_resource['vimLevelResourceType']
            if rsc_kind == 'Pod':
                # target 1: Singleton Pod
                pod_target_vnfc = vnfc_rsc
            elif not deployment_target_vnfc:
                # target 2: Deployment's Pod
                deployment_target_vnfc = vnfc_rsc
            else:
                # not target: Deployment's remianing one
                deployment_not_target_vnfc = vnfc_rsc

        # test heal SOL-002 (partial heal)
        vnfc_instance_id = \
            [pod_target_vnfc['id'], deployment_target_vnfc['id']]
        self._heal_vnf_instance(vnf_instance['id'], vnfc_instance_id)
        # wait vnflcm_op_occs.operation_state become COMPLETE
        self._wait_vnflcm_op_occs(self.context, vnf_instance['id'])
        # check vnfcResourceInfo after heal operation
        vnf_instance = _show_vnf_instance(
            self.tacker_client, vnf_instance['id'])
        after_vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)
        self.assertEqual(len(before_vnfc_rscs), len(after_vnfc_rscs))
        for vnfc_rsc in after_vnfc_rscs:
            after_pod_name = vnfc_rsc['computeResource']['resourceId']
            if vnfc_rsc['id'] == pod_target_vnfc['id']:
                # check stored pod name is not changed (Pod)
                after_resource = pod_target_vnfc
                compute_resource = after_resource['computeResource']
                before_pod_name = compute_resource['resourceId']
                self.assertEqual(after_pod_name, before_pod_name)
            elif vnfc_rsc['id'] == deployment_target_vnfc['id']:
                # check stored pod name is changed (Deployment)
                after_resource = deployment_target_vnfc
                compute_resource = after_resource['computeResource']
                before_pod_name = compute_resource['resourceId']
                self.assertNotEqual(after_pod_name, before_pod_name)
            else:
                # check stored pod name is not changed (not target)
                after_resource = deployment_not_target_vnfc
                compute_resource = after_resource['computeResource']
                before_pod_name = compute_resource['resourceId']
                self.assertEqual(after_pod_name, before_pod_name)
        self._terminate_vnf_instance(vnf_instance['id'])
        self._delete_vnf_instance(vnf_instance['id'])

    def test_heal_cnf_with_sol003(self):
        """Test heal as per SOL003 for CNF

        This test will instantiate cnf. Heal API will be invoked as per SOL003
        i.e. without passing vnfcInstanceId, so that the entire vnf is healed
        which includes Kubernetes resource (Deployment).
        """
        # use def-files of Deployment (replicas=2)
        inst_additional_param = {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/deployment_heal_simple.yaml"]}
        vnf_instance = self._create_and_instantiate_vnf_instance(
            "simple", inst_additional_param)
        before_vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)

        # test heal SOL-003 (entire heal)
        vnfc_instance_id = []
        self._heal_vnf_instance(vnf_instance['id'], vnfc_instance_id)
        # wait vnflcm_op_occs.operation_state become COMPLETE
        self._wait_vnflcm_op_occs(self.context, vnf_instance['id'])
        # check vnfcResourceInfo after heal operation
        vnf_instance = _show_vnf_instance(
            self.tacker_client, vnf_instance['id'])
        after_vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)
        self.assertEqual(len(before_vnfc_rscs), len(after_vnfc_rscs))
        # check id and pod name (as computeResource.resourceId) is changed
        for before_vnfc_rsc in before_vnfc_rscs:
            for after_vnfc_rsc in after_vnfc_rscs:
                self.assertNotEqual(
                    before_vnfc_rsc['id'], after_vnfc_rsc['id'])
                self.assertNotEqual(
                    before_vnfc_rsc['computeResource']['resourceId'],
                    after_vnfc_rsc['computeResource']['resourceId'])
        # terminate vnf instance
        self._terminate_vnf_instance(vnf_instance['id'])
        self._delete_vnf_instance(vnf_instance['id'])
