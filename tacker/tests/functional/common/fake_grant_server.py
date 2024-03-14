# Copyright (C) 2022 Fujitsu
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
import ast
import hashlib
import io
import json
import os
import random
import re
import shutil
import tempfile
import zipfile

from flask import Flask
from flask import request
from flask import Response
from flask import send_file
from keystoneauth1.identity import v3
from keystoneauth1 import session
from novaclient import client as nova_client
from oslo_utils import uuidutils
from tackerclient.v1_0 import client as tacker_client
import yaml

from tacker.common.utils import str_to_bool
from tacker.tests import constants
from tacker.tests.functional.sol_separated_nfvo.vnflcm.fake_grant import Grant
from tacker.tests.functional.sol_separated_nfvo_v2 import fake_grant_v2
from tacker.tests.functional.sol_separated_nfvo_v2 import fake_vnfpkgm_v2
from tacker.tests import utils
from tacker.tests.utils import read_file


# sample_vnf_package's abs path v1
V1_VNF_PACKAGE_PATH = 'sample_v1.zip'
V1_VNFD_FILE_NAME = 'Definitions/helloworld3_df_simple.yaml'

# sample_vnf_package's abs path v2
V2_VNF_PACKAGE_PATH = 'sample_v2.zip'
V2_VNFD_FILE_NAME = 'Definitions/v2_sample2_df_simple.yaml'


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

        if resp.content_type != 'application/zip' and len(resp.get_data()) > 0:
            try:
                body = resp.get_data().decode("utf-8")
            except AttributeError:
                body = "binary file."
        else:
            body = 'binary file.'
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
        verify = str_to_bool(vim_params.pop('cert_verify', 'False'))
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
        verify = str_to_bool(vim_params.pop('cert_verify', 'False'))
        auth_ses = session.Session(auth=auth, verify=verify)
        return nova_client.Client(constants.NOVA_CLIENT_VERSION,
                                  session=auth_ses)

    def list_zone(self):
        try:
            zone = self.nova_client.services.list()
        except nova_client.exceptions.ClientException:
            print("availability zone does not exist.", flush=True)
            return []
        return zone

    def get_vim(self):
        vim_list = self.client.list_vims()
        vim = self.get_vim_specified(vim_list, 'VIM0')
        if not vim:
            assert False, "vim is Empty: specified VIM is missing"
        return vim

    def get_vim_specified(self, vim_list, vim_name):
        if len(vim_list.values()) == 0:
            assert False, "vim_list is Empty: Default VIM is missing"

        for vim_list in vim_list.values():
            for vim in vim_list:
                if vim['name'] == vim_name:
                    return vim
        return None

    @staticmethod
    def make_get_package_content_response_body(vnfd_id):
        csar_package_path, _ = get_package_path(vnfd_id)

        tempfd, tempname = tempfile.mkstemp(
            suffix=".zip", dir='/tmp')
        os.close(tempfd)

        with zipfile.ZipFile(tempname, 'w') as zcsar:
            _write_zipfile(zcsar, vnfd_id, [csar_package_path])

        shutil.rmtree(csar_package_path)

        _update_hash(tempname)

        return tempname

    @staticmethod
    def make_get_package_vnfd(vnfd_id, path):
        csar_package_path, _ = get_package_path(vnfd_id, path)

        tempfd, tempname = tempfile.mkstemp(
            suffix=".zip", dir='/tmp')
        os.close(tempfd)

        with zipfile.ZipFile(tempname, 'w') as zcsar:
            _write_zipfile(zcsar, vnfd_id, [csar_package_path],
                           operation='vnfd')

        shutil.rmtree(csar_package_path)

        return tempname


def _write_zipfile(zcsar, unique_id, target_dir_list, operation='package'):
    common_def = ['etsi_nfv_sol001_common_types.yaml',
                  'etsi_nfv_sol001_vnfd_types.yaml']
    new_names = {}
    for target_dir in target_dir_list:
        for (dpath, _, fnames) in os.walk(target_dir):
            if not fnames:
                continue
            for fname in fnames:
                src_file = os.path.join(dpath, fname)
                dst_file = os.path.relpath(
                    os.path.join(dpath, fname), target_dir)
                if operation == 'package':
                    if 'kubernetes' in dst_file.split('/'):
                        with open(src_file, 'rb') as yfile:
                            data = yaml.safe_load(yfile)
                            old_name, new_name = _update_res_name(data)
                            zcsar.writestr(dst_file, yaml.dump(
                                data, default_flow_style=False,
                                allow_unicode=True, sort_keys=False))
                        new_names[old_name] = new_name
                    elif not dst_file.startswith('Definitions') and (
                            not dst_file.startswith('TOSCA')):
                        zcsar.write(src_file, dst_file)

    for target_dir in target_dir_list:
        for (dpath, _, fnames) in os.walk(target_dir):
            if not fnames:
                continue
            for fname in fnames:
                src_file = os.path.join(dpath, fname)
                dst_file = os.path.relpath(
                    os.path.join(dpath, fname), target_dir)
                if dst_file.startswith('Definitions') and (
                        fname not in common_def):
                    with open(src_file, 'rb') as yfile:
                        data = yaml.safe_load(yfile)
                        utils._update_unique_id_in_yaml(data, unique_id)
                        if new_names:
                            data = _update_df_name(data, new_names)
                        zcsar.writestr(dst_file, yaml.dump(
                            data, default_flow_style=False,
                            allow_unicode=True))
                if fname == 'TOSCA.meta':
                    zcsar.write(src_file, dst_file)
                if dst_file.startswith('Definitions') and (
                        fname in common_def):
                    zcsar.write(src_file, dst_file)


