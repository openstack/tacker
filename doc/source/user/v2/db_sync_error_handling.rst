=======================================
Database synchronization error-handling
=======================================

This document describes how to error-handling database synchronization errors.

Database Synchronization Description
------------------------------------

If there are differences in the Pod information (Number of Pods, Pod name)
between TackerDB and Kubernetes, Tacker will synchronize the TackerDB
information with the Kubernetes information for all VNF instance,
and synchronize according to the scale policy defined in the VNFD.

.. note:: The interval of database synchronization tasks between
          TackerDB and Kubernetes is 300 seconds.
          You can change it in /etc/tacker/tacker.conf

.. code-block:: console

    $ vim /etc/tacker/tacker.conf
    db_synchronization_interval = 300

Database Synchronization Error
------------------------------

There are some errors in database synchronization
and some error-handling operations.

* The maximum or minimum number of pods is out of range
* Error compute scale_level
* LCM operation
    * Conflict with LCM operation
    * Abnormal LCM operation status

The maximum or minimum number of pods is out of range
-----------------------------------------------------

During synchronization, Tacker will check the range of the maximum or
minimum number of pods. If it finds out of range, Tacker will output
an error log and not update the database.

When tacker-conductor.log contains the following error log,
it means the maximum or minimum number of pods is out of range.

.. note:: If you don't have tacker-conductor.log,
          you can execute the following CLI command to find log.

.. code-block:: console

  journalctl -u devstack@tacker-conductor


Error log:

.. code-block:: console

  Failed to update database vnf 81c4be9d-25ad-4726-8640-f2c4c326de2e vdu: VDU1. Pod num is out of range. pod_num: 5

Error-handling operations:

To solve this error, you can get with the following ways.

* To check with the range of the maximum or minimum number of pods in VNFD.
* To change the definition of number of pods in Kubernetes.

Check with the range of the maximum or minimum number of pods in VNFD
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note:: VNFD files included in VNF Package defines the range of the maximum or minimum number of pods in ``vdu_profile``.
          The following description uses ``helloworld3_df_simple.yaml`` as an example.

.. code-block:: console

    $ cat helloworld3_df_simple.yaml
    tosca_definitions_version: tosca_simple_yaml_1_2

    description: Simple deployment flavour for Sample VNF

    imports:
      - etsi_nfv_sol001_common_types.yaml
      - etsi_nfv_sol001_vnfd_types.yaml
      - helloworld3_types.yaml

    ...

      node_templates:
        VNF:
          type: company.provider.VNF
          properties:
            flavour_description: A simple flavour

        VDU1:
          type: tosca.nodes.nfv.Vdu.Compute
          properties:
            name: curry-probe-test001
            description: kubernetes controller resource as VDU
            vdu_profile:
              min_number_of_instances: 1
              max_number_of_instances: 3

    ...

.. note:: ``vdu_profile.min_number_of_instances`` defines the minimum number of pods.
          ``vdu_profile.max_number_of_instances`` defines the maximum number of pods.

You can follow these steps to find VNFD files:

