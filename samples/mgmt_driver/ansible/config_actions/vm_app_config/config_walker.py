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

from tacker.vnfm.mgmt_drivers.ansible import exceptions

LOG = logging.getLogger(__name__)


class VmAppConfigWalker(object):
    def __init__(self):
        self._config = None

    def set_config(self, config_value):
        self._config = config_value.get("vdus", {})

    def get_creds_from_vdu(self, vdu, vdu_name):
        vdu_dict = self._config.get(vdu_name, {}).get("config", {}).get(
            "vm_app_config", {})
        if not vdu_dict:
            exceptions.DataRetrievalError(
                vdu=vdu,
                details=("Unable to retrieve configuration information"
                "for VDU: {}".format(vdu_name))
            )
        LOG.debug("vdu_dict: {}".format(vdu_dict))

        creds = {
            "username": vdu_dict.get("username", ""),
            "password": vdu_dict.get("password", ""),
            "priv_key_file": vdu_dict.get("priv_key_file", "")
        }

        LOG.debug("creds: {}".format(creds))
        return creds
