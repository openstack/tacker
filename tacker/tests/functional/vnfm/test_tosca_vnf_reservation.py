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
import time

import datetime
import json
import testtools
import yaml

from blazarclient import exception
from tacker.plugins.common import constants as evt_constants
from tacker.tests import constants
from tacker.tests.functional import base
from tacker.tests.utils import read_file


HYPERVISORS = []


def hypervisors():
    global HYPERVISORS
    client = base.BaseTackerTest.novaclient()
    hypervisor_list = client.hypervisors.list()
    for hypervisor in hypervisor_list:
        if hypervisor.running_vms == 0:
            HYPERVISORS.append(hypervisor)
    return HYPERVISORS


class VnfTestReservationMonitor(base.BaseTackerTest):

    def _test_vnf_tosca_reservation(self, vnfd_file, vnf_name,
                              lease_id, param_values=None):
        input_yaml = read_file(vnfd_file)
        tosca_dict = yaml.safe_load(input_yaml)

        # TODO(niraj-singh): It's not possible to pass parameters through
        # parameter file due to Bug #1799683. Once this bug is fixed, no need
        # to update vnfd yaml.
        vdu_prop = tosca_dict['topology_template']['node_templates']['VDU1']
        vdu_prop['properties']['flavor'] = param_values.get('flavor')
        vdu_prop['properties']['reservation_metadata']['id'] =\
            param_values.get('server_group_id')
        vdu_prop['properties']['reservation_metadata']['resource_type'] =\
            param_values.get('resource_type')
        policies = tosca_dict['topology_template']['policies']
        policies[0]['RSV']['reservation']['properties']['lease_id'] =\
            param_values.get('lease_id')

        tosca_arg = {'vnfd': {'name': vnf_name,
                              'attributes': {'vnfd': tosca_dict}}}
        blazarclient = self.blazarclient()

        # Create vnfd with tosca template
        vnfd_instance = self.client.create_vnfd(body=tosca_arg)
        self.assertIsNotNone(vnfd_instance)

        # Create vnf with vnfd_id
        vnfd_id = vnfd_instance['vnfd']['id']
        self.addCleanup(self.client.delete_vnfd, vnfd_id)

        vnf_arg = {'vnf': {'vnfd_id': vnfd_id, 'name': vnf_name}}
        vnf_instance = self.client.create_vnf(body=vnf_arg)

        self.validate_vnf_instance(vnfd_instance, vnf_instance)

        vnf_id = vnf_instance['vnf']['id']

        def _get_reservation_policy(vnfd_dict):
            policies = vnfd_dict['topology_template'].get('policies', [])
            res_policy = dict()
            for policy_dict in policies:
                for name, policy in policy_dict.items():
                    if policy['type'] == constants.POLICY_RESERVATION:
                        reservations = policy['reservation']
                        for reserv_key, reserv_value in reservations.items():
                            if reserv_key == 'properties':
                                continue
                            for policy_action in reserv_value:
                                res_policy[reserv_key] = policy_action
            return res_policy

        def _check_lease_event_status():
            lease_event_status = _verify_and_get_lease_event_status()
            self.assertEqual(lease_event_status, constants.LEASE_EVENT_STATUS,
                             "Lease %(lease_id)s with status %(status)s is"
                             " expected to be %(target)s" %
                             {"lease_id": lease_id,
                              "status": lease_event_status,
                              "target": constants.LEASE_EVENT_STATUS})

        def _verify_and_get_lease_event_status():
            start_time = int(time.time())
            while ((int(time.time()) - start_time) <
                   constants.LEASE_CHECK_EVENT_TIMEOUT):
                lease_detail = blazarclient.lease.get(lease_id)
                lease_events = lease_detail.get('events')
                for event in lease_events:
                    lease_event_status = event.get('status')
                    if ((event.get('event_type') ==
                         constants.START_LEASE_EVET_TYPE) and (
                            lease_event_status ==
                            constants.LEASE_EVENT_STATUS)):
                        return lease_event_status
                time.sleep(constants.LEASE_CHECK_SLEEP_TIME)

        def _wait_vnf_active_and_assert_vdu_count(vdu_count, scale_type=None):
            self.wait_until_vnf_active(
                vnf_id,
                constants.VNF_CIRROS_CREATE_TIMEOUT,
                constants.ACTIVE_SLEEP_TIME)

            vnf = self.client.show_vnf(vnf_id)['vnf']
            # {"VDU1": ["10.0.0.14", "10.0.0.5"]}
            if scale_type == 'scaling-in' and vdu_count == 0:
                try:
                    # After sacling-in the vnf['mgmt_ip_address'] will be the
                    # list containg null values. As vnf['mgmt_ip_address']
                    # is string so we can not access ip address list for VDU1
                    # so converting that into the dict using ast lib.
                    # If the list contains the null value then it will raise
                    # ValueError so on the basis of that we are confirming the
                    # scaling-in is successful.
                    ast.literal_eval(vnf['mgmt_ip_address'])
                    self.fail("Scaling-in should not contain "
                              "mgmt_ip_address")
                except ValueError:
                    assert True, ("Management Ip address list for VDU1 "
                                  "contains null values.")
            elif scale_type == 'scaling-out':
                self.assertEqual(vdu_count, len(json.loads(
                    vnf['mgmt_ip_address'])['VDU1']))
            elif vdu_count == 0 and scale_type is None:
                self.assertIsNone(vnf['mgmt_ip_address'])

        reservation_policy = _get_reservation_policy(tosca_dict)
        _wait_vnf_active_and_assert_vdu_count(0)

        # trigger alarm for start action
        start_action = reservation_policy.get('start_actions')
        scaling_out_action = start_action + '-out'
        _check_lease_event_status()
        # scaling-out action
        self.trigger_vnf(vnf_id, 'start_actions', scaling_out_action)
        time.sleep(constants.SCALE_SLEEP_TIME)
        # checking VDU's count after scaling out
        _wait_vnf_active_and_assert_vdu_count(2, scale_type='scaling-out')
        time.sleep(constants.SCALE_WINDOW_SLEEP_TIME)

        # trigger alarm for before end action
        before_end_action = reservation_policy.get('before_end_actions')
        scaling_in_action = before_end_action + '-in'

        # scaling-in action
        self.trigger_vnf(vnf_id, 'before_end_actions', scaling_in_action)
        time.sleep(constants.SCALE_SLEEP_TIME)
        # checking VDU's count after scaling in
        _wait_vnf_active_and_assert_vdu_count(0, scale_type='scaling-in')

        self.verify_vnf_crud_events(
            vnf_id, evt_constants.RES_EVT_SCALE,
            evt_constants.ACTIVE, cnt=2)
        self.verify_vnf_crud_events(
            vnf_id, evt_constants.RES_EVT_SCALE,
            evt_constants.PENDING_SCALE_OUT, cnt=1)
        self.verify_vnf_crud_events(
            vnf_id, evt_constants.RES_EVT_SCALE,
            evt_constants.PENDING_SCALE_IN, cnt=1)

        try:
            self.client.delete_vnf(vnf_id)
        except Exception:
            assert False, (
                "Failed to delete vnf %s after the reservation test" % vnf_id)
        # Wait for delete vnf_instance
        self.addCleanup(self.wait_until_vnf_delete, vnf_id,
                        constants.VNF_CIRROS_DELETE_TIMEOUT)

    def _get_instance_reservation(self):
        blazarclient = self.blazarclient()
        reservations = [{'disk_gb': 0,
                         'vcpus': 1, 'memory_mb': 1,
                         'amount': 1, 'affinity': False,
                         'resource_properties': '',
                         'resource_type': 'virtual:instance'}]
        events = []

        start_date = (datetime.datetime.utcnow() + datetime.timedelta(
            minutes=2)).strftime("%Y-%m-%d %H:%M")
        end_date = (datetime.datetime.utcnow() + datetime.timedelta(
            minutes=30)).strftime("%Y-%m-%d %H:%M")
        host_added = False
        for hypervisor in HYPERVISORS:
            try:
                blazar_host = blazarclient.host.create(
                    hypervisor.hypervisor_hostname)
                host_added = True
            except exception.BlazarClientException:
                pass

        if not host_added:
            self.skipTest("Skip test as Blazar failed to create host from one"
                          " of available hypervisors '%s' as it found some"
                          " instances were running on them" %
                          ",".join([hypervisor.hypervisor_hostname
                                    for hypervisor in HYPERVISORS]))
        instance_reservation = blazarclient.lease.create(
            'test-reservation', start_date, end_date, reservations, events)

        self.addCleanup(
            blazarclient.host.delete, blazar_host.get('id'))
        self.addCleanup(
            blazarclient.lease.delete, instance_reservation['id'])

        return instance_reservation, blazar_host

    @testtools.skipIf(len(hypervisors()) == 0,
                      'Skip test as there are no'
                      ' hypervisors available in nova')
    def test_vnf_alarm_scale_with_instance_reservation(self):
        instance_reservation, blazar_host = self._get_instance_reservation()
        lease_id = str(instance_reservation['reservations'][0]['lease_id'])
        flavor_id = str(instance_reservation['reservations'][0]['flavor_id'])
        server_group_id = str(
            instance_reservation['reservations'][0]['server_group_id'])
        param_to_create_lease = {'lease_id': lease_id,
                                 'flavor': flavor_id,
                                 'server_group_id': server_group_id,
                                 'resource_type': 'virtual_instance'}
        self._test_vnf_tosca_reservation(
            'sample-tosca-vnfd-instance-reservation.yaml',
            'VNFD1', lease_id, param_to_create_lease)
