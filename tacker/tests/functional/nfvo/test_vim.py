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

from tacker.tests.functional import base
from tacker.tests.utils import read_file

import yaml


class VimTestCreate(base.BaseTackerTest):
    def _test_create_delete_vim(self, vim_file, name,
                                description, vim_type):
        data = dict()
        data = yaml.load(read_file(vim_file))

        password = data['password']
        username = data['username']
        project_name = data['project_name']
        auth_url = data['auth_url']
        vim_arg = {'vim': {'name': name, 'description': description,
                           'type': vim_type,
                           'auth_url': auth_url,
                           'auth_cred': {'username': username,
                                         'password': password},
                           'vim_project': {'name': project_name}}}

        # Register vim
        vim_instance = self.client.create_vim(vim_arg)
        vim_id = vim_instance['vim']['id']
        self.verify_vim(vim_instance, data, name, description)

        # Read vim
        vim_instance_show = self.client.show_vim(vim_id)
        self.verify_vim(vim_instance_show, data, name, description)

        # Delete vim
        try:
            self.client.delete_vim(vim_id)
        except Exception:
            assert False, ("Failed to delete vim %s" %
                           vim_id)

    def test_create_delete_local_vim(self):
        name = 'Default vim'
        description = 'Local vim description'
        vim_type = 'openstack'
        self._test_create_delete_vim(
            'local-vim.yaml', name, description, vim_type)
