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
import shutil
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
from tacker.vnfm.infra_drivers.kubernetes.kubernetes_driver import CONF

VNF_PACKAGE_UPLOAD_TIMEOUT = 300
RETRY_WAIT_TIME = 5

WAIT_TIMEOUT_ERR_MSG = ("Failed to %(action)s, process could not be completed"
                        " within %(timeout)s seconds")


class BaseVnfLcmKubernetesTest(base.BaseTackerTest):

    @classmethod
    def setUpClass(cls):
        super(BaseVnfLcmKubernetesTest, cls).setUpClass()
        cls.tacker_client = base.BaseTackerTest.tacker_http_client()
        cls.base_vnf_package_url = "/vnfpkgm/v1/vnf_packages"
        cls.base_vnf_instances_url = "/vnflcm/v1/vnf_instances"
        cls.base_vnf_lcm_op_occs_url = "/vnflcm/v1/vnf_lcm_op_occs"
        # [NOTE] culculate timeout from configuration. In addition to the sleep
        # time for each retry, add 1 second to timeout value for waiting
        # specified state as another processing time for each retry.
        timeout = (CONF.kubernetes_vim.stack_retries *
                   (CONF.kubernetes_vim.stack_retry_wait + 1))
        cls.lcm_timeout = {
            "instantiate": timeout,
            "terminate": timeout,
            "heal_sol002": timeout,
            "heal_sol003": timeout * 2,
            "scale": timeout,
            "modify": timeout
        }
        cls.vnf_package_ids = []

    @classmethod
    def tearDownClass(cls):
        # Update vnf package operational state to DISABLED and delete
        for package_id in cls.vnf_package_ids:
            cls._disable_and_delete_vnf_package(package_id)

        super(BaseVnfLcmKubernetesTest, cls).tearDownClass()

    def setUp(self):
        super(BaseVnfLcmKubernetesTest, self).setUp()
        self.context = context.get_admin_context()
        vim_list = self.client.list_vims()
        if not vim_list:
            self.skipTest("Vims are not configured")

        vim_name = 'vim-kubernetes'
        vim = self.get_vim(vim_list, vim_name)
        if not vim:
            self.skipTest(f"Kubernetes VIM '{vim_name}' is missing")
        self.vim_id = vim['id']

    def _create_and_upload_vnf_package_add_mgmt(
            self, tacker_client, csar_package_name,
            user_defined_data, mgmt_rela_path):
        # create vnf package
        body = jsonutils.dumps({"userDefinedData": user_defined_data})
        _, vnf_package = tacker_client.do_request(
            self.base_vnf_package_url, "POST", body=body)
        vnf_pkg_id = vnf_package['id']

        # cp MgmtDriver to package
        mgmt_abs_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), mgmt_rela_path))
        mgmt_package_abs_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         f"../../../etc/samples/etsi/nfv/"
                         f"{csar_package_name}/Scripts/"))
        os.mkdir(mgmt_package_abs_path)
        shutil.copy(mgmt_abs_path, mgmt_package_abs_path)

        # upload vnf package
        csar_package_path = ("../../../etc/samples/etsi/nfv/"
                             f"{csar_package_name}")
        file_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), csar_package_path))

        # Generating unique vnfd id. This is required when multiple workers
        # are running concurrently. The call below creates a new temporary
        # CSAR with unique vnfd id.
        file_path, _ = utils.create_csar_with_unique_vnfd_id(file_path)

        with open(file_path, 'rb') as file_object:
            tacker_client.do_request(
                f"{self.base_vnf_package_url}/{vnf_pkg_id}/package_content",
                "PUT", body=file_object, content_type='application/zip')

        # wait for onboard
        start_time = int(time.time())
        show_url = os.path.join(self.base_vnf_package_url, vnf_pkg_id)
        vnfd_id = None
        while True:
            _, body = tacker_client.do_request(show_url, "GET")
            if body['onboardingState'] == "ONBOARDED":
                vnfd_id = body['vnfdId']
                break

            if (int(time.time()) - start_time) > VNF_PACKAGE_UPLOAD_TIMEOUT:
                raise Exception(WAIT_TIMEOUT_ERR_MSG %
                    {"action": "onboard vnf package",
                     "timeout": VNF_PACKAGE_UPLOAD_TIMEOUT})

            time.sleep(RETRY_WAIT_TIME)

        # remove temporarily created CSAR file
        os.remove(file_path)
        shutil.rmtree(mgmt_package_abs_path)
        return vnf_package['id'], vnfd_id

    def _create_and_upload_vnf_package(self, tacker_client, csar_package_name,
                                       user_defined_data):
        # create vnf package
        body = jsonutils.dumps({"userDefinedData": user_defined_data})
        _, vnf_package = tacker_client.do_request(
            self.base_vnf_package_url, "POST", body=body)
        vnf_pkg_id = vnf_package['id']

        # upload vnf package
        csar_package_path = ("../../../etc/samples/etsi/nfv/"
                             f"{csar_package_name}")
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                 csar_package_path))

        # Generating unique vnfd id. This is required when multiple workers
        # are running concurrently. The call below creates a new temporary
        # CSAR with unique vnfd id.
        file_path, _ = utils.create_csar_with_unique_vnfd_id(file_path)

        with open(file_path, 'rb') as file_object:
            tacker_client.do_request(
                f"{self.base_vnf_package_url}/{vnf_pkg_id}/package_content",
                "PUT", body=file_object, content_type='application/zip')

        # wait for onboard
        start_time = int(time.time())
        show_url = os.path.join(self.base_vnf_package_url, vnf_pkg_id)
        vnfd_id = None
        while True:
            _, body = tacker_client.do_request(show_url, "GET")
            if body['onboardingState'] == "ONBOARDED":
                vnfd_id = body['vnfdId']
                break

            if (int(time.time()) - start_time) > VNF_PACKAGE_UPLOAD_TIMEOUT:
                raise Exception(WAIT_TIMEOUT_ERR_MSG %
                    {"action": "onboard vnf package",
                     "timeout": VNF_PACKAGE_UPLOAD_TIMEOUT})

            time.sleep(RETRY_WAIT_TIME)

        # remove temporarily created CSAR file
        os.remove(file_path)
        return vnf_package['id'], vnfd_id

    @classmethod
    def _disable_and_delete_vnf_package(cls, package_id):
        # Update vnf package operational state to DISABLED
        update_req_body = jsonutils.dumps({
            "operationalState": "DISABLED"})
        cls.tacker_client.do_request(
            f'{cls.base_vnf_package_url}/{package_id}',
            "PATCH", content_type='application/json',
            body=update_req_body)

        # Delete vnf package
        url = f'{cls.base_vnf_package_url}/{package_id}'
        cls.tacker_client.do_request(url, "DELETE")

    @classmethod
    def _instantiate_vnf_instance_request(
            cls, flavour_id, vim_id=None, additional_param=None):
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
        self.assertEqual(201, resp.status_code)
        return resp, response_body

    def _delete_wait_vnf_instance(self, id):
        url = os.path.join(self.base_vnf_instances_url, id)
        start_time = int(time.time())
        while True:
            resp, _ = self.tacker_client.do_request(url, "DELETE")
            if 204 == resp.status_code:
                break

            if (int(time.time()) - start_time) > self.lcm_timeout['terminate']:
                raise Exception(WAIT_TIMEOUT_ERR_MSG %
                    {"action": "delete vnf instance",
                     "timeout": self.lcm_timeout['terminate']})
            time.sleep(RETRY_WAIT_TIME)

    def _show_vnf_instance(self, id):
        show_url = os.path.join(self.base_vnf_instances_url, id)
        _, vnf_instance = self.tacker_client.do_request(show_url, "GET")

        return vnf_instance

    def _vnf_instance_wait(
            self, id,
            instantiation_state=fields.VnfInstanceState.INSTANTIATED,
            timeout=None):
        show_url = os.path.join(self.base_vnf_instances_url, id)
        start_time = int(time.time())
        if timeout is None:
            timeout = self.lcm_timeout['instantiate']
        while True:
            _, body = self.tacker_client.do_request(show_url, "GET")
            if body['instantiationState'] == instantiation_state:
                break

            if (int(time.time()) - start_time) > timeout:
                raise Exception(WAIT_TIMEOUT_ERR_MSG %
                    {"action": "wait vnf instance", "timeout": timeout})

            time.sleep(RETRY_WAIT_TIME)

    def _instantiate_vnf_instance(self, id, request_body,
                                  wait_state="COMPLETED"):
        url = os.path.join(self.base_vnf_instances_url, id, "instantiate")
        resp, _ = self.http_client.do_request(
            url, "POST", body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)
        if wait_state == "COMPLETED":
            self._vnf_instance_wait(id)
        # wait vnflcm_op_occs.operation_state become wait_state
        self._wait_vnflcm_op_occs(self.context, id,
                                  self.lcm_timeout['instantiate'], wait_state)

    def _create_and_instantiate_vnf_instance(self, vnfd_id, flavour_id,
                                             inst_name, inst_desc,
                                             additional_params):
        # create vnf instance
        _, vnf_instance = self._create_vnf_instance(
            vnfd_id, vnf_instance_name=inst_name,
            vnf_instance_description=inst_desc)
        self.assertEqual(
            'NOT_INSTANTIATED', vnf_instance['instantiationState'])

        # instantiate vnf instance
        additional_param = additional_params
        request_body = self._instantiate_vnf_instance_request(
            flavour_id, vim_id=self.vim_id, additional_param=additional_param)

        self._instantiate_vnf_instance(vnf_instance['id'], request_body)
        vnf_instance = self._show_vnf_instance(vnf_instance['id'])

        self.assertEqual(
            'INSTANTIATED', vnf_instance['instantiationState'])
        vnflcm_op_occ = self._get_vnflcm_op_occs_by_id(
            self.context, vnf_instance['id'])
        self.assertEqual('COMPLETED', vnflcm_op_occ.operation_state)
        self.assertEqual('INSTANTIATE', vnflcm_op_occ.operation)

        return vnf_instance

    def _modify_vnf_instance(self, vnf_instance_id, request_body):
        # modify vnf instance
        url = os.path.join(self.base_vnf_instances_url, vnf_instance_id)
        resp, _ = self.http_client.do_request(
            url, "PATCH", body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)
        time.sleep(5)
        self._wait_vnflcm_op_occs(
            self.context, vnf_instance_id, self.lcm_timeout['modify'])
        vnflcm_op_occ = self._get_vnflcm_op_occs_by_id(
            self.context, vnf_instance_id)
        self.assertEqual('MODIFY_INFO', vnflcm_op_occ.operation)
        vnf_instance = self._show_vnf_instance(vnf_instance_id)
        vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)
        return vnf_instance, vnfc_rscs

    def _terminate_vnf_instance(self, id, request_body=None):
        if request_body is None:
            # Terminate vnf forcefully
            request_body = {
                "terminationType": fields.VnfInstanceTerminationType.FORCEFUL,
            }
        url = os.path.join(self.base_vnf_instances_url, id, "terminate")
        resp, _ = self.http_client.do_request(
            url, "POST", body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)

        timeout = request_body.get('gracefulTerminationTimeout', None)
        start_time = int(time.time())

        self._vnf_instance_wait(
            id, instantiation_state=fields.VnfInstanceState.NOT_INSTANTIATED,
            timeout=self.lcm_timeout['terminate'])

        # If gracefulTerminationTimeout is set, check whether vnf
        # instantiation_state is set to NOT_INSTANTIATED after
        # gracefulTerminationTimeout seconds.
        if timeout and int(time.time()) - start_time < timeout:
            self.fail("Vnf is terminated before graceful termination "
                      "timeout period")

    def _delete_vnf_instance(self, id):
        self._delete_wait_vnf_instance(id)

        # verify vnf instance is deleted
        url = os.path.join(self.base_vnf_instances_url, id)
        resp, _ = self.http_client.do_request(url, "GET")
        self.assertEqual(404, resp.status_code)

    def _scale_vnf_instance(self, id, type, aspect_id,
                            number_of_steps=1):
        url = os.path.join(self.base_vnf_instances_url, id, "scale")
        # generate body
        request_body = {
            "type": type,
            "aspectId": aspect_id,
            "numberOfSteps": number_of_steps}
        resp, _ = self.http_client.do_request(
            url, "POST", body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)

    def _heal_vnf_instance(self, id, vnfc_instance_id):
        url = os.path.join(self.base_vnf_instances_url, id, "heal")
        # generate body
        request_body = {
            "vnfcInstanceId": vnfc_instance_id}
        resp, _ = self.http_client.do_request(
            url, "POST", body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)

    @classmethod
    @db_api.context_manager.reader
    def _get_vnflcm_op_occs_by_id(cls, context, vnf_instance_id,
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
            self, context, vnf_instance_id, timeout,
            operation_state='COMPLETED'):
        start_time = int(time.time())
        while True:
            vnflcm_op_occ = self._get_vnflcm_op_occs_by_id(
                context, vnf_instance_id)

            if vnflcm_op_occ.operation_state == operation_state:
                break

            if (int(time.time()) - start_time) > timeout:
                raise Exception("Timeout waiting for transition to"
                                f" {operation_state} state.")

            time.sleep(RETRY_WAIT_TIME)

    @classmethod
    def _get_vnfc_resource_info(cls, vnf_instance):
        inst_vnf_info = vnf_instance['instantiatedVnfInfo']
        vnfc_resource_info = inst_vnf_info['vnfcResourceInfo']
        return vnfc_resource_info

    def _get_scale_level_by_aspect_id(self, vnf_instance, aspect_id):
        scale_status = vnf_instance['instantiatedVnfInfo']['scaleStatus']
        self.assertTrue(len(scale_status) > 0)
        for status in scale_status:
            self.assertIsNotNone(status.get('aspectId'))
            self.assertIsNotNone(status.get('scaleLevel'))
            if status.get('aspectId') == aspect_id:
                scale_level = status.get('scaleLevel')
                break
        else:
            raise Exception(f"aspectId {aspect_id} is not found.")
        return scale_level

    def _test_scale(self, id, type, aspect_id, previous_level,
                    number_of_steps=1, error=False):
        # scale operation
        self._scale_vnf_instance(id, type, aspect_id, number_of_steps)
        wait_state = "COMPLETED"
        if error:
            expected_level = previous_level
            wait_state = "FAILED_TEMP"
        elif type == 'SCALE_OUT':
            expected_level = previous_level + number_of_steps
        else:
            expected_level = previous_level - number_of_steps
        # wait vnflcm_op_occs.operation_state become COMPLETE/FAILED_TEMP
        self._wait_vnflcm_op_occs(
            self.context, id, self.lcm_timeout['scale'], wait_state)
        # check scaleStatus after scale operation
        vnf_instance = self._show_vnf_instance(id)
        scale_level = self._get_scale_level_by_aspect_id(
            vnf_instance, aspect_id)
        self.assertEqual(scale_level, expected_level)

        return scale_level

    def _test_heal(self, vnf_instance, vnfc_instance_id):
        before_vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)
        self._heal_vnf_instance(vnf_instance['id'], vnfc_instance_id)
        # wait vnflcm_op_occs.operation_state become COMPLETE
        if vnfc_instance_id:
            timeout = self.lcm_timeout['heal_sol002']
        else:
            timeout = self.lcm_timeout['heal_sol003']
        self._wait_vnflcm_op_occs(self.context, vnf_instance['id'], timeout)
        # check vnfcResourceInfo after heal operation
        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        after_vnfc_rscs = self._get_vnfc_resource_info(vnf_instance)
        self.assertEqual(len(before_vnfc_rscs), len(after_vnfc_rscs))
        return after_vnfc_rscs

    def _rollback_vnf_instance(self, vnf_lcm_op_occ_id):
        url = os.path.join(
            self.base_vnf_lcm_op_occs_url, vnf_lcm_op_occ_id, "rollback")
        # generate body
        resp, _ = self.http_client.do_request(url, "POST")
        self.assertEqual(202, resp.status_code)

    def _test_rollback_cnf_instantiate(self, id):
        # get vnflcm_op_occ id for rollback
        vnflcm_op_occ = self._get_vnflcm_op_occs_by_id(
            self.context, id)
        vnf_lcm_op_occ_id = vnflcm_op_occ.id

        # rollback operation
        self._rollback_vnf_instance(vnf_lcm_op_occ_id)
        # wait vnflcm_op_occs.operation_state become ROLLED_BACK
        self._wait_vnflcm_op_occs(self.context, id,
            self.lcm_timeout['terminate'], "ROLLED_BACK")

    def _test_rollback_cnf_scale(self, id, aspect_id, previous_level):
        # get vnflcm_op_occ id for rollback
        vnflcm_op_occ = self._get_vnflcm_op_occs_by_id(self.context, id)
        vnf_lcm_op_occ_id = vnflcm_op_occ.id

        # rollback operation
        self._rollback_vnf_instance(vnf_lcm_op_occ_id)
        # wait vnflcm_op_occs.operation_state become ROLLED_BACK
        self._wait_vnflcm_op_occs(self.context, id, self.lcm_timeout['scale'],
                                  "ROLLED_BACK")
        # check scaleStatus after scale operation
        vnf_instance = self._show_vnf_instance(id)
        expected_level = previous_level
        scale_level = self._get_scale_level_by_aspect_id(
            vnf_instance, aspect_id)
        self.assertEqual(scale_level, expected_level)
