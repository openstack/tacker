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
import urllib
import yaml

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils
from tempest.lib import base

from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.infra_drivers.openstack import heat_utils
from tacker.sol_refactored import objects
from tacker.tests.functional.common.fake_server import FakeServerManager
from tacker.tests.functional.sol_v2 import utils
from tacker.tests import utils as base_utils
from tacker import version

FAKE_SERVER_MANAGER = FakeServerManager()
MOCK_NOTIFY_CALLBACK_URL = '/notification/callback'

LOG = logging.getLogger(__name__)

VNF_PACKAGE_UPLOAD_TIMEOUT = 300


class BaseSolV2Test(base.BaseTestCase):
    """Base test case class for SOL v2 functional tests."""

    @classmethod
    def setUpClass(cls):
        super(BaseSolV2Test, cls).setUpClass()

        FAKE_SERVER_MANAGER.prepare_http_server()
        FAKE_SERVER_MANAGER.start_server()

        cfg.CONF(args=['--config-file', '/etc/tacker/tacker.conf'],
                 project='tacker',
                 version='%%prog %s' % version.version_info.release_string())
        objects.register_all()

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
        cls.glance_client = http_client.HttpClient(auth,
                                                   service_type='image')
        cls.nova_client = http_client.HttpClient(auth,
                                                 service_type='compute')
        cls.heat_client = heat_utils.HeatClient(vim_info)

        cls.cinder_client = http_client.HttpClient(
            auth, service_type='block-storage')

    @classmethod
    def tearDownClass(cls):
        super(BaseSolV2Test, cls).tearDownClass()
        FAKE_SERVER_MANAGER.stop_server()

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

    def setUp(self):
        super().setUp()

        callback_url = os.path.join(
            MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        FAKE_SERVER_MANAGER.clear_history(callback_url)
        FAKE_SERVER_MANAGER.set_callback('POST', callback_url, status_code=204)
        FAKE_SERVER_MANAGER.set_callback('GET', callback_url, status_code=204)

    def get_vnf_package(self, pkg_id):
        path = "/vnfpkgm/v1/vnf_packages/{}".format(pkg_id)
        resp, body = self.tacker_client.do_request(path, "GET")
        return body

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

    def create_network(self, name):
        path = "/v2.0/networks"
        req_body = {
            "network": {
                # "admin_state_up": true,
                "name": name
            }
        }
        try:
            resp, resp_body = self.neutron_client.do_request(
                path, "POST", body=req_body)
            return resp_body['network']['id']
        except Exception as e:
            self.fail("Failed, create network for name=<%s>, %s" %
                (name, e))

    def delete_network(self, net_id):
        path = "/v2.0/networks/{}".format(net_id)
        try:
            self.neutron_client.do_request(path, "DELETE")
        except Exception as e:
            self.fail("Failed, delete network for id=<%s>, %s" %
                (net_id, e))

    def create_subnet(self, net_id, sub_name, sub_range, ip_version):
        path = "/v2.0/subnets"
        req_body = {
            "subnet": {
                "name": sub_name,
                "network_id": net_id,
                "cidr": sub_range,
                "ip_version": ip_version
            }
        }
        try:
            resp, resp_body = self.neutron_client.do_request(
                path, "POST", body=req_body)
            return resp_body['subnet']['id']
        except Exception as e:
            self.fail("Failed, create subnet for name=<%s>, %s" %
                (sub_name, e))

    def delete_subnet(self, sub_id):
        path = "/v2.0/subnets/{}".format(sub_id)
        try:
            self.neutron_client.do_request(path, "DELETE")
        except Exception as e:
            self.fail("Failed, delete subnet for id=<%s>, %s" %
                (sub_id, e))

    def create_port(self, network_id, name):
        path = "/v2.0/ports"
        req_body = {
            'port': {
                'network_id': network_id,
                'name': name
            }
        }
        try:
            resp, resp_body = self.neutron_client.do_request(
                path, "POST", body=req_body)
            return resp_body['port']['id']
        except Exception as e:
            self.fail("Failed, create port for net_id=<%s>, %s" %
                (network_id, e))

    def delete_port(self, port_id):
        path = "/v2.0/ports/{}".format(port_id)
        try:
            self.neutron_client.do_request(path, "DELETE")
        except Exception as e:
            self.fail("Failed, delete port for id=<%s>, %s" %
                (port_id, e))

    def get_image_id(self, image_name):
        path = "/v2.0/images"
        resp, resp_body = self.glance_client.do_request(path, "GET")

        image_id = None
        for image in resp_body.get('images'):
            if image_name == image['name']:
                image_id = image['id']
        return image_id

    def get_server_details(self, server_name):
        path = "/servers/detail"
        resp, resp_body = self.nova_client.do_request(path, "GET")

        server_details = None
        for server in resp_body.get('servers'):
            if server_name == server['name']:
                server_details = server
        return server_details

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

    def list_vnf_instance(self, filter_expr=None):
        path = "/vnflcm/v2/vnf_instances"
        if filter_expr:
            path = "{}?{}".format(path, urllib.parse.urlencode(filter_expr))
        return self.tacker_client.do_request(
            path, "GET", version="2.0.0")

    def instantiate_vnf_instance(self, inst_id, req_body):
        path = "/vnflcm/v2/vnf_instances/{}/instantiate".format(inst_id)
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def scale_vnf_instance(self, inst_id, req_body):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}/scale"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def update_vnf_instance(self, inst_id, req_body):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}"
        return self.tacker_client.do_request(
            path, "PATCH", body=req_body, version="2.0.0")

    def heal_vnf_instance(self, inst_id, req_body):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}/heal"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def change_ext_conn(self, inst_id, req_body):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}/change_ext_conn"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def change_vnfpkg(self, inst_id, req_body):
        path = "/vnflcm/v2/vnf_instances/{}/change_vnfpkg".format(inst_id)
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def terminate_vnf_instance(self, inst_id, req_body):
        path = "/vnflcm/v2/vnf_instances/{}/terminate".format(inst_id)
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def rollback(self, lcmocc_id):
        path = "/vnflcm/v2/vnf_lcm_op_occs/{}/rollback".format(lcmocc_id)
        return self.tacker_client.do_request(
            path, "POST", version="2.0.0")

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

    def wait_lcmocc_failed_temp(self, lcmocc_id):
        # NOTE: It is not necessary to set timeout because the operation
        # itself set timeout and the state will become 'FAILED_TEMP'.
        path = "/vnflcm/v2/vnf_lcm_op_occs/{}".format(lcmocc_id)
        while True:
            time.sleep(5)
            _, body = self.tacker_client.do_request(
                path, "GET", expected_status=[200], version="2.0.0")
            state = body['operationState']
            if state == 'FAILED_TEMP':
                return
            elif state in ['STARTING', 'PROCESSING']:
                continue
            elif state == 'COMPLETED':
                raise Exception("Operation unexpected COMPLETED.")
            else:  # ROLLED_BACK
                raise Exception("Operation failed. state: %s" % state)

    def wait_lcmocc_rolled_back(self, lcmocc_id):
        # NOTE: It is not necessary to set timeout because the operation
        # itself set timeout and the state will become 'FAILED_TEMP'.
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}"
        while True:
            time.sleep(5)
            _, body = self.tacker_client.do_request(
                path, "GET", expected_status=[200], version="2.0.0")
            state = body['operationState']
            if state == 'ROLLED_BACK':
                return
            if state in ['ROLLING_BACK']:
                continue

            raise Exception(f"Operation failed. state: {state}")

    def show_lcmocc(self, lcmocc_id):
        path = "/vnflcm/v2/vnf_lcm_op_occs/{}".format(lcmocc_id)
        return self.tacker_client.do_request(
            path, "GET", version="2.0.0")

    def list_lcmocc(self, filter_expr=None):
        path = "/vnflcm/v2/vnf_lcm_op_occs"
        if filter_expr:
            path = "{}?{}".format(path, urllib.parse.urlencode(filter_expr))
        return self.tacker_client.do_request(
            path, "GET", version="2.0.0")

    def rollback_lcmocc(self, lcmocc_id):
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}/rollback"
        return self.tacker_client.do_request(
            path, "POST", version="2.0.0")

    def retry_lcmocc(self, lcmocc_id):
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}/retry"
        return self.tacker_client.do_request(
            path, "POST", version="2.0.0")

    def fail_lcmocc(self, lcmocc_id):
        path = f"/vnflcm/v2/vnf_lcm_op_occs/{lcmocc_id}/fail"
        return self.tacker_client.do_request(
            path, "POST", version="2.0.0")

    def create_subscription(self, req_body):
        path = "/vnflcm/v2/subscriptions"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version="2.0.0")

    def delete_subscription(self, sub_id):
        path = "/vnflcm/v2/subscriptions/{}".format(sub_id)
        return self.tacker_client.do_request(
            path, "DELETE", version="2.0.0")

    def show_subscription(self, sub_id):
        path = "/vnflcm/v2/subscriptions/{}".format(sub_id)
        return self.tacker_client.do_request(
            path, "GET", version="2.0.0")

    def list_subscriptions(self, filter_expr=None):
        path = "/vnflcm/v2/subscriptions"
        if filter_expr:
            path = "{}?{}".format(path, urllib.parse.urlencode(filter_expr))
        return self.tacker_client.do_request(
            path, "GET", version="2.0.0")

    def _check_resp_headers(self, resp, supported_headers):
        unsupported_headers = ['Link', 'Retry-After',
                               'Content-Range', 'WWW-Authenticate']
        for s in supported_headers:
            if s not in resp.headers:
                raise Exception("Supported header doesn't exist: %s" % s)
        for u in unsupported_headers:
            if u in resp.headers:
                raise Exception("Unsupported header exist: %s" % u)

    def check_resp_headers_in_create(self, resp):
        # includes location header and response body
        supported_headers = ['Version', 'Location', 'Content-Type',
                             'Accept-Ranges']
        self._check_resp_headers(resp, supported_headers)

    def check_resp_headers_in_operation_task(self, resp):
        # includes location header and no response body
        supported_headers = ['Version', 'Location']
        self._check_resp_headers(resp, supported_headers)

    def check_resp_headers_in_get(self, resp):
        # includes response body and no location header
        supported_headers = ['Version', 'Content-Type',
                             'Accept-Ranges']
        self._check_resp_headers(resp, supported_headers)

    def check_resp_headers_in_delete(self, resp):
        # no location header and response body
        supported_headers = ['Version']
        self._check_resp_headers(resp, supported_headers)

    def check_resp_body(self, body, expected_attrs):
        for attr in expected_attrs:
            if attr not in body:
                raise Exception("Expected attribute doesn't exist: %s" % attr)

    def assert_notification_get(self, callback_url):
        notify_mock_responses = FAKE_SERVER_MANAGER.get_history(
            callback_url)
        FAKE_SERVER_MANAGER.clear_history(
            callback_url)
        self.assertEqual(1, len(notify_mock_responses))
        self.assertEqual(204, notify_mock_responses[0].status_code)

    def get_current_vdu_image(
            self, stack_id, stack_name, resource_name):
        vdu_info = self.heat_client.get_resource_info(
            f"{stack_name}/{stack_id}", resource_name)
        if vdu_info.get('attributes').get('image'):
            image_id = vdu_info.get('attributes').get('image').get('id')
        else:
            volume_ids = [volume.get('id') for volume in vdu_info.get(
                'attributes').get('os-extended-volumes:volumes_attached')]
            for volume_id in volume_ids:
                path = f"/volumes/{volume_id}"
                resp, resp_body = self.cinder_client.do_request(path, "GET")
                if resp_body['volume']['volume_image_metadata']:
                    image_id = resp_body['volume'][
                        'volume_image_metadata'].get('image_id')

        return image_id
