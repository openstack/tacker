# Copyright 2011 OpenStack Foundation
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

import gettext

from oslo_service import backend


gettext.install('tacker')

# NOTE: oslo.service defaults to its eventlet backend when nothing selects
# one, which no longer exists for tacker: there is no eventlet in the
# requirements and nothing monkey patches the standard library. Registering
# the hook here makes threading the default for every entry into the
# package, the services as well as the unit tests, the config generator and
# the docs build, while an explicit init_backend() still wins over it.
backend.register_backend_default_hook(lambda: backend.BackendType.THREADING)
