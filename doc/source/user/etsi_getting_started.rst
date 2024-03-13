..
      Copyright 2014-2015 OpenStack Foundation
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

==============================
Getting Started with v1 Tacker
==============================

Summary
-------

This lecture enables you to:

-  create & delete a sample VNF on the OpenStack with Tacker v1 API

.. note::

  This is a document for Tacker v1 API.
  See :doc:`/user/v2/getting_started/index` for Tacker v2 API.


Following two types of VNF deployment supported by Tacker are introduced in
this lecture.

- :doc:`/user/etsi_vnf_deployment_as_vm_with_tosca`
- :doc:`/user/etsi_vnf_deployment_as_vm_with_user_data`

"VNF Deployment with LCM Operation User Data" is optional.
The part will be clarified with the notation [This is UserData specific part].

The following figure shows a sample VNF used in this lecture.

.. figure:: /_images/etsi-getting-started-sample-vnf.png
    :align: left


.. note::

  VIM config, a VNF package, and instantiation parameters used in this tutorial are placed at the repository.

  - `samples/etsi_getting_started/tosca`_
  - `samples/etsi_getting_started/userdata`_


.. note::

  You can see logs of Tacker with this command:

  .. code-block:: console

    $ sudo journalctl -u devstack@tacker.service
    $ sudo journalctl -u devstack@tacker-conductor.service


Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

Configuration
^^^^^^^^^^^^^

Load credentials for client operations
""""""""""""""""""""""""""""""""""""""

Before any Tacker commands can be run, your credentials need to be sourced.

.. note::

  See `Create OpenStack client environment scripts`_ for details.
  In this document, the settings are as follows:

  .. code-block::

    OS_REGION_NAME=RegionOne
    OS_PROJECT_DOMAIN_ID=default
    OS_CACERT=
    OS_AUTH_URL=http://192.168.56.10/identity
    OS_TENANT_NAME=admin
    OS_USER_DOMAIN_ID=default
    OS_USERNAME=admin
    OS_VOLUME_API_VERSION=3
    OS_AUTH_TYPE=password
    OS_PROJECT_NAME=admin
    OS_PASSWORD=devstack
    OS_IDENTITY_API_VERSION=3


You can confirm that Tacker is available by checking this command works without
error:

.. code-block:: console

  $ openstack vim list


.. note::

  See :doc:`/cli/index` to find all the available commands.


Register VIM
------------

#. Prepare VIM configuration file:

   You can use a setup script for generating VIM configuration or edit it from
   scratch as described in :doc:`/reference/vim_config`.
   This script finds parameters for the configuration, such as user
   name or password, from your environment variables.
   Here is an example of generating OpenStack VIM configuration as
   ``vim_config.yaml``. In this document, ``TACKER_ROOT`` is the root of
   tacker's repository on your server.

   .. code-block:: console

     $ bash TACKER_ROOT/tools/gen_vim_config.sh
     Config for OpenStack VIM 'vim_config.yaml' generated.


   There are several options for configuring parameters from command
   line supported. Refer help with ``-h`` for details.

   You can also use a sample configuration file `vim_config.yaml`_ instead of
   using the script.

   .. code-block:: console

     $ cp TACKER_ROOT/samples/etsi_getting_started/tosca/vim/vim_config.yaml ./
     $ vi vim_config.yaml


   .. literalinclude:: ../../../samples/etsi_getting_started/tosca/vim/vim_config.yaml
            :language: yaml


#. Register Default VIM:

   Once you setup VIM configuration file, you register default VIM via
   ``openstack`` command with ``--is-default`` option.

   .. code-block:: console

     $ openstack vim register --config-file ./vim_config.yaml \
       --is-default --fit-width openstack-admin-vim
     +----------------+-----------------------------------------------------+
     | Field          | Value                                               |
     +----------------+-----------------------------------------------------+
     | auth_cred      | {                                                   |
     |                |     "username": "admin",                            |
     |                |     "user_domain_name": "default",                  |
     |                |     "cert_verify": "True",                          |
     |                |     "project_id": null,                             |
     |                |     "project_name": "admin",                        |
     |                |     "project_domain_name": "default",               |
     |                |     "auth_url": "http://192.168.56.10/identity/v3", |
     |                |     "key_type": "barbican_key",                     |
     |                |     "secret_uuid": "***",                           |
     |                |     "password": "***"                               |
     |                | }                                                   |
     | auth_url       | http://192.168.56.10/identity/v3                    |
     | created_at     | 2023-12-21 07:39:09.617234                          |
     | description    |                                                     |
     | extra          |                                                     |
     | id             | 662e5f4f-3b16-4ca6-b560-28b62dd0e13b                |
     | is_default     | True                                                |
     | name           | openstack-admin-vim                                 |
     | placement_attr | {                                                   |
     |                |     "regions": [                                    |
     |                |         "RegionOne"                                 |
     |                |     ]                                               |
     |                | }                                                   |
     | project_id     | 1994d69783d64c00aadab564038c2fd7                    |
     | status         | ACTIVE                                              |
     | type           | openstack                                           |
     | updated_at     | None                                                |
     | vim_project    | {                                                   |
     |                |     "name": "admin",                                |
     |                |     "project_domain_name": "default"                |
     |                | }                                                   |
     +----------------+-----------------------------------------------------+


