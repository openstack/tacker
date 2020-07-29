..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

Tacker Resource Events Usage Guide
==================================

Overview
--------

OpenStack Tacker supports capturing resource event information when the
tacker resources undergo create, update, delete, scale and monitor
operations. This information becomes useful to an admin for audit purposes.

Tacker Resources supporting Events
----------------------------------
As of Newton release, events information is captured for below:

- VNF

- VNFD

- VIM

Tacker supported event types
----------------------------
Below are the event types that are currently supported:

- CREATE

- DELETE

- MONITOR

- SCALE

- UPDATE

The above can be used as filters when listing events using tacker client.

Accessing Events
----------------

Tacker supports display of events to an end user via

- Horizon UI - a separate events tab per resource displays associated events.

- OpenStackClient CLI - supports below commands:
    - openstack nfv event show: Show detailed info for a given event ID.
    - openstack nfv event list: Lists all events for all resources.

NOTE: For more details on the syntax of these CLIs, refer to
`OpenStackClient CLI reference guide <https://docs.openstack.org/tacker/latest/admin/index.html>`_

OpenStackClient CLI usage examples to access resource lifecycle events
----------------------------------------------------------------------

1. The following command displays all the state transitions that occurred on
a long running VNF. The sample output illustrates a VNF that has
successfully gone through a scale out operation. Note, the <VNF Resource ID>
here is VNF's uuid.

.. code-block:: console

  openstack nfv event list --resource-id <VNF Resource ID>

  +----+---------------+-------------------+-------------------+------------+-------------------+---------------------+
  | ID | Resource Type | Resource ID       | Resource State    | Event Type | Timestamp         | Event Details       |
  +----+---------------+-------------------+-------------------+------------+-------------------+---------------------+
  | 13 | vnf           | 9dd7b2f1-e91e-418 | PENDING_CREATE    | CREATE     | 2016-09-21        | VNF UUID assigned.  |
  |    |               | 3-bcbe-           |                   |            | 20:12:37          |                     |
  |    |               | 34b80bdb18fb      |                   |            |                   |                     |
  | 14 | vnf           | 9dd7b2f1-e91e-418 | PENDING_CREATE    | CREATE     | 2016-09-21        | Infra Instance ID   |
  |    |               | 3-bcbe-           |                   |            | 20:13:09          | created: 3bd369e4-9 |
  |    |               | 34b80bdb18fb      |                   |            |                   | ee3-4e58-86e3-8acbb |
  |    |               |                   |                   |            |                   | dccedb5 and Mgmt    |
  |    |               |                   |                   |            |                   | URL set: {"VDU1":   |
  |    |               |                   |                   |            |                   | ["10.0.0.9",        |
  |    |               |                   |                   |            |                   | "10.0.0.2"],        |
  |    |               |                   |                   |            |                   | "VDU2":             |
  |    |               |                   |                   |            |                   | ["10.0.0.4",        |
  |    |               |                   |                   |            |                   | "10.0.0.5"]}        |
  | 15 | vnf           | 9dd7b2f1-e91e-418 | ACTIVE            | CREATE     | 2016-09-21        | VNF status updated  |
  |    |               | 3-bcbe-           |                   |            | 20:13:09          |                     |
  |    |               | 34b80bdb18fb      |                   |            |                   |                     |
  | 16 | vnf           | 9dd7b2f1-e91e-418 | PENDING_SCALE_OUT | SCALE      | 2016-09-21        |                     |
  |    |               | 3-bcbe-           |                   |            | 20:23:58          |                     |
  |    |               | 34b80bdb18fb      |                   |            |                   |                     |
  | 17 | vnf           | 9dd7b2f1-e91e-418 | ACTIVE            | SCALE      | 2016-09-21        |                     |
  |    |               | 3-bcbe-           |                   |            | 20:24:45          |                     |
  |    |               | 34b80bdb18fb      |                   |            |                   |                     |
  +----+---------------+-------------------+-------------------+------------+-------------------+---------------------+

2. The following command displays any reachability issues related to a VIM
site. The sample output illustrates a VIM that is reachable. Note, the
<VIM Resource ID> here is a VIM uuid.

.. code-block:: console

  openstack nfv event list --resource-id <VIM Resource ID>

  +----+---------------+---------------------+----------------+------------+---------------------+---------------+
  | ID | Resource Type | Resource ID         | Resource State | Event Type | Timestamp           | Event Details |
  +----+---------------+---------------------+----------------+------------+---------------------+---------------+
  |  1 | vim           | d8c11a53-876c-454a- | PENDING        | CREATE     | 2016-09-20 23:07:42 |               |
  |    |               | bad1-cb13ad057595   |                |            |                     |               |
  |  2 | vim           | d8c11a53-876c-454a- | REACHABLE      | MONITOR    | 2016-09-20 23:07:42 |               |
  |    |               | bad1-cb13ad057595   |                |            |                     |               |
  +----+---------------+---------------------+----------------+------------+---------------------+---------------+


Miscellaneous events command examples:
--------------------------------------

1. List all events for all resources from the beginning

