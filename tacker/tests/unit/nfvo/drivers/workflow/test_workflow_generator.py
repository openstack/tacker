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
from tacker.nfvo.drivers.workflow import workflow_generator
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


def get_dummy_vnffg_ns():
    return {
        u'ns': {
            'description': '',
            'vim_id': u'96025dd5-ca16-49f3-9823-958eb04260c4',
            'vnf_ids': '', u'attributes': {},
            u'nsd_id': u'b8587afb-6099-4f56-abce-572c62e3d61d',
            u'name': u'test_create_ns'},
        'vnfd_details': {
            u'vnf1': {'instances': ['VNF1'],
                      'id': u'dec09ed4-f355-4ec8-a00b-8548f6575a80'},
            u'vnf2': {'instances': ['VNF2'],
                      'id': u'9f8f2af7-6407-4f79-a6fe-302c56172231'}},
        'placement_attr': {},
        'vnffgd_templates': {
            'VNFFG1': {
                'tosca_definitions_version':
                    'tosca_simple_profile_for_nfv_1_0_0',
                'description': 'VNFFG1 descriptor',
                'topology_template': {
                    'node_templates': {
                        'Forwarding_path1': {
                            'type': 'tosca.nodes.nfv.FP.TackerV2',
                            'description': 'creates path inside ns - test',
                            'properties': {
                                'policy': {
                                    'type': 'ACL',
                                    'criteria': [{
                                        'classifier': {
                                            'ip_proto': 6,
                                            'network_src_port_id': {
                                                'get_input': 'net_src_port_id'
                                            },
                                            'ip_dst_prefix': {
                                                'get_input': 'ip_dest_prefix'
                                            },
                                            'destination_port_range': '80-1024'
                                        },
                                        'name': 'block_tcp'}]},
                                'path': [
                                    {'capability': 'CP12',
                                     'forwarder': 'vnf1'},
                                    {'capability': 'CP22',
                                     'forwarder': 'vnf2'}],
                                'id': 51}}},
                    'groups': {
                        'VNFFG1': {
                            'type': 'tosca.groups.nfv.VNFFG',
                            'description': 'HTTP to Corporate Net',
                            'members': ['Forwarding_path1'],
                            'properties': {
                                'version': 1.0,
                                'vendor': 'tacker',
                                'constituent_vnfs': ['vnf1', 'vnf2'],
                                'connection_point': ['CP12', 'CP22'],
                                'number_of_endpoints': 2,
                                'dependent_virtual_link': ['VL1', 'VL2']}
                        }
                    }
                }
            }
        }
    }


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
    return {'std.create_ns_dummy': {'input': ['ns'],
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
                            'mgmt_ip_address_VNF2': ' <% task('
                                                    'wait_vnf_active_VNF2).'
                                                    'result.vnf.'
                                                    'mgmt_ip_address %>'},
                        'on-success': [{
                            'delete_vnf_VNF2': '<% $.status_VNF2='
                                               '"ERROR" %>'}]},
                    'create_ns_VNF2': {
                        'action': 'tacker.create_vnf body=<% $.ns.VNF2 %>',
                        'input': {'body': '<% $.ns.VNF2 %>'},
                        'publish': {
                            'status_VNF2': '<% task(create_ns_VNF2).'
                                           'result.vnf.status %>',
                            'vim_id_VNF2': '<% task(create_ns_VNF2).'
                                           'result.vnf.vim_id %>',
                            'mgmt_ip_address_VNF2': '<% task('
                                                    'create_ns_VNF2).'
                                                    'result.vnf.'
                                                    'mgmt_ip_address %>',
                            'vnf_id_VNF2': '<% task(create_ns_VNF2)'
                                           '.result.vnf.id %>'},
                            'on-success': ['wait_vnf_active_VNF2']},
                    'create_ns_VNF1': {
                        'action': 'tacker.create_vnf body=<% $.ns.VNF1 %>',
                        'input': {'body': '<% $.ns.VNF1 %>'},
                        'publish': {
                            'status_VNF1': '<% task(create_ns_VNF1).'
                                           'result.vnf.status %>',
                            'vnf_id_VNF1': '<% task(create_ns_VNF1).'
                                           'result.vnf.id %>',
                            'mgmt_ip_address_VNF1': '<% task('
                                                    'create_ns_VNF1).'
                                                    'result.vnf.'
                                                    'mgmt_ip_address %>',
                            'vim_id_VNF1': '<% task(create_ns_VNF1).'
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
                            'mgmt_ip_address_VNF1': ' <% task('
                                                    'wait_vnf_active_VNF1).'
                                                    'result.vnf.'
                                                    'mgmt_ip_address %>'},
                        'on-success': [{'delete_vnf_VNF1': '<% $.status_VNF1='
                                                           '"ERROR" %>'}]},
                    'delete_vnf_VNF1': {
                        'action': 'tacker.delete_vnf vnf=<% $.vnf_id_VNF1%>',
                        'input': {'body': {'vnf': {'attributes': {
                                                   'force': False}}}}},
                    'delete_vnf_VNF2': {
                        'action': 'tacker.delete_vnf vnf=<% $.vnf_id_VNF2%>',
                        'input': {'body': {'vnf': {'attributes': {
                                                   'force': False}}}}}},
                'type': 'direct', 'output': {
                    'status_VNF1': '<% $.status_VNF1 %>',
                    'status_VNF2': '<% $.status_VNF2 %>',
                    'mgmt_ip_address_VNF2': '<% $.mgmt_ip_address_VNF2 %>',
                    'mgmt_ip_address_VNF1': '<% $.mgmt_ip_address_VNF1 %>',
                    'vim_id_VNF2': '<% $.vim_id_VNF2 %>',
                    'vnf_id_VNF1': '<% $.vnf_id_VNF1 %>',
                    'vnf_id_VNF2': '<% $.vnf_id_VNF2 %>',
                    'vim_id_VNF1': '<% $.vim_id_VNF1 %>'}},
            'version': '2.0'}


