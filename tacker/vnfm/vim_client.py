
# Copyright 2015-2016 Brocade Communications Systems Ine All Rights Reserved.
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
from oslo_config import cfg
from oslo_log import log as logging

from tacker.extensions import nfvo
from tacker.keymgr import API as KEYMGR_API
from tacker import manager
from tacker.plugins.common import constants

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class VimClient(object):
    def get_vim(self, context, vim_id=None, region_name=None):
        """Get Vim information for provided VIM id

        Initiate the NFVO plugin, request VIM information for the provided
        VIM id and validate region
        """
        nfvo_plugin = manager.TackerManager.get_service_plugins().get(
            constants.NFVO)

        if not vim_id:
            LOG.debug('VIM id not provided. Attempting to find default '
                      'VIM information')
            try:
                vim_info = nfvo_plugin.get_default_vim(context)
            except Exception as ex:
                LOG.debug('Fail to get default vim due to %s', ex)
                raise nfvo.VimDefaultNotDefined()
        else:
            try:
                vim_info = nfvo_plugin.get_vim(context, vim_id,
                                               mask_password=False)
            except Exception:
                raise nfvo.VimNotFoundException(vim_id=vim_id)
        LOG.debug('VIM info found for vim id %s', vim_id)
        if region_name and not self.region_valid(vim_info['placement_attr']
                                                 ['regions'], region_name):
            raise nfvo.VimRegionNotFoundException(region_name=region_name)

        vim_auth = self._build_vim_auth(context, vim_info)
        vim_res = {'vim_auth': vim_auth, 'vim_id': vim_info['id'],
                   'vim_name': vim_info.get('name', vim_info['id']),
                   'vim_type': vim_info['type']}
        return vim_res

    @staticmethod
    def region_valid(vim_regions, region_name):
        return region_name in vim_regions

    def _build_vim_auth(self, context, vim_info):
        LOG.debug('VIM id is %s', vim_info['id'])
        vim_auth = vim_info['auth_cred']
        vim_auth['password'] = self._decode_vim_auth(context,
                                                     vim_info['id'],
                                                     vim_auth)
        vim_auth['auth_url'] = vim_info['auth_url']

        # These attributes are needless for authentication
        # from keystone, so we remove them.
        needless_attrs = ['key_type', 'secret_uuid']
        for attr in needless_attrs:
            if attr in vim_auth:
                vim_auth.pop(attr, None)
        return vim_auth

    def _decode_vim_auth(self, context, vim_id, auth):
        """Decode Vim credentials

        Decrypt VIM cred, get fernet Key from local_file_system or
        barbican.
        """
        cred = auth['password'].encode('utf-8')
        if auth.get('key_type') == 'barbican_key':
            keystone_conf = CONF.keystone_authtoken
            secret_uuid = auth['secret_uuid']
            keymgr_api = KEYMGR_API(keystone_conf.auth_url)
            secret_obj = keymgr_api.get(context, secret_uuid)
            vim_key = secret_obj.payload
        else:
            vim_key = self._find_vim_key(vim_id)

        f = fernet.Fernet(vim_key)
        if not f:
            LOG.warning('Unable to decode VIM auth')
            raise nfvo.VimNotFoundException(
                'Unable to decode VIM auth key')
        return f.decrypt(cred)

    @staticmethod
    def _find_vim_key(vim_id):
        key_file = os.path.join(CONF.vim_keys.openstack, vim_id)
        LOG.debug('Attempting to open key file for vim id %s', vim_id)
        with open(key_file, 'r') as f:
                return f.read()
        LOG.warning('VIM id invalid or key not found for  %s', vim_id)