#. Confirm that the status of registered VIM is ``ACTIVE`` as ready to use:

   .. code-block:: console

     $ openstack vim list
     +--------------------------------------+---------------------+----------------------------------+-----------+------------+--------+
     | ID                                   | Name                | Tenant_id                        | Type      | Is Default | Status |
     +--------------------------------------+---------------------+----------------------------------+-----------+------------+--------+
     | 662e5f4f-3b16-4ca6-b560-28b62dd0e13b | openstack-admin-vim | 1994d69783d64c00aadab564038c2fd7 | openstack | True       | ACTIVE |
     +--------------------------------------+---------------------+----------------------------------+-----------+------------+--------+


Create and Upload VNF Package
-----------------------------

Prepare VNF Package
^^^^^^^^^^^^^^^^^^^

#. Create VNF Package CSAR directories:

   .. code-block:: console

     $ mkdir -p ./sample_vnf_package_csar/TOSCA-Metadata \
       ./sample_vnf_package_csar/Definitions \
       ./sample_vnf_package_csar/Files/images


   [This is UserData specific part] When using UserData, create the following directories in addition.

   .. code-block:: console

     $ mkdir -p ./sample_vnf_package_csar/BaseHOT/simple \
       ./sample_vnf_package_csar/UserData


#. Create a ``TOSCA.meta`` file:

   .. code-block:: console

     $ vi ./sample_vnf_package_csar/TOSCA-Metadata/TOSCA.meta


   .. literalinclude:: ../../../samples/etsi_getting_started/tosca/sample_vnf_package_csar/TOSCA-Metadata/TOSCA.meta
            :language: text


#. Download image file:

   .. code-block:: console

     $ cd ./sample_vnf_package_csar/Files/images
     $ wget https://download.cirros-cloud.net/0.5.2/cirros-0.5.2-x86_64-disk.img


#. Download ETSI definition files:

   You should set ``${TOSCA_VERSION}`` to one of the appropriate TOSCA service
   template versions (`SOL001`_), e.g., ``export TOSCA_VERSION=v2.6.1``.

   .. important::

     You should also check if the version of TOSCA service template is
     supported by tacker.
     See :doc:`/user/vnfd-sol001` for supported version.


   .. code-block:: console

     $ cd -
     $ cd ./sample_vnf_package_csar/Definitions
     $ wget https://forge.etsi.org/rep/nfv/SOL001/raw/${TOSCA_VERSION}/etsi_nfv_sol001_common_types.yaml
     $ wget https://forge.etsi.org/rep/nfv/SOL001/raw/${TOSCA_VERSION}/etsi_nfv_sol001_vnfd_types.yaml


#. Create VNFD files:

   -  Create ``sample_vnfd_top.yaml``

      .. code-block:: console

        $ vi ./sample_vnfd_top.yaml

      .. literalinclude:: ../../../samples/etsi_getting_started/tosca/sample_vnf_package_csar/Definitions/sample_vnfd_top.yaml
               :language: yaml


   -  Create ``sample_vnfd_types.yaml``

      .. code-block:: console

        $ vi ./sample_vnfd_types.yaml


      .. literalinclude:: ../../../samples/etsi_getting_started/tosca/sample_vnf_package_csar/Definitions/sample_vnfd_types.yaml
               :language: yaml


      .. note::

        ``description_id`` shall be globally unique, i.e., you cannot create
        multiple VNFDs with the same ``description_id``.


   -  Create ``sample_vnfd_df_simple.yaml``

      .. code-block:: console

        $ vi ./sample_vnfd_df_simple.yaml


      .. literalinclude:: ../../../samples/etsi_getting_started/tosca/sample_vnf_package_csar/Definitions/sample_vnfd_df_simple.yaml
               :language: yaml


      .. note::

        The ``flavour_description`` should be updated by the property in "VNF" but
        Tacker cannot handle it. After the instantiation, the default value in
        ``sample_vnfd_types.yaml`` is always used.


