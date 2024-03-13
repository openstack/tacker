========================
ETSI NFV-SOL VNF Healing
========================

This document describes how to heal VNF in Tacker v1 API.

.. note::

  This is a document for Tacker v1 API.
  See :doc:`/user/v2/vnf/heal/index` for Tacker v2 API.


Overview
--------

The diagram below shows an overview of the VNF healing.

1. Request heal VNF

   A user requests tacker-server to heal a VNF or all VNFs with tacker-client
   by requesting ``heal VNF``.

2. Call OpenStack Heat API

   Upon receiving a request from tacker-client, tacker-server redirects it to
   tacker-conductor. In tacker-conductor, the request is redirected again to
   an appropriate infra-driver (in this case OpenStack infra-driver) according
   to the contents of the instantiate parameters. Then, OpenStack infra-driver
   calls OpenStack Heat APIs.

3. Re-create VMs

   OpenStack Heat re-creates VMs according to the API calls.

.. figure:: /_images/etsi_vnf_healing.png


Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

A default VIM should be registered according to
:doc:`/cli/cli-legacy-vim`.

The VNF Package(sample_vnf_package_csar.zip) used below is prepared
by referring to :doc:`/user/vnf-package`.

The procedure of prepare for healing operation that from "register VIM" to
"Instantiate VNF", basically refer to
:doc:`/user/etsi_vnf_deployment_as_vm_with_tosca` or
:doc:`/user/etsi_vnf_deployment_as_vm_with_user_data`.

This procedure uses an example using the sample VNF package.


Healing Target VNF Instance
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Assuming that the following VNF instance exists,
this instance will be healed.

.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID


Result:

