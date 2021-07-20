#!/bin/bash
set -o xtrace
###############################################################################
#
# This script will insall external LoadBalancer.
# It's confirmed operation on Ubuntu of below.
#
# * OS type             : Ubuntu(64 bit)
# * OS version          : 20.04 LTS
# * OS architecture     : amd64 (x86_64)
# * Disk/Ram size       : 40GB/2GB
# * Pre setup user      : ubuntu
#
###############################################################################

#==============================================================================
# Usage Definition
#==============================================================================
function usage {
    sudo cat <<_EOT_
$(basename ${0}) is script to install external loadbalancer.

Usage:
  $(basename ${0}) [-d] [-o] [-m <master ip address>]
    [-w <worker ip address>]

Description:
  This script is to install external loadbalancer and set
  loadbalancer's configuration.

Options:
  -m              all master nodes ip(use "," to separate)
  -w              all worker nodes ip(use "," to separate)
  --help, -h      Print this

_EOT_
    exit 1
}

declare -g DEBUG_MODE="False"
declare -g OUTPUT_LOGFILE="False"
# master/worker ip
declare -g MASTER_IPADDRS=${MASTER_IPADDRS:-}
declare -a -g MASTER_IPS=${MASTER_IPS:-}
declare -g WORKER_IPADDRS=${WORKER_IPADDRS:-}
declare -a -g WORKER_IPS=${WORKER_IPS:-}

if [ "$OPTIND" = 1 ]; then
    while getopts dom:w:h OPT; do
        case $OPT in
        m)
            MASTER_IPADDRS=$OPTARG # 192.168.120.17,192.168.120.18
            MASTER_IPS=(${MASTER_IPADDRS//,/ })
            ;;
        w)
            WORKER_IPADDRS=$OPTARG # 192.168.120.2,192.168.120.3
            WORKER_IPS=(${WORKER_IPADDRS//,/ })
            ;;
        h)
            echo "h option. display help"
            usage
            ;;
        \?)
            echo "Try to enter the h option." 1>&2
            ;;
        esac
    done
else
    echo "No installed getopts-command." 1>&2
    exit 1
fi

# Install Haproxy
#----------------
function install_haproxy {
    REPOS_UPDATED=False apt_get_update
    apt_get install haproxy
}

function modify_haproxy_conf {
    cat <<EOF | sudo tee -a /etc/haproxy/haproxy.cfg >/dev/null
frontend kubernetes-apiserver
    mode                 tcp
    bind                 *:8383
    option               tcplog
    default_backend      kubernetes-apiserver
backend kubernetes-apiserver
    mode        tcp
    balance     roundrobin
EOF
    for master_ip in ${MASTER_IPS[@]}; do
        split_ips=(${master_ip//./ })
        cat <<EOF | sudo tee -a /etc/haproxy/haproxy.cfg >/dev/null
    server  master${split_ips[3]} $master_ip:6443 check
EOF
    done
    cat <<EOF | sudo tee -a /etc/haproxy/haproxy.cfg >/dev/null
backend kubernetes-nodeport
    mode        tcp
    balance     roundrobin
EOF
    for master_ip in ${MASTER_IPS[@]}; do
        split_ips=(${master_ip//./ })
        cat <<EOF | sudo tee -a /etc/haproxy/haproxy.cfg >/dev/null
    server  master${split_ips[3]} $master_ip check
EOF
    done
    for worker_ip in ${WORKER_IPS[@]}; do
        split_ips=(${worker_ip//./ })
        cat <<EOF | sudo tee -a /etc/haproxy/haproxy.cfg >/dev/null
    server  worker${split_ips[3]} $worker_ip check
EOF
    done
}

function start_haproxy {
    sudo systemctl enable haproxy
    sudo systemctl start haproxy
    sudo systemctl status haproxy | grep Active
    result=$(ss -lnt |grep -E "8383")
    if [[ -z $result ]]; then
        sudo systemctl restart haproxy
    fi
}

# Install Kubectl
#-------------------
function install_kubectl {
    REPOS_UPDATED=False apt_get_update
    sudo apt_get install -y apt-transport-https curl
    result=`curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
        sudo apt-key add -`
    if [[ $result != "OK" ]]; then
        exit 0
    fi
    echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | \
        sudo tee -a /etc/apt/sources.list.d/kubernetes.list
    apt_get update
    apt_get install -y kubectl
    mkdir -p $HOME/.kube
    touch $HOME/.kube/config

    sudo apt-get install mlocate
    locate bash_completion
    source /usr/share/bash-completion/bash_completion
    source <(kubectl completion bash)
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
        http_proxy=${http_proxy:-} https_proxy=${https_proxy:-} \
        no_proxy=${no_proxy:-} \
        apt-get --option "Dpkg::Options::=--force-confold" \
            --assume-yes "$@" < /dev/null
    result=$?

    # stop the clock
    time_stop "apt-get"
    return $result
}

# Pre preparations
# ________________

function check_OS {
    . /etc/os-release
    if [[ $PRETTY_NAME =~ "Ubuntu 20.04" ]]; then
        os_architecture=`uname -a | grep 'x86_64'`
        if [[ $os_architecture == "" ]]; then
            echo "Your OS does not support at present."
            echo "It only supports x86_64."
        fi
    else
        echo "Your OS does not support at present."
        echo "It only supports Ubuntu 20.04.1 LTS."
    fi
}

function set_sudoers {
    echo "ubuntu ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/ubuntu
}

function set_apt-conf_proxy {
    sudo touch /etc/apt/apt.conf.d/proxy.conf

    cat <<EOF | sudo tee /etc/apt/apt.conf.d/proxy.conf >/dev/null
Acquire::http::Proxy "${http_proxy}";
Acquire::https::Proxy "${https_proxy}";
EOF
}


# Main
# ____

# pre preparations
set_apt-conf_proxy
set_sudoers
check_OS

# install haproxy and set config file
install_haproxy
modify_haproxy_conf
start_haproxy

# install kubectl
install_kubectl
