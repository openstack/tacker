============================================
ETSI NFV-SOL VNF Deployment as VM with TOSCA
============================================

This document describes how to deploy VNF as VM with TOSCA
in Tacker v1 API using CLI commands.

.. note::

  This is a document for Tacker v1 API.
  Please note that this is not supported by Tacker v2 API.


Overview
--------

The diagram below shows an overview of the VNF deployment.

1. Request create VNF

   A user requests tacker-server to create a VNF with tacker-client by
   uploading a VNF Package and requesting ``create VNF``. The VNF Package
   should contain ``VNFD``. The detailed explanation of ``VNFD`` can be found
   in :doc:`/user/vnf-package`.

2. Request instantiate VNF

   A user requests tacker-server to instantiate the created VNF by requesting
   ``instantiate VNF`` with instantiate parameters.

3. Call OpenStack Heat API

   Upon receiving a request from tacker-client, tacker-server redirects it to
   tacker-conductor. In tacker-conductor, the request is redirected again to
   an appropriate infra-driver (in this case OpenStack infra-driver) according
   to the contents of the instantiate parameters. Then, OpenStack infra-driver
   calls OpenStack Heat APIs to create a VM as a VNF.

4. Create a VM

   OpenStack Heat creates a VM according to the API calls.

.. figure:: /_images/etsi_vnf_deployment_as_vm_with_tosca.png


Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

A default VIM should be registered according to
:doc:`/cli/cli-legacy-vim`.

As an example, you can register default VIM as follow.

.. code-block:: console

  $ cat vim_config.yaml
  auth_url: "http://192.168.56.10/identity"
  username: "admin"
  password: "devstack"
  project_name: "admin"
  domain_name: "default"
  project_domain_name: "default"
  user_domain_name: "default"
  cert_verify: "True"

  $ openstack vim register --config-file vim_config.yaml \
    --is-default openstack-admin-vim
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


The VNF Package(sample_vnf_package_csar.zip) used below is prepared
by referring to :doc:`/user/vnf-package`.

As an example, you can create a VNF Package as follow.

.. code-block:: console

  $ cd TACKER_ROOT/samples/etsi_getting_started/tosca/sample_vnf_package_csar
  $ zip sample_vnf_package_csar.zip -r Definitions/ Files/ TOSCA-Metadata/
  updating: Definitions/ (stored 0%)
  updating: Definitions/sample_vnfd_types.yaml (deflated 71%)
  updating: Definitions/etsi_nfv_sol001_vnfd_types.yaml (deflated 84%)
  updating: Definitions/etsi_nfv_sol001_common_types.yaml (deflated 77%)
  updating: Definitions/sample_vnfd_df_simple.yaml (deflated 66%)
  updating: Definitions/sample_vnfd_top.yaml (deflated 55%)
  updating: Files/ (stored 0%)
  updating: Files/images/ (stored 0%)
  updating: Files/images/cirros-0.5.2-x86_64-disk.img (deflated 3%)
  updating: TOSCA-Metadata/ (stored 0%)
  updating: TOSCA-Metadata/TOSCA.meta (deflated 15%)
  $ ll
  ...
  drwxr-xr-x 2 stack stack     4096 Dec 21 08:50 Definitions/
  drwxr-xr-x 3 stack stack     4096 Dec 21 03:53 Files/
  -rw-rw-r-- 1 stack stack 15761428 Dec 21 08:50 sample_vnf_package_csar.zip
  drwxr-xr-x 2 stack stack     4096 Dec 21 07:41 TOSCA-Metadata/


.. note::

  In this document, ``TACKER_ROOT`` is the root of tacker's repository on
  the server.


After you have done the above, you will have the sample VNF package
`sample_vnf_package_csar.zip`.


VNF Deployment Procedure as VM
------------------------------

In order to deploy VNF as VM, it is necessary to execute
the following procedure.
Details of CLI commands are described in
:doc:`/cli/cli-etsi-vnfpkgm` and :doc:`/cli/cli-etsi-vnflcm`.


1. Create VNF Package Info
^^^^^^^^^^^^^^^^^^^^^^^^^^

Execute the following CLI command to create VNF Package.

.. code-block:: console

  $ openstack vnf package create


Result:

.. code-block:: console

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


After that, execute the following CLI command and confirm that
VNF Package creation was successful.

* Confirm that the 'Onboarding State' is 'CREATED'.
* Confirm that the 'Operational State' is 'DISABLED'.
* Confirm that the 'Usage State' is 'NOT_IN_USE'.

