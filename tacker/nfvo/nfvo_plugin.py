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

import uuid

from oslo_config import cfg

from tacker.common import driver_manager
from tacker.common import log
from tacker.common import utils
from tacker.db.nfvo import nfvo_db
from tacker.openstack.common import excutils
from tacker.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class NfvoPlugin(nfvo_db.NfvoPluginDb):
    """NFVO reference plugin for NFVO extension

    Implements the NFVO extension and defines public facing APIs for VIM
    operations. NFVO internally invokes the appropriate VIM driver in
    backend based on configured VIM types. Plugin also interacts with VNFM
    extension for providing the specified VIM information
    """
    supported_extension_aliases = ['nfvo']

    OPTS = [
        cfg.ListOpt(
            'vim_drivers', default=['openstack'],
            help=_('VIM driver for launching VNFs')),
    ]
    cfg.CONF.register_opts(OPTS, 'nfvo_vim')

    def __init__(self):
        super(NfvoPlugin, self).__init__()
        self._vim_drivers = driver_manager.DriverManager(
            'tacker.nfvo.vim.drivers',
            cfg.CONF.nfvo_vim.vim_drivers)

    @log.log
    def create_vim(self, context, vim):
        LOG.debug(_('Create vim called with parameters %s'), vim)
        vim_obj = vim['vim']
        vim_type = vim_obj['type']
        vim_obj['id'] = str(uuid.uuid4())
        try:
            self._vim_drivers.invoke(vim_type, 'register_vim', vim_obj=vim_obj)
            res = super(NfvoPlugin, self).create_vim(context, vim_obj)
            return res
        except Exception:
            with excutils.save_and_reraise_exception():
                self._vim_drivers.invoke(vim_type, 'delete_vim_auth',
                                         vim_id=vim_obj['id'])

    def _get_vim(self, context, vim_id):
        if not self.is_vim_still_in_use(context, vim_id):
            return self.get_vim(context, vim_id)

    @log.log
    def update_vim(self, context, vim_id, vim):
        vim_obj = self._get_vim(context, vim_id)
        utils.deep_update(vim_obj, vim['vim'])
        vim_type = vim_obj['type']
        try:
            self._vim_drivers.invoke(vim_type, 'register_vim', vim_obj=vim_obj)
            return super(NfvoPlugin, self).update_vim(context, vim_id, vim_obj)
        except Exception:
            with excutils.save_and_reraise_exception():
                self._vim_drivers.invoke(vim_type, 'delete_vim_auth',
                                         vim_id=vim_obj['id'])

    @log.log
    def delete_vim(self, context, vim_id):
        vim_obj = self._get_vim(context, vim_id)
        self._vim_drivers.invoke(vim_obj['type'], 'deregister_vim',
                                 vim_id=vim_id)
        super(NfvoPlugin, self).delete_vim(context, vim_id)
