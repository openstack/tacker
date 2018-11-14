# Copyright 2013 VMware, Inc
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

"""
Unit tests for extension extended attribute
"""

import webob.exc as webexc

import tacker
from tacker.api import extensions
from tacker.api.v1 import attributes
from tacker.common import config
from tacker import manager
from tacker.tests import base
from tacker.tests.unit.api.v2 import test_api_v2
from tacker.tests.unit.extensions import extendedattribute as extattr
from tacker.tests.unit import testlib_api
from tacker import wsgi

_uuid = test_api_v2._uuid
_get_path = test_api_v2._get_path
extensions_path = ':'.join(tacker.tests.unit.extensions.__path__)


class ExtensionExtendedAttributeTestCase(base.BaseTestCase):
    def setUp(self):
        super(ExtensionExtendedAttributeTestCase, self).setUp()
        self.skip("Not ready yet")
        plugin = (
            "tacker.tests.unit.test_extension_extended_attribute."
            "ExtensionExtendedAttributeTestPlugin"
        )

        # point config file to: tacker/tests/etc/tacker.conf.test
        self.config_parse()

        self.setup_coreplugin(plugin)

        ext_mgr = extensions.ExtensionManager(extensions_path)
        ext_mgr.extend_resources("1.0", {})
        extensions.ExtensionManager._instance = ext_mgr

        app = config.load_paste_app('extensions_test_app')
        self._api = extensions.ExtensionMiddleware(app, ext_mgr=ext_mgr)

        self._tenant_id = "8c70909f-b081-452d-872b-df48e6c355d1"
        # Save the global RESOURCE_ATTRIBUTE_MAP
        self.saved_attr_map = {}
        for resource, attrs in (attributes.RESOURCE_ATTRIBUTE_MAP).items():
            self.saved_attr_map[resource] = attrs.copy()
        # Add the resources to the global attribute map
        # This is done here as the setup process won't
        # initialize the main API router which extends
        # the global attribute map
        attributes.RESOURCE_ATTRIBUTE_MAP.update(
            extattr.EXTENDED_ATTRIBUTES_2_0)
        self.agentscheduler_dbMinxin = manager.TackerManager.get_plugin()
        self.addCleanup(self.restore_attribute_map)

    def restore_attribute_map(self):
        # Restore the original RESOURCE_ATTRIBUTE_MAP
        attributes.RESOURCE_ATTRIBUTE_MAP = self.saved_attr_map

    def _do_request(self, method, path, data=None, params=None, action=None):
        content_type = 'application/json'
        body = None
        if data is not None:  # empty dict is valid
            body = wsgi.Serializer().serialize(data, content_type)

        req = testlib_api.create_request(
            path, body, content_type,
            method, query_string=params)
        res = req.get_response(self._api)
        if res.status_code >= 400:
            raise webexc.HTTPClientError(detail=res.body, code=res.status_code)
        if res.status_code != webexc.HTTPNoContent.code:
            return res.json

    def _ext_test_resource_create(self, attr=None):
        data = {
            "ext_test_resource": {
                "tenant_id": self._tenant_id,
                "name": "test",
                extattr.EXTENDED_ATTRIBUTE: attr
            }
        }

        res = self._do_request('POST', _get_path('ext_test_resources'), data)
        return res['ext_test_resource']

    def test_ext_test_resource_create(self):
        ext_test_resource = self._ext_test_resource_create()
        attr = _uuid()
        ext_test_resource = self._ext_test_resource_create(attr)
        self.assertEqual(attr, ext_test_resource[extattr.EXTENDED_ATTRIBUTE])

    def test_ext_test_resource_get(self):
        attr = _uuid()
        obj = self._ext_test_resource_create(attr)
        obj_id = obj['id']
        res = self._do_request('GET', _get_path(
            'ext_test_resources/{0}'.format(obj_id)))
        obj2 = res['ext_test_resource']
        self.assertEqual(attr, obj2[extattr.EXTENDED_ATTRIBUTE])