.. code-block:: console

  $ openstack vnf package show VNF_PACKAGE_ID \
    -c 'Onboarding State' -c 'Operational State' -c 'Usage State'


Result:

.. code-block:: console

  +-------------------+------------+
  | Field             | Value      |
  +-------------------+------------+
  | Onboarding State  | CREATED    |
  | Operational State | DISABLED   |
  | Usage State       | NOT_IN_USE |
  +-------------------+------------+


2. Upload VNF Package
^^^^^^^^^^^^^^^^^^^^^

Execute the following CLI command to upload VNF Package.

.. code-block:: console

  $ openstack vnf package upload --path sample_vnf_package_csar.zip VNF_PACKAGE_ID


Result:

.. code-block:: console

  Upload request for VNF package 156f1c4f-bfe2-492b-a079-a1bad32c0c3d has been accepted.


After that, execute the following CLI command and confirm that
VNF Package uploading was successful.

* Confirm that the 'Onboarding State' is 'ONBOARDED'.
* Confirm that the 'Operational State' is 'ENABLED'.
* Confirm that the 'Usage State' is 'NOT_IN_USE'.
* Take a note of the 'VNFD ID' because you will need it in the next
  'Create VNF Identifier'.

.. note::

  The state of 'Onboarding State' changes in the order of
  'UPLOADING', 'PROCESSING', 'ONBOARDED'.


.. code-block:: console

  $ openstack vnf package show VNF_PACKAGE_ID \
    -c 'Onboarding State' -c 'Operational State' -c 'Usage State' -c 'VNFD ID'


Result:

.. code-block:: console

  +-------------------+--------------------------------------+
  | Field             | Value                                |
  +-------------------+--------------------------------------+
  | Onboarding State  | ONBOARDED                            |
  | Operational State | ENABLED                              |
  | Usage State       | NOT_IN_USE                           |
  | VNFD ID           | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177 |
  +-------------------+--------------------------------------+


3. Create VNF Identifier
^^^^^^^^^^^^^^^^^^^^^^^^

Execute the following CLI command to create a VNF instance.

.. code-block:: console

  $ openstack vnflcm create VNFD_ID


Result:

.. code-block:: console

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


After that, execute the following CLI command and confirm that
VNF instance creation was successful.

* Confirm that the 'Usage State' of the VNF Package is 'IN_USE'.
* Confirm that the 'Instantiation State' of the VNF instance
  is 'NOT_INSTANTIATED'.

.. code-block:: console

  $ openstack vnf package show VNF_PACKAGE_ID -c 'Usage State'


Result:

.. code-block:: console

  +-------------+--------+
  | Field       | Value  |
  +-------------+--------+
  | Usage State | IN_USE |
  +-------------+--------+


.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID -c 'Instantiation State'


Result:

.. code-block:: console

  +---------------------+------------------+
  | Field               | Value            |
  +---------------------+------------------+
  | Instantiation State | NOT_INSTANTIATED |
  +---------------------+------------------+


4. Instantiate VNF
^^^^^^^^^^^^^^^^^^

Create a sample_param_file.json file with the following format.
This is the file that defines the parameters for an instantiate request.
These parameters will be set in the body of the instantiate request.

Required parameter:

* flavourId

.. note::

  Details of flavourId is described in :doc:`/user/vnfd-sol001`.


Optional parameters:

* instantiationLevelId
* extVirtualLinks
* extManagedVirtualLinks
* vimConnectionInfo
* localizationLanguage
* additionalParams
* extensions

.. note::

  You can skip ``vimConnectionInfo`` only when you have
  the default VIM described in :doc:`/cli/cli-legacy-vim`.


.. note::

  This operation can specify the ``vimConnectionInfo``
  for the VNF instance.
  Even if this operation specify multiple ``vimConnectionInfo``
  associated with one VNF instance, only one of them will be used for
  life cycle management operations.


An example of a param file with only required parameters:

.. code-block:: console

  {
    "flavourId": "simple"
  }


An example of a param file with optional parameters:

