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

from oslo_utils import uuidutils


class WorkflowGeneratorBase(object):
    def __init__(self, resource, action):
        self.resource = resource
        self.action = action
        self.wf_name = self.action + '_' + self.resource
        self.wf_identifier = 'std.' + self.wf_name + uuidutils.generate_uuid()
        self.task = getattr(self, self.wf_name)
        self.input_dict = dict()
        self._build_basic_workflow()

    def _build_basic_workflow(self):
        self.definition = {
            'version': '2.0',
            self.wf_identifier: {
                'type': 'direct',
                'input': [self.resource]
            }
        }

    def get_tasks(self):
        return self.definition[self.wf_identifier].get('tasks')
