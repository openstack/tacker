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
from tacker.vnfm.mgmt_drivers import constants

from tacker.vnfm.mgmt_drivers.ansible import event_handler
from tacker.vnfm.mgmt_drivers.ansible import exceptions

from tacker.vnfm.mgmt_drivers.ansible.config_actions import abstract_config
from tacker.vnfm.mgmt_drivers.ansible.config_actions.\
    vm_app_config import ansible_playbook_exec

LOG = logging.getLogger(__name__)
EVENT_HANDLER = event_handler.AnsibleEventHandler()


class VmAppConfigAction(abstract_config.AbstractConfigAction):
    def __init__(self):
        self._mgmt_executors = {}
        self._mgmt_executors["ansible"] = \
            ansible_playbook_exec.AnsiblePlaybookExecutor()

        self._vdu = None
        self._vnf = None
        self._context = None
        self._mgmt_executor_type = None

    def execute(self, **kwargs):
        vdu = kwargs["vdu"]
        vnf = kwargs["vnf"]
        context = kwargs["context"]
        conf_value = kwargs["conf_value"]
        mgmt_url = kwargs["mgmt_url"]
        action = kwargs["action"]
        failed_vdu_name = vnf.get("failed_vdu_name", "")
        cfg_parser = kwargs["cfg_parser"]
        stack_map = kwargs["stack_map"]
        config_yaml = kwargs["config_yaml"]

        self._vdu = vdu
        self._vnf = vnf
        self._context = context

        mgmt_executor = \
            self._get_mgmt_executor(conf_value.get("type", "ansible"))
        mgmt_executor_type = self._mgmt_executor_type
        action_key = self._get_action_key(action, failed_vdu_name)
        skip_execute = self._is_skipped(action_key, failed_vdu_name, stack_map)

        mgmt_ip_address = ""

        mgmt_ip_address_list = self._get_mgmt_ip_address(skip_execute,
            mgmt_url, stack_map)

        for mgmt_ip_address in mgmt_ip_address_list:
            mgmt_executor.execute(
                vdu=vdu,
                vnf=vnf,
                context=context,
                mgmt_ip_address=mgmt_ip_address,
                conf_value=conf_value,
                mgmt_url=mgmt_url,
                cfg_parser=cfg_parser,
                failed_vdu_name=failed_vdu_name,
                action_key=action_key,
                skip_execute=skip_execute,
                config_yaml=config_yaml,
                mgmt_executor_type=mgmt_executor_type
            )

    def _get_mgmt_executor(self, mgmt_type):
        self._mgmt_executor_type = mgmt_type
        mgmt_executor = self._mgmt_executors.get(mgmt_type, None)

        if not mgmt_executor:
            raise exceptions.InvalidKeyError(vdu=self._vdu, key=mgmt_type)

        return mgmt_executor

    def _get_mgmt_ip_address(self, skip_execute, mgmt_url, stack_map):
        mgmt_ip_address = []
        if not skip_execute:
            if stack_map:
                mgmt_ip_address = stack_map.get(self._vdu, "")
            else:
                mgmt_ip_address = mgmt_url.get(self._vdu, "")

            if not mgmt_ip_address:
                raise exceptions.DataRetrievalError(
                    vdu=self._vdu,
                    details="Cannot get mgmt address for the VDU: {}".format(
                        self._vdu)
                )

            if not isinstance(mgmt_ip_address, list):
                # put ip inside list
                mgmt_ip_address = [mgmt_ip_address]
        return mgmt_ip_address

    def _get_action_key(self, action, failed_vdu_name):
        # if no key for a particular VNF operation is found,
        # use the default 'playbooks'
        action_key = None
        if action == constants.ACTION_HEAL_VNF:
            if failed_vdu_name:
                LOG.debug("failed vdu name: %s", failed_vdu_name)
                action_key = "healing"
        elif action == constants.ACTION_INSTANTIATE_VNF:
            action_key = "instantiation"
        elif action == constants.ACTION_TERMINATE_VNF:
            action_key = "termination"
        elif action == constants.ACTION_SCALE_IN_VNF:
            action_key = "scale-in"
        elif action == constants.ACTION_SCALE_OUT_VNF:
            action_key = "scale-out"
        return action_key

    def _is_skipped(self, action_key, failed_vdu_name, stack_map):
        is_skipped = False
        if action_key:
            if action_key == "healing":
                if self._vdu != failed_vdu_name:
                    is_skipped = True
                    LOG.debug("VDU %s did not fail.", self._vdu)
            elif action_key == "scale-in" or action_key == "scale-out":
                if self._vdu not in stack_map:
                    is_skipped = True
                    LOG.debug("VDU is not scaling target: {}".format(
                        self._vdu))
        else:
            is_skipped = True
            LOG.debug("Action not supported.")
        return is_skipped
