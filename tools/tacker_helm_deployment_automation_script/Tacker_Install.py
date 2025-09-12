#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# File Name     : Tacker_install.py
# Description   : This script automates the installation of Tacker with all
#                 its dependencies over kubernetes environment.
# Author        : NEC Corp.
# Created Date  : 2025-07-18
# Last Modified : 2025-07-18
# Version       : 1.0
# Python Version: 3.10+
# -----------------------------------------------------------------------------

import logging
import subprocess
import sys
import json
import time
import yaml
import os
import pwd

##configuration variable
config = None

## Configure Logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s", filename= "./logs/script.log", filemode="a")

# -----------------------------------------------------------------------------
# Function Name : clear_repo
# Description   : deletes all the repo downloaded earlier and verifies the
#                 python version and ensures that user are created.
# Arguments     : none
# Returns       : none
# -----------------------------------------------------------------------------
def clear_repo():
    print("Inside function clear_repo")
    if not os.path.exists("logs"):
        os.makedirs("logs")
        os.system('touch logs/script.log')
    if sys.version_info.major<3:
        logging.error("The current python version is less than 3 update the version")
        logging.info("The current python version is less than 3 update the version")
        print("current python version is older")
        result= myshell("sudo apt update && sudo apt install python3 python3-pip -y", capture=True)
        logggig.debug("python3 installed %s", result)
        logggig.info("python3 installed %s", result)
        print("python3 installed \n")
    paths = ["./osh", "./openstack-helm"]
    k8s_path = "./osh"
    openstack_path = "./openstack-helm"
    for path in paths:
        if os.path.isfile(path):
            os.remove(k8s_path)
            print("repo removed: "+path+"\n")
    try:
        if pwd.getpwnam('ubuntu'):
            print("user ubuntu exists\n")
    except:
        print("creating user ubuntu")
        result = myshell("sudo useradd ubuntu -y",capture=True)
        logging.debug("ubutu user created %s", result)
        logging.info("ubutu user created %s", result)
# -----------------------------------------------------------------------------
# Function Name : load_config
# Description   : Loads the config data kept in config.yaml
# Arguments     : none
# Returns       : none
# -----------------------------------------------------------------------------
def load_config(filepath="./config/config.yaml"):
    global config
    with open(filepath, 'r') as file:
        config = yaml.safe_load(file)

# -----------------------------------------------------------------------------
# Function Name : myshell
# Description   : executes the requested command in a subshell.
# Arguments     : CMD - command string
#                 check - boolean, if true calls CalledProcessError if command
#                 returns non zero
#                 captures - boolean, captures the return of command
#                 **kw - dictionary, for any additional argument to pass.
# Returns       : result| None
# -----------------------------------------------------------------------------
def myshell(CMD: str, check=True, capture=False, **kw):
    logging.debug("CMD > %s", CMD)
    if capture:
        result = subprocess.run(CMD, shell=True, check=check, text=True, capture_output= capture, **kw)
        return result.stdout.strip()
    else:
        result = subprocess.run(CMD, shell=True, check=check, text=True, stdout=None, stderr=None, **kw)
        return None

# -----------------------------------------------------------------------------
# Function Name : handelexceptionshell
# Description   : executes the requested command in a subshell.
# Arguments     : CMD - command string
#                 check - boolean, if true calls CalledProcessError if command
#                 returns non zero
#                 captures - boolean, captures the return of command
#                 **kw - dictionary, for any additional argument to pass.
# Returns       : result| None
# -----------------------------------------------------------------------------
def handelexceptionshell(CMD: str, check=True, capture=False, **kw):
    logging.debug("CMD > %s", CMD)
    try:
        if capture:
            result = subprocess.run(CMD, shell=True, check=check, text=True, capture_output= capture, **kw)
            return result.stdout.strip()
        else:
            result = subprocess.run(CMD, shell=True, check=check, text=True, stdout=None, stderr=None, **kw)
            return None
    except subprocess.CalledProcessError as err:
        logging.warning("Command %s faced issue: %s",CMD, err)
        print("Issue while executing the command:  "+CMD+"\n")

# -----------------------------------------------------------------------------
# Function Name : pod_status
# Description   : Check the pod status to ensure that all pods are running.
# Arguments     : none
# Returns       : none
# -----------------------------------------------------------------------------
def pod_status():
    print("Inside the pod_status function \n")
    while True:
        command = "kubectl get pods -n " + config['K8S']['NAMESPACE'] + " -o json"
        endtime = time.time() + config['DURATION']['TIMEOUT']
        Jstatus = myshell(config['K8S']['SET_ENVIRONMENT']+" && "+command, capture=True)
        Lstatus = json.loads(Jstatus)
        not_ready = []
        for pod in Lstatus.get("items",[]):
            condition = {condition["type"]: condition["status"] for condition in pod["status"].get("conditions",[])}
            if condition.get("Ready") != "True":
                not_ready.append(pod["metadata"]["name"])
        if not not_ready:
            print("All pods are ready in namespace "+ config['K8S']['NAMESPACE'])
            logging.debug("kube-system pods in ready state \n")
            logging.info("kube-system pods in ready state")
            return
        if time.time > endtime:
            print("Error: pod status timedout after "+ str(endtime)+"\n")
            raise TimeoutError(f"Timed out after {timeout}s – still not ready: {', '.join(not_ready)}")
        time.sleep(config['DURATION']['POLL_INTERVAL'])

