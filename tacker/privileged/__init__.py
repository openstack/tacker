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


"""Setup privsep decorator."""

from oslo_privsep import capabilities as caps
from oslo_privsep import priv_context

default = priv_context.PrivContext(
    __name__,
    cfg_section='privsep',
    pypath=__name__ + '.default',
    capabilities=[caps.CAP_SYS_ADMIN,
                  caps.CAP_NET_ADMIN,
                  caps.CAP_DAC_OVERRIDE,
                  caps.CAP_DAC_READ_SEARCH,
                  caps.CAP_SYS_PTRACE],
)
