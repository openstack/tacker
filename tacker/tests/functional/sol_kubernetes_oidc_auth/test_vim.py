# Copyright (C) 2022 FUJITSU
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

import yaml

from tackerclient.common import exceptions

from tacker.tests.functional import base
from tacker.tests.utils import read_file

SECRET_PASSWORD = '***'


class VimTest(base.BaseTackerTest):

    @classmethod
    def generate_vim_info_oidc_for_creation(cls):

        data = yaml.safe_load(read_file('local-k8s-vim-oidc.yaml'))
        auth_cred = {'oidc_token_url': data['oidc_token_url'],
                     'username': data['username'],
                     'password': data['password'],
                     'client_id': data['client_id'],
                     'client_secret': data['client_secret']}
        if 'ssl_ca_cert' in data:
            auth_cred['ssl_ca_cert'] = data['ssl_ca_cert']
        return {'vim': {'name': 'VIM-OIDC-AUTH',
                        'description': 'Kubernetes VIM with oidc auth',
                        'type': 'kubernetes',
                        'auth_url': data['auth_url'],
                        'auth_cred': auth_cred,
                        'vim_project': {'name': 'default'},
                        'is_default': False}}

    @classmethod
    def generate_vim_info_oidc_for_update(cls):

        data = yaml.safe_load(read_file('local-k8s-vim-oidc.yaml'))
        auth_cred = {'oidc_token_url': data['oidc_token_url'],
                     'username': data['username'],
                     'password': data['password'],
                     'client_id': data['client_id'],
                     'client_secret': data['client_secret']}
        if 'ssl_ca_cert' in data:
            auth_cred['ssl_ca_cert'] = data['ssl_ca_cert']
        return {'vim': {'name': 'VIM-OIDC-AUTH',
                        'description': 'Kubernetes VIM with oidc auth',
                        'auth_cred': auth_cred}}

    @classmethod
    def generate_vim_info_token_for_update(cls):

        data = yaml.safe_load(read_file('local-k8s-vim.yaml'))
        auth_cred = {'bearer_token': data['bearer_token']}
        if 'ssl_ca_cert' in data:
            auth_cred['ssl_ca_cert'] = data['ssl_ca_cert']
        return {'vim': {'name': 'VIM-BEARER-TOKEN',
                        'description': 'Kubernetes VIM with bearer token',
                        'auth_cred': auth_cred}}

    def assert_vim_auth_oidc(self, vim_auth_req, vim_auth_res):
        unexpected_attrs = {'bearer_token'}
        # check only specified attributes exist
        self.assertNotIn(unexpected_attrs, vim_auth_res)
        self.assertEqual(vim_auth_req['oidc_token_url'],
                         vim_auth_res['oidc_token_url'])
        self.assertEqual(vim_auth_req['username'],
                         vim_auth_res['username'])
        self.assertEqual(SECRET_PASSWORD,
                         vim_auth_res['password'])
        self.assertEqual(vim_auth_req['client_id'],
                         vim_auth_res['client_id'])
        self.assertEqual(SECRET_PASSWORD,
                         vim_auth_res['client_secret'])

    def assert_vim_auth_token(self, vim_auth_res):
        unexpected_attrs = {'oidc_token_url', 'username', 'password',
                            'client_id', 'client_secret'}
        # check only specified attributes exist
        self.assertNotIn(unexpected_attrs, vim_auth_res)
        self.assertEqual(SECRET_PASSWORD,
                         vim_auth_res['bearer_token'])

    def test_vim_creation_update_with_oidc_auth(self):

        vim_oidc_create = self.generate_vim_info_oidc_for_creation()
        vim_oidc_update = self.generate_vim_info_oidc_for_update()
        vim_token_update = self.generate_vim_info_token_for_update()

        # Register vim
        vim_res = self.client.create_vim(vim_oidc_create)
        vim_id = vim_res['vim']['id']
        self.assert_vim_auth_oidc(vim_oidc_create['vim']['auth_cred'],
                                  vim_res['vim']['auth_cred'])
        # Read vim
        vim_show_res = self.client.show_vim(vim_id)
        self.assert_vim_auth_oidc(vim_oidc_create['vim']['auth_cred'],
                                  vim_show_res['vim']['auth_cred'])

        # Update vim (oidc -> token)
        vim_update = self.client.update_vim(vim_id, vim_token_update)
        self.assert_vim_auth_token(vim_update['vim']['auth_cred'])

        # Read vim
        vim_show_res = self.client.show_vim(vim_id)
        self.assert_vim_auth_token(vim_show_res['vim']['auth_cred'])

        # Update vim (token -> oidc)
        vim_update = self.client.update_vim(vim_id, vim_oidc_update)
        self.assert_vim_auth_oidc(vim_oidc_update['vim']['auth_cred'],
                                  vim_update['vim']['auth_cred'])

        # Read vim
        vim_show_res = self.client.show_vim(vim_id)
        self.assert_vim_auth_oidc(vim_oidc_update['vim']['auth_cred'],
                                  vim_show_res['vim']['auth_cred'])

        # Delete vim
        self.client.delete_vim(vim_id)

    def test_vim_creation_with_bad_oidc_auth_info(self):

        vim_oidc = self.generate_vim_info_oidc_for_creation()
        vim_oidc['vim']['auth_cred']['password'] = 'bad password'
        vim_oidc['vim']['auth_cred']['client_secret'] = 'bad secret'

        # Register vim
        exc = self.assertRaises(exceptions.InternalServerError,
                                self.client.create_vim,
                                vim_oidc)
        message = ('OIDC authentication and authorization failed. '
                   'Detail: response code: 401, body: '
                   '{"error":"unauthorized_client",'
                   '"error_description":"Invalid client secret"}')
        self.assertEqual(message, exc.message)
