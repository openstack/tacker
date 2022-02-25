===================================================================
How to use Mgmt Driver for deploying Kubernetes Cluster (Kubespray)
===================================================================

Overview
--------

1. Mgmt Driver Introduction
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Mgmt Driver enables Users to configure their VNF before and/or after
its VNF Lifecycle Management operation. Users can customize the logic
of Mgmt Driver by implementing their own Mgmt Driver and these
customizations are specified by "interface" definition in
`NFV-SOL001 v2.6.1`_.
This user guide aims to deploy Kubernetes cluster via
Mgmt Driver which is customized by user.

2. Use Cases
^^^^^^^^^^^^
In the present user guide, the Kubernetes cluster is deployed by `Kubespray`_
(a tool to deploy Kubernetes cluster using ansible), so you need to set up a
server in advance to run Kubespray. The Load Balancer VM will be instantiated
together with the node of the Kubernetes cluster. You can access the
Kubernetes cluster through the Load Balancer. The Mgmt Driver can use
Kubespray to deploy Kubernetes cluster, install and configure the Load
Balancer. It only supports one case with the sample Mgmt Driver.

* simple: Deploy one master node with worker nodes. In this
  case, it supports to scale worker node and heal worker node.

Simple : Single Master Node
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The simple Kubernetes cluster contains one master node as controller node and
a Load Balancer VM for external access.
You can deploy it with the sample script we provided. The diagram below shows
simple Kubernetes cluster architecture:

.. code-block:: console

      +--------------+                       +--------------+
      | user traffic |                       | Kubespray    |
      |              |                       | (Pre-install)|
      +------+-------+                       +------+-------+
             |                                      |
             |To access pod                         |Install k8s cluster
             |Load Balancer SSH IP:NodePort         |
             |                                      |
             |                                      |
    +-------------------+                           |
    |   Load Balancer   |                           |
    |                   |                           |
    |   kubectl         |                           |
    +------+------------+                           |
           |                                        |
       +---|----------------------+-------------------------+
       |   |                      |                         |
       |   |----------------------|---+---------------------|---+
       |   |MasterNodeIP          |   |WorkerNodeIP1        |   |WorkerNodeIP2
       |   |:6443                 |   |:NodePort1           |   |:NodePort2
       v   v                      v   v                     v   v
    +-------------------+  +----------------------+  +----------------------+
    | MasterNode        |  | WorkerNode1          |  | WorkerNode2          |
    |      |            |  |          |           |  |          |           |
    |      |            |  |          |           |  |          |           |
    |      v            |  |          |           |  |          |           |
    |    +---------+    |  |          |           |  |          |           |
    |    | k8s-api |    |  |          |           |  |          |           |
    |    |         |    |  |          |           |  |          |           |
    |    +---------+    |  |          |           |  |          |           |
    |                   |  |          v           |  |          v           |
    |    +-------------------------------------------------------------+    |
    |    |                           Service                           |    |
    |    |                                                             |    |
    |    +----------------------------+-------------------------+------+    |
    |                   |  |          |           |  |          |           |
    |                   |  |          |CLUSTER-IP1|  |          |CLUSTER-IP2|
    |                   |  |          |:Port1     |  |          |:Port2     |
    |                   |  |          v           |  |          v           |
    |    +---------+    |  |     +---------+      |  |     +---------+      |
    |    |  etcd   |    |  |     |  pod    |      |  |     |  pod    |      |
    |    |         |    |  |     |         |      |  |     |         |      |
    |    +---------+    |  |     +---------+      |  |     +---------+      |
    +-------------------+  +----------------------+  +----------------------+

Preparations
------------
The preparations of OpenStack, ubuntu image and configuration of Mgmt Driver
is necessary for deploying Kubernetes cluster with Kubespray.
You can refer to `Preparations`_ in
`How to use Mgmt Driver for deploying Kubernetes Cluster`_ for the preparations of
the router's configuration of OpenStack,  ubuntu image, and usage of Mgmt
Driver file.

1. Configure Kubespray
^^^^^^^^^^^^^^^^^^^^^^
For this user guide, you should install Kubespray first. The Kubespray
version supported by this Mgmt Driver is **2.16.0**.
You can refer to the `Kubespray's official documentation`_ to install
Kubespray.

After you install Kubespray, you should modify the
**/etc/ansible/ansible.cfg** file to avoid the `host_key_checking`
when use Mgmt Driver to deploy the Kubernetes cluster.

.. code-block:: console

    $ sudo vi /etc/ansible/ansible.cfg
    ...
    # uncomment this to disable SSH key host checking
    host_key_checking = False
    ...

2. Upload ubuntu image
^^^^^^^^^^^^^^^^^^^^^^
Since the images used by master node, worker node, and Load Balancer are all
ubuntu 20.04, in order to save resources, we recommend creating an image on
openstack in advance and setting the name to the VNFD file.

The following is sample CLI command to create image.

.. code-block:: console

    $ openstack image create --file ubuntu-20.04-server-cloudimg-amd64.img \
       --container-format bare --disk-format qcow2 ubuntu-20.04-server-cloudimg-amd64
    +------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field            | Value                                                                                                                                                                    |
    +------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | container_format | bare                                                                                                                                                                     |
    | created_at       | 2021-09-03T02:26:46Z                                                                                                                                                     |
    | disk_format      | qcow2                                                                                                                                                                    |
    | file             | /v2/images/a99e9430-af8f-408d-acb2-9b0140a75974/file                                                                                                                     |
    | id               | a99e9430-af8f-408d-acb2-9b0140a75974                                                                                                                                     |
    | min_disk         | 0                                                                                                                                                                        |
    | min_ram          | 0                                                                                                                                                                        |
    | name             | ubuntu-20.04-server-cloudimg-amd64                                                                                                                                       |
    | owner            | 7e757a0cfea940dab100216036212a65                                                                                                                                         |
    | properties       | os_hidden='False', owner_specified.openstack.md5='', owner_specified.openstack.object='images/ubuntu-20.04-server-cloudimg-amd64-2', owner_specified.openstack.sha256='' |
    | protected        | False                                                                                                                                                                    |
    | schema           | /v2/schemas/image                                                                                                                                                        |
    | status           | queued                                                                                                                                                                   |
    | tags             |                                                                                                                                                                          |
    | updated_at       | 2021-09-03T02:26:46Z                                                                                                                                                     |
    | visibility       | shared                                                                                                                                                                   |
    +------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Create and Upload VNF Package
-----------------------------

You can refer to chapter `Create and Upload VNF Package`_ in
`How to use Mgmt Driver for deploying Kubernetes Cluster`_
for the introduction and usage of VNF Package.

1. Directory Structure
^^^^^^^^^^^^^^^^^^^^^^
The sample structure of VNF Package is shown below.

.. note::

    You can also find them in the
    `samples/mgmt_driver/kubernetes/kubespray/kubespray_vnf_package/`_
    directory of the tacker.

The directory structure:

