#!/bin/sh
# kube-controller-tacker.sh

CONTROLLER_IP_ADDRESS="192.168.56.21"
OS_AUTH_URL="http://${CONTROLLER_IP_ADDRESS}/identity"
CONTROLLER_K8S_IP_ADDRESS="192.168.56.23"

### Change the IP address of the file local-vim.yaml
cd "${HOME}" || exit
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

cd "${HOME}" || exit

### Install the tool kubectl on this host controller-tacker.
curl -LO https://dl.k8s.io/release/v1.30.5/bin/linux/amd64/kubectl
curl -LO "https://dl.k8s.io/release/v1.30.5/bin/linux/amd64/kubectl.sha256"
echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
kubectl version --client
mkdir .kube
if [ -f "/tmp/kubeconfig" ]
then
        sudo mv /tmp/kubeconfig .kube/config
        sudo chown stack:stack .kube/config
        sudo chmod 600 .kube/config
else
        echo "the file /tmp/kubeconfig is not exist."
fi
ls -l .kube
kubectl cluster-info

### Register the Secret and modify the file local-k8s-vim.yaml using the tool gen_vim_config.sh.
# kubectl get secret
if [ -f "tacker/samples/tests/etc/samples/local-k8s-vim.yaml" ] && \
   [ -f "tacker/tools/gen_vim_config.sh" ]
then
        cp -p tacker/samples/tests/etc/samples/local-k8s-vim.yaml tacker/samples/tests/etc/samples/local-k8s-vim.yaml_bk
        bash tacker/tools/gen_vim_config.sh -p default -t k8s -e https://${CONTROLLER_K8S_IP_ADDRESS}:6443 --k8s-use-cert -o tacker/samples/tests/etc/samples/local-k8s-vim.yaml
        kubectl get secret
        diff -u tacker/samples/tests/etc/samples/local-k8s-vim.yaml_bk tacker/samples/tests/etc/samples/local-k8s-vim.yaml
        # cat tacker/samples/tests/etc/samples/local-k8s-vim.yaml
else
        echo "the file tacker/samples/tests/etc/samples/local-k8s-vim.yaml is not exist."
        echo "or the file tacker/tools/gen_vim_config.sh is not exist."
fi

### Add the extra configuration to the file local-k8s-vim.yaml.
if [ -f "tacker/samples/tests/etc/samples/local-k8s-vim.yaml" ]
then
        cp -p tacker/samples/tests/etc/samples/local-k8s-vim.yaml tacker/samples/tests/etc/samples/local-k8s-vim.yaml_bk2
cat << EOF >> "tacker/samples/tests/etc/samples/local-k8s-vim.yaml"
extra:
  helm_info: "{'masternode_ip':['${CONTROLLER_K8S_IP_ADDRESS}'],'masternode_username':'helm','masternode_password':'helm_password'}"
EOF
        # cat tacker/samples/tests/etc/samples/local-k8s-vim.yaml
else
        echo "the file tacker/samples/tests/etc/samples/local-k8s-vim.yaml is not exist."
fi

### Modify the file local-k8s-vim-helm.yaml using the tool gen_vim_config.sh.
if [ -f "tacker/samples/tests/etc/samples/local-k8s-vim-helm.yaml" ] && \
   [ -f "tacker/tools/gen_vim_config.sh" ]
then
        cp -p tacker/samples/tests/etc/samples/local-k8s-vim-helm.yaml tacker/samples/tests/etc/samples/local-k8s-vim-helm.yaml_bk
        bash tacker/tools/gen_vim_config.sh -p default -t k8s -e https://${CONTROLLER_K8S_IP_ADDRESS}:6443 --k8s-use-cert --k8s-use-helm -o tacker/samples/tests/etc/samples/local-k8s-vim-helm.yaml
        diff -u tacker/samples/tests/etc/samples/local-k8s-vim-helm.yaml_bk tacker/samples/tests/etc/samples/local-k8s-vim-helm.yaml
        # cat tacker/samples/tests/etc/samples/local-k8s-vim-helm.yaml