.. code-block:: console

  +-----------------------------+----------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------+
  | ID                          | c3f9c200-7f52-42c5-9c64-6032faa3faf8                                                                                 |
  | Instantiated Vnf Info       | {                                                                                                                    |
  |                             |     "flavourId": "simple",                                                                                           |
  |                             |     "vnfState": "STARTED",                                                                                           |
  |                             |     "scaleStatus": [                                                                                                 |
  |                             |         {                                                                                                            |
  |                             |             "aspectId": "worker_instance",                                                                           |
  |                             |             "scaleLevel": 0                                                                                          |
  |                             |         }                                                                                                            |
  |                             |     ],                                                                                                               |
  |                             |     "extCpInfo": [                                                                                                   |
  |                             |         {                                                                                                            |
  |                             |             "id": "d7c14d6f-3bac-4e11-a512-5101b4933545",                                                            |
  |                             |             "cpdId": "VDU1_CP1",                                                                                     |
  |                             |             "extLinkPortId": null,                                                                                   |
  |                             |             "associatedVnfcCpId": "b0f677ce-93db-416a-839b-998707338d14",                                            |
  |                             |             "cpProtocolInfo": []                                                                                     |
  |                             |         },                                                                                                           |
  |                             |         {                                                                                                            |
  |                             |             "id": "e3513495-c555-4a1f-a9cc-07a0feae2720",                                                            |
  |                             |             "cpdId": "VDU2_CP1",                                                                                     |
  |                             |             "extLinkPortId": null,                                                                                   |
  |                             |             "associatedVnfcCpId": "9da6945b-d9a3-4001-a03a-7b239b7e7084",                                            |
  |                             |             "cpProtocolInfo": []                                                                                     |
  |                             |         },                                                                                                           |
  |                             |         {                                                                                                            |
  |                             |             "id": "53c187aa-d05c-4995-9518-3119ac02ee66",                                                            |
  |                             |             "cpdId": "VDU1_CP2",                                                                                     |
  |                             |             "extLinkPortId": null,                                                                                   |
  |                             |             "associatedVnfcCpId": "b0f677ce-93db-416a-839b-998707338d14",                                            |
  |                             |             "cpProtocolInfo": [                                                                                      |
  |                             |                 {                                                                                                    |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                             |
  |                             |                     "ipOverEthernet": {                                                                              |
  |                             |                         "macAddress": null,                                                                          |
  |                             |                         "ipAddresses": [                                                                             |
  |                             |                             {                                                                                        |
  |                             |                                 "type": "IPV4",                                                                      |
  |                             |                                 "subnetId": "d290cae3-0dbc-44a3-a043-1a50ded04a64",                                  |
  |                             |                                 "isDynamic": false,                                                                  |
  |                             |                                 "addresses": [                                                                       |
  |                             |                                     "22.22.1.10"                                                                     |
  |                             |                                 ]                                                                                    |
  |                             |                             }                                                                                        |
  |                             |                         ]                                                                                            |
  |                             |                     }                                                                                                |
  |                             |                 }                                                                                                    |
  |                             |             ]                                                                                                        |
  |                             |         },                                                                                                           |
  |                             |         {                                                                                                            |
  |                             |             "id": "9fcec4e1-e808-4dc6-b048-79ec88d0aa40",                                                            |
  |                             |             "cpdId": "VDU2_CP2",                                                                                     |
  |                             |             "extLinkPortId": null,                                                                                   |
  |                             |             "associatedVnfcCpId": "9da6945b-d9a3-4001-a03a-7b239b7e7084",                                            |
  |                             |             "cpProtocolInfo": [                                                                                      |
  |                             |                 {                                                                                                    |
  |                             |                     "layerProtocol": "IP_OVER_ETHERNET",                                                             |
  |                             |                     "ipOverEthernet": {                                                                              |
  |                             |                         "macAddress": null,                                                                          |
  |                             |                         "ipAddresses": [                                                                             |
  |                             |                             {                                                                                        |
  |                             |                                 "type": "IPV4",                                                                      |
  |                             |                                 "subnetId": "d290cae3-0dbc-44a3-a043-1a50ded04a64",                                  |
  |                             |                                 "isDynamic": false,                                                                  |
  |                             |                                 "addresses": [                                                                       |
  |                             |                                     "22.22.1.20"                                                                     |
  |                             |                                 ]                                                                                    |
  |                             |                             }                                                                                        |
  |                             |                         ]                                                                                            |
  |                             |                     }                                                                                                |
  |                             |                 }                                                                                                    |
  |                             |             ]                                                                                                        |
  |                             |         }                                                                                                            |
  |                             |     ],                                                                                                               |
  |                             |     "extVirtualLinkInfo": [                                                                                          |
  |                             |         {                                                                                                            |
  |                             |             "id": "91bcff6d-4703-4ba9-b1c2-009e6db92a9c",                                                            |
  |                             |             "resourceHandle": {                                                                                      |
  |                             |                 "vimConnectionId": "79a97d01-e5f3-4eaa-b2bc-8f513ecb8a56",                                           |
  |                             |                 "resourceId": "3019b1e7-99d8-4748-97ac-104922bc78d9",                                                |
  |                             |                 "vimLevelResourceType": null                                                                         |
  |                             |             },                                                                                                       |
  |                             |             "extLinkPorts": [                                                                                        |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "6b7c0b3a-cc2d-4b94-9f6f-81df69a7cc2f",                                                    |
  |                             |                     "resourceHandle": {                                                                              |
  |                             |                         "vimConnectionId": "79a97d01-e5f3-4eaa-b2bc-8f513ecb8a56",                                   |
  |                             |                         "resourceId": "972a375d-921f-46f5-bfdb-19af95fc49e1",                                        |
  |                             |                         "vimLevelResourceType": null                                                                 |
  |                             |                     },                                                                                               |
  |                             |                     "cpInstanceId": "9fcec4e1-e808-4dc6-b048-79ec88d0aa40"                                           |
  |                             |                 },                                                                                                   |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "02d867e7-b955-4b4a-b92f-c78c7ede63bf",                                                    |
  |                             |                     "resourceHandle": {                                                                              |
  |                             |                         "vimConnectionId": "79a97d01-e5f3-4eaa-b2bc-8f513ecb8a56",                                   |
  |                             |                         "resourceId": "b853b5c5-cd97-4dfb-8750-cac6e5c62477",                                        |
  |                             |                         "vimLevelResourceType": null                                                                 |
  |                             |                     },                                                                                               |
  |                             |                     "cpInstanceId": "9fcec4e1-e808-4dc6-b048-79ec88d0aa40"                                           |
  |                             |                 }                                                                                                    |
  |                             |             ]                                                                                                        |
  |                             |         },                                                                                                           |
  |                             |         {                                                                                                            |
  |                             |             "id": "a96d2f5b-c01a-48e1-813c-76132965042c",                                                            |
  |                             |             "resourceHandle": {                                                                                      |
  |                             |                 "vimConnectionId": "79a97d01-e5f3-4eaa-b2bc-8f513ecb8a56",                                           |
  |                             |                 "resourceId": "589a045a-65d9-4f4d-a9b3-35aa655374d0",                                                |
  |                             |                 "vimLevelResourceType": null                                                                         |
  |                             |             }                                                                                                        |
  |                             |         }                                                                                                            |
  |                             |     ],                                                                                                               |
  |                             |     "extManagedVirtualLinkInfo": [                                                                                   |
  |                             |         {                                                                                                            |
  |                             |             "id": "8f9d8da0-2386-4f00-bbb0-860f50d32a5a",                                                            |
  |                             |             "vnfVirtualLinkDescId": "internalVL1",                                                                   |
  |                             |             "networkResource": {                                                                                     |
  |                             |                 "vimConnectionId": null,                                                                             |
  |                             |                 "resourceId": "0e498d08-ed3a-4212-83e0-1b6808f6fcb6",                                                |
  |                             |                 "vimLevelResourceType": "OS::Neutron::Net"                                                           |
  |                             |             },                                                                                                       |
  |                             |             "vnfLinkPorts": [                                                                                        |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "f5de777b-22e9-480a-a044-5359cc8b6263",                                                    |
  |                             |                     "resourceHandle": {                                                                              |
  |                             |                         "vimConnectionId": "c637c425-62e8-432f-94f4-bff8d3323e29",                                   |
  |                             |                         "resourceId": "ddb45b78-385d-4c18-aec3-10bf6bafb840",                                        |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                  |
  |                             |                     },                                                                                               |
  |                             |                     "cpInstanceId": "a98f1c4b-f4c9-4603-8813-4a9dbb003950"                                           |
  |                             |                 },                                                                                                   |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "d754bcb0-5ab4-4715-9469-e946ec69733e",                                                    |
  |                             |                     "resourceHandle": {                                                                              |
  |                             |                         "vimConnectionId": "c637c425-62e8-432f-94f4-bff8d3323e29",                                   |
  |                             |                         "resourceId": "29de4ae6-1004-4607-9023-818efacba3ce",                                        |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                  |
  |                             |                     },                                                                                               |
  |                             |                     "cpInstanceId": "c408c3a8-924b-4570-a896-ddb5bd56d14a"                                           |
  |                             |                 }                                                                                                    |
  |                             |             ]                                                                                                        |
  |                             |         },                                                                                                           |
  |                             |         {                                                                                                            |
  |                             |             "id": "11d68761-aab7-419c-955c-0c6497f13692",                                                            |
  |                             |             "vnfVirtualLinkDescId": "internalVL2",                                                                   |
  |                             |             "networkResource": {                                                                                     |
  |                             |                 "vimConnectionId": null,                                                                             |
  |                             |                 "resourceId": "38a8d4ba-ac1b-41a2-a92b-ff2a3e5e9b12",                                                |
  |                             |                 "vimLevelResourceType": "OS::Neutron::Net"                                                           |
  |                             |             },                                                                                                       |
  |                             |             "vnfLinkPorts": [                                                                                        |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "1b664cfb-6c8b-4f02-a535-f683fe414e31",                                                    |
  |                             |                     "resourceHandle": {                                                                              |
  |                             |                         "vimConnectionId": "c637c425-62e8-432f-94f4-bff8d3323e29",                                   |
  |                             |                         "resourceId": "2215cb28-9876-4c43-a71d-c63ae42a7ab4",                                        |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                  |
  |                             |                     },                                                                                               |
  |                             |                     "cpInstanceId": "f16e20d7-cb86-4b4d-a4fa-f27802eaf628"                                           |
  |                             |                 },                                                                                                   |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "65c35b4c-1a8b-4495-a396-73d09f4cebea",                                                    |
  |                             |                     "resourceHandle": {                                                                              |
  |                             |                         "vimConnectionId": "c637c425-62e8-432f-94f4-bff8d3323e29",                                   |
  |                             |                         "resourceId": "0019f288-38b3-4247-89fc-51ecf7663401",                                        |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                  |
  |                             |                     },                                                                                               |
  |                             |                     "cpInstanceId": "269b2b44-7577-45b5-8038-1e67d34dea41"                                           |
  |                             |                 }                                                                                                    |
  |                             |             ]                                                                                                        |
  |                             |         }                                                                                                            |
  |                             |     ],                                                                                                               |
  |                             |     "vnfcResourceInfo": [                                                                                            |
  |                             |         {                                                                                                            |
  |                             |             "id": "b0f677ce-93db-416a-839b-998707338d14",                                                            |
  |                             |             "vduId": "VDU1",                                                                                         |
  |                             |             "computeResource": {                                                                                     |
  |                             |                 "vimConnectionId": "c637c425-62e8-432f-94f4-bff8d3323e29",                                           |
  |                             |                 "resourceId": "2bd41386-1971-425c-9f27-310c7a4d6181",                                                |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                           |
  |                             |             },                                                                                                       |
  |                             |             "storageResourceIds": [],                                                                                |
  |                             |             "vnfcCpInfo": [                                                                                          |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "c86cef0a-150d-4eff-a21f-a48c6fcfa258",                                                    |
  |                             |                     "cpdId": "VDU1_CP1",                                                                             |
  |                             |                     "vnfExtCpId": "6b7c0b3a-cc2d-4b94-9f6f-81df69a7cc2f",                                            |
  |                             |                     "vnfLinkPortId": "f2105dd9-fed4-43dd-8d74-fcf0199cb716"                                          |
  |                             |                 },                                                                                                   |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "426c0473-2de1-42dc-ae1f-ff4cf4d8b29b",                                                    |
  |                             |                     "cpdId": "VDU1_CP2",                                                                             |
  |                             |                     "vnfExtCpId": null,                                                                              |
  |                             |                     "vnfLinkPortId": "9925668e-ceea-45ef-817a-25d19572a494",                                         |
  |                             |                     "cpProtocolInfo": [                                                                              |
  |                             |                         {                                                                                            |
  |                             |                             "layerProtocol": "IP_OVER_ETHERNET",                                                     |
  |                             |                             "ipOverEthernet": {                                                                      |
  |                             |                                 "macAddress": null,                                                                  |
  |                             |                                 "ipAddresses": [                                                                     |
  |                             |                                     {                                                                                |
  |                             |                                         "type": "IPV4",                                                              |
  |                             |                                         "subnetId": "d290cae3-0dbc-44a3-a043-1a50ded04a64",                          |
  |                             |                                         "isDynamic": false,                                                          |
  |                             |                                         "addresses": [                                                               |
  |                             |                                             "22.22.1.10"                                                             |
  |                             |                                         ]                                                                            |
  |                             |                                     }                                                                                |
  |                             |                                 ]                                                                                    |
  |                             |                             }                                                                                        |
  |                             |                         }                                                                                            |
  |                             |                     ]                                                                                                |
  |                             |                 },                                                                                                   |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "a98f1c4b-f4c9-4603-8813-4a9dbb003950",                                                    |
  |                             |                     "cpdId": "VDU1_CP3",                                                                             |
  |                             |                     "vnfExtCpId": null,                                                                              |
  |                             |                     "vnfLinkPortId": "f5de777b-22e9-480a-a044-5359cc8b6263"                                          |
  |                             |                 },                                                                                                   |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "f16e20d7-cb86-4b4d-a4fa-f27802eaf628",                                                    |
  |                             |                     "cpdId": "VDU1_CP4",                                                                             |
  |                             |                     "vnfExtCpId": null,                                                                              |
  |                             |                     "vnfLinkPortId": "1b664cfb-6c8b-4f02-a535-f683fe414e31"                                          |
  |                             |                 },                                                                                                   |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "89dd97c3-ef2d-4df5-a18a-f542e573a5bd",                                                    |
  |                             |                     "cpdId": "VDU1_CP5",                                                                             |
  |                             |                     "vnfExtCpId": null,                                                                              |
  |                             |                     "vnfLinkPortId": "1a8d6c49-40bb-4f24-96e7-6efba6001671"                                          |
  |                             |                 }                                                                                                    |
  |                             |             ]                                                                                                        |
  |                             |         },                                                                                                           |
  |                             |         {                                                                                                            |
  |                             |             "id": "9da6945b-d9a3-4001-a03a-7b239b7e7084",                                                            |
  |                             |             "vduId": "VDU2",                                                                                         |
  |                             |             "computeResource": {                                                                                     |
  |                             |                 "vimConnectionId": "c637c425-62e8-432f-94f4-bff8d3323e29",                                           |
  |                             |                 "resourceId": "777515dd-35c9-4f06-ad6b-f79323097e0f",                                                |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                           |
  |                             |             },                                                                                                       |
  |                             |             "storageResourceIds": [],                                                                                |
  |                             |             "vnfcCpInfo": [                                                                                          |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "12ea4352-66a5-47a4-989f-d4d06d5bab1a",                                                    |
  |                             |                     "cpdId": "VDU2_CP1",                                                                             |
  |                             |                     "vnfExtCpId": "02d867e7-b955-4b4a-b92f-c78c7ede63bf",                                            |
  |                             |                     "vnfLinkPortId": "6043706d-6173-40ef-8bc5-519868ce9fe4"                                          |
  |                             |                 },                                                                                                   |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "b6a56d88-da99-4036-872f-f10759b00ed8",                                                    |
  |                             |                     "cpdId": "VDU2_CP2",                                                                             |
  |                             |                     "vnfExtCpId": null,                                                                              |
  |                             |                     "vnfLinkPortId": "bfd0d3ad-1f9c-4102-b446-c7f33881b136",                                         |
  |                             |                     "cpProtocolInfo": [                                                                              |
  |                             |                         {                                                                                            |
  |                             |                             "layerProtocol": "IP_OVER_ETHERNET",                                                     |
  |                             |                             "ipOverEthernet": {                                                                      |
  |                             |                                 "macAddress": null,                                                                  |
  |                             |                                 "ipAddresses": [                                                                     |
  |                             |                                     {                                                                                |
  |                             |                                         "type": "IPV4",                                                              |
  |                             |                                         "subnetId": "d290cae3-0dbc-44a3-a043-1a50ded04a64",                          |
  |                             |                                         "isDynamic": false,                                                          |
  |                             |                                         "addresses": [                                                               |
  |                             |                                             "22.22.1.20"                                                             |
  |                             |                                         ]                                                                            |
  |                             |                                     }                                                                                |
  |                             |                                 ]                                                                                    |
  |                             |                             }                                                                                        |
  |                             |                         }                                                                                            |
  |                             |                     ]                                                                                                |
  |                             |                 },                                                                                                   |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "c408c3a8-924b-4570-a896-ddb5bd56d14a",                                                    |
  |                             |                     "cpdId": "VDU2_CP3",                                                                             |
  |                             |                     "vnfExtCpId": null,                                                                              |
  |                             |                     "vnfLinkPortId": "d754bcb0-5ab4-4715-9469-e946ec69733e"                                          |
  |                             |                 },                                                                                                   |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "269b2b44-7577-45b5-8038-1e67d34dea41",                                                    |
  |                             |                     "cpdId": "VDU2_CP4",                                                                             |
  |                             |                     "vnfExtCpId": null,                                                                              |
  |                             |                     "vnfLinkPortId": "65c35b4c-1a8b-4495-a396-73d09f4cebea"                                          |
  |                             |                 },                                                                                                   |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "bb1ed2d3-da19-4b45-b326-cf9e76fd788a",                                                    |
  |                             |                     "cpdId": "VDU2_CP5",                                                                             |
  |                             |                     "vnfExtCpId": null,                                                                              |
  |                             |                     "vnfLinkPortId": "46cd8f09-d877-491b-8928-345ec6461637"                                          |
  |                             |                 }                                                                                                    |
  |                             |             ]                                                                                                        |
  |                             |         }                                                                                                            |
  |                             |     ],                                                                                                               |
  |                             |     "vnfVirtualLinkResourceInfo": [                                                                                  |
  |                             |         {                                                                                                            |
  |                             |             "id": "b3244c22-2365-476e-bc7b-40cbaee45ce1",                                                            |
  |                             |             "vnfVirtualLinkDescId": "internalVL1",                                                                   |
  |                             |             "networkResource": {                                                                                     |
  |                             |                 "vimConnectionId": null,                                                                             |
  |                             |                 "resourceId": "0e498d08-ed3a-4212-83e0-1b6808f6fcb6",                                                |
  |                             |                 "vimLevelResourceType": "OS::Neutron::Net"                                                           |
  |                             |             },                                                                                                       |
  |                             |             "vnfLinkPorts": [                                                                                        |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "f5de777b-22e9-480a-a044-5359cc8b6263",                                                    |
  |                             |                     "resourceHandle": {                                                                              |
  |                             |                         "vimConnectionId": "c637c425-62e8-432f-94f4-bff8d3323e29",                                   |
  |                             |                         "resourceId": "ddb45b78-385d-4c18-aec3-10bf6bafb840",                                        |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                  |
  |                             |                     },                                                                                               |
  |                             |                     "cpInstanceId": "a98f1c4b-f4c9-4603-8813-4a9dbb003950"                                           |
  |                             |                 },                                                                                                   |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "d754bcb0-5ab4-4715-9469-e946ec69733e",                                                    |
  |                             |                     "resourceHandle": {                                                                              |
  |                             |                         "vimConnectionId": "c637c425-62e8-432f-94f4-bff8d3323e29",                                   |
  |                             |                         "resourceId": "29de4ae6-1004-4607-9023-818efacba3ce",                                        |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                  |
  |                             |                     },                                                                                               |
  |                             |                     "cpInstanceId": "c408c3a8-924b-4570-a896-ddb5bd56d14a"                                           |
  |                             |                 }                                                                                                    |
  |                             |             ]                                                                                                        |
  |                             |         },                                                                                                           |
  |                             |         {                                                                                                            |
  |                             |             "id": "c9182342-bfc4-4ba8-9e26-02fd0565db4d",                                                            |
  |                             |             "vnfVirtualLinkDescId": "internalVL2",                                                                   |
  |                             |             "networkResource": {                                                                                     |
  |                             |                 "vimConnectionId": null,                                                                             |
  |                             |                 "resourceId": "38a8d4ba-ac1b-41a2-a92b-ff2a3e5e9b12",                                                |
  |                             |                 "vimLevelResourceType": "OS::Neutron::Net"                                                           |
  |                             |             },                                                                                                       |
  |                             |             "vnfLinkPorts": [                                                                                        |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "1b664cfb-6c8b-4f02-a535-f683fe414e31",                                                    |
  |                             |                     "resourceHandle": {                                                                              |
  |                             |                         "vimConnectionId": "c637c425-62e8-432f-94f4-bff8d3323e29",                                   |
  |                             |                         "resourceId": "2215cb28-9876-4c43-a71d-c63ae42a7ab4",                                        |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                  |
  |                             |                     },                                                                                               |
  |                             |                     "cpInstanceId": "f16e20d7-cb86-4b4d-a4fa-f27802eaf628"                                           |
  |                             |                 },                                                                                                   |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "65c35b4c-1a8b-4495-a396-73d09f4cebea",                                                    |
  |                             |                     "resourceHandle": {                                                                              |
  |                             |                         "vimConnectionId": "c637c425-62e8-432f-94f4-bff8d3323e29",                                   |
  |                             |                         "resourceId": "0019f288-38b3-4247-89fc-51ecf7663401",                                        |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                  |
  |                             |                     },                                                                                               |
  |                             |                     "cpInstanceId": "269b2b44-7577-45b5-8038-1e67d34dea41"                                           |
  |                             |                 }                                                                                                    |
  |                             |             ]                                                                                                        |
  |                             |         },                                                                                                           |
  |                             |         {                                                                                                            |
  |                             |             "id": "81ed1791-a1c2-46fb-a999-dd9d601b06ec",                                                            |
  |                             |             "vnfVirtualLinkDescId": "internalVL3",                                                                   |
  |                             |             "networkResource": {                                                                                     |
  |                             |                 "vimConnectionId": null,                                                                             |
  |                             |                 "resourceId": "",                                                                                    |
  |                             |                 "vimLevelResourceType": null                                                                         |
  |                             |             },                                                                                                       |
  |                             |             "vnfLinkPorts": [                                                                                        |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "1a8d6c49-40bb-4f24-96e7-6efba6001671",                                                    |
  |                             |                     "resourceHandle": {                                                                              |
  |                             |                         "vimConnectionId": "c637c425-62e8-432f-94f4-bff8d3323e29",                                   |
  |                             |                         "resourceId": "84d7fc8c-fb52-4593-875b-bf303ec5fc8c",                                        |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                  |
  |                             |                     },                                                                                               |
  |                             |                     "cpInstanceId": "89dd97c3-ef2d-4df5-a18a-f542e573a5bd"                                           |
  |                             |                 },                                                                                                   |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "46cd8f09-d877-491b-8928-345ec6461637",                                                    |
  |                             |                     "resourceHandle": {                                                                              |
  |                             |                         "vimConnectionId": "c637c425-62e8-432f-94f4-bff8d3323e29",                                   |
  |                             |                         "resourceId": "65650d05-a562-4c5f-84d2-e9304ef68377",                                        |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                  |
  |                             |                     },                                                                                               |
  |                             |                     "cpInstanceId": "bb1ed2d3-da19-4b45-b326-cf9e76fd788a"                                           |
  |                             |                 }                                                                                                    |
  |                             |             ]                                                                                                        |
  |                             |         },                                                                                                           |
  |                             |         {                                                                                                            |
  |                             |             "id": "1d1a0824-5c4d-461e-9a29-5e72db1e5855",                                                            |
  |                             |             "vnfVirtualLinkDescId": "91bcff6d-4703-4ba9-b1c2-009e6db92a9c",                                          |
  |                             |             "networkResource": {                                                                                     |
  |                             |                 "vimConnectionId": "79a97d01-e5f3-4eaa-b2bc-8f513ecb8a56",                                           |
  |                             |                 "resourceId": "3019b1e7-99d8-4748-97ac-104922bc78d9",                                                |
  |                             |                 "vimLevelResourceType": "OS::Neutron::Net"                                                           |
  |                             |             },                                                                                                       |
  |                             |             "vnfLinkPorts": [                                                                                        |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "f2105dd9-fed4-43dd-8d74-fcf0199cb716",                                                    |
  |                             |                     "resourceHandle": {                                                                              |
  |                             |                         "vimConnectionId": "c637c425-62e8-432f-94f4-bff8d3323e29",                                   |
  |                             |                         "resourceId": "f0cf8bfd-261a-4c54-b783-42cce6d90859",                                        |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                  |
  |                             |                     },                                                                                               |
  |                             |                     "cpInstanceId": "c86cef0a-150d-4eff-a21f-a48c6fcfa258"                                           |
  |                             |                 },                                                                                                   |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "6043706d-6173-40ef-8bc5-519868ce9fe4",                                                    |
  |                             |                     "resourceHandle": {                                                                              |
  |                             |                         "vimConnectionId": "c637c425-62e8-432f-94f4-bff8d3323e29",                                   |
  |                             |                         "resourceId": "6a349003-66a1-4bfa-bd4b-83705957482a",                                        |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                  |
  |                             |                     },                                                                                               |
  |                             |                     "cpInstanceId": "12ea4352-66a5-47a4-989f-d4d06d5bab1a"                                           |
  |                             |                 }                                                                                                    |
  |                             |             ]                                                                                                        |
  |                             |         },                                                                                                           |
  |                             |         {                                                                                                            |
  |                             |             "id": "d8fc6199-c9d6-4e74-b896-c44018fa4382",                                                            |
  |                             |             "vnfVirtualLinkDescId": "a96d2f5b-c01a-48e1-813c-76132965042c",                                          |
  |                             |             "networkResource": {                                                                                     |
  |                             |                 "vimConnectionId": "79a97d01-e5f3-4eaa-b2bc-8f513ecb8a56",                                           |
  |                             |                 "resourceId": "589a045a-65d9-4f4d-a9b3-35aa655374d0",                                                |
  |                             |                 "vimLevelResourceType": "OS::Neutron::Net"                                                           |
  |                             |             },                                                                                                       |
  |                             |             "vnfLinkPorts": [                                                                                        |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "9925668e-ceea-45ef-817a-25d19572a494",                                                    |
  |                             |                     "resourceHandle": {                                                                              |
  |                             |                         "vimConnectionId": "c637c425-62e8-432f-94f4-bff8d3323e29",                                   |
  |                             |                         "resourceId": "53700068-3c4b-444b-b4eb-bbaa887a0e28",                                        |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                  |
  |                             |                     },                                                                                               |
  |                             |                     "cpInstanceId": "426c0473-2de1-42dc-ae1f-ff4cf4d8b29b"                                           |
  |                             |                 },                                                                                                   |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "bfd0d3ad-1f9c-4102-b446-c7f33881b136",                                                    |
  |                             |                     "resourceHandle": {                                                                              |
  |                             |                         "vimConnectionId": "c637c425-62e8-432f-94f4-bff8d3323e29",                                   |
  |                             |                         "resourceId": "136f1448-feb7-480d-8d92-15d7e4d02f37",                                        |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                  |
  |                             |                     },                                                                                               |
  |                             |                     "cpInstanceId": "b6a56d88-da99-4036-872f-f10759b00ed8"                                           |
  |                             |                 }                                                                                                    |
  |                             |             ]                                                                                                        |
  |                             |         }                                                                                                            |
  |                             |     ],                                                                                                               |
  |                             |     "vnfcInfo": [                                                                                                    |
  |                             |         {                                                                                                            |
  |                             |             "id": "b9b73267-40ce-468f-87ab-a6653cee664f",                                                            |
  |                             |             "vduId": "VDU1",                                                                                         |
  |                             |             "vnfcState": "STARTED"                                                                                   |
  |                             |         },                                                                                                           |
  |                             |         {                                                                                                            |
  |                             |             "id": "1842c052-b6af-45bb-b976-f99cd1212182",                                                            |
  |                             |             "vduId": "VDU2",                                                                                         |
  |                             |             "vnfcState": "STARTED"                                                                                   |
  |                             |         }                                                                                                            |
  |                             |     ],                                                                                                               |
  |                             |     "additionalParams": {                                                                                            |
  |                             |         "lcm-operation-user-data": "./UserData/lcm_user_data.py",                                                    |
  |                             |         "lcm-operation-user-data-class": "SampleUserData"                                                            |
  |                             |     }                                                                                                                |
  |                             | }                                                                                                                    |
  | Instantiation State         | INSTANTIATED                                                                                                         |
  | Links                       | {                                                                                                                    |
  |                             |     "self": {                                                                                                        |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/c3f9c200-7f52-42c5-9c64-6032faa3faf8"                 |
  |                             |     },                                                                                                               |
  |                             |     "terminate": {                                                                                                   |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/c3f9c200-7f52-42c5-9c64-6032faa3faf8/terminate"       |
  |                             |     },                                                                                                               |
  |                             |     "heal": {                                                                                                        |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/c3f9c200-7f52-42c5-9c64-6032faa3faf8/heal"            |
  |                             |     },                                                                                                               |
  |                             |     "changeExtConn": {                                                                                               |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/c3f9c200-7f52-42c5-9c64-6032faa3faf8/change_ext_conn" |
  |                             |     }                                                                                                                |
  |                             | }                                                                                                                    |
  | VIM Connection Info         | [                                                                                                                    |
  |                             |     {                                                                                                                |
  |                             |         "id": "79a97d01-e5f3-4eaa-b2bc-8f513ecb8a56",                                                                |
  |                             |         "vimId": null,                                                                                               |
  |                             |         "vimType": "ETSINFV.OPENSTACK_KEYSTONE.v_2",                                                                 |
  |                             |         "interfaceInfo": {                                                                                           |
  |                             |             "endpoint": "http://127.0.0.1/identity"                                                                  |
  |                             |         },                                                                                                           |
  |                             |         "accessInfo": {                                                                                              |
  |                             |             "region": "RegionOne",                                                                                   |
  |                             |             "tenant": "1994d69783d64c00aadab564038c2fd7",                                                            |
  |                             |             "password": "devstack",                                                                                  |
  |                             |             "username": "nfv_user"                                                                                   |
  |                             |         },                                                                                                           |
  |                             |         "extra": {}                                                                                                  |
  |                             |     },                                                                                                               |
  |                             |     {                                                                                                                |
  |                             |         "id": "700a68db-0789-49e0-97d5-9824d5eeb272",                                                                |
  |                             |         "vimId": "c637c425-62e8-432f-94f4-bff8d3323e29",                                                             |
  |                             |         "vimType": "openstack",                                                                                      |
  |                             |         "interfaceInfo": {},                                                                                         |
  |                             |         "accessInfo": {},                                                                                            |
  |                             |         "extra": {}                                                                                                  |
  |                             |     }                                                                                                                |
  |                             | ]                                                                                                                    |
  | VNF Configurable Properties |                                                                                                                      |
  | VNF Instance Description    |                                                                                                                      |
  | VNF Instance Name           | vnf-c3f9c200-7f52-42c5-9c64-6032faa3faf8                                                                             |
  | VNF Product Name            | Sample VNF                                                                                                           |
  | VNF Provider                | Company                                                                                                              |
  | VNF Software Version        | 1.0                                                                                                                  |
  | VNFD ID                     | b1bb0ce7-ebca-4fa7-95ed-4840d7000321                                                                                 |
  | VNFD Version                | 1.0                                                                                                                  |
  | metadata                    | tenant=nfv                                                                                                           |
  | vnfPkgId                    |                                                                                                                      |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------+


