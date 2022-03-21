# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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

import abc

from tacker.sol_refactored.common import exceptions as sol_ex


class AbstractUserData(metaclass=abc.ABCMeta):
    """Definition of each method

    Args:
        req: Request dict for each API
             (ex. InstantiateVnfRequest for instantiate)
        inst: VnfInstance dict
        grant_req: GrantRequest dict
        grant: Grant dict
        tmp_csar_dir: directory path that csar contents are extracted

    Returns:
        dict of parameters for create/update heat stack.
        see the example of userdata_default.py.
    """

    @staticmethod
    @abc.abstractmethod
    def instantiate(req, inst, grant_req, grant, tmp_csar_dir):
        raise sol_ex.UserDataClassNotImplemented()

    @staticmethod
    @abc.abstractmethod
    def scale(req, inst, grant_req, grant, tmp_csar_dir):
        raise sol_ex.UserDataClassNotImplemented()

    @staticmethod
    @abc.abstractmethod
    def change_ext_conn(req, inst, grant_req, grant, tmp_csar_dir):
        raise sol_ex.UserDataClassNotImplemented()

    @staticmethod
    @abc.abstractmethod
    def heal(req, inst, grant_req, grant, tmp_csar_dir):
        raise sol_ex.UserDataClassNotImplemented()
