================================
Prometheus Plugin Use Case Guide
================================

Overview
~~~~~~~~

This document describes about Prometheus Plugin that provides
monitoring functions in combination with External Monitoring Tool.

The Prometheus Plugin has 5 functions:

- Alerting function for ETSI NFV-SOL 002/003 based Performance Management Job.
- Alerting function for ETSI NFV-SOL 002/003 based Performance Management
  Threshold.
- Alerting function for ETSI NFV-SOL 002/003 based Fault Management.
- Alerting function for Prometheus Plugin AutoScaling.
- Alerting function for Prometheus Plugin AutoHealing.

The Prometheus Plugin works in conjunction with the External Monitoring
Tool. External Monitoring Tool is a monitoring service based on Prometheus.
When External Monitoring Tool detects an alerting event on CNF/VNF,
External Monitoring Tool sends an alert to Prometheus Plugin.

.. note::

  Performance Management and Fault Management support only CNF.
  AutoScaling and AutoHealing support both CNF and VNF.


The External Monitoring Tool is implemented by each operators,
thus it is not included in Tacker.


Configuration
~~~~~~~~~~~~~

Prometheus Plugin is disabled by default.
It can be enabled by configuration file (e.g. /etc/tacker/tacker.conf).
To enable Prometheus Plugin, be sure to set true for
performance_management, fault_management, auto_scaling or auto_healing below.

.. list-table::
  :header-rows: 1
  :widths: 20 10 40

  * - Configuration (CONF.prometheus_plugin)
    - Default
    - Description
  * - ``performance_management``
    - false
    - Enable prometheus plugin performance management.
  * - ``reporting_period_margin``
    - 1
    - Some margin time for PM jos's reportingPeriod.
      When multiple alerts are received within a time period
      shorter than (reportingPeriod - reporting_period_margin),
      the subsequent alerts are ignored.
  * - ``fault_management``
    - false
    - Enable prometheus plugin fault management.
  * - ``auto_scaling``
    - false
    - Enable prometheus plugin autoscaling.
  * - ``auto_healing``
    - false
    - Enable prometheus plugin autohealing.
  * - ``timer_interval``
    - 20
    - When multiple auto heal alerts for a VNF instance are
      notified in the ``timer_interval`` seconds,
      Tacker packs these notifications into single event.
      By doing this, Tacker can avoid making too many healing requests.
  * - ``test_rule_with_promtool``
    - false
    - Enable rule file validation using promtool.
  * - ``reporting_period_threshold``
    - 90
    - The time of reportingPeriod for the pm threshold.
  * - ``collection_period_threshold``
    - 30
    - The time of collectionPeriod for the pm threshold.


Prerequisite
------------

There is another prerequisite for using the AutoScaling/AutoHealing
function.
When instantiate VNF, you need to add the parameter
``isAutoscaleEnabled/isAutohealEnabled`` to ``true`` in the request body.

The example reference is as follows:

.. code-block:: console

  {
    "flavourId": "dummy",
    "vimConnectionInfo": {
      ...
    },
    "additionalParams": {
      ...
    },
    "vnfConfigurableProperties": {
      "isAutoscaleEnabled": true
    }
  }


System
~~~~~~

Prometheus Plugin needs external service called External
Monitoring Tool.

Prometheus Plugin operates the External Monitoring Tool
along the Performance Management, Fault Management, AutoScaling or
AutoHealing.
The flow of each process is as follows.

- ``ETSI NFV-SOL 002/003 based Performance Management Job``

  .. code-block:: console

                                      +---------------------------------+
                                      | Client (NFVO/EM)                |
                                      | 8. Perform scaling if necessary <--+
                                      +----+----------------------------+  |
                                           | 1.Create PM job               | 7. Notify PM event
                                      +----v-------------------------------+---------------+
                                      |                                             Tacker |
    +-------------+                   | +------------------------------------------------+ |
    |  External   | 3. Set alert rule | | Prometheus Plugin                              | |
    |  Monitoring <-------------------+ | 2. Convert PM job to Prometheus Alert Rule     | |
    |  Tool       | 5. Send alert     | |                                                | |
    |             +-------------------> | 6. Convert Prometheus Alert event to PM event  | |
    |             |                   | +------------------------------------------------+ |
    +--+----------+                   +----------------------------------------------------+
       | 4. Performance
       |    monitoring                +----------------------------------------------------+
       |                              |                                           CISM/CIS |
       |                              | +------------+   +------------+   +------------+   |
       +------------------------------> | CNF        |   | CNF        |   | CNF        |   |
                                      | +------------+   +------------+   +------------+   |
                                      +----------------------------------------------------+