.. note::

  The value set for 'VNF Instance Name' corresponds to 'Stack Name'
  managed by Heat.
  In this manual, it corresponds to **vnf-c3f9c200-7f52-42c5-9c64-6032faa3faf8**.


VNF Healing Procedure
---------------------

As mentioned in **Prerequisites** and **Healing target VNF instance**,
the VNF must be instantiated before healing.

Details of CLI commands are described in
:doc:`/cli/cli-etsi-vnflcm`.

There are two main methods for VNF healing.

* Healing of the entire VNF
* Healing specified with VNFC instances

.. note::

  A VNFC is a 'VNF Component', and one VNFC basically
  corresponds to one VDU in the VNF.
  For more information on VNFC, see `NFV-SOL002 v2.6.1`_.


How to Heal of the Entire VNF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When healing of the entire VNF, the following APIs are executed
from Tacker to Heat.
See `Heat API reference`_. for details on Heat APIs.

* stack delete
* stack create

Execute Heat CLI command and check 'ID' and 'Stack Status' of the stack
before and after healing.
This is to confirm that stack 'ID' has changed
before and after healing, and that the re-creation has been
completed successfully.
See `Heat CLI reference`_. for details on Heat CLI commands.


Stack information before healing:

.. code-block:: console

  $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'


Result:

