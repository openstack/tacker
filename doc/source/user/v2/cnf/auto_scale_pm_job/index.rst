===================================================================
ETSI NFV-SOL CNF Auto Scaling With Prometheus via PM Job Interfaces
===================================================================

This document describes how to auto scale CNF in Tacker v2 API with
Prometheus via Performance Management Job Interfaces.


Overview
--------

The diagram below shows an overview of the CNF auto scaling.

1. Create PM job

   The NFVO sends a request to the Tacker to create a PM job.

2. Set PM job

   Prometheus Plugin sets PM job to Prometheus.

3. Trigger event

   Prometheus collects metrics and decides whether triggering event is
   needed or not.

4. POST event

   Prometheus sends POST request to Tacker with specified URI. Tacker
   collects data related to the PM event.

5. Convert event to report

   Tacker receives informed event, converts it to report, and saves
   it to DB. Tacker also saves timestamp of the event.

6. Send report notification

   VnfPmDriverV2 finds all jobs in the DB and matches the report to
   job. If there is a job that can match successfully, the report is
   sent to the specified path of the NFVO. If the match is not successful,
   the processing ends.

7. Get PM report

   The NFVO make a request for the content of the report, then make a
   decision of scaling.

8. Scale

   Upon receiving a request to scale VNF from NFVO, tacker-server
   redirects it to tacker-conductor.

9. Call Kubernetes API

   In tacker-conductor, the request is redirected again to an
   appropriate infra-driver (in this case Kubernetes infra-driver)
   according to the contents of the instantiate parameters. Then,
   Kubernetes infra-driver calls Kubernetes APIs.

10. Change the number of Pods

    Kubernetes Cluster change the number of Pods according to the
    API calls.


.. figure:: img/auto_scale_pm_job.svg


Prerequisites
-------------

* The following packages should be installed:

  * tacker
  * python-tackerclient

  At least one VNF instance with status of ``INSTANTIATED`` is required.
  You can refer to :doc:`/user/v2/cnf/deployment/index` for the
  procedure to instantiate VNF.

  The VNF Package used can refer to `the sample`_.

* The following third-party services should be installed

  * NFVO
  * Prometheus(including Alertmanager)

  Each operator has its own NFVO, there is no restriction here, as long as
  it conforms to `ETSI NFV-SOL 002 v3.3.1`_ and `ETSI NFV-SOL 003 v3.3.1`_,
  it can be used.

  For the installation of Prometheus and Alertmanager, please refer to
  the `official website`_.

  .. note::

    Tacker reloads the Prometheus configuration by sending
    an HTTP POST request to the ``/-/reload`` endpoint.
    Therefore, the Prometheus needs the ``--web.enable-lifecycle`` flag
    to be enabled.
    Please see `Prometheus CONFIGURATION`_ for details.


How to configure Prometheus Plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Prometheus Plugin is disabled by default in Tacker.
For it to work, we need to find ``performance_management`` in
``tacker.conf`` and change its value to ``True``.

.. code-block:: console

  $ vi /etc/tacker/tacker.conf
  ...
  [prometheus_plugin]
  performance_management = True
  [v2_vnfm]
  # Enable https access to notification server from Tacker (boolean value)
  notification_verify_cert = true
  ...


After modifying the configuration file, don't forget to restart the
Tacker service to take effect.

.. code-block:: console

  $ sudo systemctl stop devstack@tacker
  $ sudo systemctl restart devstack@tacker-conductor
  $ sudo systemctl start devstack@tacker


How to create a PM job
~~~~~~~~~~~~~~~~~~~~~~

After having a CNF that can scale, we need to create a PM job. It
determines the monitoring metrics and monitoring resources to be
used by Prometheus.

.. note::

  When having an NFVO client, the request is sent by NFVO.


The interface for creating PM jobs is defined in both
`ETSI NFV-SOL 002 v3.3.1`_ and `ETSI NFV-SOL 003 v3.3.1`_.

The following are the parameters required by this interface.

