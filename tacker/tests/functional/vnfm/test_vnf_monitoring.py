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

from tacker.tests.functional import base
from tacker.tests.utils import read_file


class VnfTestPingMonitor(base.BaseTackerTest):

    def _test_vnf_with_monitoring(self, vnfd_file, vnf_name):
        data = dict()
        data['tosca'] = read_file(vnfd_file)
        toscal = data['tosca']
        tosca_arg = {'vnfd': {'attributes': {'vnfd': toscal}}}

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

        # Delete vnfd_instance
        try:
            self.client.delete_vnfd(vnfd_id)
        except Exception:
            assert False, ("Failed to delete vnfd %s after the monitor test" %
                           vnfd_id)

    def test_create_delete_vnf_monitoring(self):
        self._test_vnf_with_monitoring(
            'sample-vnfd-single-vdu-monitoring.yaml',
            'ping monitor vnf')

    def test_create_delete_vnf_http_monitoring(self):
        self._test_vnf_with_monitoring(
            'sample_cirros_http_monitoring.yaml',
            'http monitor vnf')

    def test_create_delete_vnf_multi_vdu_ping_monitoring(self):
        self._test_vnf_with_monitoring(
            'sample-vnfd-multi-vdu-monitoring.yaml',
            'multi vdu ping monitor vnf')

    def test_create_delete_vnf_monitoring_new_template(self):
        self._test_vnf_with_monitoring(
            'sample-vnfd-single-vdu-monitoring-new-template.yaml',
            'ping monitor vnf new template')
