# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2013, 2014 Intel Corporation.
# Copyright 2013, 2014 Isaku Yamahata <isaku.yamahata at intel com>
#                                     <isaku.yamahata at gmail com>
# All Rights Reserved.
#
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

# sevice type
SVC_TYPE_ROUTER = 'router'
SVC_TYPE_LOADBALANCER = 'loadbalancer'

# attribute key for service to spin up device
# for nova driver. novaclient library uses those
ATTR_KEY_IMAGE = 'image'
ATTR_KEY_FLAVOR = 'flavor'
ATTR_KEY_MGMT_NETWORK = 'mgmt-network'

# attribute key for device template for heat
ATTR_KEY_HEAT_STACK_NAME = 'stack_name'
ATTR_KEY_HEAT_TEMPLATE_URL = 'template_url'
ATTR_KEY_HEAT_TEMPLATE = 'template'
ATTR_KEY_HEAT_FILES = 'files'
ATTR_KEY_HEAT_PARAMETERS = 'parameters'

# Role of service context
ROLE_NONE = 'None'
ROLE_MGMT = 'mgmt'
ROLE_TWOLEG_INGRESS = 'two-leg-ingress'
ROLE_TWOLEG_EGRESS = 'two-leg-egress'
