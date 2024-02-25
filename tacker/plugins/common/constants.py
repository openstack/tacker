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
PENDING_CHANGE_EXT_CONN = "PENDING_CHANGE_EXT_CONN"
DEAD = "DEAD"
ERROR = "ERROR"
NACK = "NACK"

PENDING_STATUSES = (
    PENDING_INSTANTIATE,
    PENDING_CREATE,
    PENDING_UPDATE,
    PENDING_DELETE,
    PENDING_SCALE_IN,
    PENDING_SCALE_OUT,
    PENDING_HEAL,
    PENDING_TERMINATE,
    PENDING_CHANGE_EXT_CONN,
)
ALL_STATUSES = (
    ACTIVE,
    INACTIVE,
    ERROR,
    *PENDING_STATUSES,
)

RES_EVT_INSTANTIATE = "INSTANTIATE"
RES_EVT_TERMINATE = "TERMINATE"
RES_EVT_SCALE = "SCALE"
RES_EVT_HEAL = "HEAL"

TYPE_COMPUTE = "COMPUTE"
TYPE_LINKPORT = "LINKPORT"
TYPE_STORAGE = "STORAGE"
TYPE_VL = "VL"
