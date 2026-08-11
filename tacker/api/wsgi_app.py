# Copyright (C) 2026 Nippon Telegraph and Telephone Corporation
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

"""WSGI application entry point for the Tacker API.

This module provides the WSGI application used to run the Tacker API
under a WSGI server such as uWSGI or mod_wsgi, without the
eventlet based standalone server. Use ``tacker.api.wsgi.api`` as the
WSGI module, or the ``tacker-api-wsgi`` script generated from the
``wsgi_scripts`` entry point for non-editable installations.
"""

import os

from oslo_config import cfg

from tacker.common import config
from tacker import objects
from tacker.sol_refactored import objects as sol_objects


CONFIG_FILES = ['api-paste.ini', 'tacker.conf']


def _get_config_files(env=None):
    if env is None:
        env = os.environ
    dirname = env.get('OS_TACKER_CONFIG_DIR', '/etc/tacker').strip()
    return [os.path.join(dirname, config_file)
            for config_file in CONFIG_FILES
            if os.path.exists(os.path.join(dirname, config_file))]


def init_application():
    conf_files = _get_config_files()
    config.init([], default_config_files=conf_files)
    config.setup_logging(cfg.CONF)

    objects.register_all()
    sol_objects.register_all()

    return config.load_paste_app('tacker')
