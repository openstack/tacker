===========================================
ETSI NFV-SOL VNF Change Current VNF Package
===========================================

This document describes how to change current VNF package for VNF in Tacker.

Overview
--------

The diagram below shows an overview of changing current VNF package.

1. Request Change Current VNF Package

   A user requests tacker-server to change current VNF package for VNF instance
   with tacker-client by requesting ``change current vnf package``.

2. Call OpenStack Heat API

   Upon receiving a request from tacker-client, tacker-server redirects it to
   tacker-conductor.  In tacker-conductor, the request is redirected again to
   an appropriate infra-driver (in this case OpenStack infra-driver) according
   to the contents of VNF instance.  Then, OpenStack infra-driver calls
   OpenStack Heat APIs.

3. Change the image of VMs

   OpenStack Heat change the image of VMs according to the API calls.

.. figure:: ../_images/etsi_vnf_change_current_vnf_package.png
    :align: left

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

At least one VNF instance with status of ``INSTANTIATED`` is required.
You can refer to :doc:`./etsi_vnf_deployment_as_vm_with_tosca` for the
procedure to instantiate VNF.

You can refer to :doc:`./vnf-package` for the operation of uploading
VNF package.


.. note::
   You can deploy a VM directly by image or volume.
   Therefore, when updating the
   image of the VM, there will be two cases.

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

You need to upload the VNF package you want to change to before
executing change current vnf package.

Details of CLI commands are described in
:doc:`../cli/cli-etsi-vnflcm`.

For changing current VNF package, you need to prepare a JSON-formatted
definition file before running command for changing the VNF package.

``sample_param_file_for_multi_resources.json:``

