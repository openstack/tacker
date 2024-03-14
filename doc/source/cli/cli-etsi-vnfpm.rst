==========================
VNF Performance Management
==========================

This document describes how to manage VNF Performance with CLI in Tacker.

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

CLI Reference for VNF Performance Management
--------------------------------------------

.. note::
    To call the VNF PM API with vnfpm subcommand, ....
    you need to use the option **--os-tacker-api-version 2**

1. Create PM job
^^^^^^^^^^^^^^^^

'param-file': Specify create VNF PM job request parameters in a json file.

.. code-block:: console

  $ openstack vnfpm job create <param-file> --os-tacker-api-version 2


Result:

.. code-block:: console

  +-------------------------+----------------------------------------------------------------------------------------------------------+
  | Field                   | Value                                                                                                    |
  +-------------------------+----------------------------------------------------------------------------------------------------------+
  | Callback Uri            | http://localhost:9990/notification/callback/test_performancemanagement_interface_min_1                   |
  | Criteria                | {                                                                                                        |
  |                         |     "performanceMetric": [                                                                               |
  |                         |         "VCpuUsageMeanVnf.{7749c637-6e8d-4b6c-a6f4-563aa73744dd}"                                        |
  |                         |     ],                                                                                                   |
  |                         |     "collectionPeriod": 5,                                                                               |
  |                         |     "reportingPeriod": 10                                                                                |
  |                         | }                                                                                                        |
  | ID                      | ca9b58cf-8493-44e3-9e76-678ea0e80a80                                                                     |
  | Links                   | {                                                                                                        |
  |                         |     "self": {                                                                                            |
  |                         |         "href": "http://127.0.0.1:9890/vnfpm/v2/pm_jobs/ca9b58cf-8493-44e3-9e76-678ea0e80a80"            |
  |                         |     },                                                                                                   |
  |                         |     "objects": [                                                                                         |
  |                         |         {                                                                                                |
  |                         |             "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/7749c637-6e8d-4b6c-a6f4-563aa73744dd" |
  |                         |         }                                                                                                |
  |                         |     ]                                                                                                    |
  |                         | }                                                                                                        |
  | Object Instance Ids     | [                                                                                                        |
  |                         |     "7749c637-6e8d-4b6c-a6f4-563aa73744dd"                                                               |
  |                         | ]                                                                                                        |
  | Object Type             | Vnf                                                                                                      |
  | Reports                 | []                                                                                                       |
  | Sub Object Instance Ids |                                                                                                          |
  +-------------------------+----------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnfpm job create --os-tacker-api-version 2 --help
  usage: openstack vnfpm job create [-h] [-f {json,shell,table,value,yaml}]
                                    [-c COLUMN] [--noindent] [--prefix PREFIX]
                                    [--max-width <integer>] [--fit-width]
                                    [--print-empty]
                                    <param-file>

  Create a new VNF PM job

  positional arguments:
    <param-file>        Specify create VNF PM job request parameters in a json file.

  optional arguments:
    -h, --help          show this help message and exit

  output formatters:
    output formatter options

    -f {json,shell,table,value,yaml}, --format {json,shell,table,value,yaml}
                        the output format, defaults to table
    -c COLUMN, --column COLUMN
                        specify the column(s) to include, can be repeated to
                        show multiple columns

  json formatter:
    --noindent          whether to disable indenting the JSON

  shell formatter:
    a format a UNIX shell can parse (variable="value")

    --prefix PREFIX
                        add a prefix to all variable names

  table formatter:
    --max-width <integer>
                        Maximum display width, <1 to disable. You can also use
                        the CLIFF_MAX_TERM_WIDTH environment variable, but the
                        parameter takes precedence.
    --fit-width         Fit the table to the display width. Implied if
                        --max-width greater than 0. Set the environment variable
                        CLIFF_FIT_WIDTH=1 to always enable
    --print-empty       Print empty table if there is no data to show.


2. Update PM job
^^^^^^^^^^^^^^^^

The `<vnf-pm-job-id>` should be replaced with the 'ID' in result of
'1. Create PM job'. In the following sample,
`ca9b58cf-8493-44e3-9e76-678ea0e80a80` is used.

