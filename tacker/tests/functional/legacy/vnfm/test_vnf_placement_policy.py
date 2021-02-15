# Copyright 2018 NTT DATA
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
import yaml

from tackerclient.common import exceptions

from tacker.tests import constants
from tacker.tests.functional import base
from tacker.tests.utils import read_file


class VnfTestCreate(base.BaseTackerTest):
    def _test_create_delete_vnf(self, vnf_name, vnfd_name,
                                placement_policy, vdu_name,
                                vnf_expected_status="ACTIVE"):
        input_yaml = read_file(vnfd_name + '.yaml')
        tosca_dict = yaml.safe_load(input_yaml)
        tosca_arg = {'vnfd': {'name': vnfd_name,
                     'attributes': {'vnfd': tosca_dict}}}

        # Create vnfd with tosca template
        vnfd_instance = self.client.create_vnfd(body=tosca_arg)
        self.assertIsNotNone(vnfd_instance)

        # Get vnfd_id
        vnfd_id = vnfd_instance['vnfd']['id']

        # Add vnfd delete to cleanup job so that if vnf_instance fails to
        # create then it will be cleaned-up automatically in tearDown()
        self.addCleanup(self.client.delete_vnfd, vnfd_id)

        vnf_arg = {'vnf': {'vnfd_id': vnfd_id, 'name': vnf_name}}

        # Create vnf instance
        vnf_instance = self.client.create_vnf(body=vnf_arg)
        vnf_id = vnf_instance['vnf']['id']

        # Delete vnf_instance after tearDown
        self.addCleanup(self.wait_until_vnf_delete, vnf_id,
                        constants.VNF_CIRROS_DELETE_TIMEOUT)
        self.addCleanup(self.client.delete_vnf, vnf_id)

        self.validate_vnf_instance(vnfd_instance, vnf_instance)

        self.wait_until_vnf_status(
            vnf_id,
            vnf_expected_status,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)

        # VDU names are random generated names with initials of *vnf_name*.
        # Search the instance_list with *vdu_name* regular expression
        opts = {
            "name": vdu_name
        }
        compute_hosts = []
        vm_statuses = []
        for server in self.novaclient().servers.list(search_opts=opts):
            instance_host = getattr(server,
                                    "OS-EXT-SRV-ATTR:hypervisor_hostname")
            vm_statuses.append(getattr(server, "status"))
            compute_hosts.append(instance_host)

        # check vnf placement policies
        if placement_policy == 'affinity':
            # check "compute_hosts" is not empty
            self.assertTrue(compute_hosts)

            # Get the first compute_host on which VDU is deployed and compare
            # it with other compute hosts of VDU's
            compute_host = compute_hosts[0]
            for vnf in compute_hosts:
                self.assertEqual(compute_host, vnf)
        elif placement_policy == 'anti-affinity':
            if vnf_expected_status == "ERROR":
                # Check one of the VM should be in "ERROR" status
                # and instance host should be None.
                self.assertIn("ERROR", vm_statuses)
                self.assertIn(None, compute_hosts)
            else:
                distinct_comp_hosts = set(compute_hosts)
                self.assertEqual(len(compute_hosts), len(distinct_comp_hosts))

    def test_create_delete_vnf_with_placement_policy_affinity(self):
        self._test_create_delete_vnf(
            vnf_name='test_vnf_with_placement_policy_affinity',
            vnfd_name='sample-tosca-vnfd-placement-policy-affinity',
            vdu_name='affinity-vdu',
            placement_policy='affinity')

    def test_create_delete_vnf_with_placement_policy_anti_affinity(self):
        self._test_create_delete_vnf(
            vnf_name='test_vnf_with_placement_policy_anti_affinity',
            vnfd_name='sample-tosca-vnfd-placement-policy-anti-affinity',
            vdu_name='anti-affinity-vdu-multi-comp-nodes',
            placement_policy='anti-affinity')

    def test_vnf_with_policy_anti_affinity_insufficient_comp_nodes(self):
        self._test_create_delete_vnf(
            vnf_name='test_vnf_anti_affinity_insufficient_comp_nodes',
            vnfd_name='sample-tosca-vnfd-anti-affinity-multi-vdu',
            vdu_name='anti-affinity-vdu-insufficient-comp-nodes',
            placement_policy='anti-affinity',
            vnf_expected_status="ERROR")

    def test_vnf_with_placement_policy_invalid(self):
        exc = self.assertRaises(
            exceptions.InternalServerError,
            self._test_create_delete_vnf,
            vnf_name='test_vnf_with_placement_policy_invalid',
            vnfd_name='sample-tosca-vnfd-placement-policy-invalid',
            vdu_name='invalid-placement-policy-vdu',
            placement_policy='invalid')
        self.assertIn('["invalid"]', exc.message)
        self.assertIn('is not an allowed value ["anti-affinity", "affinity", '
                      '"soft-anti-affinity", "soft-affinity"]', exc.message)
