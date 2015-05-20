# Copyright 2015 Intel Corporation.
# Copyright 2015 Isaku Yamahata <isaku.yamahata at intel com>
#                               <isaku.yamahata at gmail com>
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
#
# @author: Isaku Yamahata, Intel Corporation.

import abc
import six
import threading
import time

from keystoneclient.v2_0 import client as ks_client
from oslo_config import cfg
from oslo_utils import timeutils

from tacker.agent.linux import utils as linux_utils
from tacker import context as t_context
from tacker.i18n import _LW
from tacker.openstack.common import jsonutils
from tacker.openstack.common import log as logging
from tacker.vm.drivers.heat import heat


LOG = logging.getLogger(__name__)
CONF = cfg.CONF
OPTS = [
    cfg.IntOpt('check_intvl',
               default=10,
               help=_("check interval for monitor")),
    cfg.IntOpt('boot_wait',
               default=30,
               help=_("boot wait for monitor")),
]
CONF.register_opts(OPTS, group='monitor')


def _is_pingable(ip):
    """Checks whether an IP address is reachable by pinging.

    Use linux utils to execute the ping (ICMP ECHO) command.
    Sends 5 packets with an interval of 0.2 seconds and timeout of 1
    seconds. Runtime error implies unreachability else IP is pingable.
    :param ip: IP to check
    :return: bool - True or False depending on pingability.
    """
    ping_cmd = ['ping',
                '-c', '5',
                '-W', '1',
                '-i', '0.2',
                ip]
    try:
        linux_utils.execute(ping_cmd, check_exit_code=True)
        return True
    except RuntimeError:
        LOG.warning(_LW("Cannot ping ip address: %s"), ip)
        return False


class DeviceStatus(object):
    """Device status"""

    _instance = None
    _hosting_devices = dict()   # device_id => dict of parameters
    _status_check_intvl = 0
    _lock = threading.Lock()

    def __new__(cls, check_intvl=None):
        if not cls._instance:
            cls._instance = super(DeviceStatus, cls).__new__(cls)
        return cls._instance

    def __init__(self, check_intvl=None):
        if check_intvl is None:
            check_intvl = cfg.CONF.monitor.check_intvl
        self._status_check_intvl = check_intvl
        LOG.debug('Spawning device status thread')
        threading.Thread(target=self.__run__).start()

    def __run__(self):
        while(1):
            time.sleep(self._status_check_intvl)
            dead_hosting_devices = []
            with self._lock:
                for hosting_device in self._hosting_devices.values():
                    if hosting_device.get('dead', False):
                        continue
                    if not timeutils.is_older_than(
                            hosting_device['boot_at'],
                            hosting_device['boot_wait']):
                        continue
                    if not self.is_hosting_device_reachable(hosting_device):
                        dead_hosting_devices.append(hosting_device)
            for hosting_device in dead_hosting_devices:
                hosting_device['down_cb'](hosting_device)

    @staticmethod
    def to_hosting_device(device_dict, down_cb):
        return {
            'id': device_dict['id'],
            'management_ip_addresses': jsonutils.loads(
                device_dict['mgmt_url']),
            'boot_wait': cfg.CONF.monitor.boot_wait,
            'down_cb': down_cb,
            'device': device_dict,
        }

    def add_hosting_device(self, new_device):
        LOG.debug('Adding host %(id)s, Mgmt IP %(ips)s',
                  {'id': new_device['id'],
                   'ips': new_device['management_ip_addresses']})
        new_device['boot_at'] = timeutils.utcnow()
        with self._lock:
            self._hosting_devices[new_device['id']] = new_device

    def delete_hosting_device(self, device_id):
        LOG.debug('deleting device_id %(device_id)s', {'device_id': device_id})
        with self._lock:
            hosting_device = self._hosting_devices.pop(device_id, None)
            if hosting_device:
                LOG.debug('deleting device_id %(device_id)s, Mgmt IP %(ips)s',
                        {'device_id': device_id,
                         'ips': hosting_device['management_ip_addresses']})

    def is_hosting_device_reachable(self, hosting_device):
        """Check the hosting device which hosts this resource is reachable.

        If the resource is not reachable, it is added to the backlog.

        :param hosting_device : dict of the hosting device
        :return True if device is reachable, else None
        """
        for key, mgmt_ip_address in hosting_device[
                'management_ip_addresses'].items():
            if not _is_pingable(mgmt_ip_address):
                LOG.debug('Host %(id)s:%(key)s:%(ip)s, is unreachable',
                          {'id': hosting_device['id'],
                           'key': key,
                           'ip': mgmt_ip_address})
                hosting_device['dead_at'] = timeutils.utcnow()
                return False

            LOG.debug('Host %(id)s:%(key)s:%(ip)s, is reachable',
                      {'id': hosting_device['id'],
                       'key': key,
                       'ip': mgmt_ip_address})

        return True

    def mark_dead(self, device_id):
        self._hosting_devices[device_id]['dead'] = True


