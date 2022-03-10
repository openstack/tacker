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
import os
import shutil
import tempfile

from oslo_utils import uuidutils

from tacker.tests.functional.sol_v2 import paramgen
from tacker.tests.functional.sol_v2 import utils


zip_file_name = os.path.basename(os.path.abspath(".")) + '.zip'
tmp_dir = tempfile.mkdtemp()
vnfd_id = uuidutils.generate_uuid()

# tacker/tests/etc...
#             /functional/sol_v2/samples/smapleX
image_dir = "../../../../etc/samples/etsi/nfv/common/Files/images/"
image_file = "cirros-0.5.2-x86_64-disk.img"
image_path = os.path.abspath(image_dir + image_file)

utils.make_zip(".", tmp_dir, vnfd_id, image_path)

shutil.move(os.path.join(tmp_dir, zip_file_name), ".")
shutil.rmtree(tmp_dir)

subscription_req = paramgen.sub_create_max("http://127.0.0.1/")
create_req = paramgen.create_vnf_max(vnfd_id)
scaleout_req = paramgen.scaleout_vnf_max()
terminate_req = paramgen.terminate_vnf_max()

print('#####################################################################\n'
      '# Run pre.py if an error occurs                                     #\n'
      '#  - If an error occurs, run the pre.py script in advance           #\n'
      '#    to create the openstack resource required to run this script.  #\n'
      '# Run post.py when you finish tests                                 #\n'
      '#  - When you no longer need these openstack resources              #\n'
      '#    after testing, run post.py and delete them.                    #\n'
      '#####################################################################')

net_ids = utils.get_network_ids(['net0', 'net1', 'net_mgmt', 'ft-net0'])
subnet_ids = utils.get_subnet_ids(
    ['subnet0', 'subnet1', 'ft-ipv4-subnet0', 'ft-ipv6-subnet0'])
port_ids = utils.get_port_ids(['VDU2_CP1-1', 'VDU2_CP1-2'])

instantiate_req = paramgen.instantiate_vnf_max(
    net_ids, subnet_ids, port_ids, "http://localhost/identity/v3")

with open("subscription_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(subscription_req, indent=2))

with open("create_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(create_req, indent=2))

with open("terminate_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(terminate_req, indent=2))

with open("scaleout_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(scaleout_req, indent=2))

with open("instantiate_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(instantiate_req, indent=2))
