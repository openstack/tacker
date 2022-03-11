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

# tacker/tests/etc...
#             /functional/sol_v2/samples/smapleX
image_dir = "../../../../etc/samples/etsi/nfv/common/Files/images/"
image_file = "cirros-0.5.2-x86_64-disk.img"
image_path = os.path.abspath(image_dir + image_file)

utils.make_zip(".", tmp_dir, vnfd_id, image_path)

shutil.move(os.path.join(tmp_dir, zip_file_name), ".")
shutil.rmtree(tmp_dir)

create_req = paramgen.create_vnf_max(vnfd_id)
scaleout_req = paramgen.scaleout_vnf_max()
scalein_req = paramgen.scalein_vnf_max()
terminate_req = paramgen.terminate_vnf_max()

print('#####################################################################\n'
      '# Run pre.py if an error occurs                                     #\n'
      '#  - If an error occurs, run the pre.py script in advance           #\n'
      '#    to create the openstack resource required to run this script.  #\n'
      '# Run post.py when you finish tests                                 #\n'
      '#  - When you no longer need these openstack resources              #\n'
      '#    after testing, run post.py and delete them.                    #\n'
      '# vnfc ids should be changed in heal req files by show vnf manually.#\n'
      '#####################################################################')

net_ids = utils.get_network_ids(['net0', 'net1', 'net_mgmt', 'ft-net0',
    'ft-net1'])
subnet_ids = utils.get_subnet_ids(['subnet0', 'subnet1', 'ft-ipv4-subnet0',
    'ft-ipv6-subnet0', 'ft-ipv4-subnet1', 'ft-ipv6-subnet1'])
port_ids = utils.get_port_ids(['VDU2_CP1-1', 'VDU2_CP1-2'])

instantiate_req = paramgen.instantiate_vnf_max(
    net_ids, subnet_ids, port_ids, "http://localhost/identity/v3")

# fake vnfc id, should be get from show vnf
vnfc_ids = ['VDU1-9300a3cb-bd3b-45e4-9967-095040caf827',
    'VDU2-39681281-e6e6-4179-8898-d9ec70f1642a']
heal_vnfc_req = paramgen.heal_vnf_vnfc_max(vnfc_ids[0])
heal_vnfc_with_omit_all_req = paramgen.heal_vnf_vnfc_max_with_parameter(
    vnfc_ids)
heal_vnfc_with_all_false_req = paramgen.heal_vnf_vnfc_max_with_parameter(
    vnfc_ids, False)
heal_vnfc_with_all_true_req = paramgen.heal_vnf_vnfc_max_with_parameter(
    vnfc_ids, True)
heal_all_with_omit_all_req = paramgen.heal_vnf_all_max_with_parameter()
heal_all_with_all_true_req = paramgen.heal_vnf_all_max_with_parameter(True)
heal_all_with_all_false_req = paramgen.heal_vnf_all_max_with_parameter(False)
change_ext_conn_max_req = paramgen.change_ext_conn_max(net_ids, subnet_ids,
    "http://localhost/identity/v3")
# Only this package have external connectivity.
# So min pattern also use this package.
change_ext_conn_min_req = paramgen.change_ext_conn_min(net_ids, subnet_ids)

with open("create_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(create_req, indent=2))

with open("terminate_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(terminate_req, indent=2))

with open("scaleout_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(scaleout_req, indent=2))

with open("scalein_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(scalein_req, indent=2))

with open("instantiate_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(instantiate_req, indent=2))

with open("heal_vnfc_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_vnfc_req, indent=2))

with open("heal_vnfc_with_omit_all_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_vnfc_with_omit_all_req, indent=2))

with open("heal_vnfc_with_all_false_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_vnfc_with_all_false_req, indent=2))

with open("heal_vnfc_with_all_true_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_vnfc_with_all_true_req, indent=2))

with open("heal_all_with_omit_all_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_all_with_omit_all_req, indent=2))

with open("heal_all_with_all_true_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_all_with_all_true_req, indent=2))

with open("heal_all_with_all_false_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_all_with_all_false_req, indent=2))

with open("change_ext_conn_max_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(change_ext_conn_max_req, indent=2))

with open("change_ext_conn_min_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(change_ext_conn_min_req, indent=2))
