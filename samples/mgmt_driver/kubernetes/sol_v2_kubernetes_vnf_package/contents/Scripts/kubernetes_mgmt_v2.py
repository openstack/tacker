# Copyright (C) 2024 Nippon Telegraph and Telephone Corporation
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
import pickle
import sys
import time

import paramiko

from tacker.common import cmd_executer
from tacker.common import exceptions
from tacker.sol_refactored.infra_drivers.openstack import heat_utils
from tacker.sol_refactored import objects

CONNECT_MASTER_RETRY_TIMES = 4
K8S_CMD_TIMEOUT = 30
K8S_INSTALL_TIMEOUT = 2700
SERVER_WAIT_COMPLETE_TIME = 60


class KubernetesMgmtDriver(object):

    def __init__(self, req, inst, grant_req, grant, csar_dir):
        self.req = req
        self.inst = inst
        self.grant_req = grant_req
        self.grant = grant
        self.csar_dir = csar_dir
        self._init_flag()
        objects.register_all()
        if self.inst.get('vimConnectionInfo'):
            self.heat_client = heat_utils.HeatClient(
                objects.VimConnectionInfo.from_dict(
                    self._select_vim_info(self.inst['vimConnectionInfo'])))

    def _init_flag(self):
        self.FLOATING_IP_FLAG = False
        self.SET_NODE_LABEL_FLAG = False

    def _select_vim_info(self, vim_connection_info):
        for vim_info in vim_connection_info.values():
            if vim_info['vimType'] == 'kubernetes':
                vim_info['vimType'] = 'ETSINFV.KUBERNETES.V_1'
            return vim_info

    def _check_is_cidr(self, cidr_str):
        # instantiate: check cidr
        try:
            ipaddress.ip_network(cidr_str)
            return True
        except ValueError:
            return False

    def _execute_command(self, commander, ssh_command, timeout, type, retry):
        while retry >= 0:
            try:
                result = commander.execute_command(ssh_command,
                                                   input_data=None)
                break
            except Exception:
                msg = ('It is time out, When execute command: '
                       '{}.'.format(ssh_command))
                sys.stderr.write(msg)
                retry -= 1
                if retry < 0:
                    msg = ('It is time out, When execute command: '
                           '{}.'.format(ssh_command))
                    raise Exception(msg)
                time.sleep(30)
        if type == 'common' or type == 'etcd':
            err = result.get_stderr()
            if err:
                raise Exception(err)
        elif type in ('certificate_key', 'install', 'scp', 'set_hosts'):
            if result.get_return_code() != 0:
                err = result.get_stderr()
                raise Exception(err)
        elif type == 'check_node':
            err = result.get_stderr()[0].replace('\n', '')
            if result.get_return_code() == 0:
                pass
            elif (result.get_return_code() != 0 and
                    "kubectl: command not found" in err):
                return "False"
            else:
                raise Exception(err)
        elif type == 'check_secret':
            if result.get_return_code() == 0:
                return True
            err = result.get_stderr()[0].replace('\n', '')
            if (result.get_return_code() != 0 and
                    'secrets "default-token-k8vim" not found' in err):
                return False
        elif type == 'check_installed':
            if result.get_return_code() == 0:
                return True
            else:
                return False
        return result.get_stdout()

    def _get_nic_ip(self, stack_id, cp_name):
        cp_info = self.heat_client.get_resource_info(stack_id, cp_name)
        cp_info.get('attributes', {}).get('fixed_ips')
        return cp_info['attributes']['fixed_ips'][0].get('ip_address')

    def _get_ssh_ip(self, stack_id, cp_name):
        # NOTE: It is assumed that if the user want to use floating_ip,
        # he must specify the resource name of 'OS::Neutron::FloatingIP'
        # resource as cp_name (ex. VDU1_FloatingIp).
        cp_info = self.heat_client.get_resource_info(stack_id, cp_name)
        if cp_info.get('attributes', {}).get('floating_ip_address'):
            self.FLOATING_IP_FLAG = True
            return cp_info['attributes']['floating_ip_address']
        elif cp_info.get('attributes', {}).get('fixed_ips'):
            return cp_info['attributes']['fixed_ips'][0].get('ip_address')

    def _get_host_compute(self, stack_id, vdu_id):
        node_res_info = self.heat_client.get_resource_info(stack_id, vdu_id)
        host_compute = node_res_info.get('attributes', {}).get(
            'OS-EXT-SRV-ATTR:host')
        return host_compute

    def _get_install_info_for_k8s_node(self, nest_stack_id, node, role):
        # instantiate: get k8s ssh ips
        vm_dict_list = []
        vdu_id = node['vdu_id']
        # get ssh_ip and nic_ip and set ssh's values
        vnfcs = self._get_vnfcs(vdu_id)
        for vnfc in vnfcs:
            host_compute = ''
            stack_id = vnfc['metadata']['stack_id']
            ssh_ip = self._get_ssh_ip(stack_id, node['ssh_cp_name'])
            nic_ip = self._get_nic_ip(stack_id, node['nic_cp_name'])
            if not ssh_ip:
                raise Exception('ssh ip not found.')

            host_compute = self._get_host_compute(stack_id, vdu_id)
            vm_dict = {
                "host_compute": host_compute,
                "ssh": {
                    "username": node["username"],
                    "password": node["password"],
                    "ipaddr": ssh_ip,
                    "nic_ip": nic_ip
                }
            }
            vm_dict_list.append(vm_dict)
        # get cluster_ip from master node
        if role == 'master':
            cluster_fip = ''
            cluster_ip = ''
            if len(vm_dict_list) > 1:
                stack_id = nest_stack_id
            else:
                stack_id = vnfcs[0]['metadata']['stack_id']
            cluster_ip = self._get_nic_ip(stack_id, node['cluster_cp_name'])
            if self.FLOATING_IP_FLAG and node.get('cluster_fip_name'):
                cluster_fip = self._get_ssh_ip(stack_id,
                                               node['cluster_fip_name'])
            # set k8s_cluster's values
            for vm_dict in vm_dict_list:
                vm_dict['k8s_cluster'] = {
                    "pod_cidr": node['pod_cidr'],
                    "cluster_cidr": node['cluster_cidr'],
                    "ipaddr": cluster_ip,
                    "cluster_fip": cluster_fip
                }
        return vm_dict_list

    def _get_hosts(self, master_vm_dict_list, worker_vm_dict_list):
        # merge /etc/hosts
        hosts = []
        for master_vm_dict in master_vm_dict_list:
            hosts_master_ip = master_vm_dict['ssh']['nic_ip']
            hosts.append(hosts_master_ip + ' ' + 'master' +
                         hosts_master_ip.split('.')[-1])
        for worker_vm_dict in worker_vm_dict_list:
            hosts_worker_ip = worker_vm_dict['ssh']['nic_ip']
            hosts.append(hosts_worker_ip + ' ' + 'worker' +
                         hosts_worker_ip.split('.')[-1])
        hosts_str = '\\n'.join(hosts)
        return hosts_str

    def _get_stack_id(self):
        return (f"vnf-{self.inst['id']}/"
                f"{self.inst['instantiatedVnfInfo']['metadata']['stack_id']}")

    def _init_commander_and_send_install_scripts(
            self, user, password, host, vnf_package_path=None,
            script_path=None):
        retry = 4
        while retry > 0:
            try:
                if vnf_package_path and script_path:
                    connect = paramiko.Transport(host, 22)
                    connect.connect(username=user, password=password)
                    sftp = paramiko.SFTPClient.from_transport(connect)
                    # put script file content to '/tmp/install_k8s_cluster.sh'
                    sftp.put(os.path.join(vnf_package_path, script_path),
                             "/tmp/install_k8s_cluster.sh")
                    sftp.put(os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        "create_admin_token.yaml"),
                        "/tmp/create_admin_token.yaml")
                    connect.close()
                commander = cmd_executer.RemoteCommandExecutor(
                    user=user, password=password, host=host,
                    timeout=K8S_INSTALL_TIMEOUT)
                return commander
            except (exceptions.NotAuthorized, paramiko.SSHException,
                    paramiko.ssh_exception.NoValidConnectionsError) as e:
                sys.stderr.write(str(e))
                retry -= 1
                if retry == 0:
                    raise Exception(e)
                time.sleep(SERVER_WAIT_COMPLETE_TIME)

    def _init_commander(self, user, password, host, retry=4):
        while retry > 0:
            try:
                commander = cmd_executer.RemoteCommandExecutor(
                    user=user, password=password, host=host,
                    timeout=K8S_INSTALL_TIMEOUT)
                return commander
            except Exception as e:
                sys.stderr.write(str(e))
                retry -= 1
                if retry == 0:
                    sys.stderr.write(str(e))
                    raise
                time.sleep(SERVER_WAIT_COMPLETE_TIME)

    def _install_worker_node(self, commander, ha_flag, nic_ip, cluster_ip,
                             kubeadm_token, ssl_ca_cert_hash):
        ssh_command = \
            "export ha_flag={ha_flag};" \
            "bash /tmp/install_k8s_cluster.sh " \
            "-w {worker_ip} -i {cluster_ip} " \
            "-t {kubeadm_token} -s {ssl_ca_cert_hash}".format(
                ha_flag=ha_flag,
                worker_ip=nic_ip, cluster_ip=cluster_ip,
                kubeadm_token=kubeadm_token,
                ssl_ca_cert_hash=ssl_ca_cert_hash)

        self._execute_command(
            commander, ssh_command, K8S_INSTALL_TIMEOUT, 'install', 0)

    def _set_node_label(self, commander, nic_ip, host_compute):
        """Set node label function

        This function can set a node label to worker node in kubernetes
        cluster. After login master node of kubernetes cluster via ssh,
        it will execute a cli command of kubectl. This command can update
        the labels on a resource.

        For example:
        If the following command has been executed.
            $ kubectl label nodes worker24 CIS-node=compute01
        The result is:
            $ kubectl get node --show-labels | grep worker24
            NAME      STATUS  ROLES  AGE     VERSION   LABELS
            worker46  Ready   <none> 1m33s   v1.21.0   CIS-node=compute01...

        Then when you deploy pods with this label(`CIS-node`) in
        pod-affinity rule, the pod will be deployed on different worker nodes.
        """
        host_name = 'worker' + nic_ip.split('.')[3]
        if host_compute:
            ssh_command = "kubectl label nodes {host_name}" \
                          " CIS-node={host_compute}".format(
                              host_name=host_name,
                              host_compute=host_compute)
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)

    def _is_master_installed(self, vm_dict):
        nic_ip = vm_dict['ssh']['nic_ip']
        master_name = 'master' + nic_ip.split('.')[-1]
        user = vm_dict['ssh']['username']
        password = vm_dict['ssh']['password']
        host = vm_dict['ssh']['ipaddr']
        commander = self._init_commander_and_send_install_scripts(
            user, password, host)
        ssh_command = f"kubectl get node | grep {master_name}"
        result = self._execute_command(commander, ssh_command,
                                       K8S_CMD_TIMEOUT, 'check_node', 0)
        if result != "False":
            for res in result:
                if res.split(' ')[0].strip() == master_name:
                    return True
        return False

    def _install_k8s_cluster(self, script_path,
                             master_vm_dict_list, worker_vm_dict_list):
        # instantiate: pre /etc/hosts
        hosts_str = self._get_hosts(
            master_vm_dict_list, worker_vm_dict_list)
        master_ssh_ips_str = ','.join(
            [vm_dict['ssh']['nic_ip'] for vm_dict in master_vm_dict_list])
        ha_flag = "True"
        if len(master_vm_dict_list) == 1:
            ha_flag = "False"

        # get vnf package path and check script_path
        abs_script_path = os.path.join(self.csar_dir, script_path)
        if not os.path.exists(abs_script_path):
            raise Exception("The path of install script is invalid")

        # install k8s
        active_username = ""
        active_password = ""
        active_host = ""
        ssl_ca_cert_hash = ""
        kubeadm_token = ""
        get_node_names = []

        # check master_node exist in k8s-cluster
        vm_dict = master_vm_dict_list[0]
        if not self._is_master_installed(vm_dict):
            active_username = vm_dict['ssh']['username']
            active_password = vm_dict['ssh']['password']
            active_host = vm_dict['ssh']['ipaddr']
            k8s_cluster = vm_dict['k8s_cluster']
            commander = self._init_commander_and_send_install_scripts(
                active_username, active_password, active_host,
                self.csar_dir, script_path)

            # set /etc/hosts for each node
            self._set_node_ip_in_hosts(
                commander, 'instantiate_end', hosts_str=hosts_str)

            # execute install k8s command on VM
            ssh_command = \
                "bash /tmp/install_k8s_cluster.sh " \
                "-m {master_ip} -i {cluster_ip} " \
                "-p {pod_cidr} -a {k8s_cluster_cidr}".format(
                    master_ip=master_ssh_ips_str,
                    cluster_ip=k8s_cluster.get("ipaddr"),
                    pod_cidr=k8s_cluster.get('pod_cidr'),
                    k8s_cluster_cidr=k8s_cluster.get('cluster_cidr'))

            results = self._execute_command(
                commander, ssh_command, K8S_INSTALL_TIMEOUT, 'install', 0)

            # get install-information from active master node
            for result in results:
                if 'token:' in result:
                    kubeadm_token = result.replace(
                        'token:', '').replace('\n', '')
                if 'server:' in result:
                    server = result.replace(
                        'server:', '').replace('\n', '')
                if 'ssl_ca_cert_hash:' in result:
                    ssl_ca_cert_hash = result.replace(
                        'ssl_ca_cert_hash:', '').replace('\n', '')
                if 'certificate_key:' in result:
                    certificate_key = result.replace(
                        'certificate_key:', '').replace('\n', '')
            begin_index = results.index('-----BEGIN CERTIFICATE-----\n')
            end_index = results.index('-----END CERTIFICATE-----\n')
            ssl_ca_cert = ''.join(results[begin_index: end_index + 1])
            commander = cmd_executer.RemoteCommandExecutor(
                active_username, active_password, active_host,
                timeout=K8S_CMD_TIMEOUT)

            # Check whether the secret already exists
            if not self._has_secret(commander):
                ssh_command = ("kubectl create clusterrolebinding "
                               "cluster-admin-binding "
                               "--clusterrole cluster-admin "
                               "--serviceaccount=default:default && "
                               "kubectl create -f "
                               "/tmp/create_admin_token.yaml")
                self._execute_command(
                    commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
                time.sleep(30)
            else:
                ssh_command = "kubectl get node"
                get_node_names = self._execute_command(
                    commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)

            ssh_command = "kubectl get secret " \
                          "| grep '^default-token' " \
                          "| awk '{print $1}' " \
                          "| xargs -i kubectl describe secret {} " \
                          "| grep 'token:' | awk '{print $2}'"
            bearer_token = self._execute_command(
                commander, ssh_command,
                K8S_CMD_TIMEOUT, 'common', 0)[0].replace('\n', '')
            commander.close_session()

        for vm_dict in master_vm_dict_list[1:]:
            if self._is_master_installed(vm_dict):
                continue
            user = vm_dict['ssh']['username']
            password = vm_dict['ssh']['password']
            host = vm_dict['ssh']['ipaddr']
            k8s_cluster = vm_dict['k8s_cluster']
            commander = self._init_commander_and_send_install_scripts(
                user, password, host, self.csar_dir, script_path)

            # set /etc/hosts for each node
            self._set_node_ip_in_hosts(
                commander, 'instantiate_end', hosts_str=hosts_str)

            # execute install k8s command on VM
            ssh_command = \
                "bash /tmp/install_k8s_cluster.sh " \
                "-m {master_ip} -i {cluster_ip} " \
                "-p {pod_cidr} -a {k8s_cluster_cidr} " \
                "-t {kubeadm_token} -s {ssl_ca_cert_hash} " \
                "-k {certificate_key}".format(
                    master_ip=master_ssh_ips_str,
                    cluster_ip=k8s_cluster.get("ipaddr"),
                    pod_cidr=k8s_cluster.get('pod_cidr'),
                    k8s_cluster_cidr=k8s_cluster.get('cluster_cidr'),
                    kubeadm_token=kubeadm_token,
                    ssl_ca_cert_hash=ssl_ca_cert_hash,
                    certificate_key=certificate_key)

            results = self._execute_command(
                commander, ssh_command, K8S_INSTALL_TIMEOUT, 'install', 0)
            commander.close_session()

        # install worker node
        for vm_dict in worker_vm_dict_list:
            user = vm_dict['ssh']['username']
            password = vm_dict['ssh']['password']
            host = vm_dict['ssh']['ipaddr']
            nic_ip = vm_dict['ssh']['nic_ip']
            cluster_ip = master_vm_dict_list[0]['k8s_cluster']['ipaddr']
            commander = self._init_commander_and_send_install_scripts(
                user, password, host, self.csar_dir, script_path)

            # set /etc/hosts for each node
            self._set_node_ip_in_hosts(
                commander, 'instantiate_end', hosts_str=hosts_str)

            # execute install k8s command on VM
            for get_node_name in get_node_names:
                if ('worker' + nic_ip.split('.')[-1] ==
                        get_node_name.split(' ')[0]):
                    break
            else:
                self._install_worker_node(
                    commander, ha_flag, nic_ip, cluster_ip,
                    kubeadm_token, ssl_ca_cert_hash)
            commander.close_session()

            # set node label
            commander = cmd_executer.RemoteCommandExecutor(
                user=active_username, password=active_password,
                host=active_host, timeout=K8S_CMD_TIMEOUT)
            self._set_node_label(commander, nic_ip, vm_dict['host_compute'])
            commander.close_session()

        # check cilium status
        commander = cmd_executer.RemoteCommandExecutor(
            user=active_username, password=active_password,
            host=active_host, timeout=K8S_CMD_TIMEOUT)
        self._check_cilium_status(commander)
        commander.close_session()

        return (server, bearer_token, ssl_ca_cert)

    def _has_secret(self, commander):
        # NOTE: Check secret to be registered in file
        # "create_admin_token.yaml".
        ssh_command = "kubectl get secret default-token-k8svim"
        return self._execute_command(
            commander, ssh_command, K8S_CMD_TIMEOUT, 'check_secret', 0)

    def _connect_ssh_scale(self, master_ip_list, master_username,
                           master_password):
        for master_ip in master_ip_list:
            retry = 4
            while retry > 0:
                try:
                    commander = cmd_executer.RemoteCommandExecutor(
                        user=master_username, password=master_password,
                        host=master_ip, timeout=K8S_CMD_TIMEOUT)
                    return commander, master_ip
                except (exceptions.NotAuthorized, paramiko.SSHException,
                        paramiko.ssh_exception.NoValidConnectionsError):
                    retry -= 1
                    time.sleep(SERVER_WAIT_COMPLETE_TIME)
        if master_ip == master_ip_list[-1]:
            msg = 'Failed to execute remote command.'
            raise Exception(msg)

    def evacuate_wait(self, commander, daemonset_content):
        # scale: evacuate wait
        wait_flag = True
        retry_count = 20
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
                            'cilium' not in daemonset_name and \
                            'kube-proxy' not in daemonset_name:
                        break
                else:
                    wait_flag = False
            else:
                break
            if not wait_flag:
                break
            time.sleep(15)
            retry_count -= 1

    def _get_vnfcs(self, vdu_id):
        return [vnfc
            for vnfc in self.inst['instantiatedVnfInfo']['vnfcResourceInfo']
            if vnfc['vduId'] == vdu_id]

    def _get_user_info(self, node):
        return node["username"], node["password"]

    def _delete_scale_in_worker(self, worker_node, scale_in_ids, commander):
        # scale: get host name
        scale_worker_nic_ips = []
        normal_worker_ssh_ips = []
        worker_host_names = []

        vnfcs = self._get_vnfcs(worker_node['vdu_id'])
        for vnfc in vnfcs:
            stack_id = vnfc['metadata']['stack_id']
            if vnfc.get('computeResource').get('resourceId') in scale_in_ids:
                nic_ip = self._get_nic_ip(stack_id, worker_node['nic_cp_name'])
                scale_worker_nic_ips.append(nic_ip)
                worker_host_name = 'worker' + nic_ip.split('.')[-1]
                worker_host_names.append(worker_host_name)
            else:
                ssh_ip = self._get_ssh_ip(stack_id, worker_node['ssh_cp_name'])
                normal_worker_ssh_ips.append(ssh_ip)

        for worker_host_name in worker_host_names:
            ssh_command = "kubectl get pods --field-selector=spec." \
                          "nodeName={} --all-namespaces " \
                          "-o json".format(worker_host_name)
            result = self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 3)
            daemonset_content_str = ''.join(result)
            daemonset_content = json.loads(daemonset_content_str)
            if not daemonset_content['items']:
                continue
            ssh_command = \
                "kubectl drain {resource} --ignore-daemonsets " \
                "--timeout={k8s_cmd_timeout}s".format(
                    resource=worker_host_name,
                    k8s_cmd_timeout=K8S_CMD_TIMEOUT)
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'drain', 3)
            # evacuate_wait()
            # input: resource, daemonset_content
            self.evacuate_wait(commander, daemonset_content)
            ssh_command = "kubectl delete node {}".format(worker_host_name)
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 3)
        return scale_worker_nic_ips, normal_worker_ssh_ips

    def _get_worker_info(self, worker_node, scale_out_ids):
        normal_ssh_worker_ip_list = []
        normal_nic_worker_ip_list = []
        add_worker_ssh_ip_list = []
        add_worker_nic_ip_list = []
        host_compute_dict = {}

        vnfcs = self._get_vnfcs(worker_node['vdu_id'])
        for vnfc in vnfcs:
            host_compute = ''
            stack_id = vnfc['metadata']['stack_id']
            ssh_ip = self._get_ssh_ip(stack_id, worker_node['ssh_cp_name'])
            nic_ip = self._get_nic_ip(stack_id, worker_node['nic_cp_name'])

            if vnfc['id'] in scale_out_ids:
                add_worker_ssh_ip_list.append(ssh_ip)
                add_worker_nic_ip_list.append(nic_ip)
                host_compute = self._get_host_compute(
                    stack_id, worker_node['vdu_id'])
                host_compute_dict[nic_ip] = host_compute
            else:
                normal_ssh_worker_ip_list.append(ssh_ip)
                normal_nic_worker_ip_list.append(nic_ip)

        return (add_worker_ssh_ip_list, add_worker_nic_ip_list,
                normal_ssh_worker_ip_list, normal_nic_worker_ip_list,
                host_compute_dict)

    def _set_node_ip_in_hosts(self, commander,
                              operation, ips=None, hosts_str=None):
        ssh_command = "cp /etc/hosts /tmp/tmp_hosts"
        self._execute_command(
            commander, ssh_command, K8S_CMD_TIMEOUT, 'set_hosts', 0)
        if operation == 'scale_in':
            for ip in ips:
                ssh_command = "sed -i '/{}/d' /tmp/tmp_hosts".format(ip + " ")
                self._execute_command(
                    commander, ssh_command, K8S_CMD_TIMEOUT, 'set_hosts', 0)
        elif (operation == 'scale_out'
                or operation == 'heal_end'
                or operation == 'instantiate_end'):
            ssh_command = "sed -i '$a{}' /tmp/tmp_hosts".format(hosts_str)
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'set_hosts', 0)
        ssh_command = "sudo mv /tmp/tmp_hosts /etc/hosts;"
        self._execute_command(
            commander, ssh_command, K8S_CMD_TIMEOUT, 'set_hosts', 0)

    def _check_cilium_status(self, commander):
        ssh_command = "cilium status --wait"
        return self._execute_command(
            commander, ssh_command, K8S_CMD_TIMEOUT, 'install', 0)

    def _delete_master_node(
            self, fixed_master_infos, not_fixed_master_infos,
            master_username, master_password):
        not_fixed_master_ssh_ips = [
            master_ips['master_ssh_ip']
            for master_ips in not_fixed_master_infos.values()]

        for fixed_master_name in fixed_master_infos.keys():
            # delete heal master node info from haproxy.cfg
            # on other master node
            for not_fixed_master_ssh_ip in not_fixed_master_ssh_ips:
                commander = cmd_executer.RemoteCommandExecutor(
                    user=master_username, password=master_password,
                    host=not_fixed_master_ssh_ip, timeout=K8S_CMD_TIMEOUT)
                master_ssh_ip = not_fixed_master_ssh_ip
                ssh_command = "sudo sed -i '/server  {}/d' " \
                              "/etc/haproxy/haproxy.cfg;" \
                              "sudo service haproxy restart;" \
                              "".format(fixed_master_name)
                self._execute_command(
                    commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 3)

            # check worker_node exist in k8s-cluster
            result = self._is_worker_node_installed(commander,
                                                    fixed_master_name)
            if not result:
                continue
            for res in result:
                if res.split(' ')[0].strip() == fixed_master_name:
                    # fixed_master_name is found
                    break
            else:
                continue

            # delete master node
            ssh_command = "kubectl delete node " + fixed_master_name
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 3)
            connect_master_name = ''
            for not_master_name, not_master_ip_info in \
                    not_fixed_master_infos.items():
                if not_master_ip_info['master_ssh_ip'] == master_ssh_ip:
                    connect_master_name = not_master_name
            ssh_command = \
                "kubectl get pods -n kube-system | " \
                "grep %(connect_master_name)s | " \
                "awk '{print $1}'" \
                "" % {'connect_master_name': connect_master_name}
            etcd_name = self._execute_command(
                commander, ssh_command,
                K8S_CMD_TIMEOUT, 'common', 3)[0].replace('\n', '')
            ssh_command = \
                "kubectl exec -i %(etcd_name)s -n kube-system " \
                "-- sh<< EOF\n" \
                "etcdctl --endpoints 127.0.0.1:2379 " \
                "--cacert /etc/kubernetes/pki/etcd/ca.crt " \
                "--cert /etc/kubernetes/pki/etcd/server.crt " \
                "--key /etc/kubernetes/pki/etcd/server.key " \
                "member list\nEOF" \
                "" % {'etcd_name': etcd_name}
            results = self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'etcd', 3)
            etcd_id = [res for res in results
                       if fixed_master_name in res][0].split(',')[0]
            ssh_command = \
                "kubectl exec -i %(etcd_name)s -n kube-system " \
                "-- sh<< EOF\n" \
                "etcdctl --endpoints 127.0.0.1:2379 " \
                "--cacert /etc/kubernetes/pki/etcd/ca.crt " \
                "--cert /etc/kubernetes/pki/etcd/server.crt " \
                "--key /etc/kubernetes/pki/etcd/server.key " \
                "member remove %(etcd_id)s\nEOF" % \
                {'etcd_name': etcd_name, "etcd_id": etcd_id}
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'etcd', 3)
            commander.close_session()

    def _is_worker_node_installed(self, commander, fixed_master_name):
        ssh_command = f"kubectl get node | grep {fixed_master_name}"
        return self._execute_command(
            commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)

    def _delete_worker_node(
            self, fixed_worker_infos, not_fixed_master_infos,
            master_username, master_password):
        not_fixed_master_ssh_ips = [
            master_ips['master_ssh_ip']
            for master_ips in not_fixed_master_infos.values()]
        for fixed_worker_name in fixed_worker_infos.keys():
            commander, master_ssh_ip = self._connect_ssh_scale(
                not_fixed_master_ssh_ips, master_username, master_password)
            ssh_command = "kubectl get pods --field-selector=" \
                          "spec.nodeName={} --all-namespaces " \
                          "-o json".format(fixed_worker_name)
            result = self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 3)
            worker_node_pod_info_str = ''.join(result)
            worker_node_pod_info = json.loads(worker_node_pod_info_str)
            if not worker_node_pod_info['items']:
                continue
            ssh_command = "kubectl drain {} " \
                          "--ignore-daemonsets " \
                          "--timeout={}s" \
                          "".format(fixed_worker_name, K8S_CMD_TIMEOUT)
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'drain', 3)
            self.evacuate_wait(commander, worker_node_pod_info)
            ssh_command = "kubectl delete node {}".format(fixed_worker_name)
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 3)
            commander.close_session()

    def _get_master_node_name(self, heal_ids, master_node):
        fixed_master_infos = {}
        not_fixed_master_infos = {}
        flag_master = False

        vnfcs = self._get_vnfcs(master_node['vdu_id'])
        for vnfc in vnfcs:
            stack_id = vnfc['metadata']['stack_id']
            master_ssh_ip = self._get_ssh_ip(stack_id,
                                             master_node['ssh_cp_name'])
            master_nic_ip = self._get_nic_ip(stack_id,
                                             master_node['nic_cp_name'])
            master_name = 'master' + master_nic_ip.split('.')[-1]
            if vnfc.get('computeResource').get('resourceId') in heal_ids:
                flag_master = True
                fixed_master_infos[master_name] = {}
                fixed_master_infos[master_name]['master_ssh_ip'] = \
                    master_ssh_ip
                fixed_master_infos[master_name]['master_nic_ip'] = \
                    master_nic_ip
            else:
                not_fixed_master_infos[master_name] = {}
                not_fixed_master_infos[master_name]['master_ssh_ip'] = \
                    master_ssh_ip
                not_fixed_master_infos[master_name]['master_nic_ip'] = \
                    master_nic_ip
        if flag_master and len(vnfcs) == len(fixed_master_infos):
            msg = ("An error occurred in MgmtDriver:"
                   "{Not all MasterNodes can be heal targets.}")
            raise Exception(msg)

        return flag_master, fixed_master_infos, not_fixed_master_infos

    def _get_worker_node_name(self, heal_ids, worker_node):
        fixed_worker_infos = {}
        not_fixed_worker_infos = {}
        flag_worker = False

        vnfcs = self._get_vnfcs(worker_node['vdu_id'])
        for vnfc in vnfcs:
            stack_id = vnfc['metadata']['stack_id']
            worker_ssh_ip = self._get_ssh_ip(stack_id,
                                             worker_node['ssh_cp_name'])
            worker_nic_ip = self._get_nic_ip(stack_id,
                                             worker_node['nic_cp_name'])
            worker_name = 'worker' + worker_nic_ip.split('.')[-1]
            if vnfc.get('computeResource').get('resourceId') in heal_ids:
                flag_worker = True
                fixed_worker_infos[worker_name] = {}
                fixed_worker_infos[worker_name]['worker_ssh_ip'] = \
                    worker_ssh_ip
                fixed_worker_infos[worker_name]['worker_nic_ip'] = \
                    worker_nic_ip
            else:
                not_fixed_worker_infos[worker_name] = {}
                not_fixed_worker_infos[worker_name]['worker_ssh_ip'] = \
                    worker_ssh_ip
                not_fixed_worker_infos[worker_name]['worker_nic_ip'] = \
                    worker_nic_ip
        return flag_worker, fixed_worker_infos, not_fixed_worker_infos

    def _is_node_installed(self, host, node_info):
        user = node_info['username']
        password = node_info['password']
        commander = self._init_commander_and_send_install_scripts(
            user, password, host)
        ssh_command = "ls /tmp/installed"
        result = self._execute_command(
            commander, ssh_command, K8S_CMD_TIMEOUT, 'check_installed', 0)
        return result

    def _get_heal_master_node(self, master_node):
        fixed_master_infos = {}
        not_fixed_master_infos = {}
        flag_master = False

        vnfcs = self._get_vnfcs(master_node['vdu_id'])
        for vnfc in vnfcs:
            stack_id = vnfc['metadata']['stack_id']
            ssh_ip = self._get_ssh_ip(stack_id, master_node['ssh_cp_name'])
            nic_ip = self._get_nic_ip(stack_id, master_node['nic_cp_name'])
            master_name = 'master' + nic_ip.split('.')[-1]
            if not self._is_node_installed(ssh_ip, master_node):
                flag_master = True
                fixed_master_infos[master_name] = {}
                fixed_master_infos[master_name]['master_ssh_ip'] = ssh_ip
                fixed_master_infos[master_name]['master_nic_ip'] = nic_ip
            else:
                not_fixed_master_infos[master_name] = {}
                not_fixed_master_infos[master_name]['master_ssh_ip'] = ssh_ip
                not_fixed_master_infos[master_name]['master_nic_ip'] = nic_ip
        if flag_master and len(vnfcs) == 1:
            msg = ("An error occurred in MgmtDriver:"
                   "{Not all MasterNodes can be heal targets.")
            raise Exception(msg)

        return flag_master, fixed_master_infos, not_fixed_master_infos

    def _get_heal_worker_node(self, worker_node):
        fixed_worker_infos = {}
        not_fixed_worker_infos = {}
        flag_worker = False

        vnfcs = self._get_vnfcs(worker_node['vdu_id'])
        for vnfc in vnfcs:
            stack_id = vnfc['metadata']['stack_id']
            ssh_ip = self._get_ssh_ip(stack_id, worker_node['ssh_cp_name'])
            nic_ip = self._get_nic_ip(stack_id, worker_node['nic_cp_name'])
            worker_name = 'worker' + nic_ip.split('.')[-1]
            if not self._is_node_installed(ssh_ip, worker_node):
                flag_worker = True
                fixed_worker_infos[worker_name] = {}
                fixed_worker_infos[worker_name]['worker_ssh_ip'] = ssh_ip
                fixed_worker_infos[worker_name]['worker_nic_ip'] = nic_ip
                host_compute = self._get_host_compute(
                    vnfc['metadata']['stack_id'], worker_node['vdu_id'])
                fixed_worker_infos[worker_name]['host_compute'] = host_compute
            else:
                not_fixed_worker_infos[worker_name] = {}
                not_fixed_worker_infos[worker_name]['worker_ssh_ip'] = ssh_ip
                not_fixed_worker_infos[worker_name]['worker_nic_ip'] = nic_ip
        return flag_worker, fixed_worker_infos, not_fixed_worker_infos

    def _delete_node(self, stack_id, heal_ids,
            master_username, master_password, master_node, worker_node):
        master_resource_list = [
            vnfc.get('computeResource').get('resourceId')
            for vnfc in self.inst['instantiatedVnfInfo']['vnfcResourceInfo']
            if vnfc['vduId'] == master_node['vdu_id']]
        flag_master, fixed_master_infos, not_fixed_master_infos = \
            self._get_master_node_name(heal_ids, master_node)

        if (flag_master and
                len(master_resource_list) == len(fixed_master_infos)):
            msg = ("An error occurred in MgmtDriver:"
                   "{Not all MasterNodes can be heal targets.}")
            raise Exception(msg)

        flag_worker, fixed_worker_infos, not_fixed_worker_infos = \
            self._get_worker_node_name(heal_ids, worker_node)
        if flag_master:
            self._delete_master_node(
                fixed_master_infos, not_fixed_master_infos,
                master_username, master_password)
        if flag_worker:
            self._delete_worker_node(
                fixed_worker_infos, not_fixed_master_infos,
                master_username, master_password)

    def _fix_master_node(
            self, not_fixed_master_infos, hosts_str,
            fixed_master_infos, master_username, master_password,
            script_path, cluster_ip, pod_cidr, cluster_cidr,
            kubeadm_token, ssl_ca_cert_hash, ha_flag):
        not_fixed_master_nic_ips = [
            master_ips.get('master_nic_ip')
            for master_ips in not_fixed_master_infos.values()]
        not_fixed_master_ssh_ips = [
            master_ips.get('master_ssh_ip')
            for master_ips in not_fixed_master_infos.values()]
        fixed_master_nic_ips = [
            master_ips.get('master_nic_ip')
            for master_ips in fixed_master_infos.values()]
        master_ssh_ips_str = ','.join(
            not_fixed_master_nic_ips + fixed_master_nic_ips)
        for fixed_master_name, fixed_master_info in fixed_master_infos.items():
            commander, master_ip = self._connect_ssh_scale(
                not_fixed_master_ssh_ips, master_username, master_password)
            ssh_command = "sudo kubeadm init phase upload-certs " \
                          "--upload-certs"
            result = self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'certificate_key', 3)
            certificate_key = result[-1].replace('\n', '')
            commander.close_session()
            commander = self._init_commander_and_send_install_scripts(
                master_username, master_password,
                fixed_master_info.get('master_ssh_ip'),
                self.csar_dir, script_path)
            self._set_node_ip_in_hosts(
                commander, 'heal_end', hosts_str=hosts_str)

            ssh_command = \
                "export ha_flag={ha_flag};" \
                "bash /tmp/install_k8s_cluster.sh " \
                "-m {master_ip} -i {cluster_ip} " \
                "-p {pod_cidr} -a {k8s_cluster_cidr} " \
                "-t {kubeadm_token} -s {ssl_ca_cert_hash} " \
                "-k {certificate_key}".format(
                    ha_flag=ha_flag,
                    master_ip=master_ssh_ips_str,
                    cluster_ip=cluster_ip,
                    pod_cidr=pod_cidr,
                    k8s_cluster_cidr=cluster_cidr,
                    kubeadm_token=kubeadm_token,
                    ssl_ca_cert_hash=ssl_ca_cert_hash,
                    certificate_key=certificate_key)

            self._execute_command(
                commander, ssh_command, K8S_INSTALL_TIMEOUT, 'install', 0)
            commander.close_session()
            for not_fixed_master_name, not_fixed_master in \
                    not_fixed_master_infos.items():
                commander = self._init_commander_and_send_install_scripts(
                    master_username, master_password,
                    not_fixed_master.get('master_ssh_ip'))
                ssh_command = "grep 'server  master' " \
                              "/etc/haproxy/haproxy.cfg | tail -n 1"
                server_string = self._execute_command(
                    commander, ssh_command, K8S_CMD_TIMEOUT,
                    'common', 3)[0].replace('\n', '')
                ssh_command = r"sudo sed -i '/{}/a\    server  " \
                              "{}  {}:6443 check' " \
                              "/etc/haproxy/haproxy.cfg" \
                              "".format(server_string, fixed_master_name,
                                        fixed_master_info.get('master_nic_ip'))
                self._execute_command(
                    commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 3)
                commander.close_session()

    def _fix_worker_node(
            self, fixed_worker_infos, hosts_str, worker_username,
            worker_password, script_path, cluster_ip,
            kubeadm_token, ssl_ca_cert_hash, ha_flag):
        for fixed_worker_name, fixed_worker in fixed_worker_infos.items():
            commander = self._init_commander_and_send_install_scripts(
                worker_username, worker_password,
                fixed_worker.get('worker_ssh_ip'), self.csar_dir, script_path)
            self._install_worker_node(
                commander, ha_flag, fixed_worker.get('worker_nic_ip'),
                cluster_ip, kubeadm_token, ssl_ca_cert_hash)
            self._set_node_ip_in_hosts(
                commander, 'heal_end', hosts_str=hosts_str)
            commander.close_session()

    def _get_all_hosts(self, not_fixed_master_infos, fixed_master_infos,
                       not_fixed_worker_infos, fixed_worker_infos):
        master_hosts = []
        worker_hosts = []

        not_fixed_master_nic_ips = [
            master_ips.get('master_nic_ip')
            for master_ips in not_fixed_master_infos.values()]
        fixed_master_nic_ips = [
            master_ips.get('master_nic_ip')
            for master_ips in fixed_master_infos.values()]
        not_fixed_worker_nic_ips = [
            worker_ips.get('worker_nic_ip')
            for worker_ips in not_fixed_worker_infos.values()]
        fixed_worker_nic_ips = [
            worker_ips.get('worker_nic_ip')
            for worker_ips in fixed_worker_infos.values()]

        for not_fixed_master_ip in not_fixed_master_nic_ips:
            master_ip_str = \
                not_fixed_master_ip + ' master' + \
                not_fixed_master_ip.split('.')[-1]
            master_hosts.append(master_ip_str)

        for fixed_master_nic_ip in fixed_master_nic_ips:
            master_ip_str = \
                fixed_master_nic_ip + ' master' + \
                fixed_master_nic_ip.split('.')[-1]
            master_hosts.append(master_ip_str)

        for not_fixed_worker_ip in not_fixed_worker_nic_ips:
            worker_ip_str = \
                not_fixed_worker_ip + ' worker' + \
                not_fixed_worker_ip.split('.')[-1]
            worker_hosts.append(worker_ip_str)

        for fixed_worker_nic_ip in fixed_worker_nic_ips:
            worker_ip_str = \
                fixed_worker_nic_ip + ' worker' + \
                fixed_worker_nic_ip.split('.')[-1]
            worker_hosts.append(worker_ip_str)

        hosts_str = '\\n'.join(master_hosts + worker_hosts)

        return hosts_str

    def _join_k8s_node(
            self, stack_id, k8s_install_params, master_node, worker_node):

        flag_master, fixed_master_infos, not_fixed_master_infos = \
            self._get_heal_master_node(master_node)

        flag_worker, fixed_worker_infos, not_fixed_worker_infos = \
            self._get_heal_worker_node(worker_node)

        if len(fixed_master_infos) + len(not_fixed_master_infos) > 1:
            ha_flag = True
            cluster_ip = self._get_nic_ip(stack_id,
                                          master_node['cluster_cp_name'])
        else:
            ha_flag = False
            cluster_ip = list(not_fixed_master_infos.values())[0].get(
                'master_nic_ip')

        script_path = k8s_install_params['script_path']
        pod_cidr = master_node['pod_cidr']
        cluster_cidr = master_node["cluster_cidr"]
        not_fixed_master_ssh_ips = [
            master_ips.get('master_ssh_ip')
            for master_ips in not_fixed_master_infos.values()]
        commander, master_ip = self._connect_ssh_scale(
            not_fixed_master_ssh_ips, master_node["username"],
            master_node["password"])
        ssh_command = "sudo kubeadm token create"
        kubeadm_token = self._execute_command(
            commander, ssh_command,
            K8S_CMD_TIMEOUT, 'common', 3)[0].replace('\n', '')

        # get hash from one of master node
        ssh_command = "sudo openssl x509 -pubkey -in " \
                      "/etc/kubernetes/pki/ca.crt | openssl rsa " \
                      "-pubin -outform der 2>/dev/null | " \
                      "openssl dgst -sha256 -hex | sed 's/^.* //'"
        ssl_ca_cert_hash = self._execute_command(
            commander, ssh_command,
            K8S_CMD_TIMEOUT, 'common', 3)[0].replace('\n', '')

        commander.close_session()

        hosts_str = self._get_all_hosts(
            not_fixed_master_infos, fixed_master_infos,
            not_fixed_worker_infos, fixed_worker_infos)

        if flag_master:
            self._fix_master_node(
                not_fixed_master_infos, hosts_str, fixed_master_infos,
                master_node["username"], master_node["password"],
                script_path, cluster_ip, pod_cidr, cluster_cidr,
                kubeadm_token, ssl_ca_cert_hash, ha_flag)

        if flag_worker:
            self._fix_worker_node(
                fixed_worker_infos, hosts_str,
                worker_node["username"], worker_node["password"], script_path,
                cluster_ip, kubeadm_token, ssl_ca_cert_hash, ha_flag)

            # Set worker node labels
            for fixed_worker_name, fixed_worker in fixed_worker_infos.items():
                commander, _ = self._connect_ssh_scale(
                    not_fixed_master_ssh_ips, master_node["username"],
                    master_node["password"])
                self._set_node_label(
                    commander, fixed_worker.get('worker_nic_ip'),
                    fixed_worker.get('host_compute'))

    def _check_master_node_param(self, node_info):
        if node_info is None:
            msg = 'master_node is not defined in additionalParams.'
            raise Exception(msg)

        params = ["vdu_id", "ssh_cp_name", "nic_cp_name", "username",
                  "password", "cluster_cp_name"]
        for param in params:
            if node_info.get(param) is None:
                msg = (f'master_node {param} is not defined in '
                       f'additionalParams.')
                raise Exception(msg)

        pod_cidr = node_info.get('pod_cidr')
        # check pod_cidr's value
        if pod_cidr:
            if not self._check_is_cidr(pod_cidr):
                msg = 'The pod_cidr in the additionalParams is invalid.'
                raise Exception(msg)
        else:
            node_info['pod_cidr'] = '10.0.0.0/8'

        cluster_cidr = node_info.get('cluster_cidr')
        # check cluster_cidr's value
        if cluster_cidr:
            if not self._check_is_cidr(cluster_cidr):
                msg = 'The cluster_cidr in the additionalParams is invalid.'
                raise Exception(msg)
        else:
            node_info['cluster_cidr'] = '10.96.0.0/12'

    def _check_worker_node_param(self, node_info):
        if node_info is None:
            msg = 'worker_node is not defined in additionalParams.'
            raise Exception(msg)

        params = ["vdu_id", "ssh_cp_name", "nic_cp_name", "username",
                  "password"]
        for param in params:
            if node_info.get(param) is None:
                msg = (f'worker_node {param} is not defined in '
                       f'additionalParams.')
                raise Exception(msg)

    def instantiate_start(self):
        pass

    def instantiate_end(self):
        k8s_install_params = self.req.get('additionalParams').get(
            'k8s_cluster_installation_param', {})
        script_path = k8s_install_params.get('script_path')
        if script_path is None:
            msg = 'The script_path in the additionalParams is invalid.'
            raise Exception(msg)

        master_node = k8s_install_params.get('master_node')
        # Check master_node parameter
        self._check_master_node_param(master_node)

        worker_node = k8s_install_params.get('worker_node')
        # Check worker_node parameter
        self._check_worker_node_param(worker_node)

        # get stack_id
        nest_stack_id = self._get_stack_id()

        master_vm_dict_list = self._get_install_info_for_k8s_node(
            nest_stack_id, master_node, 'master')
        worker_vm_dict_list = self._get_install_info_for_k8s_node(
            nest_stack_id, worker_node, 'worker')
        server, bearer_token, ssl_ca_cert = \
            self._install_k8s_cluster(
                script_path, master_vm_dict_list, worker_vm_dict_list)

    def terminate_start(self):
        pass

    def terminate_end(self):
        pass

    def scale_start(self):
        if self.req['type'] == 'SCALE_OUT':
            return
        master_node = self.req.get('additionalParams').get(
            'k8s_cluster_installation_param', {}).get('master_node')
        # Check master_node parameter
        self._check_master_node_param(master_node)

        worker_node = self.req.get('additionalParams').get(
            'k8s_cluster_installation_param', {}).get('worker_node')
        # Check worker_node parameter
        self._check_worker_node_param(worker_node)

        master_username, master_password = self._get_user_info(master_node)
        worker_username, worker_password = self._get_user_info(worker_node)

        vnfcs = self._get_vnfcs(master_node['vdu_id'])
        master_ip_list = []
        for vnfc in vnfcs:
            stack_id = vnfc['metadata']['stack_id']
            ssh_ip = self._get_ssh_ip(stack_id, master_node['ssh_cp_name'])
            master_ip_list.append(ssh_ip)

        commander, master_ip = self._connect_ssh_scale(
            master_ip_list, master_username, master_password)

        scale_in_ids = [res_def.get('resource', {}).get('resourceId')
                        for res_def in self.grant_req.get('removeResources')
                        if res_def.get('type') == 'COMPUTE']

        scale_worker_nic_ips, normal_worker_ssh_ips = \
            self._delete_scale_in_worker(worker_node, scale_in_ids, commander)
        commander.close_session()

        # modify /etc/hosts/ on each node
        for master_ip in master_ip_list:
            commander = self._init_commander_and_send_install_scripts(
                master_username, master_password, master_ip)
            self._set_node_ip_in_hosts(
                commander, 'scale_in', scale_worker_nic_ips)
            commander.close_session()
        for worker_ip in normal_worker_ssh_ips:
            commander = self._init_commander_and_send_install_scripts(
                worker_username, worker_password, worker_ip)
            self._set_node_ip_in_hosts(
                commander, 'scale_in', scale_worker_nic_ips)
            commander.close_session()

    def scale_end(self):
        if self.req.get('type') == 'SCALE_IN':
            return
        k8s_install_params = self.req.get('additionalParams', {}).get(
            'k8s_cluster_installation_param', {})
        nest_stack_id = self._get_stack_id()

        master_node = k8s_install_params.get('master_node')
        # Check master_node parameter
        self._check_master_node_param(master_node)

        worker_node = k8s_install_params.get('worker_node')
        # Check worker_node parameter
        self._check_worker_node_param(worker_node)

        master_username, master_password = self._get_user_info(master_node)
        worker_username, worker_password = self._get_user_info(worker_node)

        # get scale_out num
        res_def = [res_def
                   for res_def in self.grant_req.get('addResources', {})
                   if res_def.get('type') == 'COMPUTE']
        vnfcs = self._get_vnfcs(worker_node['vdu_id'])
        scale_out_ids = [vnfc['id'] for vnfc in vnfcs[0:len(res_def)]]

        # get master_ip
        master_ssh_ip_list = []
        master_nic_ip_list = []

        # get master ssh_ip and nic_ip
        vnfcs = self._get_vnfcs(master_node['vdu_id'])
        for vnfc in vnfcs:
            stack_id = vnfc['metadata']['stack_id']
            ssh_ip = self._get_ssh_ip(stack_id, master_node['ssh_cp_name'])
            nic_ip = self._get_nic_ip(stack_id, master_node['nic_cp_name'])
            master_ssh_ip_list.append(ssh_ip)
            master_nic_ip_list.append(nic_ip)

        if len(master_ssh_ip_list) > 1:
            stack_id = nest_stack_id
        else:
            stack_id = vnfcs[0]['metadata']['stack_id']
        cluster_ip = self._get_nic_ip(stack_id,
                                      master_node['cluster_cp_name'])
        (add_worker_ssh_ip_list, add_worker_nic_ip_list,
         normal_ssh_worker_ip_list, normal_nic_worker_ip_list,
         host_compute_dict) = \
            self._get_worker_info(worker_node, scale_out_ids)

        # get kubeadm_token from one of master node
        commander, master_ip = self._connect_ssh_scale(
            master_ssh_ip_list, master_username, master_password)
        ssh_command = "kubeadm token create;"
        kubeadm_token = self._execute_command(
            commander, ssh_command,
            K8S_CMD_TIMEOUT, 'common', 3)[0].replace('\n', '')

        # get hash from one of master node
        ssh_command = "openssl x509 -pubkey -in " \
                      "/etc/kubernetes/pki/ca.crt | openssl rsa " \
                      "-pubin -outform der 2>/dev/null | " \
                      "openssl dgst -sha256 -hex | sed 's/^.* //';"
        ssl_ca_cert_hash = self._execute_command(
            commander, ssh_command,
            K8S_CMD_TIMEOUT, 'common', 3)[0].replace('\n', '')
        commander.close_session()

        # set /etc/hosts
        master_hosts = [master_ip + ' master' + master_ip.split('.')[-1]
                        for master_ip in master_nic_ip_list]
        add_worker_hosts = [worker_ip + ' worker' + worker_ip.split('.')[-1]
                            for worker_ip in add_worker_nic_ip_list]
        normal_worker_hosts = [worker_ip + ' worker' + worker_ip.split('.')[-1]
                               for worker_ip in normal_nic_worker_ip_list]

        ha_flag = True
        if len(master_nic_ip_list) == 1:
            ha_flag = False

        script_path = k8s_install_params['script_path']
        for worker_ip in add_worker_ssh_ip_list:
            commander = self._init_commander_and_send_install_scripts(
                worker_username, worker_password,
                worker_ip, self.csar_dir, script_path)
            hosts_str = '\\n'.join(
                master_hosts + add_worker_hosts + normal_worker_hosts)
            self._set_node_ip_in_hosts(commander,
                                       'scale_out', hosts_str=hosts_str)
            worker_nic_ip = add_worker_nic_ip_list[
                add_worker_ssh_ip_list.index(worker_ip)]
            self._install_worker_node(
                commander, ha_flag, worker_nic_ip, cluster_ip,
                kubeadm_token, ssl_ca_cert_hash)
            commander.close_session()

            # Set worker node labels
            commander, _ = self._connect_ssh_scale(
                master_ssh_ip_list, master_username, master_password)
            self._set_node_label(
                commander, worker_nic_ip, host_compute_dict[worker_nic_ip])
            commander.close_session()

        commander, _ = self._connect_ssh_scale(
            master_ssh_ip_list, master_username, master_password)
        self._check_cilium_status(commander)
        commander.close_session()

        hosts_str = '\\n'.join(add_worker_hosts)
        # set /etc/hosts on master node and normal worker node
        for master_ip in master_ssh_ip_list:
            commander = self._init_commander_and_send_install_scripts(
                worker_username, worker_password, master_ip)
            self._set_node_ip_in_hosts(
                commander, 'scale_out', hosts_str=hosts_str)
            commander.close_session()
        for worker_ip in normal_ssh_worker_ip_list:
            commander = self._init_commander_and_send_install_scripts(
                worker_username, worker_password, worker_ip)
            self._set_node_ip_in_hosts(
                commander, 'scale_out', hosts_str=hosts_str)
            commander.close_session()

    def heal_start(self):
        stack_id = self._get_stack_id()
        k8s_install_params = self.req.get('additionalParams', {}).get(
            'k8s_cluster_installation_param', {})
        master_node = k8s_install_params.get('master_node')
        # Check master_node parameter
        self._check_master_node_param(master_node)

        worker_node = k8s_install_params.get('worker_node')
        # Check worker_node parameter
        self._check_worker_node_param(worker_node)

        master_username, master_password = self._get_user_info(master_node)

        if self.req.get('vnfcInstanceId') is not None:
            heal_ids = [res_def.get('resource', {}).get('resourceId')
                        for res_def in self.grant_req.get('removeResources')
                        if res_def.get('type') == 'COMPUTE']
            if heal_ids:
                self._delete_node(stack_id, heal_ids, master_username,
                                  master_password, master_node, worker_node)

    def heal_end(self):
        k8s_install_params = self.req.get('additionalParams', {}).get(
            'k8s_cluster_installation_param', {})
        master_node = k8s_install_params.get('master_node')
        # Check master_node parameter
        self._check_master_node_param(master_node)

        worker_node = k8s_install_params.get('worker_node')
        # Check worker_node parameter
        self._check_worker_node_param(worker_node)

        if self.req.get('vnfcInstanceId') is None:
            self.instantiate_end()
        else:
            stack_id = self._get_stack_id()
            self._join_k8s_node(
                stack_id, k8s_install_params, master_node, worker_node)

    def change_external_connectivity_start(self):
        pass

    def change_external_connectivity_end(self):
        pass

    def modify_information_start(self):
        pass

    def modify_information_end(self):
        pass


def main():
    script_dict = pickle.load(sys.stdin.buffer)

    operation = script_dict['operation']
    req = script_dict['request']
    inst = script_dict['vnf_instance']
    grant_req = script_dict['grant_request']
    grant = script_dict['grant_response']
    csar_dir = script_dict['tmp_csar_dir']

    script = KubernetesMgmtDriver(req, inst, grant_req, grant, csar_dir)
    getattr(script, operation)()


if __name__ == "__main__":
    try:
        main()
        os._exit(0)
    except Exception as ex:
        sys.stderr.write(str(ex))
        sys.stderr.flush()
        os._exit(1)
