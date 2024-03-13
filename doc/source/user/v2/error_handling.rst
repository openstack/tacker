===============================
ETSI NFV-SOL VNF error-handling
===============================

This document describes how to error-handling VNF in Tacker v2 API.


Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

Execute up to "Instantiate VNF" in the procedure of
:doc:`/user/v2/vnf/deployment_with_user_data/index`.
In other words, the procedure after "Terminate VNF" is not executed.


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

  $ openstack vnflcm op list --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------------------------------+-----------------+--------------------------------------+-------------+
  | ID                                   | Operation State | VNF Instance ID                      | Operation   |
  +--------------------------------------+-----------------+--------------------------------------+-------------+
  | a7f80542-faeb-4324-ba82-c6214307e864 | FAILED_TEMP     | 385fc2ff-1ef5-42f4-8196-3d913160074d | INSTANTIATE |
  +--------------------------------------+-----------------+--------------------------------------+-------------+


Error-handling can be executed only when **operationState** is **FAILED_TMP**.

If the Subscription is registered, the above operation trigger
that caused the FAILED_TEMP send a 'Notification' to the **callbackUri**
of the Subscription.

**vnfLcmOpOccId** included in this 'Notification' corresponds
to VNF_LCM_OP_OCC_ID.

See `VNF LCM v2 API`_ for details on the APIs used here.


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
       | As a result, the newest VNFc(VM) is deleted.
       | e.g. Tacker reverts desired_capacity and executes Heat stack-update.
     - FAILED_TEMP
     - ROLLED_BACK or FAILED_TEMP
   * - Modify
     - VNFM reverts the update of the VNF instance information.
     - FAILED_TEMP
     - ROLLED_BACK or FAILED_TEMP
   * - Change external connectivity
     - | VNFM reverts changes of the external connectivity for VNF instances.
       | e.g. Tacker reverts stack parameters and executes Heat stack-update.
     - FAILED_TEMP
     - ROLLED_BACK or FAILED_TEMP
   * - Change Current VNF Package
     - | VNFM reverts changes of current vnf package for VNF instances.
       | e.g. Tacker reverts stack parameters and executes Heat stack-update.
     - FAILED_TEMP
     - ROLLED_BACK or FAILED_TEMP


.. note::

  In some cases, Rollback of Change external connectivity cannot recover
  the IP address and Port Id of virtual resources.
  If the operation fails before performing VIM processing: updating stack,
  the IP address and Port Id will be recovered by its rollback operation.
  Otherwise, dynamic IP address and Port Id are not recovered
  by rollback operation.


This manual describes the following operations as use cases for
rollback operations.

* "Instantiate VNF" fails
* Rollback VNF lifecycle management operation
* Delete VNF

As shown below, if "Instantiate VNF" fails, "Delete VNF" cannot be executed
without executing "Rollback VNF lifecycle management operation".

.. code-block:: console

  $ openstack vnflcm delete VNF_INSTANCE_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  Failed to delete vnf instance with ID '385fc2ff-1ef5-42f4-8196-3d913160074d': Other LCM operation of vnfInstance 385fc2ff-1ef5-42f4-8196-3d913160074d is in progress.
  Failed to delete 1 of 1 vnf instances.

Therefore, "Rollback VNF lifecycle management operation" with
the following CLI command.

.. code-block:: console

  $ openstack vnflcm op rollback VNF_LCM_OP_OCC_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  Rollback request for LCM operation a7f80542-faeb-4324-ba82-c6214307e864 has been accepted


If "Rollback VNF lifecycle management operation" is successful,
then "Delete VNF" is also successful.

.. code-block:: console

  $ openstack vnflcm delete VNF_INSTANCE_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  Vnf instance '385fc2ff-1ef5-42f4-8196-3d913160074d' is deleted successfully


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
   * - Change Current VNF Package
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

  $ openstack vnflcm delete VNF_INSTANCE_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  Failed to delete vnf instance with ID '385fc2ff-1ef5-42f4-8196-3d913160074d': Other LCM operation of vnfInstance 385fc2ff-1ef5-42f4-8196-3d913160074d is in progress.
  Failed to delete 1 of 1 vnf instances.


Therefore, "Fail VNF lifecycle management operation" with
the following CLI command.

.. code-block:: console

  $ openstack vnflcm op fail VNF_LCM_OP_OCC_ID \
    --fit-width --os-tacker-api-version 2


Result:

