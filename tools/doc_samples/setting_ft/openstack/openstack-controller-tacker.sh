#!/bin/sh
# openstack-controller-tacker.sh

CONTROLLER_IP_ADDRESS="192.168.56.11"
OS_AUTH_URL="http://${CONTROLLER_IP_ADDRESS}/identity"

### Change the IP address of the file local-vim.yaml
if [ -f "tacker/samples/tests/etc/samples/local-vim.yaml" ]
then
        cp -p tacker/samples/tests/etc/samples/local-vim.yaml tacker/samples/tests/etc/samples/local-vim.yaml_bk
        sed -i "s/auth_url:\ http:\/\/127.0.0.1\/identity/auth_url:\ http:\/\/${CONTROLLER_IP_ADDRESS}\/identity/" tacker/samples/tests/etc/samples/local-vim.yaml
else
        echo "the file tacker/samples/tests/etc/samples/local-vim.yaml is not exist."
fi

### Register the default VIM
if [ -d "${HOME}/tacker" ]
then
        cd "${HOME}/tacker" || exit
else
        echo "the directory ${HOME}/tacker is not exist."
fi
openstack vim register \
    --os-username nfv_user \
    --os-project-name nfv \
    --os-password devstack \
    --os-auth-url "${OS_AUTH_URL}" \
    --os-project-domain-name Default \
    --os-user-domain-name Default \
    --is-default \
    --description "Default VIM" \
    --config-file /opt/stack/tacker/samples/tests/etc/samples/local-vim.yaml \
    VIM0

# echo "End shell script ${0}"
