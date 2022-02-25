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

import json
import os
import shutil
import tempfile

from oslo_utils import uuidutils

from tacker.tests.functional.sol_v2 import paramgen
from tacker.tests.functional.sol_v2 import utils


zip_file_name = os.path.basename(os.path.abspath(".")) + '.zip'
tmp_dir = tempfile.mkdtemp()
vnfd_id = uuidutils.generate_uuid()
utils.make_zip(".", tmp_dir, vnfd_id)

shutil.copy(os.path.join(tmp_dir, zip_file_name), ".")
shutil.rmtree(tmp_dir)

create_req = paramgen.create_vnf_min(vnfd_id)
terminate_req = paramgen.terminate_vnf_min()
instantiate_req = paramgen.instantiate_vnf_min()
scaleout_req = paramgen.scaleout_vnf_min()
scalein_req = paramgen.scalein_vnf_min()
update_seq = paramgen.update_vnf_min()
# fake vnfc id, should be get from show vnf
VNFC_ID = "VDU1-9300a3cb-bd3b-45e4-9967-095040caf827"
heal_req = paramgen.heal_vnf_vnfc_min(VNFC_ID)
heal_without_parameter_req = paramgen.heal_vnf_all_min()
net_ids = {}
net_ids['ft-net1'] = '51e62f5f-3711-4182-b844-0f23e0408e51'
subnet_ids = {}
subnet_ids['ft-ipv4-subnet1'] = '8bf9b119-68bd-4e01-b518-dd4cde71687c'
subnet_ids['ft-ipv6-subnet1'] = '2bbaeb35-4d75-4aae-ab59-10c22a04d06b'
change_ext_conn_req = paramgen.change_ext_conn_min(net_ids, subnet_ids)

print('#####################################################################\n'
      '# vnfc id should be changed in heal req file by show vnf manually.  #\n'
      '#####################################################################')

with open("create_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(create_req, indent=2))

with open("terminate_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(terminate_req, indent=2))

with open("instantiate_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(instantiate_req, indent=2))

with open("scaleout_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(scaleout_req, indent=2))

with open("scalein_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(scalein_req, indent=2))

with open("update_seq", "w", encoding='utf-8') as f:
    f.write(json.dumps(update_seq, indent=2))

with open("heal_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_req, indent=2))

with open("heal_without_parameter_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_without_parameter_req, indent=2))

with open("change_ext_conn_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(change_ext_conn_req, indent=2))
