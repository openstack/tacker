#!/bin/bash

# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
# All Rights Reserved.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

# Uncomment for debugging.
#set -x

# Default values for optional inputs.
VIMC_DEFAULT_PROJ=admin
VIMC_DEFAULT_OS_DOMAIN=Default
VIMC_DEFAULT_TYPE=openstack
VIMC_DEFAULT_OUTPUT=vim_config.yaml
VIMC_DEFAULT_K8S_HELM_INFO_IP=127.0.0.1
VIMC_DEFAULT_K8S_HELM_INFO_USER=helm_user
VIMC_DEFAULT_K8S_HELM_INFO_PASS=helm_password

#######################################
# Find token from first entry of secrets.
# Returns:
#   Secret token retrieved from kubectl.
#######################################
function k8s_token() {
    # NOTES:
    # - Service account tokens are no longer automatically generated
    #   for each ServiceAccount in Kubernetes 1.24,
    #   so it is necessary to manually register Secret.
    kubectl create -f - <<EOF &>/dev/null
apiVersion: v1
kind: Secret
metadata:
  name: default-token-k8svim
  annotations:
    kubernetes.io/service-account.name: "default"
type: kubernetes.io/service-account-token
EOF

    echo $(kubectl get secret default-token-k8svim -o \
        jsonpath="{.data.token}" | base64 --decode)
}

