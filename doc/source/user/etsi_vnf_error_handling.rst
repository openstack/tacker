===============================
ETSI NFV-SOL VNF error-handling
===============================

This document describes how to error-handling VNF in Tacker v1 API.

.. note::

  This is a document for Tacker v1 API.
  See :doc:`/user/v2/error_handling` for Tacker v2 API.


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


VNF Error-handling Procedures
-----------------------------

As mentioned in Prerequisites, the VNF must be created
before performing error-handling.

Details of CLI commands are described in
:doc:`/cli/cli-etsi-vnflcm`.

There are some operations to error-handling VNF.

* Rollback VNF lifecycle management operation
* Fail VNF lifecycle management operation
* Retry VNF lifecycle management operation

In order to execute error-handling, it is necessary to specify
VNF_LCM_OP_OCC_ID, which is the ID for the target LCM operation.
First, the method of specifying the ID will be described.


Identify VNF_LCM_OP_OCC_ID
~~~~~~~~~~~~~~~~~~~~~~~~~~

The VNF_LCM_OP_OCC_ID can be obtained via CLI.

Details of CLI commands are described in
:doc:`/cli/cli-etsi-vnflcm`.

Before checking the "VNF_LCM_OP_OCC_ID", you should get VNF_INSTANCE_ID first.

.. code-block:: console

  $ openstack vnflcm op list


Result:

.. code-block:: console

  $ openstack vnflcm op list
  +--------------------------------------+-----------------+--------------------------------------+-------------+
  | ID                                   | Operation State | VNF Instance ID                      | Operation   |
  +--------------------------------------+-----------------+--------------------------------------+-------------+
  | c7afb90a-351b-4d33-a945-8f937deeadb4 | FAILED_TEMP     | d45ae5cb-121b-4420-bc97-6a00f5fa63b6 | INSTANTIATE |
  +--------------------------------------+-----------------+--------------------------------------+-------------+


Error-handling can be executed only when **operationState** is **FAILED_TMP**.

If the Subscription is registered, the above operation trigger
that caused the FAILED_TEMP send a 'Notification' to the **callbackUri**
of the Subscription.

**vnfLcmOpOccId** included in this 'Notification' corresponds
to VNF_LCM_OP_OCC_ID.

See `VNF LCM v1 API`_ for details on the APIs used here.


Rollback VNF LCM Operation
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 10 40 15 15
   :header-rows: 1

   * - LCM Operation
     - Description of Rollback
     - Precondition
     - Postcondition
   * - Instantiate
     - | VNFM removes all VMs and resources.
       | e.g. Tacker executes Heat stack-delete for deletion of the target VM.
     - FAILED_TEMP
     - ROLLED_BACK or FAILED_TEMP
   * - Scale-out
     - | VNFM reverts changes of VMs and resources specified in the middle of scale-out operation.
       | As a result, the oldest VNFc(VM) is deleted.
       | e.g. Tacker reverts desired_capacity and executes Heat stack-update.
     - FAILED_TEMP
     - ROLLED_BACK or FAILED_TEMP


This manual describes the following operations as use cases for
rollback operations.

* "Instantiate VNF" fails
* Rollback VNF lifecycle management operation
* Delete VNF

As shown below, if "Instantiate VNF" fails, "Delete VNF" cannot be executed
without executing "Rollback VNF lifecycle management operation".

.. code-block:: console

  $ openstack vnflcm delete VNF_INSTANCE_ID


Result:

.. code-block:: console

  Failed to delete vnf instance with ID 'd45ae5cb-121b-4420-bc97-6a00f5fa63b6': Vnf d45ae5cb-121b-4420-bc97-6a00f5fa63b6 in status ERROR. Cannot delete while the vnf is in this state.
  Failed to delete 1 of 1 vnf instances.


Therefore, "Rollback VNF lifecycle management operation" with
the following CLI command.

.. code-block:: console

  $ openstack vnflcm op rollback VNF_LCM_OP_OCC_ID


Result:

.. code-block:: console

  Rollback request for LCM operation c7afb90a-351b-4d33-a945-8f937deeadb4 has been accepted


If "Rollback VNF lifecycle management operation" is successful,
then "Delete VNF" is also successful.

