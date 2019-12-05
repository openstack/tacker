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

from tacker.mistral import workflow_generator


OUTPUT = {
    'create_vnf': ['vnf_id', 'vim_id', 'mgmt_ip_address', 'status'],
    'create_vnffg': ['vnffg_id'],
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
                    'action': 'tacker.create_vnf body=<% $.ns.{0} '
                              '%>'.format(node),
                    'input': {'body': '<% $.ns.{0} %>'.format(node)},
                    'publish': {
                        'vnf_id_' + node: '<% task({0}).result.vnf.id '
                                          '%>'.format(task),
                        'vim_id_' + node: '<% task({0}).result.vnf.vim_id'
                                          ' %>'.format(task),
                        'mgmt_ip_address_' + node: '<% task({0}).result.vnf.'
                                                   'mgmt_ip_address '
                                                   '%>'.format(task),
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
                        'break-on': '<% $.status_{0} = "ERROR"'
                                    ' %>'.format(node),
                        'continue-on': '<% $.status_{0} = "PENDING_CREATE" '
                                       '%>'.format(node),
                              },
                    'publish': {
                        'mgmt_ip_address_' + node: ' <% task({0}).result.'
                                                   'vnf.mgmt_ip_address '
                                                   '%>'.format(task),
                        'status_' + node: '<% task({0}).result.vnf.status'
                                          ' %>'.format(task),
                              },
                    'on-success': [
                        {'delete_vnf_' + node: '<% $.status_{0}='
                                               '"ERROR" %>'.format(node)}
                              ]
                }
                vnffgd_templates = ns.get('vnffgd_templates')
                if vnffgd_templates:
                    for vnffg_name in vnffgd_templates:
                        vnffg_group = vnffgd_templates[vnffg_name][
                            'topology_template']['groups'][vnffg_name]
                        constituent_vnfs = vnffg_group[
                            'properties']['constituent_vnfs']

                        if vnfd_name in constituent_vnfs:
                            task_dict[task]['on-success'].append(
                                'create_vnffg_%s' % vnffg_name)
        return task_dict

    def _add_delete_vnf_tasks(self, ns, vnffg_ids=None):
        vnfds = ns['vnfd_details']
        vnf_attr = {'vnf': {'attributes': {
                            'force': ns.get('force_delete', False)}}}
        task_dict = dict()
        for vnfd_name, vnfd_info in (vnfds).items():
            nodes = vnfd_info['instances']
            for node in nodes:
                task = 'delete_vnf_%s' % node
                task_dict[task] = {
                    'action': 'tacker.delete_vnf vnf=<% $.vnf_id_{0}'
                              '%>'.format(node),
                    'input': {'body': vnf_attr},
                }
                if vnffg_ids and len(vnffg_ids):
                    task_dict[task].update({'join': 'all'})
        return task_dict

    def _add_create_vnffg_task(self, vnffgd_templates):
        task_dict = dict()
        previous_task = None
        for vnffg_name in vnffgd_templates:
            task = 'create_vnffg_%s' % vnffg_name
            vnffg_output = 'vnffg_id_%s' % vnffg_name
            task_dict[task] = {
                'join': 'all',
                'action': 'tacker.create_vnffg body=<% $.ns.{0} '
                          '%>'.format(vnffg_name),
                'input': {'body': '<% $.ns.{0} %>'.format(vnffg_name)},
                'publish': {
                    vnffg_output: '<% task({0}).result.'
                                  'vnffg.id %>'.format(task)}
            }
            if previous_task:
                task_dict[previous_task].update({'on-success': [task]})
            previous_task = task
        return task_dict

    def _add_delete_vnffg_task(self, ns):
        task_dict = dict()
        vnfds = ns['vnfd_details']
        vnffg_ids = ns['vnffg_details']
        delayed_tasks = list()

        for vnfd_name, vnfd_info in (vnfds).items():
            nodes = vnfd_info['instances']
            for node in nodes:
                wait_task = 'delete_vnf_%s' % node
                delayed_tasks.append(wait_task)

        previous_task = None
        for vnffg_name in vnffg_ids:
            task = 'delete_vnffg_%s' % vnffg_name
            if previous_task:
                wait_tasks = delayed_tasks + [previous_task]
            else:
                wait_tasks = delayed_tasks
            previous_task = task
            task_dict[task] = {
                'action': 'tacker.delete_vnffg vnffg=<% $.{0} '
                          '%>'.format(vnffg_name),
                'on-success': wait_tasks
            }
        return task_dict

    def _build_output_dict(self, ns):
        vnfds = ns['vnfd_details']
        task_dict = dict()
        for vnfd_name, vnfd_info in (vnfds).items():
            nodes = vnfd_info['instances']
            for node in nodes:
                for op_name in OUTPUT['create_vnf']:
                    task_dict[op_name + '_' + node] = \
                        '<% $.{0}_{1} %>'.format(op_name, node)
        vnffgd_templates = ns.get('vnffgd_templates')
        if vnffgd_templates:
            for vnffg_name in vnffgd_templates:
                for op_name in OUTPUT['create_vnffg']:
                    vnffg_output = '%s_%s' % (op_name, vnffg_name)
                    task_dict[vnffg_output] = \
                        '<% $.{0}_{1} %>'.format(op_name, vnffg_name)
        return task_dict

    def get_input_dict(self):
        return self.input_dict

    def build_input(self, ns, params):
        vnfds = ns['vnfd_details']
        ns_id = ns['ns'].get('ns_id')
        ns_name = ns['ns'].get('name')
        self.input_dict = {'ns': {}}
        for vnfd_name, vnfd_info in (vnfds).items():
            nodes = vnfd_info['instances']
            for node in nodes:
                vnf_name = '%s_VNF_%s' % (ns_name, vnfd_info['id'])
                self.input_dict['ns'][node] = dict()
                self.input_dict['ns'][node]['vnf'] = {
                    'attributes': {},
                    'vim_id': ns['ns'].get('vim_id', ''),
                    'vnfd_id': vnfd_info['id'],
                    'name': vnf_name
                }
                if params.get(vnfd_name):
                    self.input_dict['ns'][node]['vnf']['attributes'] = {
                        'param_values': params.get(vnfd_name)
                    }
        if ns.get('vnffgd_templates'):
            vnffg_input = self.build_vnffg_input(ns, params, ns_id)
            self.input_dict['ns'].update(vnffg_input)

    def build_vnffg_input(self, ns, params, ns_id):
        vnffgd_templates = ns.get('vnffgd_templates')
        vnffg_input = dict()
        for vnffg_name in vnffgd_templates:
            vnffg_group = vnffgd_templates[vnffg_name][
                'topology_template']['groups'][vnffg_name]
            constituent_vnfs = vnffg_group[
                'properties']['constituent_vnfs']
            vnf_mapping = self.get_vnf_mapping(ns, constituent_vnfs)
            vnffgd_body = dict()
            vnffgd_body['vnffg'] = {
                'name': '%s_%s_%s' % (ns['ns'].get('name'), vnffg_name, ns_id),
                'vnffgd_template': vnffgd_templates[vnffg_name],
                'vnf_mapping': vnf_mapping,
                'attributes': {
                    'param_values': params.get('nsd')},
                'ns_id': ns_id
            }
            vnffg_input[vnffg_name] = vnffgd_body
        return vnffg_input

    def get_vnf_mapping(self, ns, constituent_vnfs):
        vnfds = ns['vnfd_details']
        vnf_mapping = dict()
        for vnfd_name, vnfd_info in (vnfds).items():
            if vnfd_name in constituent_vnfs:
                vnf_name = '%s_VNF_%s' % (ns['ns'].get('name'),
                                          vnfd_info['id'])
                vnf_mapping[vnfd_name] = vnf_name
        return vnf_mapping

    def create_ns(self, **kwargs):
        ns = kwargs.get('ns')
        params = kwargs.get('params')

        tasks = {}
        for func in [self._add_create_vnf_tasks,
                     self._add_wait_vnf_tasks,
                     self._add_delete_vnf_tasks]:
            tasks.update(func(ns))

        self.build_input(ns, params)
        vnffgd_templates = ns.get('vnffgd_templates')
        if vnffgd_templates:
            create_task = self._add_create_vnffg_task(vnffgd_templates)
            tasks.update(create_task)

        self.definition[self.wf_identifier]['tasks'] = tasks
        self.definition[self.wf_identifier]['output'] = \
            self._build_output_dict(ns)

    def delete_ns(self, ns):
        ns_dict = {'vnfd_details': {}}
        vnf_ids = ast.literal_eval(ns['vnf_ids'])
        self.definition[self.wf_identifier]['input'] = []
        for vnf in vnf_ids:
            vnf_key = 'vnf_id_' + vnf
            self.definition[self.wf_identifier]['input'].append(vnf_key)
            self.input_dict[vnf_key] = vnf_ids[vnf]
            ns_dict['vnfd_details'][vnf] = {'instances': [vnf]}
        self.definition[self.wf_identifier]['tasks'] = dict()

        vnffg_ids = ast.literal_eval(ns.get('vnffg_ids'))
        if len(vnffg_ids):
            for vnffg_name in vnffg_ids:
                self.definition[self.wf_identifier]['input'].append(vnffg_name)
                self.input_dict[vnffg_name] = vnffg_ids[vnffg_name]
                ns_dict['vnffg_details'] = vnffg_ids
            self.definition[self.wf_identifier]['tasks'].update(
                self._add_delete_vnffg_task(ns_dict))
        ns_dict['force_delete'] = ns.get('force_delete', False)
        self.definition[self.wf_identifier]['tasks'].update(
            self._add_delete_vnf_tasks(ns_dict, vnffg_ids))
