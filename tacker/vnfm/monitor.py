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

import ast
import copy
import inspect
import random
import string
import threading
import time

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import timeutils

from tacker._i18n import _
from tacker.common import driver_manager
from tacker.common import exceptions
from tacker import context as t_context
from tacker.plugins.common import constants
from tacker.vnfm import utils as vnfm_utils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF
OPTS = [
    cfg.IntOpt('check_intvl',
               default=10,
               help=_("check interval for monitor")),
]
CONF.register_opts(OPTS, group='monitor')


def config_opts():
    return [('monitor', OPTS),
            ('tacker', VNFMonitor.OPTS),
            ('tacker', VNFAlarmMonitor.OPTS),
            ('tacker', VNFAppMonitor.OPTS)]


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
                for hosting_vnf in VNFMonitor._hosting_vnfs.values():
                    if hosting_vnf.get('dead', False) or (
                            hosting_vnf['vnf']['status'] ==
                            constants.PENDING_HEAL):
                        LOG.debug(
                            'monitor skips for DEAD/PENDING_HEAL vnf %s',
                            hosting_vnf)
                        continue
                    try:
                        self.run_monitor(hosting_vnf)
                    except Exception as ex:
                        LOG.exception("Unknown exception: Monitoring failed "
                                      "for VNF '%s' due to '%s' ",
                                      hosting_vnf['id'], ex)

    @staticmethod
    def to_hosting_vnf(vnf_dict, action_cb):
        return {
            'id': vnf_dict['id'],
            'mgmt_ip_addresses': jsonutils.loads(
                vnf_dict['mgmt_ip_address']),
            'action_cb': action_cb,
            'vnf': vnf_dict,
            'monitoring_policy': jsonutils.loads(
                vnf_dict['attributes']['monitoring_policy'])
        }

    def add_hosting_vnf(self, new_vnf):
        LOG.debug('Adding host %(id)s, Mgmt IP %(ips)s',
                  {'id': new_vnf['id'],
                   'ips': new_vnf['mgmt_ip_addresses']})
        new_vnf['boot_at'] = timeutils.utcnow()
        with self._lock:
            VNFMonitor._hosting_vnfs[new_vnf['id']] = new_vnf

        attrib_dict = new_vnf['vnf']['attributes']
        mon_policy_dict = attrib_dict['monitoring_policy']
        evt_details = (("VNF added for monitoring. "
                        "mon_policy_dict = %s,") % (mon_policy_dict))
        vnfm_utils.log_events(t_context.get_admin_context(),
                              new_vnf['vnf'],
                              constants.RES_EVT_MONITOR, evt_details)

    def delete_hosting_vnf(self, vnf_id):
        LOG.debug('deleting vnf_id %(vnf_id)s', {'vnf_id': vnf_id})
        with self._lock:
            hosting_vnf = VNFMonitor._hosting_vnfs.pop(vnf_id, None)
            if hosting_vnf:
                LOG.debug('deleting vnf_id %(vnf_id)s, Mgmt IP %(ips)s',
                          {'vnf_id': vnf_id,
                           'ips': hosting_vnf['mgmt_ip_addresses']})

    def update_hosting_vnf(self, updated_vnf_dict, evt_details=None):
        with self._lock:
            vnf_to_update = VNFMonitor._hosting_vnfs.get(
                updated_vnf_dict.get('id'))
            if vnf_to_update:
                updated_vnf = copy.deepcopy(updated_vnf_dict)
                vnf_to_update['vnf'] = updated_vnf
                vnf_to_update['mgmt_ip_addresses'] = jsonutils.loads(
                    updated_vnf_dict['mgmt_ip_address'])

                if evt_details is not None:
                    vnfm_utils.log_events(t_context.get_admin_context(),
                                          vnf_to_update['vnf'],
                                          constants.RES_EVT_HEAL,
                                          evt_details=evt_details)

    def run_monitor(self, hosting_vnf):
        mgmt_ips = hosting_vnf['mgmt_ip_addresses']
        vdupolicies = hosting_vnf['monitoring_policy']['vdus']

        vnf_delay = hosting_vnf['monitoring_policy'].get(
            'monitoring_delay', self.boot_wait)

        for vdu in vdupolicies:
            if hosting_vnf.get('dead') or (
                    hosting_vnf['vnf']['status']) == constants.PENDING_HEAL:
                return

            policy = vdupolicies[vdu]
            for driver in policy:
                params = policy[driver].get('monitoring_params', {})

                vdu_delay = params.get('monitoring_delay', vnf_delay)

                if not timeutils.is_older_than(hosting_vnf['boot_at'],
                                               vdu_delay):
                    continue

                actions = policy[driver].get('actions', {})
                params['mgmt_ip'] = mgmt_ips[vdu]

                driver_return = self.monitor_call(driver,
                                                  hosting_vnf['vnf'],
                                                  params)

                LOG.debug('driver_return %s', driver_return)

                if driver_return in actions:
                    action = actions[driver_return]
                    hosting_vnf['action_cb'](action, vdu_name=vdu)

    def mark_dead(self, vnf_id):
        VNFMonitor._hosting_vnfs[vnf_id]['dead'] = True

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


