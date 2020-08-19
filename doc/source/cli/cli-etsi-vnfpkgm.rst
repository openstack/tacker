======================
VNF Package Management
======================

This document describes how to manage VNF Package with CLI in Tacker.

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

CLI Reference for VNF Package Management
----------------------------------------

.. TODO(yoshito-ito): add Fetch VNF Package artifacts CLI reference.

1. Create VNF Package Info
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf package create


Result:

.. code-block:: console

  +-------------------+----------------------------------------------------------------------------------------------------+
  | Field             | Value                                                                                              |
  +-------------------+----------------------------------------------------------------------------------------------------+
  | ID                | e712a702-741f-4093-a971-b3ad69411ac1                                                               |
  | Links             | packageContent=href=/vnfpkgm/v1/vnf_packages/e712a702-741f-4093-a971-b3ad69411ac1/package_content, |
  |                   | self=href=s/vnfpkgm/v1/vnf_packages/e712a702-741f-4093-a971-b3ad69411ac1                           |
  | Onboarding State  | CREATED                                                                                            |
  | Operational State | DISABLED                                                                                           |
  | Usage State       | NOT_IN_USE                                                                                         |
  | User Defined Data |                                                                                                    |
  +-------------------+----------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf package create --help
  usage: openstack vnf package create [-h] [-f {json,shell,table,value,yaml}]
                                      [-c COLUMN] [--noindent] [--prefix PREFIX]
                                      [--max-width <integer>] [--fit-width]
                                      [--print-empty] [--user-data <key=value>]

  Create a new VNF Package

  optional arguments:
    -h, --help            show this help message and exit
    --user-data <key=value>
                          User defined data for the VNF package (repeat option
                          to set multiple user defined data)


2. Upload VNF Package
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf package upload --path sample_csar.zip \
      <ID: e712a702-741f-4093-a971-b3ad69411ac1>


Result:

.. code-block:: console

  Upload request for VNF package e712a702-741f-4093-a971-b3ad69411ac1 has been accepted.


Help:

.. code-block:: console

  $ openstack vnf package upload --help
  usage: openstack vnf package upload [-h] (--path <file> | --url <Uri>)
                                      [--user-name <user-name>]
                                      [--password <password>]
                                      <vnf-package>

  Upload VNF Package

  positional arguments:
    <vnf-package>         VNF package ID

  optional arguments:
    -h, --help            show this help message and exit
    --path <file>         Upload VNF CSAR package from local file
    --url <Uri>           Uri of the VNF package content
    --user-name <user-name>
                          User name for authentication
    --password <password>
                          Password for authentication


3. Fetch VNF Package
^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf package download --file <FILE: download_sample_csar.zip> \
      <ID: e712a702-741f-4093-a971-b3ad69411ac1>


Help:

.. code-block:: console

  $ openstack vnf package download --help
  usage: openstack vnf package download [-h] [--file <FILE>] [--vnfd]
                                        [--type <type>]
                                        <vnf-package>

  Download VNF package contents or VNFD of an on-boarded VNF package.

  positional arguments:
    <vnf-package>  VNF package ID

  optional arguments:
    -h, --help     show this help message and exit
    --file <FILE>  Local file to save downloaded VNF Package or VNFD data. If
                  this is not specified and there is no redirection then data
                  will not be saved.
    --vnfd         Download VNFD of an on-boarded vnf package.
    --type <type>  Provide text/plain when VNFD is implemented as a single YAML
                  file otherwise use application/zip. If you are not aware
                  whether VNFD is a single or multiple yaml files, then you can
                  specify 'both' option value. Provide this option only when
                  --vnfd is set.

4. List VNF Package
^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf package list


Result:

.. code-block:: console

  +--------------------------------------+------------------+------------------+-------------+-------------------+
  | Id                                   | Vnf Product Name | Onboarding State | Usage State | Operational State |
  +--------------------------------------+------------------+------------------+-------------+-------------------+
  | e712a702-741f-4093-a971-b3ad69411ac1 | Sample VNF       | ONBOARDED        | NOT_IN_USE  | ENABLED           |
  +--------------------------------------+------------------+------------------+-------------+-------------------+


Help:

.. code-block:: console

  $ openstack vnf package list --help
  usage: openstack vnf package list [-h] [-f {csv,json,table,value,yaml}]
                                    [-c COLUMN]
                                    [--quote {all,minimal,none,nonnumeric}]
                                    [--noindent] [--max-width <integer>]
                                    [--fit-width] [--print-empty]
                                    [--sort-column SORT_COLUMN]
                                    [--filter <filter>]
                                    [--all_fields | --fields fields | --exclude_fields exclude-fields]
                                    [--exclude_default]

  List VNF Packages

  optional arguments:
    -h, --help            show this help message and exit
    --filter <filter>     Atrribute-based-filtering parameters
    --all_fields          Include all complex attributes in the response
    --fields fields       Complex attributes to be included into the response
    --exclude_fields exclude-fields
                          Complex attributes to be excluded from the response
    --exclude_default     Indicates to exclude all complex attributes from the
                          response. This argument can be used alone or with
                          --fields and --filter. For all other combinations
                          tacker server will throw bad request error


