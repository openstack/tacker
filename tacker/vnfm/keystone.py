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
from keystoneauth1 import adapter
from keystoneauth1 import identity
from keystoneauth1 import session
from oslo_config import cfg
from oslo_log import log as logging

from tacker.common import utils


DEFAULT_IDENTITY_VERSION = "v3"
LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class Keystone(object):
    """Keystone module for OpenStack VIM

    Handles identity operations for a given OpenStack
    instance such as version, session and client
    """

    def get_version(self, base_url=None, verify=False):
        # TODO(h-asahina): Maybe it's better to add error handling here. In
        # that case, defiining common exceptions for this module would be also
        # better.
        sess = session.Session()
        return sess.get(base_url, authenticated=False, verify=verify)

    def get_session(self, auth_plugin, verify):
        sess = session.Session(auth=auth_plugin, verify=verify)
        return adapter.Adapter(session=sess,
                               service_type='identity')

    def get_endpoint(self, ses, service_type, region_name=None):
        return ses.get_endpoint(service_type, region_name)

    def initialize_client(self, **kwargs):
        verify = utils.str_to_bool(kwargs.pop('cert_verify', 'True'))
        if 'token' in kwargs:
            auth_plugin = identity.v3.Token(**kwargs)
        else:
            auth_plugin = identity.v3.Password(**kwargs)
        return self.get_session(auth_plugin=auth_plugin, verify=verify)

    @staticmethod
    def create_key_dir(path):
        if not os.access(path, os.F_OK):
            LOG.info('[fernet_tokens] key_repository does not appear to '
                     'exist; attempting to create it')
            try:
                os.makedirs(path, 0o700)
            except OSError:
                LOG.error(
                    'Failed to create [fernet_tokens] key_repository: either '
                    'it already exists or you don\'t have sufficient '
                    'permissions to create it')

    def create_fernet_key(self):
        fernet_key = fernet.Fernet.generate_key()
        fernet_obj = fernet.Fernet(fernet_key)
        return fernet_key, fernet_obj
