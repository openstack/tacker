====================
VNF Fault Management
====================

This document describes how to manage VNF Fault with CLI in Tacker.

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

CLI Reference for VNF Fault Management
--------------------------------------

.. note::
    To call the VNF FM API with vnffm subcommand,
    you need to use the option **--os-tacker-api-version 2**

1. List alarms
^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnffm alarm list --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------------------------------+--------------------------------------+--------------+------------------------+--------------------+--------------------+
  | ID                                   | Managed Object Id                    | Ack State    | Event Type             | Perceived Severity | Probable Cause     |
  +--------------------------------------+--------------------------------------+--------------+------------------------+--------------------+--------------------+
  | d59545c5-6882-47a2-85aa-b25a5a0591c0 | 398c139d-a047-4047-bd3c-56558de87e67 | ACKNOWLEDGED | PROCESSING_ERROR_ALARM | WARNING            | Process Terminated |
  | fadd40db-a6f8-405f-a77a-72a9d408d7ae | ef635ef7-1f14-47d5-abcb-ed3b28f8ba74 | ACKNOWLEDGED | PROCESSING_ERROR_ALARM | WARNING            | Process Terminated |
  +--------------------------------------+--------------------------------------+--------------+------------------------+--------------------+--------------------+


Help:

.. code-block:: console

  $ openstack vnffm alarm list --os-tacker-api-version 2 --help
  usage: openstack vnffm alarm list [-h] [-f {csv,json,table,value,yaml}]
                                    [-c COLUMN]
                                    [--quote {all,minimal,none,nonnumeric}] [--noindent]
                                    [--max-width <integer>] [--fit-width] [--print-empty]
                                    [--sort-column SORT_COLUMN]
                                    [--sort-ascending | --sort-descending]
                                    [--filter <filter>]

  List VNF FM alarms

  optional arguments:
    -h, --help            show this help message and exit
    --filter <filter>     Attribute-based-filtering parameters

  output formatters:
    output formatter options

    -f {csv,json,table,value,yaml}, --format {csv,json,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple
                          columns
    --sort-column SORT_COLUMN
                          specify the column(s) to sort the data (columns specified first have a
                          priority, non-existing columns are ignored), can be repeated
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


2. Show alarm
^^^^^^^^^^^^^

The `<vnf-fm-alarm-id>` should be replaced with the 'ID' in result of
'1. List alarms'. In the following sample,
`d59545c5-6882-47a2-85aa-b25a5a0591c0` is used.

.. code-block:: console

  $ openstack vnffm alarm show <vnf-fm-alarm-id> --os-tacker-api-version 2


Result:

.. code-block:: console

  +----------------------------+------------------------------------------------------------------------------------------------------+
  | Field                      | Value                                                                                                |
  +----------------------------+------------------------------------------------------------------------------------------------------+
  | Ack State                  | ACKNOWLEDGED                                                                                         |
  | Alarm Acknowledged Time    | 2022-08-30T12:23:52Z                                                                                 |
  | Alarm Changed Time         | 2022-08-29T05:49:02Z                                                                                 |
  | Alarm Cleared Time         | 2022-06-22T23:47:36Z                                                                                 |
  | Alarm Raised Time          | 2022-08-29T05:48:56Z                                                                                 |
  | Correlated Alarm Ids       |                                                                                                      |
  | Event Time                 | 2022-06-21T23:47:36Z                                                                                 |
  | Event Type                 | PROCESSING_ERROR_ALARM                                                                               |
  | Fault Details              | [                                                                                                    |
  |                            |     "fingerprint: 5ef77f1f8a3ecb8d",                                                                 |
  |                            |     "detail: pid 12345"                                                                              |
  |                            | ]                                                                                                    |
  | Fault Type                 | Server Down                                                                                          |
  | ID                         | d59545c5-6882-47a2-85aa-b25a5a0591c0                                                                 |
  | Is Root Cause              | False                                                                                                |
  | Links                      | {                                                                                                    |
  |                            |     "self": {                                                                                        |
  |                            |         "href": "http://127.0.0.1:9890/vnffm/v1/alarms/d59545c5-6882-47a2-85aa-b25a5a0591c0"         |
  |                            |     },                                                                                               |
  |                            |     "objectInstance": {                                                                              |
  |                            |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/398c139d-a047-4047-bd3c-56558de87e67" |
  |                            |     }                                                                                                |
  |                            | }                                                                                                    |
  | Managed Object Id          | 398c139d-a047-4047-bd3c-56558de87e67                                                                 |
  | Perceived Severity         | WARNING                                                                                              |
  | Probable Cause             | Process Terminated                                                                                   |
  | Root Cause Faulty Resource |                                                                                                      |
  | Vnfc Instance Ids          | []                                                                                                   |
  +----------------------------+------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnffm alarm show --os-tacker-api-version 2  --help
  usage: openstack vnffm alarm show [-h] [-f {json,shell,table,value,yaml}]
                                  [-c COLUMN] [--noindent] [--prefix PREFIX]
                                  [--max-width <integer>] [--fit-width] [--print-empty]
                                  <vnf-fm-alarm-id>

  Display VNF FM alarm details

  positional arguments:
    <vnf-fm-alarm-id>     VNF FM alarm ID to display

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


3. Update alarm
^^^^^^^^^^^^^^^

The `<vnf-fm-alarm-id>` should be replaced with the 'ID' in result of
'1. List alarms'. In the following sample,
`d59545c5-6882-47a2-85aa-b25a5a0591c0` is used.

.. code-block:: console

  $ openstack vnffm alarm update <vnf-fm-alarm-id> --ack-state UNACKNOWLEDGED --os-tacker-api-version 2


Result:

.. code-block:: console

  +-----------+----------------+
  | Field     | Value          |
  +-----------+----------------+
  | Ack State | UNACKNOWLEDGED |
  +-----------+----------------+


Help:

.. code-block:: console

  $ openstack vnffm alarm update --os-tacker-api-version 2 --help
  usage: openstack vnffm alarm update [-h] [-f {json,shell,table,value,yaml}]
                                      [-c COLUMN] [--noindent] [--prefix PREFIX]
                                      [--max-width <integer>] [--fit-width] [--print-empty]
                                      [--ack-state <ack-state>]
                                      <vnf-fm-alarm-id>

  Update information about an individual VNF FM alarm

  positional arguments:
    <vnf-fm-alarm-id>     VNF FM alarm ID to update.

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

  require arguments:
    --ack-state <ack-state>
                          Ask state can be 'ACKNOWLEDGED' or 'UNACKNOWLEDGED'.


4. Create subscription
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnffm sub create <param-file> --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------+-----------------------------------------------------------------------------------------------------+
  | Field        | Value                                                                                               |
  +--------------+-----------------------------------------------------------------------------------------------------+
  | Callback Uri | /nfvo/notify/alarm                                                                                  |
  | Filter       | {                                                                                                   |
  |              |     "vnfInstanceSubscriptionFilter": {                                                              |
  |              |         "vnfdIds": [                                                                                |
  |              |             "27b1c79c-5d78-43dd-a653-a1d6b9f3ea5d"                                                  |
  |              |         ],                                                                                          |
  |              |         "vnfProductsFromProviders": [                                                               |
  |              |             {                                                                                       |
  |              |                 "vnfProvider": "Company",                                                           |
  |              |                 "vnfProducts": [                                                                    |
  |              |                     {                                                                               |
  |              |                         "vnfProductName": "Sample VNF",                                             |
  |              |                         "versions": [                                                               |
  |              |                             {                                                                       |
  |              |                                 "vnfSoftwareVersion": "1.0",                                        |
  |              |                                 "vnfdVersions": [                                                   |
  |              |                                     "1.0",                                                          |
  |              |                                     "2.0"                                                           |
  |              |                                 ]                                                                   |
  |              |                             }                                                                       |
  |              |                         ]                                                                           |
  |              |                     }                                                                               |
  |              |                 ]                                                                                   |
  |              |             }                                                                                       |
  |              |         ],                                                                                          |
  |              |         "vnfInstanceIds": [                                                                         |
  |              |             "b0314420-0c9e-40e0-975e-4bf23b07d0c1"                                                  |
  |              |         ],                                                                                          |
  |              |         "vnfInstanceNames": [                                                                       |
  |              |             "test"                                                                                  |
  |              |         ]                                                                                           |
  |              |     },                                                                                              |
  |              |     "notificationTypes": [                                                                          |
  |              |         "AlarmNotification",                                                                        |
  |              |         "AlarmClearedNotification"                                                                  |
  |              |     ],                                                                                              |
  |              |     "faultyResourceTypes": [                                                                        |
  |              |         "COMPUTE"                                                                                   |
  |              |     ],                                                                                              |
  |              |     "perceivedSeverities": [                                                                        |
  |              |         "WARNING"                                                                                   |
  |              |     ],                                                                                              |
  |              |     "eventTypes": [                                                                                 |
  |              |         "PROCESSING_ERROR_ALARM"                                                                    |
  |              |     ],                                                                                              |
  |              |     "probableCauses": [                                                                             |
  |              |         "Process Terminated"                                                                        |
  |              |     ]                                                                                               |
  |              | }                                                                                                   |
  | ID           | 4102e2a5-019b-40ea-8da2-579ecd5f17db                                                                |
  | Links        | {                                                                                                   |
  |              |     "self": {                                                                                       |
  |              |         "href": "http://127.0.0.1:9890/vnffm/v1/subscriptions/4102e2a5-019b-40ea-8da2-579ecd5f17db" |
  |              |     }                                                                                               |
  |              | }                                                                                                   |
  +--------------+-----------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnffm sub create --os-tacker-api-version 2 --help
  usage: openstack vnffm sub create [-h] [-f {json,shell,table,value,yaml}]
                                    [-c COLUMN] [--noindent] [--prefix PREFIX]
                                    [--max-width <integer>] [--fit-width] [--print-empty]
                                    <param-file>

  Create a new VNF FM subscription

  positional arguments:
    <param-file>  Specify create VNF FM subscription request parameters in a json file.

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


5. List subscriptions
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnffm sub list --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------------------------------+--------------------+
  | ID                                   | Callback Uri       |
  +--------------------------------------+--------------------+
  | 4102e2a5-019b-40ea-8da2-579ecd5f17db | /nfvo/notify/alarm |
  +--------------------------------------+--------------------+


Help:

.. code-block:: console

  $ openstack vnffm sub list --os-tacker-api-version 2 --help
  usage: openstack vnffm sub list [-h] [-f {csv,json,table,value,yaml}]
                                  [-c COLUMN]
                                  [--quote {all,minimal,none,nonnumeric}]
                                  [--noindent] [--max-width <integer>] [--fit-width]
                                  [--print-empty] [--sort-column SORT_COLUMN]
                                  [--sort-ascending | --sort-descending]
                                  [--filter <filter>]

  List VNF FM subs

  optional arguments:
    -h, --help            show this help message and exit
    --filter <filter>
                        Attribute-based-filtering parameters

  output formatters:
    output formatter options

    -f {csv,json,table,value,yaml}, --format {csv,json,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple
                          columns
    --sort-column SORT_COLUMN
                          specify the column(s) to sort the data (columns specified first
                          have a priority, non-existing columns are ignored), can be repeated
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
    --fit-width           Fit the table to the display width. Implied if --max-width greater
                          than 0. Set the environment variable CLIFF_FIT_WIDTH=1 to always
                          enable
    --print-empty         Print empty table if there is no data to show.


6. Show subscription
^^^^^^^^^^^^^^^^^^^^

The `<vnf-fm-sub-id>` should be replaced with the 'ID' in result of
'4. Create subscription' or '5. List subscriptions'. In the following sample,
`4102e2a5-019b-40ea-8da2-579ecd5f17db` is used.

.. code-block:: console

  $ openstack vnffm sub show <vnf-fm-sub-id> --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------+-----------------------------------------------------------------------------------------------------+
  | Field        | Value                                                                                               |
  +--------------+-----------------------------------------------------------------------------------------------------+
  | Callback Uri | /nfvo/notify/alarm                                                                                  |
  | Filter       | {                                                                                                   |
  |              |     "vnfInstanceSubscriptionFilter": {                                                              |
  |              |         "vnfdIds": [                                                                                |
  |              |             "27b1c79c-5d78-43dd-a653-a1d6b9f3ea5d"                                                  |
  |              |         ],                                                                                          |
  |              |         "vnfProductsFromProviders": [                                                               |
  |              |             {                                                                                       |
  |              |                 "vnfProvider": "Company",                                                           |
  |              |                 "vnfProducts": [                                                                    |
  |              |                     {                                                                               |
  |              |                         "vnfProductName": "Sample VNF",                                             |
  |              |                         "versions": [                                                               |
  |              |                             {                                                                       |
  |              |                                 "vnfSoftwareVersion": "1.0",                                        |
  |              |                                 "vnfdVersions": [                                                   |
  |              |                                     "1.0",                                                          |
  |              |                                     "2.0"                                                           |
  |              |                                 ]                                                                   |
  |              |                             }                                                                       |
  |              |                         ]                                                                           |
  |              |                     }                                                                               |
  |              |                 ]                                                                                   |
  |              |             }                                                                                       |
  |              |         ],                                                                                          |
  |              |         "vnfInstanceIds": [                                                                         |
  |              |             "b0314420-0c9e-40e0-975e-4bf23b07d0c1"                                                  |
  |              |         ],                                                                                          |
  |              |         "vnfInstanceNames": [                                                                       |
  |              |             "test"                                                                                  |
  |              |         ]                                                                                           |
  |              |     },                                                                                              |
  |              |     "notificationTypes": [                                                                          |
  |              |         "AlarmNotification",                                                                        |
  |              |         "AlarmClearedNotification"                                                                  |
  |              |     ],                                                                                              |
  |              |     "faultyResourceTypes": [                                                                        |
  |              |         "COMPUTE"                                                                                   |
  |              |     ],                                                                                              |
  |              |     "perceivedSeverities": [                                                                        |
  |              |         "WARNING"                                                                                   |
  |              |     ],                                                                                              |
  |              |     "eventTypes": [                                                                                 |
  |              |         "PROCESSING_ERROR_ALARM"                                                                    |
  |              |     ],                                                                                              |
  |              |     "probableCauses": [                                                                             |
  |              |         "Process Terminated"                                                                        |
  |              |     ]                                                                                               |
  |              | }                                                                                                   |
  | ID           | 4102e2a5-019b-40ea-8da2-579ecd5f17db                                                                |
  | Links        | {                                                                                                   |
  |              |     "self": {                                                                                       |
  |              |         "href": "http://127.0.0.1:9890/vnffm/v1/subscriptions/4102e2a5-019b-40ea-8da2-579ecd5f17db" |
  |              |     }                                                                                               |
  |              | }                                                                                                   |
  +--------------+-----------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnffm sub show --os-tacker-api-version 2 --help
  usage: openstack vnffm sub show [-h] [-f {json,shell,table,value,yaml}]
                                  [-c COLUMN] [--noindent] [--prefix PREFIX]
                                  [--max-width <integer>] [--fit-width] [--print-empty]
                                  <vnf-fm-sub-id>

  Display VNF FM subscription details

  positional arguments:
  <vnf-fm-sub-id>
                        VNF FM subscription ID to display

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


7. Delete subscription
^^^^^^^^^^^^^^^^^^^^^^

The `<vnf-fm-sub-id>` should be replaced with the 'ID' in result of
'4. Create subscription' or '5. List subscriptions'. In the following sample,
`4102e2a5-019b-40ea-8da2-579ecd5f17db` is used.

.. code-block:: console

  $ openstack vnffm sub delete <vnf-fm-sub-id> --os-tacker-api-version 2


Result:

.. code-block:: console

  VNF FM subscription '4102e2a5-019b-40ea-8da2-579ecd5f17db' deleted successfully


Help:

.. code-block:: console

  $ openstack vnffm sub delete --os-tacker-api-version 2 --help
  usage: openstack vnffm sub delete [-h] <vnf-fm-sub-id> [<vnf-fm-sub-id> ...]

  Delete VNF FM subscription(s)

  positional arguments:
    <vnf-fm-sub-id>       VNF FM subscription ID(s) to delete

  optional arguments:
    -h, --help            show this help message and exit
