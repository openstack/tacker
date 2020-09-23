# Copyright 2015 Brocade Communications System, Inc.
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

import base64
import http.server
import os
import re
import shutil
import threading

from oslo_utils import uuidutils
import socketserver
import tempfile
import yaml
import zipfile


def read_file(input_file):
    yaml_file = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             'etc/samples/' + str(input_file)))
    with open(yaml_file, 'r') as f:
        return f.read()


def _update_unique_id_in_yaml(data, uid):
    try:
        prop = data['topology_template']['node_templates']['VNF'][
            'properties']
        if (prop.get('descriptor_id', None)):
            prop['descriptor_id'] = uid
    except KeyError:
        # Let's check for 'node_types'
        pass

    if not data.get('node_types', None):
        return

    for ntype in data['node_types'].values():
        if ntype['derived_from'] != 'tosca.nodes.nfv.VNF':
            continue
        try:
            desc_id = ntype['properties']['descriptor_id']
            if desc_id.get('constraints', None):
                for constraint in desc_id.get('constraints'):
                    if constraint.get('valid_values', None):
                        constraint['valid_values'] = [uid]
            if desc_id.get('default', None):
                desc_id['default'] = uid
        except KeyError:
            # Let's check next node_type
            pass


def create_csar_with_unique_vnfd_id(csar_dir):
    """Create CSAR file from a directory structure

    For various tests it is necessary to have a CSAR having unique vnfd id.
    This function reads a directory structure, updates vnfd id in yaml files
    and creates a temporary CSAR zip file.

    :returns:
        - csar_file_name
        - vnfd_id
    """
    unique_id = uuidutils.generate_uuid()
    tempfd, tempname = tempfile.mkstemp(suffix=".zip",
        dir=os.path.dirname(csar_dir))
    os.close(tempfd)
    common_dir = os.path.join(csar_dir, "../common/")
    zcsar = zipfile.ZipFile(tempname, 'w')

    artifact_files = []
    for (dpath, _, fnames) in os.walk(csar_dir):
        if not fnames:
            continue
        for fname in fnames:
            if fname == 'TOSCA.meta' or fname.endswith('.mf'):
                src_file = os.path.join(dpath, fname)
                with open(src_file, 'rb') as f:
                    artifacts_data = f.read()
                artifacts_data_split = re.split(b'\n\n+', artifacts_data)
                for data in artifacts_data_split:
                    if re.findall(b'.?Algorithm:.?|.?Hash:.?', data):
                        artifact_data_dict = yaml.safe_load(data)
                        artifact_files.append(
                            artifact_data_dict['Source']
                            if 'Source' in artifact_data_dict.keys()
                            else artifact_data_dict['Name'])
    artifact_files = list(set(artifact_files))

    for (dpath, _, fnames) in os.walk(csar_dir):
        if not fnames:
            continue
        for fname in fnames:
            src_file = os.path.join(dpath, fname)
            dst_file = os.path.relpath(os.path.join(dpath, fname), csar_dir)
            if fname.endswith('.yaml') or fname.endswith('.yml'):
                if dst_file not in artifact_files:
                    with open(src_file, 'rb') as yfile:
                        data = yaml.safe_load(yfile)
                        _update_unique_id_in_yaml(data, unique_id)
                        zcsar.writestr(dst_file, yaml.dump(
                            data, default_flow_style=False,
                            allow_unicode=True))
                else:
                    zcsar.write(src_file, dst_file)
            else:
                zcsar.write(src_file, dst_file)

    for (dpath, _, fnames) in os.walk(common_dir):
        if not fnames:
            continue
        for fname in fnames:
            src_file = os.path.join(dpath, fname)
            dst_file = os.path.relpath(os.path.join(dpath, fname), common_dir)
            zcsar.write(src_file, dst_file)

    zcsar.close()
    return tempname, unique_id


def create_csar_with_unique_artifact(csar_dir):
    unique_id = uuidutils.generate_uuid()
    tempfd, tempname = tempfile.mkstemp(suffix=".zip",
                                        dir=os.path.dirname(csar_dir))
    os.close(tempfd)
    common_artifact_dir = os.path.join(csar_dir, '../common_artifact')
    common_dir = os.path.join(csar_dir, '../common')
    zcsar = zipfile.ZipFile(tempname, 'w')

    artifact_files = []
    for (dpath, _, fnames) in os.walk(csar_dir):
        if not fnames:
            continue
        for fname in fnames:
            if fname == 'TOSCA.meta' or fname.endswith('.mf'):
                src_file = os.path.join(dpath, fname)
                with open(src_file, 'rb') as f:
                    artifacts_data = f.read()
                artifacts_data_split = re.split(b'\n\n+', artifacts_data)
                for data in artifacts_data_split:
                    if re.findall(b".?Algorithm:.?", data) and\
                            re.findall(b".?Hash:.?", data):
                        artifact_data_dict = yaml.safe_load(data)
                        artifact_files.append(
                            artifact_data_dict['Source']
                            if 'Source' in artifact_data_dict.keys()
                            else artifact_data_dict['Name'])
    artifact_files = list(set(artifact_files))

    for (dpath, _, fnames) in os.walk(common_artifact_dir):
        if not fnames:
            continue
        for fname in fnames:
            src_file = os.path.join(dpath, fname)
            dst_file = os.path.relpath(
                os.path.join(dpath, fname), common_artifact_dir)
            if fname.endswith('.yaml') or fname.endswith('.yml'):
                if dst_file not in artifact_files:
                    with open(src_file, 'rb') as yfile:
                        data = yaml.safe_load(yfile)
                        _update_unique_id_in_yaml(data, unique_id)
                        zcsar.writestr(dst_file, yaml.dump(
                            data, default_flow_style=False,
                            allow_unicode=True))
                else:
                    zcsar.write(src_file, dst_file)
            else:
                zcsar.write(src_file, dst_file)

    for (dpath, _, fnames) in os.walk(csar_dir):
        if not fnames:
            continue
        for fname in fnames:
            src_file = os.path.join(dpath, fname)
            dst_file = os.path.relpath(os.path.join(dpath, fname), csar_dir)
            zcsar.write(src_file, dst_file)

    for (dpath, _, fnames) in os.walk(common_dir):
        if not fnames:
            continue
        if ('vnf_instance' in csar_dir and 'kubernetes' in dpath) or \
                ('vnf_instance' in csar_dir and 'Scripts' in dpath):
            continue
        for fname in fnames:
            src_file = os.path.join(dpath, fname)
            dst_file = os.path.relpath(os.path.join(dpath, fname), common_dir)
            zcsar.write(src_file, dst_file)

    zcsar.close()

    return tempname