#. [This is UserData specific part] Create BaseHOT files:

   .. code-block:: console

     $ cd -
     $ vi ./sample_vnf_package_csar/BaseHOT/simple/sample_lcm_with_user_data_hot.yaml


   .. literalinclude:: ../../../samples/etsi_getting_started/userdata/sample_vnf_package_csar/BaseHOT/simple/sample_lcm_with_user_data_hot.yaml
            :language: yaml


#. [This is UserData specific part] Create UserData files:

   .. code-block:: console

     $ cd ./sample_vnf_package_csar/UserData/
     $ touch ./__init__.py
     $ vi ./lcm_user_data.py


   .. literalinclude:: ../../../samples/etsi_getting_started/userdata/sample_vnf_package_csar/UserData/lcm_user_data.py
            :language: python


#. Compress the VNF Package CSAR to zip:

   .. code-block:: console

     $ cd -
     $ cd ./sample_vnf_package_csar
     $ zip sample_vnf_package_csar.zip -r Definitions/ Files/ TOSCA-Metadata/


   The contents of the zip file should look something like this.

   .. code-block:: console

     $ unzip -Z -1 sample_vnf_package_csar.zip
     Definitions/
     Definitions/etsi_nfv_sol001_vnfd_types.yaml
     Definitions/sample_vnfd_top.yaml
     Definitions/etsi_nfv_sol001_common_types.yaml
     Definitions/sample_vnfd_types.yaml
     Definitions/sample_vnfd_df_simple.yaml
     Files/
     Files/images/
     Files/images/cirros-0.5.2-x86_64-disk.img
     TOSCA-Metadata/
     TOSCA-Metadata/TOSCA.meta


   - [This is UserData specific part] When using UserData, add ``BaseHOT`` and ``UserData`` directories.

     .. code-block:: console

       $ zip sample_vnf_package_csar.zip -r BaseHOT/ UserData/


     The contents of the zip file should look something like this.

     .. code-block:: console

       $ unzip -Z -1 sample_vnf_package_csar.zip
       BaseHOT/
       BaseHOT/simple/
       BaseHOT/simple/sample_lcm_with_user_data_hot.yaml
       Definitions/
       Definitions/etsi_nfv_sol001_vnfd_types.yaml
       Definitions/sample_vnfd_top.yaml
       Definitions/etsi_nfv_sol001_common_types.yaml
       Definitions/sample_vnfd_types.yaml
       Definitions/sample_vnfd_df_simple.yaml
       Files/
       Files/images/
       Files/images/cirros-0.5.2-x86_64-disk.img
       TOSCA-Metadata/
       TOSCA-Metadata/TOSCA.meta
       UserData/
       UserData/lcm_user_data.py
       UserData/__init__.py


   Here, you can find the structure of the sample VNF Package CSAR as a
   zip file.


Create VNF Package
^^^^^^^^^^^^^^^^^^

#. Execute vnfpkgm create:

   Take a note of "VNF Package ID" as it will be used in the next step.

   .. code-block:: console

     $ cd -

   .. code-block:: console

     $ openstack vnf package create
     +-------------------+-------------------------------------------------------------------------------------------------+
     | Field             | Value                                                                                           |
     +-------------------+-------------------------------------------------------------------------------------------------+
     | ID                | 156f1c4f-bfe2-492b-a079-a1bad32c0c3d                                                            |
     | Links             | {                                                                                               |
     |                   |     "self": {                                                                                   |
     |                   |         "href": "/vnfpkgm/v1/vnf_packages/156f1c4f-bfe2-492b-a079-a1bad32c0c3d"                 |
     |                   |     },                                                                                          |
     |                   |     "packageContent": {                                                                         |
     |                   |         "href": "/vnfpkgm/v1/vnf_packages/156f1c4f-bfe2-492b-a079-a1bad32c0c3d/package_content" |
     |                   |     }                                                                                           |
     |                   | }                                                                                               |
     | Onboarding State  | CREATED                                                                                         |
     | Operational State | DISABLED                                                                                        |
     | Usage State       | NOT_IN_USE                                                                                      |
     | User Defined Data | {}                                                                                              |
     +-------------------+-------------------------------------------------------------------------------------------------+


