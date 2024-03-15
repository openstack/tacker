# Copyright 2013, 2014 Intel Corporation.
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

from oslo_config import cfg
from oslo_log import log as logging

from tacker._i18n import _
from tacker.common import driver_manager
from tacker import context as t_context
from tacker.db.vnfm import vnfm_db
from tacker.vnfm import vim_client


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def config_opts():
    return [('tacker', VNFMPlugin.OPTS_INFRA_DRIVER)]


class VNFMPlugin(vnfm_db.VNFMPluginDb):
    """VNFMPlugin which supports VNFM framework.

    Plugin which supports Tacker framework
    """

    OPTS_INFRA_DRIVER = [
        cfg.ListOpt(
            'infra_driver', default=['noop', 'openstack', 'kubernetes'],
            help=_('Hosting vnf drivers tacker plugin will use')),
    ]
    cfg.CONF.register_opts(OPTS_INFRA_DRIVER, 'tacker')

    supported_extension_aliases = ['vnfm']

    def __init__(self):
        super(VNFMPlugin, self).__init__()
        self.vim_client = vim_client.VimClient()
        self._vnf_manager = driver_manager.DriverManager(
            'tacker.tacker.vnfm.drivers',
            cfg.CONF.tacker.infra_driver)
        # NOTE(ueha): Workaround to suppress the following Exception:
        #             oslo_db.sqlalchemy.enginefacade.AlreadyStartedError
        _ = self.get_vnfs(t_context.get_admin_context())

    def spawn_n(self, function, *args, **kwargs):
        self._pool.spawn_n(function, *args, **kwargs)

    def get_vim(self, context, vnf):
        region_name = vnf.setdefault('placement_attr', {}).get(
            'region_name', None)
        vim_res = self.vim_client.get_vim(context, vnf['vim_id'],
                                          region_name)
        vnf['placement_attr']['vim_name'] = vim_res['vim_name']
        vnf['vim_id'] = vim_res['vim_id']
        return vim_res