.. list-table:: additional params
  :widths: 18 18 10 50
  :header-rows: 1

  * - Attribute name
    - Data type
    - Cardinality
    - Description
  * - objectType
    - String
    - 1
    - Type of the measured object. The applicable measured object type for a
      measurement is defined in clause 7.2 of `ETSI GS NFV-IFA 027`_.
  * - objectInstanceIds
    - Identifier
    - 1..N
    - Identifiers of the measured object instances for which performance
      information is requested to be collected.
  * - subObjectInstanceIds
    - IdentifierInVnf
    - 0..N
    - Identifiers of the measured object instances in case of a structured
      measured object.
  * - criteria
    - PmJobCriteria
    - 1
    - Criteria of the collection of performance information.
  * - performanceMetric
    - String
    - 0..N
    - This defines the types of performance metrics for the specified object
      instances. Valid values are specified as "Measurement Name" values in
      clause 7.2 of `ETSI GS NFV-IFA 027`_. At least one of the two
      attributes (performance metric or group) shall be present.
  * - performanceMetricGroup
    - String
    - 0..N
    - Group of performance metrics. A metric group is a pre-defined list of
      metrics, known to the API producer that it can decompose to individual
      metrics. Valid values are specified as "Measurement Group" values in
      clause 7.2 of `ETSI GS NFV-IFA 027`_. At least one of the two
      attributes (performance metric or group) shall be present.
  * - collectionPeriod
    - UnsignedInt
    - 1
    - Specifies the periodicity at which the API producer will collect
      performance information. The unit shall be seconds.
  * - reportingPeriod
    - UnsignedInt
    - 1
    - Specifies the periodicity at which the API producer will report to
      the API consumer. about performance information. The unit shall be
      seconds. The reportingPeriod should be equal to or a multiple of
      the collectionPeriod.
  * - reportingBoundary
    - DateTime
    - 0..1
    - Identifies a time boundary after which the reporting will stop. The
      boundary shall allow a single reporting as well as periodic reporting
      up to the boundary.
  * - callbackUri
    - Uri
    - 1
    - The URI of the endpoint to send the notification to.
  * - authentication
    - SubscriptionAuthentication
    - 0..1
    - Authentication parameters to configure the use of Authorization when
      sending notifications corresponding to this subscription. See as
      clause 8.3.4 of `ETSI GS NFV-SOL 013`_.
  * - metadata
    - Structure
    - 1
    - Additional parameters to create PM job.
  * - monitoring
    - Structure
    - 1
    - Treats to specify such as monitoring system and driver information.
  * - monitorName
    - String
    - 1
    - In case specifying “prometheus”, backend of monitoring feature is
      to be Prometheus.
  * - driverType
    - String
    - 1
    - “external”: SCP/SFTP for config file transfer.
  * - targetsInfo
    - Structure
    - 1..N
    - Information about the target monitoring system.
  * - prometheusHost
    - String
    - 1
    - FQDN or ip address of target PrometheusServer.
  * - prometheusHostPort
    - Int
    - 1
    - Port of the ssh target PrometheusServer.
  * - alertRuleConfigPath
    - String
    - 1
    - Path of alertRuleConfig path for target Prometheus.
  * - prometheusReloadApiEndpoint
    - String
    - 1
    - Endpoint url of reload API of target Prometheus.
  * - authInfo
    - Structure
    - 1
    - Define authentication information to access host.
  * - ssh_username
    - String
    - 1
    - The username of the target host for ssh.
  * - ssh_password
    - String
    - 1
    - The password of the target host for ssh.


.. note::

  * If ``subObjectInstanceIds`` is present, the cardinality of the
    ``objectInstanceIds`` attribute shall be 1.
  * ``performanceMetric`` and ``performanceMetricGroup``, at least one of
    the two attributes shall be present.
  * ``objectType`` has only the following values: ``Vnf``, ``Vnfc``,
    ``VnfIntCp``, ``VnfExtCp``.


Create PM job can be executed by the following CLI command.

.. code-block:: console

  $ openstack vnfpm job create sample_param_file.json --os-tacker-api-version 2


The content of the sample ``sample_param_file.json`` in this document is
as follows:

