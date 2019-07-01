# Copyright 2019 NTT DATA
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from tacker.tests import uuidsentinel


def get_dummy_stack(outputs=True, status='CREATE_COMPELETE'):
    outputs_value = [{}]
    if outputs:
        outputs_value = [{'output_value': '192.168.120.216',
                         'output_key': 'mgmt_ip-VDU1',
                         'description': 'No description given'}]

    dummy_stack = {'parent': None, 'disable_rollback': True,
            'description': 'Demo example\n',
            'deletion_time': None, 'stack_name':
                'vnf-6_3f089d15-0000-4dc0-8519-a613d577a07b',
            'stack_status_reason': 'Stack CREATE completed successfully',
            'creation_time': '2019-02-28T15:17:48Z',
            'outputs': outputs_value,
            'timeout_mins': 10, 'stack_status': status,
            'stack_owner': None,
            'updated_time': None,
            'id': uuidsentinel.instance_id}
    return dummy_stack


def get_dummy_resource(resource_status='CREATE_COMPLETE'):
    return {'resource_name': 'SP1_group',
            'logical_resource_id': 'SP1_group',
            'creation_time': '2019-03-06T08:57:47Z',
            'resource_status_reason': 'state changed',
            'updated_time': '2019-03-06T08:57:47Z',
            'required_by': ['SP1_scale_out', 'SP1_scale_in'],
            'resource_status': resource_status,
            'physical_resource_id': uuidsentinel.stack_id,
            'attributes': {'outputs_list': None, 'refs': None,
                           'refs_map': None, 'outputs': None,
                           'current_size': None, 'mgmt_ip-vdu1': 'test1'},
            'resource_type': 'OS::Heat::AutoScalingGroup'}


def get_dummy_event(resource_status='CREATE_COMPLETE'):
    return {'resource_name': 'SP1_scale_out',
            'event_time': '2019-03-06T05:44:27Z',
            'logical_resource_id': 'SP1_scale_out',
            'resource_status': resource_status,
            'resource_status_reason': 'state changed',
            'id': uuidsentinel.event_id}


def get_dummy_policy_dict():
    return {'instance_id': uuidsentinel.instance_id,
            'vnf': {'attributes': {'scaling_group_names': '{"SP1": "G1"}'},
                    'id': uuidsentinel.vnf_id},
            'name': 'SP1',
            'action': 'out',
            'type': 'tosca.policies.tacker.Scaling',
            'properties': {}}
