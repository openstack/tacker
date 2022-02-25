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

import eventlet
import ipaddress
import json
import os
import re
import time
import yaml

from oslo_log import log as logging
from oslo_utils import uuidutils
import paramiko

from tacker.common import cmd_executer
from tacker.common import exceptions
from tacker.db.db_base import CommonDbMixin
from tacker.db.nfvo import nfvo_db
from tacker.nfvo.nfvo_plugin import NfvoPlugin
from tacker import objects
from tacker.vnflcm import utils as vnflcm_utils
from tacker.vnfm.infra_drivers.openstack import heat_client as hc
from tacker.vnfm.mgmt_drivers import vnflcm_abstract_driver

CHECK_PV_AVAILABLE_RETRY = 5
CHECK_PV_DEL_COMPLETE_RETRY = 5
CONNECT_MASTER_RETRY_TIMES = 4
HELM_CMD_TIMEOUT = 30
HELM_INSTALL_TIMEOUT = 300
HELM_CHART_DIR = "/var/tacker/helm"
HELM_CHART_CMP_PATH = "/tmp/tacker-helm.tgz"
K8S_CMD_TIMEOUT = 30
K8S_INSTALL_TIMEOUT = 2700
LOG = logging.getLogger(__name__)
NFS_CMD_TIMEOUT = 30
NFS_INSTALL_TIMEOUT = 2700
SERVER_WAIT_COMPLETE_TIME = 60

# CLI timeout period when setting private registries connection
PR_CONNECT_TIMEOUT = 30
PR_CMD_TIMEOUT = 300