def _update_hash(tempname):
    old_hash = {}
    new_hash = {}
    file_content = {}
    with zipfile.ZipFile(tempname, 'r') as z:
        paths = [file for file in z.namelist() if 'kubernetes' in file]
        tosca_content = z.read('TOSCA-Metadata/TOSCA.meta')
        contents = re.split(b'\n\n+', z.read('TOSCA-Metadata/TOSCA.meta'))
        if paths:
            for path in paths:
                hash_obj = hashlib.sha256()
                hash_obj.update(z.read(path))
                new_hash[path] = hash_obj.hexdigest()
                old_hash[path] = [
                    yaml.safe_load(content)['Hash'] for content
                    in contents if yaml.safe_load(content).get(
                        'Name') == path][0]
            name_list = z.namelist()
            for name in z.namelist():
                if not name.startswith('TOSCA'):
                    file_content[name] = z.read(name)

    if new_hash:
        with zipfile.ZipFile(tempname, 'w') as z:
            for name in name_list:
                if name.startswith('TOSCA'):
                    for file, hash in new_hash.items():
                        old_value = [value for key, value in old_hash.items()
                                     if key == file][0]
                        new_tosca = tosca_content.replace(
                            bytes(old_value, 'utf-8'), bytes(hash, 'utf-8'))
                    z.writestr('TOSCA-Metadata/TOSCA.meta', new_tosca)
                else:
                    z.writestr(name, file_content[name])


def _update_df_name(data, new_names):
    data_str = str(data)
    for old_name, new_name in new_names.items():
        data_str = data_str.replace(old_name, new_name)
    data = ast.literal_eval(data_str)
    return data


def _get_random_string(slen=5):
    random_str = ''
    base_str = 'abcdefghigklmnopqrstuvwxyz0123456789'
    length = len(base_str) - 1
    for i in range(slen):
        random_str += base_str[random.randint(0, length)]
    return random_str


def _update_res_name(data):
    old_name = data['metadata']['name']
    data['metadata']['name'] = (
        f"{data['metadata']['name']}-{_get_random_string()}")
    return old_name, data['metadata']['name']


def get_package_path(vnfd_id, version='v1'):
    if version == 'v1':
        csar_package_path = V1_VNF_PACKAGE_PATH
        vnfd_path = V1_VNFD_FILE_NAME
    else:
        csar_package_path = V2_VNF_PACKAGE_PATH
        vnfd_path = V2_VNFD_FILE_NAME
    (tmp_path, _) = os.path.split(csar_package_path)
    tmp_abs_path = os.path.join(tmp_path, vnfd_id)
    with zipfile.ZipFile(csar_package_path) as zf_obj:
        zf_obj.extractall(path=tmp_abs_path)
    return tmp_abs_path, vnfd_path


def get_common_resp_info(request_body):
    csar_path, vnfd_path = get_package_path(request_body['vnfdId'])
    glance_image = fake_grant_v2.GrantV2.get_sw_image(csar_path, vnfd_path)
    flavour_vdu_dict = fake_grant_v2.GrantV2.get_compute_flavor(
        csar_path, vnfd_path)
    availability_zone_info = GrantServer().list_zone()
    zone_name_list = list(set(
        [zone.zone for zone in availability_zone_info
         if zone.binary == 'nova-compute']))
    return glance_image, flavour_vdu_dict, zone_name_list


@GrantServer.app.route('/v1/grant/v1/grants', methods=['POST'])
def grant():
    body = request.json
    request_body = Grant.convert_body_to_dict(body)
    glance_image, flavour_vdu_dict, zone_name_list = get_common_resp_info(
        request_body)
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


@GrantServer.app.route('/grant/v1/grants', methods=['POST'])
def grant_v2():
    body = request.json
    request_body = fake_grant_v2.GrantV2.convert_body_to_dict(body)
    glance_image, flavour_vdu_dict, zone_name_list = get_common_resp_info(
        request_body)
    if request_body['operation'] == 'INSTANTIATE':
        resp_body = fake_grant_v2.GrantV2.make_inst_response_body(
            body, glance_image, flavour_vdu_dict,
            zone_name_list)
    if request_body['operation'] == 'SCALE':
        resp_body = fake_grant_v2.GrantV2.make_scale_response_body(
            body, glance_image, flavour_vdu_dict,
            zone_name_list)
    if request_body['operation'] == 'HEAL':
        resp_body = fake_grant_v2.GrantV2.make_heal_response_body(
            body, glance_image, flavour_vdu_dict,
            zone_name_list)
    if request_body['operation'] == 'CHANGE_EXT_CONN':
        resp_body = fake_grant_v2.GrantV2.make_change_ext_conn_response_body(
            body, zone_name_list)
    if request_body['operation'] == 'CHANGE_VNFPKG':
        resp_body = fake_grant_v2.GrantV2.make_change_vnfpkg_response_body(
            body)
    if request_body['operation'] == 'TERMINATE':
        resp_body = fake_grant_v2.GrantV2.make_term_response_body(body)
    resp = (resp_body, '201', {"content-type": "application/json"})
    return resp


