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

from oslo_log import log as logging

from tacker.nfvo.drivers.workflow import workflow_generator

LOG = logging.getLogger(__name__)
FREQUENCY = 10
SLEEP = 5


class MistralClient(object):

    def __init__(self, context, client, resource, action):
        self.context = context
        self.client = client
        self.wg = workflow_generator.WorkflowGenerator(resource, action)

    def prepare_workflow(self, **kwargs):
        self.wg.task(**kwargs)

    def create_workflow(self):
        definition_yaml = yaml.dump(self.wg.definition)
        wf = self.client.workflows.create(definition_yaml)
        wf_id = wf[0].id
        return wf_id

    def delete_workflow(self, wf_id):
        self.client.workflows.delete(wf_id)

    def execute_workflow(self, wf_id):
        wf_ex = self.client.executions.create(
            workflow_identifier=wf_id,
            workflow_input=self.wg.input_dict,
            wf_params={})
        return wf_ex

    def get_execution_state(self, ex_id):
        return self.client.executions.get(ex_id).state

    def delete_execution(self, ex_id):
        self.client.executions.delete(ex_id)
