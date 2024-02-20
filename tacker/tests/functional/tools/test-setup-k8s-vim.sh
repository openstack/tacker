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

conf_dir=/opt/stack/tacker/samples/tests/etc/samples

register_vim() {
    openstack vim register \
        --os-username nfv_user \
        --os-project-name nfv \
        --os-password devstack \
        --os-auth-url http://127.0.0.1/identity \
        --os-project-domain-name Default \
        --os-user-domain-name Default \
        --description "Kubernetes VIM" \
        --config-file $1 \
        $2
}

# register vim with bearer token
register_vim $conf_dir/local-k8s-vim.yaml vim-kubernetes

# register vim with OpenID Connect info
if [ -f /tmp/keycloak.crt ]
then
    register_vim $conf_dir/local-k8s-vim-oidc.yaml vim-kubernetes-oidc
fi

# register vim with extra used helm
if [ -f $conf_dir/local-k8s-vim-helm.yaml ]
then
    register_vim $conf_dir/local-k8s-vim-helm.yaml vim-kubernetes-helm
fi

