=======================================================================
How to use Mgmt Driver for deploying Kubernetes Cluster with Cilium CNI
=======================================================================

This document describes how to deploy a Kubernetes cluster with Cilium CNI
using MgmtDriver.


Sample VNF Package Description
------------------------------
This document describes the procedure using the sample VNF package provided
under ``samples/mgmt_driver/kubernetes/sol_v2_kubernetes_vnf_package``.
The Mgmt Driver script in this sample VNF package creates a Kubernetes cluster
with kubeadm and uses Cilium for CNI Plugin.
There are two deployment flavors, each of which creates a Kubernetes cluster
with the following configuration.


.. note::

  This VNF package uses v2 API.


* simple: Deploy 1 MasterNode and 2 WorkerNodes. This flavor supports Scale
  and Heal for WorkerNode.
* complex： Deploy 3 MasterNodes and 2 WorkerNodes. This flavor supports Heal
  for MasterNode, Scale and Heal for WorkerNode.

Software version
----------------

* OS(VM):  Ubuntu 22.04 LTS
* kubeadm: 1.26.8
* kubelet: 1.26.8
* kubectl: 1.26.8
* containerd: 1.7.11
* runc: 1.1.10
* cilium cli: v0.15.23
* cilium: 1.14.5


Environmental Preparation
-------------------------

This section describes the environment preparation steps for creating a
Kubernetes cluster.
The environment used in this document assumes access to VMs via Floating IP.

Create OpenStack Router
^^^^^^^^^^^^^^^^^^^^^^^

In order for the VM to access the external network, a router is needed between
the public network and the internal network.
The following steps create a router between the public network and the
internal network net0.

.. code-block:: console

  $ openstack router create router-net0
  +-------------------------+--------------------------------------+
  | Field                   | Value                                |
  +-------------------------+--------------------------------------+
  | admin_state_up          | UP                                   |
  | availability_zone_hints |                                      |
  | availability_zones      |                                      |
  | created_at              | 2024-04-16T04:08:27Z                 |
  | description             |                                      |
  | enable_ndp_proxy        | None                                 |
  | external_gateway_info   | null                                 |
  | flavor_id               | None                                 |
  | id                      | e3de8025-57c0-4e7a-a472-746d0b4a89d7 |
  | name                    | router-net0                          |
  | project_id              | 5d711196514b4f11b02382403b3342a9     |
  | revision_number         | 1                                    |
  | routes                  |                                      |
  | status                  | ACTIVE                               |
  | tags                    |                                      |
  | tenant_id               | 5d711196514b4f11b02382403b3342a9     |
  | updated_at              | 2024-04-16T04:08:27Z                 |
  +-------------------------+--------------------------------------+

  $ openstack router set --external-gateway public router-net0
  $ openstack router show router-net0
  +-------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field                   | Value                                                                                                                                               |
  +-------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
  | admin_state_up          | UP                                                                                                                                                  |
  | availability_zone_hints |                                                                                                                                                     |
  | availability_zones      |                                                                                                                                                     |
  | created_at              | 2024-04-16T04:08:27Z                                                                                                                                |
  | description             |                                                                                                                                                     |
  | enable_ndp_proxy        | None                                                                                                                                                |
  | external_gateway_info   | {"network_id": "89e36da8-4652-4454-be91-fb54223c4674", "external_fixed_ips": [{"subnet_id": "063e9703-25a8-4496-a423-0d94a9637d71", "ip_address":   |
  |                         | "172.24.4.62"}, {"subnet_id": "2fd2348a-c6a3-48b8-8f9f-98f20a9229cc", "ip_address": "2001:db8::1a7"}], "enable_snat": true}                         |
  | flavor_id               | None                                                                                                                                                |
  | id                      | e3de8025-57c0-4e7a-a472-746d0b4a89d7                                                                                                                |
  | interfaces_info         | []                                                                                                                                                  |
  | name                    | router-net0                                                                                                                                         |
  | project_id              | 5d711196514b4f11b02382403b3342a9                                                                                                                    |
  | revision_number         | 3                                                                                                                                                   |
  | routes                  |                                                                                                                                                     |
  | status                  | ACTIVE                                                                                                                                              |
  | tags                    |                                                                                                                                                     |
  | tenant_id               | 5d711196514b4f11b02382403b3342a9                                                                                                                    |
  | updated_at              | 2024-04-16T04:08:39Z                                                                                                                                |
  +-------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+

  $ openstack router add subnet router-net0 subnet0
  $ openstack router show router-net0
  +-------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field                   | Value                                                                                                                                               |
  +-------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
  | admin_state_up          | UP                                                                                                                                                  |
  | availability_zone_hints |                                                                                                                                                     |
  | availability_zones      |                                                                                                                                                     |
  | created_at              | 2024-04-16T04:08:27Z                                                                                                                                |
  | description             |                                                                                                                                                     |
  | enable_ndp_proxy        | None                                                                                                                                                |
  | external_gateway_info   | {"network_id": "89e36da8-4652-4454-be91-fb54223c4674", "external_fixed_ips": [{"subnet_id": "063e9703-25a8-4496-a423-0d94a9637d71", "ip_address":   |
  |                         | "172.24.4.62"}, {"subnet_id": "2fd2348a-c6a3-48b8-8f9f-98f20a9229cc", "ip_address": "2001:db8::1a7"}], "enable_snat": true}                         |
  | flavor_id               | None                                                                                                                                                |
  | id                      | e3de8025-57c0-4e7a-a472-746d0b4a89d7                                                                                                                |
  | interfaces_info         | [{"port_id": "a1a697eb-10e7-41fe-ad70-11990e926897", "ip_address": "10.10.0.1", "subnet_id": "1c8d1f2d-5e45-427f-920e-1b49f6978985"}]               |
  | name                    | router-net0                                                                                                                                         |
  | project_id              | 5d711196514b4f11b02382403b3342a9                                                                                                                    |
  | revision_number         | 4                                                                                                                                                   |
  | routes                  |                                                                                                                                                     |
  | status                  | ACTIVE                                                                                                                                              |
  | tags                    |                                                                                                                                                     |
  | tenant_id               | 5d711196514b4f11b02382403b3342a9                                                                                                                    |
  | updated_at              | 2024-04-16T04:09:01Z                                                                                                                                |
  +-------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+


Security Group Settings
^^^^^^^^^^^^^^^^^^^^^^^

In order to create a Kubernetes cluster, a security group needs to be set up.
This document adds rules to the default group.

Get default security group ID for nfv project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

  $ auth='--os-username nfv_user --os-project-name nfv --os-password devstack  --os-auth-url http://127.0.0.1/identity --os-project-domain-name Default --os-user-domain-name Default'
  $ nfv_project_id=`openstack project list $auth | grep -w '| nfv' | awk '{print $2}'`
  $ default_id=`openstack security group list $auth | grep -w 'default' | grep $nfv_project_id | awk '{print $2}'`


Add rules to security group
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

  $ openstack security group rule create --protocol tcp --dst-port 22 $default_id $auth
  $ openstack security group rule create --protocol tcp $default_id $auth
  $ openstack security group rule create --protocol icmp $default_id $auth
  $ openstack security group rule create --protocol udp $default_id $auth
  $ openstack security group rule create --protocol tcp --dst-port 53 $default_id $auth
  $ openstack security group rule create --protocol tcp --dst-port 6443 $default_id $auth
  $ openstack security group rule create --protocol tcp --dst-port 16443 $default_id $auth
  $ openstack security group rule create --protocol tcp --dst-port 2379:2380 $default_id $auth
  $ openstack security group rule create --protocol tcp --dst-port 10250:10255 $default_id $auth
  $ openstack security group rule create --protocol tcp --dst-port 30000:32767 $default_id $auth


Download and modify Ubuntu Image
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``samples/mgmt_driver/kubernetes/sol_v2_kubernetes_vnf_package`` does
not contain VM Images. The VM Image must be downloaded and modified.
In order for the Mgmt Driver script to create the Kubernetes cluster,
the VM must be accessed via SSH password authentication.
By default, SSH password authentication is not allowed, so change the setting.
In this guide, we will use guestfish to change the configuration of the
Ubuntu Image.

Install libguestfs-tools
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

  $ sudo apt-get install libguestfs-tools


Download Ubuntu Image
~~~~~~~~~~~~~~~~~~~~~

To use the Ubuntu Image when creating the VNF package, download it to the
following path.

.. code-block:: console

  $ cd ~/tacker/samples/mgmt_driver/kubernetes/sol_v2_kubernetes_vnf_package
  $ wget https://cloud-images.ubuntu.com/releases/jammy/release/ubuntu-22.04-server-cloudimg-amd64.img


Change Ubuntu Image settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In this document, the password is set as "ubuntu". The password set here is
used as a request parameter to create a Kubernetes cluster in the MgmtDriver
script.

.. code-block:: console

  $ sudo guestfish -a ubuntu-22.04-server-cloudimg-amd64.img -i sh "sed -i 's/lock\_passwd\: True/lock\_passwd\: false/g' /etc/cloud/cloud.cfg"
  $ sudo guestfish -a ubuntu-22.04-server-cloudimg-amd64.img -i sh "sed -i '/[ ][ ][ ][ ]lock\_passwd\: false/a\    plain\_text\_passwd\: ubuntu' /etc/cloud/cloud.cfg"
  $ sudo guestfish -a ubuntu-22.04-server-cloudimg-amd64.img -i sh "sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config.d/60-cloudimg-settings.conf"


Create and register VNF Package
-------------------------------

Create and register a VNF Package.

Create VNF Package
^^^^^^^^^^^^^^^^^^

Create a VNF Package using pkggen.py under
``samples/mgmt_driver/kubernetes/sol_v2_kubernetes_vnf_package``.
Before running pkggen.py, place the Ubuntu image configured in the above
procedure in the following directory structure.


The directory structure:

.. code-block:: console

  !----sol_v2_kubernetes_vnf_package
          !---- contents
                  !---- BaseHOT
                  !---- Definitions
                  !---- Scripts
                  !---- TOSCA-Metadata
          !---- pkggen.py
          !---- ubuntu-22.04-server-cloudimg-amd64.img


Execute pkggen.py
The package will be created as sol_v2_kubernetes_vnf_package.zip.

.. code-block:: console

  $ cd ~/tacker/samples/mgmt_driver/kubernetes/sol_v2_kubernetes_vnf_package
  $ python3 pkggen.py


Register VNF Package
^^^^^^^^^^^^^^^^^^^^

Register the created VNF Package.

.. code-block:: console

  $ openstack vnf package create
  +-------------------+-------------------------------------------------------------------------------------------------+
  | Field             | Value                                                                                           |
  +-------------------+-------------------------------------------------------------------------------------------------+
  | ID                | baec2512-2c97-4ced-857a-4a7e3f0bbb93                                                            |
  | Links             | {                                                                                               |
  |                   |     "self": {                                                                                   |
  |                   |         "href": "/vnfpkgm/v1/vnf_packages/baec2512-2c97-4ced-857a-4a7e3f0bbb93"                 |
  |                   |     },                                                                                          |
  |                   |     "packageContent": {                                                                         |
  |                   |         "href": "/vnfpkgm/v1/vnf_packages/baec2512-2c97-4ced-857a-4a7e3f0bbb93/package_content" |
  |                   |     }                                                                                           |
  |                   | }                                                                                               |
  | Onboarding State  | CREATED                                                                                         |
  | Operational State | DISABLED                                                                                        |
  | Usage State       | NOT_IN_USE                                                                                      |
  | User Defined Data | {}                                                                                              |
  +-------------------+-------------------------------------------------------------------------------------------------+

.. code-block:: console

  $ openstack vnf package upload baec2512-2c97-4ced-857a-4a7e3f0bbb93 --path sol_v2_kubernetes_vnf_package.zip
  Upload request for VNF package baec2512-2c97-4ced-857a-4a7e3f0bbb93 has been accepted.


Check the VNF Package
^^^^^^^^^^^^^^^^^^^^^

After executing the VNF Package Upload command, check if the package is
successfully registered.
Confirm that "Onboarding State" is ONBOARDED and "Operational State" is ENABLED.

.. code-block:: console

  $ openstack vnf package show baec2512-2c97-4ced-857a-4a7e3f0bbb93
  +----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field                | Value                                                                                                                                                  |
  +----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Additional Artifacts |                                                                                                                                                        |
  | Checksum             | {                                                                                                                                                      |
  |                      |     "algorithm": "sha512",                                                                                                                             |
  |                      |     "hash": "e7932b21fad5702528814da80319358bf0676026cbbb71c55288da75cd208497f9273c8c08d7df3de41cc660810256e1b64228ffa13f21e8519768b467d152a2"         |
  |                      | }                                                                                                                                                      |
  | ID                   | baec2512-2c97-4ced-857a-4a7e3f0bbb93                                                                                                                   |
  | Links                | {                                                                                                                                                      |
  |                      |     "self": {                                                                                                                                          |
  |                      |         "href": "/vnfpkgm/v1/vnf_packages/baec2512-2c97-4ced-857a-4a7e3f0bbb93"                                                                        |
  |                      |     },                                                                                                                                                 |
  |                      |     "packageContent": {                                                                                                                                |
  |                      |         "href": "/vnfpkgm/v1/vnf_packages/baec2512-2c97-4ced-857a-4a7e3f0bbb93/package_content"                                                        |
  |                      |     }                                                                                                                                                  |
  |                      | }                                                                                                                                                      |
  | Onboarding State     | ONBOARDED                                                                                                                                              |
  | Operational State    | ENABLED                                                                                                                                                |
  | Software Images      | [                                                                                                                                                      |
  |                      |     {                                                                                                                                                  |
  |                      |         "provider": "",                                                                                                                                |
  |                      |         "id": "masterNode",                                                                                                                            |
  |                      |         "containerFormat": "bare",                                                                                                                     |
  |                      |         "name": "masterNode-image",                                                                                                                    |
  |                      |         "diskFormat": "qcow2",                                                                                                                         |
  |                      |         "createdAt": "2024-04-16 04:22:31+00:00",                                                                                                      |
  |                      |         "size": 2000000000,                                                                                                                            |
  |                      |         "minRam": 0,                                                                                                                                   |
  |                      |         "imagePath": "Files/images/ubuntu-22.04-server-cloudimg-amd64.img",                                                                            |
  |                      |         "version": "22.04",                                                                                                                            |
  |                      |         "minDisk": 0,                                                                                                                                  |
  |                      |         "checksum": {                                                                                                                                  |
  |                      |             "algorithm": "sha-512",                                                                                                                    |
  |                      |             "hash": "aa6e468377de91730afca98b7dd596cc8f86e06b1e850b1be4badc15f8dd44b49f2ed1b20e0b3ac2b4a7a2e5067fc0ca3d18cd3a3a84a21c31e90f89d6517cc7" |
  |                      |         },                                                                                                                                             |
  |                      |         "userMetadata": {}                                                                                                                             |
  |                      |     },                                                                                                                                                 |
  |                      |     {                                                                                                                                                  |
  |                      |         "provider": "",                                                                                                                                |
  |                      |         "id": "workerNode",                                                                                                                            |
  |                      |         "containerFormat": "bare",                                                                                                                     |
  |                      |         "name": "workerNode-image",                                                                                                                    |
  |                      |         "diskFormat": "qcow2",                                                                                                                         |
  |                      |         "createdAt": "2024-04-16 04:22:32+00:00",                                                                                                      |
  |                      |         "size": 2000000000,                                                                                                                            |
  |                      |         "minRam": 0,                                                                                                                                   |
  |                      |         "imagePath": "Files/images/ubuntu-22.04-server-cloudimg-amd64.img",                                                                            |
  |                      |         "version": "22.04",                                                                                                                            |
  |                      |         "minDisk": 0,                                                                                                                                  |
  |                      |         "checksum": {                                                                                                                                  |
  |                      |             "algorithm": "sha-512",                                                                                                                    |
  |                      |             "hash": "aa6e468377de91730afca98b7dd596cc8f86e06b1e850b1be4badc15f8dd44b49f2ed1b20e0b3ac2b4a7a2e5067fc0ca3d18cd3a3a84a21c31e90f89d6517cc7" |
  |                      |         },                                                                                                                                             |
  |                      |         "userMetadata": {}                                                                                                                             |
  |                      |     },                                                                                                                                                 |
  |                      |     {                                                                                                                                                  |
  |                      |         "provider": "",                                                                                                                                |
  |                      |         "id": "masterNode",                                                                                                                            |
  |                      |         "containerFormat": "bare",                                                                                                                     |
  |                      |         "name": "masterNode-image",                                                                                                                    |
  |                      |         "diskFormat": "qcow2",                                                                                                                         |
  |                      |         "createdAt": "2024-04-16 04:22:36+00:00",                                                                                                      |
  |                      |         "size": 2000000000,                                                                                                                            |
  |                      |         "minRam": 0,                                                                                                                                   |
  |                      |         "imagePath": "Files/images/ubuntu-22.04-server-cloudimg-amd64.img",                                                                            |
  |                      |         "version": "22.04",                                                                                                                            |
  |                      |         "minDisk": 0,                                                                                                                                  |
  |                      |         "checksum": {                                                                                                                                  |
  |                      |             "algorithm": "sha-512",                                                                                                                    |
  |                      |             "hash": "aa6e468377de91730afca98b7dd596cc8f86e06b1e850b1be4badc15f8dd44b49f2ed1b20e0b3ac2b4a7a2e5067fc0ca3d18cd3a3a84a21c31e90f89d6517cc7" |
  |                      |         },                                                                                                                                             |
  |                      |         "userMetadata": {}                                                                                                                             |
  |                      |     },                                                                                                                                                 |
  |                      |     {                                                                                                                                                  |
  |                      |         "provider": "",                                                                                                                                |
  |                      |         "id": "workerNode",                                                                                                                            |
  |                      |         "containerFormat": "bare",                                                                                                                     |
  |                      |         "name": "workerNode-image",                                                                                                                    |
  |                      |         "diskFormat": "qcow2",                                                                                                                         |
  |                      |         "createdAt": "2024-04-16 04:22:37+00:00",                                                                                                      |
  |                      |         "size": 2000000000,                                                                                                                            |
  |                      |         "minRam": 0,                                                                                                                                   |
  |                      |         "imagePath": "Files/images/ubuntu-22.04-server-cloudimg-amd64.img",                                                                            |
  |                      |         "version": "22.04",                                                                                                                            |
  |                      |         "minDisk": 0,                                                                                                                                  |
  |                      |         "checksum": {                                                                                                                                  |
  |                      |             "algorithm": "sha-512",                                                                                                                    |
  |                      |             "hash": "aa6e468377de91730afca98b7dd596cc8f86e06b1e850b1be4badc15f8dd44b49f2ed1b20e0b3ac2b4a7a2e5067fc0ca3d18cd3a3a84a21c31e90f89d6517cc7" |
  |                      |         },                                                                                                                                             |
  |                      |         "userMetadata": {}                                                                                                                             |
  |                      |     }                                                                                                                                                  |
  |                      | ]                                                                                                                                                      |
  | Usage State          | NOT_IN_USE                                                                                                                                             |
  | User Defined Data    | {}                                                                                                                                                     |
  | VNF Product Name     | Sample VNF                                                                                                                                             |
  | VNF Provider         | Company                                                                                                                                                |
  | VNF Software Version | 1.0                                                                                                                                                    |
  | VNFD ID              | d34ac189-5376-493f-828f-224dd5fe7393                                                                                                                   |
  | VNFD Version         | 1.0                                                                                                                                                    |
  +----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+


