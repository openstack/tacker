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

import threading
import time
import uuid

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import strutils

from tacker.common import driver_manager
from tacker.common import log
from tacker.common import utils
from tacker import context as t_context
from tacker.db.nfvo import nfvo_db

LOG = logging.getLogger(__name__)


def config_opts():
    return [('nfvo', NfvoPlugin.OPTS)]


class NfvoPlugin(nfvo_db.NfvoPluginDb):
    """NFVO reference plugin for NFVO extension

    Implements the NFVO extension and defines public facing APIs for VIM
    operations. NFVO internally invokes the appropriate VIM driver in
    backend based on configured VIM types. Plugin also interacts with VNFM
    extension for providing the specified VIM information
    """
    supported_extension_aliases = ['nfvo']
    _lock = threading.RLock()

    OPTS = [
        cfg.ListOpt(
            'vim_drivers', default=['openstack'],
            help=_('VIM driver for launching VNFs')),
        cfg.IntOpt(
            'monitor_interval', default=30,
            help=_('Interval to check for VIM health')),
    ]
    cfg.CONF.register_opts(OPTS, 'nfvo_vim')

    def __init__(self):
        super(NfvoPlugin, self).__init__()
        self._vim_drivers = driver_manager.DriverManager(
            'tacker.nfvo.vim.drivers',
            cfg.CONF.nfvo_vim.vim_drivers)
        self._created_vims = dict()
        context = t_context.get_admin_context()
        vims = self.get_vims(context)
        for vim in vims:
            self._created_vims[vim["id"]] = vim
        self._monitor_interval = cfg.CONF.nfvo_vim.monitor_interval
        threading.Thread(target=self.__run__).start()

    def __run__(self):
        while(1):
            time.sleep(self._monitor_interval)
            for created_vim in self._created_vims.values():
                self.monitor_vim(created_vim)

    @log.log
    def create_vim(self, context, vim):
        LOG.debug(_('Create vim called with parameters %s'),
             strutils.mask_password(vim))
        vim_obj = vim['vim']
        vim_type = vim_obj['type']
        vim_obj['id'] = str(uuid.uuid4())
        vim_obj['status'] = 'PENDING'
        try:
            self._vim_drivers.invoke(vim_type, 'register_vim', vim_obj=vim_obj)
            res = super(NfvoPlugin, self).create_vim(context, vim_obj)
            vim_obj["status"] = "REGISTERING"
            with self._lock:
                self._created_vims[res["id"]] = res
            self.monitor_vim(vim_obj)
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
        with self._lock:
            self._created_vims.pop(vim_id, None)
        super(NfvoPlugin, self).delete_vim(context, vim_id)

    @log.log
    def monitor_vim(self, vim_obj):
        vim_id = vim_obj["id"]
        auth_url = vim_obj["auth_url"]
        vim_status = self._vim_drivers.invoke(vim_obj['type'],
                                              'vim_status',
                                              auth_url=auth_url)
        current_status = "REACHABLE" if vim_status else "UNREACHABLE"
        if current_status != vim_obj["status"]:
            status = current_status
            with self._lock:
                super(NfvoPlugin, self).update_vim_status(
                    t_context.get_admin_context(),
                    vim_id, status)
                self._created_vims[vim_id]["status"] = status
