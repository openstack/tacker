#!/bin/bash
set -o xtrace
###############################################################################
#
# This script will modify free5gc config file
# It's confirmed operation on Ubuntu of below.
#
# * OS type             : Ubuntu(64 bit)
# * OS version          : 18.04 LTS
# * OS architecture     : amd64 (x86_64)
# * Disk/Ram size       : 160GB/8GB
# * Pre setup user      : ubuntu
#
###############################################################################

#==============================================================================
# Usage Definition
#==============================================================================
function usage {
    sudo cat <<_EOT_
$(basename ${0}) is script to modify free5gc config file.

Usage:
  $(basename ${0}) [-A <amf config file path>]
    [-s <smf config file path>] [-u <upf config file path>]

Options:
  -A              The config file path of amf
  -a              The ip of amf
  -S              The config file path of smf
  -s              The ip of smf
  -U              The config file path of upf
  -u              The ip of upf
  --help, -h        Print this

_EOT_
    exit 1
}

declare -g AMF_CONFIG_FILE_PATH=${AMF_CONFIG_FILE_PATH:-}
declare -g SMF_CONFIG_FILE_PATH=${SMF_CONFIG_FILE_PATH:-}
declare -g UPF_CONFIG_FILE_PATH=${UPF_CONFIG_FILE_PATH:-}
declare -g AMF_IP=${AMF_IP:-}
declare -g SMF_IP=${SMF_IP:-}
declare -g UPF_IP=${UPF_IPADDRS:-}

if [ "$OPTIND" = 1 ]; then
    while getopts A:a:S:s:U:u:l:h OPT; do
        case $OPT in
        A)
            AMF_CONFIG_FILE_PATH=$OPTARG
            ;;
        a)
            AMF_IP=$OPTARG
            ;;
        S)
            SMF_CONFIG_FILE_PATH=$OPTARG
            ;;
        s)
            SMF_IP=$OPTARG
            ;;
        U)
            UPF_CONFIG_FILE_PATH=$OPTARG
            ;;
        u)
            UPF_IP=$OPTARG
            ;;
        l)
            UPF_IPADDRS=$OPTARG
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

# Pre preparations
# ________________

function check_OS {
    . /etc/os-release
    if [[ $PRETTY_NAME =~ "Ubuntu 18.04" ]]; then
        os_architecture=`uname -a | grep 'x86_64'`
        if [[ $os_architecture == "" ]]; then
            echo "Your OS does not support at present."
            echo "It only supports x86_64."
        fi
    else
        echo "Your OS does not support at present."
        echo "It only supports Ubuntu 18.04 LTS."
    fi
}
function set_sudoers {
    echo "admin ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/admin
}

# Main
# ____
check_OS
set_sudoers
# modify amf path
sed -i "s/- 10.10.0.6/- $AMF_IP/g" $AMF_CONFIG_FILE_PATH
# modify smf path
sed -i "s/addr: 10.10.0.6/addr: $SMF_IP/g" $SMF_CONFIG_FILE_PATH

sed -i "s/node_id: 172.168.151.92/node_id: $UPF_IP/g" $SMF_CONFIG_FILE_PATH

UPF_IPS=(${UPF_IPADDRS//,/ })
for upf_ip in ${UPF_IPS[@]}; do
    if [[ "$UPF_IP" != "$upf_ip" ]]; then
        sed -i "/^        node_id:*/a\      UPF2:\n        type: UPF\n        node_id: $upf_ip" $SMF_CONFIG_FILE_PATH
    fi
done
# modify upf path
sed -i "s/addr: 172.168.151.92/addr: $UPF_IP/g" $UPF_CONFIG_FILE_PATH
