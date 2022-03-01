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
import paramiko
import yaml

from tacker.common import cmd_executer
from tacker.common import exceptions
from tacker.common import log
from tacker.vnflcm import utils as vnflcm_utils
from tacker.vnfm.mgmt_drivers import vnflcm_abstract_driver

LOG = logging.getLogger(__name__)
FREE5GC_CMD_TIMEOUT = 30


class Free5gcMgmtDriverCnf(vnflcm_abstract_driver.VnflcmMgmtAbstractDriver):
    def get_type(self):
        return 'mgmt-drivers-free5gc-cnf'

    def get_name(self):
        return 'mgmt-drivers-free5gc-cnf'

    def get_description(self):
        return 'Tacker VNFMgmt Free5gc CNF Driver'

    @log.log
    def instantiate_start(self, context, vnf_instance,
                          instantiate_vnf_request, grant,
                          grant_request, **kwargs):
        vnf_package_path = vnflcm_utils._get_vnf_package_path(
            context, vnf_instance.vnfd_id)
        kubernetes_file_paths = instantiate_vnf_request.\
            additional_params.get('lcm-kubernetes-def-files')
        for path in kubernetes_file_paths:
            if 'configmap' in path:
                configmap_path = os.path.join(vnf_package_path, path)
            if 'amf' in path:
                amf_path = os.path.join(vnf_package_path, path)
            if 'smf' in path:
                smf_path = os.path.join(vnf_package_path, path)
            if 'upf' in path:
                upf_path = os.path.join(vnf_package_path, path)
        with open(amf_path) as f:
            results = yaml.safe_load_all(f)
            for result in results:
                if result.get('kind') == 'Deployment':
                    amf_init_containers = result.get('spec').get(
                        'template').get('spec').get('initContainers')
                    amf_ip_list = []
                    for amf_init_container in amf_init_containers:
                        amf_ip_args = amf_init_container.get('args')
                        for amf_ip_arg in amf_ip_args:
                            if '-i=' in amf_ip_arg:
                                amf_ip = amf_ip_arg.replace('-i=', '')
                                amf_ip = amf_ip.partition('/')[0]
                                amf_ip_list.append(amf_ip)
        with open(smf_path) as f:
            results = yaml.safe_load_all(f)
            for result in results:
                if result.get('kind') == 'Deployment':
                    smf_init_containers = result.get('spec').get(
                        'template').get('spec').get('initContainers')
                    smf_ip_list = []
                    for smf_init_container in smf_init_containers:
                        smf_ip_args = smf_init_container.get('args')
                        for smf_ip_arg in smf_ip_args:
                            if '-i=' in smf_ip_arg:
                                smf_ip = smf_ip_arg.replace('-i=', '')
                                smf_ip = smf_ip.partition('/')[0]
                                smf_ip_list.append(smf_ip)
        with open(upf_path) as f:
            results = yaml.safe_load_all(f)
            for result in results:
                if result.get('kind') == 'Deployment':
                    upf_init_containers = result.get('spec').get(
                        'template').get('spec').get('initContainers')
                    upf_ip_list = []
                    for upf_init_container in upf_init_containers:
                        upf_ip_args = upf_init_container.get('args')
                        for upf_ip_arg in upf_ip_args:
                            if '-i=' in upf_ip_arg:
                                upf_ip = upf_ip_arg.replace('-i=', '')
                                upf_ip = upf_ip.partition('/')[0]
                                upf_ip_list.append(upf_ip)

        with open(configmap_path, encoding='utf-8') as f:
            results = yaml.safe_load_all(f)
            for result in results:
                # check amfcfg.yaml in configmap
                amf_file = result.get('data').get('amfcfg.yaml')
                index_start = \
                    amf_file.index('ngapIpList') + len('ngapIpList') + 1
                index_end = amf_file.index('sbi')
                amf_ip_str = amf_file[index_start:index_end]
                count = 0
                for amf_ip in amf_ip_list:
                    if amf_ip in amf_ip_str:
                        count = count + 1
                if count == 0:
                    LOG.error('The configmap of amfcfg.yaml is invalid.'
                              ' "ngapIpList" may be wrong.')
                    raise exceptions.MgmtDriverOtherError(
                        'The configmap of amfcfg.yaml is invalid.'
                        ' "ngapIpList" may be wrong.')

                # check smfcfg.yaml in configmap
                smf_file = result.get('data').get('smfcfg.yaml')
                index_start = smf_file.index('pfcp') + len('pfcp') + 1
                index_end = smf_file.index('userplane_information')
                smf_ip_str = smf_file[index_start:index_end]
                for smf_pfcp in smf_ip_list:
                    if smf_pfcp in smf_ip_str:
                        break
                else:
                    LOG.error('The configmap of smfcfg.yaml is invalid.'
                              ' "pfcp" may be wrong.')
                    raise exceptions.MgmtDriverOtherError(
                        'The configmap of smfcfg.yaml is invalid.'
                        ' "pfcp" may be wrong.')
                index_start2 = smf_file.index('UPF:') + len('UPF:') + 1
                index_end2 = smf_file.index('sNssaiUpfInfos')
                upf_pfcp_ip_str = smf_file[index_start2:index_end2]
                for upf_ip in upf_ip_list:
                    if upf_ip in upf_pfcp_ip_str:
                        break
                else:
                    LOG.error('The configmap of smfcfg.yaml is invalid.'
                              ' The node_id of UPF may be wrong.')
                    raise exceptions.MgmtDriverOtherError(
                        'The configmap of smfcfg.yaml is invalid.'
                        ' The node_id of UPF may be wrong.')

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
        if type == 'common':
            err = result.get_stderr()
            if err:
                LOG.error(err)
                raise exceptions.MgmtDriverRemoteCommandError(err_info=err)
        return result.get_stdout()

    def _check_values(self, additional_param):
        if not additional_param.get('master_node_username'):
            LOG.error('The master_node_username in the '
                      'additionalParams cannot be None.')
            raise exceptions.MgmtDriverNotFound(
                param='master_node_username')
        if not additional_param.get('master_node_password'):
            LOG.error('The master_node_password in the '
                      'additionalParams cannot be None.')
            raise exceptions.MgmtDriverNotFound(
                param='master_node_username')
        if not additional_param.get('ssh_master_node_ip'):
            LOG.error('The ssh_master_node_ip in the '
                      'additionalParams cannot be None.')
            raise exceptions.MgmtDriverNotFound(
                param='ssh_master_node_ip')

    def _send_and_receive_file(self, host, user, password,
                               remote_file, local_file, operation):
        connect = paramiko.Transport(host, 22)
        connect.connect(username=user, password=password)
        sftp = paramiko.SFTPClient.from_transport(connect)
        if operation == 'receive':
            sftp.get(remote_file, local_file)
        else:
            sftp.put(local_file, remote_file)
        connect.close()

    @log.log
    def instantiate_end(self, context, vnf_instance,
                        instantiate_vnf_request, grant,
                        grant_request, **kwargs):
        additional_param = instantiate_vnf_request.\
            additional_params.get('free5gc', {})
        self._check_values(additional_param)
        ssh_master_node_ip = additional_param.get('ssh_master_node_ip')
        master_node_username = additional_param.get('master_node_username')
        master_node_password = additional_param.get('master_node_password')
        if not additional_param.get('upf_config_file_path'):
            upf_config_file_path = \
                '/go/src/free5gc/NFs/upf/build/config/upfcfg.yaml'
        if not additional_param.get('smf_config_file_path'):
            smf_config_file_path = '/go/src/free5gc/config/smfcfg.yaml'

        commander = cmd_executer.RemoteCommandExecutor(
            user=master_node_username, password=master_node_password,
            host=ssh_master_node_ip,
            timeout=30)
        # get upf ip from smf
        ssh_command = "kubectl get pod | grep smf | awk '{print $1}'"
        smf_pod_name = self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)[0].replace('\n', '')
        ssh_command = ("kubectl cp {smf_pod_name}:{smf_config_file_path}"
                       " /tmp/smfcfg.yaml"
                       .format(smf_pod_name=smf_pod_name,
                               smf_config_file_path=smf_config_file_path))
        self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)
        local_smf_path = '/tmp/smfcfg.yaml'
        self._send_and_receive_file(
            ssh_master_node_ip, master_node_username, master_node_password,
            '/tmp/smfcfg.yaml', local_smf_path, 'receive')
        upf_gtpu_list = []
        with open(local_smf_path) as f:
            file_content = yaml.safe_load(f)
            upf_pfcp_ip = file_content['configuration'][
                'userplane_information']['up_nodes']['UPF']['node_id']
            upf_gtpu_interface_list = file_content['configuration'][
                'userplane_information']['up_nodes']['UPF']['interfaces']
            for upf_gtpu_interface in upf_gtpu_interface_list:
                upf_gtpu_list = (upf_gtpu_interface['endpoints'] +
                                 upf_gtpu_list)

        # modify upf info
        upf_example_file_path = \
            '/go/src/free5gc/NFs/upf/build/config/upfcfg.yaml'
        ssh_command = "kubectl get pod | grep upf | awk '{print $1}'"
        upf_pod_name = self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)[0].replace('\n', '')
        ssh_command = ("kubectl cp {upf_pod_name}:{upf_example_file_path}"
                       " /tmp/upfcfg.yaml -c myapp-container"
                       .format(upf_pod_name=upf_pod_name,
                               upf_example_file_path=upf_example_file_path))
        self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)
        local_upf_path = '/tmp/upfcfg.yaml'
        self._send_and_receive_file(
            ssh_master_node_ip, master_node_username, master_node_password,
            '/tmp/upfcfg.yaml', local_upf_path, 'receive')
        with open(local_upf_path, 'r') as f:
            upf_content = yaml.safe_load(f)
            upf_content['configuration']['pfcp'][0]['addr'] = upf_pfcp_ip
            for index in range(len(upf_gtpu_list)):
                upf_content['configuration']['gtpu'][index]['addr'] =\
                    upf_gtpu_list[index]
        with open(local_upf_path, 'w') as nf:
            yaml.safe_dump(upf_content, nf, default_flow_style=False)
        self._send_and_receive_file(
            ssh_master_node_ip, master_node_username, master_node_password,
            '/tmp/upfcfg.yaml', local_upf_path, 'send')
        ssh_command = ("kubectl cp /tmp/upfcfg.yaml"
                       " {upf_pod_name}:{upf_config_file_path}"
                       " -c myapp-container"
                       .format(upf_pod_name=upf_pod_name,
                               upf_config_file_path=upf_config_file_path))
        self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)

        # start upf process
        ssh_command = ('cat <<EOF | sudo tee "run_upf.sh" >/dev/null\n'
                       'kubectl exec'
                       ' {} -i -- sh'
                       '<< eof\n'
                       'ip link delete upfgtp\neof\n'
                       'kubectl exec'
                       ' {} -i -- sh'
                       '<< eof\n'
                       './NFs/upf/build/bin/free5gc-upfd -f {}\neof'
                       '\nEOF\n'
                       .format(upf_pod_name, upf_pod_name,
                               upf_config_file_path))
        self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)
        ssh_command = "sudo chmod 777 run_upf.sh"
        self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)
        ssh_command = "nohup ./run_upf.sh > upf.txt  2>&1 &"
        self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)

        # restart smf
        ssh_command = "kubectl get pod {} -o yaml | " \
                      "kubectl replace --force -f -".format(smf_pod_name)
        self._execute_command(
            commander, ssh_command, 120,
            'common', 0)
        time.sleep(120)
        ssh_command = "kubectl get pod | grep smf | awk '{print $1}'"
        smf_pod_name = self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)[0].replace('\n', '')
        ssh_command = "kubectl get pod {} | " \
                      "grep 'Running'".format(smf_pod_name)
        result = self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 0)
        if not result:
            LOG.error('SMF restart failed. Please check'
                      ' you k8s-cluster environment.')
            raise exceptions.MgmtDriverOtherError(
                'SMF restart failed. Please check you'
                ' k8s-cluster environment.')
        commander.close_session()
        os.remove(local_upf_path)
        os.remove(local_smf_path)

    @log.log
    def terminate_start(self, context, vnf_instance,
                        terminate_vnf_request, grant,
                        grant_request, **kwargs):
        pass

    @log.log
    def terminate_end(self, context, vnf_instance,
                      terminate_vnf_request, grant,
                      grant_request, **kwargs):
        pass

    @log.log
    def scale_start(self, context, vnf_instance,
                    scale_vnf_request, grant,
                    grant_request, **kwargs):
        pass

    @log.log
    def scale_end(self, context, vnf_instance,
                  scale_vnf_request, grant,
                  grant_request, **kwargs):
        additional_param = vnf_instance.instantiated_vnf_info.\
            additional_params.get('free5gc', {})
        ssh_master_node_ip = additional_param.get('ssh_master_node_ip')
        master_node_username = additional_param.get('master_node_username')
        master_node_password = additional_param.get('master_node_password')
        if not additional_param.get('upf_config_file_path'):
            upf_config_file_path = \
                '/go/src/free5gc/NFs/upf/build/config/upfcfg.yaml'
        if not additional_param.get('smf_config_file_path'):
            smf_config_file_path = '/go/src/free5gc/config/smfcfg.yaml'

        commander = cmd_executer.RemoteCommandExecutor(
            user=master_node_username, password=master_node_password,
            host=ssh_master_node_ip,
            timeout=30)
        ssh_command = "kubectl get pod | grep smf | awk '{print $1}'"
        smf_pod_name = self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)[0].replace('\n', '')
        # get upf2's ip from smfcfg.yaml
        ssh_command = ("kubectl cp {smf_pod_name}:{smf_config_file_path}"
                       " /tmp/smfcfg.yaml -c myapp-container"
                       .format(smf_pod_name=smf_pod_name,
                               smf_config_file_path=smf_config_file_path))
        self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)
        local_smf_path = '/tmp/smfcfg.yaml'
        self._send_and_receive_file(
            ssh_master_node_ip, master_node_username, master_node_password,
            '/tmp/smfcfg.yaml', local_smf_path, 'receive')
        upf_gtpu_list = []
        with open(local_smf_path) as f:
            file_content = yaml.safe_load(f)
            upf_pfcp_ip = file_content['configuration'][
                'userplane_information']['up_nodes']['UPF2']['node_id']
            upf_gtpu_interface_list = file_content['configuration'][
                'userplane_information']['up_nodes']['UPF2']['interfaces']
            for upf_gtpu_interface in upf_gtpu_interface_list:
                upf_gtpu_list = (upf_gtpu_interface['endpoints'] +
                                 upf_gtpu_list)

        # modify upf2's config file
        ssh_command = "kubectl get pod | grep upf | awk '{print $5}'"
        upf_pod_age_list = self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)
        count = 1
        age_all = {}
        age_day = 0
        age_h = 0
        age_m = 0
        age_s = 0
        for age in upf_pod_age_list:
            if 'd' in age:
                age_day = age.split('d')[0]
                if 'h' in age:
                    age_h = age.split('d')[1].split('h')[0]
            elif 'h' in age and not age_h:
                age_h = age.split('h')[0]
                if 'm' in age:
                    age_m = age.split('h')[1].split('m')[0]
            elif 'm' in age and not age_m:
                age_m = age.split('m')[0]
                if 's' in age:
                    age_s = age.split('m')[1].split('s')[0]
            elif 's' in age and not age_s:
                age_s = age.split('s')[0]
            age_all[count] = \
                int(age_day) * 24 * 60 * 60 + int(age_h) * 60 * 60 +\
                int(age_m) * 60 + int(age_s) * 60
            count = count + 1
        age1 = age_all[1]
        age2 = age_all[2]
        if age1 > age2:
            scale_count = 1
        else:
            scale_count = 0
        ssh_command = ("kubectl get pod | grep upf | grep Running | awk '{"
                       "print $1}'")
        upf_pod_name_list = self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)
        upf2_pod_name = upf_pod_name_list[scale_count].replace('\n', '')
        upf_example_file_path = \
            '/go/src/free5gc/NFs/upf/build/config/upfcfg.yaml'
        ssh_command = ("kubectl cp {upf_pod_name}:{upf_example_file_path}"
                       " /tmp/upfcfg.yaml -c myapp-container"
                       .format(upf_pod_name=upf2_pod_name,
                               upf_example_file_path=upf_example_file_path))
        self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)
        local_upf_path = '/tmp/upfcfg.yaml'
        self._send_and_receive_file(
            ssh_master_node_ip, master_node_username, master_node_password,
            '/tmp/upfcfg.yaml', local_upf_path, 'receive')
        with open(local_upf_path, 'r') as f:
            upf_content = yaml.safe_load(f)
            upf_content['configuration']['pfcp'][0]['addr'] = upf_pfcp_ip
            for index in range(len(upf_gtpu_list)):
                upf_content['configuration']['gtpu'][index]['addr'] = \
                    upf_gtpu_list[index]
        with open(local_upf_path, 'w') as nf:
            yaml.safe_dump(upf_content, nf, default_flow_style=False)
        self._send_and_receive_file(
            ssh_master_node_ip, master_node_username, master_node_password,
            '/tmp/upfcfg.yaml', local_upf_path, 'send')
        ssh_command = ("kubectl cp /tmp/upfcfg.yaml"
                       " {upf_pod_name}:{upf_config_file_path} "
                       "-c myapp-container"
                       .format(upf_pod_name=upf2_pod_name,
                               upf_config_file_path=upf_config_file_path))
        self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)
        ssh_command = ("kubectl exec {upf2_pod_name} -c myapp-container -- "
                       "ifconfig eth1 {ip}/24"
                       .format(upf2_pod_name=upf2_pod_name,
                               ip=upf_gtpu_list[0]))
        self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)
        ssh_command = ("kubectl exec {upf2_pod_name} -c myapp-container -- "
                       "ifconfig eth2 {ip}/23"
                       .format(upf2_pod_name=upf2_pod_name, ip=upf_pfcp_ip))
        self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)
        ssh_command = ("kubectl exec {upf2_pod_name} -c myapp-container -- "
                       "ifconfig eth3 192.168.52.253/24"
                       .format(upf2_pod_name=upf2_pod_name))
        self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)
        # start upf process
        ssh_command = ('cat <<EOF | sudo tee "run_upf2.sh" >/dev/null\n'
                       'kubectl exec'
                       ' {} -i -- sh'
                       '<< eof\n'
                       'ip link delete upfgtp\neof\n'
                       'kubectl exec'
                       ' {} -i -- sh'
                       '<< eof\n'
                       './NFs/upf/build/bin/free5gc-upfd -f {}\neof'
                       '\nEOF\n'.format(upf2_pod_name, upf2_pod_name,
                                        upf_config_file_path))
        self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)
        ssh_command = "sudo chmod 777 run_upf2.sh"
        self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)
        ssh_command = "nohup ./run_upf2.sh > upf2.txt 2>&1 &"
        self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)

        # restrat smf process
        ssh_command = "kubectl get pod {} -o yaml | " \
                      "kubectl replace --force -f -".format(smf_pod_name)
        self._execute_command(
            commander, ssh_command, 120,
            'common', 0)
        time.sleep(120)
        ssh_command = "kubectl get pod | grep smf | awk '{print $1}'"
        smf_pod_name = self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)[0].replace('\n', '')
        ssh_command = "kubectl get pod {} | " \
                      "grep 'Running'".format(smf_pod_name)
        result = self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 0)
        if not result:
            LOG.error('SMF restart failed. Please check'
                      ' you k8s-cluster environment.')
            raise exceptions.MgmtDriverOtherError(
                'SMF restart failed. Please check you'
                ' k8s-cluster environment.')
        commander.close_session()
        os.remove(local_smf_path)
        os.remove(local_upf_path)

        # if pod-affinity rule exists, check the pod deployed on different
        # worker
        affinity_flag = False
        artifact_files = vnf_instance.instantiated_vnf_info.\
            additional_params.get('lcm-kubernetes-def-files', {})
        vnf_package_path = vnflcm_utils._get_vnf_package_path(
            context, vnf_instance.vnfd_id)
        for artifact_file in artifact_files:
            if 'upf' in artifact_file:
                upf_file_path = os.path.join(
                    vnf_package_path, artifact_file)
                LOG.debug('upf_path:{}'.format(upf_file_path))
                with open(upf_file_path) as f:
                    yaml_content_all = yaml.safe_load_all(f.read())
                for yaml_content in yaml_content_all:
                    if (yaml_content['spec']['template']['spec']
                            .get('affinity')):
                        affinity_rule = (yaml_content['spec']['template']
                                         ['spec'].get('affinity'))
                        if affinity_rule.get('podAntiAffinity'):
                            affinity_flag = True
        LOG.debug('affinity_flag:{}'.format(affinity_flag))
        if affinity_flag:
            commander = cmd_executer.RemoteCommandExecutor(
                user=master_node_username, password=master_node_password,
                host=ssh_master_node_ip,
                timeout=30)
            ssh_command = ("kubectl get pod -o wide | grep 'upf' | awk '{"
                           "print $7}'")
            result = self._execute_command(
                commander, ssh_command, FREE5GC_CMD_TIMEOUT,
                'common', 0)
            if result[0] == result[1]:
                LOG.error('The pod-affinity rule doesn\'t worker.'
                          ' Please check your yaml file {}'.format(
                              upf_file_path))
                raise exceptions.MgmtDriverOtherError(
                    'The pod-affinity rule doesn\'t worker.'
                    ' Please check your yaml file {}'.format(
                        upf_file_path))
            else:
                LOG.debug('The pod has deployed on different worker node.')

    @log.log
    def heal_start(self, context, vnf_instance,
                   heal_vnf_request, grant,
                   grant_request, **kwargs):
        pass

    @log.log
    def heal_end(self, context, vnf_instance,
                 heal_vnf_request, grant,
                 grant_request, **kwargs):
        additional_param = vnf_instance.instantiated_vnf_info. \
            additional_params.get('free5gc', {})
        ssh_master_node_ip = additional_param.get('ssh_master_node_ip')
        master_node_username = additional_param.get('master_node_username')
        master_node_password = additional_param.get('master_node_password')
        if not additional_param.get('smf_config_file_path'):
            smf_config_file_path = '/go/src/free5gc/config/smfcfg.yaml'
        if not additional_param.get('upf_config_file_path'):
            upf_config_file_path = \
                '/go/src/free5gc/NFs/upf/build/config/upfcfg.yaml'
        commander = cmd_executer.RemoteCommandExecutor(
            user=master_node_username, password=master_node_password,
            host=ssh_master_node_ip,
            timeout=30)
        ssh_command = "kubectl get pod | grep upf | awk '{print $5}'"
        upf_pod_age_list = self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT,
            'common', 3)
        if len(upf_pod_age_list) > 1:
            # get upf ip
            ssh_command = "kubectl get pod | grep smf | awk '{print $1}'"
            smf_pod_name = self._execute_command(
                commander, ssh_command, FREE5GC_CMD_TIMEOUT,
                'common', 3)[0].replace('\n', '')
            ssh_command = ("kubectl cp {smf_pod_name}:{smf_config_file_path}"
                           " /tmp/smfcfg.yaml -c myapp-container"
                           .format(smf_pod_name=smf_pod_name,
                                   smf_config_file_path=smf_config_file_path))
            self._execute_command(
                commander, ssh_command, FREE5GC_CMD_TIMEOUT,
                'common', 3)
            local_smf_path = '/tmp/smfcfg.yaml'
            self._send_and_receive_file(
                ssh_master_node_ip, master_node_username, master_node_password,
                '/tmp/smfcfg.yaml', local_smf_path, 'receive')
            with open(local_smf_path) as f:
                file_content = yaml.safe_load(f)
                upf1_pfcp_ip = file_content['configuration'][
                    'userplane_information']['up_nodes']['UPF']['node_id']
                upf2_pfcp_ip = file_content['configuration'][
                    'userplane_information']['up_nodes']['UPF2']['node_id']
            ssh_command = "kubectl get pod | grep upf | awk '{print $1}'"
            upf_pod_name_list = self._execute_command(
                commander, ssh_command, FREE5GC_CMD_TIMEOUT,
                'common', 3)
            for upf_pod in upf_pod_name_list:
                upf_example_file_path = \
                    '/go/src/free5gc/NFs/upf/build/config/upfcfg.yaml'
                ssh_command = "kubectl exec {} -c myapp-container --" \
                              " cat {}".format(upf_pod.replace('\n', ''),
                                               upf_example_file_path)
                results = self._execute_command(
                    commander, ssh_command, FREE5GC_CMD_TIMEOUT,
                    'common', 3)
                for result in results:
                    if upf1_pfcp_ip in result:
                        flag = 'UPF2'
                        unhealed_upf_pod_name = upf_pod
                        break
                    if upf2_pfcp_ip in result:
                        flag = 'UPF'
                        unhealed_upf_pod_name = upf_pod
            upf_pod_name_list.remove(unhealed_upf_pod_name)
            upf_pod_name = upf_pod_name_list[0].replace('\n', '')
            upf_gtpu_list = []
            with open(local_smf_path) as f:
                file_content = yaml.safe_load(f)
                if flag == 'UPF':
                    upf_pfcp_ip = file_content['configuration'][
                        'userplane_information']['up_nodes']['UPF']['node_id']
                    upf_gtpu_interface_list = (
                        file_content['configuration']['userplane_information']
                        ['up_nodes']['UPF']['interfaces'])
                    for upf_gtpu_interface in upf_gtpu_interface_list:
                        upf_gtpu_list = (upf_gtpu_interface['endpoints'] +
                                         upf_gtpu_list)
                else:
                    upf_pfcp_ip = file_content['configuration'][
                        'userplane_information']['up_nodes']['UPF2']['node_id']
                    upf_gtpu_interface_list = (
                        file_content['configuration']['userplane_information']
                        ['up_nodes']['UPF2']['interfaces'])
                    for upf_gtpu_interface in upf_gtpu_interface_list:
                        upf_gtpu_list = (upf_gtpu_interface['endpoints'] +
                                         upf_gtpu_list)
            # modify upf config file
            upf_example_file_path = \
                '/go/src/free5gc/NFs/upf/build/config/upfcfg.yaml'
            ssh_command = ("kubectl cp {upf_pod_name}:{upf_example_file_path}"
                           " /tmp/upfcfg.yaml -c myapp-container".format(
                               upf_pod_name=upf_pod_name,
                               upf_example_file_path=upf_example_file_path))
            self._execute_command(
                commander, ssh_command, FREE5GC_CMD_TIMEOUT,
                'common', 3)
            local_upf_path = '/tmp/upfcfg.yaml'
            self._send_and_receive_file(
                ssh_master_node_ip, master_node_username, master_node_password,
                '/tmp/upfcfg.yaml', local_upf_path, 'receive')
            with open(local_upf_path, 'r') as f:
                upf_content = yaml.safe_load(f)
                upf_content['configuration']['pfcp'][0]['addr'] = upf_pfcp_ip
                for index in range(len(upf_gtpu_list)):
                    upf_content['configuration']['gtpu'][index]['addr'] = \
                        upf_gtpu_list[index]
            with open(local_upf_path, 'w') as nf:
                yaml.safe_dump(upf_content, nf, default_flow_style=False)
            self._send_and_receive_file(
                ssh_master_node_ip, master_node_username, master_node_password,
                '/tmp/upfcfg.yaml', local_upf_path, 'send')
            ssh_command = ("kubectl cp /tmp/upfcfg.yaml"
                           " {upf_pod_name}:{upf_config_file_path}"
                           " -c myapp-container"
                           .format(upf_pod_name=upf_pod_name,
                                   upf_config_file_path=upf_config_file_path))
            self._execute_command(
                commander, ssh_command, FREE5GC_CMD_TIMEOUT,
                'common', 3)

            # start upf process
            ssh_command = ('cat <<EOF | sudo tee "run_upf.sh" >/dev/null\n'
                           'kubectl exec'
                           ' {} -i -- sh'
                           '<< eof\n'
                           'ip link delete upfgtp\neof\n'
                           'kubectl exec'
                           ' {} -i -- sh'
                           '<< eof\n'
                           './NFs/upf/build/bin/free5gc-upfd -f {}\neof'
                           '\nEOF\n'
                           .format(upf_pod_name, upf_pod_name,
                                   upf_config_file_path))
            self._execute_command(
                commander, ssh_command, FREE5GC_CMD_TIMEOUT,
                'common', 3)
            ssh_command = "sudo chmod 777 run_upf.sh"
            self._execute_command(
                commander, ssh_command, FREE5GC_CMD_TIMEOUT,
                'common', 3)
            ssh_command = "nohup ./run_upf.sh > upf_heal.txt  2>&1 &"
            self._execute_command(
                commander, ssh_command, FREE5GC_CMD_TIMEOUT,
                'common', 3)

            # restart smf
            ssh_command = "kubectl get pod {} -o yaml | " \
                          "kubectl replace --force -f -".format(smf_pod_name)
            self._execute_command(
                commander, ssh_command, 120,
                'common', 0)
            time.sleep(120)
            ssh_command = "kubectl get pod | grep smf | awk '{print $1}'"
            smf_pod_name = self._execute_command(
                commander, ssh_command, FREE5GC_CMD_TIMEOUT,
                'common', 3)[0].replace('\n', '')
            ssh_command = "kubectl get pod {} | " \
                          "grep 'Running'".format(smf_pod_name)
            result = self._execute_command(
                commander, ssh_command, FREE5GC_CMD_TIMEOUT,
                'common', 0)
            if not result:
                LOG.error('SMF restart failed. Please check'
                          ' you k8s-cluster environment.')
                raise exceptions.MgmtDriverOtherError(
                    'SMF restart failed. Please check you'
                    ' k8s-cluster environment.')
            commander.close_session()
            os.remove(local_upf_path)
            os.remove(local_smf_path)
        else:
            self.instantiate_end(context, vnf_instance,
                                 vnf_instance.instantiated_vnf_info, grant,
                                 grant_request, **kwargs)

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