5. Show VNF Package
^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf package show <ID: e712a702-741f-4093-a971-b3ad69411ac1>


Result:

.. code-block:: console

  +----------------------+------------------------------------------------------------------------------------------------------------+
  | Field                | Value                                                                                                      |
  +----------------------+------------------------------------------------------------------------------------------------------------+
  | Checksum             | algorithm=sha512, hash=f8eb9883f04901af2d6e09d3621b7bbb37a36a89b076d322cc5994f3c5264854d1a0137efb23e61be96 |
  |                      | 9a7ba60989715b3e3feced9d7c582ffaaec6b5a89e2b1                                                              |
  | ID                   | e712a702-741f-4093-a971-b3ad69411ac1                                                                       |
  | Links                | packageContent=href=/vnfpkgm/v1/vnf_packages/e712a702-741f-4093-a971-b3ad69411ac1/package_content,         |
  |                      | self=href=/vnfpkgm/v1/vnf_packages/e712a702-741f-4093-a971-b3ad69411ac1                                    |
  | Onboarding State     | ONBOARDED                                                                                                  |
  | Operational State    | ENABLED                                                                                                    |
  | Software Images      | [{'diskFormat': 'qcow2', 'minDisk': 1, 'minRam': 0, 'imagePath': '', 'size': 1, 'createdAt': '2020-05-28   |
  |                      | 01:50:14+00:00', 'containerFormat': 'bare', 'version': '0.4.0', 'provider': '', 'id': 'VDU1', 'name':      |
  |                      | 'Software of VDU1', 'checksum': {'algorithm': 'sha-256', 'hash': '6513f21e44aa3da349f248188a44bc304a3653a0 |
  |                      | 4122d8fb4535423c8e1d14cd6a153f735bb0982e2161b5b5186106570c17a9e58b64dd39390617cd5a350f78'},                |
  |                      | 'userMetadata': {}}]                                                                                       |
  | Usage State          | NOT_IN_USE                                                                                                 |
  | User Defined Data    |                                                                                                            |
  | VNF Product Name     | Sample VNF                                                                                                 |
  | VNF Provider         | Company                                                                                                    |
  | VNF Software Version | 1.0                                                                                                        |
  | VNFD ID              | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177                                                                       |
  | VNFD Version         | 1.0                                                                                                        |
  +----------------------+------------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf package show --help
  usage: openstack vnf package show [-h] [-f {json,shell,table,value,yaml}]
                                    [-c COLUMN] [--noindent] [--prefix PREFIX]
                                    [--max-width <integer>] [--fit-width]
                                    [--print-empty]
                                    <vnf-package>

  Show VNF Package Details

  positional arguments:
    <vnf-package>         VNF package ID

  optional arguments:
    -h, --help            show this help message and exit


6. Update VNF Package Info
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf package update --operational-state 'DISABLED' \
      <ID: e712a702-741f-4093-a971-b3ad69411ac>


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
  usage: openstack vnf package update [-h] [-f {json,shell,table,value,yaml}]
                                      [-c COLUMN] [--noindent] [--prefix PREFIX]
                                      [--max-width <integer>] [--fit-width]
                                      [--print-empty]
                                      [--operational-state <operational-state>]
                                      [--user-data <key=value>]
                                      <vnf-package>

  Update information about an individual VNF package

  positional arguments:
    <vnf-package>         VNF package ID

  optional arguments:
    -h, --help            show this help message and exit
    --operational-state <operational-state>
                          Change the operational state of VNF Package, Valid
                          values are 'ENABLED' or 'DISABLED'.
    --user-data <key=value>
                          User defined data for the VNF package (repeat option
                          to set multiple user defined data)


7. Delete VNF Package
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  openstack vnf package delete <ID: e712a702-741f-4093-a971-b3ad69411ac1>


Result:

.. code-block:: console

  All specified vnf-package(s) deleted successfully


Help:

.. code-block:: console

  $ openstack vnf package delete --help
  usage: openstack vnf package delete [-h] <vnf-package> [<vnf-package> ...]

  Delete VNF Package

  positional arguments:
    <vnf-package>  Vnf package(s) ID to delete

  optional arguments:
    -h, --help     show this help message and exit