#######################################
# Get endpoint of k8s.
# Returns:
#   URL of endpoint retrieved from kubectl.
#######################################
function k8s_endpoints() {
    local _attr="'kubeadm.kubernetes.io/kube-apiserver.advertise-address.endpoint'"
    _attr=${_attr//\./\\.}
    local _ep=$(kubectl get pods -A -o \
        jsonpath="{.items[*].metadata.annotations[$_attr]}")
    local _ep_array=($_ep)
    echo "https://${_ep_array[0]}"
}

#######################################
# Get cert from first entry of secrets.
# Returns:
#   Contents of CA sert retrieved from kubectl.
#######################################
function k8s_ssl_ca_cert() {
    echo $(kubectl get secrets default-token-k8svim -o \
        jsonpath="{.data.ca\.crt}" | base64 --decode)
}

#######################################
# Setup contents of config from given params and output to a file.
# Globals:
#   VIMC_OS_CERT_VERIFY
#   VIMC_OUTPUT
#   VIMC_ENDPOINT
#   VIMC_OS_USER
#   VIMC_OS_PASSWORD
#   VIMC_PROJ
#   VIMC_OS_PROJ_DOMAIN
#   VIMC_OS_USER_DOMAIN
# Outputs:
#   Writes contents of config for OpenStack VIM to a file, ${VIMC_OUTPUT}.
#######################################
function setup_os_config() {
    local _cert_verify=
    if "${VIMC_OS_CERT_VERIFY}"; then
        _cert_verify=True
    else
        _cert_verify=False
    fi

    cat << EOF > ${VIMC_OUTPUT}
auth_url: "${VIMC_ENDPOINT}"
username: "${VIMC_OS_USER}"
password: "${VIMC_OS_PASSWORD}"
project_name: "${VIMC_PROJ}"
domain_name: "${VIMC_OS_PROJ_DOMAIN}"
project_domain_name: "${VIMC_OS_PROJ_DOMAIN}"
user_domain_name: "${VIMC_OS_USER_DOMAIN}"
cert_verify: "${_cert_verify}"
EOF
}

#######################################
# Setup contents of config from given params and output to a file.
# Globals:
#   VIMC_K8S_USE_CERT
#   VIMC_K8S_USE_HELM
#   VIMC_K8S_HELM_INFO
#   VIMC_K8S_HELM_INFO_IP
#   VIMC_K8S_HELM_INFO_USER
#   VIMC_K8S_HELM_INFO_PASS
#   VIMC_OUTPUT
#   VIMC_ENDPOINT
#   VIMC_K8S_TOKEN
#   VIMC_PROJ
# Outputs:
#   Write contents of config for OpenStack Kubernetes to a file, ${VIMC_OUTPUT}.
#######################################
function setup_k8s_config() {
    # In the contents of cert, blanks are replaced with `\n` without
    # in header and footer. So, remove before the procedure at once, then
    # add after that again.
    local _cert_header="-----BEGIN CERTIFICATE-----"
    local _cert_footer="-----END CERTIFICATE-----"

    # Delimiter used temporarily for replacing blanks.
    local _delim=":"

    local _extra=""
    local _indent1="    "
    local _indent2="${_indent1}${_indent1}"

    if "${VIMC_K8S_USE_CERT}"; then
        local _k8s_cert=`k8s_ssl_ca_cert`
        _k8s_cert=`echo ${_k8s_cert} | sed "s/${_cert_header}//"`
        _k8s_cert=`echo ${_k8s_cert} | sed "s/${_cert_footer}//"`
        _k8s_cert=`echo ${_k8s_cert} | sed -e "s/ /${_delim}/g"`
        _k8s_cert=`echo \
            "${_cert_header}${_delim}${_k8s_cert}${_delim}${_cert_footer}"`
        _k8s_cert=`echo ${_k8s_cert} | sed -e "s/${_delim}/\\n/g"`
    else
        _k8s_cert="None"
    fi

    if "${VIMC_K8S_USE_HELM}"; then
        _extra="extra:"$'\n'"${_indent1}use_helm: true"
    fi

    if "${VIMC_K8S_HELM_INFO}"; then
        VIMC_K8S_HELM_INFO_IP=`echo ${VIMC_K8S_HELM_INFO_IP} | sed -e "s/,/\"\\n${_indent2}- \"/g"`
        _extra="extra:"$'\n'"${_indent1}helm_info:"$'\n'""
        _extra="${_extra}${_indent2}masternode_ip:"$'\n'"${_indent2}- \"${VIMC_K8S_HELM_INFO_IP}\""$'\n'""
        _extra="${_extra}${_indent2}masternode_username: \"${VIMC_K8S_HELM_INFO_USER}\""$'\n'""
        _extra="${_extra}${_indent2}masternode_password: \"${VIMC_K8S_HELM_INFO_PASS}\""
    fi

    cat << EOF > ${VIMC_OUTPUT}
auth_url: "${VIMC_ENDPOINT}"
bearer_token: "${VIMC_K8S_TOKEN}"
ssl_ca_cert: "${_k8s_cert}"
project_name: "${VIMC_PROJ}"
type: "kubernetes"
${_extra}
EOF
}

#######################################
# Show help message.
# Outputs:
#   Writes help message to stdout.
#######################################
function show_help() {
    cat << EOS
Generate config file for registering VIM

usage:
  $(basename $0) [-t VIM_TYPE] [-o OUTPUT_FILE] [-e ENDPOINT]
      [-p PROJECT_NAME] [--os-user USER_NAME] [--os-password PASSWORD]
      [--os-project-domain PROJECT_DOMAIN] [--os-user-domain USER_DOMAIN]
      [--os-disable-cert-verify] [--k8s-token TOKEN] [--k8s-use-cert]
      [--k8s-helm-info] [--k8s-helm-info-ip K8S_MASTER_NODE_IP]
      [--k8s-helm-info-user HELM_USER] [--k8s-helm-info-pass HELM_PASSWORD]
      [--k8s-use-helm] [-h]

options:
  All of options are optional.

  1) Common options
    -t|--type VIM_TYPE
      type of VIM.
        * 'openstack' or 'os' for OpenStack
        * 'kubernetes' or 'k8s' for Kubernetes
      default value is '${VIMC_DEFAULT_TYPE}'.
    -o|--output OUTPUT_FILE
      name of output file, default value is '${VIMC_DEFAULT_OUTPUT}'.
    -e|--endpoint ENDPOINT
      endpoint consists of url and port, such as 'https://127.0.0.1:6443'.
    -p|--project PROJECT_NAME
      name of project in which VIM is registered, default value is
      '${VIMC_DEFAULT_PROJ}'.
    -h|--help
      show this message.

  2) Options for OpenStack VIM
    --os-user USER_NAME
      name of OpenStack user, value of 'OS_USERNAME' is used by default.
    --os-password PASSWORD
      password of OpenStack user, value of 'OS_PASSWORD' is used by default.
    --os-project-domain PROJECT_DOMAIN
      name of project domain, value of 'OS_PROJECT_DOMAIN_ID' is used by
      default.
    --os-user-domain USER_DOMAIN
      name of user domain, value of 'OS_USER_DOMAIN_ID' is used by default.
    --os-disable-cert-verify
      use this option only if you set 'cert_verify' to False to disable
      verifying against system certificates for keystone.

  3) Options for Kubernetes VIM
    --k8s-token TOKEN
      bearer token.
    --k8s-use-cert
      use SSL CA cert.
    --k8s-helm-info
      configure VIM to use helm for v1 Tacker.
    --k8s-helm-info-ip K8S_MASTER_NODE_IP
      k8s master node IPs, such as '192.168.56.10,192.168.56.11'.
      can be used if --k8s-helm-info is specified, default value is '${VIMC_DEFAULT_K8S_HELM_INFO_IP}'.
    --k8s-helm-info-user HELM_USER
      user to login through ssh to execute the CLI command of Helm.
      can be used if --k8s-helm-info is specified, default value is '${VIMC_DEFAULT_K8S_HELM_INFO_USER}'.
    --k8s-helm-info-pass HELM_PASSWORD
      password of the user specified by --k8s-helm-info-user.
      can be used if --k8s-helm-info is specified, default value is '${VIMC_DEFAULT_K8S_HELM_INFO_PASS}'.
    --k8s-use-helm
      configure VIM to use helm for v2 Tacker.
