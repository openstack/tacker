# Copyright 2012 OpenStack Foundation.
# All Rights Reserved.
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

# service type constants:
CORE = "CORE"
DUMMY = "DUMMY"
VNFM = "VNFM"
NFVO = "NFVO"
COMMONSERVICES = "COMMONSERVICES"

COMMON_PREFIXES = {
    CORE: "",
    DUMMY: "/dummy_svc",
    VNFM: "",
    NFVO: "",
    COMMONSERVICES: ""
}

# Service operation status constants
ACTIVE = "ACTIVE"
ACK = "ACK"
INACTIVE = "INACTIVE"
PENDING_INSTANTIATE = "PENDING_INSTANTIATE"
PENDING_CREATE = "PENDING_CREATE"
PENDING_UPDATE = "PENDING_UPDATE"
PENDING_DELETE = "PENDING_DELETE"
PENDING_SCALE_IN = "PENDING_SCALE_IN"
PENDING_SCALE_OUT = "PENDING_SCALE_OUT"
PENDING_HEAL = "PENDING_HEAL"
PENDING_TERMINATE = "PENDING_TERMINATE"
DEAD = "DEAD"
ERROR = "ERROR"
NACK = "NACK"

ACTIVE_PENDING_STATUSES = (
    ACTIVE,
    PENDING_CREATE,
    PENDING_UPDATE
)

POLICY_SCALING = 'tosca.policies.tacker.Scaling'
POLICY_SCALING_ACTIONS = (ACTION_SCALE_OUT,
                          ACTION_SCALE_IN) = ('out', 'in')
POLICY_ACTIONS = {POLICY_SCALING: POLICY_SCALING_ACTIONS}
POLICY_ALARMING = 'tosca.policies.tacker.Alarming'
POLICY_EVENT_ALARMING = 'tosca.policies.tacker.EventAlarming'
VALID_POLICY_TYPES = [POLICY_SCALING, POLICY_ALARMING]
POLICY_RESERVATION = 'tosca.policies.tacker.Reservation'
RESERVATION_POLICY_ACTIONS = ['start_actions',
                              'before_end_actions', 'end_actions']
DEFAULT_ALARM_ACTIONS = ['respawn', 'log', 'log_and_kill', 'notify']

RES_TYPE_VNFD = "vnfd"
RES_TYPE_NSD = "nsd"
RES_TYPE_NS = "ns"
RES_TYPE_VNF = "vnf"
RES_TYPE_VIM = "vim"

RES_EVT_CREATE = "CREATE"
RES_EVT_INSTANTIATE = "INSTANTIATE"
RES_EVT_TERMINATE = "TERMINATE"
RES_EVT_DELETE = "DELETE"
RES_EVT_UPDATE = "UPDATE"
RES_EVT_MONITOR = "MONITOR"
RES_EVT_SCALE = "SCALE"
RES_EVT_NA_STATE = "Not Applicable"
RES_EVT_ONBOARDED = "OnBoarded"
RES_EVT_HEAL = "HEAL"
RES_EVT_MAINTENANCE = [
    "MAINTENANCE", "SCALE_IN", "MAINTENANCE_COMPLETE",
    "PREPARE_MAINTENANCE", "PLANNED_MAINTENANCE", "INSTANCE_ACTION_DONE"
]


VNF_STATUS_TO_EVT_TYPES = {PENDING_CREATE: RES_EVT_CREATE,
                           PENDING_UPDATE: RES_EVT_UPDATE,
                           PENDING_DELETE: RES_EVT_DELETE,
                           PENDING_HEAL: RES_EVT_HEAL}


RES_EVT_CREATED_FLD = "created_at"
RES_EVT_DELETED_FLD = "deleted_at"
RES_EVT_UPDATED_FLD = "updated_at"

TYPE_COMPUTE = "COMPUTE"
TYPE_LINKPORT = "LINKPORT"
TYPE_STORAGE = "STORAGE"
TYPE_VL = "VL"