Upload VNF Package
^^^^^^^^^^^^^^^^^^

#. Execute vnfpkgm upload:

   The "VNF Package ID" ``156f1c4f-bfe2-492b-a079-a1bad32c0c3d`` needs to be
   replaced with the appropriate one that was obtained from `Create VNF
   Package`.

   .. code-block:: console

     $ openstack vnf package upload \
       --path ./sample_vnf_package_csar/sample_vnf_package_csar.zip \
       156f1c4f-bfe2-492b-a079-a1bad32c0c3d
     Upload request for VNF package 156f1c4f-bfe2-492b-a079-a1bad32c0c3d has been accepted.


Check the created VNF Package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Confirm the "Onboarding State" to be ``ONBOARDED`` (it may take more than 30
   seconds):

   .. code-block:: console

     $ openstack vnf package list
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
     | Id                                   | Vnf Product Name | Onboarding State | Usage State | Operational State | Links                                                                                           |
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
     | 156f1c4f-bfe2-492b-a079-a1bad32c0c3d |                  | PROCESSING       | NOT_IN_USE  | DISABLED          | {                                                                                               |
     |                                      |                  |                  |             |                   |     "self": {                                                                                   |
     |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/156f1c4f-bfe2-492b-a079-a1bad32c0c3d"                 |
     |                                      |                  |                  |             |                   |     },                                                                                          |
     |                                      |                  |                  |             |                   |     "packageContent": {                                                                         |
     |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/156f1c4f-bfe2-492b-a079-a1bad32c0c3d/package_content" |
     |                                      |                  |                  |             |                   |     }                                                                                           |
     |                                      |                  |                  |             |                   | }                                                                                               |
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+

     $ openstack vnf package list
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
     | Id                                   | Vnf Product Name | Onboarding State | Usage State | Operational State | Links                                                                                           |
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
     | 156f1c4f-bfe2-492b-a079-a1bad32c0c3d | Sample VNF       | ONBOARDED        | NOT_IN_USE  | ENABLED           | {                                                                                               |
     |                                      |                  |                  |             |                   |     "self": {                                                                                   |
     |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/156f1c4f-bfe2-492b-a079-a1bad32c0c3d"                 |
     |                                      |                  |                  |             |                   |     },                                                                                          |
     |                                      |                  |                  |             |                   |     "packageContent": {                                                                         |
     |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/156f1c4f-bfe2-492b-a079-a1bad32c0c3d/package_content" |
     |                                      |                  |                  |             |                   |     }                                                                                           |
     |                                      |                  |                  |             |                   | }                                                                                               |
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+


Create & Instantiate VNF
------------------------

Create VNF
^^^^^^^^^^

#. Find "VNFD ID" to create VNF:

   The "VNFD-ID" can be found to be ``b1bb0ce7-ebca-4fa7-95ed-4840d70a1177`` in
   the example.

   .. code-block:: console

     $ openstack vnf package show \
       156f1c4f-bfe2-492b-a079-a1bad32c0c3d -c 'VNFD ID'
     +---------+--------------------------------------+
     | Field   | Value                                |
     +---------+--------------------------------------+
     | VNFD ID | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177 |
     +---------+--------------------------------------+


#. Create VNF:

   The "VNFD ID" ``b1bb0ce7-ebca-4fa7-95ed-4840d70a1177`` needs to be replaced
   with the appropriate one.

   .. code-block:: console

     $ openstack vnflcm create b1bb0ce7-ebca-4fa7-95ed-4840d70a1177
     +-----------------------------+------------------------------------------------------------------------------------------------------------------+
     | Field                       | Value                                                                                                            |
     +-----------------------------+------------------------------------------------------------------------------------------------------------------+
     | ID                          | 810d8c9b-e467-4b06-9265-ac9dce015fce                                                                             |
     | Instantiation State         | NOT_INSTANTIATED                                                                                                 |
     | Links                       | {                                                                                                                |
     |                             |     "self": {                                                                                                    |
     |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/810d8c9b-e467-4b06-9265-ac9dce015fce"             |
     |                             |     },                                                                                                           |
     |                             |     "instantiate": {                                                                                             |
     |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/810d8c9b-e467-4b06-9265-ac9dce015fce/instantiate" |
     |                             |     }                                                                                                            |
     |                             | }                                                                                                                |
     | VNF Configurable Properties |                                                                                                                  |
     | VNF Instance Description    |                                                                                                                  |
     | VNF Instance Name           | vnf-810d8c9b-e467-4b06-9265-ac9dce015fce                                                                         |
     | VNF Product Name            | Sample VNF                                                                                                       |
     | VNF Provider                | Company                                                                                                          |
     | VNF Software Version        | 1.0                                                                                                              |
     | VNFD ID                     | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177                                                                             |
     | VNFD Version                | 1.0                                                                                                              |
     | vnfPkgId                    |                                                                                                                  |
     +-----------------------------+------------------------------------------------------------------------------------------------------------------+


