=================================================================
ETSI NFV-SOL VNF Change Current VNF Package with StandardUserData
=================================================================

This document describes how to change current VNF package for VNF when
using StandardUserData as the UserData class in Tacker.

Overview
--------

The diagram below shows an overview of changing current VNF package.

1. Request Change Current VNF Package

   A user requests tacker-server to change current VNF package for VNF
   instance with tacker-client by requesting
   ``change current vnf package``.

2. Call OpenStack Heat API

   Upon receiving a request from tacker-client, tacker-server redirects
   it to tacker-conductor.
   In tacker-conductor, the request is redirected again to an
   appropriate infra-driver (in this case OpenStack infra-driver)
   according to the contents of VNF instance.
   Then, OpenStack infra-driver calls OpenStack Heat APIs.

3. Change the resource of VMs

   OpenStack Heat change the resource (image, flavor, external network)
   of VMs according to the API calls.

.. figure:: ../_images/etsi_vnf_change_current_vnf_package.png
    :align: left

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

At least one VNF instance with status of ``INSTANTIATED`` is required.
You can refer to :doc:`./etsi_vnf_deployment_as_vm_with_user_data` for
the procedure to instantiate VNF.

You can refer to :doc:`./vnf-package` for the operation of uploading VNF
package.

.. note::
  You can deploy a VM directly by image or volume.
  Therefore, when updating the image of the VM, there will be two
  cases.

  Use the common VNF package and the flavor_id to instantiate,
  and then use the VNF package in the corresponding link to
  execute ``change current vnf package`` operation,
  you can update the image of the VM in the following two ways.

  1. change VM created by image to VM created by new image

  2. change VM created by volume to VM created by new volume

Change Current VNF Package
--------------------------

As mentioned in Prerequisites, the VNF must be created
before performing change current VNF package.

.. note::
  Currently, this operation only supports some functions of
  ``Change Current VNF Package``.

  * There are several ways to update VDUs, but in the Antelope version
    Tacker only supports ``RollingUpdate`` type.
    You can set it via ``upgrade_type`` param.

  * Supported updates:

    * Change image of VMs
    * Change flavor of VMs
    * Modify, add, and delete external networks

  * Unsupported updates:

    * Increase or decrease the number of VNFcs according to the VNF
      package
    * Add and delete the entire VDU

You need to upload the VNF package you want to change to before
executing change current vnf package.

Details of CLI commands are described in
:doc:`../cli/cli-etsi-vnflcm`.

For changing current VNF package, you need to prepare a JSON-formatted
definition file before running command.

``sample_param_file_for_standard_user_data.json:``