def get_dummy_create_vnffg_ns_workflow():
    return {
        'std.create_ns_dummy': {
            'input': ['ns'],
            'tasks': {
                'wait_vnf_active_VNF2': {
                    'action': 'tacker.show_vnf vnf=<% $.vnf_id_VNF2 %>',
                    'retry': {
                        'count': 10,
                        'delay': 10,
                        'continue-on':
                            '<% $.status_VNF2 = "PENDING_CREATE" %>',
                        'break-on':
                            '<% $.status_VNF2 = "ERROR" %>'},
                    'publish': {
                        'status_VNF2':
                            '<% task(wait_vnf_active_VNF2).result.'
                            'vnf.status %>',
                        'mgmt_ip_address_VNF2':
                            ' <% task(wait_vnf_active_VNF2).result.'
                            'vnf.mgmt_ip_address %>'},
                    'on-success': [
                        {'delete_vnf_VNF2': '<% $.status_VNF2="ERROR" %>'},
                        'create_vnffg_VNFFG1']},
                'create_vnffg_VNFFG1': {
                    'action': 'tacker.create_vnffg body=<% $.ns.VNFFG1 %>',
                    'input': {'body': '<% $.ns.VNFFG1 %>'},
                    'join': 'all',
                    'publish': {
                        'vnffg_id_VNFFG1': '<% task(create_vnffg_VNFFG1).'
                                           'result.vnffg.id %>'}},
                'wait_vnf_active_VNF1': {
                    'action': 'tacker.show_vnf vnf=<% $.vnf_id_VNF1 %>',
                    'retry': {
                        'count': 10,
                        'delay': 10,
                        'continue-on':
                            '<% $.status_VNF1 = "PENDING_CREATE" %>',
                        'break-on':
                            '<% $.status_VNF1 = "ERROR" %>'},
                    'publish': {
                        'status_VNF1':
                            '<% task(wait_vnf_active_VNF1).result.'
                            'vnf.status %>',
                        'mgmt_ip_address_VNF1':
                            ' <% task(wait_vnf_active_VNF1).result.'
                            'vnf.mgmt_ip_address %>'},
                    'on-success': [
                        {'delete_vnf_VNF1': '<% $.status_VNF1="ERROR" %>'},
                        'create_vnffg_VNFFG1']},
                'create_ns_VNF1': {
                    'action': 'tacker.create_vnf body=<% $.ns.VNF1 %>',
                    'input': {'body': '<% $.ns.VNF1 %>'},
                    'publish': {
                        'status_VNF1':
                            '<% task(create_ns_VNF1).result.vnf.status %>',
                        'vnf_id_VNF1':
                            '<% task(create_ns_VNF1).result.vnf.id %>',
                        'mgmt_ip_address_VNF1':
                            '<% task(create_ns_VNF1).result.'
                            'vnf.mgmt_ip_address %>',
                        'vim_id_VNF1':
                            '<% task(create_ns_VNF1).result.vnf.vim_id %>'},
                    'on-success': ['wait_vnf_active_VNF1']},
                'create_ns_VNF2': {
                    'action': 'tacker.create_vnf body=<% $.ns.VNF2 %>',
                    'input': {'body': '<% $.ns.VNF2 %>'},
                    'publish': {
                        'status_VNF2':
                            '<% task(create_ns_VNF2).result.vnf.status %>',
                        'vim_id_VNF2':
                            '<% task(create_ns_VNF2).result.vnf.vim_id %>',
                        'mgmt_ip_address_VNF2':
                            '<% task(create_ns_VNF2).result.'
                            'vnf.mgmt_ip_address %>',
                        'vnf_id_VNF2':
                            '<% task(create_ns_VNF2).result.vnf.id %>'},
                    'on-success': ['wait_vnf_active_VNF2']},
                'delete_vnf_VNF1': {
                    'action': 'tacker.delete_vnf vnf=<% $.vnf_id_VNF1%>',
                    'input': {'body': {'vnf': {'attributes': {
                                               'force': False}}}}},
                'delete_vnf_VNF2': {
                    'action': 'tacker.delete_vnf vnf=<% $.vnf_id_VNF2%>',
                    'input': {'body': {'vnf': {'attributes': {
                                               'force': False}}}}}},
            'type': 'direct',
            'output': {
                'status_VNF1': '<% $.status_VNF1 %>',
                'status_VNF2': '<% $.status_VNF2 %>',
                'mgmt_ip_address_VNF2': '<% $.mgmt_ip_address_VNF2 %>',
                'mgmt_ip_address_VNF1': '<% $.mgmt_ip_address_VNF1 %>',
                'vnffg_id_VNFFG1': '<% $.vnffg_id_VNFFG1 %>',
                'vim_id_VNF2': '<% $.vim_id_VNF2 %>',
                'vnf_id_VNF1': '<% $.vnf_id_VNF1 %>',
                'vnf_id_VNF2': '<% $.vnf_id_VNF2 %>',
                'vim_id_VNF1': '<% $.vim_id_VNF1 %>'}},
        'version': '2.0'}


