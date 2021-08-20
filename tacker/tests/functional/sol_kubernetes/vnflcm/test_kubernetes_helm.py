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
VNF_SCALE_TIMEOUT = 600
RETRY_WAIT_TIME = 5


def _create_and_upload_vnf_package(tacker_client, csar_package_name,
                                   user_defined_data):
    # create vnf package
    body = jsonutils.dumps({"userDefinedData": user_defined_data})
    resp, vnf_package = tacker_client.do_request(
        '/vnfpkgm/v1/vnf_packages', "POST", body=body)

    # upload vnf package
    csar_package_path = "../../../etc/samples/etsi/nfv/{}".format(
                        csar_package_name)
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             csar_package_path))

    # Generating unique vnfd id. This is required when multiple workers
    # are running concurrently. The call below creates a new temporary
    # CSAR with unique vnfd id.
    file_path, uniqueid = utils.create_csar_with_unique_vnfd_id(file_path)

    with open(file_path, 'rb') as file_object:
        resp, resp_body = tacker_client.do_request(
            '/vnfpkgm/v1/vnf_packages/{}/package_content'.format(
                vnf_package['id']),
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
                " be completed within {} seconds".format(
                    VNF_PACKAGE_UPLOAD_TIMEOUT))

        time.sleep(RETRY_WAIT_TIME)

    # remove temporarily created CSAR file
    os.remove(file_path)
    return vnf_package['id'], vnfd_id