class VNFAppMonitor(object):
    """VNF App monitor"""
    OPTS = [
        cfg.ListOpt(
            'app_monitor_driver', default=['zabbix'],
            help=_('App monitoring driver to communicate with '
                   'Hosting VNF/logical service '
                   'instance tacker plugin will use')),
    ]
    cfg.CONF.register_opts(OPTS, 'tacker')

    def __init__(self):
        self._application_monitor_manager = driver_manager.DriverManager(
            'tacker.tacker.app_monitor.drivers',
            cfg.CONF.tacker.app_monitor_driver)

    def _create_app_monitoring_dict(self, dev_attrs, mgmt_ip_address):
        app_policy = 'app_monitoring_policy'
        appmonitoring_dict = ast.literal_eval(dev_attrs[app_policy])
        vdulist = appmonitoring_dict['vdus'].keys()

        for vduname in vdulist:
            temp = ast.literal_eval(mgmt_ip_address)
            appmonitoring_dict['vdus'][vduname]['mgmt_ip'] = temp[vduname]
        return appmonitoring_dict

    def create_app_dict(self, context, vnf_dict):
        dev_attrs = vnf_dict['attributes']
        mgmt_ip_address = vnf_dict['mgmt_ip_address']
        return self._create_app_monitoring_dict(dev_attrs, mgmt_ip_address)

    def _invoke(self, driver, **kwargs):
        method = inspect.stack()[1][3]
        return self._application_monitor_manager.\
            invoke(driver, method, **kwargs)

    def add_to_appmonitor(self, applicationvnfdict, vnf_dict):
        vdunode = applicationvnfdict['vdus'].keys()
        driver = applicationvnfdict['vdus'][vdunode[0]]['name']
        kwargs = applicationvnfdict
        return self._invoke(driver, vnf=vnf_dict, kwargs=kwargs)


class VNFAlarmMonitor(object):
    """VNF Alarm monitor"""
    OPTS = [
        cfg.ListOpt(
            'alarm_monitor_driver', default=['ceilometer'],
            help=_('Alarm monitoring driver to communicate with '
                   'Hosting VNF/logical service '
                   'instance tacker plugin will use')),
    ]
    cfg.CONF.register_opts(OPTS, 'tacker')

    # get alarm here
    def __init__(self):
        self._alarm_monitor_manager = driver_manager.DriverManager(
            'tacker.tacker.alarm_monitor.drivers',
            cfg.CONF.tacker.alarm_monitor_driver)

    def update_vnf_with_alarm(self, plugin, context, vnf, policy_dict):
        triggers = policy_dict['triggers']
        alarm_url = dict()
        for trigger_name, trigger_dict in triggers.items():
            params = dict()
            params['vnf_id'] = vnf['id']
            params['mon_policy_name'] = trigger_name
            driver = trigger_dict['event_type']['implementation']
            # TODO(Tung Doan) trigger_dict.get('actions') needs to be used
            policy_action = trigger_dict.get('action')
            if len(policy_action) == 0:
                vnfm_utils.log_events(t_context.get_admin_context(), vnf,
                                      constants.RES_EVT_MONITOR,
                                      "Alarm not set: policy action missing")
                return
            # Other backend policies with the construct (policy, action)
            # ex: (SP1, in), (SP1, out)

            def _refactor_backend_policy(bk_policy_name, bk_action_name):
                policy = '%(policy_name)s-%(action_name)s' % {
                    'policy_name': bk_policy_name,
                    'action_name': bk_action_name}
                return policy

            for index, policy_action_name in enumerate(policy_action):
                filters = {'name': policy_action_name}
                bkend_policies =\
                    plugin.get_vnf_policies(context, vnf['id'], filters)
                if bkend_policies:
                    bkend_policy = bkend_policies[0]
                    if bkend_policy['type'] == constants.POLICY_SCALING:
                        cp = trigger_dict['condition'].\
                            get('comparison_operator')
                        scaling_type = 'out' if cp == 'gt' else 'in'
                        policy_action[index] = _refactor_backend_policy(
                            policy_action_name, scaling_type)

            # Support multiple action. Ex: respawn % notify
            action_name = '%'.join(policy_action)

            params['mon_policy_action'] = action_name
            alarm_url[trigger_name] =\
                self.call_alarm_url(driver, vnf, params)
            details = "Alarm URL set successfully: %s" % alarm_url
            vnfm_utils.log_events(t_context.get_admin_context(), vnf,
                                  constants.RES_EVT_MONITOR, details)
        return alarm_url

    def process_alarm_for_vnf(self, vnf, trigger):
        """call in plugin"""
        params = trigger['params']
        mon_prop = trigger['trigger']
        alarm_dict = dict()
        alarm_dict['alarm_id'] = params['data'].get('alarm_id')
        alarm_dict['status'] = params['data'].get('current')
        trigger_name, trigger_dict = list(mon_prop.items())[0]
        driver = trigger_dict['event_type']['implementation']
        return self.process_alarm(driver, vnf, alarm_dict)

    def _invoke(self, driver, **kwargs):
        method = inspect.stack()[1][3]
        return self._alarm_monitor_manager.invoke(
            driver, method, **kwargs)

    def call_alarm_url(self, driver, vnf_dict, kwargs):
        return self._invoke(driver,
                            vnf=vnf_dict, kwargs=kwargs)

    def process_alarm(self, driver, vnf_dict, kwargs):
        return self._invoke(driver,
                            vnf=vnf_dict, kwargs=kwargs)