def dummy_delete_ns_obj():
    return {'vnf_ids': u"{'VNF1': '5de5eca6-3e21-4bbd-a9d7-86458de75f0c'}",
            'vnffg_ids': u"{}"}


def dummy_delete_vnffg_ns_obj():
    return {'vnf_ids': u"{'VNF1': '5de5eca6-3e21-4bbd-a9d7-86458de75f0c'}",
            'vnffg_ids': u"{'VNFFG1': '99066f25-3124-44f1-bc5d-bc0bf236b012'}"}


def get_dummy_delete_workflow():
    return {'version': '2.0',
            'std.delete_ns_dummy': {
                'input': ['vnf_id_VNF1'],
                'tasks': {
                    'delete_vnf_VNF1': {
                        'action': 'tacker.delete_vnf vnf=<% $.vnf_id_VNF1%>',
                        'input': {'body': {'vnf': {'attributes': {
                                                   'force': False}}}}}},
                'type': 'direct'}}


def get_dummy_delete_vnffg_ns_workflow():
    return {'version': '2.0',
            'std.delete_ns_dummy': {
                'input': ['vnf_id_VNF1', 'VNFFG1'],
                'tasks': {
                    'delete_vnf_VNF1': {
                        'join': 'all',
                        'action': 'tacker.delete_vnf vnf=<% $.vnf_id_VNF1%>',
                        'input': {'body': {'vnf': {'attributes': {
                                                   'force': False}}}}},
                    'delete_vnffg_VNFFG1': {
                        'action': 'tacker.delete_vnffg vnffg='
                                  '<% $.VNFFG1 %>',
                        'on-success': ['delete_vnf_VNF1']}},
                'type': 'direct'}}


