..
  Licensed under the Apache License, Version 2.0 (the "License"); you may
  not use this file except in compliance with the License. You may obtain
  a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
  License for the specific language governing permissions and limitations
  under the License.

.. _ref-alarm_frm:

==========================
Alarm monitoring framework
==========================

This document describes how to use alarm-based monitoring driver in Tacker.

Sample TOSCA with monitoring policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following example shows monitoring policy using TOSCA template.
The target (VDU1) of the monitoring policy in this example need to be
described firstly like other TOSCA templates in Tacker.

.. code-block:: yaml

  policies:
    - vdu1_cpu_usage_monitoring_policy:
        type: tosca.policies.tacker.Alarming
        triggers:
            vdu_hcpu_usage_respawning:
                event_type:
                    type: tosca.events.resource.utilization
                    implementation: ceilometer
                metric: cpu_util
                condition:
                    threshold: 50
                    constraint: utilization greater_than 50%
                    granularity: 600
                    evaluations: 1
                    aggregation_method: mean
                    resource_type: instance
                    comparison_operator: gt
                metadata: VDU1
                action: [respawn]

Alarm framework already supported the some default backend actions like
**scaling, respawn, log, and log_and_kill**.

Tacker users could change the desired action as described in the above example.
Until now, the backend actions could be pointed to the specific policy which
is also described in TOSCA template like scaling policy. The integration
between alarming monitoring and scaling was also supported by Alarm monitor
in Tacker:

.. code-block:: yaml

    tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0
    description: Demo example

    metadata:
     template_name: sample-tosca-vnfd

    topology_template:
      node_templates:
        VDU1:
          type: tosca.nodes.nfv.VDU.Tacker
          capabilities:
            nfv_compute:
              properties:
                disk_size: 1 GB
                mem_size: 512 MB
                num_cpus: 2
          properties:
            image: cirros-0.4.0-x86_64-disk
            mgmt_driver: noop
            availability_zone: nova
            metadata: {metering.server_group: SG1}

        CP1:
          type: tosca.nodes.nfv.CP.Tacker
          properties:
            management: true
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
        - SP1:
            type: tosca.policies.tacker.Scaling
            targets: [VDU1]
            properties:
              increment: 1
              cooldown: 120
              min_instances: 1
              max_instances: 3
              default_instances: 1

        - vdu_cpu_usage_monitoring_policy:
            type: tosca.policies.tacker.Alarming
            triggers:
                vdu_hcpu_usage_scaling_out:
                    event_type:
                        type: tosca.events.resource.utilization
                        implementation: ceilometer
                    metric: cpu_util
                    condition:
                        threshold: 80
                        constraint: utilization greater_than 80%
                        granularity: 300
                        evaluations: 1
                        aggregation_method: mean
                        resource_type: instance
                        comparison_operator: gt
                    metadata: SG1
                    action: [SP1]

                vdu_lcpu_usage_scaling_in:
                    event_type:
                        type: tosca.events.resource.utilization
                        implementation: ceilometer
                    metric: cpu_util
                    condition:
                        threshold: 10
                        constraint: utilization less_than 10%
                        granularity: 300
                        evaluations: 1
                        aggregation_method: mean
                        resource_type: instance
                        comparison_operator: lt
                    metadata: SG1
                    action: [SP1]


**NOTE:**
metadata defined in VDU properties must be matched with metadata
in monitoring policy

How to setup environment
~~~~~~~~~~~~~~~~~~~~~~~~

If OpenStack Devstack is used to test alarm monitoring in Tacker, OpenStack
Ceilometer and Aodh plugins will need to be enabled in local.conf:

.. code-block::ini

**enable_plugin ceilometer https://opendev.org/openstack/ceilometer master**

**enable_plugin aodh https://opendev.org/openstack/aodh master**

How to monitor VNFs via alarm triggers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

How to setup alarm configuration
================================

Tacker provides templates that implemented Ceilometer as alarm for monitoring
VNFs, which are located in  **tacker/samples/tosca-templates/vnfd**.

1. tosca-vnfd-alarm-multi-actions.yaml

2. tosca-vnfd-alarm-respawn.yaml

3. tosca-vnfd-alarm-scale.yaml

The following commands shows creating VNF with alarms for scaling in and out.

.. code-block:: console

    $ cd ~/tacker/samples/tosca-templates/vnfd
    $ openstack vnf create --vnfd-template tosca-vnfd-alarm-scale.yaml VNF1

Firstly, vnfd and vnf need to be created successfully using pre-defined TOSCA
template for alarm monitoring. Then, in order to know whether alarm
configuration defined in Tacker is successfully passed to Ceilometer,
Tacker users could use CLI:

