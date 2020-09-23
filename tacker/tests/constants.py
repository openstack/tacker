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
POLICY_RESERVATION = 'tosca.policies.tacker.Reservation'
VNF_CIRROS_CREATE_TIMEOUT = 300
VNFC_CREATE_TIMEOUT = 600
VNF_CIRROS_UPDATE_TIMEOUT = 300
VNF_CIRROS_DELETE_TIMEOUT = 300
VNF_CIRROS_DEAD_TIMEOUT = 500
ACTIVE_SLEEP_TIME = 3
DEAD_SLEEP_TIME = 1
SCALE_WINDOW_SLEEP_TIME = 120
SCALE_SLEEP_TIME = 120
NS_CREATE_TIMEOUT = 400
NS_DELETE_TIMEOUT = 300
NOVA_CLIENT_VERSION = 2
VDU_MARK_UNHEALTHY_TIMEOUT = 500
VDU_MARK_UNHEALTHY_SLEEP_TIME = 3
VDU_AUTOHEALING_TIMEOUT = 500
VDU_AUTOHEALING_SLEEP_TIME = 3
VNF_CIRROS_PENDING_HEAL_TIMEOUT = 300
PENDING_SLEEP_TIME = 3

# Blazar related
LEASE_EVENT_STATUS = 'DONE'
START_LEASE_EVET_TYPE = 'start_lease'
LEASE_CHECK_EVENT_TIMEOUT = 300
LEASE_CHECK_SLEEP_TIME = 3
UUID = 'f26f181d-7891-4720-b022-b074ec1733ef'
INVALID_UUID = 'f181d-7891-4720-b022-b074ec3ef'
# artifact related
ARTIFACT_PATH = 'Scripts/install.sh'
INVALID_ARTIFACT_PATH = 'Fake_Scripts/fake_install.sh'
