===============================================================================
How to use Mgmt Driver for deploying Kubernetes Cluster with Private Registries
===============================================================================

Overview
--------
It is supported downloading image files from Docker public registry
in the Kubernetes Cluster built with the user guide
`How to use Mgmt Driver for deploying Kubernetes Cluster`_,
but not supported from Docker private registry. In this user guide,
we provide a way to support the use of Docker private registry for
Kubernetes cluster. The Docker private registry can either be created
in the Tacker or created outside. If you want to use Tacker to create
a Docker private registry, we provide a sample user script run by
Mgmt Driver to install a Docker private registry. You can refer to
chapter :ref:`Install Docker Private Registry` for this usage.
If you want to use a private registry created outside of the tacker,
please create it and then add the configuration of your private
registry into the parameters of instantiation request body of Kubernetes
cluster.

.. _Install Docker Private Registry:

Install Docker Private Registry
-------------------------------
1. Preparations
^^^^^^^^^^^^^^^
The preparations of installing Docker private registry is the same as
the one in `How to use Mgmt Driver for deploying Kubernetes Cluster`_.
You can refer to it for how to set OpenStack configuration, how to
download ubuntu image and how to register Mgmt Driver and usage of VNF
Package.

The sample structure of VNF Package is shown below.

.. note::

    You can also find them in the
    `samples/mgmt_driver/kubernetes/private_registry_vnf_package/`_
    directory of the tacker.

The directory structure:

