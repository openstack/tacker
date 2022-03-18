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
import os

from oslo_log import log as logging
from six import iteritems
from tacker.vnfm.mgmt_drivers.ansible import event_handler
from tacker.vnfm.mgmt_drivers.ansible import exceptions

from tacker.vnfm.mgmt_drivers.ansible.config_actions.\
    vm_app_config import executor

LOG = logging.getLogger(__name__)
EVENT_HANDLER = event_handler.AnsibleEventHandler()


class AnsiblePlaybookExecutor(executor.Executor):
    def _get_default_execute_host(self, conf_value=None):
        user = self._conf_opts["user"]
        password = self._conf_opts["password"]
        host = self._conf_opts["host"]
        host_private_key_file = self._conf_opts["private_key_file"]
        return user, password, host, host_private_key_file

    def _get_target_host(self, conf_value):
        target_user = conf_value.get("username", "")
        target_password = conf_value.get("password", "")
        target_private_key_file = conf_value.get("priv_key_file", "")
        target_host = {
            "target_user": target_user,
            "target_password": target_password,
            "target_private_key_file": target_private_key_file
        }

        return target_host

    def _get_playbook_target_hosts(self, playbook_cmd):
        target_hosts = playbook_cmd.get("target_hosts", "")
        host_ips = ""
        if not target_hosts:
            host_ips = ",{}".format(self._mgmt_ip_address)
        else:
            for host_name in target_hosts:
                # process host
                if host_name in self._mgmt_url:
                    # the given config value "host" is a VDU name
                    host_ip = self._mgmt_url.get(host_name, "")
                else:
                    # the given config value "host" is an address
                    host_ip = host_name
                host_ips = host_ips + ",{}".format(host_ip)
        return host_ips

    def _get_node_pair_ip(self, conf_value, mgmt_url):
        node_pair_ip = None
        if "node_pair" in conf_value:
            node_pair_ip = mgmt_url.get(conf_value["node_pair"], "")

        return node_pair_ip

    def _get_params(self, playbook_cmd):
        params = ""
        obj_params = playbook_cmd.get("params", "")
        if obj_params:
            for key, value in iteritems(obj_params):
                if isinstance(value, dict):
                    str_value = json.dumps(
                        value, separators=(',', ':')).replace('"', '\\"')
                else:
                    str_value = "{}".format(value)

                params += "{}={} ".format(key, str_value)
        return params

    def _convert_mgmt_url_to_extra_vars(self, mgmt_url):
        return json.dumps(mgmt_url)

    def _get_playbook_path(self, playbook_cmd):
        path = playbook_cmd.get("path", "")
        if not path:
            raise exceptions.ConfigValidationError(
                vdu=self._vdu,
                details="Playbook {} did not specify path".format(playbook_cmd)
            )
        return path

    def _get_final_command(self, playbook_cmd):
        init_cmd = ("cd {} ; ansible-playbook -i {} -vvv {} "
        "--extra-vars \"host={} node_pair_ip={}".format(
            os.path.dirname(self._get_playbook_path(playbook_cmd)),
            self._get_playbook_target_hosts(playbook_cmd),
            self._get_playbook_path(playbook_cmd),
            self._mgmt_ip_address,
            self._node_pair_ip))
        ssh_args = ("ansible_ssh_extra_args='-o StrictHostKeyChecking=no "
        "-o UserKnownHostsFile=/dev/null'")

        target_host_param = False
        ssh_creds = ""

        if self._target_host:
            if self._target_host["target_user"]:
                ssh_creds = "ansible_ssh_user={}".format(
                    self._target_host["target_user"]
                )
                target_host_param = True

            if self._target_host["target_private_key_file"]:
                if not target_host_param:
                    ssh_creds = "ansible_ssh_private_key_file={}".format(
                        self._target_host["target_private_key_file"]
                    )
                    target_host_param = True
                else:
                    ssh_creds = ssh_creds + " ansible_ssh_private_key_"
                    "file={}".format(
                        self._target_host["target_private_key_file"])

            if self._target_host["target_password"]:
                if not target_host_param:
                    ssh_creds = "ansible_ssh_pass={}".format(
                        self._target_host["target_password"]
                    )
                else:
                    ssh_creds = ssh_creds + " ansible_ssh_pass={}".format(
                        self._target_host["target_password"]
                    )

        ssh_creds = ssh_creds + "\""
        mgmt_url_vars = " --extra-vars '{}'".format(
            self._convert_mgmt_url_to_extra_vars(self._mgmt_url))

        cmd_raw = "{} {} {} {} {}".format(
            init_cmd,
            ssh_args,
            self._get_params(playbook_cmd),
            ssh_creds,
            mgmt_url_vars
        )

        # substitute passed VNF parameter to its corresponding value
        inline_param = {
            'mgmt_ip_address': self._mgmt_ip_address,
            'vdu': self._vdu
        }
        return self._cfg_parser.substitute(cmd_raw, **inline_param)

    def _is_execution_error(self, res_code):
        return False if res_code == 0 else True
