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
import time

from oslo_serialization import jsonutils

from tacker.plugins.common import constants as evt_constants
from tacker.tests import constants
from tacker.tests.functional import base


class VnfTestAlarmMonitor(base.BaseTackerTest):

    def _test_vnf_tosca_alarm(self, vnfd_file, vnf_name):
        vnfd_instance, vnf_instance, tosca_dict = self.vnfd_and_vnf_create(
            vnfd_file, vnf_name)

        vnf_id = vnf_instance['vnf']['id']

        def _waiting_time(count):
            self.wait_until_vnf_active(
                vnf_id,
                constants.VNF_CIRROS_CREATE_TIMEOUT,
                constants.ACTIVE_SLEEP_TIME)
            vnf = self.client.show_vnf(vnf_id)['vnf']
            # {"VDU1": ["10.0.0.14", "10.0.0.5"]}
            self.assertEqual(count, len(jsonutils.loads(vnf[
                'mgmt_ip_address'])['VDU1']))

        def _inject_monitoring_policy(vnfd_dict):
            polices = vnfd_dict['topology_template'].get('policies', [])
            mon_policy = dict()
            for policy_dict in polices:
                for name, policy in policy_dict.items():
                    if policy['type'] == constants.POLICY_ALARMING:
                        triggers = policy['triggers']
                        for trigger_name, trigger_dict in triggers.items():
                            policy_action_list = trigger_dict['action']
                            for policy_action_name in policy_action_list:
                                mon_policy[trigger_name] = policy_action_name
            return mon_policy

        def verify_policy(policy_dict, kw_policy):
            for name, action in policy_dict.items():
                if kw_policy in name:
                    return name

        # trigger alarm
        monitoring_policy = _inject_monitoring_policy(tosca_dict)
        for mon_policy_name, mon_policy_action in monitoring_policy.items():
            if mon_policy_action in constants.DEFAULT_ALARM_ACTIONS:
                self.wait_until_vnf_active(
                    vnf_id,
                    constants.VNF_CIRROS_CREATE_TIMEOUT,
                    constants.ACTIVE_SLEEP_TIME)
                self.trigger_vnf(vnf_id, mon_policy_name, mon_policy_action)
            else:
                if 'scaling_out' in mon_policy_name:
                    _waiting_time(2)
                    time.sleep(constants.SCALE_WINDOW_SLEEP_TIME)
                    # scaling-out backend action
                    scaling_out_action = mon_policy_action + '-out'
                    self.trigger_vnf(
                        vnf_id, mon_policy_name, scaling_out_action)

                    _waiting_time(3)

                    scaling_in_name = verify_policy(monitoring_policy,
                                                    kw_policy='scaling_in')
                    if scaling_in_name:
                        time.sleep(constants.SCALE_WINDOW_SLEEP_TIME)
                        # scaling-in backend action
                        scaling_in_action = mon_policy_action + '-in'
                        self.trigger_vnf(
                            vnf_id, scaling_in_name, scaling_in_action)

                        _waiting_time(2)

                    self.verify_vnf_crud_events(
                        vnf_id, evt_constants.RES_EVT_SCALE,
                        evt_constants.ACTIVE, cnt=2)
                    self.verify_vnf_crud_events(
                        vnf_id, evt_constants.RES_EVT_SCALE,
                        evt_constants.PENDING_SCALE_OUT, cnt=1)
                    self.verify_vnf_crud_events(
                        vnf_id, evt_constants.RES_EVT_SCALE,
                        evt_constants.PENDING_SCALE_IN, cnt=1)
        # Delete vnf_instance with vnf_id
        try:
            self.client.delete_vnf(vnf_id)
        except Exception:
            assert False, ("Failed to delete vnf %s after the monitor test" %
                           vnf_id)

        # Verify VNF monitor events captured for states, ACTIVE and DEAD
        vnf_state_list = [evt_constants.ACTIVE, evt_constants.DEAD]
        self.verify_vnf_monitor_events(vnf_id, vnf_state_list)

        # Wait for delete vnf_instance
        self.addCleanup(self.wait_until_vnf_delete, vnf_id,
                        constants.VNF_CIRROS_DELETE_TIMEOUT)

    def test_vnf_alarm_respawn(self):
        self._test_vnf_tosca_alarm(
            'sample-tosca-alarm-respawn.yaml',
            'alarm and respawn-vnf')

    def test_vnf_alarm_scale(self):
        self._test_vnf_tosca_alarm(
            'sample-tosca-alarm-scale.yaml',
            'alarm and scale vnf')