# -----------------------------------------------------------------------------
# Function Name : install_cluster
# Description   : Install kubernetes cluster and all its dependecies
# Arguments     : none
# Returns       : none
# -----------------------------------------------------------------------------
def install_cluster():
    print("Inside the install_cluster function\n ")
    try:
        result = myshell("mkdir -p osh", capture=True)
        print("osh folder created \n")
        result = myshell("cd ./osh && git clone " + config['REPOS']['OPENSTACK_REPO'] +" && git clone "+ config['REPOS']['ZUUL_REPO'], capture=True)
        logging.debug("git repo cloned for k8s cluster: %s", result)
        logging.info("git repo cloned for k8s cluster")
        print("git repo cloned for cluster: +", result+"\n")
    except subprocess.CalledProcessError as err:
        print("Repo did not download \n")
        logging.debug("Repo did not download %s", err)

    result = myshell("cd ./osh && pip install ansible netaddr", capture=True)
    result = myshell("cp ./k8s_env/inventory.yaml ./osh/ && cp ./k8s_env/deploy-env.yaml ./osh/", capture=True)
    logging.debug("inventory file copied %s", result)
    result = myshell("sudo apt install containerd python3-openstackclient -y", capture=True)
    print("result is: "+ str(result))
    logging.debug("cotainerD installed for k8s: %s", result)
    ### Here need to check how to create ssh-keygen for user ubuntu
    result = myshell("cd ./osh && export ANSIBLE_ROLES_PATH=~/osh/openstack-helm/roles:~/osh/zuul-jobs/roles &&  ansible-playbook -i inventory.yaml deploy-env.yaml", capture=False)
    print("kubernetes deployment successful ", result)
    logging.debug("kubernetes deployment successful result= %s", result)
    logging.info("kubernetes deployment successful result= %s", result)
    ### need to add the kubeconfig to be able to run kubectl command export KUBECONFIG=/etc/kubernetes/admin.conf && kubectl get pods -A
    print("Checking pod status .. ")
    pod_status()

# -----------------------------------------------------------------------------
# Function Name : install_dependecies
# Description   : verify system prerequisites and call for k8s installation
#                in case the k8s installation is not available.
# Arguments     : none
# Returns       : none
# -----------------------------------------------------------------------------
def install_dependecies():
    print("Inside install_dependencies function \n")
    verify_ubuntu = myshell("lsb_release -a", capture=True)
    logging.debug("ubuntu version details: %s",verify_ubuntu)
    print("ubuntu version details: %s",verify_ubuntu)
    first_line= verify_ubuntu.strip().split("\n")[0]
    if(str(first_line.split(":", -1)[1]).strip() != "Ubuntu"):
        logging.error("the OS is not Ubuntu")
        print("the OS is not Ubuntu")
        sys.exit()
    output = ""
    """
    ## disabled the below part for starlingx
    try:
        output = myshell("kubectl version --short", capture=True)
        print("kubernetes connection successful. %s ", output)
        logging.debug("kubernetes connection successful. %s ", output)
        logging.info("kubernetes conenction successful")
    except subprocess.CalledProcessError:
        logging.error("Kubernetes unrechable via the API\n %s", output)
        logging.info("Installing Kubernetes  %s", output)
        install_cluster()
    """
    try:
        result = myshell("helm version --short", capture=True)
        logging.debug("helm already available %s", result)
    except:
        logging.info("Installing helm on the system \n")
        print("Installing helm on the system \n")
        result = myshell("curl -fsSL -o get_helm.sh"+ config['HELM']['HELM_SCRIPT'], capture=True)
        logging.debug("helm script downloaded %s", result)
        result = myshell("chmod 700 get_helm.sh && ./get_helm.sh", capture=True)
        logging.info("helm installed: %s", result)
        print("helm installed: %s", result)

