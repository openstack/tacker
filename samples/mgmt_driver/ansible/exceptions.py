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


class AnsibleDriverException(Exception):
    def __init__(self, vdu=None, **kwargs):
        if "details" not in kwargs or not kwargs["details"]:
            kwargs["details"] = "No error information available."

        self.vdu = vdu
        self.message = self.message % kwargs
        super(AnsibleDriverException, self).__init__(self.message)


class InternalErrorException(AnsibleDriverException):
    """Internal Error.

    Define the following upon using this exception:
      - details: the exception message or error information
    """
    message = "Management driver internal error: %(details)s"


class ConfigParserConfigurationError(AnsibleDriverException):
    """Config parser configuration error.

    Define the following upon using this exception:
      - ex_type: the exception type
      - details: the exception message or error information
    """
    message = "Parameter conversion error. "
    "Error encountered in configuring parser: [%(ex_type)s, %(details)s]"


class ConfigParserParsingError(AnsibleDriverException):
    """Config parser parsing error.

    Define the following upon using this exception:
      - cmd: the command being parsed that resulted in error
      - ex_type: the exception type
      - details: the exception message or error information
    """
    message = "Parameter conversion error. "
    "Encountered error in parsing '%(cmd)s': [%(ex_type)s, %(details)s]"


class ConfigValidationError(AnsibleDriverException):
    """Config file validation error.

    Define the following upon using this exception:
      - details: the exception message or error information
    """
    message = "Config file validation error: %(details)s"


class MandatoryKeyNotDefinedError(AnsibleDriverException):
    """Config file validation error. Mandatory key is not defined.

    Define the following upon using this exception:
      - key: the offending key
    """
    message = "Config file validation error. "
    "The key '%(key)s' is not defined."


class InvalidValueError(AnsibleDriverException):
    """Config file validation error. Invalid value for a key is defined.

    Define the following upon using this exception:
      - key: the offending key
    """
    message = "Config file validation error. "
    "Invalid value of '%(key)s' is defined."


class PlaybooksCommandsNotFound(AnsibleDriverException):
    """Config file validation error. Playbooks or commands not found.

    Define the following upon using this exception:
      - key: the offending action key
    """
    message = "Config file validation error. "
    "Playbooks or commands not found for action key: %(key)s"


class InvalidKeyError(AnsibleDriverException):
    """Config file validation error. Invalid key error.

    Define the following upon using this exception:
      - key: the offending key
    """
    message = "Config file validation error. The key '%(key)s' is not valid."


class DataRetrievalError(AnsibleDriverException):
    """Data retrieval error.

    Define the following upon using this exception:
      - details: the exception message or error information
    """
    message = "Data retrieval error: %(details)s"


class CommandExecutionError(AnsibleDriverException):
    """Command execution error.

    Define the following upon using this exception:
      - details: the exception message or error information
    """
    message = "Command execution error: %(details)s"


class CommandExecutionTimeoutError(AnsibleDriverException):
    """Command execution timeout error.

    Define the following upon using this exception:
      - host: the target host for execution
      - cmd: the command executed that caused the error
    """
    message = "Command execution has reached timeout. "
    "Target: %(host)s Command: %(cmd)s"


class CommandConnectionLimitReached(AnsibleDriverException):
    """Command connection attempt limit reached."""
    message = "Connection attempt has reached its limit."


class CommandConnectionError(AnsibleDriverException):
    """Command connection error.

    Define the following upon using this exception:
      - details: the exception message or error information
    """
    message = "Connection attempt error: %(details)s"