class VnfLcmKubernetesHelmTest(base.BaseTackerTest):

    @classmethod
    def setUpClass(cls):
        cls.tacker_client = base.BaseTackerTest.tacker_http_client()
        cls.vnf_package_resource, cls.vnfd_id_resource = \
            _create_and_upload_vnf_package(
                cls.tacker_client, "test_cnf_helmchart",
                {"key": "sample_helmchart_functional"})
        cls.vnf_instance_ids = []
        super(VnfLcmKubernetesHelmTest, cls).setUpClass()

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
            url = '/vnfpkgm/v1/vnf_packages/{}'.format(package_id)
            cls.tacker_client.do_request(url, "DELETE")

        super(VnfLcmKubernetesHelmTest, cls).tearDownClass()

    def setUp(self):
        super(VnfLcmKubernetesHelmTest, self).setUp()
        self.base_vnf_instances_url = "/vnflcm/v1/vnf_instances"
        self.base_vnf_lcm_op_occs_url = "/vnflcm/v1/vnf_lcm_op_occs"
        self.context = context.get_admin_context()
        vim_list = self.client.list_vims()
        if not vim_list:
            self.skipTest("Vims are not configured")

        vim_id = 'vim-kubernetes'
        vim = self.get_vim(vim_list, vim_id)
        if not vim:
            self.skipTest("Kubernetes VIM '{}' is missing".format(vim_id))
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

    def _delete_wait_vnf_instance(self, id):
        url = os.path.join("/vnflcm/v1/vnf_instances", id)
        start_time = int(time.time())
        while True:
            resp, body = self.tacker_client.do_request(url, "DELETE")
            if 204 == resp.status_code:
                break

            if ((int(time.time()) - start_time) > VNF_TERMINATE_TIMEOUT):
                raise Exception("Failed to delete vnf instance, process could"
                    " not be completed within {} seconds".format(
                        VNF_TERMINATE_TIMEOUT))

            time.sleep(RETRY_WAIT_TIME)

    def _show_vnf_instance(self, id):
        show_url = os.path.join("/vnflcm/v1/vnf_instances", id)
        resp, vnf_instance = self.tacker_client.do_request(show_url, "GET")

        return vnf_instance

    def _vnf_instance_wait(
            self, id,
            instantiation_state=fields.VnfInstanceState.INSTANTIATED,
            timeout=VNF_INSTANTIATE_TIMEOUT):
        show_url = os.path.join("/vnflcm/v1/vnf_instances", id)
        start_time = int(time.time())
        while True:
            resp, body = self.tacker_client.do_request(show_url, "GET")
            if body['instantiationState'] == instantiation_state:
                break

            if ((int(time.time()) - start_time) > timeout):
                raise Exception("Failed to wait vnf instance, process could"
                    " not be completed within {} seconds".format(timeout))

            time.sleep(RETRY_WAIT_TIME)

    def _instantiate_vnf_instance(self, id, request_body):
        url = os.path.join(self.base_vnf_instances_url, id, "instantiate")
        resp, body = self.http_client.do_request(
            url, "POST", body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)
        self._vnf_instance_wait(id)

    def _create_and_instantiate_vnf_instance(self, flavour_id,
                                             additional_params):
        # create vnf instance
        vnf_instance_name = "test_vnf_instance_for_cnf_heal-{}".format(
                            uuidutils.generate_uuid())
        vnf_instance_description = "vnf instance for cnf heal testing"
        resp, vnf_instance = self._create_vnf_instance(
            self.vnfd_id_resource, vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description)

        # instantiate vnf instance
        additional_param = additional_params
        request_body = self._instantiate_vnf_instance_request(
            flavour_id, vim_id=self.vim_id, additional_param=additional_param)

        self._instantiate_vnf_instance(vnf_instance['id'], request_body)
        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
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
        self._vnf_instance_wait(
            id,
            instantiation_state=fields.VnfInstanceState.NOT_INSTANTIATED,
            timeout=VNF_TERMINATE_TIMEOUT)

    def _delete_vnf_instance(self, id):
        self._delete_wait_vnf_instance(id)

        # verify vnf instance is deleted
        url = os.path.join(self.base_vnf_instances_url, id)
        resp, body = self.http_client.do_request(url, "GET")
        self.assertEqual(404, resp.status_code)

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

    def _test_scale_cnf(self, vnf_instance):
        """Test scale in/out CNF"""
        def _test_scale(id, type, aspect_id, previous_level,
                        delta_num=1, number_of_steps=1):
            # scale operation
            self._scale_vnf_instance(id, type, aspect_id, number_of_steps)
            # wait vnflcm_op_occs.operation_state become COMPLETE
            self._wait_vnflcm_op_occs(self.context, id)
            # check scaleStatus after scale operation
            vnf_instance = self._show_vnf_instance(id)
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
        previous_level = _test_scale(
            vnf_instance['id'], 'SCALE_OUT', aspect_id, previous_level)

        # test scale in
        previous_level = _test_scale(
            vnf_instance['id'], 'SCALE_IN', aspect_id, previous_level)

    def _test_heal_cnf_with_sol002(self, vnf_instance):
        """Test heal as per SOL002 for CNF"""
        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        before_vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)

        # get vnfc_instance_id of heal target
        before_pod_name = dict()
        vnfc_instance_id = list()
        for vnfc_rsc in before_vnfc_rscs:
            if vnfc_rsc['vduId'] == "vdu1":
                before_pod_name['vdu1'] = \
                    vnfc_rsc['computeResource']['resourceId']
            elif vnfc_rsc['vduId'] == "vdu2":
                before_pod_name['vdu2'] = \
                    vnfc_rsc['computeResource']['resourceId']
            vnfc_instance_id.append(vnfc_rsc['id'])

        # test heal SOL-002 (partial heal)
        self._heal_vnf_instance(vnf_instance['id'], vnfc_instance_id)
        # wait vnflcm_op_occs.operation_state become COMPLETE
        self._wait_vnflcm_op_occs(self.context, vnf_instance['id'])
        # check vnfcResourceInfo after heal operation
        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        after_vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)
        self.assertEqual(len(before_vnfc_rscs), len(after_vnfc_rscs))
        for vnfc_rsc in after_vnfc_rscs:
            after_pod_name = vnfc_rsc['computeResource']['resourceId']
            if vnfc_rsc['vduId'] == "vdu1":
                # check stored pod name is changed (vdu1)
                compute_resource = vnfc_rsc['computeResource']
                before_pod_name = compute_resource['resourceId']
                self.assertNotEqual(after_pod_name, before_pod_name['vdu1'])
            elif vnfc_rsc['vduId'] == "vdu2":
                # check stored pod name is changed (vdu2)
                compute_resource = vnfc_rsc['computeResource']
                before_pod_name = compute_resource['resourceId']
                self.assertNotEqual(after_pod_name, before_pod_name['vdu2'])

    def _test_heal_cnf_with_sol003(self, vnf_instance):
        """Test heal as per SOL003 for CNF"""
        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        before_vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)

        # test heal SOL-003 (entire heal)
        vnfc_instance_id = []
        self._heal_vnf_instance(vnf_instance['id'], vnfc_instance_id)
        # wait vnflcm_op_occs.operation_state become COMPLETE
        self._wait_vnflcm_op_occs(self.context, vnf_instance['id'])
        # check vnfcResourceInfo after heal operation
        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
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

    def test_vnflcm_with_helmchart(self):
        # use def-files of singleton Pod and Deployment (replicas=2)
        helmchartfile_path = "Files/kubernetes/localhelm-0.1.0.tgz"
        inst_additional_param = {
            "namespace": "default",
            "use_helm": "true",
            "using_helm_install_param": [
                {
                    "exthelmchart": "false",
                    "helmchartfile_path": helmchartfile_path,
                    "helmreleasename": "vdu1",
                    "helmparameter": [
                        "service.port=8081"
                    ]
                },
                {
                    "exthelmchart": "true",
                    "helmreleasename": "vdu2",
                    "helmrepositoryname": "bitnami",
                    "helmchartname": "apache",
                    "exthelmrepo_url": "https://charts.bitnami.com/bitnami"
                }
            ]
        }
        vnf_instance = self._create_and_instantiate_vnf_instance(
            "helmchart", inst_additional_param)
        self._test_scale_cnf(vnf_instance)
        self._test_heal_cnf_with_sol002(vnf_instance)
        self._test_heal_cnf_with_sol003(vnf_instance)

        self._terminate_vnf_instance(vnf_instance['id'])
        self._delete_vnf_instance(vnf_instance['id'])
