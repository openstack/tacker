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

import requests
import time
import yaml

from oslo_config import cfg
from oslo_serialization import jsonutils

from tacker.common import clients
from tacker.common import log
from tacker.extensions import vnfm
from tacker.plugins.common import constants
from tacker.vnfm import vim_client


CONF = cfg.CONF
OPTS = [
    cfg.IntOpt('lead_time', default=120,
               help=_('Time for migration_type operation')),
    cfg.IntOpt('max_interruption_time', default=120,
               help=_('Time for how long live migration can take')),
    cfg.IntOpt('recovery_time', default=2,
               help=_('Time for migrated node could be fully running state')),
    cfg.IntOpt('request_retries',
               default=5,
               help=_("Number of attempts to retry for request")),
    cfg.IntOpt('request_retry_wait',
               default=5,
               help=_("Wait time (in seconds) between consecutive request"))
]
CONF.register_opts(OPTS, 'fenix')
MAINTENANCE_KEYS = (
    'instance_ids', 'session_id', 'state', 'reply_url'
)
MAINTENANCE_SUB_KEYS = {
    'PREPARE_MAINTENANCE': [('allowed_actions', 'list'),
                            ('instance_ids', 'list')],
    'PLANNED_MAINTENANCE': [('allowed_actions', 'list'),
                            ('instance_ids', 'list')]
}


def config_opts():
    return [('fenix', OPTS)]


