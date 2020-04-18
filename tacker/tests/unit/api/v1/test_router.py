# Copyright (c) 2014-2018 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from oslo_serialization import jsonutils

from tacker.api.v1.router import APIRouter
from tacker.api.v1.router import Index
from tacker.tests import base
from tacker import wsgi


class TestIndex(base.BaseTestCase):

    def test_index(self):
        request = wsgi.Request.blank(
            "/test/", body=b"{'name': 'tacker'}", method='POST',
            headers={'Content-Type': "application/json"})

        index_cls = Index({"version": "v1"})
        result = index_cls(request)
        expect_body = {'resources': [
            {'collection': 'v1',
             'links': [
                 {'href': 'http://localhost/test/v1',
                  'rel': 'self'}],
             'name': 'version'}]}

        self.assertEqual(expect_body, jsonutils.loads(result.body))
        self.assertEqual('application/json', result.content_type)


@mock.patch('tacker.api.v1.router.APIRouter.factory', return_value=None)
class TestAPIRouter(base.BaseTestCase):

    def test_api_factory(self, factory_mock):
        result = APIRouter().factory({})
        factory_mock.assert_called_once_with({})
        self.assertEqual(None, result)
