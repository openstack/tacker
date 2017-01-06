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
            resize_compute:
                event_type:
                    type: tosca.events.resource.utilization
                    implementation: ceilometer
                metrics: cpu_util
                condition:
                    threshold: 50
                    constraint: utilization greater_than 50%
                    period: 65
                    evaluations: 1
                    method: avg
                    comparison_operator: gt
                actions: [respawn]

Alarm framework already supported the some default backend actions like
**scaling, respawn, log, and log_and_kill**.

Tacker users could change the desired action as described in the above example.
Until now, the backend actions could be pointed to the specific policy which
is also described in TOSCA template like scaling policy. The integration between
alarming monitoring and scaling was also supported by Alarm monitor in Tacker:

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
            image: cirros-0.3.4-x86_64-uec
            mgmt_driver: noop
            availability_zone: nova
            metadata: {metering.vnf: SG1}

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
        VDU2:
          type: tosca.nodes.nfv.VDU.Tacker
          capabilities:
            nfv_compute:
              properties:
                disk_size: 1 GB
                mem_size: 512 MB
                num_cpus: 2
          properties:
            image: cirros-0.3.4-x86_64-uec
            mgmt_driver: noop
            availability_zone: nova
            metadata: {metering.vnf: SG1}

        CP2:
          type: tosca.nodes.nfv.CP.Tacker
          properties:
            management: true
            anti_spoofing_protection: false
          requirements:
            - virtualLink:
                node: VL1
            - virtualBinding:
                node: VDU2

        VL1:
          type: tosca.nodes.nfv.VL
          properties:
            network_name: net_mgmt
            vendor: Tacker

      policies:
        - SP1:
            type: tosca.policies.tacker.Scaling
            properties:
              increment: 1
              cooldown: 120
              min_instances: 1
              max_instances: 3
              default_instances: 2
              targets: [VDU1,VDU2]

        - vdu_cpu_usage_monitoring_policy:
            type: tosca.policies.tacker.Alarming
            triggers:
                vdu_hcpu_usage_scaling_out:
                    event_type:
                        type: tosca.events.resource.utilization
                        implementation: ceilometer
                    metrics: cpu_util
                    condition:
                        threshold: 50
                        constraint: utilization greater_than 50%
                        period: 600
                        evaluations: 1
                        method: avg
                        comparison_operator: gt
                    metadata: SG1
                    actions: [SP1]

                vdu_lcpu_usage_scaling_in:
                    targets: [VDU1, VDU2]
                    event_type:
                        type: tosca.events.resource.utilization
                        implementation: ceilometer
                    metrics: cpu_util
                    condition:
                        threshold: 10
                        constraint: utilization less_than 10%
                        period: 600
                        evaluations: 1
                        method: avg
                        comparison_operator: lt
                    metadata: SG1
                    actions: [SP1]


**NOTE:**
metadata defined in VDU properties must be matched with metadata in monitoring policy

How to setup environment
~~~~~~~~~~~~~~~~~~~~~~~~

If OpenStack Devstack is used to test alarm monitoring in Tacker, OpenStack
Ceilometer and Aodh plugins will need to be enabled in local.conf:

.. code-block::ini

**enable_plugin ceilometer https://git.openstack.org/openstack/ceilometer master**

**enable_plugin aodh https://git.openstack.org/openstack/aodh master**

How to monitor VNFs via alarm triggers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

How to setup alarm configuration
================================

Firstly, vnfd and vnf need to be created successfully using pre-defined TOSCA
template for alarm monitoring. Then, in order to know whether alarm
configuration defined in Tacker is successfully passed to Ceilometer,
Tacker users could use CLI:

