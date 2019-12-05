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

import copy

from heatclient import client as heatclient
from openstack import connection

from tacker.vnfm import keystone


class OpenstackClients(object):

    def __init__(self, auth_attr, region_name=None):
        super(OpenstackClients, self).__init__()
        self.keystone_plugin = keystone.Keystone()
        self.heat_client = None
        self.mistral_client = None
        self.keystone_client = None
        self.region_name = region_name

        if auth_attr:
            # Note(tpatil): In vnflcm, auth_attr contains region information
            # which should be popped before creating the keystoneclient.
            auth_attr = copy.deepcopy(auth_attr)
            auth_attr.pop('region', None)

        self.auth_attr = auth_attr

    def _keystone_client(self):
        return self.keystone_plugin.initialize_client(**self.auth_attr)

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


class OpenstackSdkConnection(object):

    def __init__(self, vim_connection_info, version=None):
        super(OpenstackSdkConnection, self).__init__()
        self.keystone_plugin = keystone.Keystone()
        self.connection = self.openstack_connection(vim_connection_info,
                                                    version)

    def openstack_connection(self, vim_connection_info, version):
        access_info = vim_connection_info.access_info
        auth = dict(auth_url=access_info['auth_url'],
          username=access_info['username'],
          password=access_info['password'],
          project_name=access_info['project_name'],
          user_domain_name=access_info['user_domain_name'],
          project_domain_name=access_info['project_domain_name'])

        session = self.keystone_plugin.initialize_client(**auth).session

        conn = connection.Connection(
            region_name=access_info.get('region'),
            session=session,
            identity_interface='internal',
            image_api_version=version)

        return conn
