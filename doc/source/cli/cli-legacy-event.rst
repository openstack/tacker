================
Event Management
================

This document describes how to manage Event with CLI in Tacker.

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

CLI reference for Event Management
----------------------------------

1. List Events
^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack nfv event list


Result:

.. code-block:: console

  +----+---------------+--------------------------------------+-------------------+------------+---------------------+
  | ID | Resource Type | Resource ID                          | Resource State    | Event Type | Timestamp           |
  +----+---------------+--------------------------------------+-------------------+------------+---------------------+
  |  1 | vim           | aacb3c7f-d532-44d9-b8ed-49e2b30114aa | PENDING           | CREATE     | 2020-08-12 02:28:22 |
  |  2 | vim           | aacb3c7f-d532-44d9-b8ed-49e2b30114aa | REACHABLE         | MONITOR    | 2020-08-12 02:28:23 |
  |  3 | vim           | aacb3c7f-d532-44d9-b8ed-49e2b30114aa | REACHABLE         | UPDATE     | 2020-08-12 02:40:40 |
  |  4 | vnfd          | 94f2b44c-06f7-4d43-a2bb-dcd54f44d0f5 | OnBoarded         | CREATE     | 2020-08-13 05:52:07 |
  |  5 | vnf           | 4ffb436f-7f2c-4df1-96c4-38e9208261fd | PENDING_CREATE    | CREATE     | 2020-08-13 05:53:45 |
  |  6 | vnf           | 4ffb436f-7f2c-4df1-96c4-38e9208261fd | ACTIVE            | CREATE     | 2020-08-13 05:53:45 |
  |  7 | vnf           | 83fb8124-b475-400f-b0eb-f2b6741eeedc | PENDING_CREATE    | CREATE     | 2020-08-13 05:54:07 |
  |  8 | vnf           | 83fb8124-b475-400f-b0eb-f2b6741eeedc | ACTIVE            | CREATE     | 2020-08-13 05:54:07 |
  +----+---------------+--------------------------------------+-------------------+------------+---------------------+


Help:

.. code-block:: console

  $ openstack nfv event list --help
  usage: openstack nfv event list [-h] [-f {csv,json,table,value,yaml}]
                                  [-c COLUMN]
                                  [--quote {all,minimal,none,nonnumeric}]
                                  [--noindent] [--max-width <integer>]
                                  [--fit-width] [--print-empty]
                                  [--sort-column SORT_COLUMN] [--id ID]
                                  [--resource-type RESOURCE_TYPE]
                                  [--resource-id RESOURCE_ID]
                                  [--resource-state RESOURCE_STATE]
                                  [--event-type EVENT_TYPE] [--long]

  List events of resources.

  optional arguments:
    -h, --help            show this help message and exit
    --id ID               id of the event to look up.
    --resource-type RESOURCE_TYPE
                          resource type of the events to look up.
    --resource-id RESOURCE_ID
                          resource id of the events to look up.
    --resource-state RESOURCE_STATE
                          resource state of the events to look up.
    --event-type EVENT_TYPE
                          event type of the events to look up.
    --long                List additional fields in output


2. Show Event
^^^^^^^^^^^^^

.. code-block:: console

  $ openstack nfv event show <ID: 1>


Result:

.. code-block:: console

  +----------------+--------------------------------------+
  | Field          | Value                                |
  +----------------+--------------------------------------+
  | event_details  |                                      |
  | event_type     | CREATE                               |
  | id             | 1                                    |
  | resource_id    | aacb3c7f-d532-44d9-b8ed-49e2b30114aa |
  | resource_state | PENDING                              |
  | resource_type  | vim                                  |
  | timestamp      | 2020-08-12 02:28:22                  |
  +----------------+--------------------------------------+


Help:

.. code-block:: console

  $ openstack nfv event show --help
  usage: openstack nfv event show [-h] [-f {json,shell,table,value,yaml}]
                                  [-c COLUMN] [--noindent] [--prefix PREFIX]
                                  [--max-width <integer>] [--fit-width]
                                  [--print-empty]
                                  ID

  Show event given the event id.

  positional arguments:
    ID                    ID of event to display

  optional arguments:
    -h, --help            show this help message and exit
