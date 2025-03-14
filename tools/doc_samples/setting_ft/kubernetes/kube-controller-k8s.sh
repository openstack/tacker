#!/bin/sh
# kube-controller-k8s.sh

cd "${HOME}" || exit

### Add values for unqualified-search-registries of the file registries.conf
if [ -f "/etc/containers/registries.conf" ]
then
        sudo cp -p /etc/containers/registries.conf /etc/containers/registries.conf_bk
        sudo sed -i "s/unqualified-search-registries\ =\ \[\"docker\.io\",\ \"quay\.io\"\]/unqualified-search-registries\ =\ \[\"docker\.io\",\ \"k8s\.gcr\.io\",\ \"quay\.io\",\ \"celebdor\"\]/" \
 /etc/containers/registries.conf
else
        echo "the file /etc/containers/registries.conf is not exist."
fi

### Removing ip link and restarting kubelet
# kubectl get all -A
# ip link
sudo ip link set cni0 down
sudo ip link set flannel.1 down
# ip link
sudo ip link delete cni0
sudo ip link delete flannel.1
ip link
sudo systemctl restart kubelet
kubectl get all -A

### Restart coredns
kubectl delete pod -n kube-system $(kubectl get pod -n kube-system --no-headers -o custom-columns=":metadata.name" | grep coredns | tr -s '\n' ' ')
kubectl get all -A

### Transfer the file .kube/config from this host controller-k8s to the host controller-tacker.
### Install Tool sshpass to run the command scp without entering an interactive passphrase.
sudo apt-get -y install sshpass
sshpass -p "vagrant" scp -po "StrictHostKeyChecking no" .kube/config vagrant@controller-tacker:/tmp/kubeconfig

### Create and configure user helm.
sudo adduser --disabled-password --gecos "" "helm"
echo "helm:helm_password" | sudo chpasswd
sudo sh -c "cat >> /etc/sudoers.d/50_helm_sh" << EOF
helm ALL=(root) NOPASSWD:ALL
EOF
if [ -d "/home/helm" ]
then
        sudo cp -pr .kube /home/helm/.
        sudo ls -la /home/helm/.kube
        sudo chown -R helm:helm /home/helm/.kube
else
        echo "the directory /home/helm is not exist."
fi
sudo ls -la /home/helm/.kube
sudo mkdir -p /var/tacker/helm
sudo chmod 755 /var/tacker/helm
sudo chown helm:helm /var/tacker/helm
ls -l /var/tacker/.
if [ -f "/etc/ssh/sshd_config" ]
then
        sudo cp -p /etc/ssh/sshd_config /etc/ssh/sshd_config_bk
        sudo sh -c "sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config"
        diff -u /etc/ssh/sshd_config_bk /etc/ssh/sshd_config
else
        echo "the file /etc/ssh/sshd_config is not exist."
fi
sudo systemctl restart sshd

### Install the Helm package.
curl -O https://get.helm.sh/helm-v3.15.4-linux-amd64.tar.gz
if [ -f "helm-v3.15.4-linux-amd64.tar.gz" ]
then
        tar -zxvf helm-v3.15.4-linux-amd64.tar.gz
else
        echo "the file helm-v3.15.4-linux-amd64.tar.gz is not exist."
fi
if [ -f "linux-amd64/helm" ]
then
        sudo mv linux-amd64/helm /usr/local/bin/helm
else
        echo "the file linux-amd64/helm is not exist."
fi
helm version

# echo "End shell script ${0}"