a.Find VNF instance ID in tacker-conductor.log
''''''''''''''''''''''''''''''''''''''''''''''

Execute the following CLI command to find tacker-conductor.log.

.. code-block:: console

    $ cat /opt/stack/logs/tacker-conductor.log | grep "Failed to update database vnf"

.. note:: If you don't have tacker-conductor.log,
          you can execute the following CLI commands to view the log.

.. code-block:: console

    journalctl -u devstack@tacker-conductor

Result:

.. code-block:: console

    Failed to update database vnf 81c4be9d-25ad-4726-8640-f2c4c326de2e Pod num is out of range. pod_num: 5

.. note:: VNF instance ID in this case is 81c4be9d-25ad-4726-8640-f2c4c326de2e.

b. Find VNFD ID using VNF instance ID
'''''''''''''''''''''''''''''''''''''

Execute the following CLI command to find VNFD ID.

.. code-block:: console

    $ openstack vnf package list --filter '(eq,vnfdId,68014f5a-1f6b-47b2-914b-11bf0d1bd820)' -c 'Id'

Result:

.. code-block:: console

    +---------+--------------------------------------+
    | Field   | Value                                |
    +---------+--------------------------------------+
    | VNFD ID | 68014f5a-1f6b-47b2-914b-11bf0d1bd820 |
    +---------+--------------------------------------+

c. Find VNF package ID using VNFD ID
''''''''''''''''''''''''''''''''''''

Execute the following CLI command to find VNF package ID.

.. code-block:: console

    $ openstack vnf package list --filter '(eq,vnfdId,68014f5a-1f6b-47b2-914b-11bf0d1bd820)' -c 'Id'

Result:

.. code-block:: console

    +--------------------------------------+
    | Id                                   |
    +--------------------------------------+
    | eceb8b32-efb5-4940-a065-cef47fcdd973 |
    +--------------------------------------+

d.Find VNFD files with VNF package ID
'''''''''''''''''''''''''''''''''''''

Execute the following CLI command to find VNF package ID.

.. code-block:: console

    $ openstack vnf package download eceb8b32-efb5-4940-a065-cef47fcdd973 --vnfd --file sample_vnfd.zip
    $ unzip sample_vnfd.zip
    $ vim sample_vnfd/Definitions/helloworld3_df_simple.yaml

.. _Change the definition of number of pods in Kubernetes :

Change the definition of number of pods in Kubernetes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. note:: You can see
          `Check with the range of the maximum or minimum number of pods in VNFD`_
          to find Kubernetes deployment name with helloworld3_df_simple.yaml
          in ``VDU1.properties.name``.

You need to log in to the master node of the Kubernetes first,
and execute the following CLI command to
change the definition of number of pods in Kubernetes.

.. code-block:: console

    $ kubectl edit deploy curry-probe-test001 -n kube-system
    apiVersion: apps/v1
    kind: Deployment
    ...
    spec:
      progressDeadlineSeconds: 600
      replicas: 2
      revisionHistoryLimit: 10
      selector:
        matchLabels:
          app.kubernetes.io/name: curry-probe-test001
    ...

.. note:: Change the number of pods in ``spec.replicas``.

Error compute scale_level
-------------------------

During synchronization (add or delete vnfc resource),
Tacker will compute scale_level.
When the pod numbers in Kubernetes are different from the initial number plus
the scale number in the VNFD.
Tacker will output an error log and do not update database.

When tacker-conductor.log contains the following error log,
it means compute scale_level error.

.. note:: If you don't have tacker-conductor.log,
          you can execute the following CLI command to show tacker-conductor.log.

.. code-block:: console

    journalctl -u devstack@tacker-conductor

Error log:

.. code-block:: console

  Error computing 'scale_level'. current Pod num: 4 delta: 2. vnf: 81c4be9d-25ad-4726-8640-f2c4c326de2e vdu: VDU1

Error-handling operations:

To solve this error, you can get with the following ways.

* To check with the scale_level in VNFD.
* To change the definition of number of pods in Kubernetes

Check with scale_level in VNFD (take vdu1 as an example)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note:: ``helloworld3_df_simple.yaml`` defines the scale_level of vdu1 in
          ``vdu1_scaling_aspect_deltas.properties.deltas.delta_1.number_of_instances``,
          and initial delta in ``vdu1_initial_delta.properties.initial_delta.number_of_instances``.

.. code-block:: console

    $ cat helloworld3_df_simple.yaml
    tosca_definitions_version: tosca_simple_yaml_1_2

    description: Simple deployment flavour for Sample VNF

    imports:
      - etsi_nfv_sol001_common_types.yaml
      - etsi_nfv_sol001_vnfd_types.yaml
      - helloworld3_types.yaml

    ...

      policies:
        - scaling_aspects:
            type: tosca.policies.nfv.ScalingAspects
            properties:
              aspects:
                vdu1_aspect:
                  name: vdu1_aspect
                  description: vdu1 scaling aspect
                  max_scale_level: 2
                  step_deltas:
                    - delta_1

        - vdu1_initial_delta:
            type: tosca.policies.nfv.VduInitialDelta
            properties:
              initial_delta:
                number_of_instances: 1
            targets: [ VDU1 ]

        - vdu1_scaling_aspect_deltas:
            type: tosca.policies.nfv.VduScalingAspectDeltas
            properties:
              aspect: vdu1_aspect
              deltas:
                delta_1:
                  number_of_instances: 1
            targets: [ VDU1 ]

        - instantiation_levels:
            type: tosca.policies.nfv.InstantiationLevels
            properties:
              levels:
                instantiation_level_1:
                  description: Smallest size
                  scale_info:
                    vdu1_aspect:
                      scale_level: 0
                instantiation_level_2:
                  description: Largest size
                  scale_info:
                    vdu1_aspect:
                      scale_level: 2
              default_level: instantiation_level_1

        - vdu1_instantiation_levels:
            type: tosca.policies.nfv.VduInstantiationLevels
            properties:
              levels:
                instantiation_level_1:
                  number_of_instances: 1
                instantiation_level_2:
                  number_of_instances: 3
            targets: [ VDU1 ]

.. note:: You can follow these steps to find VNFD files in
          `Check with the range of the maximum or minimum number of pods in VNFD`_
          from `a.Find VNF instance ID in tacker-conductor.log`_
          to `d.Find VNFD files with VNF package ID`_

Change the definition of number of pods in Kubernetes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The pod numbers should satisfy that the pod numbers in Kubernetes minus
the initial increment is a multiple of the scale level.

.. note:: You can See
          `Check with scale_level in VNFD (take vdu1 as an example)`_
          to find initial delta and scale level, and refer to
          `Change the definition of number of pods in Kubernetes`_
          for details.


LCM operation
-------------

Conflict with LCM operation
^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are two kinds of conflicts:

* Database synchronization occurs while LCM operation is in progress.
* LCM operation occurs during DB synchronization.

Database synchronization occurs while a LCM operation is in progress
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

When tacker-conductor.log contains the following info log,
it means database synchronization conflict with LCM operation,
and database synchronization will skip.

.. note:: If you don't have tacker-conductor.log,
          you can execute the following CLI command to show tacker-conductor.log.

.. code-block:: console

    journalctl -u devstack@tacker-conductor

Info log:

.. code-block:: console

    There is an LCM operation in progress, so skip this DB synchronization. vnf:81c4be9d-25ad-4726-8640-f2c4c326de2e

Conflict resolution operations:
Waiting for LCM operation completes
and database synchronization will be repeated at a default time.

LCM operation occurs during DB synchronization
''''''''''''''''''''''''''''''''''''''''''''''

When LCM operation responds 409, it conflicts with Database synchronization.

Conflict resolution operations:

Execute LCM operation again after database synchronization completes.

.. note:: When completed, you can get the following information from log.

Debug log:

.. code-block:: console

    Ended sync_db


Abnormal LCM operation status
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

During synchronization, Tacker checks the operationState of VnfLcmOpOcc.
For the same vnf instance, if ``FAILED_TEMP`` exists in the operationState,
or the latest operationState is ``FAILED``,
Tacker will output an error log and do not update database.

.. note:: If you don't have tacker-conductor.log,
          you can execute the following CLI command to show tacker-conductor.log.

.. code-block:: console

    journalctl -u devstack@tacker-conductor

Error log:

.. code-block:: console

    The LCM operation status of the vnf: 81c4be9d-25ad-4726-8640-f2c4c326de2e is abnormal, so skip this DB synchronization.

Error-handling operations:

To solve this error, you can get with the following ways.

* For the operation state of ``FAILED_TEMP``, please refer to
  :doc:`/user/v2/error_handling`.

* For the operation state of ``FAILED``, please perform other LCM operations
  on this vnf instance until the result is ``COMPLETED``.