* **TOSCA-Metadata/TOSCA.meta**
* **Definitions/**
* **Scripts/**
* **BaseHOT/**
* **UserData/**

.. code-block:: console

  !----TOSCA-Metadata
          !---- TOSCA.meta
  !----Definitions
          !---- etsi_nfv_sol001_common_types.yaml
          !---- etsi_nfv_sol001_vnfd_types.yaml
          !---- sample_kubernetes_top.vnfd.yaml
          !---- sample_kubernetes_types.yaml
          !---- sample_kubernetes_df_simple.yaml
  !----Scripts
          !---- install_external_lb.sh
          !---- kubespray_mgmt.py
  !----BaseHOT
          !---- simple
                  !---- nested
                          !---- base_hot_nested_master.yaml
                          !---- base_hot_nested_worker.yaml
                  !---- base_hot_top.yaml
  !----UserData
          !---- __init__.py
          !---- lcm_user_data.py

Deploy Kubernetes Cluster
-------------------------

Single Master Node
^^^^^^^^^^^^^^^^^^

A single master Kubernetes cluster can be installed by Kubespray
and set up in "instantiate_end" operation, which allows you to
execute any scripts after its instantiation, and it's enabled
with Mgmt Driver support. Deploying Kubernetes cluster with Kubespray
only supports one master node and multiple worker nodes.

1. Create the Parameter File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a ``simple_kubernetes_param_file.json`` file with the following format.
This file defines the parameters which will be set
in the body of the instantiate request.

Other parameters are the same as the configuration in
`How to use Mgmt Driver for deploying Kubernetes Cluster`_, you can refer to
`Create the Parameter File`_ for detailed configuration. This user guide
mainly modified ``k8s_cluster_installation_param`` to adapt to Kubespray.

**Explanation of the parameters for deploying a Kubernetes cluster**

For deploying Kubernetes cluster, you must set the
``k8s_cluster_installation_param`` key in additionalParams.
The KeyValuePairs is shown in table below:

.. list-table:: **List of additionalParams.k8s_cluster_installation_param(specified by user)**
   :widths: 20 10 40 15
   :header-rows: 1

   * - parameter
     - data type
     - description
     - required/optional
   * - vim_name
     - String
     - The vim name of deployed Kubernetes cluster registered by tacker
     - optional
   * - master_node
     - dict
     - Information for the VM of the master node group
     - required
   * - worker_node
     - dict
     - Information for the VM of the master node group
     - required
   * - proxy
     - dict
     - Information for proxy setting on VM
     - optional
   * - ansible
     - dict
     - Specify Ansible related configuration such as ip address
       (``ip_address``) and playbook (``kubespray_root_path``) to execute
     - required
   * - external_lb_param
     - dict
     - Properties to install External Load Balancer
     - required

.. list-table::  **master_node dict**
   :widths: 20 10 40 15
   :header-rows: 1

   * - parameter
     - data type
     - description
     - required/optional
   * - aspect_id
     - String
     - The resource name of the master node group, and is same as the
       `aspect` in `vnfd`. If you use user data, it must be set
     - optional
   * - ssh_cp_name
     - String
     - Resource name of port corresponding to the master node's ssh ip
     - required
   * - nic_cp_name
     - String
     - Resource name of port corresponding to the master node's nic ip
       (which used for deploying Kubernetes cluster).
       If ssh ip is floating ip, this is required
     - optional
   * - username
     - String
     - Username for VM access
     - required
   * - password
     - String
     - Password for VM access
     - required
   * - pod_cidr
     - String
     - CIDR for pod
     - optional
   * - cluster_cidr
     - String
     - CIDR for service
     - optional

.. list-table::  **worker_node dict**
   :widths: 20 10 40 15
   :header-rows: 1

   * - parameter
     - data type
     - description
     - required/optional
   * - aspect_id
     - String
     - The resource name of the worker node group, and is same as the
       `aspect` in `vnfd`. If you use user data, it must be set
     - optional
   * - ssh_cp_name
     - String
     - Resource name of port corresponding to the worker node's ssh ip
     - required
   * - nic_cp_name
     - String
     - Resource name of port corresponding to the worker node's nic ip
       (which used for deploying Kubernetes cluster).
       If ssh ip is floating ip, this is required
     - optional
   * - username
     - String
     - Username for VM access
     - required
   * - password
     - String
     - Password for VM access
     - required

.. list-table::  **proxy dict**
   :widths: 20 10 40 15
   :header-rows: 1

   * - parameter
     - data type
     - description
     - required/optional
   * - http_proxy
     - String
     - Http proxy server address
     - optional
   * - https_proxy
     - String
     - Https proxy server address
     - optional

.. list-table::  **ansible dict**
   :widths: 20 10 40 15
   :header-rows: 1

   * - parameter
     - data type
     - description
     - required/optional
   * - ip_address
     - String
     - IP address of Ansible server
     - required
   * - username
     - String
     - Username of Ansible server
     - required
   * - password
     - String
     - Password of Ansible server
     - required
   * - kubespray_root_path
     - String
     - Root directory of kubespray
     - required
   * - transferring_inventory_path
     - String
     - Target path to transfer the generated inventory file
     - required

.. list-table::  **external_lb_param dict**
   :widths: 20 10 40 15
   :header-rows: 1

   * - parameter
     - data type
     - description
     - required/optional
   * - ssh_cp_name
     - String
     - Resource name of CP to access to deployed VM via SSH
     - required
   * - ssh_username
     - String
     - User name of deployed VM to access via SSH
     - required
   * - ssh_password
     - String
     - Password of deployed VM to access via SSH
     - required
   * - script_path
     - String
     - Path of the installation shell script for External Load Balancer
     - required

simple_kubernetes_param_file.json

.. code-block::

    {
        "flavourId": "simple",
        "vimConnectionInfo": [{
            "id": "daa80cf2-9b73-4806-8176-56cd6fab8cea",
            "vimId": "c3369b54-e376-4423-bb61-afd255900fea", #Set the uuid of the VIM to use
            "vimType": "openstack"
        }],
        "additionalParams": {
            "k8s_cluster_installation_param": {
                "vim_name": "kubernetes_vim",
                "master_node": {
                    "aspect_id": "master_instance",
                    "ssh_cp_name": "masterNode_FloatingIP",
                    "nic_cp_name": "masterNode_CP1",
                    "username": "ubuntu",
                    "password": "ubuntu",
                    "pod_cidr": "192.168.0.0/16",
                    "cluster_cidr": "10.199.187.0/24"
                },
                "worker_node": {
                    "aspect_id": "worker_instance",
                    "ssh_cp_name": "workerNode_FloatingIP",
                    "nic_cp_name": "workerNode_CP2",
                    "username": "ubuntu",
                    "password": "ubuntu"
                },
                "proxy": {
                    "http_proxy": "http://user1:password1@host1:port1",
                    "https_proxy": "https://user2:password2@host2:port2"
                },
                "ansible": {
                    "ip_address": "10.10.0.50", # set your own Kubespray server's ssh_ip
                    "username": "ubuntu",
                    "password": "ubuntu",
                    "kubespray_root_path": "/home/ubuntu/kubespray-2.16.0",
                    "transferring_inventory_path": "/home/ubuntu/kubespray-2.16.0/inventory/mycluster"
                },
                "external_lb_param": {
                    "ssh_cp_name": "externalLB_FloatingIP",
                    "ssh_username": "ubuntu",
                    "ssh_password": "ubuntu",
                    "script_path": "Scripts/install_external_lb.sh"
                }
            },
            "lcm-operation-user-data": "./UserData/lcm_user_data.py",
            "lcm-operation-user-data-class": "SampleUserData"
        },
        "extVirtualLinks": [{
            "id": "35d69de0-bf3b-4690-8724-16e9edb68b19",
            "resourceId": "1642ac54-642c-407c-9c7d-e94c55ba5d33", #Set the uuid of the network to use
            "extCps": [{
                "cpdId": "masterNode_CP1",
                "cpConfig": [{
                    "linkPortId": "35d69de0-bf3b-4690-8724-16e9edb68b19"
                }]
            }]
        }, {
            "id": "fb60ddb1-8787-49cd-8439-d379a449b6fa",
            "resourceId": "1642ac54-642c-407c-9c7d-e94c55ba5d33", #Set the uuid of the network to use
            "extCps": [{
                "cpdId": "workerNode_CP2",
                "cpConfig": [{
                    "linkPortId": "fb60ddb1-8787-49cd-8439-d379a449b6fa"
                }]
            }]
        }, {
            "id": "dd462031-64d6-4fed-be90-b9c366223a12",
            "resourceId": "1642ac54-642c-407c-9c7d-e94c55ba5d33", #Set the uuid of the network to use
            "extCps": [{
                "cpdId": "externalLB_CP3",
                "cpConfig": [{
                    "linkPortId": "dd462031-64d6-4fed-be90-b9c366223a12"
                }]
            }]
        }]
    }

.. note::
    If you want to deploy multiple Kubernetes cluster in OpenStack, you must
    set different **transferring_inventory_path** in `ansible` parameter.

2. Execute the Instantiation Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute the following CLI command to instantiate the VNF instance.

.. code-block:: console

    $ openstack vnflcm create b1db0ce7-ebca-2fb7-95ed-4840d70a1163
    +--------------------------+---------------------------------------------------------------------------------------------+
    | Field                    | Value                                                                                       |
    +--------------------------+---------------------------------------------------------------------------------------------+
    | ID                       | 4cdc110f-b21e-4b79-b3f5-252ee5937a36                                                        |
    | Instantiation State      | NOT_INSTANTIATED                                                                            |
    | Links                    | {                                                                                           |
    |                          |     "self": {                                                                               |
    |                          |         "href": "/vnflcm/v1/vnf_instances/4cdc110f-b21e-4b79-b3f5-252ee5937a36"             |
    |                          |     },                                                                                      |
    |                          |     "instantiate": {                                                                        |
    |                          |         "href": "/vnflcm/v1/vnf_instances/4cdc110f-b21e-4b79-b3f5-252ee5937a36/instantiate" |
    |                          |     }                                                                                       |
    |                          | }                                                                                           |
    | VNF Instance Description | None                                                                                        |
    | VNF Instance Name        | vnf-4cdc110f-b21e-4b79-b3f5-252ee5937a36                                                    |
    | VNF Product Name         | Sample VNF                                                                                  |
    | VNF Provider             | Company                                                                                     |
    | VNF Software Version     | 1.0                                                                                         |
    | VNFD ID                  | b1db0ce7-ebca-2fb7-95ed-4840d70a1163                                                        |
    | VNFD Version             | 1.0                                                                                         |
    | vnfPkgId                 |                                                                                             |
    +--------------------------+---------------------------------------------------------------------------------------------+
    $ openstack vnflcm instantiate 4cdc110f-b21e-4b79-b3f5-252ee5937a36 ./simple_kubernetes_param_file.json
    Instantiate request for VNF Instance 4cdc110f-b21e-4b79-b3f5-252ee5937a36 has been accepted.
    $ openstack vnflcm show 4cdc110f-b21e-4b79-b3f5-252ee5937a36
    +--------------------------+--------------------------------------------------------------------------------------------------+
    | Field                    | Value                                                                                            |
    +--------------------------+--------------------------------------------------------------------------------------------------+
    | ID                       | 4cdc110f-b21e-4b79-b3f5-252ee5937a36                                                             |
    | Instantiated Vnf Info    | {                                                                                                |
    |                          |     "flavourId": "simple",                                                                       |
    |                          |     "vnfState": "STARTED",                                                                       |
    |                          |     "scaleStatus": [                                                                             |
    |                          |         {                                                                                        |
    |                          |             "aspectId": "master_instance",                                                       |
    |                          |             "scaleLevel": 0                                                                      |
    |                          |         },                                                                                       |
    |                          |         {                                                                                        |
    |                          |             "aspectId": "worker_instance",                                                       |
    |                          |             "scaleLevel": 0                                                                      |
    |                          |         }                                                                                        |
    |                          |     ],                                                                                           |
    |                          |     "extCpInfo": [                                                                               |
    |                          |         {                                                                                        |
    |                          |             "id": "ebe12a4c-5cbf-4b19-848b-d68592f27dd7",                                        |
    |                          |             "cpdId": "masterNode_CP1",                                                           |
    |                          |             "extLinkPortId": null,                                                               |
    |                          |             "associatedVnfcCpId": "dc0e4e27-91e1-4ff1-8aba-48e402e18092",                        |
    |                          |             "cpProtocolInfo": []                                                                 |
    |                          |         },                                                                                       |
    |                          |         {                                                                                        |
    |                          |             "id": "4a6db6a4-1048-4f6f-83cf-0fccda25e92c",                                        |
    |                          |             "cpdId": "workerNode_CP2",                                                           |
    |                          |             "extLinkPortId": null,                                                               |
    |                          |             "associatedVnfcCpId": "f8829938-d57e-4b96-b383-cf3783651822",                        |
    |                          |             "cpProtocolInfo": []                                                                 |
    |                          |         },                                                                                       |
    |                          |         {                                                                                        |
    |                          |             "id": "538c068e-c2c4-449d-80f6-383242c602f2",                                        |
    |                          |             "cpdId": "externalLB_CP3",                                                           |
    |                          |             "extLinkPortId": null,                                                               |
    |                          |             "associatedVnfcCpId": "d5c51363-1acd-4f72-b98b-cd2f8da810f9",                        |
    |                          |             "cpProtocolInfo": []                                                                 |
    |                          |         }                                                                                        |
    |                          |     ],                                                                                           |
    |                          |     "extVirtualLinkInfo": [                                                                      |
    |                          |         {                                                                                        |
    |                          |             "id": "35d69de0-bf3b-4690-8724-16e9edb68b19",                                        |
    |                          |             "resourceHandle": {                                                                  |
    |                          |                 "vimConnectionId": null,                                                         |
    |                          |                 "resourceId": "1642ac54-642c-407c-9c7d-e94c55ba5d33",                            |
    |                          |                 "vimLevelResourceType": null                                                     |
    |                          |             }                                                                                    |
    |                          |         },                                                                                       |
    |                          |         {                                                                                        |
    |                          |             "id": "fb60ddb1-8787-49cd-8439-d379a449b6fa",                                        |
    |                          |             "resourceHandle": {                                                                  |
    |                          |                 "vimConnectionId": null,                                                         |
    |                          |                 "resourceId": "1642ac54-642c-407c-9c7d-e94c55ba5d33",                            |
    |                          |                 "vimLevelResourceType": null                                                     |
    |                          |             }                                                                                    |
    |                          |         },                                                                                       |
    |                          |         {                                                                                        |
    |                          |             "id": "dd462031-64d6-4fed-be90-b9c366223a12",                                        |
    |                          |             "resourceHandle": {                                                                  |
    |                          |                 "vimConnectionId": null,                                                         |
    |                          |                 "resourceId": "1642ac54-642c-407c-9c7d-e94c55ba5d33",                            |
    |                          |                 "vimLevelResourceType": null                                                     |
    |                          |             }                                                                                    |
    |                          |         }                                                                                        |
    |                          |     ],                                                                                           |
    |                          |     "vnfcResourceInfo": [                                                                        |
    |                          |         {                                                                                        |
    |                          |             "id": "d5c51363-1acd-4f72-b98b-cd2f8da810f9",                                        |
    |                          |             "vduId": "externalLB",                                                               |
    |                          |             "computeResource": {                                                                 |
    |                          |                 "vimConnectionId": "c3369b54-e376-4423-bb61-afd255900fea",                       |
    |                          |                 "resourceId": "6361ae44-7d34-4afc-b89b-00b2445425de",                            |
    |                          |                 "vimLevelResourceType": "OS::Nova::Server"                                       |
    |                          |             },                                                                                   |
    |                          |             "storageResourceIds": [],                                                            |
    |                          |             "vnfcCpInfo": [                                                                      |
    |                          |                 {                                                                                |
    |                          |                     "id": "ec72958c-16ff-4947-94c8-e5e32c3c453b",                                |
    |                          |                     "cpdId": "externalLB_CP3",                                                   |
    |                          |                     "vnfExtCpId": "dd462031-64d6-4fed-be90-b9c366223a12",                        |
    |                          |                     "vnfLinkPortId": "7db09403-cc2c-42c9-9661-438b9345a549"                      |
    |                          |                 }                                                                                |
    |                          |             ]                                                                                    |
    |                          |         },                                                                                       |
    |                          |         {                                                                                        |
    |                          |             "id": "dc0e4e27-91e1-4ff1-8aba-48e402e18092",                                        |
    |                          |             "vduId": "masterNode",                                                               |
    |                          |             "computeResource": {                                                                 |
    |                          |                 "vimConnectionId": "c3369b54-e376-4423-bb61-afd255900fea",                       |
    |                          |                 "resourceId": "5877e1ba-dfe0-4a9e-9ddf-08a6590942c4",                            |
    |                          |                 "vimLevelResourceType": "OS::Nova::Server"                                       |
    |                          |             },                                                                                   |
    |                          |             "storageResourceIds": [],                                                            |
    |                          |             "vnfcCpInfo": [                                                                      |
    |                          |                 {                                                                                |
    |                          |                     "id": "ae5d8222-ac43-4a89-a1b0-1d414c84f5c9",                                |
    |                          |                     "cpdId": "masterNode_CP1",                                                   |
    |                          |                     "vnfExtCpId": "35d69de0-bf3b-4690-8724-16e9edb68b19",                        |
    |                          |                     "vnfLinkPortId": "23d92486-3584-49ed-afd1-0e5a71750269"                      |
    |                          |                 }                                                                                |
    |                          |             ]                                                                                    |
    |                          |         },                                                                                       |
    |                          |         {                                                                                        |
    |                          |             "id": "f8829938-d57e-4b96-b383-cf3783651822",                                        |
    |                          |             "vduId": "workerNode",                                                               |
    |                          |             "computeResource": {                                                                 |
    |                          |                 "vimConnectionId": "c3369b54-e376-4423-bb61-afd255900fea",                       |
    |                          |                 "resourceId": "b8cc0d5b-600a-47eb-a67f-45d4d6051c44",                            |
    |                          |                 "vimLevelResourceType": "OS::Nova::Server"                                       |
    |                          |             },                                                                                   |
    |                          |             "storageResourceIds": [],                                                            |
    |                          |             "vnfcCpInfo": [                                                                      |
    |                          |                 {                                                                                |
    |                          |                     "id": "140332c5-a9b1-4663-b3e3-8006ed1b26ea",                                |
    |                          |                     "cpdId": "workerNode_CP2",                                                   |
    |                          |                     "vnfExtCpId": "fb60ddb1-8787-49cd-8439-d379a449b6fa",                        |
    |                          |                     "vnfLinkPortId": "02c54919-290c-42a4-a0f0-dbff2b7a4725"                      |
    |                          |                 }                                                                                |
    |                          |             ]                                                                                    |
    |                          |         },                                                                                       |
    |                          |         {                                                                                        |
    |                          |             "id": "cebda558-e1bd-4b98-9e11-c60a1e9fcdd7",                                        |
    |                          |             "vduId": "workerNode",                                                               |
    |                          |             "computeResource": {                                                                 |
    |                          |                 "vimConnectionId": "c3369b54-e376-4423-bb61-afd255900fea",                       |
    |                          |                 "resourceId": "89b58460-df0a-41c8-82ce-8386491d65d8",                            |
    |                          |                 "vimLevelResourceType": "OS::Nova::Server"                                       |
    |                          |             },                                                                                   |
    |                          |             "storageResourceIds": [],                                                            |
    |                          |             "vnfcCpInfo": [                                                                      |
    |                          |                 {                                                                                |
    |                          |                     "id": "63124ada-576a-44d4-a9c8-eec5f53fc776",                                |
    |                          |                     "cpdId": "workerNode_CP2",                                                   |
    |                          |                     "vnfExtCpId": "fb60ddb1-8787-49cd-8439-d379a449b6fa",                        |
    |                          |                     "vnfLinkPortId": "c43a748a-4fd4-4d2f-9545-c0faec985001"                      |
    |                          |                 }                                                                                |
    |                          |             ]                                                                                    |
    |                          |         }                                                                                        |
    |                          |     ],                                                                                           |
    |                          |     "vnfVirtualLinkResourceInfo": [                                                              |
    |                          |         {                                                                                        |
    |                          |             "id": "e3167cae-64e4-471d-83f8-93f1ed0701f0",                                        |
    |                          |             "vnfVirtualLinkDescId": "35d69de0-bf3b-4690-8724-16e9edb68b19",                      |
    |                          |             "networkResource": {                                                                 |
    |                          |                 "vimConnectionId": null,                                                         |
    |                          |                 "resourceId": "1642ac54-642c-407c-9c7d-e94c55ba5d33",                            |
    |                          |                 "vimLevelResourceType": "OS::Neutron::Net"                                       |
    |                          |             },                                                                                   |
    |                          |             "vnfLinkPorts": [                                                                    |
    |                          |                 {                                                                                |
    |                          |                     "id": "23d92486-3584-49ed-afd1-0e5a71750269",                                |
    |                          |                     "resourceHandle": {                                                          |
    |                          |                         "vimConnectionId": "c3369b54-e376-4423-bb61-afd255900fea",               |
    |                          |                         "resourceId": "2fecdfa7-bb48-4a59-81a7-aa369a3b8ab8",                    |
    |                          |                         "vimLevelResourceType": "OS::Neutron::Port"                              |
    |                          |                     },                                                                           |
    |                          |                     "cpInstanceId": "ae5d8222-ac43-4a89-a1b0-1d414c84f5c9"                       |
    |                          |                 }                                                                                |
    |                          |             ]                                                                                    |
    |                          |         },                                                                                       |
    |                          |         {                                                                                        |
    |                          |             "id": "28ee72d2-eacd-4d97-ab3b-aae552db4ca1",                                        |
    |                          |             "vnfVirtualLinkDescId": "fb60ddb1-8787-49cd-8439-d379a449b6fa",                      |
    |                          |             "networkResource": {                                                                 |
    |                          |                 "vimConnectionId": null,                                                         |
    |                          |                 "resourceId": "1642ac54-642c-407c-9c7d-e94c55ba5d33",                            |
    |                          |                 "vimLevelResourceType": "OS::Neutron::Net"                                       |
    |                          |             },                                                                                   |
    |                          |             "vnfLinkPorts": [                                                                    |
    |                          |                 {                                                                                |
    |                          |                     "id": "02c54919-290c-42a4-a0f0-dbff2b7a4725",                                |
    |                          |                     "resourceHandle": {                                                          |
    |                          |                         "vimConnectionId": "c3369b54-e376-4423-bb61-afd255900fea",               |
    |                          |                         "resourceId": "82f78566-7746-4b58-a03d-c40602279e6c",                    |
    |                          |                         "vimLevelResourceType": "OS::Neutron::Port"                              |
    |                          |                     },                                                                           |
    |                          |                     "cpInstanceId": "140332c5-a9b1-4663-b3e3-8006ed1b26ea"                       |
    |                          |                 },                                                                               |
    |                          |                 {                                                                                |
    |                          |                     "id": "c43a748a-4fd4-4d2f-9545-c0faec985001",                                |
    |                          |                     "resourceHandle": {                                                          |
    |                          |                         "vimConnectionId": "c3369b54-e376-4423-bb61-afd255900fea",               |
    |                          |                         "resourceId": "2cfdbf95-a8b1-45da-bb18-34390bb08f46",                    |
    |                          |                         "vimLevelResourceType": "OS::Neutron::Port"                              |
    |                          |                     },                                                                           |
    |                          |                     "cpInstanceId": "63124ada-576a-44d4-a9c8-eec5f53fc776"                       |
    |                          |                 }                                                                                |
    |                          |             ]                                                                                    |
    |                          |         },                                                                                       |
    |                          |         {                                                                                        |
    |                          |             "id": "7bbe2404-9532-4eea-8872-d585aa9ceb49",                                        |
    |                          |             "vnfVirtualLinkDescId": "dd462031-64d6-4fed-be90-b9c366223a12",                      |
    |                          |             "networkResource": {                                                                 |
    |                          |                 "vimConnectionId": null,                                                         |
    |                          |                 "resourceId": "1642ac54-642c-407c-9c7d-e94c55ba5d33",                            |
    |                          |                 "vimLevelResourceType": "OS::Neutron::Net"                                       |
    |                          |             },                                                                                   |
    |                          |             "vnfLinkPorts": [                                                                    |
    |                          |                 {                                                                                |
    |                          |                     "id": "7db09403-cc2c-42c9-9661-438b9345a549",                                |
    |                          |                     "resourceHandle": {                                                          |
    |                          |                         "vimConnectionId": "c3369b54-e376-4423-bb61-afd255900fea",               |
    |                          |                         "resourceId": "9c5211ee-e008-47c6-a984-a00291f01624",                    |
    |                          |                         "vimLevelResourceType": "OS::Neutron::Port"                              |
    |                          |                     },                                                                           |
    |                          |                     "cpInstanceId": "ec72958c-16ff-4947-94c8-e5e32c3c453b"                       |
    |                          |                 }                                                                                |
    |                          |             ]                                                                                    |
    |                          |         }                                                                                        |
    |                          |     ],                                                                                           |
    |                          |     "vnfcInfo": [                                                                                |
    |                          |         {                                                                                        |
    |                          |             "id": "ef18f7d2-75ed-4f1c-ba4f-47f3d8d8af87",                                        |
    |                          |             "vduId": "externalLB",                                                               |
    |                          |             "vnfcState": "STARTED"                                                               |
    |                          |         },                                                                                       |
    |                          |         {                                                                                        |
    |                          |             "id": "c4388ce1-31ec-4b07-a263-7fccba839a68",                                        |
    |                          |             "vduId": "masterNode",                                                               |
    |                          |             "vnfcState": "STARTED"                                                               |
    |                          |         },                                                                                       |
    |                          |         {                                                                                        |
    |                          |             "id": "b829f679-861c-4c86-8f21-384dee974b12",                                        |
    |                          |             "vduId": "workerNode",                                                               |
    |                          |             "vnfcState": "STARTED"                                                               |
    |                          |         },                                                                                       |
    |                          |         {                                                                                        |
    |                          |             "id": "18f6eed0-5fd4-4983-a3f4-e05f41ba2c56",                                        |
    |                          |             "vduId": "workerNode",                                                               |
    |                          |             "vnfcState": "STARTED"                                                               |
    |                          |         }                                                                                        |
    |                          |     ],                                                                                           |
    |                          |     "additionalParams": {                                                                        |
    |                          |         "lcm-operation-user-data": "./UserData/lcm_user_data.py",                                |
    |                          |         "lcm-operation-user-data-class": "SampleUserData",                                       |
    |                          |         "k8sClusterInstallationParam": {                                                         |
    |                          |             "proxy": {                                                                           |
    |                          |                 "httpProxy": "http://voltserver:7926612078@10.85.45.88:8080",                    |
    |                          |                 "httpsProxy": "http://voltserver:7926612078@10.85.45.88:8080"                    |
    |                          |             },                                                                                   |
    |                          |             "ansible": {                                                                         |
    |                          |                 "password": "ubuntu",                                                            |
    |                          |                 "username": "ubuntu",                                                            |
    |                          |                 "ipAddress": "10.10.0.50",                                                       |
    |                          |                 "kubesprayRootPath": "/home/ubuntu/kubespray-2.16.0",                            |
    |                          |                 "transferringInventoryPath": "/home/ubuntu/kubespray-2.16.0/inventory/mycluster" |
    |                          |             },                                                                                   |
    |                          |             "masterNode": {                                                                      |
    |                          |                 "password": "ubuntu",                                                            |
    |                          |                 "podCidr": "192.168.0.0/16",                                                     |
    |                          |                 "username": "ubuntu",                                                            |
    |                          |                 "aspectId": "master_instance",                                                   |
    |                          |                 "nicCpName": "masterNode_CP1",                                                   |
    |                          |                 "sshCpName": "masterNode_FloatingIP",                                            |
    |                          |                 "clusterCidr": "10.199.187.0/24"                                                 |
    |                          |             },                                                                                   |
    |                          |             "workerNode": {                                                                      |
    |                          |                 "password": "ubuntu",                                                            |
    |                          |                 "username": "ubuntu",                                                            |
    |                          |                 "aspectId": "worker_instance",                                                   |
    |                          |                 "nicCpName": "workerNode_CP2",                                                   |
    |                          |                 "sshCpName": "workerNode_FloatingIP"                                             |
    |                          |             },                                                                                   |
    |                          |             "externalLbParam": {                                                                 |
    |                          |                 "scriptPath": "Scripts/install_external_lb.sh",                                  |
    |                          |                 "sshCpName": "externalLB_FloatingIP",                                            |
    |                          |                 "sshPassword": "ubuntu",                                                         |
    |                          |                 "sshUsername": "ubuntu"                                                          |
    |                          |             }                                                                                    |
    |                          |         }                                                                                        |
    |                          |     }                                                                                            |
    |                          | }                                                                                                |
    | Instantiation State      | INSTANTIATED                                                                                     |
    | Links                    | {                                                                                                |
    |                          |     "self": {                                                                                    |
    |                          |         "href": "/vnflcm/v1/vnf_instances/4cdc110f-b21e-4b79-b3f5-252ee5937a36"                  |
    |                          |     },                                                                                           |
    |                          |     "terminate": {                                                                               |
    |                          |         "href": "/vnflcm/v1/vnf_instances/4cdc110f-b21e-4b79-b3f5-252ee5937a36/terminate"        |
    |                          |     },                                                                                           |
    |                          |     "heal": {                                                                                    |
    |                          |         "href": "/vnflcm/v1/vnf_instances/4cdc110f-b21e-4b79-b3f5-252ee5937a36/heal"             |
    |                          |     },                                                                                           |
    |                          |     "changeExtConn": {                                                                           |
    |                          |         "href": "/vnflcm/v1/vnf_instances/4cdc110f-b21e-4b79-b3f5-252ee5937a36/change_ext_conn"  |
    |                          |     }                                                                                            |
    |                          | }                                                                                                |
    | VIM Connection Info      | [                                                                                                |
    |                          |     {                                                                                            |
    |                          |         "id": "daa80cf2-9b73-4806-8176-56cd6fab8cea",                                            |
    |                          |         "vimId": "c3369b54-e376-4423-bb61-afd255900fea",                                         |
    |                          |         "vimType": "openstack",                                                                  |
    |                          |         "interfaceInfo": {},                                                                     |
    |                          |         "accessInfo": {}                                                                         |
    |                          |     },                                                                                           |
    |                          |     {                                                                                            |
    |                          |         "id": "b41d21ae-fd65-4c4e-8a8e-2faa73dd1805",                                            |
    |                          |         "vimId": "9b95449d-cac9-4e23-8e35-749c917ed181",                                         |
    |                          |         "vimType": "kubernetes",                                                                 |
    |                          |         "interfaceInfo": null,                                                                   |
    |                          |         "accessInfo": {                                                                          |
    |                          |             "authUrl": "https://192.168.10.182:8383"                                             |
    |                          |         }                                                                                        |
    |                          |     }                                                                                            |
    |                          | ]                                                                                                |
    | VNF Instance Description | None                                                                                             |
    | VNF Instance Name        | vnf-4cdc110f-b21e-4b79-b3f5-252ee5937a36                                                         |
    | VNF Product Name         | Sample VNF                                                                                       |
    | VNF Provider             | Company                                                                                          |
    | VNF Software Version     | 1.0                                                                                              |
    | VNFD ID                  | b1db0ce7-ebca-2fb7-95ed-4840d70a1163                                                             |
    | VNFD Version             | 1.0                                                                                              |
    | vnfPkgId                 |                                                                                                  |
    +--------------------------+--------------------------------------------------------------------------------------------------+

Scale Kubernetes Worker Nodes
-----------------------------

You can refer to `Scale Kubernetes Worker Nodes`_ in
`How to use Mgmt Driver for deploying Kubernetes Cluster` for scale
operation.

1. Create the Parameter File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The following is scale parameter to "POST /vnf_instances/{id}/scale" as
``ScaleVnfRequest`` data type in ETSI `NFV-SOL003 v2.6.1`_:

.. code-block::

    +------------------+---------------------------------------------------------+
    | Attribute name   | Parameter description                                   |
    +------------------+---------------------------------------------------------+
    | type             | User specify scaling operation type:                    |
    |                  | "SCALE_IN" or "SCALE_OUT"                               |
    +------------------+---------------------------------------------------------+
    | aspectId         | User specify target aspectId, aspectId is defined in    |
    |                  | above VNFD and user can know by                         |
    |                  | ``InstantiatedVnfInfo.ScaleStatus`` that contained in   |
    |                  | the response of "GET /vnf_instances/{id}"               |
    +------------------+---------------------------------------------------------+
    | numberOfSteps    | Number of scaling steps                                 |
    +------------------+---------------------------------------------------------+
    | additionalParams | If your want to change info of worker node, Kubespray   |
    |                  | Server, or Load Balancer, you can set the parameters in |
    |                  | additionalParams. The format is the same as the one in   |
    |                  | `simple_kubernetes_param_file.json`.                    |
    +------------------+---------------------------------------------------------+

.. note::
    If you define Kubernetes info of additionalParams in `ScaleVnfRequest`,
    You need to define all the parameters in the corresponding dict. The three
    dicts are 'worker_node', 'ansible' and 'external_lb_param'. Even if you
    only want to change one of the values such as password, you also need to
    set values for all keys.

Following are four samples of scaling request body:

SCALE_OUT_sample (no additionalParams)

.. code-block:: console

    {
        "type": "SCALE_OUT",
        "aspectId": "worker_instance",
        "numberOfSteps": "1"
    }

SCALE_OUT_sample (with additionalParams)

.. code-block:: console

    {
        "type": "SCALE_OUT",
        "aspectId": "worker_instance",
        "numberOfSteps": "1"
        "additionalParams": {
            "k8s_cluster_installation_param": {
                "worker_node": {
                    "aspect_id": "worker_instance",
                    "ssh_cp_name": "workerNode_FloatingIP",
                    "nic_cp_name": "workerNode_CP2",
                    "username": "ubuntu",
                    "password": "workernode1"
                    },
                "ansible": {
                    "ip_address": "10.10.0.23",
                    "username": "ansible",
                    "password": "ansible",
                    "kubespray_root_path": "/home/ubuntu/kubespray-2.16.0",
                    "transferring_inventory_path":
                    "/home/ubuntu/kubespray-2.16.0/inventory/mycluster"
                    },
                "external_lb_param": {
                    "ssh_cp_name": "externalLB_FloatingIP",
                    "ssh_username": "external_lb_user",
                    "ssh_password": "externallb",
                    "script_path": "Scripts/install_external_lb.sh"
                }
            }
        }
    }

SCALE_IN_sample (no additionalParams)

.. code-block:: console

    {
        "type": "SCALE_IN",
        "aspectId": "worker_instance",
        "numberOfSteps": "1"
    }

SCALE_IN_sample (with additionalParams)

.. code-block:: console

    {
        "type": "SCALE_IN",
        "aspectId": "worker_instance",
        "numberOfSteps": "1"
        "additionalParams": {
            "k8s_cluster_installation_param": {
                "worker_node": {
                    "aspect_id": "worker_instance",
                    "ssh_cp_name": "workerNode_FloatingIP",
                    "nic_cp_name": "workerNode_CP2",
                    "username": "ubuntu",
                    "password": "workernode1"
                    },
                "ansible": {
                    "ip_address": "10.10.0.23",
                    "username": "ansible",
                    "password": "ansible",
                    "kubespray_root_path": "/home/ubuntu/kubespray-2.16.0",
                    "transferring_inventory_path":
                    "/home/ubuntu/kubespray-2.16.0/inventory/mycluster"
                    },
                "external_lb_param": {
                    "ssh_cp_name": "externalLB_FloatingIP",
                    "ssh_username": "external_lb_user",
                    "ssh_password": "externallb",
                    "script_path": "Scripts/install_external_lb.sh"
                }
            }
        }
    }

.. note::
    Scale operations for worker node are supported in this user guide,
    but scale operations for master node are not supported because
    master node is assumed to be a single node configuration.

2. Execute the Scale Operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before you execute `scale` command, you must ensure that your VNF instance
is already instantiated.
The VNF Package should be uploaded in ``Create and Upload VNF Package``
and the Kubernetes cluster should be deployed with the process in
``Deploy Kubernetes Cluster``.

When executing the scale operation of worker nodes, the following Heat API
is called from Tacker.

* stack resource signal
* stack update

The steps to confirm whether scaling is successful are shown below:

1. Execute Heat CLI command and check the number of resource list in
'worker_instance' of the stack
before and after scaling.

2. Login to Load Balancer and check the number of
worker nodes before and after scaling.

To confirm the number of worker nodes after scaling, you can find the
increased or decreased number of stack resource with Heat CLI. Also
the number of registered worker nodes in the Kubernetes cluster
should be updated.
See `Heat CLI reference`_ for details on Heat CLI commands.

Stack information before scaling:

.. code-block:: console

    $ openstack stack resource list vnflcm_4cdc110f-b21e-4b79-b3f5-252ee5937a36 -n 2 \
        --filter type=base_hot_nested_worker.yaml -c resource_name -c physical_resource_id \
        -c resource_type -c resource_status
    +---------------+--------------------------------------+-----------------------------+-----------------+
    | resource_name | physical_resource_id                 | resource_type               | resource_status |
    +---------------+--------------------------------------+-----------------------------+-----------------+
    | hq3esjpgdtp6  | d3405e32-f049-45e5-8dd1-71791b369235 | base_hot_nested_worker.yaml | CREATE_COMPLETE |
    | k8bhx9mta1vu  | a6994377-e488-aeca-1083-9b4c538b2b6d | base_hot_nested_worker.yaml | CREATE_COMPLETE |
    +---------------+--------------------------------------+-----------------------------+-----------------+

worker node in Kubernetes cluster before scaling:

.. code-block:: console

    $ ssh ubuntu@192.168.10.182
    $ kubectl get nodes
    NAME        STATUS   ROLES                  AGE   VERSION
    master228   Ready    control-plane,master   22m   v1.20.7
    worker55    Ready    <none>                 19m   v1.20.7
    worker75    Ready    <none>                 19m   v1.20.7

Scaling out execution of the vnf_instance:

.. code-block:: console

  $ openstack vnflcm scale 4cdc110f-b21e-4b79-b3f5-252ee5937a36 --type "SCALE_OUT" --aspect-id worker_instance --number-of-steps 1
    Scale request for VNF Instance 4cdc110f-b21e-4b79-b3f5-252ee5937a36 has been accepted.

Stack information after scaling out:

.. code-block:: console

    $ openstack stack resource list vnflcm_4cdc110f-b21e-4b79-b3f5-252ee5937a36 -n 2 \
        --filter type=base_hot_nested_worker.yaml -c resource_name -c physical_resource_id \
        -c resource_type -c resource_status
    +---------------+--------------------------------------+-----------------------------+-----------------+
    | resource_name | physical_resource_id                 | resource_type               | resource_status |
    +---------------+--------------------------------------+-----------------------------+-----------------+
    | hq3esjpgdtp6  | d3405e32-f049-45e5-8dd1-71791b369235 | base_hot_nested_worker.yaml | UPDATE_COMPLETE |
    | k8bhx9mta1vu  | 56c9ec6f-5e52-44db-9d0d-57e3484e763f | base_hot_nested_worker.yaml | UPDATE_COMPLETE |
    | ls8ecxdtkg4m  | a6994377-e488-aeca-1083-9b4c538b2b6d | base_hot_nested_worker.yaml | CREATE_COMPLETE |
    +---------------+--------------------------------------+-----------------------------+-----------------+

worker node in Kubernetes cluster after scaling out:

.. code-block:: console

    $ ssh ubuntu@192.168.10.182
    $ kubectl get nodes
    NAME        STATUS   ROLES                  AGE     VERSION
    master228   Ready    control-plane,master   32m     v1.20.7
    worker55    Ready    <none>                 29m     v1.20.7
    worker75    Ready    <none>                 29m     v1.20.7
    worker43    Ready    <none>                 5m48s   v1.20.7

Scaling in execution of the vnf_instance:

.. code-block:: console

    $ openstack vnflcm scale 4cdc110f-b21e-4b79-b3f5-252ee5937a36 --type "SCALE_IN" --aspect-id worker_instance --number-of-steps 1
    Scale request for VNF Instance 4cdc110f-b21e-4b79-b3f5-252ee5937a36 has been accepted.

.. note::
    This example shows the output of "SCALE_IN" after its "SCALE_OUT" operation.

Stack information after scaling in:

.. code-block:: console

    $ openstack stack resource list vnflcm_4cdc110f-b21e-4b79-b3f5-252ee5937a36 -n 2 \
        --filter type=base_hot_nested_worker.yaml -c resource_name -c physical_resource_id \
        -c resource_type -c resource_status
    +---------------+--------------------------------------+-----------------------------+-----------------+
    | resource_name | physical_resource_id                 | resource_type               | resource_status |
    +---------------+--------------------------------------+-----------------------------+-----------------+
    | k8bhx9mta1vu  | 56c9ec6f-5e52-44db-9d0d-57e3484e763f | base_hot_nested_worker.yaml | UPDATE_COMPLETE |
    | ls8ecxdtkg4m  | a6994377-e488-aeca-1083-9b4c538b2b6d | base_hot_nested_worker.yaml | UPDATE_COMPLETE |
    +---------------+--------------------------------------+-----------------------------+-----------------+

worker node in Kubernetes cluster after scaling in:

.. code-block:: console

    $ ssh ubuntu@192.168.10.182
    $ kubectl get nodes
    NAME        STATUS   ROLES                  AGE   VERSION
    master228   Ready    control-plane,master   40m   v1.20.7
    worker75    Ready    <none>                 37m   v1.20.7
    worker43    Ready    <none>                 13m   v1.20.7

Heal Kubernetes Worker Nodes
----------------------------

You can refer to `Heal Kubernetes Master/Worker Nodes`_ in
`How to use Mgmt Driver for deploying Kubernetes Cluster` for heal
operation.

.. note::
    This user guide just supports `heal worker nodes` because the
    Kubernetes cluster deployed by Kubespray only has one master node.

1. Create the Parameter File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following is heal parameter to "POST /vnf_instances/{id}/heal" as
``HealVnfRequest`` data type. It is not the same in SOL002 and SOL003.

In `NFV-SOL002 v2.6.1`_:

.. code-block::

    +------------------+---------------------------------------------------------+
    | Attribute name   | Parameter description                                   |
    +------------------+---------------------------------------------------------+
    | vnfcInstanceId   | User specify heal target, user can know "vnfcInstanceId"|
    |                  | by ``InstantiatedVnfInfo.vnfcResourceInfo`` that        |
    |                  | contained in the response of "GET /vnf_instances/{id}". |
    +------------------+---------------------------------------------------------+
    | cause            | Not needed                                              |
    +------------------+---------------------------------------------------------+
    | additionalParams | If your want to change info of worker node, Kubespray   |
    |                  | Server, or Load Balancer, you can set the parameters in |
    |                  | additionalParams. So format is the same as the one in   |
    |                  | `simple_kubernetes_param_file.json`.                    |
    +------------------+---------------------------------------------------------+

In `NFV-SOL003 v2.6.1`_:

.. code-block::

    +------------------+---------------------------------------------------------+
    | Attribute name   | Parameter description                                   |
    +------------------+---------------------------------------------------------+
    | cause            | Not needed                                              |
    +------------------+---------------------------------------------------------+
    | additionalParams | If your want to change info of worker node, Kubespray   |
    |                  | Server, or Load Balancer, you can set the parameters in |
    |                  | additionalParams. So format is the same as the one in   |
    |                  | `simple_kubernetes_param_file.json`.                    |
    +------------------+---------------------------------------------------------+


``cause`` and ``additionalParams``
are supported for both of SOL002 and SOL003.

If the vnfcInstanceId parameter is null, this means that healing operation is
required for the entire Kubernetes cluster, which is the case in SOL003.

Following is a sample of healing request body for SOL002:

HEAL_sample (no additionalParams)

.. code-block::

    {
        "vnfcInstanceId": "f8829938-d57e-4b96-b383-cf3783651822"
    }

HEAL_sample (with additionalParams)

.. code-block::

    {
        "vnfcInstanceId": "f8829938-d57e-4b96-b383-cf3783651822",
        "additionalParams": {
            "k8s_cluster_installation_param": {
                "worker_node": {
                    "aspect_id": "worker_instance",
                    "ssh_cp_name": "workerNode_FloatingIP",
                    "nic_cp_name": "workerNode_CP2",
                    "username": "ubuntu",
                    "password": "ubuntu"
                    },
                "ansible": {
                    "ip_address": "10.10.0.50",
                    "username": "ubuntu",
                    "password": "ubuntu",
                    "kubespray_root_path": "/home/ubuntu/kubespray-2.16.0",
                    "transferring_inventory_path":
                    "/home/ubuntu/kubespray-2.16.0/inventory/mycluster"
                    },
                "external_lb_param": {
                    "ssh_cp_name": "externalLB_FloatingIP",
                    "ssh_username": "ubuntu",
                    "ssh_password": "ubuntu",
                    "script_path": "Scripts/install_external_lb.sh"
                }
            }
        }
    }

.. note::
    In chapter `Deploy Kubernetes cluster`, the result of VNF instance
    instantiated has shown in CLI command `openstack vnflcm show VNF INSTANCE ID`.

    You can get the vnfcInstanceId from ``Instantiated Vnf Info`` in above result.
    The ``vnfcResourceInfo.id`` is vnfcInstanceId.

    The ``physical_resource_id`` mentioned below is
    the same as ``vnfcResourceInfo.computeResource.resourceId``.

2. Execute the Heal Operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Heal a Worker Node
~~~~~~~~~~~~~~~~~~~~~

When healing specified with VNFC instances,
Heat APIs are called from Tacker.

* stack resource mark unhealthy
* stack update

The steps to confirm whether healing is successful are shown below:

1. Execute Heat CLI command and check physical_resource_id and
resource_status of worker node before and after healing.

2. Login to Load Balancer and check the age
of worker node before and after healing.

To confirm that healing the worker node is successful, you can find
the physical_resource_id of this resource of
'worker_instance resource list' has changed with Heat CLI. Also
the age of worker node healed should be updated in Kubernetes cluster.

.. note::
    Note that 'vnfc-instance-id' managed by Tacker and
    'physical-resource-id' managed by Heat are different.

worker node information before healing:

.. code-block:: console

    $ openstack stack resource list vnflcm_4cdc110f-b21e-4b79-b3f5-252ee5937a36 -n 2 \
        --filter type=OS::Nova::Server -c resource_name -c physical_resource_id -c \
        resource_type -c resource_status
    +---------------+--------------------------------------+------------------+-----------------+
    | resource_name | physical_resource_id                 | resource_type    | resource_status |
    +---------------+--------------------------------------+------------------+-----------------+
    | workerNode    | b8cc0d5b-600a-47eb-a67f-45d4d6051c44 | OS::Nova::Server | CREATE_COMPLETE |
    | workerNode    | 89b58460-df0a-41c8-82ce-8386491d65d8 | OS::Nova::Server | CREATE_COMPLETE |
    | masterNode    | 5877e1ba-dfe0-4a9e-9ddf-08a6590942c4 | OS::Nova::Server | CREATE_COMPLETE |
    +---------------+--------------------------------------+------------------+-----------------+

worker node in Kubernetes cluster before healing:

.. code-block:: console

    $ ssh ubuntu@192.168.10.182
    $ kubectl get node
    NAME        STATUS   ROLES                  AGE   VERSION
    master228   Ready    control-plane,master   82m   v1.20.7
    worker55    Ready    <none>                 79m   v1.20.7
    worker75    Ready    <none>                 79m   v1.20.7

We heal the worker node with ``physical_resource_id``
``b8cc0d5b-600a-47eb-a67f-45d4d6051c44``, its ``vnfc_instance_id``
is ``f8829938-d57e-4b96-b383-cf3783651822``.

Healing worker node execution of the vnf_instance:

.. code-block:: console

    $ openstack vnflcm heal 4cdc110f-b21e-4b79-b3f5-252ee5937a36 --vnfc-instance f8829938-d57e-4b96-b383-cf3783651822
    Heal request for VNF Instance 4cdc110f-b21e-4b79-b3f5-252ee5937a36 has been accepted.

worker node information after healing:

.. code-block:: console

    $ openstack stack resource list vnflcm_4cdc110f-b21e-4b79-b3f5-252ee5937a36 -n 2 \
        --filter type=OS::Nova::Server -c resource_name -c physical_resource_id -c \
        resource_type -c resource_status
    +---------------+--------------------------------------+------------------+-----------------+
    | resource_name | physical_resource_id                 | resource_type    | resource_status |
    +---------------+--------------------------------------+------------------+-----------------+
    | workerNode    | e046adef-937b-4b39-b96e-0c56cedb318c | OS::Nova::Server | CREATE_COMPLETE |
    | workerNode    | 89b58460-df0a-41c8-82ce-8386491d65d8 | OS::Nova::Server | CREATE_COMPLETE |
    | masterNode    | 5877e1ba-dfe0-4a9e-9ddf-08a6590942c4 | OS::Nova::Server | CREATE_COMPLETE |
    +---------------+--------------------------------------+------------------+-----------------+

worker node in Kubernetes cluster after healing:

.. code-block:: console

    $ ssh ubuntu@192.168.10.182
    $ kubectl get node
    NAME        STATUS   ROLES                  AGE      VERSION
    master228   Ready    control-plane,master   102m     v1.20.7
    worker55    Ready    <none>                 79m      v1.20.7
    worker75    Ready    <none>                 5m48s    v1.20.7

2. Heal the Entire Kubernetes Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When healing of the entire VNF, the following APIs are executed
from Tacker to Heat.

* stack delete
* stack create

1. Execute Heat CLI command and check 'ID' and 'Stack Status' of the stack
before and after healing.

2. All the information of Kubernetes cluster will be
changed.

This is to confirm that stack 'ID' has changed
before and after healing.

Stack information before healing:

.. code-block:: console

    $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'
    +--------------------------------------+---------------------------------------------+-----------------+
    | ID                                   | Stack Name                                  | Stack Status    |
    +--------------------------------------+---------------------------------------------+-----------------+
    | 62477704-94a9-4ab4-26f8-685c146a9129 | vnflcm_4cdc110f-b21e-4b79-b3f5-252ee5937a36 | CREATE_COMPLETE |
    +--------------------------------------+---------------------------------------------+-----------------+

Kubernetes cluster information before healing:

.. code-block:: console

    $ ssh ubuntu@192.168.10.182
    $ kubectl get node
    NAME        STATUS   ROLES                  AGE      VERSION
    master228   Ready    control-plane,master   102m     v1.20.7
    worker55    Ready    <none>                 79m      v1.20.7
    worker75    Ready    <none>                 5m48s    v1.20.7

Healing execution of the entire VNF:

.. code-block:: console

    $ openstack vnflcm heal 4cdc110f-b21e-4b79-b3f5-252ee5937a36
    Heal request for VNF Instance 4cdc110f-b21e-4b79-b3f5-252ee5937a36 has been accepted.

Stack information after healing:

.. code-block:: console

    $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'
    +--------------------------------------+---------------------------------------------+-----------------+
    | ID                                   | Stack Name                                  | Stack Status    |
    +--------------------------------------+---------------------------------------------+-----------------+
    | f0e87a99-0b90-aad8-4af0-151c1303ed22 | vnflcm_4cdc110f-b21e-4b79-b3f5-252ee5937a36 | CREATE_COMPLETE |
    +--------------------------------------+---------------------------------------------+-----------------+

Kubernetes cluster information after healing:

.. code-block:: console

    $ ssh ubuntu@192.168.10.232
    $ kubectl get node
    NAME        STATUS   ROLES                  AGE     VERSION
    master26    Ready    control-plane,master   23m     v1.20.7
    worker78    Ready    <none>                 20m     v1.20.7
    worker119   Ready    <none>                 20m     v1.20.7

Configuration of Load Balancer
------------------------------
When you instantiate CNF with this type of Kubernetes vim (which is deployed
by Kubespray), if deployed resources contain services with 'NodePort' type,
you should set the NodePort to Load Balancer. We provide a sample VNF package
and Mgmt Driver for CNF to configure the Load Balancer.

The Mgmt Driver only supports instantiation and heal entire operation because
only the two operations can create service resource in Kubernetes cluster.

.. note::
    The load balancer mentioned in this user guide is not a service whose
    type is ExternalLB in Kubernetes, but constitutes the Load Balancer server
    in the diagram of `Simple : Single Master Node`_.

1. Structure of VNF Package for CNF
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The usage of VNF Package for CNF is the same as the one in chapter
`Create and Upload VNF Package`.

The sample structure of this Package is shown below.

.. note::

    You can also find them in the
    `samples/mgmt_driver/kubernetes/kubespray/cnf_nodeport_setting/cnf_nodeport_setting_vnf_package`_
    directory of the tacker.

The directory structure:

* **TOSCA-Metadata/TOSCA.meta**
* **Definitions/**
* **Scripts/**
* **Files/**

.. code-block:: console

  !----TOSCA-Metadata
          !---- TOSCA.meta
  !----Definitions
          !---- etsi_nfv_sol001_common_types.yaml
          !---- etsi_nfv_sol001_vnfd_types.yaml
          !---- helloworld3_df_simple.yaml
          !---- helloworld3_top.vnfd.yaml
          !---- helloworld3_types.yaml
  !----Scripts
          !---- configure_lb.sh
          !---- cnf_nodeport_mgmt.py
  !----Files
          !---- kubernetes
                   !---- deployment.yaml
                   !---- service_with_nodeport.yaml
                   !---- service_without_nodeport.yaml

2. Deploy CNF
^^^^^^^^^^^^^
1. Create the Parameter File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
You can refer to `Set the value to the request parameter file`_
in `ETSI NFV-SOL CNF (Containerized VNF) Deployment` for the
parameters introduction of CNF.

Here is a sample request body when deploying CNF.

simple_cnf_param_file.json

.. code-block:: console

    {
        "flavourId": "simple",
        "vimConnectionInfo": [{
            "id": "f5d17ce5-1e48-4971-8946-5c0126c0425e",
            "vimId": "9b95449d-cac9-4e23-8e35-749c917ed181",
            "vimType": "kubernetes"
        }],
        "additionalParams": {
            "lcm-kubernetes-def-files": ["Files/kubernetes/deployment.yaml", "Files/kubernetes/service_with_nodeport.yaml", "Files/kubernetes/service_without_nodeport.yaml"],
            "lcm-kubernetes-external-lb": {
                "script_path": "Scripts/configure_lb.sh",
                "external_lb_param": {
                    "ssh_ip": "192.168.10.182",
                    "ssh_username": "ubuntu",
                    "ssh_password": "ubuntu"
                }
            }
        }
    }

2. Execute the Instantiation Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute the following CLI command to instantiate CNF.

Create VNF with VNFD ID:

.. code-block:: console

    $ openstack vnflcm create babb0ce7-ebca-4fa7-95ed-4840d70a1177
    +--------------------------+---------------------------------------------------------------------------------------------+
    | Field                    | Value                                                                                       |
    +--------------------------+---------------------------------------------------------------------------------------------+
    | ID                       | 342a083d-caec-4b44-8881-733fa7cd1754                                                        |
    | Instantiation State      | NOT_INSTANTIATED                                                                            |
    | Links                    | {                                                                                           |
    |                          |     "self": {                                                                               |
    |                          |         "href": "/vnflcm/v1/vnf_instances/342a083d-caec-4b44-8881-733fa7cd1754"             |
    |                          |     },                                                                                      |
    |                          |     "instantiate": {                                                                        |
    |                          |         "href": "/vnflcm/v1/vnf_instances/342a083d-caec-4b44-8881-733fa7cd1754/instantiate" |
    |                          |     }                                                                                       |
    |                          | }                                                                                           |
    | VNF Instance Description | None                                                                                        |
    | VNF Instance Name        | vnf-342a083d-caec-4b44-8881-733fa7cd1754                                                    |
    | VNF Product Name         | Sample VNF                                                                                  |
    | VNF Provider             | Company                                                                                     |
    | VNF Software Version     | 1.0                                                                                         |
    | VNFD ID                  | babb0ce7-ebca-4fa7-95ed-4840d70a1177                                                        |
    | VNFD Version             | 1.0                                                                                         |
    | vnfPkgId                 |                                                                                             |
    +--------------------------+---------------------------------------------------------------------------------------------+

Instantiate VNF with VNF ID:

.. code-block:: console

    $ openstack vnflcm instantiate 342a083d-caec-4b44-8881-733fa7cd1754 ./simple_cnf_param_file.json
    Instantiate request for VNF Instance 342a083d-caec-4b44-8881-733fa7cd1754 has been accepted.

Check instantiation state:

.. code-block:: console

    $ openstack vnflcm show 342a083d-caec-4b44-8881-733fa7cd1754
    +--------------------------+-------------------------------------------------------------------------------------------------+
    | Field                    | Value                                                                                           |
    +--------------------------+-------------------------------------------------------------------------------------------------+
    | ID                       | 342a083d-caec-4b44-8881-733fa7cd1754                                                            |
    | Instantiated Vnf Info    | {                                                                                               |
    |                          |     "flavourId": "simple",                                                                      |
    |                          |     "vnfState": "STARTED",                                                                      |
    |                          |     "scaleStatus": [                                                                            |
    |                          |         {                                                                                       |
    |                          |             "aspectId": "vdu1_aspect",                                                          |
    |                          |             "scaleLevel": 0                                                                     |
    |                          |         }                                                                                       |
    |                          |     ],                                                                                          |
    |                          |     "extCpInfo": [],                                                                            |
    |                          |     "vnfcResourceInfo": [                                                                       |
    |                          |         {                                                                                       |
    |                          |             "id": "29db4f9d-6e50-4d5a-bd84-9e0b747e09d9",                                       |
    |                          |             "vduId": "VDU1",                                                                    |
    |                          |             "computeResource": {                                                                |
    |                          |                 "vimConnectionId": null,                                                        |
    |                          |                 "resourceId": "vdu1-simple-5b84bf645f-rnw8j",                                   |
    |                          |                 "vimLevelResourceType": "Deployment"                                            |
    |                          |             },                                                                                  |
    |                          |             "storageResourceIds": []                                                            |
    |                          |         }                                                                                       |
    |                          |     ],                                                                                          |
    |                          |     "additionalParams": {                                                                       |
    |                          |         "lcm-kubernetes-def-files": [                                                           |
    |                          |             "Files/kubernetes/deployment.yaml",                                                 |
    |                          |             "Files/kubernetes/service_with_nodeport.yaml",                                      |
    |                          |             "Files/kubernetes/service_without_nodeport.yaml"                                    |
    |                          |         ],                                                                                      |
    |                          |         "lcm-kubernetes-external-lb": {                                                         |
    |                          |             "scriptPath": "Scripts/configure_lb.sh",                                            |
    |                          |             "externalLbParam": {                                                                |
    |                          |                 "sshIp": "192.168.10.182",                                                      |
    |                          |                 "sshPassword": "ubuntu",                                                        |
    |                          |                 "sshUsername": "ubuntu"                                                         |
    |                          |             }                                                                                   |
    |                          |         }                                                                                       |
    |                          |     }                                                                                           |
    |                          | }                                                                                               |
    | Instantiation State      | INSTANTIATED                                                                                    |
    | Links                    | {                                                                                               |
    |                          |     "self": {                                                                                   |
    |                          |         "href": "/vnflcm/v1/vnf_instances/342a083d-caec-4b44-8881-733fa7cd1754"                 |
    |                          |     },                                                                                          |
    |                          |     "terminate": {                                                                              |
    |                          |         "href": "/vnflcm/v1/vnf_instances/342a083d-caec-4b44-8881-733fa7cd1754/terminate"       |
    |                          |     },                                                                                          |
    |                          |     "heal": {                                                                                   |
    |                          |         "href": "/vnflcm/v1/vnf_instances/342a083d-caec-4b44-8881-733fa7cd1754/heal"            |
    |                          |     },                                                                                          |
    |                          |     "changeExtConn": {                                                                          |
    |                          |         "href": "/vnflcm/v1/vnf_instances/342a083d-caec-4b44-8881-733fa7cd1754/change_ext_conn" |
    |                          |     }                                                                                           |
    |                          | }                                                                                               |
    | VIM Connection Info      | [                                                                                               |
    |                          |     {                                                                                           |
    |                          |         "id": "f5d17ce5-1e48-4971-8946-5c0126c0425e",                                           |
    |                          |         "vimId": "9b95449d-cac9-4e23-8e35-749c917ed181",                                        |
    |                          |         "vimType": "kubernetes",                                                                |
    |                          |         "interfaceInfo": {},                                                                    |
    |                          |         "accessInfo": {}                                                                        |
    |                          |     }                                                                                           |
    |                          | ]                                                                                               |
    | VNF Instance Description | None                                                                                            |
    | VNF Instance Name        | vnf-342a083d-caec-4b44-8881-733fa7cd1754                                                        |
    | VNF Product Name         | Sample VNF                                                                                      |
    | VNF Provider             | Company                                                                                         |
    | VNF Software Version     | 1.0                                                                                             |
    | VNFD ID                  | babb0ce7-ebca-4fa7-95ed-4840d70a1177                                                            |
    | VNFD Version             | 1.0                                                                                             |
    | vnfPkgId                 |                                                                                                 |
    +--------------------------+-------------------------------------------------------------------------------------------------+

To confirm the NodePort has set to Load Balancer, you should login
Load Balancer via ssh. The Load Balancer will monitor the NodePort
created by the service. You can execute the following command to confirm them.

.. code-block:: console

    $ ssh ubuntu@192.168.10.182
    $ kubectl get svc --all-namespaces
    NAMESPACE     NAME            TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)                       AGE
    default       kubernetes      ClusterIP   10.199.187.1     <none>        443/TCP                       2d18h
    default       nginx-service   NodePort    10.199.187.127   <none>        80:30422/TCP,8080:32019/TCP   7m42s
    kube-system   coredns         ClusterIP   10.199.187.3     <none>        53/UDP,53/TCP,9153/TCP        2d18h
    kube-system   nginx-service   NodePort    10.199.187.43    <none>        80:30058/TCP                  7m42s

    $ ss -lnt
    State                         Recv-Q                        Send-Q                                               Local Address:Port                                                  Peer Address:Port                        Process
    LISTEN                        0                             490                                                        0.0.0.0:30058                                                      0.0.0.0:*
    LISTEN                        0                             490                                                        0.0.0.0:32019                                                      0.0.0.0:*
    LISTEN                        0                             4096                                                 127.0.0.53%lo:53                                                         0.0.0.0:*
    LISTEN                        0                             490                                                        0.0.0.0:30422                                                      0.0.0.0:*
    LISTEN                        0                             128                                                        0.0.0.0:22                                                         0.0.0.0:*
    LISTEN                        0                             490                                                        0.0.0.0:8383                                                       0.0.0.0:*
    LISTEN                        0                             128                                                           [::]:22                                                            [::]:*

You can find that the NodePorts are '30422', '32019' and '30058',
and all the NodePorts are listened on Load Balancer.

3. Heal the entire CNF
^^^^^^^^^^^^^^^^^^^^^^
When the service type is NodePort and NodePort is not specified, Kubernetes
will randomly generate a port. So when you execute the heal CNF entire command
and the resource contains a service without specified NodePort, the randomly
generated port may be changed. At this time, the Mgmt Driver for CNF will
delete the original port and reset the new port to Load Balancer.

1. Create the Parameter File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The parameter file of heal CNF entire is the same as the one chapter
`Create the Parameter File` of `Heal Kubernetes Worker Nodes`.
It also follows the rules of `NFV-SOL003 v2.6.1`_.

2. Execute the Healing Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Execute the following CLI command to heal CNF entire.

.. code-block:: console

    $ openstack vnflcm heal 342a083d-caec-4b44-8881-733fa7cd1754
    Heal request for VNF Instance 342a083d-caec-4b44-8881-733fa7cd1754 has been accepted.

To confirm the new NodePort has set to Load Balancer, you should login
Load Balancer via ssh. The Load Balancer will monitor the new NodePort
created by the service. You can execute the following command to confirm them.

.. code-block:: console

    $ ssh ubuntu@192.168.10.182
    $ kubectl get svc --all-namespaces
    NAMESPACE     NAME            TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)                       AGE
    default       kubernetes      ClusterIP   10.199.187.1     <none>        443/TCP                       2d19h
    default       nginx-service   NodePort    10.199.187.137   <none>        80:30422/TCP,8080:32019/TCP   73s
    kube-system   coredns         ClusterIP   10.199.187.3     <none>        53/UDP,53/TCP,9153/TCP        2d19h
    kube-system   nginx-service   NodePort    10.199.187.132   <none>        80:30702/TCP                  73s

    $ ss -lnt
    State                         Recv-Q                        Send-Q                                               Local Address:Port                                                  Peer Address:Port                        Process
    LISTEN                        0                             490                                                        0.0.0.0:30702                                                      0.0.0.0:*
    LISTEN                        0                             490                                                        0.0.0.0:32019                                                      0.0.0.0:*
    LISTEN                        0                             4096                                                 127.0.0.53%lo:53                                                         0.0.0.0:*
    LISTEN                        0                             490                                                        0.0.0.0:30422                                                      0.0.0.0:*
    LISTEN                        0                             128                                                        0.0.0.0:22                                                         0.0.0.0:*
    LISTEN                        0                             490                                                        0.0.0.0:8383                                                       0.0.0.0:*
    LISTEN                        0                             128                                                           [::]:22                                                            [::]:*

In this user guide, the service named 'nginx-service' in 'kube-system'
namespace does not have specified NodePort.
You can find that the exposed port number by NodePort has changed
from '30058' to '30702', and all the NodePorts are listened
on Load Balancer.

Limitations
-----------
1. This user guide provides a VNF Package in format of UserData.
   You can also use TOSCA based VNF Package in the manner of SOL001
   v2.6.1, but it does not support scaling operation.
2. Since Tacker currently only supports installing single-master Kubernetes
   cluster, you cannot heal master node.

.. _How to use Mgmt Driver for deploying Kubernetes Cluster: https://docs.openstack.org/tacker/latest/user/mgmt_driver_deploy_k8s_usage_guide.html#mgmt-driver-introduction
.. _Kubespray: https://github.com/kubernetes-sigs/kubespray
.. _Create and Upload VNF Package: https://docs.openstack.org/tacker/latest/user/mgmt_driver_deploy_k8s_usage_guide.html#create-and-upload-vnf-package
.. _Preparations: https://docs.openstack.org/tacker/latest/user/mgmt_driver_deploy_k8s_usage_guide.html#preparations
.. _Kubespray's official documentation: https://github.com/kubernetes-sigs/kubespray/#quick-start
.. _samples/mgmt_driver/kubernetes/kubespray/kubespray_vnf_package/: https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes/kubespray/kubespray_vnf_package/
.. _Create the Parameter File: https://docs.openstack.org/tacker/latest/user/mgmt_driver_deploy_k8s_usage_guide.html#create-the-parameter-file
.. _Scale Kubernetes Worker Nodes: https://docs.openstack.org/tacker/latest/user/mgmt_driver_deploy_k8s_usage_guide.html#scale-kubernetes-worker-nodes
.. _Heal Kubernetes Master/Worker Nodes: https://docs.openstack.org/tacker/latest/user/mgmt_driver_deploy_k8s_usage_guide.html#heal-kubernetes-master-worker-nodes
.. _NFV-SOL001 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/001/02.06.01_60/gs_NFV-SOL001v020601p.pdf
.. _NFV-SOL002 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/002/02.06.01_60/gs_NFV-SOL002v020601p.pdf
.. _NFV-SOL003 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/003/02.06.01_60/gs_NFV-SOL003v020601p.pdf
.. _Heat CLI reference : https://docs.openstack.org/python-openstackclient/latest/cli/plugin-commands/heat.html
.. _Set the value to the request parameter file: https://docs.openstack.org/tacker/latest/user/etsi_containerized_vnf_usage_guide.html#set-the-value-to-the-request-parameter-file
.. _samples/mgmt_driver/kubernetes/kubespray/cnf_nodeport_setting/cnf_nodeport_setting_vnf_package: https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes/kubespray/cnf_nodeport_setting/cnf_nodeport_setting_vnf_package
