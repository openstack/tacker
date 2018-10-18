..
      Copyright (c) 2018 NEC, Corp.
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

=============
tacker-status
=============

----------------------------------------
CLI interface for Tacker status commands
----------------------------------------

Synopsis
========

::

  tacker-status <category> <command> [<args>]

Description
===========

:program:`tacker-status` is a tool that provides routines for checking the
status of a Tacker deployment.

Options
=======

The standard pattern for executing a :program:`tacker-status` command is::

    tacker-status <category> <command> [<args>]

Run without arguments to see a list of available command categories::

    tacker-status

Categories are:

* ``upgrade``

Detailed descriptions are below:

You can also run with a category argument such as ``upgrade`` to see a list of
all commands in that category::

    tacker-status upgrade

These sections describe the available categories and arguments for
:program:`tacker-status`.

Upgrade
~~~~~~~

.. _tacker-status-checks:

``tacker-status upgrade check``
  Performs a release-specific readiness check before restarting services with
  new code. For example, missing or changed configuration options,
  incompatible object states, or other conditions that could lead to
  failures while upgrading.

  **Return Codes**

  .. list-table::
     :widths: 20 80
     :header-rows: 1

     * - Return code
       - Description
     * - 0
       - All upgrade readiness checks passed successfully and there is nothing
         to do.
     * - 1
       - At least one check encountered an issue and requires further
         investigation. This is considered a warning but the upgrade may be OK.
     * - 2
       - There was an upgrade status check failure that needs to be
         investigated. This should be considered something that stops an
         upgrade.
     * - 255
       - An unexpected error occurred.

  **History of Checks**

  **0.11.0 (Stein)**

  * Sample check to be filled in with checks as they are added in Stein.
