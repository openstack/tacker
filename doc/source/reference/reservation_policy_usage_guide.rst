..
      Copyright 2018 NTT DATA

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

===================================
VNF scaling with reserved resources
===================================

Tacker allows you to configure reserved compute resources in reservation
policy. The compute resources should be first reserved in the OpenStack
``Blazar`` service by creating leases which can then be configured in the
VNFD template.

TOSCA schema for reservation policy
-----------------------------------

Tacker defines TOSCA schema for the reservation policy as given below:

.. code-block:: yaml

  tosca.policies.tacker.Reservation:
      derived_from: tosca.policies.Reservation
      reservation:
        start_actions:
          type: map
          entry_schema:
            type: string
            required: true
        before_end_actions:
          type: map
          entry_schema:
            type: string
            required: true
        end_actions:
          type: map
          entry_schema:
            type: string
            required: true
        properties:
          lease_id:
            type: string
            required: true

Following TOSCA snippet shows VNFD template using reservation policy.
In this policy, you can see there are three different types of actions.

#. start_actions

#. before_end_actions

#. end_actions

In these actions, you can configure multiple actions but scaling policy is
mandatory in start_actions and one of before_end_actions or end_actions.
The scaling policy configured in the start_actions will be scaling-out policy
so configure max_instances as per the compute resources reserved in the Blazar
service and the scaling policy configured in either of before_end_actions or
end_actions will be scaling-in policy so configure min_instances to 0.
Also, `default_instances` should be set to 0 because we don't want VDUs until
tacker receives the lease start trigger from Blazar through Aodh service.
The parameter `increment` should also be set equal to `max_instances` as
tacker will receive lease start trigger only once during the lifecycle
of a lease.

.. code-block:: yaml

  policies:

    - RSV:
        type: tosca.policies.tacker.Reservation
        reservation:
          start_actions: [SP_RSV, log]
          before_end_actions: [SP_RSV]
          end_actions: [noop]
          properties:
            lease_id: { get_input: lease_id }
    - SP_RSV:
        type: tosca.policies.tacker.Scaling
        properties:
          increment: 2
          cooldown: 120
          min_instances: 0
          max_instances: 2
          default_instances: 0
        targets: [VDU1]


Installation and configurations
-------------------------------

1. You need Blazar, ceilometer and Aodh OpenStack services.

2. Modify the below configuration files:

/etc/blazar/blazar.conf:

.. code-block:: yaml

    [oslo_messaging_notifications]
    driver = messaging, log

/etc/ceilometer/event_pipeline.yaml:

.. code-block:: yaml

    sinks:
      - name: event_sink
        transformers:
        publishers:
            - gnocchi://?archive_policy=low&filter_project=gnocchi_swift
            - notifier://
            - notifier://?topic=alarm.all

/etc/ceilometer/event_definitions.yaml:

.. code-block:: yaml

    - event_type: lease.event.start_lease
      traits: &lease_traits
       lease_id:
         fields: payload.lease_id
       project_id:
         fields: payload.project_id
       user_id:
         fields: payload.user_id
       start_date:
         fields: payload.start_date
       end_date:
         fields: payload.end_date
    - event_type: lease.event.before_end_lease
      traits: *lease_traits
    - event_type: lease.event.end_lease
      traits: *lease_traits


Deploying reservation tosca template with tacker
------------------------------------------------

When reservation resource type is virtual:instance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Create a lease in blazar for instance reservation:

