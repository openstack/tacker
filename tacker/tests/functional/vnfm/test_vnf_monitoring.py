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
from tacker.tests.utils import read_file


class VnfTestPingMonitor(base.BaseTackerTest):

    def _test_vnf_with_monitoring(self, vnfd_file, vnf_name):
        data = dict()
        data['tosca'] = read_file(vnfd_file)
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

        # Delete vnfd_instance
        self.addCleanup(self.client.delete_vnfd, vnfd_id)
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
