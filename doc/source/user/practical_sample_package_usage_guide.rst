=======================================================
How to use a Sample VNF Package for practical use cases
=======================================================

Overview
--------

1. The Sample VNF Package Introduction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The sample of
`VNF Package Sample for practical use cases`_
is designed for users who want to deploy VNF that is required in
more practical environment.
You can know how to use it in this user guide.

2. Use Cases
^^^^^^^^^^^^
In this sample, the use cases listed below is supported.

* using multiple deployment flavours
* deploying VNF connected to an external network
* deploying VNF as HA cluster
* deploying scalable VNF

3. Structure of The Sample VNF Package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This sample includes two deployment flavours listed below.

* ha
* scalable

1. Deployment Flavour of ha
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The deployment flavour of ha defines the structure of VNF that is
designed as a high availability cluster.
It has two VDUs, and each VDU have a CP that is connected to both
internal and external networks.
It also has a CP shared by the VDUs, and the CP is designed to be used as VIP.
Each CP has its own fixed IP address.

.. note::
    This sample just defines the openstack resources.
    Therefore, additional configuration such as
    cloud_init or mgmt driver is needed to have the VNF clustered as HA.

2. Deployment Flavour of scalable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The deployment flavour of scalable defines the structure of VNF that can
scale out or scale in.
It defines three VDUs.
It is possible not to deploy The VDU_2 initially and deploy it later
by scaling operation.
Each VDU has its own fixed IP address and those information is passed by
InstantiateVNFRequest.
The address of the VDU_2 can also be passed in it
even though the VDU_2 is not deployed initially.

The diagrams below show the architecture of the VNFD used in this sample.

.. code-block:: console

  +--------------------------------------+
  |  VNFD                                |
  |                                      |
  |    +----------------------------+    |
  |    | Deployment flavour: ha     |    |
  |    |  +---------+ +---------+   |    |
  |    |  | VDU_0   | | VDU_1   |   |    |
  |    |  |         | |         |   |    |
  |    |  |         | |         |   |    |
  |    |  |         | |         |   |    |
  |    |  +------+--+ +--+------+   |    |
  |    |         |\     /|          |    |
  |    |         | \   / |          |    |
  |    |         |  \ /  |          |    |
  |    |         |   +vip|          |    |
  |    |         |   |   |          |    |
  |    |         |   |   |  int net |    |
  |    |   ------+---+---+-------   |    |
  |    |         |   |   |          |    |
  |    +---------|---|---|----------+    |
  |              |   |   |               |
  |              |   |   |               |
  +--------------|---|---|---------------+
                 |   |   |
                 |   |   |  ext net
             ----+---+---+---------

.. code-block:: console

  +---------------------------------------------------------------------------------------------------------------+
  |  VNFD                                                                                                         |
  |                                                                                                               |
  |    +----------------------------------------------------------------------------------------------------+     |
  |    |   Deployment flavour: scalable                                                                     |     |
  |    | |------------------------------+ +------------------------------+ +------------------------------+ |     |
  |    | | VDU_0                        | | VDU_1                        | | VDU_2                        | |     |
  |    | |   properties:                | |   properties:                | |   properties:                | |     |
  |    | |     vdu_profile:             | |     vdu_profile:             | |     vdu_profile:             | |     |
  |    | |       min_num_of_instance:1  | |       min_num_of_instance:1  | |       min_num_of_instance:0  | |     |
  |    | |       max_num_of_instance:1  | |       max_num_of_instance:1  | |       max_num_of_instance:1  | |     |
  |    | +------+--------------+--------+ +------+--------------+--------+ +------+--------------+--------+ |     |
  |    |        |              |                 |              |                 |              |          |     |
  |    |        |              |                 |              |                 |              |          |     |
  |    |        |              |                 |              |                 |              |          |     |
  |    |        |              |                 |              |                 |              |          |     |
  |    |        |              |                 |              |                 |              |  int net |     |
  |    |    ----+--------------|-----------------+--------------|-----------------+--------------|-------   |     |
  |    |                       |                                |                                |          |     |
  |    +-----------------------|--------------------------------|--------------------------------|----------+     |
  |                            |                                |                                |                |
  |                            |                                |                                |                |
  +----------------------------|--------------------------------|--------------------------------|----------------+
                               |                                |                                |
                               |                                |                                |   ext net
                      ---------+--------------------------------+--------------------------------+-------

Preparations
------------
To instantiate this sample, preparations explained below is needed.

1. Create External Network
^^^^^^^^^^^^^^^^^^^^^^^^^^

This sample uses an external network.
You should create an external network and
set up the network configuration referring to
`mgmt_driver_deploy_k8s_usage_guide`_.

2. Create Image
^^^^^^^^^^^^^^^
In this user guide, the cirros image is used.

1. Download Cirros Image
~~~~~~~~~~~~~~~~~~~~~~~~
Download the cirros image (version 0.5.1) from the official website.
The command is shown below:

.. code-block:: console

    $ wget -P ./ http://download.cirros-cloud.net/0.5.1/cirros-0.5.1-x86_64-disk.img

2. Create Image
~~~~~~~~~~~~~~~
Execute the following CLI command to create Image.

.. code-block:: console

    $ openstack image create --disk-format qcow2 --container-format bare \
      --public --file ./cirros-0.5.1-x86_64-disk sample_image

