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

from heatclient import client as heatclient
from tacker.vnfm import keystone


class OpenstackClients(object):

    def __init__(self, auth_attr, region_name=None):
        super(OpenstackClients, self).__init__()
        self.keystone_plugin = keystone.Keystone()
        self.heat_client = None
        self.mistral_client = None
        self.keystone_client = None
        self.region_name = region_name
        self.auth_attr = auth_attr

    def _keystone_client(self):
        version = self.auth_attr['auth_url'].rpartition('/')[2]
        return self.keystone_plugin.initialize_client(version,
                                                      **self.auth_attr)

    def _heat_client(self):
        endpoint = self.keystone_session.get_endpoint(
            service_type='orchestration', region_name=self.region_name)
        return heatclient.Client('1', endpoint=endpoint,
                                 session=self.keystone_session)

    @property
    def keystone_session(self):
        return self.keystone.session

    @property
    def keystone(self):
        if not self.keystone_client:
            self.keystone_client = self._keystone_client()
        return self.keystone_client

    @property
    def heat(self):
        if not self.heat_client:
            self.heat_client = self._heat_client()
        return self.heat_client
