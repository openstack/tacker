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

import abc
import inspect
import threading
import time

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import timeutils
import six

from tacker.common import clients
from tacker.common import driver_manager
from tacker import context as t_context
from tacker.vnfm.infra_drivers.heat import heat


LOG = logging.getLogger(__name__)
CONF = cfg.CONF
OPTS = [
    cfg.IntOpt('check_intvl',
               default=10,
               help=_("check interval for monitor")),
]
CONF.register_opts(OPTS, group='monitor')


def config_opts():
    return [('monitor', OPTS), ('tacker', VNFMonitor.OPTS)]


class VNFMonitor(object):
    """VNF Monitor."""

    _instance = None
    _hosting_vnfs = dict()   # vnf_id => dict of parameters
    _status_check_intvl = 0
    _lock = threading.RLock()

    OPTS = [
        cfg.ListOpt(
            'monitor_driver', default=['ping', 'http_ping'],
            help=_('Monitor driver to communicate with '
                   'Hosting VNF/logical service '
                   'instance tacker plugin will use')),
    ]
    cfg.CONF.register_opts(OPTS, 'tacker')

    def __new__(cls, boot_wait, check_intvl=None):
        if not cls._instance:
            cls._instance = super(VNFMonitor, cls).__new__(cls)
        return cls._instance

    def __init__(self, boot_wait, check_intvl=None):
        self._monitor_manager = driver_manager.DriverManager(
            'tacker.tacker.monitor.drivers',
            cfg.CONF.tacker.monitor_driver)

        self.boot_wait = boot_wait
        if check_intvl is None:
            check_intvl = cfg.CONF.monitor.check_intvl
        self._status_check_intvl = check_intvl
        LOG.debug('Spawning VNF monitor thread')
        threading.Thread(target=self.__run__).start()

    def __run__(self):
        while(1):
            time.sleep(self._status_check_intvl)

            with self._lock:
                for hosting_vnf in self._hosting_vnfs.values():
                    if hosting_vnf.get('dead', False):
                        continue

                    self.run_monitor(hosting_vnf)

    @staticmethod
    def to_hosting_vnf(vnf_dict, action_cb):
        return {
            'id': vnf_dict['id'],
            'management_ip_addresses': jsonutils.loads(
                vnf_dict['mgmt_url']),
            'action_cb': action_cb,
            'vnf': vnf_dict,
            'monitoring_policy': jsonutils.loads(
                vnf_dict['attributes']['monitoring_policy'])
        }

    def add_hosting_vnf(self, new_vnf):
        LOG.debug('Adding host %(id)s, Mgmt IP %(ips)s',
                  {'id': new_vnf['id'],
                   'ips': new_vnf['management_ip_addresses']})
        new_vnf['boot_at'] = timeutils.utcnow()
        with self._lock:
            self._hosting_vnfs[new_vnf['id']] = new_vnf

    def delete_hosting_vnf(self, vnf_id):
        LOG.debug('deleting vnf_id %(vnf_id)s', {'vnf_id': vnf_id})
        with self._lock:
            hosting_vnf = self._hosting_vnfs.pop(vnf_id, None)
            if hosting_vnf:
                LOG.debug('deleting vnf_id %(vnf_id)s, Mgmt IP %(ips)s',
                          {'vnf_id': vnf_id,
                           'ips': hosting_vnf['management_ip_addresses']})

    def run_monitor(self, hosting_vnf):
        mgmt_ips = hosting_vnf['management_ip_addresses']
        vdupolicies = hosting_vnf['monitoring_policy']['vdus']

        vnf_delay = hosting_vnf['monitoring_policy'].get(
            'monitoring_delay', self.boot_wait)

        for vdu in vdupolicies.keys():
            if hosting_vnf.get('dead'):
                return

            policy = vdupolicies[vdu]
            for driver in policy.keys():
                params = policy[driver].get('monitoring_params', {})

                vdu_delay = params.get('monitoring_delay', vnf_delay)

                if not timeutils.is_older_than(
                    hosting_vnf['boot_at'],
                        vdu_delay):
                        continue

                actions = policy[driver].get('actions', {})
                if 'mgmt_ip' not in params:
                    params['mgmt_ip'] = mgmt_ips[vdu]

                driver_return = self.monitor_call(driver,
                                                  hosting_vnf['vnf'],
                                                  params)

                LOG.debug('driver_return %s', driver_return)

                if driver_return in actions:
                    action = actions[driver_return]
                    hosting_vnf['action_cb'](hosting_vnf, action)

    def mark_dead(self, vnf_id):
        self._hosting_vnfs[vnf_id]['dead'] = True

    def _invoke(self, driver, **kwargs):
        method = inspect.stack()[1][3]
        return self._monitor_manager.invoke(
            driver, method, **kwargs)

    def monitor_get_config(self, vnf_dict):
        return self._invoke(
            vnf_dict, monitor=self, vnf=vnf_dict)

    def monitor_url(self, vnf_dict):
        return self._invoke(
            vnf_dict, monitor=self, vnf=vnf_dict)

    def monitor_call(self, driver, vnf_dict, kwargs):
        return self._invoke(driver,
                            vnf=vnf_dict, kwargs=kwargs)


