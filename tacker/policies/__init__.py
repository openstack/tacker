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


import itertools

from tacker.policies import base
from tacker.policies import vnf_lcm
from tacker.policies import vnf_package
from tacker.sol_refactored.api.policies import vnffm_v1
from tacker.sol_refactored.api.policies import vnflcm_v2
from tacker.sol_refactored.api.policies import vnfpm_v2


def list_rules():
    return itertools.chain(
        base.list_rules(),
        vnf_package.list_rules(),
        vnf_lcm.list_rules(),
        vnflcm_v2.list_rules(),
        vnffm_v1.list_rules(),
        vnfpm_v2.list_rules(),
    )