.. sourcecode:: console

   $ blazar lease-create --reservation resource_type=virtual:instance,vcpus=1,memory_mb=1024,disk_gb=20,amount=0,affinity=False
   --start-date "2019-04-24 20:00" --end-date "2019-07-09 21:00" lease-1

    +--------------+-----------------------------------------------------------------+
    | Field        | Value                                                           |
    +--------------+-----------------------------------------------------------------+
    | created_at   | 2018-12-10 07:44:46                                             |
    | degraded     | False                                                           |
    | end_date     | 2019-07-09T21:00:00.000000                                      |
    | events       | {                                                               |
    |              |     "status": "UNDONE",                                         |
    |              |     "lease_id": "aca14613-2bed-480e-aefe-97fa02813fcf",         |
    |              |     "event_type": "start_lease",                                |
    |              |     "created_at": "2018-12-10 07:44:49",                        |
    |              |     "updated_at": null,                                         |
    |              |     "time": "2019-04-24T20:00:00.000000",                       |
    |              |     "id": "038c882a-1c9e-4785-aab0-07a6898653cf"                |
    |              | }                                                               |
    |              | {                                                               |
    |              |     "status": "UNDONE",                                         |
    |              |     "lease_id": "aca14613-2bed-480e-aefe-97fa02813fcf",         |
    |              |     "event_type": "before_end_lease",                           |
    |              |     "created_at": "2018-12-10 07:44:49",                        |
    |              |     "updated_at": null,                                         |
    |              |     "time": "2019-07-09T20:00:00.000000",                       |
    |              |     "id": "607fb807-55e1-44ff-927e-64a4ec71b0f1"                |
    |              | }                                                               |
    |              | {                                                               |
    |              |     "status": "UNDONE",                                         |
    |              |     "lease_id": "aca14613-2bed-480e-aefe-97fa02813fcf",         |
    |              |     "event_type": "end_lease",                                  |
    |              |     "created_at": "2018-12-10 07:44:49",                        |
    |              |     "updated_at": null,                                         |
    |              |     "time": "2019-07-09T21:00:00.000000",                       |
    |              |     "id": "fd6b1f91-bfc8-49d8-94a7-5136ee2fdaee"                |
    |              | }                                                               |
    | id           | aca14613-2bed-480e-aefe-97fa02813fcf                            |
    | name         | lease-1                                                         |
    | project_id   | 683322bea7154651b18792b59df67d4e                                |
    | reservations | {                                                               |
    |              |     "status": "pending",                                        |
    |              |     "memory_mb": 1024,                                          |
    |              |     "lease_id": "aca14613-2bed-480e-aefe-97fa02813fcf",         |
    |              |     "resource_properties": "",                                  |
    |              |     "disk_gb": 10,                                              |
    |              |     "resource_id": "bb335cc1-770d-4251-90d8-8f9ea95dac56",      |
    |              |     "created_at": "2018-12-10 07:44:46",                        |
    |              |     "updated_at": "2018-12-10 07:44:49",                        |
    |              |     "missing_resources": false,                                 |
    |              |     "server_group_id": "589b014e-2a68-48b1-87ee-4e9054560206",  |
    |              |     "amount": 1,                                                |
    |              |     "affinity": false,                                          |
    |              |     "flavor_id": "edcc0e22-1f7f-4d57-abe4-aeb0775cbd36",        |
    |              |     "id": "edcc0e22-1f7f-4d57-abe4-aeb0775cbd36",               |
    |              |     "aggregate_id": 6,                                          |
    |              |     "vcpus": 1,                                                 |
    |              |     "resource_type": "virtual:instance",                        |
    |              |     "resources_changed": false                                  |
    |              | }                                                               |
    | start_date   | 2019-04-24T20:00:00.000000                                      |
    | status       | PENDING                                                         |
    | trust_id     | 080f059dabbb4cb0a6398743abcc3224                                |
    | updated_at   | 2018-12-10 07:44:49                                             |
    | user_id      | c42317bee82940509427c63410fd058a                                |
    +--------------+-----------------------------------------------------------------+

..

2. Replace the flavor, lease_id and server_group_id value in the parameter file
given for reservation with the lease response flavor, lease_id and
server_group_id value.
Ref:
``samples/tosca-templates/vnfd/tosca-vnfd-instance-reservation-param-values.yaml``

.. note::
    The `server_group_id` parameter should be specified in VDU section only
    when reservation resource type is `virtual:instance`. Operator shouldn't
    configure both placement policy under policies and server_group_id in VDU
    in VNFD template otherwise the server_group_id specified in VDU will be
    superseded by the server group that will be created by heat for placement
    policy.

.. code-block:: yaml

   {

   flavor: 'edcc0e22-1f7f-4d57-abe4-aeb0775cbd36',
   lease_id: 'aca14613-2bed-480e-aefe-97fa02813fcf',
   resource_type: 'virtual_instance',
   server_group_id: '8b01bdf8-a47c-49ea-96f1-3504fccfc9d4',

   }

