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


class FailScript(object):
    def __init__(self, vnfc_param):
        self.vnfc_param = vnfc_param

    def run(self):
        operation = 'change_vnfpkg'
        if self.vnfc_param['is_rollback']:
            operation += '_rollback'
        if os.path.exists(f'/tmp/{operation}'):
            raise Exception(f'test {operation} error')


def main():
    vnfc_param = pickle.load(sys.stdin.buffer)
    script = FailScript(vnfc_param)
    script.run()


if __name__ == "__main__":
    try:
        main()
        os._exit(0)
    except Exception as ex:
        sys.stderr.write(str(ex))
        sys.stderr.flush()
        os._exit(1)
