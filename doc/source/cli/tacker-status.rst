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

.. code-block:: console

  $ tacker-status <category> <command> [<args>]


Description
===========

The ``tacker-status`` command is a tool that provides routines for checking the
status of a Tacker deployment.

Options
=======

The standard pattern for executing a ``tacker-status`` command is:

.. code-block:: console

  $ tacker-status <category> <command> [<args>]


You can run the command with `\-h` or `\-\-help` to see a list of
available command categories and usage.

.. code-block:: console

  $ tacker-status --help
  usage: tacker-status [-h] [--config-dir DIR] [--config-file PATH] {upgrade} ...

  options:
    -h, --help          show this help message and exit
    --config-dir DIR    Path to a config directory to pull `*.conf` files from. This file set is sorted, so as
                        to provide a predictable parse order if individual options are over-ridden. The set is
                        parsed after the file(s) specified via previous --config-file, arguments hence over-
                        ridden options in the directory take precedence. This option must be set from the
                        command-line.
    --config-file PATH  Path to a config file to use. Multiple config files can be specified, with values in
                        later files taking precedence. Defaults to None. This option must be set from the
                        command-line.

    {upgrade}


As shown in the above output, currently available category is:

* ``upgrade``

You can also see a list of all commands in category such as ``upgrade``
by running the command with category argument and `\-h` or `\-\-help` option.

.. code-block:: console

  $ tacker-status upgrade --help
  usage: tacker-status upgrade [-h] [--json] check

  positional arguments:
    check

  options:
    -h, --help  show this help message and exit
    --json      Output the results in JSON format. Default is to print results in human readable table format.


As shown in the above output, currently available command of
``upgrade`` category is:

* ``check``

Following sections describe the available categories
and arguments for ``tacker-status``.

Upgrade
~~~~~~~

``tacker-status upgrade check``
  Performs a release-specific readiness check before restarting services with
  new code. For example, missing or changed configuration options,
  incompatible object states, or other conditions that could lead to
  failures while upgrading.

  .. code-block:: console

    $ tacker-status upgrade check
    +-------------------------------------------+
    | Upgrade Check Results                     |
    +-------------------------------------------+
    | Check: Policy File JSON to YAML Migration |
    | Result: Success                           |
    | Details: None                             |
    +-------------------------------------------+


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


  **History of Upgrade checks**

  **0.11.0 (Stein)**

  * Add the functionality of tacker-status CLI for performing upgrade checks.

  **5.0.0 (Wallaby)**

  * Add check of the change the default value of '[oslo_policy] policy_file'
    config option from 'policy.json' to 'policy.yaml'.
