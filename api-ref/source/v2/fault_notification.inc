.. -*- rst -*-

============================
Fault Notification Interface
============================

This interface is used for notifying fault events that is detected by VIM.
When fault events occur in VIM, VIM notifies fault event to Tacker via
the interface. Tacker performs autohealing according to the fault event.

Notify a fault event
====================

.. rest_method::  POST /server_notification/vnf_instances/{vnfInstanceId}/servers/{server_id}/notify

Notifies Tacker when a fault event occur in VIM.

This interface can be alerted by multiple times in a short period.
To prevent invoking multiple heal operations to single VNF,
the multiple requests by this interface are packed for
a configured period of time (CONF.server_notification.timer_interval).

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 204

.. rest_status_code:: error status.yaml

  - 400
  - 404: fault_notification

Request Parameters
------------------

.. rest_parameters:: parameters_fault_notification.yaml

  - vnfInstanceId: vnf_instance_id
  - server_id: server_id
  - notification: notification
  - host_id: host_id
  - alarm_id: alarm_id
  - fault_id: fault_id
  - fault_type: fault_type
  - fault_option: fault_option

Request Example
---------------

.. literalinclude:: samples/fault_notification/notify.json
   :language: javascript
