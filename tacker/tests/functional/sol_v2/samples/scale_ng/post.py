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

utils.delete_network('ft-net0')
# NOTE: subnet is automatically deleted by network deletion
utils.delete_port('VDU2_CP1-1')
utils.delete_port('VDU2_CP1-2')
