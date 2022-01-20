# All Rights Reserved.
#
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

import os
import time

import eventlet
from oslo_log import log as logging
from oslo_serialization import jsonutils
import paramiko

from tacker.common import cmd_executer
from tacker.extensions import vnfm

LOG = logging.getLogger(__name__)
HELM_CMD_TIMEOUT = 30
HELM_INSTALL_TIMEOUT = 120
HELM_UPGRADE_TIMEOUT = 120
VALUE_SPLIT_CHARACTER = '.'
TRANSPORT_RETRIES = 2
TRANSPORT_WAIT = 15


class HelmClient():
    """Helm client for hosting containerized vnfs"""

    def __init__(self, ip, username, password):
        self.host_ip = ip
        self.username = username
        self.password = password
        self.commander = cmd_executer.RemoteCommandExecutor(
            user=username,
            password=password,
            host=ip,
            timeout=HELM_CMD_TIMEOUT)

    def _execute_command(self, ssh_command, timeout=HELM_CMD_TIMEOUT, retry=0):
        eventlet.monkey_patch()
        while retry >= 0:
            try:
                with eventlet.Timeout(timeout, True):
                    result = self.commander.execute_command(
                        ssh_command, input_data=None)
                    break
            except eventlet.timeout.Timeout:
                error_message = ('It is time out, When execute command: '
                                 f'{ssh_command}.')
                LOG.debug(error_message)
                retry -= 1
                if retry < 0:
                    self.close_session()
                    LOG.error(error_message)
                    raise vnfm.HelmClientOtherError(
                        error_message=error_message)
                time.sleep(30)
        if result.get_return_code():
            self.close_session()
            err = result.get_stderr()
            LOG.error(err)
            raise vnfm.HelmClientRemoteCommandError(message=err)
        return result.get_stdout()

    def add_repository(self, repo_name, repo_url):
        # execute helm repo add command
        ssh_command = f"helm repo add {repo_name} {repo_url}"
        self._execute_command(ssh_command)

    def remove_repository(self, repo_name):
        # execute helm repo remove command
        ssh_command = f"helm repo remove {repo_name}"
        self._execute_command(ssh_command)

    def _transport_helmchart(self, source_path, target_path):
        # transfer helm chart file
        retry = TRANSPORT_RETRIES
        while retry > 0:
            try:
                connect = paramiko.Transport(self.host_ip, 22)
                connect.connect(username=self.username, password=self.password)
                sftp = paramiko.SFTPClient.from_transport(connect)
                # put helm chart file
                sftp.put(source_path, target_path)
                connect.close()
                return
            except paramiko.SSHException as e:
                LOG.debug(e)
                retry -= 1
                if retry == 0:
                    self.close_session()
                    LOG.error(e)
                    raise paramiko.SSHException()
                time.sleep(TRANSPORT_WAIT)

    def put_helmchart(self, source_path, target_dir):
        # create helm chart directory and change permission
        ssh_command = (f"if [ ! -d {target_dir} ]; then "
                       f"`sudo mkdir -p {target_dir}; "
                       f"sudo chown -R {self.username} {target_dir};`; fi")
        self._execute_command(ssh_command)
        # get helm chart name and target path
        chartfile_name = source_path[source_path.rfind(os.sep) + 1:]
        target_path = os.path.join(target_dir, chartfile_name)
        # transport helm chart file
        self._transport_helmchart(source_path, target_path)
        # decompress helm chart file
        ssh_command = f"tar -zxf {target_path} -C {target_dir}"
        self._execute_command(ssh_command)

    def delete_helmchart(self, target_path):
        # delete helm chart folder
        ssh_command = f"sudo rm -rf {target_path}"
        self._execute_command(ssh_command)

    def install(self, release_name, chart_name, namespace, parameters):
        # execute helm install command
        ssh_command = f"helm install {release_name} {chart_name}"
        if namespace:
            ssh_command = f"{ssh_command} --namespace {namespace}"
        if parameters:
            for param in parameters:
                ssh_command = f"{ssh_command} --set {param}"
        self._execute_command(ssh_command, timeout=HELM_INSTALL_TIMEOUT)

    def uninstall(self, release_name, namespace):
        # execute helm uninstall command
        ssh_command = f"helm uninstall {release_name}"
        if namespace:
            ssh_command = f"{ssh_command} --namespace {namespace}"
        self._execute_command(ssh_command, timeout=HELM_INSTALL_TIMEOUT)

    def get_manifest(self, release_name, namespace):
        # execute helm get manifest command
        ssh_command = f"helm get manifest {release_name}"
        if namespace:
            ssh_command = f"{ssh_command} --namespace {namespace}"
        result = self._execute_command(ssh_command)
        # convert manifest to text format
        mf_content = ''.join(result)
        return mf_content

    def _get_values(self, release_name, namespace):
        # execute helm get values command
        ssh_command = f"helm get values {release_name} --all --output json"
        if namespace:
            ssh_command = f"{ssh_command} --namespace {namespace}"
        result = self._execute_command(ssh_command)
        # get values (json format) from result and convert to dict
        values = jsonutils.loads(result[0])
        return values

    def get_value(self, release_name, namespace, value):
        res = self._get_values(release_name, namespace)
        # get specified value (loop for nested value: e.g. "foo.bar")
        for val in value.split(VALUE_SPLIT_CHARACTER):
            if isinstance(res, dict):
                res = res.get(val)
            else:
                # if not of type dict, target value is not found
                res = None
            if res is None:
                self.close_session()
                LOG.error(f"{value} is not found in retrieved values.")
                raise vnfm.HelmClientMissingParamsError(value=value)
        return res

    def upgrade_values(self, release_name, chart_name, namespace, parameters):
        # execute helm upgrade command
        ssh_command = (f"helm upgrade {release_name} {chart_name}"
                       " --reuse-values")
        if namespace:
            ssh_command = f"{ssh_command} --namespace {namespace}"
        for param_key, param_val in parameters.items():
            ssh_command = f"{ssh_command} --set {param_key}={param_val}"
        self._execute_command(ssh_command, timeout=HELM_UPGRADE_TIMEOUT)

    def close_session(self):
        self.commander.close_session()
