# Copyright (C) 2023 Fujitsu
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

from oslo_config import cfg

from tacker._i18n import _

CONF = cfg.CONF

policy_opts = [
    cfg.BoolOpt('enhanced_tacker_policy',
               default=False,
               help=_('Enable enhanced tacker policy')),
]


def register_opts(conf):
    conf.register_opts(policy_opts, group='oslo_policy')


def list_opts():
    return {'oslo_policy': policy_opts}
