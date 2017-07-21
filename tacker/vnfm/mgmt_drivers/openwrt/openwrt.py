# Copyright 2015 Intel Corporation.
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
from oslo_serialization import jsonutils
import yaml

from tacker.common import cmd_executer
from tacker.common import exceptions
from tacker.common import log
from tacker.vnfm.mgmt_drivers import abstract_driver
from tacker.vnfm.mgmt_drivers import constants as mgmt_constants


LOG = logging.getLogger(__name__)
OPTS = [
    cfg.StrOpt('user', default='root', help=_('user name to login openwrt')),
    cfg.StrOpt('password', default='', help=_('password to login openwrt')),
]
cfg.CONF.register_opts(OPTS, 'openwrt')


def config_opts():
    return [('openwrt', OPTS)]


class DeviceMgmtOpenWRT(abstract_driver.DeviceMGMTAbstractDriver):
    def get_type(self):
        return 'openwrt'

    def get_name(self):
        return 'openwrt'

    def get_description(self):
        return 'Tacker VNFMgmt OpenWRT Driver'

    def mgmt_url(self, plugin, context, vnf):
        LOG.debug('mgmt_url %s', vnf)
        return vnf.get('mgmt_url', '')

    @log.log
    def _config_service(self, mgmt_ip_address, service, config):
        user = cfg.CONF.openwrt.user
        password = cfg.CONF.openwrt.password
        try:
            cmd = "uci import %s; /etc/init.d/%s restart" % (service, service)
            LOG.debug('execute command: %(cmd)s on mgmt_ip_address '
                      '%(mgmt_ip)s',
                      {'cmd': cmd,
                       'mgmt_ip': mgmt_ip_address})
            commander = cmd_executer.RemoteCommandExecutor(
                user, password, mgmt_ip_address)
            commander.execute_command(cmd, input_data=config)
        except Exception as ex:
            LOG.error("While executing command on remote "
                      "%(mgmt_ip)s: %(exception)s",
                      {'mgmt_ip': mgmt_ip_address,
                       'exception': ex})
            raise exceptions.MgmtDriverException()

    @log.log
    def mgmt_call(self, plugin, context, vnf, kwargs):
        if (kwargs[mgmt_constants.KEY_ACTION] !=
                mgmt_constants.ACTION_UPDATE_VNF):
            return
        dev_attrs = vnf.get('attributes', {})

        mgmt_url = jsonutils.loads(vnf.get('mgmt_url', '{}'))
        if not mgmt_url:
            return

        vdus_config = dev_attrs.get('config', '')
        config_yaml = yaml.safe_load(vdus_config)
        if not config_yaml:
            return
        vdus_config_dict = config_yaml.get('vdus', {})
        for vdu, vdu_dict in vdus_config_dict.items():
            config = vdu_dict.get('config', {})
            for key, conf_value in config.items():
                KNOWN_SERVICES = ('firewall', 'network')
                if key not in KNOWN_SERVICES:
                    continue
                mgmt_ip_address = mgmt_url.get(vdu, '')
                if not mgmt_ip_address:
                    LOG.warning('tried to configure unknown mgmt '
                                'address on VNF %(vnf)s VDU %(vdu)s',
                                {'vnf': vnf.get('name'),
                                 'vdu': vdu})
                    continue

                if isinstance(mgmt_ip_address, list):
                    for ip_address in mgmt_ip_address:
                        self._config_service(ip_address, key, conf_value)
                else:
                    self._config_service(mgmt_ip_address, key, conf_value)
