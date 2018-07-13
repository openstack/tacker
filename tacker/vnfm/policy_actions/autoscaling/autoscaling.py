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

from tacker.plugins.common import constants
from tacker.vnfm.policy_actions import abstract_action
from tacker.vnfm import utils as vnfm_utils

LOG = logging.getLogger(__name__)


class VNFActionAutoscaling(abstract_action.AbstractPolicyAction):
    def get_type(self):
        return 'autoscaling'

    def get_name(self):
        return 'autoscaling'

    def get_description(self):
        return 'Tacker VNF auto-scaling policy'

    def execute_action(self, plugin, context, vnf_dict, args):
        vnf_id = vnf_dict['id']
        vnfm_utils.log_events(context, vnf_dict,
                              constants.RES_EVT_MONITOR,
                              "ActionAutoscalingHeat invoked")
        plugin.create_vnf_scale(context, vnf_id, args)
