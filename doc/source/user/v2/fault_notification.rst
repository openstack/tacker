==============================================
VNF AutoHealing triggered by FaultNotification
==============================================

Overview
--------

Tacker supports ``AutoHealing`` using ``FaultNotification`` interface.
When fault events occur in VIM, VIM notifies fault event to Tacker via
the interface. Tacker takes initiative of AutoHealing. Tacker checks
faultID attribute in the fault event and determines whether
AutoHealing should be performed. In case of performing AutoHealing,
VMs are deleted or created.


Configuration
-------------

FaultNotification is disabled by default.
To enable FaultNotification, be sure to set true for
``CONF.server_notification.server_notification``.

.. list-table::
  :header-rows: 1
  :widths: 20 10 40

  * - Configuration (CONF.server_notification)
    - Default
    - Description
  * - ``server_notification``
    - false
    - Enable FaultNotification interface.
  * - ``uri_path_prefix``
    - /server_notification
    - Uri path prefix string for FaultNotification interface.
      When changing this configuration,
      server_notification description in api-paste.ini
      must be changed to the same value.
  * - ``timer_interval``
    - 20
    - When multiple fault events for a vnf instance are
      notified in the ``timer_interval`` seconds,
      Tacker packs these notifications into single event.
      By doing this, Tacker can avoid making too many healing request.


System
------

FaultNotification AutoHealing needs external service called
Server Notifier.

The ``Server Notifier`` is a monitoring service that is implemented
by each operators, thus it is not included in Tacker.
When the Server Notifier detects fault events in VIM, it will send
FaultNotification to Tacker.

Setting FaultNotification interface uri or enabling monitoring
for the Server Notifier is performed along the vnf lifecycle.
So Tacker provides a sample implementation of the ``mgmt driver script``
to achieve interface registration and enabling monitoring.

.. code-block:: console

                            +--------------------------+
                            |      Client (NFVO)       +--------+
                            +--------------------------+        | 1. Vnf instantiation
                            +-----------------------------------v--------------------------------+
                            |               2.Create VM                                   Tacker |
     6.FaultNotification    |               3.Interface registration (in mgmt driver)            |
             +-------------->               7.Perform Healing                                    |
             |              |               8.Delete failed VM and Create new VM                 |
             |              +---------------------------------------+-------------+--------------+
             |       +----------------------------------------------+             |
      +------|-------|------------------------------------------------------------|--------------+
      |      |       | 4.Start monitoring                +---------------+--------+     VIM/NFVI |
      |      |       |                                   |               |                       |
      |   +--+-------v--+                       +--------v----+   +------v------+                |
      |   | Server      | 5.Detects fault event | +--------+  |   | +--------+  |                |
      |   | Notifier    +-------------------------> VNF    |  |   | | VNF    |  |                |
      |   |             |                       | +--------+  |   | +--------+  |                |
      |   |             |                       |          VM |   |          VM |                |
      |   +-------------+                       +-------------+   +-------------+                |
      +------------------------------------------------------------------------------------------+


For details about the interface,
please refer to `Fault Notification Interface`_.


Mgmt driver script
------------------

Sample mgmt driver script to achieve
interface registration and enabling monitoring is
``tacker/sol_refactored/mgmt_drivers/server_notification.py``

Put this script into target VNF package and Server Notifier
can detect fault event on the VNF.


LCM interface
-------------

The LCM interface is modified to set parameters for Server Notifier.
The ``additionalParams`` must be set when using FaultNotification.