Deploying a Kubernetes cluster
------------------------------

Create a Kubernetes cluster using MgmtDriver.

Request Parameter Description
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You must define k8s_cluster_installation_param in the additionalParams of each
request as the information to configure the Kubernetes cluster in the
MgmtDriver script.

Describes the parameters of k8s_cluster_installation_param.

k8s_cluster_installation_param

- script_path: Path to the Kubernetes cluster Install script
  (install_k8s_cluster.sh).

- master_node: Master Node Configuration Information.

    - vdu_id:  Master Node's vduId.
    - ssh_cp_name: Resource name of the Port used for SSH connection to the VM.
    - nic_cp_name: Resource name of the Port used by the VM's Network
      Interface.
    - username: User for VM login.
    - password: User password for VM login. Specify the password changed
      in Ubuntu Image settings.
    - pod_cidr: Network address used by Kubernetes pod(default:10.0.0.0/8).
    - cluster_cidr: Network address used by the Service in the Kubernetes
      cluster(default:10.96.0.0/12).
    - cluster_cp_name: Resources used for Kubernetes cluster endpoints
      In single configuration, use the nic_cp_name of the MasterNode,
      and in complex configuration, use the resource used for the Cluster IP.
    - cluster_fip_name: Resources used by FloatingIP for Cluster IP.

- worker_node: Worker Node Configuration Information.

    - vdu_id: Worker Node's vduId.
    - ssh_cp_name: Resource name of the Port used for SSH connection to the VM.
    - nic_cp_name: Resource name of the Port used by the VM's Network
      Interface.
    - username: User for VM login.
    - password: User password for VM login. Specify the password changed in
      Ubuntu Image settings.


Creating a Kubernetes cluster using simple flavour
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a Kubernetes cluster using simple flavour.

Create VNF Instance
~~~~~~~~~~~~~~~~~~~

Create a VNF instance.

.. code-block:: console

  $ openstack vnflcm create d34ac189-5376-493f-828f-224dd5fe7393 --name v2-kubernetes-sample --description v2-kubernetes-sample --os-tacker-api-version 2
  +-----------------------------+------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                            |
  +-----------------------------+------------------------------------------------------------------------------------------------------------------+
  | ID                          | 14c5406b-f627-4391-b91b-440f242623ac                                                                             |
  | Instantiation State         | NOT_INSTANTIATED                                                                                                 |
  | Links                       | {                                                                                                                |
  |                             |     "self": {                                                                                                    |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac"             |
  |                             |     },                                                                                                           |
  |                             |     "instantiate": {                                                                                             |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/instantiate" |
  |                             |     }                                                                                                            |
  |                             | }                                                                                                                |
  | VNF Configurable Properties |                                                                                                                  |
  | VNF Instance Description    | v2-kubernetes-sample                                                                                             |
  | VNF Instance Name           | v2-kubernetes-sample                                                                                             |
  | VNF Product Name            | Sample VNF                                                                                                       |
  | VNF Provider                | Company                                                                                                          |
  | VNF Software Version        | 1.0                                                                                                              |
  | VNFD ID                     | d34ac189-5376-493f-828f-224dd5fe7393                                                                             |
  | VNFD Version                | 1.0                                                                                                              |
  +-----------------------------+------------------------------------------------------------------------------------------------------------------+


Instantiate VNF
~~~~~~~~~~~~~~~

Instantiate using the following request parameter. The file name is
simple_kubernetes_param_file_v2.json. Some parameters need to be changed to
suit your environment.

