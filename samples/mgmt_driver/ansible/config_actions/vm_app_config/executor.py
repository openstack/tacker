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
from oslo_log import log as logging

from tacker.vnfm.mgmt_drivers.ansible import event_handler
from tacker.vnfm.mgmt_drivers.ansible import exceptions
from tacker.vnfm.mgmt_drivers.ansible import utils

from tacker.vnfm.mgmt_drivers.ansible.config_actions.\
    vm_app_config import config_walker

import subprocess

LOG = logging.getLogger(__name__)
EVENT_HANDLER = event_handler.AnsibleEventHandler()
OPTS = [
    cfg.StrOpt("user", default="root",
        help="user name to login ansible server"),
    cfg.StrOpt("password", default="root123",
        help="password to login ansible server"),
    cfg.StrOpt("host", default="127.0.0.1",
        help="host of the ansible server"),
    cfg.StrOpt("private_key_file", default="",
        help="private_key_file of the ansible server"),
    cfg.IntOpt("retry_count", default=120, help="maximum no. of retries"),
    cfg.IntOpt("retry_interval", default=30,
        help="time in seconds before next retry"),
    cfg.IntOpt("connection_wait_timeout", default=3600,
        help="time in seconds before ssh timeout"),
    cfg.IntOpt("command_execution_wait_timeout", default=3600,
        help="maximum time allocated to a command to return result"),
]
cfg.CONF.register_opts(OPTS, "ansible")


