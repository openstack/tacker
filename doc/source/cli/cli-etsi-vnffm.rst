====================
VNF Fault Management
====================

This document describes how to manage VNF Fault with CLI in Tacker.

.. note::

  The content of this document has been confirmed to work
  using Tacker 2024.1 Caracal, Kubernetes 1.26, Prometheus 2.45 and
  AlertManager 0.26.


Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

CLI Reference for VNF Fault Management
--------------------------------------

.. note::

    To call the VNF FM API with ``vnffm`` subcommand,
    you need to use the option **\-\-os-tacker-api-version 2**


1. List alarms
^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnffm alarm list --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------------------------------+--------------------------------------+----------------+-----------------+--------------------+---------------------------------+
  | ID                                   | Managed Object Id                    | Ack State      | Event Type      | Perceived Severity | Probable Cause                  |
  +--------------------------------------+--------------------------------------+----------------+-----------------+--------------------+---------------------------------+
  | a5848818-3119-4dec-bdde-fed03c7f5cef | 703148ca-addc-4226-bee8-ef73d81dbbbf | UNACKNOWLEDGED | EQUIPMENT_ALARM | WARNING            | The server cannot be connected. |
  | c3bd2e65-dfbd-41d9-a491-ddfee29a71c0 | 703148ca-addc-4226-bee8-ef73d81dbbbf | UNACKNOWLEDGED | EQUIPMENT_ALARM | WARNING            | The server cannot be connected. |
  | de02ff55-dae3-4b2a-984e-c578f591a320 | 703148ca-addc-4226-bee8-ef73d81dbbbf | UNACKNOWLEDGED | EQUIPMENT_ALARM | WARNING            | Process Terminated              |
  +--------------------------------------+--------------------------------------+----------------+-----------------+--------------------+---------------------------------+


Help:

.. code-block:: console

  $ openstack vnffm alarm list --os-tacker-api-version 2 --help
  usage: openstack vnffm alarm list [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN]
                                    [--quote {all,minimal,none,nonnumeric}] [--noindent]
                                    [--max-width <integer>] [--fit-width] [--print-empty]
                                    [--sort-column SORT_COLUMN] [--sort-ascending | --sort-descending]
                                    [--filter <filter>]

  List VNF FM alarms

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


2. Show alarm
^^^^^^^^^^^^^

The `VNF_FM_ALARM_ID` should be replaced with the ID of VNF FM alarm.

