# Copyright 2011 VMware, Inc.
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

# If ../tacker/__init__.py exists, add ../ to Python search path, so that
# it will override what happens to be installed in /usr/(local/)lib/python...

import sys

from oslo_config import cfg
import oslo_i18n
from oslo_service import service as common_service

from tacker._i18n import _
from tacker.common import config
from tacker import objects
from tacker import service
from tacker.sol_refactored import objects as sol_objects


oslo_i18n.install("tacker")


def main():
    # the configuration will be read into the cfg.CONF global data structure
    config.init(sys.argv[1:])
    objects.register_all()
    sol_objects.register_all()
    if not cfg.CONF.config_file:
        sys.exit(_("ERROR: Unable to find configuration file via the default"
                   " search paths (~/.tacker/, ~/, /etc/tacker/, /etc/) and"
                   " the '--config-file' option!"))

    try:
        tacker_api = service.serve_wsgi(service.TackerApiService)
        launcher = common_service.launch(cfg.CONF, tacker_api,
                                         workers=cfg.CONF.api_workers or None,
                                         restart_method='mutate')
        launcher.wait()
    except KeyboardInterrupt:
        pass
    except RuntimeError as e:
        sys.exit(_("ERROR: %s") % e)