@six.add_metaclass(abc.ABCMeta)
class FailurePolicy(object):
    @classmethod
    @abc.abstractmethod
    def on_failure(cls, plugin, device_dict):
        pass

    _POLICIES = {}

    @staticmethod
    def register(policy, infra_driver=None):
        def _register(cls):
            cls._POLICIES.setdefault(policy, {})[infra_driver] = cls
            return cls
        return _register

    @classmethod
    def get_policy(cls, policy, device):
        failure_clses = cls._POLICIES.get(policy)
        if not failure_clses:
            return None
        infra_driver = device['device_template'].get('infra_driver')
        cls = failure_clses.get(infra_driver)
        if cls:
            return cls
        return failure_clses.get(None)

    @abc.abstractmethod
    def on_failure(cls, plugin, device_dict):
        pass


@FailurePolicy.register('respawn')
class Respawn(FailurePolicy):
    @classmethod
    def on_failure(cls, plugin, device_dict):
        LOG.error(_('device %s dead'), device_dict['id'])
        attributes = device_dict['attributes'].copy()
        attributes['dead_device_id'] = device_dict['id']
        new_device = {'attributes': attributes}
        for key in ('tenant_id', 'template_id', 'name'):
            new_device[key] = device_dict[key]
        LOG.debug(_('new_device %s'), new_device)

        # keystone v2.0 specific
        auth_url = CONF.keystone_authtoken.auth_uri + '/v2.0'
        authtoken = CONF.keystone_authtoken
        kc = ks_client.Client(
            tenant_name=authtoken.project_name,
            username=authtoken.username,
            password=authtoken.password,
            auth_url=auth_url)
        token = kc.service_catalog.get_token()

        context = t_context.get_admin_context()
        context.tenant_name = authtoken.project_name
        context.user_name = authtoken.username
        context.auth_token = token['id']
        context.tenant_id = token['tenant_id']
        context.user_id = token['user_id']
        new_device_dict = plugin.create_device(context, {'device': new_device})
        LOG.info(_('respawned new device %s'), new_device_dict['id'])


@FailurePolicy.register('respawn', 'heat')
class RespawnHeat(FailurePolicy):
    @classmethod
    def on_failure(cls, plugin, device_dict):
        device_id = device_dict['id']
        LOG.error(_('device %s dead'), device_id)
        attributes = device_dict['attributes']
        config = attributes.get('config')
        LOG.debug(_('device config %s dead'), config)
        failure_count = int(attributes.get('failure_count', '0')) + 1
        failure_count_str = str(failure_count)
        attributes['failure_count'] = failure_count_str
        attributes['dead_instance_id_' + failure_count_str] = device_dict[
            'instance_id']

        new_device_id = device_id + '-RESPAWN-' + failure_count_str
        attributes = device_dict['attributes'].copy()
        attributes['dead_device_id'] = device_id
        new_device = {'id': new_device_id, 'attributes': attributes}
        for key in ('tenant_id', 'template_id', 'name'):
            new_device[key] = device_dict[key]
        LOG.debug(_('new_device %s'), new_device)

        # kill heat stack
        heatclient = heat.HeatClient(None)
        heatclient.delete(device_dict['instance_id'])

        # keystone v2.0 specific
        auth_url = CONF.keystone_authtoken.auth_uri + '/v2.0'
        authtoken = CONF.keystone_authtoken
        kc = ks_client.Client(
            tenant_name=authtoken.project_name,
            username=authtoken.username,
            password=authtoken.password,
            auth_url=auth_url)
        token = kc.service_catalog.get_token()

        context = t_context.get_admin_context()
        context.tenant_name = authtoken.project_name
        context.user_name = authtoken.username
        context.auth_token = token['id']
        context.tenant_id = token['tenant_id']
        context.user_id = token['user_id']

        new_device_dict = plugin.create_device_sync(
            context, {'device': new_device})
        LOG.info(_('respawned new device %s'), new_device_dict['id'])

        # ungly hack to keep id unchanged
        dead_device_id = device_id + '-DEAD-' + failure_count_str
        LOG.debug(_('%(dead)s %(new)s %(cur)s'),
                  {'dead': dead_device_id,
                   'new': new_device_id,
                   'cur': device_id})
        with context.session.begin(subtransactions=True):
            plugin.rename_device_id(context, device_id, dead_device_id)
            plugin.rename_device_id(context, new_device_id, device_id)
        plugin.delete_device(context, dead_device_id)
        new_device_dict['id'] = device_id
        if config:
            new_device_dict.setdefault('attributes', {})['config'] = config
        plugin.config_device(context, new_device_dict)

        plugin.add_device_to_monitor(new_device_dict)


@FailurePolicy.register('log_and_kill')
class LogAndKill(FailurePolicy):
    @classmethod
    def on_failure(cls, plugin, device_dict):
        device_id = device_dict['id']
        LOG.error(_('device %s dead'), device_id)
        plugin.delete_device(t_context.get_admin_context(), device_id)
