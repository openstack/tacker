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

import copy

import eventlet
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import strutils
from oslo_utils import uuidutils

from tacker._i18n import _
from tacker.common import driver_manager
from tacker.common import log
from tacker.common import utils
from tacker.db.nfvo import nfvo_db_plugin
from tacker.extensions import nfvo
from tacker.vnfm import keystone
from tacker.vnfm import vim_client


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def config_opts():
    return [('nfvo_vim', NfvoPlugin.OPTS)]


class NfvoPlugin(nfvo_db_plugin.NfvoPluginDb):
    """NFVO reference plugin for NFVO extension

    Implements the NFVO extension and defines public facing APIs for VIM
    operations. NFVO internally invokes the appropriate VIM driver in
    backend based on configured VIM types. Plugin also interacts with VNFM
    extension for providing the specified VIM information
    """
    supported_extension_aliases = ['nfvo']

    OPTS = [
        cfg.ListOpt(
            'vim_drivers', default=['openstack', 'kubernetes'],
            help=_('VIM driver for launching VNFs')),
    ]
    cfg.CONF.register_opts(OPTS, 'nfvo_vim')

    def __init__(self):
        super(NfvoPlugin, self).__init__()
        self._pool = eventlet.GreenPool()
        self._vim_drivers = driver_manager.DriverManager(
            'tacker.nfvo.vim.drivers',
            cfg.CONF.nfvo_vim.vim_drivers)
        self.vim_client = vim_client.VimClient()

    @staticmethod
    def validate_keystone_auth_url(auth_url, verify):
        # NOTE(h-asahina): `verify` will be used as an arg of session to
        # validate certificate
        keystone_obj = keystone.Keystone()
        auth_url = utils.get_auth_url_v3(auth_url)
        try:
            keystone_obj.get_version(auth_url, verify)
        except Exception as e:
            LOG.error(f'Validation Failed for Keystone auth_url: {auth_url}')
            raise nfvo.VimConnectionException(message=str(e))

    @log.log
    def create_vim(self, context, vim):
        LOG.debug('Create vim called with parameters %s',
                  strutils.mask_password(vim))
        vim_obj = vim['vim']
        vim_type = vim_obj['type']
        if vim_type == 'openstack':
            vim_obj['auth_url'] = utils.get_auth_url_v3(vim_obj['auth_url'])
        vim_obj['id'] = uuidutils.generate_uuid()
        try:
            self._vim_drivers.invoke(vim_type,
                                     'register_vim',
                                     vim_obj=vim_obj)
            res = super(NfvoPlugin, self).create_vim(context, vim_obj)
        except Exception:
            with excutils.save_and_reraise_exception():
                self._vim_drivers.invoke(vim_type,
                                         'delete_vim_auth',
                                         vim_id=vim_obj['id'],
                                         auth=vim_obj['auth_cred'])
        return res

    def _get_vim(self, context, vim_id):
        if not self.is_vim_still_in_use(context, vim_id):
            return self.get_vim(context, vim_id, mask_password=False)

    @log.log
    def update_vim(self, context, vim_id, vim):
        vim_obj = self._get_vim(context, vim_id)
        old_vim_obj = copy.deepcopy(vim_obj)
        utils.deep_update(vim_obj, vim['vim'])
        vim_type = vim_obj['type']
        update_args = vim['vim']
        old_auth_need_delete = False
        new_auth_created = False
        try:
            # re-register the VIM only if there is a change in bearer_token,
            # username, password or bearer_token.
            # auth_url of auth_cred is from vim object which
            # is not updatable. so no need to consider it
            if 'auth_cred' in update_args:
                auth_cred = update_args['auth_cred']
                if 'oidc_token_url' in auth_cred:
                    # update oidc info, and remove bearer_token if exists
                    vim_obj['auth_cred']['oidc_token_url'] = auth_cred.get(
                        'oidc_token_url')
                    vim_obj['auth_cred']['username'] = auth_cred.get(
                        'username')
                    vim_obj['auth_cred']['password'] = auth_cred.get(
                        'password')
                    vim_obj['auth_cred']['client_id'] = auth_cred.get(
                        'client_id')
                    vim_obj['auth_cred']['client_secret'] = auth_cred.get(
                        'client_secret')
                    if 'bearer_token' in vim_obj['auth_cred']:
                        vim_obj['auth_cred'].pop('bearer_token')
                elif ('username' in auth_cred) and ('password' in auth_cred)\
                        and (auth_cred['password'] is not None):
                    # update new username and password, remove bearer_token
                    # if it exists in the old vim
                    vim_obj['auth_cred']['username'] = auth_cred['username']
                    vim_obj['auth_cred']['password'] = auth_cred['password']
                    if 'bearer_token' in vim_obj['auth_cred']:
                        vim_obj['auth_cred'].pop('bearer_token')
                    if 'oidc_token_url' in vim_obj['auth_cred']:
                        vim_obj['auth_cred'].pop('oidc_token_url')
                    if 'client_id' in vim_obj['auth_cred']:
                        vim_obj['auth_cred'].pop('client_id')
                    if 'client_secret' in vim_obj['auth_cred']:
                        vim_obj['auth_cred'].pop('client_secret')
                elif 'bearer_token' in auth_cred:
                    # update bearer_token, remove username and password
                    # if they exist in the old vim
                    vim_obj['auth_cred']['bearer_token'] =\
                        auth_cred['bearer_token']
                    if 'username' in vim_obj['auth_cred']:
                        vim_obj['auth_cred'].pop('username')
                    if 'password' in vim_obj['auth_cred']:
                        vim_obj['auth_cred'].pop('password')
                    if 'oidc_token_url' in vim_obj['auth_cred']:
                        vim_obj['auth_cred'].pop('oidc_token_url')
                    if 'client_id' in vim_obj['auth_cred']:
                        vim_obj['auth_cred'].pop('client_id')
                    if 'client_secret' in vim_obj['auth_cred']:
                        vim_obj['auth_cred'].pop('client_secret')
                if 'ssl_ca_cert' in auth_cred:
                    # update new ssl_ca_cert
                    vim_obj['auth_cred']['ssl_ca_cert'] =\
                        auth_cred['ssl_ca_cert']
                # Notice: vim_obj may be updated in vim driver's
                self._vim_drivers.invoke(vim_type,
                                         'register_vim',
                                         vim_obj=vim_obj)
                new_auth_created = True

                # Check whether old vim's auth need to be deleted
                old_key_type = old_vim_obj['auth_cred'].get('key_type')
                if old_key_type == 'barbican_key':
                    old_auth_need_delete = True

            vim_obj = super(NfvoPlugin, self).update_vim(
                context, vim_id, vim_obj)
            if old_auth_need_delete:
                try:
                    self._vim_drivers.invoke(vim_type,
                                             'delete_vim_auth',
                                             vim_id=old_vim_obj['id'],
                                             auth=old_vim_obj['auth_cred'])
                except Exception as ex:
                    LOG.warning("Fail to delete old auth for vim %s due to %s",
                                vim_id, ex)
            return vim_obj
        except Exception as ex:
            LOG.error("Got exception when update_vim %s due to %s",
                      vim_id, ex)
            with excutils.save_and_reraise_exception():
                if new_auth_created:
                    # delete new-created vim auth, old auth is still used.
                    self._vim_drivers.invoke(vim_type,
                                             'delete_vim_auth',
                                             vim_id=vim_obj['id'],
                                             auth=vim_obj['auth_cred'])

    @log.log
    def delete_vim(self, context, vim_id):
        vim_obj = self._get_vim(context, vim_id)
        self._vim_drivers.invoke(vim_obj['type'],
                                 'deregister_vim',
                                 vim_obj=vim_obj)
        super(NfvoPlugin, self).delete_vim(context, vim_id)
