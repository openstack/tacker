#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

POLICY_ALARMING = 'tosca.policies.tacker.Alarming'
DEFAULT_ALARM_ACTIONS = ['respawn', 'log', 'log_and_kill', 'notify']
VNF_CIRROS_CREATE_TIMEOUT = 300
VNFC_CREATE_TIMEOUT = 600
VNF_CIRROS_DELETE_TIMEOUT = 300
VNF_CIRROS_DEAD_TIMEOUT = 500
ACTIVE_SLEEP_TIME = 3
DEAD_SLEEP_TIME = 1
SCALE_WINDOW_SLEEP_TIME = 120
NS_CREATE_TIMEOUT = 400
NS_DELETE_TIMEOUT = 300
NOVA_CLIENT_VERSION = 2