* **TOSCA-Metadata/TOSCA.meta**
* **Definitions/**
* **Files/images/**
* **Scripts/**

.. code-block:: console

  !----TOSCA-Metadata
          !---- TOSCA.meta
  !----Definitions
          !---- etsi_nfv_sol001_common_types.yaml
          !---- etsi_nfv_sol001_vnfd_types.yaml
          !---- sample_vnfd_df_simple.yaml
          !---- sample_vnfd_top.yaml
          !---- sample_vnfd_types.yaml
  !----Files
          !---- images
                  !---- ubuntu-20.04-server-cloudimg-amd64.img
  !----Scripts
          !---- private_registry_mgmt.py

2. Deploy Docker Private Registry VNF
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Docker private registry can be installed and set up in
``instantiate_end`` operation, which allows you to execute any
scripts after its instantiation, and it's enabled with Mgmt Driver
support.

You must create the parameter file which is used to instantiate
correctly. The following are the methods of creating the parameter
file and CLI commands of OpenStack.

1. Create the Parameter File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a ``private_registry_param_file.json`` file with the following format.
This is the file that defines the parameters for an instantiate request.
These parameters will be set in the body of the instantiate request.

Required parameter:

* flavourId
* additionalParams

Optional parameters:

* instantiationLevelId
* extVirtualLinks
* extManagedVirtualLinks
* vimConnectionInfo

In this guide, the VMs need to have extCPs to be accessed via SSH by Tacker.
Therefore, ``extVirtualLinks`` parameter is required. You can skip
``vimConnectionInfo`` only when you have the default VIM described in
`cli-legacy-vim`_.

**Explanation of the parameters for deploying Docker private registry VNF**

For deploying Docker private registry VNF, you must set the
``private_registry_installation_param`` key in additionalParams.
The KeyValuePairs is shown in table below:

.. list-table:: **List of additionalParams.private_registry_installation_param(specified by user)**
   :widths: 10 10 25 10
   :header-rows: 1

   * - parameter
     - data type
     - description
     - required/optional
   * - ssh_cp_name
     - string
     - CP name that MgmtDriver uses when SSH/SFTP access to
       the Private Registry VM.
     - required
   * - ssh_username
     - string
     - User name that MgmtDriver uses when SSH/SFTP access
       to the Private Registry VM.
     - required
   * - ssh_password
     - string
     - User password that MgmtDriver uses when SSH/SFTP
       access to the Private Registry VM.
     - required
   * - image_path
     - string
     - Path of the Docker image file in the VNF Package for the
       Private Registry container to run on Docker. If this attribute
       is omitted, the image for the Private Registry container is
       pulled from the Docker public registry. If the Private Registry
       VM is unable to connect to the Docker public registry, put
       the file created using "docker save" command into the VNF
       Package and specify the path of the file in this attribute.
     - optional
   * - port_no
     - string
     - The default value is 5000. TCP port number provides the
       private registry service.
     - optional
   * - proxy
     - dict
     - Information for proxy setting on VM
     - optional

.. list-table:: **proxy dict**
   :widths: 10 10 25 10
   :header-rows: 1

   * - parameter
     - data type
     - description
     - required/optional
   * - http_proxy
     - string
     - Http proxy server address
     - optional
   * - https_proxy
     - string
     - Https proxy server address
     - optional
   * - no_proxy
     - string
     - User-customized, proxy server-free IP address or segment
     - optional

private_registry_param_file.json

.. code-block::


    {
        "flavourId": "simple",
        "extVirtualLinks": [{
            "id": "net0",
            "resourceId": "f0c82461-36b5-4d86-8322-b0bc19cda65f", #Set the uuid of the network to use
            "extCps": [{
                "cpdId": "CP1",
                "cpConfig": [{
                    "cpProtocolData": [{
                        "layerProtocol": "IP_OVER_ETHERNET"
                    }]
                }]
            }]
        }],
        "additionalParams": {
            "private_registry_installation_param": {
                "ssh_cp_name": "CP1",
                "ssh_username": "ubuntu",
                "ssh_password": "ubuntu",
                "proxy": {
                    "http_proxy": "http://user1:password1@host1:port1",
                    "https_proxy": "https://user2:password2@host2:port2",
                    "no_proxy": "192.168.246.0/24,10.0.0.1"
                }
            }
        },
        "vimConnectionInfo": [{
            "id": "8a3adb69-0784-43c7-833e-aab0b6ab4470",
            "vimId": "8d8373fe-6977-49ff-83ac-7756572ed186", #Set the uuid of the VIM to use
            "vimType": "openstack"
        }]
    }


2. Execute the Instantiation Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute the following CLI command to instantiate the VNF instance.

Create VNF with VNFD ID:

.. code-block:: console

    $ openstack vnflcm create c1bb0ce7-ebca-4fa7-95ed-4840d70a118f
    +--------------------------+---------------------------------------------------------------------------------------------+
    | Field                    | Value                                                                                       |
    +--------------------------+---------------------------------------------------------------------------------------------+
    | ID                       | f93ed99c-e2f2-4f18-8377-37a171ea344f                                                        |
    | Instantiation State      | NOT_INSTANTIATED                                                                            |
    | Links                    | {                                                                                           |
    |                          |     "self": {                                                                               |
    |                          |         "href": "/vnflcm/v1/vnf_instances/f93ed99c-e2f2-4f18-8377-37a171ea344f"             |
    |                          |     },                                                                                      |
    |                          |     "instantiate": {                                                                        |
    |                          |         "href": "/vnflcm/v1/vnf_instances/f93ed99c-e2f2-4f18-8377-37a171ea344f/instantiate" |
    |                          |     }                                                                                       |
    |                          | }                                                                                           |
    | VNF Instance Description | None                                                                                        |
    | VNF Instance Name        | vnf-f93ed99c-e2f2-4f18-8377-37a171ea344f                                                    |
    | VNF Product Name         | Sample Private registry VNF                                                                 |
    | VNF Provider             | Company                                                                                     |
    | VNF Software Version     | 1.0                                                                                         |
    | VNFD ID                  | c1bb0ce7-ebca-4fa7-95ed-4840d70a118f                                                        |
    | VNFD Version             | 1.0                                                                                         |
    | vnfPkgId                 |                                                                                             |
    +--------------------------+---------------------------------------------------------------------------------------------+

Instantiate VNF with VNF ID:

.. code-block:: console

    $ openstack vnflcm instantiate f93ed99c-e2f2-4f18-8377-37a171ea344f ./private_registry_param_file.json
    Instantiate request for VNF Instance f93ed99c-e2f2-4f18-8377-37a171ea344f has been accepted.

Check instantiation state:

.. code-block:: console

    $ openstack vnflcm show f93ed99c-e2f2-4f18-8377-37a171ea344f
    +--------------------------+-------------------------------------------------------------------------------------------------+
    | Field                    | Value                                                                                           |
    +--------------------------+-------------------------------------------------------------------------------------------------+
    | ID                       | f93ed99c-e2f2-4f18-8377-37a171ea344f                                                            |
    | Instantiated Vnf Info    | {                                                                                               |
    |                          |     "flavourId": "simple",                                                                      |
    |                          |     "vnfState": "STARTED",                                                                      |
    |                          |     "extCpInfo": [                                                                              |
    |                          |         {                                                                                       |
    |                          |             "id": "187cc96a-7577-4156-8b0a-efcda82d56fc",                                       |
    |                          |             "cpdId": "CP1",                                                                     |
    |                          |             "extLinkPortId": null,                                                              |
    |                          |             "associatedVnfcCpId": "52431660-dde4-49de-99a4-9d593b17b9c4",                       |
    |                          |             "cpProtocolInfo": [                                                                 |
    |                          |                 {                                                                               |
    |                          |                     "layerProtocol": "IP_OVER_ETHERNET"                                         |
    |                          |                 }                                                                               |
    |                          |             ]                                                                                   |
    |                          |         }                                                                                       |
    |                          |     ],                                                                                          |
    |                          |     "extVirtualLinkInfo": [                                                                     |
    |                          |         {                                                                                       |
    |                          |             "id": "net0",                                                                       |
    |                          |             "resourceHandle": {                                                                 |
    |                          |                 "vimConnectionId": null,                                                        |
    |                          |                 "resourceId": "1642ac54-642c-407c-9c7d-e94c55ba5d33",                           |
    |                          |                 "vimLevelResourceType": null                                                    |
    |                          |             }                                                                                   |
    |                          |         }                                                                                       |
    |                          |     ],                                                                                          |
    |                          |     "vnfcResourceInfo": [                                                                       |
    |                          |         {                                                                                       |
    |                          |             "id": "52431660-dde4-49de-99a4-9d593b17b9c4",                                       |
    |                          |             "vduId": "PrivateRegistryVDU",                                                      |
    |                          |             "computeResource": {                                                                |
    |                          |                 "vimConnectionId": "c3369b54-e376-4423-bb61-afd255900fea",                      |
    |                          |                 "resourceId": "f93edf04-07ac-410e-96aa-7fd64774f951",                           |
    |                          |                 "vimLevelResourceType": "OS::Nova::Server"                                      |
    |                          |             },                                                                                  |
    |                          |             "storageResourceIds": [],                                                           |
    |                          |             "vnfcCpInfo": [                                                                     |
    |                          |                 {                                                                               |
    |                          |                     "id": "8355de52-61ec-495e-ac81-537d0c676915",                               |
    |                          |                     "cpdId": "CP1",                                                             |
    |                          |                     "vnfExtCpId": null,                                                         |
    |                          |                     "vnfLinkPortId": "2b7fa3dc-35a8-4d46-93ba-0c11f39ccced",                    |
    |                          |                     "cpProtocolInfo": [                                                         |
    |                          |                         {                                                                       |
    |                          |                             "layerProtocol": "IP_OVER_ETHERNET"                                 |
    |                          |                         }                                                                       |
    |                          |                     ]                                                                           |
    |                          |                 }                                                                               |
    |                          |             ]                                                                                   |
    |                          |         }                                                                                       |
    |                          |     ],                                                                                          |
    |                          |     "vnfVirtualLinkResourceInfo": [                                                             |
    |                          |         {                                                                                       |
    |                          |             "id": "245b35c0-7cf1-4470-87c7-5927eb0ad2ee",                                       |
    |                          |             "vnfVirtualLinkDescId": "net0",                                                     |
    |                          |             "networkResource": {                                                                |
    |                          |                 "vimConnectionId": null,                                                        |
    |                          |                 "resourceId": "1642ac54-642c-407c-9c7d-e94c55ba5d33",                           |
    |                          |                 "vimLevelResourceType": "OS::Neutron::Net"                                      |
    |                          |             },                                                                                  |
    |                          |             "vnfLinkPorts": [                                                                   |
    |                          |                 {                                                                               |
    |                          |                     "id": "2b7fa3dc-35a8-4d46-93ba-0c11f39ccced",                               |
    |                          |                     "resourceHandle": {                                                         |
    |                          |                         "vimConnectionId": "c3369b54-e376-4423-bb61-afd255900fea",              |
    |                          |                         "resourceId": "2eb5d67b-fe24-40ca-b25a-8c4e47520aee",                   |
    |                          |                         "vimLevelResourceType": "OS::Neutron::Port"                             |
    |                          |                     },                                                                          |
    |                          |                     "cpInstanceId": "8355de52-61ec-495e-ac81-537d0c676915"                      |
    |                          |                 }                                                                               |
    |                          |             ]                                                                                   |
    |                          |         }                                                                                       |
    |                          |     ],                                                                                          |
    |                          |     "vnfcInfo": [                                                                               |
    |                          |         {                                                                                       |
    |                          |             "id": "49330b17-bb00-44df-a1e1-34ea0cd09307",                                       |
    |                          |             "vduId": "PrivateRegistryVDU",                                                      |
    |                          |             "vnfcState": "STARTED"                                                              |
    |                          |         }                                                                                       |
    |                          |     ],                                                                                          |
    |                          |     "additionalParams": {                                                                       |
    |                          |         "private_registry_installation_param": {                                                |
    |                          |             "proxy": {                                                                          |
    |                          |                 "http_proxy": "http://user1:password1@host1:port1",                             |
    |                          |                 "https_proxy": "https://user2:password2@host2:port2",                           |
    |                          |                 "no_proxy": "192.168.246.0/24,10.0.0.1"                                         |
    |                          |             },                                                                                  |
    |                          |             "ssh_cp_name": "CP1",                                                               |
    |                          |             "ssh_username": "ubuntu",                                                           |
    |                          |             "ssh_password": "ubuntu"                                                            |
    |                          |         }                                                                                       |
    |                          |     }                                                                                           |
    |                          | }                                                                                               |
    | Instantiation State      | INSTANTIATED                                                                                    |
    | Links                    | {                                                                                               |
    |                          |     "self": {                                                                                   |
    |                          |         "href": "/vnflcm/v1/vnf_instances/f93ed99c-e2f2-4f18-8377-37a171ea344f"                 |
    |                          |     },                                                                                          |
    |                          |     "terminate": {                                                                              |
    |                          |         "href": "/vnflcm/v1/vnf_instances/f93ed99c-e2f2-4f18-8377-37a171ea344f/terminate"       |
    |                          |     },                                                                                          |
    |                          |     "heal": {                                                                                   |
    |                          |         "href": "/vnflcm/v1/vnf_instances/f93ed99c-e2f2-4f18-8377-37a171ea344f/heal"            |
    |                          |     },                                                                                          |
    |                          |     "changeExtConn": {                                                                          |
    |                          |         "href": "/vnflcm/v1/vnf_instances/f93ed99c-e2f2-4f18-8377-37a171ea344f/change_ext_conn" |
    |                          |     }                                                                                           |
    |                          | }                                                                                               |
    | VIM Connection Info      | [                                                                                               |
    |                          |     {                                                                                           |
    |                          |         "id": "8a3adb69-0884-43c7-833e-aab0b6ab4470",                                           |
    |                          |         "vimId": "c3369b54-e376-4423-bb61-afd255900fea",                                        |
    |                          |         "vimType": "openstack",                                                                 |
    |                          |         "interfaceInfo": {},                                                                    |
    |                          |         "accessInfo": {}                                                                        |
    |                          |     }                                                                                           |
    |                          | ]                                                                                               |
    | VNF Instance Description | None                                                                                            |
    | VNF Instance Name        | vnf-f93ed99c-e2f2-4f18-8377-37a171ea344f                                                        |
    | VNF Product Name         | Sample Private registry VNF                                                                     |
    | VNF Provider             | Company                                                                                         |
    | VNF Software Version     | 1.0                                                                                             |
    | VNFD ID                  | c1bb0ce7-ebca-4fa7-95ed-4840d70a118f                                                            |
    | VNFD Version             | 1.0                                                                                             |
    | vnfPkgId                 |                                                                                                 |
    +--------------------------+-------------------------------------------------------------------------------------------------+

3. Heal Docker Private Registry VNF
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

According to `NFV-SOL001 v2.6.1`_, `heal_start` and `heal_end`
operation allows users to execute any scripts in the heal
operation, and healing operations on the private registry server
is supported with Mgmt Driver.

After instantiating Docker private registry VNF, if it is not running
properly, you can heal it. The following are the methods of creating
the parameter file and CLI commands of OpenStack.

.. note::
    Since the heal entire operation will cause the server's ip to change,
    user should avoid using it when the Docker private registry service
    has already been used.

.. note::
    The image information registered in the Docker private registry that
    is the target of Heal is not retained after Heal.

1. Create the Parameter File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following is heal parameter to "POST /vnf_instances/{id}/heal" as
``HealVnfRequest`` data type. It is not the same in SOL002 and SOL003.

In `NFV-SOL002 v2.6.1`_:

.. list-table:: **heal parameter**
   :widths: 10 25
   :header-rows: 1

   * - Attribute name
     - Parameter description
   * - vnfcInstanceId
     - User specify heal target, user can know "vnfcInstanceId"
       by ``InstantiatedVnfInfo.vnfcResourceInfo`` that
       contained in the response of "GET /vnf_instances/{id}".
   * - cause
     - Not needed
   * - additionalParams
     - Not needed
   * - healScript
     - Not needed

In `NFV-SOL003 v2.6.1`_:

.. list-table:: **heal parameter**
   :widths: 10 25
   :header-rows: 1

   * - Attribute name
     - Parameter description
   * - cause
     - Not needed
   * - additionalParams
     - Not needed

If the vnfcInstanceId parameter is null, this means that healing operation is
required for the entire Kubernetes cluster, which is the case in SOL003.

Following is a sample of healing request body for SOL002:

.. code-block::

    {
        "vnfcInstanceId": "52431660-dde4-49de-99a4-9d593b17b9c4"
    }

.. note::
    In chapter of ``Deploy Docker Private Registry VNF``, the result of VNF instance
    instantiated has shown in CLI command `openstack vnflcm show VNF INSTANCE ID`.

    You can get the vnfcInstanceId from ``Instantiated Vnf Info`` in above result.
    The ``vnfcResourceInfo.id`` is vnfcInstanceId.

2. Execute Heal Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Heal Docker Private Registry VNF (Specify VNFC)
..................................................

When healing specified with VNFC instances,
Heat APIs are called from Tacker.

* stack resource mark unhealthy
* stack update

To confirm whether healing is successful, execute Heat CLI command
and check physical_resource_id and resource_status of private
registry VNF before and after healing.

.. note::
    Note that 'vnfc-instance-id' managed by Tacker and
    'physical-resource-id' managed by Heat are different.
    The ``physical_resource_id`` is the same as
    ``vnfcResourceInfo.computeResource.resourceId``.

Private registry VNF information before healing:

.. code-block:: console

    $ openstack stack resource list vnf-f93ed99c-e2f2-4f18-8377-37a171ea344f -n 2 \
     --filter type=OS::Nova::Server -c resource_name -c physical_resource_id -c \
     resource_type -c resource_status
    +--------------------+--------------------------------------+------------------+-----------------+
    | resource_name      | physical_resource_id                 | resource_type    | resource_status |
    +--------------------+--------------------------------------+------------------+-----------------+
    | PrivateRegistryVDU | f93edf04-07ac-410e-96aa-7fd64774f951 | OS::Nova::Server | CREATE_COMPLETE |
    +--------------------+--------------------------------------+------------------+-----------------+

We heal the private registry VNF with ``physical_resource_id``
``f93edf04-07ac-410e-96aa-7fd64774f951``, its ``vnfc_instance_id``
is ``52431660-dde4-49de-99a4-9d593b17b9c4``.

Healing private registry vnf of the vnf_instance:

.. code-block:: console

    $ openstack vnflcm heal f93ed99c-e2f2-4f18-8377-37a171ea344f --vnfc-instance 52431660-dde4-49de-99a4-9d593b17b9c4
    Heal request for VNF Instance f93ed99c-e2f2-4f18-8377-37a171ea344f has been accepted.

private registry vnf information after healing:

.. code-block:: console

    $ openstack stack resource list vnf-c5215213-af4b-4080-95ab-377920474e1a -n 2 \
     --filter type=OS::Nova::Server -c resource_name -c physical_resource_id -c \
     resource_type -c resource_status
    +--------------------+--------------------------------------+------------------+-----------------+
    | resource_name      | physical_resource_id                 | resource_type    | resource_status |
    +--------------------+--------------------------------------+------------------+-----------------+
    | PrivateRegistryVDU | c8a67180-f49b-492c-a2a2-1ac668a80453 | OS::Nova::Server | CREATE_COMPLETE |
    +--------------------+--------------------------------------+------------------+-----------------+

2. Heal Docker Private Registry VNF (Entire Heal)
.................................................

When healing of the entire VNF, the following APIs are executed
from Tacker to Heat.

* stack delete
* stack create

1. Execute Heat CLI command and check 'ID' and 'Stack Status' of the stack
before and after healing.

2. All the information of Private Registry VNF will be
changed.

This is to confirm that stack 'ID' has changed
before and after healing.

Stack information before healing:

.. code-block:: console

    $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'
    +--------------------------------------+---------------------------------------------+-----------------+
    | ID                                   | Stack Name                                  | Stack Status    |
    +--------------------------------------+---------------------------------------------+-----------------+
    | fb03d2f0-3bd1-4382-a303-b7619484a4fa | vnf-f93ed99c-e2f2-4f18-8377-37a171ea344f    | CREATE_COMPLETE |
    +--------------------------------------+---------------------------------------------+-----------------+

Healing execution of the entire VNF:

.. code-block:: console

    $ openstack vnflcm heal f93ed99c-e2f2-4f18-8377-37a171ea344f
    Heal request for VNF Instance f93ed99c-e2f2-4f18-8377-37a171ea344f has been accepted.

Stack information after healing:

.. code-block:: console

    $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'
    +--------------------------------------+---------------------------------------------+-----------------+
    | ID                                   | Stack Name                                  | Stack Status    |
    +--------------------------------------+---------------------------------------------+-----------------+
    | 98ef6003-5422-4b04-bfc8-d56614d23fcc | vnf-f93ed99c-e2f2-4f18-8377-37a171ea344f    | CREATE_COMPLETE |
    +--------------------------------------+---------------------------------------------+-----------------+

Deploy Kubernetes Cluster with Docker Private Registry
------------------------------------------------------

1. Instantiate Kubernetes Cluster
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The VNF Package for Kubernetes Cluster VNF used here has no change
with the one used in
`How to use Mgmt Driver for deploying Kubernetes Cluster`_.

To use Docker private registry for Kubernetes Cluster, the operation
steps and methods of instantiating are the same as those in
`Deploy Kubernetes Cluster`_ in
`How to use Mgmt Driver for deploying Kubernetes Cluster`.
The difference is the parameter file.
The following attributes should be added into `k8s_cluster_installation_param`
of ``additionalParams`` described in ``Deploy Kubernetes Cluster``.

.. list-table:: **List of additionalParams.k8s_cluster_installation_param.private_registry_connection_info(specified by user)**
   :widths: 10 10 25 10
   :header-rows: 1

   * - parameter
     - data type
     - description
     - required/optional
   * - connection_type
     - string
     - Type of connection. Set one of the following values.
       0 : HTTP, 1 : HTTPS.
       Set to 0 if connecting to the deployed
       Docker private registry VNF or a Docker
       private registry outside of Tacker over HTTP.
       Set to 1 if connecting to a Docker private
       registry outside of Tacker over HTTPS.
     - required
   * - server
     - string
     - Server name of the Docker private registry to connect to.
       For example, "192.168.0.10:5000"
     - required
   * - username
     - string
     - Username to log in to the Docker private registry.
     - optional
   * - password
     - string
     - Password to log in to the Docker private registry.
     - optional
   * - certificate_path
     - string
     - The path of the CA certificate file to use for HTTPS connection.
     - optional
   * - hosts_string
     - string
     - String to add to /etc/hosts. The base Kubernetes
       cluster environment does not have a DNS server
       and must be added to /etc/hosts. The value consists of
       "<IP address> <FQDN>". For example,
       "192.168.0.20 registry.example.com".
     - optional

The ``private_registry_kubernetes_param_file.json`` is shown below.

private_registry_kubernetes_param_file.json

.. code-block::


    {
        "flavourId": "simple",
        "vimConnectionInfo": [{
            "id": "3cc2c4ff-525c-48b4-94c9-29247223322f",
            "vimId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496", #Set the uuid of the VIM to use
            "vimType": "openstack"
        }],
        "additionalParams": {
            "k8s_cluster_installation_param": {
                "script_path": "Scripts/install_k8s_cluster.sh",
                "vim_name": "kubernetes_vim",
                "master_node": {
                    "aspect_id": "master_instance",
                    "ssh_cp_name": "masterNode_CP1",
                    "nic_cp_name": "masterNode_CP1",
                    "username": "ubuntu",
                    "password": "ubuntu",
                    "pod_cidr": "192.168.0.0/16",
                    "cluster_cidr": "10.199.187.0/24",
                    "cluster_cp_name": "vip_CP"
                },
                "worker_node": {
                    "aspect_id": "worker_instance",
                    "ssh_cp_name": "workerNode_CP2",
                    "nic_cp_name": "workerNode_CP2",
                    "username": "ubuntu",
                    "password": "ubuntu"
                },
                "proxy": {
                    "http_proxy": "http://user1:password1@host1:port1",
                    "https_proxy": "https://user2:password2@host2:port2",
                    "no_proxy": "192.168.246.0/24,10.0.0.1",
                    "k8s_node_cidr": "10.10.0.0/24"
                },
                "private_registry_connection_info": [
                    {
                        "connection_type": "0",
                        "server": "192.168.246.10:5000"  #Set the server of Docker private registry to use
                    }
                ]
            },
            "lcm-operation-user-data": "./UserData/k8s_cluster_user_data.py",
            "lcm-operation-user-data-class": "KubernetesClusterUserData"
        },
        "extVirtualLinks": [{
            "id": "net0_master",
            "resourceId": "71a3fbd1-f31e-4c2c-b0e2-26267d64a9ee",  #Set the uuid of the network to use
            "extCps": [{
                "cpdId": "masterNode_CP1",
                "cpConfig": [{
                    "cpProtocolData": [{
                        "layerProtocol": "IP_OVER_ETHERNET"
                    }]
                }]
            }]
        }, {
            "id": "net0_worker",
            "resourceId": "71a3fbd1-f31e-4c2c-b0e2-26267d64a9ee",  #Set the uuid of the network to use
            "extCps": [{
                "cpdId": "workerNode_CP2",
                "cpConfig": [{
                    "cpProtocolData": [{
                        "layerProtocol": "IP_OVER_ETHERNET"
                    }]
                }]
            }]
        }]
    }

2. Scale and Heal Operation
^^^^^^^^^^^^^^^^^^^^^^^^^^^
For users, other operations such as scale and heal are the same as
the ones in `How to use Mgmt Driver for deploying Kubernetes Cluster`_.

Limitations
-----------
1. Heal entire operation will cause the server's ip to change,
   user should avoid using it when the Docker private registry
   service is in use.
2. The image information registered in the Docker private registry
   that is the target of Heal is not retained after Heal.

.. _How to use Mgmt Driver for deploying Kubernetes Cluster: https://docs.openstack.org/tacker/wallaby/user/mgmt_driver_deploy_k8s_usage_guide.html
.. _cli-legacy-vim : https://docs.openstack.org/tacker/latest/cli/cli-legacy-vim.html#register-vim
.. _Deploy Kubernetes Cluster: https://docs.openstack.org/tacker/wallaby/user/mgmt_driver_deploy_k8s_usage_guide.html#deploy-kubernetes-cluster
.. _NFV-SOL001 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/001/02.06.01_60/gs_NFV-SOL001v020601p.pdf
.. _NFV-SOL002 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/002/02.06.01_60/gs_NFV-SOL002v020601p.pdf
.. _NFV-SOL003 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/003/02.06.01_60/gs_NFV-SOL003v020601p.pdf
.. _samples/mgmt_driver/kubernetes/private_registry_vnf_package/: https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes/private_registry_vnf_package/
