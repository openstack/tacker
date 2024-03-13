========================
ETSI NFV-SOL VNF Scaling
========================

This document describes how to scale VNF in Tacker v1 API.

.. note::

  This is a document for Tacker v1 API.
  See :doc:`/user/v2/vnf/scale/index` for Tacker v2 API.


Overview
--------

The diagram below shows an overview of the VNF scaling.

1. Request scale VNF

   A user requests tacker-server to scale a VNF or all VNFs with tacker-client
   by requesting ``scale VNF``.

2. Call OpenStack Heat API

   Upon receiving a request from tacker-client, tacker-server redirects it to
   tacker-conductor. In tacker-conductor, the request is redirected again to
   an appropriate infra-driver (in this case OpenStack infra-driver) according
   to the contents of the instantiate parameters. Then, OpenStack infra-driver
   calls OpenStack Heat APIs.

3. Change the number of VMs

   OpenStack Heat change the number of VMs according to the API calls.

.. figure:: /_images/etsi_vnf_scaling.png


.. note::

  Scale API version 1 supports is_reverse option.
  Scale-in operation with this option deletes VNF from the last
  registered VM.


Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

A default VIM should be registered according to
:doc:`/cli/cli-legacy-vim`.

The VNF Package(sample_vnf_package_csar.zip) used below is prepared
by referring to :doc:`/user/vnf-package`.

The procedure of prepare for scaling operation that from "register VIM" to
"Instantiate VNF", basically refer to
:doc:`/user/etsi_vnf_deployment_as_vm_with_user_data`.

This procedure uses an example using the sample VNF package.


VNF Scaling Procedure
---------------------

As mentioned in Prerequisites, the VNF must be instantiated
before performing scaling.

Details of CLI commands are described in
:doc:`/cli/cli-etsi-vnflcm`.

There are two main methods for VNF scaling.

* Scale out VNF
* Scale in VNF


How to Identify ASPECT_ID
~~~~~~~~~~~~~~~~~~~~~~~~~

In order to execute scaling, it is necessary to specify
ASPECT_ID, which is the ID for the target scaling group.
First, the method of specifying the ID will be described.

ASPECT_ID is described in VNFD included in the VNF Package.
In the following VNFD excerpt, **VDU1_scale**
corresponds to ASPECT_ID.

.. code-block:: yaml

  node_templates:
    VDU1:
      type: tosca.nodes.nfv.Vdu.Compute
      properties:
        name: VDU1
        description: VDU1 compute node
        vdu_profile:
          min_number_of_instances: 1
          max_number_of_instances: 3

  ...snip VNFD...

  policies:
    - scaling_aspects:
        type: tosca.policies.nfv.ScalingAspects
        properties:
          aspects:
            VDU1_scale:
              name: VDU1_scale
              description: VDU1 scaling aspect
              max_scale_level: 2
              step_deltas:
                - delta_1

    - VDU1_initial_delta:
        type: tosca.policies.nfv.VduInitialDelta
        properties:
          initial_delta:
            number_of_instances: 1
        targets: [ VDU1 ]

    - VDU1_scaling_aspect_deltas:
        type: tosca.policies.nfv.VduScalingAspectDeltas
        properties:
          aspect: VDU1_scale
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
                VDU1_scale:
                  scale_level: 0
            instantiation_level_2:
              description: Largest size
              scale_info:
                VDU1_scale:
                  scale_level: 2
          default_level: instantiation_level_1

    - VDU1_instantiation_levels:
        type: tosca.policies.nfv.VduInstantiationLevels
        properties:
          levels:
            instantiation_level_1:
              number_of_instances: 1
            instantiation_level_2:
              number_of_instances: 3
        targets: [ VDU1 ]

  ...snip VNFD...


.. note::

  See `NFV-SOL001 v2.6.1`_ annex A.6 for details about ASPECT_ID.


How to Scale Out VNF
~~~~~~~~~~~~~~~~~~~~

