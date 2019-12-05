# Copyright 2019 NTT DATA
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import fixtures

from heatclient import client
from keystoneauth1 import fixture
from keystoneauth1 import loading
from keystoneauth1 import session
from openstack import connection

IDENTITY_URL = 'http://identityserver:5000/v3'
HEAT_URL = 'http://heat-api'
GLANCE_URL = 'http://image-api/v2'


class ClientFixture(fixtures.Fixture):

    def __init__(self, requests_mock, heat_url=HEAT_URL,
                 identity_url=IDENTITY_URL):
        super(ClientFixture, self).__init__()
        self.identity_url = identity_url
        self.client = None
        self.token = fixture.V2Token()
        self.token.set_scope()
        self.requests_mock = requests_mock
        self.discovery = fixture.V2Discovery(href=self.identity_url)
        s = self.token.add_service('orchestration')
        s.add_endpoint(heat_url)
        self.auth_url = '%s/tokens' % self.identity_url

    def setUp(self):
        super(ClientFixture, self).setUp()
        headers = {'X-Content-Type': 'application/json'}
        self.requests_mock.post(self.auth_url,
                      json=self.token, headers=headers)
        self.requests_mock.get(self.identity_url,
                      json=self.discovery, headers=headers)
        self.client = self.new_client()

    def _set_session(self):
        self.session = session.Session()
        loader = loading.get_plugin_loader('password')
        self.session.auth = loader.load_from_options(
            auth_url=self.identity_url, username='xx', password='xx')

    def new_client(self):
        self._set_session()
        return client.Client("1", session=self.session)


class SdkConnectionFixture(ClientFixture):
    """Fixture class to access the apis via openstacksdk's Connection object.

        This class is mocking the requests of glance api.
    """

    def __init__(self, requests_mock, glance_url=GLANCE_URL):
        super(SdkConnectionFixture, self).__init__(requests_mock)
        s = self.token.add_service('image')
        s.add_endpoint(glance_url)

    def new_client(self):
        self._set_session()
        conn = connection.Connection(
            region_name=None,
            session=self.session,
            identity_interface='internal',
            image_api_version='2')
        return conn