EOS
}

#######################################
# Main function for OpenStack VIM config.
# Globals:
#   VIMC_ENDPOINT
#   VIMC_OS_USER
#   VIMC_OS_PASSWORD
#   VIMC_OS_PROJ_DOMAIN
#   VIMC_OS_USER_DOMAIN
#######################################
function os_main() {
    VIMC_ENDPOINT=${VIMC_ENDPOINT:-${OS_AUTH_URL}}
    if [ ! ${VIMC_ENDPOINT} ]; then
        clean_exit 1 \
            "Error: Set 'OS_AUTH_URL' or use '--endpoint'."
    fi

    VIMC_OS_USER=${VIMC_OS_USER:-${OS_USERNAME}}
    if [ ! ${VIMC_OS_USER} ]; then
        clean_exit 1 \
            "Error: No username found. Set 'OS_USERNAME' or use '--os-user'."
    fi

    VIMC_OS_PASSWORD=${VIMC_OS_PASSWORD:-${OS_PASSWORD}}
    if [ ! ${VIMC_OS_PASSWORD} ]; then
        clean_exit 1 \
            "Error: No password found. Set 'OS_PASSWORD' or use '--os-password'."
    fi

    VIMC_OS_PROJ_DOMAIN=${VIMC_OS_PROJ_DOMAIN:-${OS_PROJECT_DOMAIN_ID}}
    if [ ! ${VIMC_OS_PROJ_DOMAIN} ]; then
        VIMC_OS_PROJ_DOMAIN=${VIMC_DEFAULT_OS_DOMAIN}
    fi

    VIMC_OS_USER_DOMAIN=${VIMC_OS_USER_DOMAIN:-${OS_USER_DOMAIN_ID}}
    if [ ! ${VIMC_OS_USER_DOMAIN} ]; then
        VIMC_OS_USER_DOMAIN=${VIMC_DEFAULT_OS_DOMAIN}
    fi

    setup_os_config
}

#######################################
# Main function for Kubernetes VIM config.
# Globals:
#   VIMC_K8S_TOKEN
#   VIMC_ENDPOINT
#######################################
function k8s_main() {
    kubectl create clusterrolebinding cluster-admin-binding \
        --clusterrole cluster-admin --serviceaccount=default:default \
        &>/dev/null

    VIMC_K8S_TOKEN=${VIMC_K8S_TOKEN:-`k8s_token`}
    VIMC_ENDPOINT=${VIMC_ENDPOINT:-`k8s_endpoints`}

    setup_k8s_config
}

#######################################
# Re-wind OPTIND and clean all other variables as finalization.
# Globals:
#   OPTIND
#   PREV_OPTIND
#   VIMC_DEFAULT_TYPE
#   VIMC_DEFAULT_OUTPUT
#   VIMC_DEFAULT_PROJ
#   VIMC_DEFAULT_K8S_HELM_INFO_IP
#   VIMC_DEFAULT_K8S_HELM_INFO_USER
#   VIMC_DEFAULT_K8S_HELM_INFO_PASS
#   VIMC_TYPE
#   VIMC_OUTPUT
#   VIMC_ENDPOINT
#   VIMC_PROJ
#   VIMC_OS_USER
#   VIMC_OS_PASSWORD
#   VIMC_OS_PROJ_DOMAIN
#   VIMC_OS_USER_DOMAIN
#   VIMC_OS_CERT_VERIFY
#   VIMC_K8S_TOKEN
#   VIMC_K8S_USE_CERT
#   VIMC_K8S_USE_HELM
#   VIMC_K8S_HELM_INFO
#   VIMC_K8S_HELM_INFO_IP
#   VIMC_K8S_HELM_INFO_USER
#   VIMC_K8S_HELM_INFO_PASS
#######################################
function cleanup() {
    OPTIND=${PREV_OPTIND}
    VIMC_DEFAULT_TYPE=
    VIMC_DEFAULT_OUTPUT=
    VIMC_DEFAULT_PROJ=
    VIMC_DEFAULT_K8S_HELM_INFO_IP=
    VIMC_DEFAULT_K8S_HELM_INFO_USER=
    VIMC_DEFAULT_K8S_HELM_INFO_PASS=
    VIMC_TYPE=
    VIMC_OUTPUT=
    VIMC_ENDPOINT=
    VIMC_PROJ=
    VIMC_OS_USER=
    VIMC_OS_PASSWORD=
    VIMC_OS_PROJ_DOMAIN=
    VIMC_OS_USER_DOMAIN=
    VIMC_OS_CERT_VERIFY=
    VIMC_K8S_TOKEN=
    VIMC_K8S_USE_CERT=
    VIMC_K8S_USE_HELM=
    VIMC_K8S_HELM_INFO=
    VIMC_K8S_HELM_INFO_IP=
    VIMC_K8S_HELM_INFO_USER=
    VIMC_K8S_HELM_INFO_PASS=
}