Execute Scale CLI command and check the number of stacks
before and after scaling.
This is to confirm that the number of stacks has increased
after Scale-out.
See `Heat CLI reference`_. for details on Heat CLI commands.


Stack information before scale-out:

.. code-block:: console

  $ openstack stack list --nested -c 'ID' -c 'Stack Name' -c 'Stack Status' -c 'Parent'


Result:

.. code-block:: console

  +--------------------------------------+-----------------------------------------------------------------------------------------------+-----------------+--------------------------------------+
  | ID                                   | Stack Name                                                                                    | Stack Status    | Parent                               |
  +--------------------------------------+-----------------------------------------------------------------------------------------------+-----------------+--------------------------------------+
  | 3315a9f5-9c55-45ec-8b52-91875856c6e6 | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a-VDU1_scale-3x6qwnzbj6ep                           | CREATE_COMPLETE | e9d4576f-950c-4076-a54d-35b5cf43ebdd |
  | 1b0bd450-3154-4301-b004-46a8b21152c1 | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a-VDU1_scale-3x6qwnzbj6ep-gfrxqjt6nfqb-2ufs4pbsedui | CREATE_COMPLETE | 3315a9f5-9c55-45ec-8b52-91875856c6e6 |
  | e9d4576f-950c-4076-a54d-35b5cf43ebdd | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a                                                   | CREATE_COMPLETE | None                                 |
  +--------------------------------------+-----------------------------------------------------------------------------------------------+-----------------+--------------------------------------+


Scale-out VNF can be executed by the following CLI command.

.. code-block:: console

  $ openstack vnflcm scale --type SCALE_OUT --aspect-id VDU1_scale VNF_INSTANCE_ID


Result:

.. code-block:: console

  Scale request for VNF Instance 0c3644ff-b207-4a6a-9d3a-d1295cda153a has been accepted.


Stack information after scale-out:

.. code-block:: console

  $ openstack stack list --nested -c 'ID' -c 'Stack Name' -c 'Stack Status' -c 'Parent'


Result:

.. code-block:: console

  +--------------------------------------+-----------------------------------------------------------------------------------------------+-----------------+--------------------------------------+
  | ID                                   | Stack Name                                                                                    | Stack Status    | Parent                               |
  +--------------------------------------+-----------------------------------------------------------------------------------------------+-----------------+--------------------------------------+
  | 909dc6a6-f60a-4410-84a1-9cfbfb788be1 | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a-VDU1_scale-3x6qwnzbj6ep-cvfcy4h2rmuh-6zmqn6ason36 | CREATE_COMPLETE | 3315a9f5-9c55-45ec-8b52-91875856c6e6 |
  | 3315a9f5-9c55-45ec-8b52-91875856c6e6 | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a-VDU1_scale-3x6qwnzbj6ep                           | UPDATE_COMPLETE | e9d4576f-950c-4076-a54d-35b5cf43ebdd |
  | 1b0bd450-3154-4301-b004-46a8b21152c1 | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a-VDU1_scale-3x6qwnzbj6ep-gfrxqjt6nfqb-2ufs4pbsedui | UPDATE_COMPLETE | 3315a9f5-9c55-45ec-8b52-91875856c6e6 |
  | e9d4576f-950c-4076-a54d-35b5cf43ebdd | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a                                                   | CREATE_COMPLETE | None                                 |
  +--------------------------------------+-----------------------------------------------------------------------------------------------+-----------------+--------------------------------------+


Stack details:

