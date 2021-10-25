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
import os
import paramiko
import time

from oslo_log import log as logging

from tacker.common import cmd_executer
from tacker.common import exceptions
from tacker.common import log
from tacker import objects
from tacker.vnflcm import utils as vnflcm_utils
from tacker.vnfm.infra_drivers.openstack import heat_client as hc
from tacker.vnfm.mgmt_drivers import vnflcm_abstract_driver

LOG = logging.getLogger(__name__)
FREE5GC_CMD_TIMEOUT = 30
FREE5GC_MODIFY_CONFIG_TIMEOUT = 60


class Free5gcMgmtDriver(vnflcm_abstract_driver.VnflcmMgmtAbstractDriver):
    def get_type(self):
        return 'mgmt-drivers-free5gc'

    def get_name(self):
        return 'mgmt-drivers-free5gc'

    def get_description(self):
        return 'Tacker VNFMgmt Free5gc Driver'

    @log.log
    def instantiate_start(self, context, vnf_instance,
                          instantiate_vnf_request, grant,
                          grant_request, **kwargs):
        pass

    def _get_vim_connection_info(self, context, instantiate_vnf_req):

        vim_info = vnflcm_utils._get_vim(context,
                instantiate_vnf_req.vim_connection_info)

        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        return vim_connection_info

    def _check_values(self, additional_param):
        if not additional_param.get('username'):
            LOG.error('The username in the '
                      'additionalParams is invalid.')
            raise exceptions.MgmtDriverNotFound(param='username')
        if not additional_param.get('password'):
            LOG.error('The password in the '
                      'additionalParams is invalid.')
            raise exceptions.MgmtDriverNotFound(param='password')
        if not additional_param.get('aspect_id'):
            LOG.error('The aspect_id in the '
                      'additionalParams is invalid.')
            raise exceptions.MgmtDriverNotFound(param='password')
        if not additional_param.get('ssh_cp_name'):
            LOG.error('The ssh_cp_name in the '
                      'additionalParams is invalid.')
            raise exceptions.MgmtDriverNotFound(param='password')
        if not additional_param.get('amf_cp_name'):
            LOG.error('The amf_cp_name in the '
                      'additionalParams is invalid.')
            raise exceptions.MgmtDriverNotFound(param='password')
        if not additional_param.get('smf_cp_name'):
            LOG.error('The smf_cp_name in the '
                      'additionalParams is invalid.')
            raise exceptions.MgmtDriverNotFound(param='password')
        if not additional_param.get('upf_cp_name'):
            LOG.error('The upf_cp_name in the '
                      'additionalParams is invalid.')
            raise exceptions.MgmtDriverNotFound(param='password')
        if not additional_param.get('modify_script_path'):
            LOG.error('The modify_script_path in the '
                      'additionalParams is invalid.')
            raise exceptions.MgmtDriverNotFound(param='ssh_cp_name')

    def _get_group_resources_list(
            self, heatclient, stack_id, aspect_id, additional_params):
        nest_resources_list = heatclient.resources.list(stack_id=stack_id)
        group_stack_name = aspect_id
        if 'lcm-operation-user-data' in additional_params.keys() and \
                'lcm-operation-user-data-class' in additional_params.keys():
            group_stack_name = group_stack_name + '_group'
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

    def _init_commander_and_send_modify_scripts(self, user, password, host,
                        vnf_package_path=None, script_path=None):
        retry = 4
        while retry > 0:
            try:
                if vnf_package_path and script_path:
                    connect = paramiko.Transport(host, 22)
                    connect.connect(username=user, password=password)
                    sftp = paramiko.SFTPClient.from_transport(connect)
                    # put script file content to '/tmp/modify_config.sh'
                    sftp.put(os.path.join(vnf_package_path, script_path),
                             "/tmp/modify_config.sh")
                    connect.close()
                commander = cmd_executer.RemoteCommandExecutor(
                    user=user, password=password, host=host,
                    timeout=30)
                return commander
            except paramiko.SSHException as e:
                LOG.debug(e)
                retry -= 1
                if retry == 0:
                    LOG.error(e)
                    raise paramiko.SSHException()
                time.sleep(120)

    def _execute_command(self, commander, ssh_command, timeout, type, retry,
            input_data=None):
        eventlet.monkey_patch()
        while retry >= 0:
            try:
                with eventlet.Timeout(timeout, True):
                    result = commander.execute_command(
                        ssh_command, input_data=input_data)
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
            if result.get_return_code() != 0:
                err = result.get_stderr()
                LOG.error(err)
                raise exceptions.MgmtDriverRemoteCommandError(err_info=err)
        return result.get_stdout()

    def _get_smf_and_amf_ip(
            self, heatclient, stack_id, amf_cp_name, smf_cp_name):
        amf_cplan_ip = heatclient.resources.get(
            stack_id=stack_id,
            resource_name=amf_cp_name).attributes.get(
            'fixed_ips')[0].get('ip_address')
        smf_pfcp_ip = heatclient.resources.get(
            stack_id=stack_id,
            resource_name=smf_cp_name).attributes.get(
            'fixed_ips')[0].get('ip_address')
        return amf_cplan_ip, smf_pfcp_ip

    def _modify_config_path_and_start_process(
            self, group_resources_list, heatclient,
            vnf_package_path, additional_param, operation_type,
            **kwargs):
        ssh_cp_name = additional_param.get('ssh_cp_name')
        username = additional_param.get('username')
        password = additional_param.get('password')
        amf_cp_name = additional_param.get('amf_cp_name')
        smf_cp_name = additional_param.get('smf_cp_name')
        upf_cp_name = additional_param.get('upf_cp_name')
        modify_script_path = additional_param.get('modify_script_path')

        if operation_type == 'HEAL':
            target_physical_resource_ids = \
                kwargs['target_physical_resource_ids']
            vnf_ssh_ip, heal_stack_id = self._get_vnf_ssh_ip(
                group_resources_list, heatclient, ssh_cp_name,
                target_physical_resource_ids, upf_cp_name)
            ssh_ip = vnf_ssh_ip['heal']
            amf_cplan_ip, smf_pfcp_ip = \
                self._get_smf_and_amf_ip(
                    heatclient, heal_stack_id, amf_cp_name,
                    smf_cp_name)
            upf_pfcp_ip_master = vnf_ssh_ip['upf_pfcp_ip']

        for group_resource in group_resources_list:
            stack_id = group_resource.physical_resource_id
            resource_name = ssh_cp_name
            resource_info = heatclient.resources.get(
                stack_id=stack_id,
                resource_name=resource_name)
            # get ssh_ip
            upf_pfcp_ip_list = []
            if operation_type == 'INSTANTIATE':
                if resource_info.attributes.get('floating_ip_address'):
                    ssh_ip = resource_info.attributes.get(
                        'floating_ip_address')
                else:
                    ssh_ip = heatclient.resources.get(
                        stack_id=stack_id,
                        resource_name=resource_name).attributes.get(
                        'fixed_ips')[0].get('ip_address')
                # get amf,smf,upf's config ip
                amf_cplan_ip, smf_pfcp_ip = \
                    self._get_smf_and_amf_ip(
                        heatclient, stack_id, amf_cp_name,
                        smf_cp_name)
                upf_pfcp_ip_master = heatclient.resources.get(
                    stack_id=stack_id,
                    resource_name=upf_cp_name).attributes.get(
                    'fixed_ips')[0].get('ip_address')
                upf_pfcp_ip_list.append(upf_pfcp_ip_master)
            else:
                upf_pfcp_ip = heatclient.resources.get(
                    stack_id=stack_id,
                    resource_name=upf_cp_name).attributes.get(
                    'fixed_ips')[0].get('ip_address')
                upf_pfcp_ip_list.append(upf_pfcp_ip)

        upf_pfcp_ips_str = ','.join(upf_pfcp_ip_list)
        # get all config file path
        amf_config_path = additional_param.get('amf_config_path')
        if not amf_config_path:
            amf_config_path = '~/free5gc/config/amfcfg.conf'
        smf_config_path = additional_param.get('smf_config_path')
        if not smf_config_path:
            smf_config_path = '~/free5gc/config/smfcfg.conf'
        upf_config_path = additional_param.get('upf_config_path')
        if not upf_config_path:
            upf_config_path = '~/free5gc/src/upf/build/config/upfcfg.yaml'
        start_process_script_path = \
            additional_param.get('start_process_script_path')
        if not start_process_script_path:
            start_process_script_path = '~/free5gc/run.sh'
            start_process_script_dir = \
                start_process_script_path.replace('/run.sh', '')
        web_console_script_path = \
            additional_param.get('web_console_script_path')
        if not web_console_script_path:
            web_console_script_path = '~/free5gc/webconsole/server.go'
        web_console_script_path = web_console_script_path.replace('/server.go',
                                                                  '')
        commander = self._init_commander_and_send_modify_scripts(
            username, password, ssh_ip,
            vnf_package_path, modify_script_path)
        # modify config file
        ssh_command = "bash /tmp/modify_config.sh " \
                      "-A {amf_config_path} -a {amf_cplan_ip} " \
                      "-S {smf_config_path} -s {smf_pfcp_ip} " \
                      "-U {upf_config_path} -u {upf_pfcp_ip} " \
                      "-l {upf_pfcp_ip_str}".format(
                          amf_config_path=amf_config_path,
                          smf_config_path=smf_config_path,
                          upf_config_path=upf_config_path,
                          amf_cplan_ip=amf_cplan_ip,
                          smf_pfcp_ip=smf_pfcp_ip,
                          upf_pfcp_ip=upf_pfcp_ip_master,
                          upf_pfcp_ip_str=upf_pfcp_ips_str)
        self._execute_command(
            commander, ssh_command, FREE5GC_MODIFY_CONFIG_TIMEOUT,
            'common', 0, input_data=password)
        # start all process
        ssh_command = ("cd {start_process_script_dir};"
                       "touch result.txt;"
                       "nohup ./run.sh > result.txt 2>&1 &".format(
                           start_process_script_dir=start_process_script_dir))
        self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT, 'common', 0)
        time.sleep(120)
        # confirm process running
        ssh_command = r'ps -ef | grep "\./bin"'
        results = self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT, 'common', 0)
        free5gc_list = ['free5gc-upfd', 'nrf', 'amf',
                        'smf', 'udr', 'pcf', 'udm', 'nssf', 'ausf']
        count = 0
        for result in results:
            for nf in free5gc_list:
                if nf in result:
                    count = count + 1
                    break
        if count != 10:
            LOG.error('The process of free5gc start failed.')
            raise exceptions.MgmtDriverOtherError(
                error_message='The process of free5gc start failed.')
        # start web console
        ssh_command = ("cd {web_console_script_path}; touch webconsole.txt; "
                       "nohup go run server.go > webconsole.txt 2>&1 &".format(
                           web_console_script_path=web_console_script_path))
        self._execute_command(
            commander, ssh_command, FREE5GC_CMD_TIMEOUT, 'common', 0)
        commander.close_session()

    @log.log
    def instantiate_end(self, context, vnf_instance,
                        instantiate_vnf_request, grant,
                        grant_request, **kwargs):
        # get vim_connect_info
        if hasattr(instantiate_vnf_request, 'vim_connection_info'):
            vim_connection_info = self._get_vim_connection_info(
                context, instantiate_vnf_request)
        else:
            vim_connection_info = self._get_vim_connection_info(
                context, vnf_instance)
        additional_param = instantiate_vnf_request.additional_params.get(
            'free5gc', {})
        self._check_values(additional_param)
        aspect_id = additional_param.get('aspect_id')

        vnf_package_path = vnflcm_utils._get_vnf_package_path(
            context, vnf_instance.vnfd_id)

        access_info = vim_connection_info.access_info
        heatclient = hc.HeatClient(access_info)
        nest_stack_id = vnf_instance.instantiated_vnf_info.instance_id
        group_resources_list = self._get_group_resources_list(
            heatclient, nest_stack_id, aspect_id,
            instantiate_vnf_request.additional_params)
        self._modify_config_path_and_start_process(
            group_resources_list, heatclient, vnf_package_path,
            additional_param, 'INSTANTIATE')

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
        additional_param = vnf_instance.instantiated_vnf_info. \
            additional_params.get('free5gc', {})
        ssh_cp_name = additional_param.get('ssh_cp_name')
        username = additional_param.get('username')
        password = additional_param.get('password')
        nest_stack_id = vnf_instance.instantiated_vnf_info.instance_id
        upf_cp_name = additional_param.get('upf_cp_name')
        upf_config_path = additional_param.get('upf_config_path')
        if not upf_config_path:
            upf_config_path = '~/free5gc/src/upf/build/config/upfcfg.yaml'
        start_process_script_path = \
            additional_param.get('start_process_script_path')
        if not start_process_script_path:
            start_process_script_path = '~/free5gc/run.sh'
            start_process_script_dir = \
                start_process_script_path.replace('/run.sh', '')
        smf_config_path = additional_param.get('smf_config_path')
        if not smf_config_path:
            smf_config_path = '~/free5gc/config/smfcfg.conf'
        vim_connection_info = \
            self._get_vim_connection_info(context, vnf_instance)
        heatclient = hc.HeatClient(vim_connection_info.access_info)
        scale_out_id_list = kwargs.get('scale_out_id_list')
        group_resources_list = self._get_group_resources_list(
            heatclient, nest_stack_id, scale_vnf_request.aspect_id,
            vnf_instance.instantiated_vnf_info.additional_params)
        for group_resource in group_resources_list:
            stack_id = group_resource.physical_resource_id
            if stack_id not in scale_out_id_list:
                resource_name = ssh_cp_name
                resource_info = heatclient.resources.get(
                    stack_id=stack_id,
                    resource_name=resource_name)
                # get ssh_ip
                if resource_info.attributes.get('floating_ip_address'):
                    vnf1_ssh_ip = resource_info.attributes.get(
                        'floating_ip_address')
                else:
                    vnf1_ssh_ip = heatclient.resources.get(
                        stack_id=stack_id,
                        resource_name=resource_name).attributes.get(
                        'fixed_ips')[0].get('ip_address')
            else:
                resource_name = ssh_cp_name
                resource_info = heatclient.resources.get(
                    stack_id=stack_id,
                    resource_name=resource_name)
                # get ssh_ip
                if resource_info.attributes.get('floating_ip_address'):
                    vnf2_ssh_ip = resource_info.attributes.get(
                        'floating_ip_address')
                else:
                    vnf2_ssh_ip = heatclient.resources.get(
                        stack_id=stack_id,
                        resource_name=resource_name).attributes.get(
                        'fixed_ips')[0].get('ip_address')
                upf_pfcp_ip = heatclient.resources.get(
                    stack_id=stack_id,
                    resource_name=upf_cp_name).attributes.get(
                    'fixed_ips')[0].get('ip_address')

        # stop VNF1's smf process
        commander = cmd_executer.RemoteCommandExecutor(
            user=username, password=password,
            host=vnf1_ssh_ip,
            timeout=30)
        ssh_command = "ps -ef | grep smf | awk '{print $2}'"
        process_pid = self._execute_command(
            commander, ssh_command,
            FREE5GC_CMD_TIMEOUT, 'common', 0)[0].replace('\n', '')
        ssh_command = "kill -9 {}".format(process_pid)
        self._execute_command(
            commander, ssh_command,
            FREE5GC_CMD_TIMEOUT, 'common', 0)
        time.sleep(30)
        commander.close_session()

        # modify upf2's config file
        commander = cmd_executer.RemoteCommandExecutor(
            user=username, password=password,
            host=vnf2_ssh_ip,
            timeout=30)
        ssh_command = ('sed -i "s/addr: 172.168.151.92/addr: {upf_pfcp_ip}/g"'
                       ' {upf_config_path}'
                       .format(upf_pfcp_ip=upf_pfcp_ip,
                               upf_config_path=upf_config_path))
        self._execute_command(
            commander, ssh_command,
            FREE5GC_CMD_TIMEOUT, 'common', 0)
        # start upf2
        ssh_command = 'cd {};cd src/upf/build;sudo -E ./bin/free5gc-upfd &'.\
            format(start_process_script_dir)
        self._execute_command(
            commander, ssh_command,
            FREE5GC_CMD_TIMEOUT, 'common', 0)
        commander.close_session()

        # add new upf's config in smf config
        commander = cmd_executer.RemoteCommandExecutor(
            user=username, password=password,
            host=vnf1_ssh_ip,
            timeout=30)
        ssh_command = r"sed -i '/^        node_id:*/a\      UPF2:\\n" \
                      "        type: UPF\\n" \
                      "        node_id: {}' {}".\
            format(upf_pfcp_ip, smf_config_path)
        self._execute_command(
            commander, ssh_command,
            FREE5GC_CMD_TIMEOUT, 'common', 0)
        # start smf process
        ssh_command = "cd {};" \
                      "touch smf.txt;".format(start_process_script_dir)
        self._execute_command(
            commander, ssh_command,
            FREE5GC_CMD_TIMEOUT, 'common', 0)
        ssh_command = "cd {};echo './bin/smf &' | tee run_smf.sh;" \
                      "chmod 777 run_smf.sh".format(start_process_script_dir)
        self._execute_command(
            commander, ssh_command,
            FREE5GC_CMD_TIMEOUT, 'common', 0)
        ssh_command = "cd {};nohup ./run_smf.sh > smf.txt 2>&1 &".format(
            start_process_script_dir)
        self._execute_command(
            commander, ssh_command,
            FREE5GC_CMD_TIMEOUT, 'common', 0)
        commander.close_session()

    def _get_vnfc_resource_id(self, vnfc_resource_info, vnfc_instance_id):
        for vnfc_resource in vnfc_resource_info:
            if vnfc_resource.id == vnfc_instance_id:
                return vnfc_resource
        else:
            return None

    def _get_target_physical_resource_ids(self, vnf_instance,
                                          heal_vnf_request):
        target_physical_resource_ids = []
        for vnfc_instance_id in heal_vnf_request.vnfc_instance_id:
            instantiated_vnf_info = vnf_instance.instantiated_vnf_info
            vnfc_resource_info = instantiated_vnf_info.vnfc_resource_info
            vnfc_resource = self._get_vnfc_resource_id(
                vnfc_resource_info, vnfc_instance_id)
            if vnfc_resource:
                target_physical_resource_ids.append(
                    vnfc_resource.compute_resource.resource_id)

        return target_physical_resource_ids

    @log.log
    def heal_start(self, context, vnf_instance,
                   heal_vnf_request, grant,
                   grant_request, **kwargs):
        if heal_vnf_request.vnfc_instance_id:
            additional_param = vnf_instance.instantiated_vnf_info. \
                additional_params.get('free5gc', {})
            aspect_id = additional_param.get('aspect_id')
            ssh_cp_name = additional_param.get('ssh_cp_name')
            upf_cp_name = additional_param.get('upf_cp_name')
            vim_connection_info = \
                self._get_vim_connection_info(context, vnf_instance)
            heatclient = hc.HeatClient(vim_connection_info.access_info)
            nest_stack_id = vnf_instance.instantiated_vnf_info.instance_id
            group_resources_list = self._get_group_resources_list(
                heatclient, nest_stack_id, aspect_id,
                vnf_instance.instantiated_vnf_info.additional_params)
            if len(group_resources_list) > 1:
                target_physical_resource_ids = \
                    self._get_target_physical_resource_ids(
                        vnf_instance, heal_vnf_request)
                vnf_ssh_ip, _ = self._get_vnf_ssh_ip(
                    group_resources_list, heatclient, ssh_cp_name,
                    target_physical_resource_ids, upf_cp_name)
                vnf1_ssh_ip = vnf_ssh_ip['not_heal']
                # connect to vnf1
                username = additional_param.get('username')
                password = additional_param.get('password')
                commander = cmd_executer.RemoteCommandExecutor(
                    user=username, password=password,
                    host=vnf1_ssh_ip,
                    timeout=30)
                ssh_command = r"ps -ef | grep '\./bin' | grep smf | " \
                              "awk '{print $2}'"
                # stop smf's process
                process = self._execute_command(
                    commander, ssh_command,
                    FREE5GC_CMD_TIMEOUT, 'common', 0)
                if len(process) > 1:
                    process_pid = process[0].replace('\n', '')
                    ssh_command = "kill -9 {}".format(process_pid)
                    self._execute_command(
                        commander, ssh_command,
                        FREE5GC_CMD_TIMEOUT, 'common', 0)
                    time.sleep(30)
                commander.close_session()

    def _get_cp_ip(self, ssh_cp_name, heatclient, stack_id):
        resource_name = ssh_cp_name
        resource_info = heatclient.resources.get(
            stack_id=stack_id,
            resource_name=resource_name)
        # get ssh_ip
        if resource_info.attributes.get('floating_ip_address'):
            cp_ip = resource_info.attributes.get(
                'floating_ip_address')
        else:
            cp_ip = heatclient.resources.get(
                stack_id=stack_id,
                resource_name=resource_name).attributes.get(
                'fixed_ips')[0].get('ip_address')
        return cp_ip

    def _get_vnf_ssh_ip(self, group_resources_list, heatclient,
                        ssh_cp_name, target_physical_resource_ids,
                        upf_cp_name):
        vnf_ssh_ip = {}
        for group_resource in group_resources_list:
            stack_id = group_resource.physical_resource_id
            resource_info_list = heatclient.resources.list(
                stack_id=stack_id)
            for resource in resource_info_list:
                if resource.resource_type == 'OS::Nova::Server' and \
                        resource.physical_resource_id not in \
                        target_physical_resource_ids:
                    vnf_ssh_ip['not_heal'] = self._get_cp_ip(
                        ssh_cp_name, heatclient, stack_id)
                if resource.resource_type == 'OS::Nova::Server' and \
                        resource.physical_resource_id in \
                        target_physical_resource_ids:
                    vnf_ssh_ip['heal'] = self._get_cp_ip(
                        ssh_cp_name, heatclient, stack_id)
                    vnf_ssh_ip['upf_pfcp_ip'] = heatclient.resources.get(
                        stack_id=stack_id,
                        resource_name=upf_cp_name).attributes.get(
                        'fixed_ips')[0].get('ip_address')
                    heal_stack_id = stack_id

        return vnf_ssh_ip, heal_stack_id

    @log.log
    def heal_end(self, context, vnf_instance,
                 heal_vnf_request, grant,
                 grant_request, **kwargs):
        nest_stack_id = vnf_instance.instantiated_vnf_info.instance_id
        additional_param = vnf_instance.instantiated_vnf_info. \
            additional_params.get('free5gc', {})
        ssh_cp_name = additional_param.get('ssh_cp_name')
        username = additional_param.get('username')
        password = additional_param.get('password')
        upf_cp_name = additional_param.get('upf_cp_name')
        upf_config_path = additional_param.get('upf_config_path')
        if not upf_config_path:
            upf_config_path = '~/free5gc/src/upf/build/config/upfcfg.yaml'
        start_process_script_path = \
            additional_param.get('start_process_script_path')
        if not start_process_script_path:
            start_process_script_path = '~/free5gc/run.sh'
            start_process_script_dir = \
                start_process_script_path.replace('/run.sh', '')
        vim_connection_info = \
            self._get_vim_connection_info(context, vnf_instance)
        heatclient = hc.HeatClient(vim_connection_info.access_info)
        aspect_id = additional_param.get('aspect_id')
        group_resources_list = self._get_group_resources_list(
            heatclient, nest_stack_id, aspect_id,
            vnf_instance.instantiated_vnf_info.additional_params)

        if not heal_vnf_request.vnfc_instance_id or len(
                group_resources_list) == 1:
            self.instantiate_end(
                context, vnf_instance,
                vnf_instance.instantiated_vnf_info,
                grant, grant_request, **kwargs)
        else:
            target_physical_resource_ids = \
                self._get_target_physical_resource_ids(
                    vnf_instance, heal_vnf_request)
            vnf_ssh_ip, _ = self._get_vnf_ssh_ip(
                group_resources_list, heatclient, ssh_cp_name,
                target_physical_resource_ids, upf_cp_name)
            vnf_not_heal_ssh_ip = vnf_ssh_ip['not_heal']
            commander = cmd_executer.RemoteCommandExecutor(
                user=username, password=password,
                host=vnf_not_heal_ssh_ip,
                timeout=30)
            ssh_command = r"ps -ef | grep '\./bin' | grep amf | " \
                          "awk '{print $2}'"
            process = self._execute_command(
                commander, ssh_command,
                FREE5GC_CMD_TIMEOUT, 'common', 0)
            if len(process) > 1:
                healed_VM_smf_flag = False

            if not healed_VM_smf_flag:
                vnf2_ssh_ip = vnf_ssh_ip['heal']
                vnf1_ssh_ip = vnf_ssh_ip['not_heal']
                upf_pfcp_ip = vnf_ssh_ip['upf_pfcp_ip']

                # modify upf2's config file and start upf2
                commander = cmd_executer.RemoteCommandExecutor(
                    user=username, password=password,
                    host=vnf2_ssh_ip,
                    timeout=30)
                ssh_command = \
                    'sed -i "s/addr: 172.168.151.92/addr: {upf_pfcp_ip}"' \
                    ' {upf_config_path}'.format(
                        upf_pfcp_ip=upf_pfcp_ip,
                        upf_config_path=upf_config_path)
                self._execute_command(
                    commander, ssh_command,
                    FREE5GC_CMD_TIMEOUT, 'common', 0)
                # start upf2
                ssh_command = 'cd {};cd src/upf/build;' \
                              'sudo -E ./bin/free5gc-upfd &'. \
                    format(start_process_script_dir)
                self._execute_command(
                    commander, ssh_command,
                    FREE5GC_CMD_TIMEOUT, 'common', 0)
                commander.close_session()

                # start vnf1's smf's process
                commander = cmd_executer.RemoteCommandExecutor(
                    user=username, password=password,
                    host=vnf1_ssh_ip,
                    timeout=30)
                ssh_command = "cd {};" \
                              "touch smf.txt;".format(start_process_script_dir)
                self._execute_command(
                    commander, ssh_command,
                    FREE5GC_CMD_TIMEOUT, 'common', 0)
                ssh_command = ("cd {};echo './bin/smf &' | tee run_smf.sh;"
                               "chmod 777 run_smf.sh"
                               .format(start_process_script_dir))
                self._execute_command(
                    commander, ssh_command,
                    FREE5GC_CMD_TIMEOUT, 'common', 0)
                ssh_command = ("cd {};nohup ./run_smf.sh > smf.txt 2>&1 "
                               "&".format(start_process_script_dir))
                self._execute_command(
                    commander, ssh_command,
                    FREE5GC_CMD_TIMEOUT, 'common', 0)
                commander.close_session()
            else:
                vnf_package_path = vnflcm_utils._get_vnf_package_path(
                    context, vnf_instance.vnfd_id)
                self._modify_config_path_and_start_process(
                    group_resources_list, heatclient, vnf_package_path,
                    additional_param, 'HEAL',
                    target_physical_resource_ids=target_physical_resource_ids)

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
