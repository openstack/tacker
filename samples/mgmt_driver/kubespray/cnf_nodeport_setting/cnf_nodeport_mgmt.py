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
import yaml

from tacker.common import cmd_executer
from tacker.common import exceptions
from tacker.common import log
from tacker.vnflcm import utils as vnflcm_utils
from tacker.vnfm.mgmt_drivers import vnflcm_abstract_driver

COMMAND_WAIT_RETRY_TIME = 30
CONNECT_REMOTE_SERVER_RETRY_COUNT = 4
LOG = logging.getLogger(__name__)
K8S_CMD_TIMEOUT = 60
K8S_DEPLOY_TIMEOUT = 300
SERVER_WAIT_COMPLETE_TIME = 120


class CnfNodePortMgmt(vnflcm_abstract_driver.VnflcmMgmtAbstractDriver):
    def get_type(self):
        return 'mgmt-drivers-cnf-nodeport'

    def get_name(self):
        return 'mgmt-drivers-cnf-nodeport'

    def get_description(self):
        return 'Tacker CNFMgmt NodePort Setting Driver'

    @log.log
    def instantiate_start(self, context, vnf_instance,
                          instantiate_vnf_request, grant,
                          grant_request, **kwargs):
        pass

    def _check_is_cidr(self, key, value, cidr_str):
        # instantiate: check cidr
        try:
            ipaddress.ip_network(cidr_str)
        except ValueError:
            LOG.error('The {value} of {key} in the '
                      'additionalParams is invalid.'.format(
                          value=value, key=key))
            raise exceptions.MgmtDriverParamInvalid(param=value)

    def _check_input_parameters(self, additional_param, vnf_package_path):
        if not additional_param:
            LOG.error("The 'lcm-kubernetes-external-lb' cannot be None "
                      "in additionalParams.")
            raise exceptions.MgmtDriverOtherError(
                error_message="The 'lcm-kubernetes-external-lb' cannot"
                              " be None in additionalParams.")
        if not isinstance(additional_param, dict):
            LOG.error("The format of 'lcm-kubernetes-external-lb' in "
                      "additionalParams is invalid. It must be dict.")
            raise exceptions.MgmtDriverOtherError(
                error_message="The format of 'lcm-kubernetes-external-lb' in "
                              "additionalParams is invalid. It must be dict.")
        for key, value in additional_param.items():
            if key == 'external_lb_param':
                for attr in ['ssh_username', 'ssh_password', 'ssh_ip']:
                    if not value.get(attr):
                        LOG.error(
                            'The {} of {} in the '
                            'additionalParams cannot'
                            ' be None.'.format(attr, key))
                        raise exceptions.MgmtDriverNotFound(
                            param=attr)
                if value.get('ssh_ip'):
                    self._check_is_cidr(
                        key, 'ssh_ip', value.get('ssh_ip'))
        if not additional_param.get('script_path'):
            LOG.error('The script_path of {} in the '
                      'additionalParams cannot be None.'.format(key))
            raise exceptions.MgmtDriverNotFound(
                param='script_path')
        abs_script_path = os.path.join(
            vnf_package_path, additional_param.get('script_path'))
        if not os.path.exists(abs_script_path):
            LOG.error('The path of external_lb_param'
                      ' script is invalid.')
            raise exceptions.MgmtDriverOtherError(
                error_message="The path of external_lb_param"
                              " script is invalid")

    def _init_commander_and_set_script(self, user, password, host,
                                       timeout, vnf_package_path=None,
                                       script_path=None):
        retry = CONNECT_REMOTE_SERVER_RETRY_COUNT
        while retry > 0:
            try:
                if (vnf_package_path and script_path):
                    connect = paramiko.Transport(host, 22)
                    connect.connect(username=user, password=password)
                    sftp = paramiko.SFTPClient.from_transport(connect)
                    sftp.put(os.path.join(vnf_package_path, script_path),
                             "/tmp/{}".format(
                                 script_path.replace('Scripts', '')))
                    connect.close()
                commander = cmd_executer.RemoteCommandExecutor(
                    user=user, password=password, host=host,
                    timeout=timeout)
                return commander
            except (exceptions.NotAuthorized, paramiko.SSHException,
                    paramiko.ssh_exception.NoValidConnectionsError) as e:
                LOG.debug(e)
                retry -= 1
                if retry == 0:
                    LOG.error(e)
                    raise paramiko.SSHException()
                time.sleep(SERVER_WAIT_COMPLETE_TIME)

    def _execute_command(self, commander, ssh_command, timeout, type, retry):
        eventlet.monkey_patch()
        while retry >= 0:
            try:
                with eventlet.Timeout(timeout, True):
                    result = commander.execute_command(
                        ssh_command, input_data=None)
                    break
            except eventlet.timeout.Timeout:
                LOG.debug('It is time out, When execute command: '
                          '{}.'.format(ssh_command))
                retry -= 1
                if retry < 0:
                    LOG.error('It is time out, When execute command: '
                              '{}.'.format(ssh_command))
                    raise exceptions.MgmtDriverOtherError(
                        error_message='It is time out, When execute command: '
                                      '{}.'.format(ssh_command))
                time.sleep(COMMAND_WAIT_RETRY_TIME)
        if type == 'common':
            if result.get_return_code() != 0:
                err = result.get_stderr()
                LOG.error(err)
                raise exceptions.MgmtDriverRemoteCommandError(err_info=err)

        return result.get_stdout()

    def _get_nodeport_from_kubernetes(self, no_port_info_list, lb_commander,
                                      resource_info_list):
        for no_port_info in no_port_info_list:
            ssh_command = "kubectl describe svc '%(svc_name)s' -n" \
                          " '%(namespace)s' | grep NodePort: | awk" \
                          " '{print $3}' | awk -F '/' '{print $1}'" \
                          % {'svc_name': no_port_info.get('name'),
                             'namespace': no_port_info.get('namespace')}
            results = self._execute_command(
                lb_commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
            node_ports = ','.join([result.replace(
                '\n', '') for result in results])
            no_port_info['node_ports'] = node_ports
            resource_info_list.append(no_port_info)

    def _get_script_input_parameter(self, vnf_package_path, additional_param,
                                    operation_type):
        script_path = additional_param.get(
            'lcm-kubernetes-external-lb', {}).get('script_path')
        ssh_ip = additional_param.get(
            'lcm-kubernetes-external-lb', {}).get('external_lb_param').get(
            'ssh_ip')
        ssh_username = additional_param.get(
            'lcm-kubernetes-external-lb', {}).get('external_lb_param').get(
            'ssh_username')
        ssh_password = additional_param.get(
            'lcm-kubernetes-external-lb', {}).get('external_lb_param').get(
            'ssh_password')
        artifact_files = additional_param.get(
            'lcm-kubernetes-def-files', {})
        resource_info_list = []
        no_port_info_list = []
        for artifact_file in artifact_files:
            artiface_file_path = os.path.join(
                vnf_package_path, artifact_file)
            with open(artiface_file_path, 'r', encoding='utf-8') as f:
                yaml_content_all = yaml.safe_load_all(f.read())
            for yaml_content in yaml_content_all:
                if yaml_content.get('kind') == 'Service' and \
                        yaml_content.get('spec').get('type') == 'NodePort':
                    if operation_type == 'INSTANTIATE':
                        ports = yaml_content.get('spec').get('ports')
                        node_ports = [port.get(
                            'nodePort') for port in ports if port.get(
                            'nodePort')]
                        if len(node_ports) == len(ports):
                            node_ports_str = ','.join([str(
                                port) for port in node_ports])
                            resource_info = {
                                "namespace": yaml_content.get('metadata').get(
                                    'namespace', 'default'),
                                "name": yaml_content.get('metadata').get(
                                    'name'),
                                "node_ports": node_ports_str
                            }
                            resource_info_list.append(resource_info)
                        else:
                            no_port_info = {
                                "namespace": yaml_content.get('metadata').get(
                                    'namespace', 'default'),
                                "name": yaml_content.get('metadata').get(
                                    'name'),
                            }
                            no_port_info_list.append(no_port_info)
                    else:
                        resource_info = {
                            "namespace": yaml_content.get('metadata').get(
                                'namespace', 'default'),
                            "name": yaml_content.get('metadata').get('name')
                        }
                        resource_info_list.append(resource_info)

        lb_commander = self._init_commander_and_set_script(
            ssh_username, ssh_password, ssh_ip, K8S_CMD_TIMEOUT,
            vnf_package_path=vnf_package_path,
            script_path=script_path)
        if operation_type == 'INSTANTIATE':
            # get nodeport info from kubernetes
            self._get_nodeport_from_kubernetes(
                no_port_info_list, lb_commander, resource_info_list)
        resource_info_str_list = []
        for resource_info in resource_info_list:
            resource_info_str = ','.join(
                [value for key, value in resource_info.items()])
            resource_info_str_list.append(resource_info_str)
        all_resource_info_str = '#'.join(resource_info_str_list)
        return lb_commander, all_resource_info_str

    @log.log
    def instantiate_end(self, context, vnf_instance,
                        instantiate_vnf_request, grant,
                        grant_request, **kwargs):
        additional_param = instantiate_vnf_request.additional_params
        vnf_package_path = vnflcm_utils._get_vnf_package_path(
            context, vnf_instance.vnfd_id)
        self._check_input_parameters(additional_param.get(
            'lcm-kubernetes-external-lb', {}), vnf_package_path)
        lb_commander, all_resource_info_str = \
            self._get_script_input_parameter(
                vnf_package_path, additional_param, 'INSTANTIATE')
        ssh_command = 'bash /tmp/configure_lb.sh -i {} -a True'.format(
            all_resource_info_str)
        self._execute_command(
            lb_commander, ssh_command, K8S_DEPLOY_TIMEOUT, 'common', 0)
        lb_commander.close_session()

    @log.log
    def terminate_start(self, context, vnf_instance,
                        terminate_vnf_request, grant,
                        grant_request, **kwargs):
        pass

    @log.log
    def terminate_end(self, context, vnf_instance,
                      terminate_vnf_request, grant,
                      grant_request, **kwargs):
        vnf_package_path = vnflcm_utils._get_vnf_package_path(
            context, vnf_instance.vnfd_id)
        add_param = {}
        if hasattr(terminate_vnf_request, 'additional_params') and \
                terminate_vnf_request.additional_params:
            additional_params = terminate_vnf_request.additional_params
            lb_params_default = \
                vnf_instance.instantiated_vnf_info.additional_params.get(
                    'lcm-kubernetes-external-lb')
            add_param['lcm-kubernetes-external-lb'] = additional_params.get(
                'lcm-kubernetes-external-lb', lb_params_default)
            add_param['lcm-kubernetes-def-files'] = \
                vnf_instance.instantiated_vnf_info.additional_params.get(
                    'lcm-kubernetes-def-files')
        else:
            add_param = \
                vnf_instance.instantiated_vnf_info.additional_params

        lb_commander, all_resource_info_str = \
            self._get_script_input_parameter(
                vnf_package_path, add_param, 'TERMINATE')
        ssh_command = 'bash /tmp/configure_lb.sh -i {} -a False'.format(
            all_resource_info_str)
        self._execute_command(
            lb_commander, ssh_command, K8S_DEPLOY_TIMEOUT, 'common', 0)
        lb_commander.close_session()

    @log.log
    def scale_start(self, context, vnf_instance,
                    scale_vnf_request, grant,
                    grant_request, **kwargs):
        pass

    @log.log
    def scale_end(self, context, vnf_instance,
                  scale_vnf_request, grant,
                  grant_request, **kwargs):
        pass

    @log.log
    def heal_start(self, context, vnf_instance,
                   heal_vnf_request, grant,
                   grant_request, **kwargs):
        if not heal_vnf_request.vnfc_instance_id:
            self.terminate_end(
                context, vnf_instance, heal_vnf_request,
                grant, grant_request)
        else:
            pass

    @log.log
    def heal_end(self, context, vnf_instance,
                 heal_vnf_request, grant,
                 grant_request, **kwargs):
        if not heal_vnf_request.vnfc_instance_id:
            if hasattr(heal_vnf_request, 'additional_params') and \
                    heal_vnf_request.additional_params:
                lb_params_default = \
                    vnf_instance.instantiated_vnf_info.additional_params.get(
                        'lcm-kubernetes-external-lb')
                if not heal_vnf_request.additional_params.get(
                        'lcm-kubernetes-external-lb'):
                    heal_vnf_request.additional_params[
                        'lcm-kubernetes-external-lb'] = lb_params_default
                heal_vnf_request.additional_params[
                    'lcm-kubernetes-def-files'] = \
                    vnf_instance.instantiated_vnf_info.additional_params.get(
                        'lcm-kubernetes-def-files')
            else:
                heal_vnf_request.additional_params = \
                    vnf_instance.instantiated_vnf_info.additional_params
            self.instantiate_end(context, vnf_instance, heal_vnf_request,
                                 grant, grant_request)
        else:
            pass

    @log.log
    def change_external_connectivity_start(
            self, context, vnf_instance,
            change_ext_conn_request, grant,
            grant_request, **kwargs):
        pass

    @log.log
    def change_external_connectivity_end(
            self, context, vnf_instance,
            change_ext_conn_request, grant,
            grant_request, **kwargs):
        pass
