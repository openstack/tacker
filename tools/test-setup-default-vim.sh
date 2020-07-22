#!/bin/bash -xe

# This script is used to set up default vim
# for functional testing, which cannot be put
# in devstack/plugin.sh because new zuul3 CI
# cannot keep the devstack plugins order
#
# Also, this script updates the following
# parameter which has been modified
# unintentionally by ansible playbook
# `roles/setup-default-vim/tasks/main.yaml`
# according to the execution environment of
# Zuul.
#
#  --os-auth-url
#  --config-file

openstack vim register \
    --os-username nfv_user \
    --os-project-name nfv \
    --os-password devstack \
    --os-auth-url http://127.0.0.1/identity \
    --os-project-domain-name Default \
    --os-user-domain-name Default \
    --is-default \
    --description "Default VIM" \
    --config-file /opt/stack/tacker/tacker/tests/etc/samples/local-vim.yaml \
    VIM0
