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

4. Fetch VNF Package Artifacts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf package artifact download --file <FILE: /tmp/deployment.yaml> \
      <ID: e712a702-741f-4093-a971-b3ad69411ac1> <artifact-path: Files/kubernetes/deployment.yaml>


Help:

.. code-block:: console

  $ openstack vnf package artifact download --help
  usage: openstack vnf package artifact download [-h] [--file <FILE>]
                                                 <vnf-package> <artifact-path>

  Download VNF package artifact of an on-boarded VNF package.

  positional arguments:
    <vnf-package>    VNF package ID
    <artifact-path>  The artifact file's path

  optional arguments:
    -h, --help       show this help message and exit
    --file <FILE>    Local file to save downloaded VNF Package artifact file
                     data. If this is not specified and there is no redirection
                     then data will not be saved.

5. List VNF Package
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


6. Show VNF Package
^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf package show <ID: e712a702-741f-4093-a971-b3ad69411ac1>


Result:

.. code-block:: console

  +----------------------+------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field                | Value                                                                                                                                          |
  +----------------------+------------------------------------------------------------------------------------------------------------------------------------------------+
  | Additional Artifacts | [                                                                                                                                              |
  |                      |     {                                                                                                                                          |
  |                      |         "artifactPath": "Files/kubernetes/deployment.yaml",                                                                                    |
  |                      |         "checksum": {                                                                                                                          |
  |                      |             "hash": "6a40dfb06764394fb604ae807d1198bc2e2ee8aece3b9483dfde48e53f316a58",                                                        |
  |                      |             "algorithm": "SHA-256"                                                                                                             |
  |                      |         },                                                                                                                                     |
  |                      |         "metadata": {}                                                                                                                         |
  |                      |     }                                                                                                                                          |
  |                      | ]                                                                                                                                              |
  | Checksum             | {                                                                                                                                              |
  |                      |     "algorithm": "sha512",                                                                                                                     |
  |                      |     "hash": "f51de874f4dd831986aff19b4d74b8e30009681683ff2d25b2969a2c679ae3a78f6bd79cc131d00e92a5e264cd8df02e2decb8b3f2acc6e877161977cdbdd304" |
  |                      | }                                                                                                                                              |
  | ID                   | e712a702-741f-4093-a971-b3ad69411ac1                                                                                                           |
  | Links                | {                                                                                                                                              |
  |                      |     "self": {                                                                                                                                  |
  |                      |         "href": "/vnfpkgm/v1/vnf_packages/08d00a5c-e8aa-4219-9412-411458eaa7d2"                                                                |
  |                      |     },                                                                                                                                         |
  |                      |     "packageContent": {                                                                                                                        |
  |                      |         "href": "/vnfpkgm/v1/vnf_packages/08d00a5c-e8aa-4219-9412-411458eaa7d2/package_content"                                                |
  |                      |     }                                                                                                                                          |
  |                      | }                                                                                                                                              |
  | Onboarding State     | ONBOARDED                                                                                                                                      |
  | Operational State    | ENABLED                                                                                                                                        |
  | Software Images      |                                                                                                                                                |
  | Usage State          | IN_USE                                                                                                                                         |
  | User Defined Data    | {}                                                                                                                                             |
  | VNF Product Name     | Sample VNF                                                                                                                                     |
  | VNF Provider         | Company                                                                                                                                        |
  | VNF Software Version | 1.0                                                                                                                                            |
  | VNFD ID              | b1bb0ce7-ebca-4fa7-95ed-4840d7000003                                                                                                           |
  | VNFD Version         | 1.0                                                                                                                                            |
  +----------------------+------------------------------------------------------------------------------------------------------------------------------------------------+

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


7. Update VNF Package Info
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


8. Delete VNF Package
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
