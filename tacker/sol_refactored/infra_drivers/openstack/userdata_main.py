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

import importlib
import os
import pickle
import sys
import traceback


def main():
    script_dict = pickle.load(sys.stdin.buffer)

    req = script_dict['request']
    inst = script_dict['vnf_instance']
    grant_req = script_dict['grant_request']
    grant = script_dict['grant_response']
    tmp_csar_dir = script_dict['tmp_csar_dir']

    additional_params = req['additionalParams']
    userdata_path = additional_params['lcm-operation-user-data']
    userdata_class = additional_params['lcm-operation-user-data-class']

    sys.path.append(tmp_csar_dir)
    class_module = os.path.splitext(
        userdata_path.lstrip('./'))[0].replace('/', '.')
    module = importlib.import_module(class_module)
    klass = getattr(module, userdata_class)

    method = getattr(klass, grant_req['operation'].lower())
    stack_dict = method(req, inst, grant_req, grant, tmp_csar_dir)

    pickle.dump(stack_dict, sys.stdout.buffer)
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
        os._exit(0)
    except Exception:
        sys.stderr.write(traceback.format_exc())
        sys.stderr.flush()
        os._exit(1)
