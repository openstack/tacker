#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import yaml

from oslo_config import cfg
from oslo_log import log as logging

from tacker.common import rpc
from tacker.mistral.actionrpc import kill_action as killaction
from tacker.mistral import mistral_client
from tacker.nfvo.workflows.vim_monitor import workflow_generator
from tacker.vnfm import keystone


LOG = logging.getLogger(__name__)


def get_mistral_client(auth_dict):
    return mistral_client.MistralClient(
        keystone.Keystone().initialize_client(**auth_dict),
        auth_dict['token']).get_client()


def prepare_and_create_workflow(mistral_client, vim_id, action,
                                kwargs):
    wg = workflow_generator.WorkflowGenerator(vim_id, action)
    wg.task(**kwargs)
    yaml.SafeDumper.ignore_aliases = lambda self, data: True
    definition_yaml = yaml.safe_dump(wg.definition, default_flow_style=False)
    LOG.debug('vim monitor workflow: %s', definition_yaml)
    workflow = mistral_client.workflows.create(definition_yaml)
    return {'id': workflow[0].id, 'input': wg.get_input_dict()}


def execute_workflow(mistral_client, workflow):
    return mistral_client.executions.create(
        workflow_identifier=workflow['id'],
        workflow_input=workflow['input'],
        wf_params={})


def delete_executions(mistral_client, vim_id):
    executions = mistral_client.executions.list(
        workflow_name='vim_id_' + vim_id)
    for execution in executions:
        mistral_client.executions.delete(execution.id, force=True)


def delete_workflow(mistral_client, vim_id):
    return mistral_client.workflows.delete('vim_id_' + vim_id)


def monitor_vim(auth_dict, vim_obj):
    mc = get_mistral_client(auth_dict)
    auth_url = vim_obj["auth_url"]
    vim_type = vim_obj['type']
    if vim_type == 'openstack':
        vim_ip = auth_url.split("//")[-1].split(":")[0].split("/")[0]
    elif vim_type == 'kubernetes':
        vim_ip = auth_url.split("//")[-1].split(":")[0]
    workflow_input_dict = {
        'vim_id': vim_obj['id'],
        'count': cfg.CONF.vim_monitor.count,
        'timeout': cfg.CONF.vim_monitor.timeout,
        'interval': cfg.CONF.vim_monitor.interval,
        'targetip': vim_ip}
    workflow = prepare_and_create_workflow(
        mc, vim_obj['id'], 'monitor',
        workflow_input_dict)
    execute_workflow(mc, workflow)


def kill_action(context, vim_obj):
    target = killaction.MistralActionKillRPC.target
    rpc_client = rpc.get_client(target)
    cctxt = rpc_client.prepare(server=vim_obj['id'])
    cctxt.cast(context, 'killAction')


def delete_vim_monitor(context, auth_dict, vim_obj):
    mc = get_mistral_client(auth_dict)
    delete_executions(mc, vim_obj['id'])
    delete_workflow(mc, vim_obj['id'])
    kill_action(context, vim_obj)