Instantiate VNF
^^^^^^^^^^^^^^^

#. Create ``<param-file>``:

   Required parameter:

   -  flavourID

   Optional parametes:

   -  instantiationLevelId
   -  extVirtualLinks
   -  extManagedVirtualLinks
   -  vimConnectionInfo

   .. note::

     You can skip ``vimConnectionInfo`` only when you have the default VIM.


   A sample ``<param-file>`` named as ``sample_param_file.json`` with
   minimal parametes:

   .. code-block:: console

     $ vi ./sample_param_file.json


   - When using TOSCA, use the following parameters.

     .. literalinclude:: ../../../samples/etsi_getting_started/tosca/lcm_instantiate_request/sample_param_file.json
              :language: json


   - [This is UserData specific part] When using UserData, use the following parameters instead.

     .. literalinclude:: ../../../samples/etsi_getting_started/userdata/lcm_instantiate_request/sample_param_file.json
              :language: json


   ``${network_uuid}``, ``${subnet_uuid}`` and ``${vim_uuid}`` should be
   replaced with the uuid of the network to use, the uuid of the subnet to use
   and the uuid of the VIM to use, respectively.

   .. hint::

     You can find uuids of the network and the corresponding subnet with
     `network command`_:

     .. code-block:: console

       $ openstack network list