.. code-block:: console

  +--------------------------------------+---------------------------------------------+-----------------+
  | ID                                   | Stack Name                                  | Stack Status    |
  +--------------------------------------+---------------------------------------------+-----------------+
  | 00d1871d-4acc-4d6b-99bc-cc68ad0b8a6a | vnflcm_c3f9c200-7f52-42c5-9c64-6032faa3faf8 | CREATE_COMPLETE |
  +--------------------------------------+---------------------------------------------+-----------------+


Healing execution of the entire VNF:

.. code-block:: console

  $ openstack vnflcm heal VNF_INSTANCE_ID


Result:

.. code-block:: console

  Heal request for VNF Instance 0c3644ff-b207-4a6a-9d3a-d1295cda153a has been accepted.


Stack information after healing:

.. code-block:: console

  $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'


Result:

.. code-block:: console

  +--------------------------------------+---------------------------------------------+-----------------+
  | ID                                   | Stack Name                                  | Stack Status    |
  +--------------------------------------+---------------------------------------------+-----------------+
  | c220dd92-034e-4e7f-bea3-e5e7e95b145c | vnflcm_c3f9c200-7f52-42c5-9c64-6032faa3faf8 | CREATE_COMPLETE |
  +--------------------------------------+---------------------------------------------+-----------------+

