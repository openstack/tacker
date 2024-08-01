==========================
VNF Performance Management
==========================

This document describes how to manage VNF Performance with CLI in Tacker.

.. note::

  The content of this document has been confirmed to work
  using Tacker 2024.1 Caracal, Kubernetes 1.26, Prometheus 2.45 and
  AlertManager 0.26.


Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

CLI Reference for VNF Performance Management
--------------------------------------------

.. note::

    To call the VNF PM API with ``vnfpm`` subcommand,
    you need to use the option **\-\-os-tacker-api-version 2**


1. Create PM job
^^^^^^^^^^^^^^^^

The `PARAM_FILE.json` should be replaced with the path of parameter json file
that will be used to create VNF PM job.

.. code-block:: console

  $ openstack vnfpm job create PARAM_FILE.json --os-tacker-api-version 2


Result:

.. code-block:: console

  +-------------------------+----------------------------------------------------------------------------------------------------------+
  | Field                   | Value                                                                                                    |
  +-------------------------+----------------------------------------------------------------------------------------------------------+
  | Callback Uri            | http://127.0.0.1:9990/notification/callbackuri/703148ca-addc-4226-bee8-ef73d81dbbbf                      |
  | Criteria                | {                                                                                                        |
  |                         |     "performanceMetric": [                                                                               |
  |                         |         "VCpuUsageMeanVnf.703148ca-addc-4226-bee8-ef73d81dbbbf"                                          |
  |                         |     ],                                                                                                   |
  |                         |     "collectionPeriod": 30,                                                                              |
  |                         |     "reportingPeriod": 60                                                                                |
  |                         | }                                                                                                        |
  | ID                      | 003c633c-7f4c-4bbf-8482-e0535b58d982                                                                     |
  | Links                   | {                                                                                                        |
  |                         |     "self": {                                                                                            |
  |                         |         "href": "http://127.0.0.1:9890/vnfpm/v2/pm_jobs/003c633c-7f4c-4bbf-8482-e0535b58d982"            |
  |                         |     },                                                                                                   |
  |                         |     "objects": [                                                                                         |
  |                         |         {                                                                                                |
  |                         |             "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/703148ca-addc-4226-bee8-ef73d81dbbbf" |
  |                         |         }                                                                                                |
  |                         |     ]                                                                                                    |
  |                         | }                                                                                                        |
  | Object Instance Ids     | [                                                                                                        |
  |                         |     "703148ca-addc-4226-bee8-ef73d81dbbbf"                                                               |
  |                         | ]                                                                                                        |
  | Object Type             | Vnf                                                                                                      |
  | Reports                 | []                                                                                                       |
  | Sub Object Instance Ids |                                                                                                          |
  +-------------------------+----------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnfpm job create --os-tacker-api-version 2 --help
  usage: openstack vnfpm job create [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                    [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                    [--fit-width] [--print-empty]
                                    <param-file>

  Create a new VNF PM job

  positional arguments:
    <param-file>  Specify create VNF PM job request parameters in a json file.

  options:
    -h, --help            show this help message and exit

  output formatters:
    output formatter options

    -f {json,shell,table,value,yaml}, --format {json,shell,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple columns

  json formatter:
    --noindent            whether to disable indenting the JSON

  shell formatter:
    a format a UNIX shell can parse (variable="value")

    --prefix PREFIX
                          add a prefix to all variable names

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use the CLIFF_MAX_TERM_WIDTH
                          environment variable, but the parameter takes precedence.
    --fit-width           Fit the table to the display width. Implied if --max-width greater than 0. Set the
                          environment variable CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.

  This command is provided by the python-tackerclient plugin.


2. Update PM job
^^^^^^^^^^^^^^^^

The `VNF_PM_JOB_ID` and `PARAM_FILE.json` should be replaced with the ID of
VNF PM job and the path of parameter json file that will be used to update VNF
PM job, respectively.

.. code-block:: console

  $ openstack vnfpm job update VNF_PM_JOB_ID PARAM_FILE.json --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------+--------------------------------------------------------------------------------------------+
  | Field        | Value                                                                                      |
  +--------------+--------------------------------------------------------------------------------------------+
  | Callback Uri | http://127.0.0.1:9990/notification/callbackuri/703148ca-addc-4226-bee8-ef73d81dbbbf_update |
  +--------------+--------------------------------------------------------------------------------------------+

Help:

.. code-block:: console

  $ openstack vnfpm job update --os-tacker-api-version 2 --help
  usage: openstack vnfpm job update [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                    [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                    [--fit-width] [--print-empty]
                                    <vnf-pm-job-id> <param-file>

  Update information about an individual VNF PM job

  positional arguments:
    <vnf-pm-job-id>
                          VNF PM job ID to update.
    <param-file>  Specify update PM job request parameters in a json file.

  options:
    -h, --help            show this help message and exit

  output formatters:
    output formatter options

    -f {json,shell,table,value,yaml}, --format {json,shell,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple columns

  json formatter:
    --noindent            whether to disable indenting the JSON

  shell formatter:
    a format a UNIX shell can parse (variable="value")

    --prefix PREFIX
                          add a prefix to all variable names

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use the CLIFF_MAX_TERM_WIDTH
                          environment variable, but the parameter takes precedence.
    --fit-width           Fit the table to the display width. Implied if --max-width greater than 0. Set the
                          environment variable CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.

  This command is provided by the python-tackerclient plugin.


3. List PM jobs
^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnfpm job list --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------------------------------+-------------+----------------------------------------------------------------------------------------------------------+
  | Id                                   | Object Type | Links                                                                                                    |
  +--------------------------------------+-------------+----------------------------------------------------------------------------------------------------------+
  | 003c633c-7f4c-4bbf-8482-e0535b58d982 | Vnf         | {                                                                                                        |
  |                                      |             |     "self": {                                                                                            |
  |                                      |             |         "href":                                                                                          |
  |                                      |             | "http://127.0.0.1:9890/vnfpm/v2/pm_jobs/003c633c-7f4c-4bbf-8482-e0535b58d982"                            |
  |                                      |             |     },                                                                                                   |
  |                                      |             |     "objects": [                                                                                         |
  |                                      |             |         {                                                                                                |
  |                                      |             |             "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/703148ca-addc-4226-bee8-ef73d81dbbbf" |
  |                                      |             |         }                                                                                                |
  |                                      |             |     ]                                                                                                    |
  |                                      |             | }                                                                                                        |
  +--------------------------------------+-------------+----------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnfpm job list --os-tacker-api-version 2 --help
  usage: openstack vnfpm job list [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN]
                                  [--quote {all,minimal,none,nonnumeric}] [--noindent]
                                  [--max-width <integer>] [--fit-width] [--print-empty]
                                  [--sort-column SORT_COLUMN] [--sort-ascending | --sort-descending]
                                  [--filter <filter>]
                                  [--all_fields | --fields fields | --exclude_fields exclude-fields]
                                  [--exclude_default]

  List VNF PM jobs

  options:
    -h, --help            show this help message and exit
    --filter <filter>
                          Attribute-based-filtering parameters
    --all_fields          Include all complex attributes in the response
    --fields fields
                          Complex attributes to be included into the response
    --exclude_fields exclude-fields
                          Complex attributes to be excluded from the response
    --exclude_default     Indicates to exclude all complex attributes from the response. This argument can be
                          used alone or with --fields and --filter. For all other combinations tacker server
                          will throw bad request error

  output formatters:
    output formatter options

    -f {csv,json,table,value,yaml}, --format {csv,json,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple columns
    --sort-column SORT_COLUMN
                          specify the column(s) to sort the data (columns specified first have a priority,
                          non-existing columns are ignored), can be repeated
    --sort-ascending      sort the column(s) in ascending order
    --sort-descending     sort the column(s) in descending order

  CSV Formatter:
    --quote {all,minimal,none,nonnumeric}
                          when to include quotes, defaults to nonnumeric

  json formatter:
    --noindent            whether to disable indenting the JSON

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use the CLIFF_MAX_TERM_WIDTH
                          environment variable, but the parameter takes precedence.
    --fit-width           Fit the table to the display width. Implied if --max-width greater than 0. Set the
                          environment variable CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.

  This command is provided by the python-tackerclient plugin.


4. Show PM job
^^^^^^^^^^^^^^

The `VNF_PM_JOB_ID` should be replaced with the ID of VNF PM job.

.. code-block:: console

  $ openstack vnfpm job show VNF_PM_JOB_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  +-------------------------+---------------------------------------------------------------------------------------------------------------+
  | Field                   | Value                                                                                                         |
  +-------------------------+---------------------------------------------------------------------------------------------------------------+
  | Callback Uri            | http://127.0.0.1:9990/notification/callbackuri/703148ca-addc-4226-bee8-ef73d81dbbbf                           |
  | Criteria                | {                                                                                                             |
  |                         |     "performanceMetric": [                                                                                    |
  |                         |         "VCpuUsageMeanVnf.703148ca-addc-4226-bee8-ef73d81dbbbf"                                               |
  |                         |     ],                                                                                                        |
  |                         |     "collectionPeriod": 30,                                                                                   |
  |                         |     "reportingPeriod": 60                                                                                     |
  |                         | }                                                                                                             |
  | ID                      | 003c633c-7f4c-4bbf-8482-e0535b58d982                                                                          |
  | Links                   | {                                                                                                             |
  |                         |     "self": {                                                                                                 |
  |                         |         "href": "http://127.0.0.1:9890/vnfpm/v2/pm_jobs/003c633c-7f4c-4bbf-8482-e0535b58d982"                 |
  |                         |     },                                                                                                        |
  |                         |     "objects": [                                                                                              |
  |                         |         {                                                                                                     |
  |                         |             "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/703148ca-addc-4226-bee8-ef73d81dbbbf"      |
  |                         |         }                                                                                                     |
  |                         |     ]                                                                                                         |
  |                         | }                                                                                                             |
  | Object Instance Ids     | [                                                                                                             |
  |                         |     "703148ca-addc-4226-bee8-ef73d81dbbbf"                                                                    |
  |                         | ]                                                                                                             |
  | Object Type             | Vnf                                                                                                           |
  | Reports                 | [                                                                                                             |
  |                         |     {                                                                                                         |
  |                         |         "href": "http://127.0.0.1:9890/vnfpm/v2/pm_jobs/003c633c-7f4c-4bbf-8482-                              |
  |                         | e0535b58d982/reports/c6652793-4279-4989-9cf7-08485b5cd2a8",                                                   |
  |                         |         "readyTime": "2024-07-26T00:49:02Z"                                                                   |
  |                         |     },                                                                                                        |
  |                         |     {                                                                                                         |
  |                         |         "href": "http://127.0.0.1:9890/vnfpm/v2/pm_jobs/003c633c-7f4c-4bbf-8482-                              |
  |                         | e0535b58d982/reports/42ca4619-534f-4199-bf9c-9c65709c3b03",                                                   |
  |                         |         "readyTime": "2024-07-26T00:50:02Z"                                                                   |
  |                         |     }                                                                                                         |
  |                         | ]                                                                                                             |
  | Sub Object Instance Ids |                                                                                                               |
  +-------------------------+---------------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnfpm job show --os-tacker-api-version 2 --help
  usage: openstack vnfpm job show [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                  [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                  [--fit-width] [--print-empty]
                                  <vnf-pm-job-id>

  Display VNF PM job details

  positional arguments:
    <vnf-pm-job-id>
                          VNF PM job ID to display

  options:
    -h, --help            show this help message and exit

  output formatters:
    output formatter options

    -f {json,shell,table,value,yaml}, --format {json,shell,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple columns

  json formatter:
    --noindent            whether to disable indenting the JSON

  shell formatter:
    a format a UNIX shell can parse (variable="value")

    --prefix PREFIX
                          add a prefix to all variable names

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use the CLIFF_MAX_TERM_WIDTH
                          environment variable, but the parameter takes precedence.
    --fit-width           Fit the table to the display width. Implied if --max-width greater than 0. Set the
                          environment variable CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.

  This command is provided by the python-tackerclient plugin.


5. Delete PM job
^^^^^^^^^^^^^^^^

The `VNF_PM_JOB_ID` should be replaced with the ID of VNF PM job.

.. code-block:: console

  $ openstack vnfpm job delete VNF_PM_JOB_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  VNF PM job '003c633c-7f4c-4bbf-8482-e0535b58d982' deleted successfully


Help:

.. code-block:: console

  $ openstack vnfpm job delete --os-tacker-api-version 2 --help
  usage: openstack vnfpm job delete [-h] <vnf-pm-job-id> [<vnf-pm-job-id> ...]

  Delete VNF PM job

  positional arguments:
    <vnf-pm-job-id>
                          VNF PM job ID(s) to delete

  options:
    -h, --help            show this help message and exit

  This command is provided by the python-tackerclient plugin.


6. Show PM job report
^^^^^^^^^^^^^^^^^^^^^

The `VNF_PM_JOB_ID` and `VNF_PM_REPORT_ID` should be replaced with the ID of
VNF PM job and the ID of VNF PM report, respectively. The ID of VNF PM report can
be found at the last part of 'href' of an individual VNF PM report from the
output of 'Show PM job'.

.. code-block:: console

  $ openstack vnfpm report show VNF_PM_JOB_ID VNF_PM_REPORT_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  +---------+---------------------------------------------------------------------------------------+
  | Field   | Value                                                                                 |
  +---------+---------------------------------------------------------------------------------------+
  | Entries | [                                                                                     |
  |         |     {                                                                                 |
  |         |         "objectType": "Vnf",                                                          |
  |         |         "objectInstanceId": "703148ca-addc-4226-bee8-ef73d81dbbbf",                   |
  |         |         "performanceMetric": "VCpuUsageMeanVnf.703148ca-addc-4226-bee8-ef73d81dbbbf", |
  |         |         "performanceValues": [                                                        |
  |         |             {                                                                         |
  |         |                 "timeStamp": "2024-07-26T00:49:02Z",                                  |
  |         |                 "value": "0.5507727539609485"                                         |
  |         |             }                                                                         |
  |         |         ]                                                                             |
  |         |     }                                                                                 |
  |         | ]                                                                                     |
  +---------+---------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnfpm report show --os-tacker-api-version 2 --help
  usage: openstack vnfpm report show [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                    [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                    [--fit-width] [--print-empty]
                                    <vnf-pm-job-id> <vnf-pm-report-id>

  Display VNF PM report details

  positional arguments:
    <vnf-pm-job-id>
                          VNF PM job id where the VNF PM report is located
    <vnf-pm-report-id>
                          VNF PM report ID to display

  options:
    -h, --help            show this help message and exit

  output formatters:
    output formatter options

    -f {json,shell,table,value,yaml}, --format {json,shell,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple columns

  json formatter:
    --noindent            whether to disable indenting the JSON

  shell formatter:
    a format a UNIX shell can parse (variable="value")

    --prefix PREFIX
                          add a prefix to all variable names

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use the CLIFF_MAX_TERM_WIDTH
                          environment variable, but the parameter takes precedence.
    --fit-width           Fit the table to the display width. Implied if --max-width greater than 0. Set the
                          environment variable CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.

  This command is provided by the python-tackerclient plugin.


7. Create PM threshold
^^^^^^^^^^^^^^^^^^^^^^

The `PARAM_FILE.json` should be replaced with the path of parameter json file
that will be used to create VNF PM threshold.

.. code-block:: console

  $ openstack vnfpm threshold create PARAM_FILE.json --os-tacker-api-version 2


Result:

.. code-block:: console

  +-------------------------+------------------------------------------------------------------------------------------------------+
  | Field                   | Value                                                                                                |
  +-------------------------+------------------------------------------------------------------------------------------------------+
  | Callback Uri            | http://127.0.0.1:9990/notification/callbackuri/703148ca-addc-4226-bee8-ef73d81dbbbf                  |
  | Criteria                | {                                                                                                    |
  |                         |     "performanceMetric": "VCpuUsageMeanVnf.703148ca-addc-4226-bee8-ef73d81dbbbf",                    |
  |                         |     "thresholdType": "SIMPLE",                                                                       |
  |                         |     "simpleThresholdDetails": {                                                                      |
  |                         |         "thresholdValue": 1.0,                                                                       |
  |                         |         "hysteresis": 0.5                                                                            |
  |                         |     }                                                                                                |
  |                         | }                                                                                                    |
  | ID                      | c748455b-89d7-414b-a4ee-4a24238b3536                                                                 |
  | Links                   | {                                                                                                    |
  |                         |     "self": {                                                                                        |
  |                         |         "href": "http://127.0.0.1:9890/vnfpm/v2/thresholds/c748455b-89d7-414b-a4ee-4a24238b3536"     |
  |                         |     },                                                                                               |
  |                         |     "object": {                                                                                      |
  |                         |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/703148ca-addc-4226-bee8-ef73d81dbbbf" |
  |                         |     }                                                                                                |
  |                         | }                                                                                                    |
  | Object Instance Id      | 703148ca-addc-4226-bee8-ef73d81dbbbf                                                                 |
  | Object Type             | Vnf                                                                                                  |
  | Sub Object Instance Ids |                                                                                                      |
  +-------------------------+------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnfpm threshold create --os-tacker-api-version 2 --help
  usage: openstack vnfpm threshold create [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                          [--noindent] [--prefix PREFIX]
                                          [--max-width <integer>] [--fit-width] [--print-empty]
                                          <param-file>

  Create a new VNF PM threshold

  positional arguments:
    <param-file>  Specify create VNF PM threshold request parameters in a json file.

  options:
    -h, --help            show this help message and exit

  output formatters:
    output formatter options

    -f {json,shell,table,value,yaml}, --format {json,shell,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple columns

  json formatter:
    --noindent            whether to disable indenting the JSON

  shell formatter:
    a format a UNIX shell can parse (variable="value")

    --prefix PREFIX
                          add a prefix to all variable names

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use the CLIFF_MAX_TERM_WIDTH
                          environment variable, but the parameter takes precedence.
    --fit-width           Fit the table to the display width. Implied if --max-width greater than 0. Set the
                          environment variable CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.

  This command is provided by the python-tackerclient plugin.


8. Update PM threshold
^^^^^^^^^^^^^^^^^^^^^^

The `VNF_PM_THRESHOLD_ID` and `PARAM_FILE.json` should be replaced with the ID
of VNF PM threshold and the path of parameter json file that will be used to
update VNF PM threshold, respectively.

.. code-block:: console

  $ openstack vnfpm threshold update VNF_PM_THRESHOLD_ID PARAM_FILE.json --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------+--------------------------------------------------------------------------------------------+
  | Field        | Value                                                                                      |
  +--------------+--------------------------------------------------------------------------------------------+
  | Callback Uri | http://127.0.0.1:9990/notification/callbackuri/703148ca-addc-4226-bee8-ef73d81dbbbf_update |
  +--------------+--------------------------------------------------------------------------------------------+

Help:

.. code-block:: console

  $ openstack vnfpm threshold update --os-tacker-api-version 2 --help
  usage: openstack vnfpm threshold update [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                          [--noindent] [--prefix PREFIX]
                                          [--max-width <integer>] [--fit-width] [--print-empty]
                                          <vnf-pm-threshold-id> <param-file>

  Update information about an individual VNF PM threshold

  positional arguments:
    <vnf-pm-threshold-id>
                          VNF PM threshold ID to update.
    <param-file>  Specify update PM threshold request parameters in a json file.

  options:
    -h, --help            show this help message and exit

  output formatters:
    output formatter options

    -f {json,shell,table,value,yaml}, --format {json,shell,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple columns

  json formatter:
    --noindent            whether to disable indenting the JSON

  shell formatter:
    a format a UNIX shell can parse (variable="value")

    --prefix PREFIX
                          add a prefix to all variable names

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use the CLIFF_MAX_TERM_WIDTH
                          environment variable, but the parameter takes precedence.
    --fit-width           Fit the table to the display width. Implied if --max-width greater than 0. Set the
                          environment variable CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.

  This command is provided by the python-tackerclient plugin.


9. List PM thresholds
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnfpm threshold list --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------------------------------+-------------+------------------------------------------------------------------------------------------------------+
  | ID                                   | Object Type | Links                                                                                                |
  +--------------------------------------+-------------+------------------------------------------------------------------------------------------------------+
  | c748455b-89d7-414b-a4ee-4a24238b3536 | Vnf         | {                                                                                                    |
  |                                      |             |     "self": {                                                                                        |
  |                                      |             |         "href": "http://127.0.0.1:9890/vnfpm/v2/thresholds/c748455b-89d7-414b-a4ee-4a24238b3536"     |
  |                                      |             |     },                                                                                               |
  |                                      |             |     "object": {                                                                                      |
  |                                      |             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/703148ca-addc-4226-bee8-ef73d81dbbbf" |
  |                                      |             |     }                                                                                                |
  |                                      |             | }                                                                                                    |
  +--------------------------------------+-------------+------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnfpm threshold list --os-tacker-api-version 2 --help
  usage: openstack vnfpm threshold list [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN]
                                        [--quote {all,minimal,none,nonnumeric}] [--noindent]
                                        [--max-width <integer>] [--fit-width] [--print-empty]
                                        [--sort-column SORT_COLUMN]
                                        [--sort-ascending | --sort-descending] [--filter <filter>]

  List VNF PM thresholds

  options:
    -h, --help            show this help message and exit
    --filter <filter>
                          Attribute-based-filtering parameters

  output formatters:
    output formatter options

    -f {csv,json,table,value,yaml}, --format {csv,json,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple columns
    --sort-column SORT_COLUMN
                          specify the column(s) to sort the data (columns specified first have a priority,
                          non-existing columns are ignored), can be repeated
    --sort-ascending      sort the column(s) in ascending order
    --sort-descending     sort the column(s) in descending order

  CSV Formatter:
    --quote {all,minimal,none,nonnumeric}
                          when to include quotes, defaults to nonnumeric

  json formatter:
    --noindent            whether to disable indenting the JSON

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use the CLIFF_MAX_TERM_WIDTH
                          environment variable, but the parameter takes precedence.
    --fit-width           Fit the table to the display width. Implied if --max-width greater than 0. Set the
                          environment variable CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.

  This command is provided by the python-tackerclient plugin.


10. Show PM threshold
^^^^^^^^^^^^^^^^^^^^^

The `VNF_PM_THRESHOLD_ID` should be replaced with the ID of VNF PM threshold.

.. code-block:: console

  $ openstack vnfpm threshold show VNF_PM_THRESHOLD_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  +-------------------------+------------------------------------------------------------------------------------------------------+
  | Field                   | Value                                                                                                |
  +-------------------------+------------------------------------------------------------------------------------------------------+
  | Callback Uri            | http://127.0.0.1:9990/notification/callbackuri/703148ca-addc-4226-bee8-ef73d81dbbbf_update           |
  | Criteria                | {                                                                                                    |
  |                         |     "performanceMetric": "VCpuUsageMeanVnf.703148ca-addc-4226-bee8-ef73d81dbbbf",                    |
  |                         |     "thresholdType": "SIMPLE",                                                                       |
  |                         |     "simpleThresholdDetails": {                                                                      |
  |                         |         "thresholdValue": 1.0,                                                                       |
  |                         |         "hysteresis": 0.5                                                                            |
  |                         |     }                                                                                                |
  |                         | }                                                                                                    |
  | ID                      | c748455b-89d7-414b-a4ee-4a24238b3536                                                                 |
  | Links                   | {                                                                                                    |
  |                         |     "self": {                                                                                        |
  |                         |         "href": "http://127.0.0.1:9890/vnfpm/v2/thresholds/c748455b-89d7-414b-a4ee-4a24238b3536"     |
  |                         |     },                                                                                               |
  |                         |     "object": {                                                                                      |
  |                         |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/703148ca-addc-4226-bee8-ef73d81dbbbf" |
  |                         |     }                                                                                                |
  |                         | }                                                                                                    |
  | Object Instance Id      | 703148ca-addc-4226-bee8-ef73d81dbbbf                                                                 |
  | Object Type             | Vnf                                                                                                  |
  | Sub Object Instance Ids |                                                                                                      |
  +-------------------------+------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnfpm threshold show --os-tacker-api-version 2 --help
  usage: openstack vnfpm threshold show [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                        [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                        [--fit-width] [--print-empty]
                                        <vnf-pm-threshold-id>

  Display VNF PM threshold details

  positional arguments:
    <vnf-pm-threshold-id>
                          VNF PM threshold ID to display

  options:
    -h, --help            show this help message and exit

  output formatters:
    output formatter options

    -f {json,shell,table,value,yaml}, --format {json,shell,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple columns

  json formatter:
    --noindent            whether to disable indenting the JSON

  shell formatter:
    a format a UNIX shell can parse (variable="value")

    --prefix PREFIX
                          add a prefix to all variable names

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use the CLIFF_MAX_TERM_WIDTH
                          environment variable, but the parameter takes precedence.
    --fit-width           Fit the table to the display width. Implied if --max-width greater than 0. Set the
                          environment variable CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.

  This command is provided by the python-tackerclient plugin.


11. Delete PM threshold
^^^^^^^^^^^^^^^^^^^^^^^

The `VNF_PM_THRESHOLD_ID` should be replaced with the ID of VNF PM threshold.

.. code-block:: console

  $ openstack vnfpm threshold delete VNF_PM_THRESHOLD_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  VNF PM threshold 'c748455b-89d7-414b-a4ee-4a24238b3536' deleted successfully


Help:

.. code-block:: console

  $ openstack vnfpm threshold delete --os-tacker-api-version 2 --help
  usage: openstack vnfpm threshold delete [-h]
                                          <vnf-pm-threshold-id> [<vnf-pm-threshold-id> ...]

  Delete VNF PM threshold

  positional arguments:
    <vnf-pm-threshold-id>
                          VNF PM threshold ID(s) to delete

  options:
    -h, --help            show this help message and exit

  This command is provided by the python-tackerclient plugin.
