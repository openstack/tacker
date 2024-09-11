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

import json
import shutil

from tacker.tests.functional.sol_v2_common import paramgen
from tacker.tests.functional.sol_v2_common import utils
from tacker.tests.functional.sol_v2_common import zipgen


vnfd_id, zip_path = zipgen.userdata_standard()

shutil.move(zip_path, ".")
shutil.rmtree(zip_path.rsplit('/', 1)[0])

create_req = paramgen.sample3_create(vnfd_id)
terminate_req = paramgen.sample3_terminate()

net_ids = utils.get_network_ids(['net0', 'net1', 'net_mgmt'])
subnet_ids = utils.get_subnet_ids(['subnet0', 'subnet1'])

instantiate_req = paramgen.sample3_instantiate(
    net_ids, subnet_ids, "http://localhost/identity/v3")

scale_out_req = paramgen.sample3_scale_out()
scale_in_req = paramgen.sample3_scale_in()
heal_req = paramgen.sample3_heal()
change_ext_conn_req = paramgen.sample3_change_ext_conn(net_ids)
update_req = paramgen.sample3_update_vnf_vnfd_id("replace real vnfd id")

with open("create_req", "w") as f:
    f.write(json.dumps(create_req, indent=2))

with open("terminate_req", "w") as f:
    f.write(json.dumps(terminate_req, indent=2))

with open("instantiate_req", "w") as f:
    f.write(json.dumps(instantiate_req, indent=2))

with open("scale_out_req", "w") as f:
    f.write(json.dumps(scale_out_req, indent=2))

with open("scale_in_req", "w") as f:
    f.write(json.dumps(scale_in_req, indent=2))

# NOTE: vnfcInstanceId should be filled by hand
with open("heal_req", "w") as f:
    f.write(json.dumps(heal_req, indent=2))

with open("change_ext_conn_req", "w") as f:
    f.write(json.dumps(change_ext_conn_req, indent=2))

with open("update_req", "w") as f:
    f.write(json.dumps(update_req, indent=2))