.. code-block:: console

  openstack nfv event list

  +----+---------------+-----------------+----------------+------------+-----------------+-----------------+
  | ID | Resource Type | Resource ID     | Resource State | Event Type | Timestamp       | Event Details   |
  +----+---------------+-----------------+----------------+------------+-----------------+-----------------+
  |  1 | vim           | c89e5d9d-6d55-4 | PENDING        | CREATE     | 2016-09-10      |                 |
  |    |               | db1-bd67-30982f |                |            | 20:32:46        |                 |
  |    |               | 01133e          |                |            |                 |                 |
  |  2 | vim           | c89e5d9d-6d55-4 | REACHABLE      | MONITOR    | 2016-09-10      |                 |
  |    |               | db1-bd67-30982f |                |            | 20:32:46        |                 |
  |    |               | 01133e          |                |            |                 |                 |
  |  3 | vnfd          | afc0c662-5117-4 | Not Applicable | CREATE     | 2016-09-14      |                 |
  |    |               | 7a7-8088-02e9f8 |                |            | 05:17:30        |                 |
  |    |               | a3532b          |                |            |                 |                 |
  |  4 | vnf           | 52adaae4-36b5   | PENDING_CREATE | CREATE     | 2016-09-14      | VNF UUID        |
  |    |               | -41cf-acb5-32ab |                |            | 17:49:24        | assigned.       |
  |    |               | 8c109265        |                |            |                 |                 |
  |  5 | vnf           | 52adaae4-36b5   | PENDING_CREATE | CREATE     | 2016-09-14      | Infra Instance  |
  |    |               | -41cf-acb5-32ab |                |            | 17:49:51        | ID created:     |
  |    |               | 8c109265        |                |            |                 | 046dcb04-318d-4 |
  |    |               |                 |                |            |                 | ec9-8a23-19d9c1 |
  |    |               |                 |                |            |                 | f8c21d and Mgmt |
  |    |               |                 |                |            |                 | URL set:        |
  |    |               |                 |                |            |                 | {"VDU1": "192.1 |
  |    |               |                 |                |            |                 | 68.120.8"}      |
  |  6 | vnf           | 52adaae4-36b5   | ACTIVE         | CREATE     | 2016-09-14      | VNF status      |
  |    |               | -41cf-acb5-32ab |                |            | 17:49:51        | updated         |
  |    |               | 8c109265        |                |            |                 |                 |
  +----+---------------+-----------------+----------------+------------+-----------------+-----------------+

2. List all events for all resources given a certain event type

.. code-block:: console

  openstack nfv event list --event-type CREATE

  +----+---------------+-----------------+----------------+------------+-----------------+-----------------+
  | ID | Resource Type | Resource ID     | Resource State | Event Type | Timestamp       | Event Details   |
  +----+---------------+-----------------+----------------+------------+-----------------+-----------------+
  |  1 | vim           | c89e5d9d-6d55-4 | PENDING        | CREATE     | 2016-09-10      |                 |
  |    |               | db1-bd67-30982f |                |            | 20:32:46        |                 |
  |    |               | 01133e          |                |            |                 |                 |
  |  3 | vnfd          | afc0c662-5117-4 | ACTIVE         | CREATE     | 2016-09-14      |                 |
  |    |               | 7a7-8088-02e9f8 |                |            | 05:17:30        |                 |
  |    |               | a3532b          |                |            |                 |                 |
  |  4 | vnf           | 52adaae4-36b5   | PENDING_CREATE | CREATE     | 2016-09-14      | VNF UUID        |
  |    |               | -41cf-acb5-32ab |                |            | 17:49:24        | assigned.       |
  |    |               | 8c109265        |                |            |                 |                 |
  |  5 | vnf           | 52adaae4-36b5   | PENDING_CREATE | CREATE     | 2016-09-14      | Infra Instance  |
  |    |               | -41cf-acb5-32ab |                |            | 17:49:51        | ID created:     |
  |    |               | 8c109265        |                |            |                 | 046dcb04-318d-4 |
  |    |               |                 |                |            |                 | ec9-8a23-19d9c1 |
  |    |               |                 |                |            |                 | f8c21d and Mgmt |
  |    |               |                 |                |            |                 | URL set:        |
  |    |               |                 |                |            |                 | {"VDU1": "192.1 |
  |    |               |                 |                |            |                 | 68.120.8"}      |
  |  6 | vnf           | 52adaae4-36b5   | ACTIVE         | CREATE     | 2016-09-14      | VNF status      |
  |    |               | -41cf-acb5-32ab |                |            | 17:49:51        | updated         |
  |    |               | 8c109265        |                |            |                 |                 |
  +----+---------------+-----------------+----------------+------------+-----------------+-----------------+


3. List details for a specific event

.. code-block:: console

  openstack nfv event show 5

  +----------------+------------------------------------------------------------------------------------------+
  | Field          | Value                                                                                    |
  +----------------+------------------------------------------------------------------------------------------+
  | event_details  | Infra Instance ID created: 046dcb04-318d-4ec9-8a23-19d9c1f8c21d and Mgmt IP address set: |
  |                | {"VDU1": "192.168.120.8"}                                                                |
  | event_type     | CREATE                                                                                   |
  | id             | 5                                                                                        |
  | resource_id    | 52adaae4-36b5-41cf-acb5-32ab8c109265                                                     |
  | resource_state | PENDING_CREATE                                                                           |
  | resource_type  | vnf                                                                                      |
  | timestamp      | 2016-09-14 17:49:51                                                                      |
  +----------------+------------------------------------------------------------------------------------------+


Note for Tacker developers
--------------------------

If as a developer, you are creating new resources and would like to capture
event information for resource operations such as create, update, delete,
scale and monitor, you would need to :

- Import the module tacker.db.common_services.common_services_db to use the
  create_event() method for logging events.

- Make edits in the file tacker/plugins/common/constants.py if you would need
  to create new event types.
