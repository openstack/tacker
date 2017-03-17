# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tacker import context
from tacker.nfvo.drivers.workflow import mistral
from tacker.tests.unit import base


def get_dummy_ns():
    return {u'ns': {'description': '',
                    'tenant_id': u'a81900a92bda40588c52699e1873a92f',
                    'vim_id': u'96025dd5-ca16-49f3-9823-958eb04260c4',
                    'vnf_ids': '', u'attributes': {},
                    u'nsd_id': u'b8587afb-6099-4f56-abce-572c62e3d61d',
                    u'name': u'test_create_ns'},
            'vnfd_details': {u'vnf1': {'instances': ['VNF1'],
                             'id': u'dec09ed4-f355-4ec8-a00b-8548f6575a80'},
            u'vnf2': {'instances': ['VNF2'],
                      'id': u'9f8f2af7-6407-4f79-a6fe-302c56172231'}},
            'placement_attr': {}}


def get_dummy_param():
    return {u'vnf1': {'substitution_mappings': {u'VL1b8587afb-60': {
            'type': 'tosca.nodes.nfv.VL', 'properties': {
                'network_name': u'net_mgmt',
                'vendor': 'tacker'}}, 'requirements': {
                    'virtualLink2': u'VL2b8587afb-60',
                    'virtualLink1': u'VL1b8587afb-60'}, u'VL2b8587afb-60': {
                        'type': 'tosca.nodes.nfv.VL',
                        'properties': {'network_name': u'net0',
                            'vendor': 'tacker'}}}},
            u'nsd': {u'vl2_name': u'net0', u'vl1_name': u'net_mgmt'}}


def get_dummy_create_workflow():
    return {'std.create_vnf_dummy': {'input': ['vnf'],
                'tasks': {
                    'wait_vnf_active_VNF2': {
                        'action': 'tacker.show_vnf vnf=<% $.vnf_id_VNF2 %>',
                        'retry': {'count': 10, 'delay': 10,
                            'continue-on': '<% $.status_VNF2 = '
                                           '"PENDING_CREATE" %>',
                            'break-on': '<% $.status_VNF2 = "ERROR" %>'},
                        'publish': {
                            'status_VNF2': '<% task(wait_vnf_active_VNF2).'
                                           'result.vnf.status %>',
                            'mgmt_url_VNF2': ' <% task(wait_vnf_active_VNF2).'
                                             'result.vnf.mgmt_url %>'},
                        'on-success': [{
                            'delete_vnf_VNF2': '<% $.status_VNF2='
                                               '"ERROR" %>'}]},
                    'create_vnf_VNF2': {
                        'action': 'tacker.create_vnf body=<% $.vnf.VNF2 %>',
                        'input': {'body': '<% $.vnf.VNF2 %>'},
                        'publish': {
                            'status_VNF2': '<% task(create_vnf_VNF2).'
                                           'result.vnf.status %>',
                            'vim_id_VNF2': '<% task(create_vnf_VNF2).'
                                           'result.vnf.vim_id %>',
                            'mgmt_url_VNF2': '<% task(create_vnf_VNF2).'
                                             'result.vnf.mgmt_url %>',
                            'vnf_id_VNF2': '<% task(create_vnf_VNF2)'
                                           '.result.vnf.id %>'},
                            'on-success': ['wait_vnf_active_VNF2']},
                    'create_vnf_VNF1': {
                        'action': 'tacker.create_vnf body=<% $.vnf.VNF1 %>',
                        'input': {'body': '<% $.vnf.VNF1 %>'},
                        'publish': {
                            'status_VNF1': '<% task(create_vnf_VNF1).'
                                           'result.vnf.status %>',
                            'vnf_id_VNF1': '<% task(create_vnf_VNF1).'
                                           'result.vnf.id %>',
                            'mgmt_url_VNF1': '<% task(create_vnf_VNF1).'
                                             'result.vnf.mgmt_url %>',
                            'vim_id_VNF1': '<% task(create_vnf_VNF1).'
                                           'result.vnf.vim_id %>'},
                        'on-success': ['wait_vnf_active_VNF1']},
                    'wait_vnf_active_VNF1': {
                        'action': 'tacker.show_vnf vnf=<% $.vnf_id_VNF1 %>',
                        'retry': {'count': 10, 'delay': 10,
                            'continue-on': '<% $.status_VNF1 = "PENDING_'
                                           'CREATE" %>',
                            'break-on': '<% $.status_VNF1 = "ERROR" %>'},
                        'publish': {
                            'status_VNF1': '<% task(wait_vnf_active_VNF1).'
                                           'result.vnf.status %>',
                            'mgmt_url_VNF1': ' <% task(wait_vnf_active_VNF1).'
                                             'result.vnf.mgmt_url %>'},
                        'on-success': [{'delete_vnf_VNF1': '<% $.status_VNF1='
                                                           '"ERROR" %>'}]},
                    'delete_vnf_VNF1': {'action': 'tacker.delete_vnf vnf=<% '
                                                  '$.vnf_id_VNF1%>'},
                    'delete_vnf_VNF2': {'action': 'tacker.delete_vnf vnf=<% '
                                                  '$.vnf_id_VNF2%>'}},
                'type': 'direct', 'output': {
                    'status_VNF1': '<% $.status_VNF1 %>',
                    'status_VNF2': '<% $.status_VNF2 %>',
                    'mgmt_url_VNF2': '<% $.mgmt_url_VNF2 %>',
                    'mgmt_url_VNF1': '<% $.mgmt_url_VNF1 %>',
                    'vim_id_VNF2': '<% $.vim_id_VNF2 %>',
                    'vnf_id_VNF1': '<% $.vnf_id_VNF1 %>',
                    'vnf_id_VNF2': '<% $.vnf_id_VNF2 %>',
                    'vim_id_VNF1': '<% $.vim_id_VNF1 %>'}},
            'version': '2.0'}


def dummy_delete_ns_obj():
    return {'vnf_ids': u"{'VNF1': '5de5eca6-3e21-4bbd-a9d7-86458de75f0c'}"}


def get_dummy_delete_workflow():
    return {'version': '2.0',
            'std.delete_vnf_dummy': {'input': ['vnf_id_VNF1'],
                'tasks': {'delete_vnf_VNF1': {
                    'action': 'tacker.delete_vnf vnf=<% $.vnf_id_VNF1%>'}},
                'type': 'direct'}}


class FakeMistral(object):
    def __init__(self):
        pass


class TestMistralClient(base.TestCase):
    def setUp(self):
        super(TestMistralClient, self).setUp()
        self.mistral_client = FakeMistral()

    def test_prepare_workflow_create(self):
        mc = mistral.MistralClient(context, self.mistral_client,
                                   resource='vnf', action='create')
        mc.prepare_workflow(ns=get_dummy_ns(), params=get_dummy_param())
        wf_def_values = [mc.wg.definition[k] for k in mc.wg.definition]
        self.assertIn(get_dummy_create_workflow()['std.create_vnf_dummy'],
                      wf_def_values)
        self.assertEqual(get_dummy_create_workflow()['version'],
                         mc.wg.definition['version'])

    def test_prepare_workflow_delete(self):
        mc = mistral.MistralClient(context, self.mistral_client,
                                   resource='vnf', action='delete')
        mc.prepare_workflow(ns=dummy_delete_ns_obj())
        wf_def_values = [mc.wg.definition[k] for k in mc.wg.definition]
        self.assertIn(get_dummy_delete_workflow()['std.delete_vnf_dummy'],
                      wf_def_values)
        self.assertEqual(get_dummy_delete_workflow()['version'],
                         mc.wg.definition['version'])
