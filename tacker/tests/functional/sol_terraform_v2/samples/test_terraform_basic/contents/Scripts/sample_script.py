# Copyright (C) 2023 Nippon Telegraph and Telephone Corporation
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


if __name__ == "__main__":
    try:
        main()
        os._exit(0)
    except Exception as ex:
        sys.stderr.write(str(ex))
        sys.stderr.flush()
        os._exit(1)