``Sample tosca-template``:

.. sourcecode:: yaml

    tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0

    description: VNF TOSCA template with flavor input parameters

    metadata:
      template_name: sample-tosca-vnfd-instance-reservation

    topology_template:
      inputs:
        flavor:
          type: string
          description: Flavor Information

        lease_id:
          type: string
          description: lease id

        resource_type:
          type: string
          description: reservation resource type

        server_group_id:
          type: string
          description: server group id

      node_templates:
        VDU1:
          type: tosca.nodes.nfv.VDU.Tacker
          properties:
            image: cirros-0.4.0-x86_64-disk
            flavor: { get_input: flavor }
            reservation_metadata:
              resource_type: { get_input: resource_type }
              id: { get_input: server_group_id }

        CP1:
          type: tosca.nodes.nfv.CP.Tacker
          properties:
            management: true
            order: 0
            anti_spoofing_protection: false
          requirements:
            - virtualLink:
                node: VL1
            - virtualBinding:
                node: VDU1

        VL1:
          type: tosca.nodes.nfv.VL
          properties:
            network_name: net_mgmt
            vendor: Tacker


      policies:
        - RSV:
            type: tosca.policies.tacker.Reservation
            reservation:
              start_actions: [SP_RSV]
              before_end_actions: [SP_RSV]
              end_actions: [noop]
              properties:
                lease_id: { get_input: lease_id }
        - SP_RSV:
            type: tosca.policies.tacker.Scaling
            properties:
              increment: 2
              cooldown: 120
              min_instances: 0
              max_instances: 2
              default_instances: 0
            targets: [VDU1]

..

``Scaling process``

After the lease lifecycle begins in the Blazar service, tacker will receive a
start_lease event at ``2019-04-24T20:00:00``. Tacker will start scaling-out
process and you should notice VDUs will be created as per the ``increment``
value.
Similarly, when before_end_lease event is triggered at ``2019-07-09T20:00``,
tacker will start scaling-in process in which VDUs will be deleted as per the
``increment`` value.

When reservation resource type is physical:host
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Create a lease for compute host reservation:

.. sourcecode:: console

    $ blazar lease-create --physical-reservation min=1,max=1,hypervisor_properties='[">=", "$vcpus", "2"]' --start-date
    "2019-04-08 12:00" --end-date "2019-07-09 12:00" lease-1

    +--------------+--------------------------------------------------------------+
    | Field        | Value                                                        |
    +--------------+--------------------------------------------------------------+
    | created_at   | 2018-12-10 07:42:44                                          |
    | degraded     | False                                                        |
    | end_date     | 2019-07-09T12:00:00.000000                                   |
    | events       | {                                                            |
    |              |     "status": "UNDONE",                                      |
    |              |     "lease_id": "5caba925-b591-48d9-bafb-6b2b1fc1c934",      |
    |              |     "event_type": "before_end_lease",                        |
    |              |     "created_at": "2018-12-10 07:42:46",                     |
    |              |     "updated_at": null,                                      |
    |              |     "time": "2019-07-09T11:00:00.000000",                    |
    |              |     "id": "62682a3a-07fa-49f9-8f95-5b1d8ea49a7f"             |
    |              | }                                                            |
    |              | {                                                            |
    |              |     "status": "UNDONE",                                      |
    |              |     "lease_id": "5caba925-b591-48d9-bafb-6b2b1fc1c934",      |
    |              |     "event_type": "end_lease",                               |
    |              |     "created_at": "2018-12-10 07:42:46",                     |
    |              |     "updated_at": null,                                      |
    |              |     "time": "2019-07-09T12:00:00.000000",                    |
    |              |     "id": "9f98f8a3-3154-4e8f-b27e-8f61646110d2"             |
    |              | }                                                            |
    |              | {                                                            |
    |              |     "status": "UNDONE",                                      |
    |              |     "lease_id": "5caba925-b591-48d9-bafb-6b2b1fc1c934",      |
    |              |     "event_type": "start_lease",                             |
    |              |     "created_at": "2018-12-10 07:42:46",                     |
    |              |     "updated_at": null,                                      |
    |              |     "time": "2019-04-08T12:00:00.000000",                    |
    |              |     "id": "c9cd4310-ba8e-41da-a6a0-40dc38702fab"             |
    |              | }                                                            |
    | id           | 5caba925-b591-48d9-bafb-6b2b1fc1c934                         |
    | name         | lease-1                                                      |
    | project_id   | 683322bea7154651b18792b59df67d4e                             |
    | reservations | {                                                            |
    |              |     "status": "pending",                                     |
    |              |     "before_end": "default",                                 |
    |              |     "lease_id": "5caba925-b591-48d9-bafb-6b2b1fc1c934",      |
    |              |     "resource_id": "1c05b68f-a94a-4c64-8010-745c3d51dcd8",   |
    |              |     "max": 1,                                                |
    |              |     "created_at": "2018-12-10 07:42:44",                     |
    |              |     "min": 1,                                                |
    |              |     "updated_at": "2018-12-10 07:42:46",                     |
    |              |     "missing_resources": false,                              |
    |              |     "hypervisor_properties": "[\">=\", \"$vcpus\", \"2\"]",  |
    |              |     "resource_properties": "",                               |
    |              |     "id": "c56778a4-028c-4425-8e99-babc049de9dc",            |
    |              |     "resource_type": "physical:host",                        |
    |              |     "resources_changed": false                               |
    |              | }                                                            |
    | start_date   | 2019-04-08T12:00:00.000000                                   |
    | status       | PENDING                                                      |
    | trust_id     | dddffafc804c4063898f0a5d2a6d8709                             |
    | updated_at   | 2018-12-10 07:42:46                                          |
    | user_id      | c42317bee82940509427c63410fd058a                             |
    +--------------+--------------------------------------------------------------+

