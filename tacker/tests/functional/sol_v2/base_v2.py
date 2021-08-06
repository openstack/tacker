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
import shutil
import tempfile
import time
import yaml

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils
from tempest.lib import base

from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.infra_drivers.openstack import heat_utils
from tacker.sol_refactored import objects
from tacker.tests.functional.sol_v2 import utils
from tacker.tests import utils as base_utils
from tacker import version


LOG = logging.getLogger(__name__)

VNF_PACKAGE_UPLOAD_TIMEOUT = 300


class BaseSolV2Test(base.BaseTestCase):
    """Base test case class for SOL v2 functionl tests."""

    @classmethod
    def setUpClass(cls):
        super(BaseSolV2Test, cls).setUpClass()

        cfg.CONF(args=['--config-file', '/etc/tacker/tacker.conf'],
                 project='tacker',
                 version='%%prog %s' % version.version_info.release_string())
        objects.register_all(False)

        vim_info = cls.get_vim_info()
        cls.auth_url = vim_info.interfaceInfo['endpoint']

        auth = http_client.KeystonePasswordAuthHandle(
            auth_url=vim_info.interfaceInfo['endpoint'],
            username=vim_info.accessInfo['username'],
            password=vim_info.accessInfo['password'],
            project_name=vim_info.accessInfo['project'],
            user_domain_name=vim_info.accessInfo['userDomain'],
            project_domain_name=vim_info.accessInfo['projectDomain']
        )
        cls.tacker_client = http_client.HttpClient(auth)
        cls.neutron_client = http_client.HttpClient(auth,
                                                    service_type='network')
        cls.heat_client = heat_utils.HeatClient(vim_info)

    @classmethod
    def get_vim_info(cls):
        vim_params = yaml.safe_load(base_utils.read_file('local-vim.yaml'))
        vim_params['auth_url'] += '/v3'

        vim_info = objects.VimConnectionInfo(
            interfaceInfo={'endpoint': vim_params['auth_url']},
            accessInfo={
                'region': 'RegionOne',
                'project': vim_params['project_name'],
                'username': vim_params['username'],
                'password': vim_params['password'],
                'userDomain': vim_params['user_domain_name'],
                'projectDomain': vim_params['project_domain_name']
            }
        )

        return vim_info

    @classmethod
    def create_vnf_package(cls, sample_path, user_data={}, image_path=None):
        vnfd_id = uuidutils.generate_uuid()
        tmp_dir = tempfile.mkdtemp()

        utils.make_zip(sample_path, tmp_dir, vnfd_id, image_path)

        zip_file_name = os.path.basename(os.path.abspath(sample_path)) + ".zip"
        zip_file_path = os.path.join(tmp_dir, zip_file_name)

        path = "/vnfpkgm/v1/vnf_packages"
        req_body = {'userDefinedData': user_data}
        resp, body = cls.tacker_client.do_request(
            path, "POST", expected_status=[201], body=req_body)

        pkg_id = body['id']

        with open(zip_file_path, 'rb') as fp:
            path = "/vnfpkgm/v1/vnf_packages/{}/package_content".format(pkg_id)
            resp, body = cls.tacker_client.do_request(
                path, "PUT", body=fp, content_type='application/zip',
                expected_status=[202])

        # wait for onboard
        timeout = VNF_PACKAGE_UPLOAD_TIMEOUT
        start_time = int(time.time())
        path = "/vnfpkgm/v1/vnf_packages/{}".format(pkg_id)
        while True:
            resp, body = cls.tacker_client.do_request(
                path, "GET", expected_status=[200])
            if body['onboardingState'] == "ONBOARDED":
                break

            if ((int(time.time()) - start_time) > timeout):
                raise Exception("Failed to onboard vnf package")

            time.sleep(5)

        shutil.rmtree(tmp_dir)

        return pkg_id, vnfd_id

    @classmethod
    def delete_vnf_package(cls, pkg_id):
        path = "/vnfpkgm/v1/vnf_packages/{}".format(pkg_id)
        req_body = {"operationalState": "DISABLED"}
        resp, _ = cls.tacker_client.do_request(
            path, "PATCH", body=req_body)
        if resp.status_code != 200:
            LOG.error("failed to set operationalState to DISABLED")
            return

        cls.tacker_client.do_request(path, "DELETE")

    def get_network_ids(self, networks):
        path = "/v2.0/networks"
        resp, body = self.neutron_client.do_request(path, "GET")
        net_ids = {}
        for net in body['networks']:
            if net['name'] in networks:
                net_ids[net['name']] = net['id']
        return net_ids

    def get_subnet_ids(self, subnets):
        path = "/v2.0/subnets"
        resp, body = self.neutron_client.do_request(path, "GET")
        subnet_ids = {}
        for subnet in body['subnets']:
            if subnet['name'] in subnets:
                subnet_ids[subnet['name']] = subnet['id']
        return subnet_ids

    def create_vnf_instance(self, req_body):
        path = "/vnflcm/v2/vnf_instances"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def delete_vnf_instance(self, inst_id):
        path = "/vnflcm/v2/vnf_instances/{}".format(inst_id)
        return self.tacker_client.do_request(
            path, "DELETE", version="2.0.0")

    def show_vnf_instance(self, inst_id):
        path = "/vnflcm/v2/vnf_instances/{}".format(inst_id)
        return self.tacker_client.do_request(
            path, "GET", version="2.0.0")

    def instantiate_vnf_instance(self, inst_id, req_body):
        path = "/vnflcm/v2/vnf_instances/{}/instantiate".format(inst_id)
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def terminate_vnf_instance(self, inst_id, req_body):
        path = "/vnflcm/v2/vnf_instances/{}/terminate".format(inst_id)
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def wait_lcmocc_complete(self, lcmocc_id):
        # NOTE: It is not necessary to set timeout because the operation
        # itself set timeout and the state will become 'FAILED_TEMP'.
        path = "/vnflcm/v2/vnf_lcm_op_occs/{}".format(lcmocc_id)
        while True:
            time.sleep(5)
            _, body = self.tacker_client.do_request(
                path, "GET", expected_status=[200], version="2.0.0")
            state = body['operationState']
            if state == 'COMPLETED':
                return
            elif state in ['STARTING', 'PROCESSING']:
                continue
            else:  # FAILED_TEMP or ROLLED_BACK
                raise Exception("Operation failed. state: %s" % state)
