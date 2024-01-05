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

import hashlib
from itertools import chain
import os
import re
import tempfile
import time
import yaml
import zipfile

from glanceclient.v2 import client as glance_client
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client as ks_client
from oslo_serialization import jsonutils
from oslo_utils import uuidutils
from tackerclient.v1_0 import client as tacker_client

from tacker.common import utils
from tacker.objects import fields
from tacker.tests.functional import base
from tacker.tests.functional.base import BaseTackerTest
from tacker.tests.functional.sol.vnflcm import base as vnflcm_base
from tacker.tests.functional.sol.vnflcm import fake_vnflcm
from tacker.tests.utils import _update_unique_id_in_yaml
from tacker.tests.utils import read_file
from tacker.tests.utils import test_etc_sample


class BaseEnhancedPolicyTest(object):

    TK_CLIENT_NAME = 'tk_client_%(username)s'
    TK_HTTP_CLIENT_NAME = 'tk_http_client_%(username)s'
    local_vim_conf_file = 'local-vim.yaml'
    base_subscriptions_url = "/vnflcm/v1/subscriptions"
    vim_base_url = "/v1.0/vims"
    pkg_base_url = '/vnfpkgm/v1/vnf_packages'
    user_role_map = {}
    vim_user_project_map = {}

    @classmethod
    def setUpClass(cls, subclass_with_maps):
        cls.user_role_map = subclass_with_maps.user_role_map
        cls.vim_user_project_map = subclass_with_maps.vim_user_project_map
        cls.ks_client = cls.keystone_client()
        cls.project = cls._get_project()
        cls._create_project()
        cls._create_user_role()
        cls.create_tacker_http_client_for_user()
        cls.cleanup_list = []
        cls.images_to_delete = []

    @classmethod
    def create_tacker_http_client_for_user(cls):
        for user in cls.users:
            client = cls.get_tacker_client_for_user(user)
            setattr(cls,
                    cls.TK_CLIENT_NAME % {'username': user.name}, client)
            http_client = cls.get_tacker_http_client_for_user(user)
            setattr(cls,
                    cls.TK_HTTP_CLIENT_NAME % {'username': user.name},
                    http_client)

    @classmethod
    def tearDownClass(cls):
        cls._delete_image()
        cls._delete_user_role()
        cls._delete_project()

    @classmethod
    def keystone_client(cls):
        auth_session = base.BaseTackerTest.get_auth_session(
            vim_conf_file=cls.local_vim_conf_file)
        keystone = ks_client.Client(session=auth_session)
        return keystone

    @classmethod
    def _step_pkg_create(cls, username):
        client = cls.get_tk_http_client_by_user(username)
        resp, pkg = client.do_request(
            cls.pkg_base_url, 'POST',
            body=jsonutils.dumps({"userDefinedData": {"foo": "bar"}}))
        if resp.status_code == 201:
            return pkg
        else:
            raise Exception('Failed to create package.')

    @classmethod
    def _wait_for_onboard(cls, client, package_uuid):
        show_url = os.path.join(cls.pkg_base_url, package_uuid)
        timeout = vnflcm_base.VNF_PACKAGE_UPLOAD_TIMEOUT
        start_time = int(time.time())
        while True:
            resp, body = client.do_request(show_url, "GET")

            if body['onboardingState'] == "ONBOARDED":
                break

            if (int(time.time()) - start_time) > timeout:
                raise Exception("Failed to onboard vnf package")

            time.sleep(1)

    @classmethod
    def _step_pkg_upload_content(cls, username, pkg, csar_name, provider,
                                 namespace=None):
        client = cls.get_tk_http_client_by_user(username)
        csar_dir = cls._get_csar_dir_path(csar_name)

        file_path, vnfd_id = cls.custom_csar(csar_dir, provider,
                                             namespace=namespace)
        cls.addClassCleanup(os.remove, file_path)

        with open(file_path, 'rb') as file_object:
            resp, _ = client.do_request(
                '{base_path}/{id}/package_content'.format(
                    id=pkg['id'],
                    base_path=cls.pkg_base_url),
                "PUT", body=file_object, content_type='application/zip')
        if resp.status_code == 202:
            cls._wait_for_onboard(client, pkg['id'])
        else:
            raise Exception('Failed to upload content.')

        return vnfd_id

    @classmethod
    def _step_pkg_disable(cls, username, pkg):
        client = cls.get_tk_http_client_by_user(username)
        update_req_body = jsonutils.dumps({
            "operationalState": "DISABLED"})
        resp, _ = client.do_request(
            '{base_path}/{id}'.format(id=pkg['id'],
                                      base_path=cls.pkg_base_url),
            "PATCH", content_type='application/json', body=update_req_body)
        if resp.status_code != 200:
            raise Exception('Failed to disable package.')

    @classmethod
    def _step_pkg_delete(cls, username, pkg):
        client = cls.get_tk_http_client_by_user(username)
        resp, _ = client.do_request(
            os.path.join(cls.pkg_base_url, pkg.get('id')),
            'DELETE')
        if resp.status_code != 204:
            raise Exception('Failed to delete package.')

    @classmethod
    def _create_project(cls):
        cls.projects = []
        if cls.vim_user_project_map:
            # create project
            projects = cls.ks_client.projects.list()
            project_names = [project.name for project in projects]
            projects_to_create = [
                project_name
                for project_name in cls.vim_user_project_map.values()
                if project_name not in project_names]
            if projects_to_create:
                for project_name in set(projects_to_create):
                    project = cls.ks_client.projects.create(project_name,
                                                            'default')
                    cls.projects.append(project)

    @classmethod
    def _get_project(cls, project_name=None):
        if not project_name:
            vim_params = base.BaseTackerTest.get_credentials(
                cls.local_vim_conf_file)
            project_name = vim_params['project_name']
        projects = cls.ks_client.projects.list()
        for project in projects:
            if project.name == project_name:
                return project
        else:
            raise Exception('project not found.')

    @classmethod
    def _delete_project(cls):
        if cls.projects:
            for project in cls.projects:
                cls.ks_client.projects.delete(project.id)

    @classmethod
    def _get_user_by_name(cls, name):
        for user in cls.users:
            if user.name == name:
                return user
        else:
            raise Exception(f'user {name} not found.')

    @classmethod
    def _create_user_role(cls):
        if cls.user_role_map:
            user_role_map = cls.user_role_map
        else:
            raise Exception('user_role_map is needed.')
        # create user
        users_to_create = user_role_map.keys()
        users = cls.ks_client.users.list()
        usernames = [user.name for user in users]
        users_to_create = set(users_to_create) - set(usernames)
        project_id = cls.project.id
        password = 'devstack'
        cls.users = []
        for username in users_to_create:
            user = cls.ks_client.users.create(
                username,
                project=project_id,
                password=password
            )
            cls.users.append(user)
        username_exists = set(usernames) & user_role_map.keys()
        for user in users:
            if user.name in username_exists:
                cls.users.append(user)

        # create roles
        roles_to_create = set(chain(*user_role_map.values()))
        cls._create_roles(roles_to_create)

        for username, roles in user_role_map.items():
            for role in roles:
                cls.ks_client.roles.grant(
                    cls.role_map.get(role.lower()),
                    user=cls._get_user_by_name(username),
                    project=cls.project.id
                )

    @classmethod
    def create_vim_user(cls):
        if cls.vim_user_project_map:
            vim_user_project_map = cls.vim_user_project_map
        else:
            raise Exception('vim_user_project_map is needed.')
        users = cls.ks_client.users.list()
        usernames = [user.name for user in users]
        projects = cls.ks_client.projects.list()
        password = 'devstack'
        for username in vim_user_project_map.keys():
            vim_username = f'vim_{username}'
            if vim_username in usernames:
                # already exist
                continue
            project_name = vim_user_project_map[username]
            project_id = [project.id for project in projects
                          if project_name == project.name][0]
            user = cls.ks_client.users.create(
                vim_username, project=project_id, password=password)
            cls.users.append(user)
            # add member role to vim users
            cls.ks_client.roles.grant(
                cls.role_map.get('member'),
                user=cls._get_user_by_name(vim_username),
                project=project_id
            )

    @classmethod
    def _create_role(cls, role_name):
        role = cls.ks_client.roles.create(role_name)
        return role

    @classmethod
    def _create_roles(cls, role_names):
        roles = cls.ks_client.roles.list()
        role_map = {role.name.lower(): role for role in roles}

        for role_name in role_names:
            if role_name.lower() not in role_map:
                role = cls._create_role(role_name)
                role_map[role_name.lower()] = role

        cls.role_map = role_map
        cls.roles_to_delete = [
            role_map[role_name.lower()] for role_name in role_names]

    @classmethod
    def _delete_user_role(cls):
        for user in cls.users:
            cls.ks_client.users.delete(user)

    @classmethod
    def _get_auth_session_for_user(cls, user):
        vim_params = base.BaseTackerTest.get_credentials(
            cls.local_vim_conf_file)
        auth = v3.Password(
            auth_url=vim_params['auth_url'],
            username=user.name,
            password='devstack',
            project_name=cls.project.name,
            user_domain_name=vim_params['user_domain_name'],
            project_domain_name=vim_params['project_domain_name'])
        verify = utils.str_to_bool(vim_params.pop('cert_verify', 'False'))
        auth_ses = session.Session(auth=auth, verify=verify)
        return auth_ses

    @classmethod
    def get_tacker_client_for_user(cls, user):
        return tacker_client.Client(
            session=cls._get_auth_session_for_user(user), retries=5)

    @classmethod
    def get_tacker_http_client_for_user(cls, user):
        return base.SessionClient(
            session=cls._get_auth_session_for_user(user),
            service_type='nfv-orchestration',
            region_name='RegionOne')

    @classmethod
    def get_tk_http_client_by_user(cls, username):
        return getattr(cls, cls.TK_HTTP_CLIENT_NAME % {'username': username})

    @classmethod
    def register_vim(cls, client, url, vim_file, name, description, vim_type,
                     extra, is_default=False, username=None, tenant=None):
        base_data = yaml.safe_load(read_file(vim_file))
        if vim_type == 'openstack':
            username = f'vim_{username}' if username else base_data['username']
            auth_cred = {
                'username': username,
                'password': base_data['password'],
                'user_domain_name': base_data['user_domain_name']
            }
        elif vim_type == 'kubernetes':
            auth_cred = {'bearer_token': base_data['bearer_token']}
        else:
            raise Exception(f'unknown vim type: {vim_type}.')
        vim_project = {
            'name': tenant if tenant else base_data['project_name'],
        }
        if 'project_domain_name' in base_data:
            vim_project['project_domain_name'] = (
                base_data['project_domain_name'])
        vim_req = {
            'vim': {
                'name': name,
                'description': description,
                'type': vim_type,
                'auth_url': base_data['auth_url'],
                'auth_cred': auth_cred,
                'vim_project': vim_project,
                'is_default': is_default
            }
        }
        if extra:
            vim_req['vim'].update({'extra': extra})
        resp, body = client.do_request(
            url, 'POST', body=jsonutils.dumps(vim_req)
        )
        return resp, body

    @classmethod
    def _update_provider_in_yaml(cls, data, provider):
        try:
            prop = data['topology_template']['node_templates']['VNF'][
                'properties']
            if prop.get('provider', None):
                prop['provider'] = provider
        except KeyError:
            # Let's check for 'node_types'
            pass

        if not data.get('node_types', None):
            return

        for ntype in data['node_types'].values():
            if ntype['derived_from'] != 'tosca.nodes.nfv.VNF':
                continue
            try:
                desc_id = ntype['properties']['provider']
                if desc_id.get('constraints', None):
                    for constraint in desc_id.get('constraints'):
                        if constraint.get('valid_values', None):
                            constraint['valid_values'] = [provider]
                if desc_id.get('default', None):
                    desc_id['default'] = provider
            except KeyError:
                # Let's check next node_type
                pass

    @classmethod
    def custom_csar(cls, csar_dir, provider, namespace=None):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csar_dir = os.path.join(current_dir, "../../", csar_dir)
        unique_id = uuidutils.generate_uuid()
        tempfd, tempname = tempfile.mkstemp(suffix=".zip",
                                            dir=os.path.dirname(csar_dir))
        os.close(tempfd)
        common_dir = os.path.join(csar_dir, "../common/")
        zcsar = zipfile.ZipFile(tempname, 'w')

        namespace_file = None
        if namespace:
            src_file = os.path.join(
                csar_dir, "Files", "kubernetes", "namespace.yaml")
            dst_file = os.path.join("Files", "kubernetes", "namespace.yaml")
            namespace_file = dst_file
            with open(src_file, 'r') as f:
                data = yaml.safe_load(f)
            data["metadata"]["name"] = namespace
            ns_str = yaml.dump(
                data, default_flow_style=False,
                allow_unicode=True)
            hash_value = hashlib.sha256(ns_str.encode()).hexdigest()
            zcsar.writestr(dst_file, ns_str)

        tosca_file = None
        artifact_files = []
        for (dpath, _, fnames) in os.walk(csar_dir):
            if not fnames:
                continue
            for fname in fnames:
                if fname == 'TOSCA.meta' or fname.endswith('.mf'):
                    src_file = os.path.join(dpath, fname)
                    tosca_file = src_file
                    with open(src_file, 'rb') as f:
                        artifacts_data = f.read()
                    artifacts_data_split = re.split(b'\n\n+', artifacts_data)
                    artifact_data_strs = []
                    for data in artifacts_data_split:

                        artifact_data_dict = yaml.safe_load(data)
                        if re.findall(b'.?Algorithm:.?|.?Hash:.?', data):
                            artifact_file = (artifact_data_dict['Source']
                                if 'Source' in artifact_data_dict.keys()
                                else artifact_data_dict['Name'])
                            if (namespace_file and
                                    artifact_file.endswith('namespace.yaml')):
                                artifact_data_dict['Hash'] = hash_value
                            artifact_files.append(artifact_file)
                        artifact_data_strs.append(
                            yaml.dump(artifact_data_dict,
                                      default_flow_style=False,
                                      allow_unicode=True))

                    if namespace_file:
                        dst_file = os.path.relpath(
                            os.path.join(dpath, fname), csar_dir)
                        zcsar.writestr(dst_file, '\n'.join(artifact_data_strs))

        artifact_files = list(set(artifact_files))

        for (dpath, _, fnames) in os.walk(csar_dir):
            if not fnames:
                continue
            for fname in fnames:
                src_file = os.path.join(dpath, fname)
                dst_file = os.path.relpath(
                    os.path.join(dpath, fname), csar_dir)

                if (namespace_file and tosca_file and
                        src_file.endswith(tosca_file)):
                    continue
                if fname.endswith('.yaml') or fname.endswith('.yml'):
                    if dst_file not in artifact_files:
                        with open(src_file, 'rb') as yfile:
                            data = yaml.safe_load(yfile)
                            _update_unique_id_in_yaml(data, unique_id)
                            cls._update_provider_in_yaml(data, provider)
                            zcsar.writestr(dst_file, yaml.dump(
                                data, default_flow_style=False,
                                allow_unicode=True))
                    else:
                        if not dst_file.endswith('namespace.yaml'):
                            zcsar.write(src_file, dst_file)
                else:
                    zcsar.write(src_file, dst_file)

        for (dpath, _, fnames) in os.walk(common_dir):
            if not fnames:
                continue
            if ('test_cnf' in csar_dir and
                    re.search('images|kubernetes|Scripts', dpath)):
                continue
            for fname in fnames:
                src_file = os.path.join(dpath, fname)
                dst_file = os.path.relpath(
                    os.path.join(dpath, fname), common_dir)
                zcsar.write(src_file, dst_file)

        zcsar.close()
        return tempname, unique_id

    @classmethod
    def _step_vim_register(
            cls, username, vim_type, local_vim, vim_name, area,
            is_default=False, tenant=None):
        extra = {}
        if area:
            extra = {'area': area}
        resp, body = cls.register_vim(
            cls.get_tk_http_client_by_user(username), cls.vim_base_url,
            local_vim, vim_name,
            "{}-{}".format(vim_name, uuidutils.generate_uuid()),
            vim_type, extra, is_default=is_default, username=username,
            tenant=tenant)
        if resp.status_code == 201:
            return body.get('vim')
        else:
            raise Exception('Failed to create vim.')

    @classmethod
    def _step_vim_delete(cls, username, vim):
        client = cls.get_tk_http_client_by_user(username)
        resp, _ = client.do_request(
            os.path.join(cls.vim_base_url, vim.get('id')), 'DELETE')
        if resp.status_code != 204:
            raise Exception('Failed to delete vim.')

    @classmethod
    def _get_csar_dir_path(cls, csar_name):
        return test_etc_sample("etsi/nfv", csar_name)

    @classmethod
    def _glance_client(cls, username=None, tenant=None):
        vim_params = base.BaseTackerTest.get_credentials()
        auth = v3.Password(auth_url=vim_params['auth_url'],
            username=username if username else vim_params['username'],
            password=vim_params['password'],
            project_name=tenant if tenant else vim_params['project_name'],
            user_domain_name=vim_params['user_domain_name'],
            project_domain_name=vim_params['project_domain_name'])
        verify = 'True' == vim_params.pop('cert_verify', 'False')
        auth_ses = session.Session(auth=auth, verify=verify)
        return glance_client.Client(session=auth_ses)

    @classmethod
    def create_image(cls):
        if cls.vim_user_project_map:
            vim_user_project_map = cls.vim_user_project_map
        else:
            raise Exception('vim_user_project_map is needed.')
        image_name = "cirros-0.5.2-x86_64-disk"
        image_path = test_etc_sample("nfv/common/Files/images",
                                     f"{image_name}.img")
        image_data = {
            'disk_format': 'qcow2',
            'container_format': 'bare',
            'visibility': 'private',
            'name': image_name}
        for username, projectname in vim_user_project_map.items():
            glance_client = cls._glance_client(username=f'vim_{username}',
                                               tenant=projectname)
            images = glance_client.images.list()
            images = list(filter(
                lambda image: image.name == image_name, images))
            if not images:
                image = glance_client.images.create(**image_data)
                with open(image_path, 'rb') as f:
                    glance_client.images.upload(image.id, f)
                cls.images_to_delete.append(image)

    @classmethod
    def _delete_image(cls):
        if not cls.images_to_delete:
            return
        glance_client = cls._glance_client()
        for image in cls.images_to_delete:
            glance_client.images.delete(image.id)

    def _register_subscription(self, request_body, http_client=None):
        if http_client is None:
            http_client = self.http_client
        resp, response_body = http_client.do_request(
            self.base_subscriptions_url,
            "POST",
            body=jsonutils.dumps(request_body))
        return resp, response_body

    def register_subscription(self):
        client = self.get_tk_http_client_by_user('user_all')

        callback_url = os.path.join(vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
                                    self._testMethodName)
        request_body = fake_vnflcm.Subscription.make_create_request_body(
            'http://localhost:{}{}'.format(
                vnflcm_base.FAKE_SERVER_MANAGER.SERVER_PORT,
                callback_url))
        resp, response_body = self._register_subscription(
            request_body, http_client=client)
        self.assertEqual(201, resp.status_code)
        self.assert_http_header_location_for_subscription(resp.headers)
        self.assert_notification_get(callback_url)
        subscription_id = response_body.get('id')
        self.addCleanup(
            self._delete_subscription, subscription_id, tacker_client=client)

    def create_port(self, neutron_client, network_id):
        body = {'port': {'network_id': network_id}}
        port = neutron_client.create_port(body=body)["port"]
        self.addCleanup(neutron_client.delete_port, port['id'])
        return port['id']

    def create_network(self, neutron_client, network_name):
        net = neutron_client.create_network(
            {'network': {'name': "network-%s" % uuidutils.generate_uuid()}})
        net_id = net['network']['id']
        self.addCleanup(neutron_client.delete_network, net_id)
        return net_id