# -----------------------------------------------------------------------------
# Function Name : clone_code
# Description   : Ensure the openstack repo availability for deployment
# Arguments     : none
# Returns       : none
# -----------------------------------------------------------------------------
def clone_code():
    print("Inside the clone_code function \n")
    try:
        git_clone = myshell("git clone "+config['REPOS']['OPENSTACK_REPO'], capture=True)
        logging.debug("clone for the tacker repo done: %s", git_clone)
        print("clone for the tacker repo done: %s", istr(git_clone))
    except:
        print("could not clone the repo %s and %s to the node \n", config['REPOS']['OPENSTACK_REPO'], config['REPOS']['TACKER_INFRA_REPO'])
        logging.debug("could not clone the repo %s and %s to the node \n", config['REPOS']['OPENSTACK_REPO'], config['REPOS']['TACKER_INFRA_REPO'])


# -----------------------------------------------------------------------------
# Function Name : create_namespace
# Description   : Ensure that the preriquisites of the openstack installation
#                 are fulfilled.
# Arguments     : none
# Returns       : none
# -----------------------------------------------------------------------------
def create_namespace():
    print("Inside create_namespace function \n")
    try:
        result = myshell(config['K8S']['SET_ENVIRONMENT'] +" && kubectl get ns openstack", capture=True)
        logging.debug("namespace already existing ")
        print("namespace already existing ")
    except:
        logging.debug("namespace openstack not availble %s", result)
        result = myshell(config['K8S']['SET_ENVIRONMENT']+" && kubectl create ns openstack", capture=True)
        logging.debug("namespace openstack created %s", result)
        print("namespace openstack created %s", result)
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && kubectl label node "+config['NODES']['TACKER_NODE']+" openstack-control-plane=enabled", capture=True)
    logging.debug("master node labeling done: %s", result)
    result = myshell("helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx", capture=True)
    logging.debug("ingress repo added: %s", result)
    print("ingress repo added "+ result+"\n")
    result = myshell(config['K8S']['SET_ENVIRONMENT']+' && helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx --version="4.8.3" --namespace=openstack --set controller.kind=Deployment --set controller.admissionWebhooks.enabled="false" --set controller.scope.enabled="true" --set controller.service.enabled="false" --set controller.ingressClassResource.name=nginx --set controller.ingressClassResource.controllerValue="k8s.io/ingress-nginx" --set controller.ingressClassResource.default="false" --set controller.ingressClass=nginx --set controller.labels.app=ingress-api', capture=True)
    logging.debug("ingress created: %s", result)
    print("ingress created: %s", result)
    time.sleep(config['DURATION']['CHECK_INTERVAL'])
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && kubectl get pods -A | grep ingress && helm ls -A | grep ingress", capture=True)
    logging.debug("Ingress pod state: %s", result)
    print("Ingress pod state: %s \n", result)