else
        echo "the file tacker/samples/tests/etc/samples/local-k8s-vim-helm.yaml is not exist."
        echo "or the file tacker/tools/gen_vim_config.sh is not exist."
fi

### Register the Kubernetes VIM
openstack vim list \
    --os-username nfv_user \
    --os-project-name nfv \
    --os-password devstack \
    --os-auth-url "${OS_AUTH_URL}" \
    --os-project-domain-name Default \
    --os-user-domain-name Default

openstack vim register \
    --os-username nfv_user \
    --os-project-name nfv \
    --os-password devstack \
    --os-auth-url "${OS_AUTH_URL}" \
    --os-project-domain-name Default \
    --os-user-domain-name Default \
    --description "Kubernetes VIM" \
    --config-file tacker/samples/tests/etc/samples/local-k8s-vim.yaml \
    vim-kubernetes

openstack vim register \
    --os-username nfv_user \
    --os-project-name nfv \
    --os-password devstack \
    --os-auth-url "${OS_AUTH_URL}" \
    --os-project-domain-name Default \
    --os-user-domain-name Default \
    --description "Kubernetes VIM" \
    --config-file tacker/samples/tests/etc/samples/local-k8s-vim-helm.yaml \
    vim-kubernetes-helm

openstack vim list \
    --os-username nfv_user \
    --os-project-name nfv \
    --os-password devstack \
    --os-auth-url "${OS_AUTH_URL}" \
    --os-project-domain-name Default \
    --os-user-domain-name Default

### Set MgmtDriver.
if [ -d "/opt/stack/tacker/tacker/vnfm/mgmt_drivers" ] && \
   [ -f "/opt/stack/tacker/samples/mgmt_driver/kubernetes/container_update/container_update_mgmt.py" ]
then
        # ls /opt/stack/tacker/tacker/vnfm/mgmt_drivers
        cp -p /opt/stack/tacker/samples/mgmt_driver/kubernetes/container_update/container_update_mgmt.py /opt/stack/tacker/tacker/vnfm/mgmt_drivers/.
        ls /opt/stack/tacker/tacker/vnfm/mgmt_drivers
        sudo chown stack:stack /opt/stack/tacker/tacker/vnfm/mgmt_drivers/container_update_mgmt.py
else
        echo "the directory /opt/stack/tacker/tacker/vnfm/mgmt_drivers is not exist."
        echo "or the file /opt/stack/tacker/samples/mgmt_driver/kubernetes/container_update/container_update_mgmt.py is not exist."
fi

if [ -f "/opt/stack/tacker/setup.cfg" ]
then
        cp -p /opt/stack/tacker/setup.cfg /opt/stack/tacker/setup.cfg_bk
        sudo sed -i "/VnflcmMgmtNoop/a \ \ \ \ mgmt-container-update = \
tacker.vnfm.mgmt_drivers.container_update_mgmt:ContainerUpdateMgmtDriver" \
/opt/stack/tacker/setup.cfg
        diff -u /opt/stack/tacker/setup.cfg_bk /opt/stack/tacker/setup.cfg
else
        echo "the file /opt/stack/tacker/setup.cfg is not exist."
fi

if [ -f "/etc/tacker/tacker.conf" ]
then
        cp -p /etc/tacker/tacker.conf /etc/tacker/tacker.conf_bk
        sudo sed -i "/vnflcm_mgmt_driver = vnflcm_noop/a vnflcm_mgmt_driver = \
vnflcm_noop,mgmt-container-update" /etc/tacker/tacker.conf
        diff -u /etc/tacker/tacker.conf_bk /etc/tacker/tacker.conf
else
        echo "the file /etc/tacker/tacker.conf is not exist."
fi

if [ -d "/opt/stack/tacker" ]
then
        cd "/opt/stack/tacker" || exit
        sudo python3 setup.py build
        sudo chown -R stack:stack /opt/stack/tacker/
else
        echo "the directory /opt/stack/tacker is not exist."
fi
sudo systemctl restart devstack@tacker-conductor
cd "${HOME}" || exit

# echo "End shell script ${0}"
