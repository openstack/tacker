# Copyright (C) 2024 Nippon Telegraph and Telephone Corporation
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

import hashlib
import os
import shutil
import tempfile


# NOTE: This package is a sample for vnflcm v2 API to deploy kubernetes cluster
# with cilium CNI using the management driver.
# This sample package requires an OS Image
# (ubuntu-22.04-server-cloudimg-amd64.img) with password access settings
# to be placed in the top directory.

SAMPLE_IMAGE_HASH = "7273f6c927c2fccb31ac1398da7c30dc9265f7c51896e41d062f" \
                    "9426afd061326947c9af442df6b0eddd04bca7c29239baaccf2d" \
                    "ec4ace19a39bcdb74bbb4758"
image_file = "ubuntu-22.04-server-cloudimg-amd64.img"
if not os.path.isfile(image_file):
    print("Ubuntu image does not exists. This sample requires OS image.")
    os._exit(1)

tmp_dir = tempfile.mkdtemp()
zip_file_name = os.path.basename(os.path.abspath("."))
zip_file_path = os.path.join(tmp_dir, zip_file_name)

tmp_contents = os.path.join(tmp_dir, "contents")
shutil.copytree(os.path.join(".", "contents"), tmp_contents)

# add userdata script
# tacker/sol_refactored/infra_drivers/openstack/userdata_standard.py
userdata_dir = "../../../../tacker/sol_refactored/infra_drivers/openstack/"
userdata_file = "userdata_standard.py"
userdata_path = os.path.abspath(userdata_dir + userdata_file)
# mkdir UserData/ and copy userdata_path into it
file_path = os.path.join(tmp_contents, "UserData")
os.makedirs(file_path)
shutil.copy(userdata_path, file_path)

# add common vnfd files
common_dir = "../../../tests/functional/sol_v2_common/common/Definitions/"
for entry in os.listdir(common_dir):
    shutil.copy(os.path.join(common_dir, entry),
                os.path.join(tmp_contents, "Definitions"))

# check os-image hash and replace hash value
with open(image_file, 'rb') as f:
    content = f.read()
hash_value = hashlib.sha512(content).hexdigest()

def_path = os.path.join(tmp_contents, "Definitions")
for entry in os.listdir(def_path):
    entry_path = os.path.join(def_path, entry)
    with open(entry_path, 'r') as f:
        content = f.read()
    content = content.replace(SAMPLE_IMAGE_HASH, hash_value)
    with open(entry_path, 'w') as f:
        f.write(content)

# create Files dir and copy image_path into it
file_path = os.path.join(tmp_contents, "Files", "images")
os.makedirs(file_path)
shutil.copy(image_file, file_path)

# make zip file
shutil.make_archive(zip_file_path, "zip", tmp_contents)

shutil.copy(os.path.join(tmp_dir, zip_file_name + ".zip"), ".")
shutil.rmtree(tmp_dir)
