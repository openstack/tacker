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

import netaddr

from oslo_config import cfg
from oslo_log import log as logging
import random
import string
from tacker._i18n import _
from tacker.common import utils
from tacker.vnfm.monitor_drivers import abstract_driver


LOG = logging.getLogger(__name__)

OPTS = [
    cfg.HostAddressOpt('host', default=utils.get_hostname(),
                       help=_('Address which drivers use to trigger')),
    cfg.PortOpt('port', default=9890,
               help=_('port number which drivers use to trigger'))
]
cfg.CONF.register_opts(OPTS, group='ceilometer')


def config_opts():
    return [('ceilometer', OPTS)]


ALARM_INFO = (
    ALARM_ACTIONS, OK_ACTIONS, REPEAT_ACTIONS, ALARM,
    INSUFFICIENT_DATA_ACTIONS, DESCRIPTION, ENABLED, TIME_CONSTRAINTS,
    SEVERITY,
) = ('alarm_actions', 'ok_actions', 'repeat_actions', 'alarm',
     'insufficient_data_actions', 'description', 'enabled', 'time_constraints',
     'severity',
     )


class VNFMonitorCeilometer(
        abstract_driver.VNFMonitorAbstractDriver):
    def get_type(self):
        return 'ceilometer'

    def get_name(self):
        return 'ceilometer'

    def get_description(self):
        return 'Tacker VNFMonitor Ceilometer Driver'

    def _create_alarm_url(self, vnf_id, mon_policy_name, mon_policy_action):
        # alarm_url = 'http://host:port/v1.0/vnfs/vnf-uuid/monitoring-policy
        # -name/action-name?key=8785'
        host = cfg.CONF.ceilometer.host
        port = cfg.CONF.ceilometer.port
        LOG.info("Tacker in heat listening on %(host)s:%(port)s",
                 {'host': host,
                  'port': port})
        origin = "http://%(host)s:%(port)s/v1.0/vnfs" % {
            'host': host, 'port': port}
        if netaddr.valid_ipv6(host):
            origin = "http://[%(host)s]:%(port)s/v1.0/vnfs" % {
                'host': host, 'port': port}
        access_key = ''.join(
            random.SystemRandom().choice(
                string.ascii_lowercase + string.digits)
            for _ in range(8))
        alarm_url = "".join([origin, '/', vnf_id, '/', mon_policy_name, '/',
                             mon_policy_action, '/', access_key])
        return alarm_url

    def call_alarm_url(self, vnf, kwargs):
        '''must be used after call heat-create in plugin'''
        return self._create_alarm_url(**kwargs)

    def _process_alarm(self, alarm_id, status):
        if alarm_id and status == ALARM:
            return True

    def process_alarm(self, vnf, kwargs):
        '''Check alarm state. if available, will be processed'''
        return self._process_alarm(**kwargs)

    def monitor_url(self, plugin, context, vnf):
        pass

    def monitor_call(self, vnf, kwargs):
        pass