- ``ETSI NFV-SOL 002/003 based Performance Management Threshold``

  .. code-block:: console

                                      +---------------------------------+
                                      | Client (NFVO/EM)                |
                                      | 8. Perform scaling if necessary <--+
                                      +----+----------------------------+  |
                                           | 1.Create PM threshold         | 7. Notify threshold state
                                      +----v-------------------------------+---------------------+
                                      |                                                   Tacker |
    +-------------+                   | +------------------------------------------------------+ |
    |  External   | 3. Set alert rule | | Prometheus Plugin                                    | |
    |  Monitoring <-------------------+ | 2. Convert PM threshold to Prometheus Alert Rule     | |
    |  Tool       | 5. Send alert     | |                                                      | |
    |             +-------------------> | 6. Convert Prometheus Alert event to threshold state | |
    |             |                   | +------------------------------------------------------+ |
    +--+----------+                   +----------------------------------------------------------+
       | 4. Performance
       |    monitoring                +----------------------------------------------------------+
       |                              |                                                 CISM/CIS |
       |                              | +------------+     +------------+     +------------+     |
       +------------------------------> | CNF        |     | CNF        |     | CNF        |     |
                                      | +------------+     +------------+     +------------+     |
                                      +----------------------------------------------------------+


- ``ETSI NFV-SOL 002/003 based Fault Management``

  .. code-block:: console

                                     +---------------------------------+
                                     | Client (NFVO/EM)                |
        +----------------------------+ 7. Perform healing if necessary <--+
        | 2. Set alert rule          +----+----------------------------+  |
        |                                 | 1. Subscribe FM alarms        | 6. Notify FM alarm
        |                            +----v-------------------------------+---------------+
        |                            |                                             Tacker |
    +---v---------+                  | +------------------------------------------------+ |
    |  External   | 4. Send alert    | | Prometheus Plugin                              | |
    |  Monitoring +------------------> | 5. Convert Prometheus Alert event to FM alarm  | |
    |  Tool       |                  | +------------------------------------------------+ |
    +--+----------+                  +----------------------------------------------------+
       | 3. Fault
       |    monitoring               +----------------------------------------------------+
       |                             |                                           CISM/CIS |
       |                             | +------------+   +------------+   +------------+   |
       +-----------------------------> | CNF        |   | CNF        |   | CNF        |   |
                                     | +------------+   +------------+   +------------+   |
                                     +----------------------------------------------------+


- ``Prometheus Plugin AutoScaling``

  .. code-block:: console

                                     +--------------------------+
        +----------------------------+   Client (NFVO/EM)       |
        | 1. Set alert rule          +--------------------------+
        |
        |                            +----------------------------------------------------+
        |                            |                                             Tacker |
    +---v---------+                  | +------------------------------------------------+ |
    |  External   | 3. Send alert    | | Prometheus Plugin                              | |
    |  Monitoring +------------------> | 4. Perform scaling                             | |
    |  Tool       |                  | +------------------------------------------------+ |
    +--+----------+                  +-----------------------+----------------------------+
       | 2. Scaling event                                    |  5. Delete or Create pods/VMs
       |    monitoring               +-----------------------|----------------------------+
       |                             |           +-----------+--------------+    CISM/VIM |
       |                             | +---------v--+   +----v-------+   +--v---------+   |
       +-----------------------------> | CNF/VNF    |   | CNF/VNF    |   | CNF/VNF    |   |
                                     | +------------+   +------------+   +------------+   |
                                     +----------------------------------------------------+


