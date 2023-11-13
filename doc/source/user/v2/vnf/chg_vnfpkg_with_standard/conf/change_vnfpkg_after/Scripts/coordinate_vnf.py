# Copyright (C) 2022 Nippon Telegraph and Telephone Corporation
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

from tacker.common import config
from tacker.sol_refactored.common import coord_client


class CoordScript(object):
    def __init__(self, vnfc_param):
        self.vnfc_param = vnfc_param

    def run(self):
        coord_req = self.vnfc_param['LcmCoordRequest']
        coord_req['coordinationActionName'] = (
            "prv.tacker_organization.coordination_test")
        endpoint = self.vnfc_param.get('endpoint')
        authentication = self.vnfc_param.get('authentication')
        timeout = self.vnfc_param.get('timeout')

        input_params = self.vnfc_param.get('inputParams')
        if input_params is not None:
            coord_req['inputParams'] = input_params

        if endpoint is None:
            raise Exception('endpoint must be specified.')
        if authentication is None:
            raise Exception('authentication must be specified.')

        # Reload "tacker.conf" when using OAUTH2_CLIENT_CERT
        # for authentication.
        args = ["--config-file", "/etc/tacker/tacker.conf"]
        config.init(args)

        coord = coord_client.create_coordination(
            endpoint, authentication, coord_req, timeout)
        if coord['coordinationResult'] != "CONTINUE":
            raise Exception(
                f"coordinationResult is {coord['coordinationResult']}")


def main():
    vnfc_param = pickle.load(sys.stdin.buffer)
    script = CoordScript(vnfc_param)
    script.run()


if __name__ == "__main__":
    try:
        main()
        os._exit(0)
    except Exception as ex:
        sys.stderr.write(str(ex))
        sys.stderr.flush()
        os._exit(1)