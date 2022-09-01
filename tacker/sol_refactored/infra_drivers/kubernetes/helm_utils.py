# Copyright (C) 2022 Nippon Telegraph and Telephone Corporation
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

import subprocess
import yaml

from oslo_log import log as logging

from tacker.sol_refactored.common import exceptions as sol_ex

LOG = logging.getLogger(__name__)

HELM_INSTALL_TIMEOUT = "120s"


class HelmClient():

    def __init__(self, helm_auth_params):
        self.helm_auth_params = helm_auth_params

    def _execute_command(self, helm_command, raise_ex=True):
        helm_command.extend(self.helm_auth_params)
        result = subprocess.run(helm_command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
        if raise_ex and result.returncode != 0:
            raise sol_ex.HelmOperationFailed(sol_detail=str(result))
        return result

    def _get_revision(self, result):
        for line in result.stdout.split('\n'):
            if 'REVISION' in line:
                revision = line.split()[-1]
                return revision

    def is_release_exist(self, release_name, namespace):
        # execute helm status command
        helm_command = ["helm", "status", release_name, "--namespace",
                        namespace]
        result = self._execute_command(helm_command, False)
        return result.returncode == 0

    def install(self, release_name, chart_name, namespace, parameters):
        # execute helm install command
        helm_command = ["helm", "install", release_name, chart_name,
                        "--namespace", namespace, "--create-namespace"]
        if parameters:
            set_params = ','.join([f"{key}={value}"
                                   for key, value in parameters.items()])
            helm_command.extend(["--set", set_params])
        helm_command.extend(["--timeout", HELM_INSTALL_TIMEOUT])
        result = self._execute_command(helm_command)

        return self._get_revision(result)

    def upgrade(self, release_name, chart_name, namespace, parameters):
        # execute helm install command
        helm_command = ["helm", "upgrade", release_name, chart_name,
                        "--namespace", namespace, "--reuse-values"]
        if parameters:
            set_params = ','.join([f"{key}={value}"
                                   for key, value in parameters.items()])
            helm_command.extend(["--set", set_params])
        helm_command.extend(["--timeout", HELM_INSTALL_TIMEOUT])
        result = self._execute_command(helm_command)

        return self._get_revision(result)

    def uninstall(self, release_name, namespace):
        # execute helm uninstall command
        helm_command = ["helm", "uninstall", release_name, "--namespace",
                        namespace, "--timeout", HELM_INSTALL_TIMEOUT]
        self._execute_command(helm_command)

    def get_manifest(self, release_name, namespace):
        # execute helm get manifest command
        helm_command = ["helm", "get", "manifest", release_name,
                        "--namespace", namespace]
        result = self._execute_command(helm_command)

        return list(yaml.safe_load_all(result.stdout))

    def rollback(self, release_name, revision_no, namespace):
        # execute helm get manifest command
        helm_command = ["helm", "rollback", release_name, revision_no,
                        "--namespace", namespace]
        self._execute_command(helm_command)
