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

  * - Configuration
    - Default
    - Description
  * - ``CONF.server_notification.server_notification``
    - false
    - Enable FaultNotification interface.
  * - ``CONF.server_notification.uri_path_prefix``
    - /server_notification
    - Uri path prefix string for FaultNotification interface.
      When changing this configuration,
      server_notification description in api-paste.ini
      must be changed to the same value.
  * - ``CONF.server_notification.timer_interval``
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
please refer to [#fault_notification_apiref]_.

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
    ``Only the additionalParams for FaultNotification are described here``.
  | **Method type**: POST
  | **URL for the resource**: /vnflcm/v2/vnf_instances/
                              {vnfInstanceId}/instantiate
  | **Request**:

  .. list-table::
    :header-rows: 1
    :widths: 18 18 10 50

    * - Attribute name (InstantiateVnfRequest)
      - Data type
      - Cardinality
      - Description
    * - additionalParams
      - 0..1
      - KeyValuePairs (inlined)
      - Additional input parameters for the instantiation process,
        specific to the VNF being instantiated.
    * - >ServerNotifierUri
      - 1
      - String
      - Base Uri for ServerNotifier.
    * - >ServerNotifierFaultID
      - 1..N
      - String
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
  |                             |         "ServerNotifierFaultID": "1234"                                                                                                                              |
  |                             |     }                                                                                                                                                                |
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

References
==========

.. [#fault_notification_apiref] https://docs.openstack.org/api-ref/nfv-orchestration/v2/fault_notification.html
