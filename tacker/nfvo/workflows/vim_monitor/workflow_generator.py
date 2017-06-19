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

from oslo_log import log as logging

from tacker.mistral import workflow_generator
from tacker.nfvo.workflows import vim_monitor

LOG = logging.getLogger(__name__)


class WorkflowGenerator(workflow_generator.WorkflowGeneratorBase):
    def __init__(self, vim_id, action):
        super(WorkflowGenerator, self).__init__(
            vim_monitor.RESOURCE_NAME, action)
        self.wf_identifier = 'vim_id_' + vim_id
        self._build_basic_workflow()

    def _add_ping_vim_tasks(self):
        task_dict = dict()
        task = self.wf_name + vim_monitor.PING_VIM_TASK_NAME
        task_dict[task] = {
            'action': 'tacker.vim_ping_action',
            'input': {'count': self.input_dict_data['count'],
                      'targetip': self.input_dict_data['targetip'],
                      'vim_id': self.input_dict_data['vim_id'],
                      'interval': self.input_dict_data['interval'],
                      'timeout': self.input_dict_data['timeout']},
        }
        return task_dict

    def get_input_dict(self):
        return self.input_dict

    def _build_input(self, vim_id, count, timeout,
                     interval, targetip):
        self.input_dict_data = {'vim_id': vim_id,
                                'count': count,
                                'timeout': timeout,
                                'interval': interval,
                                'targetip': targetip}
        self.input_dict[self.resource] = self.input_dict_data

    def monitor_ping_vim(self, vim_id=None, count=1, timeout=1,
                         interval=1, targetip="127.0.0.1"):
        self._build_input(vim_id, count, timeout,
                          interval, targetip)
        self.definition[self.wf_identifier]['tasks'] = dict()
        self.definition[self.wf_identifier]['tasks'].update(
            self._add_ping_vim_tasks())