.. code-block:: console

    $aodh alarm list

    +--------------------------------------+-----------+--------------------------------------------------------------------------------------------------------------------------------------+-------------------+----------+---------+
    | alarm_id                             | type      | name                                                                                                                                 | state             | severity | enabled |
    +--------------------------------------+-----------+--------------------------------------------------------------------------------------------------------------------------------------+-------------------+----------+---------+
    | 6f2336b9-e0a2-4e33-88be-bc036192b42b | threshold | tacker.vnfm.infra_drivers.openstack.openstack_OpenStack-a0f60b00-ad3d-4769-92ef-e8d9518da2c8-vdu_lcpu_scaling_in-smgctfnc3ql5        | insufficient data | low      | True    |
    | e049f0d3-09a8-46c0-9b88-e61f1f524aab | threshold | tacker.vnfm.infra_drivers.openstack.openstack_OpenStack-a0f60b00-ad3d-4769-92ef-e8d9518da2c8-vdu_hcpu_usage_scaling_out-lubylov5g6xb | insufficient data | low      | True    |
    +--------------------------------------+-----------+--------------------------------------------------------------------------------------------------------------------------------------+-------------------+----------+---------+

.. code-block:: console

    $aodh alarm show 6f2336b9-e0a2-4e33-88be-bc036192b42b

    +---------------------------+-------------------------------------------------------------------------------------------------------------------------------+
    | Field                     | Value                                                                                                                         |
    +---------------------------+-------------------------------------------------------------------------------------------------------------------------------+
    | alarm_actions             | [u'http://pinedcn:9890/v1.0/vnfs/a0f60b00-ad3d-4769-92ef-e8d9518da2c8/vdu_lcpu_scaling_in/SP1-in/yl7kh5qd']                   |
    | alarm_id                  | 6f2336b9-e0a2-4e33-88be-bc036192b42b                                                                                          |
    | comparison_operator       | lt                                                                                                                            |
    | description               | utilization less_than 10%                                                                                                     |
    | enabled                   | True                                                                                                                          |
    | evaluation_periods        | 1                                                                                                                             |
    | exclude_outliers          | False                                                                                                                         |
    | insufficient_data_actions | None                                                                                                                          |
    | meter_name                | cpu_util                                                                                                                      |
    | name                      | tacker.vnfm.infra_drivers.openstack.openstack_OpenStack-a0f60b00-ad3d-4769-92ef-e8d9518da2c8-vdu_lcpu_scaling_in-smgctfnc3ql5 |
    | ok_actions                | None                                                                                                                          |
    | period                    | 600                                                                                                                           |
    | project_id                | 3db801789c9e4b61b14ce448c9e7fb6d                                                                                              |
    | query                     | metadata.user_metadata.vnf_id = a0f60b00-ad3d-4769-92ef-e8d9518da2c8                                                          |
    | repeat_actions            | True                                                                                                                          |
    | severity                  | low                                                                                                                           |
    | state                     | insufficient data                                                                                                             |
    | state_timestamp           | 2016-11-16T18:39:30.134954                                                                                                    |
    | statistic                 | avg                                                                                                                           |
    | threshold                 | 10.0                                                                                                                          |
    | time_constraints          | []                                                                                                                            |
    | timestamp                 | 2016-11-16T18:39:30.134954                                                                                                    |
    | type                      | threshold                                                                                                                     |
    | user_id                   | a783e8a94768484fb9a43af03c6426cb                                                                                              |
    +---------------------------+-------------------------------------------------------------------------------------------------------------------------------+


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

.. code-block::ini

curl -H "Content-Type: application/json" -X POST -d '{"alarm_id": "35a80852-e24f-46ed-bd34-e2f831d00172", "current": "alarm"}' http://pinedcn:9890/v1.0/vnfs/a0f60b00-ad3d-4769-92ef-e8d9518da2c8/vdu_lcpu_scaling_in/SP1-in/yl7kh5qd

Then, users can check Horizon to know if vnf is respawned. Please note that
the url used in the above command could be captured from "**ceilometer alarm-show** command as shown before.
"key" attribute in body request need to be captured from the url. The reason is that key will be authenticated
so that the url is requested only one time.
