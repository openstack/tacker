# Copyright (C) 2022 Nippon Telegraph and Telephone Corporation
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
from tacker.tests.functional.sol_v2 import utils

utils.create_network('ft-net0')
utils.create_subnet('ft-ipv4-subnet0', 'ft-net0', '100.100.100.0/24', '4')
utils.create_subnet('ft-ipv6-subnet0', 'ft-net0', '1111:2222:3333::/64', '6')
utils.create_port('VDU2_CP1-1', 'net0')
utils.create_port('VDU2_CP1-2', 'net0')