.. code-block:: console

    $ openstack alarm list

    +--------------------------------------+--------------------------------------------+-----------------------------------------------------------------------------------+-------------------+----------+---------+
    | alarm_id                             | type                                       | name                                                                              | state             | severity | enabled |
    +--------------------------------------+--------------------------------------------+-----------------------------------------------------------------------------------+-------------------+----------+---------+
    | f418ebf8-f8a6-4991-8f0d-938e38434411 | gnocchi_aggregation_by_resources_threshold | VNF1_7582cdf4-58ed-4df8-8fa2-c15938adf70b-vdu_hcpu_usage_scaling_out-4imzw3c7cicb | insufficient data | low      | True    |
    | 70d86622-940a-4bc3-87c2-d5dfbb01bbea | gnocchi_aggregation_by_resources_threshold | VNF1_7582cdf4-58ed-4df8-8fa2-c15938adf70b-vdu_lcpu_usage_scaling_in-dwvdvbegiqdk  | insufficient data | low      | True    |
    +--------------------------------------+--------------------------------------------+-----------------------------------------------------------------------------------+-------------------+----------+---------+


.. code-block:: console

    $ openstack alarm show 70d86622-940a-4bc3-87c2-d5dfbb01bbea
    +---------------------------+------------------------------------------------------------------------------------------------------------------+
    | Field                     | Value                                                                                                            |
    +---------------------------+------------------------------------------------------------------------------------------------------------------+
    | aggregation_method        | mean                                                                                                             |
    | alarm_actions             | [u'http://ubuntu:9890/v1.0/vnfs/7582cdf4-58ed-4df8-8fa2-c15938adf70b/vdu_lcpu_usage_scaling_in/SP1-in/v2fq7rd7'] |
    | alarm_id                  | 70d86622-940a-4bc3-87c2-d5dfbb01bbea                                                                             |
    | comparison_operator       | lt                                                                                                               |
    | description               | utilization less_than 10%                                                                                        |
    | enabled                   | True                                                                                                             |
    | evaluation_periods        | 1                                                                                                                |
    | granularity               | 60                                                                                                               |
    | insufficient_data_actions | []                                                                                                               |
    | metric                    | cpu_util                                                                                                         |
    | name                      | VNF1_7582cdf4-58ed-4df8-8fa2-c15938adf70b-vdu_lcpu_usage_scaling_in-dwvdvbegiqdk                                 |
    | ok_actions                | []                                                                                                               |
    | project_id                | b5e054a3861b4da2b084aca9530096be                                                                                 |
    | query                     | {"=": {"server_group": "SG1-64beb5e4-c0"}}                                                                       |
    | repeat_actions            | True                                                                                                             |
    | resource_type             | instance                                                                                                         |
    | severity                  | low                                                                                                              |
    | state                     | insufficient data                                                                                                |
    | state_reason              | Not evaluated yet                                                                                                |
    | state_timestamp           | 2018-07-20T06:00:33.142762                                                                                       |
    | threshold                 | 10.0                                                                                                             |
    | time_constraints          | []                                                                                                               |
    | timestamp                 | 2018-07-20T06:00:33.142762                                                                                       |
    | type                      | gnocchi_aggregation_by_resources_threshold                                                                       |
    | user_id                   | 61fb5c6193e549f3baee26bd508c0b29                                                                                 |
    +---------------------------+------------------------------------------------------------------------------------------------------------------+


How to trigger alarms:
======================

As shown in the above Ceilometer command, alarm state is shown as
"insufficient data". Alarm is triggered by Ceilometer once alarm
state changes to "alarm".
To make VNF instance reach to the pre-defined threshold, some
simple scripts could be used.

Note: Because Ceilometer pipeline set the default interval to 600s (10 mins),
in order to reduce this interval, users could edit "interval" value
in **/etc/ceilometer/pipeline.yaml** file and then restart Ceilometer service.

Another way could be used to check if backend action is handled well in Tacker:

.. code-block:: console

    curl -H "Content-Type: application/json" -X POST -d '{"alarm_id": "35a80852-e24f-46ed-bd34-e2f831d00172", "current": "alarm"}' http://ubuntu:9890/v1.0/vnfs/7582cdf4-58ed-4df8-8fa2-c15938adf70b/vdu_lcpu_usage_scaling_in/SP1-in/v2fq7rd7

Then, users can check Horizon to know if vnf is respawned. Please note
that the url used in the above command could be captured from
"**ceilometer alarm-show** command as shown before. "key" attribute
in body request need to be captured from the url. The reason is that
key will be authenticated so that the url is requested only one time.