.. code-block:: console

  $ openstack vnfpm job update <vnf-pm-job-id> <param-file> --os-tacker-api-version 2


Result:

.. code-block:: console

  +----------------+---------------------------------------------------------+
  | Field          | Value                                                   |
  +----------------+---------------------------------------------------------+
  | Callback Uri   | http://localhost:9990/notification/callback/callbackUri |
  +----------------+---------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnfpm job update --os-tacker-api-version 2 --help
  usage: openstack vnfpm job update [-h] [-f {json,shell,table,value,yaml}]
                                    [-c COLUMN] [--noindent] [--prefix PREFIX]
                                    [--max-width <integer>] [--fit-width]
                                    [--print-empty]
                                    <vnf-pm-job-id> <param-file>

  Update information about an individual VNF PM job

  positional arguments:
    <vnf-pm-job-id>     VNF PM job ID to update.
    <param-file>        Specify update PM job request parameters in a json file.

  optional arguments:
    -h, --help          show this help message and exit

  output formatters:
    output formatter options

    -f {json,shell,table,value,yaml}, --format {json,shell,table,value,yaml}
                        the output format, defaults to table
    -c COLUMN, --column COLUMN
                        specify the column(s) to include, can be repeated to
                        show multiple columns

  json formatter:
    --noindent          whether to disable indenting the JSON

  shell formatter:
    a format a UNIX shell can parse (variable="value")

    --prefix PREFIX
                        add a prefix to all variable names

  table formatter:
    --max-width <integer>
                        Maximum display width, <1 to disable. You can also use
                        the CLIFF_MAX_TERM_WIDTH environment variable, but the
                        parameter takes precedence.
    --fit-width         Fit the table to the display width. Implied if --max-width
                        greater than 0. Set the environment variable CLIFF_FIT_WIDTH=1
                        to always enable
    --print-empty       Print empty table if there is no data to show.