.. note::

  'ID' has changed from the ID before healing.
  'Stack Status' transitions to CREATE_COMPLETE.


How to Heal Specified with VNFC Instances
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extract the value of vnfcResourceInfo -> id from 'Instantiated Vnf Info'
in **Healing target VNF instance**.
This is the VNFC instance ID.

.. code-block:: console

  $ openstack vnflcm show c3f9c200-7f52-42c5-9c64-6032faa3faf8 \
   -f json | jq '."Instantiated Vnf Info".vnfcResourceInfo[].id'
  "b0f677ce-93db-416a-839b-998707338d14"
  "9da6945b-d9a3-4001-a03a-7b239b7e7084"


This manual shows an example of healing VDU1 as VNFC.
In this manual, **b0f677ce-93db-416a-839b-998707338d14** corresponds to
the VNFC instance ID of VDU1.

When healing specified with VNFC instances, the following
APIs are executed from Tacker to Heat.
See `Heat API reference`_ for details on Heat APIs.

* stack resource mark unhealthy
* stack update

Execute Heat CLI command and check physical_resource_id and
resource_status of VDU1 before and after healing.
This is to confirm that the resource ID of this VDU1 has changed
before and after healing, and that the re-creation has been
completed successfully.
See `Heat CLI reference`_ for details on Heat CLI commands.