.. code-block:: console

  +-------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field                   | Value                                                                                                                                                                                                                            |
  +-------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Error                   | {                                                                                                                                                                                                                                |
  |                         |     "title": "Stack create failed",                                                                                                                                                                                              |
  |                         |     "status": 422,                                                                                                                                                                                                               |
  |                         |     "detail": "Resource CREATE failed: resources.wifiut5qtngn: resources.VDU1_scale_group.Property error: resources.VDU1_CP1.properties.network: Error validating value 'errornetwork': Unable to find network with name or id   |
  |                         | 'errornetwork'"                                                                                                                                                                                                                  |
  |                         | }                                                                                                                                                                                                                                |
  | ID                      | a7f80542-faeb-4324-ba82-c6214307e864                                                                                                                                                                                             |
  | Is Automatic Invocation | False                                                                                                                                                                                                                            |
  | Is Cancel Pending       | False                                                                                                                                                                                                                            |
  | Links                   | {                                                                                                                                                                                                                                |
  |                         |     "self": {                                                                                                                                                                                                                    |
  |                         |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_lcm_op_occs/a7f80542-faeb-4324-ba82-c6214307e864"                                                                                                                           |
  |                         |     },                                                                                                                                                                                                                           |
  |                         |     "vnfInstance": {                                                                                                                                                                                                             |
  |                         |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/385fc2ff-1ef5-42f4-8196-3d913160074d"                                                                                                                             |
  |                         |     },                                                                                                                                                                                                                           |
  |                         |     "retry": {                                                                                                                                                                                                                   |
  |                         |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_lcm_op_occs/a7f80542-faeb-4324-ba82-c6214307e864/retry"                                                                                                                     |
  |                         |     },                                                                                                                                                                                                                           |
  |                         |     "rollback": {                                                                                                                                                                                                                |
  |                         |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_lcm_op_occs/a7f80542-faeb-4324-ba82-c6214307e864/rollback"                                                                                                                  |
  |                         |     },                                                                                                                                                                                                                           |
  |                         |     "fail": {                                                                                                                                                                                                                    |
  |                         |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_lcm_op_occs/a7f80542-faeb-4324-ba82-c6214307e864/fail"                                                                                                                      |
  |                         |     }                                                                                                                                                                                                                            |
  |                         | }                                                                                                                                                                                                                                |
  | Operation               | INSTANTIATE                                                                                                                                                                                                                      |
  | Operation State         | FAILED                                                                                                                                                                                                                           |
  | Start Time              | 2023-11-14T04:32:57Z                                                                                                                                                                                                             |
  | State Entered Time      | 2023-11-14T04:32:57Z                                                                                                                                                                                                             |
  | VNF Instance ID         | 385fc2ff-1ef5-42f4-8196-3d913160074d                                                                                                                                                                                             |
  | grantId                 | 008eccda-5466-4820-ae76-bdce6e128d8c                                                                                                                                                                                             |
  | operationParams         | {                                                                                                                                                                                                                                |
  |                         |     "flavourId": "simple"                                                                                                                                                                                                        |
  |                         | }                                                                                                                                                                                                                                |
  +-------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


If "Fail VNF lifecycle management operation" is successful,
then "Delete VNF" is also successful.

.. code-block:: console

  $ openstack vnflcm delete VNF_INSTANCE_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  Vnf instance '385fc2ff-1ef5-42f4-8196-3d913160074d' is deleted successfully


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
   * - Change Current VNF Package
     - VNFM retries a Change Current VNF Package operation.
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

  $ openstack vnflcm op retry VNF_LCM_OP_OCC_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  Retry request for LCM operation a7f80542-faeb-4324-ba82-c6214307e864 has been accepted


If "Retry VNF lifecycle management operation" is successful,
then another LCM can be operational.


Error-handling of MgmtDriver
----------------------------

Error-handling includes Retry, Rollback and Fail operations.

* For the fail operation, it will not perform LCM when it is executed,
  so there is no need to use MgmtDriver.

* For the retry operation, it will perform the LCM again when it is executed,
  so as long as the LCM is configured with MgmtDriver, the MgmtDriver will
  also be called during the retry operation, and no additional configuration
  is required.

* For the rollback operation,
  because there is no definition of ``rollback_start`` and ``rollback_end`` in
  ``6.7 Interface Types`` of `NFV-SOL001 v2.6.1`_, so when the rollback
  operation is performed, MgmtDriver will not be called.

The VNFD in the VNF Package must be modified before calling MgmtDriver in the
rollback operation.

.. note::

  In the MgmtDriver, the user saves the data that needs to be kept
  when the LCM fails in the ``user_script_err_handling_data`` variable.
  It is saved in the corresponding VNF_LCM_OP_OCC, and can be viewed through
  `Show VNF LCM OP OCC`_.

  During error-handling (retry or rollback), use the data in the
  ``user_script_err_handling_data`` variable to perform corresponding
  processing.


Modifications of VNF Package
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Users need to make the following modifications when creating
a :doc:`/user/vnf-package`.

The rollback operation currently supports multiple
`Rollback VNF LCM Operation`_.
The following takes the rollback operations of instantiate and scale-out
as examples to demonstrate how to modify VNFD.

.. note::

    The following provides the sample files ``v2_sample2_df_simple.yaml`` and
    ``v2_sample2_types.yaml`` that need to be modified, which are stored in
    the Definitions directory of the VNF Package.

    * ``v2_sample2_df_simple.yaml`` corresponds to
      ``4. Topology Template File with Deployment Flavour``
      in :doc:`/user/vnfd-sol001`.

    * ``v2_sample2_types.yaml`` corresponds to
      ``2. User Defined Types Definition File``
      in :doc:`/user/vnfd-sol001`.