class KubernetesMgmtDriver(vnflcm_abstract_driver.VnflcmMgmtAbstractDriver):

    def __init__(self):
        self._init_flag()

    def get_type(self):
        return 'mgmt-drivers-kubernetes'

    def get_name(self):
        return 'mgmt-drivers-kubernetes'

    def get_description(self):
        return 'Tacker Kubernetes VNFMgmt Driver'

    def instantiate_start(self, context, vnf_instance,
                          instantiate_vnf_request, grant,
                          grant_request, **kwargs):
        pass

    def _init_flag(self):
        self.FLOATING_IP_FLAG = False
        self.SET_NODE_LABEL_FLAG = False
        self.SET_ZONE_ID_FLAG = False
        self.nfvo_plugin = NfvoPlugin()

    def _check_is_cidr(self, cidr_str):
        # instantiate: check cidr
        try:
            ipaddress.ip_network(cidr_str)
            return True
        except ValueError:
            return False

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
                time.sleep(30)
        if type == 'common' or type == 'etcd':
            err = result.get_stderr()
            if err:
                LOG.error(err)
                raise exceptions.MgmtDriverRemoteCommandError(err_info=err)
        elif type == 'drain':
            for res in result.get_stdout():
                if 'drained' in res:
                    break
            else:
                err = result.get_stderr()
                stdout = result.get_stdout()
                LOG.debug(stdout)
                LOG.debug(err)
        elif type in ('certificate_key', 'install', 'scp'):
            if result.get_return_code() != 0:
                err = result.get_stderr()
                LOG.error(err)
                raise exceptions.MgmtDriverRemoteCommandError(err_info=err)
        elif type == 'docker_login':
            ret1 = result.get_stdout()
            ret2 = result.get_stderr()
            return ret1, ret2
        elif type == 'helm_repo_list':
            if result.get_return_code() != 0:
                err = result.get_stderr()[0].replace('\n', '')
                if err == 'Error: no repositories to show':
                    return []
                raise exceptions.MgmtDriverRemoteCommandError(err_info=err)
        elif type == 'check_node':
            err = result.get_stderr()
            if result.get_return_code() == 0:
                pass
            elif (result.get_return_code() != 0 and
                  "kubectl: command not found" in err):
                return "False"
            else:
                LOG.error(err)
                raise exceptions.MgmtDriverRemoteCommandError(err_info=err)
        return result.get_stdout()

    def _create_vim(self, context, vnf_instance, server, bearer_token,
                    ssl_ca_cert, vim_name, project_name, master_vm_dict_list,
                    masternode_ip_list):
        # ha: create vim
        vim_info = {
            'vim': {
                'name': vim_name,
                'auth_url': server,
                'vim_project': {
                    'name': project_name
                },
                'auth_cred': {
                    'bearer_token': bearer_token,
                    'ssl_ca_cert': ssl_ca_cert
                },
                'type': 'kubernetes',
                'tenant_id': context.project_id
            }
        }
        if self.FLOATING_IP_FLAG:
            if not master_vm_dict_list[0].get(
                    'k8s_cluster', {}).get('cluster_fip'):
                register_ip = master_vm_dict_list[0].get('ssh').get('ipaddr')
            else:
                register_ip = master_vm_dict_list[0].get(
                    'k8s_cluster', {}).get('cluster_fip')
            server = re.sub(r'(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})',
                            register_ip, server)
            vim_info['vim']['auth_url'] = server
            del vim_info['vim']['auth_cred']['ssl_ca_cert']
        extra = {}
        if masternode_ip_list:
            username = master_vm_dict_list[0].get('ssh').get('username')
            password = master_vm_dict_list[0].get('ssh').get('password')
            helm_info = {
                'masternode_ip': masternode_ip_list,
                'masternode_username': username,
                'masternode_password': password}
            extra['helm_info'] = str(helm_info)
            vim_info['vim']['extra'] = extra

        created_vim_info = self._get_or_create_vim(
            context, vim_name, server, vim_info)

        id = uuidutils.generate_uuid()
        vim_id = created_vim_info.get('id')
        vim_type = 'kubernetes'
        access_info = {
            'auth_url': server
        }
        vim_connection_info = objects.VimConnectionInfo(
            id=id, vim_id=vim_id, vim_type=vim_type,
            access_info=access_info, interface_info=None, extra=extra
        )
        vim_connection_infos = vnf_instance.vim_connection_info
        vim_connection_infos.append(vim_connection_info)
        vnf_instance.vim_connection_info = vim_connection_infos
        vnf_instance.save()

    def _get_or_create_vim(
            self, context, vim_name, server, create_vim_info):
        created_vim_info = self._get_vim_by_name(context, vim_name)
        if created_vim_info:
            vim_info = self.nfvo_plugin.get_vim(
                context, created_vim_info.id)
            if (vim_info['auth_url'] == server and
                    vim_info['status'] == 'REACHABLE'):
                return vim_info
        try:
            return self.nfvo_plugin.create_vim(context, create_vim_info)
        except Exception as e:
            LOG.error(f"Failed to register kubernetes vim: {e}")
            raise exceptions.MgmtDriverOtherError(
                error_message="Failed to register "
                              f"kubernetes vim: {e}")

    def _get_ha_group_resources_list(
            self, heatclient, stack_id, node, additional_params):
        # ha: get group resources list
        nest_resources_list = heatclient.resources.list(stack_id=stack_id)
        group_stack_name = node.get("aspect_id")
        group_stack_id = ""
        for nest_resources in nest_resources_list:
            if nest_resources.resource_name == group_stack_name:
                group_stack_id = nest_resources.physical_resource_id
        if not group_stack_id:
            LOG.error('No stack id matching the group was found.')
            raise exceptions.MgmtDriverOtherError(
                error_message="No stack id matching the group was found")
        group_resources_list = heatclient.resources.list(
            stack_id=group_stack_id)
        return group_resources_list

    def _get_cluster_ip(self, heatclient, resource_num,
                        node, stack_id, nest_stack_id):
        cluster_cp_name = node.get('cluster_cp_name')
        if not node.get('aspect_id'):
            # num_master_node = 1, type=OS::Nova::Server
            cluster_ip = heatclient.resources.get(
                stack_id=nest_stack_id,
                resource_name=cluster_cp_name).attributes.get(
                'fixed_ips')[0].get('ip_address')
        else:
            # num_master_node > 1, type=OS::Heat::AutoScalingGroup
            if resource_num > 1:
                cluster_ip = heatclient.resources.get(
                    stack_id=nest_stack_id,
                    resource_name=cluster_cp_name).attributes.get(
                    'fixed_ips')[0].get('ip_address')
            # num_master_node = 1, type=OS::Heat::AutoScalingGroup
            else:
                cluster_ip = heatclient.resources.get(
                    stack_id=stack_id,
                    resource_name=cluster_cp_name).attributes.get(
                    'fixed_ips')[0].get('ip_address')
        if not cluster_ip:
            LOG.error('Failed to get the cluster ip.')
            raise exceptions.MgmtDriverOtherError(
                error_message="Failed to get the cluster ip")
        return cluster_ip

    def _get_zone_id_from_grant(self, vnf_instance, grant, operation_type,
                                physical_resource_id):
        zone_id = ''
        for vnfc_resource in \
                vnf_instance.instantiated_vnf_info.vnfc_resource_info:
            if physical_resource_id == \
                    vnfc_resource.compute_resource.resource_id:
                vnfc_id = vnfc_resource.id
                break
        if not vnfc_id:
            msg = 'Failed to find Vnfc Resource related ' \
                  'to this physical_resource_id {}.'.format(
                      physical_resource_id)
            LOG.error(msg)
            raise exceptions.MgmtDriverOtherError(
                error_message=msg)

        if operation_type == 'HEAL':
            resources = grant.update_resources
        else:
            resources = grant.add_resources

        for resource in resources:
            if vnfc_id == resource.resource_definition_id:
                add_resource_zone_id = resource.zone_id
                break
        if not add_resource_zone_id:
            msg = 'Failed to find specified zone id' \
                  ' related to Vnfc Resource {} in grant'.format(
                      vnfc_id)
            LOG.warning(msg)
        else:
            for zone in grant.zones:
                if add_resource_zone_id == zone.id:
                    zone_id = zone.zone_id
                    break

        return zone_id

    def _get_pod_affinity_info(self, heatclient, nest_stack_id, stack_id,
                               vnf_instance, grant):
        zone_id = ''
        host_compute = ''
        srv_grp_phy_res_id_list = []
        nest_resources_list = heatclient.resources.list(
            stack_id=nest_stack_id)
        for nest_res in nest_resources_list:
            if nest_res.resource_type == 'OS::Nova::ServerGroup':
                pod_affinity_res_info = heatclient.resources.get(
                    stack_id=nest_stack_id,
                    resource_name=nest_res.resource_name)
                srv_grp_policies = pod_affinity_res_info.attributes.get(
                    'policy')
                if srv_grp_policies and srv_grp_policies == 'anti-affinity':
                    srv_grp_phy_res_id_list.append(
                        pod_affinity_res_info.physical_resource_id)
        lowest_res_list = heatclient.resources.list(stack_id=stack_id)
        for lowest_res in lowest_res_list:
            if lowest_res.resource_type == 'OS::Nova::Server':
                lowest_res_name = lowest_res.resource_name
                worker_node_res_info = heatclient.resources.get(
                    stack_id=stack_id, resource_name=lowest_res_name)
                srv_groups = worker_node_res_info.attributes.get(
                    'server_groups')
                srv_grp_phy_res_id = set(
                    srv_grp_phy_res_id_list) & set(srv_groups)
                if srv_grp_phy_res_id:
                    host_compute = worker_node_res_info.attributes.get(
                        'OS-EXT-SRV-ATTR:host')
                    if self.SET_ZONE_ID_FLAG:
                        phy_res_id = worker_node_res_info.physical_resource_id
                        zone_id = self._get_zone_id_from_grant(
                            vnf_instance, grant, 'INSTANTIATE', phy_res_id)
        return host_compute, zone_id

    def _get_install_info_for_k8s_node(self, nest_stack_id, node,
                                       additional_params, role,
                                       access_info, vnf_instance, grant):
        # instantiate: get k8s ssh ips
        vm_dict_list = []
        stack_id = ''
        zone_id = ''
        host_compute = ''
        heatclient = hc.HeatClient(access_info)

        # get ssh_ip and nic_ip and set ssh's values
        if not node.get('aspect_id'):
            ssh_ip = heatclient.resources.get(
                stack_id=nest_stack_id,
                resource_name=node.get('ssh_cp_name')).attributes.get(
                    'fixed_ips')[0].get('ip_address')
            nic_ip = heatclient.resources.get(
                stack_id=nest_stack_id,
                resource_name=node.get('nic_cp_name')).attributes.get(
                    'fixed_ips')[0].get('ip_address')
            vm_dict = {
                "ssh": {
                    "username": node.get("username"),
                    "password": node.get("password"),
                    "ipaddr": ssh_ip,
                    "nic_ip": nic_ip
                }
            }
            vm_dict_list.append(vm_dict)
        else:
            group_resources_list = self._get_ha_group_resources_list(
                heatclient, nest_stack_id, node, additional_params)
            for group_resource in group_resources_list:
                stack_id = group_resource.physical_resource_id
                resource_name = node.get('ssh_cp_name')
                resource_info = heatclient.resources.get(
                    stack_id=stack_id,
                    resource_name=resource_name)
                if resource_info.attributes.get('floating_ip_address'):
                    self.FLOATING_IP_FLAG = True
                    ssh_ip = resource_info.attributes.get(
                        'floating_ip_address')
                    nic_ip = heatclient.resources.get(
                        stack_id=stack_id,
                        resource_name=node.get('nic_cp_name')).attributes.get(
                        'fixed_ips')[0].get('ip_address')
                else:
                    ssh_ip = heatclient.resources.get(
                        stack_id=stack_id,
                        resource_name=resource_name).attributes.get(
                        'fixed_ips')[0].get('ip_address')
                    nic_ip = heatclient.resources.get(
                        stack_id=stack_id,
                        resource_name=node.get('nic_cp_name')).attributes.get(
                        'fixed_ips')[0].get('ip_address')
                if role == 'worker':
                    # get pod_affinity info
                    host_compute, zone_id = self._get_pod_affinity_info(
                        heatclient, nest_stack_id, stack_id,
                        vnf_instance, grant)
                vm_dict_list.append({
                    "host_compute": host_compute,
                    "zone_id": zone_id,
                    "ssh": {
                        "username": node.get("username"),
                        "password": node.get("password"),
                        "ipaddr": ssh_ip,
                        "nic_ip": nic_ip
                    }
                })

        # get cluster_ip from master node
        if role == 'master':
            cluster_fip = ''
            resource_num = len(vm_dict_list)
            cluster_ip = self._get_cluster_ip(heatclient,
                resource_num, node, stack_id, nest_stack_id)
            if self.FLOATING_IP_FLAG and len(vm_dict_list) > 1:
                cluster_fip = heatclient.resource_get(
                    nest_stack_id,
                    node.get('cluster_fip_name')).attributes.get(
                        'floating_ip_address')

            # set k8s_cluster's values
            for vm_dict in vm_dict_list:
                vm_dict["k8s_cluster"] = {
                    "pod_cidr": node.get('pod_cidr'),
                    "cluster_cidr": node.get('cluster_cidr'),
                    "ipaddr": cluster_ip,
                    "cluster_fip": cluster_fip
                }
        return vm_dict_list

    def _get_hosts(self, master_vm_dict_list, worker_vm_dict_list):
        # merge /etc/hosts
        hosts = []
        for master_vm_dict in master_vm_dict_list:
            hosts_master_ip = master_vm_dict.get('ssh', ()).get('nic_ip')
            hosts.append(hosts_master_ip + ' ' + 'master' +
                         hosts_master_ip.split('.')[-1])
        for worker_vm_dict in worker_vm_dict_list:
            hosts_worker_ip = worker_vm_dict.get('ssh', ()).get('nic_ip')
            hosts.append(hosts_worker_ip + ' ' + 'worker' +
                         hosts_worker_ip.split('.')[-1])
        hosts_str = '\\n'.join(hosts)
        return hosts_str

    def _init_commander_and_send_install_scripts(self, user, password, host,
                        vnf_package_path=None, script_path=None,
                        helm_inst_script_path=None):
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
                        "../../../samples/mgmt_driver/kubernetes/"
                        "create_admin_token.yaml"),
                        "/tmp/create_admin_token.yaml")
                    if helm_inst_script_path:
                        sftp.put(os.path.join(
                            vnf_package_path, helm_inst_script_path),
                            "/tmp/install_helm.sh")
                    connect.close()
                commander = cmd_executer.RemoteCommandExecutor(
                    user=user, password=password, host=host,
                    timeout=K8S_INSTALL_TIMEOUT)
                return commander
            except paramiko.SSHException as e:
                LOG.debug(e)
                retry -= 1
                if retry == 0:
                    LOG.error(e)
                    raise paramiko.SSHException()
                time.sleep(SERVER_WAIT_COMPLETE_TIME)

    def _init_commander(self, user, password, host, retry=4):
        while retry > 0:
            try:
                commander = cmd_executer.RemoteCommandExecutor(
                    user=user, password=password, host=host,
                    timeout=K8S_INSTALL_TIMEOUT)
                return commander
            except Exception as e:
                LOG.debug(e)
                retry -= 1
                if retry == 0:
                    LOG.error(e)
                    raise
                time.sleep(SERVER_WAIT_COMPLETE_TIME)

    def _get_vm_cidr_list(self, master_ip, proxy):
        # ha and scale: get vm cidr list
        vm_cidr_list = []
        if proxy.get('k8s_node_cidr'):
            cidr = proxy.get('k8s_node_cidr')
        else:
            cidr = master_ip + '/24'
        network_ips = ipaddress.ip_network(cidr, False)
        for network_ip in network_ips:
            vm_cidr_list.append(str(network_ip))
        return vm_cidr_list

    def _install_worker_node(self, commander, proxy,
                             ha_flag, nic_ip, cluster_ip, kubeadm_token,
                             ssl_ca_cert_hash, http_private_registries):
        if proxy.get('http_proxy') and proxy.get('https_proxy'):
            ssh_command = \
                "export http_proxy={http_proxy};" \
                "export https_proxy={https_proxy};" \
                "export no_proxy={no_proxy};" \
                "export ha_flag={ha_flag};" \
                "bash /tmp/install_k8s_cluster.sh " \
                "-w {worker_ip} -i {cluster_ip} " \
                "-t {kubeadm_token} -s {ssl_ca_cert_hash}".format(
                    http_proxy=proxy.get('http_proxy'),
                    https_proxy=proxy.get('https_proxy'),
                    no_proxy=proxy.get('no_proxy'),
                    ha_flag=ha_flag,
                    worker_ip=nic_ip, cluster_ip=cluster_ip,
                    kubeadm_token=kubeadm_token,
                    ssl_ca_cert_hash=ssl_ca_cert_hash)
        else:
            ssh_command = \
                "export ha_flag={ha_flag};" \
                "bash /tmp/install_k8s_cluster.sh " \
                "-w {worker_ip} -i {cluster_ip} " \
                "-t {kubeadm_token} -s {ssl_ca_cert_hash}".format(
                    ha_flag=ha_flag,
                    worker_ip=nic_ip, cluster_ip=cluster_ip,
                    kubeadm_token=kubeadm_token,
                    ssl_ca_cert_hash=ssl_ca_cert_hash)

        # if connecting to the private registries over HTTP,
        # add "export HTTP_PRIVATE_REGISTRIES" command
        if http_private_registries:
            ssh_command = "export HTTP_PRIVATE_REGISTRIES=\"{}\";{}".format(
                http_private_registries, ssh_command)

        self._execute_command(
            commander, ssh_command, K8S_INSTALL_TIMEOUT, 'install', 0)

    def _install_helm(self, commander, proxy):
        ssh_command = ""
        if proxy.get("http_proxy") and proxy.get("https_proxy"):
            ssh_command += ("export http_proxy={http_proxy}; "
                            "export https_proxy={https_proxy}; "
                            "export no_proxy={no_proxy}; ").format(
                                http_proxy=proxy.get('http_proxy'),
                                https_proxy=proxy.get('https_proxy'),
                                no_proxy=proxy.get('no_proxy'))
        ssh_command += "bash /tmp/install_helm.sh;"
        self._execute_command(
            commander, ssh_command, HELM_INSTALL_TIMEOUT, 'install', 0)

    def _set_node_label(self, commander, nic_ip, host_compute, zone_id):
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
        worker_host_name = 'worker' + nic_ip.split('.')[3]
        if host_compute:
            ssh_command = "kubectl label nodes {worker_host_name}" \
                          " CIS-node={host_compute}".format(
                              worker_host_name=worker_host_name,
                              host_compute=host_compute)
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
        if zone_id:
            ssh_command = "kubectl label nodes {worker_host_name}" \
                          " kubernetes.io/zone={zone_id}".format(
                              worker_host_name=worker_host_name,
                              zone_id=zone_id)
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
            commander.close_session()

    def _get_http_private_registries(self, pr_connection_info):
        http_private_registries = ""
        if pr_connection_info:
            http_pr_list = []
            for pr_info in pr_connection_info:
                pr_connection_type = str(pr_info.get('connection_type'))
                pr_server = pr_info.get('server')
                # NOTE: "connection_type" values are "0" for HTTP and
                #       "1" for HTTPS.
                if pr_connection_type == "0":
                    http_pr_list.append("\\\"" + pr_server + "\\\"")
            if http_pr_list:
                http_private_registries = ",".join(http_pr_list)
        return http_private_registries

    def _connect_to_private_registries(self, vnf_package_path,
                                       pr_connection_info, node_username,
                                       node_password, node_ip):
        LOG.debug("Start the _connect_to_private_registries function. "
            "node ip: {}, pr connection info: {}".format(
                node_ip, pr_connection_info))

        commander = cmd_executer.RemoteCommandExecutor(
            user=node_username, password=node_password,
            host=node_ip, timeout=PR_CONNECT_TIMEOUT)

        # create a cert file list for file transfer
        cert_file_list = []
        for pr_info in pr_connection_info:
            pr_certificate_path = pr_info.get('certificate_path')
            if pr_certificate_path:
                local_file_path = os.path.join(
                    vnf_package_path, pr_certificate_path)
                # check existence of cert file
                if not os.path.exists(local_file_path):
                    err_param = "certificate_path(path:{})".format(
                        pr_certificate_path)
                    LOG.error("The {} in the additionalParams is invalid. "
                              "File does not exist.".format(err_param))
                    commander.close_session()
                    raise exceptions.MgmtDriverParamInvalid(param=err_param)
                cert_file_name = os.path.basename(pr_certificate_path)
                remote_tmp_path = os.path.join("/tmp", cert_file_name)
                remote_dir_path = os.path.join(
                    "/etc/docker/certs.d", pr_info.get('server'))
                remote_file_path = os.path.join(
                    remote_dir_path, cert_file_name)
                cert_file_list.append((local_file_path, remote_tmp_path,
                    remote_dir_path, remote_file_path))

        # send cert files to node
        if cert_file_list:
            retry = 4
            while retry > 0:
                try:
                    transport = paramiko.Transport(node_ip, 22)
                    transport.connect(
                        username=node_username, password=node_password)
                    sftp_client = paramiko.SFTPClient.from_transport(
                        transport)
                    for cert_item in cert_file_list:
                        local_file_path = cert_item[0]
                        remote_tmp_path = cert_item[1]
                        remote_dir_path = cert_item[2]
                        remote_file_path = cert_item[3]
                        # send cert file to tmp directory
                        sftp_client.put(local_file_path, remote_tmp_path)
                        # copy under /etc/docker/certs.d/<server>
                        ssh_command = ("sudo mkdir -p {} && "
                            "sudo cp {} {} && sudo rm -f {}".format(
                                remote_dir_path, remote_tmp_path,
                                remote_file_path, remote_tmp_path))
                        self._execute_command(
                            commander, ssh_command,
                            PR_CMD_TIMEOUT, 'common', 0)
                    break
                except paramiko.SSHException as e:
                    LOG.debug(e)
                    retry -= 1
                    if retry == 0:
                        LOG.error(e)
                        commander.close_session()
                        raise paramiko.SSHException()
                    time.sleep(SERVER_WAIT_COMPLETE_TIME)
                except (exceptions.MgmtDriverOtherError,
                        exceptions.MgmtDriverRemoteCommandError) as ex:
                    LOG.error(ex)
                    commander.close_session()
                    raise ex
                finally:
                    transport.close()

        # connect to private registries
        for pr_info in pr_connection_info:
            # add host to /etc/hosts
            pr_hosts_string = pr_info.get('hosts_string')
            if pr_hosts_string:
                ssh_command = ("echo '{}' | sudo tee -a /etc/hosts "
                    ">/dev/null".format(pr_hosts_string))
                self._execute_command(
                    commander, ssh_command, PR_CMD_TIMEOUT, 'common', 0)

            # connect to private registry (run docker login)
            pr_server = pr_info.get('server')
            login_username = pr_info.get('username', 'tacker')
            login_password = pr_info.get('password', 'tacker')
            ssh_command = ("sudo docker login {} "
                "--username {} --password {}".format(
                    pr_server, login_username, login_password))
            result = self._execute_command(
                commander, ssh_command, PR_CMD_TIMEOUT, 'docker_login', 0)
            stdout = result[0]
            login_successful = (
                [line for line in stdout if "Login Succeeded" in line])
            if not login_successful:
                # Login Failed
                stderr = result[1]
                unnecessary_msg = "WARNING! Using --password via the CLI"
                err_info = (
                    [line for line in stderr if not(unnecessary_msg in line)])
                err_msg = ("Failed to login Docker private registry. "
                    "ErrInfo:{}".format(err_info))
                LOG.error(err_msg)
                commander.close_session()
                raise exceptions.MgmtDriverOtherError(error_message=err_msg)

        commander.close_session()
        LOG.debug("_connect_to_private_registries function complete.")

    def _is_master_installed(self, vm_dict):
        nic_ip = vm_dict['ssh']['nic_ip']
        master_name = 'master' + nic_ip.split('.')[-1]
        user = vm_dict.get('ssh', {}).get('username')
        password = vm_dict.get('ssh', {}).get('password')
        host = vm_dict.get('ssh', {}).get('ipaddr')
        commander = cmd_executer.RemoteCommandExecutor(
            user=user, password=password,
            host=host, timeout=K8S_CMD_TIMEOUT)
        ssh_command = f"kubectl get node | grep {master_name}"
        result = self._execute_command(commander, ssh_command,
                                       K8S_CMD_TIMEOUT, 'check_node', 0)
        if result != "False":
            for res in result:
                if res.split(' ')[0].strip() == master_name:
                    return True
        return False

    def _install_k8s_cluster(self, context, vnf_instance,
                             proxy, script_path,
                             master_vm_dict_list, worker_vm_dict_list,
                             helm_inst_script_path, pr_connection_info):
        # instantiate: pre /etc/hosts
        hosts_str = self._get_hosts(
            master_vm_dict_list, worker_vm_dict_list)
        master_ssh_ips_str = ','.join([
            vm_dict.get('ssh', {}).get('nic_ip')
            for vm_dict in master_vm_dict_list])
        ha_flag = "True"
        if ',' not in master_ssh_ips_str:
            ha_flag = "False"

        # get vnf package path and check script_path
        vnf_package_path = vnflcm_utils._get_vnf_package_path(
            context, vnf_instance.vnfd_id)
        abs_script_path = os.path.join(vnf_package_path, script_path)
        if not os.path.exists(abs_script_path):
            LOG.error('The path of install script is invalid.')
            raise exceptions.MgmtDriverOtherError(
                error_message="The path of install script is invalid")

        # check helm install and get helm install script_path
        masternode_ip_list = []
        if helm_inst_script_path:
            abs_helm_inst_script_path = os.path.join(
                vnf_package_path, helm_inst_script_path)
            if not os.path.exists(abs_helm_inst_script_path):
                LOG.error('The path of helm install script is invalid.')
                raise exceptions.MgmtDriverParamInvalid(
                    param='helm_installation_script_path')

        # set no proxy
        project_name = ''
        if proxy.get("http_proxy") and proxy.get("https_proxy"):
            vm_cidr_list = self._get_vm_cidr_list(
                master_ssh_ips_str.split(',')[0], proxy)
            master_cluster_ip = master_vm_dict_list[0].get(
                "k8s_cluster", {}).get('ipaddr')
            pod_cidr = master_vm_dict_list[0].get(
                "k8s_cluster", {}).get("pod_cidr")
            cluster_cidr = master_vm_dict_list[0].get(
                "k8s_cluster", {}).get("cluster_cidr")
            proxy["no_proxy"] = ",".join(list(filter(None, [
                proxy.get("no_proxy"), pod_cidr, cluster_cidr,
                "127.0.0.1", "localhost",
                master_cluster_ip] + vm_cidr_list)))

        # get private registries of type HTTP
        http_private_registries = self._get_http_private_registries(
            pr_connection_info)

        # install k8s
        active_username = ""
        active_password = ""
        active_host = ""
        ssl_ca_cert_hash = ""
        kubeadm_token = ""
        get_node_names = []
        # install master node
        for vm_dict in master_vm_dict_list:

            # check master_node exist in k8s-cluster
            if self._is_master_installed(vm_dict):
                continue

            if vm_dict.get('ssh', {}).get('nic_ip') == \
                    master_ssh_ips_str.split(',')[0]:
                active_username = vm_dict.get('ssh', {}).get('username')
                active_password = vm_dict.get('ssh', {}).get('password')
                active_host = vm_dict.get('ssh', {}).get('ipaddr')
            else:
                # get certificate key from active master node
                commander = cmd_executer.RemoteCommandExecutor(
                    user=active_username, password=active_password,
                    host=active_host, timeout=K8S_CMD_TIMEOUT)
                ssh_command = "sudo kubeadm init phase upload-certs " \
                              "--upload-certs"
                result = self._execute_command(
                    commander, ssh_command,
                    K8S_CMD_TIMEOUT, 'certificate_key', 3)
                certificate_key = result[-1].replace('\n', '')

            user = vm_dict.get('ssh', {}).get('username')
            password = vm_dict.get('ssh', {}).get('password')
            host = vm_dict.get('ssh', {}).get('ipaddr')
            k8s_cluster = vm_dict.get('k8s_cluster', {})
            commander = self._init_commander_and_send_install_scripts(
                user, password, host,
                vnf_package_path, script_path, helm_inst_script_path)

            # set /etc/hosts for each node
            ssh_command = "> /tmp/tmp_hosts"
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
            ssh_command = "cp /etc/hosts /tmp/tmp_hosts"
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
            ssh_command = "sed -i '$a{}' /tmp/tmp_hosts".format(
                hosts_str)
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
            ssh_command = "sudo mv /tmp/tmp_hosts /etc/hosts;"
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)

            # execute install k8s command on VM
            if proxy.get('http_proxy') and proxy.get('https_proxy'):
                if vm_dict.get('ssh', {}).get('nic_ip') == \
                        master_ssh_ips_str.split(',')[0]:
                    ssh_command = \
                        "export http_proxy={http_proxy};" \
                        "export https_proxy={https_proxy};" \
                        "export no_proxy={no_proxy};" \
                        "bash /tmp/install_k8s_cluster.sh " \
                        "-m {master_ip} -i {cluster_ip} " \
                        "-p {pod_cidr} -a {k8s_cluster_cidr}".format(
                            http_proxy=proxy.get('http_proxy'),
                            https_proxy=proxy.get('https_proxy'),
                            no_proxy=proxy.get('no_proxy'),
                            master_ip=master_ssh_ips_str,
                            cluster_ip=k8s_cluster.get("ipaddr"),
                            pod_cidr=k8s_cluster.get('pod_cidr'),
                            k8s_cluster_cidr=k8s_cluster.get('cluster_cidr'))
                else:
                    ssh_command = \
                        "export http_proxy={http_proxy};" \
                        "export https_proxy={https_proxy};" \
                        "export no_proxy={no_proxy};" \
                        "bash /tmp/install_k8s_cluster.sh " \
                        "-m {master_ip} -i {cluster_ip} " \
                        "-p {pod_cidr} -a {k8s_cluster_cidr} " \
                        "-t {kubeadm_token} -s {ssl_ca_cert_hash} " \
                        "-k {certificate_key}".format(
                            http_proxy=proxy.get('http_proxy'),
                            https_proxy=proxy.get('https_proxy'),
                            no_proxy=proxy.get('no_proxy'),
                            master_ip=master_ssh_ips_str,
                            cluster_ip=k8s_cluster.get("ipaddr"),
                            pod_cidr=k8s_cluster.get('pod_cidr'),
                            k8s_cluster_cidr=k8s_cluster.get('cluster_cidr'),
                            kubeadm_token=kubeadm_token,
                            ssl_ca_cert_hash=ssl_ca_cert_hash,
                            certificate_key=certificate_key)
            else:
                if vm_dict.get('ssh', {}).get('nic_ip') == \
                        master_ssh_ips_str.split(',')[0]:
                    ssh_command = \
                        "bash /tmp/install_k8s_cluster.sh " \
                        "-m {master_ip} -i {cluster_ip} " \
                        "-p {pod_cidr} -a {k8s_cluster_cidr}".format(
                            master_ip=master_ssh_ips_str,
                            cluster_ip=k8s_cluster.get("ipaddr"),
                            pod_cidr=k8s_cluster.get('pod_cidr'),
                            k8s_cluster_cidr=k8s_cluster.get('cluster_cidr'))

                else:
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

            # if connecting to the private registries over HTTP,
            # add "export HTTP_PRIVATE_REGISTRIES" command
            if http_private_registries:
                ssh_command = \
                    "export HTTP_PRIVATE_REGISTRIES=\"{}\";{}".format(
                        http_private_registries, ssh_command)

            results = self._execute_command(
                commander, ssh_command, K8S_INSTALL_TIMEOUT, 'install', 0)

            # get install-information from active master node
            if vm_dict.get('ssh', {}).get('nic_ip') == \
                    master_ssh_ips_str.split(',')[0]:
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
                begin_index = results.index('-----BEGIN CERTIFICATE-----\n')
                end_index = results.index('-----END CERTIFICATE-----\n')
                ssl_ca_cert = ''.join(results[begin_index: end_index + 1])
                commander = cmd_executer.RemoteCommandExecutor(
                    user=user, password=password, host=host,
                    timeout=K8S_CMD_TIMEOUT)

                # Check whether the secret already exists
                if not self._has_secret(commander):
                    ssh_command = ("kubectl create -f "
                                   "/tmp/create_admin_token.yaml")
                    self._execute_command(
                        commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
                    time.sleep(30)
                else:
                    ssh_command = "kubectl get node"
                    get_node_names = self._execute_command(
                        commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)

                ssh_command = "kubectl get secret -n kube-system " \
                              "| grep '^admin-token' " \
                              "| awk '{print $1}' " \
                              "| xargs -i kubectl describe secret {} " \
                              "-n kube-system" \
                              "| grep 'token:' | awk '{print $2}'"
                bearer_token = self._execute_command(
                    commander, ssh_command,
                    K8S_CMD_TIMEOUT, 'common', 0)[0].replace('\n', '')
            if helm_inst_script_path:
                self._install_helm(commander, proxy)
                masternode_ip_list.append(host)
            commander.close_session()

            # connect to private registries
            if pr_connection_info:
                self._connect_to_private_registries(
                    vnf_package_path, pr_connection_info,
                    user, password, host)

        # install worker node
        for vm_dict in worker_vm_dict_list:
            user = vm_dict.get('ssh', {}).get('username')
            password = vm_dict.get('ssh', {}).get('password')
            host = vm_dict.get('ssh', {}).get('ipaddr')
            nic_ip = vm_dict.get('ssh', {}).get('nic_ip')
            cluster_ip = master_vm_dict_list[0].get(
                'k8s_cluster', {}).get('ipaddr')
            commander = self._init_commander_and_send_install_scripts(
                user, password, host,
                vnf_package_path, script_path)

            # set /etc/hosts for each node
            ssh_command = "> /tmp/tmp_hosts"
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
            ssh_command = "cp /etc/hosts /tmp/tmp_hosts"
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
            ssh_command = "sed -i '$a{}' /tmp/tmp_hosts".format(
                hosts_str)
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
            ssh_command = "sudo mv /tmp/tmp_hosts /etc/hosts;"
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)

            # execute install k8s command on VM
            for get_node_name in get_node_names:
                if ('worker' + nic_ip.split('.')[-1] ==
                        get_node_name.split(' ')[0]):
                    break
            else:
                self._install_worker_node(
                    commander, proxy, ha_flag, nic_ip,
                    cluster_ip, kubeadm_token, ssl_ca_cert_hash,
                    http_private_registries)
            commander.close_session()

            # connect to private registries
            if pr_connection_info:
                self._connect_to_private_registries(
                    vnf_package_path, pr_connection_info,
                    user, password, host)

            # set pod_affinity
            commander = cmd_executer.RemoteCommandExecutor(
                user=active_username, password=active_password,
                host=active_host, timeout=K8S_CMD_TIMEOUT)
            self._set_node_label(
                commander, nic_ip, vm_dict.get('host_compute'),
                vm_dict.get('zone_id'))

        return (server, bearer_token, ssl_ca_cert, project_name,
                masternode_ip_list)

    def _has_secret(self, commander):
        ssh_command = ("kubectl get secret -n kube-system "
                       "| grep '^admin-token'")
        return self._execute_command(
            commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)

    def _check_values(self, additional_param):
        for key, value in additional_param.items():
            if 'master_node' == key or 'worker_node' == key:
                if not value.get('username'):
                    LOG.error('The username in the '
                              'additionalParams is invalid.')
                    raise exceptions.MgmtDriverNotFound(param='username')
                if not value.get('password'):
                    LOG.error('The password in the '
                              'additionalParams is invalid.')
                    raise exceptions.MgmtDriverNotFound(param='password')
                if not value.get('ssh_cp_name'):
                    LOG.error('The ssh_cp_name in the '
                              'additionalParams is invalid.')
                    raise exceptions.MgmtDriverNotFound(
                        param='ssh_cp_name')
                if 'master_node' == key:
                    if not value.get('cluster_cp_name'):
                        LOG.error('The cluster_cp_name in the '
                                  'additionalParams is invalid.')
                        raise exceptions.MgmtDriverNotFound(
                            param='cluster_cp_name')

    def _get_vim_connection_info(self, context, instantiate_vnf_req):

        vim_info = vnflcm_utils._get_vim(context,
                instantiate_vnf_req.vim_connection_info)

        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        return vim_connection_info

    def _check_ss_installation_params(self, ss_installation_params):
        first_level_keys = ('ssh_cp_name', 'username', 'password')
        for key in first_level_keys:
            if not ss_installation_params.get(key):
                LOG.error(f"The {key} in the ss_installation_params "
                          "does not exist.")
                raise exceptions.MgmtDriverNotFound(
                    param=key)

        cinder_volume_setup_params = \
            ss_installation_params.get('cinder_volume_setup_params')
        cinder_volume_setup_param_keys = ('volume_resource_id', 'mount_to')
        for cinder_volume_setup_param in cinder_volume_setup_params:
            for key in cinder_volume_setup_param_keys:
                if not cinder_volume_setup_param.get(key):
                    LOG.error(f"The {key} in the cinder_volume_setup_params "
                              "does not exist.")
                    raise exceptions.MgmtDriverNotFound(
                        param=key)

        nfs_server_setup_params = \
            ss_installation_params.get('nfs_server_setup_params')
        nfs_server_setup_param_keys = ('export_dir', 'export_to')
        for nfs_server_setup_param in nfs_server_setup_params:
            for key in nfs_server_setup_param_keys:
                if not nfs_server_setup_param.get(key):
                    LOG.error(f"The {key} in the nfs_server_setup_params "
                              "does not exist.")
                    raise exceptions.MgmtDriverNotFound(
                        param=key)

    def _check_pv_registration_params(self, pv_registration_params):
        pv_registration_param_keys = ('pv_manifest_file_path',
                                      'nfs_server_cp')
        for pv_registration_param in pv_registration_params:
            for key in pv_registration_param_keys:
                if not pv_registration_param.get(key):
                    LOG.error(f"The {key} in the pv_registration_params "
                              "does not exist.")
                    raise exceptions.MgmtDriverNotFound(
                        param=key)

    def instantiate_end(self, context, vnf_instance,
                        instantiate_vnf_request, grant,
                        grant_request, **kwargs):
        self._init_flag()
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
        self._check_values(additional_param)
        script_path = additional_param.get('script_path')
        vim_name = additional_param.get('vim_name')
        master_node = additional_param.get('master_node', {})
        worker_node = additional_param.get('worker_node', {})
        proxy = additional_param.get('proxy', {})
        helm_inst_script_path = additional_param.get(
            'helm_installation_script_path', None)
        # check script_path
        if not script_path:
            LOG.error('The script_path in the '
                      'additionalParams is invalid.')
            raise exceptions.MgmtDriverNotFound(param='script_path')
        # get pod_cidr and cluster_cidr
        pod_cidr = additional_param.get('master_node', {}).get('pod_cidr')
        cluster_cidr = additional_param.get(
            'master_node', {}).get('cluster_cidr')
        # check pod_cidr's value
        if pod_cidr:
            if not self._check_is_cidr(pod_cidr):
                LOG.error('The pod_cidr in the '
                          'additionalParams is invalid.')
                raise exceptions.MgmtDriverParamInvalid(param='pod_cidr')
        else:
            additional_param['master_node']['pod_cidr'] = '192.168.0.0/16'
        # check cluster_cidr's value
        if cluster_cidr:
            if not self._check_is_cidr(cluster_cidr):
                LOG.error('The cluster_cidr in the '
                          'additionalParams is invalid.')
                raise exceptions.MgmtDriverParamInvalid(param='cluster_cidr')
        else:
            additional_param['master_node']['cluster_cidr'] = '10.96.0.0/12'

        # check storage_server/pv_registration_params
        ss_installation_params = additional_param.get('storage_server')
        pv_registration_params = \
            additional_param.get('pv_registration_params')
        if ss_installation_params:
            self._check_ss_installation_params(ss_installation_params)
        if pv_registration_params:
            self._check_pv_registration_params(pv_registration_params)

        # get private_registry_connection_info param
        pr_connection_info = additional_param.get(
            'private_registry_connection_info')
        if pr_connection_info:
            # check private_registry_connection_info param
            for pr_info in pr_connection_info:
                pr_connection_type = str(pr_info.get('connection_type', ''))
                pr_server = pr_info.get('server')
                # check connection_type param exists
                if not pr_connection_type:
                    LOG.error("The connection_type "
                              "in the additionalParams does not exist.")
                    raise exceptions.MgmtDriverNotFound(
                        param="connection_type")
                # check server param exists
                if not pr_server:
                    LOG.error("The server "
                              "in the additionalParams does not exist.")
                    raise exceptions.MgmtDriverNotFound(param="server")
                # check connection_type value
                # NOTE: "connection_type" values are "0" for HTTP and
                #       "1" for HTTPS.
                if not (pr_connection_type == "0"
                        or pr_connection_type == "1"):
                    LOG.error("The connection_type "
                              "in the additionalParams is invalid.")
                    raise exceptions.MgmtDriverParamInvalid(
                        param="connection_type")

        # check grants exists
        if grant:
            self.SET_ZONE_ID_FLAG = True
        # get stack_id
        nest_stack_id = vnf_instance.instantiated_vnf_info.instance_id
        # set vim_name
        if not vim_name:
            vim_name = 'kubernetes_vim_' + vnf_instance.id

        # get vm list
        access_info = vim_connection_info.access_info
        master_vm_dict_list = \
            self._get_install_info_for_k8s_node(
                nest_stack_id, master_node,
                instantiate_vnf_request.additional_params,
                'master', access_info, vnf_instance, grant)
        worker_vm_dict_list = self._get_install_info_for_k8s_node(
            nest_stack_id, worker_node,
            instantiate_vnf_request.additional_params, 'worker',
            access_info, vnf_instance, grant)
        server, bearer_token, ssl_ca_cert, project_name, masternode_ip_list = \
            self._install_k8s_cluster(context, vnf_instance,
                                      proxy, script_path,
                                      master_vm_dict_list,
                                      worker_vm_dict_list,
                                      helm_inst_script_path,
                                      pr_connection_info)

        if ss_installation_params:
            self._install_storage_server(context, vnf_instance, proxy,
                                         ss_installation_params)
            for vm_dict in master_vm_dict_list + worker_vm_dict_list:
                self._install_nfs_client(
                    vm_dict.get('ssh', {}).get('username'),
                    vm_dict.get('ssh', {}).get('password'),
                    vm_dict.get('ssh', {}).get('ipaddr'))
            commander, master_vm_dict = \
                self._get_connect_master(master_vm_dict_list)
            self._register_persistent_volumes(
                context, vnf_instance, commander,
                master_vm_dict.get('ssh', {}).get('username'),
                master_vm_dict.get('ssh', {}).get('password'),
                master_vm_dict.get('ssh', {}).get('ipaddr'),
                pv_registration_params)

        # register vim with kubernetes cluster info
        self._create_vim(context, vnf_instance, server,
                         bearer_token, ssl_ca_cert, vim_name, project_name,
                         master_vm_dict_list, masternode_ip_list)

    def _get_connect_master(self, master_vm_dict_list):
        for vm_dict in master_vm_dict_list:
            retry = CONNECT_MASTER_RETRY_TIMES
            while retry > 0:
                try:
                    commander = cmd_executer.RemoteCommandExecutor(
                        user=vm_dict.get('ssh', {}).get('username'),
                        password=vm_dict.get('ssh', {}).get('password'),
                        host=vm_dict.get('ssh', {}).get('ipaddr'),
                        timeout=K8S_CMD_TIMEOUT)
                    return commander, vm_dict
                except (exceptions.NotAuthorized, paramiko.SSHException,
                        paramiko.ssh_exception.NoValidConnectionsError) as e:
                    LOG.debug(e)
                    retry -= 1
                    time.sleep(SERVER_WAIT_COMPLETE_TIME)
        else:
            LOG.error('Failed to execute remote command.')
            raise exceptions.MgmtDriverRemoteCommandError()

    def terminate_start(self, context, vnf_instance,
                        terminate_vnf_request, grant,
                        grant_request, **kwargs):
        pass

    def _get_vim_by_name(self, context, k8s_vim_name):
        common_db_api = CommonDbMixin()
        result = common_db_api._get_by_name(
            context, nfvo_db.Vim, k8s_vim_name)

        if not result:
            LOG.debug("Cannot find kubernetes "
                      "vim with name: {}".format(k8s_vim_name))

        return result

    def terminate_end(self, context, vnf_instance,
                      terminate_vnf_request, grant,
                      grant_request, **kwargs):
        self._init_flag()
        k8s_params = vnf_instance.instantiated_vnf_info.additional_params.get(
            'k8s_cluster_installation_param', {})
        k8s_vim_name = k8s_params.get('vim_name')
        if not k8s_vim_name:
            k8s_vim_name = 'kubernetes_vim_' + vnf_instance.id

        vim_info = self._get_vim_by_name(
            context, k8s_vim_name)
        if vim_info:
            self.nfvo_plugin.delete_vim(context, vim_info.id)

    def _get_username_pwd(self, vnf_request, vnf_instance, role):
        # heal and scale: get user pwd
        kwargs_additional_params = vnf_request.additional_params
        additionalParams = \
            vnf_instance.instantiated_vnf_info.additional_params
        if role == 'master':
            if kwargs_additional_params and \
                kwargs_additional_params.get('master_node_username') and \
                    kwargs_additional_params.get('master_node_password'):
                username = \
                    kwargs_additional_params.get('master_node_username')
                password = \
                    kwargs_additional_params.get('master_node_password')
            else:
                username = \
                    additionalParams.get(
                        'k8s_cluster_installation_param').get(
                        'master_node').get('username')
                password = \
                    additionalParams.get(
                        'k8s_cluster_installation_param').get(
                        'master_node').get('password')
        else:
            if kwargs_additional_params and \
                kwargs_additional_params.get('worker_node_username') and \
                    kwargs_additional_params.get('worker_node_username'):
                username = \
                    kwargs_additional_params.get('worker_node_username')
                password = \
                    kwargs_additional_params.get('worker_node_password')
            else:
                username = \
                    additionalParams.get(
                        'k8s_cluster_installation_param').get(
                        'worker_node').get('username')
                password = \
                    additionalParams.get(
                        'k8s_cluster_installation_param').get(
                        'worker_node').get('password')
        return username, password

    def _get_resources_list(self, heatclient, stack_id, resource_name):
        # scale: get resources list
        physical_resource_id = heatclient.resources.get(
            stack_id=stack_id,
            resource_name=resource_name).physical_resource_id
        resources_list = heatclient.resources.list(
            stack_id=physical_resource_id)
        return resources_list

    def _get_host_resource_list(self, heatclient, stack_id, node):
        # scale: get host resource list
        host_ips_list = []
        node_resource_name = node.get('aspect_id')
        if node_resource_name:
            resources_list = self._get_resources_list(
                heatclient, stack_id, node_resource_name)
            for resources in resources_list:
                resource_info = heatclient.resource_get(
                    resources.physical_resource_id,
                    node.get('ssh_cp_name'))
                if resource_info.attributes.get('floating_ip_address'):
                    self.FLOATING_IP_FLAG = True
                    ssh_master_ip = resource_info.attributes.get(
                        'floating_ip_address')
                else:
                    ssh_master_ip = resource_info.attributes.get(
                        'fixed_ips')[0].get('ip_address')
                host_ips_list.append(ssh_master_ip)
        else:
            master_ip = heatclient.resource_get(
                stack_id, node.get('ssh_cp_name')).attributes.get(
                'fixed_ips')[0].get('ip_address')
            host_ips_list.append(master_ip)
        return host_ips_list

    def _connect_ssh_scale(self, master_ip_list, master_username,
                           master_password):
        for master_ip in master_ip_list:
            retry = 4
            while retry > 0:
                try:
                    commander = cmd_executer.RemoteCommandExecutor(
                        user=master_username, password=master_password,
                        host=master_ip,
                        timeout=K8S_CMD_TIMEOUT)
                    return commander, master_ip
                except (exceptions.NotAuthorized, paramiko.SSHException,
                        paramiko.ssh_exception.NoValidConnectionsError) as e:
                    LOG.debug(e)
                    retry -= 1
                    time.sleep(SERVER_WAIT_COMPLETE_TIME)
            if master_ip == master_ip_list[-1]:
                LOG.error('Failed to execute remote command.')
                raise exceptions.MgmtDriverRemoteCommandError()

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
                            'calico-node' not in daemonset_name and \
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

    def _delete_scale_in_worker(
            self, worker_node, kwargs, heatclient, stack_id,
            commander):
        # scale: get host name
        scale_worker_nic_ips = []
        normal_worker_ssh_ips = []
        worker_host_names = []
        scale_name_list = kwargs.get('scale_name_list')
        physical_resource_id = heatclient.resource_get(
            stack_id,
            kwargs.get('scale_vnf_request', {}).aspect_id) \
            .physical_resource_id
        worker_resource_list = heatclient.resource_get_list(
            physical_resource_id)
        for worker_resource in worker_resource_list:
            worker_cp_resource = heatclient.resource_get(
                worker_resource.physical_resource_id,
                worker_node.get('nic_cp_name'))
            if worker_resource.resource_name in scale_name_list:
                scale_worker_ip = worker_cp_resource.attributes.get(
                    'fixed_ips')[0].get('ip_address')
                scale_worker_nic_ips.append(scale_worker_ip)
                worker_host_name = \
                    'worker' + scale_worker_ip.split('.')[-1]
                worker_host_names.append(worker_host_name)
            else:
                normal_worker_ssh_cp_resource = heatclient.resource_get(
                    worker_resource.physical_resource_id,
                    worker_node.get('ssh_cp_name'))
                if normal_worker_ssh_cp_resource.attributes.get(
                        'floating_ip_address'):
                    normal_worker_ssh_ips.append(
                        normal_worker_ssh_cp_resource.attributes.get(
                            'floating_ip_address'))
                else:
                    normal_worker_ssh_ips.append(
                        normal_worker_ssh_cp_resource.attributes.get(
                            'fixed_ips')[0].get('ip_address'))

        for worker_host_name in worker_host_names:
            ssh_command = "kubectl get pods --field-selector=spec." \
                          "nodeName={} --all-namespaces " \
                          "-o json".format(worker_host_name)
            result = self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 3)
            daemonset_content_str = ''.join(result)
            daemonset_content = json.loads(
                daemonset_content_str)
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

    def _set_node_ip_in_hosts(self, commander,
                              type, ips=None, hosts_str=None):
        ssh_command = "> /tmp/tmp_hosts"
        self._execute_command(
            commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
        ssh_command = "cp /etc/hosts /tmp/tmp_hosts"
        self._execute_command(
            commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
        if type == 'scale_in':
            for ip in ips:
                ssh_command = "sed -i '/{}/d' /tmp/tmp_hosts".format(
                    ip)
                self._execute_command(
                    commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
        elif type == 'scale_out' or type == 'heal_end':
            ssh_command = "sed -i '$a{}' /tmp/tmp_hosts".format(
                hosts_str)
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)
        ssh_command = "sudo mv /tmp/tmp_hosts /etc/hosts;"
        self._execute_command(
            commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 0)

    def scale_start(self, context, vnf_instance,
                    scale_vnf_request, grant,
                    grant_request, **kwargs):
        self._init_flag()
        if scale_vnf_request.type == 'SCALE_IN':
            vim_connection_info = \
                self._get_vim_connection_info(context, vnf_instance)

            kwargs['scale_vnf_request'] = scale_vnf_request
            heatclient = hc.HeatClient(vim_connection_info.access_info)
            additionalParams = \
                vnf_instance.instantiated_vnf_info.additional_params
            master_username, master_password = self._get_username_pwd(
                scale_vnf_request, vnf_instance, 'master')
            worker_username, worker_password = self._get_username_pwd(
                scale_vnf_request, vnf_instance, 'worker')
            stack_id = vnf_instance.instantiated_vnf_info.instance_id
            master_node = \
                additionalParams.get('k8s_cluster_installation_param').get(
                    'master_node')
            worker_node = \
                additionalParams.get('k8s_cluster_installation_param').get(
                    'worker_node')
            master_ip_list = self._get_host_resource_list(
                heatclient, stack_id, master_node)
            commander, master_ip = self._connect_ssh_scale(
                master_ip_list, master_username,
                master_password)

            scale_worker_nic_ips, normal_worker_ssh_ips = \
                self._delete_scale_in_worker(
                    worker_node, kwargs, heatclient, stack_id, commander)
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
        else:
            pass

    def _get_worker_info(self, worker_node, worker_resource_list,
                         heatclient, scale_out_id_list, vnf_instance, grant):
        normal_ssh_worker_ip_list = []
        normal_nic_worker_ip_list = []
        add_worker_ssh_ip_list = []
        add_worker_nic_ip_list = []
        zone_id_dict = {}
        host_compute_dict = {}
        for worker_resource in worker_resource_list:
            if self.FLOATING_IP_FLAG:
                ssh_ip = heatclient.resources.get(
                    stack_id=worker_resource.physical_resource_id,
                    resource_name=worker_node.get('ssh_cp_name')). \
                    attributes.get('floating_ip_address')
            else:
                ssh_ip = heatclient.resources.get(
                    stack_id=worker_resource.physical_resource_id,
                    resource_name=worker_node.get('ssh_cp_name')). \
                    attributes.get(
                    'fixed_ips')[0].get('ip_address')
            nic_ip = heatclient.resources.get(
                stack_id=worker_resource.physical_resource_id,
                resource_name=worker_node.get('nic_cp_name')). \
                attributes.get('fixed_ips')[0].get('ip_address')

            if worker_resource.physical_resource_id in scale_out_id_list:
                add_worker_ssh_ip_list.append(ssh_ip)
                add_worker_nic_ip_list.append(nic_ip)
                if self.SET_NODE_LABEL_FLAG:
                    lowest_worker_resources_list = heatclient.resources.list(
                        stack_id=worker_resource.physical_resource_id)
                    for lowest_resource in lowest_worker_resources_list:
                        if lowest_resource.resource_type == \
                                'OS::Nova::Server':
                            worker_node_resource_info = \
                                heatclient.resource_get(
                                    worker_resource.physical_resource_id,
                                    lowest_resource.resource_name)
                            host_compute = worker_node_resource_info.\
                                attributes.get('OS-EXT-SRV-ATTR:host')
                            if self.SET_ZONE_ID_FLAG:
                                physical_resource_id = \
                                    lowest_resource.physical_resource_id
                                zone_id = self._get_zone_id_from_grant(
                                    vnf_instance, grant, 'SCALE',
                                    physical_resource_id)
                                zone_id_dict[nic_ip] = zone_id
                            host_compute_dict[nic_ip] = host_compute
            elif worker_resource.physical_resource_id not in \
                    scale_out_id_list:
                normal_ssh_worker_ip_list.append(ssh_ip)
                normal_nic_worker_ip_list.append(nic_ip)

        return (add_worker_ssh_ip_list, add_worker_nic_ip_list,
                normal_ssh_worker_ip_list, normal_nic_worker_ip_list,
                host_compute_dict, zone_id_dict)

    def _get_master_info(
            self, master_resource_list, heatclient, master_node):
        master_ssh_ip_list = []
        master_nic_ip_list = []
        for master_resource in master_resource_list:
            master_host_reource_info = heatclient.resource_get(
                master_resource.physical_resource_id,
                master_node.get('ssh_cp_name'))
            if master_host_reource_info.attributes.get('floating_ip_address'):
                self.FLOATING_IP_FLAG = True
                master_ssh_ip = master_host_reource_info.attributes.get(
                    'floating_ip_address')
            else:
                master_ssh_ip = master_host_reource_info.attributes. \
                    get('fixed_ips')[0].get('ip_address')
            master_nic_ip = heatclient.resource_get(
                master_resource.physical_resource_id,
                master_node.get('nic_cp_name')).attributes. \
                get('fixed_ips')[0].get('ip_address')
            master_ssh_ip_list.append(master_ssh_ip)
            master_nic_ip_list.append(master_nic_ip)
        return master_ssh_ip_list, master_nic_ip_list

    def _check_pod_affinity(self, heatclient, nest_stack_id, worker_node):
        stack_base_hot_template = heatclient.stacks.template(
            stack_id=nest_stack_id)
        worker_instance_group_name = worker_node.get('aspect_id')
        worker_node_properties = stack_base_hot_template['resources'][
            worker_instance_group_name][
            'properties']['resource']['properties']
        if 'scheduler_hints' in worker_node_properties:
            self.SET_NODE_LABEL_FLAG = True

    def scale_end(self, context, vnf_instance,
                  scale_vnf_request, grant,
                  grant_request, **kwargs):
        self._init_flag()
        if scale_vnf_request.type == 'SCALE_OUT':
            k8s_cluster_installation_param = \
                vnf_instance.instantiated_vnf_info. \
                additional_params.get('k8s_cluster_installation_param')
            vnf_package_path = vnflcm_utils._get_vnf_package_path(
                context, vnf_instance.vnfd_id)
            nest_stack_id = vnf_instance.instantiated_vnf_info.instance_id
            resource_name = scale_vnf_request.aspect_id
            vim_connection_info = \
                self._get_vim_connection_info(context, vnf_instance)
            heatclient = hc.HeatClient(vim_connection_info.access_info)
            scale_out_id_list = kwargs.get('scale_out_id_list')

            # get private_registry_connection_info param
            pr_connection_info = k8s_cluster_installation_param.get(
                'private_registry_connection_info')
            # get private registries of type HTTP
            http_private_registries = self._get_http_private_registries(
                pr_connection_info)

            # get master_ip
            master_ssh_ip_list = []
            master_nic_ip_list = []
            master_node = k8s_cluster_installation_param.get('master_node')

            # The VM is created with SOL001 TOSCA-based VNFD and
            # not use policies. At present, scale operation dose
            # not support this case.
            if not master_node.get('aspect_id'):
                master_ssh_ip_list.append(heatclient.resources.get(
                    stack_id=nest_stack_id,
                    resource_name=master_node.get(
                        'ssh_cp_name')).attributes.get(
                    'fixed_ips')[0].get('ip_address'))
                master_nic_ip_list.append(heatclient.resources.get(
                    stack_id=nest_stack_id,
                    resource_name=master_node.get(
                        'nic_cp_name')).attributes.get(
                    'fixed_ips')[0].get('ip_address'))
                cluster_ip = self._get_cluster_ip(
                    heatclient, 1, master_node, None, nest_stack_id)

            # The VM is created with UserData format
            else:
                master_resource_list = self._get_resources_list(
                    heatclient, nest_stack_id, master_node.get(
                        'aspect_id'))
                master_ssh_ip_list, master_nic_ip_list = \
                    self._get_master_info(master_resource_list,
                                          heatclient, master_node)
                resource_num = len(master_resource_list)
                cluster_ip = self._get_cluster_ip(
                    heatclient, resource_num, master_node,
                    master_resource_list[0].physical_resource_id,
                    nest_stack_id)

            # get scale out worker_ips
            worker_resource_list = self._get_resources_list(
                heatclient, nest_stack_id, resource_name)
            worker_node = \
                k8s_cluster_installation_param['worker_node']

            # check pod-affinity flag
            if grant:
                self.SET_ZONE_ID_FLAG = True
            self._check_pod_affinity(heatclient, nest_stack_id, worker_node)
            (add_worker_ssh_ip_list, add_worker_nic_ip_list,
             normal_ssh_worker_ip_list, normal_nic_worker_ip_list,
             host_compute_dict, zone_id_dict) = \
                self._get_worker_info(
                worker_node, worker_resource_list,
                heatclient, scale_out_id_list, vnf_instance, grant)

            # get kubeadm_token from one of master node
            master_username, master_password = self._get_username_pwd(
                scale_vnf_request, vnf_instance, 'master')
            worker_username, worker_password = self._get_username_pwd(
                scale_vnf_request, vnf_instance, 'worker')
            commander, master_ip = self._connect_ssh_scale(
                master_ssh_ip_list, master_username,
                master_password)
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
            # set no_proxy
            proxy = k8s_cluster_installation_param.get('proxy')
            vm_cidr_list = self._get_vm_cidr_list(
                master_nic_ip_list[0], proxy)
            pod_cidr = master_node.get('pod_cidr', '192.168.0.0/16')
            cluster_cidr = master_node.get("cluster_cidr", '10.96.0.0/12')
            if proxy.get("http_proxy") and proxy.get("https_proxy"):
                no_proxy = ','.join(list(filter(None, [
                    proxy.get("no_proxy"), pod_cidr, cluster_cidr,
                    "127.0.0.1", "localhost",
                    cluster_ip] + vm_cidr_list)))
                proxy['no_proxy'] = no_proxy

            # set /etc/hosts
            master_hosts = []
            add_worker_hosts = []
            normal_worker_hosts = []
            for master_ip in master_nic_ip_list:
                master_ip_str = \
                    master_ip + ' master' + master_ip.split('.')[-1]
                master_hosts.append(master_ip_str)
            for worker_ip in add_worker_nic_ip_list:
                worker_ip_str = \
                    worker_ip + ' worker' + worker_ip.split('.')[-1]
                add_worker_hosts.append(worker_ip_str)
            for worker_ip in normal_nic_worker_ip_list:
                worker_ip_str = \
                    worker_ip + ' worker' + worker_ip.split('.')[-1]
                normal_worker_hosts.append(worker_ip_str)

            ha_flag = True
            if len(master_nic_ip_list) == 1:
                ha_flag = False
            for worker_ip in add_worker_ssh_ip_list:
                script_path = \
                    k8s_cluster_installation_param.get('script_path')
                commander = self._init_commander_and_send_install_scripts(
                    worker_username, worker_password,
                    worker_ip, vnf_package_path, script_path)
                hosts_str = '\\n'.join(master_hosts + add_worker_hosts +
                                       normal_worker_hosts)
                self._set_node_ip_in_hosts(commander,
                                           'scale_out', hosts_str=hosts_str)
                worker_nic_ip = add_worker_nic_ip_list[
                    add_worker_ssh_ip_list.index(worker_ip)]
                self._install_worker_node(
                    commander, proxy, ha_flag, worker_nic_ip,
                    cluster_ip, kubeadm_token, ssl_ca_cert_hash,
                    http_private_registries)
                commander.close_session()

                # connect to private registries
                if pr_connection_info:
                    self._connect_to_private_registries(
                        vnf_package_path, pr_connection_info,
                        worker_username, worker_password, worker_ip)

                if self.SET_NODE_LABEL_FLAG:
                    commander, _ = self._connect_ssh_scale(
                        master_ssh_ip_list, master_username,
                        master_password)
                    self._set_node_label(
                        commander, worker_nic_ip,
                        host_compute_dict.get(worker_nic_ip),
                        zone_id_dict.get(worker_nic_ip))
                storage_server_param = vnf_instance.instantiated_vnf_info \
                    .additional_params.get('k8s_cluster_installation_param')\
                    .get('storage_server')
                if storage_server_param:
                    self._install_nfs_client(worker_username, worker_password,
                                             worker_ip)

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
                    worker_node.get('username'), worker_node.get('password'),
                    worker_ip)
                self._set_node_ip_in_hosts(
                    commander, 'scale_out', hosts_str=hosts_str)
                commander.close_session()
        else:
            pass

    def _get_vnfc_resource_id(self, vnfc_resource_info, vnfc_instance_id):
        for vnfc_resource in vnfc_resource_info:
            if vnfc_resource.id == vnfc_instance_id:
                return vnfc_resource
        else:
            return None

    def _get_master_node_name(
            self, heatclient, master_resource_list,
            target_physical_resource_ids, master_node):
        fixed_master_infos = {}
        not_fixed_master_infos = {}
        flag_master = False
        for master_resource in master_resource_list:
            master_resource_infos = heatclient.resources.list(
                master_resource.physical_resource_id)
            master_host_reource_info = heatclient.resource_get(
                master_resource.physical_resource_id,
                master_node.get('ssh_cp_name'))
            for master_resource_info in master_resource_infos:
                if master_resource_info.resource_type == \
                        'OS::Nova::Server' and \
                        master_resource_info.physical_resource_id in \
                        target_physical_resource_ids:
                    flag_master = True
                    if master_host_reource_info.attributes.get(
                            'floating_ip_address'):
                        self.FLOATING_IP_FLAG = True
                        master_ssh_ip = master_host_reource_info.attributes.\
                            get('floating_ip_address')
                    else:
                        master_ssh_ip = heatclient.resource_get(
                            master_resource.physical_resource_id,
                            master_node.get('ssh_cp_name')).attributes.get(
                            'fixed_ips')[0].get('ip_address')
                    master_nic_ip = heatclient.resource_get(
                        master_resource.physical_resource_id,
                        master_node.get('nic_cp_name')).attributes. \
                        get('fixed_ips')[0].get('ip_address')
                    master_name = 'master' + master_nic_ip.split('.')[-1]
                    fixed_master_infos[master_name] = {}
                    fixed_master_infos[master_name]['master_ssh_ip'] = \
                        master_ssh_ip
                    fixed_master_infos[master_name]['master_nic_ip'] = \
                        master_nic_ip
                elif master_resource_info.resource_type == \
                        'OS::Nova::Server' and \
                        master_resource_info.physical_resource_id not in \
                        target_physical_resource_ids:
                    if master_host_reource_info.attributes.get(
                            'floating_ip_address'):
                        self.FLOATING_IP_FLAG = True
                        master_ssh_ip = master_host_reource_info.attributes.\
                            get('floating_ip_address')
                    else:
                        master_ssh_ip = heatclient.resource_get(
                            master_resource.physical_resource_id,
                            master_node.get('ssh_cp_name')).attributes.get(
                            'fixed_ips')[0].get('ip_address')
                    master_nic_ip = heatclient.resource_get(
                        master_resource.physical_resource_id,
                        master_node.get('nic_cp_name')).attributes. \
                        get('fixed_ips')[0].get('ip_address')
                    master_name = 'master' + master_nic_ip.split('.')[-1]
                    not_fixed_master_infos[master_name] = {}
                    not_fixed_master_infos[master_name]['master_ssh_ip'] = \
                        master_ssh_ip
                    not_fixed_master_infos[master_name]['master_nic_ip'] = \
                        master_nic_ip
        if flag_master and len(master_resource_list) == 1:
            LOG.error("An error occurred in MgmtDriver:{"
                      "The number of Master-Nodes is 1 "
                      "or less. If you want to heal, "
                      "please respawn.}")
            raise exceptions.MgmtDriverOtherError(
                error_message="An error occurred in MgmtDriver:{"
                              "The number of Master-Nodes is 1 "
                              "or less. If you want to heal, "
                              "please respawn.}")
        return flag_master, fixed_master_infos, not_fixed_master_infos

    def _get_worker_node_name(
            self, heatclient, worker_resource_list,
            target_physical_resource_ids, worker_node, vnf_instance, grant):
        fixed_worker_infos = {}
        not_fixed_worker_infos = {}
        flag_worker = False
        for worker_resource in worker_resource_list:
            worker_resource_infos = heatclient.resources.list(
                worker_resource.physical_resource_id)
            worker_host_reource_info = heatclient.resource_get(
                worker_resource.physical_resource_id,
                worker_node.get('ssh_cp_name'))
            for worker_resource_info in worker_resource_infos:
                if worker_resource_info.resource_type == \
                        'OS::Nova::Server' and \
                        worker_resource_info.physical_resource_id in \
                        target_physical_resource_ids:
                    flag_worker = True
                    if worker_host_reource_info.attributes.get(
                            'floating_ip_address'):
                        self.FLOATING_IP_FLAG = True
                        worker_ssh_ip = worker_host_reource_info.attributes.\
                            get('floating_ip_address')
                    else:
                        worker_ssh_ip = heatclient.resource_get(
                            worker_resource.physical_resource_id,
                            worker_node.get('ssh_cp_name')).attributes.get(
                            'fixed_ips')[0].get('ip_address')
                    worker_nic_ip = heatclient.resource_get(
                        worker_resource.physical_resource_id,
                        worker_node.get('nic_cp_name')).attributes. \
                        get('fixed_ips')[0].get('ip_address')
                    worker_name = 'worker' + worker_nic_ip.split('.')[-1]
                    fixed_worker_infos[worker_name] = {}
                    if self.SET_NODE_LABEL_FLAG:
                        worker_node_resource_info = heatclient.resource_get(
                            worker_resource.physical_resource_id,
                            worker_resource_info.resource_name)
                        host_compute = worker_node_resource_info.attributes.\
                            get('OS-EXT-SRV-ATTR:host')
                        fixed_worker_infos[worker_name]['host_compute'] = \
                            host_compute
                        if self.SET_ZONE_ID_FLAG:
                            physical_resource_id = \
                                worker_resource_info.physical_resource_id
                            zone_id = self._get_zone_id_from_grant(
                                vnf_instance, grant, 'HEAL',
                                physical_resource_id)
                            fixed_worker_infos[worker_name]['zone_id'] = \
                                zone_id
                    fixed_worker_infos[worker_name]['worker_ssh_ip'] = \
                        worker_ssh_ip
                    fixed_worker_infos[worker_name]['worker_nic_ip'] = \
                        worker_nic_ip
                elif worker_resource_info.resource_type == \
                        'OS::Nova::Server' and \
                        worker_resource_info.physical_resource_id not in \
                        target_physical_resource_ids:
                    if worker_host_reource_info.attributes.get(
                            'floating_ip_address'):
                        self.FLOATING_IP_FLAG = True
                        worker_ssh_ip = worker_host_reource_info.attributes.\
                            get('floating_ip_address')
                    else:
                        worker_ssh_ip = heatclient.resource_get(
                            worker_resource.physical_resource_id,
                            worker_node.get('ssh_cp_name')).attributes.get(
                            'fixed_ips')[0].get('ip_address')
                    worker_nic_ip = heatclient.resource_get(
                        worker_resource.physical_resource_id,
                        worker_node.get('nic_cp_name')).attributes. \
                        get('fixed_ips')[0].get('ip_address')
                    worker_name = 'worker' + worker_nic_ip.split('.')[-1]
                    not_fixed_worker_infos[worker_name] = {}
                    not_fixed_worker_infos[worker_name]['worker_ssh_ip'] = \
                        worker_ssh_ip
                    not_fixed_worker_infos[worker_name]['worker_nic_ip'] = \
                        worker_nic_ip
        return flag_worker, fixed_worker_infos, not_fixed_worker_infos

    def _get_worker_ssh_ip(
            self, heatclient, stack_id, master_resource_name,
            worker_resource_name, target_physical_resource_ids):
        flag_worker = False
        fixed_worker_infos = dict()
        not_fixed_master_infos = dict()
        stack_resource_list = heatclient.resources.list(stack_id)
        worker_ip = heatclient.resource_get(
            stack_id, worker_resource_name).attributes.get(
            'fixed_ips')[0].get('ip_address')
        master_ip = heatclient.resource_get(
            stack_id, master_resource_name).attributes.get(
            'fixed_ips')[0].get('ip_address')
        master_name = 'master' + master_ip.split('.')[-1]
        for stack_resource in stack_resource_list:
            if stack_resource.resource_type == 'OS::Nova::Server':
                current_ip_list = []
                current_address = heatclient.resource_get(
                    stack_id, stack_resource.resource_name).attributes.get(
                    'addresses', {})
                for network, network_info in current_address.items():
                    for network_ip_info in network_info:
                        current_ip_list.append(network_ip_info.get('addr'))

                if stack_resource.physical_resource_id in \
                        target_physical_resource_ids and \
                        master_ip in current_ip_list:
                    LOG.error("An error occurred in MgmtDriver:{"
                              "The number of Master-Nodes is 1 "
                              "or less. If you want to heal, "
                              "please respawn.}")
                    raise exceptions.MgmtDriverOtherError(
                        error_message="An error occurred in MgmtDriver:{"
                                      "The number of Master-Nodes is 1 "
                                      "or less. If you want to heal, "
                                      "please respawn.}")
                elif stack_resource.physical_resource_id not in \
                        target_physical_resource_ids and \
                        master_ip in current_ip_list:
                    not_fixed_master_infos.update(
                        {master_name: {'master_ssh_ip': master_ip}})
                    not_fixed_master_infos[master_name].update(
                        {'master_nic_ip': master_ip})
                elif stack_resource.physical_resource_id in \
                        target_physical_resource_ids and \
                        worker_ip in current_ip_list:
                    worker_name = 'worker' + worker_ip.split('.')[-1]
                    fixed_worker_infos.update(
                        {worker_name: {'worker_ssh_ip': worker_ip}})
                    fixed_worker_infos[worker_name].update(
                        {'worker_nic_ip': worker_ip})
                    flag_worker = True
        return flag_worker, fixed_worker_infos, not_fixed_master_infos, {}

    def _delete_master_node(
            self, fixed_master_infos, not_fixed_master_infos,
            master_username, master_password):
        not_fixed_master_ssh_ips = [
            master_ips.get('master_ssh_ip')
            for master_ips in not_fixed_master_infos.values()]

        for fixed_master_name in fixed_master_infos.keys():
            # delete heal master node info from haproxy.cfg
            # on other master node
            for not_fixed_master_ssh_ip in not_fixed_master_ssh_ips:
                commander = cmd_executer.RemoteCommandExecutor(
                    user=master_username, password=master_password,
                    host=not_fixed_master_ssh_ip,
                    timeout=K8S_CMD_TIMEOUT)
                master_ssh_ip = not_fixed_master_ssh_ip
                ssh_command = "sudo sed -i '/server  {}/d' " \
                              "/etc/haproxy/haproxy.cfg;" \
                              "sudo service haproxy restart;" \
                              "".format(fixed_master_name)
                self._execute_command(
                    commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 3)

            # check worker_node exist in k8s-cluster
            result = self._is_worker_node_installed(
                commander, fixed_master_name)
            if not result:
                continue
            for res in result:
                if res.split(' ')[0].strip() == fixed_master_name:
                    # fixed_master_name is found
                    break
            else:
                continue

            # delete master node
            ssh_command = "kubectl delete node " + \
                          fixed_master_name
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
                       if fixed_master_name
                       in res][0].split(',')[0]
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
            master_ips.get('master_ssh_ip')
            for master_ips in not_fixed_master_infos.values()]
        for fixed_worker_name in fixed_worker_infos.keys():
            commander, master_ssh_ip = self._connect_ssh_scale(
                not_fixed_master_ssh_ips, master_username,
                master_password)
            ssh_command = "kubectl get pods --field-selector=" \
                          "spec.nodeName={} -o json" \
                          "".format(fixed_worker_name)
            result = self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 3)
            worker_node_pod_info_str = ''.join(result)
            worker_node_pod_info = json.loads(
                worker_node_pod_info_str)
            if not worker_node_pod_info['items']:
                continue
            ssh_command = "kubectl drain {} " \
                          "--ignore-daemonsets " \
                          "--timeout={}s" \
                          "".format(fixed_worker_name,
                                    K8S_CMD_TIMEOUT)
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'drain', 3)
            self.evacuate_wait(
                commander, worker_node_pod_info)
            ssh_command = "kubectl delete node {}".format(
                fixed_worker_name)
            self._execute_command(
                commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 3)
            commander.close_session()

    def _delete_node_to_be_healed(
            self, heatclient, stack_id, target_physical_resource_ids,
            master_username, master_password, worker_resource_name,
            master_resource_name, master_node, worker_node):
        master_ssh_cp_name = master_node.get('nic_cp_name')
        flag_master = False
        flag_worker = False
        if master_resource_name == master_ssh_cp_name:
            (flag_worker, fixed_worker_infos, not_fixed_master_infos,
             not_fixed_worker_infos) = \
                self._get_worker_ssh_ip(
                    heatclient, stack_id, master_resource_name,
                    worker_resource_name, target_physical_resource_ids)
        else:
            master_resource_list = self._get_resources_list(
                heatclient, stack_id, master_resource_name)
            flag_master, fixed_master_infos, not_fixed_master_infos = \
                self._get_master_node_name(
                    heatclient, master_resource_list,
                    target_physical_resource_ids,
                    master_node)
            if len(master_resource_list) == 1 and flag_master:
                LOG.error("An error occurred in MgmtDriver:{"
                          "The number of Master-Nodes is 1 "
                          "or less. If you want to heal, "
                          "please respawn.}")
                raise exceptions.MgmtDriverOtherError(
                    error_message="An error occurred in MgmtDriver:{"
                                  "The number of Master-Nodes is 1 "
                                  "or less. If you want to heal, "
                                  "please respawn.}")
            worker_resource_list = self._get_resources_list(
                heatclient, stack_id, worker_resource_name)
            flag_worker, fixed_worker_infos, not_fixed_worker_infos = \
                self._get_worker_node_name(
                    heatclient, worker_resource_list,
                    target_physical_resource_ids,
                    worker_node, vnf_instance=None, grant=None)
        if flag_master:
            self._delete_master_node(
                fixed_master_infos, not_fixed_master_infos,
                master_username, master_password)
        if flag_worker:
            self._delete_worker_node(
                fixed_worker_infos, not_fixed_master_infos,
                master_username, master_password)

    def _get_node_resource_name(self, vnf_additional_params, node):
        if node.get('aspect_id'):
            # in case of HA master node
            resource_name = node.get('aspect_id')
        else:
            # in case of single master node
            resource_name = node.get('nic_cp_name')
        return resource_name

    def _get_target_physical_resource_ids(self, vnf_instance,
                                          heal_vnf_request):
        target_node_physical_resource_ids = []
        target_ss_physical_resource_ids = []
        storage_server_param = vnf_instance.instantiated_vnf_info \
            .additional_params.get('k8s_cluster_installation_param')\
            .get('storage_server', {})
        target_ss_cp_name = storage_server_param.get('nic_cp_name', None)
        for vnfc_instance_id in heal_vnf_request.vnfc_instance_id:
            instantiated_vnf_info = vnf_instance.instantiated_vnf_info
            vnfc_resource_info = instantiated_vnf_info.vnfc_resource_info
            vnfc_resource = self._get_vnfc_resource_id(
                vnfc_resource_info, vnfc_instance_id)
            if vnfc_resource:
                storage_server_flag = False
                if hasattr(vnfc_resource, 'vnfc_cp_info') and \
                        target_ss_cp_name:
                    vnfc_cp_infos = vnfc_resource.vnfc_cp_info
                    for vnfc_cp_info in vnfc_cp_infos:
                        if vnfc_cp_info.cpd_id == target_ss_cp_name:
                            storage_server_flag = True
                            break
                if storage_server_flag:
                    target_ss_physical_resource_ids.append(
                        vnfc_resource.compute_resource.resource_id)
                else:
                    target_node_physical_resource_ids.append(
                        vnfc_resource.compute_resource.resource_id)

        return target_node_physical_resource_ids, \
            target_ss_physical_resource_ids

    def _prepare_for_restoring_helm(self, commander, master_ip):
        helm_info = {}
        # get helm repo list
        ssh_command = "helm repo list -o json"
        result = self._execute_command(
            commander, ssh_command, K8S_CMD_TIMEOUT, 'helm_repo_list', 0)
        if result:
            helmrepo_list = json.loads(result)
            helm_info['ext_helmrepo_list'] = helmrepo_list
        # compress local helm chart
        ssh_command = ("sudo tar -zcf {cmp_path} -P {helm_chart_dir}"
            .format(cmp_path=HELM_CHART_CMP_PATH,
                    helm_chart_dir=HELM_CHART_DIR))
        self._execute_command(
            commander, ssh_command, HELM_INSTALL_TIMEOUT, 'common', 0)
        helm_info['local_repo_src_ip'] = master_ip

        return helm_info

    def _restore_helm_repo(self, commander, master_username, master_password,
                           local_repo_src_ip, ext_repo_list):
        # restore local helm chart
        ssh_command = (
            "sudo sshpass -p {master_password} "
            "scp -o StrictHostKeyChecking=no "
            "{master_username}@{local_repo_src_ip}:{helm_chart_cmp_path} "
            "{helm_chart_cmp_path};").format(
                master_password=master_password,
                master_username=master_username,
                local_repo_src_ip=local_repo_src_ip,
                helm_chart_cmp_path=HELM_CHART_CMP_PATH
        )
        ssh_command += "sudo tar -Pzxf {helm_chart_cmp_path};".format(
            helm_chart_cmp_path=HELM_CHART_CMP_PATH)
        self._execute_command(
            commander, ssh_command, HELM_CMD_TIMEOUT, 'scp', 0)
        # restore external helm repository
        if ext_repo_list:
            for ext_repo in ext_repo_list:
                ssh_command += "helm repo add {name} {url};".format(
                    name=ext_repo.get('name'), url=ext_repo.get('url'))
            self._execute_command(
                commander, ssh_command, HELM_CMD_TIMEOUT, 'common', 0)

    def heal_start(self, context, vnf_instance,
                   heal_vnf_request, grant,
                   grant_request, **kwargs):
        self._init_flag()
        stack_id = vnf_instance.instantiated_vnf_info.instance_id
        vnf_additional_params = \
            vnf_instance.instantiated_vnf_info.additional_params
        master_node = vnf_additional_params.get(
            'k8s_cluster_installation_param', {}).get(
            'master_node', {})
        worker_node = vnf_additional_params.get(
            'k8s_cluster_installation_param', {}).get(
            'worker_node', {})
        master_resource_name = self._get_node_resource_name(
            vnf_additional_params, master_node)
        worker_resource_name = self._get_node_resource_name(
            vnf_additional_params, worker_node)
        master_username, master_password = self._get_username_pwd(
            heal_vnf_request, vnf_instance, 'master')
        vim_connection_info = self._get_vim_connection_info(
            context, vnf_instance)
        heatclient = hc.HeatClient(vim_connection_info.access_info)
        if not heal_vnf_request.vnfc_instance_id:
            k8s_params = vnf_additional_params.get(
                'k8s_cluster_installation_param', {})
            k8s_vim_name = k8s_params.get('vim_name')
            if not k8s_vim_name:
                k8s_vim_name = 'kubernetes_vim_' + vnf_instance.id
            k8s_vim_info = self._get_vim_by_name(
                context, k8s_vim_name)
            if k8s_vim_info:
                self.nfvo_plugin.delete_vim(context, k8s_vim_info.id)
                for vim_info in vnf_instance.vim_connection_info:
                    if vim_info.vim_id == k8s_vim_info.id:
                        vnf_instance.vim_connection_info.remove(vim_info)
        else:
            target_node_physical_resource_ids, \
                target_ss_physical_resource_ids = \
                self._get_target_physical_resource_ids(
                    vnf_instance, heal_vnf_request)
            if target_node_physical_resource_ids:
                self._delete_node_to_be_healed(
                    heatclient, stack_id, target_node_physical_resource_ids,
                    master_username, master_password, worker_resource_name,
                    master_resource_name, master_node, worker_node)
            if target_ss_physical_resource_ids:
                self._heal_start_storage_server(
                    context, vnf_instance,
                    vnf_additional_params, heatclient, stack_id,
                    target_node_physical_resource_ids, master_username,
                    master_password, master_resource_name, master_node)

    def _fix_master_node(
            self, not_fixed_master_infos, hosts_str,
            fixed_master_infos, proxy,
            master_username, master_password, vnf_package_path,
            script_path, cluster_ip, pod_cidr, cluster_cidr,
            kubeadm_token, ssl_ca_cert_hash, ha_flag, helm_info,
            pr_connection_info, http_private_registries):
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
        for fixed_master_name, fixed_master_info in \
                fixed_master_infos.items():
            commander, master_ip = self._connect_ssh_scale(
                not_fixed_master_ssh_ips,
                master_username, master_password)
            ssh_command = "sudo kubeadm init phase upload-certs " \
                          "--upload-certs"
            result = self._execute_command(
                commander, ssh_command,
                K8S_CMD_TIMEOUT, 'certificate_key', 3)
            certificate_key = result[-1].replace('\n', '')
            commander.close_session()
            commander = self._init_commander_and_send_install_scripts(
                master_username, master_password,
                fixed_master_info.get('master_ssh_ip'),
                vnf_package_path, script_path,
                helm_info.get('script_path', None))
            self._set_node_ip_in_hosts(
                commander, 'heal_end', hosts_str=hosts_str)
            if proxy.get('http_proxy') and proxy.get('https_proxy'):
                ssh_command = \
                    "export http_proxy={http_proxy};" \
                    "export https_proxy={https_proxy};" \
                    "export no_proxy={no_proxy};" \
                    "export ha_flag={ha_flag};" \
                    "bash /tmp/install_k8s_cluster.sh " \
                    "-m {master_ip} -i {cluster_ip} " \
                    "-p {pod_cidr} -a {k8s_cluster_cidr} " \
                    "-t {kubeadm_token} -s {ssl_ca_cert_hash} " \
                    "-k {certificate_key}".format(
                        http_proxy=proxy.get('http_proxy'),
                        https_proxy=proxy.get('https_proxy'),
                        no_proxy=proxy.get('no_proxy'),
                        ha_flag=ha_flag,
                        master_ip=master_ssh_ips_str,
                        cluster_ip=cluster_ip,
                        pod_cidr=pod_cidr,
                        k8s_cluster_cidr=cluster_cidr,
                        kubeadm_token=kubeadm_token,
                        ssl_ca_cert_hash=ssl_ca_cert_hash,
                        certificate_key=certificate_key)
            else:
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

            # if connecting to the private registries over HTTP,
            # add "export HTTP_PRIVATE_REGISTRIES" command
            if http_private_registries:
                ssh_command = \
                    "export HTTP_PRIVATE_REGISTRIES=\"{}\";{}".format(
                        http_private_registries, ssh_command)

            self._execute_command(
                commander, ssh_command, K8S_INSTALL_TIMEOUT, 'install', 0)
            if helm_info:
                self._install_helm(commander, proxy)
                self._restore_helm_repo(
                    commander, master_username, master_password,
                    helm_info.get('local_repo_src_ip'),
                    helm_info.get('ext_helmrepo_list', ''))
            commander.close_session()
            for not_fixed_master_name, not_fixed_master in \
                    not_fixed_master_infos.items():
                commander = self._init_commander_and_send_install_scripts(
                    master_username, master_password,
                    not_fixed_master.get('master_ssh_ip'))
                ssh_command = r"sudo sed -i '/server * check/a\    server " \
                              "{} {}:6443 check' " \
                              "/etc/haproxy/haproxy.cfg" \
                              "".format(fixed_master_name,
                                        fixed_master_info.get(
                                            'master_nic_ip'))
                self._execute_command(
                    commander, ssh_command, K8S_CMD_TIMEOUT, 'common', 3)
                commander.close_session()

            # connect to private registries
            if pr_connection_info:
                self._connect_to_private_registries(
                    vnf_package_path, pr_connection_info,
                    master_username, master_password,
                    fixed_master_info.get('master_ssh_ip'))

    def _fix_worker_node(
            self, fixed_worker_infos,
            hosts_str, worker_username, worker_password,
            vnf_package_path, script_path, proxy, cluster_ip,
            kubeadm_token, ssl_ca_cert_hash, ha_flag,
            pr_connection_info, http_private_registries):
        for fixed_worker_name, fixed_worker in fixed_worker_infos.items():
            commander = self._init_commander_and_send_install_scripts(
                worker_username, worker_password,
                fixed_worker.get('worker_ssh_ip'),
                vnf_package_path, script_path)
            self._install_worker_node(
                commander, proxy, ha_flag,
                fixed_worker.get('worker_nic_ip'),
                cluster_ip, kubeadm_token, ssl_ca_cert_hash,
                http_private_registries)
            self._set_node_ip_in_hosts(
                commander, 'heal_end', hosts_str=hosts_str)
            commander.close_session()

            # connect to private registries
            if pr_connection_info:
                self._connect_to_private_registries(
                    vnf_package_path, pr_connection_info,
                    worker_username, worker_password,
                    fixed_worker.get('worker_ssh_ip'))

    def _heal_and_join_k8s_node(
            self, heatclient, stack_id, target_physical_resource_ids,
            vnf_additional_params, master_resource_name, master_username,
            master_password, vnf_package_path, worker_resource_name,
            worker_username, worker_password, cluster_resource_name,
            master_node, worker_node, vnf_instance, grant):
        master_ssh_cp_name = master_node.get('nic_cp_name')
        flag_master = False
        flag_worker = False
        fixed_master_infos = {}
        if master_resource_name == master_ssh_cp_name:
            (flag_worker, fixed_worker_infos, not_fixed_master_infos,
             not_fixed_worker_infos) = \
                self._get_worker_ssh_ip(
                    heatclient, stack_id, master_resource_name,
                    worker_resource_name, target_physical_resource_ids)
            cluster_ip = heatclient.resource_get(
                stack_id, master_node.get('cluster_cp_name')).attributes.get(
                'fixed_ips')[0].get('ip_address')
        else:
            master_resource_list = self._get_resources_list(
                heatclient, stack_id, master_resource_name)
            flag_master, fixed_master_infos, not_fixed_master_infos = \
                self._get_master_node_name(
                    heatclient, master_resource_list,
                    target_physical_resource_ids, master_node)

            # check pod_affinity flag
            if grant:
                self.SET_ZONE_ID_FLAG = True
            self._check_pod_affinity(heatclient, stack_id, worker_node)
            worker_resource_list = self._get_resources_list(
                heatclient, stack_id, worker_resource_name)
            flag_worker, fixed_worker_infos, not_fixed_worker_infos = \
                self._get_worker_node_name(
                    heatclient, worker_resource_list,
                    target_physical_resource_ids,
                    worker_node, vnf_instance, grant)
            if len(master_resource_list) > 1:
                cluster_resource = heatclient.resource_get(
                    stack_id, cluster_resource_name)
                cluster_ip = cluster_resource.attributes.get(
                    'fixed_ips')[0].get('ip_address')
            else:
                cluster_ip = list(not_fixed_master_infos.values())[0].get(
                    'master_nic_ip')
        vm_cidr_list = []
        k8s_cluster_installation_param = vnf_additional_params.get(
            'k8s_cluster_installation_param', {})
        proxy = k8s_cluster_installation_param.get('proxy', {})
        if proxy.get('k8s_node_cidr'):
            cidr = proxy.get('k8s_node_cidr')
        else:
            cidr = list(not_fixed_master_infos.values())[0].get(
                'master_nic_ip') + '/24'
        network_ips = ipaddress.ip_network(cidr, False)
        for network_ip in network_ips:
            vm_cidr_list.append(str(network_ip))
        master_node = k8s_cluster_installation_param.get('master_node')
        script_path = k8s_cluster_installation_param.get('script_path')
        ss_installation_params = \
            k8s_cluster_installation_param.get('storage_server')
        pod_cidr = master_node.get('pod_cidr', '192.168.0.0/16')
        cluster_cidr = master_node.get("cluster_cidr", '10.96.0.0/12')
        if proxy.get("http_proxy") and proxy.get("https_proxy"):
            no_proxy = ','.join(list(filter(None, [
                proxy.get("no_proxy"), pod_cidr, cluster_cidr,
                "127.0.0.1", "localhost",
                cluster_ip] + vm_cidr_list)))
            proxy['no_proxy'] = no_proxy
        not_fixed_master_ssh_ips = [
            master_ips.get('master_ssh_ip')
            for master_ips in not_fixed_master_infos.values()]
        commander, master_ip = self._connect_ssh_scale(
            not_fixed_master_ssh_ips,
            master_username, master_password)
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

        # prepare for restoring helm repository
        helm_inst_script_path = k8s_cluster_installation_param.get(
            'helm_installation_script_path', None)
        helm_info = {}
        if helm_inst_script_path:
            helm_info = self._prepare_for_restoring_helm(commander, master_ip)
            helm_info['script_path'] = helm_inst_script_path

        commander.close_session()
        if len(fixed_master_infos) + len(not_fixed_master_ssh_ips) == 1:
            ha_flag = False
        else:
            ha_flag = True

        hosts_str = self._get_all_hosts(
            not_fixed_master_infos, fixed_master_infos,
            not_fixed_worker_infos, fixed_worker_infos)

        # get private_registry_connection_info param
        pr_connection_info = k8s_cluster_installation_param.get(
            'private_registry_connection_info')
        # get private registries of type HTTP
        http_private_registries = self._get_http_private_registries(
            pr_connection_info)

        if flag_master:
            self._fix_master_node(
                not_fixed_master_infos, hosts_str,
                fixed_master_infos, proxy,
                master_username, master_password, vnf_package_path,
                script_path, cluster_ip, pod_cidr, cluster_cidr,
                kubeadm_token, ssl_ca_cert_hash, ha_flag, helm_info,
                pr_connection_info, http_private_registries)

            for fixed_master_info in fixed_master_infos.values():
                node_ip = fixed_master_info.get('master_ssh_ip')
                if ss_installation_params:
                    self._install_nfs_client(
                        master_username, master_password, node_ip)
        if flag_worker:
            self._fix_worker_node(
                fixed_worker_infos,
                hosts_str, worker_username, worker_password,
                vnf_package_path, script_path, proxy, cluster_ip,
                kubeadm_token, ssl_ca_cert_hash, ha_flag,
                pr_connection_info, http_private_registries)

            for fixed_worker_info in fixed_worker_infos.values():
                node_ip = fixed_worker_info.get('worker_ssh_ip')
                if ss_installation_params:
                    self._install_nfs_client(worker_username, worker_password,
                                         node_ip)

        if self.SET_NODE_LABEL_FLAG:
            for fixed_worker_name, fixed_worker in fixed_worker_infos.items():
                commander, _ = self._connect_ssh_scale(
                    not_fixed_master_ssh_ips,
                    master_username, master_password)
                self._set_node_label(
                    commander, fixed_worker.get('worker_nic_ip'),
                    fixed_worker.get('host_compute'),
                    fixed_worker.get('zone_id'))

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

    def heal_end(self, context, vnf_instance,
                 heal_vnf_request, grant,
                 grant_request, **kwargs):
        self._init_flag()
        vnf_package_path = vnflcm_utils._get_vnf_package_path(
            context, vnf_instance.vnfd_id)
        vnf_additional_params = \
            vnf_instance.instantiated_vnf_info.additional_params
        master_node = \
            vnf_additional_params.get(
                'k8s_cluster_installation_param', {}).get(
                'master_node', {})
        worker_node = \
            vnf_additional_params.get(
                'k8s_cluster_installation_param', {}).get(
                'worker_node', {})
        if not heal_vnf_request.vnfc_instance_id:
            self.instantiate_end(context, vnf_instance,
                                 vnf_instance.instantiated_vnf_info,
                                 grant=grant,
                                 grant_request=grant_request, **kwargs)
        else:
            stack_id = vnf_instance.instantiated_vnf_info.instance_id
            master_resource_name = self._get_node_resource_name(
                vnf_additional_params, master_node)
            worker_resource_name = self._get_node_resource_name(
                vnf_additional_params, worker_node)
            cluster_resource_name = master_node.get('cluster_cp_name')
            master_username, master_password = self._get_username_pwd(
                heal_vnf_request, vnf_instance, 'master')
            worker_username, worker_password = self._get_username_pwd(
                heal_vnf_request, vnf_instance, 'worker')
            vim_connection_info = self._get_vim_connection_info(
                context, vnf_instance)
            heatclient = hc.HeatClient(vim_connection_info.access_info)

            # get all target physical resource id
            target_node_physical_resource_ids, \
                target_ss_physical_resource_ids = \
                self._get_target_physical_resource_ids(
                    vnf_instance, heal_vnf_request)
            if target_node_physical_resource_ids:
                self._heal_and_join_k8s_node(
                    heatclient, stack_id, target_node_physical_resource_ids,
                    vnf_additional_params, master_resource_name,
                    master_username, master_password, vnf_package_path,
                    worker_resource_name, worker_username, worker_password,
                    cluster_resource_name, master_node, worker_node,
                    vnf_instance, grant)
            if target_ss_physical_resource_ids:
                self._heal_end_storage_server(context, vnf_instance,
                    vnf_additional_params, stack_id, master_node,
                    master_resource_name, heatclient,
                    target_node_physical_resource_ids,
                    master_username, master_password)

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

    def _check_envi(self, commander):
        ssh_command = 'cat /etc/os-release | grep "PRETTY_NAME=" | ' \
                      'grep -c "Ubuntu 20.04"; arch | grep -c x86_64'
        result = self._execute_command(
            commander, ssh_command, NFS_CMD_TIMEOUT, 'common', 3)
        results = [int(item.replace('\n', '')) for item in result]
        if not (results[0] and results[1]):
            raise exceptions.MgmtDriverOtherError(
                error_message="Storage server VM setup failed."
                              "Your OS does not support at present."
                              "It only supports Ubuntu 20.04 (x86_64)"
            )

    def _install_storage_server(self, context, vnf_instance, proxy,
                                ss_installation_params):
        ssh_cp_name = ss_installation_params.get('ssh_cp_name')
        ssh_username = ss_installation_params.get('username')
        ssh_password = ss_installation_params.get('password')
        cinder_volume_setup_params = \
            ss_installation_params.get('cinder_volume_setup_params')
        nfs_server_setup_params = \
            ss_installation_params.get('nfs_server_setup_params')
        stack_id = vnf_instance.instantiated_vnf_info.instance_id
        vim_connection_info = self._get_vim_connection_info(
            context, vnf_instance)

        heatclient = hc.HeatClient(vim_connection_info.access_info)

        resource_info = heatclient.resources.get(
            stack_id=stack_id,
            resource_name=ssh_cp_name
        )
        ssh_ip_address = resource_info.attributes.get('floating_ip_address')
        if ssh_ip_address is None and resource_info.attributes.get(
                'fixed_ips'):
            ssh_ip_address = resource_info.attributes.get(
                'fixed_ips')[0].get('ip_address')

        try:
            ipaddress.ip_address(ssh_ip_address)
        except ValueError:
            raise exceptions.MgmtDriverOtherError(
                error_message="The IP address of "
                              "Storage server VM is invalid.")
        if ssh_ip_address is None:
            raise exceptions.MgmtDriverOtherError(
                error_message="Failed to get IP address for "
                              "Storage server VM")

        commander = self._init_commander(ssh_username, ssh_password,
                                         ssh_ip_address)
        self._check_envi(commander)

        for setup_info in cinder_volume_setup_params:
            volume_resource_id = setup_info.get('volume_resource_id')
            volume_mount_to = setup_info.get('mount_to')
            resource_info = heatclient.resources.get(
                stack_id=stack_id,
                resource_name=volume_resource_id
            )
            volume_device = resource_info.attributes.get(
                'attachments')[0].get('device')
            if not volume_device:
                raise exceptions.MgmtDriverOtherError(
                    error_message=f"Failed to get device information for "
                                  f"Cinder volume.volume_resource_id:"
                                  f"{volume_resource_id}")

            ssh_command = \
                f"sudo mkfs -t ext4 {volume_device} 2>/dev/null && " \
                f"sudo mkdir -p {volume_mount_to} && " \
                f"sudo mount {volume_device} {volume_mount_to} -t ext4"
            result = self._execute_command(
                commander, ssh_command, NFS_CMD_TIMEOUT * 5, 'common', 3)

            ssh_command = f"df | grep -c {volume_device}"
            result = self._execute_command(
                commander, ssh_command, NFS_CMD_TIMEOUT, 'common', 3)
            results = [int(item.replace('\n', '')) for item in result]
            if not results[0]:
                raise exceptions.MgmtDriverOtherError(
                    error_message=f"Failed to setup Cinder volume device on "
                                  f"Storage Server VM"
                                  f"(device:{volume_device}).")

            http_proxy = proxy.get('http_proxy')
            https_proxy = proxy.get('https_proxy')
            if http_proxy and https_proxy:
                ssh_command = \
                    f'echo -e "Acquire::http::Proxy \\"{http_proxy}\\";\n' \
                    f'Acquire::https::Proxy \\"{https_proxy}\\";" | ' \
                    f'sudo tee /etc/apt/apt.conf.d/proxy.conf >/dev/null ' \
                    f'&& ' \
                    f'sudo apt-get update && ' \
                    f'export DEBIAN_FRONTEND=noninteractive;' \
                    f'sudo -E apt-get install -y nfs-kernel-server'
            else:
                ssh_command = "sudo apt-get update && " \
                              "export DEBIAN_FRONTEND=noninteractive;" \
                              "sudo -E apt-get install -y nfs-kernel-server"
            result = self._execute_command(
                commander, ssh_command, NFS_INSTALL_TIMEOUT, 'common', 3)

        for setup_info in nfs_server_setup_params:
            export_dir = setup_info.get('export_dir')
            export_to = setup_info.get('export_to')
            export_str = f"{export_dir} {export_to}" \
                         f"(rw,sync,no_subtree_check,insecure,all_squash)"
            ssh_command = f'sudo mkdir -p {export_dir} && ' \
                          f'sudo chown nobody.nogroup {export_dir} && ' \
                          f'echo "{export_str}" | ' \
                          f'sudo tee -a /etc/exports >/dev/null'
            result = self._execute_command(
                commander, ssh_command, NFS_CMD_TIMEOUT * 10, 'common', 3)
            ssh_command = "sudo exportfs -ra"
            result = self._execute_command(
                commander, ssh_command, NFS_CMD_TIMEOUT, 'common', 3)
        ssh_command = "sudo exportfs"
        result = self._execute_command(
            commander, ssh_command, NFS_CMD_TIMEOUT, 'common', 3)
        for setup_info in nfs_server_setup_params:
            export_dir = setup_info.get('export_dir')
            if export_dir not in ','.join(result):
                raise exceptions.MgmtDriverOtherError(
                    error_message=f"Failed to setup NFS export on Storage "
                                  f"Server VM(export_dir:{export_dir})")

    def _install_nfs_client(self, node_username, node_password, node_ip):
        # commander = cmd_executer.RemoteCommandExecutor(
        #     user=node_username, password=node_password, host=node_ip,
        #     timeout=K8S_CMD_TIMEOUT)
        commander = self._init_commander(node_username, node_password, node_ip)

        ssh_command = "sudo apt-get update && " \
                      "export DEBIAN_FRONTEND=noninteractive;" \
                      "sudo -E apt-get install -y nfs-common"
        result = self._execute_command(
            commander, ssh_command, NFS_INSTALL_TIMEOUT, 'common', 3)

        ssh_command = "sudo apt list --installed 2>/dev/null | " \
                      "grep -c nfs-common"
        result = self._execute_command(
            commander, ssh_command, NFS_CMD_TIMEOUT, 'common', 3)
        results = [int(item.replace('\n', '')) for item in result]
        if not results[0]:
            raise exceptions.MgmtDriverOtherError(
                error_message=f"Failed to install NFS client"
                              f"(node ip:{node_ip})")

    def _register_persistent_volumes(self, context, vnf_instance, commander,
                                     master_username, master_password,
                                     master_ip, pv_registration_params):
        vnf_package_path = vnflcm_utils._get_vnf_package_path(
            context, vnf_instance.vnfd_id)
        pv_file_list = []
        for pv_info in pv_registration_params:
            pv_manifest_file_path = pv_info.get('pv_manifest_file_path')
            nfs_server_cp = pv_info.get('nfs_server_cp')
            local_file_path = os.path.join(vnf_package_path,
                                           pv_manifest_file_path)
            if not os.path.exists(local_file_path):
                raise exceptions.MgmtDriverParamInvalid(
                    param=f"pv_manifest_file_path"
                          f"(path:{pv_manifest_file_path})")
            with open(local_file_path, 'r', encoding='utf-8') as f:
                nfs_pv = yaml.safe_load(f)
                pv_name = nfs_pv.get('metadata', {}).get('name')
            if not pv_name:
                raise exceptions.MgmtDriverOtherError(
                    error_message=f"Failed to get Kubernetes PersistentVolume"
                                  f" name from manifest file"
                                  f"(path:{pv_manifest_file_path})")
            remote_file_path = os.path.join('/tmp', pv_manifest_file_path)
            remote_dir_path = os.path.dirname(remote_file_path)
            ssh_command = f"mkdir -p {remote_dir_path}"
            result = self._execute_command(
                commander, ssh_command, NFS_CMD_TIMEOUT, 'common', 3)
            pv_file_list.append(
                (local_file_path, remote_file_path, nfs_server_cp, pv_name))

        with paramiko.Transport(master_ip, 22) as connect:
            connect.connect(
                username=master_username, password=master_password)
            sftp_client = paramiko.SFTPClient.from_transport(connect)
            for pv_info in pv_file_list:
                sftp_client.put(pv_info[0], pv_info[1])

        vim_connection_info = self._get_vim_connection_info(
            context, vnf_instance)
        heatclient = hc.HeatClient(vim_connection_info.access_info)
        stack_id = vnf_instance.instantiated_vnf_info.instance_id
        nfs_server_cp_dict = {}
        for pv_info in pv_file_list:
            pv_file_path = pv_info[1]
            nfs_server_cp = pv_info[2]
            pv_name = pv_info[3]
            nfs_server_ip = nfs_server_cp_dict.get(nfs_server_cp)
            if not nfs_server_ip:
                resource_info = heatclient.resources.get(
                    stack_id, nfs_server_cp)
                nfs_server_ip = resource_info.attributes \
                    .get('fixed_ips')[0].get('ip_address')
                if not nfs_server_ip:
                    raise exceptions.MgmtDriverOtherError(
                        error_message=f"Failed to get NFS server IP address"
                                      f"(nfs_server_cp:{nfs_server_cp})")
                nfs_server_cp_dict[nfs_server_cp] = nfs_server_ip

            ssh_command = \
                f'sed -i -E ' \
                f'"s/server *: *[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+/server: ' \
                f'{nfs_server_ip}/g" {pv_file_path} && ' \
                f'kubectl apply -f {pv_file_path}'
            result = self._execute_command(
                commander, ssh_command, NFS_CMD_TIMEOUT, 'common', 3)

            ssh_command = f"kubectl get pv {pv_name} " \
                          "-o jsonpath='{.status.phase}'"
            for _ in range(CHECK_PV_AVAILABLE_RETRY):
                result = self._execute_command(
                    commander, ssh_command, NFS_CMD_TIMEOUT, 'common', 5)
                if 'Available' in ','.join(result):
                    break
                else:
                    time.sleep(30)
            else:
                ssh_command = f"kubectl delete pv {pv_name}"
                result = self._execute_command(
                    commander, ssh_command, NFS_CMD_TIMEOUT, 'common', 5)
                raise exceptions.MgmtDriverOtherError(
                    error_message='Failed to register Persistent volume'
                                  '(Status is not "Available" state)')
            ssh_command = f"rm -f {pv_file_path}"
            result = self._execute_command(
                commander, ssh_command, NFS_CMD_TIMEOUT, 'common', 5)

    def _heal_start_storage_server(
            self, context, vnf_instance, vnf_additional_params, heatclient,
            stack_id, target_node_physical_resource_ids, master_username,
            master_password, master_resource_name, master_node):
        master_ssh_ips = []
        if master_node.get('aspect_id'):
            master_resource_list = self._get_resources_list(
                heatclient, stack_id, master_resource_name)
            flag_master, fixed_master_infos, not_fixed_master_infos = \
                self._get_master_node_name(
                    heatclient, master_resource_list,
                    target_node_physical_resource_ids,
                    master_node)
            for value in not_fixed_master_infos.values():
                master_ssh_ips.append(value.get('master_ssh_ip'))
        else:
            resource_info = heatclient.resources.get(
                stack_id, master_node.get('ssh_cp_name'))
            master_ssh_ips.append(resource_info.attributes.get(
                'fixed_ips')[0].get('ip_address'))

        commander, master_ip = self._connect_ssh_scale(
            master_ssh_ips, master_username,
            master_password)

        vnf_package_path = vnflcm_utils._get_vnf_package_path(
            context, vnf_instance.vnfd_id)
        pv_registration_params = \
            vnf_additional_params.get(
                'k8s_cluster_installation_param').get(
                'pv_registration_params')

        pv_name_list = []
        for pv_info in pv_registration_params:
            pv_manifest_file_path = pv_info.get('pv_manifest_file_path')
            pv_file_path = \
                os.path.join(vnf_package_path, pv_manifest_file_path)
            with open(pv_file_path, 'r', encoding='utf-8') as f:
                nfs_pv = yaml.safe_load(f)
                pv_name = nfs_pv.get('metadata').get('name')
                pv_name_list.append(pv_name)

        ssh_command = 'kubectl get pv ' \
                      '-o jsonpath=\'{range.items[*]}' \
                      'status:{@.status.phase},' \
                      'name:{@.metadata.name}{"\\n"}{end}\' | ' \
                      'grep "status:Bound"'
        result = self._execute_command(
            commander, ssh_command, NFS_CMD_TIMEOUT, 'common', 3)
        for result_line in result:
            in_use_pv_name = \
                result_line.replace('\n', '').split(',')[1].split(':')[1]
            if in_use_pv_name in pv_name_list:
                raise exceptions.MgmtDriverOtherError(
                    error_message=f"heal_start failed({in_use_pv_name} "
                                  f"Persistent volume is in use)")

        for pv_name in pv_name_list:
            ssh_command = f"kubectl delete pv {pv_name}"
            result = self._execute_command(
                commander, ssh_command, NFS_CMD_TIMEOUT, 'common', 5)

        ssh_command = 'kubectl get pv ' \
                      '-o jsonpath=\'{range .items[*]}' \
                      '{@.metadata.name}{"\\n"}{end}\''
        for _ in range(CHECK_PV_DEL_COMPLETE_RETRY):
            result = self._execute_command(
                commander, ssh_command, NFS_CMD_TIMEOUT, 'common', 5)
            pv_delete_comp_flag = True
            for result_line in result:
                if result_line.replace('\n', '') in pv_name_list:
                    pv_delete_comp_flag = False
                    break
            if pv_delete_comp_flag:
                break
            else:
                time.sleep(30)
        else:
            raise exceptions.MgmtDriverOtherError(
                error_message='heal_start failed'
                              '(Persistent volume deletion timeout)')

    def _heal_end_storage_server(self, context, vnf_instance,
                                 vnf_additional_params, stack_id, master_node,
                                 master_resource_name, heatclient,
                                 target_node_physical_resource_ids,
                                 master_username, master_password):
        k8s_cluster_installation_param = vnf_additional_params.get(
            'k8s_cluster_installation_param', {})
        proxy = k8s_cluster_installation_param.get('proxy', {})
        ss_installation_params = vnf_additional_params\
            .get('k8s_cluster_installation_param', {}).get('storage_server')
        self._install_storage_server(context, vnf_instance, proxy,
                                     ss_installation_params)
        master_ssh_ips = []
        if master_node.get('aspect_id'):
            master_resource_list = self._get_resources_list(
                heatclient, stack_id, master_resource_name)
            flag_master, fixed_master_infos, not_fixed_master_infos = \
                self._get_master_node_name(
                    heatclient, master_resource_list,
                    target_node_physical_resource_ids,
                    master_node)
            for value in not_fixed_master_infos.values():
                master_ssh_ips.append(value.get('master_ssh_ip'))
        else:
            resource_info = heatclient.resources.get(
                stack_id, master_node.get('ssh_cp_name'))
            master_ssh_ips.append(resource_info.attributes.get(
                'fixed_ips')[0].get('ip_address'))

        commander, master_ip = self._connect_ssh_scale(
            master_ssh_ips, master_username,
            master_password)
        pv_registration_params = vnf_additional_params\
            .get('k8s_cluster_installation_param')\
            .get('pv_registration_params')
        self._register_persistent_volumes(
            context, vnf_instance, commander, master_username,
            master_password, master_ip, pv_registration_params)
