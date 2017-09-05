# This script is used to prepare functional test env after devstack
# installation of tacker

DEVSTACK_DIR=${DEVSTACK_DIR:-~/devstack}
TACKER_DIR=$(dirname "$0")/..
PRIVATE_KEY_FILE=${PRIVATE_KEY_FILE:-/dev/null}
NFV_USER=${NFV_USER:-"nfv_user"}

# Test devstack dir setting
if [ ! -f ${DEVSTACK_DIR}/openrc ]; then
    echo "Please set right DEVSTACK_DIR"
    exit 1
fi

. $DEVSTACK_DIR/openrc admin admin
. ${TACKER_DIR}/tacker/tests/contrib/post_test_hook_lib.sh

fixup_quota
add_key_if_not_exist
add_secgrp_if_not_exist