.. note::

  Note that 'vnfc-instance-id' managed by Tacker and
  'physical-resource-id' managed by Heat are different.


VDU1 information before healing:

.. code-block:: console

  $ openstack stack resource show HEAT_STACK_ID \
    VDU_NAME -c physical_resource_id -c resource_status


Result:

.. code-block:: console

  +----------------------+--------------------------------------+
  | Field                | Value                                |
  +----------------------+--------------------------------------+
  | physical_resource_id | 6b89f9c9-ebd8-49ca-8e2c-c01838daeb95 |
  | resource_status      | CREATE_COMPLETE                      |
  +----------------------+--------------------------------------+


Healing execution of VDU1:

.. code-block:: console

  $ openstack vnflcm heal VNF_INSTANCE_ID --vnfc-instance VNFC_INSTANCE_ID


Result:

.. code-block:: console

  Heal request for VNF Instance c3f9c200-7f52-42c5-9c64-6032faa3faf8 has been accepted.


.. note::

  It is possible to specify multiple VNFC instance IDs in '--vnfc-instance' option.


VDU1 information after healing:

.. code-block:: console

  $ openstack stack resource show HEAT_STACK_ID \
    VDU_NAME -c physical_resource_id -c resource_status


Result:

.. code-block:: console

  +----------------------+--------------------------------------+
  | Field                | Value                                |
  +----------------------+--------------------------------------+
  | physical_resource_id | 6b89f9c9-ebd8-49ca-8e2c-c01838daeb95 |
  | resource_status      | UPDATE_COMPLETE                      |
  +----------------------+--------------------------------------+


.. note::

  'physical_resource_id' has not changed from the ID before healing.
  'resource_status' transitions to UPDATE_COMPLETE.


.. _NFV-SOL002 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/002/02.06.01_60/gs_NFV-SOL002v020601p.pdf
.. _Heat API reference : https://docs.openstack.org/api-ref/orchestration/v1/index.html
.. _Heat CLI reference : https://docs.openstack.org/python-openstackclient/latest/cli/plugin-commands/heat.html