3. List PM jobs
^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnfpm job list --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------------------------------+-------------+----------------------------------------------------------------------------------------------------------+
  | Id                                   | Object Type | Links                                                                                                    |
  +--------------------------------------+-------------+----------------------------------------------------------------------------------------------------------+
  | ca9b58cf-8493-44e3-9e76-678ea0e80a80 | Vnf         | {                                                                                                        |
  |                                      |             |     "self": {                                                                                            |
  |                                      |             |         "href": "http://127.0.0.1:9890/vnfpm/v2/pm_jobs/ca9b58cf-8493-44e3-9e76-678ea0e80a80"            |
  |                                      |             |     },                                                                                                   |
  |                                      |             |     "objects": [                                                                                         |
  |                                      |             |         {                                                                                                |
  |                                      |             |             "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/7749c637-6e8d-4b6c-a6f4-563aa73744dd" |
  |                                      |             |         }                                                                                                |
  |                                      |             |     ]                                                                                                    |
  |                                      |             | }                                                                                                        |
  | 2067f412-6a02-4491-a5ab-426c772110f2 | Vnf         | {                                                                                                        |
  |                                      |             |     "self": {                                                                                            |
  |                                      |             |         "href": "http://127.0.0.1:9890/vnfpm/v2/pm_jobs/2067f412-6a02-4491-a5ab-426c772110f2"            |
  |                                      |             |     },                                                                                                   |
  |                                      |             |     "objects": [                                                                                         |
  |                                      |             |         {                                                                                                |
  |                                      |             |             "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/492c6347-668f-4b04-bb98-e69af8194887" |
  |                                      |             |         }                                                                                                |
  |                                      |             |     ]                                                                                                    |
  |                                      |             | }                                                                                                        |
  +--------------------------------------+-------------+----------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnfpm job list --os-tacker-api-version 2 --help
  usage: openstack vnfpm job list [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN]
                                  [--quote {all,minimal,none,nonnumeric}]
                                  [--noindent] [--max-width <integer>] [--fit-width]
                                  [--print-empty] [--sort-column SORT_COLUMN]
                                  [--sort-ascending | --sort-descending]
                                  [--filter <filter>]
                                  [--all_fields | --fields fields | --exclude_fields exclude-fields]
                                  [--exclude_default]

  List VNF PM jobs

  optional arguments:
    -h, --help            show this help message and exit
    --filter <filter>     Attribute-based-filtering parameters
    --all_fields          Include all complex attributes in the response
    --fields fields       Complex attributes to be included into the response
    --exclude_fields exclude-fields
                          Complex attributes to be excluded from the response
    --exclude_default     Indicates to exclude all complex attributes from the response. This
                          argument can be used alone or with --fields and --filter. For all
                          other combinations tacker server will throw bad request error

  output formatters:
    output formatter options

    -f {csv,json,table,value,yaml}, --format {csv,json,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple
                          columns
    --sort-column SORT_COLUMN
                          specify the column(s) to sort the data (columns specified first have a
                          priority, non-existing columns are ignored),
                          can be repeated
    --sort-ascending      sort the column(s) in ascending order
    --sort-descending     sort the column(s) in descending order

  CSV Formatter:
    --quote {all,minimal,none,nonnumeric}
                          when to include quotes, defaults to nonnumeric

  json formatter:
    --noindent            whether to disable indenting the JSON

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use the
                          CLIFF_MAX_TERM_WIDTH environment variable, but the parameter takes
                          precedence.
    --fit-width           Fit the table to the display width. Implied if --max-width greater than
                          0. Set the environment variable CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.


4. Show PM job
^^^^^^^^^^^^^^

The `<vnf-pm-job-id>` should be replaced with the 'ID' in result of
'1. Create PM job' or '3. List PM jobs'. In the following sample,
`ca9b58cf-8493-44e3-9e76-678ea0e80a80` is used.

.. code-block:: console

  $ openstack vnfpm job show <vnf-pm-job-id> --os-tacker-api-version 2


Result:

.. code-block:: console

    +-------------------------+---------------------------------------------------------------------------------------------------------------------------------------------+
    | Field                   | Value                                                                                                                                       |
    +-------------------------+---------------------------------------------------------------------------------------------------------------------------------------------+
    | Callback Uri            | http://127.0.0.1:9990/notification/callbackuri/5c5985e3-9f28-4e80-9ed8-66c18cca50e5                                                         |
    | Criteria                | {                                                                                                                                           |
    |                         |     "performanceMetric": [                                                                                                                  |
    |                         |         "VCpuUsageMeanVnf.5c5985e3-9f28-4e80-9ed8-66c18cca50e5"                                                                             |
    |                         |     ],                                                                                                                                      |
    |                         |     "collectionPeriod": 30,                                                                                                                 |
    |                         |     "reportingPeriod": 60                                                                                                                   |
    |                         | }                                                                                                                                           |
    | ID                      | 8a1979b3-29dc-4ba3-aeb5-acce07607648                                                                                                        |
    | Links                   | {                                                                                                                                           |
    |                         |     "self": {                                                                                                                               |
    |                         |         "href": "http://127.0.0.1:9890/vnfpm/v2/pm_jobs/8a1979b3-29dc-4ba3-aeb5-acce07607648"                                               |
    |                         |     },                                                                                                                                      |
    |                         |     "objects": [                                                                                                                            |
    |                         |         {                                                                                                                                   |
    |                         |             "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/5c5985e3-9f28-4e80-9ed8-66c18cca50e5"                                    |
    |                         |         }                                                                                                                                   |
    |                         |     ]                                                                                                                                       |
    |                         | }                                                                                                                                           |
    | Object Instance Ids     | [                                                                                                                                           |
    |                         |     "5c5985e3-9f28-4e80-9ed8-66c18cca50e5"                                                                                                  |
    |                         | ]                                                                                                                                           |
    | Object Type             | Vnf                                                                                                                                         |
    | Reports                 | [                                                                                                                                           |
    |                         |     {                                                                                                                                       |
    |                         |         "href": "http://127.0.0.1:9890/vnfpm/v2/pm_jobs/8a1979b3-29dc-4ba3-aeb5-acce07607648/reports/e138a740-039c-40d2-9467-85bef9819c90", |
    |                         |         "readyTime": "2024-02-21T09:00:53Z"                                                                                                 |
    |                         |     }                                                                                                                                       |
    |                         | ]                                                                                                                                           |
    | Sub Object Instance Ids |                                                                                                                                             |
    +-------------------------+---------------------------------------------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnfpm job show --os-tacker-api-version 2 --help
  usage: openstack vnfpm job show [-h] [-f {json,shell,table,value,yaml}]
                                  [-c COLUMN] [--noindent] [--prefix PREFIX]
                                  [--max-width <integer>] [--fit-width] [--print-empty]
                                  <vnf-pm-job-id>

  Display VNF PM job details

  positional arguments:
    <vnf-pm-job-id>       VNF PM job ID to display

  optional arguments:
    -h, --help            show this help message and exit

  output formatters:
    output formatter options

    -f {json,shell,table,value,yaml}, --format {json,shell,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple
                          columns

  json formatter:
    --noindent            whether to disable indenting the JSON

  shell formatter:
    a format a UNIX shell can parse (variable="value")

    --prefix PREFIX       add a prefix to all variable names

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use the
                          CLIFF_MAX_TERM_WIDTH environment variable, but the parameter takes
                          precedence.
    --fit-width           Fit the table to the display width. Implied if --max-width greater than
                          0. Set the environment variable CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.


5. Delete PM job
^^^^^^^^^^^^^^^^

The `<vnf-pm-job-id>` should be replaced with the 'ID' in result of
'1. Create PM job' or '3. List PM jobs'. In the following sample,
`ca9b58cf-8493-44e3-9e76-678ea0e80a80` is used.

.. code-block:: console

  $ openstack vnfpm job delete <vnf-pm-job-id> --os-tacker-api-version 2


Result:

.. code-block:: console

  VNF PM job 'ca9b58cf-8493-44e3-9e76-678ea0e80a80' deleted successfully


Help:

.. code-block:: console

  $ openstack vnfpm job delete --os-tacker-api-version 2 --help
  usage: openstack vnfpm job delete [-h] <vnf-pm-job-id> [<vnf-pm-job-id> ...]

  Delete VNF PM job

  positional arguments:
    <vnf-pm-job-id>       VNF PM job ID(s) to delete

  optional arguments:
    -h, --help            show this help message and exit


6. Show PM job report
^^^^^^^^^^^^^^^^^^^^^

The `<vnf-pm-job-id>` should be replaced with the 'ID' in result of
'1. Create PM job' or '3. List PM jobs'. In the following sample,
`500f538e-44a5-460a-a95e-e9189354c2be` is used.
The `<vnf-pm-report-id>` should be replaced with the last part marked by `/` of
'href'. The 'href' is part of 'Reports' in result of '4. Show PM job'.
In the following sample, `53aafe25-7124-4880-8b58-47a93b3dc371` is used.

.. code-block:: console

  $ openstack vnfpm report show <vnf-pm-job-id> <vnf-pm-report-id> --os-tacker-api-version 2


Result:

.. code-block:: console

  +---------+---------------------------------------------------------------------------------------+
  | Field   | Value                                                                                 |
  +---------+---------------------------------------------------------------------------------------+
  | Entries | [                                                                                     |
  |         |     {                                                                                 |
  |         |         "objectType": "Vnf",                                                          |
  |         |         "objectInstanceId": "495ffedf-2755-42c8-bf14-a5433701311e",                   |
  |         |         "performanceMetric": "VCpuUsageMeanVnf.495ffedf-2755-42c8-bf14-a5433701311e", |
  |         |         "performanceValues": [                                                        |
  |         |             {                                                                         |
  |         |                 "timeStamp": "2022-08-30T08:02:58Z",                                  |
  |         |                 "value": "99.0"                                                       |
  |         |             }                                                                         |
  |         |         ]                                                                             |
  |         |     }                                                                                 |
  |         | ]                                                                                     |
  +---------+---------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnfpm report show --os-tacker-api-version 2 --help
  usage: openstack vnfpm report show [-h] [-f {json,shell,table,value,yaml}]
                                     [-c COLUMN] [--noindent] [--prefix PREFIX]
                                     [--max-width <integer>] [--fit-width] [--print-empty]
                                     <vnf-pm-job-id> <vnf-pm-report-id>

  Display VNF PM report details

  positional arguments:
    <vnf-pm-job-id>
                          VNF PM job id where the VNF PM report is located
    <vnf-pm-report-id>
                          VNF PM report ID to display

  optional arguments:
    -h, --help            show this help message and exit

  output formatters:
    output formatter options

    -f {json,shell,table,value,yaml}, --format {json,shell,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple
                          columns

  json formatter:
    --noindent            whether to disable indenting the JSON

  shell formatter:
    a format a UNIX shell can parse (variable="value")

    --prefix PREFIX
                          add a prefix to all variable names

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use the
                          CLIFF_MAX_TERM_WIDTH environment variable, but the parameter takes
                          precedence.
    --fit-width           Fit the table to the display width. Implied if --max-width greater than
                          0. Set the environment variable CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.


7. Create PM threshold
^^^^^^^^^^^^^^^^^^^^^^

'param-file': Specify create VNF PM threshold request parameters in a json
file.

.. code-block:: console

  $ openstack vnfpm threshold create <param-file> --os-tacker-api-version 2


Result:

.. code-block:: console

  +-------------------------+------------------------------------------------------------------------------------------------------+
  | Field                   | Value                                                                                                |
  +-------------------------+------------------------------------------------------------------------------------------------------+
  | Callback Uri            | http://127.0.0.1:9990/notification/callbackuri/511a2d68-c975-4913-b7b8-d75468e3102b                  |
  | Criteria                | {                                                                                                    |
  |                         |     "performanceMetric": "VMemoryUsageMeanVnf.511a2d68-c975-4913-b7b8-d75468e3102b",                 |
  |                         |     "thresholdType": "SIMPLE",                                                                       |
  |                         |     "simpleThresholdDetails": {                                                                      |
  |                         |         "thresholdValue": 55.0,                                                                      |
  |                         |         "hysteresis": 30.0                                                                           |
  |                         |     }                                                                                                |
  |                         | }                                                                                                    |
  | ID                      | 4787c544-c3d0-4aeb-bf60-1598125c3d4f                                                                 |
  | Links                   | {                                                                                                    |
  |                         |     "self": {                                                                                        |
  |                         |         "href": "http://127.0.0.1:9890/vnfpm/v2/thresholds/4787c544-c3d0-4aeb-bf60-1598125c3d4f"     |
  |                         |     },                                                                                               |
  |                         |     "object": {                                                                                      |
  |                         |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/511a2d68-c975-4913-b7b8-d75468e3102b" |
  |                         |     }                                                                                                |
  |                         | }                                                                                                    |
  | Object Instance Id      | 511a2d68-c975-4913-b7b8-d75468e3102b                                                                 |
  | Object Type             | Vnf                                                                                                  |
  | Sub Object Instance Ids |                                                                                                      |
  +-------------------------+------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnfpm threshold create --os-tacker-api-version 2 --help
  usage: openstack vnfpm threshold create [-h] [-f {json,shell,table,value,yaml}]
                                          [-c COLUMN] [--noindent] [--prefix PREFIX]
                                          [--max-width <integer>] [--fit-width]
                                          [--print-empty]
                                          <param-file>

  Create a new VNF PM threshold

  positional arguments:
    <param-file>          Specify create VNF PM threshold request parameters in a json file.

  optional arguments:
    -h, --help            show this help message and exit

  output formatters:
    output formatter options

    -f {json,shell,table,value,yaml}, --format {json,shell,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to
                          show multiple columns

  json formatter:
    --noindent            whether to disable indenting the JSON

  shell formatter:
    a format a UNIX shell can parse (variable="value")

    --prefix PREFIX       add a prefix to all variable names

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use
                          the CLIFF_MAX_TERM_WIDTH environment variable, but the
                          parameter takes precedence.
    --fit-width           Fit the table to the display width. Implied if --max-width
                          greater than 0. Set the environment variable
                          CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.


8. Update PM threshold
^^^^^^^^^^^^^^^^^^^^^^

The `<vnf-pm-threshold-id>` should be replaced with the 'ID' in result of
'7. Create PM threshold'. In the following sample,
`4787c544-c3d0-4aeb-bf60-1598125c3d4f` is used.

.. code-block:: console

  $ openstack vnfpm threshold update <vnf-pm-threshold-id> <param-file> --os-tacker-api-version 2


Result:

.. code-block:: console

  +----------------+------------------------------------------------------------+
  | Field          | Value                                                      |
  +----------------+------------------------------------------------------------+
  | Callback Uri   | http://127.0.0.1:9990/notification/callbackuri/callbackUri |
  +----------------+------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnfpm threshold update --os-tacker-api-version 2 --help
  usage: openstack vnfpm threshold update [-h] [-f {json,shell,table,value,yaml}]
                                          [-c COLUMN] [--noindent] [--prefix PREFIX]
                                          [--max-width <integer>] [--fit-width]
                                          [--print-empty]
                                          <vnf-pm-threshold-id> <param-file>

  Update information about an individual VNF PM threshold

  positional arguments:
    <vnf-pm-threshold-id> VNF PM threshold ID to update.
    <param-file>          Specify update PM threshold request parameters in a json file.

  optional arguments:
    -h, --help            show this help message and exit

  output formatters:
    output formatter options

    -f {json,shell,table,value,yaml}, --format {json,shell,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to
                          show multiple columns

  json formatter:
    --noindent            whether to disable indenting the JSON

  shell formatter:
    a format a UNIX shell can parse (variable="value")

    --prefix PREFIX       add a prefix to all variable names

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use
                          the CLIFF_MAX_TERM_WIDTH environment variable, but the
                          parameter takes precedence.
    --fit-width           Fit the table to the display width. Implied if
                          --max-width greater than 0. Set the environment variable
                          CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.


9. List PM thresholds
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnfpm threshold list --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------------------------------+-------------+------------------------------------------------------------------------------------------------------+
  | ID                                   | Object Type | Links                                                                                                |
  +--------------------------------------+-------------+------------------------------------------------------------------------------------------------------+
  | 4787c544-c3d0-4aeb-bf60-1598125c3d4f | Vnf         | {                                                                                                    |
  |                                      |             |     "self": {                                                                                        |
  |                                      |             |         "href": "http://127.0.0.1:9890/vnfpm/v2/thresholds/4787c544-c3d0-4aeb-bf60-1598125c3d4f"     |
  |                                      |             |     },                                                                                               |
  |                                      |             |     "object": {                                                                                      |
  |                                      |             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/511a2d68-c975-4913-b7b8-d75468e3102b" |
  |                                      |             |     }                                                                                                |
  |                                      |             | }                                                                                                    |
  +--------------------------------------+-------------+------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnfpm threshold list --os-tacker-api-version 2 --help
  usage: openstack vnfpm threshold list [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN]
                                      [--quote {all,minimal,none,nonnumeric}] [--noindent]
                                      [--max-width <integer>]
                                      [--fit-width] [--print-empty] [--sort-column SORT_COLUMN]
                                      [--sort-ascending | --sort-descending] [--filter <filter>]

  List VNF PM thresholds

  optional arguments:
    -h, --help            show this help message and exit
    --filter <filter>     Attribute-based-filtering parameters

  output formatters:
    output formatter options

    -f {csv,json,table,value,yaml}, --format {csv,json,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to
                          show multiple columns
    --sort-column SORT_COLUMN
                          specify the column(s) to sort the data (
                          columns specified first have a priority,
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
                          Maximum display width, <1 to disable. You can also
                          use the CLIFF_MAX_TERM_WIDTH environment variable,
                          but the parameter takes precedence.
    --fit-width           Fit the table to the display width. Implied if
                          --max-width greater than 0. Set the environment variable
                          CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.


10. Show PM threshold
^^^^^^^^^^^^^^^^^^^^^

The `<vnf-pm-threshold-id>` should be replaced with the 'ID' in result of
'7. Create PM threshold' or '9. List PM thresholds'. In the following sample,
`4787c544-c3d0-4aeb-bf60-1598125c3d4f` is used.

.. code-block:: console

  $openstack vnfpm threshold show <vnf-pm-threshold-id> --os-tacker-api-version 2


Result:

.. code-block:: console

  +-------------------------+------------------------------------------------------------------------------------------------------+
  | Field                   | Value                                                                                                |
  +-------------------------+------------------------------------------------------------------------------------------------------+
  | Callback Uri            | http://127.0.0.1:9990/notification/callbackuri/callbackUri                                           |
  | Criteria                | {                                                                                                    |
  |                         |     "performanceMetric": "VMemoryUsageMeanVnf.511a2d68-c975-4913-b7b8-d75468e3102b",                 |
  |                         |     "thresholdType": "SIMPLE",                                                                       |
  |                         |     "simpleThresholdDetails": {                                                                      |
  |                         |         "thresholdValue": 55.0,                                                                      |
  |                         |         "hysteresis": 30.0                                                                           |
  |                         |     }                                                                                                |
  |                         | }                                                                                                    |
  | ID                      | 4787c544-c3d0-4aeb-bf60-1598125c3d4f                                                                 |
  | Links                   | {                                                                                                    |
  |                         |     "self": {                                                                                        |
  |                         |         "href": "http://127.0.0.1:9890/vnfpm/v2/thresholds/4787c544-c3d0-4aeb-bf60-1598125c3d4f"     |
  |                         |     },                                                                                               |
  |                         |     "object": {                                                                                      |
  |                         |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/511a2d68-c975-4913-b7b8-d75468e3102b" |
  |                         |     }                                                                                                |
  |                         | }                                                                                                    |
  | Object Instance Id      | 511a2d68-c975-4913-b7b8-d75468e3102b                                                                 |
  | Object Type             | Vnf                                                                                                  |
  | Sub Object Instance Ids |                                                                                                      |
  +-------------------------+------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnfpm threshold show --os-tacker-api-version 2 --help
  usage: openstack vnfpm threshold show [-h] [-f {json,shell,table,value,yaml}]
                                      [-c COLUMN] [--noindent]
                                      [--prefix PREFIX] [--max-width <integer>]
                                      [--fit-width] [--print-empty]
                                      <vnf-pm-threshold-id>

  Display VNF PM threshold details

  positional arguments:
    <vnf-pm-threshold-id> VNF PM threshold ID to display

  optional arguments:
    -h, --help            show this help message and exit

  output formatters:
    output formatter options

    -f {json,shell,table,value,yaml}, --format {json,shell,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to
                          show multiple columns

  json formatter:
    --noindent            whether to disable indenting the JSON

  shell formatter:
    a format a UNIX shell can parse (variable="value")

    --prefix PREFIX       add a prefix to all variable names

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use
                          the CLIFF_MAX_TERM_WIDTH environment variable, but the
                          parameter takes precedence.
    --fit-width           Fit the table to the display width. Implied if
                          --max-width greater than 0. Set the environment variable
                          CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.


11. Delete PM threshold
^^^^^^^^^^^^^^^^^^^^^^^

The `<vnf-pm-threshold-id>` should be replaced with the 'ID' in result of
'7. Create PM threshold' or '9. List PM thresholds'. In the following sample,
`4787c544-c3d0-4aeb-bf60-1598125c3d4f` is used.

.. code-block:: console

  $ openstack vnfpm threshold delete <vnf-pm-threshold-id> --os-tacker-api-version 2


Result:

.. code-block:: console

  VNF PM threshold '4787c544-c3d0-4aeb-bf60-1598125c3d4f' deleted successfully


Help:

.. code-block:: console

  $ openstack vnfpm threshold delete --os-tacker-api-version 2 --help
  usage: openstack vnfpm threshold delete [-h] <vnf-pm-threshold-id> [<vnf-pm-threshold-id> ...]

  Delete VNF PM threshold

  positional arguments:
    <vnf-pm-threshold-id> VNF PM threshold ID(s) to delete

  optional arguments:
    -h, --help            show this help message and exit