class Executor(config_walker.VmAppConfigWalker):
    def __init__(self):
        self._queue = {}
        self._execute_host = {}
        self._local_execute_host = {}
        self._target_host = {}
        self._conf_opts = {}
        self._node_pair_ip = None

        self._action_key = ""
        self._skip_execute = False
        self._failed_vdu_name = None

        self._vdu = None
        self._vnf = None
        self._context = None
        self._mgmt_ip_address = None
        self._conf_value = None
        self._mgmt_url = None
        self._cfg_parser = None
        self._mgmt_executor_type = None

        super(Executor, self).__init__()

    def execute(self, **kwargs):
        self._vdu = kwargs["vdu"]
        self._vnf = kwargs["vnf"]
        self._context = kwargs["context"]
        self._mgmt_ip_address = kwargs["mgmt_ip_address"]
        self._conf_value = kwargs["conf_value"]
        self._mgmt_url = kwargs["mgmt_url"]
        self._cfg_parser = kwargs["cfg_parser"]
        self._action_key = kwargs["action_key"]
        self._skip_execute = kwargs["skip_execute"]
        self._failed_vdu_name = kwargs["failed_vdu_name"]
        self._mgmt_executor_type = kwargs["mgmt_executor_type"]
        self.set_config(kwargs["config_yaml"])

        if self._skip_execute:
            LOG.debug("Skip execution for VDU: {}".format(self._vdu))
            return

        self._conf_opts = {
            "user": cfg.CONF.ansible.user,
            "password": cfg.CONF.ansible.password,
            "host": cfg.CONF.ansible.host,
            "private_key_file": cfg.CONF.ansible.private_key_file
        }
        retry_count = self._conf_value.get("retry_count",
            cfg.CONF.ansible.retry_count)
        retry_interval = self._conf_value.get("retry_interval",
            cfg.CONF.ansible.retry_interval)
        connection_wait_timeout = self._conf_value.get(
            "connection_wait_timeout",
            cfg.CONF.ansible.connection_wait_timeout)
        command_execution_wait_timeout = \
            self._conf_value.get("command_execution_wait_timeout",
                cfg.CONF.ansible.command_execution_wait_timeout)

        self._execute_host = self._get_execute_host(
            execute_host=self._conf_value.get("execute-host", {}),
            conf_value=self._conf_value)
        self._target_host = self._get_target_host(self._conf_value)
        self._node_pair_ip = self._get_node_pair_ip(self._conf_value,
            self._mgmt_url)

        # translate some params
        inline_param = {
            'mgmt_ip_address': self._mgmt_ip_address,
            'vdu': self._vdu
        }

        retry_count = self._cfg_parser.substitute(retry_count, **inline_param)
        retry_interval = self._cfg_parser.substitute(retry_interval,
            **inline_param)
        connection_wait_timeout = self._cfg_parser.substitute(
            connection_wait_timeout, **inline_param)
        command_execution_wait_timeout = self._cfg_parser.substitute(
            command_execution_wait_timeout, **inline_param)

        LOG.debug("Command execution settings - retry count: {}".format(
            retry_count))
        LOG.debug("Command execution settings - retry interval: {}".format(
            retry_interval))
        LOG.debug("Command execution settings - "
            "connection_wait_timeout: {}".format(connection_wait_timeout))
        LOG.debug("Command execution settings - "
            "command_execution_wait_timeout: {}".format(
                command_execution_wait_timeout))

        playbook_cmd_list = self._conf_value.get(self._action_key, None)
        if not playbook_cmd_list:
            msg = "No '{}' configuration defined for VDU '{}' "
            "with IP Address '{}'"
            EVENT_HANDLER.create_event(
                self._context,
                self._vnf,
                utils.get_event_by_action_key(self._action_key),
                msg.format(self._action_key, self._vdu, self._mgmt_ip_address)
            )
        else:
            LOG.debug("conf_value @ {} {}".format(self._action_key,
                playbook_cmd_list))

            self._sort_playbook_cmd_list(playbook_cmd_list)
            LOG.debug("Sorted playbooks/commands: {}".format(
                self._queue.values()))

            self._execute(retry_count, retry_interval,
                connection_wait_timeout, command_execution_wait_timeout)

    def _execute(self, retry_count, retry_interval, connection_wait_timeout,
            command_execution_wait_timeout):
        for order in sorted(self._queue):
            playbook_cmd_list = self._queue[order]

            for playbook_cmd in playbook_cmd_list:
                LOG.debug("playbook/command: {}".format(playbook_cmd))

                self._pre_execution(playbook_cmd)

                cmd = self._get_final_command(playbook_cmd)
                LOG.debug("command for execution: {}".format(cmd))

                res_code = -1
                try:
                    res_code, host = self._execute_cmd(
                        cmd,
                        retry_count,
                        retry_interval,
                        connection_wait_timeout,
                        command_execution_wait_timeout
                    )
                except exceptions.AnsibleDriverException:
                    raise
                except Exception as ex:
                    raise exceptions.CommandExecutionError(vdu=self._vdu,
                        details=ex)

                self._post_execution(cmd, res_code, host)

                if self._is_execution_error(res_code):
                    raise exceptions.CommandExecutionError(
                        vdu=self._vdu,
                        details="Non-zero return code"
                    )

    def _sort_playbook_cmd_list(self, playbook_cmd_list):
        self._queue = {}
        for playbook_cmd in playbook_cmd_list:
            self._add_to_queue(playbook_cmd)

    def _add_to_queue(self, playbook_cmd):
        if "order" not in playbook_cmd:
            raise exceptions.MandatoryKeyNotDefinedError(vdu=self._vdu,
                key="order")

        try:
            order = int(playbook_cmd["order"])
        except ValueError:
            raise exceptions.InvalidValueError(vdu=self._vdu, key="order")

        if order in self._queue:
            self._queue[order].append(playbook_cmd)
        else:
            entity_list = []
            entity_list.append(playbook_cmd)
            self._queue[order] = entity_list

    def _execute_cmd(self, cmd, retry_count, retry_interval,
            connection_wait_timeout, command_execution_wait_timeout):

        if self._local_execute_host:
            user = self._local_execute_host["user"]
            host = self._local_execute_host["host"]
            password = self._local_execute_host["password"]
            host_private_key_file = \
                self._local_execute_host["host_private_key_file"]

        else:
            user = self._execute_host["user"]
            host = self._execute_host["host"]
            password = self._execute_host["password"]
            host_private_key_file = \
                self._execute_host["host_private_key_file"]

        LOG.debug("Executing command: {} for VDU {}, host: {}, "
            "username: {}, password: {}, private_key_file {}".format(
                cmd, self._vdu, host, user, password, host_private_key_file))

        # create command executor
        result = subprocess.Popen(cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=True, universal_newlines=True)
        std_out, std_err = result.communicate()

        LOG.debug("command execution result code: {}".format(
            result.returncode))
        LOG.debug("command execution result code: {}".format(std_out))
        LOG.debug("command execution result code: {}".format(std_err))

        return result.returncode, host

    def _post_execution(self, cmd, res_code, host):

        msg = ("Command executed for the VDU '{}' with IP Address "
        "'{}' on execute-host '{}' and result code '{}' => {}".format(
            self._vdu,
            self._mgmt_ip_address,
            host,
            res_code,
            cmd))

        EVENT_HANDLER.create_event(
            self._context,
            self._vnf,
            utils.get_event_by_action_key(self._action_key),
            msg,
            self._is_execution_error(res_code)
        )

        # reset local execute-host details
        self._local_execute_host = None

    def _get_execute_host(self, execute_host, conf_value=None,
            use_default=True):
        # some inline variables for parameter translation
        inline_param = {
            'mgmt_ip_address': self._mgmt_ip_address,
            'vdu': self._vdu
        }

        if not execute_host:
            if use_default:
                user, password, host, host_private_key_file = \
                    self._get_default_execute_host(conf_value)
            else:
                return None
        else:
            host_name = execute_host.get("host", "")
            # process host
            if host_name in self._mgmt_url:
                # the given config value "host" is a VDU name
                host = self._mgmt_url.get(host_name, "")
                vdu_creds = self.get_creds_from_vdu(self._vdu, host_name)
                user = vdu_creds.get("username", "")
                password = vdu_creds.get("password", "")
                host_private_key_file = vdu_creds.get("priv_key_file", "")
            else:
                # the given config value "host" is an address
                host = host_name
                user = execute_host.get("username", "")
                password = execute_host.get("password", "")
                host_private_key_file = execute_host.get("priv_key_file", "")

        # validate config
        if not host:
            raise exceptions.DataRetrievalError(
                vdu=self._vdu,
                details="Unable to retrieve 'host' for execute-host"
            )

        if not user:
            raise exceptions.DataRetrievalError(
                vdu=self._vdu,
                details="Unable to retrieve 'username' for execute-host"
            )

        if not password and not host_private_key_file:
            raise exceptions.DataRetrievalError(
                vdu=self._vdu,
                details="Unable to retrieve either 'password' or "
                "'priv_key_file' for execute-host"
            )

        user = self._cfg_parser.substitute(user, **inline_param)
        password = self._cfg_parser.substitute(password, **inline_param)
        host = self._cfg_parser.substitute(host, **inline_param)
        host_private_key_file = self._cfg_parser.substitute(
            host_private_key_file, **inline_param)

        execute_host = {
            "user": user,
            "password": password,
            "host": host,
            "host_private_key_file": host_private_key_file
        }

        LOG.debug("execute-host->user: {}".format(user))
        LOG.debug("execute-host->password: {}".format(password))
        LOG.debug("execute-host->host: {}".format(host))
        LOG.debug("execute-host->pkeyfile: {}".format(host_private_key_file))

        return execute_host

    def _pre_execution(self, playbook_cmd):
        local_execute_host = playbook_cmd.get("execute-host", {})
        LOG.debug('conf_value local_execute_host: {}'.format(
            local_execute_host))
        self._local_execute_host = self._get_execute_host(
            execute_host=local_execute_host, use_default=False)

    def _get_final_command(self, playbook_cmd):
        raise NotImplementedError

    def _is_execution_error(self, res_code):
        raise NotImplementedError

    def _get_target_host(self, conf_value):
        raise NotImplementedError

    def _get_node_pair_ip(self, conf_value, mgmt_url):
        raise NotImplementedError

    def _get_default_execute_host(self, conf_value=None):
        raise NotImplementedError
