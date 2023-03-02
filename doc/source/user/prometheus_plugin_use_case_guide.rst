================================
Prometheus Plugin Use Case Guide
================================

Overview
~~~~~~~~

This document describes about Prometheus Plugin that provides
monitoring functions in combination with External Monitoring Tool

The Prometheus Plugin has 4 functions:

- Alerting function for ETSI NFV-SOL 002/003 based Performance Management.
- Alerting function for ETSI NFV-SOL 002/003 based Fault Management.
- Alerting function for Prometheus Plugin AutoScaling.
- Alerting function for Prometheus Plugin AutoHealing.

The Prometheus Plugin works in conjunction with the External Monitoring
Tool. External Monitoring Tool is a monitoring service based on Prometheus.
When External Monitoring Tool detects an alerting event on CNF/VNF,
External Monitoring Tool sends an alert to Prometheus Plugin.

.. note::

    PM/FM only support CNF.

    AutoScale/Heal support both CNF and VNF.

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

  * - Configuration
    - Default
    - Description
  * - ``CONF.prometheus_plugin.performance_management``
    - false
    - Enable prometheus plugin performance management.
  * - ``CONF.prometheus_plugin.reporting_period_margin``
    - 1
    - Some margin time for PM jos's reportingPeriod.
      When multiple alerts are received within a time period
      shorter than (reportingPeriod - reporting_period_margin),
      the subsequent alerts are ignored.
  * - ``CONF.prometheus_plugin.fault_management``
    - false
    - Enable prometheus plugin fault management.
  * - ``CONF.prometheus_plugin.auto_scaling``
    - false
    - Enable prometheus plugin autoscaling.
  * - ``CONF.prometheus_plugin.auto_healing``
    - false
    - Enable prometheus plugin autohealing.
  * - ``CONF.prometheus_plugin.timer_interval``
    - 20
    - When multiple auto heal alerts for a VNF instance are
      notified in the ``timer_interval`` seconds,
      Tacker packs these notifications into single event.
      By doing this, Tacker can avoid making too many healing requests.
  * - ``CONF.prometheus_plugin.test_rule_with_promtool``
    - false
    - Enable rule file validation using promtool.

Prerequisite
------------

There is another prerequisite for using the AutoScale/Heal function.
When instantiate VNF, you need to add the parameter
``isAutoscaleEnabled/isAutohealEnabled`` to ``True`` in the request body.

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
      "isAutoscaleEnabled": True
    }
  }

System
~~~~~~

Prometheus Plugin needs external service called External
Monitoring Tool.

Prometheus Plugin operates the External Monitoring Tool
along the Performance Management, Fault Management, Auto scaling or
Auto healing.
The flow of each process is as follows.

