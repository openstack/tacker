================================
Prometheus Plugin Use Case Guide
================================

Overview
~~~~~~~~

This document describes about Prometheus Plugin that provides
monitoring functions in combination with External Monitoring Tool

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
  * - ``CONF.prometheus_plugin.reporting_period_threshold``
    - 90
    - The time of reportingPeriod for the pm threshold.
  * - ``CONF.prometheus_plugin.collection_period_threshold``
    - 30
    - The time of collectionPeriod for the pm threshold.

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
          - function_type = vnfpm_threshold
          receiver: vnfpm-threshold
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
    - name: vnfpm-threshold
      webhook_configs:
      - url: "http://<tacker_host>/vnfpm_threshold"
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
        "objectInstanceIds": ["507280d8-bfc5-4b88-904b-9280ba6bc3ea"],
        "criteria": {
            "performanceMetric": [
                "VMemoryUsageMeanVnf.507280d8-bfc5-4b88-904b-9280ba6bc3ea"],
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
        "objectInstanceId": "511a2d68-c975-4913-b7b8-d75468e3102b",
        "criteria": {
            "performanceMetric": "VMemoryUsageMeanVnf.511a2d68-c975-4913-b7b8-d75468e3102b",
            "thresholdType": "SIMPLE",
            "simpleThresholdDetails": {
                "thresholdValue": 55,
                "hysteresis": 30
            }
        },
        "callbackUri": "<client_callback_uri>",
        "metadata": {
            "monitoring": {
                "monitorName": "prometheus",
                "driverType": "external",
                "targetsInfo": [
                    {
                        "prometheusHost": "<prometheus_server_hostname>",
                        "prometheusHostPort": 22,
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
    measure without container name. That means it provides only most
    impacted value among the containers. For example:

    ``avg(max(container_fs_usage_bytes{pod=~"pod name"} /
    container_fs_limit_bytes{pod=~"pod name"}))``

ETSI NFV-SOL 002/003 based Fault Management
-------------------------------------------

Registration of alerting rule is performed by updating
rule file directly. Below is an example of alert rule.

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
rule file directly. Below is an example of alert rule.

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

The file is described in yaml format [#yaml]_.

Root configuration
------------------

The configuration consists of PromQL config for PMJob API and
PromQL config for Threshold API. The PMJob and the Threshold are
defined in ETSI GS NFV-SOL 003 [#etsi_sol_003]_.

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
ETSI GS NFV-SOL 003 [#etsi_sol_003]_.

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

For above PromQL statement, f-string of python [#f_string]_ is used.
In the f-string, below replacement field can be used. They are replaced
with a SOL-API's attribute [#etsi_sol_003]_ or Tacker internal value.

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

  * - Configuration
    - Default
    - Description
  * - ``CONF.prometheus_plugin.performance_management_package``
    - tacker.sol_refactored.common.prometheus_plugin
    - Package name for performance management job.
  * - ``CONF.prometheus_plugin.performance_management_threshold_package``
    - tacker.sol_refactored.common.prometheus_plugin
    - Package name for performance management threshold.
  * - ``CONF.prometheus_plugin.performance_management_class``
    - PrometheusPluginPm
    - Class name for performance management job.
  * - ``CONF.prometheus_plugin.performance_management_threshold_class``
    - PrometheusPluginThreshold
    - Class name for performance management threshold.
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

.. rubric:: Footnotes
.. [#yaml] https://yaml.org/spec/1.2-old/spec.html
.. [#etsi_sol_003] https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/003/03.03.01_60/gs_nfv-sol003v030301p.pdf
.. [#f_string] https://docs.python.org/3.9/tutorial/inputoutput.html#fancier-output-formatting