.. code-block:: json

  {
      "objectType": "Vnf",
      "objectInstanceIds": ["a0205e7c-fdeb-4f6c-b266-962246e32626"],
      "criteria": {
      "performanceMetric": ["VCpuUsageMeanVnf.a0205e7c-fdeb-4f6c-b266-962246e32626"],
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


Here is an example of create PM job:

.. code-block:: console

  $ openstack vnfpm job create sample_param_file.json --os-tacker-api-version 2
  +-------------------------+----------------------------------------------------------------------------------------------------------+
  | Field                   | Value                                                                                                    |
  +-------------------------+----------------------------------------------------------------------------------------------------------+
  | Callback Uri            | http://127.0.0.1:9990/notification/callbackuri/a0205e7c-fdeb-4f6c-b266-962246e32626                      |
  | Criteria                | {                                                                                                        |
  |                         |     "performanceMetric": [                                                                               |
  |                         |         "VCpuUsageMeanVnf.a0205e7c-fdeb-4f6c-b266-962246e32626"                                          |
  |                         |     ],                                                                                                   |
  |                         |     "collectionPeriod": 30,                                                                              |
  |                         |     "reportingPeriod": 60                                                                                |
  |                         | }                                                                                                        |
  | ID                      | 84b227dc-5ed0-411a-aff6-c830528eaec5                                                                     |
  | Links                   | {                                                                                                        |
  |                         |     "self": {                                                                                            |
  |                         |         "href": "http://127.0.0.1:9890/vnfpm/v2/pm_jobs/84b227dc-5ed0-411a-aff6-c830528eaec5"            |
  |                         |     },                                                                                                   |
  |                         |     "objects": [                                                                                         |
  |                         |         {                                                                                                |
  |                         |             "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/a0205e7c-fdeb-4f6c-b266-962246e32626" |
  |                         |         }                                                                                                |
  |                         |     ]                                                                                                    |
  |                         | }                                                                                                        |
  | Object Instance Ids     | [                                                                                                        |
  |                         |     "a0205e7c-fdeb-4f6c-b266-962246e32626"                                                               |
  |                         | ]                                                                                                        |
  | Object Type             | Vnf                                                                                                      |
  | Reports                 | []                                                                                                       |
  | Sub Object Instance Ids |                                                                                                          |
  +-------------------------+----------------------------------------------------------------------------------------------------------+


When creating a PM job, Tacker will modify the configuration file on the
specified Prometheus based on ``metadata``.
Then Prometheus will monitor the specified resource and send the monitored
information to Tacker.

The following is an example of the request body that Prometheus sends
information:

.. code-block:: json

  {
      "receiver": "receiver",
      "status": "firing",
      "alerts": [
          {
              "status": "firing",
              "labels": {
                  "receiver_type": "tacker",
                  "function_type": "vnfpm",
                  "job_id": "84b227dc-5ed0-411a-aff6-c830528eaec5",
                  "metric": "VCpuUsageMeanVnf.a0205e7c-fdeb-4f6c-b266-962246e32626",
                  "object_instance_id": "a0205e7c-fdeb-4f6c-b266-962246e32626"
              },
              "annotations": {
                  "value": 99
              },
              "startsAt": "2022-06-21T23:47:36.453Z",
              "endsAt": "0001-01-01T00:00:00Z",
              "generatorURL": "http://192.168.121.35:9090/graph?g0.expr=up%7Bjob%3D%22node%22%7D+%3D%3D+0&g0.tab=1",
              "fingerprint": "5ef77f1f8a3ecb8d"
          }
      ],
      "groupLabels": {},
      "commonLabels": {
          "alertname": "NodeInstanceDown",
          "job": "node"
      },
      "commonAnnotations": {
          "description": "sample"
      },
      "externalURL": "http://192.168.121.35:9093",
      "version": "4",
      "groupKey": "{}:{}",
      "truncatedAlerts": 0
  }


Tacker converts the received monitoring information into a report and
sends a notification request to NFVO.

The following is the request body of a sample notification request.

.. code-block:: json

  {
      "id": "29de3afc-0547-4f43-b921-1d6ceaf16bd4",
      "notificationType": "PerformanceInformationAvailableNotification",
      "timeStamp": "2023-11-20T14:25:04Z",
      "pmJobId": "84b227dc-5ed0-411a-aff6-c830528eaec5",
      "objectType": "Vnf",
      "objectInstanceId": "a0205e7c-fdeb-4f6c-b266-962246e32626",
      "_links": {
          "objectInstance": {
              "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/a0205e7c-fdeb-4f6c-b266-962246e32626"
          },
          "pmJob": {
              "href": "http://127.0.0.1:9890/vnfpm/v2/pm_jobs/84b227dc-5ed0-411a-aff6-c830528eaec5"
          },
          "performanceReport": {
              "href": "http://127.0.0.1:9890/vnfpm/v2/pm_jobs/84b227dc-5ed0-411a-aff6-c830528eaec5/reports/eab93857-eb72-49ce-9173-628a3f00ba2d"
          }
      }
  }


.. note::

  The target URL of this notification request is the ``Callback Uri``
  field in the PM job.


How does NFVO Auto Scale CNF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

NFVO will send a get PM report request to Tacker according to the URL
of the report in the notification request.

The response returned by Tacker is as follows:

.. code-block:: json

  {
      "entries": [{
          "objectType": "Vnf",
          "objectInstanceId": "a0205e7c-fdeb-4f6c-b266-962246e32626",
          "performanceMetric": "VCpuUsageMeanVnf.a0205e7c-fdeb-4f6c-b266-962246e32626",
          "performanceValues": [{
              "timeStamp": "2023-11-20T14:25:04Z",
              "value": "1.0002889206831795"
          }]
      }]
  }


NFVO will determine whether a scale operation is required based on
the report data. If needed, a scale request will be sent to Tacker.


How to use the CLI of PM interfaces
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a PM job
^^^^^^^^^^^^^^^

The creation of PM job has been introduced in the
`How to create a PM job`_ above, and the use case of the CLI
command can be referred to there.


Get all PM jobs
^^^^^^^^^^^^^^^

Get all PM jobs can be executed by the following CLI command.

.. code-block:: console

  $ openstack vnfpm job list --os-tacker-api-version 2


Here is an example of getting all PM jobs:

.. code-block:: console

  $ openstack vnfpm job list --os-tacker-api-version 2
  +--------------------------------------+-------------+----------------------------------------------------------------------------------------------------------+
  | Id                                   | Object Type | Links                                                                                                    |
  +--------------------------------------+-------------+----------------------------------------------------------------------------------------------------------+
  | 84b227dc-5ed0-411a-aff6-c830528eaec5 | Vnf         | {                                                                                                        |
  |                                      |             |     "self": {                                                                                            |
  |                                      |             |         "href": "http://127.0.0.1:9890/vnfpm/v2/pm_jobs/84b227dc-5ed0-411a-aff6-c830528eaec5"            |
  |                                      |             |     },                                                                                                   |
  |                                      |             |     "objects": [                                                                                         |
  |                                      |             |         {                                                                                                |
  |                                      |             |             "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/a0205e7c-fdeb-4f6c-b266-962246e32626" |
  |                                      |             |         }                                                                                                |
  |                                      |             |     ]                                                                                                    |
  |                                      |             | }                                                                                                        |
  +--------------------------------------+-------------+----------------------------------------------------------------------------------------------------------+


Get the specified PM job
^^^^^^^^^^^^^^^^^^^^^^^^

Get the specified PM job can be executed by the following CLI command.

.. code-block:: console

  $ openstack vnfpm job show JOB_ID --os-tacker-api-version 2


Here is an example of getting the specified PM job:

.. code-block:: console

  $ openstack vnfpm job show 84b227dc-5ed0-411a-aff6-c830528eaec5 --os-tacker-api-version 2
  +-------------------------+----------------------------------------------------------------------------------------------------------+
  | Field                   | Value                                                                                                    |
  +-------------------------+----------------------------------------------------------------------------------------------------------+
  | Callback Uri            | http://127.0.0.1:9990/notification/callbackuri/a0205e7c-fdeb-4f6c-b266-962246e32626                      |
  | Criteria                | {                                                                                                        |
  |                         |     "performanceMetric": [                                                                               |
  |                         |         "VCpuUsageMeanVnf.a0205e7c-fdeb-4f6c-b266-962246e32626"                                          |
  |                         |     ],                                                                                                   |
  |                         |     "collectionPeriod": 30,                                                                              |
  |                         |     "reportingPeriod": 60                                                                                |
  |                         | }                                                                                                        |
  | ID                      | 84b227dc-5ed0-411a-aff6-c830528eaec5                                                                     |
  | Links                   | {                                                                                                        |
  |                         |     "self": {                                                                                            |
  |                         |         "href": "http://127.0.0.1:9890/vnfpm/v2/pm_jobs/84b227dc-5ed0-411a-aff6-c830528eaec5"            |
  |                         |     },                                                                                                   |
  |                         |     "objects": [                                                                                         |
  |                         |         {                                                                                                |
  |                         |             "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/a0205e7c-fdeb-4f6c-b266-962246e32626" |
  |                         |         }                                                                                                |
  |                         |     ]                                                                                                    |
  |                         | }                                                                                                        |
  | Object Instance Ids     | [                                                                                                        |
  |                         |     "a0205e7c-fdeb-4f6c-b266-962246e32626"                                                               |
  |                         | ]                                                                                                        |
  | Object Type             | Vnf                                                                                                      |
  | Reports                 | []                                                                                                       |
  | Sub Object Instance Ids |                                                                                                          |
  +-------------------------+----------------------------------------------------------------------------------------------------------+


Change target PM job
^^^^^^^^^^^^^^^^^^^^

Updating a PM job can only change two fields, callbackUri and authentication.
It can be executed by the following CLI command.

.. code-block:: console

  $ openstack vnfpm job update JOB_ID sample_param_file.json --os-tacker-api-version 2


The content of the sample ``sample_param_file.json`` in this document is
as follows:

.. code-block:: json

  {
      "callbackUri": "http://127.0.0.1:9990/notification/callbackuri/a0205e7c-fdeb-4f6c-b266-962246e32626-update"
  }


Here is an example of changing target PM job:

.. code-block:: console

  $ openstack vnfpm job update 84b227dc-5ed0-411a-aff6-c830528eaec5 sample_param_file.json --os-tacker-api-version 2
  +----------------+--------------------------------------------------------------------------------------------+
  | Field          | Value                                                                                      |
  +----------------+--------------------------------------------------------------------------------------------+
  | Callback Uri   | http://127.0.0.1:9990/notification/callbackuri/a0205e7c-fdeb-4f6c-b266-962246e32626-update |
  +----------------+--------------------------------------------------------------------------------------------+


Delete the specified PM job
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Delete the specified PM job can be executed by the following CLI command.

.. code-block:: console

  $ openstack vnfpm job delete JOB_ID --os-tacker-api-version 2


Here is an example of deleting the specified PM job:

.. code-block:: console

  $ openstack vnfpm job delete 84b227dc-5ed0-411a-aff6-c830528eaec5 --os-tacker-api-version 2
  VNF PM job '84b227dc-5ed0-411a-aff6-c830528eaec5' deleted successfully


Get the specified PM report
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Get the specified PM report can be executed by the following CLI command.

.. code-block:: console

  $ openstack vnfpm report show JOB_ID REPORT_ID --os-tacker-api-version 2


Here is an example of getting the specified PM report:

.. code-block:: console

  $ openstack vnfpm report show 84b227dc-5ed0-411a-aff6-c830528eaec5 eab93857-eb72-49ce-9173-628a3f00ba2d --os-tacker-api-version 2
  +---------+---------------------------------------------------------------------------------------+
  | Field   | Value                                                                                 |
  +---------+---------------------------------------------------------------------------------------+
  | Entries | [                                                                                     |
  |         |     {                                                                                 |
  |         |         "objectType": "Vnf",                                                          |
  |         |         "objectInstanceId": "a0205e7c-fdeb-4f6c-b266-962246e32626",                   |
  |         |         "performanceMetric": "VCpuUsageMeanVnf.a0205e7c-fdeb-4f6c-b266-962246e32626", |
  |         |         "performanceValues": [                                                        |
  |         |             {                                                                         |
  |         |                 "timeStamp": "2023-11-20T14:25:04Z",                                  |
  |         |                 "value": "1.0002889206831795"                                         |
  |         |             }                                                                         |
  |         |         ]                                                                             |
  |         |     }                                                                                 |
  |         | ]                                                                                     |
  +---------+---------------------------------------------------------------------------------------+


History of Checks
-----------------

The content of this document has been confirmed to work
using Prometheus 2.45 and Alertmanager 0.26.


.. _ETSI NFV-SOL 002 v3.3.1:
  https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/002/03.03.01_60/gs_nfv-sol002v030301p.pdf
.. _ETSI NFV-SOL 003 v3.3.1:
  https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/003/03.03.01_60/gs_nfv-sol003v030301p.pdf
.. _official website: https://prometheus.io/docs/prometheus/latest/getting_started/
.. _Prometheus CONFIGURATION:
  https://prometheus.io/docs/prometheus/latest/configuration/configuration
.. _the sample:
  https://opendev.org/openstack/tacker/src/branch/master/samples/tests/functional/sol_kubernetes_v2/test_instantiate_cnf_resources
.. _ETSI GS NFV-IFA 027:
  https://www.etsi.org/deliver/etsi_gs/NFV-IFA/001_099/027/03.03.01_60/gs_nfv-ifa027v030301p.pdf
.. _ETSI GS NFV-SOL 013:
  https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/013/03.04.01_60/gs_nfv-sol013v030401p.pdf
