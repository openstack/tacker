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
import json
import os
import time

import eventlet
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils
import paramiko
import yaml

from tacker.common import cmd_executer
from tacker.common import exceptions
from tacker.common import log
from tacker.db.db_base import CommonDbMixin
from tacker.db.nfvo import nfvo_db
from tacker.extensions import nfvo
from tacker.nfvo.nfvo_plugin import NfvoPlugin
from tacker import objects
from tacker.vnfm.infra_drivers.openstack import heat_client as hc
from tacker.vnfm.mgmt_drivers import vnflcm_abstract_driver
from tacker.vnfm import vim_client

CHECK_POD_STATUS_RETRY_COUNT = 20
COMMAND_WAIT_COMPLETE_TIME = 0.2
COMMAND_WAIT_RETRY_TIME = 30
CONF = cfg.CONF
CONNECT_REMOTE_SERVER_RETRY_COUNT = 4
DRAIN_TIMEOUT = 300
K8S_CMD_TIMEOUT = 30
K8S_DEPLOY_TIMEOUT = 300
K8S_INSTALL_TIMEOUT = 2700
LOG = logging.getLogger(__name__)
NEXT_CHECK_INTERVAL_TIME = 15
ROLE_MASTER = 'master'
ROLE_WORKER = 'worker'
SERVER_WAIT_COMPLETE_TIME = 240
TOKEN_CREATE_WAIT_TIME = 30
UNINSTALL_NODE_TIMEOUT = 900