.. code-block:: json

  {
    "vnfdId": "5b09fc55-5324-47b4-9f3d-70d1ca59a765",
    "extVirtualLinks": [
      {
        "id": "ext_vl_id_net4",
        "resourceId": "1dad756e-a9d2-4c49-b490-d26940c6cbaf",
        "extCps": [
          {
            "cpdId": "VDU1_CP4",
            "cpConfig": {
              "VDU1_CP4_1": {
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
          },
          {
            "cpdId": "VDU2_CP4",
            "cpConfig": {
              "VDU2_CP4_1": {
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
    ],
    "extManagedVirtualLinks": [
      {
        "id": "ext_managed_vl_1",
        "vnfVirtualLinkDescId": "internalVL1",
        "resourceId": "4daf6f6c-8f19-4cc6-96b5-0e3ccc9c7c93"
      }
    ],
    "additionalParams": {
      "upgrade_type": "RollingUpdate",
      "lcm-operation-coordinate-old-vnf": "./Scripts/coordinate_old_vnf.py",
      "lcm-operation-coordinate-new-vnf": "./Scripts/coordinate_new_vnf.py",
      "vdu_params": [
        {
          "vdu_id": "VDU1",
          "old_vnfc_param": {
            "cp_name": "VDU1_CP1",
            "username": "ubuntu",
            "password": "ubuntu"
          },
          "new_vnfc_param": {
            "cp_name": "VDU1_CP1",
            "username": "ubuntu",
            "password": "ubuntu"
          }
        },
        {
          "vdu_id": "VDU2",
          "old_vnfc_param": {
            "cp_name": "VDU2_CP1",
            "username": "ubuntu",
            "password": "ubuntu"
          },
          "new_vnfc_param": {
            "cp_name": "VDU2_CP1",
            "username": "ubuntu",
            "password": "ubuntu"
          }
        }
      ],
      "lcm-operation-user-data": "./UserData/userdata_standard.py",
      "lcm-operation-user-data-class": "StandardUserData"
    },
    "vimConnectionInfo": {
      "vim1": {
        "accessInfo": {
          "password": "devstack",
          "project": "nfv",
          "projectDomain": "Default",
          "region": "RegionOne",
          "userDomain": "Default",
          "username": "nfv_user"
        },
        "extra": {
          "new-key": "new-val"
        },
        "interfaceInfo": {
          "endpoint": "http://localhost/identity/v3"
        },
        "vimId": "defb2f96-5670-4bef-8036-27bf61267fc1",
        "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3"
      }
    }
  }

.. note::
  * ``vnfdId`` is the vnfd id of the new VNF package you uploaded.
  * ``lcm-operation-coordinate-old-vnf`` and
    ``lcm-operation-coordinate-new-vnf`` are unique implementations of
    Tacker to simulate the coordination interface in
    `ETSI NFV-SOL002 v3.5.1`_.
    Mainly a script that can communicate with the VM after the VM is
    created, perform special customization of the VM or confirm the
    status of the VM.
  * ``vimConnectionInfo`` is an optional parameter.
    This operation can specify the ``vimConnectionInfo`` for the VNF
    instance.
    Even if this operation specifies multiple ``vimConnectionInfo``
    associated with one VNF instance, only one of them will be used for
    life cycle management operations.
    It is not possible to delete the key of registered
    ``vimConnectionInfo``.

You can set following parameter in additionalParams:

.. list-table:: additionalParams
  :widths: 15 10 30
  :header-rows: 1

  * - Attribute name
    - Cardinality
    - Parameter description
  * - upgrade_type
    - 1
    - Type of file update operation method. Specify Blue-Green or
      Rolling update.
  * - lcm-operation-coordinate-old-vnf
    - 1
    - The file path of the script that simulates the behavior of
      CoordinateVNF for old VNF.
  * - lcm-operation-coordinate-new-vnf
    - 1
    - The file path of the script that simulates the behavior of
      CoordinateVNF for new VNF.
  * - vdu_params
    - 0..N
    - VDU information of target VDU to update. Specifying a vdu_params
      is required for OpenStack VIM and not required for Kubernetes VIM.
  * - > vdu_id
    - 1
    - VDU name of target VDU to update.
  * - > old_vnfc_param
    - 0..1
    - Old VNFC connection information. Required for ssh connection in
      CoordinateVNF operation for application configuration to VNFC.
  * - >> cp-name
    - 1
    - Connection point name of old VNFC to update.
  * - >> username
    - 1
    - User name of old VNFC to update.
  * - >> password
    - 1
    - Password of old VNFC to update.
  * - > new_vnfc_param
    - 0..1
    - New VNFC connection information. Required for ssh connection in
      CoordinateVNF operation for application configuration to VNFC.
  * - >> cp-name
    - 1
    - Connection point name of new VNFC to update.
  * - >> username
    - 1
    - User name of new VNFC to update.
  * - >> password
    - 1
    - Password of new VNFC to update.
  * - external_lb_param
    - 0..1
    - Load balancer information that requires configuration changes.
      Required only for the Blue-Green deployment process of OpenStack
      VIM.
  * - > ip_address
    - 1
    - IP address of load balancer server.
  * - > username
    - 1
    - User name of load balancer server.
  * - > password
    - 1
    - Password of load balancer server.
  * - lcm-operation-user-data
    - 0..1
    - File name of UserData to use.
  * - lcm-operation-user-data-class
    - 0..1
    - Class name of UserData to use.

.. note::
  When using StandardUserData as UserData, the following settings are
  required in additionalParams.

  * "lcm-operation-user-data": "./UserData/userdata_standard.py"
  * "lcm-operation-user-data-class": "StandardUserData"

How to change image for VM created by image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute Change Current VNF Package CLI command. After complete this
change operation, you should check resource status by Heat CLI commands.

1. check 'ID' and 'Stack Status' of the stack before and after
operation.
This is to confirm that stack 'ID' has not been changed before and
after operation, and that the Stack update has been updated
successfully.

2. check 'physical_resource_id' and 'resource_status' of the VDU and
VDU's parent resource.
This is to confirm that 'physical_resource_id' has no change before
and after operation, and that the resource_status has been updated
successfully.

3. check 'image' information of VDU before and after operation.
This is to confirm that VDU's image has been changed successfully.
See `Heat CLI reference`_ for details on Heat CLI commands.

* Check point 1 before operation

  Stack information before operation:

  .. code-block:: console

    $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'

  Result:

  .. code-block:: console

    +--------------------------------------+------------------------------------------+-----------------+
    | ID                                   | Stack Name                               | Stack Status    |
    +--------------------------------------+------------------------------------------+-----------------+
    | 16358585-d7bf-4702-abe0-b0f4007775c9 | vnf-b144a27b-164f-4a04-bb98-578a2363bb9a | CREATE_COMPLETE |
    +--------------------------------------+------------------------------------------+-----------------+

* Check point 2 before operation

  Stack resource information before operation:

  .. code-block:: console

    $ openstack stack resource list 16358585-d7bf-4702-abe0-b0f4007775c9 \
      --filter type='VDU1.yaml'

  Result:

  .. code-block:: console

    +---------------+--------------------------------------+---------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type | resource_status | updated_time         |
    +---------------+--------------------------------------+---------------+-----------------+----------------------+
    | VDU1-0        | 09b59157-19fb-4254-bb49-e5dd74634840 | VDU1.yaml     | CREATE_COMPLETE | 2023-02-13T08:04:09Z |
    +---------------+--------------------------------------+---------------+-----------------+----------------------+

  VDU information before operation:

  .. code-block:: console

    $ openstack stack resource list 09b59157-19fb-4254-bb49-e5dd74634840 \
      --filter type='OS::Nova::Server'

  Result:

  .. code-block:: console

    +---------------+--------------------------------------+-------------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type     | resource_status | updated_time         |
    +---------------+--------------------------------------+-------------------+-----------------+----------------------+
    | VDU1          | 283bf442-9671-4d29-b936-4a04c6b8316a | OS::Nova::Server  | CREATE_COMPLETE | 2023-02-13T08:04:12Z |
    +---------------+--------------------------------------+-------------------+-----------------+----------------------+

* Check point 3 before operation

  VDU detailed information before operation:

  .. code-block:: console

    $ openstack stack resource show 09b59157-19fb-4254-bb49-e5dd74634840 VDU1 \
      -f json | jq .attributes.image.id

  Result:

  .. code-block:: console

    "c0b684bd-445f-44f1-9ab7-1e151a090ec7"

* Execute Change Current VNF Package

  Change Current VNF Package execution of the entire VNF:

  .. code-block:: console

    $ openstack vnflcm change-vnfpkg VNF_INSTANCE_ID \
         ./sample_param_file_for_standard_user_data.json \
         --os-tacker-api-version 2

  Result:

  .. code-block:: console

    Change Current VNF Package for VNF Instance b144a27b-164f-4a04-bb98-578a2363bb9a has been accepted.

* Check point 1 after operation

  Stack information after operation:

  .. code-block:: console

    $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'

  Result:

  .. code-block:: console

    +--------------------------------------+------------------------------------------+-----------------+
    | ID                                   | Stack Name                               | Stack Status    |
    +--------------------------------------+------------------------------------------+-----------------+
    | 16358585-d7bf-4702-abe0-b0f4007775c9 | vnf-b144a27b-164f-4a04-bb98-578a2363bb9a | UPDATE_COMPLETE |
    +--------------------------------------+------------------------------------------+-----------------+

  .. note::
    'Stack Status' transitions to UPDATE_COMPLETE.

* Check point 2 after operation

  Stack resource information after operation:

  .. code-block:: console

    $ openstack stack resource list 16358585-d7bf-4702-abe0-b0f4007775c9 \
      --filter type='VDU1-ver2.yaml'

  Result:

  .. code-block:: console

    +---------------+--------------------------------------+----------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type  | resource_status | updated_time         |
    +---------------+--------------------------------------+----------------+-----------------+----------------------+
    | VDU1-0        | 09b59157-19fb-4254-bb49-e5dd74634840 | VDU1-ver2.yaml | UPDATE_COMPLETE | 2023-02-13T08:10:35Z |
    +---------------+--------------------------------------+----------------+-----------------+----------------------+

  VDU information after operation:

  .. code-block:: console

    $ openstack stack resource list 09b59157-19fb-4254-bb49-e5dd74634840 \
      --filter type='OS::Nova::Server'

  Result:

  .. code-block:: console

    +---------------+--------------------------------------+-------------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type     | resource_status | updated_time         |
    +---------------+--------------------------------------+-------------------+-----------------+----------------------+
    | VDU1          | 283bf442-9671-4d29-b936-4a04c6b8316a | OS::Nova::Server  | UPDATE_COMPLETE | 2023-02-13T08:10:08Z |
    +---------------+--------------------------------------+-------------------+-----------------+----------------------+

  .. note::
    'resource_status' transitions to UPDATE_COMPLETE.

* Check point 3 after operation

  VDU detailed information after operation:

  .. code-block:: console

    $ openstack stack resource show 09b59157-19fb-4254-bb49-e5dd74634840 VDU1 \
      -f json | jq .attributes.image.id

  Result:

  .. code-block:: console

    "4718c711-16ad-4778-a2cb-33b213567e16"

  .. note::
    You can check 'attributes.image.id' has been changed from
    'c0b684bd-445f-44f1-9ab7-1e151a090ec7' to
    '4718c711-16ad-4778-a2cb-33b213567e16'.

How to change image for VM created by volume
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute Change Current VNF Package CLI command. After complete this
change operation, you should check resource status by Heat CLI commands.

1. check 'ID' and 'Stack Status' of the stack before and after
operation.
This is to confirm that stack 'ID' has not been changed before and after
operation, and the Stack update has been updated successfully.

2. check 'physical_resource_id' and 'resource_status' of the VDU and
VDU's parent resource. This is to confirm that 'physical_resource_id' of
VDU has changed before and after operation, 'physical_resource_id' of
VDU's parent resource has no change before and after operation, and that
the 'resource_status' of VDU has been created successfully,
'resource_status' of VDU's parent resource has been updated
successfully.

3. check 'os-extended-volumes:volumes_attached' information of VDU
before and after operation.
This is to confirm that VDU's image has been changed successfully.
See `Heat CLI reference`_ for details on Heat CLI commands.

* Check point 1 before operation

  Stack information before operation:

  .. code-block:: console

    $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'

  Result:

  .. code-block:: console

    +--------------------------------------+------------------------------------------+-----------------+
    | ID                                   | Stack Name                               | Stack Status    |
    +--------------------------------------+------------------------------------------+-----------------+
    | 16358585-d7bf-4702-abe0-b0f4007775c9 | vnf-b144a27b-164f-4a04-bb98-578a2363bb9a | CREATE_COMPLETE |
    +--------------------------------------+------------------------------------------+-----------------+

* Check point 2 before operation

  Stack resource information before operation:

  .. code-block:: console

    $ openstack stack resource list 16358585-d7bf-4702-abe0-b0f4007775c9 \
      --filter type='VDU2.yaml'

  Result:

  .. code-block:: console

    +---------------+--------------------------------------+---------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type | resource_status | updated_time         |
    +---------------+--------------------------------------+---------------+-----------------+----------------------+
    | VDU2-0        | 1ddc79f1-33c9-4e44-8aa8-1450a63471eb | VDU2.yaml     | CREATE_COMPLETE | 2023-02-13T08:04:09Z |
    +---------------+--------------------------------------+---------------+-----------------+----------------------+

  VDU information before operation:

  .. code-block:: console

    $ openstack stack resource list 1ddc79f1-33c9-4e44-8aa8-1450a63471eb \
      --filter type='OS::Nova::Server'

  Result:

  .. code-block:: console

    +---------------------+--------------------------------------+------------------------+-----------------+----------------------+
    | resource_name       | physical_resource_id                 | resource_type          | resource_status | updated_time         |
    +---------------------+--------------------------------------+------------------------+-----------------+----------------------+
    | VDU2                | dd1ae073-f7d1-4619-b6b6-7d6f9a37ce88 | OS::Nova::Server       | CREATE_COMPLETE | 2023-02-13T08:04:13Z |
    +---------------------+--------------------------------------+------------------------+-----------------+----------------------+

* Check point 3 before operation

  VDU detailed information before operation:

  .. code-block:: console

    $ openstack stack resource show 1ddc79f1-33c9-4e44-8aa8-1450a63471eb VDU2 \
      -f json | jq '.attributes."os-extended-volumes:volumes_attached"[].id'

  Result:

  .. code-block:: console

    "46a5bc58-ee2e-4a18-87ad-1b3efd0fff77"

* Execute Change Current VNF Package

  Change Current VNF Package execution of the entire VNF:

  .. code-block:: console

    $ openstack vnflcm change-vnfpkg VNF_INSTANCE_ID \
         ./sample_param_file_for_standard_user_data.json \
         --os-tacker-api-version 2

  Result:

  .. code-block:: console

    Change Current VNF Package for VNF Instance b144a27b-164f-4a04-bb98-578a2363bb9a has been accepted.

* Check point 1 after operation

  Stack information after operation:

  .. code-block:: console

    $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'

  Result:

  .. code-block:: console

    +--------------------------------------+------------------------------------------+-----------------+
    | ID                                   | Stack Name                               | Stack Status    |
    +--------------------------------------+------------------------------------------+-----------------+
    | 16358585-d7bf-4702-abe0-b0f4007775c9 | vnf-b144a27b-164f-4a04-bb98-578a2363bb9a | UPDATE_COMPLETE |
    +--------------------------------------+------------------------------------------+-----------------+

  .. note::
    'Stack Status' transitions to UPDATE_COMPLETE.

* Check point 2 after operation

  Stack resource information before operation:

  .. code-block:: console

    $ openstack stack resource list 16358585-d7bf-4702-abe0-b0f4007775c9 \
      --filter type='VDU2-ver2.yaml'

  Result:

  .. code-block:: console

    +---------------+--------------------------------------+----------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type  | resource_status | updated_time         |
    +---------------+--------------------------------------+----------------+-----------------+----------------------+
    | VDU2-0        | 1ddc79f1-33c9-4e44-8aa8-1450a63471eb | VDU2-ver2.yaml | UPDATE_COMPLETE | 2023-02-13T08:10:36Z |
    +---------------+--------------------------------------+----------------+-----------------+----------------------+

  VDU information after operation:

  .. code-block:: console

    $ openstack stack resource list 1ddc79f1-33c9-4e44-8aa8-1450a63471eb \
      --filter type='OS::Nova::Server'

  Result:

  .. code-block:: console

    +---------------------+--------------------------------------+------------------------+-----------------+----------------------+
    | resource_name       | physical_resource_id                 | resource_type          | resource_status | updated_time         |
    +---------------------+--------------------------------------+------------------------+-----------------+----------------------+
    | VDU2                | 0d19e66b-9016-4d34-85ef-d918e62e8661 | OS::Nova::Server       | CREATE_COMPLETE | 2023-02-13T08:09:35Z |
    +---------------------+--------------------------------------+------------------------+-----------------+----------------------+

  .. note::
    'resource_status' transitions to CREATE_COMPLETE.
    'physical_resource_id' has been changed from
    'dd1ae073-f7d1-4619-b6b6-7d6f9a37ce88' to
    '0d19e66b-9016-4d34-85ef-d918e62e8661'.

* Check point 3 after operation

  VDU detailed information after operation:

  .. code-block:: console

    $ openstack stack resource show 1ddc79f1-33c9-4e44-8aa8-1450a63471eb VDU2 \
      -f json | jq '.attributes."os-extended-volumes:volumes_attached"[].id'

  Result:

  .. code-block:: console

    "88a9df83-1546-4e53-a38b-62dc17f11826"

  .. note::
    You can check 'attributes.os-extended-volumes:volumes_attached.id'
    has been changed from '46a5bc58-ee2e-4a18-87ad-1b3efd0fff77' to
    '88a9df83-1546-4e53-a38b-62dc17f11826'.

How to change flavor of VMs
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute Change Current VNF Package CLI command. After complete this
change operation, you should check resource status by Heat CLI commands.

1. check 'flavor' information of VDU before and after operation.
This is to confirm that VDU's flavor have been changed successfully.
See `Heat CLI reference`_ for details on Heat CLI commands.

* Check point 1 before operation

  VDU detailed information before operation:

  .. code-block:: console

    $ openstack stack resource show 1ddc79f1-33c9-4e44-8aa8-1450a63471eb VDU2 \
      -f json | jq .attributes.flavor

  Result:

  .. code-block:: console

    {
      "vcpus": 1,
      "ram": 512,
      "disk": 1,
      "ephemeral": 0,
      "swap": 0,
      "original_name": "m1.tiny",
      "extra_specs": {
        "hw_rng:allowed": "True"
      }
    }

* Execute change Current VNF Package

  Change Current VNF Package execution of the entire VNF:

  .. code-block:: console

    $ openstack vnflcm change-vnfpkg VNF_INSTANCE_ID \
         ./sample_param_file_for_standard_user_data.json \
         --os-tacker-api-version 2

  Result:

  .. code-block:: console

    Change Current VNF Package for VNF Instance b144a27b-164f-4a04-bb98-578a2363bb9a has been accepted.

* Check point 1 after operation

  VDU detailed information after operation:

  .. code-block:: console

    $ openstack stack resource show 1ddc79f1-33c9-4e44-8aa8-1450a63471eb VDU2 \
      -f json | jq .attributes.flavor

  Result:

  .. code-block:: console

    {
      "vcpus": 1,
      "ram": 2048,
      "disk": 20,
      "ephemeral": 0,
      "swap": 0,
      "original_name": "m1.small",
      "extra_specs": {
        "hw_rng:allowed": "True"
      }
    }

  .. note::
    You can check 'attributes.flavor' has been changed.
    In this example, it has been changed as follows.

    * 'attributes.flavor.ram' has been changed from '512' to '2048'
    * 'attributes.flavor.disk' has been changed from '1' to '20'
    * 'attributes.flavor.original_name' has been changed from 'm1.tiny'
      to 'm1.small'

How to change external networks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute Change Current VNF Package CLI command. After complete this
change operation, you should check resource status by Heat CLI commands.

1. check the number or 'physical_resource_id' of the external network
resources.
In the case of add and delete, this is to confirm that the number of
resources has been changed before and after operation.
And in the case of modify, this is to confirm that
'physical_resource_id' has been changed.

2. check 'address' information of VDU before and after operation.
This is to confirm that VDU's external networks have been changed
successfully.
See `Heat CLI reference`_ for details on Heat CLI commands.

* Check point 1 before operation

  External networks information before operation:

  .. code-block:: console

    $ openstack stack resource list 09b59157-19fb-4254-bb49-e5dd74634840 \
      --filter type='OS::Neutron::Port'

  Result:

  .. code-block:: console

    +---------------+--------------------------------------+-------------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type     | resource_status | updated_time         |
    +---------------+--------------------------------------+-------------------+-----------------+----------------------+
    | VDU1_CP2      | 6b72ba80-3287-4d8f-8ec1-7e6aca8d39a0 | OS::Neutron::Port | CREATE_COMPLETE | 2023-02-13T08:04:12Z |
    | VDU1_CP3      | ae68a952-e571-4fa3-921a-d86bd85e7746 | OS::Neutron::Port | CREATE_COMPLETE | 2023-02-13T08:04:12Z |
    | VDU1_CP1      | ead7a816-097f-4a0c-ab72-48a90284c0c4 | OS::Neutron::Port | CREATE_COMPLETE | 2023-02-13T08:04:12Z |
    +---------------+--------------------------------------+-------------------+-----------------+----------------------+

* Check point 2 before operation

  External networks detailed information before operation:

  .. code-block:: console

    $ openstack stack resource show 09b59157-19fb-4254-bb49-e5dd74634840 VDU1 \
      -f json | jq .attributes.addresses

  Result:

  .. code-block:: console

    {
      "net1": [
        {
          "version": 4,
          "addr": "10.10.1.48",
          "OS-EXT-IPS:type": "fixed",
          "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:8c:c4:3d"
        }
      ],
      "net_mgmt": [
        {
          "version": 4,
          "addr": "192.168.120.66",
          "OS-EXT-IPS:type": "fixed",
          "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:b9:21:b7"
        }
      ],
      "vnf-b144a27b-164f-4a04-bb98-578a2363bb9a-internalVL2-3qan642mfebl": [
        {
          "version": 4,
          "addr": "192.168.4.21",
          "OS-EXT-IPS:type": "fixed",
          "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:1b:ae:ea"
        }
      ]
    }

* Execute Change Current VNF Package

  Change Current VNF Package execution of the entire VNF:

  .. code-block:: console

    $ openstack vnflcm change-vnfpkg VNF_INSTANCE_ID \
         ./sample_param_file_for_standard_user_data.json \
         --os-tacker-api-version 2

  Result:

  .. code-block:: console

    Change Current VNF Package for VNF Instance b144a27b-164f-4a04-bb98-578a2363bb9a has been accepted.

* Check point 1 after operation

  External networks information after operation:

  .. code-block:: console

    $ openstack stack resource list 09b59157-19fb-4254-bb49-e5dd74634840 \
      --filter type='OS::Neutron::Port'

  Result:

  .. code-block:: console

    +---------------+--------------------------------------+-------------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type     | resource_status | updated_time         |
    +---------------+--------------------------------------+-------------------+-----------------+----------------------+
    | VDU1_CP2      | 6b72ba80-3287-4d8f-8ec1-7e6aca8d39a0 | OS::Neutron::Port | CREATE_COMPLETE | 2023-02-13T08:04:12Z |
    | VDU1_CP1      | ead7a816-097f-4a0c-ab72-48a90284c0c4 | OS::Neutron::Port | CREATE_COMPLETE | 2023-02-13T08:04:12Z |
    | VDU1_CP4      | 6d6745fc-868f-42be-87fe-89d0970ed9de | OS::Neutron::Port | CREATE_COMPLETE | 2023-02-13T08:10:03Z |
    | VDU1_CP3      | 306c7b61-34a3-466f-93a6-37625c336dae | OS::Neutron::Port | CREATE_COMPLETE | 2023-02-13T08:10:07Z |
    +---------------+--------------------------------------+-------------------+-----------------+----------------------+

  .. note::
    The number or 'resource_status' of the external network resources
    have been changed.
    In this example, the number has been changed from '3' to '4'.

* Check point 2 after operation

  External networks detailed information after operation:

  .. code-block:: console

    $ openstack stack resource show 09b59157-19fb-4254-bb49-e5dd74634840 VDU1 \
      -f json | jq .attributes.addresses

  Result:

  .. code-block:: console

    {
      "net1": [
        {
          "version": 4,
          "addr": "10.10.1.48",
          "OS-EXT-IPS:type": "fixed",
          "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:8c:c4:3d"
        }
      ],
      "net_mgmt": [
        {
          "version": 4,
          "addr": "192.168.120.66",
          "OS-EXT-IPS:type": "fixed",
          "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:b9:21:b7"
        }
      ],
      "vnf-b144a27b-164f-4a04-bb98-578a2363bb9a-internalVL3-5tpq76i3eddx": [
        {
          "version": 4,
          "addr": "192.168.5.87",
          "OS-EXT-IPS:type": "fixed",
          "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:24:27:44"
        }
      ],
      "net0": [
        {
          "version": 4,
          "addr": "10.10.0.223",
          "OS-EXT-IPS:type": "fixed",
          "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:a8:df:00"
        }
      ]
    }

  .. note::
    You can check 'attributes.addresses' has been changed.
    In this example, 'net0' has been added.

.. _Heat CLI reference: https://docs.openstack.org/python-openstackclient/latest/cli/plugin-commands/heat.html
.. _ETSI NFV-SOL002 v3.5.1: https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/002/03.05.01_60/gs_nfv-sol002v030501p.pdf
