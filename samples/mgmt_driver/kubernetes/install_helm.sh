#!/bin/bash
set -o xtrace

###############################################################################
#
# This script will install and setting Helm for Tacker.
#
###############################################################################

declare -g HELM_VERSION="3.5.4"
declare -g HELM_CHART_DIR="/var/tacker/helm"

# Install Helm
#-------------
function install_helm {
    wget -P /tmp https://get.helm.sh/helm-v$HELM_VERSION-linux-amd64.tar.gz
    tar zxf /tmp/helm-v$HELM_VERSION-linux-amd64.tar.gz -C /tmp
    sudo mv /tmp/linux-amd64/helm /usr/local/bin/helm
}

# Install sshpass
#----------------
function install_sshpass {
    sudo apt-get install -y sshpass
}

# Create helm chart directory
#----------------------------
function create_helm_chart_dir {
    sudo mkdir -p $HELM_CHART_DIR
}

# Set proxy to environment
#-------------------------
function set_env_proxy {
    cat <<EOF | sudo tee -a /etc/environment >/dev/null
http_proxy=${http_proxy//%40/@}
https_proxy=${https_proxy//%40/@}
no_proxy=$no_proxy
EOF
}

# Main
# ____
install_helm
install_sshpass
create_helm_chart_dir
set_env_proxy
exit 0
