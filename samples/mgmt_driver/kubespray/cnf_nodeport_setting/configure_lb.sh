#!/bin/bash
set -o xtrace
###############################################################################
#
# This script will set nodePort into external LoadBalancer.
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
  $(basename ${0}) [-d] [-o] [-i <nodePort info>]
  [-a <add configuration flag>]

Description:
  This script is to set nodePort info into external loadbalancer's
  configuration.

Options:
  -i              all nodePort info(use "#" to separate)
  -a              add/delete configuration flag
  --help, -h      Print this

_EOT_
    exit 1
}

declare -g DEBUG_MODE="False"
declare -g OUTPUT_LOGFILE="False"
# nodePort info
declare -g NODEPORTSTR=${NODEPORTSTR:-}
declare -a -g NODEPORTS=${NODEPORTS:-}
declare -g ADD_CONFIGURE_FLAG="True"


if [ "$OPTIND" = 1 ]; then
    while getopts doi:a:h OPT; do
        case $OPT in
        i)
            NODEPORTSTR=$OPTARG # defalut,test,8080,8011#mynamespace,nginx,8012
            NODEPORTS=(${NODEPORTSTR//#/ })
            ;;
        a)
            ADD_CONFIGURE_FLAG=$OPTARG
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

# Modify Haproxy
#----------------
function add_haproxy_conf {
    for(( i=0;i<${#NODEPORTS[@]};i++)); do
        split_node_port=(${NODEPORTS[i]//,/ })
        cat <<EOF | sudo tee -a /etc/haproxy/haproxy.cfg >/dev/null
frontend ${split_node_port[0]}_${split_node_port[1]}
    mode                 tcp
EOF
        unset split_node_port[0]
        unset split_node_port[1]
        all_node_port=("${split_node_port[@]}")
        for(( j=0;j<${#all_node_port[@]};j++)); do
            cat <<EOF | sudo tee -a /etc/haproxy/haproxy.cfg >/dev/null
    bind                 *:${all_node_port[j]}
EOF
        done
        cat <<EOF | sudo tee -a /etc/haproxy/haproxy.cfg >/dev/null
    option               tcplog
    default_backend      kubernetes-nodeport
EOF
    done
}

function delete_haproxy_conf {
    for(( i=0;i<${#NODEPORTS[@]};i++)); do
        split_node_port=(${NODEPORTS[i]//,/ })
        start_str=${split_node_port[0]}_${split_node_port[1]}
        end_str='default_backend      kubernetes-nodeport'
        start_line_no=`grep -n "$start_str" /etc/haproxy/haproxy.cfg | \
        cut -d ":" -f 1`
        end_line_no=`grep -n "$end_str" /etc/haproxy/haproxy.cfg | head -1 |\
        cut -d ":" -f 1`
        sudo sed -i "${start_line_no},${end_line_no}d" /etc/haproxy/haproxy.cfg
    done
}

function restart_haproxy {
    sudo systemctl restart haproxy
    sudo systemctl status haproxy | grep Active
    result=$(ss -lnt |grep -E "8383")
    if [[ -z $result ]]; then
        echo 'restart haproxy failed!'
        exit 255
    fi
}

# Main
# ____

# set config file
if [[ $ADD_CONFIGURE_FLAG == "True" ]]; then
    add_haproxy_conf
else
    delete_haproxy_conf
fi
restart_haproxy
