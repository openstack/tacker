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

import json
import yaml

from jsonschema import exceptions as json_exp
from jsonschema import validate
from oslo_log import log as logging

from tacker.vnfm.mgmt_drivers.ansible import event_handler
from tacker.vnfm.mgmt_drivers.ansible import exceptions

from tacker.vnfm.mgmt_drivers.ansible.config_validator_schema import SCHEMA

LOG = logging.getLogger(__name__)
EVENT_HANDLER = event_handler.AnsibleEventHandler()


class AnsibleConfigValidator(object):
    def __init__(self):
        self._schema = yaml.safe_load(SCHEMA)

    def validate(self, config_yaml):
        try:
            validate(config_yaml, self._schema)
        except json_exp.ValidationError as err:
            raise exceptions.ConfigValidationError(
                details=str(err).splitlines()[0])

    def filter_vdus(self, context, vnf, event, mgmt_url, config_yaml):
        vdu_config = config_yaml.get("vdus", {})
        filtered_vdu_config = {}

        if vdu_config:
            for vdu in mgmt_url:
                if vdu in vdu_config:
                    filtered_vdu_config[vdu] = vdu_config.get(vdu)
                else:
                    msg = ("Could not find configuration entry for VDU '{}' "
                    "with IP Address '{}': skipping configuration")
                    EVENT_HANDLER.create_event(
                        context,
                        vnf,
                        event,
                        msg.format(vdu, json.dumps(mgmt_url.get(vdu, "")))
                    )

        config_yaml["vdus"] = filtered_vdu_config
        LOG.debug("filtered config yaml: {}".format(config_yaml))
        return config_yaml
