#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import tempfile
import time
import yaml
import zipfile

from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from tacker.objects import fields
from tacker.tests.functional import base
from tacker.tests import utils


VNF_PACKAGE_UPLOAD_TIMEOUT = 60
VNF_INSTANTIATE_TIMEOUT = 60
VNF_TERMINATE_TIMEOUT = 60
VNF_INSTANTIATE_ERROR_WAIT = 80
VNF_DELETE_COMPLETION_WAIT = 60


def _get_external_virtual_links(net0_id):
    return [
        {
            "id": "net0",
            "resourceId": net0_id,
            "extCps": [{
                "cpdId": "CP1",
                "cpConfig": [{
                    "cpProtocolData": [{
                        "layerProtocol": "IP_OVER_ETHERNET",
                    }]
                }]
            }]
        }
    ]


def _create_csar_with_unique_vnfd_id(csar_dir):
    unique_id = uuidutils.generate_uuid()
    tempfd, tempname = tempfile.mkstemp(suffix=".zip",
        dir=os.path.dirname(csar_dir))
    os.close(tempfd)
    common_dir = os.path.join(csar_dir, "../common/")
    ud_common_dir = os.path.join(csar_dir, "../user_data_common/")
    zcsar = zipfile.ZipFile(tempname, 'w')

    target_dir_list = [csar_dir, common_dir, ud_common_dir]
    _write_zipfile(zcsar, unique_id, target_dir_list)

    zcsar.close()
    return tempname, unique_id


def _write_zipfile(zcsar, unique_id, target_dir_list):
    for target_dir in target_dir_list:
        for (dpath, _, fnames) in os.walk(target_dir):
            if not fnames:
                continue
            for fname in fnames:
                src_file = os.path.join(dpath, fname)
                dst_file = os.path.relpath(
                    os.path.join(dpath, fname), target_dir)
                if fname.endswith('.yaml') or fname.endswith('.yml'):
                    with open(src_file, 'rb') as yfile:
                        data = yaml.safe_load(yfile)
                        utils._update_unique_id_in_yaml(data, unique_id)
                        zcsar.writestr(dst_file, yaml.dump(
                            data, default_flow_style=False,
                            allow_unicode=True))
                else:
                    zcsar.write(src_file, dst_file)


def _create_and_upload_vnf_package(tacker_client, csar_package_name,
        user_defined_data):
    # create vnf package
    body = jsonutils.dumps({"userDefinedData": user_defined_data})
    resp, vnf_package = tacker_client.do_request(
        '/vnfpkgm/v1/vnf_packages', "POST", body=body)

    # upload vnf package
    csar_package_path = \
        "../../etc/samples/etsi/nfv/%s" % csar_package_name
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
        csar_package_path))

    # Generating unique vnfd id. This is required when multiple workers
    # are running concurrently. The call below creates a new temporary
    # CSAR with unique vnfd id.
    file_path, uniqueid = _create_csar_with_unique_vnfd_id(file_path)

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


