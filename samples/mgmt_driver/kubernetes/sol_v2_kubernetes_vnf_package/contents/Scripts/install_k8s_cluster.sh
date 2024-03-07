#!/bin/bash
set -o xtrace
###############################################################################
#
# This script will install and setting for the Kubernetes Cluster on Ubuntu.
# It's confirmed operation on Ubuntu of below.
#
# * OS type             : Ubuntu(64 bit)
# * OS version          : 22.04 LTS
# * OS architecture     : amd64 (x86_64)
# * Disk/Ram size       : 15GB/2GB
# * Pre setup user      : ubuntu
#
###############################################################################

#==============================================================================
# Usage Definition
#==============================================================================
function usage {
    sudo cat <<_EOT_
$(basename ${0}) is script to construct the kubernetes cluster.

Usage:
  $(basename ${0}) [-d] [-o] [-m <master ip address>]
    [-w <worker ip address>] [-i <master cluster ip address>]
    [-a <k8s api cluster cidr] [-p <k8s pod network cidr>]
    [-t <token name>] [-s <token hash>] [-k <certificate key>]

Description:
  This script is to construct the kubernetes cluster on a virtual machine.
  It can install and configure a Master node or each Worker Node
  as specify arguments.

Options:
  -m              Install and setup all master nodes(use "," to separate, the first master ip is main master ip)
  -w              Install and setup worker node
  -i              master cluster IP address (e.g. 192.168.120.100)
  -a              Kubernetes api cluster CIDR (e.g. 10.96.0.0/12)
  -p              Kubernetes pod network CIDR (e.g. 192.168.0.0/16)
  -d              Display the execution result in debug mode
  -o              Output the execution result to the log file
  -t              The first master's token name
  -s              The first master's token hash
  -k              The first master‘s certificate key

_EOT_
    exit 1
}

declare -g INSTALL_MODE=""
declare -g DEBUG_MODE="False"
declare -g OUTPUT_LOGFILE="False"
# master/worker ip
declare -g MASTER_IPADDRS=${MASTER_IPADDRS:-}
declare -a -g MASTER_IPS=${MASTER_IPS:-}
declare -g MASTER_IP=${MASTER_IP:-}
declare -g WORKER_IPADDR=${WORKER_IPADDR:-}
declare -g TOKEN_NAME=${TOKEN_NAME:-}
declare -g TOKEN_HASH=${TOKEN_HASH:-}
declare -g CERT_KEY=${CERT_KEY:-}
declare -g K8S_API_CLUSTER_CIDR=${K8S_API_CLUSTER_CIDR:-10.96.0.0/12}
declare -g K8S_POD_CIDR=${K8S_POD_CIDR:-10.0.0.0/8}
# software version
declare -g K8S_MINOR_VERSION="1.26"
declare -g K8S_VERSION="1.26.8-1.1"
declare -g CONTAINERD_VERSION="1.7.11"
declare -g RUNC_VERSION="1.1.10"
declare -g CILIUM_VERSION="1.14.5"

if [ "$OPTIND" = 1 ]; then
    while getopts dom:w:i:a:p:t:s:k:h OPT; do
        case $OPT in
        m)
            MASTER_IPADDRS=$OPTARG # 192.168.120.17,192.168.120.18,192.168.120.19
            INSTALL_MODE="master"  # master
            MASTER_IPS=(${MASTER_IPADDRS//,/ })
            MASTER_IP=${MASTER_IPS[0]}
            ;;
        w)
            WORKER_IPADDR=$OPTARG # 192.168.120.2
            INSTALL_MODE="worker" # worker
            ;;
        i)
            MASTER_CLUSTER_IP=$OPTARG # master cluster ip: 192.168.120.100
            ;;
        a)
            K8S_API_CLUSTER_CIDR=$OPTARG # cluster cidr: 10.96.0.0/12
            ;;
        p)
            K8S_POD_CIDR=$OPTARG # pod network cidr: 192.168.0.0/16
            ;;
        d)
            DEBUG_MODE="True" # start debug
            ;;
        o)
            OUTPUT_LOGFILE="True" # output log file
            ;;
        t)
            TOKEN_NAME=$OPTARG # token name
            ;;
        s)
            TOKEN_HASH=$OPTARG # token hash
            ;;
        k)
            CERT_KEY=$OPTARG # certificate key
            ;;
        esac
    done