3. Create Flavor
^^^^^^^^^^^^^^^^
Execute the following CLI command to create Flavor.

.. code-block:: console

    $  openstack flavor create sample_flavor --ram 512 --disk 1 --vcpus 1

Result:

.. code-block:: console

    +----------------------------+--------------------------------------+
    | Field                      | Value                                |
    +----------------------------+--------------------------------------+
    | OS-FLV-DISABLED:disabled   | False                                |
    | OS-FLV-EXT-DATA:ephemeral  | 0                                    |
    | description                | None                                 |
    | disk                       | 1                                    |
    | extra_specs                | {}                                   |
    | id                         | 22afc806-b361-4fae-83b5-5da4e86f2597 |
    | name                       | sample_flavor                        |
    | os-flavor-access:is_public | True                                 |
    | properties                 |                                      |
    | ram                        | 512                                  |
    | rxtx_factor                | 1.0                                  |
    | swap                       | 0                                    |
    | vcpus                      | 1                                    |
    +----------------------------+--------------------------------------+

4. Register VIM
^^^^^^^^^^^^^^^
A VIM should be registered according to
:doc:`../cli/cli-legacy-vim`.

Create and Upload VNF Package
-----------------------------

VNF Package is a ZIP file including VNFD and other
artifact resources such as scripts and config files. The directory structure
and file contents are defined in `NFV-SOL004 v2.6.1`_.
According to `NFV-SOL004 v2.6.1`_, VNF Package should be the ZIP file format
with the `TOSCA-Simple-Profile-YAML-v1.2`_ Specifications.
In this user guide, the CSAR with TOSCA-Metadata directory is used.

.. note::

    For more detailed definitions of VNF Package, you can see `VNF Package`_.

1. Directory Structure
^^^^^^^^^^^^^^^^^^^^^^
The structure of this sample is as follows.

.. code-block:: console

  !----TOSCA-Metadata
          !---- TOSCA.meta
  !----Definitions
          !---- etsi_nfv_sol001_common_types.yaml
          !---- etsi_nfv_sol001_vnfd_types.yaml
          !---- Common.yaml
          !---- Node.yaml
          !---- df_ha.yaml
          !---- df_scalable.yaml
  !----BaseHOT
          !---- ha
                  !---- ha_hot.yaml
          !---- scalable
                  !---- nested
                          !---- VDU_0.yaml
                          !---- VDU_1.yaml
                          !---- VDU_2.yaml
                  !---- scalable_hot.yaml
  !----UserData
          !---- __init__.py
          !---- lcm_user_data.py

.. note::

    You can also find them in the
    ``samples/practical_vnf_package``
    directory of the tacker.

TOSCA-Metadata/TOSCA.meta
~~~~~~~~~~~~~~~~~~~~~~~~~

According to `TOSCA-Simple-Profile-YAML-v1.2`_ specifications, the
``TOSCA.meta`` metadata file is described in `TOSCA-1.0-specification`_.
The files under ``Scripts`` directory are artifact files, therefore, you
should add their location and digest into ``TOSCA.meta`` metadata file.
The sample file is shown below:

* `TOSCA.meta`_

Definitions/
~~~~~~~~~~~~
All VNFD YAML files are located here. In this guide, there are two types
of definition files, ETSI NFV types definition file and User defined types
definition file.