class FenixPlugin(object):
    def __init__(self):
        self.REQUEST_RETRIES = cfg.CONF.fenix.request_retries
        self.REQUEST_RETRY_WAIT = cfg.CONF.fenix.request_retry_wait
        self.endpoint = None
        self._instances = {}
        self.vim_client = vim_client.VimClient()

    @log.log
    def request(self, plugin, context, vnf_dict, maintenance={},
                data_func=None):
        params_list = [maintenance]
        method = 'put'
        is_reply = True
        if data_func:
            action, create_func = data_func.split('_', 1)
            create_func = '_create_%s_list' % create_func
            if action in ['update', 'delete'] and hasattr(self, create_func):
                params_list = getattr(self, create_func)(
                    context, vnf_dict, action)
                method = action if action == 'delete' else 'put'
                is_reply = False
        for params in params_list:
            self._request(plugin, context, vnf_dict, params, method, is_reply)
        return len(params_list)

    @log.log
    def create_vnf_constraints(self, plugin, context, vnf_dict):
        self.update_vnf_constraints(plugin, context, vnf_dict,
                                    objects=['instance_group',
                                             'project_instance'])

    @log.log
    def delete_vnf_constraints(self, plugin, context, vnf_dict):
        self.update_vnf_constraints(plugin, context, vnf_dict,
                                    action='delete',
                                    objects=['instance_group',
                                             'project_instance'])

    @log.log
    def update_vnf_instances(self, plugin, context, vnf_dict,
                             action='update'):
        requests = self.update_vnf_constraints(plugin, context,
                                               vnf_dict, action,
                                               objects=['project_instance'])
        if requests[0]:
            self.post(context, vnf_dict)

    @log.log
    def update_vnf_constraints(self, plugin, context, vnf_dict,
                               action='update', objects=[]):
        result = []
        for obj in objects:
            requests = self.request(plugin, context, vnf_dict,
                                    data_func='%s_%s' % (action, obj))
            result.append(requests)
        return result

    @log.log
    def post(self, context, vnf_dict, **kwargs):
        post_function = getattr(context, 'maintenance_post_function', None)
        if not post_function:
            return
        post_function(context, vnf_dict)
        del context.maintenance_post_function

    @log.log
    def project_instance_pre(self, context, vnf_dict):
        key = vnf_dict['id']
        if key not in self._instances:
            self._instances.update({
                key: self._get_instances(context, vnf_dict)})

    @log.log
    def validate_maintenance(self, maintenance):
        body = maintenance['maintenance']['params']['data']['body']
        if not set(MAINTENANCE_KEYS).issubset(body) or \
                body['state'] not in constants.RES_EVT_MAINTENANCE:
            raise vnfm.InvalidMaintenanceParameter()
        sub_keys = MAINTENANCE_SUB_KEYS.get(body['state'], ())
        for key, val_type in sub_keys:
            if key not in body or type(body[key]) is not eval(val_type):
                raise vnfm.InvalidMaintenanceParameter()
        return body

    @log.log
    def _request(self, plugin, context, vnf_dict, maintenance,
                 method='put', is_reply=True):
        client = self._get_openstack_clients(context, vnf_dict)
        if not self.endpoint:
            self.endpoint = client.keystone_session.get_endpoint(
                service_type='maintenance', region_name=client.region_name)
            if not self.endpoint:
                raise vnfm.ServiceTypeNotFound(service_type_id='maintenance')

        if 'reply_url' in maintenance:
            url = maintenance['reply_url']
        elif 'url' in maintenance:
            url = "%s/%s" % (self.endpoint.rstrip('/'),
                             maintenance['url'].strip('/'))
        else:
            return

        def create_headers():
            return {
                'X-Auth-Token': client.keystone_session.get_token(),
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

        request_body = {}
        request_body['headers'] = create_headers()
        state = constants.ACK if vnf_dict['status'] == constants.ACTIVE \
            else constants.NACK
        if method == 'put':
            data = maintenance.get('data', {})
            if is_reply:
                data['session_id'] = maintenance.get('session_id', '')
                data['state'] = "%s_%s" % (state, maintenance['state'])
            request_body['data'] = jsonutils.dump_as_bytes(data)

        def request_wait():
            retries = self.REQUEST_RETRIES
            while retries > 0:
                response = getattr(requests, method)(url, **request_body)
                if response.status_code == 200:
                    break
                else:
                    retries -= 1
                    time.sleep(self.REQUEST_RETRY_WAIT)

        plugin.spawn_n(request_wait)

    @log.log
    def handle_maintenance(self, plugin, context, maintenance):
        action = '_create_%s' % maintenance['state'].lower()
        maintenance['data'] = {}
        if hasattr(self, action):
            getattr(self, action)(plugin, context, maintenance)

    @log.log
    def _create_maintenance(self, plugin, context, maintenance):
        vnf_dict = maintenance.get('vnf', {})
        vnf_dict['attributes'].update({'maintenance_scaled': 0})
        plugin._update_vnf_post(context, vnf_dict['id'], constants.ACTIVE,
                                vnf_dict, constants.ACTIVE,
                                constants.RES_EVT_UPDATE)
        instances = self._get_instances(context, vnf_dict)
        instance_ids = [x['id'] for x in instances]
        maintenance['data'].update({'instance_ids': instance_ids})

    @log.log
    def _create_scale_in(self, plugin, context, maintenance):
        def post_function(context, vnf_dict):
            scaled = int(vnf_dict['attributes'].get('maintenance_scaled', 0))
            vnf_dict['attributes']['maintenance_scaled'] = str(scaled + 1)
            plugin._update_vnf_post(context, vnf_dict['id'], constants.ACTIVE,
                                    vnf_dict, constants.ACTIVE,
                                    constants.RES_EVT_UPDATE)
            instances = self._get_instances(context, vnf_dict)
            instance_ids = [x['id'] for x in instances]
            maintenance['data'].update({'instance_ids': instance_ids})
            self.request(plugin, context, vnf_dict, maintenance)

        vnf_dict = maintenance.get('vnf', {})
        policy_action = self._create_scale_dict(plugin, context, vnf_dict)
        if policy_action:
            maintenance.update({'policy_action': policy_action})
        context.maintenance_post_function = post_function

    @log.log
    def _create_prepare_maintenance(self, plugin, context, maintenance):
        self._create_planned_maintenance(plugin, context, maintenance)

    @log.log
    def _create_planned_maintenance(self, plugin, context, maintenance):
        def post_function(context, vnf_dict):
            migration_type = self._get_constraints(vnf_dict,
                                                   key='migration_type',
                                                   default='MIGRATE')
            maintenance['data'].update({'instance_action': migration_type})
            self.request(plugin, context, vnf_dict, maintenance)

        vnf_dict = maintenance.get('vnf', {})
        instances = self._get_instances(context, vnf_dict)
        request_instance_id = maintenance['instance_ids'][0]
        selected = None
        for instance in instances:
            if instance['id'] == request_instance_id:
                selected = instance
                break
        if not selected:
            vnfm.InvalidMaintenanceParameter()

        migration_type = self._get_constraints(vnf_dict, key='migration_type',
                                               default='MIGRATE')
        if migration_type == 'OWN_ACTION':
            policy_action = self._create_migrate_dict(context, vnf_dict,
                                                      selected)
            maintenance.update({'policy_action': policy_action})
            context.maintenance_post_function = post_function
        else:
            post_function(context, vnf_dict)

    @log.log
    def _create_maintenance_complete(self, plugin, context, maintenance):
        def post_function(context, vnf_dict):
            vim_res = self.vim_client.get_vim(context, vnf_dict['vim_id'])
            scaled = int(vnf_dict['attributes'].get('maintenance_scaled', 0))
            if vim_res['vim_type'] == 'openstack':
                scaled -= 1
                vnf_dict['attributes']['maintenance_scaled'] = str(scaled)
                plugin._update_vnf_post(context, vnf_dict['id'],
                                        constants.ACTIVE, vnf_dict,
                                        constants.ACTIVE,
                                        constants.RES_EVT_UPDATE)
            if scaled > 0:
                scale_out(plugin, context, vnf_dict)
            else:
                instances = self._get_instances(context, vnf_dict)
                instance_ids = [x['id'] for x in instances]
                maintenance['data'].update({'instance_ids': instance_ids})
                self.request(plugin, context, vnf_dict, maintenance)

        def scale_out(plugin, context, vnf_dict):
            policy_action = self._create_scale_dict(plugin, context, vnf_dict,
                                                    scale_type='out')
            context.maintenance_post_function = post_function
            plugin._vnf_action.invoke(policy_action['action'],
                                      'execute_action', plugin=plugin,
                                      context=context, vnf_dict=vnf_dict,
                                      args=policy_action['args'])

        vnf_dict = maintenance.get('vnf', {})
        scaled = vnf_dict.get('attributes', {}).get('maintenance_scaled', 0)
        if int(scaled):
            policy_action = self._create_scale_dict(plugin, context, vnf_dict,
                                                    scale_type='out')
            maintenance.update({'policy_action': policy_action})
            context.maintenance_post_function = post_function

    @log.log
    def _create_scale_dict(self, plugin, context, vnf_dict, scale_type='in'):
        policy_action, scale_dict = {}, {}
        policies = self._get_scaling_policies(plugin, context, vnf_dict)
        if not policies:
            return
        scale_dict['type'] = scale_type
        scale_dict['policy'] = policies[0]['name']
        policy_action['action'] = 'autoscaling'
        policy_action['args'] = {'scale': scale_dict}
        return policy_action

    @log.log
    def _create_migrate_dict(self, context, vnf_dict, instance):
        policy_action, heal_dict = {}, {}
        heal_dict['vdu_name'] = instance['name']
        heal_dict['cause'] = ["Migrate resource '%s' to other host."]
        heal_dict['stack_id'] = instance['stack_name']
        if 'scaling_group_names' in vnf_dict['attributes']:
            sg_names = vnf_dict['attributes']['scaling_group_names']
            sg_names = list(jsonutils.loads(sg_names).keys())
            heal_dict['heat_tpl'] = '%s_res.yaml' % sg_names[0]
        policy_action['action'] = 'vdu_autoheal'
        policy_action['args'] = heal_dict
        return policy_action

    @log.log
    def _create_instance_group_list(self, context, vnf_dict, action):
        group_id = vnf_dict['attributes'].get('maintenance_group', '')
        if not group_id:
            return

        def get_constraints(data):
            maintenance_config = self._get_constraints(vnf_dict)
            data['max_impacted_members'] = maintenance_config.get(
                'max_impacted_members', 1)
            data['recovery_time'] = maintenance_config.get('recovery_time', 60)

        params, data = {}, {}
        params['url'] = '/instance_group/%s' % group_id
        if action == 'update':
            data['group_id'] = group_id
            data['project_id'] = vnf_dict['tenant_id']
            data['group_name'] = 'tacker_nonha_app_group_%s' % vnf_dict['id']
            data['anti_affinity_group'] = False
            data['max_instances_per_host'] = 0
            data['resource_mitigation'] = True
            get_constraints(data)
        params.update({'data': data})
        return [params]

    @log.log
    def _create_project_instance_list(self, context, vnf_dict, action):
        group_id = vnf_dict.get('attributes', {}).get('maintenance_group', '')
        if not group_id:
            return

        params_list = []
        url = '/instance'
        instances = self._get_instances(context, vnf_dict)
        _instances = self._instances.get(vnf_dict['id'], {})
        if _instances:
            if action == 'update':
                instances = [v for v in instances if v not in _instances]
                del self._instances[vnf_dict['id']]
            else:
                instances = [v for v in _instances if v not in instances]
                if len(instances) != len(_instances):
                    del self._instances[vnf_dict['id']]

        if action == 'update':
            maintenance_configs = self._get_constraints(vnf_dict)
            for instance in instances:
                params, data = {}, {}
                params['url'] = '%s/%s' % (url, instance['id'])
                data['project_id'] = instance['project_id']
                data['instance_id'] = instance['id']
                data['instance_name'] = instance['name']
                data['migration_type'] = maintenance_configs.get(
                    'migration_type', 'MIGRATE')
                data['resource_mitigation'] = maintenance_configs.get(
                    'mitigation_type', True)
                data['max_interruption_time'] = maintenance_configs.get(
                    'max_interruption_time',
                    cfg.CONF.fenix.max_interruption_time)
                data['lead_time'] = maintenance_configs.get(
                    'lead_time', cfg.CONF.fenix.lead_time)
                data['group_id'] = group_id
                params.update({'data': data})
                params_list.append(params)
        elif action == 'delete':
            for instance in instances:
                params = {}
                params['url'] = '%s/%s' % (url, instance['id'])
                params_list.append(params)
        return params_list

    @log.log
    def _get_instances(self, context, vnf_dict):
        vim_res = self.vim_client.get_vim(context, vnf_dict['vim_id'])
        action = '_get_instances_with_%s' % vim_res['vim_type']
        if hasattr(self, action):
            return getattr(self, action)(context, vnf_dict)
        return {}

    @log.log
    def _get_instances_with_openstack(self, context, vnf_dict):
        def get_attrs_with_link(links):
            attrs = {}
            for link in links:
                href, rel = link['href'], link['rel']
                if rel == 'self':
                    words = href.split('/')
                    attrs['project_id'] = words[5]
                    attrs['stack_name'] = words[7]
                    break
            return attrs

        instances = []
        client = self._get_openstack_clients(context, vnf_dict)
        resources = client.heat.resources.list(vnf_dict['instance_id'],
                                               nested_depth=2)
        for resource in resources:
            if resource.resource_type == 'OS::Nova::Server' and \
               resource.resource_status != 'DELETE_IN_PROGRESS':
                instance = {
                    'id': resource.physical_resource_id,
                    'name': resource.resource_name
                }
                instance.update(get_attrs_with_link(resource.links))
                instances.append(instance)
        return instances

    @log.log
    def _get_scaling_policies(self, plugin, context, vnf_dict):
        vnf_id = vnf_dict['id']
        policies = []
        if 'scaling_group_names' in vnf_dict['attributes']:
            policies = plugin.get_vnf_policies(
                context, vnf_id, filters={'type': constants.POLICY_SCALING})
        return policies

    @log.log
    def _get_constraints(self, vnf, key=None, default=None):
        config = vnf.get('attributes', {}).get('config', '{}')
        maintenance_config = yaml.safe_load(config).get('maintenance', {})
        if key:
            return maintenance_config.get(key, default)
        return maintenance_config

    @log.log
    def _get_openstack_clients(self, context, vnf_dict):
        vim_res = self.vim_client.get_vim(context, vnf_dict['vim_id'])
        region_name = vnf_dict.setdefault('placement_attr', {}).get(
            'region_name', None)
        client = clients.OpenstackClients(auth_attr=vim_res['vim_auth'],
                                          region_name=region_name)
        return client
