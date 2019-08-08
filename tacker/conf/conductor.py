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

from oslo_config import cfg


CONF = cfg.CONF

interval_opts = [
    cfg.IntOpt('vnf_package_delete_interval',
               default=1800,
               help=_('Seconds between running periodic tasks '
                      'to cleanup residues of deleted vnf packages')),
]


def register_opts(conf):
    conf.register_opts(interval_opts)


def list_opts():
    return {'DEFAULT': interval_opts}
