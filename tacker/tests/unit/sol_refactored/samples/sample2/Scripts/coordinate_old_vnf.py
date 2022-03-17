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

from oslo_log import log as logging


LOG = logging.getLogger(__name__)


class SampleOldCoordinateVNFScript(object):

    def __init__(self, req, inst, grant_req, grant, csar_dir, k8s_info):
        self.req = req
        self.inst = inst
        self.grant_req = grant_req
        self.grant = grant
        self.csar_dir = csar_dir
        self.k8s_info = k8s_info

    def coordinate_vnf(self):
        pass


def main():
    operation = "coordinate_vnf"
    script_dict = pickle.load(sys.stdin.buffer)
    req = script_dict['request']
    inst = script_dict['vnf_instance']
    grant_req = script_dict['grant_request']
    grant = script_dict['grant_response']
    csar_dir = script_dict['tmp_csar_dir']
    k8s_info = script_dict['k8s_info']
    script = SampleOldCoordinateVNFScript(
        req, inst, grant_req, grant,
        csar_dir, k8s_info)
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
