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

# NOTE: init_backend() can be called only once per process and must run
# before any other oslo.service module is imported, otherwise the default
# eventlet backend is selected implicitly. The get_backend_type() guard
# avoids BackendAlreadySelected when this module is imported alongside
# tacker.cmd.eventlet in the same process, e.g. by Sphinx autodoc during
# the docs build.
from oslo_service import backend

if backend.get_backend_type() is None:
    backend.init_backend(backend.BackendType.THREADING)

from tacker.conductor import conductor_server  # noqa: E402
from tacker import objects  # noqa: E402


def main():
    objects.register_all()
    conductor_server.main()
