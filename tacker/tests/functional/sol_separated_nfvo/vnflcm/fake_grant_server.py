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
import re

from flask import Flask
from flask import request
from keystoneauth1.identity import v3
from keystoneauth1 import session
from novaclient import client as nova_client
from tackerclient.v1_0 import client as tacker_client
import yaml

from tacker.tests import constants
from tacker.tests.functional.sol_separated_nfvo.vnflcm.fake_grant import Grant
from tacker.tests.utils import read_file


class GrantServer:
    app = Flask(__name__)

    def __init__(self):
        self.client = self.tackerclient()
        self.nova_client = self.novaclient()

    @staticmethod
    def log_http_request():
        message = "Method:{0}, Url:{1}, Headers:{2}, Body:{3}"
        body = ""
        ct = "{0}".format(request.headers.get("Content-type"))
        print(ct)
        if len(request.get_data()) > 0 and not re.match(
                ".*?application/zip.*?", ct):
            body = request.get_data().decode("utf-8")
        hs = ""
        ff = "{0}:{1};"
        for k, v in request.headers.items():
            hs += ff.format(k, v)
        message = message.format(request.method, request.url, hs, body)
        print(message)

    @staticmethod
    def log_http_response(resp):
        message = "Status:{0}, Body:{1}"
        body = ""

        if len(resp.get_data()) > 0:
            try:
                body = resp.get_data().decode("utf-8")
            except AttributeError:
                body = "binary file."
        message = message.format(resp.status_code, body)
        print(message)
        return resp

    def get_auth_session(self):
        vim_params = self.get_credentials()
        auth = v3.Password(
            auth_url=vim_params['auth_url'],
            username=vim_params['username'],
            password=vim_params['password'],
            project_name=vim_params['project_name'],
            user_domain_name=vim_params['user_domain_name'],
            project_domain_name=vim_params['project_domain_name'])
        verify = 'True' == vim_params.pop('cert_verify', 'False')
        auth_ses = session.Session(auth=auth, verify=verify)
        return auth_ses

    def get_credentials(self):
        vim_params = yaml.safe_load(read_file('local-vim.yaml'))
        vim_params['auth_url'] += '/v3'
        return vim_params

    def tackerclient(self):
        auth_session = self.get_auth_session()
        return tacker_client.Client(session=auth_session, retries=5)

    def novaclient(self):
        vim_params = self.get_credentials()
        auth = v3.Password(auth_url=vim_params['auth_url'],
            username=vim_params['username'],
            password=vim_params['password'],
            project_name=vim_params['project_name'],
            user_domain_name=vim_params['user_domain_name'],
            project_domain_name=vim_params['project_domain_name'])
        verify = 'True' == vim_params.pop('cert_verify', 'False')
        auth_ses = session.Session(auth=auth, verify=verify)
        return nova_client.Client(constants.NOVA_CLIENT_VERSION,
                                  session=auth_ses)

    def list_zone(self):
        try:
            zone = self.nova_client.services.list()
        except nova_client.exceptions.ClientException:
            print("availability zone does not exists.", flush=True)
            return []
        return zone

    def get_vim(self):
        vim_list = self.client.list_vims()
        vim = self.get_vim_specified(vim_list, 'openstack-admin-vim')
        if not vim:
            assert False, "vim_list is Empty: Default VIM is missing"
        return vim

    def get_vim_specified(self, vim_list, vim_name):
        if len(vim_list.values()) == 0:
            assert False, "vim_list is Empty: Default VIM is missing"

        for vim_list in vim_list.values():
            for vim in vim_list:
                if vim['name'] == vim_name:
                    return vim
        return None


@GrantServer.app.route('/grant/v1/grants', methods=['POST'])
def grant():
    body = request.json
    request_body = Grant.convert_body_to_dict(body)
    glance_image = Grant.get_sw_image("functional5")
    flavour_vdu_dict = Grant.get_compute_flavor("functional5")
    availability_zone_info = GrantServer().list_zone()
    zone_name_list = list(set(
        [zone.zone for zone in availability_zone_info
         if zone.binary == 'nova-compute']))
    vim = GrantServer().get_vim()
    if request_body['operation'] == 'INSTANTIATE':
        return Grant.make_inst_response_body(
            body, vim['tenant_id'], glance_image, flavour_vdu_dict,
            zone_name_list)
    if request_body['operation'] == 'SCALE':
        return Grant.make_scale_response_body(
            body, vim['tenant_id'], glance_image, flavour_vdu_dict,
            zone_name_list)
    if request_body['operation'] == 'HEAL':
        return Grant.make_heal_response_body(
            body, vim['tenant_id'], glance_image, flavour_vdu_dict,
            zone_name_list)
    if request_body['operation'] == 'CHANGE_EXT_CONN':
        return Grant.make_change_ext_conn_response_body(
            body, vim['tenant_id'], zone_name_list)
    if request_body['operation'] == 'TERMINATE':
        return Grant.make_term_response_body(body)


# Start Fake_Grant_Server for manual test
GrantServer.app.before_request(GrantServer.log_http_request)
GrantServer.app.after_request(GrantServer.log_http_response)
GrantServer.app.run(host="127.0.0.1", port=9990, debug=False)