class VnfLcmWithUserDataTest(base.BaseTackerTest):

    def setUp(self):
        super(VnfLcmWithUserDataTest, self).setUp()

        self.tacker_client = base.BaseTackerTest.tacker_http_client()
        self.base_url = "/vnflcm/v1/vnf_instances"

        vim_list = self.client.list_vims()
        self.vim = self.get_vim(vim_list, 'VIM0')
        if not self.vim:
            assert False, "vim_list is Empty: Default VIM is missing"

        neutron_client = self.neutronclient()
        net = neutron_client.list_networks()
        networks = {}
        for network in net['networks']:
            networks[network['name']] = network['id']

        net0_id = networks.get('net0')
        if not net0_id:
            self.fail("net0 network is not available")

        self.ext_vl = _get_external_virtual_links(net0_id)

    def _create_instantiate_vnf_request_body(self, flavour_id,
            instantiation_level_id=None, vim_id=None, ext_vl=None,
            add_params=None):
        request_body = {"flavourId": flavour_id}

        if instantiation_level_id:
            request_body["instantiationLevelId"] = instantiation_level_id

        if ext_vl:
            request_body["extVirtualLinks"] = ext_vl

        if vim_id:
            request_body["vimConnectionInfo"] = [
                {"id": uuidutils.generate_uuid(),
                 "vimId": vim_id,
                 "vimType": "ETSINFV.OPENSTACK_KEYSTONE.v_2"}]

        if add_params:
            request_body["additionalParams"] = add_params

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

    def _delete_vnf_instance(self, id):
        url = os.path.join(self.base_url, id)
        resp, body = self.http_client.do_request(url, "DELETE")
        self.assertEqual(204, resp.status_code)

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

    def _vnf_instance_wait(self, id,
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

            time.sleep(5)

    def _vnf_instance_wait_until_fail_detected(self, id,
            instantiation_state=fields.VnfInstanceState.NOT_INSTANTIATED,
            timeout=VNF_INSTANTIATE_ERROR_WAIT):
        show_url = os.path.join(self.base_url, id)

        time.sleep(VNF_INSTANTIATE_ERROR_WAIT)
        resp, body = self.http_client.do_request(show_url, "GET")
        if body['instantiationState'] != instantiation_state:
            error = ("Vnf instance %(id)s status is %(current)s, "
                     "expected status should be %(expected)s")
            self.fail(error % {"id": id,
                "current": body['instantiationState'],
                "expected": instantiation_state})

    def _instantiate_vnf_instance(self, id, request_body):
        url = os.path.join(self.base_url, id, "instantiate")
        resp, body = self.http_client.do_request(url, "POST",
                body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)
        self._vnf_instance_wait(id)

    def _instantiate_vnf_instance_fail(self, id, request_body):
        url = os.path.join(self.base_url, id, "instantiate")
        resp, body = self.http_client.do_request(url, "POST",
                body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)

        # Confirm that the state doesn't change from NOT_INSTANTIATED.
        self._vnf_instance_wait_until_fail_detected(id)

    def _terminate_vnf_instance(self, id, request_body):
        url = os.path.join(self.base_url, id, "terminate")
        resp, body = self.http_client.do_request(url, "POST",
                body=jsonutils.dumps(request_body))
        self.assertEqual(202, resp.status_code)

        timeout = request_body.get('gracefulTerminationTimeout')
        start_time = int(time.time())

        self._vnf_instance_wait(id,
            instantiation_state=fields.VnfInstanceState.NOT_INSTANTIATED,
            timeout=VNF_TERMINATE_TIMEOUT)

        # If gracefulTerminationTimeout is set, check whether vnf
        # instantiation_state is set to NOT_INSTANTIATED after
        # gracefulTerminationTimeout seconds.
        if timeout and int(time.time()) - start_time < timeout:
            self.fail("Vnf is terminated before graceful termination "
                      "timeout period")

        # wait for status completion
        time.sleep(VNF_DELETE_COMPLETION_WAIT)

    def _delete_vnf_package(self, vnf_package_id):
        url = '/vnfpkgm/v1/vnf_packages/%s' % vnf_package_id

        # Update vnf package before delete
        req_body = jsonutils.dumps({"operationalState": "DISABLED"})
        self.tacker_client.do_request(url, "PATCH", body=req_body)

        # Delete vnf package before delete
        self.tacker_client.do_request(url, "DELETE")

    def test_instantiate_vnf_normal(self):
        # Create vnf package
        sample_name = "user_data_sample_normal"
        vnf_package_id, vnfd_id = _create_and_upload_vnf_package(
            self.tacker_client, sample_name, {"key": sample_name})

        # Reserve deleting vnf package
        self.addCleanup(self._delete_vnf_package, vnf_package_id)

        # Settings
        vnf_instance_name = "vnf_with_user_data-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf_with_user_data_normal"

        add_params = {
            "lcm-operation-user-data": "./UserData/lcm_user_data.py",
            "lcm-operation-user-data-class": "SampleUserData"}

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance(vnfd_id,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)

        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # Reserve deleting vnf instance
        self.addCleanup(self._delete_vnf_instance, vnf_instance['id'])

        request_body = self._create_instantiate_vnf_request_body("simple",
            vim_id=self.vim['id'], ext_vl=self.ext_vl, add_params=add_params)

        self._instantiate_vnf_instance(vnf_instance['id'], request_body)

        vnf_instance = self._show_vnf_instance(vnf_instance['id'])
        vdu_count = len(vnf_instance['instantiatedVnfInfo']
            ['vnfcResourceInfo'])
        self.assertEqual(1, vdu_count)

        # Terminate vnf forcefully
        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.FORCEFUL
        }

        self._terminate_vnf_instance(vnf_instance['id'], terminate_req_body)

    def test_instantiate_vnf_basehot_invalid(self):
        # Create vnf package
        sample_name = "user_data_sample_basehot_invalid"
        vnf_package_id, vnfd_id = _create_and_upload_vnf_package(
            self.tacker_client, sample_name, {"key": sample_name})

        # Reserve deleting vnf package
        self.addCleanup(self._delete_vnf_package, vnf_package_id)

        # Settings
        vnf_instance_name = "vnf_with_user_data-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf_with_user_data_basehot_invalid"
        add_params = {
            "lcm-operation-user-data": "./UserData/lcm_user_data.py",
            "lcm-operation-user-data-class": "SampleUserData"}

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance(vnfd_id,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # Reserve deleting vnf instance
        self.addCleanup(self._delete_vnf_instance, vnf_instance['id'])

        request_body = self._create_instantiate_vnf_request_body("simple",
            vim_id=self.vim['id'], ext_vl=self.ext_vl, add_params=add_params)

        self._instantiate_vnf_instance_fail(vnf_instance['id'], request_body)

    def test_instantiate_vnf_userdata_timeout(self):
        # Create vnf package
        sample_name = "user_data_sample_userdata_timeout"
        vnf_package_id, vnfd_id = _create_and_upload_vnf_package(
            self.tacker_client, sample_name, {"key": sample_name})

        # Reserve deleting vnf package
        self.addCleanup(self._delete_vnf_package, vnf_package_id)

        # Settings
        vnf_instance_name = "vnf_with_user_data-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf_with_user_data_timeout"
        add_params = {
            "lcm-operation-user-data": "./UserData/lcm_user_data_sleeping.py",
            "lcm-operation-user-data-class": "SampleUserData"}

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance(vnfd_id,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # Reserve deleting vnf instance
        self.addCleanup(self._delete_vnf_instance, vnf_instance['id'])

        request_body = self._create_instantiate_vnf_request_body("simple",
            vim_id=self.vim['id'], ext_vl=self.ext_vl, add_params=add_params)

        self._instantiate_vnf_instance_fail(vnf_instance['id'], request_body)

    def test_instantiate_vnf_userdata_invalid_hot_param(self):
        # Create vnf package
        sample_name = "user_data_sample_userdata_invalid_hot_param"
        vnf_package_id, vnfd_id = _create_and_upload_vnf_package(
            self.tacker_client, sample_name, {"key": sample_name})

        # Reserve deleting vnf package
        self.addCleanup(self._delete_vnf_package, vnf_package_id)

        # Settings
        vnf_instance_name = "vnf_with_user_data-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf_with_user_data_timeout"
        add_params = {
            "lcm-operation-user-data": "./UserData/"
            "lcm_user_data_invalid_hot_param.py",
            "lcm-operation-user-data-class": "SampleUserData"}

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance(vnfd_id,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # Reserve deleting vnf instance
        self.addCleanup(self._delete_vnf_instance, vnf_instance['id'])

        request_body = self._create_instantiate_vnf_request_body("simple",
            vim_id=self.vim['id'], ext_vl=self.ext_vl, add_params=add_params)

        self._instantiate_vnf_instance_fail(vnf_instance['id'], request_body)

    def test_instantiate_vnf_userdata_none(self):
        # Create vnf package
        sample_name = "user_data_sample_userdata_none"
        vnf_package_id, vnfd_id = _create_and_upload_vnf_package(
            self.tacker_client, sample_name, {"key": sample_name})

        # Reserve deleting vnf package
        self.addCleanup(self._delete_vnf_package, vnf_package_id)

        # Settings
        vnf_instance_name = "vnf_with_user_data-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf_with_user_data_timeout"
        add_params = {
            "lcm-operation-user-data": "./UserData/lcm_user_data.py",
            "lcm-operation-user-data-class": "SampleUserData"}

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance(vnfd_id,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # Reserve deleting vnf instance
        self.addCleanup(self._delete_vnf_instance, vnf_instance['id'])

        request_body = self._create_instantiate_vnf_request_body("simple",
            vim_id=self.vim['id'], ext_vl=self.ext_vl, add_params=add_params)

        self._instantiate_vnf_instance_fail(vnf_instance['id'], request_body)

    def test_instantiate_vnf_userdata_invalid_script(self):
        # Create vnf package
        sample_name = "user_data_sample_userdata_invalid_script"
        vnf_package_id, vnfd_id = _create_and_upload_vnf_package(
            self.tacker_client, sample_name, {"key": sample_name})

        # Reserve deleting vnf package
        self.addCleanup(self._delete_vnf_package, vnf_package_id)

        # Settings
        vnf_instance_name = "vnf_with_user_data-%s" % \
            uuidutils.generate_uuid()
        vnf_instance_description = "vnf_with_user_data_timeout"
        add_params = {
            "lcm-operation-user-data": "./UserData/"
            "lcm_user_data_invalid_script.py",
            "lcm-operation-user-data-class": "SampleUserData"}

        # Create vnf instance
        resp, vnf_instance = self._create_vnf_instance(vnfd_id,
                vnf_instance_name=vnf_instance_name,
                vnf_instance_description=vnf_instance_description)
        self.assertIsNotNone(vnf_instance['id'])
        self.assertEqual(201, resp.status_code)

        # Reserve deleting vnf instance
        self.addCleanup(self._delete_vnf_instance, vnf_instance['id'])

        request_body = self._create_instantiate_vnf_request_body("simple",
            vim_id=self.vim['id'], ext_vl=self.ext_vl, add_params=add_params)

        self._instantiate_vnf_instance_fail(vnf_instance['id'], request_body)