class VimAPIsTest(BaseTackerTest, BaseEnhancedPolicyTest):

    base_url = "/v1.0/vims"
    user_role_map = {
        'user_a': ['AREA_area_A@region_A', 'manager'],
        'user_b': ['AREA_area_B@region_B', 'manager'],
        'user_c': ['AREA_all@all', 'manager'],
        'user_all': ['AREA_all@all', 'manager'],
        'user_admin': ['admin']
    }

    @classmethod
    def setUpClass(cls):
        BaseTackerTest.setUpClass()
        BaseEnhancedPolicyTest.setUpClass(cls)

    @classmethod
    def tearDownClass(cls):
        BaseEnhancedPolicyTest.tearDownClass()
        BaseTackerTest.tearDownClass()

    def _step_vim_register(self, username, vim_type, local_vim, vim_name, area,
                           expected_status_code):
        extra = {}
        if area:
            extra = {'area': area}
        resp, body = self.register_vim(
            self.get_tk_http_client_by_user(username), self.base_url,
            local_vim, vim_name,
            "{}-{}".format(vim_name, uuidutils.generate_uuid()),
            vim_type, extra)
        vim = body.get('vim')
        self.assertEqual(expected_status_code, resp.status_code)
        self.assertEqual(extra.get('area'), vim.get('extra', {}).get('area'))
        return vim

    def _step_vim_delete(self, username, vim, expected_status_code):
        client = self.get_tk_http_client_by_user(username)
        resp, _ = client.do_request(
            os.path.join(self.base_url, vim.get('id')), 'DELETE')
        self.assertEqual(expected_status_code, resp.status_code)

    def _step_vim_show(self, username, vim, expected_status_code):
        client = self.get_tk_http_client_by_user(username)
        resp, body = client.do_request(
            os.path.join(self.base_url, vim.get('id')), 'GET')
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code != 404:
            self.assertEqual(vim.get('extra', {}).get('area'),
                body.get('vim', {}).get('extra', {}).get('area'))

    def _step_vim_list(self, username, expected_vim_list):
        client = self.get_tk_http_client_by_user(username)
        resp, body = client.do_request(self.base_url, 'GET')
        self.assertEqual(200, resp.status_code)
        vim_ids = [vim.get('id') for vim in body.get('vims')]
        for vim in expected_vim_list:
            self.assertIn(vim['id'], vim_ids)

    def _step_vim_update(self, username, vim, expected_status_code):
        client = self.get_tk_http_client_by_user(username)
        req_body = {'vim': {'description': 'vim update'}}
        resp, body = client.do_request(
            os.path.join(self.base_url, vim.get('id')), 'PUT',
            body=jsonutils.dumps(req_body)
        )
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code != 404:
            self.assertEqual(vim.get('extra', {}).get('area'),
                body.get('vim', {}).get('extra', {}).get('area'))

    def _test_vim_apis_enhanced_policy(self, vim_type, local_vim):
        # step 1 VIM-Register, Resource Group A / User Group A
        vim_a = self._step_vim_register(
            'user_a', vim_type, local_vim, 'vim_a', 'area_A@region_A', 201)

        # step 2 VIM-Register, Resource Group B / User Group all
        vim_b = self._step_vim_register(
            'user_all', vim_type, local_vim, 'vim_b', 'area_B@region_B', 201)

        # step 3 VIM-Register, Resource Group C / User Group A
        vim_c = self._step_vim_register(
            'user_a', vim_type, local_vim, 'vim_c', None, 201)

        # step 4 VIM-Show Resource Group A / User Group A
        self._step_vim_show('user_a', vim_a, 200)

        # step 5 VIM-Show Resource Group B / User Group A
        self._step_vim_show('user_a', vim_b, 404)

        # step 6 VIM-Show Resource Group A / User Group all
        self._step_vim_show('user_all', vim_b, 200)

        # step 7 VIM-List Resource Group - / User Group A
        self._step_vim_list('user_a', [vim_a])

        # step 8 VIM-List Resource Group - / User Group B
        self._step_vim_list('user_b', [vim_b])

        # step 9 VIM-List Resource Group - / User Group all
        self._step_vim_list('user_all', [vim_a, vim_b])

        # step 10 VIM-Update Resource Group A - User Group A
        self._step_vim_update('user_a', vim_a, 200)

        # step 11 VIM-Update Resource Group B - User Group A
        self._step_vim_update('user_a', vim_b, 404)

        # step 12 VIM-Update Resource Group B - User Group all
        self._step_vim_update('user_all', vim_b, 200)

        # step 13 VIM-Delete, Resource Group A / User Group A
        self._step_vim_delete('user_a', vim_a, 204)

        # step 14 VIM-Delete, Resource Group B / User Group A
        self._step_vim_delete('user_a', vim_b, 404)

        # step 15 VIM-Delete, Resource Group B / User Group all
        self._step_vim_delete('user_all', vim_b, 204)

        # step 16 VIM-Delete, Resource Group C / User Group admin
        self._step_vim_delete('user_admin', vim_c, 204)

    def _test_vim_apis_vim_without_area_attribute(self, vim_type, local_vim):
        # step 1 VIM-Register, Resource Group C / User Group C
        vim_c = self._step_vim_register(
            'user_c', vim_type, local_vim, 'vim_c', None, 201)

        # step 2 VIM-Show Resource Group C / User Group C
        self._step_vim_show('user_c', vim_c, 404)

        # step 3 VIM-Show Resource Group C / User Group admin
        self._step_vim_show('user_admin', vim_c, 200)

        # step 4 VIM-List Resource Group - / User Group C
        self._step_vim_list('user_c', [])

        # step 5 VIM-List Resource Group - / User Group admin
        self._step_vim_list('user_admin', [vim_c])

        # step 6 VIM-Update Resource Group C - User Group C
        self._step_vim_update('user_c', vim_c, 404)

        # step 7 VIM-Update Resource Group C - User Group admin
        self._step_vim_update('user_admin', vim_c, 200)

        # step 8 VIM-Delete, Resource Group C / User Group C
        self._step_vim_delete('user_c', vim_c, 404)

        # step 9 VIM-Delete, Resource Group C / User Group admin
        self._step_vim_delete('user_admin', vim_c, 204)