def copy_csar_files(fake_csar_path, csar_dir_name,
                    csar_without_tosca_meta=False, read_vnfd_only=False):
    """Copy csar directory to temporary directory

    :param fake_csar_path: a temporary directory in which csar data will be
                           copied.
    :param csar_dir_name: the relative path of csar directory with respect to
                          './tacker/tests/etc/samples/etsi/nfv' directory.
                          for ex. 'vnfpkgm1'.
    :param csar_without_tosca_meta: when set to 'True', it will only copy root
                                    level yaml file and image file.
    :param read_vnfd_only: when set to 'True', it won't copy the image file
                           from source directory.
    """
    sample_vnf_package = os.path.join(
        "./tacker/tests/etc/samples/etsi/nfv", csar_dir_name)
    shutil.copytree(sample_vnf_package, fake_csar_path)
    common_files_path = os.path.join(
        "./tacker/tests/etc/samples/etsi/nfv/common/")

    if not read_vnfd_only:
        # Copying image file.
        shutil.copytree(os.path.join(common_files_path, "Files/"),
                        os.path.join(fake_csar_path, "Files/"))

    if csar_without_tosca_meta:
        return

    # Copying common vnfd files.
    tosca_definition_file_path = os.path.join(common_files_path,
                                              "Definitions/")
    for (dpath, _, fnames) in os.walk(tosca_definition_file_path):
        if not fnames:
            continue
        for fname in fnames:
            src_file = os.path.join(dpath, fname)
            shutil.copy(src_file, os.path.join(fake_csar_path,
                                               "Definitions"))


def copy_artifact_files(fake_csar_path, csar_dir_name,
                    csar_without_tosca_meta=False, read_vnfd_only=False):
    sample_vnf_package = os.path.join(
        "./tacker/tests/etc/samples/etsi/nfv", csar_dir_name)
    shutil.copytree(sample_vnf_package, fake_csar_path)
    common_files_path = os.path.join(
        "./tacker/tests/etc/samples/etsi/nfv/")

    if not read_vnfd_only:
        # Copying image file.
        shutil.copytree(os.path.join(common_files_path, "Files/"),
                        os.path.join(fake_csar_path, "Files/"))
        shutil.copytree(os.path.join(common_files_path, "Scripts/"),
                        os.path.join(fake_csar_path, "Scripts/"))

    if csar_without_tosca_meta:
        return

    # Copying common vnfd files.
    tosca_definition_file_paths = [
        os.path.join(common_files_path, "common_artifact/Definitions/"),
        os.path.join(common_files_path, "common/Definitions/")
    ]
    for tosca_definition_file_path in tosca_definition_file_paths:
        for (dpath, _, fnames) in os.walk(tosca_definition_file_path):
            if not fnames:
                continue
            for fname in fnames:
                src_file = os.path.join(dpath, fname)
                if not os.path.exists(os.path.join(
                        fake_csar_path, "Definitions")):
                    os.mkdir(os.path.join(fake_csar_path, "Definitions"))
                os.mknod(os.path.join(fake_csar_path, "Definitions", fname))
                shutil.copyfile(src_file, os.path.join(
                    fake_csar_path, "Definitions", fname))


class AuthHandler(http.server.SimpleHTTPRequestHandler):
    '''Main class to present webpages and authentication.'''

    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"Test\"')
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

    def do_GET(self):
        '''Present frontpage with user authentication.'''
        global key
        if 'Authorization' not in self.headers:
            http.server.SimpleHTTPRequestHandler.do_GET(self)
        elif self.headers.get('Authorization') is None:
            self.do_AUTHHEAD()
            self.wfile.write(bytes('no auth header received'))
        elif self.headers.get('Authorization') == 'Basic ' + base64.b64encode(
                b"username:password").decode("utf-8"):
            http.server.SimpleHTTPRequestHandler.do_GET(self)
        else:
            self.do_AUTHHEAD()
            self.wfile.write(bytes(self.headers.get('Authorization')))
            self.wfile.write(bytes('not authenticated'))


class StaticHttpFileHandler(object):

    def __init__(self, static_files_path):
        if os.path.isabs(static_files_path):
            web_dir = static_files_path
        else:
            web_dir = os.path.join(os.path.dirname(__file__),
                static_files_path)
        os.chdir(web_dir)
        server_address = ('127.0.0.1', 0)
        self.httpd = socketserver.TCPServer(server_address, AuthHandler)
        self.port = self.httpd.socket.getsockname()[1]

        thread = threading.Thread(target=self.httpd.serve_forever)
        thread.daemon = True
        thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