.. code-block:: console

  $ openstack vnffm alarm show VNF_FM_ALARM_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  +----------------------------+------------------------------------------------------------------------------------------------------+
  | Field                      | Value                                                                                                |
  +----------------------------+------------------------------------------------------------------------------------------------------+
  | Ack State                  | UNACKNOWLEDGED                                                                                       |
  | Alarm Acknowledged Time    |                                                                                                      |
  | Alarm Changed Time         |                                                                                                      |
  | Alarm Cleared Time         |                                                                                                      |
  | Alarm Raised Time          | 2024-07-19T00:54:36Z                                                                                 |
  | Correlated Alarm Ids       |                                                                                                      |
  | Event Time                 | 2024-07-19T00:58:12Z                                                                                 |
  | Event Type                 | EQUIPMENT_ALARM                                                                                      |
  | Fault Details              | [                                                                                                    |
  |                            |     "fingerprint: 145e974be8f3163f",                                                                 |
  |                            |     "detail: fault details"                                                                          |
  |                            | ]                                                                                                    |
  | Fault Type                 | Server Down                                                                                          |
  | ID                         | c3bd2e65-dfbd-41d9-a491-ddfee29a71c0                                                                 |
  | Is Root Cause              | False                                                                                                |
  | Links                      | {                                                                                                    |
  |                            |     "self": {                                                                                        |
  |                            |         "href": "http://127.0.0.1:9890/vnffm/v1/alarms/c3bd2e65-dfbd-41d9-a491-ddfee29a71c0"         |
  |                            |     },                                                                                               |
  |                            |     "objectInstance": {                                                                              |
  |                            |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/703148ca-addc-4226-bee8-ef73d81dbbbf" |
  |                            |     }                                                                                                |
  |                            | }                                                                                                    |
  | Managed Object Id          | 703148ca-addc-4226-bee8-ef73d81dbbbf                                                                 |
  | Perceived Severity         | WARNING                                                                                              |
  | Probable Cause             | The server cannot be connected.                                                                      |
  | Root Cause Faulty Resource |                                                                                                      |
  | Vnfc Instance Ids          | [                                                                                                    |
  |                            |     "VDU2-vdu2-8499c98765-4mwd7"                                                                     |
  |                            | ]                                                                                                    |
  +----------------------------+------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnffm alarm show --os-tacker-api-version 2 --help
  usage: openstack vnffm alarm show [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                    [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                    [--fit-width] [--print-empty]
                                    <vnf-fm-alarm-id>

  Display VNF FM alarm details

  positional arguments:
    <vnf-fm-alarm-id>
                          VNF FM alarm ID to display

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


3. Update alarm
^^^^^^^^^^^^^^^

The `VNF_FM_ALARM_ID` should be replaced with the ID of VNF FM alarm.

.. code-block:: console

  $ openstack vnffm alarm update VNF_FM_ALARM_ID --ack-state ACKNOWLEDGED --os-tacker-api-version 2


Result:

.. code-block:: console

  +-----------+--------------+
  | Field     | Value        |
  +-----------+--------------+
  | Ack State | ACKNOWLEDGED |
  +-----------+--------------+


Help:

.. code-block:: console

  $ openstack vnffm alarm update --os-tacker-api-version 2 --help
  usage: openstack vnffm alarm update [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                      [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                      [--fit-width] [--print-empty] [--ack-state <ack-state>]
                                      <vnf-fm-alarm-id>

  Update information about an individual VNF FM alarm

  positional arguments:
    <vnf-fm-alarm-id>
                          VNF FM alarm ID to update.

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

  require arguments:
    --ack-state <ack-state>
                          Ask state can be 'ACKNOWLEDGED' or 'UNACKNOWLEDGED'.

  This command is provided by the python-tackerclient plugin.


4. Create subscription
^^^^^^^^^^^^^^^^^^^^^^

The `PARAM_FILE.json` should be replaced with the path of parameter json file
that will be used to create VNF FM subscription.

.. code-block:: console

  $ openstack vnffm sub create PARAM_FILE.json --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------+-----------------------------------------------------------------------------------------------------+
  | Field        | Value                                                                                               |
  +--------------+-----------------------------------------------------------------------------------------------------+
  | Callback Uri | http://127.0.0.1:9990/notification/callbackuri/703148ca-addc-4226-bee8-ef73d81dbbbf                 |
  | Filter       | {                                                                                                   |
  |              |     "vnfInstanceSubscriptionFilter": {                                                              |
  |              |         "vnfdIds": [                                                                                |
  |              |             "eb37da52-9d03-4544-a1b5-ff5664c7687d"                                                  |
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
  |              |             "703148ca-addc-4226-bee8-ef73d81dbbbf"                                                  |
  |              |         ],                                                                                          |
  |              |         "vnfInstanceNames": [                                                                       |
  |              |             "Sample VNF"                                                                            |
  |              |         ]                                                                                           |
  |              |     },                                                                                              |
  |              |     "notificationTypes": [                                                                          |
  |              |         "AlarmNotification"                                                                         |
  |              |     ],                                                                                              |
  |              |     "faultyResourceTypes": [                                                                        |
  |              |         "COMPUTE"                                                                                   |
  |              |     ],                                                                                              |
  |              |     "perceivedSeverities": [                                                                        |
  |              |         "WARNING"                                                                                   |
  |              |     ],                                                                                              |
  |              |     "eventTypes": [                                                                                 |
  |              |         "EQUIPMENT_ALARM"                                                                           |
  |              |     ],                                                                                              |
  |              |     "probableCauses": [                                                                             |
  |              |         "The server cannot be connected."                                                           |
  |              |     ]                                                                                               |
  |              | }                                                                                                   |
  | ID           | 2416b1fa-73db-42f3-8cef-2e05eb5bca6f                                                                |
  | Links        | {                                                                                                   |
  |              |     "self": {                                                                                       |
  |              |         "href": "http://127.0.0.1:9890/vnffm/v1/subscriptions/2416b1fa-73db-42f3-8cef-2e05eb5bca6f" |
  |              |     }                                                                                               |
  |              | }                                                                                                   |
  +--------------+-----------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnffm sub create --os-tacker-api-version 2 --help
  usage: openstack vnffm sub create [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                    [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                    [--fit-width] [--print-empty]
                                    <param-file>

  Create a new VNF FM subscription

  positional arguments:
    <param-file>  Specify create VNF FM subscription request parameters in a json file.

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


5. List subscriptions
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnffm sub list --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------------------------------+-------------------------------------------------------------------------------------+
  | ID                                   | Callback Uri                                                                        |
  +--------------------------------------+-------------------------------------------------------------------------------------+
  | 2416b1fa-73db-42f3-8cef-2e05eb5bca6f | http://127.0.0.1:9990/notification/callbackuri/703148ca-addc-4226-bee8-ef73d81dbbbf |
  +--------------------------------------+-------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnffm sub list --os-tacker-api-version 2 --help
  usage: openstack vnffm sub list [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN]
                                  [--quote {all,minimal,none,nonnumeric}] [--noindent]
                                  [--max-width <integer>] [--fit-width] [--print-empty]
                                  [--sort-column SORT_COLUMN] [--sort-ascending | --sort-descending]
                                  [--filter <filter>]

  List VNF FM subs

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


6. Show subscription
^^^^^^^^^^^^^^^^^^^^

The `VNF_FM_SUB_ID` should be replaced with the ID of VNF FM subscription.

.. code-block:: console

  $ openstack vnffm sub show VNF_FM_SUB_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------+-----------------------------------------------------------------------------------------------------+
  | Field        | Value                                                                                               |
  +--------------+-----------------------------------------------------------------------------------------------------+
  | Callback Uri | http://127.0.0.1:9990/notification/callbackuri/703148ca-addc-4226-bee8-ef73d81dbbbf                 |
  | Filter       | {                                                                                                   |
  |              |     "vnfInstanceSubscriptionFilter": {                                                              |
  |              |         "vnfdIds": [                                                                                |
  |              |             "eb37da52-9d03-4544-a1b5-ff5664c7687d"                                                  |
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
  |              |             "703148ca-addc-4226-bee8-ef73d81dbbbf"                                                  |
  |              |         ],                                                                                          |
  |              |         "vnfInstanceNames": [                                                                       |
  |              |             "Sample VNF"                                                                            |
  |              |         ]                                                                                           |
  |              |     },                                                                                              |
  |              |     "notificationTypes": [                                                                          |
  |              |         "AlarmNotification"                                                                         |
  |              |     ],                                                                                              |
  |              |     "faultyResourceTypes": [                                                                        |
  |              |         "COMPUTE"                                                                                   |
  |              |     ],                                                                                              |
  |              |     "perceivedSeverities": [                                                                        |
  |              |         "WARNING"                                                                                   |
  |              |     ],                                                                                              |
  |              |     "eventTypes": [                                                                                 |
  |              |         "EQUIPMENT_ALARM"                                                                           |
  |              |     ],                                                                                              |
  |              |     "probableCauses": [                                                                             |
  |              |         "The server cannot be connected."                                                           |
  |              |     ]                                                                                               |
  |              | }                                                                                                   |
  | ID           | 2416b1fa-73db-42f3-8cef-2e05eb5bca6f                                                                |
  | Links        | {                                                                                                   |
  |              |     "self": {                                                                                       |
  |              |         "href": "http://127.0.0.1:9890/vnffm/v1/subscriptions/2416b1fa-73db-42f3-8cef-2e05eb5bca6f" |
  |              |     }                                                                                               |
  |              | }                                                                                                   |
  +--------------+-----------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnffm sub show --os-tacker-api-version 2 --help
  usage: openstack vnffm sub show [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                  [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                  [--fit-width] [--print-empty]
                                  <vnf-fm-sub-id>

  Display VNF FM subscription details

  positional arguments:
    <vnf-fm-sub-id>
                          VNF FM subscription ID to display

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


7. Delete subscription
^^^^^^^^^^^^^^^^^^^^^^

The `VNF_FM_SUB_ID` should be replaced with the ID of VNF FM subscription.

.. code-block:: console

  $ openstack vnffm sub delete VNF_FM_SUB_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  VNF FM subscription '2416b1fa-73db-42f3-8cef-2e05eb5bca6f' deleted successfully


Help:

.. code-block:: console

  $ openstack vnffm sub delete --os-tacker-api-version 2 --help
  usage: openstack vnffm sub delete [-h] <vnf-fm-sub-id> [<vnf-fm-sub-id> ...]

  Delete VNF FM subscription(s)

  positional arguments:
    <vnf-fm-sub-id>
                          VNF FM subscription ID(s) to delete

  options:
    -h, --help            show this help message and exit

  This command is provided by the python-tackerclient plugin.