.. code-block:: console

  $ openstack vnflcm delete VNF_INSTANCE_ID


Result:

.. code-block:: console

  Vnf instance 'd45ae5cb-121b-4420-bc97-6a00f5fa63b6' is deleted successfully


Fail VNF LCM Operation
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 10 40 15 15
   :header-rows: 1

   * - LCM Operation
     - Description of Fail
     - Precondition
     - Postcondition
   * - Instantiate
     - Tacker simply changes LCM operation state to "FAILED" on Tacker-DB.
     - FAILED_TEMP
     - FAILED
   * - Terminate
     - Tacker simply changes LCM operation state to "FAILED" on Tacker-DB.
     - FAILED_TEMP
     - FAILED
   * - Heal
     - Tacker simply changes LCM operation state to "FAILED" on Tacker-DB.
     - FAILED_TEMP
     - FAILED
   * - Scale
     - Tacker simply changes LCM operation state to "FAILED" on Tacker-DB.
     - FAILED_TEMP
     - FAILED
   * - Modify
     - Tacker simply changes LCM operation state to "FAILED" on Tacker-DB.
     - FAILED_TEMP
     - FAILED
   * - Change external connectivity
     - Tacker simply changes LCM operation state to "FAILED" on Tacker-DB.
     - FAILED_TEMP
     - FAILED


This manual describes the following operations as use cases for
fail operations.

* "Instantiate VNF" fails
* Fail VNF lifecycle management operation
* Delete VNF

As shown below, if "Instantiate VNF" fails, "Delete VNF" cannot be executed
after executing "Fail VNF lifecycle management operation".

.. code-block:: console

  $ openstack vnflcm delete VNF_INSTANCE_ID


Result:

.. code-block:: console

  Failed to delete vnf instance with ID 'd45ae5cb-121b-4420-bc97-6a00f5fa63b6': Vnf d45ae5cb-121b-4420-bc97-6a00f5fa63b6 in status ERROR. Cannot delete while the vnf is in this state.
  Failed to delete 1 of 1 vnf instances.


Therefore, "Fail VNF lifecycle management operation" with
the following CLI command.

.. code-block:: console

  $ openstack vnflcm op fail VNF_LCM_OP_OCC_ID


Result:

