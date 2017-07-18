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
from oslo_utils import uuidutils

from tacker.mistral import workflow_generator


OUTPUT = {
    'create_vnf': ['vnf_id', 'vim_id', 'mgmt_url', 'status']
}


class WorkflowGenerator(workflow_generator.WorkflowGeneratorBase):

    def _add_create_vnf_tasks(self, ns):
        vnfds = ns['vnfd_details']
        task_dict = dict()
        for vnfd_name, vnfd_info in (vnfds).items():
            nodes = vnfd_info['instances']
            for node in nodes:
                task = self.wf_name + '_' + node
                task_dict[task] = {
                    'action': 'tacker.create_vnf body=<% $.vnf.{0} '
                              '%>'.format(node),
                    'input': {'body': '<% $.vnf.{0} %>'.format(node)},
                    'publish': {
                        'vnf_id_' + node: '<% task({0}).result.vnf.id '
                                          '%>'.format(task),
                        'vim_id_' + node: '<% task({0}).result.vnf.vim_id'
                                          ' %>'.format(task),
                        'mgmt_url_' + node: '<% task({0}).result.vnf.mgmt_url'
                                            ' %>'.format(task),
                        'status_' + node: '<% task({0}).result.vnf.status'
                                          ' %>'.format(task),
                              },
                    'on-success': ['wait_vnf_active_%s' % node]
                }
        return task_dict

    def _add_wait_vnf_tasks(self, ns):
        vnfds = ns['vnfd_details']
        task_dict = dict()
        for vnfd_name, vnfd_info in (vnfds).items():
            nodes = vnfd_info['instances']
            for node in nodes:
                task = 'wait_vnf_active_%s' % node
                task_dict[task] = {
                    'action': 'tacker.show_vnf vnf=<% $.vnf_id_{0} '
                              '%>'.format(node),
                    'retry': {
                        'count': 10,
                        'delay': 10,
                        'break-on': '<% $.status_{0} = "ACTIVE" '
                                    '%>'.format(node),
                        'break-on': '<% $.status_{0} = "ERROR"'
                                    ' %>'.format(node),
                        'continue-on': '<% $.status_{0} = "PENDING_CREATE" '
                                       '%>'.format(node),
                              },
                    'publish': {
                        'mgmt_url_' + node: ' <% task({0}).result.vnf.'
                                            'mgmt_url %>'.format(task),
                        'status_' + node: '<% task({0}).result.vnf.status'
                                          ' %>'.format(task),
                              },
                    'on-success': [
                        {'delete_vnf_' + node: '<% $.status_{0}='
                                               '"ERROR" %>'.format(node)}
                              ]
                }
        return task_dict

    def _add_delete_vnf_tasks(self, ns):
        vnfds = ns['vnfd_details']
        task_dict = dict()
        for vnfd_name, vnfd_info in (vnfds).items():
            nodes = vnfd_info['instances']
            for node in nodes:
                task = 'delete_vnf_%s' % node
                task_dict[task] = {
                    'action': 'tacker.delete_vnf vnf=<% $.vnf_id_{0}'
                              '%>'.format(node),
                }
        return task_dict

    def _build_output_dict(self, ns):
        vnfds = ns['vnfd_details']
        task_dict = dict()
        for vnfd_name, vnfd_info in (vnfds).items():
            nodes = vnfd_info['instances']
            for node in nodes:
                for op_name in OUTPUT[self.wf_name]:
                    task_dict[op_name + '_' + node] = \
                        '<% $.{0}_{1} %>'.format(op_name, node)
        return task_dict

    def get_input_dict(self):
        return self.input_dict

    def build_input(self, ns, params):
        vnfds = ns['vnfd_details']
        id = uuidutils.generate_uuid()
        self.input_dict = {'vnf': {}}
        for vnfd_name, vnfd_info in (vnfds).items():
            nodes = vnfd_info['instances']
            for node in nodes:
                self.input_dict['vnf'][node] = dict()
                self.input_dict['vnf'][node]['vnf'] = {
                    'attributes': {},
                    'vim_id': ns['ns'].get('vim_id', ''),
                    'vnfd_id': vnfd_info['id'],
                    'name': 'create_vnf_%s_%s' % (vnfd_info['id'], id)
                }
                if params.get(vnfd_name):
                    self.input_dict['vnf'][node]['vnf']['attributes'] = {
                        'param_values': params.get(vnfd_name)
                    }

    def create_vnf(self, **kwargs):
        ns = kwargs.get('ns')
        params = kwargs.get('params')
        # TODO(anyone): Keep this statements in a loop and
        # remove in all the methods.
        self.definition[self.wf_identifier]['tasks'] = dict()
        self.definition[self.wf_identifier]['tasks'].update(
            self._add_create_vnf_tasks(ns))
        self.definition[self.wf_identifier]['tasks'].update(
            self._add_wait_vnf_tasks(ns))
        self.definition[self.wf_identifier]['tasks'].update(
            self._add_delete_vnf_tasks(ns))
        self.definition[self.wf_identifier]['output'] = \
            self._build_output_dict(ns)
        self.build_input(ns, params)

    def delete_vnf(self, ns):
        ns_dict = {'vnfd_details': {}}
        vnf_ids = ast.literal_eval(ns['vnf_ids'])
        self.definition[self.wf_identifier]['input'] = []
        for vnf in vnf_ids.keys():
            vnf_key = 'vnf_id_' + vnf
            self.definition[self.wf_identifier]['input'].append(vnf_key)
            self.input_dict[vnf_key] = vnf_ids[vnf]
            ns_dict['vnfd_details'][vnf] = {'instances': [vnf]}
        self.definition[self.wf_identifier]['tasks'] = dict()
        self.definition[self.wf_identifier]['tasks'].update(
            self._add_delete_vnf_tasks(ns_dict))
