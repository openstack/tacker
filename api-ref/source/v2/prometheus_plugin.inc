.. -*- rst -*-

===========================
Prometheus Plugin Interface
===========================

This interface is used for notifying alert that is detected by
the External Monitoring Tool. The External Monitoring Tool is
Prometheus based Monitoring system.

The Prometheus Plugin has 5 functions:

- Alerting interface for ETSI NFV-SOL 002/003 based Performance Management Job.
- Alerting interface for ETSI NFV-SOL 002/003 based Performance Management
  Threshold.
- Alerting interface for ETSI NFV-SOL 002/003 based Fault Management.
- Alerting interface for Prometheus Plugin AutoScaling.
- Alerting interface for Prometheus Plugin AutoHealing.

Alerting interface for ETSI NFV-SOL 002/003 based Performance Management Job
============================================================================

.. rest_method::  POST /pm_event

Alert Tacker when one or more Performance values are obtained.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 204

.. rest_status_code:: error status.yaml

  - 400
  - 404: prometheus_plugin_pm

Request Parameters
------------------

.. rest_parameters:: parameters_prometheus_plugin.yaml

  - alerts: alerts
  - status: status
  - labels: labels
  - receiver_type: receiver_type
  - function_type: function_type_pm
  - job_id: job_id
  - object_instance_id: object_instance_id
  - sub_object_instance_id: sub_object_instance_id
  - metric: metric
  - annotations: annotations
  - value: value
  - startsAt: startsAt
  - endsAt: endsAt
  - fingerprint: fingerprint

Request Example
---------------

.. literalinclude:: samples/prometheus_plugin/alert_pm.json
   :language: javascript


Alerting interface for ETSI NFV-SOL 002/003 based Performance Management Threshold
==================================================================================

.. rest_method::  POST /pm_threshold

Alert Tacker when one or more Performance values are obtained.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 204

.. rest_status_code:: error status.yaml

  - 400
  - 404: prometheus_plugin_pm

Request Parameters
------------------

.. rest_parameters:: parameters_prometheus_plugin.yaml

  - alerts: alerts
  - status: status
  - labels: labels
  - receiver_type: receiver_type
  - function_type: function_type_threshold
  - threshold_id: threshold_id
  - object_instance_id: object_instance_id
  - sub_object_instance_id: sub_object_instance_id
  - metric: metric
  - annotations: annotations
  - value: value
  - startsAt: startsAt
  - endsAt: endsAt
  - fingerprint: fingerprint

Request Example
---------------

.. literalinclude:: samples/prometheus_plugin/alert_pm_threshold.json
   :language: javascript


Alerting interface for ETSI NFV-SOL 002/003 based Fault Management
==================================================================

.. rest_method::  POST /alert

Alert Tacker when one or more Fault event are obtained.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 204

.. rest_status_code:: error status.yaml

  - 400
  - 404: prometheus_plugin_fm

Request Parameters
------------------

.. rest_parameters:: parameters_prometheus_plugin.yaml

  - alerts: alerts
  - status: status
  - labels: labels
  - receiver_type: receiver_type
  - function_type: function_type_fm
  - vnf_instance_id: vnf_instance_id
  - pod: pod
  - perceived_severity: perceived_severity
  - event_type: event_type
  - annotations: annotations
  - probable_cause: probable_cause
  - fault_type: fault_type
  - fault_details: fault_details
  - startsAt: startsAt
  - endsAt: endsAt
  - fingerprint: fingerprint

Request Example
---------------

.. literalinclude:: samples/prometheus_plugin/alert_fm.json
   :language: javascript

Alerting interface for Prometheus Plugin AutoScaling
====================================================

.. rest_method::  POST /alert/auto_scaling

Alert Tacker when scaling should be performed.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 204

.. rest_status_code:: error status.yaml

  - 400
  - 404: prometheus_plugin_auto_scale

Request Parameters
------------------

.. rest_parameters:: parameters_prometheus_plugin.yaml

  - alerts: alerts
  - status: status
  - labels: labels
  - receiver_type: receiver_type
  - function_type: function_type_auto_scale
  - vnf_instance_id: vnf_instance_id
  - auto_scale_type: auto_scale_type
  - aspect_id: aspect_id
  - annotations: annotations
  - startsAt: startsAt
  - endsAt: endsAt
  - fingerprint: fingerprint

Request Example
---------------

.. literalinclude:: samples/prometheus_plugin/alert_auto_scale.json
   :language: javascript

Alerting interface for Prometheus Plugin AutoHealing
====================================================

.. rest_method::  POST /alert/auto_healing

Alert Tacker when healing should be performed.

This interface can be alerted by multiple times in a short period.
To prevent invoking multiple heal operations to single VNF,
the multiple requests by this interface are packed for
a configured period of time (CONF.prometheus_plugin.timer_interval).

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 204

.. rest_status_code:: error status.yaml

  - 400
  - 404: prometheus_plugin_auto_heal

Request Parameters
------------------

.. rest_parameters:: parameters_prometheus_plugin.yaml

  - alerts: alerts
  - status: status
  - labels: labels
  - receiver_type: receiver_type
  - function_type: function_type_auto_heal
  - vnf_instance_id: vnf_instance_id
  - vnfc_info_id: vnfc_info_id
  - annotations: annotations
  - startsAt: startsAt
  - endsAt: endsAt
  - fingerprint: fingerprint

Request Example
---------------

.. literalinclude:: samples/prometheus_plugin/alert_auto_heal.json
   :language: javascript