.. code-block::

  {
    "flavourId": "simple",
    "vimConnectionInfo": {
      "vim1": {
        "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
        "vimId": "d82ee798-a1d2-4854-8f74-4892ad706751",
        "interfaceInfo": {
          "endpoint": "http://localhost/identity/v3"
        },
        "accessInfo": {
          "username": "nfv_user",
          "region": "RegionOne",
          "password": "devstack",
          "project": "nfv",
          "projectDomain": "Default",
          "userDomain": "Default"
        }
      }
    },
    "additionalParams": {
      "k8s_cluster_installation_param": {
         "script_path": "Scripts/install_k8s_cluster.sh",
         "vim_name": "kubernetes_vim",
         "master_node": {
           "vdu_id": "masterNode",
           "ssh_cp_name": "masterNode_CP1_floating_ip",
           "nic_cp_name": "masterNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu",
           "pod_cidr": "10.200.0.0/16",
           "cluster_cp_name": "masterNode_CP1"
         },
         "worker_node": {
           "vdu_id": "workerNode",
           "ssh_cp_name": "workerNode_CP1_floating_ip",
           "nic_cp_name": "workerNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu"
         }
      },
      "lcm-operation-user-data": "./UserData/userdata_standard.py",
      "lcm-operation-user-data-class": "StandardUserData"
    },
    "extVirtualLinks": [
      {
        "id": "net0_master",
        "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313",
        "extCps": [
          {
            "cpdId": "masterNode_CP1",
            "cpConfig": {
              "Master_CP1": {
                "cpProtocolData": [
                  {
                    "layerProtocol": "IP_OVER_ETHERNET",
                    "ipOverEthernet": {
                      "ipAddresses": [
                        {
                          "type": "IPV4",
                          "numDynamicAddresses": 1
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        ]
      },
      {
        "id": "net0_worker",
        "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313",
        "extCps": [
          {
            "cpdId": "workerNode_CP1",
            "cpConfig": {
              "WorkerCP1": {
                "cpProtocolData": [
                  {
                    "layerProtocol": "IP_OVER_ETHERNET",
                    "ipOverEthernet": {
                      "ipAddresses": [
                        {
                          "type": "IPV4",
                          "numDynamicAddresses": 1
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    ]
  }


Instantiate operation.

.. code-block:: console

  $ openstack vnflcm instantiate 14c5406b-f627-4391-b91b-440f242623ac simple_kubernetes_param_file_v2.json --os-tacker-api-version 2
  Instantiate request for VNF Instance 14c5406b-f627-4391-b91b-440f242623ac has been accepted.


Check after Operation
~~~~~~~~~~~~~~~~~~~~~

After the Status of LCM operation is COMPLETE, check the VNF instance and
Kubernetes cluster.

.. code-block:: console

  $ openstack vnflcm show 14c5406b-f627-4391-b91b-440f242623ac --os-tacker-api-version 2
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                                  |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | ID                          | 14c5406b-f627-4391-b91b-440f242623ac                                                                                                   |
  | Instantiated Vnf Info       | {                                                                                                                                      |
  |                             |     "flavourId": "simple",                                                                                                             |
  |                             |     "vnfState": "STARTED",                                                                                                             |
  |                             |     "scaleStatus": [                                                                                                                   |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 0                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "maxScaleLevels": [                                                                                                                |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 2                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extCpInfo": [                                                                                                                     |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-ae1688fc-6a57-4be5-9556-9436d46827a2",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "ae1688fc-6a57-4be5-9556-9436d46827a2",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-6d57c7b2-85c9-4c35-9e37-23ebdb9f9172",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "6d57c7b2-85c9-4c35-9e37-23ebdb9f9172",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-ea9875b6-ff85-4d36-a559-913e424963d5"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-bed06f84-ad08-4c5d-bc5e-92126338fc19"                                                |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extVirtualLinkInfo": [                                                                                                            |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_master",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "ae1688fc-6a57-4be5-9556-9436d46827a2",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "ae1688fc-6a57-4be5-9556-9436d46827a2",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-ae1688fc-6a57-4be5-9556-9436d46827a2"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "Master_CP1": {                                                                                                |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_worker",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "6d57c7b2-85c9-4c35-9e37-23ebdb9f9172",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "6d57c7b2-85c9-4c35-9e37-23ebdb9f9172",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-6d57c7b2-85c9-4c35-9e37-23ebdb9f9172"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "WorkerCP1": {                                                                                                 |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcResourceInfo": [                                                                                                              |
  |                             |         {                                                                                                                              |
  |                             |             "id": "ea9875b6-ff85-4d36-a559-913e424963d5",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "ea9875b6-ff85-4d36-a559-913e424963d5",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-ea9875b6-ff85-4d36-a559-913e424963d5",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-6d57c7b2-85c9-4c35-9e37-23ebdb9f9172"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-16T04:53:45Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-1-kzucycjp37uz/44c28eaf-10a0-4899-8cf7-9793ce2e2699", |
  |                             |                 "vdu_idx": 1,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-1": "529f058a-6097-463b-bda0-f25a4356d62f"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-ae1688fc-6a57-4be5-9556-9436d46827a2"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-16T04:53:44Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-0-nido6vmrnvkx/6184e70f-e8b8-4555-b1a8-18be7a553bf6", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-0": "f9766b26-6876-427d-a745-d6a83606d5bb"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-16T04:53:43Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-0-qi6uhdjwtdux/134dfd69-cedf-4886-b032-34120fad03f1", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-0": "529f058a-6097-463b-bda0-f25a4356d62f"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcInfo": [                                                                                                                      |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-ea9875b6-ff85-4d36-a559-913e424963d5",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "ea9875b6-ff85-4d36-a559-913e424963d5",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "metadata": {                                                                                                                      |
  |                             |         "stack_id": "bb1fa0a7-f4d0-4205-b77c-b0f22506c0b4",                                                                            |
  |                             |         "nfv": {                                                                                                                       |
  |                             |             "VDU": {                                                                                                                   |
  |                             |                 "masterNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "f9766b26-6876-427d-a745-d6a83606d5bb"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "529f058a-6097-463b-bda0-f25a4356d62f"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-1": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "529f058a-6097-463b-bda0-f25a4356d62f"                                                                |
  |                             |                 }                                                                                                                      |
  |                             |             },                                                                                                                         |
  |                             |             "CP": {                                                                                                                    |
  |                             |                 "masterNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-1": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         "tenant": "nfv"                                                                                                                |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | Instantiation State         | INSTANTIATED                                                                                                                           |
  | Links                       | {                                                                                                                                      |
  |                             |     "self": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac"                                   |
  |                             |     },                                                                                                                                 |
  |                             |     "terminate": {                                                                                                                     |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/terminate"                         |
  |                             |     },                                                                                                                                 |
  |                             |     "scale": {                                                                                                                         |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/scale"                             |
  |                             |     },                                                                                                                                 |
  |                             |     "heal": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/heal"                              |
  |                             |     },                                                                                                                                 |
  |                             |     "changeExtConn": {                                                                                                                 |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/change_ext_conn"                   |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VIM Connection Info         | {                                                                                                                                      |
  |                             |     "vim1": {                                                                                                                          |
  |                             |         "vimId": "d82ee798-a1d2-4854-8f74-4892ad706751",                                                                               |
  |                             |         "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",                                                                                   |
  |                             |         "interfaceInfo": {                                                                                                             |
  |                             |             "endpoint": "http://localhost/identity/v3"                                                                                 |
  |                             |         },                                                                                                                             |
  |                             |         "accessInfo": {                                                                                                                |
  |                             |             "region": "RegionOne",                                                                                                     |
  |                             |             "project": "nfv",                                                                                                          |
  |                             |             "username": "nfv_user",                                                                                                    |
  |                             |             "userDomain": "Default",                                                                                                   |
  |                             |             "projectDomain": "Default"                                                                                                 |
  |                             |         }                                                                                                                              |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VNF Configurable Properties |                                                                                                                                        |
  | VNF Instance Description    | v2-kubernetes-sample                                                                                                                   |
  | VNF Instance Name           | v2-kubernetes-sample                                                                                                                   |
  | VNF Product Name            | Sample VNF                                                                                                                             |
  | VNF Provider                | Company                                                                                                                                |
  | VNF Software Version        | 1.0                                                                                                                                    |
  | VNFD ID                     | d34ac189-5376-493f-828f-224dd5fe7393                                                                                                   |
  | VNFD Version                | 1.0                                                                                                                                    |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+


Confirm that the MasterNode and WorkerNode VMs have been created.

.. code-block:: console

  $ openstack server list
  +--------------------------------------+------------+--------+-------------------------------+------------------+-----------+
  | ID                                   | Name       | Status | Networks                      | Image            | Flavor    |
  +--------------------------------------+------------+--------+-------------------------------+------------------+-----------+
  | bed06f84-ad08-4c5d-bc5e-92126338fc19 | workerNode | ACTIVE | net0=10.10.0.9, 172.24.4.72   | workerNode-image | m1.medium |
  | ea9875b6-ff85-4d36-a559-913e424963d5 | workerNode | ACTIVE | net0=10.10.0.30, 172.24.4.161 | workerNode-image | m1.medium |
  | ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded | masterNode | ACTIVE | net0=10.10.0.231, 172.24.4.3  | masterNode-image | m1.medium |
  +--------------------------------------+------------+--------+-------------------------------+------------------+-----------+


Login to the MasterNode via SSH and check the Node of the Kubernetes cluster.
Verify that all VMs are in the cluster and that the STATUS of the Node is
Ready.

.. note::

  In this script, the VM's hostname is configured as a node role
  (master or worker) and the fourth octet of IP addresses.


.. code-block:: console

  $ kubectl get node -o wide
  NAME        STATUS   ROLES           AGE     VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION       CONTAINER-RUNTIME
  master231   Ready    control-plane   10m     v1.26.8   10.10.0.231   <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker30    Ready    <none>          6m38s   v1.26.8   10.10.0.30    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker9     Ready    <none>          4m18s   v1.26.8   10.10.0.9     <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11



Scale out VNF
~~~~~~~~~~~~~

Perform Scale out operation on the WorkerNode.

Scale out with the following parameters in additionalParams.

.. code-block::

  {
    "additionalParams": {
      "k8s_cluster_installation_param": {
         "script_path": "Scripts/install_k8s_cluster.sh",
         "master_node": {
           "vdu_id": "masterNode",
           "ssh_cp_name": "masterNode_CP1_floating_ip",
           "nic_cp_name": "masterNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu",
           "pod_cidr": "10.200.0.0/16",
           "cluster_cp_name": "masterNode_CP1"
         },
         "worker_node": {
           "vdu_id": "workerNode",
           "ssh_cp_name": "workerNode_CP1_floating_ip",
           "nic_cp_name": "workerNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu"
         }
      },
      "lcm-operation-user-data": "./UserData/userdata_standard.py",
      "lcm-operation-user-data-class": "StandardUserData"
    }
  }


Perform Scale out operation on the WorkerNode.

.. code-block:: console

  $ openstack vnflcm scale 14c5406b-f627-4391-b91b-440f242623ac --type SCALE_OUT --aspect-id workerNode_scale --number-of-steps 1 --additional-param-file simple_additional_params_req --os-tacker-api-version 2
  Scale request for VNF Instance 14c5406b-f627-4391-b91b-440f242623ac has been accepted.


Check after Operation
~~~~~~~~~~~~~~~~~~~~~

After the Status of LCM operation is COMPLETE, check the VNF instance and
Kubernetes cluster.

.. code-block:: console

  $ openstack vnflcm show 14c5406b-f627-4391-b91b-440f242623ac --os-tacker-api-version 2
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                                  |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | ID                          | 14c5406b-f627-4391-b91b-440f242623ac                                                                                                   |
  | Instantiated Vnf Info       | {                                                                                                                                      |
  |                             |     "flavourId": "simple",                                                                                                             |
  |                             |     "vnfState": "STARTED",                                                                                                             |
  |                             |     "scaleStatus": [                                                                                                                   |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 1                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "maxScaleLevels": [                                                                                                                |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 2                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extCpInfo": [                                                                                                                     |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-ae1688fc-6a57-4be5-9556-9436d46827a2",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "ae1688fc-6a57-4be5-9556-9436d46827a2",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-6d57c7b2-85c9-4c35-9e37-23ebdb9f9172",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "6d57c7b2-85c9-4c35-9e37-23ebdb9f9172",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-ea9875b6-ff85-4d36-a559-913e424963d5"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-bed06f84-ad08-4c5d-bc5e-92126338fc19"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-897de2e7-6468-4255-8c94-e244e5f3efc1",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "897de2e7-6468-4255-8c94-e244e5f3efc1",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-e5008abc-f6c4-4828-947d-acd6e7dce86b"                                                |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extVirtualLinkInfo": [                                                                                                            |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_master",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "ae1688fc-6a57-4be5-9556-9436d46827a2",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "ae1688fc-6a57-4be5-9556-9436d46827a2",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-ae1688fc-6a57-4be5-9556-9436d46827a2"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "Master_CP1": {                                                                                                |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_worker",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "6d57c7b2-85c9-4c35-9e37-23ebdb9f9172",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "6d57c7b2-85c9-4c35-9e37-23ebdb9f9172",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-6d57c7b2-85c9-4c35-9e37-23ebdb9f9172"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "897de2e7-6468-4255-8c94-e244e5f3efc1",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "897de2e7-6468-4255-8c94-e244e5f3efc1",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-897de2e7-6468-4255-8c94-e244e5f3efc1"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "WorkerCP1": {                                                                                                 |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcResourceInfo": [                                                                                                              |
  |                             |         {                                                                                                                              |
  |                             |             "id": "e5008abc-f6c4-4828-947d-acd6e7dce86b",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "e5008abc-f6c4-4828-947d-acd6e7dce86b",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-e5008abc-f6c4-4828-947d-acd6e7dce86b",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-897de2e7-6468-4255-8c94-e244e5f3efc1"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-16T05:33:36Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-2-t2uwzgmhvzec/74cff50f-694a-4c00-ae95-d01834be03fe", |
  |                             |                 "vdu_idx": 2,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-2": "529f058a-6097-463b-bda0-f25a4356d62f"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "ea9875b6-ff85-4d36-a559-913e424963d5",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "ea9875b6-ff85-4d36-a559-913e424963d5",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-ea9875b6-ff85-4d36-a559-913e424963d5",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-6d57c7b2-85c9-4c35-9e37-23ebdb9f9172"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-16T04:53:45Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-1-kzucycjp37uz/44c28eaf-10a0-4899-8cf7-9793ce2e2699", |
  |                             |                 "vdu_idx": 1,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-1": "529f058a-6097-463b-bda0-f25a4356d62f"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-ae1688fc-6a57-4be5-9556-9436d46827a2"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-16T04:53:44Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-0-nido6vmrnvkx/6184e70f-e8b8-4555-b1a8-18be7a553bf6", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-0": "f9766b26-6876-427d-a745-d6a83606d5bb"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-16T04:53:43Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-0-qi6uhdjwtdux/134dfd69-cedf-4886-b032-34120fad03f1", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-0": "529f058a-6097-463b-bda0-f25a4356d62f"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcInfo": [                                                                                                                      |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-e5008abc-f6c4-4828-947d-acd6e7dce86b",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "e5008abc-f6c4-4828-947d-acd6e7dce86b",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-ea9875b6-ff85-4d36-a559-913e424963d5",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "ea9875b6-ff85-4d36-a559-913e424963d5",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "metadata": {                                                                                                                      |
  |                             |         "stack_id": "bb1fa0a7-f4d0-4205-b77c-b0f22506c0b4",                                                                            |
  |                             |         "nfv": {                                                                                                                       |
  |                             |             "VDU": {                                                                                                                   |
  |                             |                 "masterNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "f9766b26-6876-427d-a745-d6a83606d5bb"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "529f058a-6097-463b-bda0-f25a4356d62f"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-1": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "529f058a-6097-463b-bda0-f25a4356d62f"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-2": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "529f058a-6097-463b-bda0-f25a4356d62f"                                                                |
  |                             |                 }                                                                                                                      |
  |                             |             },                                                                                                                         |
  |                             |             "CP": {                                                                                                                    |
  |                             |                 "masterNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-1": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-2": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         "tenant": "nfv"                                                                                                                |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | Instantiation State         | INSTANTIATED                                                                                                                           |
  | Links                       | {                                                                                                                                      |
  |                             |     "self": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac"                                   |
  |                             |     },                                                                                                                                 |
  |                             |     "terminate": {                                                                                                                     |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/terminate"                         |
  |                             |     },                                                                                                                                 |
  |                             |     "scale": {                                                                                                                         |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/scale"                             |
  |                             |     },                                                                                                                                 |
  |                             |     "heal": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/heal"                              |
  |                             |     },                                                                                                                                 |
  |                             |     "changeExtConn": {                                                                                                                 |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/change_ext_conn"                   |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VIM Connection Info         | {                                                                                                                                      |
  |                             |     "vim1": {                                                                                                                          |
  |                             |         "vimId": "d82ee798-a1d2-4854-8f74-4892ad706751",                                                                               |
  |                             |         "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",                                                                                   |
  |                             |         "interfaceInfo": {                                                                                                             |
  |                             |             "endpoint": "http://localhost/identity/v3"                                                                                 |
  |                             |         },                                                                                                                             |
  |                             |         "accessInfo": {                                                                                                                |
  |                             |             "region": "RegionOne",                                                                                                     |
  |                             |             "project": "nfv",                                                                                                          |
  |                             |             "username": "nfv_user",                                                                                                    |
  |                             |             "userDomain": "Default",                                                                                                   |
  |                             |             "projectDomain": "Default"                                                                                                 |
  |                             |         }                                                                                                                              |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VNF Configurable Properties |                                                                                                                                        |
  | VNF Instance Description    | v2-kubernetes-sample                                                                                                                   |
  | VNF Instance Name           | v2-kubernetes-sample                                                                                                                   |
  | VNF Product Name            | Sample VNF                                                                                                                             |
  | VNF Provider                | Company                                                                                                                                |
  | VNF Software Version        | 1.0                                                                                                                                    |
  | VNFD ID                     | d34ac189-5376-493f-828f-224dd5fe7393                                                                                                   |
  | VNFD Version                | 1.0                                                                                                                                    |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+


Confirm that the VM for the WorkerNode has been added.

.. code-block:: console

  $ openstack server list
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+
  | ID                                   | Name       | Status | Networks                       | Image            | Flavor    |
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+
  | e5008abc-f6c4-4828-947d-acd6e7dce86b | workerNode | ACTIVE | net0=10.10.0.155, 172.24.4.134 | workerNode-image | m1.medium |
  | bed06f84-ad08-4c5d-bc5e-92126338fc19 | workerNode | ACTIVE | net0=10.10.0.9, 172.24.4.72    | workerNode-image | m1.medium |
  | ea9875b6-ff85-4d36-a559-913e424963d5 | workerNode | ACTIVE | net0=10.10.0.30, 172.24.4.161  | workerNode-image | m1.medium |
  | ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded | masterNode | ACTIVE | net0=10.10.0.231, 172.24.4.3   | masterNode-image | m1.medium |
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+


Login to the MasterNode via SSH and check the Node of the Kubernetes cluster.
Verify that the Node has been added and that the STATUS of all Nodes is Ready.

.. code-block:: console

  ubuntu@master231:~$ kubectl get node -o wide
  NAME        STATUS   ROLES           AGE     VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION       CONTAINER-RUNTIME
  master231   Ready    control-plane   41m     v1.26.8   10.10.0.231   <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker155   Ready    <none>          3m40s   v1.26.8   10.10.0.155   <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker30    Ready    <none>          37m     v1.26.8   10.10.0.30    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker9     Ready    <none>          34m     v1.26.8   10.10.0.9     <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11


You also check if cilium is ready.

.. code-block:: console

  ubuntu@master231:~$ cilium status
      /￣￣\
   /￣￣\__/￣￣\    Cilium:             OK
   \__/￣￣\__/    Operator:           OK
   /￣￣\__/￣￣\    Envoy DaemonSet:    disabled (using embedded mode)
   \__/￣￣\__/    Hubble Relay:       disabled
      \__/       ClusterMesh:        disabled

  Deployment             cilium-operator    Desired: 1, Ready: 1/1, Available: 1/1
  DaemonSet              cilium             Desired: 4, Ready: 4/4, Available: 4/4
  Containers:            cilium             Running: 4
                         cilium-operator    Running: 1
  Cluster Pods:          2/2 managed by Cilium
  Helm chart version:
  Image versions         cilium             quay.io/cilium/cilium:v1.14.5@sha256:d3b287029755b6a47dee01420e2ea469469f1b174a2089c10af7e5e9289ef05b: 4
                         cilium-operator    quay.io/cilium/operator-generic:v1.14.5@sha256:303f9076bdc73b3fc32aaedee64a14f6f44c8bb08ee9e3956d443021103ebe7a: 1


Scale in VNF
~~~~~~~~~~~~

Perform Scale in operation on a WorkerNode.
Here, the Scale out operation is followed by the Scale in operation,
which deletes the Node added by Scale out.

The following parameters are specified in additionalParams to perform
the Scale in operation.

.. code-block::

  {
    "additionalParams": {
      "k8s_cluster_installation_param": {
         "script_path": "Scripts/install_k8s_cluster.sh",
         "master_node": {
           "vdu_id": "masterNode",
           "ssh_cp_name": "masterNode_CP1_floating_ip",
           "nic_cp_name": "masterNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu",
           "pod_cidr": "10.200.0.0/16",
           "cluster_cp_name": "masterNode_CP1"
         },
         "worker_node": {
           "vdu_id": "workerNode",
           "ssh_cp_name": "workerNode_CP1_floating_ip",
           "nic_cp_name": "workerNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu"
         }
      },
      "lcm-operation-user-data": "./UserData/userdata_standard.py",
      "lcm-operation-user-data-class": "StandardUserData"
    }
  }


Perform Scale in operation on the WorkerNode.

.. code-block:: console

  $ openstack vnflcm scale 14c5406b-f627-4391-b91b-440f242623ac --type SCALE_IN --aspect-id workerNode_scale --number-of-steps 1 --additional-param-file simple_additional_params_req --os-tacker-api-version 2
  Scale request for VNF Instance 14c5406b-f627-4391-b91b-440f242623ac has been accepted.


Check after Operation
~~~~~~~~~~~~~~~~~~~~~

After the Status of LCM operation is COMPLETE, check the VNF instance and
Kubernetes cluster.

.. code-block:: console

  $ openstack vnflcm show 14c5406b-f627-4391-b91b-440f242623ac --os-tacker-api-version 2
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                                  |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | ID                          | 14c5406b-f627-4391-b91b-440f242623ac                                                                                                   |
  | Instantiated Vnf Info       | {                                                                                                                                      |
  |                             |     "flavourId": "simple",                                                                                                             |
  |                             |     "vnfState": "STARTED",                                                                                                             |
  |                             |     "scaleStatus": [                                                                                                                   |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 0                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "maxScaleLevels": [                                                                                                                |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 2                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extCpInfo": [                                                                                                                     |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-ae1688fc-6a57-4be5-9556-9436d46827a2",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "ae1688fc-6a57-4be5-9556-9436d46827a2",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-6d57c7b2-85c9-4c35-9e37-23ebdb9f9172",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "6d57c7b2-85c9-4c35-9e37-23ebdb9f9172",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-ea9875b6-ff85-4d36-a559-913e424963d5"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-bed06f84-ad08-4c5d-bc5e-92126338fc19"                                                |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extVirtualLinkInfo": [                                                                                                            |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_master",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "ae1688fc-6a57-4be5-9556-9436d46827a2",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "ae1688fc-6a57-4be5-9556-9436d46827a2",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-ae1688fc-6a57-4be5-9556-9436d46827a2"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "Master_CP1": {                                                                                                |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_worker",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "6d57c7b2-85c9-4c35-9e37-23ebdb9f9172",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "6d57c7b2-85c9-4c35-9e37-23ebdb9f9172",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-6d57c7b2-85c9-4c35-9e37-23ebdb9f9172"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "WorkerCP1": {                                                                                                 |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcResourceInfo": [                                                                                                              |
  |                             |         {                                                                                                                              |
  |                             |             "id": "ea9875b6-ff85-4d36-a559-913e424963d5",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "ea9875b6-ff85-4d36-a559-913e424963d5",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-ea9875b6-ff85-4d36-a559-913e424963d5",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-6d57c7b2-85c9-4c35-9e37-23ebdb9f9172"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-16T04:53:45Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-1-kzucycjp37uz/44c28eaf-10a0-4899-8cf7-9793ce2e2699", |
  |                             |                 "vdu_idx": 1,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-1": "529f058a-6097-463b-bda0-f25a4356d62f"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-ae1688fc-6a57-4be5-9556-9436d46827a2"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-16T04:53:44Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-0-nido6vmrnvkx/6184e70f-e8b8-4555-b1a8-18be7a553bf6", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-0": "f9766b26-6876-427d-a745-d6a83606d5bb"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-16T04:53:43Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-0-qi6uhdjwtdux/134dfd69-cedf-4886-b032-34120fad03f1", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-0": "529f058a-6097-463b-bda0-f25a4356d62f"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcInfo": [                                                                                                                      |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-ea9875b6-ff85-4d36-a559-913e424963d5",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "ea9875b6-ff85-4d36-a559-913e424963d5",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "metadata": {                                                                                                                      |
  |                             |         "stack_id": "bb1fa0a7-f4d0-4205-b77c-b0f22506c0b4",                                                                            |
  |                             |         "nfv": {                                                                                                                       |
  |                             |             "VDU": {                                                                                                                   |
  |                             |                 "masterNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "f9766b26-6876-427d-a745-d6a83606d5bb"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "529f058a-6097-463b-bda0-f25a4356d62f"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-1": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "529f058a-6097-463b-bda0-f25a4356d62f"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-2": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "529f058a-6097-463b-bda0-f25a4356d62f"                                                                |
  |                             |                 }                                                                                                                      |
  |                             |             },                                                                                                                         |
  |                             |             "CP": {                                                                                                                    |
  |                             |                 "masterNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-1": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-2": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         "tenant": "nfv"                                                                                                                |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | Instantiation State         | INSTANTIATED                                                                                                                           |
  | Links                       | {                                                                                                                                      |
  |                             |     "self": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac"                                   |
  |                             |     },                                                                                                                                 |
  |                             |     "terminate": {                                                                                                                     |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/terminate"                         |
  |                             |     },                                                                                                                                 |
  |                             |     "scale": {                                                                                                                         |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/scale"                             |
  |                             |     },                                                                                                                                 |
  |                             |     "heal": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/heal"                              |
  |                             |     },                                                                                                                                 |
  |                             |     "changeExtConn": {                                                                                                                 |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/change_ext_conn"                   |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VIM Connection Info         | {                                                                                                                                      |
  |                             |     "vim1": {                                                                                                                          |
  |                             |         "vimId": "d82ee798-a1d2-4854-8f74-4892ad706751",                                                                               |
  |                             |         "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",                                                                                   |
  |                             |         "interfaceInfo": {                                                                                                             |
  |                             |             "endpoint": "http://localhost/identity/v3"                                                                                 |
  |                             |         },                                                                                                                             |
  |                             |         "accessInfo": {                                                                                                                |
  |                             |             "region": "RegionOne",                                                                                                     |
  |                             |             "project": "nfv",                                                                                                          |
  |                             |             "username": "nfv_user",                                                                                                    |
  |                             |             "userDomain": "Default",                                                                                                   |
  |                             |             "projectDomain": "Default"                                                                                                 |
  |                             |         }                                                                                                                              |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VNF Configurable Properties |                                                                                                                                        |
  | VNF Instance Description    | v2-kubernetes-sample                                                                                                                   |
  | VNF Instance Name           | v2-kubernetes-sample                                                                                                                   |
  | VNF Product Name            | Sample VNF                                                                                                                             |
  | VNF Provider                | Company                                                                                                                                |
  | VNF Software Version        | 1.0                                                                                                                                    |
  | VNFD ID                     | d34ac189-5376-493f-828f-224dd5fe7393                                                                                                   |
  | VNFD Version                | 1.0                                                                                                                                    |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+


Confirm that the VM for the WorkerNode has been deleted by the Scale in
operation.

.. code-block:: console

  $ openstack server list
  +--------------------------------------+------------+--------+-------------------------------+------------------+-----------+
  | ID                                   | Name       | Status | Networks                      | Image            | Flavor    |
  +--------------------------------------+------------+--------+-------------------------------+------------------+-----------+
  | bed06f84-ad08-4c5d-bc5e-92126338fc19 | workerNode | ACTIVE | net0=10.10.0.9, 172.24.4.72   | workerNode-image | m1.medium |
  | ea9875b6-ff85-4d36-a559-913e424963d5 | workerNode | ACTIVE | net0=10.10.0.30, 172.24.4.161 | workerNode-image | m1.medium |
  | ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded | masterNode | ACTIVE | net0=10.10.0.231, 172.24.4.3  | masterNode-image | m1.medium |
  +--------------------------------------+------------+--------+-------------------------------+------------------+-----------+


Login to the MasterNode via SSH and check the Node of the Kubernetes cluster.
Verify that the Node has been deleted and that the STATUS of all Nodes is Ready.

.. code-block:: console

  ubuntu@master231:~$ kubectl get node -o wide
  NAME        STATUS   ROLES           AGE   VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION       CONTAINER-RUNTIME
  master231   Ready    control-plane   49m   v1.26.8   10.10.0.231   <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker30    Ready    <none>          45m   v1.26.8   10.10.0.30    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker9     Ready    <none>          42m   v1.26.8   10.10.0.9     <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11


You also check if cilium is ready.

.. code-block:: console

  ubuntu@master231:~$ cilium status
      /￣￣\
   /￣￣\__/￣￣\    Cilium:             OK
   \__/￣￣\__/    Operator:           OK
   /￣￣\__/￣￣\    Envoy DaemonSet:    disabled (using embedded mode)
   \__/￣￣\__/    Hubble Relay:       disabled
      \__/       ClusterMesh:        disabled

  Deployment             cilium-operator    Desired: 1, Ready: 1/1, Available: 1/1
  DaemonSet              cilium             Desired: 3, Ready: 3/3, Available: 3/3
  Containers:            cilium             Running: 3
                         cilium-operator    Running: 1
  Cluster Pods:          2/2 managed by Cilium
  Helm chart version:
  Image versions         cilium             quay.io/cilium/cilium:v1.14.5@sha256:d3b287029755b6a47dee01420e2ea469469f1b174a2089c10af7e5e9289ef05b: 3
                         cilium-operator    quay.io/cilium/operator-generic:v1.14.5@sha256:303f9076bdc73b3fc32aaedee64a14f6f44c8bb08ee9e3956d443021103ebe7a: 1


Heal VNF
~~~~~~~~

Perform Heal operation on a VNFC.

Heal by specifying the following in additionalParams.

.. code-block::

  {
    "additionalParams": {
      "k8s_cluster_installation_param": {
         "script_path": "Scripts/install_k8s_cluster.sh",
         "master_node": {
           "vdu_id": "masterNode",
           "ssh_cp_name": "masterNode_CP1_floating_ip",
           "nic_cp_name": "masterNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu",
           "pod_cidr": "10.200.0.0/16",
           "cluster_cp_name": "masterNode_CP1"
         },
         "worker_node": {
           "vdu_id": "workerNode",
           "ssh_cp_name": "workerNode_CP1_floating_ip",
           "nic_cp_name": "workerNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu"
         }
      },
      "lcm-operation-user-data": "./UserData/userdata_standard.py",
      "lcm-operation-user-data-class": "StandardUserData"
      }
  }


Perform heal operation on WorkerNode's
VNFC(workerNode-ea9875b6-ff85-4d36-a559-913e424963d5).

.. code-block:: console

  $ openstack vnflcm heal 14c5406b-f627-4391-b91b-440f242623ac --vnfc-instance workerNode-ea9875b6-ff85-4d36-a559-913e424963d5 --additional-param-file simple_additional_params_req --os-tacker-api-version 2
  Heal request for VNF Instance 14c5406b-f627-4391-b91b-440f242623ac has been accepted.


Check after Operation
~~~~~~~~~~~~~~~~~~~~~

After the Status of LCM operation is COMPLETE, check the VNF instance and
Kubernetes cluster.

.. code-block:: console

  $ openstack vnflcm show 14c5406b-f627-4391-b91b-440f242623ac --os-tacker-api-version 2
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                                  |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | ID                          | 14c5406b-f627-4391-b91b-440f242623ac                                                                                                   |
  | Instantiated Vnf Info       | {                                                                                                                                      |
  |                             |     "flavourId": "simple",                                                                                                             |
  |                             |     "vnfState": "STARTED",                                                                                                             |
  |                             |     "scaleStatus": [                                                                                                                   |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 0                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "maxScaleLevels": [                                                                                                                |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 2                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extCpInfo": [                                                                                                                     |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-ae1688fc-6a57-4be5-9556-9436d46827a2",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "ae1688fc-6a57-4be5-9556-9436d46827a2",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-6d57c7b2-85c9-4c35-9e37-23ebdb9f9172",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "6d57c7b2-85c9-4c35-9e37-23ebdb9f9172",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-a1131239-9951-44b3-a99e-336d9bb36cfb"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-bed06f84-ad08-4c5d-bc5e-92126338fc19"                                                |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extVirtualLinkInfo": [                                                                                                            |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_master",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "ae1688fc-6a57-4be5-9556-9436d46827a2",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "ae1688fc-6a57-4be5-9556-9436d46827a2",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-ae1688fc-6a57-4be5-9556-9436d46827a2"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "Master_CP1": {                                                                                                |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_worker",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "6d57c7b2-85c9-4c35-9e37-23ebdb9f9172",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "6d57c7b2-85c9-4c35-9e37-23ebdb9f9172",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-6d57c7b2-85c9-4c35-9e37-23ebdb9f9172"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "WorkerCP1": {                                                                                                 |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcResourceInfo": [                                                                                                              |
  |                             |         {                                                                                                                              |
  |                             |             "id": "a1131239-9951-44b3-a99e-336d9bb36cfb",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "a1131239-9951-44b3-a99e-336d9bb36cfb",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-a1131239-9951-44b3-a99e-336d9bb36cfb",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-6d57c7b2-85c9-4c35-9e37-23ebdb9f9172"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-16T06:02:06Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-1-kzucycjp37uz/44c28eaf-10a0-4899-8cf7-9793ce2e2699", |
  |                             |                 "vdu_idx": 1,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-1": "529f058a-6097-463b-bda0-f25a4356d62f"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-ae1688fc-6a57-4be5-9556-9436d46827a2"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-16T04:53:44Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-0-nido6vmrnvkx/6184e70f-e8b8-4555-b1a8-18be7a553bf6", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-0": "f9766b26-6876-427d-a745-d6a83606d5bb"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-63f4daeb-ab7b-4e2f-a1d8-d9fa7288ae85"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-16T04:53:43Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-0-qi6uhdjwtdux/134dfd69-cedf-4886-b032-34120fad03f1", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-0": "529f058a-6097-463b-bda0-f25a4356d62f"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcInfo": [                                                                                                                      |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-a1131239-9951-44b3-a99e-336d9bb36cfb",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "a1131239-9951-44b3-a99e-336d9bb36cfb",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "bed06f84-ad08-4c5d-bc5e-92126338fc19",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "metadata": {                                                                                                                      |
  |                             |         "stack_id": "bb1fa0a7-f4d0-4205-b77c-b0f22506c0b4",                                                                            |
  |                             |         "nfv": {                                                                                                                       |
  |                             |             "VDU": {                                                                                                                   |
  |                             |                 "masterNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "f9766b26-6876-427d-a745-d6a83606d5bb"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "529f058a-6097-463b-bda0-f25a4356d62f"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-1": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "529f058a-6097-463b-bda0-f25a4356d62f"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-2": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "529f058a-6097-463b-bda0-f25a4356d62f"                                                                |
  |                             |                 }                                                                                                                      |
  |                             |             },                                                                                                                         |
  |                             |             "CP": {                                                                                                                    |
  |                             |                 "masterNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-1": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-2": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         "tenant": "nfv"                                                                                                                |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | Instantiation State         | INSTANTIATED                                                                                                                           |
  | Links                       | {                                                                                                                                      |
  |                             |     "self": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac"                                   |
  |                             |     },                                                                                                                                 |
  |                             |     "terminate": {                                                                                                                     |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/terminate"                         |
  |                             |     },                                                                                                                                 |
  |                             |     "scale": {                                                                                                                         |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/scale"                             |
  |                             |     },                                                                                                                                 |
  |                             |     "heal": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/heal"                              |
  |                             |     },                                                                                                                                 |
  |                             |     "changeExtConn": {                                                                                                                 |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/change_ext_conn"                   |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VIM Connection Info         | {                                                                                                                                      |
  |                             |     "vim1": {                                                                                                                          |
  |                             |         "vimId": "d82ee798-a1d2-4854-8f74-4892ad706751",                                                                               |
  |                             |         "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",                                                                                   |
  |                             |         "interfaceInfo": {                                                                                                             |
  |                             |             "endpoint": "http://localhost/identity/v3"                                                                                 |
  |                             |         },                                                                                                                             |
  |                             |         "accessInfo": {                                                                                                                |
  |                             |             "region": "RegionOne",                                                                                                     |
  |                             |             "project": "nfv",                                                                                                          |
  |                             |             "username": "nfv_user",                                                                                                    |
  |                             |             "userDomain": "Default",                                                                                                   |
  |                             |             "projectDomain": "Default"                                                                                                 |
  |                             |         }                                                                                                                              |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VNF Configurable Properties |                                                                                                                                        |
  | VNF Instance Description    | v2-kubernetes-sample                                                                                                                   |
  | VNF Instance Name           | v2-kubernetes-sample                                                                                                                   |
  | VNF Product Name            | Sample VNF                                                                                                                             |
  | VNF Provider                | Company                                                                                                                                |
  | VNF Software Version        | 1.0                                                                                                                                    |
  | VNFD ID                     | d34ac189-5376-493f-828f-224dd5fe7393                                                                                                   |
  | VNFD Version                | 1.0                                                                                                                                    |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+


Confirm that the VM of the WorkerNode is recreated by the Heal operation.

.. code-block:: console

  $ openstack server list
  +--------------------------------------+------------+--------+-------------------------------+------------------+-----------+
  | ID                                   | Name       | Status | Networks                      | Image            | Flavor    |
  +--------------------------------------+------------+--------+-------------------------------+------------------+-----------+
  | a1131239-9951-44b3-a99e-336d9bb36cfb | workerNode | ACTIVE | net0=10.10.0.30, 172.24.4.161 | workerNode-image | m1.medium |
  | bed06f84-ad08-4c5d-bc5e-92126338fc19 | workerNode | ACTIVE | net0=10.10.0.9, 172.24.4.72   | workerNode-image | m1.medium |
  | ebe3b84b-dd2f-4f5a-83e6-4b8e8e589ded | masterNode | ACTIVE | net0=10.10.0.231, 172.24.4.3  | masterNode-image | m1.medium |
  +--------------------------------------+------------+--------+-------------------------------+------------------+-----------+


Login to the MasterNode via SSH and check the Node of the Kubernetes cluster.
Confirm that the STATUS of the re-created worker30 Node is Ready.

.. code-block:: console

  ubuntu@master231:~$ kubectl get node
  NAME        STATUS   ROLES           AGE    VERSION
  master231   Ready    control-plane   68m    v1.26.8
  worker30    Ready    <none>          118s   v1.26.8
  worker9     Ready    <none>          62m    v1.26.8


You also check if cilium is ready.

.. code-block:: console

  ubuntu@master231:~$ cilium status
      /￣￣\
   /￣￣\__/￣￣\    Cilium:             OK
   \__/￣￣\__/    Operator:           OK
   /￣￣\__/￣￣\    Envoy DaemonSet:    disabled (using embedded mode)
   \__/￣￣\__/    Hubble Relay:       disabled
      \__/       ClusterMesh:        disabled

  Deployment             cilium-operator    Desired: 1, Ready: 1/1, Available: 1/1
  DaemonSet              cilium             Desired: 3, Ready: 3/3, Available: 3/3
  Containers:            cilium             Running: 3
                         cilium-operator    Running: 1
  Cluster Pods:          2/2 managed by Cilium
  Helm chart version:
  Image versions         cilium             quay.io/cilium/cilium:v1.14.5@sha256:d3b287029755b6a47dee01420e2ea469469f1b174a2089c10af7e5e9289ef05b: 3
                         cilium-operator    quay.io/cilium/operator-generic:v1.14.5@sha256:303f9076bdc73b3fc32aaedee64a14f6f44c8bb08ee9e3956d443021103ebe7a: 1


Heal VNF
~~~~~~~~

Perform entire VNF heal operations.
Add the parameter "all: true" to the additionalParams of the heal that
specifies the VNFC.

.. code-block::

  {
    "additionalParams": {
      "all": true,
      "k8s_cluster_installation_param": {
         "script_path": "Scripts/install_k8s_cluster.sh",
         "master_node": {
           "vdu_id": "masterNode",
           "ssh_cp_name": "masterNode_CP1_floating_ip",
           "nic_cp_name": "masterNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu",
           "pod_cidr": "10.200.0.0/16",
           "cluster_cp_name": "masterNode_CP1"
         },
         "worker_node": {
           "vdu_id": "workerNode",
           "ssh_cp_name": "workerNode_CP1_floating_ip",
           "nic_cp_name": "workerNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu"
         }
      },
      "lcm-operation-user-data": "./UserData/userdata_standard.py",
      "lcm-operation-user-data-class": "StandardUserData"
    }
  }



Confirm stack id before heal.

.. code-block:: console

  $ openstack stack list
  +------------------------------------+------------------------------------+----------------------------------+-----------------+----------------------+----------------------+
  | ID                                 | Stack Name                         | Project                          | Stack Status    | Creation Time        | Updated Time         |
  +------------------------------------+------------------------------------+----------------------------------+-----------------+----------------------+----------------------+
  | bb1fa0a7-f4d0-4205-b77c-           | vnf-14c5406b-f627-4391-b91b-       | 5d711196514b4f11b02382403b3342a9 | UPDATE_COMPLETE | 2024-04-16T04:53:42Z | 2024-04-16T06:13:27Z |
  | b0f22506c0b4                       | 440f242623ac                       |                                  |                 |                      |                      |
  +------------------------------------+------------------------------------+----------------------------------+-----------------+----------------------+----------------------+


Perform Heal operation.

.. code-block:: console

  $ openstack vnflcm heal 14c5406b-f627-4391-b91b-440f242623ac --additional-param-file simple_additional_params_req --os-tacker-api-version 2
  Heal request for VNF Instance 14c5406b-f627-4391-b91b-440f242623ac has been accepted.


Check after Operation
~~~~~~~~~~~~~~~~~~~~~

After the Status of LCM operation is COMPLETE, check the VNF instance and
Kubernetes cluster.

Verify that the stack has been recreated.

.. code-block:: console

  $ openstack stack list
  +--------------------------------------+------------------------------------------+----------------------------------+-----------------+----------------------+--------------+
  | ID                                   | Stack Name                               | Project                          | Stack Status    | Creation Time        | Updated Time |
  +--------------------------------------+------------------------------------------+----------------------------------+-----------------+----------------------+--------------+
  | 8bcc0978-7d69-4950-87e5-396c4a978f09 | vnf-14c5406b-f627-4391-b91b-440f242623ac | 5d711196514b4f11b02382403b3342a9 | CREATE_COMPLETE | 2024-04-16T06:34:22Z | None         |
  +--------------------------------------+------------------------------------------+----------------------------------+-----------------+----------------------+--------------+


.. code-block:: console

  $ openstack vnflcm show 14c5406b-f627-4391-b91b-440f242623ac --os-tacker-api-version 2
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                                  |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | ID                          | 14c5406b-f627-4391-b91b-440f242623ac                                                                                                   |
  | Instantiated Vnf Info       | {                                                                                                                                      |
  |                             |     "flavourId": "simple",                                                                                                             |
  |                             |     "vnfState": "STARTED",                                                                                                             |
  |                             |     "scaleStatus": [                                                                                                                   |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 0                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "maxScaleLevels": [                                                                                                                |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 2                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extCpInfo": [                                                                                                                     |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-b2c7a409-b20c-4608-870b-7d28bbae0707",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "b2c7a409-b20c-4608-870b-7d28bbae0707",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-78c53b6c-4f96-4ee0-afc5-ca3c9b7dd70c"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-01550e61-6512-405e-8e68-d643a2ced0e3",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "01550e61-6512-405e-8e68-d643a2ced0e3",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-04bd1f79-8878-4649-b062-741899bd3e40"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-8dfe2918-baae-4843-b094-f063174d1a94",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "8dfe2918-baae-4843-b094-f063174d1a94",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-953d61b5-9cc1-454b-ae95-0a2483afd41b"                                                |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extVirtualLinkInfo": [                                                                                                            |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_master",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "b2c7a409-b20c-4608-870b-7d28bbae0707",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "b2c7a409-b20c-4608-870b-7d28bbae0707",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-b2c7a409-b20c-4608-870b-7d28bbae0707"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "Master_CP1": {                                                                                                |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_worker",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "01550e61-6512-405e-8e68-d643a2ced0e3",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "01550e61-6512-405e-8e68-d643a2ced0e3",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-01550e61-6512-405e-8e68-d643a2ced0e3"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "8dfe2918-baae-4843-b094-f063174d1a94",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "8dfe2918-baae-4843-b094-f063174d1a94",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-8dfe2918-baae-4843-b094-f063174d1a94"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "WorkerCP1": {                                                                                                 |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcResourceInfo": [                                                                                                              |
  |                             |         {                                                                                                                              |
  |                             |             "id": "04bd1f79-8878-4649-b062-741899bd3e40",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "04bd1f79-8878-4649-b062-741899bd3e40",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-04bd1f79-8878-4649-b062-741899bd3e40",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-01550e61-6512-405e-8e68-d643a2ced0e3"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-16T06:34:23Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-1-ovgtzrd75exq/d26115ff-6736-4d67-9be2-bff9e1f65470", |
  |                             |                 "vdu_idx": 1,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-1": "529f058a-6097-463b-bda0-f25a4356d62f"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "78c53b6c-4f96-4ee0-afc5-ca3c9b7dd70c",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "78c53b6c-4f96-4ee0-afc5-ca3c9b7dd70c",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-78c53b6c-4f96-4ee0-afc5-ca3c9b7dd70c",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-b2c7a409-b20c-4608-870b-7d28bbae0707"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-16T06:34:25Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-0-spjxfsbzjqom/16fa1b79-e6e0-4ad9-9a39-11824921afdb", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-0": "f9766b26-6876-427d-a745-d6a83606d5bb"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "953d61b5-9cc1-454b-ae95-0a2483afd41b",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "953d61b5-9cc1-454b-ae95-0a2483afd41b",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-953d61b5-9cc1-454b-ae95-0a2483afd41b",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-8dfe2918-baae-4843-b094-f063174d1a94"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-16T06:34:24Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-0-g774ainjzuuj/a03258d9-d14e-43ee-8c3f-66903365f690", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-0": "529f058a-6097-463b-bda0-f25a4356d62f"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcInfo": [                                                                                                                      |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-04bd1f79-8878-4649-b062-741899bd3e40",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "04bd1f79-8878-4649-b062-741899bd3e40",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-78c53b6c-4f96-4ee0-afc5-ca3c9b7dd70c",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "78c53b6c-4f96-4ee0-afc5-ca3c9b7dd70c",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-953d61b5-9cc1-454b-ae95-0a2483afd41b",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "953d61b5-9cc1-454b-ae95-0a2483afd41b",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "metadata": {                                                                                                                      |
  |                             |         "stack_id": "8bcc0978-7d69-4950-87e5-396c4a978f09",                                                                            |
  |                             |         "nfv": {                                                                                                                       |
  |                             |             "VDU": {                                                                                                                   |
  |                             |                 "masterNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "f9766b26-6876-427d-a745-d6a83606d5bb"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "529f058a-6097-463b-bda0-f25a4356d62f"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-1": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "529f058a-6097-463b-bda0-f25a4356d62f"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-2": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "529f058a-6097-463b-bda0-f25a4356d62f"                                                                |
  |                             |                 }                                                                                                                      |
  |                             |             },                                                                                                                         |
  |                             |             "CP": {                                                                                                                    |
  |                             |                 "masterNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-1": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-2": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         "tenant": "nfv"                                                                                                                |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | Instantiation State         | INSTANTIATED                                                                                                                           |
  | Links                       | {                                                                                                                                      |
  |                             |     "self": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac"                                   |
  |                             |     },                                                                                                                                 |
  |                             |     "terminate": {                                                                                                                     |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/terminate"                         |
  |                             |     },                                                                                                                                 |
  |                             |     "scale": {                                                                                                                         |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/scale"                             |
  |                             |     },                                                                                                                                 |
  |                             |     "heal": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/heal"                              |
  |                             |     },                                                                                                                                 |
  |                             |     "changeExtConn": {                                                                                                                 |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/change_ext_conn"                   |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VIM Connection Info         | {                                                                                                                                      |
  |                             |     "vim1": {                                                                                                                          |
  |                             |         "vimId": "d82ee798-a1d2-4854-8f74-4892ad706751",                                                                               |
  |                             |         "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",                                                                                   |
  |                             |         "interfaceInfo": {                                                                                                             |
  |                             |             "endpoint": "http://localhost/identity/v3"                                                                                 |
  |                             |         },                                                                                                                             |
  |                             |         "accessInfo": {                                                                                                                |
  |                             |             "region": "RegionOne",                                                                                                     |
  |                             |             "project": "nfv",                                                                                                          |
  |                             |             "username": "nfv_user",                                                                                                    |
  |                             |             "userDomain": "Default",                                                                                                   |
  |                             |             "projectDomain": "Default"                                                                                                 |
  |                             |         }                                                                                                                              |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VNF Configurable Properties |                                                                                                                                        |
  | VNF Instance Description    | v2-kubernetes-sample                                                                                                                   |
  | VNF Instance Name           | v2-kubernetes-sample                                                                                                                   |
  | VNF Product Name            | Sample VNF                                                                                                                             |
  | VNF Provider                | Company                                                                                                                                |
  | VNF Software Version        | 1.0                                                                                                                                    |
  | VNFD ID                     | d34ac189-5376-493f-828f-224dd5fe7393                                                                                                   |
  | VNFD Version                | 1.0                                                                                                                                    |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+


Verify that all VMs are recreated.

.. code-block:: console

  $ openstack server list
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+
  | ID                                   | Name       | Status | Networks                       | Image            | Flavor    |
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+
  | 78c53b6c-4f96-4ee0-afc5-ca3c9b7dd70c | masterNode | ACTIVE | net0=10.10.0.112, 172.24.4.225 | masterNode-image | m1.medium |
  | 953d61b5-9cc1-454b-ae95-0a2483afd41b | workerNode | ACTIVE | net0=10.10.0.122, 172.24.4.164 | workerNode-image | m1.medium |
  | 04bd1f79-8878-4649-b062-741899bd3e40 | workerNode | ACTIVE | net0=10.10.0.94, 172.24.4.103  | workerNode-image | m1.medium |
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+


Login to the MasterNode via SSH and check the Node of the Kubernetes cluster.
Verify that all VMs are in the cluster and that the STATUS of the Node is
Ready.

.. code-block:: console

  ubuntu@master112:~$ kubectl get node -o wide
  NAME        STATUS   ROLES           AGE     VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION       CONTAINER-RUNTIME
  master112   Ready    control-plane   11m     v1.26.8   10.10.0.112   <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker122   Ready    <none>          4m45s   v1.26.8   10.10.0.122   <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker94    Ready    <none>          7m5s    v1.26.8   10.10.0.94    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11


You also check if cilium is ready.

.. code-block:: console

  ubuntu@master112:~$ cilium status
      /￣￣\
   /￣￣\__/￣￣\    Cilium:             OK
   \__/￣￣\__/    Operator:           OK
   /￣￣\__/￣￣\    Envoy DaemonSet:    disabled (using embedded mode)
   \__/￣￣\__/    Hubble Relay:       disabled
      \__/       ClusterMesh:        disabled

  Deployment             cilium-operator    Desired: 1, Ready: 1/1, Available: 1/1
  DaemonSet              cilium             Desired: 3, Ready: 3/3, Available: 3/3
  Containers:            cilium-operator    Running: 1
                         cilium             Running: 3
  Cluster Pods:          2/2 managed by Cilium
  Helm chart version:
  Image versions         cilium             quay.io/cilium/cilium:v1.14.5@sha256:d3b287029755b6a47dee01420e2ea469469f1b174a2089c10af7e5e9289ef05b: 3
                         cilium-operator    quay.io/cilium/operator-generic:v1.14.5@sha256:303f9076bdc73b3fc32aaedee64a14f6f44c8bb08ee9e3956d443021103ebe7a: 1
  ubuntu@master112:~$



Creating a Kubernetes cluster using complex flavour
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a Kubernetes cluster using complex flavour.

Instantiate VNF
~~~~~~~~~~~~~~~

Instantiate using the following request parameter. The file name is
complex_kubernetes_param_file_v2.json. Some parameters need to be changed to
suit your environment.

.. code-block::

  {
    "flavourId": "complex",
    "vimConnectionInfo": {
      "vim1": {
        "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
        "vimId": "d82ee798-a1d2-4854-8f74-4892ad706751",
        "interfaceInfo": {
          "endpoint": "http://localhost/identity/v3"
        },
        "accessInfo": {
          "username": "nfv_user",
          "region": "RegionOne",
          "password": "devstack",
          "project": "nfv",
          "projectDomain": "Default",
          "userDomain": "Default"
        }
      }
    },
    "additionalParams": {
      "k8s_cluster_installation_param": {
         "script_path": "Scripts/install_k8s_cluster.sh",
         "master_node": {
           "vdu_id": "masterNode",
           "ssh_cp_name": "masterNode_CP1_floating_ip",
           "nic_cp_name": "masterNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu",
           "pod_cidr": "10.200.0.0/16",
           "cluster_cp_name": "vip_CP",
           "cluster_fip_name": "vip_CP_floating_ip"
         },
         "worker_node": {
           "vdu_id": "workerNode",
           "ssh_cp_name": "workerNode_CP1_floating_ip",
           "nic_cp_name": "workerNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu"
         }
      },
      "lcm-operation-user-data": "./UserData/userdata_standard.py",
      "lcm-operation-user-data-class": "StandardUserData"
    },
    "extVirtualLinks": [
      {
        "id": "net0_master",
        "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313",
        "extCps": [
          {
            "cpdId": "masterNode_CP1",
            "cpConfig": {
              "Master_CP1": {
                "cpProtocolData": [
                  {
                    "layerProtocol": "IP_OVER_ETHERNET",
                    "ipOverEthernet": {
                      "ipAddresses": [
                        {
                          "type": "IPV4",
                          "numDynamicAddresses": 1
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        ]
      },
      {
        "id": "net0_worker",
        "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313",
        "extCps": [
          {
            "cpdId": "workerNode_CP1",
            "cpConfig": {
              "WorkerCP1": {
                "cpProtocolData": [
                  {
                    "layerProtocol": "IP_OVER_ETHERNET",
                    "ipOverEthernet": {
                      "ipAddresses": [
                        {
                          "type": "IPV4",
                          "numDynamicAddresses": 1
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    ]
  }


Instantiate operation.

.. code-block:: console

  $ openstack vnflcm instantiate 14c5406b-f627-4391-b91b-440f242623ac complex_kubernetes_param_file_v2.json --os-tacker-api-version 2
  Instantiate request for VNF Instance 14c5406b-f627-4391-b91b-440f242623ac has been accepted.


Check after Operation
~~~~~~~~~~~~~~~~~~~~~

After the Status of LCM operation is COMPLETE, check the VNF instance and
Kubernetes cluster.


Confirm that all VMs for MasterNode and WorkerNode have been created.

.. code-block:: console

  $ openstack server list
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+
  | ID                                   | Name       | Status | Networks                       | Image            | Flavor    |
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+
  | 20ee4d5b-e51f-4e6b-a400-47bfabd48f59 | masterNode | ACTIVE | net0=10.10.0.15, 172.24.4.156  | masterNode-image | m1.medium |
  | 90091dbb-1047-4207-8394-114bd3a3aec9 | masterNode | ACTIVE | net0=10.10.0.153, 172.24.4.107 | masterNode-image | m1.medium |
  | c20645b0-d5b3-4341-bbf2-31528976e760 | masterNode | ACTIVE | net0=10.10.0.219, 172.24.4.140 | masterNode-image | m1.medium |
  | 2cbfaab9-1be9-42c8-be67-ee83083c8e1f | workerNode | ACTIVE | net0=10.10.0.45, 172.24.4.186  | workerNode-image | m1.medium |
  | 355d2203-0952-4f1a-aa71-340d6a5a893f | workerNode | ACTIVE | net0=10.10.0.86, 172.24.4.26   | workerNode-image | m1.medium |
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+


.. code-block:: console

  $ openstack vnflcm show 14c5406b-f627-4391-b91b-440f242623ac --os-tacker-api-version 2
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                                  |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | ID                          | 14c5406b-f627-4391-b91b-440f242623ac                                                                                                   |
  | Instantiated Vnf Info       | {                                                                                                                                      |
  |                             |     "flavourId": "complex",                                                                                                            |
  |                             |     "vnfState": "STARTED",                                                                                                             |
  |                             |     "scaleStatus": [                                                                                                                   |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 0                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "maxScaleLevels": [                                                                                                                |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 2                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extCpInfo": [                                                                                                                     |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-20ee4d5b-e51f-4e6b-a400-47bfabd48f59"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-2f6135f3-7981-4e31-b19c-c7fe84e5af86",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "2f6135f3-7981-4e31-b19c-c7fe84e5af86",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-2cbfaab9-1be9-42c8-be67-ee83083c8e1f"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-90091dbb-1047-4207-8394-114bd3a3aec9"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-049181f6-3df6-4e8c-a518-2954d5ba707e",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "049181f6-3df6-4e8c-a518-2954d5ba707e",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-355d2203-0952-4f1a-aa71-340d6a5a893f"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-adf6941b-56a5-47af-a590-3d7a8d20c6dc",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "adf6941b-56a5-47af-a590-3d7a8d20c6dc",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-c20645b0-d5b3-4341-bbf2-31528976e760"                                                |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extVirtualLinkInfo": [                                                                                                            |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_master",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "adf6941b-56a5-47af-a590-3d7a8d20c6dc",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "adf6941b-56a5-47af-a590-3d7a8d20c6dc",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-adf6941b-56a5-47af-a590-3d7a8d20c6dc"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "Master_CP1": {                                                                                                |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_worker",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "2f6135f3-7981-4e31-b19c-c7fe84e5af86",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "2f6135f3-7981-4e31-b19c-c7fe84e5af86",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-2f6135f3-7981-4e31-b19c-c7fe84e5af86"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "049181f6-3df6-4e8c-a518-2954d5ba707e",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "049181f6-3df6-4e8c-a518-2954d5ba707e",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-049181f6-3df6-4e8c-a518-2954d5ba707e"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "WorkerCP1": {                                                                                                 |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcResourceInfo": [                                                                                                              |
  |                             |         {                                                                                                                              |
  |                             |             "id": "c20645b0-d5b3-4341-bbf2-31528976e760",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "c20645b0-d5b3-4341-bbf2-31528976e760",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-c20645b0-d5b3-4341-bbf2-31528976e760",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-adf6941b-56a5-47af-a590-3d7a8d20c6dc"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:14Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-2-jdclzcogomqy/756fee55-4478-4a1d-a420-1695943bf24a", |
  |                             |                 "vdu_idx": 2,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-2": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "90091dbb-1047-4207-8394-114bd3a3aec9",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "90091dbb-1047-4207-8394-114bd3a3aec9",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-90091dbb-1047-4207-8394-114bd3a3aec9",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:14Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-1-ewevxjfpa5du/6c93f15d-0e1c-419a-82a6-dc0daa8d254c", |
  |                             |                 "vdu_idx": 1,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-1": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-2f6135f3-7981-4e31-b19c-c7fe84e5af86"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:13Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-1-25n3lsnj6kop/e03f90f6-750e-4e86-8f56-fec0f9e8e28b", |
  |                             |                 "vdu_idx": 1,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-1": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:14Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-0-kkckwhq5raf2/efa4697a-7c98-408e-afa8-aece3c5bb42d", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-0": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "355d2203-0952-4f1a-aa71-340d6a5a893f",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "355d2203-0952-4f1a-aa71-340d6a5a893f",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-355d2203-0952-4f1a-aa71-340d6a5a893f",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-049181f6-3df6-4e8c-a518-2954d5ba707e"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:13Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-0-hwuihryx6ik4/abd2ea60-5b70-4787-959f-3dece676cc00", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-0": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcInfo": [                                                                                                                      |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-c20645b0-d5b3-4341-bbf2-31528976e760",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "c20645b0-d5b3-4341-bbf2-31528976e760",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-90091dbb-1047-4207-8394-114bd3a3aec9",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "90091dbb-1047-4207-8394-114bd3a3aec9",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-355d2203-0952-4f1a-aa71-340d6a5a893f",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "355d2203-0952-4f1a-aa71-340d6a5a893f",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "metadata": {                                                                                                                      |
  |                             |         "stack_id": "642dbe88-1cda-4cf4-af9f-f81d53f10232",                                                                            |
  |                             |         "nfv": {                                                                                                                       |
  |                             |             "VDU": {                                                                                                                   |
  |                             |                 "masterNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode-1": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode-2": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-1": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                                |
  |                             |                 }                                                                                                                      |
  |                             |             },                                                                                                                         |
  |                             |             "CP": {                                                                                                                    |
  |                             |                 "masterNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode_CP1-1": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode_CP1-2": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-1": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         "tenant": "nfv"                                                                                                                |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | Instantiation State         | INSTANTIATED                                                                                                                           |
  | Links                       | {                                                                                                                                      |
  |                             |     "self": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac"                                   |
  |                             |     },                                                                                                                                 |
  |                             |     "terminate": {                                                                                                                     |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/terminate"                         |
  |                             |     },                                                                                                                                 |
  |                             |     "scale": {                                                                                                                         |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/scale"                             |
  |                             |     },                                                                                                                                 |
  |                             |     "heal": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/heal"                              |
  |                             |     },                                                                                                                                 |
  |                             |     "changeExtConn": {                                                                                                                 |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/change_ext_conn"                   |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VIM Connection Info         | {                                                                                                                                      |
  |                             |     "vim1": {                                                                                                                          |
  |                             |         "vimId": "d82ee798-a1d2-4854-8f74-4892ad706751",                                                                               |
  |                             |         "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",                                                                                   |
  |                             |         "interfaceInfo": {                                                                                                             |
  |                             |             "endpoint": "http://localhost/identity/v3"                                                                                 |
  |                             |         },                                                                                                                             |
  |                             |         "accessInfo": {                                                                                                                |
  |                             |             "region": "RegionOne",                                                                                                     |
  |                             |             "project": "nfv",                                                                                                          |
  |                             |             "username": "nfv_user",                                                                                                    |
  |                             |             "userDomain": "Default",                                                                                                   |
  |                             |             "projectDomain": "Default"                                                                                                 |
  |                             |         }                                                                                                                              |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VNF Configurable Properties |                                                                                                                                        |
  | VNF Instance Description    | v2-kubernetes-sample                                                                                                                   |
  | VNF Instance Name           | v2-kubernetes-sample                                                                                                                   |
  | VNF Product Name            | Sample VNF                                                                                                                             |
  | VNF Provider                | Company                                                                                                                                |
  | VNF Software Version        | 1.0                                                                                                                                    |
  | VNFD ID                     | d34ac189-5376-493f-828f-224dd5fe7393                                                                                                   |
  | VNFD Version                | 1.0                                                                                                                                    |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+


Log in to any one of the MasterNodes via SSH and check the Nodes in the
Kubernetes cluster. Verify that all VMs are in the cluster and that the
STATUS of the Node is Ready.

.. code-block:: console

  ubuntu@master15:~$ kubectl get node -o wide
  NAME        STATUS   ROLES           AGE     VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION       CONTAINER-RUNTIME
  master15    Ready    control-plane   9m5s    v1.26.8   10.10.0.15    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  master153   Ready    control-plane   13m     v1.26.8   10.10.0.153   <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  master219   Ready    control-plane   18m     v1.26.8   10.10.0.219   <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker45    Ready    <none>          6m26s   v1.26.8   10.10.0.45    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker86    Ready    <none>          4m6s    v1.26.8   10.10.0.86    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11


You also check if cilium is ready.

.. code-block:: console

  ubuntu@master15:~$ cilium status
      /￣￣\
   /￣￣\__/￣￣\    Cilium:             OK
   \__/￣￣\__/    Operator:           OK
   /￣￣\__/￣￣\    Envoy DaemonSet:    disabled (using embedded mode)
   \__/￣￣\__/    Hubble Relay:       disabled
      \__/       ClusterMesh:        disabled

  DaemonSet              cilium             Desired: 5, Ready: 5/5, Available: 5/5
  Deployment             cilium-operator    Desired: 1, Ready: 1/1, Available: 1/1
  Containers:            cilium             Running: 5
                         cilium-operator    Running: 1
  Cluster Pods:          2/2 managed by Cilium
  Helm chart version:
  Image versions         cilium             quay.io/cilium/cilium:v1.14.5@sha256:d3b287029755b6a47dee01420e2ea469469f1b174a2089c10af7e5e9289ef05b: 5
                         cilium-operator    quay.io/cilium/operator-generic:v1.14.5@sha256:303f9076bdc73b3fc32aaedee64a14f6f44c8bb08ee9e3956d443021103ebe7a: 1



Scale out VNF
~~~~~~~~~~~~~

Perform the Scale out operation.

The following sample request parameter is used to perform the Scale out
operation.

.. code-block::

  {
    "additionalParams": {
      "k8s_cluster_installation_param": {
         "script_path": "Scripts/install_k8s_cluster.sh",
         "master_node": {
           "vdu_id": "masterNode",
           "ssh_cp_name": "masterNode_CP1_floating_ip",
           "nic_cp_name": "masterNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu",
           "pod_cidr": "10.200.0.0/16",
           "cluster_cp_name": "vip_CP",
           "cluster_fip_name": "vip_CP_floating_ip"
         },
         "worker_node": {
           "vdu_id": "workerNode",
           "ssh_cp_name": "workerNode_CP1_floating_ip",
           "nic_cp_name": "workerNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu"
         }
      },
      "lcm-operation-user-data": "./UserData/userdata_standard.py",
      "lcm-operation-user-data-class": "StandardUserData"
    }
  }


Perform Scale out operation.

.. code-block:: console

  $ openstack vnflcm scale 14c5406b-f627-4391-b91b-440f242623ac --type SCALE_OUT --aspect-id workerNode_scale --number-of-steps 1 --additional-param-file complex_additional_params_req --os-tacker-api-version 2
  Scale request for VNF Instance 14c5406b-f627-4391-b91b-440f242623ac has been accepted.


Check after Operation
~~~~~~~~~~~~~~~~~~~~~

After the Status of LCM operation is COMPLETE, check the VNF instance and
Kubernetes cluster.

.. code-block:: console

  $ openstack server list
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+
  | ID                                   | Name       | Status | Networks                       | Image            | Flavor    |
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+
  | fbb74f94-52ad-4829-9a9d-a0af3ce2f284 | workerNode | ACTIVE | net0=10.10.0.146, 172.24.4.76  | workerNode-image | m1.medium |
  | 20ee4d5b-e51f-4e6b-a400-47bfabd48f59 | masterNode | ACTIVE | net0=10.10.0.15, 172.24.4.156  | masterNode-image | m1.medium |
  | 90091dbb-1047-4207-8394-114bd3a3aec9 | masterNode | ACTIVE | net0=10.10.0.153, 172.24.4.107 | masterNode-image | m1.medium |
  | c20645b0-d5b3-4341-bbf2-31528976e760 | masterNode | ACTIVE | net0=10.10.0.219, 172.24.4.140 | masterNode-image | m1.medium |
  | 2cbfaab9-1be9-42c8-be67-ee83083c8e1f | workerNode | ACTIVE | net0=10.10.0.45, 172.24.4.186  | workerNode-image | m1.medium |
  | 355d2203-0952-4f1a-aa71-340d6a5a893f | workerNode | ACTIVE | net0=10.10.0.86, 172.24.4.26   | workerNode-image | m1.medium |
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+


.. code-block:: console

  $ openstack vnflcm show 14c5406b-f627-4391-b91b-440f242623ac --os-tacker-api-version 2
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                                  |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | ID                          | 14c5406b-f627-4391-b91b-440f242623ac                                                                                                   |
  | Instantiated Vnf Info       | {                                                                                                                                      |
  |                             |     "flavourId": "complex",                                                                                                            |
  |                             |     "vnfState": "STARTED",                                                                                                             |
  |                             |     "scaleStatus": [                                                                                                                   |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 1                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "maxScaleLevels": [                                                                                                                |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 2                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extCpInfo": [                                                                                                                     |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-20ee4d5b-e51f-4e6b-a400-47bfabd48f59"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-2f6135f3-7981-4e31-b19c-c7fe84e5af86",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "2f6135f3-7981-4e31-b19c-c7fe84e5af86",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-2cbfaab9-1be9-42c8-be67-ee83083c8e1f"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-90091dbb-1047-4207-8394-114bd3a3aec9"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-049181f6-3df6-4e8c-a518-2954d5ba707e",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "049181f6-3df6-4e8c-a518-2954d5ba707e",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-355d2203-0952-4f1a-aa71-340d6a5a893f"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-adf6941b-56a5-47af-a590-3d7a8d20c6dc",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "adf6941b-56a5-47af-a590-3d7a8d20c6dc",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-c20645b0-d5b3-4341-bbf2-31528976e760"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-8672ebdf-3dc6-4360-b0ad-5c96686a9b51",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "8672ebdf-3dc6-4360-b0ad-5c96686a9b51",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-fbb74f94-52ad-4829-9a9d-a0af3ce2f284"                                                |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extVirtualLinkInfo": [                                                                                                            |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_master",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "adf6941b-56a5-47af-a590-3d7a8d20c6dc",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "adf6941b-56a5-47af-a590-3d7a8d20c6dc",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-adf6941b-56a5-47af-a590-3d7a8d20c6dc"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "Master_CP1": {                                                                                                |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_worker",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "2f6135f3-7981-4e31-b19c-c7fe84e5af86",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "2f6135f3-7981-4e31-b19c-c7fe84e5af86",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-2f6135f3-7981-4e31-b19c-c7fe84e5af86"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "049181f6-3df6-4e8c-a518-2954d5ba707e",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "049181f6-3df6-4e8c-a518-2954d5ba707e",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-049181f6-3df6-4e8c-a518-2954d5ba707e"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "8672ebdf-3dc6-4360-b0ad-5c96686a9b51",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "8672ebdf-3dc6-4360-b0ad-5c96686a9b51",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-8672ebdf-3dc6-4360-b0ad-5c96686a9b51"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "WorkerCP1": {                                                                                                 |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcResourceInfo": [                                                                                                              |
  |                             |         {                                                                                                                              |
  |                             |             "id": "fbb74f94-52ad-4829-9a9d-a0af3ce2f284",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "fbb74f94-52ad-4829-9a9d-a0af3ce2f284",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-fbb74f94-52ad-4829-9a9d-a0af3ce2f284",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-8672ebdf-3dc6-4360-b0ad-5c96686a9b51"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T04:15:08Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-2-ocanqfdokv6b/7a8ec846-fadc-42fa-8fc5-bb476518739a", |
  |                             |                 "vdu_idx": 2,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-2": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "c20645b0-d5b3-4341-bbf2-31528976e760",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "c20645b0-d5b3-4341-bbf2-31528976e760",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-c20645b0-d5b3-4341-bbf2-31528976e760",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-adf6941b-56a5-47af-a590-3d7a8d20c6dc"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:14Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-2-jdclzcogomqy/756fee55-4478-4a1d-a420-1695943bf24a", |
  |                             |                 "vdu_idx": 2,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-2": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "90091dbb-1047-4207-8394-114bd3a3aec9",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "90091dbb-1047-4207-8394-114bd3a3aec9",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-90091dbb-1047-4207-8394-114bd3a3aec9",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:14Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-1-ewevxjfpa5du/6c93f15d-0e1c-419a-82a6-dc0daa8d254c", |
  |                             |                 "vdu_idx": 1,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-1": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-2f6135f3-7981-4e31-b19c-c7fe84e5af86"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:13Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-1-25n3lsnj6kop/e03f90f6-750e-4e86-8f56-fec0f9e8e28b", |
  |                             |                 "vdu_idx": 1,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-1": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:14Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-0-kkckwhq5raf2/efa4697a-7c98-408e-afa8-aece3c5bb42d", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-0": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "355d2203-0952-4f1a-aa71-340d6a5a893f",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "355d2203-0952-4f1a-aa71-340d6a5a893f",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-355d2203-0952-4f1a-aa71-340d6a5a893f",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-049181f6-3df6-4e8c-a518-2954d5ba707e"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:13Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-0-hwuihryx6ik4/abd2ea60-5b70-4787-959f-3dece676cc00", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-0": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcInfo": [                                                                                                                      |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-fbb74f94-52ad-4829-9a9d-a0af3ce2f284",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "fbb74f94-52ad-4829-9a9d-a0af3ce2f284",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-c20645b0-d5b3-4341-bbf2-31528976e760",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "c20645b0-d5b3-4341-bbf2-31528976e760",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-90091dbb-1047-4207-8394-114bd3a3aec9",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "90091dbb-1047-4207-8394-114bd3a3aec9",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-355d2203-0952-4f1a-aa71-340d6a5a893f",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "355d2203-0952-4f1a-aa71-340d6a5a893f",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "metadata": {                                                                                                                      |
  |                             |         "stack_id": "642dbe88-1cda-4cf4-af9f-f81d53f10232",                                                                            |
  |                             |         "nfv": {                                                                                                                       |
  |                             |             "VDU": {                                                                                                                   |
  |                             |                 "masterNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode-1": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode-2": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-1": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-2": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                                |
  |                             |                 }                                                                                                                      |
  |                             |             },                                                                                                                         |
  |                             |             "CP": {                                                                                                                    |
  |                             |                 "masterNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode_CP1-1": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode_CP1-2": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-1": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-2": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         "tenant": "nfv"                                                                                                                |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | Instantiation State         | INSTANTIATED                                                                                                                           |
  | Links                       | {                                                                                                                                      |
  |                             |     "self": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac"                                   |
  |                             |     },                                                                                                                                 |
  |                             |     "terminate": {                                                                                                                     |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/terminate"                         |
  |                             |     },                                                                                                                                 |
  |                             |     "scale": {                                                                                                                         |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/scale"                             |
  |                             |     },                                                                                                                                 |
  |                             |     "heal": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/heal"                              |
  |                             |     },                                                                                                                                 |
  |                             |     "changeExtConn": {                                                                                                                 |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/change_ext_conn"                   |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VIM Connection Info         | {                                                                                                                                      |
  |                             |     "vim1": {                                                                                                                          |
  |                             |         "vimId": "d82ee798-a1d2-4854-8f74-4892ad706751",                                                                               |
  |                             |         "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",                                                                                   |
  |                             |         "interfaceInfo": {                                                                                                             |
  |                             |             "endpoint": "http://localhost/identity/v3"                                                                                 |
  |                             |         },                                                                                                                             |
  |                             |         "accessInfo": {                                                                                                                |
  |                             |             "region": "RegionOne",                                                                                                     |
  |                             |             "project": "nfv",                                                                                                          |
  |                             |             "username": "nfv_user",                                                                                                    |
  |                             |             "userDomain": "Default",                                                                                                   |
  |                             |             "projectDomain": "Default"                                                                                                 |
  |                             |         }                                                                                                                              |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VNF Configurable Properties |                                                                                                                                        |
  | VNF Instance Description    | v2-kubernetes-sample                                                                                                                   |
  | VNF Instance Name           | v2-kubernetes-sample                                                                                                                   |
  | VNF Product Name            | Sample VNF                                                                                                                             |
  | VNF Provider                | Company                                                                                                                                |
  | VNF Software Version        | 1.0                                                                                                                                    |
  | VNFD ID                     | d34ac189-5376-493f-828f-224dd5fe7393                                                                                                   |
  | VNFD Version                | 1.0                                                                                                                                    |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+


Log in to any one of the MasterNodes via SSH and check the Nodes in
the Kubernetes cluster. Verify that the Nodes have been added and
that the STATUS are all Ready. In this example, worker146 has been added.

.. code-block:: console

  ubuntu@master15:~$ kubectl get node -o wide
  NAME        STATUS   ROLES           AGE     VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION       CONTAINER-RUNTIME
  master15    Ready    control-plane   122m    v1.26.8   10.10.0.15    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  master153   Ready    control-plane   126m    v1.26.8   10.10.0.153   <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  master219   Ready    control-plane   132m    v1.26.8   10.10.0.219   <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker146   Ready    <none>          3m28s   v1.26.8   10.10.0.146   <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker45    Ready    <none>          119m    v1.26.8   10.10.0.45    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker86    Ready    <none>          117m    v1.26.8   10.10.0.86    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11


You also check if cilium is ready.

.. code-block:: console

  ubuntu@master15:~$ cilium status
      /￣￣\
   /￣￣\__/￣￣\    Cilium:             OK
   \__/￣￣\__/    Operator:           OK
   /￣￣\__/￣￣\    Envoy DaemonSet:    disabled (using embedded mode)
   \__/￣￣\__/    Hubble Relay:       disabled
      \__/       ClusterMesh:        disabled


Scale in VNF
~~~~~~~~~~~~

The following parameters are specified in additionalParams to perform
the Scale in operation.

.. code-block::

  {
    "additionalParams": {
      "k8s_cluster_installation_param": {
         "script_path": "Scripts/install_k8s_cluster.sh",
         "master_node": {
           "vdu_id": "masterNode",
           "ssh_cp_name": "masterNode_CP1_floating_ip",
           "nic_cp_name": "masterNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu",
           "pod_cidr": "10.200.0.0/16",
           "cluster_cp_name": "vip_CP",
           "cluster_fip_name": "vip_CP_floating_ip"
         },
         "worker_node": {
           "vdu_id": "workerNode",
           "ssh_cp_name": "workerNode_CP1_floating_ip",
           "nic_cp_name": "workerNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu"
         }
      },
      "lcm-operation-user-data": "./UserData/userdata_standard.py",
      "lcm-operation-user-data-class": "StandardUserData"
    }
  }


Perform Scale in operation.

.. code-block:: console

  $ openstack vnflcm scale 14c5406b-f627-4391-b91b-440f242623ac --type SCALE_IN --aspect-id workerNode_scale --number-of-steps 1 --additional-param-file complex_additional_params_req --os-tacker-api-version 2
  Scale request for VNF Instance 14c5406b-f627-4391-b91b-440f242623ac has been accepted.


Check after Operation
~~~~~~~~~~~~~~~~~~~~~

After the Status of LCM operation is COMPLETE, check the VNF instance and
Kubernetes cluster.

Confirm that the VM for the WorkerNode has been deleted by the Scale in
operation.

.. code-block:: console

  $ openstack server list
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+
  | ID                                   | Name       | Status | Networks                       | Image            | Flavor    |
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+
  | 20ee4d5b-e51f-4e6b-a400-47bfabd48f59 | masterNode | ACTIVE | net0=10.10.0.15, 172.24.4.156  | masterNode-image | m1.medium |
  | 90091dbb-1047-4207-8394-114bd3a3aec9 | masterNode | ACTIVE | net0=10.10.0.153, 172.24.4.107 | masterNode-image | m1.medium |
  | c20645b0-d5b3-4341-bbf2-31528976e760 | masterNode | ACTIVE | net0=10.10.0.219, 172.24.4.140 | masterNode-image | m1.medium |
  | 2cbfaab9-1be9-42c8-be67-ee83083c8e1f | workerNode | ACTIVE | net0=10.10.0.45, 172.24.4.186  | workerNode-image | m1.medium |
  | 355d2203-0952-4f1a-aa71-340d6a5a893f | workerNode | ACTIVE | net0=10.10.0.86, 172.24.4.26   | workerNode-image | m1.medium |
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+

.. code-block:: console

  $ openstack vnflcm show 14c5406b-f627-4391-b91b-440f242623ac --os-tacker-api-version 2
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                                  |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | ID                          | 14c5406b-f627-4391-b91b-440f242623ac                                                                                                   |
  | Instantiated Vnf Info       | {                                                                                                                                      |
  |                             |     "flavourId": "complex",                                                                                                            |
  |                             |     "vnfState": "STARTED",                                                                                                             |
  |                             |     "scaleStatus": [                                                                                                                   |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 0                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "maxScaleLevels": [                                                                                                                |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 2                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extCpInfo": [                                                                                                                     |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-20ee4d5b-e51f-4e6b-a400-47bfabd48f59"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-2f6135f3-7981-4e31-b19c-c7fe84e5af86",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "2f6135f3-7981-4e31-b19c-c7fe84e5af86",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-2cbfaab9-1be9-42c8-be67-ee83083c8e1f"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-90091dbb-1047-4207-8394-114bd3a3aec9"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-049181f6-3df6-4e8c-a518-2954d5ba707e",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "049181f6-3df6-4e8c-a518-2954d5ba707e",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-355d2203-0952-4f1a-aa71-340d6a5a893f"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-adf6941b-56a5-47af-a590-3d7a8d20c6dc",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "adf6941b-56a5-47af-a590-3d7a8d20c6dc",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-c20645b0-d5b3-4341-bbf2-31528976e760"                                                |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extVirtualLinkInfo": [                                                                                                            |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_master",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "adf6941b-56a5-47af-a590-3d7a8d20c6dc",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "adf6941b-56a5-47af-a590-3d7a8d20c6dc",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-adf6941b-56a5-47af-a590-3d7a8d20c6dc"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "Master_CP1": {                                                                                                |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_worker",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "2f6135f3-7981-4e31-b19c-c7fe84e5af86",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "2f6135f3-7981-4e31-b19c-c7fe84e5af86",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-2f6135f3-7981-4e31-b19c-c7fe84e5af86"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "049181f6-3df6-4e8c-a518-2954d5ba707e",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "049181f6-3df6-4e8c-a518-2954d5ba707e",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-049181f6-3df6-4e8c-a518-2954d5ba707e"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "WorkerCP1": {                                                                                                 |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcResourceInfo": [                                                                                                              |
  |                             |         {                                                                                                                              |
  |                             |             "id": "c20645b0-d5b3-4341-bbf2-31528976e760",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "c20645b0-d5b3-4341-bbf2-31528976e760",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-c20645b0-d5b3-4341-bbf2-31528976e760",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-adf6941b-56a5-47af-a590-3d7a8d20c6dc"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:14Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-2-jdclzcogomqy/756fee55-4478-4a1d-a420-1695943bf24a", |
  |                             |                 "vdu_idx": 2,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-2": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "90091dbb-1047-4207-8394-114bd3a3aec9",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "90091dbb-1047-4207-8394-114bd3a3aec9",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-90091dbb-1047-4207-8394-114bd3a3aec9",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:14Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-1-ewevxjfpa5du/6c93f15d-0e1c-419a-82a6-dc0daa8d254c", |
  |                             |                 "vdu_idx": 1,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-1": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-2f6135f3-7981-4e31-b19c-c7fe84e5af86"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:13Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-1-25n3lsnj6kop/e03f90f6-750e-4e86-8f56-fec0f9e8e28b", |
  |                             |                 "vdu_idx": 1,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-1": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:14Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-0-kkckwhq5raf2/efa4697a-7c98-408e-afa8-aece3c5bb42d", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-0": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "355d2203-0952-4f1a-aa71-340d6a5a893f",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "355d2203-0952-4f1a-aa71-340d6a5a893f",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-355d2203-0952-4f1a-aa71-340d6a5a893f",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-049181f6-3df6-4e8c-a518-2954d5ba707e"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:13Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-0-hwuihryx6ik4/abd2ea60-5b70-4787-959f-3dece676cc00", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-0": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcInfo": [                                                                                                                      |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-c20645b0-d5b3-4341-bbf2-31528976e760",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "c20645b0-d5b3-4341-bbf2-31528976e760",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-90091dbb-1047-4207-8394-114bd3a3aec9",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "90091dbb-1047-4207-8394-114bd3a3aec9",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-355d2203-0952-4f1a-aa71-340d6a5a893f",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "355d2203-0952-4f1a-aa71-340d6a5a893f",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "metadata": {                                                                                                                      |
  |                             |         "stack_id": "642dbe88-1cda-4cf4-af9f-f81d53f10232",                                                                            |
  |                             |         "nfv": {                                                                                                                       |
  |                             |             "VDU": {                                                                                                                   |
  |                             |                 "masterNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode-1": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode-2": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-1": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-2": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                                |
  |                             |                 }                                                                                                                      |
  |                             |             },                                                                                                                         |
  |                             |             "CP": {                                                                                                                    |
  |                             |                 "masterNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode_CP1-1": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode_CP1-2": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-1": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-2": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         "tenant": "nfv"                                                                                                                |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | Instantiation State         | INSTANTIATED                                                                                                                           |
  | Links                       | {                                                                                                                                      |
  |                             |     "self": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac"                                   |
  |                             |     },                                                                                                                                 |
  |                             |     "terminate": {                                                                                                                     |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/terminate"                         |
  |                             |     },                                                                                                                                 |
  |                             |     "scale": {                                                                                                                         |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/scale"                             |
  |                             |     },                                                                                                                                 |
  |                             |     "heal": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/heal"                              |
  |                             |     },                                                                                                                                 |
  |                             |     "changeExtConn": {                                                                                                                 |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/change_ext_conn"                   |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VIM Connection Info         | {                                                                                                                                      |
  |                             |     "vim1": {                                                                                                                          |
  |                             |         "vimId": "d82ee798-a1d2-4854-8f74-4892ad706751",                                                                               |
  |                             |         "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",                                                                                   |
  |                             |         "interfaceInfo": {                                                                                                             |
  |                             |             "endpoint": "http://localhost/identity/v3"                                                                                 |
  |                             |         },                                                                                                                             |
  |                             |         "accessInfo": {                                                                                                                |
  |                             |             "region": "RegionOne",                                                                                                     |
  |                             |             "project": "nfv",                                                                                                          |
  |                             |             "username": "nfv_user",                                                                                                    |
  |                             |             "userDomain": "Default",                                                                                                   |
  |                             |             "projectDomain": "Default"                                                                                                 |
  |                             |         }                                                                                                                              |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VNF Configurable Properties |                                                                                                                                        |
  | VNF Instance Description    | v2-kubernetes-sample                                                                                                                   |
  | VNF Instance Name           | v2-kubernetes-sample                                                                                                                   |
  | VNF Product Name            | Sample VNF                                                                                                                             |
  | VNF Provider                | Company                                                                                                                                |
  | VNF Software Version        | 1.0                                                                                                                                    |
  | VNFD ID                     | d34ac189-5376-493f-828f-224dd5fe7393                                                                                                   |
  | VNFD Version                | 1.0                                                                                                                                    |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+


Log in to any one of the MasterNodes via SSH and check the Nodes in the
Kubernetes cluster. Confirm that the Node of worker146 has been deleted.

.. code-block:: console

  ubuntu@master15:~$ kubectl get node -o wide
  NAME        STATUS   ROLES           AGE    VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION       CONTAINER-RUNTIME
  master15    Ready    control-plane   134m   v1.26.8   10.10.0.15    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  master153   Ready    control-plane   138m   v1.26.8   10.10.0.153   <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  master219   Ready    control-plane   144m   v1.26.8   10.10.0.219   <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker45    Ready    <none>          132m   v1.26.8   10.10.0.45    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker86    Ready    <none>          129m   v1.26.8   10.10.0.86    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11


You also check if cilium is ready.

.. code-block:: console

  ubuntu@master15:~$ cilium status
      /￣￣\
   /￣￣\__/￣￣\    Cilium:             OK
   \__/￣￣\__/    Operator:           OK
   /￣￣\__/￣￣\    Envoy DaemonSet:    disabled (using embedded mode)
   \__/￣￣\__/    Hubble Relay:       disabled
      \__/       ClusterMesh:        disabled

  Deployment             cilium-operator    Desired: 1, Ready: 1/1, Available: 1/1
  DaemonSet              cilium             Desired: 5, Ready: 5/5, Available: 5/5
  Containers:            cilium             Running: 5
                         cilium-operator    Running: 1
  Cluster Pods:          2/2 managed by Cilium
  Helm chart version:
  Image versions         cilium-operator    quay.io/cilium/operator-generic:v1.14.5@sha256:303f9076bdc73b3fc32aaedee64a14f6f44c8bb08ee9e3956d443021103ebe7a: 1
                         cilium             quay.io/cilium/cilium:v1.14.5@sha256:d3b287029755b6a47dee01420e2ea469469f1b174a2089c10af7e5e9289ef05b: 5


Heal VNF
~~~~~~~~

Perform Heal operation specifying VNFC.
In this example, the heal operation is performed from the state after
the Scale in operation.

The following request is specified in additionalParams and the heal is
executed.

.. code-block::

  {
    "additionalParams": {
      "k8s_cluster_installation_param": {
         "script_path": "Scripts/install_k8s_cluster.sh",
         "master_node": {
           "vdu_id": "masterNode",
           "ssh_cp_name": "masterNode_CP1_floating_ip",
           "nic_cp_name": "masterNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu",
           "pod_cidr": "10.200.0.0/16",
           "cluster_cp_name": "vip_CP",
           "cluster_fip_name": "vip_CP_floating_ip"
         },
         "worker_node": {
           "vdu_id": "workerNode",
           "ssh_cp_name": "workerNode_CP1_floating_ip",
           "nic_cp_name": "workerNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu"
         }
      },
      "lcm-operation-user-data": "./UserData/userdata_standard.py",
      "lcm-operation-user-data-class": "StandardUserData"
    }
  }


Perform Heal operation on the MasterNode's VNFC
(masterNode-90091dbb-1047-4207-8394-114bd3a3aec9).

.. code-block:: console

  $ openstack vnflcm heal 14c5406b-f627-4391-b91b-440f242623ac --vnfc-instance masterNode-90091dbb-1047-4207-8394-114bd3a3aec9 --additional-param-file complex_additional_params_req --os-tacker-api-version 2
  Heal request for VNF Instance 14c5406b-f627-4391-b91b-440f242623ac has been accepted.


Check after Operation
~~~~~~~~~~~~~~~~~~~~~

After the Status of LCM operation is COMPLETE, check the VNF instance and
Kubernetes cluster.

.. code-block:: console

  $ openstack server list
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+
  | ID                                   | Name       | Status | Networks                       | Image            | Flavor    |
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+
  | adfc3350-6473-4ed1-9a19-f75ddf0c2169 | masterNode | ACTIVE | net0=10.10.0.153, 172.24.4.107 | masterNode-image | m1.medium |
  | 20ee4d5b-e51f-4e6b-a400-47bfabd48f59 | masterNode | ACTIVE | net0=10.10.0.15, 172.24.4.156  | masterNode-image | m1.medium |
  | c20645b0-d5b3-4341-bbf2-31528976e760 | masterNode | ACTIVE | net0=10.10.0.219, 172.24.4.140 | masterNode-image | m1.medium |
  | 2cbfaab9-1be9-42c8-be67-ee83083c8e1f | workerNode | ACTIVE | net0=10.10.0.45, 172.24.4.186  | workerNode-image | m1.medium |
  | 355d2203-0952-4f1a-aa71-340d6a5a893f | workerNode | ACTIVE | net0=10.10.0.86, 172.24.4.26   | workerNode-image | m1.medium |
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+

.. code-block:: console

  $ openstack vnflcm show 14c5406b-f627-4391-b91b-440f242623ac --os-tacker-api-version 2
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                                  |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | ID                          | 14c5406b-f627-4391-b91b-440f242623ac                                                                                                   |
  | Instantiated Vnf Info       | {                                                                                                                                      |
  |                             |     "flavourId": "complex",                                                                                                            |
  |                             |     "vnfState": "STARTED",                                                                                                             |
  |                             |     "scaleStatus": [                                                                                                                   |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 0                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "maxScaleLevels": [                                                                                                                |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 2                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extCpInfo": [                                                                                                                     |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-20ee4d5b-e51f-4e6b-a400-47bfabd48f59"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-2f6135f3-7981-4e31-b19c-c7fe84e5af86",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "2f6135f3-7981-4e31-b19c-c7fe84e5af86",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-2cbfaab9-1be9-42c8-be67-ee83083c8e1f"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-adfc3350-6473-4ed1-9a19-f75ddf0c2169"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-049181f6-3df6-4e8c-a518-2954d5ba707e",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "049181f6-3df6-4e8c-a518-2954d5ba707e",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-355d2203-0952-4f1a-aa71-340d6a5a893f"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-adf6941b-56a5-47af-a590-3d7a8d20c6dc",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "adf6941b-56a5-47af-a590-3d7a8d20c6dc",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-c20645b0-d5b3-4341-bbf2-31528976e760"                                                |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extVirtualLinkInfo": [                                                                                                            |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_master",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "adf6941b-56a5-47af-a590-3d7a8d20c6dc",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "adf6941b-56a5-47af-a590-3d7a8d20c6dc",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-adf6941b-56a5-47af-a590-3d7a8d20c6dc"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "Master_CP1": {                                                                                                |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_worker",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "2f6135f3-7981-4e31-b19c-c7fe84e5af86",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "2f6135f3-7981-4e31-b19c-c7fe84e5af86",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-2f6135f3-7981-4e31-b19c-c7fe84e5af86"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "049181f6-3df6-4e8c-a518-2954d5ba707e",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "049181f6-3df6-4e8c-a518-2954d5ba707e",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-049181f6-3df6-4e8c-a518-2954d5ba707e"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "WorkerCP1": {                                                                                                 |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcResourceInfo": [                                                                                                              |
  |                             |         {                                                                                                                              |
  |                             |             "id": "c20645b0-d5b3-4341-bbf2-31528976e760",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "c20645b0-d5b3-4341-bbf2-31528976e760",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-c20645b0-d5b3-4341-bbf2-31528976e760",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-adf6941b-56a5-47af-a590-3d7a8d20c6dc"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:14Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-2-jdclzcogomqy/756fee55-4478-4a1d-a420-1695943bf24a", |
  |                             |                 "vdu_idx": 2,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-2": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "adfc3350-6473-4ed1-9a19-f75ddf0c2169",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "adfc3350-6473-4ed1-9a19-f75ddf0c2169",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-adfc3350-6473-4ed1-9a19-f75ddf0c2169",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-b1182a3e-b1c4-43aa-bc21-61f8ae5e1fb0"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T04:41:50Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-1-ewevxjfpa5du/6c93f15d-0e1c-419a-82a6-dc0daa8d254c", |
  |                             |                 "vdu_idx": 1,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-1": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-2f6135f3-7981-4e31-b19c-c7fe84e5af86"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:13Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-1-25n3lsnj6kop/e03f90f6-750e-4e86-8f56-fec0f9e8e28b", |
  |                             |                 "vdu_idx": 1,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-1": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-905d8b08-0fb0-4ae3-b2a4-5acaf03cb46e"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:14Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-0-kkckwhq5raf2/efa4697a-7c98-408e-afa8-aece3c5bb42d", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-0": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "355d2203-0952-4f1a-aa71-340d6a5a893f",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "355d2203-0952-4f1a-aa71-340d6a5a893f",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-355d2203-0952-4f1a-aa71-340d6a5a893f",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-049181f6-3df6-4e8c-a518-2954d5ba707e"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T02:03:13Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-0-hwuihryx6ik4/abd2ea60-5b70-4787-959f-3dece676cc00", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-0": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcInfo": [                                                                                                                      |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-c20645b0-d5b3-4341-bbf2-31528976e760",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "c20645b0-d5b3-4341-bbf2-31528976e760",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-adfc3350-6473-4ed1-9a19-f75ddf0c2169",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "adfc3350-6473-4ed1-9a19-f75ddf0c2169",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "2cbfaab9-1be9-42c8-be67-ee83083c8e1f",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "20ee4d5b-e51f-4e6b-a400-47bfabd48f59",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-355d2203-0952-4f1a-aa71-340d6a5a893f",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "355d2203-0952-4f1a-aa71-340d6a5a893f",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "metadata": {                                                                                                                      |
  |                             |         "stack_id": "642dbe88-1cda-4cf4-af9f-f81d53f10232",                                                                            |
  |                             |         "nfv": {                                                                                                                       |
  |                             |             "VDU": {                                                                                                                   |
  |                             |                 "masterNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode-1": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode-2": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-1": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-2": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                                |
  |                             |                 }                                                                                                                      |
  |                             |             },                                                                                                                         |
  |                             |             "CP": {                                                                                                                    |
  |                             |                 "masterNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode_CP1-1": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode_CP1-2": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-1": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-2": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         "tenant": "nfv"                                                                                                                |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | Instantiation State         | INSTANTIATED                                                                                                                           |
  | Links                       | {                                                                                                                                      |
  |                             |     "self": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac"                                   |
  |                             |     },                                                                                                                                 |
  |                             |     "terminate": {                                                                                                                     |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/terminate"                         |
  |                             |     },                                                                                                                                 |
  |                             |     "scale": {                                                                                                                         |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/scale"                             |
  |                             |     },                                                                                                                                 |
  |                             |     "heal": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/heal"                              |
  |                             |     },                                                                                                                                 |
  |                             |     "changeExtConn": {                                                                                                                 |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/change_ext_conn"                   |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VIM Connection Info         | {                                                                                                                                      |
  |                             |     "vim1": {                                                                                                                          |
  |                             |         "vimId": "d82ee798-a1d2-4854-8f74-4892ad706751",                                                                               |
  |                             |         "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",                                                                                   |
  |                             |         "interfaceInfo": {                                                                                                             |
  |                             |             "endpoint": "http://localhost/identity/v3"                                                                                 |
  |                             |         },                                                                                                                             |
  |                             |         "accessInfo": {                                                                                                                |
  |                             |             "region": "RegionOne",                                                                                                     |
  |                             |             "project": "nfv",                                                                                                          |
  |                             |             "username": "nfv_user",                                                                                                    |
  |                             |             "userDomain": "Default",                                                                                                   |
  |                             |             "projectDomain": "Default"                                                                                                 |
  |                             |         }                                                                                                                              |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VNF Configurable Properties |                                                                                                                                        |
  | VNF Instance Description    | v2-kubernetes-sample                                                                                                                   |
  | VNF Instance Name           | v2-kubernetes-sample                                                                                                                   |
  | VNF Product Name            | Sample VNF                                                                                                                             |
  | VNF Provider                | Company                                                                                                                                |
  | VNF Software Version        | 1.0                                                                                                                                    |
  | VNFD ID                     | d34ac189-5376-493f-828f-224dd5fe7393                                                                                                   |
  | VNFD Version                | 1.0                                                                                                                                    |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+


Log in to any one of the MasterNodes via SSH and check the Nodes in the
Kubernetes cluster. Confirm that the STATUS of the recreated Node(master153)
is Ready.

.. code-block:: console

  ubuntu@master15:~$ kubectl get node -o wide
  NAME        STATUS   ROLES           AGE     VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION       CONTAINER-RUNTIME
  master15    Ready    control-plane   153m    v1.26.8   10.10.0.15    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  master153   Ready    control-plane   6m43s   v1.26.8   10.10.0.153   <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  master219   Ready    control-plane   163m    v1.26.8   10.10.0.219   <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker45    Ready    <none>          151m    v1.26.8   10.10.0.45    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker86    Ready    <none>          148m    v1.26.8   10.10.0.86    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11


You also check if cilium is ready.

.. code-block:: console

  ubuntu@master15:~$ cilium status
      /￣￣\
   /￣￣\__/￣￣\    Cilium:             OK
   \__/￣￣\__/    Operator:           OK
   /￣￣\__/￣￣\    Envoy DaemonSet:    disabled (using embedded mode)
   \__/￣￣\__/    Hubble Relay:       disabled
      \__/       ClusterMesh:        disabled

  Deployment             cilium-operator    Desired: 1, Ready: 1/1, Available: 1/1
  DaemonSet              cilium             Desired: 5, Ready: 5/5, Available: 5/5
  Containers:            cilium-operator    Running: 1
                         cilium             Running: 5
  Cluster Pods:          2/2 managed by Cilium
  Helm chart version:
  Image versions         cilium             quay.io/cilium/cilium:v1.14.5@sha256:d3b287029755b6a47dee01420e2ea469469f1b174a2089c10af7e5e9289ef05b: 5
                         cilium-operator    quay.io/cilium/operator-generic:v1.14.5@sha256:303f9076bdc73b3fc32aaedee64a14f6f44c8bb08ee9e3956d443021103ebe7a: 1



Heal VNF
~~~~~~~~

Perform entire VNF heal operations.
Add the parameter "all: true" to the additionalParams of the heal that
specifies the VNFC.

.. code-block::

  {
    "additionalParams": {
      "all": true,
      "k8s_cluster_installation_param": {
         "script_path": "Scripts/install_k8s_cluster.sh",
         "master_node": {
           "vdu_id": "masterNode",
           "ssh_cp_name": "masterNode_CP1_floating_ip",
           "nic_cp_name": "masterNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu",
           "pod_cidr": "10.200.0.0/16",
           "cluster_cp_name": "vip_CP",
           "cluster_fip_name": "vip_CP_floating_ip"
         },
         "worker_node": {
           "vdu_id": "workerNode",
           "ssh_cp_name": "workerNode_CP1_floating_ip",
           "nic_cp_name": "workerNode_CP1",
           "username": "ubuntu",
           "password": "ubuntu"
         }
      },
      "lcm-operation-user-data": "./UserData/userdata_standard.py",
      "lcm-operation-user-data-class": "StandardUserData"
    }
  }


Confirm stack id before heal.

.. code-block:: console

  $ openstack stack list
  +------------------------------------+------------------------------------+----------------------------------+-----------------+----------------------+----------------------+
  | ID                                 | Stack Name                         | Project                          | Stack Status    | Creation Time        | Updated Time         |
  +------------------------------------+------------------------------------+----------------------------------+-----------------+----------------------+----------------------+
  | 642dbe88-1cda-4cf4-af9f-           | vnf-14c5406b-f627-4391-b91b-       | 5d711196514b4f11b02382403b3342a9 | UPDATE_COMPLETE | 2024-04-17T02:03:11Z | 2024-04-17T04:41:17Z |
  | f81d53f10232                       | 440f242623ac                       |                                  |                 |                      |                      |
  +------------------------------------+------------------------------------+----------------------------------+-----------------+----------------------+----------------------+


Perform Heal operation.

.. code-block:: console

  $ openstack vnflcm heal 14c5406b-f627-4391-b91b-440f242623ac --additional-param-file complex_additional_params_req --os-tacker-api-version 2
  Heal request for VNF Instance 14c5406b-f627-4391-b91b-440f242623ac has been accepted.


Check after Operation
~~~~~~~~~~~~~~~~~~~~~

After the Status of LCM operation is COMPLETE, check the VNF instance and
Kubernetes cluster.


.. code-block:: console

  $ openstack stack list
  +--------------------------------------+------------------------------------------+----------------------------------+-----------------+----------------------+--------------+
  | ID                                   | Stack Name                               | Project                          | Stack Status    | Creation Time        | Updated Time |
  +--------------------------------------+------------------------------------------+----------------------------------+-----------------+----------------------+--------------+
  | 4e79d3dd-056d-4e29-8c46-ca761c8742d4 | vnf-14c5406b-f627-4391-b91b-440f242623ac | 5d711196514b4f11b02382403b3342a9 | CREATE_COMPLETE | 2024-04-17T05:19:21Z | None         |
  +--------------------------------------+------------------------------------------+----------------------------------+-----------------+----------------------+--------------+


.. code-block:: console

  $ openstack vnflcm show 14c5406b-f627-4391-b91b-440f242623ac --os-tacker-api-version 2
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                                  |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+
  | ID                          | 14c5406b-f627-4391-b91b-440f242623ac                                                                                                   |
  | Instantiated Vnf Info       | {                                                                                                                                      |
  |                             |     "flavourId": "complex",                                                                                                            |
  |                             |     "vnfState": "STARTED",                                                                                                             |
  |                             |     "scaleStatus": [                                                                                                                   |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 0                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "maxScaleLevels": [                                                                                                                |
  |                             |         {                                                                                                                              |
  |                             |             "aspectId": "workerNode_scale",                                                                                            |
  |                             |             "scaleLevel": 2                                                                                                            |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extCpInfo": [                                                                                                                     |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-60192796-6190-475a-b50b-b024883bf9e1",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "60192796-6190-475a-b50b-b024883bf9e1",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-b7480ecf-d523-47a8-8218-8a9a751d98fc"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-83f43a69-d1db-4e5e-91c4-b5f026a28890",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "83f43a69-d1db-4e5e-91c4-b5f026a28890",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-28ec6f59-f7c2-448c-b657-3a59b2f70c01"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-7612c547-5daa-4468-8e1c-cd23a47e7f48",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "7612c547-5daa-4468-8e1c-cd23a47e7f48",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-79234b92-b9d3-4e54-934b-c7b44d14c09b"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-54a2b4bd-3c60-4deb-a54f-f619d4cb81ac",                                                                           |
  |                             |             "cpdId": "workerNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "WorkerCP1",                                                                                                 |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "54a2b4bd-3c60-4deb-a54f-f619d4cb81ac",                                                                   |
  |                             |             "associatedVnfcCpId": "workerNode_CP1-97ffdbe6-08b4-49f6-b6d8-2b2df8df1738"                                                |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "cp-59dd29f0-6fa6-48d5-b6be-7c7d2d77e58a",                                                                           |
  |                             |             "cpdId": "masterNode_CP1",                                                                                                 |
  |                             |             "cpConfigId": "Master_CP1",                                                                                                |
  |                             |             "cpProtocolInfo": [                                                                                                        |
  |                             |                 {                                                                                                                      |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                                               |
  |                             |                     "ipOverEthernet": {                                                                                                |
  |                             |                         "ipAddresses": [                                                                                               |
  |                             |                             {                                                                                                          |
  |                             |                                 "type": "IPV4",                                                                                        |
  |                             |                                 "isDynamic": true                                                                                      |
  |                             |                             }                                                                                                          |
  |                             |                         ]                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "extLinkPortId": "59dd29f0-6fa6-48d5-b6be-7c7d2d77e58a",                                                                   |
  |                             |             "associatedVnfcCpId": "masterNode_CP1-219d4495-2504-43c8-97b2-aba3e9bf03d8"                                                |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "extVirtualLinkInfo": [                                                                                                            |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_master",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "60192796-6190-475a-b50b-b024883bf9e1",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "60192796-6190-475a-b50b-b024883bf9e1",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-60192796-6190-475a-b50b-b024883bf9e1"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "7612c547-5daa-4468-8e1c-cd23a47e7f48",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "7612c547-5daa-4468-8e1c-cd23a47e7f48",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-7612c547-5daa-4468-8e1c-cd23a47e7f48"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "59dd29f0-6fa6-48d5-b6be-7c7d2d77e58a",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "59dd29f0-6fa6-48d5-b6be-7c7d2d77e58a",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-59dd29f0-6fa6-48d5-b6be-7c7d2d77e58a"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "Master_CP1": {                                                                                                |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "net0_worker",                                                                                                       |
  |                             |             "resourceHandle": {                                                                                                        |
  |                             |                 "resourceId": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                   |
  |                             |             },                                                                                                                         |
  |                             |             "extLinkPorts": [                                                                                                          |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "83f43a69-d1db-4e5e-91c4-b5f026a28890",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "83f43a69-d1db-4e5e-91c4-b5f026a28890",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-83f43a69-d1db-4e5e-91c4-b5f026a28890"                                                          |
  |                             |                 },                                                                                                                     |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "54a2b4bd-3c60-4deb-a54f-f619d4cb81ac",                                                                      |
  |                             |                     "resourceHandle": {                                                                                                |
  |                             |                         "vimConnectionId": "vim1",                                                                                     |
  |                             |                         "resourceId": "54a2b4bd-3c60-4deb-a54f-f619d4cb81ac",                                                          |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                                    |
  |                             |                     },                                                                                                                 |
  |                             |                     "cpInstanceId": "cp-54a2b4bd-3c60-4deb-a54f-f619d4cb81ac"                                                          |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "currentVnfExtCpData": [                                                                                                   |
  |                             |                 {                                                                                                                      |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "cpConfig": {                                                                                                      |
  |                             |                         "WorkerCP1": {                                                                                                 |
  |                             |                             "cpProtocolData": [                                                                                        |
  |                             |                                 {                                                                                                      |
  |                             |                                     "layerProtocol": "IP_OVER_ETHERNET",                                                               |
  |                             |                                     "ipOverEthernet": {                                                                                |
  |                             |                                         "ipAddresses": [                                                                               |
  |                             |                                             {                                                                                          |
  |                             |                                                 "type": "IPV4",                                                                        |
  |                             |                                                 "numDynamicAddresses": 1                                                               |
  |                             |                                             }                                                                                          |
  |                             |                                         ]                                                                                              |
  |                             |                                     }                                                                                                  |
  |                             |                                 }                                                                                                      |
  |                             |                             ]                                                                                                          |
  |                             |                         }                                                                                                              |
  |                             |                     }                                                                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             ]                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcResourceInfo": [                                                                                                              |
  |                             |         {                                                                                                                              |
  |                             |             "id": "219d4495-2504-43c8-97b2-aba3e9bf03d8",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "219d4495-2504-43c8-97b2-aba3e9bf03d8",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-219d4495-2504-43c8-97b2-aba3e9bf03d8",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-59dd29f0-6fa6-48d5-b6be-7c7d2d77e58a"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T05:19:23Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-2-diif2hix6tcb/f7618b77-b73b-42b0-8843-edc373096ba5", |
  |                             |                 "vdu_idx": 2,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-2": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "28ec6f59-f7c2-448c-b657-3a59b2f70c01",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "28ec6f59-f7c2-448c-b657-3a59b2f70c01",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-28ec6f59-f7c2-448c-b657-3a59b2f70c01",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-83f43a69-d1db-4e5e-91c4-b5f026a28890"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T05:19:24Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-1-puf5bud7yaum/decf9a9b-2a61-4bb7-a0da-e15de8a6c354", |
  |                             |                 "vdu_idx": 1,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-1": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "79234b92-b9d3-4e54-934b-c7b44d14c09b",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "79234b92-b9d3-4e54-934b-c7b44d14c09b",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-79234b92-b9d3-4e54-934b-c7b44d14c09b",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-7612c547-5daa-4468-8e1c-cd23a47e7f48"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T05:19:23Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-1-j6smubvqvj4h/4a74507e-9333-47f0-bc20-c8aba4717ec1", |
  |                             |                 "vdu_idx": 1,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-1": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "97ffdbe6-08b4-49f6-b6d8-2b2df8df1738",                                                                              |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "97ffdbe6-08b4-49f6-b6d8-2b2df8df1738",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "workerNode_CP1-97ffdbe6-08b4-49f6-b6d8-2b2df8df1738",                                                       |
  |                             |                     "cpdId": "workerNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-54a2b4bd-3c60-4deb-a54f-f619d4cb81ac"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T05:19:24Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-workerNode-0-b6keccs6q253/1ebb1822-846f-46f8-9add-f20bc5aeb4f3", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-workerNode-0": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "b7480ecf-d523-47a8-8218-8a9a751d98fc",                                                                              |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "computeResource": {                                                                                                       |
  |                             |                 "vimConnectionId": "vim1",                                                                                             |
  |                             |                 "resourceId": "b7480ecf-d523-47a8-8218-8a9a751d98fc",                                                                  |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                             |
  |                             |             },                                                                                                                         |
  |                             |             "vnfcCpInfo": [                                                                                                            |
  |                             |                 {                                                                                                                      |
  |                             |                     "id": "masterNode_CP1-b7480ecf-d523-47a8-8218-8a9a751d98fc",                                                       |
  |                             |                     "cpdId": "masterNode_CP1",                                                                                         |
  |                             |                     "vnfExtCpId": "cp-60192796-6190-475a-b50b-b024883bf9e1"                                                            |
  |                             |                 }                                                                                                                      |
  |                             |             ],                                                                                                                         |
  |                             |             "metadata": {                                                                                                              |
  |                             |                 "creation_time": "2024-04-17T05:19:23Z",                                                                               |
  |                             |                 "stack_id": "vnf-14c5406b-f627-4391-b91b-440f242623ac-masterNode-0-z5bwuon4iw54/4e0ea4af-7ac9-4616-b490-d83e75edcbd1", |
  |                             |                 "vdu_idx": 0,                                                                                                          |
  |                             |                 "flavor": "m1.medium",                                                                                                 |
  |                             |                 "image-masterNode-0": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                           |
  |                             |             }                                                                                                                          |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "vnfcInfo": [                                                                                                                      |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-219d4495-2504-43c8-97b2-aba3e9bf03d8",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "219d4495-2504-43c8-97b2-aba3e9bf03d8",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-28ec6f59-f7c2-448c-b657-3a59b2f70c01",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "28ec6f59-f7c2-448c-b657-3a59b2f70c01",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-79234b92-b9d3-4e54-934b-c7b44d14c09b",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "79234b92-b9d3-4e54-934b-c7b44d14c09b",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "workerNode-97ffdbe6-08b4-49f6-b6d8-2b2df8df1738",                                                                   |
  |                             |             "vduId": "workerNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "97ffdbe6-08b4-49f6-b6d8-2b2df8df1738",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         },                                                                                                                             |
  |                             |         {                                                                                                                              |
  |                             |             "id": "masterNode-b7480ecf-d523-47a8-8218-8a9a751d98fc",                                                                   |
  |                             |             "vduId": "masterNode",                                                                                                     |
  |                             |             "vnfcResourceInfoId": "b7480ecf-d523-47a8-8218-8a9a751d98fc",                                                              |
  |                             |             "vnfcState": "STARTED"                                                                                                     |
  |                             |         }                                                                                                                              |
  |                             |     ],                                                                                                                                 |
  |                             |     "metadata": {                                                                                                                      |
  |                             |         "stack_id": "4e79d3dd-056d-4e29-8c46-ca761c8742d4",                                                                            |
  |                             |         "nfv": {                                                                                                                       |
  |                             |             "VDU": {                                                                                                                   |
  |                             |                 "masterNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode-1": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode-2": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "dff49249-bdb1-404e-be3c-f6387ba35ca0"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-0": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-1": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                                |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode-2": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.medium",                                                                                   |
  |                             |                     "vcImageId": "7aba8d56-78df-42fb-baee-9aa53dabdc89"                                                                |
  |                             |                 }                                                                                                                      |
  |                             |             },                                                                                                                         |
  |                             |             "CP": {                                                                                                                    |
  |                             |                 "masterNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode_CP1-1": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "masterNode_CP1-2": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-0": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-1": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 },                                                                                                                     |
  |                             |                 "workerNode_CP1-2": {                                                                                                  |
  |                             |                     "network": "bbc012e1-6619-4fe6-aaac-0668a4974313"                                                                  |
  |                             |                 }                                                                                                                      |
  |                             |             }                                                                                                                          |
  |                             |         },                                                                                                                             |
  |                             |         "tenant": "nfv"                                                                                                                |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | Instantiation State         | INSTANTIATED                                                                                                                           |
  | Links                       | {                                                                                                                                      |
  |                             |     "self": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac"                                   |
  |                             |     },                                                                                                                                 |
  |                             |     "terminate": {                                                                                                                     |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/terminate"                         |
  |                             |     },                                                                                                                                 |
  |                             |     "scale": {                                                                                                                         |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/scale"                             |
  |                             |     },                                                                                                                                 |
  |                             |     "heal": {                                                                                                                          |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/heal"                              |
  |                             |     },                                                                                                                                 |
  |                             |     "changeExtConn": {                                                                                                                 |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/14c5406b-f627-4391-b91b-440f242623ac/change_ext_conn"                   |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VIM Connection Info         | {                                                                                                                                      |
  |                             |     "vim1": {                                                                                                                          |
  |                             |         "vimId": "d82ee798-a1d2-4854-8f74-4892ad706751",                                                                               |
  |                             |         "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",                                                                                   |
  |                             |         "interfaceInfo": {                                                                                                             |
  |                             |             "endpoint": "http://localhost/identity/v3"                                                                                 |
  |                             |         },                                                                                                                             |
  |                             |         "accessInfo": {                                                                                                                |
  |                             |             "region": "RegionOne",                                                                                                     |
  |                             |             "project": "nfv",                                                                                                          |
  |                             |             "username": "nfv_user",                                                                                                    |
  |                             |             "userDomain": "Default",                                                                                                   |
  |                             |             "projectDomain": "Default"                                                                                                 |
  |                             |         }                                                                                                                              |
  |                             |     }                                                                                                                                  |
  |                             | }                                                                                                                                      |
  | VNF Configurable Properties |                                                                                                                                        |
  | VNF Instance Description    | v2-kubernetes-sample                                                                                                                   |
  | VNF Instance Name           | v2-kubernetes-sample                                                                                                                   |
  | VNF Product Name            | Sample VNF                                                                                                                             |
  | VNF Provider                | Company                                                                                                                                |
  | VNF Software Version        | 1.0                                                                                                                                    |
  | VNFD ID                     | d34ac189-5376-493f-828f-224dd5fe7393                                                                                                   |
  | VNFD Version                | 1.0                                                                                                                                    |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------+


Verify that all VMs are recreated.

.. code-block:: console

  $ openstack server list
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+
  | ID                                   | Name       | Status | Networks                       | Image            | Flavor    |
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+
  | 28ec6f59-f7c2-448c-b657-3a59b2f70c01 | workerNode | ACTIVE | net0=10.10.0.34, 172.24.4.169  | workerNode-image | m1.medium |
  | 219d4495-2504-43c8-97b2-aba3e9bf03d8 | masterNode | ACTIVE | net0=10.10.0.54, 172.24.4.239  | masterNode-image | m1.medium |
  | 79234b92-b9d3-4e54-934b-c7b44d14c09b | masterNode | ACTIVE | net0=10.10.0.172, 172.24.4.179 | masterNode-image | m1.medium |
  | 97ffdbe6-08b4-49f6-b6d8-2b2df8df1738 | workerNode | ACTIVE | net0=10.10.0.163, 172.24.4.33  | workerNode-image | m1.medium |
  | b7480ecf-d523-47a8-8218-8a9a751d98fc | masterNode | ACTIVE | net0=10.10.0.89, 172.24.4.64   | masterNode-image | m1.medium |
  +--------------------------------------+------------+--------+--------------------------------+------------------+-----------+


Login to the MasterNode via SSH and check the Node of the Kubernetes cluster.
Verify that all VMs are in the cluster and that the STATUS of the Node is
Ready.

.. code-block:: console

  ubuntu@master15:~$ kubectl get node -o wide
  NAME        STATUS   ROLES           AGE    VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION       CONTAINER-RUNTIME
  master172   Ready    control-plane   17m    v1.26.8   10.10.0.172   <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  master15    Ready    control-plane   23m    v1.26.8   10.10.0.54    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  master89    Ready    control-plane   13m    v1.26.8   10.10.0.89    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker163   Ready    <none>          8m8s   v1.26.8   10.10.0.163   <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11
  worker34    Ready    <none>          10m    v1.26.8   10.10.0.34    <none>        Ubuntu 22.04.4 LTS   5.15.0-101-generic   containerd://1.7.11


You also check if cilium is ready.

.. code-block:: console

  ubuntu@master15:~$ cilium status
      /￣￣\
   /￣￣\__/￣￣\    Cilium:             OK
   \__/￣￣\__/    Operator:           OK
   /￣￣\__/￣￣\    Envoy DaemonSet:    disabled (using embedded mode)
   \__/￣￣\__/    Hubble Relay:       disabled
      \__/       ClusterMesh:        disabled

  Deployment             cilium-operator    Desired: 1, Ready: 1/1, Available: 1/1
  DaemonSet              cilium             Desired: 5, Ready: 5/5, Available: 5/5
  Containers:            cilium             Running: 5
                         cilium-operator    Running: 1
  Cluster Pods:          2/2 managed by Cilium
  Helm chart version:
  Image versions         cilium             quay.io/cilium/cilium:v1.14.5@sha256:d3b287029755b6a47dee01420e2ea469469f1b174a2089c10af7e5e9289ef05b: 5
                         cilium-operator    quay.io/cilium/operator-generic:v1.14.5@sha256:303f9076bdc73b3fc32aaedee64a14f6f44c8bb08ee9e3956d443021103ebe7a: 1