class VnflcmAPIsV1Base(vnflcm_base.BaseVnfLcmTest, BaseEnhancedPolicyTest):

    @classmethod
    def setUpClass(cls):
        vnflcm_base.BaseVnfLcmTest.setUpClass()
        BaseEnhancedPolicyTest.setUpClass(cls)

    def setUp(self):
        super().setUp()

    @classmethod
    def tearDownClass(cls):
        BaseEnhancedPolicyTest.tearDownClass()
        vnflcm_base.BaseVnfLcmTest.tearDownClass()

    def _step_lcm_create(self, username, vnfd_id, vnf_instance_name,
                         expected_status_code):
        client = self.get_tk_http_client_by_user(username)

        request_body = {
            'vnfdId': vnfd_id,
            'vnfInstanceDescription': 'Sample VNF for LCM Testing',
            'vnfInstanceName':
                "{}-{}".format(self._testMethodName, vnf_instance_name)
        }
        resp, response_body = client.do_request(
            self.base_vnf_instances_url,
            "POST",
            body=jsonutils.dumps(request_body))
        self.assertEqual(expected_status_code, resp.status_code)
        return response_body.get('id')

    def _step_lcm_show(self, username, inst_id, expected_status_code):
        client = self.get_tk_http_client_by_user(username)
        show_url = os.path.join(self.base_vnf_instances_url, inst_id)
        resp, vnf_instance = client.do_request(show_url, "GET")
        self.assertEqual(expected_status_code, resp.status_code)

    def _step_lcm_list(self, username, expected_inst_list):
        client = self.get_tk_http_client_by_user(username)

        resp, vnf_instances = client.do_request(
            self.base_vnf_instances_url, "GET")

        self.assertEqual(200, resp.status_code)
        inst_ids = set([inst.get('id') for inst in vnf_instances])
        for inst_id in expected_inst_list:
            self.assertIn(inst_id, inst_ids)

    def _step_lcm_terminate(self, username, inst_id, expected_status_code):
        client = self.get_tk_http_client_by_user(username)

        terminate_req_body = {
            "terminationType": fields.VnfInstanceTerminationType.GRACEFUL,
            'gracefulTerminationTimeout': 60
        }
        url = os.path.join(self.base_vnf_instances_url, inst_id, "terminate")
        resp, body = client.do_request(url, "POST",
                                    body=jsonutils.dumps(terminate_req_body))
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(username, lcmocc_id)

    def _step_lcm_delete(self, username, inst_id, expected_status_code):
        client = self.get_tk_http_client_by_user(username)
        url = os.path.join(self.base_vnf_instances_url, inst_id)
        resp, _ = client.do_request(url, "DELETE")
        self.assertEqual(expected_status_code, resp.status_code)

    def _step_lcm_heal(self, username, inst_id, expected_status_code):
        client = self.get_tk_http_client_by_user(username)
        heal_req = {}
        url = os.path.join(self.base_vnf_instances_url, inst_id, "heal")
        resp, _ = client.do_request(
            url, "POST", body=jsonutils.dumps(heal_req))
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(username, lcmocc_id)

    def _step_lcm_scale(self, username, inst_id, request_body,
                        expected_status_code):
        client = self.get_tk_http_client_by_user(username)
        url = os.path.join(self.base_vnf_instances_url, inst_id, "scale")
        resp, _ = client.do_request(
            url, "POST", body=jsonutils.dumps(request_body))
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(username, lcmocc_id)

    def _lcm_instantiate(
            self, username, inst_id, request_body, expected_status_code):
        client = self.get_tk_http_client_by_user(username)
        url = os.path.join(self.base_vnf_instances_url, inst_id, "instantiate")
        resp, _ = client.do_request(
            url, "POST", body=jsonutils.dumps(request_body))
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(username, lcmocc_id)

    def wait_lcmocc_complete(self, username, lcmocc_id):
        # NOTE: It is not necessary to set timeout because the operation
        # itself set timeout and the state will become 'FAILED_TEMP'.
        client = self.get_tk_http_client_by_user(username)
        path = "/vnflcm/v1/vnf_lcm_op_occs/{}".format(lcmocc_id)
        while True:
            time.sleep(vnflcm_base.RETRY_WAIT_TIME)
            resp, body = client.do_request(
                path, "GET")
            self.assertEqual(200, resp.status_code)

            state = body['operationState']
            if state == 'COMPLETED':
                return
            elif state in ['STARTING', 'PROCESSING']:
                continue
            else:  # FAILED_TEMP or ROLLED_BACK
                raise Exception("Operation failed. state: %s" % state)

    def _wait_lcm_done(self,
            operation=None,
            vnf_lcm_op_occs=None,
            expected_operation_status=None,
            vnf_instance_id=None,
            fake_server_manager=None):
        if fake_server_manager is None:
            fake_server_manager = vnflcm_base.FAKE_SERVER_MANAGER
        start_time = int(time.time())
        callback_url = os.path.join(
            vnflcm_base.MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)

        while True:
            actual_status = None
            vnf_lcm_op_occ_id = None
            notify_mock_responses = fake_server_manager.get_history(
                callback_url)
            print(
                ("Wait:callback_url=<%s>, "
                "wait_operation=<%s>, "
                "wait_status=<%s>, "
                "vnf_instance_id=<%s>") %
                (callback_url, operation, expected_operation_status,
                 vnf_instance_id),
                flush=True)

            for res in notify_mock_responses:
                if (vnf_instance_id != res.request_body.get('vnfInstanceId')
                        and operation != res.request_body.get('operation')):
                    continue

                if expected_operation_status is None:
                    return
                actual_status = res.request_body.get('operationState', '')
                vnf_lcm_op_occ_id = res.request_body.get('vnfLcmOpOccId', '')
                if actual_status == expected_operation_status:
                    if operation:
                        if operation != res.request_body.get('operation'):
                            continue
                    if vnf_lcm_op_occs:
                        if (vnf_lcm_op_occs !=
                                res.request_body.get('vnfLcmOpOccId')):
                            continue
                    return
                elif actual_status == 'FAILED_TEMP':
                    error = (
                        "LCM incomplete timeout, %(vnf_lcm_op_occ_id)s"
                        " is %(actual)s,"
                        " expected status should be %(expected)s")
                    self.fail(
                        error % {
                            "vnf_lcm_op_occ_id": vnf_lcm_op_occ_id,
                            "expected": expected_operation_status,
                            "actual": actual_status})

            if ((int(time.time()) - start_time) >
                    vnflcm_base.VNF_LCM_DONE_TIMEOUT):
                if actual_status:
                    error = (
                        "LCM incomplete timeout, %(vnf_lcm_op_occ_id)s"
                        " is %(actual)s,"
                        " expected status should be %(expected)s")
                    self.fail(
                        error % {
                            "vnf_lcm_op_occ_id": vnf_lcm_op_occ_id,
                            "expected": expected_operation_status,
                            "actual": actual_status})
                else:
                    self.fail("LCM incomplete timeout")

            time.sleep(vnflcm_base.RETRY_WAIT_TIME)

    def _step_lcm_modify(self, username, inst_id, expected_status_code):
        client = self.get_tk_http_client_by_user(username)
        request_body = {
            "vnfInstanceName": "modify_{}".format(inst_id)
        }
        url = os.path.join(self.base_vnf_instances_url, inst_id)
        resp, body = client.do_request(url, "PATCH",
            body=jsonutils.dumps(request_body))
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(username, lcmocc_id)

    def steps_lcm_create_and_get_with_area(self):
        # step 1 LCM-Create, Resource Group A / User Group A
        inst_id_a = self._step_lcm_create(
            'user_a', self.vnfd_id_a, 'vnf_instance_a', 201)

        # step 2 LCM-Create, Resource Group B / User Group A
        self._step_lcm_create(
            'user_a', self.vnfd_id_b, 'vnf_instance_b', 403)

        # step 3 LCM-Create, Resource Group B / User Group all
        inst_id_b = self._step_lcm_create(
            'user_all', self.vnfd_id_b, 'vnf_instance_b', 201)

        # step 4 LCM-Show, Resource Group A / User Group A
        self._step_lcm_show('user_a', inst_id_a, 403)

        # step 5 LCM-Show, Resource Group A / User Group A-1
        self._step_lcm_show('user_a_1', inst_id_a, 403)

        # step 6 LCM-Show, Resource Group B / User Group A
        self._step_lcm_show('user_a', inst_id_b, 403)

        # step 7 LCM-Show, Resource Group B / User Group all
        self._step_lcm_show('user_all', inst_id_b, 403)

        # step 8 LCM-List, Resource Group - / User Group A
        self._step_lcm_list('user_a', [])

        # step 9 LCM-List, Resource Group - / User Group A-1
        self._step_lcm_list('user_a_1', [])

        # step 10 LCM-List, Resource Group - / User Group B
        self._step_lcm_list('user_b', [])

        # step 11 LCM-List, Resource Group - / User Group all
        self._step_lcm_list('user_all', [])

        return inst_id_a, inst_id_b

    def steps_lcm_get_scale_heal_modify_with_area(self, inst_id_a, inst_id_b):
        # step 15 LCM-Show, Resource Group A / User Group A
        self._step_lcm_show('user_a', inst_id_a, 200)

        # step 16 LCM-Show, Resource Group B / User Group A
        self._step_lcm_show('user_a', inst_id_b, 403)

        # step 17 LCM-Show, Resource Group B / User Group all
        self._step_lcm_show('user_all', inst_id_b, 200)

        # step 18 LCM-List, Resource Group - / User Group A
        self._step_lcm_list('user_a', [inst_id_a])

        # step 19 LCM-List, Resource Group - / User Group A-1
        self._step_lcm_list('user_a_1', [])

        # step 20 LCM-List, Resource Group - / User Group B
        self._step_lcm_list('user_b', [inst_id_b])

        # step 21 LCM-List, Resource Group - / User Group all
        self._step_lcm_list('user_all', [inst_id_a, inst_id_b])

        # step 22 LCM-Scale(out), Resource Group A / User Group A
        self._step_lcm_scale_out('user_a', inst_id_a, 202)

        # step 23 LCM-Scale(out), Resource Group B / User Group A
        self._step_lcm_scale_out('user_a', inst_id_b, 403)

        # step 24 LCM-Scale(out), Resource Group B / User Group all
        self._step_lcm_scale_out('user_all', inst_id_b, 202)

        # step 25 LCM-Scale(in), Resource Group A / User Group A
        self._step_lcm_scale_in('user_a', inst_id_a, 202)

        # step 26 LCM-Scale(in), Resource Group B / User Group A
        self._step_lcm_scale_in('user_a', inst_id_b, 403)

        # step 27 LCM-Scale(in), Resource Group B / User Group all
        self._step_lcm_scale_in('user_all', inst_id_b, 202)

        # step 28 LCM-Heal, Resource Group A / User Group A
        self._step_lcm_heal('user_a', inst_id_a, 202)

        # step 29 LCM-Heal, Resource Group B / User Group A
        self._step_lcm_heal('user_a', inst_id_b, 403)

        # step 30 LCM-Heal, Resource Group B / User Group all
        self._step_lcm_heal('user_all', inst_id_b, 202)

        # step 31 LCM-Modify, Resource Group A / User Group A
        self._step_lcm_modify('user_a', inst_id_a, 202)

        # step 32 LCM-Modify, Resource Group b / User Group A
        self._step_lcm_modify('user_a', inst_id_b, 403)

        # step 33 LCM-Modify, Resource Group B / User Group all
        self._step_lcm_modify('user_all', inst_id_b, 202)

    def steps_lcm_terminate_delete_with_area(self, inst_id_a, inst_id_b):
        # step 37 LCM-Terminate, Resource Group A / User Group A
        self._step_lcm_terminate('user_a', inst_id_a, 202)

        # step 38 LCM-Terminate, Resource Group B / User Group A
        self._step_lcm_terminate('user_a', inst_id_b, 403)

        # step 39 LCM-Terminate, Resource Group B / User Group A
        self._step_lcm_terminate('user_all', inst_id_b, 202)

        # step 40 LCM-Delete, Resource Group A / User Group A
        self._step_lcm_delete('user_a', inst_id_a, 204)

        # step 41 LCM-Delete, Resource Group B / User Group A
        self._step_lcm_delete('user_a', inst_id_b, 403)

        # step 42 LCM-Delete, Resource Group B / User Group A
        self._step_lcm_delete('user_all', inst_id_b, 204)

    def steps_lcm_create_and_get_without_area(self):
        # step 1 LCM-Create, Resource Group C / User Group C
        inst_id_c = self._step_lcm_create(
            'user_c', self.vnfd_id_c, 'vnf_instance_c', 201)

        # step 2 LCM-Show, Resource Group C / User Group C
        self._step_lcm_show('user_c', inst_id_c, 403)

        # step 3 LCM-Show, Resource Group C / User Group all
        self._step_lcm_show('user_all', inst_id_c, 403)

        # step 4 LCM-Show, Resource Group C / User Group admin
        self._step_lcm_show('user_admin', inst_id_c, 200)

        # step 5 LCM-List, Resource Group - / User Group C
        self._step_lcm_list('user_c', [])

        # step 6 LCM-List, Resource Group - / User Group all
        self._step_lcm_list('user_all', [])

        # step 7 LCM-List, Resource Group - / User Group admin
        self._step_lcm_list('user_admin', [inst_id_c])

        return inst_id_c

    def steps_lcm_get_scale_heal_modify_without_area(self, inst_id_c):
        # step 9 LCM-Show, Resource Group C / User Group C
        self._step_lcm_show('user_c', inst_id_c, 403)

        # step 10 LCM-Show, Resource Group C / User Group all
        self._step_lcm_show('user_all', inst_id_c, 403)

        # step 11 LCM-Show, Resource Group C / User Group admin
        self._step_lcm_show('user_admin', inst_id_c, 200)

        # step 12 LCM-List, Resource Group - / User Group C
        self._step_lcm_list('user_c', [])

        # step 13 LCM-List, Resource Group - / User Group all
        self._step_lcm_list('user_all', [])

        # step 14 LCM-List, Resource Group - / User Group admin
        self._step_lcm_list('user_admin', [inst_id_c])

        # step 15 LCM-Scale(out), Resource Group C / User Group C
        self._step_lcm_scale_out('user_c', inst_id_c, 403)

        # step 16 LCM-Scale(out), Resource Group C / User Group all
        self._step_lcm_scale_out('user_all', inst_id_c, 403)

        # step 17 LCM-Scale(out), Resource Group C / User Group admin
        self._step_lcm_scale_out('user_admin', inst_id_c, 202)

        # step 18 LCM-Scale(in), Resource Group C / User Group C
        self._step_lcm_scale_in('user_c', inst_id_c, 403)

        # step 19 LCM-Scale(in), Resource Group C / User Group all
        self._step_lcm_scale_in('user_all', inst_id_c, 403)

        # step 20 LCM-Scale(in), Resource Group C / User Group admin
        self._step_lcm_scale_in('user_admin', inst_id_c, 202)

        # step 21 LCM-Heal, Resource Group C / User Group C
        self._step_lcm_heal('user_c', inst_id_c, 403)

        # step 22 LCM-Heal, Resource Group C / User Group all
        self._step_lcm_heal('user_all', inst_id_c, 403)

        # step 23 LCM-Heal, Resource Group C / User Group admin
        self._step_lcm_heal('user_admin', inst_id_c, 202)

        # step 24 LCM-Modify, Resource Group C / User Group C
        self._step_lcm_modify('user_c', inst_id_c, 403)

        # step 25 LCM-Modify, Resource Group C / User Group all
        self._step_lcm_modify('user_all', inst_id_c, 403)

        # step 26 LCM-Modify, Resource Group C / User Group admin
        self._step_lcm_modify('user_admin', inst_id_c, 202)

    def steps_lcm_terminate_delete_without_area(self, inst_id_c):
        # step 30 LCM-Terminate, Resource Group C / User Group C
        self._step_lcm_terminate('user_c', inst_id_c, 403)

        # step 31 LCM-Terminate, Resource Group C / User Group all
        self._step_lcm_terminate('user_all', inst_id_c, 403)

        # step 32 LCM-Terminate, Resource Group C / User Group admin
        self._step_lcm_terminate('user_admin', inst_id_c, 202)

        # step 33 LCM-Delete, Resource Group C / User Group C
        self._step_lcm_delete('user_c', inst_id_c, 204)
