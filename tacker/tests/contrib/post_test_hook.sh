#!/bin/bash -x
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# This script is executed inside post_test_hook function in devstack gate.

set -xe

TACKER_DIR="$BASE/new/tacker"
DEVSTACK_DIR="$BASE/new/devstack"
SCRIPTS_DIR="/usr/os-testr-env/bin/"

venv=${1:-"dsvm-functional"}

function generate_test_logs {
    local path="$1"
    # Compress all $path/*.txt files and move the directories holding those
    # files to /opt/stack/logs. Files with .log suffix have their
    # suffix changed to .txt (so browsers will know to open the compressed
    # files and not download them).
    if [ -d "$path" ]
    then
        sudo find $path -iname "*.log" -type f -exec mv {} {}.txt \; -exec gzip -9 {}.txt \;
        sudo mv $path/* /opt/stack/logs/
    fi
}

function generate_testr_results {
    # Give job user rights to access tox logs
    sudo -H -u $owner chmod o+rw .
    sudo -H -u $owner chmod o+rw -R .stestr
    if [ -f ".stestr/0" ] ; then
        .tox/$venv/bin/subunit-1to2 < .stestr/0 > ./stestr.subunit
        $SCRIPTS_DIR/subunit2html ./stestr.subunit testr_results.html
        gzip -9 ./stestr.subunit
        gzip -9 ./testr_results.html
        sudo mv ./*.gz /opt/stack/logs/
    fi

    if [[ "$venv" == dsvm-functional* ]]
    then
        generate_test_logs $log_dir
    fi
}

. ${TACKER_DIR}/tacker/tests/contrib/post_test_hook_lib.sh

if [[ "$venv" == dsvm-functional* ]]
then
    owner=stack
    sudo_env=
    log_dir="/tmp/${venv}-logs"
    . $DEVSTACK_DIR/openrc admin admin
    fixup_quota
    add_key
    add_secgrp
fi

# Set owner permissions according to job's requirements.
cd $TACKER_DIR
sudo chown -R $owner:stack $TACKER_DIR

# Run tests
echo "Running tacker $venv test suite"
set +e

sudo -H -u $owner $sudo_env tox -e $venv
testr_exit_code=$?
set -e

# Collect and parse results
generate_testr_results
exit $testr_exit_code