- ``Prometheus Plugin AutoHealing``

  .. code-block:: console

                                     +--------------------------+
        +----------------------------+   Client (NFVO/EM)       |
        | 1. Set alert rule          +--------------------------+
        |
        |                            +----------------------------------------------------+
        |                            |                                             Tacker |
    +---v---------+                  | +------------------------------------------------+ |
    |  External   | 3. Send alert    | | Prometheus Plugin                              | |
    |  Monitoring +------------------> | 4. Perform healing                             | |
    |  Tool       |                  | +------------------------------------------------+ |
    +--+----------+                  +-----------------------+----------------------------+
       | 2. Healing event                                    |  5. Delete and Create pods/VMs
       |    monitoring               +-----------------------|----------------------------+
       |                             |           +-----------+--------------+    CISM/VIM |
       |                             | +---------v--+   +----v-------+   +--v---------+   |
       +-----------------------------> | CNF/VNF    |   | CNF/VNF    |   | CNF/VNF    |   |
                                     | +------------+   +------------+   +------------+   |
                                     +----------------------------------------------------+


External Monitoring Tool
~~~~~~~~~~~~~~~~~~~~~~~~

External Monitoring Tool is consist of Prometheus Server,
Alertmanager and SSH Server.

This section describes the requirements for each service.


Prometheus Server
-----------------

Prometheus Server needs config to scrape kubernetes information.
For example:

