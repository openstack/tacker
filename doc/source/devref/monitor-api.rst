Tacker Monitoring Framework
============================

This section will introduce tacker monitoring framework and describes the
various actions that a user can take when a specific event occurs.

* Introduction
* How to write a new monitor driver
* Events
* Actions
* How to write TOSCA template to monitor VNF entities

Introduction
-------------

Tacker monitoring framework provides the NFV operators and VNF vendors to
write a pluggable driver that monitors the various status coditions of the
VNF entities it deploys and manages.

How to write a new monitor driver
----------------------------------

A monitor driver for tacker is a python module which contains a class that
inherits from
"tacker.vm.monitor_drivers.abstract_driver.VNFMonitorAbstractDriver". If the
driver depends/imports more than one module, then create a new python package
under tacker/vm/monitor_drivers folder. After this we have to mention our
driver path in setup.cfg file in root directory.

For example:
::

  tacker.tacker.monitor_drivers =
      ping = tacker.vm.monitor_drivers.ping.ping:VNFMonitorPing

The methods that need to override in driver are:
1)def get_type(self)
This method must return the type of driver ex: ping

2)def get_name(self)
This method must return the symbolic name of the device monitor plugin

3)def get_description(self)
This method must return the description for the monitor driver

4)def monitor_get_config(self, plugin, context, device)
This method must return dict of monitor configuration data

5)def monitor_url(self, plugin, context, device)
This method must return the url of device to monitor

6)def monitor_call(self, device, kwargs)
This method must either return boolean value True if VNF is healthy or return
a event string like 'failure' or 'calls-capacity-reached' for specific VNF
health condition.

Custom events
--------------
As mentioned above, the return value of monitor_call is health status. If the
return value of monitor_call is other than boolean value True, then we have to
map those event to the corresponding action as described below.

For example:

::

  vdu1:
    monitoring_policy:
      ping:
        actions:
          failure: respawn

In this  example we have an event called 'failure'. So whenever monitor_call
returns 'failure' tacker will respawn the VNF.


Actions
--------
The available actions that a monitor driver can call when a particular event
occurs

1. respawn
2. log_and_kill
3. log

How to write TOSCA template to monitor VNF entities
----------------------------------------------------

In the vdus section, under vdu you can specify the monitors details with
corresponding actions and parameters.The syntax for writing monitor policy
is as follows:

::

  vduN:
    monitoring_policy:
      <monitoring-driver-name>:
        monitoring_params:
          <param-name>: <param-value>
          ...
        actions:
          <event>: <action-name>
          ...
      ...


Example Template
----------------

::

  vdu1:
    monitoring_policy:
      ping:
        actions:
          failure: respawn

  vdu2:
    monitoring_policy:
      http-ping:
        monitoring_params:
          port: 8080
          url: ping.cgi
        actions:
          failure: respawn

    acme_scaling_driver:
      monitoring_params:
        resource: cpu
        threshold: 10000
      actions:
        max_foo_reached: scale_up
        min_foo_reached: scale_down

