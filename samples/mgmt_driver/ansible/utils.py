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

from tacker.plugins.common import constants as plg_constants
from tacker.vnfm.mgmt_drivers import constants as mgmt_constants

CONFIG_FOLDER = "ScriptANSIBLE"


def get_event_by_action(action, failed_vdu_name):
    event_type = None
    if action == mgmt_constants.ACTION_INSTANTIATE_VNF:
        event_type = plg_constants.RES_EVT_INSTANTIATE
    elif action == mgmt_constants.ACTION_TERMINATE_VNF:
        event_type = plg_constants.RES_EVT_TERMINATE
    elif action == mgmt_constants.ACTION_HEAL_VNF:
        if failed_vdu_name:
            event_type = plg_constants.RES_EVT_HEAL
    elif action == mgmt_constants.ACTION_SCALE_IN_VNF:
        event_type = plg_constants.RES_EVT_SCALE
    elif action == mgmt_constants.ACTION_SCALE_OUT_VNF:
        event_type = plg_constants.RES_EVT_SCALE
    return event_type


def get_event_by_action_key(action_key):
    event_type = None
    if action_key == "instantiation":
        event_type = plg_constants.RES_EVT_INSTANTIATE
    elif action_key == "termination":
        event_type = plg_constants.RES_EVT_TERMINATE
    elif action_key == "healing":
        event_type = plg_constants.RES_EVT_HEAL
    elif action_key == "scale-in":
        event_type = plg_constants.RES_EVT_SCALE
    elif action_key == "scale-out":
        event_type = plg_constants.RES_EVT_SCALE
    return event_type