else
    echo "No installed getopts-command." 1>&2
    exit 1
fi

# check parameter entered by user
if [ "$DEBUG_MODE" == "True" ]; then
    echo "*** DEBUG MODE ***"
    set -x
fi

if [ "$OUTPUT_LOGFILE" == "True" ]; then
    echo "*** OUTPUT LOGFILE MODE ***"
    exec > /tmp/k8s_install_`date +%Y%m%d%H%M%S`.log 2>&1
fi

# Application Variables
#----------------------
# haproxy
declare -g CURRENT_HOST_IP=${CURRENT_HOST_IP:-}
declare -g MASTER_CLUSTER_PORT=16443
# kubeadm join
declare -g KUBEADM_JOIN_WORKER_RESULT=${KUBEADM_JOIN_WORKER_RESULT:-}


# Functions
#==========

# Set OS common functions
#------------------------

# Set public DNS
function set_public_dns {
    sudo sed -i -e 's/^#DNS=/DNS=8.8.8.8 8.8.4.4/g' /etc/systemd/resolved.conf
    ip route | grep "127.0.0.53" > /dev/null 2>&1
    result=$?
    if [ $result = 0 ]; then
        sudo ip route delete 127.0.0.53
    fi
    sudo systemctl restart systemd-resolved.service
}

function set_hostname {
    tmp_master_ipaddr3=`echo ${MASTER_IP} | sudo sed -e "s/.[0-9]\{1,3\}$//"`
    local tmp_result=""
    if [[ "$INSTALL_MODE" =~ "master" ]]; then
        for _ip in `ip -4 addr | grep -oP '(?<=inet\s)\d+(\.\d+){3}'`; do
            _tmp_ip=`echo ${_ip} |sudo sed -e "s/.[0-9]\{1,3\}$//"`
            if [[ $_tmp_ip == $tmp_master_ipaddr3 ]]; then
                CURRENT_HOST_IP=$_ip
                tmp_result=`echo $_ip|cut -d"." -f4`
                break
            fi
        done
        sudo /usr/bin/hostnamectl set-hostname master$tmp_result
    elif [[ "$INSTALL_MODE" == "worker" ]]; then
        CURRENT_HOST_IP=$WORKER_IPADDR
        tmp_result=`echo $CURRENT_HOST_IP|cut -d"." -f4`
        sudo /usr/bin/hostnamectl set-hostname worker$tmp_result
    else
        echo "set_hostname error. INSTALL_MODE is invalid."
        exit 0
    fi
}

function set_sudoers {
    echo "ubuntu ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/ubuntu
}

function set_hosts {
    hostname=`hostname`
    sudo sed -i -e 's/127.0.0.1 localhost/127.0.0.1 localhost master/g' \
    /etc/hosts
    sudo sed -i -e "s/127.0.1.1 $hostname/127.0.1.1 $hostname master/g" \
    /etc/hosts
}

function invalidate_swap {
    sudo sed -i -e '/swap/s/^/#/' /etc/fstab
    swapoff -a
}


# Install Haproxy
#----------------
function install_haproxy {
    REPOS_UPDATED=False apt_get_update
    sleep 5
    apt_get install haproxy
}

