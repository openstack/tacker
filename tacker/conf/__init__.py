# Copyright (C) 2019 NTT DATA
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

import glance_store
from oslo_config import cfg

from tacker.conf import conductor
from tacker.conf import coordination
from tacker.conf import vnf_lcm
from tacker.conf import vnf_package

CONF = cfg.CONF
CONF.import_group('keystone_authtoken', 'keystonemiddleware.auth_token')

vnf_package.register_opts(CONF)
vnf_lcm.register_opts(CONF)
conductor.register_opts(CONF)
coordination.register_opts(CONF)
glance_store.register_opts(CONF)
