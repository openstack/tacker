# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_log import log as logging
import paramiko

from tacker.common import exceptions

LOG = logging.getLogger(__name__)


class CommandResult(object):
    """Result class contains command, stdout, stderror and return code."""
    def __init__(self, cmd, stdout, stderr, return_code):
        self.__cmd = cmd
        self.__stdout = stdout
        self.__stderr = stderr
        self.__return_code = return_code

    def get_command(self):
        return self.__cmd

    def get_stdout(self):
        return self.__stdout

    def get_stderr(self):
        return self.__stderr

    def get_return_code(self):
        return self.__return_code

    def __str__(self):
        return "cmd: %s, stdout: %s, stderr: %s, return code: %s" \
            % (self.__cmd, self.__stdout, self.__stderr, self.__return_code)

    def __repr__(self):
        return "cmd: %s, stdout: %s, stderr: %s, return code: %s" \
            % (self.__cmd, self.__stdout, self.__stderr, self.__return_code)


class RemoteCommandExecutor(object):
    """Class to execute a command on remote location"""
    def __init__(self, user, password, host, timeout=10):
        self.__user = user
        self.__password = password
        self.__host = host
        self.__paramiko_conn = None
        self.__ssh = None
        self.__timeout = timeout
        self.__connect()

    def __connect(self):
        try:
            self.__ssh = paramiko.SSHClient()
            self.__ssh.set_missing_host_key_policy(paramiko.WarningPolicy())
            self.__ssh.connect(self.__host, username=self.__user,
                password=self.__password, timeout=self.__timeout)
            LOG.info("Connected to %s", self.__host)
        except paramiko.AuthenticationException:
            LOG.error("Authentication failed when connecting to %s",
                      self.__host)
            raise exceptions.NotAuthorized
        except paramiko.SSHException:
            LOG.error("Could not connect to %s. Giving up", self.__host)
            raise

    def close_session(self):
        self.__ssh.close()
        LOG.debug("Connection close")

    def execute_command(self, cmd, input_data=None):
        try:
            stdin, stdout, stderr = self.__ssh.exec_command(cmd)
            if input_data:
                stdin.write(input_data)
                LOG.debug("Input data written successfully")
                stdin.flush()
                LOG.debug("Input data flushed")
                stdin.channel.shutdown_write()

            # NOTE (dkushwaha): There might be a case, when server can take
            # too long time to write data in stdout buffer or sometimes hang
            # itself, in that case readlines() will stuck for long/infinite
            # time. To handle such cases, timeout logic should be introduce
            # here.
            cmd_out = stdout.readlines()
            cmd_err = stderr.readlines()
            return_code = stdout.channel.recv_exit_status()
        except paramiko.SSHException:
            LOG.error("Command execution failed at %s. Giving up", self.__host)
            raise
        result = CommandResult(cmd, cmd_out, cmd_err, return_code)
        LOG.debug("Remote command execution result: %s", result)
        return result

    def __del__(self):
        self.close_session()
