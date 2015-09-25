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

VENV=${1:-"dsvm-functional"}

export GATE_DEST=$BASE/new
export DEVSTACK_DIR=$GATE_DEST/devstack
export TACKER_DIR="$GATE_DEST/tacker"

case $VENV in
    dsvm-functional)
        owner=stack
        ;;
esac

sudo chown -R $owner:stack $TACKER_DIR

cd $TACKER_DIR

# Run functional tests
echo "Running Tacker $VENV test suite"
source $DEVSTACK_DIR/openrc admin admin
sudo -E -H -u $owner tox -e functional -- --concurrency=1
EXIT_CODE=$?

exit $EXIT_CODE