class FakeMistral(object):
    def __init__(self):
        pass


class FakeNFVOPlugin(object):

    def __init__(self, context, client, resource, action):
        self.context = context
        self.client = client
        self.wg = workflow_generator.WorkflowGenerator(resource, action)

    def prepare_workflow(self, **kwargs):
        self.wg.task(**kwargs)


class TestWorkflowGenerator(base.TestCase):
    def setUp(self):
        super(TestWorkflowGenerator, self).setUp()
        self.mistral_client = FakeMistral()

    def test_prepare_workflow_create(self):
        fPlugin = FakeNFVOPlugin(context, self.mistral_client,
                                 resource='ns', action='create')
        fPlugin.prepare_workflow(ns=get_dummy_ns(), params=get_dummy_param())
        wf_def_values = [fPlugin.wg.definition[k] for
            k in fPlugin.wg.definition]
        self.assertIn(get_dummy_create_workflow()['std.create_ns_dummy'],
                      wf_def_values)
        self.assertEqual(get_dummy_create_workflow()['version'],
                         fPlugin.wg.definition['version'])

    def test_prepare_vnffg_ns_workflow_create(self):
        fPlugin = FakeNFVOPlugin(context, self.mistral_client,
                                 resource='ns', action='create')
        fPlugin.prepare_workflow(ns=get_dummy_vnffg_ns(),
                                 params=get_dummy_param())
        wf_def_values = [fPlugin.wg.definition[k] for
            k in fPlugin.wg.definition]
        self.assertIn(
            get_dummy_create_vnffg_ns_workflow()['std.create_ns_dummy'],
            wf_def_values)
        self.assertEqual(
            get_dummy_create_vnffg_ns_workflow()['version'],
            fPlugin.wg.definition['version'])

    def test_prepare_workflow_delete(self):
        fPlugin = FakeNFVOPlugin(context, self.mistral_client,
                                 resource='ns', action='delete')
        fPlugin.prepare_workflow(ns=dummy_delete_ns_obj())
        wf_def_values = [fPlugin.wg.definition[k] for
            k in fPlugin.wg.definition]
        self.assertIn(get_dummy_delete_workflow()['std.delete_ns_dummy'],
                      wf_def_values)
        self.assertEqual(get_dummy_delete_workflow()['version'],
                         fPlugin.wg.definition['version'])

    def test_prepare_vnffg_ns_workflow_delete(self):
        fPlugin = FakeNFVOPlugin(context, self.mistral_client,
                                 resource='ns', action='delete')
        fPlugin.prepare_workflow(ns=dummy_delete_vnffg_ns_obj())
        wf_def_values = [fPlugin.wg.definition[k] for
            k in fPlugin.wg.definition]
        self.assertIn(
            get_dummy_delete_vnffg_ns_workflow()['std.delete_ns_dummy'],
            wf_def_values)
        self.assertEqual(
            get_dummy_delete_vnffg_ns_workflow()['version'],
            fPlugin.wg.definition['version'])