class VNFReservationAlarmMonitor(VNFAlarmMonitor):
    """VNF Reservation Alarm monitor"""

    def update_vnf_with_reservation(self, plugin, context, vnf, policy_dict):

        alarm_url = dict()

        def create_alarm_action(action, action_list, scaling_type):
            params = dict()
            params['vnf_id'] = vnf['id']
            params['mon_policy_name'] = action
            driver = 'ceilometer'

            def _refactor_backend_policy(bk_policy_name, bk_action_name):
                policy = '%(policy_name)s%(action_name)s' % {
                    'policy_name': bk_policy_name,
                    'action_name': bk_action_name}
                return policy

            for index, policy_action_name in enumerate(action_list):
                filters = {'name': policy_action_name}
                bkend_policies = \
                    plugin.get_vnf_policies(context, vnf['id'], filters)
                if bkend_policies:
                    if constants.POLICY_SCALING in str(bkend_policies[0]):
                        action_list[index] = _refactor_backend_policy(
                            policy_action_name, scaling_type)

                # Support multiple action. Ex: respawn % notify
                action_name = '%'.join(action_list)
                params['mon_policy_action'] = action_name
                alarm_url[action] = \
                    self.call_alarm_url(driver, vnf, params)
                details = "Alarm URL set successfully: %s" % alarm_url
                vnfm_utils.log_events(t_context.get_admin_context(), vnf,
                                      constants.RES_EVT_MONITOR,
                                      details)

        before_end_action = policy_dict['reservation']['before_end_actions']
        end_action = policy_dict['reservation']['end_actions']
        start_action = policy_dict['reservation']['start_actions']

        scaling_policies = \
            plugin.get_vnf_policies(
                context, vnf['id'], filters={
                    'type': constants.POLICY_SCALING})

        if len(scaling_policies) == 0:
            raise exceptions.VnfPolicyNotFound(
                policy=constants.POLICY_SCALING, vnf_id=vnf['id'])

        for scaling_policy in scaling_policies:
            # validating start_action for scale-out policy action
            if scaling_policy['name'] not in start_action:
                raise exceptions.Invalid(
                    'Not a valid template: start_action must contain'
                    ' %s as scaling-out action' % scaling_policy['name'])

            # validating before_end and end_actions for scale-in policy action
            if scaling_policy['name'] not in before_end_action:
                if scaling_policy['name'] not in end_action:
                    raise exceptions.Invalid(
                        'Not a valid template:'
                        ' before_end_action or end_action'
                        ' should contain scaling policy: %s'
                        % scaling_policy['name'])

        for action in constants.RESERVATION_POLICY_ACTIONS:
            scaling_type = "-out" if action == 'start_actions' else "-in"
            create_alarm_action(action, policy_dict[
                'reservation'][action], scaling_type)

        return alarm_url

    def process_alarm_for_vnf(self, vnf, trigger):
        """call in plugin"""
        params = trigger['params']
        alarm_dict = dict()
        alarm_dict['alarm_id'] = params['data'].get('alarm_id')
        alarm_dict['status'] = params['data'].get('current')
        driver = 'ceilometer'
        return self.process_alarm(driver, vnf, alarm_dict)


class VNFMaintenanceAlarmMonitor(VNFAlarmMonitor):
    """VNF Maintenance Alarm monitor"""

    def update_vnf_with_maintenance(self, vnf, vdu_names):
        maintenance = dict()
        vdus = dict()
        params = dict()
        params['vnf_id'] = vnf['id']
        params['mon_policy_name'] = 'maintenance'
        params['mon_policy_action'] = vnf['tenant_id']
        driver = 'ceilometer'

        url = self.call_alarm_url(driver, vnf, params)
        maintenance['url'] = url[:url.rindex('/')]
        vdu_names.append('ALL')
        for vdu in vdu_names:
            access_key = ''.join(
                random.SystemRandom().choice(
                    string.ascii_lowercase + string.digits)
                for _ in range(8))
            vdus[vdu] = access_key
        maintenance.update({'vdus': vdus})
        details = "Alarm URL set successfully: %s" % maintenance['url']
        vnfm_utils.log_events(t_context.get_admin_context(), vnf,
                              constants.RES_EVT_MONITOR, details)
        return maintenance

    def process_alarm_for_vnf(self, vnf, trigger):
        """call in plugin"""
        params = trigger['params']
        alarm_dict = dict()
        alarm_dict['alarm_id'] = params['data'].get('alarm_id')
        alarm_dict['status'] = params['data'].get('current')
        driver = 'ceilometer'
        return self.process_alarm(driver, vnf, alarm_dict)
