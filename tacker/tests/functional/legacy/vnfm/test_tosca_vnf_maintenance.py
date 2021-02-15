#    Copyright 2020 Distributed Cloud and Network (DCN)
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

from datetime import datetime
import time
import yaml

from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from tacker.plugins.common import constants as evt_constants
from tacker.tests import constants
from tacker.tests.functional import base
from tacker.tests.utils import read_file


class VnfTestMaintenanceMonitor(base.BaseTackerTest):

    def _test_vnf_tosca_maintenance(self, vnfd_file, vnf_name):
        input_yaml = read_file(vnfd_file)
        tosca_dict = yaml.safe_load(input_yaml)
        tosca_arg = {'vnfd': {'name': vnf_name,
                              'attributes': {'vnfd': tosca_dict}}}

        # Create vnfd with tosca template
        vnfd_instance = self.client.create_vnfd(body=tosca_arg)
        self.assertIsNotNone(vnfd_instance)

        # Create vnf with vnfd_id
        vnfd_id = vnfd_instance['vnfd']['id']
        vnf_arg = {'vnf': {'vnfd_id': vnfd_id, 'name': vnf_name}}
        vnf_instance = self.client.create_vnf(body=vnf_arg)
        vnf_id = vnf_instance['vnf']['id']

        self.validate_vnf_instance(vnfd_instance, vnf_instance)

        def _wait_vnf_active_and_assert_vdu_count(vdu_count, scale_type=None):
            self.wait_until_vnf_active(
                vnf_id,
                constants.VNF_CIRROS_CREATE_TIMEOUT,
                constants.ACTIVE_SLEEP_TIME)

            vnf = self.client.show_vnf(vnf_id)['vnf']
            self.assertEqual(vdu_count, len(jsonutils.loads(
                vnf['mgmt_ip_address'])['VDU1']))

        def _verify_maintenance_attributes(vnf_dict):
            vnf_attrs = vnf_dict.get('attributes', {})
            maintenance_vdus = vnf_attrs.get('maintenance', '{}')
            maintenance_vdus = jsonutils.loads(maintenance_vdus)
            maintenance_url = vnf_attrs.get('maintenance_url', '')
            words = maintenance_url.split('/')

            self.assertEqual(len(maintenance_vdus.keys()), 2)
            self.assertEqual(len(words), 8)
            self.assertEqual(words[5], vnf_dict['id'])
            self.assertEqual(words[7], vnf_dict['tenant_id'])

            maintenance_urls = {}
            for vdu, access_key in maintenance_vdus.items():
                maintenance_urls[vdu] = maintenance_url + '/' + access_key
            return maintenance_urls

        def _verify_maintenance_alarm(url, project_id):
            aodh_client = self.aodh_http_client()
            alarm_query = {
                'and': [
                    {'=': {'project_id': project_id}},
                    {'=~': {'alarm_actions': url}}]}

            # Check alarm instance for MAINTENANCE_ALL
            alarm_url = 'v2/query/alarms'
            encoded_data = jsonutils.dumps(alarm_query)
            encoded_body = jsonutils.dumps({'filter': encoded_data})
            resp, response_body = aodh_client.do_request(alarm_url, 'POST',
                                                         body=encoded_body)
            self.assertEqual(len(response_body), 1)
            alarm_dict = response_body[0]
            self.assertEqual(url, alarm_dict.get('alarm_actions', [])[0])
            return response_body[0]

        def _verify_maintenance_actions(vnf_dict, alarm_dict):
            tacker_client = self.tacker_http_client()
            alarm_url = alarm_dict.get('alarm_actions', [])[0]
            tacker_url = '/%s' % alarm_url[alarm_url.find('v1.0'):]

            def _request_maintenance_action(state):
                alarm_body = _create_alarm_data(vnf_dict, alarm_dict, state)
                resp, response_body = tacker_client.do_request(
                    tacker_url, 'POST', body=alarm_body)

                time.sleep(constants.SCALE_SLEEP_TIME)
                target_scaled = -1
                if state == 'SCALE_IN':
                    target_scaled = 1
                    _wait_vnf_active_and_assert_vdu_count(2, scale_type='in')
                elif state == 'MAINTENANCE_COMPLETE':
                    target_scaled = 0
                    _wait_vnf_active_and_assert_vdu_count(3, scale_type='out')

                updated_vnf = self.client.show_vnf(vnf_id)['vnf']
                scaled = updated_vnf['attributes'].get('maintenance_scaled',
                                                       '-1')
                self.assertEqual(int(scaled), target_scaled)
                time.sleep(constants.SCALE_WINDOW_SLEEP_TIME)

            time.sleep(constants.SCALE_WINDOW_SLEEP_TIME)
            _request_maintenance_action('SCALE_IN')
            _request_maintenance_action('MAINTENANCE_COMPLETE')

            self.verify_vnf_crud_events(
                vnf_id, evt_constants.RES_EVT_SCALE,
                evt_constants.ACTIVE, cnt=2)
            self.verify_vnf_crud_events(
                vnf_id, evt_constants.RES_EVT_SCALE,
                evt_constants.PENDING_SCALE_OUT, cnt=1)
            self.verify_vnf_crud_events(
                vnf_id, evt_constants.RES_EVT_SCALE,
                evt_constants.PENDING_SCALE_IN, cnt=1)

        def _create_alarm_data(vnf_dict, alarm_dict, state):
            '''This function creates a raw payload of alarm to trigger Tacker directly.

            This function creates a raw payload which Fenix will put
            when Fenix process maintenance procedures. Alarm_receiver and
            specific steps of Fenix workflow will be tested by sending the raw
            to Tacker directly.
            '''
            utc_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            fake_url = 'http://localhost/'
            sample_data = {
                'alarm_name': alarm_dict['name'],
                'alarm_id': alarm_dict['alarm_id'],
                'severity': 'low',
                'previous': 'alarm',
                'current': 'alarm',
                'reason': 'Alarm test for Tacker functional test',
                'reason_data': {
                    'type': 'event',
                    'event': {
                        'message_id': uuidutils.generate_uuid(),
                        'event_type': 'maintenance.scheduled',
                        'generated': utc_time,
                        'traits': [
                            ['project_id', 1, vnf_dict['tenant_id']],
                            ['allowed_actions', 1, '[]'],
                            ['instance_ids', 1, fake_url],
                            ['reply_url', 1, fake_url],
                            ['state', 1, state],
                            ['session_id', 1, uuidutils.generate_uuid()],
                            ['actions_at', 4, utc_time],
                            ['reply_at', 4, utc_time],
                            ['metadata', 1, '{}']
                        ],
                        'raw': {},
                        'message_signature': uuidutils.generate_uuid()
                    }
                }
            }
            return jsonutils.dumps(sample_data)

        _wait_vnf_active_and_assert_vdu_count(3)
        urls = _verify_maintenance_attributes(vnf_instance['vnf'])

        maintenance_url = urls.get('ALL', '')
        project_id = vnf_instance['vnf']['tenant_id']
        alarm_dict = _verify_maintenance_alarm(maintenance_url, project_id)
        _verify_maintenance_actions(vnf_instance['vnf'], alarm_dict)

        try:
            self.client.delete_vnf(vnf_id)
        except Exception:
            assert False, (
                'Failed to delete vnf %s after the maintenance test' % vnf_id)
        self.addCleanup(self.client.delete_vnfd, vnfd_id)
        self.addCleanup(self.wait_until_vnf_delete, vnf_id,
                        constants.VNF_CIRROS_DELETE_TIMEOUT)

    def test_vnf_alarm_maintenance(self):
        # instance_maintenance = self._get_instance_maintenance()
        self._test_vnf_tosca_maintenance(
            'sample-tosca-vnfd-maintenance.yaml',
            'maintenance_vnf')