.. code-block:: console

  $ openstack stack resource list 3315a9f5-9c55-45ec-8b52-91875856c6e6
  +---------------+--------------------------------------+---------------+-----------------+----------------------+
  | resource_name | physical_resource_id                 | resource_type | resource_status | updated_time         |
  +---------------+--------------------------------------+---------------+-----------------+----------------------+
  | gfrxqjt6nfqb  | 1b0bd450-3154-4301-b004-46a8b21152c1 | VDU1.yaml     | UPDATE_COMPLETE | 2023-12-28T02:36:50Z |
  | cvfcy4h2rmuh  | 909dc6a6-f60a-4410-84a1-9cfbfb788be1 | VDU1.yaml     | CREATE_COMPLETE | 2023-12-28T02:36:50Z |
  +---------------+--------------------------------------+---------------+-----------------+----------------------+

  $ openstack stack resource list 1b0bd450-3154-4301-b004-46a8b21152c1
  +---------------+--------------------------------------+-------------------+-----------------+----------------------+
  | resource_name | physical_resource_id                 | resource_type     | resource_status | updated_time         |
  +---------------+--------------------------------------+-------------------+-----------------+----------------------+
  | VDU1          | f32848eb-598f-4158-8896-5ea9479456de | OS::Nova::Server  | CREATE_COMPLETE | 2023-12-28T02:32:04Z |
  | VDU1_CP4      | e21dc5cc-eb46-4cf9-a352-7aa3cf659af7 | OS::Neutron::Port | CREATE_COMPLETE | 2023-12-28T02:32:04Z |
  | VDU1_CP2      | 0988d9dc-97ba-43be-944d-185e316785f9 | OS::Neutron::Port | CREATE_COMPLETE | 2023-12-28T02:32:04Z |
  | VDU1_CP3      | d125eec4-4e85-43cb-9887-cd5373b0abae | OS::Neutron::Port | CREATE_COMPLETE | 2023-12-28T02:32:04Z |
  | VDU1_CP5      | 16e66a58-c75c-4afe-be4f-e7eaafdfa506 | OS::Neutron::Port | CREATE_COMPLETE | 2023-12-28T02:32:04Z |
  | VDU1_CP1      | d581db6b-eac8-49cf-99e0-3c494450b33b | OS::Neutron::Port | CREATE_COMPLETE | 2023-12-28T02:32:04Z |
  +---------------+--------------------------------------+-------------------+-----------------+----------------------+

  $ openstack stack resource list 909dc6a6-f60a-4410-84a1-9cfbfb788be1
  +---------------+--------------------------------------+-------------------+-----------------+----------------------+
  | resource_name | physical_resource_id                 | resource_type     | resource_status | updated_time         |
  +---------------+--------------------------------------+-------------------+-----------------+----------------------+
  | VDU1          | e92cb6ca-72bb-46c8-91f1-531eb1d01315 | OS::Nova::Server  | CREATE_COMPLETE | 2023-12-28T02:36:52Z |
  | VDU1_CP4      | 838a673d-d684-4eaa-92ff-78f1d145b4e1 | OS::Neutron::Port | CREATE_COMPLETE | 2023-12-28T02:36:52Z |
  | VDU1_CP2      | e10f8b96-7e90-4232-b8aa-ec72b9a39d55 | OS::Neutron::Port | CREATE_COMPLETE | 2023-12-28T02:36:52Z |
  | VDU1_CP3      | 40960abd-5a3d-439f-8f2d-4ad70b5eb1ea | OS::Neutron::Port | CREATE_COMPLETE | 2023-12-28T02:36:52Z |
  | VDU1_CP5      | b71a8b32-5ce4-48fb-9cf5-8bb6328b3679 | OS::Neutron::Port | CREATE_COMPLETE | 2023-12-28T02:36:52Z |
  | VDU1_CP1      | 35344427-eff6-47e3-820b-11782996e805 | OS::Neutron::Port | CREATE_COMPLETE | 2023-12-28T02:36:52Z |
  +---------------+--------------------------------------+-------------------+-----------------+----------------------+


It can be seen that the child-stack (ID: 909dc6a6-f60a-4410-84a1-9cfbfb788be1)
with the parent-stack (ID: 3315a9f5-9c55-45ec-8b52-91875856c6e6)
is increased by the scaling out operation.


How to Scale in VNF
~~~~~~~~~~~~~~~~~~~