@six.add_metaclass(abc.ABCMeta)
class ActionPolicy(object):
    @classmethod
    @abc.abstractmethod
    def execute_action(cls, plugin, vnf_dict):
        pass

    _POLICIES = {}

    @staticmethod
    def register(policy, infra_driver=None):
        def _register(cls):
            cls._POLICIES.setdefault(policy, {})[infra_driver] = cls
            return cls
        return _register

    @classmethod
    def get_policy(cls, policy, vnf):
        action_clses = cls._POLICIES.get(policy)
        if not action_clses:
            return None
        infra_driver = vnf['vnfd'].get('infra_driver')
        cls = action_clses.get(infra_driver)
        if cls:
            return cls
        return action_clses.get(None)

    @classmethod
    def get_supported_actions(cls):
        return cls._POLICIES.keys()


@ActionPolicy.register('respawn')
class ActionRespawn(ActionPolicy):
    @classmethod
    def execute_action(cls, plugin, vnf_dict):
        LOG.error(_('vnf %s dead'), vnf_dict['id'])
        if plugin._mark_vnf_dead(vnf_dict['id']):
            plugin._vnf_monitor.mark_dead(vnf_dict['id'])

            attributes = vnf_dict['attributes'].copy()
            attributes['dead_vnf_id'] = vnf_dict['id']
            new_vnf = {'attributes': attributes}
            for key in ('tenant_id', 'vnfd_id', 'name'):
                new_vnf[key] = vnf_dict[key]
            LOG.debug(_('new_vnf %s'), new_vnf)

            # keystone v2.0 specific
            authtoken = CONF.keystone_authtoken
            token = clients.OpenstackClients().auth_token

            context = t_context.get_admin_context()
            context.tenant_name = authtoken.project_name
            context.user_name = authtoken.username
            context.auth_token = token['id']
            context.tenant_id = token['tenant_id']
            context.user_id = token['user_id']
            new_vnf_dict = plugin.create_vnf(context,
                                             {'vnf': new_vnf})
            LOG.info(_('respawned new vnf %s'), new_vnf_dict['id'])


@ActionPolicy.register('respawn', 'heat')
class ActionRespawnHeat(ActionPolicy):
    @classmethod
    def execute_action(cls, plugin, vnf_dict, auth_attr):
        vnf_id = vnf_dict['id']
        LOG.error(_('vnf %s dead'), vnf_id)
        if plugin._mark_vnf_dead(vnf_dict['id']):
            plugin._vnf_monitor.mark_dead(vnf_dict['id'])
            attributes = vnf_dict['attributes']
            failure_count = int(attributes.get('failure_count', '0')) + 1
            failure_count_str = str(failure_count)
            attributes['failure_count'] = failure_count_str
            attributes['dead_instance_id_' + failure_count_str] = vnf_dict[
                'instance_id']
            placement_attr = vnf_dict.get('placement_attr', {})
            region_name = placement_attr.get('region_name')
            # kill heat stack
            heatclient = heat.HeatClient(auth_attr=auth_attr,
                                         region_name=region_name)
            heatclient.delete(vnf_dict['instance_id'])

            # TODO(anyone) set the current request ctxt instead of admin ctxt
            context = t_context.get_admin_context()
            update_vnf_dict = plugin.create_vnf_sync(context,
                                                     vnf_dict)
            plugin.config_vnf(context, update_vnf_dict)
            plugin.add_vnf_to_monitor(update_vnf_dict, auth_attr)


@ActionPolicy.register('log')
class ActionLogOnly(ActionPolicy):
    @classmethod
    def execute_action(cls, plugin, vnf_dict):
        vnf_id = vnf_dict['id']
        LOG.error(_('vnf %s dead'), vnf_id)


@ActionPolicy.register('log_and_kill')
class ActionLogAndKill(ActionPolicy):
    @classmethod
    def execute_action(cls, plugin, vnf_dict):
        vnf_id = vnf_dict['id']
        if plugin._mark_vnf_dead(vnf_dict['id']):
            plugin._vnf_monitor.mark_dead(vnf_dict['id'])
            plugin.delete_vnf(t_context.get_admin_context(), vnf_id)
        LOG.error(_('vnf %s dead'), vnf_id)
