# Copyright 2015 Brocade Communications System, Inc.
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


from tacker.plugins.common import constants as evt_constants
from tacker.tests import constants
from tacker.tests.functional import base


class VnfTestPingMonitor(base.BaseTackerTest):

    def _test_vnf_with_monitoring(self, vnfd_file, vnf_name):
        vnfd_instance, vnf_instance, tosca_dict = self.vnfd_and_vnf_create(
            vnfd_file, vnf_name)

        # Verify vnf goes from ACTIVE->DEAD->ACTIVE states
        self.verify_vnf_restart(vnfd_instance, vnf_instance)

        # Delete vnf_instance with vnf_id
        vnf_id = vnf_instance['vnf']['id']
        try:
            self.client.delete_vnf(vnf_id)
        except Exception:
            assert False, ("Failed to delete vnf %s after the monitor test" %
                           vnf_id)

        # Verify VNF monitor events captured for states, ACTIVE and DEAD
        vnf_state_list = [evt_constants.ACTIVE, evt_constants.DEAD]
        self.verify_vnf_monitor_events(vnf_id, vnf_state_list)

        self.addCleanup(self.wait_until_vnf_delete, vnf_id,
            constants.VNF_CIRROS_DELETE_TIMEOUT)

    def test_create_delete_vnf_monitoring_tosca_template(self):
        self._test_vnf_with_monitoring(
            'sample-tosca-vnfd-monitor.yaml',
            'ping monitor vnf with tosca template')

    def test_create_delete_vnf_multi_vdu_monitoring_tosca_template(self):
        self._test_vnf_with_monitoring(
            'sample-tosca-vnfd-multi-vdu-monitoring.yaml',
            'ping monitor multi vdu vnf with tosca template')

    def _test_vnf_with_monitoring_vdu_autoheal_action(
            self, vnfd_file, vnf_name):
        vnfd_instance, vnf_instance, tosca_dict = self.vnfd_and_vnf_create(
            vnfd_file, vnf_name)
        vnf_id = vnf_instance['vnf']['id']

        self.verify_vnf_update(vnf_id)

        # Delete vnf_instance with vnf_id
        try:
            self.client.delete_vnf(vnf_id)
        except Exception:
            assert False, ("Failed to delete vnf %s after the monitor test" %
                           vnf_id)
        self.addCleanup(self.wait_until_vnf_delete, vnf_id,
                        constants.VNF_CIRROS_DELETE_TIMEOUT)

        params = {'resource_id': vnf_id,
                  'resource_state': 'PENDING_UPDATE',
                  'event_type': evt_constants.RES_EVT_MONITOR}
        vnf_events = self.client.list_vnf_events(**params)
        # Check if vdu_autoheal action emits 4 monitoring events.
        self.assertGreaterEqual(4, len(vnf_events['vnf_events']))

    def test_vnf_monitoring_with_vdu_autoheal_action_for_multi_vdu(self):
        self._test_vnf_with_monitoring_vdu_autoheal_action(
            'sample-tosca-vnfd-multi-vdu-monitoring-vdu-autoheal.yaml',
            'ping multi vdu monitor having vdu_autoheal failure action '
            'with tosca template')

    def test_vnf_monitoring_with_vdu_autoheal_action_for_single_vdu(self):
        self._test_vnf_with_monitoring_vdu_autoheal_action(
            'sample-tosca-vnfd-single-vdu-monitoring-vdu-autoheal.yaml',
            'ping vdu monitor having vdu_autoheal failure action '
            'with tosca template')