Execute Scale CLI command and check the number of stacks
before and after scaling.
This is to confirm that the number of stacks has decreased
after Scale-in.
See `Heat CLI reference`_. for details on Heat CLI commands.


Stack information before scale-in:

.. code-block:: console

  $ openstack stack list --nested -c 'ID' -c 'Stack Name' -c 'Stack Status' -c 'Parent'


Result:

.. code-block:: console

  +--------------------------------------+-----------------------------------------------------------------------------------------------+-----------------+--------------------------------------+
  | ID                                   | Stack Name                                                                                    | Stack Status    | Parent                               |
  +--------------------------------------+-----------------------------------------------------------------------------------------------+-----------------+--------------------------------------+
  | 909dc6a6-f60a-4410-84a1-9cfbfb788be1 | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a-VDU1_scale-3x6qwnzbj6ep-cvfcy4h2rmuh-6zmqn6ason36 | CREATE_COMPLETE | 3315a9f5-9c55-45ec-8b52-91875856c6e6 |
  | 3315a9f5-9c55-45ec-8b52-91875856c6e6 | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a-VDU1_scale-3x6qwnzbj6ep                           | UPDATE_COMPLETE | e9d4576f-950c-4076-a54d-35b5cf43ebdd |
  | 1b0bd450-3154-4301-b004-46a8b21152c1 | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a-VDU1_scale-3x6qwnzbj6ep-gfrxqjt6nfqb-2ufs4pbsedui | UPDATE_COMPLETE | 3315a9f5-9c55-45ec-8b52-91875856c6e6 |
  | e9d4576f-950c-4076-a54d-35b5cf43ebdd | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a                                                   | CREATE_COMPLETE | None                                 |
  +--------------------------------------+-----------------------------------------------------------------------------------------------+-----------------+--------------------------------------+


Scale-in VNF can be executed by the following CLI command.

.. code-block:: console

  $ openstack vnflcm scale --type SCALE_IN --aspect-id VDU1_scale VNF_INSTANCE_ID


Result:

.. code-block:: console

  Scale request for VNF Instance 0c3644ff-b207-4a6a-9d3a-d1295cda153a has been accepted.


Stack information after scale-in:

.. code-block:: console

  $ openstack stack list --nested -c 'ID' -c 'Stack Name' -c 'Stack Status' -c 'Parent'


Result:

.. code-block:: console

  +--------------------------------------+-----------------------------------------------------------------------------------------------+-----------------+--------------------------------------+
  | ID                                   | Stack Name                                                                                    | Stack Status    | Parent                               |
  +--------------------------------------+-----------------------------------------------------------------------------------------------+-----------------+--------------------------------------+
  | 909dc6a6-f60a-4410-84a1-9cfbfb788be1 | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a-VDU1_scale-3x6qwnzbj6ep-cvfcy4h2rmuh-6zmqn6ason36 | UPDATE_COMPLETE | 3315a9f5-9c55-45ec-8b52-91875856c6e6 |
  | 3315a9f5-9c55-45ec-8b52-91875856c6e6 | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a-VDU1_scale-3x6qwnzbj6ep                           | UPDATE_COMPLETE | e9d4576f-950c-4076-a54d-35b5cf43ebdd |
  | e9d4576f-950c-4076-a54d-35b5cf43ebdd | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a                                                   | CREATE_COMPLETE | None                                 |
  +--------------------------------------+-----------------------------------------------------------------------------------------------+-----------------+--------------------------------------+


There were two child-stacks(ID: 1b0bd450-3154-4301-b004-46a8b21152c1
and ID: 909dc6a6-f60a-4410-84a1-9cfbfb788be1) with
a parent-stack(ID: 3315a9f5-9c55-45ec-8b52-91875856c6e6),
it can be seen that one of them is decreased by the scale-in operation.


.. _NFV-SOL001 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/001/02.06.01_60/gs_NFV-SOL001v020601p.pdf
.. _Heat CLI reference : https://docs.openstack.org/python-openstackclient/latest/cli/plugin-commands/heat.html