- ``ETSI NFV-SOL 002/003 based Performance Management``

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
AlertManager and SSH Server.

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
        - /etc/prometheus/rules/*.json

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
    - job_name: "k8smetricsresourceworker2"
        static_configs:
        - targets: ["<worker2 exporter host>"]
        metrics_path: "/api/v1/nodes/worker2/proxy/metrics/resource"
    - job_name: "k8smetricscadvisorworker2"
        static_configs:
        - targets: ["<worker2 exporter host>"]
        metrics_path: "/api/v1/nodes/worker2/proxy/metrics/cadvisor"

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
        - "k8smetricsresourceworker2"
        - "k8smetricscadvisorworker2"
      group_wait: 30s
      group_interval: 30s
      repeat_interval: 30s
      receiver: default-receiver
      routes:
        - matchers:
          - function_type = vnfpm
          receiver: vnfpm
        - matchers:
          - function_type = vnffm
          receiver: vnffm
        - matchers:
          - function_type = auto-scale
          receiver: auto-scale
        - matchers:
          - function_type = auto-heal
          receiver: auto-heal

    receivers:
    - name: default-receiver
    - name: vnfpm
      webhook_configs:
      - url: "http://<tacker_host>/pm_event"
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

Alert rule registration
~~~~~~~~~~~~~~~~~~~~~~~

ETSI NFV-SOL 002/003 based Performance Management
--------------------------------------------------

Registration of alerting rule is performed through
PM job creation. Below is example of request body
of PM job creation.

Access information of External Monitoring Tool must be set
at "metadata" field.

.. code-block:: json

    {
        "objectType": "Vnf",
        "objectInstanceIds": ["507280d8-bfc5-4b88-904b-9280ba6bc3ea"],
        "criteria": {
            "performanceMetric": [
                "VCpuUsageMeanVnf.507280d8-bfc5-4b88-904b-9280ba6bc3ea"],
            "collectionPeriod": 30,
            "reportingPeriod": 90,
            "reportingBoundary": "2099-08-05T02:24:46Z"
        },
        "callbackUri": "<client_callback_uri>",
        "metadata": {
            "monitoring": {
                "monitorName": "prometheus",
                "driverType": "external",
                "targetsInfo": [
                    {
                        "prometheusHost": "<prometheus_server_hostname>",
                        "authInfo": {
                            "ssh_username": "ubuntu",
                            "ssh_password": "ubuntu"
                        },
                        "alertRuleConfigPath":
                            "/etc/prometheus/rules",
                        "prometheusReloadApiEndpoint":
                            "http://<prometheus_server_hostname>/-/reload"
                    }
                ]
            }
        }
    }

.. note::

    With the parameter, pod name can be specified but container name can not.
    And some prometheus metrics need container name. Therefore, ``max``
    statement of PromQL is alternatively used in some measurements to
    measure without container name. That means it provids only most
    impacted value among the containers. For example:

    ``avg(max(container_fs_usage_bytes{pod=~"pod name"} /
    container_fs_limit_bytes{pod=~"pod name"}))``

ETSI NFV-SOL 002/003 based Fault Management
-------------------------------------------

Registration of alerting rule is performed by updating
rule file directly. Below is example of alert rule.

.. code-block:: yaml

  groups:
    - name: example
      rules:
      - alert: Test
        expr: sum(pod_memory_working_set_bytes{namespace="default"}) > 10000000000
        for: 30s
        labels:
          receiver_type: tacker
          function_type: vnffm
          vnf_instance_id: 3721ab69-3f33-44bc-85f1-f416ad1b765e
          pod: test\\-test1\\-[0-9a-f]{1,10}-[0-9a-z]{5}$
          perceived_severity: CRITICAL
          event_type: PROCESSING_ERROR_ALARM
        annotations:
          probable_cause: Server is down.
          fault_type: Error
          fault_details: Fault detail

Prometheus Plugin AutoScaling
-----------------------------

Registration of alerting rule is performed by updating
rule file directly. Below is example of alert rule.

.. code-block:: yaml

  groups:
    - name: example
      rules:
      - alert: Test
        expr: sum(pod_memory_working_set_bytes{namespace="default"}) > 10000000000
        for: 30s
        labels:
          receiver_type: tacker
          function_type: auto_scale
          vnf_instance_id: 3721ab69-3f33-44bc-85f1-f416ad1b765e
          auto_scale_type: SCALE_OUT
          aspect_id: VDU1_aspect
        annotations:

Prometheus Plugin AutoHealing
-----------------------------

Registration of alerting rule is performed by updating
rule file directly. Below is example of alert rule.

.. code-block:: yaml

  groups:
    - name: example
      rules:
      - alert: Test
        expr: sum(pod_memory_working_set_bytes{namespace="default"}) > 10000000000
        for: 30s
        labels:
          receiver_type: tacker
          function_type: auto_heal
          vnf_instance_id: 3721ab69-3f33-44bc-85f1-f416ad1b765e
          vnfc_info_id: VDU1-85adebfa-d71c-49ab-9d39-d8dd7e393541
        annotations:

Using Vendor Specific Plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prometheus Plugin can be replaced with a vendor specific function.
To replace a plugin, change the configurations below.
The replaced class must be a subclass of
tacker.sol_refactored.common.monitoring_plugin_base.MonitoringPlugin.

.. list-table::
  :header-rows: 1
  :widths: 40 40 40

  * - Configuration
    - Default
    - Description
  * - ``CONF.prometheus_plugin.performance_management_package``
    - tacker.sol_refactored.common.prometheus_plugin
    - Package name for performance management.
  * - ``CONF.prometheus_plugin.performance_management_class``
    - PrometheusPluginPm
    - Class name for performance management.
  * - ``CONF.prometheus_plugin.fault_management_package``
    - tacker.sol_refactored.common.prometheus_plugin
    - Package name for fault management.
  * - ``CONF.prometheus_plugin.fault_management_class``
    - PrometheusPluginFm
    - Class name for fault management.
  * - ``CONF.prometheus_plugin.auto_scaling_package``
    - tacker.sol_refactored.common.prometheus_plugin
    - Package name for auto scaling.
  * - ``CONF.prometheus_plugin.auto_scaling_class``
    - PrometheusPluginAutoScaling
    - Class name for auto scaling.
  * - ``CONF.prometheus_plugin.auto_healing_package``
    - tacker.sol_refactored.common.prometheus_plugin
    - Package name for auto healing.
  * - ``CONF.prometheus_plugin.auto_healing_class``
    - PrometheusPluginAutoHealing
    - Class name for auto healing.
