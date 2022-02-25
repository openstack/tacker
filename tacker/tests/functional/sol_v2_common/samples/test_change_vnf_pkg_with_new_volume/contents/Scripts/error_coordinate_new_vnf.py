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
CMD_TIMEOUT = 30
SERVER_WAIT_COMPLETE_TIME = 60
SSH_CONNECT_RETRY_COUNT = 4


class SampleErrorNewCoordinateVNFScript(object):

    def __init__(self, req, inst, grant_req, grant, csar_dir, vdu_info):
        self.req = req
        self.inst = inst
        self.grant_req = grant_req
        self.grant = grant
        self.csar_dir = csar_dir
        self.vdu_info = vdu_info

    def coordinate_vnf(self):
        raise Exception("ErrorNewCoordinateVNFScript")


def main():
    operation = "coordinate_vnf"
    script_dict = pickle.load(sys.stdin.buffer)
    req = script_dict['request']
    inst = script_dict['vnf_instance']
    grant_req = script_dict['grant_request']
    grant = script_dict['grant_response']
    csar_dir = script_dict['tmp_csar_dir']
    vdu_info = script_dict['vdu_info']
    script = SampleErrorNewCoordinateVNFScript(
        req, inst, grant_req, grant,
        csar_dir, vdu_info)
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
