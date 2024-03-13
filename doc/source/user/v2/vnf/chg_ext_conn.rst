=============================================
ETSI NFV-SOL Change External VNF Connectivity
=============================================

This document describes how to change external VNF connectivity
in Tacker v2 API.

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

Execute up to "Instantiate VNF" in the procedure of
:doc:`/user/v2/vnf/deployment_with_user_data/index`.
In other words, the procedure after "Terminate VNF" is not executed.


Change External VNF Connectivity
--------------------------------

As mentioned in Prerequisites, the VNF must be created
before performing change external connectivity.

Assuming that the following VNF instance exists,
this instance will be changed.

Details of CLI commands are described in
:doc:`/cli/cli-etsi-vnflcm`.

For changing external VNF connectivity, you need to prepare a JSON-formatted
definition file before running command for changing the connectivity.


.. code-block:: json

  {
    "extVirtualLinks": [
      {
        "id": "ced0c31f-bb03-4351-90af-8c51f59bcf25",
        "vimConnectionId": "vim1",
        "resourceProviderId": "671cb532-4139-45e6-b873-b06b4864f0ab",
        "resourceId": "dcdd8e59-d303-4659-bdff-d32f2cb2b806",
        "extCps": [
          {
            "cpdId": "VDU1_CP1",
            "cpConfig": {
              "VDU1_CP1": {
                "cpProtocolData": [
                  {
                    "layerProtocol": "IP_OVER_ETHERNET",
                    "ipOverEthernet": {
                      "ipAddresses": [
                        {
                          "type": "IPV4",
                          "numDynamicAddresses": 1,
                          "subnetId": "ab38a204-8c01-4205-95c6-b4e74198700f"
                        }
                      ]
                    }
                  }
                ]
              }
            }
          },
          {
            "cpdId": "VDU2_CP2",
            "cpConfig": {
              "VDU2_CP2": {
                "cpProtocolData": [
                  {
                    "layerProtocol": "IP_OVER_ETHERNET",
                    "ipOverEthernet": {
                      "ipAddresses": [
                        {
                          "type": "IPV4",
                          "fixedAddresses": [
                            "22.22.22.101"
                          ],
                          "subnetId": "ab38a204-8c01-4205-95c6-b4e74198700f"
                        },
                        {
                          "type": "IPV6",
                          "numDynamicAddresses": 1,
                          "subnetId": "3f023732-8364-43e0-80de-00799d5b78af"
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
    ],
    "vimConnectionInfo": {
      "vim1": {
        "vimId": "f7ed00b1-06f1-4076-95dc-c6ed11f5541c",
        "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
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
        },
        "extra": {
          "dummy-key": "dummy-val"
        }
      }
    },
    "additionalParams": {
      "dummy-key": "dummy-val",
      "lcm-operation-user-data": "./UserData/userdata_standard.py",
      "lcm-operation-user-data-class": "StandardUserData"
    }
  }


.. note::

  sample_param_file.json contains all the data of port resource information.
  If no setting is contained, it is treated as a change in information.


.. note::

  The change external VNF Connectivity operation can change the
  ``vimConnectionInfo`` associated with an existing VNF instance.
  Even if change external VNF Connectivity operation specify multiple
  ``vimConnectionInfo`` associated with one VNF instance, only one of
  them will be used for life cycle management operations.
  It is not possible to delete the key of registered ``vimConnectionInfo``.


How to Change the Specific Port Setting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute Change External VNF Connectivity CLI command and check 'ID' and
'Stack Status' of the stack before and after operation.
This is to confirm that stack 'ID' has no change before and after operation,
and that the Stack update has been completed successfully.
See `Heat CLI reference`_. for details on Heat CLI commands.

Stack information before operation:

.. code-block:: console

  $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'


Result:

.. code-block:: console

  +--------------------------------------+------------------------------------------+-----------------+
  | ID                                   | Stack Name                               | Stack Status    |
  +--------------------------------------+------------------------------------------+-----------------+
  | 7a53b676-aa9c-4c7d-a8a7-1311646ec7e2 | vnf-df9150a0-8679-4b14-8cbc-9d2d6606ca7c | CREATE_COMPLETE |
  +--------------------------------------+------------------------------------------+-----------------+


Stack resource information:

.. code-block:: console

  $ openstack stack resource list HEAT_STACK_ID


Result:

.. code-block:: console

  +--------------------+--------------------------------------+------------------------+-----------------+----------------------+
  | resource_name      | physical_resource_id                 | resource_type          | resource_status | updated_time         |
  +--------------------+--------------------------------------+------------------------+-----------------+----------------------+
  | VDU1-0             | ea178dfa-5148-4be0-9508-58c94989b76a | VDU1.yaml              | CREATE_COMPLETE | 2023-11-13T04:14:13Z |
  | VDU1-VolumeType    | dc71e318-74f3-43dc-ad79-7503846384c7 | OS::Cinder::VolumeType | CREATE_COMPLETE | 2023-11-13T04:14:13Z |
  | VDU2-0             | cf97ee84-1681-4498-a0eb-e42f1de2a845 | VDU2.yaml              | CREATE_COMPLETE | 2023-11-13T04:14:13Z |
  | VDU2-VolumeType    | 322d5605-3409-4c63-b776-d8486a7593fe | OS::Cinder::VolumeType | CREATE_COMPLETE | 2023-11-13T04:14:13Z |
  | internalVL3_subnet | 360ec318-5f7d-4f56-b9cc-a089695b24ae | OS::Neutron::Subnet    | CREATE_COMPLETE | 2023-11-13T04:14:13Z |
  | internalVL3        | 90d2c767-2b54-4c02-85aa-7bb1ff9f4d14 | OS::Neutron::Net       | CREATE_COMPLETE | 2023-11-13T04:14:13Z |
  +--------------------+--------------------------------------+------------------------+-----------------+----------------------+


Stack resource detailed information:

.. code-block:: console

  $ openstack stack resource show HEAT_STACK_ID VDU2_CP2  \
    -f json | jq .attributes.fixed_ips


Result:

.. code-block:: console

  [
    {
      "subnet_id": "a1d042f3-88aa-4150-b42b-8620c9be746c",
      "ip_address": "100.100.100.11"
    },
    {
      "subnet_id": "a12a1603-a30d-4724-80fb-9a7019a3c79f",
      "ip_address": "1111:2222:3333::18d"
    }
  ]


Change External VNF Connectivity execution of the entire VNF:

.. code-block:: console

  $ openstack vnflcm change-ext-conn VNF_INSTANCE_ID sample_param_file.json \
    --os-tacker-api-version 2


Result:

.. code-block:: console

  Change External VNF Connectivity for VNF Instance df9150a0-8679-4b14-8cbc-9d2d6606ca7c has been accepted.


.. note::

  Create a parameter file that describes the resource information to be changed in advance.


Stack information after operation:

.. code-block:: console

  $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'


Result:

.. code-block:: console

  +--------------------------------------+------------------------------------------+-----------------+
  | ID                                   | Stack Name                               | Stack Status    |
  +--------------------------------------+------------------------------------------+-----------------+
  | 7a53b676-aa9c-4c7d-a8a7-1311646ec7e2 | vnf-df9150a0-8679-4b14-8cbc-9d2d6606ca7c | UPDATE_COMPLETE |
  +--------------------------------------+------------------------------------------+-----------------+

.. note::

  'Stack Status' transitions to UPDATE_COMPLETE.


Stack resource information:

.. code-block:: console

  $ openstack stack resource list HEAT_STACK_ID


Result:

.. code-block:: console

  +--------------------+--------------------------------------+------------------------+-----------------+----------------------+
  | resource_name      | physical_resource_id                 | resource_type          | resource_status | updated_time         |
  +--------------------+--------------------------------------+------------------------+-----------------+----------------------+
  | VDU1-0             | ea178dfa-5148-4be0-9508-58c94989b76a | VDU1.yaml              | UPDATE_COMPLETE | 2023-11-13T07:54:47Z |
  | VDU1-VolumeType    | dc71e318-74f3-43dc-ad79-7503846384c7 | OS::Cinder::VolumeType | CREATE_COMPLETE | 2023-11-13T04:14:13Z |
  | VDU2-0             | cf97ee84-1681-4498-a0eb-e42f1de2a845 | VDU2.yaml              | UPDATE_COMPLETE | 2023-11-13T07:54:46Z |
  | VDU2-VolumeType    | 322d5605-3409-4c63-b776-d8486a7593fe | OS::Cinder::VolumeType | CREATE_COMPLETE | 2023-11-13T04:14:13Z |
  | internalVL3_subnet | 360ec318-5f7d-4f56-b9cc-a089695b24ae | OS::Neutron::Subnet    | CREATE_COMPLETE | 2023-11-13T04:14:13Z |
  | internalVL3        | 90d2c767-2b54-4c02-85aa-7bb1ff9f4d14 | OS::Neutron::Net       | CREATE_COMPLETE | 2023-11-13T04:14:13Z |
  +--------------------+--------------------------------------+------------------------+-----------------+----------------------+


Stack resource detailed information:

.. code-block:: console

  $ openstack stack resource show HEAT_STACK_ID VDU2_CP2  \
    -f json | jq .attributes.fixed_ips


Result:

.. code-block:: console

  [
    {
      "subnet_id": "3f023732-8364-43e0-80de-00799d5b78af",
      "ip_address": "1111:2222:4444::39f"
    },
    {
      "subnet_id": "ab38a204-8c01-4205-95c6-b4e74198700f",
      "ip_address": "22.22.22.101"
    }
  ]


.. note::

  'fixed_ips' has changed from the IP before change external VNF
  connectivity.


See `Heat CLI reference`_. for details on Heat CLI commands.


History of Checks
-----------------

The content of this document has been confirmed to work
using the following VNF Package.

* `basic_lcms_max_individual_vnfc for 2023.2 Bobcat`_


.. _Heat CLI reference: https://docs.openstack.org/python-openstackclient/latest/cli/plugin-commands/heat.html
.. _basic_lcms_max_individual_vnfc for 2023.2 Bobcat:
  https://opendev.org/openstack/tacker/src/branch/stable/2023.2/tacker/tests/functional/sol_v2_common/samples/basic_lcms_max_individual_vnfc