* | **Name**: Instantiate VNF task
  | **Description**: This task resource represents the ``Instantiate VNF``
    operation. The client can use this resource to instantiate a VNF instance.
    ``Only the additionalParams and the vnfConfigurableProperties for
    FaultNotification are described here``.
  | **Method type**: POST
  | **URL for the resource**:
    /vnflcm/v2/vnf_instances/{vnfInstanceId}/instantiate
  | **Request**:

  .. list-table::
    :header-rows: 1
    :widths: 18 18 10 50

    * - Attribute name (InstantiateVnfRequest)
      - Data type
      - Cardinality
      - Description
    * - vnfConfigurableProperties
      - KeyValuePairs
      - 0..1
      - Additional VNF-specific attributes that
        provide the current values of the configurable
        properties of the VNF instance.
    * - additionalParams
      - KeyValuePairs
      - 0..1
      - Additional input parameters for the instantiation process,
        specific to the VNF being instantiated.


  .. list-table::
    :header-rows: 1
    :widths: 18 18 10 50

    * - Attribute name (vnfConfigurableProperties)
      - Data type
      - Cardinality
      - Description
    * - isAutohealEnabled
      - boolean
      - 0..1
      - If present, the VNF supports auto-healing. If set to
        true, auto-healing is currently enabled.
        If set to false, autohealing is currently disabled.


  .. list-table::
    :header-rows: 1
    :widths: 18 18 10 50

    * - Attribute name (additionalParams)
      - Data type
      - Cardinality
      - Description
    * - ServerNotifierUri
      - String
      - 1
      - Base Uri for ServerNotifier.
    * - ServerNotifierFaultID
      - String
      - 1..N
      - List of string that indicates which type of alarms to detect.


The value of ``ServerNotifierUri`` and ``ServerNotifierFaultID`` are stored
in ``instantiatedVnfInfo`` of vnfInstance. The values can be shown
with vnflcm show command. For example:

.. code-block:: console

  $ openstack vnflcm show 6fd264ea-78fb-4862-90c0-1a9597734d95 --os-tacker-api-version 2
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                                                                |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | ID                          | 6fd264ea-78fb-4862-90c0-1a9597734d95                                                                                                                                 |
  | Instantiated Vnf Info       | {                                                                                                                                                                    |
  |                             |  ....                                                                                                                                                                |
  |                             |     "metadata": {                                                                                                                                                    |
  |                             |         "ServerNotifierUri": "http://localhost:9990/server_notification",                                                                                            |
  |                             |         "ServerNotifierFaultID": ["1111", "1234"]                                                                                                                    |
  |                             |     }                                                                                                                                                                |
  |                             |  ....                                                                                                                                                                |
  | VNF Configurable Properties | isAutohealEnabled=True                                                                                                                                               |
  |                             |  ....                                                                                                                                                                |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------+


Auto Healing
------------

When fault events occur in VIM, ServerNotifier notifies fault event
to Tacker via the FaultNotification interface.

Tacker checks ``fault_id`` attribute in the fault event and determines
whether AutoHealing should be performed. In case of performing
AutoHealing, VMs are deleted and created via Heat. The client is
no need to handle healing.


Using Vendor Specific Plugin
----------------------------

ServerNotification plugin can be replaced with a vendor specific function.
To replace a plugin, change the configurations below.
The replaced class must be a subclass of
tacker.sol_refactored.common.monitoring_plugin_base.MonitoringPlugin.

.. list-table::
  :header-rows: 1
  :widths: 40 40 40

  * - Configuration (CONF.server_notification)
    - Default
    - Description
  * - ``server_notification_package``
    - tacker.sol_refactored.common.server_notification
    - Package name for server notification.
  * - ``server_notification_class``
    - ServerNotification
    - Class name for server notification.


Error-handling
--------------

This chapter introduces how to perform error-handling if the LCM fails in
the FaultNotification function.

The LCM of the FaultNotification function will use MgmtDriver, so if the
user wants to call MgmtDriver in the rollback operation of error-handling,
the VNF Package needs to be modified in advance.

For the specific modification method, please refer to
``Error-handling of MgmtDriver`` in :doc:`/user/v2/error_handling`.

.. note::

    After modifying the VNF Package, LCM can be performed normally. If the
    LCM fails, the user can perform error-handling operations.

    For details, please refer to the content of
    ``Retry VNF LCM Operation`` and ``Rollback VNF LCM Operation`` in
    :doc:`/user/v2/error_handling`.


.. _Fault Notification Interface:
  https://docs.openstack.org/api-ref/nfv-orchestration/v2/fault_notification.html
