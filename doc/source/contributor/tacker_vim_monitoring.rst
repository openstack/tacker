..
      Copyright 2014-2015 OpenStack Foundation
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

===============================
Mistral workflow VIM monitoring
===============================

For the purpose to make tacker server scale, the mistral workflow is used to
re-implement the VIM monitoring feature.

The main monitoring process is like this:

- user registers a VIM
- tacker server saves it into database
- tacker server generates a mistral workflow and executes it
- the VIM monitor mistral action is executed and do the monitoring, if there
  is status change, it will RPC call conductor
- the conductor changes the VIM status


Feature exploration
===================

Firstly register a VIM:

.. code-block:: console

    $ openstack vim register --config-file ~/testvim_config.yaml testvim2 -c id -c name -c status
    Created a new vim:
    +--------+--------------------------------------+
    | Field  | Value                                |
    +--------+--------------------------------------+
    | id     | 4406cf8f-f2af-46cc-bfb9-e00add5805b7 |
    | name   | testvim2                             |
    | status | PENDING                              |
    +--------+--------------------------------------+

..

The registered VIM's id is '4406cf8f-f2af-46cc-bfb9-e00add5805b7', after this,
there is a mistral workflow named as
'vim_id_4406cf8f-f2af-46cc-bfb9-e00add5805b7', is generated in mistral:

.. code-block:: console

    $ openstack workflow list --filter name=vim_id_4406cf8f-f2af-46cc-bfb9-e00add5805b7 -c ID -c Name
    +--------------------------------------+---------------------------------------------+
    | ID                                   | Name                                        |
    +--------------------------------------+---------------------------------------------+
    | 0cd0deff-6132-4ee2-a181-1c877cd594cc | vim_id_4406cf8f-f2af-46cc-bfb9-e00add5805b7 |
    +--------------------------------------+---------------------------------------------+

..

and it is executed:

.. code-block:: console

    $ openstack workflow execution list --filter workflow_name=vim_id_4406cf8f-f2af-46cc-bfb9-e00add5805b7 -c ID -c 'Workflow name' -c State
    +--------------------------------------+---------------------------------------------+---------+
    | ID                                   | Workflow name                               | State   |
    +--------------------------------------+---------------------------------------------+---------+
    | 99ced0e2-be09-4219-ab94-299df8ee8789 | vim_id_4406cf8f-f2af-46cc-bfb9-e00add5805b7 | RUNNING |
    +--------------------------------------+---------------------------------------------+---------+

..

The monitoring task is running too:

.. code-block:: console

    $ openstack task execution list --filter workflow_name=vim_id_4406cf8f-f2af-46cc-bfb9-e00add5805b7 -c ID -c 'Workflow name' -c Name  -c State
    +--------------------------------------+-----------------------------+---------------------------------------------+---------+
    | ID                                   | Name                        | Workflow name                               | State   |
    +--------------------------------------+-----------------------------+---------------------------------------------+---------+
    | f2fe2904-6ff2-4531-9bd0-4c998ef1515f | monitor_ping_vimPingVIMTASK | vim_id_4406cf8f-f2af-46cc-bfb9-e00add5805b7 | RUNNING |
    +--------------------------------------+-----------------------------+---------------------------------------------+---------+

..

Of course, the VIM's state is in 'REACHABLE' status:

.. code-block:: console

    $ openstack vim list --name testvim2 -c id -c name -c status
    +--------------------------------------+----------+-----------+
    | id                                   | name     | status    |
    +--------------------------------------+----------+-----------+
    | 4406cf8f-f2af-46cc-bfb9-e00add5805b7 | testvim2 | REACHABLE |
    +--------------------------------------+----------+-----------+

..

The deletion of VIM will lead to removal of all of these mistral resources.


Rabbitmq queues
===============

Each mistral VIM monitoring action is listening on three queues:

.. code-block:: console

    ~/tacker$ sudo rabbitmqctl list_queues | grep -i KILL_ACTION
    KILL_ACTION    0
    KILL_ACTION.4406cf8f-f2af-46cc-bfb9-e00add5805b7    0
    KILL_ACTION_fanout_a8118e2e18b9443986a1b37f7b082ab9    0

..

But only KILL_ACTION with VIM id as suffix is used.
