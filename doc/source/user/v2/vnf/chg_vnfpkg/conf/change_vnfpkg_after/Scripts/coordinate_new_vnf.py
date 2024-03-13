# Copyright (C) 2022 Fujitsu
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
import os
import pickle
import sys
import time

from oslo_log import log as logging
import paramiko

from tacker.sol_refactored.common import exceptions as sol_ex

LOG = logging.getLogger(__name__)
CMD_TIMEOUT = 30
SERVER_WAIT_COMPLETE_TIME = 60
SSH_CONNECT_RETRY_COUNT = 4


class SampleNewCoordinateVNFScript(object):

    def __init__(self, vnfc_param):
        self.vnfc_param = vnfc_param

    def coordinate_vnf(self):
        # check ssh connect and os version
        """(YiFeng) Add comment to check ssh access

            The next part of code is to check connect VM via ssh.
            Since the zuul's network cannot check this content, so
            we comment this part of code. If you want to check them
            in your local environment, please uncomment.
        # user = self.vnfc_param['username']
        # password = self.vnfc_param['password']
        # host = self.vnfc_param['ssh_ip']
        # commander = self._init_commander(
        #     user, password, host, retry=SSH_CONNECT_RETRY_COUNT)
        # ssh_command = 'cat /etc/os-release | grep PRETTY_NAME'
        # result = self._execute_command(commander, host, ssh_command)
        # os_version = result[0].replace('\n', '').split('=')[1]
        # LOG.info('The os version of this new VM is %s', os_version)
        """
        pass

    def _init_commander(self, user, password, host, retry):
        while retry > 0:
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    host, username=user, password=password)
                LOG.info("Connected to %s", host)
                return ssh
            except paramiko.AuthenticationException as e:
                LOG.error("Authentication failed when connecting to %s",
                          host)
                raise sol_ex.VMRunningFailed(e)
            except (paramiko.SSHException,
                    paramiko.ssh_exception.NoValidConnectionsError) as e:
                LOG.debug(e)
                retry -= 1
                if retry == 0:
                    LOG.error(e)
                    raise sol_ex.VMRunningFailed(e)
                time.sleep(SERVER_WAIT_COMPLETE_TIME)

    def _execute_command(self, commander, host, command):
        try:
            stdin, stdout, stderr = commander.exec_command(command)
            cmd_out = stdout.readlines()
            cmd_err = stderr.readlines()
            return_code = stdout.channel.recv_exit_status()
        except paramiko.SSHException as e:
            LOG.error("Command execution failed at %s. Giving up", host)
            raise e
        finally:
            commander.close()
        if return_code != 0:
            error = cmd_err
            raise sol_ex.VMRunningFailed(error_info=error)
        result = "cmd: %s, stdout: %s, stderr: %s, return code: %s" % (
            command, cmd_out, cmd_err, return_code)
        LOG.debug("Remote command execution result: %s", result)
        return cmd_out


def main():
    operation = "coordinate_vnf"
    vnfc_param = pickle.load(sys.stdin.buffer)
    script = SampleNewCoordinateVNFScript(vnfc_param)
    try:
        getattr(script, operation)()
    except Exception:
        raise Exception


if __name__ == "__main__":
    try:
        main()
        os._exit(0)
    except Exception as ex:
        sys.stderr.write(str(ex))
        sys.stderr.flush()
        os._exit(1)