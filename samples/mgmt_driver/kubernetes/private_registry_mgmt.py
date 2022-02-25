# Copyright (C) 2021 FUJITSU
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
import ipaddress
import os
import time

import eventlet
from oslo_log import log as logging
import paramiko

from tacker.common import cmd_executer
from tacker.common import exceptions
from tacker import objects
from tacker.vnflcm import utils as vnflcm_utils
from tacker.vnfm.infra_drivers.openstack import heat_client as hc
from tacker.vnfm.mgmt_drivers import vnflcm_abstract_driver

LOG = logging.getLogger(__name__)

# CLI timeout period
PR_CONNECT_TIMEOUT = 30
PR_CMD_TIMEOUT_DEFAULT = 600
PR_CMD_TIMEOUT_INSTALL = 2700

# retry interval(sec)
PR_CMD_RETRY_INTERVAL = 30

# number of check command retries for wait for Docker running
PR_NUM_OF_RETRY_WAIT_DOCKER = 5

# number of check command retries for wait for Private registry running
PR_NUM_OF_RETRY_WAIT_PR = 5

# Command type
CMD_TYPE_COMMON = "common"

# Default host port
DEFAULT_HOST_PORT = '5000'


class PrivateRegistryMgmtDriver(
        vnflcm_abstract_driver.VnflcmMgmtAbstractDriver):

    def get_type(self):
        return "mgmt-drivers-private-registry"

    def get_name(self):
        return "mgmt-drivers-private-registry"

    def get_description(self):
        return "Tacker Private registry VNF Mgmt Driver"

    def _get_cp_ip_address(self, vnf_instance, vim_connection_info, cp_name):
        heatclient = hc.HeatClient(vim_connection_info.access_info)
        stack_id = vnf_instance.instantiated_vnf_info.instance_id

        # get IP address from heat
        resource_info = heatclient.resources.get(
            stack_id=stack_id, resource_name=cp_name)
        cp_ip_address = resource_info.attributes.get('floating_ip_address')
        if cp_ip_address is None and resource_info.attributes.get('fixed_ips'):
            cp_ip_address = resource_info.attributes.get(
                'fixed_ips')[0].get("ip_address")

        # check result
        try:
            ipaddress.ip_address(cp_ip_address)
        except ValueError:
            err_msg = "The IP address of Private registry VM is invalid."
            LOG.error(err_msg)
            raise exceptions.MgmtDriverOtherError(error_message=err_msg)
        if cp_ip_address is None:
            err_msg = "Failed to get IP address for Private registry VM"
            LOG.error(err_msg)
            raise exceptions.MgmtDriverOtherError(error_message=err_msg)

        LOG.debug("Getting IP address succeeded. "
            "(CP name: {}, IP address: {})".format(cp_name, cp_ip_address))
        return cp_ip_address

    def _execute_command(self, commander, ssh_command,
                         timeout=PR_CMD_TIMEOUT_DEFAULT,
                         type=CMD_TYPE_COMMON, retry=0):
        eventlet.monkey_patch()
        while retry >= 0:
            try:
                with eventlet.Timeout(timeout, True):
                    LOG.debug("execute command: {}".format(ssh_command))
                    result = commander.execute_command(
                        ssh_command, input_data=None)
                    break
            except eventlet.timeout.Timeout:
                err_msg = ("It is time out, When execute command: "
                    "{}.".format(ssh_command))
                retry -= 1
                if retry < 0:
                    LOG.error(err_msg)
                    commander.close_session()
                    raise exceptions.MgmtDriverOtherError(
                        error_message=err_msg)
                err_msg += " Retry after {} seconds.".format(
                    PR_CMD_RETRY_INTERVAL)
                LOG.debug(err_msg)
                time.sleep(PR_CMD_RETRY_INTERVAL)
        if type == CMD_TYPE_COMMON:
            stderr = result.get_stderr()
            if stderr:
                err_msg = ("Failed to execute command: {}, "
                    "stderr: {}".format(ssh_command, stderr))
                LOG.error(err_msg)
                commander.close_session()
                raise exceptions.MgmtDriverOtherError(error_message=err_msg)
        return result.get_stdout()

    def _wait_docker_running(self, commander, err_msg,
                             retry=PR_NUM_OF_RETRY_WAIT_DOCKER):
        while retry >= 0:
            ssh_command = ("sudo systemctl status docker "
                "| grep Active | grep -c running")
            result = self._execute_command(commander, ssh_command)
            count_result = result[0].replace("\n", "")
            if count_result == "0":
                retry -= 1
                if retry < 0:
                    LOG.error(err_msg)
                    commander.close_session()
                    raise exceptions.MgmtDriverOtherError(
                        error_message=err_msg)
                LOG.debug("Docker service is not running. "
                    "Check again after {} seconds.".format(
                        PR_CMD_RETRY_INTERVAL))
                time.sleep(PR_CMD_RETRY_INTERVAL)
            else:
                LOG.debug("Docker service is running.")
                break

    def _wait_private_registry_running(self, commander,
                                       retry=PR_NUM_OF_RETRY_WAIT_PR):
        while retry >= 0:
            ssh_command = ("sudo docker inspect "
                "--format=\'{{.State.Status}}\' "
                "private_registry")
            result = self._execute_command(commander, ssh_command)
            status = result[0].replace("\n", "")
            if status == "running":
                LOG.debug("Private registry container is running.")
                break
            retry -= 1
            if retry < 0:
                err_msg = "Failed to run Private registry container"
                LOG.error(err_msg)
                commander.close_session()
                raise exceptions.MgmtDriverOtherError(
                    error_message=err_msg)
            LOG.debug("Private registry container is not running. "
                "Check again after {} seconds.".format(
                    PR_CMD_RETRY_INTERVAL))
            time.sleep(PR_CMD_RETRY_INTERVAL)

    def _check_pr_installation_params(self, pr_installation_params):
        if not pr_installation_params:
            LOG.error("The private_registry_installation_param "
                "in the additionalParams does not exist.")
            raise exceptions.MgmtDriverNotFound(
                param="private_registry_installation_param")
        ssh_cp_name = pr_installation_params.get("ssh_cp_name")
        ssh_username = pr_installation_params.get("ssh_username")
        ssh_password = pr_installation_params.get("ssh_password")
        if not ssh_cp_name:
            LOG.error("The ssh_cp_name "
                "in the additionalParams does not exist.")
            raise exceptions.MgmtDriverNotFound(param="ssh_cp_name")
        if not ssh_username:
            LOG.error("The ssh_username "
                "in the additionalParams does not exist.")
            raise exceptions.MgmtDriverNotFound(param="ssh_username")
        if not ssh_password:
            LOG.error("The ssh_password "
                "in the additionalParams does not exist.")
            raise exceptions.MgmtDriverNotFound(param="ssh_password")

    def _install_private_registry(self, context, vnf_instance,
                                  vim_connection_info,
                                  pr_installation_params):
        LOG.debug("Start private registry installation. "
            "installation param: {}".format(pr_installation_params))

        # check parameters
        self._check_pr_installation_params(pr_installation_params)

        ssh_cp_name = pr_installation_params.get("ssh_cp_name")
        ssh_username = pr_installation_params.get("ssh_username")
        ssh_password = pr_installation_params.get("ssh_password")
        image_path = pr_installation_params.get("image_path")
        port_no = pr_installation_params.get("port_no")
        proxy = pr_installation_params.get("proxy")

        # get IP address from cp name
        ssh_ip_address = self._get_cp_ip_address(
            vnf_instance, vim_connection_info, ssh_cp_name)

        # initialize RemoteCommandExecutor
        retry = 4
        while retry > 0:
            try:
                commander = cmd_executer.RemoteCommandExecutor(
                    user=ssh_username, password=ssh_password,
                    host=ssh_ip_address, timeout=PR_CONNECT_TIMEOUT)
                break
            except (exceptions.NotAuthorized, paramiko.SSHException,
                    paramiko.ssh_exception.NoValidConnectionsError) as e:
                LOG.debug(e)
                retry -= 1
                if retry < 0:
                    err_msg = "Failed to use SSH to connect to the registry " \
                              "server: {}".format(ssh_ip_address)
                    LOG.error(err_msg)
                    raise exceptions.MgmtDriverOtherError(
                        error_message=err_msg)
                time.sleep(PR_CMD_RETRY_INTERVAL)

        # check OS and architecture
        ssh_command = ("cat /etc/os-release "
            "| grep \"PRETTY_NAME=\" "
            "| grep -c \"Ubuntu 20.04\"; arch | grep -c x86_64")
        result = self._execute_command(commander, ssh_command)
        os_check_result = result[0].replace("\n", "")
        arch_check_result = result[1].replace("\n", "")
        if os_check_result == "0" or arch_check_result == "0":
            err_msg = ("Failed to install. "
                "Your OS does not support at present. "
                "It only supports Ubuntu 20.04 (x86_64)")
            LOG.error(err_msg)
            commander.close_session()
            raise exceptions.MgmtDriverOtherError(error_message=err_msg)

        # get proxy params
        http_proxy = ""
        https_proxy = ""
        no_proxy = ""
        if proxy:
            http_proxy = proxy.get("http_proxy")
            https_proxy = proxy.get("https_proxy")
            no_proxy = proxy.get("no_proxy")

        # execute apt-get install command
        ssh_command = ""
        if http_proxy or https_proxy:
            # set apt's proxy config
            ssh_command = "echo -e \""
            if http_proxy:
                ssh_command += ("Acquire::http::Proxy "
                    "\\\"{}\\\";\\n".format(http_proxy))
            if https_proxy:
                ssh_command += ("Acquire::https::Proxy "
                    "\\\"{}\\\";\\n".format(https_proxy))
            ssh_command += ("\" | sudo tee /etc/apt/apt.conf.d/proxy.conf "
                ">/dev/null && ")
        ssh_command += (
            "sudo apt-get update && "
            "export DEBIAN_FRONTEND=noninteractive;"
            "sudo -E apt-get install -y apt-transport-https "
            "ca-certificates curl gnupg-agent software-properties-common")
        self._execute_command(commander, ssh_command, PR_CMD_TIMEOUT_INSTALL)

        # execute add-apt-repository command
        ssh_command = ""
        if http_proxy:
            ssh_command += "export http_proxy=\"{}\";".format(http_proxy)
        if https_proxy:
            ssh_command += "export https_proxy=\"{}\";".format(https_proxy)
        if no_proxy:
            ssh_command += "export no_proxy=\"{}\";".format(no_proxy)
        ssh_command += (
            "export APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=DontWarn;"
            "curl -fsSL https://download.docker.com/linux/ubuntu/gpg "
            "| sudo -E apt-key add - && "
            "sudo add-apt-repository \"deb [arch=amd64] "
            "https://download.docker.com/linux/ubuntu "
            "$(lsb_release -cs) stable\"")
        self._execute_command(commander, ssh_command, PR_CMD_TIMEOUT_INSTALL)

        # install docker
        ssh_command = (
            "sudo apt-get update && "
            "export DEBIAN_FRONTEND=noninteractive;"
            "sudo -E apt-get install -y "
            "docker-ce=5:19.03.11~3-0~ubuntu-focal "
            "docker-ce-cli containerd.io")
        self._execute_command(commander, ssh_command, PR_CMD_TIMEOUT_INSTALL)

        # wait for the Docker service running
        err_msg = "Failed to install Docker(Docker service is not running)"
        self._wait_docker_running(commander, err_msg)

        # set Docker's proxy config
        if http_proxy or https_proxy or no_proxy:
            proxy_env_list = []
            if http_proxy:
                proxy_env = "\\\"HTTP_PROXY={}\\\"".format(http_proxy)
                proxy_env_list.append(proxy_env)
            if https_proxy:
                proxy_env = "\\\"HTTPS_PROXY={}\\\"".format(https_proxy)
                proxy_env_list.append(proxy_env)
            if no_proxy:
                proxy_env = "\\\"NO_PROXY={}\\\"".format(no_proxy)
                proxy_env_list.append(proxy_env)
            proxy_env = " ".join(proxy_env_list)
            ssh_command = (
                "sudo mkdir -p /etc/systemd/system/docker.service.d && "
                "echo -e \"[Service]\\nEnvironment={}\" | sudo tee "
                "/etc/systemd/system/docker.service.d/https-proxy.conf "
                ">/dev/null && "
                "sudo systemctl daemon-reload && "
                "sudo systemctl restart docker".format(proxy_env))
            self._execute_command(commander, ssh_command)

            # wait for the Docker service running
            err_msg = ("Failed to restart Docker"
                "(Docker service is not running)")
            self._wait_docker_running(commander, err_msg)

        # pull or load the Docker image named "registry"
        if not image_path:
            # pull the Docker image
            ssh_command = "sudo docker pull registry"
            self._execute_command(commander, ssh_command)
        else:
            vnf_package_path = vnflcm_utils._get_vnf_package_path(
                context, vnf_instance.vnfd_id)
            local_image_path = os.path.join(
                vnf_package_path, image_path)

            # check existence of local image file
            if not os.path.exists(local_image_path):
                LOG.error("The image_path in the additionalParams is invalid. "
                    "File does not exist.")
                commander.close_session()
                raise exceptions.MgmtDriverParamInvalid(param="image_path")

            # transfer the Docker image file to Private registry VM
            image_file_name = os.path.basename(image_path)
            remote_image_path = os.path.join("/tmp", image_file_name)
            transport = paramiko.Transport(ssh_ip_address, 22)
            transport.connect(username=ssh_username, password=ssh_password)
            sftp_client = paramiko.SFTPClient.from_transport(transport)
            sftp_client.put(local_image_path, remote_image_path)
            transport.close()

            # load the Docker image
            ssh_command = "sudo docker load -i {}".format(remote_image_path)
            self._execute_command(commander, ssh_command)

        # check Docker images list
        ssh_command = "sudo docker images | grep -c registry"
        result = self._execute_command(commander, ssh_command)
        count_result = result[0].replace("\n", "")
        if count_result == "0":
            err_msg = "Failed to pull or load the Docker image named registry"
            LOG.error(err_msg)
            commander.close_session()
            raise exceptions.MgmtDriverOtherError(error_message=err_msg)

        # run the Private registry container
        if port_no is None:
            port = DEFAULT_HOST_PORT
        else:
            port = str(port_no)
        ssh_command = (
            "sudo docker run -d -p {}:5000 "
            "-v /private_registry:/var/lib/registry "
            "--restart=always "
            "--name private_registry "
            "registry:latest".format(port))
        self._execute_command(commander, ssh_command)

        # wait for the Private registry container running
        self._wait_private_registry_running(commander)

        commander.close_session()
        LOG.debug("Private registry installation complete.")

    def instantiate_start(self, context, vnf_instance,
                          instantiate_vnf_request, grant,
                          grant_request, **kwargs):
        pass

    def instantiate_end(self, context, vnf_instance,
                        instantiate_vnf_request, grant,
                        grant_request, **kwargs):
        # get vim_connection_info
        vim_info = vnflcm_utils._get_vim(context,
            instantiate_vnf_request.vim_connection_info)
        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        # get parameters for private registry installation
        pr_installation_params = instantiate_vnf_request.additional_params.get(
            "private_registry_installation_param")

        self._install_private_registry(
            context, vnf_instance, vim_connection_info, pr_installation_params)

    def terminate_start(self, context, vnf_instance,
                        terminate_vnf_request, grant,
                        grant_request, **kwargs):
        pass

    def terminate_end(self, context, vnf_instance,
                      terminate_vnf_request, grant,
                      grant_request, **kwargs):
        pass

    def scale_start(self, context, vnf_instance,
                    scale_vnf_request, grant,
                    grant_request, **kwargs):
        pass

    def scale_end(self, context, vnf_instance,
                  scale_vnf_request, grant,
                  grant_request, **kwargs):
        pass

    def heal_start(self, context, vnf_instance,
                   heal_vnf_request, grant,
                   grant_request, **kwargs):
        pass

    def heal_end(self, context, vnf_instance,
                 heal_vnf_request, grant,
                 grant_request, **kwargs):
        # NOTE: Private registry VNF has only one VNFC.
        # Therefore, VNFC that is repaired by entire Heal and
        # VNFC that is repaired by specifying VNFC instance are the same VNFC.

        # get vim_connection_info
        vim_info = vnflcm_utils._get_vim(context,
            vnf_instance.vim_connection_info)
        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        # get parameters for private registry installation
        pr_installation_params = (
            vnf_instance.instantiated_vnf_info.additional_params.get(
                "private_registry_installation_param"))

        self._install_private_registry(
            context, vnf_instance, vim_connection_info, pr_installation_params)

    def change_external_connectivity_start(
            self, context, vnf_instance,
            change_ext_conn_request, grant,
            grant_request, **kwargs):
        pass

    def change_external_connectivity_end(
            self, context, vnf_instance,
            change_ext_conn_request, grant,
            grant_request, **kwargs):
        pass

    def modify_information_start(self, context, vnf_instance,
                                 modify_vnf_request, **kwargs):
        pass

    def modify_information_end(self, context, vnf_instance,
                               modify_vnf_request, **kwargs):
        pass
