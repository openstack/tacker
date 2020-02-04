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
write a pluggable driver that monitors the various status conditions of the
VNF entities it deploys and manages.

How to write a new monitor driver
----------------------------------

A monitor driver for tacker is a python module which contains a class that
inherits from
"tacker.vnfm.monitor_drivers.abstract_driver.VNFMonitorAbstractDriver". If the
driver depends/imports more than one module, then create a new python package
under tacker/vnfm/monitor_drivers folder. After this we have to mention our
driver path in setup.cfg file in root directory.

For example:
::

  tacker.tacker.monitor_drivers =
      ping = tacker.vnfm.monitor_drivers.ping.ping:VNFMonitorPing

Following methods need to be overridden in the new driver:

``def get_type(self)``
    This method must return the type of driver. ex: ping

``def get_name(self)``
    This method must return the symbolic name of the vnf monitor plugin.

``def get_description(self)``
    This method must return the description for the monitor driver.

``def monitor_get_config(self, plugin, context, vnf)``
    This method must return dictionary of configuration data for the monitor
    driver.

``def monitor_url(self, plugin, context, vnf)``
    This method must return the url of vnf to monitor.

``def monitor_call(self, vnf, kwargs)``
    This method is called cyclically each time a monitoring is
    triggered. **kwagrs** is a dict object given under **parameters** in
    the target VDU template. This method must either return boolean
    value 'True', if VNF is healthy. Otherwise it should return an event
    string like 'failure' or 'calls-capacity-reached' based on specific
    VNF health condition. More details on these event is given in below
    section.

Custom events
--------------
As mentioned in above section, if the return value of monitor_call method is
other than boolean value 'True', then we have to map those event to the
corresponding action as described below.

For example:

::

  VDU1:
    properties:
      ...
      monitoring_policy:
        name: ping
        actions:
          failure: respawn

In this example, we have an event called 'failure'. So whenever monitor_call
returns 'failure' tacker will respawn the VNF.


Actions
--------
The available actions that a monitor driver can call when a particular event
occurs.

#. respawn
    In case of OpenStack VIM, when any VDU monitoring fails, it will delete
    the entire VNF and create a new one.
#. vdu_autoheal
    In case of OpenStack VIM, when any VDU monitoring fails, it will delete
    only that specific VDU resource and create a new one alone with it's
    dependent resources like CP.
#. log
#. log_and_kill

How to write TOSCA template to monitor VNF entities
----------------------------------------------------

In the vdus section, you can specify the monitor details with
corresponding actions and parameters. The syntax for writing monitor
policy is as follows:

::

  vduN:
    properties:
      ...
      monitoring_policy:
        name: <monitoring-driver-name>:
        parameters:
          <param-name>: <param-value>
          ...
        actions:
          <event-name>: <action-name>


Example Template
----------------

::

  VDU1:
    properties:
      ...
      monitoring_policy:
        name: ping
        actions:
          failure: respawn

  VDU2:
    properties:
      ...
      monitoring_policy:
        name: http-ping
        parameters:
          port: 8080
        actions:
          failure: vdu_autoheal

  VDU3:
    properties:
      ...
      monitoring_policy:
        name: <your-driver-name>
        parameters:
          <param1>: <value1>
          <param2>: <value2>
        actions:
          <event1>: <action>
          <event2>: <action>
