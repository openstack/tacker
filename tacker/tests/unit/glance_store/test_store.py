# Copyright (C) 2019 NTT DATA
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

import glance_store
from six.moves import urllib
import six.moves.urllib.error as urlerr

from tacker.common import exceptions
import tacker.conf
from tacker.glance_store import store
from tacker.tests.unit import base


CONF = tacker.conf.CONF


class StoreBaseTest(base.TestCase):

    def setUp(self):
        super(StoreBaseTest, self).setUp()
        self.conf = CONF
        glance_store.create_stores(self.conf)
        self.body = {"address_information": "http://welcome.com/test.zip",
                     "user_name": "user1", "password": "pass1"}

    @mock.patch.object(urllib.request, 'urlopen')
    def test_get_csar_data_iter_with_username_password(self, mock_url_open):
        store.get_csar_data_iter(self.body)
        mock_url_open.assert_called_once()

    @mock.patch.object(urllib.request, 'urlopen')
    def test_get_csar_data_iter_without_username_password(self, mock_url_open):
        body = {"address_information": "http://welcome.com/test.zip",
                "user_name": None, "password": None}
        store.get_csar_data_iter(body)
        mock_url_open.assert_called_once()

    @mock.patch.object(urllib.request, 'urlopen')
    def test_get_csar_data_iter_unauthorised(self, mock_url_open):
        mock_url_open.side_effect = urlerr.HTTPError(
            url='', code=401, msg='HTTP Error 401 Unauthorized', hdrs={},
            fp=None)
        self.assertRaises(exceptions.VNFPackageURLInvalid,
                          store.get_csar_data_iter, self.body)