#######################################
# Ensure cleanup before exit.
# Arguments:
#   Exit code (optional).
#   Error message to be output to stderr (optional).
#######################################
function clean_exit() {
    cleanup
    if [[ $2 != "" ]]; then
        echo $2 >&2
    fi
    exit $1
}

#######################################
# Main procedure is started from here.
#######################################
PREV_OPTIND=${OPTIND}
OPTIND=1

while getopts t:o:e:p:ch-: opt; do

    optarg=${OPTARG}
    if [[ "${opt}" = - ]]; then
        opt="-${OPTARG%%=*}"
        optarg="${OPTARG/${OPTARG%%=*}/}"
        optarg="${optarg#=}"

        if [[ -z "$optarg" ]] && [[ ! "${!OPTIND}" = -* ]]; then
            optarg="${!OPTIND}"
            shift
        fi
    fi

    case "-${opt}" in
        -t|--type)
            VIMC_TYPE=${optarg};
            ;;
        -o|--output)
            VIMC_OUTPUT=${optarg};
            ;;
        -e|--endpoint)
            VIMC_ENDPOINT=${optarg};
            ;;
        -p|--project)
            VIMC_PROJ=${optarg};
            ;;

        --os-user)
            VIMC_OS_USER=${optarg};
            ;;
        --os-password)
            VIMC_OS_PASSWORD=${optarg};
            ;;
        --os-project-domain)
            VIMC_OS_PROJ_DOMAIN=${optarg};
            ;;
        --os-user-domain)
            VIMC_OS_USER_DOMAIN=${optarg};
            ;;
        --os-disable-cert-verify)
            VIMC_OS_CERT_VERIFY=false;
            ;;

        --k8s-token)
            VIMC_K8S_TOKEN=${optarg};
            ;;
        --k8s-use-cert)
            VIMC_K8S_USE_CERT=true;
            ;;
        --k8s-helm-info)
            VIMC_K8S_HELM_INFO=true;
            ;;
        --k8s-helm-info-ip)
            VIMC_K8S_HELM_INFO_IP=${optarg};
            ;;
        --k8s-helm-info-user)
            VIMC_K8S_HELM_INFO_USER=${optarg};
            ;;
        --k8s-helm-info-pass)
            VIMC_K8S_HELM_INFO_PASS=${optarg};
            ;;
        --k8s-use-helm)
            VIMC_K8S_USE_HELM=true;
            ;;

        -h|--help)
            show_help;
            clean_exit;
            ;;
        --*)
            clean_exit 1 "Error: Illegal option '${opt##-}'.";
            ;;
    esac
done

VIMC_TYPE=${VIMC_TYPE:-${VIMC_DEFAULT_TYPE}}
VIMC_OUTPUT=${VIMC_OUTPUT:-${VIMC_DEFAULT_OUTPUT}}
VIMC_PROJ=${VIMC_PROJ:-${VIMC_DEFAULT_PROJ}}

VIMC_OS_CERT_VERIFY=${VIMC_OS_CERT_VERIFY:-true}
VIMC_K8S_USE_CERT=${VIMC_K8S_USE_CERT:-false}
VIMC_K8S_USE_HELM=${VIMC_K8S_USE_HELM:-false}
VIMC_K8S_HELM_INFO=${VIMC_K8S_HELM_INFO:-false}
VIMC_K8S_HELM_INFO_IP=${VIMC_K8S_HELM_INFO_IP:-${VIMC_DEFAULT_K8S_HELM_INFO_IP}}
VIMC_K8S_HELM_INFO_USER=${VIMC_K8S_HELM_INFO_USER:-${VIMC_DEFAULT_K8S_HELM_INFO_USER}}
VIMC_K8S_HELM_INFO_PASS=${VIMC_K8S_HELM_INFO_PASS:-${VIMC_DEFAULT_K8S_HELM_INFO_PASS}}

if [[ ${VIMC_TYPE} == "openstack" || ${VIMC_TYPE} == "os" ]]; then
    os_main
    echo "Config for OpenStack VIM '${VIMC_OUTPUT}' generated."
elif [[ ${VIMC_TYPE} == "kubernetes" || ${VIMC_TYPE} == "k8s" ]]; then
    k8s_main
    echo "Config for Kubernetes VIM '${VIMC_OUTPUT}' generated."
else
    echo "Error: No type matched with '${VIMC_TYPE}'." >&2
fi

cleanup
set +x
