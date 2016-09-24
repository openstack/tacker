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
                action:
                  resize_compute:
                    action_name: respawn

Alarm framework already supported the some default backend actions like
**respawn, log, and log_and_kill**.

Tacker users could change the desired action as described in the above example.
Until now, the backend actions could be pointed to the specific policy which
is also described in TOSCA template like scaling policy. The integration between
alarming monitoring and auto-scaling was also supported by Alarm monitor in Tacker:

.. code-block:: yaml

    policies:
    - SP1:
        type: tosca.policy.tacker.Scaling
        properties:
          increment: 1
          cooldown: 120
          min_instances: 1
          max_instances: 3
          default_instances: 2
          targets: [VDU1]

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
                    period: 600
                    evaluations: 1
                    method: avg
                    comparison_operator: gt
                action:
                  resize_compute:
                    action_name: SP1

How to setup environment
~~~~~~~~~~~~~~~~~~~~~~~~

If OpenStack Devstack is used to test alarm monitoring in Tacker, OpenStack Ceilometer
and Aodh plugins will need to be enabled in local.conf:

.. code-block::ini

**enable_plugin ceilometer https://git.openstack.org/openstack/ceilometer master**

**enable_plugin aodh https://git.openstack.org/openstack/aodh master**

How to monitor VNFs via alarm triggers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

How to setup alarm configuration
================================

Firstly, vnfd and vnf need to be created successfully using pre-defined TOSCA template
for alarm monitoring. Then, in order to know whether alarm configuration defined in Tacker
is successfully passed to Ceilometer, Tacker users could use CLI:

.. code-block:: console

    $ceilometer alarm-list

    +--------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------+-------------------+----------+---------+------------+-------------------------------------+------------------+
    | Alarm ID                             | Name                                                                                                                                       | State             | Severity | Enabled | Continuous | Alarm condition                     | Time constraints |
    +--------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------+-------------------+----------+---------+------------+-------------------------------------+------------------+
    | f6a89242-d849-4a1a-9eb5-de4c0730252f | tacker.vnfm.infra_drivers.openstack.openstack_OpenStack-d4900104-6257-4084-8506-9fa6895d1294-vdu1_cpu_usage_monitoring_policy-7rt36gqbmuqo | insufficient data | low      | True    | True       | avg(cpu_util) > 15.0 during 1 x 65s | None             |
    +--------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------+-------------------+----------+---------+------------+-------------------------------------+------------------

.. code-block:: console

    $ ceilometer alarm-show 35a80852-e24f-46ed-bd34-e2f831d00172

    +---------------------------+--------------------------------------------------------------------------+
    | Property                  | Value                                                                    |
    +---------------------------+--------------------------------------------------------------------------+
    | alarm_actions             | ["http://pinedcn:9890/v1.0/vnfs/d4900104-6257-4084-8506-9fa6895d1294/vdu |
    |                           | 1_cpu_usage_monitoring_policy/SP1/i42kd018"]                             |
    | alarm_id                  | f6a89242-d849-4a1a-9eb5-de4c0730252f                                     |
    | comparison_operator       | gt                                                                       |
    | description               | utilization greater_than 50%                                             |
    | enabled                   | True                                                                     |
    | evaluation_periods        | 1                                                                        |
    | exclude_outliers          | False                                                                    |
    | insufficient_data_actions | None                                                                     |
    | meter_name                | cpu_util                                                                 |
    | name                      | tacker.vnfm.infra_drivers.openstack.openstack_OpenStack-d4900104-6257-40 |
    |                           | 84-8506-9fa6895d1294-vdu1_cpu_usage_monitoring_policy-7rt36gqbmuqo       |
    | ok_actions                | None                                                                     |
    | period                    | 65                                                                       |
    | project_id                | abdc74442be44b9486ca5e32a980bca1                                         |
    | query                     | metadata.user_metadata.vnf_id == d4900104-6257-4084-8506-9fa6895d1294    |
    | repeat_actions            | True                                                                     |
    | severity                  | low                                                                      |
    | state                     | insufficient data                                                        |
    | statistic                 | avg                                                                      |
    | threshold                 | 15.0                                                                     |
    | type                      | threshold                                                                |
    | user_id                   | 25a691398e534893b8627f3762712515                                         |
    +---------------------------+--------------------------------------------------------------------------+


How to trigger alarms:
======================
As shown in the above Ceilometer command, alarm state is shown as "insufficient data". Alarm is
triggered by Ceilometer once alarm state changes to "alarm".
To make VNF instance reach to the pre-defined threshold, some simple scripts could be used.

Note: Because Ceilometer pipeline set the default interval to 600s (10 mins),
in order to reduce this interval, users could edit "interval" value
in **/etc/ceilometer/pipeline.yaml** file and then restart Ceilometer service.

Another way could be used to check if backend action is handled well in Tacker:

.. code-block::ini

curl -H "Content-Type: application/json" -X POST -d '{"alarm_id": "35a80852-e24f-46ed-bd34-e2f831d00172", "current": "alarm"}' http://ubuntu:9890/v1.0/vnfs/6f3e523d-9e12-4973-a2e8-ea04b9601253/vdu1_cpu_usage_monitoring_policy/respawn/g0jtsxu9

Then, users can check Horizon to know if vnf is respawned. Please note that the url used
in the above command could be captured from "**ceilometer alarm-show** command as shown before.
"key" attribute in body request need to be captured from the url. The reason is that key will be authenticated
so that the url is requested only one time.