.. code-block:: yaml

    global:
      scrape_interval: 30s
      evaluation_interval: 30s

    rule_files:
    - /etc/prometheus/rules/*

    alerting:
      alertmanagers:
      - static_configs:
        - targets:
          - <alertmanager_host>

    scrape_configs:
    - job_name: "kubestatemetrics"
      static_configs:
      - targets: ["<kube-state-metrics exporter host>"]
    - job_name: "k8smetricsresourceworker1"
      static_configs:
      - targets: ["<worker1 exporter host>"]
      metrics_path: "/api/v1/nodes/worker1/proxy/metrics/resource"
    - job_name: "k8smetricscadvisorworker1"
        static_configs:
        - targets: ["<worker1 exporter host>"]
        metrics_path: "/api/v1/nodes/worker1/proxy/metrics/cadvisor"


Alert Manager
-------------

Alert manager needs to setup to send alert to Tacker.
For example:

.. code-block:: yaml

    global:

    route:
      group_by:
        - "kubestatemetrics"
        - "k8smetricsresourceworker1"
        - "k8smetricscadvisorworker1"
      group_wait: 30s
      group_interval: 30s
      repeat_interval: 30s
      receiver: default-receiver
      routes:
      - matchers:
        - function_type = vnfpm
        receiver: vnfpm
      - matchers:
        - function_type = vnfpm_threshold
        receiver: vnfpm-threshold
      - matchers:
        - function_type = vnffm
        receiver: vnffm
      - matchers:
        - function_type = auto_scale
        receiver: auto-scale
      - matchers:
        - function_type = auto_heal
        receiver: auto-heal

    receivers:
    - name: default-receiver
    - name: vnfpm
      webhook_configs:
      - url: "http://<tacker_host>/pm_event"
    - name: vnfpm-threshold
      webhook_configs:
      - url: "http://<tacker_host>/pm_threshold"
    - name: vnffm
      webhook_configs:
      - url: "http://<tacker_host>/alert"
    - name: auto-scale
      webhook_configs:
      - url: "http://<tacker_host>/alert/auto_scaling"
    - name: auto-heal
      webhook_configs:
      - url: "http://<tacker_host>/alert/auto_healing"


SSH server
----------

Tacker sends alert rule file via SSH. So External Monitoring Tool
needs to activate sshd.

- PasswordAuthentication setting should be "yes".
- The directory indicated by "rule_files" setting of prometheus
  server config should be accessible by SSH.


Supported versions
------------------

Tacker Zed release

- Prometheus: 2.37
- Alertmanager: 0.24

Tacker Antelope release

- Prometheus: 2.37
- Alertmanager: 0.25

Tacker Bobcat and Caracal release

- Prometheus: 2.45
- Alertmanager: 0.26


Alert rule registration
~~~~~~~~~~~~~~~~~~~~~~~

ETSI NFV-SOL 002/003 based Performance Management Job
-----------------------------------------------------

Registration of alerting rule is performed through
PM job creation. Below is an example of request body
of PM job creation.

Access information of External Monitoring Tool must be set
at "metadata" field.

.. code-block:: json

  {
      "objectType": "Vnf",
      "objectInstanceIds": ["a0205e7c-fdeb-4f6c-b266-962246e32626"],
      "criteria": {
          "performanceMetric": ["VMemoryUsageMeanVnf.a0205e7c-fdeb-4f6c-b266-962246e32626"],
          "performanceMetricGroup": [],
          "collectionPeriod": 30,
          "reportingPeriod": 60
      },
      "callbackUri": "http://127.0.0.1:9990/notification/callbackuri/a0205e7c-fdeb-4f6c-b266-962246e32626",
      "metadata": {
          "monitoring": {
              "monitorName": "prometheus",
              "driverType": "external",
              "targetsInfo": [
                  {
                      "prometheusHost": "192.168.121.35",
                      "prometheusHostPort": 22,
                      "authInfo": {
                          "ssh_username": "vagrant",
                          "ssh_password": "vagrant"
                      },
                      "alertRuleConfigPath":
                          "/etc/prometheus/rules",
                      "prometheusReloadApiEndpoint":
                          "http://192.168.121.35:9090/-/reload"
                  }
              ]
          }
      }
  }


.. note::

  With the parameter, pod name can be specified but container name can not.
  And some prometheus metrics need container name. Therefore, ``max``
  statement of PromQL is alternatively used in some measurements to
  measure without container name. That means it provides only most
  impacted value among the containers. For example:

  ``avg(max(container_fs_usage_bytes{pod=~"pod name"} /
  container_fs_limit_bytes{pod=~"pod name"}))``


ETSI NFV-SOL 002/003 based Performance Management Threshold
-----------------------------------------------------------

Registration of alerting rule is performed through
PM threshold creation. Below is an example of request body
of PM threshold creation.

Access information of External Monitoring Tool must be set
at "metadata" field.

.. code-block:: json

  {
      "objectType": "Vnf",
      "objectInstanceId": "c21fd71b-2866-45f6-89d0-70c458a5c32e",
      "criteria": {
          "performanceMetric": "VMemoryUsageMeanVnf.c21fd71b-2866-45f6-89d0-70c458a5c32e",
          "thresholdType": "SIMPLE",
          "simpleThresholdDetails": {
              "thresholdValue": 1,
              "hysteresis": 0.5
          }
      },
      "callbackUri": "http://127.0.0.1:9990/notification/callbackuri/c21fd71b-2866-45f6-89d0-70c458a5c32e",
      "metadata": {
          "monitoring": {
              "monitorName": "prometheus",
              "driverType": "external",
              "targetsInfo": [
                  {
                      "prometheusHost": "192.168.121.35",
                      "prometheusHostPort": 22,
                      "authInfo": {
                          "ssh_username": "vagrant",
                          "ssh_password": "vagrant"
                      },
                      "alertRuleConfigPath":
                          "/etc/prometheus/rules",
                      "prometheusReloadApiEndpoint":
                          "http://192.168.121.35:9090/-/reload"
                  }
              ]
          }
      }
  }


.. note::

  With the parameter, pod name can be specified but container name can not.
  And some prometheus metrics need container name. Therefore, ``max``
  statement of PromQL is alternatively used in some measurements to
  measure without container name. That means it provides only most
  impacted value among the containers. For example:

  ``avg(max(container_fs_usage_bytes{pod=~"pod name"} /
  container_fs_limit_bytes{pod=~"pod name"}))``


ETSI NFV-SOL 002/003 based Fault Management
-------------------------------------------

Registration of alerting rule is performed by updating
rule file directly. Below is an example of alert rule.

.. code-block:: json

  {
      "groups": [{
          "name": "fm_test",
          "rules": [{
              "alert": "fm_test",
              "expr": "max(sum(rate(pod_cpu_usage_seconds_total{pod='curry-probe-test001-798d577c96-5624p'}[1m]))) > 0.1",
              "for": "30s",
              "labels": {
                  "receiver_type": "tacker",
                  "function_type": "vnffm",
                  "vnf_instance_id": "c21fd71b-2866-45f6-89d0-70c458a5c32e",
                  "pod": "curry-probe-test001-798d577c96-5624p",
                  "perceived_severity": "CRITICAL",
                  "event_type": "PROCESSING_ERROR_ALARM"
              },
              "annotations": {
                  "probable_cause": "Process Terminated",
                  "fault_type": "fault_type",
                  "fault_details": "fault_details"
              }
          }]
      }]
  }


Prometheus Plugin AutoScaling
-----------------------------

Registration of alerting rule is performed by updating
rule file directly. Below is an example of alert rule.

.. code-block:: json

  {
      "groups": [{
          "name": "scale_out_test",
          "rules": [{
              "alert": "scale_out_test",
              "expr": "max(sum(rate(pod_cpu_usage_seconds_total{pod='curry-probe-test001-798d577c96-8qtg2'}[1m]))) > 0.1",
              "for": "30s",
              "labels": {
                  "receiver_type": "tacker",
                  "function_type": "auto_scale",
                  "vnf_instance_id": "fa82d5bf-c6c1-4ece-bf16-9cf9325a171a",
                  "auto_scale_type": "SCALE_OUT",
                  "aspect_id": "vdu1_aspect"
              }
          }]
      }]
  }


Prometheus Plugin AutoHealing
-----------------------------

Registration of alerting rule is performed by updating
rule file directly. Below is example of alert rule.

.. code-block:: json

  {
      "groups": [{
          "name": "heal_all_test_1",
          "rules": [{
              "alert": "heal_all_test_1",
              "expr": "max(sum(rate(pod_cpu_usage_seconds_total{pod='curry-probe-test001-798d577c96-dc5rh'}[1m]))) > 0.1",
              "for": "30s",
              "labels": {
                  "receiver_type": "tacker",
                  "function_type": "auto_heal",
                  "vnf_instance_id": "c44e89ad-6743-4b80-8df8-fe4aa4d83f44",
                  "vnfc_info_id": "VDU1-curry-probe-test001-798d577c96-dc5rh"
              }
          }]
      }]
  }


External data file
~~~~~~~~~~~~~~~~~~

The PromQL statement data for Performance Management
is able to customize with external data file. The operators can use the
original PromQL statement with this file.

The external data file includes configuration about PromQL statement for
Performance Management. The template of the file is located
at etc/tacker/prometheus-plugin.yaml from the tacker project source directory.
Edit this file if you need and put it in the configuration directory
(e.g. /etc/tacker).


Default configuration file
--------------------------

Normally, the default external data file is automatically deployed at the
installation process. However if you need to deploy the file manually,
execute below command at the top directory of tacker project.

.. code-block:: console

  sudo python3 ./setup.py install


Data format
-----------

The file is described in yaml format.


Root configuration
------------------

The configuration consists of PromQL config for PMJob API and
PromQL config for Threshold API. The PMJob and the Threshold are
defined in `ETSI GS NFV-SOL 003`_.

.. code-block:: yaml

  # PromQL config for PM Job API
  PMJob:
    PromQL: <PromQLConfig>
  # PromQL config for Threshold API
  Threshold:
    PromQL: <PromQLConfig>


<PromQLConfig>
--------------

The elements of PromQLConfig are key-value pairs of a performanceMetric
and a PromQL statement. These performanceMetric are defined in
`ETSI GS NFV-SOL 003`_.

.. code-block:: yaml

  <PromQLConfig>
    VCpuUsageMeanVnf: <F-string of PromQL statement>
    VCpuUsagePeakVnf: <F-string of PromQL statement>
    VMemoryUsageMeanVnf: <F-string of PromQL statement>
    VMemoryUsagePeakVnf: <F-string of PromQL statement>
    VDiskUsageMeanVnf: <F-string of PromQL statement>
    VDiskUsagePeakVnf: <F-string of PromQL statement>
    ByteIncomingVnfIntCp: <F-string of PromQL statement>
    PacketIncomingVnfIntCp: <F-string of PromQL statement>
    ByteOutgoingVnfIntCp: <F-string of PromQL statement>
    PacketOutgoingVnfIntCp: <F-string of PromQL statement>
    ByteIncomingVnfExtCp: <F-string of PromQL statement>
    PacketIncomingVnfExtCp: <F-string of PromQL statement>
    ByteOutgoingVnfExtCp: <F-string of PromQL statement>
    PacketOutgoingVnfExtCp: <F-string of PromQL statement>


For example, VCpuUsageMeanVnf can be described as below.

.. code-block:: yaml

  VCpuUsageMeanVnf: >-
    avg(sum(rate(pod_cpu_usage_seconds_total
    {{namespace="{namespace}",pod=~"{pod}"}}[{reporting_period}s])))


F-string of PromQL statement
----------------------------

For above PromQL statement, `f-string`_ of python is used.
In the f-string, below replacement field can be used. They are replaced
with a SOL-API's attribute(`ETSI GS NFV-SOL 003`_) or Tacker internal value.

``{collection_period}``
   Replaced with collectionPeriod attribute of SOL-API.
``{pod}``
   Replaced with a resourceId when subObjectInstanceIds are specified
   (e.g: "test-test1-8d6db447f-stzhb").
   Or, replaced with regexp that matches each resourceIds in vnfInstance when
   subObjectInstanceIds are not specified
   (e.g: "(test-test1-[0-9a-f]{1,10}-[0-9a-z]{5}$|
   test-test2-[0-9a-f]{1,10}-[0-9a-z]{5}$)").
``{reporting_period}``
   Replaced with reportingPeriod attribute of SOL-API.
``{sub_object_instance_id}``
   Replaced with an element of subObjectInstanceIds of SOL-API.
``{namespace}``
   Replaced with the kubernetes namespace that the vnfInstance belongs to.


Using Vendor Specific Plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prometheus Plugin can be replaced with a vendor specific function.
To replace a plugin, change the configurations below.
The replaced class must be a subclass of
tacker.sol_refactored.common.monitoring_plugin_base.MonitoringPlugin.

.. list-table::
  :header-rows: 1
  :widths: 40 40 40

  * - Configuration (CONF.prometheus_plugin)
    - Default
    - Description
  * - ``performance_management_package``
    - | tacker.sol_refactored.common
      | .prometheus_plugin
    - Package name for performance management job.
  * - | ``performance_management``
      | ``_threshold_package``
    - | tacker.sol_refactored.common
      | .prometheus_plugin
    - Package name for performance management threshold.
  * - ``performance_management_class``
    - PrometheusPluginPm
    - Class name for performance management job.
  * - | ``performance_management``
      | ``_threshold_class``
    - PrometheusPluginThreshold
    - Class name for performance management threshold.
  * - ``fault_management_package``
    - | tacker.sol_refactored.common
      | .prometheus_plugin
    - Package name for fault management.
  * - ``fault_management_class``
    - PrometheusPluginFm
    - Class name for fault management.
  * - ``auto_scaling_package``
    - | tacker.sol_refactored.common
      | .prometheus_plugin
    - Package name for auto scaling.
  * - ``auto_scaling_class``
    - PrometheusPluginAutoScaling
    - Class name for auto scaling.
  * - ``auto_healing_package``
    - | tacker.sol_refactored.common
      | .prometheus_plugin
    - Package name for auto healing.
  * - ``auto_healing_class``
    - PrometheusPluginAutoHealing
    - Class name for auto healing.


History of Checks
-----------------

The content of this document has been confirmed to work
using Prometheus 2.45 and Alertmanager 0.26.


.. _ETSI GS NFV-SOL 003:
  https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/003/03.03.01_60/gs_nfv-sol003v030301p.pdf
.. _f-string: https://docs.python.org/3.11/tutorial/inputoutput.html#fancier-output-formatting
