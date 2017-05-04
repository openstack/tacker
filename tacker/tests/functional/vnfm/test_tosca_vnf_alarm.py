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
import json
import time
import unittest

from tacker.plugins.common import constants as evt_constants
from tacker.tests import constants
from tacker.tests.functional import base
from tacker.tests.utils import read_file

import yaml


class VnfTestAlarmMonitor(base.BaseTackerTest):

    def _test_vnf_tosca_alarm(self, vnfd_file, vnf_name):
        vnf_trigger_path = '/vnfs/%s/triggers'
        data = dict()
        data['tosca'] = read_file(vnfd_file)
        tosca_dict = yaml.safe_load(data['tosca'])
        toscal = data['tosca']
        tosca_arg = {'vnfd': {'name': vnf_name,
                              'attributes': {'vnfd': toscal}}}

        # Create vnfd with tosca template
        vnfd_instance = self.client.create_vnfd(body=tosca_arg)
        self.assertIsNotNone(vnfd_instance)

        # Create vnf with vnfd_id
        vnfd_id = vnfd_instance['vnfd']['id']
        vnf_arg = {'vnf': {'vnfd_id': vnfd_id, 'name': vnf_name}}
        vnf_instance = self.client.create_vnf(body=vnf_arg)

        self.validate_vnf_instance(vnfd_instance, vnf_instance)

        vnf_id = vnf_instance['vnf']['id']

        def _waiting_time(count):
            self.wait_until_vnf_active(
                vnf_id,
                constants.VNF_CIRROS_CREATE_TIMEOUT,
                constants.ACTIVE_SLEEP_TIME)
            vnf = self.client.show_vnf(vnf_id)['vnf']
            # {"VDU1": ["10.0.0.14", "10.0.0.5"]}
            self.assertEqual(count, len(json.loads(vnf['mgmt_url'])['VDU1']))

        def trigger_vnf(vnf, policy_name, policy_action):
            credential = 'g0jtsxu9'
            body = {"trigger": {'policy_name': policy_name,
                                'action_name': policy_action,
                                'params': {
                                    'data': {'alarm_id': '35a80852-e24f-46ed-bd34-e2f831d00172', 'current': 'alarm'},  # noqa
                                    'credential': credential}
                                }
                    }
            self.client.post(vnf_trigger_path % vnf, body)

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
                trigger_vnf(vnf_id, mon_policy_name, mon_policy_action)
            else:
                if 'scaling_out' in mon_policy_name:
                    _waiting_time(2)
                    time.sleep(constants.SCALE_WINDOW_SLEEP_TIME)
                    # scaling-out backend action
                    scaling_out_action = mon_policy_action + '-out'
                    trigger_vnf(vnf_id, mon_policy_name, scaling_out_action)

                    _waiting_time(3)

                    scaling_in_name = verify_policy(monitoring_policy,
                                                    kw_policy='scaling_in')
                    if scaling_in_name:
                        time.sleep(constants.SCALE_WINDOW_SLEEP_TIME)
                        # scaling-in backend action
                        scaling_in_action = mon_policy_action + '-in'
                        trigger_vnf(vnf_id, scaling_in_name, scaling_in_action)

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

        # Delete vnfd_instance
        self.addCleanup(self.client.delete_vnfd, vnfd_id)
        self.addCleanup(self.wait_until_vnf_delete, vnf_id,
                        constants.VNF_CIRROS_DELETE_TIMEOUT)

    def test_vnf_alarm_respawn(self):
        self._test_vnf_tosca_alarm(
            'sample-tosca-alarm-respawn.yaml',
            'alarm and respawn vnf')

    @unittest.skip("Skip and wait for releasing Heat Translator")
    def test_vnf_alarm_scale(self):
        self._test_vnf_tosca_alarm(
            'sample-tosca-alarm-scale.yaml',
            'alarm and scale vnf')