#. Instantiate VNF:

   The "ID of vnf instance" and "path to <param-file>" are needed to
   instantiate vnf.

   .. code-block:: console

     $ openstack vnflcm instantiate \
       810d8c9b-e467-4b06-9265-ac9dce015fce ./sample_param_file.json
     Instantiate request for VNF Instance 810d8c9b-e467-4b06-9265-ac9dce015fce has been accepted.


   Check the details of the instantiated vnf.

   .. code-block:: console

     $ openstack vnflcm list
     +--------------------------------------+------------------------------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
     | ID                                   | VNF Instance Name                        | Instantiation State | VNF Provider | VNF Software Version | VNF Product Name | VNFD ID                              |
     +--------------------------------------+------------------------------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
     | 810d8c9b-e467-4b06-9265-ac9dce015fce | vnf-810d8c9b-e467-4b06-9265-ac9dce015fce | INSTANTIATED        | Company      | 1.0                  | Sample VNF       | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177 |
     +--------------------------------------+------------------------------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+

     $ openstack vnflcm show 810d8c9b-e467-4b06-9265-ac9dce015fce
     +-----------------------------+----------------------------------------------------------------------------------------------------------------------+
     | Field                       | Value                                                                                                                |
     +-----------------------------+----------------------------------------------------------------------------------------------------------------------+
     | ID                          | 810d8c9b-e467-4b06-9265-ac9dce015fce                                                                                 |
     | Instantiated Vnf Info       | {                                                                                                                    |
     |                             |     "flavourId": "simple",                                                                                           |
     |                             |     "vnfState": "STARTED",                                                                                           |
     |                             |     "extCpInfo": [],                                                                                                 |
     |                             |     "vnfcResourceInfo": [                                                                                            |
     |                             |         {                                                                                                            |
     |                             |             "id": "6894448f-4a88-45ec-801f-4ef455e8a613",                                                            |
     |                             |             "vduId": "VDU1",                                                                                         |
     |                             |             "computeResource": {                                                                                     |
     |                             |                 "vimConnectionId": "662e5f4f-3b16-4ca6-b560-28b62dd0e13b",                                           |
     |                             |                 "resourceId": "cfb5d6de-90a1-433a-9af4-1159ca279e27",                                                |
     |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                           |
     |                             |             },                                                                                                       |
     |                             |             "storageResourceIds": [],                                                                                |
     |                             |             "vnfcCpInfo": [                                                                                          |
     |                             |                 {                                                                                                    |
     |                             |                     "id": "b6dffe31-2e4b-44e6-8ddd-b94608a9210b",                                                    |
     |                             |                     "cpdId": "CP1",                                                                                  |
     |                             |                     "vnfExtCpId": null,                                                                              |
     |                             |                     "vnfLinkPortId": "5040ae0d-ef8b-4d12-b96b-d9d05a0ba7fe"                                          |
     |                             |                 }                                                                                                    |
     |                             |             ]                                                                                                        |
     |                             |         }                                                                                                            |
     |                             |     ],                                                                                                               |
     |                             |     "vnfVirtualLinkResourceInfo": [                                                                                  |
     |                             |         {                                                                                                            |
     |                             |             "id": "4b67e6f9-8133-4f7d-b384-abd64f9bcbac",                                                            |
     |                             |             "vnfVirtualLinkDescId": "internalVL1",                                                                   |
     |                             |             "networkResource": {                                                                                     |
     |                             |                 "vimConnectionId": "662e5f4f-3b16-4ca6-b560-28b62dd0e13b",                                           |
     |                             |                 "resourceId": "d04beb5f-b29a-4f7e-b32b-7ea669afa3eb",                                                |
     |                             |                 "vimLevelResourceType": "OS::Neutron::Net"                                                           |
     |                             |             },                                                                                                       |
     |                             |             "vnfLinkPorts": [                                                                                        |
     |                             |                 {                                                                                                    |
     |                             |                     "id": "5040ae0d-ef8b-4d12-b96b-d9d05a0ba7fe",                                                    |
     |                             |                     "resourceHandle": {                                                                              |
     |                             |                         "vimConnectionId": "662e5f4f-3b16-4ca6-b560-28b62dd0e13b",                                   |
     |                             |                         "resourceId": "84edd7c7-a02f-4f25-be2a-a0ee5b1c8dc7",                                        |
     |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                  |
     |                             |                     },                                                                                               |
     |                             |                     "cpInstanceId": "b6dffe31-2e4b-44e6-8ddd-b94608a9210b"                                           |
     |                             |                 }                                                                                                    |
     |                             |             ]                                                                                                        |
     |                             |         }                                                                                                            |
     |                             |     ],                                                                                                               |
     |                             |     "vnfcInfo": [                                                                                                    |
     |                             |         {                                                                                                            |
     |                             |             "id": "6c0ba2a3-3f26-4ba0-9b4f-db609b2e843c",                                                            |
     |                             |             "vduId": "VDU1",                                                                                         |
     |                             |             "vnfcState": "STARTED"                                                                                   |
     |                             |         }                                                                                                            |
     |                             |     ],                                                                                                               |
     |                             |     "additionalParams": {}                                                                                           |
     |                             | }                                                                                                                    |
     | Instantiation State         | INSTANTIATED                                                                                                         |
     | Links                       | {                                                                                                                    |
     |                             |     "self": {                                                                                                        |
     |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/810d8c9b-e467-4b06-9265-ac9dce015fce"                 |
     |                             |     },                                                                                                               |
     |                             |     "terminate": {                                                                                                   |
     |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/810d8c9b-e467-4b06-9265-ac9dce015fce/terminate"       |
     |                             |     },                                                                                                               |
     |                             |     "heal": {                                                                                                        |
     |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/810d8c9b-e467-4b06-9265-ac9dce015fce/heal"            |
     |                             |     },                                                                                                               |
     |                             |     "changeExtConn": {                                                                                               |
     |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/810d8c9b-e467-4b06-9265-ac9dce015fce/change_ext_conn" |
     |                             |     }                                                                                                                |
     |                             | }                                                                                                                    |
     | VIM Connection Info         | [                                                                                                                    |
     |                             |     {                                                                                                                |
     |                             |         "id": "e24f9796-a8e9-4cb0-85ce-5920dcddafa1",                                                                |
     |                             |         "vimId": "662e5f4f-3b16-4ca6-b560-28b62dd0e13b",                                                             |
     |                             |         "vimType": "ETSINFV.OPENSTACK_KEYSTONE.v_2",                                                                 |
     |                             |         "interfaceInfo": {},                                                                                         |
     |                             |         "accessInfo": {},                                                                                            |
     |                             |         "extra": {}                                                                                                  |
     |                             |     },                                                                                                               |
     |                             |     {                                                                                                                |
     |                             |         "id": "67820f17-a82a-4e3a-b200-8ef119646749",                                                                |
     |                             |         "vimId": "662e5f4f-3b16-4ca6-b560-28b62dd0e13b",                                                             |
     |                             |         "vimType": "openstack",                                                                                      |
     |                             |         "interfaceInfo": {},                                                                                         |
     |                             |         "accessInfo": {},                                                                                            |
     |                             |         "extra": {}                                                                                                  |
     |                             |     }                                                                                                                |
     |                             | ]                                                                                                                    |
     | VNF Configurable Properties |                                                                                                                      |
     | VNF Instance Description    |                                                                                                                      |
     | VNF Instance Name           | vnf-810d8c9b-e467-4b06-9265-ac9dce015fce                                                                             |
     | VNF Product Name            | Sample VNF                                                                                                           |
     | VNF Provider                | Company                                                                                                              |
     | VNF Software Version        | 1.0                                                                                                                  |
     | VNFD ID                     | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177                                                                                 |
     | VNFD Version                | 1.0                                                                                                                  |
     | metadata                    | tenant=admin                                                                                                         |
     | vnfPkgId                    |                                                                                                                      |
     +-----------------------------+----------------------------------------------------------------------------------------------------------------------+