@GrantServer.app.route('/token', methods=['POST'])
def get_token():
    resp_body = {"access_token": 'fake_token'}
    resp = (resp_body, '200', {"content-type": "application/json"})
    return resp


@GrantServer.app.route('/notification/callbackuri/<vnfdid>',
                       methods=['GET', 'POST'])
def callback(vnfdid):
    resp = Response(status=204)
    return resp


@GrantServer.app.route('/vnfpkgm/v1/vnf_packages',
                       methods=['GET'])
def get_vnf_package_v1():
    vnfd_id = request.url
    vnfd_id = vnfd_id.split("vnfdId%2C")[1].split("%29")[0]
    resp_body = [
        {
            "id": uuidutils.generate_uuid(),
            "vnfdId": vnfd_id,
            "vnfProvider": "Company",
            "vnfProductName": "Sample VNF",
            "vnfSoftwareVersion": "1.0",
            "vnfdVersion": "1.0",
            "onboardingState": "ONBOARDED",
            "operationalState": "ENABLED",
            "usageState": "NOT_IN_USE"
        }
    ]

    vnf_package_path = "/tmp/vnf_package_data"
    data_file = vnf_package_path + "/" + resp_body[0]["id"]
    tempname = GrantServer().make_get_package_content_response_body(vnfd_id)

    if not os.path.exists(vnf_package_path):
        os.makedirs(vnf_package_path)
    else:
        with open(data_file, "w") as f:
            f.write(tempname)

    resp = (json.dumps(resp_body), '200', {'Content-Type': 'application/json'})
    return resp


@GrantServer.app.route(
    '/vnfpkgm/v1/vnf_packages/<vnf_package_id>/vnfd',
    methods=['GET'])
def get_vnf_package_vnfd(vnf_package_id):
    zip_path = "/tmp/vnf_package_data/" + vnf_package_id
    with open(zip_path, "rb") as f:
        tempname = f.read()

    with open(tempname, "rb") as f:
        bytes_file = io.BytesIO(f.read())

    return (
        send_file(bytes_file, mimetype='application/zip'), '200',
        {'Content-Type': 'application/zip'})


@GrantServer.app.route(
    '/vnfpkgm/v1/vnf_packages/<vnf_package_id>/artifacts/<artifact_path>',
    methods=['GET'])
def get_vnf_package_artifact_path():
    resp = Response(status=200)
    return resp


@GrantServer.app.route(
    '/vnfpkgm/v1/vnf_packages/<vnf_package_id>/package_content',
    methods=['GET'])
def get_vnf_package_content_v1(vnf_package_id):
    zip_path = "/tmp/vnf_package_data/" + vnf_package_id
    with open(zip_path, "rb") as f:
        tempname = f.read()

    with open(tempname, "rb") as f:
        bytes_file = io.BytesIO(f.read())

    return (send_file(
        bytes_file, mimetype='application/zip'), '200',
        {'Content-Type': 'application/zip'})


@GrantServer.app.route(
    '/vnfpkgm/v2/onboarded_vnf_packages/<vnfdid>/package_content',
    methods=['GET'])
def get_vnf_package_content(vnfdid):
    resp_body = GrantServer().make_get_package_content_response_body(vnfdid)
    with open(resp_body, "rb") as f:
        bytes_file = io.BytesIO(f.read())
    return (send_file(
        bytes_file, mimetype='application/zip'), '200',
        {'Content-Type': 'application/zip'})


@GrantServer.app.route('/vnfpkgm/v2/onboarded_vnf_packages/<vnfdid>',
                       methods=['GET'])
def get_vnf_package(vnfdid):
    resp_body = (
        fake_vnfpkgm_v2.VnfPackage.make_get_vnf_pkg_info_resp(vnfdid))
    resp = (resp_body, '200', {'Content-Type': 'application/json'})
    return resp


@GrantServer.app.route('/vnfpkgm/v2/onboarded_vnf_packages/<vnfdid>/vnfd',
                       methods=['GET'])
def get_vnfd(vnfdid):
    resp_body = GrantServer().make_get_package_content_response_body(vnfdid)
    with open(resp_body, "rb") as f:
        bytes_file = io.BytesIO(f.read())
    return (send_file(bytes_file, mimetype='application/zip'),
            '200', {'Content-Type': 'application/zip'})


# Start Fake_Grant_Server for manual test
GrantServer.app.before_request(GrantServer.log_http_request)
GrantServer.app.after_request(GrantServer.log_http_response)
GrantServer.app.run(host="127.0.0.1", port=9990, debug=False)
