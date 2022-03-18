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

from oslo_log import log as logging

from tacker.plugins.common import constants
from tacker.vnfm import utils


LOG = logging.getLogger(__name__)


class AnsibleEventHandler(object):
    def create_event(self, context, vnf, event, msg, error_flag=False):
        vnf["status"] = constants.ERROR if error_flag else vnf["status"]
        utils.log_events(context, vnf, event, msg)
