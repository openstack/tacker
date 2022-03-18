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

from tacker.common import clients

LOG = logging.getLogger(__name__)


class AnsibleHeatClient():

    def __init__(self, context, plugin, vnf):
        access_info = plugin.get_vim(context, vnf)

        vim_auth = access_info["vim_auth"]
        auth_attr = {
            "username": vim_auth["username"],
            "password": vim_auth["password"],
            "project_name": vim_auth["project_name"],
            "cert_verify": vim_auth["cert_verify"],
            "user_domain_name": vim_auth["user_domain_name"],
            "auth_url": vim_auth["auth_url"],
            "project_id": vim_auth["project_id"],
            "project_domain_name": vim_auth["project_domain_name"]
        }

        region_name = vnf.get('placement_attr', {}).get('region_name', None)

        self._heat_client = \
            clients.OpenstackClients(auth_attr, region_name).heat

    def get_parent_stack_id(self, stack_id):
        stack = self._heat_client.stacks.get(stack_id)
        return stack.parent

    def get_resource_list(self, stack_id):
        resource_list = []
        if stack_id:
            resource_list = self._heat_client.resources.list(stack_id)
        return resource_list

    def get_resource(self, stack_id, resource_name):
        return self._heat_client.resources.get(stack_id, resource_name)

    def get_resource_attributes(self, stack_id, resource_name):
        return self.get_resource(stack_id, resource_name).attributes