.. code-block:: console

  +-------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field                   | Value                                                                                                                                                                                                                            |
  +-------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Error                   | {                                                                                                                                                                                                                                |
  |                         |     "title": "",                                                                                                                                                                                                                 |
  |                         |     "status": 500,                                                                                                                                                                                                               |
  |                         |     "detail": "ProblemDetails(created_at=<?>,deleted=0,deleted_at=<?>,detail='Vnf instantiation wait failed for vnf d45ae5cb-121b-4420-bc97-6a00f5fa63b6, error: VNF Create Resource CREATE failed: ResourceInError:             |
  |                         | resources.VDU1.resources.ril4bssciahp.resources.VDU1: Went to status ERROR due to \"Message: Build of instance 6dacc4a4-948f-4f40-97cf-2caeecbba013 aborted: privsep helper command exited non-zero (1), Code:                   |
  |                         | 500\"',status=500,title='',updated_at=<?>)"                                                                                                                                                                                      |
  |                         | }                                                                                                                                                                                                                                |
  | ID                      | c7afb90a-351b-4d33-a945-8f937deeadb4                                                                                                                                                                                             |
  | Is Automatic Invocation | False                                                                                                                                                                                                                            |
  | Is Cancel Pending       | False                                                                                                                                                                                                                            |
  | Links                   | {                                                                                                                                                                                                                                |
  |                         |     "self": {                                                                                                                                                                                                                    |
  |                         |         "href": "http://localhost:9890/vnflcm/v1/vnf_lcm_op_occs/c7afb90a-351b-4d33-a945-8f937deeadb4"                                                                                                                           |
  |                         |     },                                                                                                                                                                                                                           |
  |                         |     "vnfInstance": {                                                                                                                                                                                                             |
  |                         |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/d45ae5cb-121b-4420-bc97-6a00f5fa63b6"                                                                                                                             |
  |                         |     },                                                                                                                                                                                                                           |
  |                         |     "retry": {                                                                                                                                                                                                                   |
  |                         |         "href": "http://localhost:9890/vnflcm/v1/vnf_lcm_op_occs/c7afb90a-351b-4d33-a945-8f937deeadb4/retry"                                                                                                                     |
  |                         |     },                                                                                                                                                                                                                           |
  |                         |     "rollback": {                                                                                                                                                                                                                |
  |                         |         "href": "http://localhost:9890/vnflcm/v1/vnf_lcm_op_occs/c7afb90a-351b-4d33-a945-8f937deeadb4/rollback"                                                                                                                  |
  |                         |     },                                                                                                                                                                                                                           |
  |                         |     "grant": {                                                                                                                                                                                                                   |
  |                         |         "href": "http://localhost:9890/vnflcm/v1/vnf_lcm_op_occs/c7afb90a-351b-4d33-a945-8f937deeadb4/grant"                                                                                                                     |
  |                         |     },                                                                                                                                                                                                                           |
  |                         |     "fail": {                                                                                                                                                                                                                    |
  |                         |         "href": "http://localhost:9890/vnflcm/v1/vnf_lcm_op_occs/c7afb90a-351b-4d33-a945-8f937deeadb4/fail"                                                                                                                      |
  |                         |     }                                                                                                                                                                                                                            |
  |                         | }                                                                                                                                                                                                                                |
  | Operation               | INSTANTIATE                                                                                                                                                                                                                      |
  | Operation State         | FAILED                                                                                                                                                                                                                           |
  | Start Time              | 2023-12-27 07:05:59+00:00                                                                                                                                                                                                        |
  | State Entered Time      | 2024-01-18 01:40:55.105358+00:00                                                                                                                                                                                                 |
  | VNF Instance ID         | d45ae5cb-121b-4420-bc97-6a00f5fa63b6                                                                                                                                                                                             |
  | grantId                 | None                                                                                                                                                                                                                             |
  | operationParams         | "{\"flavourId\": \"simple\", \"instantiationLevelId\": \"instantiation_level_1\", \"extVirtualLinks\": [{\"id\": \"91bcff6d-4703-4ba9-b1c2-009e6db92a9c\", \"resourceId\": \"3019b1e7-99d8-4748-97ac-104922bc78d9\",             |
  |                         | \"vimConnectionId\": \"79a97d01-e5f3-4eaa-b2bc-8f513ecb8a56\", \"extCps\": [{\"cpdId\": \"VDU1_CP1\", \"cpConfig\": [{\"linkPortId\": \"6b7c0b3a-cc2d-4b94-9f6f-81df69a7cc2f\"}]}, {\"cpdId\": \"VDU2_CP1\", \"cpConfig\":       |
  |                         | [{\"linkPortId\": \"02d867e7-b955-4b4a-b92f-c78c7ede63bf\"}]}], \"extLinkPorts\": [{\"id\": \"6b7c0b3a-cc2d-4b94-9f6f-81df69a7cc2f\", \"resourceHandle\": {\"vimConnectionId\": \"79a97d01-e5f3-4eaa-b2bc-8f513ecb8a56\",        |
  |                         | \"resourceId\": \"972a375d-921f-46f5-bfdb-19af95fc49e1\"}}, {\"id\": \"02d867e7-b955-4b4a-b92f-c78c7ede63bf\", \"resourceHandle\": {\"vimConnectionId\": \"79a97d01-e5f3-4eaa-b2bc-8f513ecb8a56\", \"resourceId\":               |
  |                         | \"b853b5c5-cd97-4dfb-8750-cac6e5c62477\"}}]}, {\"id\": \"a96d2f5b-c01a-48e1-813c-76132965042c\", \"resourceId\": \"589a045a-65d9-4f4d-a9b3-35aa655374d0\", \"vimConnectionId\": \"79a97d01-e5f3-4eaa-b2bc-8f513ecb8a56\",        |
  |                         | \"extCps\": [{\"cpdId\": \"VDU1_CP2\", \"cpConfig\": [{\"cpProtocolData\": [{\"layerProtocol\": \"IP_OVER_ETHERNET\", \"ipOverEthernet\": {\"ipAddresses\": [{\"type\": \"IPV4\", \"fixedAddresses\": [\"22.22.1.10\"],          |
  |                         | \"subnetId\": \"d290cae3-0dbc-44a3-a043-1a50ded04a64\"}]}}]}]}, {\"cpdId\": \"VDU2_CP2\", \"cpConfig\": [{\"cpProtocolData\": [{\"layerProtocol\": \"IP_OVER_ETHERNET\", \"ipOverEthernet\": {\"ipAddresses\": [{\"type\":       |
  |                         | \"IPV4\", \"fixedAddresses\": [\"22.22.1.20\"], \"subnetId\": \"d290cae3-0dbc-44a3-a043-1a50ded04a64\"}]}}]}]}]}], \"extManagedVirtualLinks\": [{\"id\": \"8f9d8da0-2386-4f00-bbb0-860f50d32a5a\", \"vnfVirtualLinkDescId\":     |
  |                         | \"internalVL1\", \"resourceId\": \"0e498d08-ed3a-4212-83e0-1b6808f6fcb6\"}, {\"id\": \"11d68761-aab7-419c-955c-0c6497f13692\", \"vnfVirtualLinkDescId\": \"internalVL2\", \"resourceId\": \"38a8d4ba-                            |
  |                         | ac1b-41a2-a92b-ff2a3e5e9b12\"}], \"vimConnectionInfo\": [{\"id\": \"79a97d01-e5f3-4eaa-b2bc-8f513ecb8a56\", \"vimType\": \"ETSINFV.OPENSTACK_KEYSTONE.v_2\", \"vimConnectionId\": \"79a97d01-e5f3-4eaa-b2bc-8f513ecb8a56\",      |
  |                         | \"interfaceInfo\": {\"endpoint\": \"http://127.0.0.1/identity\"}, \"accessInfo\": {\"username\": \"nfv_user\", \"region\": \"RegionOne\", \"password\": \"devstack\", \"tenant\": \"1994d69783d64c00aadab564038c2fd7\"}}],       |
  |                         | \"additionalParams\": {\"lcm-operation-user-data\": \"./UserData/lcm_user_data.py\", \"lcm-operation-user-data-class\": \"SampleUserData\"}}"                                                                                    |
  | resourceChanges         | {}                                                                                                                                                                                                                               |
  +-------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


If "Fail VNF lifecycle management operation" is successful,
then "Delete VNF" is also successful.

.. code-block:: console

  $ openstack vnflcm delete VNF_INSTANCE_ID


Result:

.. code-block:: console

  Vnf instance 'd45ae5cb-121b-4420-bc97-6a00f5fa63b6' is deleted successfully


Retry VNF LCM Operation
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 10 40 15 15
   :header-rows: 1

   * - LCM Operation
     - Description of Fail
     - Precondition
     - Postcondition
   * - Instantiate
     - VNFM retries a Instantiate operation.
     - FAILED_TEMP
     - COMPLETED or FAILED_TEMP
   * - Terminate
     - VNFM retries a Terminate operation.
     - FAILED_TEMP
     - COMPLETED or FAILED_TEMP
   * - Heal
     - VNFM retries a Heal operation.
     - FAILED_TEMP
     - COMPLETED or FAILED_TEMP
   * - Scale
     - VNFM retries a Scale operation.
     - FAILED_TEMP
     - COMPLETED or FAILED_TEMP
   * - Modify
     - VNFM retries a Modify operation.
     - FAILED_TEMP
     - COMPLETED or FAILED_TEMP
   * - Change external connectivity
     - VNFM retries a Change external connectivity operation.
     - FAILED_TEMP
     - COMPLETED or FAILED_TEMP


This manual describes the following operations as use cases for
retry operations.

* "Instantiate VNF" fails
* Retry VNF lifecycle management operation

As shown below, if "Instantiate VNF" fails, If you want re-execute
previous(failed) operation , you execute "Retry" operation.

Therefore, "Retry VNF lifecycle management operation" with
the following CLI command.

.. code-block:: console

  $ openstack vnflcm op retry VNF_LCM_OP_OCC_ID


Result:

.. code-block:: console

  Retry request for LCM operation c7afb90a-351b-4d33-a945-8f937deeadb4 has been accepted


If "Retry VNF lifecycle management operation" is successful,
then another LCM can be operational.


.. _VNF LCM v1 API: https://docs.openstack.org/api-ref/nfv-orchestration/v1/vnflcm.html
