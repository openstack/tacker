# Copyright 2016 Brocade Communications System, Inc.
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

import time
import yaml

from tacker.plugins.common import constants as evt_constants
from tacker.tests.functional import base
from tacker.tests.utils import read_file

from tackerclient.common import exceptions

SECRET_PASSWORD = '***'


class VimTestCreate(base.BaseTackerTest):

    def _test_create_delete_vim(self, vim_file, name, description, vim_type,
                                version=None):

        data, vim_arg = self._generate_vim_data(
            'local-vim.yaml', name, description, vim_type, version)
        # updated args
        new_name = "fake %s" % name
        new_desc = "fake %s" % description
        update_vim_arg = {'vim': {'name': new_name,
                                  'description': new_desc}}

        # Register vim
        vim_res = self.client.create_vim(vim_arg)
        vim_obj = vim_res['vim']
        vim_id = vim_obj['id']
        self.verify_vim(vim_obj, data, name, description, version)
        self.verify_vim_events(vim_id, evt_constants.RES_EVT_CREATE)

        # Read vim
        vim_show_res = self.client.show_vim(vim_id)
        self.verify_vim(vim_show_res['vim'], data, name, description, version)

        # Update vim
        vim_update = self.client.update_vim(vim_id, update_vim_arg)
        vim_obj = vim_update['vim']
        self.verify_vim(vim_obj, data, new_name, new_desc, version)
        self.verify_vim_events(vim_id, evt_constants.RES_EVT_UPDATE)

        # With the updated name above, create another VIM with the
        # same name and check for Duplicate name exception.
        vim_arg['vim']['name'] = update_vim_arg['vim']['name']
        msg = "vim already exist with given ['tenant_id', 'name', "\
              "'deleted_at']"
        try:
            self.client.create_vim(vim_arg)
        except Exception as err:
            self.assertEqual(err.message, msg)

        # Since there already exists a DEFAULT VM, Verify that a update
        # to is_default to TRUE for another VIM raises an exception.
        update_arg = {'vim': {'is_default': True}}
        msg = "Default VIM already exists."
        self.assertRaisesRegex(exceptions.InternalServerError, msg,
                               self.client.update_vim,
                               vim_id, update_arg)

        # Delete vim
        try:
            self.client.delete_vim(vim_id)
        except Exception:
            self.assertFalse(True, "Failed to delete vim %s" % vim_id)
        self.verify_vim_events(vim_id, evt_constants.RES_EVT_DELETE)

    def verify_vim(self, vim_instance, config_data, name, description,
                   version):
        expected_regions = ['RegionOne']
        self.assertIsNotNone(vim_instance)
        self.assertEqual(description, vim_instance['description'])
        self.assertEqual(name, vim_instance['name'])
        self.assertIsNotNone(vim_instance['tenant_id'])
        self.assertIsNotNone(vim_instance['id'])
        self.assertEqual(config_data['username'],
                         vim_instance['auth_cred']['username'])
        self.assertEqual(SECRET_PASSWORD,
                         vim_instance['auth_cred']['password'])
        self.assertEqual(expected_regions,
                         vim_instance['placement_attr']['regions'])
        if version:
            method_name = 'verify_vim_' + version
            getattr(self, method_name)(vim_instance, config_data)

    def verify_vim_events(self, vim_id, evt_type, tstamp=None, cnt=1):
        params = {'resource_id': vim_id,
                  'resource_type': evt_constants.RES_TYPE_VIM,
                  'event_type': evt_type}
        if tstamp:
            params['timestamp'] = tstamp

        vim_evt_list = self.client.list_vim_events(**params)

        self.assertIsNotNone(vim_evt_list['vim_events'],
                             "List of VIM events are Empty")
        self.assertEqual(cnt, len(vim_evt_list['vim_events']))

    def verify_vim_v2(self, vim_instance, config_data):
        self.assertEqual(config_data['project_name'],
                         vim_instance['auth_cred']['tenant_name'])

    def verify_vim_v3(self, vim_instance, config_data):
        self.assertEqual(config_data['project_name'],
                         vim_instance['auth_cred']['project_name'])

    def test_create_delete_local_vim(self):
        name = 'Default vim'
        description = 'Local vim description'
        vim_type = 'openstack'
        ks_version = 'v3'
        self._test_create_delete_vim('local-vim.yaml', name, description,
                                     vim_type, ks_version)

    def _generate_vim_data(self, vim_file, name, description, vim_type,
                           version=None):

        data = yaml.safe_load(read_file(vim_file))
        password = data['password']
        username = data['username']
        project_name = data['project_name']
        auth_url = data['auth_url']
        if version:
            if ('v2' == version and (not auth_url.endswith("/v2.0") or
                                     not auth_url.endswith("/v2.0/"))):
                auth_url += "/v2.0"
            elif (not auth_url.endswith("/v3") or
                  not auth_url.endswith("/v3/")):
                auth_url += "/v3"
        domain_name = data.get('domain_name', None)
        vim_arg = {'vim': {'name': name, 'description': description,
                           'type': vim_type,
                           'auth_url': auth_url,
                           'auth_cred': {'username': username,
                                         'password': password,
                                         'user_domain_name': domain_name},
                           'vim_project': {'name': project_name,
                                           'project_domain_name':
                                               domain_name},
                           'is_default': False}}
        return data, vim_arg

    def test_re_create_delete_local_vim(self):
        name = 'test_vim'
        description = 'Test vim description'
        vim_type = 'openstack'
        ks_version = 'v3'
        self._test_create_delete_vim('local-vim.yaml', name, description,
                                     vim_type, ks_version)
        time.sleep(1)
        self._test_create_delete_vim('local-vim.yaml', name, description,
                                     vim_type, ks_version)

    def test_duplicate_vim(self):
        name = 'test_duplicate_vim'
        description = 'Test duplicate vim description'
        vim_type = 'openstack'
        version = 'v3'
        data, vim_arg = self._generate_vim_data(
            'local-vim.yaml', name, description, vim_type, version)

        # Register vim
        vim_res = self.client.create_vim(vim_arg)
        vim_obj = vim_res['vim']
        vim_id = vim_obj['id']

        # Read vim
        vim_show_res = self.client.show_vim(vim_id)
        self.verify_vim(vim_show_res['vim'], data, name, description, version)
        msg = "vim already exist with given ['tenant_id', 'name', "\
              "'deleted_at']"
        err_msg = None
        try:
            self.client.create_vim(vim_arg)
        except Exception as err:
            err_msg = err.message
        self.assertEqual(err_msg, msg)
