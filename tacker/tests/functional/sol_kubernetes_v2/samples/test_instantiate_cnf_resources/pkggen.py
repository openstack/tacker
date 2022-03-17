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

import json
import os
import shutil
import tempfile

from oslo_utils import uuidutils

from tacker.tests.functional.sol_kubernetes_v2 import paramgen
from tacker.tests.functional.sol_v2 import utils


zip_file_name = os.path.basename(os.path.abspath(".")) + '.zip'
tmp_dir = tempfile.mkdtemp()
vnfd_id = uuidutils.generate_uuid()

# tacker/tests/functional/sol_kubernetes_v2/samples/{package_name}
utils.make_zip(".", tmp_dir, vnfd_id)

shutil.move(os.path.join(tmp_dir, zip_file_name), ".")
shutil.rmtree(tmp_dir)

create_req = paramgen.test_instantiate_cnf_resources_create(vnfd_id)

# if you instantiate with all k8s resource
# please change auth_url and bear_token to your own k8s cluster's info
auth_url = "https://127.0.0.1:6443"
bearer_token = "your_k8s_cluster_bearer_token"
max_sample_instantiate = paramgen.max_sample_instantiate(
    auth_url, bearer_token)

max_sample_terminate = paramgen.max_sample_terminate()

# if you instantiate with only one resource
# please change vim_id to your k8s's vim id
vim_id = "your k8s vim's id"
min_sample_instantiate = paramgen.min_sample_instantiate(vim_id)
min_sample_terminate = paramgen.min_sample_terminate()

# if you want to use `change_vnfpkg` operation
change_vnfpkg_instantiate = paramgen.change_vnfpkg_instantiate(
    auth_url, bearer_token)

with open("create_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(create_req, indent=2))

with open("max_sample_instantiate", "w", encoding='utf-8') as f:
    f.write(json.dumps(max_sample_instantiate, indent=2))

with open("max_sample_terminate", "w", encoding='utf-8') as f:
    f.write(json.dumps(max_sample_terminate, indent=2))

with open("min_sample_instantiate", "w", encoding='utf-8') as f:
    f.write(json.dumps(min_sample_instantiate, indent=2))

with open("min_sample_terminate", "w", encoding='utf-8') as f:
    f.write(json.dumps(min_sample_terminate, indent=2))

with open("change_vnfpkg_instantiate", "w", encoding='utf-8') as f:
    f.write(json.dumps(change_vnfpkg_instantiate, indent=2))