..

2. Replace the flavor with reservation in tosca-template given for reservation
policy as below:
Ref:
``samples/tosca-templates/vnfd/tosca-vnfd-host-reservation.yaml``

.. note::
    reservation id will be used only when reservation resource type is

    physical:host.

Add lease_id and reservation id in the parameter file.

.. code-block:: yaml

   {

   resource_type: 'physical_host',
   reservation_id: 'c56778a4-028c-4425-8e99-babc049de9dc',
   lease_id: '5caba925-b591-48d9-bafb-6b2b1fc1c934',

   }

``Sample tosca-template``:

.. sourcecode:: yaml

    tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0

    description: VNF TOSCA template with reservation_id input parameters

    metadata:
      template_name: sample-tosca-vnfd-host-reservation

    topology_template:
      inputs:
        resource_type:
          type: string
          description: reservation resource type

        reservation_id:
          type: string
          description: Reservation Id Information

        lease_id:
          type: string
          description: lease id

      node_templates:
        VDU1:
          type: tosca.nodes.nfv.VDU.Tacker
          properties:
            image: cirros-0.4.0-x86_64-disk
            reservation_metadata:
              resource_type: { get_input: resource_type }
              id: { get_input: reservation_id }

        CP1:
          type: tosca.nodes.nfv.CP.Tacker
          properties:
            management: true
            order: 0
            anti_spoofing_protection: false
          requirements:
            - virtualLink:
                node: VL1
            - virtualBinding:
                node: VDU1

        VL1:
          type: tosca.nodes.nfv.VL
          properties:
            network_name: net_mgmt
            vendor: Tacker

      policies:
        - RSV:
            type: tosca.policies.tacker.Reservation
            reservation:
              start_actions: [SP_RSV]
              before_end_actions: [noop]
              end_actions: [SP_RSV]
              properties:
                lease_id: { get_input: lease_id }
        - SP_RSV:
            type: tosca.policies.tacker.Scaling
            properties:
              increment: 2
              cooldown: 120
              min_instances: 0
              max_instances: 2
              default_instances: 0
            targets: [VDU1]

..

``Scaling process``

After the lease lifecycle begins in the Blazar service, tacker will receive a
start_lease event at ``2019-04-08T12:00:00``. Tacker will start scaling-out
process and you should notice VDUs will be created as per the ``increment``
value.
Similarly, when end_lease event is triggered at ``2019-07-09T12:00``, tacker
will start scaling-in process in which VDUs will be deleted as per the
``increment`` value.