class KubesprayMgmtDriver(vnflcm_abstract_driver.VnflcmMgmtAbstractDriver):
    def get_type(self):
        return 'mgmt-drivers-kubespray'

    def get_name(self):
        return 'mgmt-drivers-kubespray'

    def get_description(self):
        return 'Tacker Kubespray VNFMgmt Driver'

    @log.log
    def instantiate_start(self, context, vnf_instance,
                          instantiate_vnf_request, grant,
                          grant_request, **kwargs):
        pass

    def _get_vim(self, context, vim_connection_info):
        vim_client_obj = vim_client.VimClient()

        if vim_connection_info:
            vim_id = vim_connection_info[0].vim_id
            access_info = vim_connection_info[0].access_info
            if access_info:
                region_name = access_info.get('region')
            else:
                region_name = None
        else:
            vim_id = None
            region_name = None

        try:
            vim_res = vim_client_obj.get_vim(
                context, vim_id, region_name=region_name)
        except nfvo.VimNotFoundException:
            raise exceptions.VimConnectionNotFound(vim_id=vim_id)

        vim_res['vim_auth'].update({'region': region_name})
        vim_info = {'id': vim_res['vim_id'], 'vim_id': vim_res['vim_id'],
                    'vim_type': vim_res['vim_type'],
                    'access_info': vim_res['vim_auth']}

        return vim_info

    def _get_vim_connection_info(self, context, instantiate_vnf_req):

        vim_info = self._get_vim(
            context, instantiate_vnf_req.vim_connection_info)

        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        return vim_connection_info

    def _check_is_cidr(self, key, value, cidr_str):
        # instantiate: check cidr
        try:
            ipaddress.ip_network(cidr_str)
        except ValueError:
            LOG.error('The {value} of {key} in the '
                      'additionalParams is invalid.'.format(
                          value=value, key=key))
            raise exceptions.MgmtDriverParamInvalid(param=value)

    def _check_value_exist(self, attr_list, value, key):
        for attr in attr_list:
            if not value.get(attr):
                LOG.error(
                    'The {} of {} in the '
                    'additionalParams cannot'
                    ' be None.'.format(attr, key))
                raise exceptions.MgmtDriverNotFound(
                    param=attr)

    def _check_input_parameters(self, additional_param, vnf_package_path):
        if not additional_param:
            LOG.error('The kubernetes cluster info cannot be None'
                      'in additionalParams.')
            raise exceptions.MgmtDriverOtherError(
                error_message="The kubernetes cluster info"
                              " cannot be None in additionalParams.")
        if not isinstance(additional_param, dict):
            LOG.error('The format of kubernetes cluster info in '
                      'additionalParams is invalid. It must be dict.')
            raise exceptions.MgmtDriverOtherError(
                error_message="The format of kubernetes cluster info in "
                              "additionalParams is invalid. It must be dict.")
        for key, value in additional_param.items():
            attr_list = []
            if key not in ('proxy', 'external_lb_param', 'vim_name'):
                attr_list.extend(['username', 'password'])
            if key in ('master_node', 'worker_node', 'external_lb_param'):
                attr_list.extend(['ssh_cp_name'])
            if key == 'ansible':
                attr_list.extend(['ip_address', 'kubespray_root_path',
                                 'transferring_inventory_path'])
            if key == 'external_lb_param':
                attr_list.extend(['ssh_username', 'ssh_password',
                                  'script_path'])
                if value.get('script_path'):
                    abs_script_path = os.path.join(
                        vnf_package_path, value.get('script_path'))
                    if not os.path.exists(abs_script_path):
                        LOG.error('The path of external_lb_param'
                                  ' script is invalid.')
                        raise exceptions.MgmtDriverOtherError(
                            error_message="The path of external_lb_param"
                                          " script is invalid")
            if key in ('master_node', 'ansible'):
                for attr in ['pod_cidr', 'cluster_cidr', 'ip_address']:
                    if value.get(attr):
                        self._check_is_cidr(
                            key, attr, value.get(attr))
            if attr_list:
                self._check_value_exist(attr_list, value, key)

    def _get_ssh_ip_and_nic_ip(self, heatclient, stack_id, node):
        resource_info = heatclient.resources.get(
            stack_id=stack_id,
            resource_name=node.get('ssh_cp_name'))
        if resource_info.attributes.get('floating_ip_address'):
            ssh_ip = resource_info.attributes.get('floating_ip_address')
        else:
            ssh_ip = resource_info.attributes.get(
                'fixed_ips')[0].get('ip_address')
        if not ssh_ip:
            LOG.error("Failed to get the node's ssh ip.")
            raise exceptions.MgmtDriverOtherError(
                error_message="Failed to get"
                              " the node's ssh ip.")
        if not node.get('nic_cp_name'):
            nic_ip = ssh_ip
        else:
            nic_ip = heatclient.resources.get(
                stack_id=stack_id,
                resource_name=node.get('nic_cp_name')).attributes.get(
                'fixed_ips')[0].get('ip_address')
            if not nic_ip:
                LOG.error("Failed to get the node's nic ip.")
                raise exceptions.MgmtDriverOtherError(
                    error_message="Failed to get"
                                  " the node's nic ip.")
        return ssh_ip, nic_ip

    def _get_group_resources_list(
            self, heatclient, stack_id, node, additional_params):
        # get group resources list
        nest_resources_list = heatclient.resources.list(stack_id=stack_id)
        group_stack_name = node.get("aspect_id")
        group_stack_id = ""
        for nest_resources in nest_resources_list:
            if nest_resources.resource_name == group_stack_name:
                group_stack_id = nest_resources.physical_resource_id
        if not group_stack_id:
            LOG.error('No stack id {} matching the group was found.'.format(
                group_stack_id))
            raise exceptions.MgmtDriverOtherError(
                error_message='No stack id {} matching the'
                              ' group was found.'.format(group_stack_id))
        group_resources_list = heatclient.resources.list(
            stack_id=group_stack_id)
        return group_resources_list

    def _get_install_info_for_k8s_node(self, nest_stack_id, node,
                                       additional_params, heatclient):
        # instantiate: get k8s ssh ips
        vm_dict_list = []

        # get ssh_ip and nic_ip from heat, and set value into vm_dict
        if not node.get('aspect_id'):
            ssh_ip, nic_ip = self._get_ssh_ip_and_nic_ip(
                heatclient, nest_stack_id, node)
            vm_dict = {
                "ssh_ip": ssh_ip,
                "nic_ip": nic_ip
            }
            vm_dict_list.append(vm_dict)
        else:
            group_resources_list = self._get_group_resources_list(
                heatclient, nest_stack_id, node, additional_params)
            for group_resource in group_resources_list:
                stack_id = group_resource.physical_resource_id
                ssh_ip, nic_ip = self._get_ssh_ip_and_nic_ip(
                    heatclient, stack_id, node)
                vm_dict = {
                    "ssh_ip": ssh_ip,
                    "nic_ip": nic_ip
                }
                vm_dict_list.append(vm_dict)
        return vm_dict_list

    def _set_lb_info(self, nest_stack_id, external_lb_param, master_node,
                     heatclient):
        # get ssh_ip and cluster_ip from heat, and set value into vm_dict
        ssh_ip, _ = self._get_ssh_ip_and_nic_ip(
            heatclient, nest_stack_id, external_lb_param)
        external_lb_param['pod_cidr'] = master_node.get('pod_cidr', '')
        external_lb_param['cluster_cidr'] = master_node.get(
            'cluster_cidr', '')
        external_lb_param['ssh_ip'] = ssh_ip
        external_lb_param['cluster_ip'] = ssh_ip

    def _init_commander_and_set_script(self, user, password, host,
                                       timeout, vnf_package_path=None,
                                       script_path=None, token_flag=False):
        retry = CONNECT_REMOTE_SERVER_RETRY_COUNT
        while retry > 0:
            try:
                if (vnf_package_path and script_path) or token_flag:
                    connect = paramiko.Transport(host, 22)
                    connect.connect(username=user, password=password)
                    sftp = paramiko.SFTPClient.from_transport(connect)
                    if vnf_package_path and script_path:
                        sftp.put(os.path.join(vnf_package_path, script_path),
                                 "/tmp/{}".format(
                                     script_path.replace('Scripts', '')))
                    if token_flag:
                        fname = 'create_admin_token.yaml'
                        sftp.put(os.path.join(
                            os.path.dirname(os.path.abspath(__file__)),
                            ("../../../samples/"
                            "mgmt_driver/kubernetes/{}".format(fname))),
                            "/tmp/{}".format(fname))
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
                    raise exceptions.MgmtDriverOtherError(error_message=e)
                time.sleep(SERVER_WAIT_COMPLETE_TIME)

    def _send_or_receive_file(self, host, user, password,
                              remote_file, local_file, operation):
        connect = paramiko.Transport(host, 22)
        connect.connect(username=user, password=password)
        sftp = paramiko.SFTPClient.from_transport(connect)
        if operation == 'receive':
            sftp.get(remote_file, local_file)
        else:
            sftp.put(local_file, remote_file)
        connect.close()

    def _execute_command(self, commander, ssh_command, timeout, type, retry):
        eventlet.monkey_patch()
        while retry >= 0:
            try:
                with eventlet.Timeout(timeout, True):
                    result = commander.execute_command(
                        ssh_command)
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
            if result.get_return_code() != 0 and result.get_stderr():
                err = result.get_stderr()
                LOG.error(err)
                raise exceptions.MgmtDriverRemoteCommandError(err_info=err)
        elif type == 'ansible':
            if result.get_return_code() != 0 \
                    and 'No such file or directory' in result.get_stderr()[0]:
                return False
            else:
                error_message = 'The transferring_inventory_path has ' \
                                'exists in kubespray server. Please check' \
                                ' your path.'
                LOG.error(error_message)
                raise exceptions.MgmtDriverRemoteCommandError(
                    err_info=error_message)
        elif type == 'install':
            if result.get_return_code() != 0:
                for error in result.get_stdout():
                    if 'Timeout (12s) waiting for ' \
                        'privilege escalation prompt' in error and \
                            retry > 0:
                        self._execute_command(commander, ssh_command,
                                              timeout, 'install', 0)
                        break
                else:
                    err = result.get_stderr()
                    LOG.error(err)
                    raise exceptions.MgmtDriverRemoteCommandError(
                        err_info=err)

        return result.get_stdout()

    def _create_hosts_yaml(self, master_node, master_vm_dict_list,
                           worker_node, worker_vm_dict_list):
        hosts_yaml_content = {
            'all': {
                'hosts': {},
                'children': {
                    'kube_control_plane': {'hosts': {}},
                    'kube_node': {'hosts': {}},
                    'etcd': {'hosts': {}},
                    'k8s_cluster': {
                        'children': {'kube_control_plane': None,
                                     'kube_node': None}},
                    'calico_rr': {'hosts': {}}}}}

        for master_vm in master_vm_dict_list:
            key = 'master' + master_vm.get('nic_ip').split('.')[-1]
            hosts_yaml_content['all']['hosts'][key] = {
                'ansible_host': master_vm.get('ssh_ip'),
                'ip': master_vm.get('nic_ip'),
                'ansible_user': master_node.get('username'),
                'ansible_password': master_node.get('password'),
            }
            hosts_yaml_content['all']['children']['kube_control_plane'][
                'hosts'][key] = None
            hosts_yaml_content['all']['children']['etcd'][
                'hosts'][key] = None

        for worker_vm in worker_vm_dict_list:
            key = 'worker' + worker_vm.get('nic_ip').split('.')[-1]
            hosts_yaml_content['all']['hosts'][key] = {
                'ansible_host': worker_vm.get('ssh_ip'),
                'ip': worker_vm.get('nic_ip'),
                'ansible_user': worker_node.get('username'),
                'ansible_password': worker_node.get('password'),
            }
            hosts_yaml_content['all']['children']['kube_node'][
                'hosts'][key] = None

        return hosts_yaml_content

    def _install_k8s_cluster_and_set_config(
            self, master_node, worker_node, proxy, ansible,
            external_lb_param, master_vm_dict_list, worker_vm_dict_list):
        """Install Kubernetes Cluster Function

        It will use Kubespray which is installed in advance to install
        a Kubernetes Cluster.
        At present, Kuberspray's version is v2.16.0. You can get detailed
        information from the following url.
        https://github.com/kubernetes-sigs/kubespray/tree/v2.16.0
        """
        # get mtu value
        master_commander = self._init_commander_and_set_script(
            master_node.get('username'), master_node.get('password'),
            master_vm_dict_list[0].get('ssh_ip'), K8S_CMD_TIMEOUT)
        ssh_command = "ip a | grep '%(nic_ip)s' -B 2 | " \
                      "grep 'mtu' | awk '{print $5}'" % \
                      {'nic_ip': master_vm_dict_list[0].get('nic_ip')}
        mtu_value = self._execute_command(
            master_commander, ssh_command,
            K8S_CMD_TIMEOUT, 'common', 0)[0].replace('\n', '')
        calico_veth_mtu = int(mtu_value) - 20
        master_commander.close_session()

        # create inventory/hosts.yaml
        ansible_commander = self._init_commander_and_set_script(
            ansible.get('username'), ansible.get('password'),
            ansible.get('ip_address'), K8S_CMD_TIMEOUT)
        ssh_command = "ls -l {}".format(
            ansible.get('transferring_inventory_path'))
        file_exists_flag = self._execute_command(
            ansible_commander, ssh_command, K8S_CMD_TIMEOUT, 'ansible', 0)
        if not file_exists_flag:
            ssh_command = 'cp -r {kubespray_root_path}/inventory/sample' \
                          ' {transferring_inventory_path}'.format(
                              kubespray_root_path=ansible.get(
                                  'kubespray_root_path'),
                              transferring_inventory_path=ansible.get(
                                  'transferring_inventory_path'))
            self._execute_command(
                ansible_commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
        hosts_yaml_content = self._create_hosts_yaml(
            master_node, master_vm_dict_list,
            worker_node, worker_vm_dict_list)
        local_hosts_yaml_path = '/tmp/hosts.yaml'
        with open(local_hosts_yaml_path, 'w', encoding='utf-8') as nf:
            yaml.safe_dump(hosts_yaml_content, nf, default_flow_style=False)
        remote_hosts_yaml_path = ansible.get(
            'transferring_inventory_path') + '/hosts.yaml'
        self._send_or_receive_file(
            ansible.get('ip_address'), ansible.get('username'),
            ansible.get('password'), remote_hosts_yaml_path,
            local_hosts_yaml_path, 'send')

        # set calico mtu value
        calico_file_path = ansible.get(
            'transferring_inventory_path') + \
            '/group_vars/k8s_cluster/k8s-net-calico.yml'
        ssh_command = 'sed -i "s/\\# calico_mtu: 1500/calico_mtu: ' \
                      '{mtu_value}/g" {calico_file_path}'.format(
                          mtu_value=mtu_value,
                          calico_file_path=calico_file_path)
        self._execute_command(ansible_commander, ssh_command,
                              K8S_CMD_TIMEOUT, 'common', 0)
        ssh_command = 'sed -i "s/\\# calico_veth_mtu: 1440/calico_veth_mtu:' \
                      ' {calico_veth_mtu}/g" {calico_file_path}'.format(
                          calico_veth_mtu=calico_veth_mtu,
                          calico_file_path=calico_file_path)
        self._execute_command(ansible_commander, ssh_command,
                              K8S_CMD_TIMEOUT, 'common', 0)

        # set pod and service cidr information
        if external_lb_param.get('cluster_cidr') and \
                external_lb_param.get('pod_cidr'):
            k8s_cluster_file_path = ansible.get(
                'transferring_inventory_path') + \
                '/group_vars/k8s_cluster/k8s-cluster.yml'
            cluster_cidr = external_lb_param.get(
                'cluster_cidr').replace('/', '\\/')
            ssh_command = 'sed -i "s/kube_service_addresses:' \
                          ' 10.233.0.0\\/18/' \
                          'kube_service_addresses: {k8s_service_address}/g"' \
                          ' {k8s_cluster_file_path}'.format(
                              k8s_service_address=cluster_cidr,
                              k8s_cluster_file_path=k8s_cluster_file_path)
            self._execute_command(ansible_commander, ssh_command,
                                  K8S_CMD_TIMEOUT, 'common', 0)
            pod_cidr = external_lb_param.get('pod_cidr').replace('/', '\\/')
            ssh_command = 'sed -i "s/kube_pods_subnet: 10.233.64.0\\/18/' \
                          'kube_pods_subnet: {pod_cidr}/g"' \
                          ' {k8s_cluster_file_path}'.format(
                              pod_cidr=pod_cidr,
                              k8s_cluster_file_path=k8s_cluster_file_path)
            self._execute_command(ansible_commander, ssh_command,
                                  K8S_CMD_TIMEOUT, 'common', 0)

        # set proxy
        if proxy:
            proxy_file_path = ansible.get(
                'transferring_inventory_path') + \
                '/group_vars/all/all.yml'
            http_proxy = proxy.get('http_proxy').replace('/', '\\/')
            https_proxy = proxy.get('http_proxy').replace('/', '\\/')
            ssh_command = 'sed -i "s/\\# http_proxy: \\"\\"/' \
                          'http_proxy: {http_proxy}/g"' \
                          ' {proxy_file_path}'.format(
                              http_proxy=http_proxy,
                              proxy_file_path=proxy_file_path)
            self._execute_command(ansible_commander, ssh_command,
                                  K8S_CMD_TIMEOUT, 'common', 0)
            ssh_command = 'sed -i "s/\\# https_proxy: \\"\\"/' \
                          'https_proxy: {https_proxy}/g"' \
                          ' {proxy_file_path}'.format(
                              https_proxy=https_proxy,
                              proxy_file_path=proxy_file_path)
            self._execute_command(ansible_commander, ssh_command,
                                  K8S_CMD_TIMEOUT, 'common', 0)
        ansible_commander.close_session()

        # install k8s cluster
        install_timeout = K8S_INSTALL_TIMEOUT * (
            len(master_vm_dict_list) + len(worker_vm_dict_list))
        ansible_commander = self._init_commander_and_set_script(
            ansible.get('username'), ansible.get('password'),
            ansible.get('ip_address'), install_timeout)
        cluster_yaml_path = ansible.get(
            'kubespray_root_path') + '/cluster.yml'
        ssh_command = 'ansible-playbook -i {}/hosts.yaml --become' \
                      ' --become-user=root {}'.format(
                          ansible.get('transferring_inventory_path'),
                          cluster_yaml_path)
        self._execute_command(ansible_commander, ssh_command,
                              install_timeout, 'install', 1)
        ansible_commander.close_session()

        # get k8s bearer token
        master_commander = self._init_commander_and_set_script(
            master_node.get('username'), master_node.get('password'),
            master_vm_dict_list[0].get('ssh_ip'), K8S_CMD_TIMEOUT,
            token_flag=True)
        ssh_command = "sudo kubectl create -f /tmp/create_admin_token.yaml"
        self._execute_command(
            master_commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
        time.sleep(TOKEN_CREATE_WAIT_TIME)
        ssh_command = "sudo kubectl get secret -n kube-system " \
                      "| grep '^admin-token' " \
                      "| awk '{print $1}' " \
                      "| xargs -i sudo kubectl get secret {} -n kube-system" \
                      " -ojsonpath={.data.token} | base64 -d"
        bearer_token = self._execute_command(
            master_commander, ssh_command,
            K8S_CMD_TIMEOUT, 'common', 0)[0].replace('\n', '')
        master_commander.close_session()
        if os.path.exists(local_hosts_yaml_path):
            os.remove(local_hosts_yaml_path)

        return bearer_token

    def _install_and_set_lb(self, external_lb_param, vnf_package_path, proxy,
                            master_vm_dict_list, worker_vm_dict_list,
                            master_node):
        lb_commander = self._init_commander_and_set_script(
            external_lb_param.get('ssh_username'),
            external_lb_param.get('ssh_password'),
            external_lb_param.get('ssh_ip'), K8S_DEPLOY_TIMEOUT,
            vnf_package_path=vnf_package_path,
            script_path=external_lb_param.get('script_path'))
        master_ssh_ips_str = ','.join([vm_dict.get(
            'nic_ip') for vm_dict in master_vm_dict_list])
        worker_ssh_ips_str = ','.join([vm_dict.get(
            'nic_ip') for vm_dict in worker_vm_dict_list])
        if proxy.get('http_proxy') and proxy.get('https_proxy'):
            ssh_command = \
                "export http_proxy={http_proxy};" \
                "export https_proxy={https_proxy};" \
                "bash /tmp/{script_path} " \
                "-m {master_ip} -w {worker_ip} ".format(
                    http_proxy=proxy.get('http_proxy'),
                    https_proxy=proxy.get('https_proxy'),
                    master_ip=master_ssh_ips_str,
                    worker_ip=worker_ssh_ips_str,
                    script_path=external_lb_param.get(
                        'script_path').replace('Scripts/', ''))
        else:
            ssh_command = \
                "bash /tmp/{script_path} " \
                "-m {master_ip} -w {worker_ip} ".format(
                    master_ip=master_ssh_ips_str,
                    worker_ip=worker_ssh_ips_str,
                    script_path=external_lb_param.get(
                        'script_path').replace('Scripts/', ''))
        self._execute_command(
            lb_commander, ssh_command, K8S_DEPLOY_TIMEOUT, 'common', 0)
        lb_commander.close_session()

        # copy k8s admin configuration file
        master_commander = self._init_commander_and_set_script(
            master_node.get('username'), master_node.get('password'),
            master_vm_dict_list[0].get('ssh_ip'), K8S_CMD_TIMEOUT)
        ssh_command = 'sudo cp /etc/kubernetes/admin.conf /tmp/config;' \
                      'sudo chown $(id -u):$(id -g) /tmp/config'
        self._execute_command(master_commander, ssh_command,
                              K8S_CMD_TIMEOUT, 'common', 0)
        ssh_command = "sed -i 's/:6443/:8383/' /tmp/config"
        self._execute_command(master_commander, ssh_command,
                              K8S_CMD_TIMEOUT, 'common', 0)
        master_commander.close_session()
        remote_admin_file_path = local_admin_file_path = '/tmp/config'
        self._send_or_receive_file(
            master_vm_dict_list[0].get('ssh_ip'),
            master_node.get('username'), master_node.get('password'),
            remote_admin_file_path, local_admin_file_path, 'receive')

        # send config file to lb server
        lb_admin_file_path = '~/.kube/config'
        if os.path.exists(local_admin_file_path):
            self._send_or_receive_file(
                external_lb_param.get('ssh_ip'),
                external_lb_param.get('ssh_username'),
                external_lb_param.get('ssh_password'),
                remote_admin_file_path, local_admin_file_path, 'send')
        lb_commander = self._init_commander_and_set_script(
            external_lb_param.get('ssh_username'),
            external_lb_param.get('ssh_password'),
            external_lb_param.get('ssh_ip'), K8S_CMD_TIMEOUT)
        ssh_command = "mv {} {}".format(remote_admin_file_path,
                                        lb_admin_file_path)
        self._execute_command(lb_commander, ssh_command,
                              K8S_CMD_TIMEOUT, 'common', 0)
        lb_commander.close_session()

        if os.path.exists(local_admin_file_path):
            os.remove(local_admin_file_path)

    def _create_vim(self, context, vnf_instance, external_lb_param,
                    bearer_token, vim_name):
        server = 'https://' + external_lb_param.get('cluster_ip') + ':8383'
        vim_info = {
            'vim': {
                'name': vim_name,
                'auth_url': server,
                'vim_project': {
                    'name': 'default'
                },
                'auth_cred': {
                    'bearer_token': bearer_token
                },
                'type': 'kubernetes',
                'tenant_id': context.project_id
            }
        }
        try:
            nfvo_plugin = NfvoPlugin()
            created_vim_info = nfvo_plugin.create_vim(context, vim_info)
        except Exception as e:
            LOG.error("Failed to register kubernetes vim: {}".format(e))
            raise exceptions.MgmtDriverOtherError(
                error_message="Failed to register kubernetes vim: {}".format(
                    e))
        id = uuidutils.generate_uuid()
        vim_id = created_vim_info.get('id')
        vim_type = 'kubernetes'
        access_info = {
            'auth_url': server
        }
        vim_connection_info = objects.VimConnectionInfo(
            id=id, vim_id=vim_id, vim_type=vim_type,
            access_info=access_info, interface_info=None
        )
        vim_connection_infos = vnf_instance.vim_connection_info
        vim_connection_infos.append(vim_connection_info)
        vnf_instance.vim_connection_info = vim_connection_infos
        vnf_instance.save()

    def _get_vnf_package_path(self, context, vnfd_id):
        return os.path.join(CONF.vnf_package.vnf_package_csar_path,
                            self._get_vnf_package_id(context, vnfd_id))

    def _get_vnf_package_id(self, context, vnfd_id):
        vnf_package = objects.VnfPackageVnfd.get_by_id(context, vnfd_id)
        return vnf_package.package_uuid

    @log.log
    def instantiate_end(self, context, vnf_instance,
                        instantiate_vnf_request, grant,
                        grant_request, **kwargs):
        # get vim_connect_info
        if hasattr(instantiate_vnf_request, 'vim_connection_info'):
            vim_connection_info = self._get_vim_connection_info(
                context, instantiate_vnf_request)
        else:
            # In case of healing entire Kubernetes cluster, 'heal_end' method
            # will call this method using 'vnf_instance.instantiated_vnf_info'
            # as the 'instantiate_vnf_request', but there is no
            # 'vim_connection_info' in it, so we should get
            # 'vim_connection_info' from 'vnf_instance'.
            vim_connection_info = self._get_vim_connection_info(
                context, vnf_instance)
        additional_param = instantiate_vnf_request.additional_params.get(
            'k8s_cluster_installation_param', {})
        vim_name = additional_param.get('vim_name')
        master_node = additional_param.get('master_node', {})
        worker_node = additional_param.get('worker_node', {})
        proxy = additional_param.get('proxy', {})
        ansible = additional_param.get('ansible', {})
        external_lb_param = additional_param.get('external_lb_param', {})
        vnf_package_path = self._get_vnf_package_path(
            context, vnf_instance.vnfd_id)
        self._check_input_parameters(additional_param, vnf_package_path)
        nest_stack_id = vnf_instance.instantiated_vnf_info.instance_id
        if not vim_name:
            vim_name = 'kubernetes_vim_' + vnf_instance.id

        # get k8s node vm list
        access_info = vim_connection_info.access_info
        heatclient = hc.HeatClient(access_info)
        master_vm_dict_list = \
            self._get_install_info_for_k8s_node(
                nest_stack_id, master_node,
                instantiate_vnf_request.additional_params,
                heatclient)
        worker_vm_dict_list = \
            self._get_install_info_for_k8s_node(
                nest_stack_id, worker_node,
                instantiate_vnf_request.additional_params, heatclient)

        # set LB vm's info
        self._set_lb_info(nest_stack_id, external_lb_param, master_node,
                          heatclient)

        # install k8s_cluster and set config
        bearer_token = self._install_k8s_cluster_and_set_config(
            master_node, worker_node, proxy, ansible, external_lb_param,
            master_vm_dict_list, worker_vm_dict_list)

        # Install and set ExternalLB
        self._install_and_set_lb(external_lb_param, vnf_package_path, proxy,
                                 master_vm_dict_list, worker_vm_dict_list,
                                 master_node)

        # create vim
        self._create_vim(context, vnf_instance, external_lb_param,
                         bearer_token, vim_name)

    @log.log
    def terminate_start(self, context, vnf_instance,
                        terminate_vnf_request, grant,
                        grant_request, **kwargs):
        pass

    def _get_vim_by_name(self, context, k8s_vim_name):
        common_db_api = CommonDbMixin()
        result = common_db_api.get_by_name(
            context, nfvo_db.Vim, k8s_vim_name)

        if not result:
            LOG.debug("Cannot find kubernetes "
                      "vim with name: {}".format(k8s_vim_name))

        return result

    @log.log
    def terminate_end(self, context, vnf_instance,
                      terminate_vnf_request, grant,
                      grant_request, **kwargs):
        # delete kubernetes vim
        k8s_params = vnf_instance.instantiated_vnf_info.additional_params.get(
            'k8s_cluster_installation_param', {})
        k8s_vim_name = k8s_params.get('vim_name')
        if not k8s_vim_name:
            k8s_vim_name = 'kubernetes_vim_' + vnf_instance.id

        vim_info = self._get_vim_by_name(
            context, k8s_vim_name)
        if vim_info:
            nfvo_plugin = NfvoPlugin()
            nfvo_plugin.delete_vim(context, vim_info.id)
            for k8s_vim in vnf_instance.vim_connection_info:
                if k8s_vim.vim_id == vim_info.id:
                    vnf_instance.vim_connection_info.remove(k8s_vim)

        # delete cluster info on ansible server
        _, _, ansible, _ = \
            self._get_initial_parameters(
                context, vnf_instance, terminate_vnf_request)
        commander = self._init_commander_and_set_script(
            ansible.get('username'), ansible.get('password'),
            ansible.get('ip_address'), K8S_CMD_TIMEOUT)
        ssh_command = 'rm -rf {}'.format(
            k8s_params.get('ansible').get('transferring_inventory_path'))
        self._execute_command(
            commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
        ssh_command = 'rm -rf ~/.ssh/known_hosts'
        self._execute_command(
            commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
        commander.close_session()

    def _update_external_lb(self, external_lb_param, lb_ssh_ip, hostname):
        external_lb_commander = self._init_commander_and_set_script(
            external_lb_param.get('ssh_username'),
            external_lb_param.get('ssh_password'),
            lb_ssh_ip,
            K8S_CMD_TIMEOUT
        )
        ssh_command = 'grep -n "{}" /etc/haproxy/haproxy.cfg | ' \
                      'cut -d : -f 1'.format(hostname)
        result = self._execute_command(
            external_lb_commander, ssh_command,
            K8S_CMD_TIMEOUT, 'common', 0)
        if result:
            worker_host_num = result[0].replace('\n', '')
            if worker_host_num.isdigit():
                lb_server_num = int(worker_host_num, base=0)
                ssh_command = "sudo sed -i '{}d' " \
                              "/etc/haproxy/haproxy.cfg" \
                    .format(lb_server_num)
                self._execute_command(
                    external_lb_commander, ssh_command,
                    K8S_CMD_TIMEOUT, 'common', 0)
                self._restart_haproxy(external_lb_commander)
        external_lb_commander.close_session()

    def _delete_worker_node_and_update_inventory_file(
            self, ansible, worker_node, worker_hostname, operation_type):
        update_hosts_yaml_path = ansible.get(
            'transferring_inventory_path') + '/hosts.yaml'
        self._modify_ansible_user_or_password(update_hosts_yaml_path,
                                              worker_node, ansible)
        # remove worker node
        ssh_command = "ansible-playbook -i" \
                      " {}/hosts.yaml" \
                      " --become --become-user=root " \
                      "{}/remove-node.yml -e" \
                      " node={}".format(ansible.get(
                          'transferring_inventory_path'),
                          ansible.get('kubespray_root_path'),
                          worker_hostname)
        try:
            with eventlet.Timeout(K8S_INSTALL_TIMEOUT, True):
                result, code = self._uninstall_worker_node(
                    ssh_command, ansible)
                if code != 0:
                    msg = 'Fail to remove the worker node {}'.\
                        format(worker_hostname)
                    LOG.error(result)
                    raise exceptions.MgmtDriverOtherError(
                        error_message=msg)
                LOG.debug(result)
        except eventlet.timeout.Timeout:
            msg = 'It is time out while deleting' \
                  ' the worker node {}'.format(worker_hostname)
            LOG.error(msg)
            raise exceptions.MgmtDriverOtherError(
                error_message=msg)

        # Gets the line of rows where worker_hostname resides
        if operation_type == 'SCALE':
            while True:
                commander_k8s = self._init_commander_and_set_script(
                    ansible.get('username'), ansible.get('password'),
                    ansible.get('ip_address'), K8S_CMD_TIMEOUT)
                ssh_command = 'grep -n "{}" {} | head -1 ' \
                              '| cut -d : -f 1'\
                    .format(worker_hostname, update_hosts_yaml_path)
                host_name = self._execute_command(
                    commander_k8s, ssh_command,
                    K8S_CMD_TIMEOUT, 'common', 0)
                if host_name:
                    host_name_line = host_name[0].replace('\n', '')
                    if host_name_line.isdigit():
                        host_name_line = int(host_name_line, base=0)
                        ssh_command = 'sed -n {}P {}' \
                            .format(host_name_line + 1,
                                    update_hosts_yaml_path)
                        is_hosts_or_children = self._execute_command(
                            commander_k8s, ssh_command,
                            K8S_CMD_TIMEOUT, 'common', 0)[0]
                        if "ansible_host" in is_hosts_or_children:
                            ssh_command = "sed -i '{}, {}d' {}" \
                                .format(host_name_line,
                                        host_name_line + 4,
                                        update_hosts_yaml_path)
                        else:
                            ssh_command = "sed -i " \
                                          "'{}d' {}"\
                                .format(host_name_line,
                                        update_hosts_yaml_path)
                        self._execute_command(
                            commander_k8s, ssh_command,
                            K8S_CMD_TIMEOUT, 'common', 0)
                else:
                    break
            commander_k8s.close_session()
        if os.path.exists(update_hosts_yaml_path):
            os.remove(update_hosts_yaml_path)

    def _uninstall_worker_node(self, ssh_command, ansible):
        end_str = ('# ', '$ ', '? ', '% ')
        end_flag = False
        result_end_flag = False
        command_return_code = 0
        try:
            trans = paramiko.Transport((ansible.get('ip_address'), 22))
            trans.start_client()
            trans.auth_password(username=ansible.get('username'),
                                password=ansible.get('password'))
            channel = trans.open_session()
            channel.settimeout(UNINSTALL_NODE_TIMEOUT)
            channel.get_pty()
            buff = ''
            channel.invoke_shell()
            channel.send(ssh_command + '\n')
            while True:
                time.sleep(COMMAND_WAIT_COMPLETE_TIME)
                resp = channel.recv(1024)
                resp = resp.decode('utf-8')
                buff += resp
                if "Type 'yes' to delete nodes" in resp:
                    channel.send('yes\n')
                    time.sleep(COMMAND_WAIT_COMPLETE_TIME)
                    resp = channel.recv(1024)
                    resp = resp.decode('utf-8')
                    buff += resp
                for end_s in end_str:
                    if resp.endswith(end_s):
                        end_flag = True
                        break
                if end_flag:
                    break
                if 'PLAY RECAP' in resp:
                    result_end_flag = True
                if result_end_flag and 'failed=0' not in resp:
                    command_return_code = 2
            channel.close()
            trans.close()
            return buff, command_return_code
        except (exceptions.NotAuthorized, paramiko.SSHException,
                paramiko.ssh_exception.NoValidConnectionsError) as e:
            LOG.debug(e)
            raise exceptions.MgmtDriverOtherError(error_message=e)

    def _get_initial_parameters(self, context, vnf_instance, action_request):
        vim_connection_info = \
            self._get_vim_connection_info(context, vnf_instance)
        k8s_cluster_installation_param = \
            vnf_instance.instantiated_vnf_info.additional_params.get(
                'k8s_cluster_installation_param')
        worker_node_default = \
            k8s_cluster_installation_param.get('worker_node')
        external_lb_param_default = \
            k8s_cluster_installation_param.get('external_lb_param')
        ansible_default = \
            k8s_cluster_installation_param.get('ansible')

        # If additional_params exist in action_request
        if hasattr(action_request, 'additional_params') and \
                action_request.additional_params:
            # Get the VM's information from action_request
            add_param = action_request. \
                additional_params.get('k8s_cluster_installation_param')
            if add_param:
                worker_node = add_param.get('worker_node', worker_node_default)
                external_lb_param = add_param.get('external_lb_param',
                                                  external_lb_param_default)
                ansible = add_param.get('ansible', ansible_default)
            else:
                worker_node = worker_node_default
                external_lb_param = external_lb_param_default
                ansible = ansible_default
        else:
            worker_node = worker_node_default
            external_lb_param = external_lb_param_default
            ansible = ansible_default

        return worker_node, external_lb_param, ansible, vim_connection_info

    def _remove_node_and_update_config_file(
            self, worker_hostnames, external_lb_param,
            lb_ssh_ip, ansible, worker_node, operation_type):
        # Migrate the pod of the worker node
        for worker_hostname in worker_hostnames:
            #  init lb RemoteCommandExecutor
            external_lb_commander = self._init_commander_and_set_script(
                external_lb_param.get('ssh_username'),
                external_lb_param.get('ssh_password'),
                lb_ssh_ip,
                K8S_CMD_TIMEOUT
            )

            # check worker_node exist in k8s-cluster
            ssh_command = "kubectl get node --no-headers {}" \
                          " 2> /dev/null".format(worker_hostname)
            result = self._execute_command(external_lb_commander,
                                           ssh_command,
                                           K8S_CMD_TIMEOUT,
                                           'common',
                                           0)
            if result:
                ssh_command = \
                    "kubectl get pods --field-selector=spec." \
                    "nodeName={} -o json".format(worker_hostname)
                result = self._execute_command(external_lb_commander,
                                               ssh_command,
                                               K8S_CMD_TIMEOUT,
                                               'common',
                                               0)

                # Get the names of all pods on the worker node
                daemonset_content_str = ''.join(result)
                daemonset_content = json.loads(
                    daemonset_content_str)
                ssh_command = "kubectl drain {}" \
                              " --ignore-daemonsets" \
                              " --delete-emptydir-data" \
                              " --timeout={}s".format(worker_hostname,
                                                      DRAIN_TIMEOUT)
                self._execute_command(external_lb_commander,
                                      ssh_command,
                                      K8S_DEPLOY_TIMEOUT,
                                      'common', 0)
                self.evacuate_wait(external_lb_commander,
                                   daemonset_content)
                external_lb_commander.close_session()

                # Uninstall worker node and update inventory file
                self._delete_worker_node_and_update_inventory_file(
                    ansible, worker_node, worker_hostname, operation_type)

            # Update ExternalLB's haproxy
            self._update_external_lb(external_lb_param, lb_ssh_ip,
                                     worker_hostname)
        ansible_commander = self._init_commander_and_set_script(
            ansible.get('username'), ansible.get('password'),
            ansible.get('ip_address'), K8S_CMD_TIMEOUT)
        ssh_command = 'rm -rf ~/.ssh/known_hosts'
        self._execute_command(
            ansible_commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
        ansible_commander.close_session()

    @log.log
    def scale_start(self, context, vnf_instance,
                    scale_vnf_request, grant,
                    grant_request, **kwargs):
        # If the type of scale is SCALE_IN
        if scale_vnf_request.type == 'SCALE_IN':
            scale_name_list = kwargs.get('scale_name_list')
            nest_stack_id = vnf_instance.instantiated_vnf_info.instance_id
            resource_name = scale_vnf_request.aspect_id

            worker_node, external_lb_param, ansible, vim_connection_info = \
                self._get_initial_parameters(
                    context, vnf_instance, scale_vnf_request)

            # Get the ssh ip of LB
            heatclient = hc.HeatClient(vim_connection_info.access_info)
            resource_info = heatclient.resources. \
                get(stack_id=nest_stack_id,
                    resource_name=external_lb_param.get('ssh_cp_name'))
            # If the VM's floating ip is not None
            # Get floating ip from resource_info and assign it to ssh ip
            lb_ssh_ip = self._get_lb_or_worker_ssh_ip(resource_info, True)

            # Get the ip of scale in worker nodes
            worker_group_resource = heatclient.resources. \
                get(stack_id=nest_stack_id,
                    resource_name=resource_name)
            # if worker_group_resource is None
            if not worker_group_resource:
                LOG.error("The specified resource was not found.")
                raise exceptions.MgmtDriverOtherError(
                    error_message='The specified resource was not found.')
            worker_resource_list = \
                heatclient.resources.list(
                    stack_id=worker_group_resource.physical_resource_id)

            worker_ip_dict_list = []
            for worker_resource in worker_resource_list:
                # If worker_resource.resource_name exists in scale_name_list
                if worker_resource.resource_name in scale_name_list:
                    stack_id = worker_resource.physical_resource_id
                    # Get the ssh_ip, nic ip of worker node
                    worker_ssh_ip, worker_nic_ip = self._get_ssh_ip_and_nic_ip(
                        heatclient, stack_id, worker_node)

                    # Create worker_ip_dict_list data
                    ip_dict = {"ssh_ip": worker_ssh_ip,
                               "nic_ip": worker_nic_ip}
                    worker_ip_dict_list.append(ip_dict)

            # Get the hostname of the scale in worker node.
            worker_hostnames = []
            for worker_ip_dict in worker_ip_dict_list:
                # get worker host names
                worker_hostname = \
                    'worker' + worker_ip_dict.get("nic_ip").split('.')[-1]
                worker_hostnames.append(worker_hostname)

            self._remove_node_and_update_config_file(
                worker_hostnames, external_lb_param,
                lb_ssh_ip, ansible, worker_node, 'SCALE')
        else:
            pass

    def evacuate_wait(self, commander, daemonset_content):
        wait_flag = True
        retry_count = CHECK_POD_STATUS_RETRY_COUNT
        while wait_flag and retry_count > 0:
            if daemonset_content.get('items'):
                ssh_command = "kubectl get pods --all-namespaces -o json"
                result = self._execute_command(
                    commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 3)
                pods_list = json.loads(''.join(result)).get('items')
                pods_names = [pod.get('metadata', {}).get('name')
                              for pod in pods_list]
                for daemonset in daemonset_content.get('items'):
                    daemonset_name = daemonset.get('metadata', {}).get('name')
                    if daemonset_name in pods_names and \
                            'calico-node' not in daemonset_name and \
                            'kube-proxy' not in daemonset_name:
                        break
                else:
                    wait_flag = False
            else:
                break
            if not wait_flag:
                break
            time.sleep(NEXT_CHECK_INTERVAL_TIME)
            retry_count -= 1

    def _get_lb_or_worker_ssh_ip(self, resource_info, is_lb):
        if resource_info.attributes.get('floating_ip_address'):
            ssh_ip = resource_info.attributes.get('floating_ip_address')
        else:
            ssh_ip = resource_info.attributes. \
                get('fixed_ips')[0].get('ip_address')

        if ssh_ip is None:
            if is_lb:
                LOG.error("Failed to get the LB's ssh ip.")
                raise exceptions.MgmtDriverOtherError(
                    error_message="Failed to get the LB's ssh ip.")
            LOG.error("Failed to get the Worker's ssh ip.")
            raise exceptions.MgmtDriverOtherError(
                error_message="Failed to get the Worker's ssh ip.")
        return ssh_ip

    def _restart_haproxy(self, external_lb_commander):
        # restart haproxy
        ssh_command = 'sudo systemctl restart haproxy'
        self._execute_command(
            external_lb_commander, ssh_command,
            K8S_CMD_TIMEOUT, 'common', 0)
        ssh_command = 'sudo systemctl status haproxy | ' \
                      'grep Active'
        self._execute_command(
            external_lb_commander, ssh_command,
            K8S_CMD_TIMEOUT, 'common', 0)

    def _update_lb_config_file(self, external_lb_param, lb_ssh_ip,
                               worker_ip_dict_list):
        external_lb_commander = self._init_commander_and_set_script(
            external_lb_param.get('ssh_username'),
            external_lb_param.get('ssh_password'),
            lb_ssh_ip,
            K8S_CMD_TIMEOUT
        )
        add_row_data = ''
        for worker_ip_dict in worker_ip_dict_list:
            worker_host_name = 'worker' + \
                               worker_ip_dict.get('nic_ip').split('.')[-1]
            nic_ip = worker_ip_dict.get('nic_ip')
            row_data = '    server  {} {} check'.format(
                worker_host_name, nic_ip)
            add_row_data += row_data + '\\n'

        ssh_command = 'grep -n "backend kubernetes-nodeport" ' \
                      '/etc/haproxy/haproxy.cfg | head -1 | cut -d : -f 1'
        result = self._execute_command(external_lb_commander,
                                       ssh_command,
                                       K8S_INSTALL_TIMEOUT,
                                       'common', 0)[0].replace('\n', '')
        write_start_row = int(result) + 2
        ssh_command = 'sudo sed -i "{}a\\{}" ' \
                      '/etc/haproxy/haproxy.cfg'.format(
                          write_start_row, add_row_data)
        LOG.debug("ssh_command: {}".format(ssh_command))
        self._execute_command(
            external_lb_commander, ssh_command,
            K8S_INSTALL_TIMEOUT, 'common', 0)

        self._restart_haproxy(external_lb_commander)
        external_lb_commander.close_session()

    def _install_node_and_update_config_file(
            self, worker_node, worker_ip_dict_list,
            ansible, external_lb_param, lb_ssh_ip):
        # check worker_VM can be accessed via ssh
        self._init_commander_and_set_script(
            worker_node.get('username'), worker_node.get('password'),
            worker_ip_dict_list[0].get('ssh_ip'), K8S_CMD_TIMEOUT)

        # Install worker node
        commander_k8s = self._init_commander_and_set_script(
            ansible.get('username'), ansible.get('password'),
            ansible.get('ip_address'),
            K8S_INSTALL_TIMEOUT * len(worker_ip_dict_list))
        facts_yaml_path = ansible.get(
            'kubespray_root_path') + '/facts.yml'
        ssh_command = "ansible-playbook -i" \
                      " {}/hosts.yaml" \
                      " --become --become-user=root {}" \
            .format(ansible.get('transferring_inventory_path'),
                    facts_yaml_path)
        self._execute_command(
            commander_k8s, ssh_command,
            K8S_DEPLOY_TIMEOUT, 'common', 0)

        scale_yaml_path = ansible.get(
            'kubespray_root_path') + '/scale.yml'
        ssh_command = "ansible-playbook -i" \
                      " {}/hosts.yaml" \
                      " --become --become-user=root {}".format(
                          ansible.get('transferring_inventory_path'),
                          scale_yaml_path)
        self._execute_command(
            commander_k8s, ssh_command,
            K8S_INSTALL_TIMEOUT * len(worker_ip_dict_list),
            'install', 0)
        commander_k8s.close_session()

        # Update ExternalLB's haproxy.cfg
        self._update_lb_config_file(
            external_lb_param, lb_ssh_ip, worker_ip_dict_list)

    @log.log
    def scale_end(self, context, vnf_instance,
                  scale_vnf_request, grant,
                  grant_request, **kwargs):
        if scale_vnf_request.type == 'SCALE_OUT':
            scale_out_id_list = kwargs.get('scale_out_id_list')
            nest_stack_id = vnf_instance.instantiated_vnf_info.instance_id
            worker_node, external_lb_param, ansible, vim_connection_info =\
                self._get_initial_parameters(
                    context, vnf_instance, scale_vnf_request)

            heatclient = hc.HeatClient(vim_connection_info.access_info)

            # Get the ssh ip of LB
            resource_info = heatclient.resources. \
                get(stack_id=nest_stack_id,
                    resource_name=external_lb_param.get('ssh_cp_name'))
            lb_ssh_ip = self._get_lb_or_worker_ssh_ip(resource_info, True)

            # get scale-out worker's info
            worker_ip_dict_list = []
            for scale_out_id in scale_out_id_list:
                stack_id = scale_out_id
                # Get the ssh_ip, nic ip of worker node
                worker_ssh_ip, worker_nic_ip = self._get_ssh_ip_and_nic_ip(
                    heatclient, stack_id, worker_node)

                # Create worker_ip_dict_list data
                ip_dict = {"ssh_ip": worker_ssh_ip, "nic_ip": worker_nic_ip}
                worker_ip_dict_list.append(ip_dict)

            # read hosts.yaml file contents
            update_hosts_yaml_path = ansible.get(
                'transferring_inventory_path') + '/hosts.yaml'
            local_hosts_yaml_path = '/tmp/hosts.yaml'
            # update hosts.yaml
            hosts_content = self._modify_ansible_user_or_password(
                update_hosts_yaml_path, worker_node, ansible)

            for worker_ip_dict in worker_ip_dict_list:
                # Update inventory file
                # update hosts.yaml file contents
                worker_host_name = 'worker' + \
                                   worker_ip_dict.get('nic_ip').split('.')[-1]
                hosts_content['all']['hosts'][worker_host_name] = {
                    'ansible_host': worker_ip_dict.get('ssh_ip'),
                    'ip': worker_ip_dict.get('nic_ip'),
                    'ansible_user': worker_node.get('username'),
                    'ansible_password': worker_node.get('password')
                }
                hosts_content['all']['children']['kube_node'][
                    'hosts'][worker_host_name] = None
            LOG.debug("get hosts_content: {}".format(hosts_content))
            with open(local_hosts_yaml_path, 'w', encoding='utf-8') as nf:
                yaml.safe_dump(hosts_content, nf,
                               default_flow_style=False)
            self._send_or_receive_file(
                ansible.get('ip_address'), ansible.get('username'),
                ansible.get('password'), update_hosts_yaml_path,
                local_hosts_yaml_path, 'send')

            # Install worker node adn update configuration file
            self._install_node_and_update_config_file(
                worker_node, worker_ip_dict_list, ansible,
                external_lb_param, lb_ssh_ip)
        else:
            pass

    def _modify_ansible_user_or_password(self, host_path,
                                         worker_node, ansible):
        try:
            # read hosts.yml
            local_hosts_yaml_path = '/tmp/hosts.yaml'
            self._send_or_receive_file(
                ansible.get('ip_address'), ansible.get('username'),
                ansible.get('password'), host_path,
                local_hosts_yaml_path, 'receive')
            with open(local_hosts_yaml_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
                hosts_content = yaml.safe_load(file_content)
            worker_nodes = hosts_content['all']['children']['kube_node'][
                'hosts']
            LOG.debug("worker_nodes: {}".format(worker_nodes))
            if worker_nodes:
                kube_node_hosts_keys = list(worker_nodes.keys())
                LOG.debug("kube_node_keys: {}".format(kube_node_hosts_keys))
                hosts_key = list(hosts_content['all']['hosts'].keys())
                LOG.debug("hosts_key: {}".format(hosts_key))
                need_modify = False
                for kube_node_hosts in kube_node_hosts_keys:
                    if kube_node_hosts in hosts_key:
                        content = \
                            hosts_content['all']['hosts'][kube_node_hosts]
                        LOG.debug("get node content: {}".format(content))
                        ansible_user = content.get("ansible_user")
                        ansible_password = content.get("ansible_password")
                        if ansible_user != worker_node.get('username'):
                            hosts_content['all']['hosts'][kube_node_hosts][
                                'ansible_user'] = worker_node.get('username')
                            need_modify = True
                        if ansible_password != worker_node.get('password'):
                            hosts_content['all']['hosts'][kube_node_hosts][
                                'ansible_password'] = \
                                worker_node.get('password')
                            need_modify = True
                if need_modify:
                    with open(local_hosts_yaml_path, 'w', encoding='utf-8') \
                            as nf:
                        yaml.safe_dump(hosts_content, nf,
                                       default_flow_style=False)
                    self._send_or_receive_file(
                        ansible.get('ip_address'), ansible.get('username'),
                        ansible.get('password'), host_path,
                        local_hosts_yaml_path, 'send')
                return hosts_content
            os.remove(local_hosts_yaml_path)
        except Exception:
            LOG.error('modify ansible_user or ansible_password has error: {}.'
                      .format(ValueError))
            raise exceptions.MgmtDriverOtherError(
                error_message='modify user or password has error: {}.'.format(
                    Exception))

    def _get_vnfc_resource_id(self, vnfc_resource_list, vnfc_instance_id):
        for vnfc_resource in vnfc_resource_list:
            if vnfc_resource.id == vnfc_instance_id:
                return vnfc_resource
        return None

    def _get_heal_physical_resource_ids(self, vnf_instance,
                                        heal_vnf_request):
        heal_physical_resource_ids = []
        for vnfc_instance_id in heal_vnf_request.vnfc_instance_id:
            instantiated_vnf_info = vnf_instance.instantiated_vnf_info
            vnfc_resource_info = instantiated_vnf_info.vnfc_resource_info
            vnfc_resource = self._get_vnfc_resource_id(
                vnfc_resource_info, vnfc_instance_id)
            if vnfc_resource:
                heal_physical_resource_ids.append(
                    vnfc_resource.compute_resource.resource_id)

        return heal_physical_resource_ids

    def _get_heal_worker_node_info(
            self, vnf_additional_params, worker_node, heatclient,
            nest_stack_id, heal_physical_resource_ids):
        worker_ip_dict_list = []
        if worker_node.get('aspect_id'):
            worker_group_resource_name = worker_node.get('aspect_id')

            worker_group_resource = heatclient.resources.get(
                stack_id=nest_stack_id,
                resource_name=worker_group_resource_name)
            if not worker_group_resource:
                raise exceptions.MgmtDriverOtherError(
                    error_message='The specified resource'
                                  ' {} was not found.'.format(
                                      worker_group_resource_name))
            worker_group_resource_list = heatclient.resources.list(
                stack_id=worker_group_resource.physical_resource_id)
            for worker_resource in worker_group_resource_list:
                lowest_resource_list = heatclient.resources.list(
                    stack_id=worker_resource.physical_resource_id)
                for lowest_resource in lowest_resource_list:
                    if lowest_resource.resource_type == 'OS::Nova::Server' \
                        and lowest_resource.physical_resource_id in \
                            heal_physical_resource_ids:
                        worker_ssh_ip, worker_nic_ip = \
                            self._get_ssh_ip_and_nic_ip(
                                heatclient,
                                worker_resource.physical_resource_id,
                                worker_node)
                        ip_dict = {"nic_ip": worker_nic_ip,
                                   "ssh_ip": worker_ssh_ip}
                        worker_ip_dict_list.append(ip_dict)
        else:
            # in case of SOL001 TOSCA-based VNFD with single worker node
            resource_list = heatclient.resources.list(
                stack_id=nest_stack_id)
            for resource in resource_list:
                if resource.resource_type == 'OS::Nova::Server' \
                    and resource.physical_resource_id in \
                        heal_physical_resource_ids:
                    worker_ssh_ip, worker_nic_ip = \
                        self._get_ssh_ip_and_nic_ip(
                            heatclient, nest_stack_id, worker_node)
                    ip_dict = {"nic_ip": worker_nic_ip,
                               "ssh_ip": worker_ssh_ip}
                    worker_ip_dict_list.append(ip_dict)

        # Get the hostname of the deleting worker nodes
        worker_hostnames = []
        for worker_ip_dict in worker_ip_dict_list:
            # get worker host names
            worker_hostname = \
                'worker' + worker_ip_dict.get("nic_ip").split('.')[-1]
            worker_hostnames.append(worker_hostname)

        return worker_hostnames, worker_ip_dict_list

    @log.log
    def heal_start(self, context, vnf_instance,
                   heal_vnf_request, grant,
                   grant_request, **kwargs):
        vnf_additional_params = \
            vnf_instance.instantiated_vnf_info.additional_params

        # heal of the entire VNF
        if not heal_vnf_request.vnfc_instance_id:
            self.terminate_end(context, vnf_instance, heal_vnf_request,
                               grant, grant_request)
        else:
            # heal specified with VNFC instances
            heal_physical_resource_ids = \
                self._get_heal_physical_resource_ids(
                    vnf_instance, heal_vnf_request)

            worker_node, external_lb_param, ansible, vim_connection_info = \
                self._get_initial_parameters(
                    context, vnf_instance, heal_vnf_request)

            nest_stack_id = vnf_instance.instantiated_vnf_info.instance_id

            # Get the ssh ip of LB
            heatclient = hc.HeatClient(vim_connection_info.access_info)
            ssh_ip, _ = self._get_ssh_ip_and_nic_ip(
                heatclient, nest_stack_id, external_lb_param)

            # Get the worker_hostnames to be healed
            worker_hostnames, _ = self._get_heal_worker_node_info(
                vnf_additional_params, worker_node, heatclient,
                nest_stack_id, heal_physical_resource_ids)

            # remove_worker_node_from_k8s_cluster and update configuration file
            self._remove_node_and_update_config_file(
                worker_hostnames, external_lb_param,
                ssh_ip, ansible, worker_node, 'HEAL')

    @log.log
    def heal_end(self, context, vnf_instance,
                 heal_vnf_request, grant,
                 grant_request, **kwargs):
        vnf_additional_params = \
            vnf_instance.instantiated_vnf_info.additional_params
        # heal of the entire VNF
        if not heal_vnf_request.vnfc_instance_id:
            add_param_list = ['master_node', 'worker_node', 'proxy',
                              'ansible', 'external_lb_param']
            for add_param in add_param_list:
                if heal_vnf_request.additional_params.get(
                        'k8s_cluster_installation_param'):
                    if add_param in heal_vnf_request.additional_params.get(
                            'k8s_cluster_installation_param'):
                        vnf_additional_params.get(
                            'k8s_cluster_installation_param')[add_param] = \
                            heal_vnf_request.additional_params[
                                'k8s_cluster_installation_param'].get(
                                add_param)
            heal_vnf_request.additional_params = vnf_additional_params
            self.instantiate_end(context, vnf_instance, heal_vnf_request,
                                 grant, grant_request)
        else:
            # heal specified with VNFC instances
            heal_physical_resource_ids = \
                self._get_heal_physical_resource_ids(
                    vnf_instance, heal_vnf_request)

            worker_node, external_lb_param, ansible, vim_connection_info = \
                self._get_initial_parameters(
                    context, vnf_instance, heal_vnf_request)

            nest_stack_id = vnf_instance.instantiated_vnf_info.instance_id

            # Get the ssh ip of LB
            heatclient = hc.HeatClient(vim_connection_info.access_info)
            ssh_ip, _ = self._get_ssh_ip_and_nic_ip(
                heatclient, nest_stack_id, external_lb_param)

            # Get the worker_ip_dict_list to be healed
            _, worker_ip_dict_list = self._get_heal_worker_node_info(
                vnf_additional_params, worker_node, heatclient,
                nest_stack_id, heal_physical_resource_ids)

            # Install worker node and update configuration file
            self._install_node_and_update_config_file(
                worker_node, worker_ip_dict_list, ansible,
                external_lb_param, ssh_ip)

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

    @log.log
    def modify_information_start(self, context, vnf_instance,
                                 modify_vnf_request, **kwargs):
        pass

    @log.log
    def modify_information_end(self, context, vnf_instance,
                               modify_vnf_request, **kwargs):
        pass