.. code-block:: json

  {
    "vnfdId": "c6595341-a5bb-8246-53c4-7aeb843d60c5",
    "additionalParams": {
      "upgrade_type": "RollingUpdate",
      "lcm-operation-coordinate-old-vnf": "./Scripts/coordinate_old_vnf.py",
      "lcm-operation-coordinate-new-vnf": "./Scripts/coordinate_new_vnf.py",
      "vdu_params": [{
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
      }, {
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
      }]
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

``sample_param_file_for_single_resource.json:``

.. code-block:: json

  {
    "vnfdId": "c6595341-a5bb-8246-53c4-7aeb843d60c5",
    "additionalParams": {
      "upgrade_type": "RollingUpdate",
      "lcm-operation-coordinate-old-vnf": "./Scripts/coordinate_old_vnf.py",
      "lcm-operation-coordinate-new-vnf": "./Scripts/coordinate_new_vnf.py",
      "vdu_params": [{
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
      }]
    }
  }

You can set following parameter in additionalParams:

.. list-table:: additionalParams
  :widths: 15 10 30
  :header-rows: 1

  * - Attribute name
    - Cardinality
    - Parameter description
  * - upgrade_type
    - 1
    - Type of file update operation method. Specify Blue-Green or Rolling update.
  * - lcm-operation-coordinate-old-vnf
    - 1
    - The file path of the script that simulates the behavior of CoordinateVNF for old VNF.
  * - lcm-operation-coordinate-new-vnf
    - 1
    - The file path of the script that simulates the behavior of CoordinateVNF for new VNF.
  * - vdu_params
    - 0..N
    - VDU information of target VDU to update. Specifying a vdu_params is required for OpenStack VIM and not required for Kubernetes VIM.
  * - > vdu_id
    - 1
    - VDU name of target VDU to update.
  * - > old_vnfc_param
    - 0..1
    - Old VNFC connection information. Required for ssh connection in CoordinateVNF operation for application configuration to VNFC.
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
    - New VNFC connection information. Required for ssh connection in CoordinateVNF operation for application configuration to VNFC.
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
    - Load balancer information that requires configuration changes. Required only for the Blue-Green deployment process of OpenStack VIM.
  * - > ip_address
    - 1
    - IP address of load balancer server.
  * - > username
    - 1
    - User name of load balancer server.
  * - > password
    - 1
    - Password of load balancer server.

.. note:: ``sample_param_file_for_multi_resources.json`` contains all optional
   parameters. It can be used to change image for both VDU created by
   ``OS::Heat::AutoScalingGroup`` and single VDU.
   ``sample_param_file_for_single_resource.json`` only used to change image for
   single VDU.

   * ``vnfdId`` is the vnfd id of the new VNF package you uploaded.
   * ``lcm-operation-coordinate-old-vnf`` and
     ``lcm-operation-coordinate-new-vnf`` are unique implementations of Tacker
     to simulate the coordination interface in `ETSI SOL002 v3.5.1`_. Mainly a
     script that can communicate with the VM after the VM is created, perform
     special customization of the VM or confirm the status of the VM.
   * ``vimConnectionInfo`` is an optional parameter.
     This operation can specify the ``vimConnectionInfo`` for
     the VNF instance.
     Even if this operation specify multiple ``vimConnectionInfo``
     associated with one VNF instance, only one of them will be used
     for life cycle management operations.
     It is not possible to delete the key of registered ``vimConnectionInfo``.

.. note:: Currently, this operation only supports some functions of
   ``Change Current VNF Package``.

   * There are several ways to update VDUs, but Yoga version Tacker only
     supports ``RollingUpdate`` type. You can set it via ``upgrade_type``
     param.

   * Currently only support update images of VMs and modify external networks..

   * Currently unsupported updates:

     * This API currently does not support increasing or decreasing the number
       of VNFcs according to the VNF package.
     * The add and delete operations of the entire VDU are not supported.
     * In the definition of ETSI, external and internal networks
       (e.g. extVirtualLinks, extManagedVirtualLinks) can be modified.
       This current API supports the operations of modifying external
       networks only and does not support the following operations.

       * Adding and deleting external networks.
       * Modifying, adding, and deleting internal networks.

How to Change VM created by image to VM created by new image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute Change Current VNF Package CLI command. After complete this change
operation you should check resource status by Heat CLI commands.

1. check 'ID' and 'Stack Status' of the stack before and after operation.
This is to confirm that stack 'ID' has changed before and after operation,
and that the Stack update has been updated successfully.

2. check 'physical_resource_id' and 'resource_status' of the VDU and VDU's
parent resource. This is to confirm that 'physical_resource_id' has no change
before and after operation, and that the resource_status has been updated
successfully.

3. check 'image' information of VDU before and after operation. This is to
confirm that VDU's has changed successfully.
See `Heat CLI reference`_. for details on Heat CLI commands.

.. note::
   Both single VM and VM created by ``OS::Heat::AutoScalingGroup`` support
   change from image to image.
   The single VM is created directly by ``OS::Nova::Server`` defined in the
   top heat template.

* Check point 1 before operation

  Stack information before operation:

  .. code-block:: console

    $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'

  Result:

  .. code-block:: console

    +--------------------------------------+------------------------------------------+-----------------+
    | ID                                   | Stack Name                               | Stack Status    |
    +--------------------------------------+------------------------------------------+-----------------+
    | 5330ea82-0fd6-4a29-a796-0646e7c6815f | vnf-7f8e5afa-101e-4e0b-a936-62fe01ef1b25 | CREATE_COMPLETE |
    +--------------------------------------+------------------------------------------+-----------------+

* Check point 2 before operation

  Stack resource information before operation:

  .. code-block:: console

    $ openstack stack resource list 5330ea82-0fd6-4a29-a796-0646e7c6815f \
      --filter type='OS::Heat::AutoScalingGroup'

  Result:

  .. code-block:: console

    +---------------+--------------------------------------+----------------------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type              | resource_status | updated_time         |
    +---------------+--------------------------------------+----------------------------+-----------------+----------------------+
    | VDU1_scale    | 2ebbff6f-cd91-489b-a758-1c98e7ff5153 | OS::Heat::AutoScalingGroup | CREATE_COMPLETE | 2022-03-16T07:02:51Z |
    +---------------+--------------------------------------+----------------------------+-----------------+----------------------+

  VDU(created by ``OS::Heat::AutoScalingGroup``)'s parent information
  before operation:

  .. code-block:: console

    $ openstack stack resource list 2ebbff6f-cd91-489b-a758-1c98e7ff5153


  Result:

  .. code-block:: console

    +---------------+--------------------------------------+---------------------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type             | resource_status | updated_time         |
    +---------------+--------------------------------------+---------------------------+-----------------+----------------------+
    | xgaeg5oul435  | f96d0234-1486-47e4-8fd5-ec986e46c01e | base_hot_nested_VDU1.yaml | CREATE_COMPLETE | 2022-03-16T07:02:51Z |
    +---------------+--------------------------------------+---------------------------+-----------------+----------------------+

  VDU(created by ``OS::Heat::AutoScalingGroup``) information before operation:

  .. code-block:: console

    $ openstack stack resource list f96d0234-1486-47e4-8fd5-ec986e46c01e


  Result:

  .. code-block:: console

    +---------------+--------------------------------------+-------------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type     | resource_status | updated_time         |
    +---------------+--------------------------------------+-------------------+-----------------+----------------------+
    | VDU1          | 0810da4d-3466-4852-aa92-60ad05027b5a | OS::Nova::Server  | CREATE_COMPLETE | 2022-03-16T07:02:52Z |
    | VDU1_CP1      | 0bb0a091-b53f-484c-8050-77a44c2537f6 | OS::Neutron::Port | CREATE_COMPLETE | 2022-03-16T07:02:52Z |
    +---------------+--------------------------------------+-------------------+-----------------+----------------------+

  VDU(single) information before operation:

  .. code-block:: console

    $ openstack stack resource list 5330ea82-0fd6-4a29-a796-0646e7c6815f


  Result:

  .. code-block:: console

    +----------------+--------------------------------------+----------------------------+-----------------+----------------------+--------------------------------------------------------------------------------------------+
    | resource_name  | physical_resource_id                 | resource_type              | resource_status | updated_time         | stack_name                                                                                 |
    +----------------+--------------------------------------+----------------------------+-----------------+----------------------+--------------------------------------------------------------------------------------------+
    | VDU2           | 2fefd9f9-b4d0-4313-a80f-e3db7df9a6bc | OS::Nova::Server           | CREATE_COMPLETE | 2022-03-16T07:02:49Z | vnf-7f8e5afa-101e-4e0b-a936-62fe01ef1b25                                                   |
    +----------------+--------------------------------------+----------------------------+-----------------+----------------------+--------------------------------------------------------------------------------------------+

* Check point 3 before operation

  VDU(created by ``OS::Heat::AutoScalingGroup``) detailed information before
  operation:

  .. code-block:: console

    $ openstack stack resource show f96d0234-1486-47e4-8fd5-ec986e46c01e VDU1 \
      -c attributes --fit-width


  Result:

  .. code-block:: console

    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field                  | Value                                                                                                                                                                                                                            |
    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | attributes             | {'id': '0810da4d-3466-4852-aa92-60ad05027b5a', 'name': 'VDU1', 'status': 'ACTIVE', 'tenant_id': '11ee4693b37c4b7995ab2ae331e9adf3', 'user_id': '26ee3a6213f049b18e88b09ff282e817', 'metadata': {}, 'hostId':                     |
    |                        | '8e3b497672d982efde3d3f6abaab5c8c1cd770ed8b95a24daf914d5c', 'image': {'id': '3f87132d-0c98-42a6-aa7b-b7db1f25e4fa', 'links': [{'rel': 'bookmark', 'href':                                                                        |
    |                        | 'http://192.168.10.115/compute/images/3f87132d-0c98-42a6-aa7b-b7db1f25e4fa'}]}, 'flavor': {'vcpus': 1, 'ram': 512, 'disk': 1, 'ephemeral': 0, 'swap': 0, 'original_name': 'm1.tiny', 'extra_specs': {'hw_rng:allowed': 'True'}}, |
    |                        | 'created': '2022-03-16T07:02:54Z', 'updated': '2022-03-16T07:03:02Z', 'addresses': {'net0': [{'version': 4, 'addr': '10.10.0.250', 'OS-EXT-IPS:type': 'fixed', 'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:00:b8:21'}]}, 'accessIPv4':  |
    |                        | '', 'accessIPv6': '', 'links': [{'rel': 'self', 'href': 'http://192.168.10.115/compute/v2.1/servers/0810da4d-3466-4852-aa92-60ad05027b5a'}, {'rel': 'bookmark', 'href':                                                          |
    |                        | 'http://192.168.10.115/compute/servers/0810da4d-3466-4852-aa92-60ad05027b5a'}], 'OS-DCF:diskConfig': 'MANUAL', 'progress': 0, 'OS-EXT-AZ:availability_zone': 'nova', 'config_drive': '', 'key_name': None, 'OS-SRV-              |
    |                        | USG:launched_at': '2022-03-16T07:07:07.000000', 'OS-SRV-USG:terminated_at': None, 'security_groups': [{'name': 'default'}], 'OS-EXT-SRV-ATTR:host': 'compute01', 'OS-EXT-SRV-ATTR:instance_name': 'instance-00000649', 'OS-EXT-  |
    |                        | SRV-ATTR:hypervisor_hostname': 'compute01', 'OS-EXT-SRV-ATTR:reservation_id': 'r-9amm9w8i', 'OS-EXT-SRV-ATTR:launch_index': 0, 'OS-EXT-SRV-ATTR:hostname': 'vdu1', 'OS-EXT-SRV-ATTR:kernel_id': '', 'OS-EXT-SRV-                 |
    |                        | ATTR:ramdisk_id': '', 'OS-EXT-SRV-ATTR:root_device_name': '/dev/vda', 'OS-EXT-SRV-ATTR:user_data': '...'                                                                                                                         |
    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

  VDU(single) detailed information before operation:

  .. code-block:: console

    $ openstack stack resource show 5330ea82-0fd6-4a29-a796-0646e7c6815f VDU2 \
      -c attributes --fit-width


  Result:

  .. code-block:: console

    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field                  | Value                                                                                                                                                                                                                            |
    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | attributes             | {'id': '2fefd9f9-b4d0-4313-a80f-e3db7df9a6bc', 'name': 'vn-5afa-101e-4e0b-a936-62fe01ef1b25-VDU2-hvcqmgvy3btj', 'status': 'ACTIVE', 'tenant_id': '11ee4693b37c4b7995ab2ae331e9adf3', 'user_id':                                  |
    |                        | '26ee3a6213f049b18e88b09ff282e817', 'metadata': {}, 'hostId': '8e3b497672d982efde3d3f6abaab5c8c1cd770ed8b95a24daf914d5c', 'image': {'id': '3f87132d-0c98-42a6-aa7b-b7db1f25e4fa', 'links': [{'rel': 'bookmark', 'href':          |
    |                        | 'http://192.168.10.115/compute/images/18fd7e66-c81f-48bb-bf18-d523996ce59c'}]}, 'flavor': {'vcpus': 1, 'ram': 512, 'disk': 1, 'ephemeral': 0, 'swap': 0, 'original_name': 'm1.tiny', 'extra_specs': {'hw_rng:allowed': 'True'}}, |
    |                        | 'created': '2022-03-16T07:02:53Z', 'updated': '2022-03-16T07:03:53Z', 'addresses': {'net0': [{'version': 4, 'addr': '10.10.0.101', 'OS-EXT-IPS:type': 'fixed', 'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:7e:04:de'}]}, 'accessIPv4':  |
    |                        | '', 'accessIPv6': '', 'links': [{'rel': 'self', 'href': 'http://192.168.10.115/compute/v2.1/servers/2fefd9f9-b4d0-4313-a80f-e3db7df9a6bc'}, {'rel': 'bookmark', 'href':                                                          |
    |                        | 'http://192.168.10.115/compute/servers/2fefd9f9-b4d0-4313-a80f-e3db7df9a6bc'}], 'OS-DCF:diskConfig': 'MANUAL', 'progress': 0, 'OS-EXT-AZ:availability_zone': 'nova', 'config_drive': '', 'key_name': None, 'OS-SRV-              |
    |                        | USG:launched_at': '2022-03-16T07:07:10.000000', 'OS-SRV-USG:terminated_at': None, 'security_groups': [{'name': 'default'}], 'OS-EXT-SRV-ATTR:host': 'compute01', 'OS-EXT-SRV-ATTR:instance_name': 'instance-00000648', 'OS-EXT-  |
    |                        | SRV-ATTR:hypervisor_hostname': 'compute01', 'OS-EXT-SRV-ATTR:reservation_id': 'r-dgt54f2r', 'OS-EXT-SRV-ATTR:launch_index': 0, 'OS-EXT-SRV-ATTR:hostname': 'vn-5afa-101e-4e0b-a936-62fe01ef1b25-vdu2-hvcqmgvy3btj', 'OS-EXT-SRV- |
    |                        | ATTR:kernel_id': '', 'OS-EXT-SRV-ATTR:ramdisk_id': '', 'OS-EXT-SRV-ATTR:root_device_name': '/dev/vda', 'OS-EXT-SRV-ATTR:user_data': '...'                                                                                        |
    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

* Execute Change Current VNF Package

  Change Current VNF Package execution of the entire VNF:

  .. code-block:: console

    $ openstack vnflcm change-vnfpkg VNF_INSTANCE_ID \
         ./sample_param_file_for_multi_resources.json \
         --os-tacker-api-version 2

  Result:

  .. code-block:: console

    Change Current VNF Package for VNF Instance 7f8e5afa-101e-4e0b-a936-62fe01ef1b25 has been accepted.

* Check point 1 after operation

  Stack information after operation:

  .. code-block:: console

    $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'

  Result:

  .. code-block:: console

    +--------------------------------------+------------------------------------------+-----------------+
    | ID                                   | Stack Name                               | Stack Status    |
    +--------------------------------------+------------------------------------------+-----------------+
    | 5330ea82-0fd6-4a29-a796-0646e7c6815f | vnf-7f8e5afa-101e-4e0b-a936-62fe01ef1b25 | UPDATE_COMPLETE |
    +--------------------------------------+------------------------------------------+-----------------+
  .. note::
         'Stack Status' transitions to UPDATE_COMPLETE.

* Check point 2 after operation

  Stack resource information after operation:

  .. code-block:: console

    $ openstack stack resource list 5330ea82-0fd6-4a29-a796-0646e7c6815f \
      --filter type='OS::Heat::AutoScalingGroup'

  Result:

  .. code-block:: console

    +---------------+--------------------------------------+----------------------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type              | resource_status | updated_time         |
    +---------------+--------------------------------------+----------------------------+-----------------+----------------------+
    | VDU1_scale    | 2ebbff6f-cd91-489b-a758-1c98e7ff5153 | OS::Heat::AutoScalingGroup | UPDATE_COMPLETE | 2022-03-16T07:14:19Z |
    +---------------+--------------------------------------+----------------------------+-----------------+----------------------+

  VDU(created by ``OS::Heat::AutoScalingGroup``)'s parent information
  after operation:

  .. code-block:: console

    $ openstack stack resource list 2ebbff6f-cd91-489b-a758-1c98e7ff5153

  Result:

  .. code-block:: console

    +---------------+--------------------------------------+---------------------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type             | resource_status | updated_time         |
    +---------------+--------------------------------------+---------------------------+-----------------+----------------------+
    | xgaeg5oul435  | f96d0234-1486-47e4-8fd5-ec986e46c01e | base_hot_nested_VDU1.yaml | UPDATE_COMPLETE | 2022-03-16T07:14:19Z |
    +---------------+--------------------------------------+---------------------------+-----------------+----------------------+
  .. note::
         'resource_status' transitions to UPDATE_COMPLETE.

  VDU(created by ``OS::Heat::AutoScalingGroup``) information after operation:

  .. code-block:: console

    $ openstack stack resource list f96d0234-1486-47e4-8fd5-ec986e46c01e

  Result:

  .. code-block:: console

    +---------------+--------------------------------------+-------------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type     | resource_status | updated_time         |
    +---------------+--------------------------------------+-------------------+-----------------+----------------------+
    | VDU1          | 0810da4d-3466-4852-aa92-60ad05027b5a | OS::Nova::Server  | UPDATE_COMPLETE | 2022-03-16T07:13:32Z |
    | VDU1_CP1      | 0bb0a091-b53f-484c-8050-77a44c2537f6 | OS::Neutron::Port | CREATE_COMPLETE | 2022-03-16T07:02:52Z |
    +---------------+--------------------------------------+-------------------+-----------------+----------------------+
  .. note::
         'resource_status' transitions to UPDATE_COMPLETE.

  VDU(single) information after operation:

  .. code-block:: console

    $ openstack stack resource list 5330ea82-0fd6-4a29-a796-0646e7c6815f

  Result:

  .. code-block:: console

    +----------------+--------------------------------------+----------------------------+-----------------+----------------------+--------------------------------------------------------------------------------------------+
    | resource_name  | physical_resource_id                 | resource_type              | resource_status | updated_time         | stack_name                                                                                 |
    +----------------+--------------------------------------+----------------------------+-----------------+----------------------+--------------------------------------------------------------------------------------------+
    | VDU2           | 2fefd9f9-b4d0-4313-a80f-e3db7df9a6bc | OS::Nova::Server           | UPDATE_COMPLETE | 2022-03-16T07:13:58Z | vnf-7f8e5afa-101e-4e0b-a936-62fe01ef1b25                                                   |
    +----------------+--------------------------------------+----------------------------+-----------------+----------------------+--------------------------------------------------------------------------------------------+

* Check point 3 after operation

  VDU(created by ``OS::Heat::AutoScalingGroup``) detailed information after
  operation:

  .. code-block:: console

    $ openstack stack resource show f96d0234-1486-47e4-8fd5-ec986e46c01e VDU1 \
      -c attributes --fit-width

  Result:

  .. code-block:: console

    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field                  | Value                                                                                                                                                                                                                            |
    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | attributes             | {'id': '0810da4d-3466-4852-aa92-60ad05027b5a', 'name': 'VDU1', 'status': 'ACTIVE', 'tenant_id': '11ee4693b37c4b7995ab2ae331e9adf3', 'user_id': '26ee3a6213f049b18e88b09ff282e817', 'metadata': {}, 'hostId':                     |
    |                        | '8e3b497672d982efde3d3f6abaab5c8c1cd770ed8b95a24daf914d5c', 'image': {'id': '68da152a-13af-43f6-aaaa-a7b88123d654', 'links': [{'rel': 'bookmark', 'href':                                                                        |
    |                        | 'http://192.168.10.115/compute/images/68da152a-13af-43f6-aaaa-a7b88123d654'}]}, 'flavor': {'vcpus': 1, 'ram': 512, 'disk': 1, 'ephemeral': 0, 'swap': 0, 'original_name': 'm1.tiny', 'extra_specs': {'hw_rng:allowed': 'True'}}, |
    |                        | 'created': '2022-03-16T07:02:54Z', 'updated': '2022-03-16T07:13:41Z', 'addresses': {'net0': [{'version': 4, 'addr': '10.10.0.250', 'OS-EXT-IPS:type': 'fixed', 'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:00:b8:21'}]}, 'accessIPv4':  |
    |                        | '', 'accessIPv6': '', 'links': [{'rel': 'self', 'href': 'http://192.168.10.115/compute/v2.1/servers/0810da4d-3466-4852-aa92-60ad05027b5a'}, {'rel': 'bookmark', 'href':                                                          |
    |                        | 'http://192.168.10.115/compute/servers/0810da4d-3466-4852-aa92-60ad05027b5a'}], 'OS-DCF:diskConfig': 'MANUAL', 'progress': 0, 'OS-EXT-AZ:availability_zone': 'nova', 'config_drive': '', 'key_name': None, 'OS-SRV-              |
    |                        | USG:launched_at': '2022-03-16T07:17:46.000000', 'OS-SRV-USG:terminated_at': None, 'security_groups': [{'name': 'default'}], 'OS-EXT-SRV-ATTR:host': 'compute01', 'OS-EXT-SRV-ATTR:instance_name': 'instance-00000649', 'OS-EXT-  |
    |                        | SRV-ATTR:hypervisor_hostname': 'compute01', 'OS-EXT-SRV-ATTR:reservation_id': 'r-9amm9w8i', 'OS-EXT-SRV-ATTR:launch_index': 0, 'OS-EXT-SRV-ATTR:hostname': 'vdu1', 'OS-EXT-SRV-ATTR:kernel_id': '', 'OS-EXT-SRV-                 |
    |                        | ATTR:ramdisk_id': '', 'OS-EXT-SRV-ATTR:root_device_name': '/dev/vda', 'OS-EXT-SRV-ATTR:user_data': '...'                                                                                                                         |
    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

  .. note:: You can check 'image'->'id' has changed from
    '3f87132d-0c98-42a6-aa7b-b7db1f25e4fa' to
    '68da152a-13af-43f6-aaaa-a7b88123d654'.

  VDU(single) detailed information after operation:

  .. code-block:: console

    $ openstack stack resource show 5330ea82-0fd6-4a29-a796-0646e7c6815f VDU2 \
      -c attributes --fit-width

  Result:

  .. code-block:: console

    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field                  | Value                                                                                                                                                                                                                            |
    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | attributes             | {'id': '2fefd9f9-b4d0-4313-a80f-e3db7df9a6bc', 'name': 'vn-5afa-101e-4e0b-a936-62fe01ef1b25-VDU2-hvcqmgvy3btj', 'status': 'ACTIVE', 'tenant_id': '11ee4693b37c4b7995ab2ae331e9adf3', 'user_id':                                  |
    |                        | '26ee3a6213f049b18e88b09ff282e817', 'metadata': {}, 'hostId': '8e3b497672d982efde3d3f6abaab5c8c1cd770ed8b95a24daf914d5c', 'image': {'id': '18fd7e66-c81f-48bb-bf18-d523996ce59c', 'links': [{'rel': 'bookmark', 'href':          |
    |                        | 'http://192.168.10.115/compute/images/18fd7e66-c81f-48bb-bf18-d523996ce59c'}]}, 'flavor': {'vcpus': 1, 'ram': 512, 'disk': 1, 'ephemeral': 0, 'swap': 0, 'original_name': 'm1.tiny', 'extra_specs': {'hw_rng:allowed': 'True'}}, |
    |                        | 'created': '2022-03-16T07:02:53Z', 'updated': '2022-03-16T07:14:05Z', 'addresses': {'net0': [{'version': 4, 'addr': '10.10.0.101', 'OS-EXT-IPS:type': 'fixed', 'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:7e:04:de'}]}, 'accessIPv4':  |
    |                        | '', 'accessIPv6': '', 'links': [{'rel': 'self', 'href': 'http://192.168.10.115/compute/v2.1/servers/2fefd9f9-b4d0-4313-a80f-e3db7df9a6bc'}, {'rel': 'bookmark', 'href':                                                          |
    |                        | 'http://192.168.10.115/compute/servers/2fefd9f9-b4d0-4313-a80f-e3db7df9a6bc'}], 'OS-DCF:diskConfig': 'MANUAL', 'progress': 0, 'OS-EXT-AZ:availability_zone': 'nova', 'config_drive': '', 'key_name': None, 'OS-SRV-              |
    |                        | USG:launched_at': '2022-03-16T07:18:10.000000', 'OS-SRV-USG:terminated_at': None, 'security_groups': [{'name': 'default'}], 'OS-EXT-SRV-ATTR:host': 'compute01', 'OS-EXT-SRV-ATTR:instance_name': 'instance-00000648', 'OS-EXT-  |
    |                        | SRV-ATTR:hypervisor_hostname': 'compute01', 'OS-EXT-SRV-ATTR:reservation_id': 'r-dgt54f2r', 'OS-EXT-SRV-ATTR:launch_index': 0, 'OS-EXT-SRV-ATTR:hostname': 'vn-5afa-101e-4e0b-a936-62fe01ef1b25-vdu2-hvcqmgvy3btj', 'OS-EXT-SRV- |
    |                        | ATTR:kernel_id': '', 'OS-EXT-SRV-ATTR:ramdisk_id': '', 'OS-EXT-SRV-ATTR:root_device_name': '/dev/vda', 'OS-EXT-SRV-ATTR:user_data': '...'                                                                                        |
    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

  .. note:: You can check 'image'->'id' has changed from
    '3f87132d-0c98-42a6-aa7b-b7db1f25e4fa' to
    '18fd7e66-c81f-48bb-bf18-d523996ce59c'.

How to Change VM created by volume to VM created by volume
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute Change Current VNF Package CLI command. After complete this change
operation you should check resource status by Heat CLI commands.

1. check 'ID' and 'Stack Status' of the stack before and after operation.
This is to confirm that stack 'ID' has changed before and after operation,
and that the Stack update has been updated successfully.

2. check 'physical_resource_id' and 'resource_status' of the VDU and VDU's
parent resource. This is to confirm that 'physical_resource_id' of VDU has
changed before and after operation, 'physical_resource_id' of VDU's parent
resource has no change before and after operation, and that the
'resource_status' of VDU has been created successfully, 'resource_status' of
VDU's parent resource has been updated successfully,

3. check 'volume' information of VDU before and after operation. This is to
confirm that VDU's has changed successfully.

.. note:: Both single VM and VM created by ``OS::Heat::AutoScalingGroup`` support
   change from image to image.

* Check point 1 before operation

  Stack information before operation:

  .. code-block:: console

    $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'

  Result:

  .. code-block:: console

    +--------------------------------------+------------------------------------------+-----------------+
    | ID                                   | Stack Name                               | Stack Status    |
    +--------------------------------------+------------------------------------------+-----------------+
    | 9112aa96-c15c-4e79-a86e-dd0d4d0ca971 | vnf-cab27275-4b9d-43ba-be17-fab9b1ba6a43 | CREATE_COMPLETE |
    +--------------------------------------+------------------------------------------+-----------------+

* Check point 2 before operation

  Stack resource information before operation:

  .. code-block:: console

    $ openstack stack resource list 9112aa96-c15c-4e79-a86e-dd0d4d0ca971 \
      --filter type='OS::Heat::AutoScalingGroup'

  Result:

  .. code-block:: console

    +---------------+--------------------------------------+----------------------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type              | resource_status | updated_time         |
    +---------------+--------------------------------------+----------------------------+-----------------+----------------------+
    | VDU1_scale    | 0aaba3e7-b2e1-49ee-98fa-ff7c4380663b | OS::Heat::AutoScalingGroup | CREATE_COMPLETE | 2022-03-18T05:19:06Z |
    +---------------+--------------------------------------+----------------------------+-----------------+----------------------+

  VDU(created by ``OS::Heat::AutoScalingGroup``)'s parent information
  before operation:

  .. code-block:: console

    $ openstack stack resource list 0aaba3e7-b2e1-49ee-98fa-ff7c4380663b

  Result:

  .. code-block:: console

    +---------------+--------------------------------------+---------------------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type             | resource_status | updated_time         |
    +---------------+--------------------------------------+---------------------------+-----------------+----------------------+
    | qkrp3rzmsnrp  | cdf81724-b4a7-4b9f-9dd3-35fddece9c89 | base_hot_nested_VDU1.yaml | CREATE_COMPLETE | 2022-03-18T05:19:06Z |
    +---------------+--------------------------------------+---------------------------+-----------------+----------------------+

  VDU(created by ``OS::Heat::AutoScalingGroup``) information before operation:

  .. code-block:: console

    $ openstack stack resource list cdf81724-b4a7-4b9f-9dd3-35fddece9c89

  Result:

  .. code-block:: console

    +---------------------+--------------------------------------+------------------------+-----------------+----------------------+
    | resource_name       | physical_resource_id                 | resource_type          | resource_status | updated_time         |
    +---------------------+--------------------------------------+------------------------+-----------------+----------------------+
    | VDU1                | 3f3fa0d8-b948-45fe-bd86-41d5d3e28974 | OS::Nova::Server       | CREATE_COMPLETE | 2022-03-18T05:19:07Z |
    | VDU1-VirtualStorage | bbc1786c-cde0-491d-9f39-fcc6ca610146 | OS::Cinder::Volume     | CREATE_COMPLETE | 2022-03-18T05:19:07Z |
    | multi               | 317c1afb-92c5-408f-9709-7a9dbb3b300d | OS::Cinder::VolumeType | CREATE_COMPLETE | 2022-03-18T05:19:07Z |
    | VDU1_CP1            | ebce7083-f345-424b-aa0f-605e7f4a010c | OS::Neutron::Port      | CREATE_COMPLETE | 2022-03-18T05:19:07Z |
    +---------------------+--------------------------------------+------------------------+-----------------+----------------------+

  VDU(single) information before operation:

  .. code-block:: console

    $ openstack stack resource list 9112aa96-c15c-4e79-a86e-dd0d4d0ca971

  Result:

  .. code-block:: console

    +---------------------+--------------------------------------+----------------------------+-----------------+----------------------+
    | resource_name       | physical_resource_id                 | resource_type              | resource_status | updated_time         |
    +---------------------+--------------------------------------+----------------------------+-----------------+----------------------+
    | VDU1_scale_in       | 98ee6547b76e4389a6089cd79becd826     | OS::Heat::ScalingPolicy    | CREATE_COMPLETE | 2022-03-18T05:19:01Z |
    | VDU1_scale_out      | f9f70e79b7eb4ddd945e5de66764398b     | OS::Heat::ScalingPolicy    | CREATE_COMPLETE | 2022-03-18T05:19:02Z |
    | VDU1_scale          | 0aaba3e7-b2e1-49ee-98fa-ff7c4380663b | OS::Heat::AutoScalingGroup | CREATE_COMPLETE | 2022-03-18T05:19:02Z |
    | VDU2                | 23122c2d-d51d-422a-8ad6-6c3625c761b6 | OS::Nova::Server           | CREATE_COMPLETE | 2022-03-18T05:19:02Z |
    | VDU2-VirtualStorage | 68a53b24-83eb-4e88-a605-1e9d922e3ec0 | OS::Cinder::Volume         | CREATE_COMPLETE | 2022-03-18T05:19:02Z |
    | multi               | 04a32f7b-b9b6-484c-a279-37452f807f6d | OS::Cinder::VolumeType     | CREATE_COMPLETE | 2022-03-18T05:19:02Z |
    | VDU2_CP1            | 2637ef79-881e-4c21-9360-86bb232a634d | OS::Neutron::Port          | CREATE_COMPLETE | 2022-03-18T05:19:02Z |
    +---------------------+--------------------------------------+----------------------------+-----------------+----------------------+

* Check point 3 before operation

  VDU(created by ``OS::Heat::AutoScalingGroup``) detailed information before
  operation:

  .. code-block:: console

    $ openstack stack resource show cdf81724-b4a7-4b9f-9dd3-35fddece9c89 VDU1 \
      -c attributes --fit-width

  Result:

  .. code-block:: console

    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field                  | Value                                                                                                                                                                                                                            |
    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | attributes             | {'id': '3f3fa0d8-b948-45fe-bd86-41d5d3e28974', 'name': 'VDU1', 'status': 'ACTIVE', 'tenant_id': 'b7457dcef9374c2fa72e22c452bb04e9', 'user_id': 'ed6a354ef25041ac92c0e445e91cc9a9', 'metadata': {}, 'hostId':                     |
    |                        | '9ffb36d3d791f739fa98677bb1f6baddb01221443abf50c2aabad442', 'image': '', 'flavor': {'vcpus': 1, 'ram': 512, 'disk': 1, 'ephemeral': 0, 'swap': 0, 'original_name': 'm1.tiny', 'extra_specs': {'hw_rng:allowed': 'True'}},        |
    |                        | 'created': '2022-03-18T05:19:22Z', 'updated': '2022-03-18T05:19:35Z', 'addresses': {'net0': [{'version': 4, 'addr': '10.10.0.25', 'OS-EXT-IPS:type': 'fixed', 'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:c4:68:6f'}]}, 'accessIPv4':   |
    |                        | '', 'accessIPv6': '', 'links': [{'rel': 'self', 'href': 'http://192.168.2.100/compute/v2.1/servers/3f3fa0d8-b948-45fe-bd86-41d5d3e28974'}, {'rel': 'bookmark', 'href': 'http://192.168.2.100/compute/servers/3f3fa0d8-b948-45fe- |
    |                        | bd86-41d5d3e28974'}], 'OS-DCF:diskConfig': 'MANUAL', 'progress': 0, 'OS-EXT-AZ:availability_zone': 'osaka', 'config_drive': '', 'key_name': None, 'OS-SRV-USG:launched_at': '2022-03-18T05:19:23.000000', 'OS-SRV-               |
    |                        | USG:terminated_at': None, 'security_groups': [{'name': 'default'}], 'OS-EXT-SRV-ATTR:host': 'compute102', 'OS-EXT-SRV-ATTR:instance_name': 'instance-000007c2', 'OS-EXT-SRV-ATTR:hypervisor_hostname': 'compute102', 'OS-EXT-    |
    |                        | SRV-ATTR:reservation_id': 'r-r0zmi6q4', 'OS-EXT-SRV-ATTR:launch_index': 0, 'OS-EXT-SRV-ATTR:hostname': 'vdu1', 'OS-EXT-SRV-ATTR:kernel_id': '', 'OS-EXT-SRV-ATTR:ramdisk_id': '', 'OS-EXT-SRV-ATTR:root_device_name':            |
    |                        | '/dev/vda', 'OS-EXT-SRV-ATTR:user_data': 'Q29udGVudC1UeXBlOiBtdWx0aXBhcnQvbWl4ZWQ7IGJvdW5kYXJ5PSI9PT09PT09PT09PT09PT04MzE3NTc1OTA5Njg2OTM3MzgxPT0iCk1JTUUtVmVyc2lvbjogMS4wCgotLT09PT09PT09PT09PT09PTgzMTc1NzU5MDk2ODY5MzczODE9PQ |
    |                        | ', 'os-extended-volumes:volumes_attached': [{'id': 'bbc1786c-cde0-491d-9f39-fcc6ca610146', 'delete_on_termination': False}], 'host_status': 'UP', 'locked': False, 'locked_reason': None, 'description': None, 'tags': [],       |
    |                        | 'trusted_image_certificates': None, 'server_groups': [], 'os_collect_config': {}}                                                                                                                                                |
    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

  VDU(single) detailed information before operation:

  .. code-block:: console

    $ openstack stack resource show 9112aa96-c15c-4e79-a86e-dd0d4d0ca971 VDU2 \
      -c attributes --fit-width

  Result:

  .. code-block:: console

    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field                  | Value                                                                                                                                                                                                                            |
    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | attributes             | {'id': '23122c2d-d51d-422a-8ad6-6c3625c761b6', 'name': 'vn-7275-4b9d-43ba-be17-fab9b1ba6a43-VDU2-ngkljvkbmvhp', 'status': 'ACTIVE', 'tenant_id': 'b7457dcef9374c2fa72e22c452bb04e9', 'user_id':                                  |
    |                        | 'ed6a354ef25041ac92c0e445e91cc9a9', 'metadata': {}, 'hostId': 'd2de6a234a80a445a7ee385f445e6084358f3aef2e110d7bc888ccf2', 'image': '', 'flavor': {'vcpus': 1, 'ram': 512, 'disk': 1, 'ephemeral': 0, 'swap': 0, 'original_name': |
    |                        | 'm1.tiny', 'extra_specs': {'hw_rng:allowed': 'True'}}, 'created': '2022-03-18T05:19:16Z', 'updated': '2022-03-18T05:19:30Z', 'addresses': {'net0': [{'version': 4, 'addr': '10.10.0.101', 'OS-EXT-IPS:type': 'fixed', 'OS-EXT-   |
    |                        | IPS-MAC:mac_addr': 'fa:16:3e:30:1a:92'}]}, 'accessIPv4': '', 'accessIPv6': '', 'links': [{'rel': 'self', 'href': 'http://192.168.2.100/compute/v2.1/servers/23122c2d-d51d-422a-8ad6-6c3625c761b6'}, {'rel': 'bookmark', 'href':  |
    |                        | 'http://192.168.2.100/compute/servers/23122c2d-d51d-422a-8ad6-6c3625c761b6'}], 'OS-DCF:diskConfig': 'MANUAL', 'progress': 0, 'OS-EXT-AZ:availability_zone': 'nova', 'config_drive': '', 'key_name': None, 'OS-SRV-               |
    |                        | USG:launched_at': '2022-03-18T05:19:44.000000', 'OS-SRV-USG:terminated_at': None, 'security_groups': [{'name': 'default'}], 'OS-EXT-SRV-ATTR:host': 'compute101', 'OS-EXT-SRV-ATTR:instance_name': 'instance-000007c1', 'OS-EXT- |
    |                        | SRV-ATTR:hypervisor_hostname': 'compute101', 'OS-EXT-SRV-ATTR:reservation_id': 'r-98ncwx8e', 'OS-EXT-SRV-ATTR:launch_index': 0, 'OS-EXT-SRV-ATTR:hostname': 'vn-7275-4b9d-43ba-be17-fab9b1ba6a43-vdu2-ngkljvkbmvhp', 'OS-EXT-    |
    |                        | SRV-ATTR:kernel_id': '', 'OS-EXT-SRV-ATTR:ramdisk_id': '', 'OS-EXT-SRV-ATTR:root_device_name': '/dev/vda', 'OS-EXT-SRV-ATTR:user_data': 'Q29udGVudC1UeXBlOiBtdWx0aXBhcnQvbWl4ZWQ7IGJvdW5kYXJ5PSI9PT09PT09PT09PT09PT0xNjQ2NzE4OTM |
    |                        | ', 'OS-EXT-STS:task_state': None, 'OS-EXT-STS:vm_state': 'active', 'OS-EXT-STS:power_state': 1, 'os-extended-volumes:volumes_attached': [{'id': '68a53b24-83eb-4e88-a605-1e9d922e3ec0', 'delete_on_termination': False}],        |
    |                        | 'host_status': 'UP', 'locked': False, 'locked_reason': None, 'description': None, 'tags': [], 'trusted_image_certificates': None, 'server_groups': [], 'os_collect_config': {}}                                                  |
    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

* Execute Change Current VNF Package

  Change Current VNF Package execution of the entire VNF:

  .. code-block:: console

    $ openstack vnflcm change-vnfpkg VNF_INSTANCE_ID \
         ./sample_param_file_for_multi_resources.json \
         --os-tacker-api-version 2

  Result:

  .. code-block:: console

    Change Current VNF Package for VNF Instance cab27275-4b9d-43ba-be17-fab9b1ba6a43 has been accepted.

* Check point 1 after operation

  Stack information after operation:

  .. code-block:: console

    $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'

  Result:

  .. code-block:: console

    +--------------------------------------+------------------------------------------+-----------------+
    | ID                                   | Stack Name                               | Stack Status    |
    +--------------------------------------+------------------------------------------+-----------------+
    | 9112aa96-c15c-4e79-a86e-dd0d4d0ca971 | vnf-cab27275-4b9d-43ba-be17-fab9b1ba6a43 | UPDATE_COMPLETE |
    +--------------------------------------+------------------------------------------+-----------------+

  .. note::
         'Stack Status' transitions to UPDATE_COMPLETE.

* Check point 2 after operation

  Stack resource information before operation:

  .. code-block:: console

    $ openstack stack resource list 9112aa96-c15c-4e79-a86e-dd0d4d0ca971 \
      --filter type='OS::Heat::AutoScalingGroup'

  Result:

  .. code-block:: console

    +---------------+--------------------------------------+----------------------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type              | resource_status | updated_time         |
    +---------------+--------------------------------------+----------------------------+-----------------+----------------------+
    | VDU1_scale    | 0aaba3e7-b2e1-49ee-98fa-ff7c4380663b | OS::Heat::AutoScalingGroup | UPDATE_COMPLETE | 2022-03-18T05:32:02Z |
    +---------------+--------------------------------------+----------------------------+-----------------+----------------------+

  VDU(created by ``OS::Heat::AutoScalingGroup``)'s parent information
  after operation:

  .. code-block:: console

    $ openstack stack resource list 0aaba3e7-b2e1-49ee-98fa-ff7c4380663b

  Result:

  .. code-block:: console

    +---------------+--------------------------------------+---------------------------+-----------------+----------------------+
    | resource_name | physical_resource_id                 | resource_type             | resource_status | updated_time         |
    +---------------+--------------------------------------+---------------------------+-----------------+----------------------+
    | qkrp3rzmsnrp  | cdf81724-b4a7-4b9f-9dd3-35fddece9c89 | base_hot_nested_VDU1.yaml | UPDATE_COMPLETE | 2022-03-18T05:32:02Z |
    +---------------+--------------------------------------+---------------------------+-----------------+----------------------+

  .. note::
         'resource_status' transitions to UPDATE_COMPLETE.

  VDU(created by ``OS::Heat::AutoScalingGroup``) information after operation:

  .. code-block:: console

    $ openstack stack resource list cdf81724-b4a7-4b9f-9dd3-35fddece9c89

  Result:

  .. code-block:: console

    +---------------------+--------------------------------------+------------------------+-----------------+----------------------+
    | resource_name       | physical_resource_id                 | resource_type          | resource_status | updated_time         |
    +---------------------+--------------------------------------+------------------------+-----------------+----------------------+
    | multi               | 317c1afb-92c5-408f-9709-7a9dbb3b300d | OS::Cinder::VolumeType | CREATE_COMPLETE | 2022-03-18T05:19:07Z |
    | VDU1_CP1            | ebce7083-f345-424b-aa0f-605e7f4a010c | OS::Neutron::Port      | CREATE_COMPLETE | 2022-03-18T05:19:07Z |
    | VDU1-VirtualStorage | 21f9aa89-4456-42a6-8888-f08c8f70933f | OS::Cinder::Volume     | CREATE_COMPLETE | 2022-03-18T05:29:58Z |
    | VDU1                | 7d19f797-eb11-4af5-ba3b-d35349136786 | OS::Nova::Server       | CREATE_COMPLETE | 2022-03-18T05:30:21Z |
    +---------------------+--------------------------------------+------------------------+-----------------+----------------------+

  .. note::
         'resource_status' transitions to CREATE_COMPLETE.
         'physical_resource_id' changes from
         '3f3fa0d8-b948-45fe-bd86-41d5d3e28974' to
         '7d19f797-eb11-4af5-ba3b-d35349136786'.

  VDU(single) information after operation:

  .. code-block:: console

    $ openstack stack resource list 9112aa96-c15c-4e79-a86e-dd0d4d0ca971

  Result:

  .. code-block:: console

    +---------------------+--------------------------------------+----------------------------+-----------------+----------------------+
    | resource_name       | physical_resource_id                 | resource_type              | resource_status | updated_time         |
    +---------------------+--------------------------------------+----------------------------+-----------------+----------------------+
    | VDU1_scale_in       | 98ee6547b76e4389a6089cd79becd826     | OS::Heat::ScalingPolicy    | CREATE_COMPLETE | 2022-03-18T05:19:01Z |
    | VDU1_scale_out      | f9f70e79b7eb4ddd945e5de66764398b     | OS::Heat::ScalingPolicy    | CREATE_COMPLETE | 2022-03-18T05:19:02Z |
    | VDU1_scale          | 0aaba3e7-b2e1-49ee-98fa-ff7c4380663b | OS::Heat::AutoScalingGroup | UPDATE_COMPLETE | 2022-03-18T05:31:55Z |
    | multi               | 04a32f7b-b9b6-484c-a279-37452f807f6d | OS::Cinder::VolumeType     | CREATE_COMPLETE | 2022-03-18T05:19:02Z |
    | VDU2_CP1            | 2637ef79-881e-4c21-9360-86bb232a634d | OS::Neutron::Port          | CREATE_COMPLETE | 2022-03-18T05:19:02Z |
    | VDU2-VirtualStorage | fc0e0fcf-8eb9-4ddc-8194-2df6c1b43a7b | OS::Cinder::Volume         | CREATE_COMPLETE | 2022-03-18T05:31:01Z |
    | VDU2                | 9aeae773-0f5b-4809-a83b-dee09214db90 | OS::Nova::Server           | CREATE_COMPLETE | 2022-03-18T05:31:15Z |
    +---------------------+--------------------------------------+----------------------------+-----------------+----------------------+

  .. note::
         'resource_status' transitions to CREATE_COMPLETE.
         'physical_resource_id' changes from
         '23122c2d-d51d-422a-8ad6-6c3625c761b6' to
         '9aeae773-0f5b-4809-a83b-dee09214db90'.

* Check point 3 after operation

  VDU(created by ``OS::Heat::AutoScalingGroup``) detailed information after
  operation:

  .. code-block:: console

    $ openstack stack resource show cdf81724-b4a7-4b9f-9dd3-35fddece9c89 VDU1 \
      -c attributes --fit-width

  Result:

  .. code-block:: console

    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field                  | Value                                                                                                                                                                                                                            |
    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | attributes             | {'id': '7d19f797-eb11-4af5-ba3b-d35349136786', 'name': 'VDU1', 'status': 'ACTIVE', 'tenant_id': 'b7457dcef9374c2fa72e22c452bb04e9', 'user_id': 'ed6a354ef25041ac92c0e445e91cc9a9', 'metadata': {}, 'hostId':                     |
    |                        | 'd2de6a234a80a445a7ee385f445e6084358f3aef2e110d7bc888ccf2', 'image': '', 'flavor': {'vcpus': 1, 'ram': 512, 'disk': 1, 'ephemeral': 0, 'swap': 0, 'original_name': 'm1.tiny', 'extra_specs': {'hw_rng:allowed': 'True'}},        |
    |                        | 'created': '2022-03-18T05:30:22Z', 'updated': '2022-03-18T05:30:36Z', 'addresses': {'net0': [{'version': 4, 'addr': '10.10.0.25', 'OS-EXT-IPS:type': 'fixed', 'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:c4:68:6f'}]}, 'accessIPv4':   |
    |                        | '', 'accessIPv6': '', 'links': [{'rel': 'self', 'href': 'http://192.168.2.100/compute/v2.1/servers/7d19f797-eb11-4af5-ba3b-d35349136786'}, {'rel': 'bookmark', 'href':                                                           |
    |                        | 'http://192.168.2.100/compute/servers/7d19f797-eb11-4af5-ba3b-d35349136786'}], 'OS-DCF:diskConfig': 'MANUAL', 'progress': 0, 'OS-EXT-AZ:availability_zone': 'nova', 'config_drive': '', 'key_name': None, 'OS-SRV-               |
    |                        | USG:launched_at': '2022-03-18T05:30:50.000000', 'OS-SRV-USG:terminated_at': None, 'security_groups': [{'name': 'default'}], 'OS-EXT-SRV-ATTR:host': 'compute101', 'OS-EXT-SRV-ATTR:instance_name': 'instance-000007c3', 'OS-EXT- |
    |                        | SRV-ATTR:hypervisor_hostname': 'compute101', 'OS-EXT-SRV-ATTR:reservation_id': 'r-nlqgnld4', 'OS-EXT-SRV-ATTR:launch_index': 0, 'OS-EXT-SRV-ATTR:hostname': 'vdu1', 'OS-EXT-SRV-ATTR:kernel_id': '', 'OS-EXT-SRV-                |
    |                        | ATTR:ramdisk_id': '', 'OS-EXT-SRV-ATTR:root_device_name': '/dev/vda', 'OS-EXT-SRV-ATTR:user_data': 'Q29udGVudC1UeXBlOiBtdWx0aXBhcnQvbWl4ZWQ7IGJvdW5kYXJ5PSI9PT09PT09PT09PT09PT04MjE3MDExNTU4', 'OS-EXT-STS:task_state': None,    |
    |                        | 'OS-EXT-STS:vm_state': 'active', 'OS-EXT-STS:power_state': 1, 'os-extended-volumes:volumes_attached': [{'id': '21f9aa89-4456-42a6-8888-f08c8f70933f', 'delete_on_termination': False}], 'host_status': 'UP', 'locked': False,    |
    |                        | 'locked_reason': None, 'description': None, 'tags': [], 'trusted_image_certificates': None, 'server_groups': [], 'os_collect_config': {}}                                                                                        |
    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

  .. note:: You can check 'os-extended-volumes:volumes_attached'->'id'
    has changed from '68a53b24-83eb-4e88-a605-1e9d922e3ec0' to
    '21f9aa89-4456-42a6-8888-f08c8f70933f'.

  VDU(single) detailed information after operation:

  .. code-block:: console

    $ openstack stack resource show 9112aa96-c15c-4e79-a86e-dd0d4d0ca971 VDU2 \
      -c attributes --fit-width

  Result:

  .. code-block:: console

    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field                  | Value                                                                                                                                                                                                                            |
    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | attributes             | {'id': '9aeae773-0f5b-4809-a83b-dee09214db90', 'name': 'vn-7275-4b9d-43ba-be17-fab9b1ba6a43-VDU2-k4inik5wcz3y', 'status': 'ACTIVE', 'tenant_id': 'b7457dcef9374c2fa72e22c452bb04e9', 'user_id':                                  |
    |                        | 'ed6a354ef25041ac92c0e445e91cc9a9', 'metadata': {}, 'hostId': 'd2de6a234a80a445a7ee385f445e6084358f3aef2e110d7bc888ccf2', 'image': '', 'flavor': {'vcpus': 1, 'ram': 512, 'disk': 1, 'ephemeral': 0, 'swap': 0, 'original_name': |
    |                        | 'm1.tiny', 'extra_specs': {'hw_rng:allowed': 'True'}}, 'created': '2022-03-18T05:31:16Z', 'updated': '2022-03-18T05:31:29Z', 'addresses': {'net0': [{'version': 4, 'addr': '10.10.0.101', 'OS-EXT-IPS:type': 'fixed', 'OS-EXT-   |
    |                        | IPS-MAC:mac_addr': 'fa:16:3e:30:1a:92'}]}, 'accessIPv4': '', 'accessIPv6': '', 'links': [{'rel': 'self', 'href': 'http://192.168.2.100/compute/v2.1/servers/9aeae773-0f5b-4809-a83b-dee09214db90'}, {'rel': 'bookmark', 'href':  |
    |                        | 'http://192.168.2.100/compute/servers/9aeae773-0f5b-4809-a83b-dee09214db90'}], 'OS-DCF:diskConfig': 'MANUAL', 'progress': 0, 'OS-EXT-AZ:availability_zone': 'nova', 'config_drive': '', 'key_name': None, 'OS-SRV-               |
    |                        | USG:launched_at': '2022-03-18T05:31:43.000000', 'OS-SRV-USG:terminated_at': None, 'security_groups': [{'name': 'default'}], 'OS-EXT-SRV-ATTR:host': 'compute101', 'OS-EXT-SRV-ATTR:instance_name': 'instance-000007c4', 'OS-EXT- |
    |                        | SRV-ATTR:hypervisor_hostname': 'compute101', 'OS-EXT-SRV-ATTR:reservation_id': 'r-gonky2fj', 'OS-EXT-SRV-ATTR:launch_index': 0, 'OS-EXT-SRV-ATTR:hostname': 'vn-7275-4b9d-43ba-be17-fab9b1ba6a43-vdu2-k4inik5wcz3y', 'OS-EXT-    |
    |                        | S', 'OS-EXT-STS:task_state': None, 'OS-EXT-STS:vm_state': 'active', 'OS-EXT-STS:power_state': 1, 'os-extended-volumes:volumes_attached': [{'id': 'fc0e0fcf-8eb9-4ddc-8194-2df6c1b43a7b', 'delete_on_termination': False}],       |
    |                        | 'host_status': 'UP', 'locked': False, 'locked_reason': None, 'description': None, 'tags': [], 'trusted_image_certificates': None, 'server_groups': [], 'os_collect_config': {}}                                                  |
    +------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

  .. note:: You can check 'os-extended-volumes:volumes_attached'->'id' has
    changed from '68a53b24-83eb-4e88-a605-1e9d922e3ec0' to
    'fc0e0fcf-8eb9-4ddc-8194-2df6c1b43a7b'.

.. _Heat CLI reference : https://docs.openstack.org/python-openstackclient/latest/cli/plugin-commands/heat.html
.. _VNF Package for Common instantiate: https://opendev.org/openstack/tacker/src/branch/master/tacker/tests/functional/sol_v2/samples/test_instantiate_vnf_with_old_image_or_volume/contents
.. _change from image to image: https://opendev.org/openstack/tacker/src/branch/master/tacker/tests/functional/sol_v2/samples/test_change_vnf_pkg_with_new_image/contents
.. _change from image to volume: https://opendev.org/openstack/tacker/src/branch/master/tacker/tests/functional/sol_v2/samples/test_change_vnf_pkg_with_new_volume/contents
.. _change from volume to image: https://opendev.org/openstack/tacker/src/branch/master/tacker/tests/functional/sol_v2/samples/test_change_vnf_pkg_with_new_image/contents
.. _change from volume to volume: https://opendev.org/openstack/tacker/src/branch/master/tacker/tests/functional/sol_v2/samples/test_change_vnf_pkg_with_new_volume/contents
.. _ETSI SOL002 v3.5.1: https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/002/03.05.01_60/gs_nfv-sol002v030501p.pdf