* In ``v2_sample2_df_simple.yaml``, ``xxx_rollback_start`` and
  ``xxx_rollback_end`` need to be added under
  ``topology_template.node_templates.VNF.interfaces.Vnflcm``.

  The following is the content of ``v2_sample2_df_simple.yaml``, the unmodified
  part is replaced by "``...``" :

  .. code-block:: yaml

    topology_template:
      ...
      node_templates:
        VNF:
          type: company.provider.VNF
          properties:
            flavour_description: A simple flavour
          interfaces:
            Vnflcm:
              instantiate_start:
                implementation: mgmt-driver-script
              instantiate_end:
                implementation: mgmt-driver-script
              heal_start:
                implementation: mgmt-driver-script
              heal_end:
                implementation: mgmt-driver-script
              scale_start:
                implementation: mgmt-driver-script
              scale_end:
                implementation: mgmt-driver-script
              terminate_start:
                implementation: mgmt-driver-script
              terminate_end:
                implementation: mgmt-driver-script
              change_external_connectivity_start:
                implementation: mgmt-driver-script
              change_external_connectivity_end:
                implementation: mgmt-driver-script
              modify_information_start:
                implementation: mgmt-driver-script
              modify_information_end:
                implementation: mgmt-driver-script
              instantiate_rollback_start:
                implementation: mgmt-driver-script
              instantiate_rollback_end:
                implementation: mgmt-driver-script
              scale_rollback_start:
                implementation: mgmt-driver-script
              scale_rollback_end:
                implementation: mgmt-driver-script
          artifacts:
            mgmt-driver-script:
              description: Sample MgmtDriver Script
              type: tosca.artifacts.Implementation.Python
              file: ../Scripts/mgmt_driver_script.py

  .. note::

    If some definitions of ``xxx_start`` and ``xxx_end`` are added in VNFD,
    corresponding ``xxx_start`` and ``xxx_end`` functions must also be
    added in MgmtDriver.


* In ``v2_sample2_types.yaml``, the definition of ``interface_types`` needs to
  be added, and the definition of ``type`` needs to be modified under
  ``node_types.company.provider.VNF.interfaces.Vnflcm``.

  The following is the content of ``v2_sample2_types.yaml``, the unmodified
  part is replaced by "``...``" :

  .. code-block:: yaml

    interface_types:
      sample.test.Vnflcm:
        derived_from: tosca.interfaces.nfv.Vnflcm
        instantiate_start:
          description: Invoked before instantiate
        instantiate_end:
          description: Invoked after instantiate
        heal_start:
          description: Invoked before heal
        heal_end:
          description: Invoked after heal
        scale_start:
          description: Invoked before scale
        scale_end:
          description: Invoked after scale
        terminate_start:
          description: Invoked before terminate
        terminate_end:
          description: Invoked after terminate
        change_external_connectivity_start:
          description: Invoked before change_external_connectivity
        change_external_connectivity_end:
          description: Invoked after change_external_connectivity
        modify_information_start:
          description: Invoked before modify_information
        modify_information_end:
          description: Invoked after modify_information
        instantiate_rollback_start:
          description: Invoked before instantiate_rollback
        instantiate_rollback_end:
          description: Invoked after instantiate_rollback
        scale_rollback_start:
          description: Invoked before scale_rollback
        scale_rollback_end:
          description: Invoked after scale_rollback

    node_types:
      company.provider.VNF:
        ...
        interfaces:
          Vnflcm:
            type: sample.test.Vnflcm


After the above modification, MgmtDriver can also be called in error-handling.

.. note::

    In the process of error-handling, the specific action of MgmtDriver
    needs to be customized by the user or provider.


History of Checks
-----------------

The content of this document has been confirmed to work
using the following VNF Package.

* `error_network for 2023.2 Bobcat`_
* `server_notification for 2023.2 Bobcat`_


.. _VNF LCM v2 API:
  https://docs.openstack.org/api-ref/nfv-orchestration/v2/vnflcm.html
.. _NFV-SOL001 v2.6.1:
  https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/001/02.06.01_60/gs_nfv-sol001v020601p.pdf
.. _Show VNF LCM OP OCC:
  https://docs.openstack.org/api-ref/nfv-orchestration/v2/vnflcm.html#show-vnf-lcm-operation-occurrence-v2
.. _error_network for 2023.2 Bobcat:
  https://opendev.org/openstack/tacker/src/branch/stable/2023.2/tacker/tests/functional/sol_v2_common/samples/error_network
.. _server_notification for 2023.2 Bobcat:
  https://opendev.org/openstack/tacker/src/branch/stable/2023.2/tacker/tests/functional/sol_v2_common/samples/server_notification