function modify_haproxy_conf {
    cat <<EOF | sudo tee /etc/haproxy/haproxy.cfg >/dev/null
global
        log /dev/log    local0
        log /dev/log    local1 notice
        chroot /var/lib/haproxy
        stats socket /run/haproxy/admin.sock mode 660 level admin expose-fd listeners
        stats timeout 30s
        user haproxy
        group haproxy
        daemon

        # Default SSL material locations
        ca-base /etc/ssl/certs
        crt-base /etc/ssl/private

        # Default ciphers to use on SSL-enabled listening sockets.
        # For more information, see ciphers(1SSL). This list is from:
        #  https://hynek.me/articles/hardening-your-web-servers-ssl-ciphers/
        # An alternative list with additional directives can be obtained from
        #  https://mozilla.github.io/server-side-tls/ssl-config-generator/?server=haproxy
        ssl-default-bind-ciphers ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:RSA+AESGCM:RSA+AES:!aNULL:!MD5:!DSS
        ssl-default-bind-options no-sslv3

defaults
        log     global
        mode    http
        option  httplog
        option  dontlognull
        timeout connect 5000
        timeout client  50000
        timeout server  50000
        errorfile 400 /etc/haproxy/errors/400.http
        errorfile 403 /etc/haproxy/errors/403.http
        errorfile 408 /etc/haproxy/errors/408.http
        errorfile 500 /etc/haproxy/errors/500.http
        errorfile 502 /etc/haproxy/errors/502.http
        errorfile 503 /etc/haproxy/errors/503.http
        errorfile 504 /etc/haproxy/errors/504.http

frontend kubernetes-apiserver
    mode                 tcp
    bind                 *:$MASTER_CLUSTER_PORT
    option               tcplog
    default_backend      kubernetes-apiserver

backend kubernetes-apiserver
    mode        tcp
    balance     roundrobin
EOF
    for master_ip in ${MASTER_IPS[@]}; do
        split_ips=(${master_ip//./ })
        cat <<EOF | sudo tee -a /etc/haproxy/haproxy.cfg >/dev/null
    server  master${split_ips[3]}  $master_ip:6443 check
EOF
    done
    cat <<EOF | sudo tee -a /etc/haproxy/haproxy.cfg >/dev/null
listen stats
    bind               *:1080
    stats auth         admin:awesomePassword
    stats refresh      5s
    stats realm        HAProxy\ Statistics
    stats uri          /admin?stats
EOF

}

function start_haproxy {
    sudo systemctl enable haproxy
    sudo systemctl start haproxy
    sudo systemctl status haproxy | grep Active
    result=$(ss -lnt |grep -E "16443|1080")
    if [[ -z $result ]]; then
        sudo systemctl restart haproxy
    fi
}


# Install Keepalived
#-------------------
function install_keepalived {
    REPOS_UPDATED=False apt_get_update
    apt_get install keepalived
}
function modify_keepalived_conf {
    local priority
    local ip_name
    local index=0
    for master_ip in ${MASTER_IPS[@]}; do
        if [[ "$CURRENT_HOST_IP" == "$master_ip" ]]; then
            priority=$(expr 103 - $index)
        fi
        index=$(expr $index + 1)
    done

    ip_name=$(ip a s | grep $CURRENT_HOST_IP | awk '{print $NF}')

    cat <<EOF | sudo tee /etc/keepalived/keepalived.conf >/dev/null
vrrp_script chk_haproxy {
    script "killall -0 haproxy"
    interval 3 fall 3
}
vrrp_instance VRRP1 {
    state MASTER
    interface $ip_name
    virtual_router_id 51
    priority $priority
    advert_int 1
    virtual_ipaddress {
         $MASTER_CLUSTER_IP/24
    }
    track_script {
        chk_haproxy
    }
}
EOF
}

function start_keepalived {
    sudo systemctl enable keepalived.service
    sudo systemctl start keepalived.service
    sudo systemctl status keepalived.service | grep Active
    result=$(sudo systemctl status keepalived.service | \
        grep Active | grep "running")
    if [[ "$result" == "" ]]; then
        exit 0
    fi
}

function install_cri {
    cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
    overlay
    br_netfilter
EOF

    sudo modprobe overlay
    sudo modprobe br_netfilter

    cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
    net.bridge.bridge-nf-call-iptables  = 1
    net.bridge.bridge-nf-call-ip6tables = 1
    net.ipv4.ip_forward                 = 1
EOF

    sudo sysctl --system
    sleep 30
    curl -OLsS https://github.com/containerd/containerd/releases/download/v${CONTAINERD_VERSION}/containerd-${CONTAINERD_VERSION}-linux-amd64.tar.gz
    curl -OLsS https://github.com/containerd/containerd/releases/download/v${CONTAINERD_VERSION}/containerd-${CONTAINERD_VERSION}-linux-amd64.tar.gz.sha256sum
    sha256sum --check containerd-${CONTAINERD_VERSION}-linux-amd64.tar.gz.sha256sum
    sudo tar Cxzvf /usr/local containerd-${CONTAINERD_VERSION}-linux-amd64.tar.gz

    sudo curl https://raw.githubusercontent.com/containerd/containerd/main/containerd.service -o /usr/local/lib/systemd/system/containerd.service --create-dirs
    sudo systemctl daemon-reload
    sudo systemctl enable --now containerd

    curl -OLsS https://github.com/opencontainers/runc/releases/download/v${RUNC_VERSION}/runc.amd64
    curl -OLsS https://github.com/opencontainers/runc/releases/download/v${RUNC_VERSION}/runc.sha256sum
    grep runc.amd64 runc.sha256sum | sha256sum --check
    sudo install -m 755 runc.amd64 /usr/local/sbin/runc

    sudo mkdir /etc/containerd
    containerd config default | sudo tee /etc/containerd/config.toml
    sudo sed -i -e "s/SystemdCgroup = false/SystemdCgroup = true/" /etc/containerd/config.toml
    sudo systemctl restart containerd
    rm containerd-${CONTAINERD_VERSION}-linux-amd64.tar.gz{,.sha256sum} runc.amd64 runc.sha256sum
}

# Install Kubernetes
#-------------------
function set_k8s_components {
    REPOS_UPDATED=False apt_get_update
    sudo apt-get install -y apt-transport-https ca-certificates curl

    sudo mkdir -p -m 755 /etc/apt/keyrings
    curl -fsSL https://pkgs.k8s.io/core:/stable:/v${K8S_MINOR_VERSION}/deb/Release.key | \
        sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
    result=$?
    if [[ $result != 0 ]]; then
        exit 1
    fi

    echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v${K8S_MINOR_VERSION}/deb/ /" | \
        sudo tee /etc/apt/sources.list.d/kubernetes.list

    apt_get update
    apt_get install -y kubelet=$K8S_VERSION kubeadm=$K8S_VERSION kubectl=$K8S_VERSION
    sudo apt-mark hold kubelet kubeadm kubectl
    echo "starting kubelet, wait 30s ..."
    sleep 30
    sudo systemctl status kubelet | grep Active
}

function init_master {
    if [[ "$MASTER_IPADDRS" =~ "," ]]; then
        sudo kubeadm init --pod-network-cidr=$K8S_POD_CIDR \
            --service-cidr=$K8S_API_CLUSTER_CIDR \
            --control-plane-endpoint "$MASTER_CLUSTER_IP:16443" --upload-certs
    else
        sudo kubeadm init --pod-network-cidr=$K8S_POD_CIDR \
            --service-cidr=$K8S_API_CLUSTER_CIDR \
            --control-plane-endpoint "$MASTER_CLUSTER_IP:6443" --upload-certs
    fi
    sleep 3
    sudo mkdir -p $HOME/.kube
    sudo /bin/cp -f /etc/kubernetes/admin.conf $HOME/.kube/config
    sudo chown $(id -u):$(id -g) $HOME/.kube/config
    sleep 20
}

function install_cilium_cli {
    CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)
    CLI_ARCH=amd64
    if [ "$(uname -m)" = "aarch64" ]; then CLI_ARCH=arm64; fi
    curl -L --fail --remote-name-all https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-${CLI_ARCH}.tar.gz{,.sha256sum}
    sha256sum --check cilium-linux-${CLI_ARCH}.tar.gz.sha256sum
    sudo tar xzvfC cilium-linux-${CLI_ARCH}.tar.gz /usr/local/bin
    rm cilium-linux-${CLI_ARCH}.tar.gz{,.sha256sum}
}

function install_pod_network {
    install_cilium_cli
    if [ ${K8S_POD_CIDR} = "10.0.0.0/8" ]; then
        cilium install --version ${CILIUM_VERSION}
    else
        cilium install --version ${CILIUM_VERSION} --set ipam.operator.clusterPoolIPv4PodCIDRList=${K8S_POD_CIDR}
    fi
    cilium status --wait
}

function add_master_node {
    sudo kubeadm join $MASTER_CLUSTER_IP:16443 \
        --token $TOKEN_NAME \
        --discovery-token-ca-cert-hash sha256:$TOKEN_HASH \
        --control-plane --certificate-key $CERT_KEY
    sudo mkdir -p $HOME/.kube
    sudo /bin/cp -f /etc/kubernetes/admin.conf $HOME/.kube/config
    sudo chown $(id -u):$(id -g) $HOME/.kube/config
    echo "add node ..."
    sleep 10
    kubectl get nodes -o wide
    echo "add node successfully"
}

function init_worker {
    sudo kubeadm init --pod-network-cidr=$K8S_POD_CIDR \
        --service-cidr=$K8S_API_CLUSTER_CIDR
    sleep 5
    sudo mkdir -p $HOME/.kube
    sudo /bin/cp -f /etc/kubernetes/admin.conf $HOME/.kube/config
    sudo chown $(id -u):$(id -g) $HOME/.kube/config
    sleep 10
}

function add_worker_node {
    if [[ "$ha_flag" != "False" ]]; then
        KUBEADM_JOIN_WORKER_RESULT=$(sudo kubeadm join \
            $MASTER_CLUSTER_IP:16443 --token $TOKEN_NAME \
            --discovery-token-ca-cert-hash sha256:$TOKEN_HASH)
    else
        KUBEADM_JOIN_WORKER_RESULT=$(sudo kubeadm join \
        $MASTER_CLUSTER_IP:6443 --token $TOKEN_NAME \
        --discovery-token-ca-cert-hash sha256:$TOKEN_HASH)
    fi
}

# Set common functions
#
# Refer: devstack project functions-common
#-----------------------------------------
function apt_get_update {
    if [[ "$REPOS_UPDATED" == "True" ]]; then
        return
    fi

    local sudo="sudo"
    [[ "$(id -u)" = "0" ]] && sudo="env"

    # time all the apt operations
    time_start "apt-get-update"

    local update_cmd="sudo apt-get update"
    if ! timeout 300 sh -c "while ! $update_cmd; do sleep 30; done"; then
        die $LINENO "Failed to update apt repos, we're dead now"
    fi

    REPOS_UPDATED=True
    # stop the clock
    time_stop "apt-get-update"
}

function time_start {
    local name=$1
    local start_time=${_TIME_START[$name]}
    if [[ -n "$start_time" ]]; then
        die $LINENO \
        "Trying to start the clock on $name, but it's already been started"
    fi

    _TIME_START[$name]=$(date +%s%3N)
}

function time_stop {
    local name
    local end_time
    local elapsed_time
    local total
    local start_time

    name=$1
    start_time=${_TIME_START[$name]}

    if [[ -z "$start_time" ]]; then
        die $LINENO \
        "Trying to stop the clock on $name, but it was never started"
    fi
    end_time=$(date +%s%3N)
    elapsed_time=$(($end_time - $start_time))
    total=${_TIME_TOTAL[$name]:-0}
    # reset the clock so we can start it in the future
    _TIME_START[$name]=""
    _TIME_TOTAL[$name]=$(($total + $elapsed_time))
}

function apt_get {
    local xtrace result
    xtrace=$(set +o | grep xtrace)                    # set +o xtrace
    set +o xtrace

    [[ "$OFFLINE" = "True" || -z "$@" ]] && return
    local sudo="sudo"
    [[ "$(id -u)" = "0" ]] && sudo="env"

    # time all the apt operations
    time_start "apt-get"

    $xtrace

    $sudo DEBIAN_FRONTEND=noninteractive \
        apt-get --option "Dpkg::Options::=--force-confold" \
            --assume-yes "$@" < /dev/null
    result=$?

    # stop the clock
    time_stop "apt-get"
    return $result
}

# Choose install function based on install mode
#----------------------------------------------
function main_master {
    # prepare
    set_public_dns
    set_hostname
    set_sudoers
    set_hosts
    invalidate_swap
    if [[ "$MASTER_IPADDRS" =~ "," ]]; then
        # haproxy
        install_haproxy
        modify_haproxy_conf
        start_haproxy

        # keepalived
        install_keepalived
        modify_keepalived_conf
        start_keepalived
    fi

    install_cri

    # kubernetes
    set_k8s_components
    init_master
    install_pod_network

    clear
    token=$(sudo kubeadm token create)
    echo "token:$token"
    server=$(kubectl cluster-info | \
        sed 's,\x1B\[[0-9;]*[a-zA-Z],,g' | \
        grep 'Kubernetes' |awk '{print $7}')
    echo "server:$server"
    cat /etc/kubernetes/pki/ca.crt
    ssl_ca_cert_hash=$(openssl x509 -pubkey -in /etc/kubernetes/pki/ca.crt | \
        openssl rsa -pubin -outform der 2>/dev/null | \
        openssl dgst -sha256 -hex | sudo sed 's/^.* //')
    echo "ssl_ca_cert_hash:$ssl_ca_cert_hash"
    cert_key=$(sudo kubeadm init phase upload-certs --upload-certs 2> /dev/null | \
        tail -n 1)
    echo "certificate_key:$cert_key"
}

function normal_master {
    # prepare
    set_public_dns
    set_hostname
    set_sudoers
    set_hosts
    invalidate_swap

    # haproxy
    install_haproxy
    modify_haproxy_conf
    start_haproxy

    # keepalived
    install_keepalived
    modify_keepalived_conf
    start_keepalived

    # kubernetes
    install_cri
    set_k8s_components
    add_master_node
    install_cilium_cli
}

function main_worker {
    # prepare
    set_public_dns
    set_hostname
    set_sudoers
    set_hosts
    invalidate_swap

    # kubernetes
    install_cri
    set_k8s_components
    add_worker_node
}

# Pre preparations
# ________________

function check_OS {
    . /etc/os-release
    if [[ $PRETTY_NAME =~ "Ubuntu 22.04" ]]; then
        os_architecture=`uname -a | grep 'x86_64'`
        if [[ $os_architecture == "" ]]; then
            echo "Your OS does not support at present."
            echo "It only supports x86_64."
        fi
    else
        echo "Your OS does not support at present."
        echo "It only supports Ubuntu 22.04 LTS."
    fi
}

# Main
# ____

flag="False"
check_OS
if [[ "$INSTALL_MODE" =~ "master" ]]; then
    echo "Start install to main master node"
    for _ip in `ip -4 addr | grep -oP '(?<=inet\s)\d+(\.\d+){3}'`; do
        if [[ $_ip == $MASTER_IP ]]; then
            flag="True"
            break
        fi
    done
    if [[ "$flag" == "True" ]]; then
        INSTALL_MODE="main_master"
        main_master
    else
        INSTALL_MODE="normal_master"
        normal_master
    fi
elif [ "$INSTALL_MODE" == "worker" ]; then
    echo "Start install to worker node"
    main_worker
else
    echo "The install mode does not support at present!"
    exit 255
fi

if [[ "$INSTALL_MODE" =~ "master" ]]; then
    result=$(kubectl get nodes -o wide | grep $CURRENT_HOST_IP)
    if [[ -z "$result" ]];then
        echo "Install Failed! The node does not exist in Kubernetes cluster."
        exit 255
    else
        echo "Install Success!" | sudo tee /tmp/installed
    fi
else
    if [[ "$KUBEADM_JOIN_WORKER_RESULT" =~ \
        "This node has joined the cluster" ]]; then
        echo "Install Success!" | sudo tee /tmp/installed
    else
        echo "Install Failed! The node does not exist in Kubernetes cluster."
        exit 255
    fi
fi

sudo chmod 666 /var/lib/kubelet/config.yaml
exit 0
