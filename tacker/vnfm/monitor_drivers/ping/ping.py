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
#

from oslo_config import cfg
from oslo_log import log as logging

from tacker.agent.linux import utils as linux_utils
from tacker.common import log
from tacker.vnfm.monitor_drivers import abstract_driver


LOG = logging.getLogger(__name__)
OPTS = [
    cfg.StrOpt('count', default='1',
               help=_('number of ICMP packets to send')),
    cfg.StrOpt('timeout', default='1',
               help=_('number of seconds to wait for a response')),
    cfg.StrOpt('interval', default='1',
               help=_('number of seconds to wait between packets'))
]
cfg.CONF.register_opts(OPTS, 'monitor_ping')


def config_opts():
    return [('monitor_ping', OPTS)]


class VNFMonitorPing(abstract_driver.VNFMonitorAbstractDriver):
    def get_type(self):
        return 'ping'

    def get_name(self):
        return 'ping'

    def get_description(self):
        return 'Tacker VNFMonitor Ping Driver'

    def monitor_url(self, plugin, context, vnf):
        LOG.debug('monitor_url %s', vnf)
        return vnf.get('monitor_url', '')

    def _is_pingable(self, mgmt_ip="", count=5, timeout=1, interval='0.2',
                     **kwargs):
        """Checks whether an IP address is reachable by pinging.

        Use linux utils to execute the ping (ICMP ECHO) command.
        Sends 5 packets with an interval of 0.2 seconds and timeout of 1
        seconds. Runtime error implies unreachability else IP is pingable.
        :param ip: IP to check
        :return: bool - True or string 'failure' depending on pingability.
        """
        ping_cmd = ['ping',
                    '-c', count,
                    '-W', timeout,
                    '-i', interval,
                    mgmt_ip]

        try:
            linux_utils.execute(ping_cmd, check_exit_code=True)
            return True
        except RuntimeError:
            LOG.warning("Cannot ping ip address: %s", mgmt_ip)
            return 'failure'

    @log.log
    def monitor_call(self, vnf, kwargs):
        if not kwargs['mgmt_ip']:
            return

        return self._is_pingable(**kwargs)
