======================
VNF Package Management
======================

This document describes how to manage VNF Package with CLI in Tacker.

.. note::

  The content of this document has been confirmed to work
  using the following VNF package.

  * `vnfpkgm1 for 2024.1 Caracal`_


Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

CLI Reference for VNF Package Management
----------------------------------------

1. Create VNF Package Info
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf package create


Result:

.. code-block:: console

  +-------------------+-------------------------------------------------------------------------------------------------+
  | Field             | Value                                                                                           |
  +-------------------+-------------------------------------------------------------------------------------------------+
  | ID                | e499a778-1a25-4bd0-88e2-835fb50a2086                                                            |
  | Links             | {                                                                                               |
  |                   |     "self": {                                                                                   |
  |                   |         "href": "/vnfpkgm/v1/vnf_packages/e499a778-1a25-4bd0-88e2-835fb50a2086"                 |
  |                   |     },                                                                                          |
  |                   |     "packageContent": {                                                                         |
  |                   |         "href": "/vnfpkgm/v1/vnf_packages/e499a778-1a25-4bd0-88e2-835fb50a2086/package_content" |
  |                   |     }                                                                                           |
  |                   | }                                                                                               |
  | Onboarding State  | CREATED                                                                                         |
  | Operational State | DISABLED                                                                                        |
  | Usage State       | NOT_IN_USE                                                                                      |
  | User Defined Data | {}                                                                                              |
  +-------------------+-------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf package create --help
  usage: openstack vnf package create [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                      [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                      [--fit-width] [--print-empty] [--user-data <key=value>]

  Create a new VNF Package

  options:
    -h, --help            show this help message and exit
    --user-data <key=value>
                          User defined data for the VNF package (repeat option to set multiple user defined
                          data)

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


2. Upload VNF Package
^^^^^^^^^^^^^^^^^^^^^

The `VNFPKG_ID` and `SAMPLE_CSAR.zip` should be replaced with
the ID of VNF Package and the path of VNF Package zip file
that will be uploaded, respectively.

.. code-block:: console

  $ openstack vnf package upload --path SAMPLE_CSAR.zip VNFPKG_ID


Result:

.. code-block:: console

  Upload request for VNF package e499a778-1a25-4bd0-88e2-835fb50a2086 has been accepted.


Help:

.. code-block:: console

  $ openstack vnf package upload --help
  usage: openstack vnf package upload [-h] (--path <file> | --url <Uri>)
                                      [--user-name <user-name>] [--password <password>]
                                      <vnf-package>

  Upload VNF Package

  positional arguments:
    <vnf-package>
                          VNF package ID

  options:
    -h, --help            show this help message and exit
    --path <file>
                          Upload VNF CSAR package from local file
    --url <Uri>   Uri of the VNF package content
    --user-name <user-name>
                          User name for authentication
    --password <password>
                          Password for authentication

  This command is provided by the python-tackerclient plugin.


3. Fetch VNF Package
^^^^^^^^^^^^^^^^^^^^

The `VNFPKG_ID` and the `DOWNLOAD_SAMPLE_CSAR.zip` should be replaced
with the ID of VNF Package and the path of VNF Package zip file
that will be downloaded, respectively.

.. code-block:: console

  $ openstack vnf package download --file DOWNLOAD_SAMPLE_CSAR.zip \
    VNFPKG_ID


Help:

.. code-block:: console

  $ openstack vnf package download --help
  usage: openstack vnf package download [-h] [--file <FILE>] [--vnfd] [--type <type>]
                                        <vnf-package>

  Download VNF package contents or VNFD of an on-boarded VNF package.

  positional arguments:
    <vnf-package>
                          VNF package ID

  options:
    -h, --help            show this help message and exit
    --file <FILE>
                          Local file to save downloaded VNF Package or VNFD data. If this is not specified and
                          there is no redirection then data will not be saved.
    --vnfd                Download VNFD of an on-boarded vnf package.
    --type <type>
                          Provide text/plain when VNFD is implemented as a single YAML file otherwise use
                          application/zip. If you are not aware whether VNFD is a single or multiple yaml
                          files, then you can specify 'both' option value. Provide this option only when
                          --vnfd is set.

  This command is provided by the python-tackerclient plugin.


4. Fetch VNF Package Artifacts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `VNFPKG_ID`, `DOWNLOAD_FILE_PATH` and `ARTIFACT_PATH` should be replaced
with the ID of VNF Package, the path of artifact file that will be downloaded
and the artifact file path from the target VNF Package, respectively.

.. code-block:: console

  $ openstack vnf package artifact download --file DOWNLOAD_FILE_PATH \
    VNFPKG_ID ARTIFACT_PATH


Help:

.. code-block:: console

  $ openstack vnf package artifact download --help
  usage: openstack vnf package artifact download [-h] [--file <FILE>]
                                                 <vnf-package> <artifact-path>

  Download VNF package artifact of an on-boarded VNF package.

  positional arguments:
    <vnf-package>
                          VNF package ID
    <artifact-path>
                          The artifact file's path

  options:
    -h, --help            show this help message and exit
    --file <FILE>
                          Local file to save downloaded VNF Package artifact file data. If this is not
                          specified and there is no redirection then data will not be saved.

  This command is provided by the python-tackerclient plugin.


5. List VNF Package
^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf package list


Result:

.. code-block:: console

  +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
  | Id                                   | Vnf Product Name | Onboarding State | Usage State | Operational State | Links                                                                                           |
  +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
  | e499a778-1a25-4bd0-88e2-835fb50a2086 | Sample VNF       | ONBOARDED        | NOT_IN_USE  | ENABLED           | {                                                                                               |
  |                                      |                  |                  |             |                   |     "self": {                                                                                   |
  |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/e499a778-1a25-4bd0-88e2-835fb50a2086"                 |
  |                                      |                  |                  |             |                   |     },                                                                                          |
  |                                      |                  |                  |             |                   |     "packageContent": {                                                                         |
  |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/e499a778-1a25-4bd0-88e2-835fb50a2086/package_content" |
  |                                      |                  |                  |             |                   |     }                                                                                           |
  |                                      |                  |                  |             |                   | }                                                                                               |
  +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf package list --help
  usage: openstack vnf package list [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN]
                                    [--quote {all,minimal,none,nonnumeric}] [--noindent]
                                    [--max-width <integer>] [--fit-width] [--print-empty]
                                    [--sort-column SORT_COLUMN] [--sort-ascending | --sort-descending]
                                    [--filter <filter>]
                                    [--all_fields | --fields fields | --exclude_fields exclude-fields]
                                    [--exclude_default]

  List VNF Packages

  options:
    -h, --help            show this help message and exit
    --filter <filter>
                          Atrribute-based-filtering parameters
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


6. Show VNF Package
^^^^^^^^^^^^^^^^^^^

The `VNFPKG_ID` should be replaced with the ID of VNF Package.

.. code-block:: console

  $ openstack vnf package show VNFPKG_ID


Result:

.. code-block:: console

  +----------------------+------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field                | Value                                                                                                                                          |
  +----------------------+------------------------------------------------------------------------------------------------------------------------------------------------+
  | Additional Artifacts | [                                                                                                                                              |
  |                      |     {                                                                                                                                          |
  |                      |         "artifactPath": "Files/kubernetes/deployment.yaml",                                                                                    |
  |                      |         "checksum": {                                                                                                                          |
  |                      |             "hash": "8115e59f56044a44f472964312f0f0770f465f5c734d70ea7061bdf0b5f28ca1",                                                        |
  |                      |             "algorithm": "SHA-256"                                                                                                             |
  |                      |         },                                                                                                                                     |
  |                      |         "metadata": {}                                                                                                                         |
  |                      |     },                                                                                                                                         |
  |                      |     {                                                                                                                                          |
  |                      |         "artifactPath": "Scripts/install.sh",                                                                                                  |
  |                      |         "checksum": {                                                                                                                          |
  |                      |             "hash": "27bbdb25d8f4ed6d07d6f6581b86515e8b2f0059b236ef7b6f50d6674b34f02a",                                                        |
  |                      |             "algorithm": "SHA-256"                                                                                                             |
  |                      |         },                                                                                                                                     |
  |                      |         "metadata": {}                                                                                                                         |
  |                      |     }                                                                                                                                          |
  |                      | ]                                                                                                                                              |
  | Checksum             | {                                                                                                                                              |
  |                      |     "algorithm": "sha512",                                                                                                                     |
  |                      |     "hash": "a76efa02d9178362e39dc0457db510d8e6a8f65c01df3feaca34bd9eddfeeae8f43ae626263cf438763652690dea447f42c6d08fe17a87687d94baa5f643f96c" |
  |                      | }                                                                                                                                              |
  | ID                   | e499a778-1a25-4bd0-88e2-835fb50a2086                                                                                                           |
  | Links                | {                                                                                                                                              |
  |                      |     "self": {                                                                                                                                  |
  |                      |         "href": "/vnfpkgm/v1/vnf_packages/e499a778-1a25-4bd0-88e2-835fb50a2086"                                                                |
  |                      |     },                                                                                                                                         |
  |                      |     "packageContent": {                                                                                                                        |
  |                      |         "href": "/vnfpkgm/v1/vnf_packages/e499a778-1a25-4bd0-88e2-835fb50a2086/package_content"                                                |
  |                      |     }                                                                                                                                          |
  |                      | }                                                                                                                                              |
  | Onboarding State     | ONBOARDED                                                                                                                                      |
  | Operational State    | ENABLED                                                                                                                                        |
  | Software Images      | [                                                                                                                                              |
  |                      |     {                                                                                                                                          |
  |                      |         "provider": "",                                                                                                                        |
  |                      |         "version": "0.5.2",                                                                                                                    |
  |                      |         "diskFormat": "qcow2",                                                                                                                 |
  |                      |         "name": "Software of VDU1",                                                                                                            |
  |                      |         "createdAt": "2024-05-24 05:05:15+00:00",                                                                                              |
  |                      |         "size": 1879048192,                                                                                                                    |
  |                      |         "minDisk": 1000000000,                                                                                                                 |
  |                      |         "minRam": 0,                                                                                                                           |
  |                      |         "id": "VDU1",                                                                                                                          |
  |                      |         "imagePath": "Files/images/cirros-0.5.2-x86_64-disk.img",                                                                              |
  |                      |         "containerFormat": "bare",                                                                                                             |
  |                      |         "checksum": {                                                                                                                          |
  |                      |             "algorithm": "sha-256",                                                                                                            |
  |                      |             "hash": "932fcae93574e242dc3d772d5235061747dfe537668443a1f0567d893614b464"                                                         |
  |                      |         },                                                                                                                                     |
  |                      |         "userMetadata": {}                                                                                                                     |
  |                      |     },                                                                                                                                         |
  |                      |     {                                                                                                                                          |
  |                      |         "provider": "",                                                                                                                        |
  |                      |         "version": "0.5.2",                                                                                                                    |
  |                      |         "diskFormat": "qcow2",                                                                                                                 |
  |                      |         "name": "VrtualStorage",                                                                                                               |
  |                      |         "createdAt": "2024-05-24 05:05:15+00:00",                                                                                              |
  |                      |         "size": 2000000000,                                                                                                                    |
  |                      |         "minDisk": 2000000000,                                                                                                                 |
  |                      |         "minRam": 8590458880,                                                                                                                  |
  |                      |         "id": "VirtualStorage",                                                                                                                |
  |                      |         "imagePath": "Files/images/cirros-0.5.2-x86_64-disk.img",                                                                              |
  |                      |         "containerFormat": "bare",                                                                                                             |
  |                      |         "checksum": {                                                                                                                          |
  |                      |             "algorithm": "sha-256",                                                                                                            |
  |                      |             "hash": "932fcae93574e242dc3d772d5235061747dfe537668443a1f0567d893614b464"                                                         |
  |                      |         },                                                                                                                                     |
  |                      |         "userMetadata": {}                                                                                                                     |
  |                      |     }                                                                                                                                          |
  |                      | ]                                                                                                                                              |
  | Usage State          | NOT_IN_USE                                                                                                                                     |
  | User Defined Data    | {}                                                                                                                                             |
  | VNF Product Name     | Sample VNF                                                                                                                                     |
  | VNF Provider         | Company                                                                                                                                        |
  | VNF Software Version | 1.0                                                                                                                                            |
  | VNFD ID              | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177                                                                                                           |
  | VNFD Version         | 1.0                                                                                                                                            |
  +----------------------+------------------------------------------------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf package show --help
  usage: openstack vnf package show [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                    [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                    [--fit-width] [--print-empty]
                                    <vnf-package>

  Show VNF Package Details

  positional arguments:
    <vnf-package>
                          VNF package ID

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


7. Update VNF Package Info
^^^^^^^^^^^^^^^^^^^^^^^^^^

The `VNFPKG_ID` should be replaced with the ID of VNF Package.

.. code-block:: console

  $ openstack vnf package update --operational-state 'DISABLED' VNFPKG_ID


Result:

.. code-block:: console

  +-------------------+----------+
  | Field             | Value    |
  +-------------------+----------+
  | Operational State | DISABLED |
  +-------------------+----------+


Help:

.. code-block:: console

  $ openstack vnf package update --help
  usage: openstack vnf package update [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                      [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                      [--fit-width] [--print-empty]
                                      [--operational-state <operational-state>]
                                      [--user-data <key=value>]
                                      <vnf-package>

  Update information about an individual VNF package

  positional arguments:
    <vnf-package>
                          VNF package ID

  options:
    -h, --help            show this help message and exit
    --operational-state <operational-state>
                          Change the operational state of VNF Package, Valid values are 'ENABLED' or
                          'DISABLED'.
    --user-data <key=value>
                          User defined data for the VNF package (repeat option to set multiple user defined
                          data)

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


8. Delete VNF Package
^^^^^^^^^^^^^^^^^^^^^

The `VNFPKG_ID` should be replaced with the ID of VNF Package.

.. code-block:: console

  openstack vnf package delete VNFPKG_ID


Result:

.. code-block:: console

  All specified vnf-package(s) deleted successfully


Help:

.. code-block:: console

  $ openstack vnf package delete --help
  usage: openstack vnf package delete [-h] <vnf-package> [<vnf-package> ...]

  Delete VNF Package

  positional arguments:
    <vnf-package>
                          Vnf package(s) ID to delete

  options:
    -h, --help            show this help message and exit

  This command is provided by the python-tackerclient plugin.


.. _vnfpkgm1 for 2024.1 Caracal:
  https://opendev.org/openstack/tacker/src/branch/stable/2024.1/samples/tests/etc/samples/etsi/nfv/vnfpkgm1
