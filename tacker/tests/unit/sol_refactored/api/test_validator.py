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

from unittest import mock

from tacker import context
from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.api import validator
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.tests import base


test_schema_v200 = {
    'type': 'object',
    'properties': {
        'vnfdId': {'type': 'string'},
        'ProductId': {'type': 'string'}
    },
    'required': ['vnfdId', 'ProductId'],
    'additionalProperties': True
}

test_schema_v210 = {
    'type': 'object',
    'properties': {
        'vnfdId': {'type': 'string'},
        'flavourId': {'type': 'string'}
    },
    'required': ['vnfdId', 'flavourId'],
    'additionalProperties': True
}


class TestValidator(base.BaseTestCase):

    def setUp(self):
        super(TestValidator, self).setUp()
        self.context = context.get_admin_context_without_session()
        self.request = mock.Mock()
        self.request.context = self.context

    @validator.schema(test_schema_v200, '2.0.0', '2.0.2')
    @validator.schema(test_schema_v210, '2.1.0', '2.2.0')
    def _test_method(self, request, body):
        return True

    @mock.patch.object(api_version, 'supported_versions',
        new=['2.0.0', '2.0.1', '2.0.2', '2.1.0', '2.2.0'])
    def test_validator(self):
        body = {"vnfdId": "vnfd_id", "ProductId": "product_id"}
        for ok_ver in ['2.0.0', '2.0.1', '2.0.2']:
            self.context.api_version = api_version.APIVersion(ok_ver)
            result = self._test_method(request=self.request, body=body)
            self.assertTrue(result)
        for ng_ver in ['2.1.0', '2.2.0']:
            self.context.api_version = api_version.APIVersion(ng_ver)
            self.assertRaises(sol_ex.SolValidationError,
                self._test_method, request=self.request, body=body)

        body = {"vnfdId": "vnfd_id", "flavourId": "flavour_id"}
        for ok_ver in ['2.1.0', '2.2.0']:
            self.context.api_version = api_version.APIVersion(ok_ver)
            result = self._test_method(request=self.request, body=body)
            self.assertTrue(result)
        for ng_ver in ['2.0.0', '2.0.1', '2.0.2']:
            self.context.api_version = api_version.APIVersion(ng_ver)
            self.assertRaises(sol_ex.SolValidationError,
                self._test_method, request=self.request, body=body)
