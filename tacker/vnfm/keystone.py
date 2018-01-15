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

import os

from cryptography import fernet
from keystoneauth1 import exceptions
from keystoneauth1 import identity
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

    def get_version(self, base_url=None, verify=True):
        try:
            keystone_client = client.Client(auth_url=base_url, verify=verify)
        except exceptions.ConnectionError:
            raise
        return keystone_client.version

    def get_session(self, auth_plugin, verify):
        ses = session.Session(auth=auth_plugin, verify=verify)
        return ses

    def get_endpoint(self, ses, service_type, region_name=None):
        return ses.get_endpoint(service_type, region_name)

    def initialize_client(self, version, **kwargs):
        verify = 'True' == kwargs.pop('cert_verify', 'True') or False
        if version == 'v2.0':
            from keystoneclient.v2_0 import client
            if 'token' in kwargs:
                auth_plugin = identity.v2.Token(**kwargs)
            else:
                auth_plugin = identity.v2.Password(**kwargs)
        else:
            from keystoneclient.v3 import client
            if 'token' in kwargs:
                auth_plugin = identity.v3.Token(**kwargs)
            else:
                auth_plugin = identity.v3.Password(**kwargs)
        ses = self.get_session(auth_plugin=auth_plugin, verify=verify)
        cli = client.Client(session=ses)
        return cli

    @staticmethod
    def create_key_dir(path):
        if not os.access(path, os.F_OK):
            LOG.info('[fernet_tokens] key_repository does not appear to '
                     'exist; attempting to create it')
            try:
                os.makedirs(path, 0o700)
            except OSError:
                LOG.error(
                    'Failed to create [fernet_tokens] key_repository: either'
                    'it already exists or you don\'t have sufficient'
                    'permissions to create it')

    def create_fernet_key(self):
        fernet_key = fernet.Fernet.generate_key()
        fernet_obj = fernet.Fernet(fernet_key)
        return fernet_key, fernet_obj