.. code-block:: console

  {
    "flavourId": "simple",
    "instantiationLevelId": "instantiation_level_1",
    "extVirtualLinks": [
      {
        "id": "279b0e12-2cc7-48d3-89dc-c58369841763",
        "vimConnectionId": "4db40866-054f-472d-b559-811e5aa7195c",
        "resourceProviderId": "Company",
        "resourceId": "6a3aeb3a-fb8b-4d27-a5f1-4f148aeb303f",
        "extCps": [
          {
            "cpdId": "VDU1_CP1",
            "cpConfig": {
              "VDU1_CP1": {
                "parentCpConfigId": "a9d72e2b-9b2f-48b8-9ca0-217ab3ba6f33",
                "cpProtocolData": [
                  {
                    "layerProtocol": "IP_OVER_ETHERNET",
                    "ipOverEthernet": {
                      "ipAddresses": [
                        {
                          "type": "IPV4",
                          "numDynamicAddresses": 1,
                          "subnetId": "649c956c-1516-4d92-a6bc-ce936d8a880d"
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        ],
        "extLinkPorts": [
          {
            "id": "2871f033-5e38-4f5f-af26-09c6390648a8",
            "resourceHandle": {
              "resourceId": "389ade82-7618-4b42-bc90-5ebbac0863cf"
            }
          }
        ]
      }
    ],
    "extManagedVirtualLinks": [
      {
        "id": "c381e923-6208-43ac-acc9-f3afec76535a",
        "vnfVirtualLinkDescId": "internalVL1",
        "vimConnectionId": "4db40866-054f-472d-b559-811e5aa7195c",
        "resourceProviderId": "Company",
        "resourceId": "9a94da3c-239f-469d-8cf9-5313a4e3961a",
        "extManagedMultisiteVirtualLinkId": "f850522e-c124-4ed9-8027-f15abc22e21d"
      }
    ],
    "vimConnectionInfo": [
      {
        "id": "e24f9796-a8e9-4cb0-85ce-5920dcddafa1",
        "vimId": "8a0fd79d-e224-4c27-85f5-ee79c6e0d870",
        "vimType": "ETSINFV.OPENSTACK_KEYSTONE.v_2"
      }
    ],
    "localizationLanguage": "ja",
    "additionalParams": {
      "key": "value"
    },
    "extensions": {
      "key": "value"
    }
  }


samlple_param_file.json used in this document is below.

.. literalinclude:: ../../../samples/etsi_getting_started/tosca/lcm_instantiate_request/sample_param_file.json
         :language: json


Execute the following CLI command to instantiate VNF instance.

.. code-block:: console

  $ openstack vnflcm instantiate VNF_INSTANCE_ID ./sample_param_file.json


Result:

.. code-block:: console

  Instantiate request for VNF Instance 810d8c9b-e467-4b06-9265-ac9dce015fce has been accepted.


After that, execute the following CLI command and confirm that
VNF instance instantiation was successful.

* Confirm that the 'Instantiation State' is 'INSTANTIATED'.

.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID -c 'Instantiation State'


Result:

.. code-block:: console

  +---------------------+--------------+
  | Field               | Value        |
  +---------------------+--------------+
  | Instantiation State | INSTANTIATED |
  +---------------------+--------------+


1. Terminate VNF
^^^^^^^^^^^^^^^^

Execute the following CLI command to terminate the VNF instance.

.. code-block:: console

  $ openstack vnflcm terminate VNF_INSTANCE_ID


Result:

.. code-block:: console

  Terminate request for VNF Instance '810d8c9b-e467-4b06-9265-ac9dce015fce' has been accepted.


After that, execute the following CLI command and confirm that
VNF instance termination was successful.

* Confirm that the 'Instantiation State' is 'NOT_INSTANTIATED'.

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


6. Delete VNF Identifier
^^^^^^^^^^^^^^^^^^^^^^^^

Execute the following CLI command to delete the VNF instance.

.. code-block:: console

  $ openstack vnflcm delete VNF_INSTANCE_ID


Result:

.. code-block:: console

  Vnf instance '810d8c9b-e467-4b06-9265-ac9dce015fce' is deleted successfully


After that, execute the following CLI command and confirm that
VNF instance deletion was successful.

* Confirm that the 'Usage State' of VNF Package is 'NOT_IN_USE'.
* Confirm that the VNF instance is not found.

.. code-block:: console

  $ openstack vnf package show VNF_PACKAGE_ID \
    -c 'Usage State'


Result:

.. code-block:: console

  +-------------+------------+
  | Field       | Value      |
  +-------------+------------+
  | Usage State | NOT_IN_USE |
  +-------------+------------+


.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID


Result:

.. code-block:: console

  Can not find requested vnf instance: 810d8c9b-e467-4b06-9265-ac9dce015fce

