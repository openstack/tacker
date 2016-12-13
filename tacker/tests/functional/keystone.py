# Copyright 2016 Brocade Communications System, Inc.
# All Rights Reserved.
#
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

from keystoneauth1 import exceptions
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient import client
from oslo_config import cfg
from oslo_log import log as logging


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class Keystone(object):
    """Keystone module for OpenStack VIM

    Handles identity operations for a given OpenStack
    instance such as version, session and client
    """

    def get_version(self, base_url=None):
        try:
            keystone_client = client.Client(auth_url=base_url)
        except exceptions.ConnectionError:
            raise
        return keystone_client.version

    def get_session(self, auth_plugin):
        ses = session.Session(auth=auth_plugin)
        return ses

    def get_endpoint(self, ses, service_type, region_name=None):
        return ses.get_endpoint(service_type, region_name)

    def initialize_client(self, version, **kwargs):
        from keystoneclient.v3 import client
        auth_plugin = v3.Password(**kwargs)
        ses = self.get_session(auth_plugin=auth_plugin)
        cli = client.Client(session=ses)
        return cli