ETSI NFV provides two types of definition files [#f1]_ which
contain all defined type definitions in `NFV-SOL001 v2.6.1`_.
You can download them from official website.

* `etsi_nfv_sol001_common_types.yaml`_
* `etsi_nfv_sol001_vnfd_types.yaml`_

You can extend their own types definition from `NFV-SOL001 v2.6.1`_. In most
cases, you need to extend ``tosca.nodes.nfv.VNF`` to define your VNF node
types. In this guide, ``df_ha.yaml`` and ``df_scalable.yaml``  are defined.
The sample files are shown below:

* `Common.yaml`_
* `Node.yaml`_
* `df_ha.yaml`_
* `df_scalable.yaml`_

BaseHOT/
~~~~~~~~

Base HOT file is a Native cloud orchestration template, HOT in this context,
which is commonly used for LCM operations in different VNFs. It is the
responsibility of the user to prepare this file, and it is necessary to make
it consistent with VNFD placed under the ``Definitions/`` directory.

In this guide, you must use user data to deploy this sample, so the
BaseHot directory must be included.

You must place the directory corresponding to ``deployment_flavour`` stored in
the ``Definitions/`` under the ``BaseHOT/`` directory, and store the
Base HOT files in it.

In this guide, there are two deployment flavours in this VNF Package, so
there are two directories under ``BaseHOT/`` directory. The sample files are
shown below:

* `ha/ha_hot.yaml`_
* `scalable/scalable_hot.yaml`_
* `scalable/VDU_0.yaml`_
* `scalable/VDU_1.yaml`_
* `scalable/VDU_2.yaml`_

UserData/
~~~~~~~~~

LCM operation user data is a script that returns key/value data as
Heat input parameters used for Base HOT. The sample file is shown below:

* `lcm_user_data.py`_


2. Create VNF Package
^^^^^^^^^^^^^^^^^^^^^

Execute the following CLI command to create VNF Package.

.. code-block:: console

    $ openstack vnf package create


Result:

.. code-block:: console

    +-------------------+-------------------------------------------------------------------------------------------------+
    | Field             | Value                                                                                           |
    +-------------------+-------------------------------------------------------------------------------------------------+
    | ID                | 5413f0ee-23a7-438d-bc5d-4ea1eb19117e                                                            |
    | Links             | {                                                                                               |
    |                   |     "self": {                                                                                   |
    |                   |         "href": "/vnfpkgm/v1/vnf_packages/5413f0ee-23a7-438d-bc5d-4ea1eb19117e"                 |
    |                   |     },                                                                                          |
    |                   |     "packageContent": {                                                                         |
    |                   |         "href": "/vnfpkgm/v1/vnf_packages/5413f0ee-23a7-438d-bc5d-4ea1eb19117e/package_content" |
    |                   |     }                                                                                           |
    |                   | }                                                                                               |
    | Onboarding State  | CREATED                                                                                         |
    | Operational State | DISABLED                                                                                        |
    | Usage State       | NOT_IN_USE                                                                                      |
    | User Defined Data | {}                                                                                              |
    +-------------------+-------------------------------------------------------------------------------------------------+

3. Upload VNF Package
^^^^^^^^^^^^^^^^^^^^^

Before you instantiate VNF, you must create a zip file of VNF Package
and upload it.

Execute the following command to make a zip file.

.. code-block:: console

    $ cd /opt/stack/tacker/samples/practical_vnf_package
    $ zip sample_csar.zip -r Definitions/ TOSCA-Metadata/ BaseHOT/ UserData/

Execute the following CLI command to upload VNF Package.

.. code-block:: console

    $ openstack vnf package upload --path ./sample_csar.zip VNF_PACKAGE_ID


Result:

.. code-block:: console

    Upload request for VNF package 5413f0ee-23a7-438d-bc5d-4ea1eb19117e has been accepted.


After that, execute the following CLI command and confirm that
VNF Package uploading was successful.

* Confirm that the 'Onboarding State' is 'ONBOARDED'.
* Confirm that the 'Operational State' is 'ENABLED'.
* Confirm that the 'Usage State' is 'NOT_IN_USE'.
* Take a note of the 'VNFD ID' because you will need it in the next
  'Deploy VNF'.

.. code-block:: console

    $ openstack vnf package show VNF_PACKAGE_ID
    +----------------------+-------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field                | Value                                                                                                                                           |
    +----------------------+-------------------------------------------------------------------------------------------------------------------------------------------------+
    | Checksum             | {                                                                                                                                               |
    |                      |     "hash": "8892cc96acf4f34117e228d7d6352812c4dc62e0b9ae894979de4eba920c6d49b153c074bfa898043507b9d2260be97b2e21c1ad3cee66691eff480d936e54bd", |
    |                      |     "algorithm": "sha512"                                                                                                                       |
    |                      | }                                                                                                                                               |
    | ID                   | 5413f0ee-23a7-438d-bc5d-4ea1eb19117e                                                                                                            |
    | Links                | {                                                                                                                                               |
    |                      |     "self": {                                                                                                                                   |
    |                      |         "href": "/vnfpkgm/v1/vnf_packages/5413f0ee-23a7-438d-bc5d-4ea1eb19117e"                                                                 |
    |                      |     },                                                                                                                                          |
    |                      |     "packageContent": {                                                                                                                         |
    |                      |         "href": "/vnfpkgm/v1/vnf_packages/5413f0ee-23a7-438d-bc5d-4ea1eb19117e/package_content"                                                 |
    |                      |     }                                                                                                                                           |
    |                      | }                                                                                                                                               |
    | Onboarding State     | ONBOARDED                                                                                                                                       |
    | Operational State    | ENABLED                                                                                                                                         |
    | Software Images      |                                                                                                                                                 |
    | Usage State          | NOT_IN_USE                                                                                                                                      |
    | User Defined Data    | {}                                                                                                                                              |
    | VNF Product Name     | Node                                                                                                                                            |
    | VNF Provider         | Sample                                                                                                                                          |
    | VNF Software Version | 10.1                                                                                                                                            |
    | VNFD ID              | 9ed8bcf4-1e01-4d91-8cfb-57cd052e6a90                                                                                                            |
    | VNFD Version         | 1.0                                                                                                                                             |
    +----------------------+-------------------------------------------------------------------------------------------------------------------------------------------------+

Deploy VNF
----------

1. Deploy VNF of ha Deployment Flavour
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Create VNF Identifier
~~~~~~~~~~~~~~~~~~~~~~~~
Execute the following CLI command to create a VNF instance.

.. code-block:: console

  openstack vnflcm create VNFD_ID

Result:

.. code-block:: console

    +--------------------------+------------------------------------------------------------------------------------------------------------------+
    | Field                    | Value                                                                                                            |
    +--------------------------+------------------------------------------------------------------------------------------------------------------+
    | ID                       | d57acd9a-34f1-4a2d-a8a0-7013270def45                                                                             |
    | Instantiation State      | NOT_INSTANTIATED                                                                                                 |
    | Links                    | {                                                                                                                |
    |                          |     "self": {                                                                                                    |
    |                          |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/d57acd9a-34f1-4a2d-a8a0-7013270def45"             |
    |                          |     },                                                                                                           |
    |                          |     "instantiate": {                                                                                             |
    |                          |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/d57acd9a-34f1-4a2d-a8a0-7013270def45/instantiate" |
    |                          |     }                                                                                                            |
    |                          | }                                                                                                                |
    | VNF Instance Description | None                                                                                                             |
    | VNF Instance Name        | vnf-d57acd9a-34f1-4a2d-a8a0-7013270def45                                                                         |
    | VNF Product Name         | Node                                                                                                             |
    | VNF Provider             | Sample                                                                                                           |
    | VNF Software Version     | 10.1                                                                                                             |
    | VNFD ID                  | 9ed8bcf4-1e01-4d91-8cfb-57cd052e6a90                                                                             |
    | VNFD Version             | 1.0                                                                                                              |
    | vnfPkgId                 |                                                                                                                  |
    +--------------------------+------------------------------------------------------------------------------------------------------------------+

After that, execute the following CLI command and confirm that
VNF instance creation was successful.

* Confirm that the 'Usage State' of the VNF Package is 'IN_USE'.
* Confirm that the 'Instantiation State' of the VNF instance
  is 'NOT_INSTANTIATED'.

.. code-block:: console

  $ openstack vnf package show VNF_PACKAGE_ID \
      -c 'Usage State'


Result:

.. code-block:: console

  +-------------+--------+
  | Field       | Value  |
  +-------------+--------+
  | Usage State | IN_USE |
  +-------------+--------+


.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID \
      -c 'Instantiation State'


Result:

.. code-block:: console

  +---------------------+------------------+
  | Field               | Value            |
  +---------------------+------------------+
  | Instantiation State | NOT_INSTANTIATED |
  +---------------------+------------------+

2. Instantiate VNF
~~~~~~~~~~~~~~~~~~

Create a sample_ha_param_file.json file with the following format.
This is the file that defines the parameters for an instantiate request.
These parameters will be set in the body of the instantiate request.

Required parameter:

* flavourId
* additionalParams
* extVirtualLinks

.. note::
    [This is UserData specific part]
    additionalParams is a parameter that can be described by KeyValuePairs.
    By setting the following two parameters in this parameter,
    instantiate using LCM operation user data becomes possible.
    For file_name.py and class_name, set the file name and class name
    described in Prerequisites.

    * lcm-operation-user-data: ./UserData/file_name.py
    * lcm-operation-user-data-class: class_name

Optional parameters:

* vimConnectionInfo

In this guide, the VMs have a connections to external networks.
Therefore, ``extVirtualLinks`` parameter is required. You can skip
``vimConnectionInfo`` only when you have the default VIM described in
`cli-legacy-vim`_.


sample_ha_param_file.json:

.. code-block:: console

    {
      "flavourId": "ha",
      "extVirtualLinks": [
        {
          "extCps": [
            {
              "cpConfig": [
                {
                  "cpProtocolData": [
                    {
                      "layerProtocol": "IP_OVER_ETHERNET",
                      "ipOverEthernet": {
                        "ipAddresses": [
                          {
                            "subnetId": "589a97b7-5fb7-4969-a1fd-e7cc206384a9", #Set the uuid of the subnet to use
                            "type": "IPV4",
                            "fixedAddresses": [
                              "10.181.221.40" #Set the fixed IP address to use
                            ]
                          }
                        ]
                      }
                    }
                  ]
                }
              ],
              "cpdId": "VDU_extvCP"
            },
            {
              "cpConfig": [
                {
                  "cpProtocolData": [
                    {
                      "layerProtocol": "IP_OVER_ETHERNET",
                      "ipOverEthernet": {
                        "ipAddresses": [
                          {
                            "subnetId": "589a97b7-5fb7-4969-a1fd-e7cc206384a9", #Set the uuid of the subnet to use
                            "type": "IPV4",
                            "fixedAddresses": [
                              "10.181.221.41" #Set the fixed IP address to use
                            ]
                          }
                        ]
                      }
                    }
                  ]
                }
              ],
              "cpdId": "VDU0_extCP0"
            },
            {
              "cpConfig": [
                {
                  "cpProtocolData": [
                    {
                      "layerProtocol": "IP_OVER_ETHERNET",
                      "ipOverEthernet": {
                        "ipAddresses": [
                          {
                            "subnetId": "589a97b7-5fb7-4969-a1fd-e7cc206384a9", #Set the uuid of the subnet to use
                            "type": "IPV4",
                            "fixedAddresses": [
                              "10.181.221.42" #Set the fixed IP address to use
                            ]
                          }
                        ]
                      }
                    }
                  ]
                }
              ],
              "cpdId": "VDU1_extCP0"
            },
            {
              "cpConfig": [
                {
                  "cpProtocolData": [
                    {
                      "layerProtocol": "IP_OVER_ETHERNET",
                      "ipOverEthernet": {
                        "ipAddresses": [
                          {
                            "subnetId": "589a97b7-5fb7-4969-a1fd-e7cc206384a9", #Set the uuid of the subnet to use
                            "type": "IPV4",
                            "fixedAddresses": [
                              "10.181.221.43" #Set the fixed IP address to use
                            ]
                          }
                        ]
                      }
                    }
                  ]
                }
              ],
              "cpdId": "RT_extCP"
            }
          ],
          "id": "mgmt_network",
          "resourceId": "1b13c680-d091-4564-b652-4074f5382da7" #Set the uuid of the network to use
        }
      ],
      "vimConnectionInfo": [
        {
          "id": "d98b6cf8-dbc4-4254-a628-5801a1c20dbe",
          "vimId": "d98b6cf8-dbc4-4254-a628-5801a1c20dbe", #Set the uuid of the VIM to use
          "vimType": "openstack"
        }
      ],
      "additionalParams": {
        "lcm-operation-user-data": "./UserData/lcm_user_data.py",
        "lcm-operation-user-data-class": "ETSICompatibleUserData",
        "security_group": "default"
      }
    }


Execute the following CLI command to instantiate VNF instance.

.. code-block:: console

  $ openstack vnflcm instantiate VNF_INSTANCE_ID \
       ./sample_ha_param_file.json


Result:

.. code-block:: console

  Instantiate request for VNF Instance d57acd9a-34f1-4a2d-a8a0-7013270def45 has been accepted.


After that, execute the following CLI command and confirm that
VNF instance instantiation was successful.

* Confirm that the 'Instantiation State' is 'INSTANTIATED'.

.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID \
      -c 'Instantiation State'


Result:

.. code-block:: console

  +---------------------+--------------+
  | Field               | Value        |
  +---------------------+--------------+
  | Instantiation State | INSTANTIATED |
  +---------------------+--------------+



2. Deploy VNF of scalable Deployment Flavour
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Create VNF Identifier
~~~~~~~~~~~~~~~~~~~~~~~~
Execute the following CLI command to create a VNF instance.

.. code-block:: console

  openstack vnflcm create VNFD_ID

Result:

.. code-block:: console

    +--------------------------+------------------------------------------------------------------------------------------------------------------+
    | Field                    | Value                                                                                                            |
    +--------------------------+------------------------------------------------------------------------------------------------------------------+
    | ID                       | 1b71922e-3531-4cd1-8961-0feb38f6f82e                                                                             |
    | Instantiation State      | NOT_INSTANTIATED                                                                                                 |
    | Links                    | {                                                                                                                |
    |                          |     "self": {                                                                                                    |
    |                          |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/1b71922e-3531-4cd1-8961-0feb38f6f82e"             |
    |                          |     },                                                                                                           |
    |                          |     "instantiate": {                                                                                             |
    |                          |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/1b71922e-3531-4cd1-8961-0feb38f6f82e/instantiate" |
    |                          |     }                                                                                                            |
    |                          | }                                                                                                                |
    | VNF Instance Description | None                                                                                                             |
    | VNF Instance Name        | vnf-1b71922e-3531-4cd1-8961-0feb38f6f82e                                                                         |
    | VNF Product Name         | Node                                                                                                             |
    | VNF Provider             | Sample                                                                                                           |
    | VNF Software Version     | 10.1                                                                                                             |
    | VNFD ID                  | 9ed8bcf4-1e01-4d91-8cfb-57cd052e6a90                                                                             |
    | VNFD Version             | 1.0                                                                                                              |
    | vnfPkgId                 |                                                                                                                  |
    +--------------------------+------------------------------------------------------------------------------------------------------------------+

After that, execute the following CLI command and confirm that
VNF instance creation was successful.

* Confirm that the 'Usage State' of the VNF Package is 'IN_USE'.
* Confirm that the 'Instantiation State' of the VNF instance
  is 'NOT_INSTANTIATED'.

.. code-block:: console

  $ openstack vnf package show VNF_PACKAGE_ID \
      -c 'Usage State'


Result:

.. code-block:: console

  +-------------+--------+
  | Field       | Value  |
  +-------------+--------+
  | Usage State | IN_USE |
  +-------------+--------+


.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID \
      -c 'Instantiation State'


Result:

.. code-block:: console

  +---------------------+------------------+
  | Field               | Value            |
  +---------------------+------------------+
  | Instantiation State | NOT_INSTANTIATED |
  +---------------------+------------------+

2. Instantiate VNF
~~~~~~~~~~~~~~~~~~

Create a sample_scalable_param_file.json file with the following format.
This is the file that defines the parameters for an instantiate request.
These parameters will be set in the body of the instantiate request.

Required parameter:

* flavourId
* instantiationLevelId
* additionalParams
* extVirtualLinks

.. note::
    [This is UserData specific part]
    additionalParams is a parameter that can be described by KeyValuePairs.
    By setting the following two parameters in this parameter,
    instantiate using LCM operation user data becomes possible.
    For file_name.py and class_name, set the file name and class name
    described in Prerequisites.

    * lcm-operation-user-data: ./UserData/file_name.py
    * lcm-operation-user-data-class: class_name

Optional parameters:

* vimConnectionInfo

In this guide, the VMs have a connections to external networks.
Therefore, ``extVirtualLinks`` parameter is required. You can skip
``vimConnectionInfo`` only when you have the default VIM described in
`cli-legacy-vim`_.


sample_scalable_param_file.json:

.. code-block:: console

    {
      "flavourId": "scalable",
      "instantiationLevelId": "r-node-min",
      "extVirtualLinks": [
        {
          "extCps": [
            {
              "cpConfig": [
                {
                  "cpProtocolData": [
                    {
                      "layerProtocol": "IP_OVER_ETHERNET",
                      "ipOverEthernet": {
                        "ipAddresses": [
                          {
                            "subnetId": "589a97b7-5fb7-4969-a1fd-e7cc206384a9", #Set the uuid of the subnet to use
                            "type": "IPV4",
                            "fixedAddresses": [
                              "10.181.221.40" #Set the fixed IP address to use
                            ]
                          }
                        ]
                      }
                    }
                  ]
                }
              ],
              "cpdId": "VDU0_CP1"
            },
            {
              "cpConfig": [
                {
                  "cpProtocolData": [
                    {
                      "layerProtocol": "IP_OVER_ETHERNET",
                      "ipOverEthernet": {
                        "ipAddresses": [
                          {
                            "subnetId": "589a97b7-5fb7-4969-a1fd-e7cc206384a9", #Set the uuid of the subnet to use
                            "type": "IPV4",
                            "fixedAddresses": [
                              "10.181.221.41" #Set the fixed IP address to use
                            ]
                          }
                        ]
                      }
                    }
                  ]
                }
              ],
              "cpdId": "VDU1_CP1"
            },
            {
              "cpConfig": [
                {
                  "cpProtocolData": [
                    {
                      "layerProtocol": "IP_OVER_ETHERNET",
                      "ipOverEthernet": {
                        "ipAddresses": [
                          {
                            "subnetId": "589a97b7-5fb7-4969-a1fd-e7cc206384a9", #Set the uuid of the subnet to use
                            "type": "IPV4",
                            "fixedAddresses": [
                              "10.181.221.42" #Set the fixed IP address to use
                            ]
                          }
                        ]
                      }
                    }
                  ]
                }
              ],
              "cpdId": "VDU2_CP1"
            }
          ],
          "id": "mgmt_network",
          "resourceId": "1b13c680-d091-4564-b652-4074f5382da7" #Set the uuid of the network to use
        }
      ],
      "vimConnectionInfo": [
        {
          "id": "d98b6cf8-dbc4-4254-a628-5801a1c20dbe",
          "vimId": "d98b6cf8-dbc4-4254-a628-5801a1c20dbe", #Set the uuid of the VIM to use
          "vimType": "openstack"
        }
      ],
      "additionalParams": {
        "lcm-operation-user-data": "./UserData/lcm_user_data.py",
        "lcm-operation-user-data-class": "ETSICompatibleUserData",
        "vdu0_availabilityzone": "sample-az-1",
        "vdu1_availabilityzone": "sample-az-2",
        "vdu2_availabilityzone": "sample-az-2",
        "security_group": "default"
      }
    }


Execute the following CLI command to instantiate VNF instance.

.. code-block:: console

  $ openstack vnflcm instantiate VNF_INSTANCE_ID \
       ./sample_scalable_param_file.json


Result:

.. code-block:: console

  Instantiate request for VNF Instance d57acd9a-34f1-4a2d-a8a0-7013270def45 has been accepted.


After that, execute the following CLI command and confirm that
VNF instance instantiation was successful.

* Confirm that the 'Instantiation State' is 'INSTANTIATED'.

.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID \
      -c 'Instantiation State'


Result:

.. code-block:: console

  +---------------------+--------------+
  | Field               | Value        |
  +---------------------+--------------+
  | Instantiation State | INSTANTIATED |
  +---------------------+--------------+

3. Scale Out VNF
~~~~~~~~~~~~~~~~

The VNF must be instantiated before performing scaling.

In order to execute scaling, it is necessary to specify
ASPECT_ID, which is the ID for the target scaling group.
First, the method of specifying the ID will be described.

ASPECT_ID is described in VNFD included in the VNF Package.
In the following VNFD excerpt, **VDU_2** corresponds to ASPECT_ID.

.. code-block:: yaml

  node_templates:
    VDU_2:
      type: tosca.nodes.nfv.Vdu.Compute
      properties:
        name: VDU_2
        description: VDU_2
        vdu_profile:
          min_number_of_instances: 0
          max_number_of_instances: 1
        sw_image_data:
          name: sample_image
          version: '1.0'
          checksum:
            algorithm: sha-512
            hash: 6513f21e44aa3da349f248188a44bc304a3653a04122d8fb4535423c8e1d14cd6a153f735bb0982e2161b5b5186106570c17a9e58b64dd39390617cd5a350f78
          container_format: bare
          disk_format: qcow2
          min_disk: 0 GB
          size: 1869 MB
      capabilities:
        virtual_compute:
          properties:
            requested_additional_capabilities:
              properties:
                requested_additional_capability_name: sample_flavor
                support_mandatory: true
                target_performance_parameters:
                  entry_schema: test
            virtual_memory:
              virtual_mem_size: 512 MB
            virtual_cpu:
              num_virtual_cpu: 1
            virtual_local_storage:
              - size_of_storage: 1 GB

    ...snip VNFD...

    policies:
    - vdu_scale:
        type: tosca.policies.nfv.ScalingAspects
        properties:
          aspects:
            VDU_2:
              name: VDU_2
              description: VDU_2
              max_scale_level: 1
              step_deltas:
                - delta_1

    - vdu_2_initial_delta:
        type: tosca.policies.nfv.VduInitialDelta
        properties:
          initial_delta:
            number_of_instances: 0
        targets: [ VDU_2 ]

    - vdu_2_scaling_aspect_deltas:
        type: tosca.policies.nfv.VduScalingAspectDeltas
        properties:
          aspect: VDU_2
          deltas:
            delta_1:
              number_of_instances: 1
        targets: [ VDU_2 ]

    - instantiation_levels:
        type: tosca.policies.nfv.InstantiationLevels
        properties:
          levels:
            r-node-min:
              description: vdu-min structure
              scale_info:
                VDU_2:
                  scale_level: 0
            r-node-max:
              description: vdu-max structure
              scale_info:
                VDU_2:
                  scale_level: 1

    - vdu_2_instantiation_levels:
        type: tosca.policies.nfv.VduInstantiationLevels
        properties:
          levels:
            r-node-min:
              number_of_instances: 0
            r-node-max:
              number_of_instances: 1
        targets: [ VDU_2 ]

  ...snip VNFD...

.. note:: See `NFV-SOL001 v2.6.1`_ annex A.6 for details about ASPECT_ID.

Execute Scale CLI command and check the number of resources
before and after scaling.
This is to confirm that the number of resources has increased
after Scale-out.
See `Heat CLI reference`_. for details on Heat CLI commands.


Stack information before scale-out:

Execute following command to check the uuid of VDU_2.

.. code-block:: console

  $ openstack stack resource list STACK_ID -c resource_name \
      -c physical_resource_id -c resource_type -c resource_status

Result:

.. code-block:: console

  +----------------------+--------------------------------------+----------------------------+-----------------+
  | resource_name        | physical_resource_id                 | resource_type              | resource_status |
  +----------------------+--------------------------------------+----------------------------+-----------------+
  | VDU_1                | 617802bf-9f55-4d13-968f-8682079514d0 | OS::Heat::AutoScalingGroup | CREATE_COMPLETE |
  | int_subnet           | 60d7daa5-7687-4bbf-bcff-bb1b35e58032 | OS::Neutron::Subnet        | CREATE_COMPLETE |
  | VDU_2_scale_out      | 11092f1a82b14151928f996070977f11     | OS::Heat::ScalingPolicy    | CREATE_COMPLETE |
  | VDU_0                | ae4376b7-d390-4c11-bc3a-a6a8223598c5 | OS::Heat::AutoScalingGroup | CREATE_COMPLETE |
  | VDU_2_scale_in       | 30d0bdda9b2e4b01bc9899453314b00d     | OS::Heat::ScalingPolicy    | CREATE_COMPLETE |
  | VDU_2                | 519c9eed-036c-429c-bf75-56b9f303689e | OS::Heat::AutoScalingGroup | CREATE_COMPLETE |
  | int_net              | 7a25ec57-d2c3-4237-8586-3f3b7c6471ec | OS::Neutron::Net           | CREATE_COMPLETE |
  | vdu_placement_policy | 1226676d-ee9b-4de8-9220-39cd37de5c98 | OS::Nova::ServerGroup      | CREATE_COMPLETE |
  +----------------------+--------------------------------------+----------------------------+-----------------+

Execute following command and confirm that no results will be returned.
This means the resource of VDU_2 has no nested resources at the time.

.. code-block:: console

  $ openstack stack resource list VDU_2_ID -c resource_name \
      -c physical_resource_id -c resource_type -c resource_status

And then, Scale-out VNF can be executed by the following CLI command.

.. code-block:: console

  $ openstack vnflcm scale --type SCALE_OUT --aspect-id VDU_2 VNF_INSTANCE_ID


Result:

.. code-block:: console

  Scale request for VNF Instance d57acd9a-34f1-4a2d-a8a0-7013270def45 has been accepted.

Stack information after scale-out:

Execute following command and confirm that
the resources have been created under the VDU_2.

.. code-block:: console

  $ openstack stack resource list VDU_2_ID -c resource_name \
      -c physical_resource_id -c resource_type -c resource_status

Result:

.. code-block:: console

  +---------------+--------------------------------------+-------------------+-----------------+
  | resource_name | physical_resource_id                 | resource_type     | resource_status |
  +---------------+--------------------------------------+-------------------+-----------------+
  | nsatlzzxx2ik  | f0258a82-53a4-4239-932e-2ab18c3b69ae | VDU_2.yaml        | CREATE_COMPLETE |
  | VDU_2         | ed2dd9d1-ffc7-43a3-8efd-75b79d922463 | OS::Nova::Server  | CREATE_COMPLETE |
  | VDU2_CP1      | 22d9d536-f1f4-4495-9a69-31be4bce9730 | OS::Neutron::Port | CREATE_COMPLETE |
  | VDU2_CP0      | cf9bbfef-beb9-42ff-94bf-5a367fb8b04d | OS::Neutron::Port | CREATE_COMPLETE |
  +---------------+--------------------------------------+-------------------+-----------------+

4. Scale In VNF
~~~~~~~~~~~~~~~

Execute Scale CLI command and check the number of resources
before and after scaling.
This is to confirm that the number of resources has decreased
after Scale-in.
See `Heat CLI reference`_. for details on Heat CLI commands.


Stack information before scale-in:

Execute following command and confirm that
there are some resources under the VDU_2.

.. code-block:: console

  $ openstack stack resource list VDU_2_ID -c resource_name \
      -c physical_resource_id -c resource_type -c resource_status

Result:

.. code-block:: console

  +---------------+--------------------------------------+-------------------+-----------------+
  | resource_name | physical_resource_id                 | resource_type     | resource_status |
  +---------------+--------------------------------------+-------------------+-----------------+
  | nsatlzzxx2ik  | f0258a82-53a4-4239-932e-2ab18c3b69ae | VDU_2.yaml        | CREATE_COMPLETE |
  | VDU_2         | ed2dd9d1-ffc7-43a3-8efd-75b79d922463 | OS::Nova::Server  | CREATE_COMPLETE |
  | VDU2_CP1      | 22d9d536-f1f4-4495-9a69-31be4bce9730 | OS::Neutron::Port | CREATE_COMPLETE |
  | VDU2_CP0      | cf9bbfef-beb9-42ff-94bf-5a367fb8b04d | OS::Neutron::Port | CREATE_COMPLETE |
  +---------------+--------------------------------------+-------------------+-----------------+

And then, Scale-in VNF can be executed by the following CLI command.

.. code-block:: console

  $ openstack vnflcm scale --type SCALE_IN --aspect-id VDU_2 VNF_INSTANCE_ID


Result:

.. code-block:: console

  Scale request for VNF Instance d57acd9a-34f1-4a2d-a8a0-7013270def45 has been accepted.

Stack information after scale-in:

Execute following command and confirm that no results will be returned.
This means the resources under the VDU_2 have been deleted.


.. code-block:: console

  $ openstack stack resource list VDU_2_ID -c resource_name \
      -c physical_resource_id -c resource_type -c resource_status


Reference
---------

.. _VNF package sample for practical use cases : https://opendev.org/openstack/tacker/src/branch/master/samples/practical_vnf_package
.. _NFV-SOL004 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/004/02.06.01_60/gs_NFV-SOL004v020601p.pdf
.. _TOSCA-Simple-Profile-YAML-v1.2 : http://docs.oasis-open.org/tosca/TOSCA-Simple-Profile-YAML/v1.2/TOSCA-Simple-Profile-YAML-v1.2.html
.. _VNF Package: https://docs.openstack.org/tacker/latest/user/vnf-package.html
.. _cli-legacy-vim : https://docs.openstack.org/tacker/latest/cli/cli-legacy-vim.html#register-vim
.. _TOSCA-1.0-specification : http://docs.oasis-open.org/tosca/TOSCA/v1.0/os/TOSCA-v1.0-os.pdf
.. [#f1] https://forge.etsi.org/rep/nfv/SOL001
.. _NFV-SOL001 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/001/02.06.01_60/gs_NFV-SOL001v020601p.pdf
.. _Node.yaml : https://opendev.org/openstack/tacker/src/branch/master/samples/practical_vnf_package/Definitions/Node.yaml
.. _df_ha.yaml : https://opendev.org/openstack/tacker/src/branch/master/samples/practical_vnf_package/Definitions/df_ha.yaml
.. _df_scalable.yaml : https://opendev.org/openstack/tacker/src/branch/master/samples/practical_vnf_package/Definitions/df_scalable.yaml
.. _ha/ha_hot.yaml : https://opendev.org/openstack/tacker/src/branch/master/samples/practical_vnf_package/BaseHOT/ha/ha_hot.yaml
.. _scalable/scalable_hot.yaml : https://opendev.org/openstack/tacker/src/branch/master/samples/practical_vnf_package/BaseHOT/scalable/scalable_hot.yaml
.. _scalable/VDU_0.yaml : https://opendev.org/openstack/tacker/src/branch/master/samples/practical_vnf_package/BaseHOT/scalable/VDU_0.yaml
.. _scalable/VDU_1.yaml : https://opendev.org/openstack/tacker/src/branch/master/samples/practical_vnf_package/BaseHOT/scalable/VDU_1.yaml
.. _scalable/VDU_2.yaml : https://opendev.org/openstack/tacker/src/branch/master/samples/practical_vnf_package/BaseHOT/scalable/VDU_2.yaml
.. _`lcm_user_data.py` : https://opendev.org/openstack/tacker/src/branch/master/samples/practical_vnf_package/UserData/lcm_user_data.py
.. _TOSCA.meta : https://opendev.org/openstack/tacker/src/branch/master/samples/practical_vnf_package/TOSCA-Metadata/TOSCA.meta
.. _Common.yaml : https://opendev.org/openstack/tacker/src/branch/master/samples/practical_vnf_package/Definitions/Common.yaml
.. _etsi_nfv_sol001_common_types.yaml : https://forge.etsi.org/rep/nfv/SOL001/raw/v2.6.1/etsi_nfv_sol001_common_types.yaml
.. _etsi_nfv_sol001_vnfd_types.yaml : https://forge.etsi.org/rep/nfv/SOL001/raw/v2.6.1/etsi_nfv_sol001_vnfd_types.yaml
.. _mgmt_driver_deploy_k8s_usage_guide : https://docs.openstack.org/tacker/latest/user/mgmt_driver_deploy_k8s_usage_guide.html#openstack-router
.. _Heat CLI reference : https://docs.openstack.org/python-openstackclient/latest/cli/plugin-commands/heat.html