Terminate & Delete VNF
----------------------

Terminate VNF
^^^^^^^^^^^^^

#. Check the VNF Instance ID to terminate:

   .. code-block:: console

     $ openstack vnflcm list
     +--------------------------------------+------------------------------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
     | ID                                   | VNF Instance Name                        | Instantiation State | VNF Provider | VNF Software Version | VNF Product Name | VNFD ID                              |
     +--------------------------------------+------------------------------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
     | 810d8c9b-e467-4b06-9265-ac9dce015fce | vnf-810d8c9b-e467-4b06-9265-ac9dce015fce | INSTANTIATED        | Company      | 1.0                  | Sample VNF       | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177 |
     +--------------------------------------+------------------------------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+


#. Terminate VNF Instance:

   Execute terminate command:

   .. code-block:: console

     $ openstack vnflcm terminate 810d8c9b-e467-4b06-9265-ac9dce015fce
     Terminate request for VNF Instance '810d8c9b-e467-4b06-9265-ac9dce015fce' has been accepted.


   Check the status of VNF Instance:

   .. code-block:: console

     $ openstack vnflcm list
     +--------------------------------------+------------------------------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
     | ID                                   | VNF Instance Name                        | Instantiation State | VNF Provider | VNF Software Version | VNF Product Name | VNFD ID                              |
     +--------------------------------------+------------------------------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
     | 810d8c9b-e467-4b06-9265-ac9dce015fce | vnf-810d8c9b-e467-4b06-9265-ac9dce015fce | NOT_INSTANTIATED    | Company      | 1.0                  | Sample VNF       | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177 |
     +--------------------------------------+------------------------------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+


Delete VNF
^^^^^^^^^^

#. Delete VNF Instance:

   .. code-block:: console

     $ openstack vnflcm delete 810d8c9b-e467-4b06-9265-ac9dce015fce
     Vnf instance '810d8c9b-e467-4b06-9265-ac9dce015fce' is deleted successfully


Delete VNF Package
------------------

#. Delete VNF Package:

   Check the VNF Package ID to delete:

   .. code-block:: console

     $ openstack vnf package list
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
     | Id                                   | Vnf Product Name | Onboarding State | Usage State | Operational State | Links                                                                                           |
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
     | 156f1c4f-bfe2-492b-a079-a1bad32c0c3d | Sample VNF       | ONBOARDED        | NOT_IN_USE  | ENABLED           | {                                                                                               |
     |                                      |                  |                  |             |                   |     "self": {                                                                                   |
     |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/156f1c4f-bfe2-492b-a079-a1bad32c0c3d"                 |
     |                                      |                  |                  |             |                   |     },                                                                                          |
     |                                      |                  |                  |             |                   |     "packageContent": {                                                                         |
     |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/156f1c4f-bfe2-492b-a079-a1bad32c0c3d/package_content" |
     |                                      |                  |                  |             |                   |     }                                                                                           |
     |                                      |                  |                  |             |                   | }                                                                                               |
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+


   Update the Operational State to ``DISABLED``:

   .. code-block:: console

     $ openstack vnf package update --operational-state 'DISABLED' \
       156f1c4f-bfe2-492b-a079-a1bad32c0c3d
     +-------------------+----------+
     | Field             | Value    |
     +-------------------+----------+
     | Operational State | DISABLED |
     +-------------------+----------+


   Check the Operational State to be changed:

   .. code-block:: console

     $ openstack vnf package list
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
     | Id                                   | Vnf Product Name | Onboarding State | Usage State | Operational State | Links                                                                                           |
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
     | 156f1c4f-bfe2-492b-a079-a1bad32c0c3d | Sample VNF       | ONBOARDED        | NOT_IN_USE  | DISABLED          | {                                                                                               |
     |                                      |                  |                  |             |                   |     "self": {                                                                                   |
     |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/156f1c4f-bfe2-492b-a079-a1bad32c0c3d"                 |
     |                                      |                  |                  |             |                   |     },                                                                                          |
     |                                      |                  |                  |             |                   |     "packageContent": {                                                                         |
     |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/156f1c4f-bfe2-492b-a079-a1bad32c0c3d/package_content" |
     |                                      |                  |                  |             |                   |     }                                                                                           |
     |                                      |                  |                  |             |                   | }                                                                                               |
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+


   Delete the VNF Package:

   .. code-block:: console

     $ openstack vnf package delete 156f1c4f-bfe2-492b-a079-a1bad32c0c3d
     All specified vnf-package(s) deleted successfully


