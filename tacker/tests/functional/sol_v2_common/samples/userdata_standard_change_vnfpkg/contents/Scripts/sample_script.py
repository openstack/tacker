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

import functools
import os
import pickle
import sys

from tacker.common import config
from tacker.sol_refactored.common import coord_client


class FailScript(object):
    """Define error method for each operation

    For example:

    def instantiate_start(self):
        if os.path.exists('/tmp/instantiate_start')
            raise Exception('test instantiate_start error')
    """

    def __init__(self, req, inst, grant_req, grant, csar_dir):
        self.req = req
        self.inst = inst
        self.grant_req = grant_req
        self.grant = grant
        self.csar_dir = csar_dir

    def _fail(self, method):
        if os.path.exists(f'/tmp/{method}'):
            raise Exception(f'test {method} error')

    def __getattr__(self, name):
        return functools.partial(self._fail, name)


class CoordScript(object):
    # Sample script for notify coordination server of
    # vnfc_id to process first
    def __init__(self, operation, req, inst, grant_req):
        self.operation = operation
        self.req = req
        self.inst = inst
        self.grant_req = grant_req

    def run(self):
        if (self.operation != 'change_current_package_start' or
                not os.path.exists('/tmp/change_vnfpkg_coordination')):
            return

        if self.grant_req.get('removeResources') is None:
            return

        vnfc_res_ids = [res_def['resource']['resourceId']
                        for res_def in self.grant_req['removeResources']
                        if res_def['type'] == 'COMPUTE']
        vnfcs = [vnfc for vnfc
                 in self.inst['instantiatedVnfInfo']['vnfcResourceInfo']
                 if vnfc['computeResource']['resourceId'] in vnfc_res_ids]

        coord_req = {}
        for vnfc_info in self.inst['instantiatedVnfInfo']['vnfcInfo']:
            if vnfc_info['vnfcResourceInfoId'] == vnfcs[0]['id']:
                # just example
                coord_req['inputParams'] = {'vnfc_info_id': vnfc_info['id']}
                break

        coord_req['vnfInstanceId'] = self.inst['id']
        coord_req['vnfLcmOpOccId'] = self.grant_req['vnfLcmOpOccId']
        coord_req['lcmOperationType'] = self.grant_req['operation']
        coord_req['coordinationActionName'] = (
            "prv.tacker_organization.coordination_test")
        coord_req['_links'] = self.grant_req['_links']

        for vdu_param in self.req['additionalParams']['vdu_params']:
            if vnfcs[0]['vduId'] == vdu_param['vdu_id']:
                vnfc_param = vdu_param['new_vnfc_param']
                break

        endpoint = vnfc_param.get('endpoint')
        authentication = vnfc_param.get('authentication')
        timeout = vnfc_param.get('timeout')

        if endpoint is None:
            raise Exception('endpoint must be specified.')
        if authentication is None:
            raise Exception('authentication must be specified.')

        # Reload "tacker.conf" when using OAUTH2_CLIENT_CERT
        # for authentication.
        args = ["--config-file", "/etc/tacker/tacker.conf"]
        config.init(args)

        coord = coord_client.create_coordination(endpoint, authentication,
                                                 coord_req, timeout)
        if coord['coordinationResult'] != "CONTINUE":
            raise Exception(
                f"coordinationResult is {coord['coordinationResult']}")


def main():
    script_dict = pickle.load(sys.stdin.buffer)

    operation = script_dict['operation']
    req = script_dict['request']
    inst = script_dict['vnf_instance']
    grant_req = script_dict['grant_request']
    grant = script_dict['grant_response']
    csar_dir = script_dict['tmp_csar_dir']

    script = FailScript(req, inst, grant_req, grant, csar_dir)
    getattr(script, operation)()
    script = CoordScript(operation, req, inst, grant_req)
    script.run()


if __name__ == "__main__":
    try:
        main()
        os._exit(0)
    except Exception as ex:
        sys.stderr.write(str(ex))
        sys.stderr.flush()
        os._exit(1)
