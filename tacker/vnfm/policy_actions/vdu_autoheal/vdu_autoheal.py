#
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
#

from oslo_log import log as logging
import yaml

from tacker import objects
from tacker.vnfm.policy_actions import abstract_action


LOG = logging.getLogger(__name__)


class VNFActionVduAutoheal(abstract_action.AbstractPolicyAction):
    def get_type(self):
        return 'vdu_autoheal'

    def get_name(self):
        return 'vdu_autoheal'

    def get_description(self):
        return 'Tacker VNF vdu_autoheal policy'

    def execute_action(self, plugin, context, vnf_dict, args):
        vdu_name = args.get('vdu_name')
        stack_id = args.get('stack_id', vnf_dict['instance_id'])
        heat_tpl = args.get('heat_tpl', 'heat_template')
        cause = args.get('cause', [])
        if vdu_name is None:
            LOG.error("VDU resource of vnf '%s' is not present for "
                      "autoheal." % vnf_dict['id'])
            return

        def _get_vdu_resources():
            """Get all the resources linked to the VDU.

            Returns: resource list for eg. ['VDU1', CP1]
            """
            resource_list = [vdu_name]
            heat_template = yaml.safe_load(vnf_dict['attributes'].get(
                heat_tpl))
            vdu_resources = heat_template['resources'].get(vdu_name)
            cp_resources = vdu_resources['properties'].get('networks')
            for resource in cp_resources:
                resource_list.append(resource['port'].get('get_resource'))

            return resource_list

        if not cause or type(cause) is not list:
            cause = ["Unable to reach while monitoring resource: '%s'",
                     "Failed to monitor VDU resource '%s'"]
        resource_list = _get_vdu_resources()
        additional_params = []
        for resource in resource_list:
            additional_params_obj = objects.HealVnfAdditionalParams(
                parameter=resource, cause=[cause[0] % resource])
            additional_params.append(additional_params_obj)

        heal_request_data_obj = objects.HealVnfRequest(
            stack_id=stack_id,
            cause=(cause[-1] % vdu_name), additional_params=additional_params)

        plugin.heal_vnf(context, vnf_dict['id'], heal_request_data_obj)
