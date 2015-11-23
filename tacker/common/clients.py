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
from keystoneclient.v2_0 import client as ks_client
from oslo_config import cfg
from oslo_log import log as logging

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

OPTS = [
    cfg.StrOpt('heat_uri',
        default='http://localhost:8004/v1',
        help=_("Heat service URI to create VNF resources"
               "specified in the VNFD templates")),
]
CONF.register_opts(OPTS, group='servicevm_heat')


class OpenstackClients(object):

    def __init__(self):
        super(OpenstackClients, self).__init__()
        self.keystone_client = None
        self.heat_client = None
        self.nova_client = None
        self.auth_url = CONF.keystone_authtoken.auth_uri + '/v2.0'
        self.auth_username = CONF.keystone_authtoken.username
        self.auth_password = CONF.keystone_authtoken.password
        self.auth_tenant_name = CONF.keystone_authtoken.project_name

    def _keystone_client(self):
        return ks_client.Client(
                   tenant_name=self.auth_tenant_name,
                   username=self.auth_username,
                   password=self.auth_password,
                   auth_url=self.auth_url)

    def _heat_client(self):
        tenant_id = self.auth_token['tenant_id']
        token = self.auth_token['id']
        endpoint = CONF.servicevm_heat.heat_uri + '/' + tenant_id
        return heatclient.Client('1', endpoint=endpoint, token=token)

    @property
    def auth_token(self):
        return self.keystone.service_catalog.get_token()

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
