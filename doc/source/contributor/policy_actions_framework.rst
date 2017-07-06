Tacker Policy Framework
=======================

This section will introduce framework for tacker policy actions.

* Introduction
* How to write a new policy action
* Event and Auditing support
* How to combine policy actions with existing monitoring frameworks in Tacker

Introduction
------------

Tacker policy actions framework provides the NFV operators and VNF vendors to
write a pluggable action that manages their own VNFs. Currently Tacker
already provided some common actions like autoscaling, respawning, and
logging. With this framework the custom actions can be easily
applied for the management purpose.

How to write a new policy action
--------------------------------

A policy action for tacker is a python module which contains a class that
inherits from
"tacker.vnfm.policy_actions.abstract_action.AbstractPolicyAction". If the
driver depends/imports more than one module, then create a new python package
under tacker/vnfm/policy_actions folder. After this we have to mention our
driver path in setup.cfg file in root directory.

For example:
::

  tacker.tacker.policy.actions =
    respawn = tacker.vnfm.policy_actions.respawn.respawn:VNFActionRespawn

Following methods need to be overridden in the new action:

``def get_type(self)``
    This method must return the type of action. ex: respawn

``def get_name(self)``
    This method must return the symbolic name of the vnf policy action.

``def get_description(self)``
    This method must return the description for the policy action.

``def execute_action(self, plugin, context, vnf, arguments)``
    This method must expose what will be executed with the policy action.
    'arguments' is used to add more options for policy actions. For example,
    if action is scaling, 'arguments' should let you know
    'scaling-out' or 'scaling-in' will be applied.

Event and Auditing support
--------------------------

This function can be used to describe the execution process of policy.
For example:
::

  _log_monitor_events(context, vnf_dict, "ActionRespawnHeat invoked")


How to combine policy with existing monitoring framework in Tacker
------------------------------------------------------------------

In the monitoring policy section, you can specify the monitors details with
corresponding action.

The below example shows how policy is used for alarm monitor.
Example Template
----------------

::

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