Trouble Shooting
----------------

-  Neutron QoSPlugin error

   .. code-block:: console

     Vnf instantiation failed for vnf 810d8c9b-e467-4b06-9265-ac9dce015fce, error: ERROR: HEAT-E99001 Service neutron is not available for resource type OS::Neutron::QoSPolicy, reason: Required extension qos in neutron service is not available.


   #. Edit ``/etc/neutron/neutron.conf``:

      .. code-block:: console

        $ sudo vi /etc/neutron/neutron.conf


      .. code-block:: diff

        - service_plugins = ovn-router,networking_sfc.services.flowclassifier.plugin.FlowClassifierPlugin,networking_sfc.services.sfc.plugin.SfcPlugin
        + service_plugins = ovn-router,networking_sfc.services.flowclassifier.plugin.FlowClassifierPlugin,networking_sfc.services.sfc.plugin.SfcPlugin,neutron.services.qos.qos_plugin.QoSPlugin,qos


   #. Edit ``/etc/neutron/plugins/ml2/ml2_conf.ini``:

      .. code-block:: console

        $ sudo vi /etc/neutron/plugins/ml2/ml2_conf.ini


      .. code-block:: diff

        - extension_drivers = port_security
        + extension_drivers = port_security,qos


   #. Restart neutron services:

      .. code-block:: console

        $ sudo systemctl restart devstack@q-*


-  Error in networking-sfc

   #. Disable networking-sfc by editting ``/etc/neutron/neutron.conf``:

      .. code-block:: console

        $ sudo vi /etc/neutron/neutron.conf


      .. code-block:: diff

        - service_plugins = ovn-router,networking_sfc.services.flowclassifier.plugin.FlowClassifierPlugin,networking_sfc.services.sfc.plugin.SfcPlugin,neutron.services.qos.qos_plugin.QoSPlugin,qos
        + service_plugins = ovn-router,neutron.services.qos.qos_plugin.QoSPlugin

        - [sfc]
        - drivers = ovs
        - [flowclassifier]
        - drivers = ovs


   #. Edit ``/etc/neutron/plugins/ml2/ml2_conf.ini``:

      .. code-block:: console

        $ sudo vi /etc/neutron/plugins/ml2/ml2_conf.ini


      .. code-block:: diff

        - [agent]
        - extensions = sfc


   #. Restart neutron services:

      .. code-block:: console

        $ sudo systemctl restart devstack@q-*


.. _samples/etsi_getting_started/tosca:
  https://opendev.org/openstack/tacker/src/branch/master/samples/etsi_getting_started/tosca
.. _samples/etsi_getting_started/userdata:
  https://opendev.org/openstack/tacker/src/branch/master/samples/etsi_getting_started/userdata
.. _Create OpenStack client environment scripts:
  https://docs.openstack.org/keystone/latest/install/keystone-openrc-rdo.html
.. _vim_config.yaml:
  https://opendev.org/openstack/tacker/src/branch/master/samples/etsi_getting_started/tosca/vim/vim_config.yaml
.. _SOL001: https://forge.etsi.org/rep/nfv/SOL001
.. _network command: https://docs.openstack.org/python-openstackclient/latest/cli/command-objects/network.html