# -----------------------------------------------------------------------------
# Function Name : deploy_openstack
# Description   : Install openstack services.
# Arguments     : none
# Returns       : none
# -----------------------------------------------------------------------------
def deploy_openstack():
    ## install rabbitmq
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && cd openstack-helm/rabbitmq && helm dependency build", capture=True)
    logging.debug("rabbitmq dependency installed %s", result)
    print("rabbitmq dependency installed %s\n", result)
    result = myshell(config['K8S']['SET_ENVIRONMENT']+"&& cd openstack-helm && ./tools/deployment/component/common/rabbitmq.sh", capture=True)
    logging.debug("rabbitmq installed: %s",result)
    time.sleep(config['DURATION']['CHECK_INTERVAL'])
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && kubectl get pods -A | grep rabbitmq && helm ls -A | grep rabbitmq", capture=True)
    logging.debug(" rabbitmq pod status: %s", result)
    print(" rabbitmq pod status: %s \n", result)

    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && cd openstack-helm/mariadb && helm dependency build", capture=True)
    logging.debug("mariadb dependency installed %s", result)
    print("mariadb dependency installed %s\n", result)
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && cd openstack-helm && ./tools/deployment/db/mariadb.sh", capture=True)
    logging.debug("mariadb installed: %s", result)
    print("mariadb installed: %s\n", result)
    time.sleep(config['DURATION']['CHECK_INTERVAL'])
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && kubectl get pods -A | grep mariadb && helm ls -A | grep mariadb", capture=True)
    logging.debug(" mariadb pod status: %s", result)
    print(" mariadb pod status: %s \n", result)

    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && cd openstack-helm/memcached && helm dependency build", capture=True)
    logging.debug("memcached dependency installed %s", result)
    print("memcached dependency installed %s\n", result)
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && cd openstack-helm && ./tools/deployment/component/common/memcached.sh", capture=True)
    logging.debug("memcached installed: %s", result)
    print("memcached installed: %s\n", result)
    time.sleep(config['DURATION']['CHECK_INTERVAL'])
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && kubectl get pods -A | grep memcached && helm ls -A | grep memcached", capture=True)
    logging.debug(" memcached pod status: %s", result)
    print(" memcached pod status: %s \n", result)
    result = myshell("cd openstack-helm/keystone && helm dependency build", capture=True)
    logging.debug("keystone dependency installed %s", result)
    print("keystone dependency installed %s\n", result)
    result = handelexceptionshell(config['K8S']['SET_ENVIRONMENT']+" && cd openstack-helm && ./tools/deployment/component/keystone/keystone.sh", capture=True)
    logging.debug("keystone installed: %s", result)
    print("keystone installed: %s \n", result)
    time.sleep(config['DURATION']['CHECK_INTERVAL'])
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && kubectl get pods -A | grep keystone && helm ls -A | grep keystone", capture=True)
    logging.debug(" keystone pod status: %s", result)
    print(" keystone pod status: %s \n", result)

    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && cd openstack-helm/glance && helm dependency build", capture=True)
    logging.debug("glance dependency installed %s", result)
    print("glance dependency installed %s\n", result)
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && kubectl apply -f ./volumes/local-storage-class.yaml", capture=True)
    logging.debug("Glance Storae class created  %s", result)
    print("Glance Storae class created "+str(result)+"\n")
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && kubectl apply -f ./volumes/local-pv-tempate.yaml", capture=True)
    logging.debug("Glance pv created  %s", result)
    print("Glance pv created "+ str(result)+"\n")
    result = handelexceptionshell(config['K8S']['SET_ENVIRONMENT']+" && cd openstack-helm && ./tools/deployment/component/glance/glance.sh", capture=True)
    logging.debug("glance installed: %s", result)
    print("glance installed: %s\n", result)
    time.sleep(config['DURATION']['CHECK_INTERVAL'])
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && kubectl get pods -A | grep glance && helm ls -A | grep glance", capture=True)
    logging.debug(" glance pod status: %s", result)
    print(" glance pod status: %s\n", result)

    result = myshell("cd openstack-helm/mariadb && helm dependency build", capture=True)
    logging.debug("mariadb dependency installed %s", result)
    print("mariadb dependency installed %s \n", result)
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && cd openstack-helm && ./tools/deployment/db/mariadb.sh", capture=True)
    logging.debug("mariadb installed: %s", result)
    print("mariadb installed: %s\n", result)
    time.sleep(config['DURATION']['CHECK_INTERVAL'])
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && kubectl get pods -A | grep mariadb && helm ls -A | grep mariadb", capture=True)
    logging.debug(" rabbitmq pod status: %s", result)
    print(" rabbitmq pod status: %s \n", result)

    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && cd openstack-helm/barbican && helm dependency build", capture=True)
    logging.debug("barbican dependency installed %s", result)
    print("barbican dependency installed %s\n", result)
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && cd openstack-helm && ./tools/deployment/component/barbican/barbican.sh", capture=True)
    logging.debug("barbican installed: %s", result)
    print("barbican installed: %s\n", result)
    time.sleep(config['DURATION']['CHECK_INTERVAL'])
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && kubectl get pods -A | grep barbican && helm ls -A | grep barbican", capture=True)
    logging.debug(" barbican pod status: %s", result)
    print(" barbican pod status: %s\n", result)


# -----------------------------------------------------------------------------
# Function Name : deploy_tacker
# Description   : Deploy tacker services
# Arguments     : none
#
# Returns       : none
# -----------------------------------------------------------------------------
def deploy_tacker():
    print("Inside deploy_tacker function \n")
    ## check PV here as well
    try:
        result = myshell(config['K8S']['SET_ENVIRONMENT']+" && kubectl apply -f ./volumes/task1-tacker-pv.yaml && kubectl apply -f ./volumes/task2-tacker-pv.yaml && kubectl apply -f ./volumes/task3-tacker-pv.yaml ", capture=True)
        logging.debug("Tacker pv created  %s", result)
        print("Tacker pv created  %s\n", result)
    except:
        logging.error("PV creation failed for Tacker ",result)
        print("PV creation failed for Tacker \n",result)
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && cd openstack-helm/tacker && helm dependency build", capture=True)
    logging.debug("Tacker dependency installed %s\n", result)
    print("Tacker dependency installed %s\n", result)
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && cd openstack-helm && ./tools/deployment/component/tacker/tacker.sh ", capture=True)
    logging.debug("tacker deployed: %s", result)
    print("tacker deployed: %s\n", result)
    result = myshell(config['K8S']['SET_ENVIRONMENT']+" && kubectl get pods -A | grep tacker && helm ls -A | grep tacker", capture=True)
    logging.debug("tacker pod status: %s", result)
    print("tacker pod status: %s\n", result)

# -----------------------------------------------------------------------------
# Function Name : main
# Description   : main function call other functions for deployment of tacker.
# Arguments     : none
#
# Returns       : none
# -----------------------------------------------------------------------------
def main():
    clear_repo()
    load_config()
    install_dependecies()
    clone_code()
    create_namespace()
    deploy_openstack()
    deploy_tacker()


if __name__ == "__main__":
    main()
