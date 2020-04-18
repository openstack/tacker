# Copyright (C) 2018 NTT DATA
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

from unittest import mock

import ddt
import six
from webob import exc

from tacker.api.v1 import base as v1_base
from tacker.extensions import nfvo
from tacker.nfvo import nfvo_plugin
from tacker.tests.unit import base
from tacker import wsgi


def get_vim_config():
    return {
        "vim": {
            "tenant_id": 'test-project',
            "type": "openstack",
            "auth_url": 'http://localhost/identity',
            "auth_cred": {
                "username": "test_user",
                "user_domain_name": "Default",
                "password": "password"
            },
            "vim_project": {
                "name": "test_project",
                "project_domain_name": "Default"
            },
            "name": "VIM1",
            "description": "Additional site",
            "is_default": False
        }
    }


@ddt.ddt
class VIMCreateTestCase(base.TestCase):

    def setUp(self):
        super(VIMCreateTestCase, self).setUp()
        plugin = nfvo_plugin.NfvoPlugin()
        resource_name = 'vim'
        collection_name = resource_name + "s"
        attribute_info = nfvo.RESOURCE_ATTRIBUTE_MAP[collection_name]
        self.controller = v1_base.Controller(plugin, collection_name,
                                        resource_name, attribute_info)

    def _vim_create_response(self):
        return {
            'auth_cred': {
                'auth_url': 'http://localhost/identity',
                'cert_verify': 'False',
                'key_type': 'barbican_key',
                'password': '***',
                'project_domain_name': 'Default',
                'project_id': None,
                'project_name': 'nfv',
                'secret_uuid': '***',
                'user_domain_name': 'Default',
                'username': 'test_user'
            },
            'auth_url': 'http://localhost/identity',
            'created_at': None,
            'description': 'Additional site',
            'id': '73493efe-3616-414c-bf87-bf450d0b3650',
            'is_default': False,
            'name': 'VIM1',
            'placement_attr': {
                'regions': [
                    'RegionOne'
                ]
            },
            'shared': False,
            'status': 'PENDING',
            'tenant_id': 'test-project',
            'type': 'openstack',
            'updated_at': None,
            'vim_project': {
                'name': 'test_project'
            }
        }

    @mock.patch.object(nfvo_plugin.NfvoPlugin, 'create_vim')
    def test_create_vim(self, mock_create_vim):
        vim_dict = get_vim_config()
        request = wsgi.Request.blank(
            "/vims.json", method='POST',
            headers={'Content-Type': "application/json"})
        request.environ['tacker.context'] = self.fake_admin_context()
        mock_create_vim.return_value = self._vim_create_response()

        result = self.controller.create(request, vim_dict)
        # End API response doesn't contain the 'shared' attribute so pop it
        # from dict
        resp_dict = self._vim_create_response()
        resp_dict.pop('shared')
        # Check whether VIM is created with the provided vim_details
        self.assertEqual(resp_dict, result['vim'])

    @ddt.data({'is_default': 'ABC'},
              {'is_default': 123},
              {'is_default': ''})
    def test_create_vim_with_invalid_is_default(self, value):
        vim_dict = get_vim_config()
        vim_dict['vim']['is_default'] = value
        request = wsgi.Request.blank("/vims.json", method='POST',
                  headers={'Content-Type': "application/json"})
        request.environ['tacker.context'] = self.fake_admin_context()
        msg = ("Invalid input for is_default. Reason: '%s' is not a "
               "valid boolean value." % vim_dict['vim']['is_default'])
        exp = self.assertRaises(exc.HTTPBadRequest,
                                self.controller.create,
                                request, vim_dict)
        self.assertEqual(msg, six.text_type(exp))

    @ddt.data("", " ", None, 123)
    def test_create_vim_with_invalid_type(self, value):
        vim_dict = get_vim_config()
        vim_dict['vim']['type'] = value
        request = wsgi.Request.blank("/vims.json", method='POST',
            headers={'Content-Type': "application/json"})
        request.environ['tacker.context'] = self.fake_admin_context()
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.create,
                          request, vim_dict)

    @ddt.data('', 'testing', {})
    def test_create_vim_with_invalid_auth_cred(self, value):
        vim_dict = get_vim_config()
        vim_dict['vim']['auth_cred'] = value
        request = wsgi.Request.blank("/vims.json", method='POST',
                headers={'Content-Type': "application/json"})
        request.environ['tacker.context'] = self.fake_admin_context()
        msg = ("Invalid input for auth_cred. Reason: '%s' is "
               "not a valid dictionary or it is an empty"
               " dictionary.") % vim_dict['vim']['auth_cred']
        exp = self.assertRaises(exc.HTTPBadRequest,
                                self.controller.create,
                                request, vim_dict)
        self.assertEqual(msg, six.text_type(exp))

    @ddt.data('', 'testing', {})
    def test_create_vim_invalid_vim_project(self, value):
        vim_dict = get_vim_config()
        vim_dict['vim']['vim_project'] = value
        request = wsgi.Request.blank("/vims.json", method='POST',
                headers={'Content-Type': "application/json"})
        request.environ['tacker.context'] = self.fake_admin_context()
        msg = ("Invalid input for vim_project. Reason: '%s' is"
               " not a valid dictionary or it is an empty"
               " dictionary.") % vim_dict['vim']['vim_project']
        exp = self.assertRaises(exc.HTTPBadRequest,
                                self.controller.create,
                                request, vim_dict)
        self.assertEqual(msg, six.text_type(exp))
