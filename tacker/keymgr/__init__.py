# Copyright (c) 2015 The Johns Hopkins University/Applied Physics Laboratory
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
from oslo_utils import importutils

key_manager_opts = [
    cfg.StrOpt('api_class',
               default='tacker.keymgr.barbican_key_manager'
                       '.BarbicanKeyManager',
               help='The full class name of the key manager API class'),
]


def config_opts():
    return [('key_manager', key_manager_opts)]


def API(auth_url, configuration=None):
    conf = configuration or cfg.CONF
    conf.register_opts(key_manager_opts, group='key_manager')

    cls = importutils.import_class(conf.key_manager.api_class)
    return cls(auth_url)
