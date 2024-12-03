=======================================
VNF Lifecycle Management with v2 Tacker
=======================================

This document describes how to manage VNF Lifecycle with CLI in Tacker v2 API.

.. note::

  The content of this document has been confirmed to work
  using the following VNF Packages.

  * `basic_lcms_max_individual_vnfc for 2023.2 Bobcat`_
  * `userdata_standard for 2023.2 Bobcat`_
  * `userdata_standard_change_vnfpkg_nw for 2023.2 Bobcat`_


Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

A default VIM should be registered according to
:doc:`/cli/cli-legacy-vim`.

CLI Reference for VNF Lifecycle Management
------------------------------------------

.. note::

  Commands call version 1 VNF LCM APIs by default.
  You can call the version 2 VNF LCM APIs
  by using the option **\-\-os-tacker-api-version 2**.


1. Create VNF Identifier
^^^^^^^^^^^^^^^^^^^^^^^^

The `VNFD_ID` should be replaced with the VNFD ID in VNF Package.

.. code-block:: console

  $ openstack vnflcm create VNFD_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  +-----------------------------+------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                            |
  +-----------------------------+------------------------------------------------------------------------------------------------------------------+
  | ID                          | 7be9dcc0-e772-4e24-9e10-c52b525a1bf1                                                                             |
  | Instantiation State         | NOT_INSTANTIATED                                                                                                 |
  | Links                       | {                                                                                                                |
  |                             |     "self": {                                                                                                    |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/7be9dcc0-e772-4e24-9e10-c52b525a1bf1"             |
  |                             |     },                                                                                                           |
  |                             |     "instantiate": {                                                                                             |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/7be9dcc0-e772-4e24-9e10-c52b525a1bf1/instantiate" |
  |                             |     }                                                                                                            |
  |                             | }                                                                                                                |
  | VNF Configurable Properties |                                                                                                                  |
  | VNF Instance Description    |                                                                                                                  |
  | VNF Instance Name           |                                                                                                                  |
  | VNF Product Name            | Sample VNF                                                                                                       |
  | VNF Provider                | Company                                                                                                          |
  | VNF Software Version        | 1.0                                                                                                              |
  | VNFD ID                     | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177                                                                             |
  | VNFD Version                | 1.0                                                                                                              |
  +-----------------------------+------------------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm create --os-tacker-api-version 2 --help
  usage: openstack vnflcm create [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                 [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                 [--fit-width] [--print-empty] [--name <vnf-instance-name>]
                                 [--description <vnf-instance-description>] [--I <param-file>]
                                 <vnfd-id>

  Create a new VNF Instance

  positional arguments:
    <vnfd-id>     Identifier that identifies the VNFD which defines the VNF instance to be created.

  options:
    -h, --help            show this help message and exit
    --name <vnf-instance-name>
                          Name of the VNF instance to be created.
    --description <vnf-instance-description>
                          Description of the VNF instance to be created.
    --I <param-file>
                          Instantiate VNF subsequently after it's creation. Specify instantiate request
                          parameters in a json file.

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


2. Instantiate VNF
^^^^^^^^^^^^^^^^^^

The `VNF_INSTANCE_ID` and `SAMPLE_PARAM_FILE.json` should be replaced with
the ID of VNF instance and the path of parameter json file
that will be used to instantiate VNF, respectively.

.. code-block:: console

  $ openstack vnflcm instantiate VNF_INSTANCE_ID SAMPLE_PARAM_FILE.json \
    --os-tacker-api-version 2


Result:

.. code-block:: console

  Instantiate request for VNF Instance 7be9dcc0-e772-4e24-9e10-c52b525a1bf1 has been accepted.


Help:

.. code-block:: console

  $ openstack vnflcm instantiate --os-tacker-api-version 2 --help
  usage: openstack vnflcm instantiate [-h] <vnf-instance> <param-file>

  Instantiate a VNF Instance

  positional arguments:
    <vnf-instance>
                          VNF instance ID to instantiate
    <param-file>  Specify instantiate request parameters in a json file.

  options:
    -h, --help            show this help message and exit

  This command is provided by the python-tackerclient plugin.


3. List VNF
^^^^^^^^^^^

.. code-block:: console

  $ openstack vnflcm list --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------------------------------+-------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
  | ID                                   | VNF Instance Name | Instantiation State | VNF Provider | VNF Software Version | VNF Product Name | VNFD ID                              |
  +--------------------------------------+-------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
  | 7be9dcc0-e772-4e24-9e10-c52b525a1bf1 |                   | INSTANTIATED        | Company      | 1.0                  | Sample VNF       | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177 |
  +--------------------------------------+-------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm list --os-tacker-api-version 2 --help
  usage: openstack vnflcm list [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN]
                               [--quote {all,minimal,none,nonnumeric}] [--noindent]
                               [--max-width <integer>] [--fit-width] [--print-empty]
                               [--sort-column SORT_COLUMN] [--sort-ascending | --sort-descending]

  List VNF Instance

  options:
    -h, --help            show this help message and exit

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


4. Show VNF
^^^^^^^^^^^

The `VNF_INSTANCE_ID` should be replaced with the ID of VNF instance.

.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  +-----------------------------+--------------------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                          |
  +-----------------------------+--------------------------------------------------------------------------------------------------------------------------------+
  | ID                          | 7be9dcc0-e772-4e24-9e10-c52b525a1bf1                                                                                           |
  | Instantiated Vnf Info       | {                                                                                                                              |
  |                             |     "flavourId": "simple",                                                                                                     |
  |                             |     "vnfState": "STARTED",                                                                                                     |
  |                             |     "scaleStatus": [                                                                                                           |
  |                             |         {                                                                                                                      |
  |                             |             "aspectId": "VDU1_scale",                                                                                          |
  |                             |             "scaleLevel": 0                                                                                                    |
  |                             |         }                                                                                                                      |
  |                             |     ],                                                                                                                         |
  |                             |     "maxScaleLevels": [                                                                                                        |
  |                             |         {                                                                                                                      |
  |                             |             "aspectId": "VDU1_scale",                                                                                          |
  |                             |             "scaleLevel": 2                                                                                                    |
  |                             |         }                                                                                                                      |
  |                             |     ],                                                                                                                         |
  |                             |     "vnfcResourceInfo": [                                                                                                      |
  |                             |         {                                                                                                                      |
  |                             |             "id": "c9e3f4b4-d1ed-4a2d-98c3-2a654ab27f2a",                                                                      |
  |                             |             "vduId": "VDU1",                                                                                                   |
  |                             |             "computeResource": {                                                                                               |
  |                             |                 "vimConnectionId": "default",                                                                                  |
  |                             |                 "resourceId": "c9e3f4b4-d1ed-4a2d-98c3-2a654ab27f2a",                                                          |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                                     |
  |                             |             },                                                                                                                 |
  |                             |             "vnfcCpInfo": [                                                                                                    |
  |                             |                 {                                                                                                              |
  |                             |                     "id": "CP1-c9e3f4b4-d1ed-4a2d-98c3-2a654ab27f2a",                                                          |
  |                             |                     "cpdId": "CP1"                                                                                             |
  |                             |                 }                                                                                                              |
  |                             |             ],                                                                                                                 |
  |                             |             "metadata": {                                                                                                      |
  |                             |                 "creation_time": "2024-04-26T02:22:57Z",                                                                       |
  |                             |                 "stack_id": "vnf-7be9dcc0-e772-4e24-9e10-c52b525a1bf1-VDU1-hfkrj4pxccl6/a2a0ca88-948d-460a-a8a1-1f689cae481a", |
  |                             |                 "vdu_idx": null,                                                                                               |
  |                             |                 "flavor": "m1.tiny",                                                                                           |
  |                             |                 "image-VDU1": "cirros-0.5.2-x86_64-disk"                                                                       |
  |                             |             }                                                                                                                  |
  |                             |         }                                                                                                                      |
  |                             |     ],                                                                                                                         |
  |                             |     "vnfVirtualLinkResourceInfo": [                                                                                            |
  |                             |         {                                                                                                                      |
  |                             |             "id": "768c130a-8a72-49ea-9e4e-609e93077342",                                                                      |
  |                             |             "vnfVirtualLinkDescId": "internalVL1",                                                                             |
  |                             |             "networkResource": {                                                                                               |
  |                             |                 "vimConnectionId": "default",                                                                                  |
  |                             |                 "resourceId": "768c130a-8a72-49ea-9e4e-609e93077342",                                                          |
  |                             |                 "vimLevelResourceType": "OS::Neutron::Net"                                                                     |
  |                             |             }                                                                                                                  |
  |                             |         }                                                                                                                      |
  |                             |     ],                                                                                                                         |
  |                             |     "vnfcInfo": [                                                                                                              |
  |                             |         {                                                                                                                      |
  |                             |             "id": "VDU1-c9e3f4b4-d1ed-4a2d-98c3-2a654ab27f2a",                                                                 |
  |                             |             "vduId": "VDU1",                                                                                                   |
  |                             |             "vnfcResourceInfoId": "c9e3f4b4-d1ed-4a2d-98c3-2a654ab27f2a",                                                      |
  |                             |             "vnfcState": "STARTED"                                                                                             |
  |                             |         }                                                                                                                      |
  |                             |     ],                                                                                                                         |
  |                             |     "metadata": {                                                                                                              |
  |                             |         "stack_id": "fd51b123-1b28-4ab4-ab01-5024fea4f125",                                                                    |
  |                             |         "nfv": {                                                                                                               |
  |                             |             "VDU": {                                                                                                           |
  |                             |                 "VDU1": {                                                                                                      |
  |                             |                     "computeFlavourId": "m1.tiny",                                                                             |
  |                             |                     "vcImageId": "cirros-0.5.2-x86_64-disk"                                                                    |
  |                             |                 }                                                                                                              |
  |                             |             }                                                                                                                  |
  |                             |         },                                                                                                                     |
  |                             |         "tenant": "nfv"                                                                                                        |
  |                             |     }                                                                                                                          |
  |                             | }                                                                                                                              |
  | Instantiation State         | INSTANTIATED                                                                                                                   |
  | Links                       | {                                                                                                                              |
  |                             |     "self": {                                                                                                                  |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/7be9dcc0-e772-4e24-9e10-c52b525a1bf1"                           |
  |                             |     },                                                                                                                         |
  |                             |     "terminate": {                                                                                                             |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/7be9dcc0-e772-4e24-9e10-c52b525a1bf1/terminate"                 |
  |                             |     },                                                                                                                         |
  |                             |     "scale": {                                                                                                                 |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/7be9dcc0-e772-4e24-9e10-c52b525a1bf1/scale"                     |
  |                             |     },                                                                                                                         |
  |                             |     "heal": {                                                                                                                  |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/7be9dcc0-e772-4e24-9e10-c52b525a1bf1/heal"                      |
  |                             |     },                                                                                                                         |
  |                             |     "changeExtConn": {                                                                                                         |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/7be9dcc0-e772-4e24-9e10-c52b525a1bf1/change_ext_conn"           |
  |                             |     }                                                                                                                          |
  |                             | }                                                                                                                              |
  | VIM Connection Info         | {                                                                                                                              |
  |                             |     "default": {                                                                                                               |
  |                             |         "vimId": "7a1fc3d6-7bbc-4f6c-9efa-9086a9fd8fbc",                                                                       |
  |                             |         "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",                                                                           |
  |                             |         "interfaceInfo": {                                                                                                     |
  |                             |             "endpoint": "http://127.0.0.1/identity/v3",                                                                        |
  |                             |             "skipCertificateHostnameCheck": true,                                                                              |
  |                             |             "skipCertificateVerification": true                                                                                |
  |                             |         },                                                                                                                     |
  |                             |         "accessInfo": {                                                                                                        |
  |                             |             "username": "nfv_user",                                                                                            |
  |                             |             "region": "RegionOne",                                                                                             |
  |                             |             "project": "nfv",                                                                                                  |
  |                             |             "projectDomain": "default",                                                                                        |
  |                             |             "userDomain": "default"                                                                                            |
  |                             |         },                                                                                                                     |
  |                             |         "extra": {}                                                                                                            |
  |                             |     }                                                                                                                          |
  |                             | }                                                                                                                              |
  | VNF Configurable Properties |                                                                                                                                |
  | VNF Instance Description    |                                                                                                                                |
  | VNF Instance Name           |                                                                                                                                |
  | VNF Product Name            | Sample VNF                                                                                                                     |
  | VNF Provider                | Company                                                                                                                        |
  | VNF Software Version        | 1.0                                                                                                                            |
  | VNFD ID                     | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177                                                                                           |
  | VNFD Version                | 1.0                                                                                                                            |
  +-----------------------------+--------------------------------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm show --os-tacker-api-version 2 --help
  usage: openstack vnflcm show [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                               [--noindent] [--prefix PREFIX] [--max-width <integer>]
                               [--fit-width] [--print-empty]
                               <vnf-instance>

  Display VNF instance details

  positional arguments:
    <vnf-instance>
                          VNF instance ID to display

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


5. Terminate VNF
^^^^^^^^^^^^^^^^

The `VNF_INSTANCE_ID` should be replaced with the ID of VNF instance.

.. code-block:: console

  $ openstack vnflcm terminate VNF_INSTANCE_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  Terminate request for VNF Instance '7be9dcc0-e772-4e24-9e10-c52b525a1bf1' has been accepted.


Help:

.. code-block:: console

  $ openstack vnflcm terminate --os-tacker-api-version 2 --help
  usage: openstack vnflcm terminate [-h] [--termination-type <termination-type>]
                                    [--graceful-termination-timeout <graceful-termination-timeout>]
                                    [--D]
                                    <vnf-instance>

  Terminate a VNF instance

  positional arguments:
    <vnf-instance>
                          VNF instance ID to terminate

  options:
    -h, --help            show this help message and exit
    --termination-type <termination-type>
                          Termination type can be 'GRACEFUL' or 'FORCEFUL'. Default is 'GRACEFUL'
    --graceful-termination-timeout <graceful-termination-timeout>
                          This attribute is only applicable in case of graceful termination. It defines the
                          time to wait for the VNF to be taken out of service before shutting down the VNF and
                          releasing the resources. The unit is seconds.
    --D                   Delete VNF Instance subsequently after it's termination

  This command is provided by the python-tackerclient plugin.


6. Delete VNF Identifier
^^^^^^^^^^^^^^^^^^^^^^^^

The `VNF_INSTANCE_ID` should be replaced with the ID of VNF instance.

.. code-block:: console

  $ openstack vnflcm delete VNF_INSTANCE_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  Vnf instance '7be9dcc0-e772-4e24-9e10-c52b525a1bf1' is deleted successfully


Help:

.. code-block:: console

  $ openstack vnflcm delete --os-tacker-api-version 2 --help
  usage: openstack vnflcm delete [-h] <vnf-instance> [<vnf-instance> ...]

  Delete VNF Instance(s)

  positional arguments:
    <vnf-instance>
                          VNF instance ID(s) to delete

  options:
    -h, --help            show this help message and exit

  This command is provided by the python-tackerclient plugin.


7. Heal VNF
^^^^^^^^^^^

The `VNF_INSTANCE_ID` should be replaced with the ID of VNF instance.

.. code-block:: console

  $ openstack vnflcm heal VNF_INSTANCE_ID --os-tacker-api-version 2


.. note::

  <vnf-instance> should either be given before \-\-vnfc-instance
  parameter or it should be separated with '\-\-' separator in
  order to come after \-\-vnfc-instance parameter.


Result:

.. code-block:: console

  Heal request for VNF Instance d44e9511-1857-4530-8a5e-1b28a6e5a744 has been accepted.


Help:

.. code-block:: console

  $ openstack vnflcm heal --os-tacker-api-version 2 --help
  usage: openstack vnflcm heal [-h] [--cause CAUSE]
                               [--vnfc-instance <vnfc-instance-id> [<vnfc-instance-id> ...]]
                               [--additional-param-file <additional-param-file>]
                               -- <vnf-instance>

  Heal VNF Instance

  positional arguments:
    <vnf-instance>
                          VNF instance ID to heal

  options:
    -h, --help            show this help message and exit
    --cause CAUSE
                          Specify the reason why a healing procedure is required.
    --vnfc-instance <vnfc-instance-id> [<vnfc-instance-id> ...]
                          List of VNFC instances requiring a healing action.
    --additional-param-file <additional-param-file>
                          Additional parameters passed by the NFVO as input to the healing process.

  This command is provided by the python-tackerclient plugin.


8. Update VNF
^^^^^^^^^^^^^

The `VNF_INSTANCE_ID` and `SAMPLE_PARAM_FILE.json` should be replaced with
the ID of VNF instance and the name of parameter json file
that will be used to update VNF, respectively.

.. code-block:: console

  $ openstack vnflcm update VNF_INSTANCE_ID --I SAMPLE_PARAM_FILE.json \
    --os-tacker-api-version 2


Result:

.. code-block:: console

  Update vnf:d44e9511-1857-4530-8a5e-1b28a6e5a744


Help:

.. code-block:: console

  $ openstack vnflcm update --os-tacker-api-version 2 --help
  usage: openstack vnflcm update [-h] [--I <param-file>] <vnf-instance>

  Update VNF Instance

  positional arguments:
    <vnf-instance>
                          VNF instance ID to update.

  options:
    -h, --help            show this help message and exit
    --I <param-file>
                          Specify update request parameters in a json file.

  This command is provided by the python-tackerclient plugin.


9. Scale VNF
^^^^^^^^^^^^

The `VNF_INSTANCE_ID` and `WORKER_INSTANCE` should be replaced with
the ID of VNF instance and the ID of the target scaling group, respectively.
See 'How to Identify ASPECT_ID' in :doc:`/user/v2/vnf/scale/index` for details.

.. code-block:: console

  $ openstack vnflcm scale --type SCALE_OUT --aspect-id WORKER_INSTANCE \
    VNF_INSTANCE_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  Scale request for VNF Instance d44e9511-1857-4530-8a5e-1b28a6e5a744 has been accepted.


Help:

.. code-block:: console

  $ openstack vnflcm scale --os-tacker-api-version 2 --help
  usage: openstack vnflcm scale [-h] [--number-of-steps <number-of-steps>]
                                [--additional-param-file <additional-param-file>] --type
                                <type> --aspect-id <aspect-id>
                                <vnf-instance>

  Scale a VNF Instance

  positional arguments:
    <vnf-instance>
                          VNF instance ID to scale

  options:
    -h, --help            show this help message and exit
    --number-of-steps <number-of-steps>
                          Number of scaling steps to be executed as part of this Scale VNF operation.
    --additional-param-file <additional-param-file>
                          Additional parameters passed by the NFVO as input to the scaling process.

  require arguments:
    --type <type>
                          SCALE_OUT or SCALE_IN for type of scale operation.
    --aspect-id <aspect-id>
                          Identifier of the scaling aspect.

  This command is provided by the python-tackerclient plugin.


10. Change External VNF Connectivity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::

  In 2024.2 Dalmatian release, Change External VNF Connectivity
  only support VNF, not CNF.


The `VNF_INSTANCE_ID` and `SAMPLE_PARAM_FILE.json` should be replaced with
the ID of VNF instance and the path of parameter json file
that will be used to change external VNF connectivity, respectively.

.. code-block:: console

  $ openstack vnflcm change-ext-conn VNF_INSTANCE_ID SAMPLE_PARAM_FILE.json \
    --os-tacker-api-version 2


Result:

.. code-block:: console

  Change External VNF Connectivity for VNF Instance d44e9511-1857-4530-8a5e-1b28a6e5a744 has been accepted.


Help:

.. code-block:: console

  $ openstack vnflcm change-ext-conn --os-tacker-api-version 2 --help
  usage: openstack vnflcm change-ext-conn [-h] <vnf-instance> <param-file>

  Change External VNF Connectivity

  positional arguments:
    <vnf-instance>
                          VNF instance ID to Change External VNF Connectivity
    <param-file>  Specify change-ext-conn request parameters in a json file.

  options:
    -h, --help            show this help message and exit

  This command is provided by the python-tackerclient plugin.


11. Change Current VNF Package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::

  In 2024.2 Dalmatian release, `Change Current VNF Package` only support ``RollingUpdate`` upgrade type,
  ``BlueGreen`` will be supported in future releases.


The `VNF_INSTANCE_ID` and the `SAMPLE_PARAM_FILE.json` should be replaced with
the ID of VNF instance and the path of parameter json file that will be used
to change VNF Package of VNF instance, respectively.

.. code-block:: console

  $ openstack vnflcm change-vnfpkg VNF_INSTANCE_ID SAMPLE_PARAM_FILE.json \
    --os-tacker-api-version 2


Result:

.. code-block:: console

  Change Current VNF Package for VNF Instance d44e9511-1857-4530-8a5e-1b28a6e5a744 has been accepted


Help:

.. code-block:: console

  $ openstack vnflcm change-vnfpkg --os-tacker-api-version 2 --help
  usage: openstack vnflcm change-vnfpkg [-h] <vnf-instance> <param-file>

  Change Current VNF Package

  positional arguments:
    <vnf-instance>
                          VNF instance ID to Change Current VNF Package
    <param-file>  Specify change-vnfpkg request parameters in a json file.

  options:
    -h, --help            show this help message and exit

  This command is provided by the python-tackerclient plugin.


12. Rollback VNF Lifecycle Management Operation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `VNF_LCM_OP_OCC_ID` should be replaced with the ID of the target
lifecycle management operation temporary failed.

.. code-block:: console

  $ openstack vnflcm op rollback VNF_LCM_OP_OCC_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  Rollback request for LCM operation 7113c882-cabe-4fff-8837-b856727fbd65 has been accepted


Help:

.. code-block:: console

  $ openstack vnflcm op rollback --os-tacker-api-version 2 --help
  usage: openstack vnflcm op rollback [-h] <vnf-lcm-op-occ-id>

  positional arguments:
    <vnf-lcm-op-occ-id>
                          VNF lifecycle management operation occurrence ID.

  options:
    -h, --help            show this help message and exit

  This command is provided by the python-tackerclient plugin.


13. Retry VNF Lifecycle Management Operation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `VNF_LCM_OP_OCC_ID` should be replaced with the ID of the target
lifecycle management operation temporary failed.

.. code-block:: console

  $ openstack vnflcm op retry VNF_LCM_OP_OCC_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  Retry request for LCM operation 1ba8410c-4181-49a0-b2aa-e3015a6e8257 has been accepted


Help:

.. code-block:: console

  $ openstack vnflcm op retry --os-tacker-api-version 2 --help
  usage: openstack vnflcm op retry [-h] <vnf-lcm-op-occ-id>

  Retry VNF Instance

  positional arguments:
    <vnf-lcm-op-occ-id>
                          VNF lifecycle management operation occurrence ID.

  options:
    -h, --help            show this help message and exit

  This command is provided by the python-tackerclient plugin.


14. Fail VNF Lifecycle Management Operation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `VNF_LCM_OP_OCC_ID` should be replaced with the ID of the target
lifecycle management operation temporary failed.

.. code-block:: console

  $ openstack vnflcm op fail VNF_LCM_OP_OCC_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  +-------------------------+-----------------------------------------------------------------------------------------------------------------+
  | Field                   | Value                                                                                                           |
  +-------------------------+-----------------------------------------------------------------------------------------------------------------+
  | Error                   | {                                                                                                               |
  |                         |     "title": "Stack delete failed",                                                                             |
  |                         |     "status": 422,                                                                                              |
  |                         |     "detail": "Resource DELETE failed: Error: resources.VDU2-0.resources.VDU2-VirtualStorage: Volume in use"    |
  |                         | }                                                                                                               |
  | ID                      | 1ba8410c-4181-49a0-b2aa-e3015a6e8257                                                                            |
  | Is Automatic Invocation | False                                                                                                           |
  | Is Cancel Pending       | False                                                                                                           |
  | Links                   | {                                                                                                               |
  |                         |     "self": {                                                                                                   |
  |                         |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_lcm_op_occs/1ba8410c-4181-49a0-b2aa-e3015a6e8257"          |
  |                         |     },                                                                                                          |
  |                         |     "vnfInstance": {                                                                                            |
  |                         |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/d44e9511-1857-4530-8a5e-1b28a6e5a744"            |
  |                         |     },                                                                                                          |
  |                         |     "retry": {                                                                                                  |
  |                         |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_lcm_op_occs/1ba8410c-4181-49a0-b2aa-e3015a6e8257/retry"    |
  |                         |     },                                                                                                          |
  |                         |     "rollback": {                                                                                               |
  |                         |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_lcm_op_occs/1ba8410c-4181-49a0-b2aa-e3015a6e8257/rollback" |
  |                         |     },                                                                                                          |
  |                         |     "fail": {                                                                                                   |
  |                         |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_lcm_op_occs/1ba8410c-4181-49a0-b2aa-e3015a6e8257/fail"     |
  |                         |     }                                                                                                           |
  |                         | }                                                                                                               |
  | Operation               | TERMINATE                                                                                                       |
  | Operation State         | FAILED                                                                                                          |
  | Start Time              | 2024-04-25T02:22:53Z                                                                                            |
  | State Entered Time      | 2024-04-25T02:24:59Z                                                                                            |
  | VNF Instance ID         | d44e9511-1857-4530-8a5e-1b28a6e5a744                                                                            |
  | grantId                 | 2fa21479-39aa-4810-af7a-3dbc4cede8ac                                                                            |
  | operationParams         | {                                                                                                               |
  |                         |     "terminationType": "GRACEFUL"                                                                               |
  |                         | }                                                                                                               |
  +-------------------------+-----------------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm op fail --os-tacker-api-version 2 --help
  usage: openstack vnflcm op fail [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                  [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                  [--fit-width] [--print-empty]
                                  <vnf-lcm-op-occ-id>

  Fail VNF Instance

  positional arguments:
    <vnf-lcm-op-occ-id>
                          VNF lifecycle management operation occurrence ID.

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


15. List LCM Operation Occurrences
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnflcm op list --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------------------------------+-----------------+--------------------------------------+-------------+
  | ID                                   | Operation State | VNF Instance ID                      | Operation   |
  +--------------------------------------+-----------------+--------------------------------------+-------------+
  | 2389ac68-8a02-4fb7-9ab7-7e622b196e8d | COMPLETED       | d5ffa129-ecb8-4cc0-b2d4-1745c3275f27 | INSTANTIATE |
  +--------------------------------------+-----------------+--------------------------------------+-------------+


Help:

.. code-block:: console

  $ openstack vnflcm op list --os-tacker-api-version 2 --help
  usage: openstack vnflcm op list [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN]
                                  [--quote {all,minimal,none,nonnumeric}] [--noindent]
                                  [--max-width <integer>] [--fit-width] [--print-empty]
                                  [--sort-column SORT_COLUMN] [--sort-ascending | --sort-descending]
                                  [--filter <filter>]
                                  [--fields <fields> | --exclude-fields <exclude-fields>]

  List LCM Operation Occurrences

  options:
    -h, --help            show this help message and exit
    --filter <filter>
                          Attribute-based-filtering parameters
    --fields <fields>
                          Complex attributes to be included into the response
    --exclude-fields <exclude-fields>
                          Complex attributes to be excluded from the response

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


16. Show LCM Operation Occurrence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `VNF_LCM_OP_OCC_ID` should be replaced with the ID of the target
lifecycle management operation.

.. code-block:: console

  $ openstack vnflcm op show VNF_LCM_OP_OCC_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  +-------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
  | Field                         | Value                                                                                                                          |
  +-------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
  | Cancel Mode                   |                                                                                                                                |
  | Changed External Connectivity |                                                                                                                                |
  | Changed Info                  |                                                                                                                                |
  | Error                         |                                                                                                                                |
  | Grant ID                      | 2bc583fb-6e1e-4d64-9213-117b9a363885                                                                                           |
  | ID                            | c4d83b35-ae2b-4291-9eea-83644d700ab8                                                                                           |
  | Is Automatic Invocation       | False                                                                                                                          |
  | Is Cancel Pending             | False                                                                                                                          |
  | Links                         | {                                                                                                                              |
  |                               |     "self": {                                                                                                                  |
  |                               |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_lcm_op_occs/c4d83b35-ae2b-4291-9eea-83644d700ab8"                         |
  |                               |     },                                                                                                                         |
  |                               |     "vnfInstance": {                                                                                                           |
  |                               |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/7be9dcc0-e772-4e24-9e10-c52b525a1bf1"                           |
  |                               |     },                                                                                                                         |
  |                               |     "retry": {                                                                                                                 |
  |                               |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_lcm_op_occs/c4d83b35-ae2b-4291-9eea-83644d700ab8/retry"                   |
  |                               |     },                                                                                                                         |
  |                               |     "rollback": {                                                                                                              |
  |                               |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_lcm_op_occs/c4d83b35-ae2b-4291-9eea-83644d700ab8/rollback"                |
  |                               |     },                                                                                                                         |
  |                               |     "fail": {                                                                                                                  |
  |                               |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_lcm_op_occs/c4d83b35-ae2b-4291-9eea-83644d700ab8/fail"                    |
  |                               |     }                                                                                                                          |
  |                               | }                                                                                                                              |
  | Operation                     | INSTANTIATE                                                                                                                    |
  | Operation Parameters          | {                                                                                                                              |
  |                               |     "flavourId": "simple"                                                                                                      |
  |                               | }                                                                                                                              |
  | Operation State               | COMPLETED                                                                                                                      |
  | Resource Changes              | {                                                                                                                              |
  |                               |     "affectedVnfcs": [                                                                                                         |
  |                               |         {                                                                                                                      |
  |                               |             "id": "c9e3f4b4-d1ed-4a2d-98c3-2a654ab27f2a",                                                                      |
  |                               |             "vduId": "VDU1",                                                                                                   |
  |                               |             "changeType": "ADDED",                                                                                             |
  |                               |             "computeResource": {                                                                                               |
  |                               |                 "vimConnectionId": "default",                                                                                  |
  |                               |                 "resourceId": "c9e3f4b4-d1ed-4a2d-98c3-2a654ab27f2a",                                                          |
  |                               |                 "vimLevelResourceType": "OS::Nova::Server"                                                                     |
  |                               |             },                                                                                                                 |
  |                               |             "metadata": {                                                                                                      |
  |                               |                 "creation_time": "2024-04-26T02:22:57Z",                                                                       |
  |                               |                 "stack_id": "vnf-7be9dcc0-e772-4e24-9e10-c52b525a1bf1-VDU1-hfkrj4pxccl6/a2a0ca88-948d-460a-a8a1-1f689cae481a", |
  |                               |                 "vdu_idx": null,                                                                                               |
  |                               |                 "flavor": "m1.tiny",                                                                                           |
  |                               |                 "image-VDU1": "cirros-0.5.2-x86_64-disk"                                                                       |
  |                               |             },                                                                                                                 |
  |                               |             "affectedVnfcCpIds": [                                                                                             |
  |                               |                 "CP1-c9e3f4b4-d1ed-4a2d-98c3-2a654ab27f2a"                                                                     |
  |                               |             ]                                                                                                                  |
  |                               |         }                                                                                                                      |
  |                               |     ],                                                                                                                         |
  |                               |     "affectedVirtualLinks": [                                                                                                  |
  |                               |         {                                                                                                                      |
  |                               |             "id": "768c130a-8a72-49ea-9e4e-609e93077342",                                                                      |
  |                               |             "vnfVirtualLinkDescId": "internalVL1",                                                                             |
  |                               |             "changeType": "ADDED",                                                                                             |
  |                               |             "networkResource": {                                                                                               |
  |                               |                 "vimConnectionId": "default",                                                                                  |
  |                               |                 "resourceId": "768c130a-8a72-49ea-9e4e-609e93077342",                                                          |
  |                               |                 "vimLevelResourceType": "OS::Neutron::Net"                                                                     |
  |                               |             }                                                                                                                  |
  |                               |         }                                                                                                                      |
  |                               |     ]                                                                                                                          |
  |                               | }                                                                                                                              |
  | Start Time                    | 2024-04-26T02:22:50Z                                                                                                           |
  | State Entered Time            | 2024-04-26T02:23:15Z                                                                                                           |
  | VNF Instance ID               | 7be9dcc0-e772-4e24-9e10-c52b525a1bf1                                                                                           |
  +-------------------------------+--------------------------------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm op show --os-tacker-api-version 2 --help
  usage: openstack vnflcm op show [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                  [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                  [--fit-width] [--print-empty]
                                  <vnf-lcm-op-occ-id>

  Display Operation Occurrence details

  positional arguments:
    <vnf-lcm-op-occ-id>
                          VNF lifecycle management operation occurrence ID.

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


17. Create Lccn Subscription
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `SAMPLE_PARAM_FILE.json` should be replaced with the path of parameter
json file that will be used to create Lccn subscription.

.. code-block:: console

  $ openstack vnflcm subsc create SAMPLE_PARAM_FILE.json --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------+------------------------------------------------------------------------------------------------------+
  | Field        | Value                                                                                                |
  +--------------+------------------------------------------------------------------------------------------------------+
  | Callback URI | http://localhost:9990/notification/callback/test                                                     |
  | Filter       | {                                                                                                    |
  |              |     "vnfInstanceSubscriptionFilter": {                                                               |
  |              |         "vnfdIds": [                                                                                 |
  |              |             "dummy-vnfdId-1",                                                                        |
  |              |             "dummy-vnfdId-2"                                                                         |
  |              |         ],                                                                                           |
  |              |         "vnfProductsFromProviders": [                                                                |
  |              |             {                                                                                        |
  |              |                 "vnfProvider": "dummy-vnfProvider-1",                                                |
  |              |                 "vnfProducts": [                                                                     |
  |              |                     {                                                                                |
  |              |                         "vnfProductName": "dummy-vnfProductName-1-1",                                |
  |              |                         "versions": [                                                                |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.0",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.0",                                                           |
  |              |                                     "2.0"                                                            |
  |              |                                 ]                                                                    |
  |              |                             },                                                                       |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.1",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.1",                                                           |
  |              |                                     "2.1"                                                            |
  |              |                                 ]                                                                    |
  |              |                             }                                                                        |
  |              |                         ]                                                                            |
  |              |                     },                                                                               |
  |              |                     {                                                                                |
  |              |                         "vnfProductName": "dummy-vnfProductName-1-2",                                |
  |              |                         "versions": [                                                                |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.0",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.0",                                                           |
  |              |                                     "2.0"                                                            |
  |              |                                 ]                                                                    |
  |              |                             },                                                                       |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.1",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.1",                                                           |
  |              |                                     "2.1"                                                            |
  |              |                                 ]                                                                    |
  |              |                             }                                                                        |
  |              |                         ]                                                                            |
  |              |                     }                                                                                |
  |              |                 ]                                                                                    |
  |              |             },                                                                                       |
  |              |             {                                                                                        |
  |              |                 "vnfProvider": "dummy-vnfProvider-2",                                                |
  |              |                 "vnfProducts": [                                                                     |
  |              |                     {                                                                                |
  |              |                         "vnfProductName": "dummy-vnfProductName-2-1",                                |
  |              |                         "versions": [                                                                |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.0",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.0",                                                           |
  |              |                                     "2.0"                                                            |
  |              |                                 ]                                                                    |
  |              |                             },                                                                       |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.1",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.1",                                                           |
  |              |                                     "2.1"                                                            |
  |              |                                 ]                                                                    |
  |              |                             }                                                                        |
  |              |                         ]                                                                            |
  |              |                     },                                                                               |
  |              |                     {                                                                                |
  |              |                         "vnfProductName": "dummy-vnfProductName-2-2",                                |
  |              |                         "versions": [                                                                |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.0",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.0",                                                           |
  |              |                                     "2.0"                                                            |
  |              |                                 ]                                                                    |
  |              |                             },                                                                       |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.1",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.1",                                                           |
  |              |                                     "2.1"                                                            |
  |              |                                 ]                                                                    |
  |              |                             }                                                                        |
  |              |                         ]                                                                            |
  |              |                     }                                                                                |
  |              |                 ]                                                                                    |
  |              |             }                                                                                        |
  |              |         ],                                                                                           |
  |              |         "vnfInstanceIds": [                                                                          |
  |              |             "dummy-vnfInstanceId-1",                                                                 |
  |              |             "dummy-vnfInstanceId-2"                                                                  |
  |              |         ],                                                                                           |
  |              |         "vnfInstanceNames": [                                                                        |
  |              |             "dummy-vnfInstanceName-1",                                                               |
  |              |             "dummy-vnfInstanceName-2"                                                                |
  |              |         ]                                                                                            |
  |              |     },                                                                                               |
  |              |     "notificationTypes": [                                                                           |
  |              |         "VnfLcmOperationOccurrenceNotification",                                                     |
  |              |         "VnfIdentifierCreationNotification",                                                         |
  |              |         "VnfLcmOperationOccurrenceNotification"                                                      |
  |              |     ],                                                                                               |
  |              |     "operationTypes": [                                                                              |
  |              |         "INSTANTIATE",                                                                               |
  |              |         "SCALE",                                                                                     |
  |              |         "TERMINATE",                                                                                 |
  |              |         "HEAL",                                                                                      |
  |              |         "MODIFY_INFO",                                                                               |
  |              |         "CHANGE_EXT_CONN"                                                                            |
  |              |     ],                                                                                               |
  |              |     "operationStates": [                                                                             |
  |              |         "COMPLETED",                                                                                 |
  |              |         "FAILED",                                                                                    |
  |              |         "FAILED_TEMP",                                                                               |
  |              |         "PROCESSING",                                                                                |
  |              |         "ROLLING_BACK",                                                                              |
  |              |         "ROLLED_BACK",                                                                               |
  |              |         "STARTING"                                                                                   |
  |              |     ]                                                                                                |
  |              | }                                                                                                    |
  | ID           | 7f18f53b-dae9-4be3-a38e-1b25e420ccfc                                                                 |
  | Links        | {                                                                                                    |
  |              |     "self": {                                                                                        |
  |              |         "href": "http://127.0.0.1:9890/vnflcm/v2/subscriptions/7f18f53b-dae9-4be3-a38e-1b25e420ccfc" |
  |              |     }                                                                                                |
  |              | }                                                                                                    |
  | verbosity    | FULL                                                                                                 |
  +--------------+------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm subsc create --os-tacker-api-version 2 --help
  usage: openstack vnflcm subsc create [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                       [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                       [--fit-width] [--print-empty]
                                       <param-file>

  Create a new Lccn Subscription

  positional arguments:
    <param-file>  Specify create request parameters in a json file.

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


18. List Lccn Subscription
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnflcm subsc list --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------------------------------+--------------------------------------------------+
  | ID                                   | Callback URI                                     |
  +--------------------------------------+--------------------------------------------------+
  | 7f18f53b-dae9-4be3-a38e-1b25e420ccfc | http://localhost:9990/notification/callback/test |
  +--------------------------------------+--------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm subsc list --os-tacker-api-version 2 --help
  usage: openstack vnflcm subsc list [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN]
                                     [--quote {all,minimal,none,nonnumeric}] [--noindent]
                                     [--max-width <integer>] [--fit-width] [--print-empty]
                                     [--sort-column SORT_COLUMN]
                                     [--sort-ascending | --sort-descending] [--filter <filter>]

  List Lccn Subscriptions

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


19. Show Lccn Subscription
^^^^^^^^^^^^^^^^^^^^^^^^^^

The `LCCN_SUBSCRIPTION_ID` should be replaced with the ID of Lccn subscription.

.. code-block:: console

  $ openstack vnflcm subsc show LCCN_SUBSCRIPTION_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  +--------------+------------------------------------------------------------------------------------------------------+
  | Field        | Value                                                                                                |
  +--------------+------------------------------------------------------------------------------------------------------+
  | Callback URI | http://localhost:9990/notification/callback/test                                                     |
  | Filter       | {                                                                                                    |
  |              |     "vnfInstanceSubscriptionFilter": {                                                               |
  |              |         "vnfdIds": [                                                                                 |
  |              |             "dummy-vnfdId-1",                                                                        |
  |              |             "dummy-vnfdId-2"                                                                         |
  |              |         ],                                                                                           |
  |              |         "vnfProductsFromProviders": [                                                                |
  |              |             {                                                                                        |
  |              |                 "vnfProvider": "dummy-vnfProvider-1",                                                |
  |              |                 "vnfProducts": [                                                                     |
  |              |                     {                                                                                |
  |              |                         "vnfProductName": "dummy-vnfProductName-1-1",                                |
  |              |                         "versions": [                                                                |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.0",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.0",                                                           |
  |              |                                     "2.0"                                                            |
  |              |                                 ]                                                                    |
  |              |                             },                                                                       |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.1",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.1",                                                           |
  |              |                                     "2.1"                                                            |
  |              |                                 ]                                                                    |
  |              |                             }                                                                        |
  |              |                         ]                                                                            |
  |              |                     },                                                                               |
  |              |                     {                                                                                |
  |              |                         "vnfProductName": "dummy-vnfProductName-1-2",                                |
  |              |                         "versions": [                                                                |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.0",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.0",                                                           |
  |              |                                     "2.0"                                                            |
  |              |                                 ]                                                                    |
  |              |                             },                                                                       |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.1",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.1",                                                           |
  |              |                                     "2.1"                                                            |
  |              |                                 ]                                                                    |
  |              |                             }                                                                        |
  |              |                         ]                                                                            |
  |              |                     }                                                                                |
  |              |                 ]                                                                                    |
  |              |             },                                                                                       |
  |              |             {                                                                                        |
  |              |                 "vnfProvider": "dummy-vnfProvider-2",                                                |
  |              |                 "vnfProducts": [                                                                     |
  |              |                     {                                                                                |
  |              |                         "vnfProductName": "dummy-vnfProductName-2-1",                                |
  |              |                         "versions": [                                                                |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.0",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.0",                                                           |
  |              |                                     "2.0"                                                            |
  |              |                                 ]                                                                    |
  |              |                             },                                                                       |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.1",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.1",                                                           |
  |              |                                     "2.1"                                                            |
  |              |                                 ]                                                                    |
  |              |                             }                                                                        |
  |              |                         ]                                                                            |
  |              |                     },                                                                               |
  |              |                     {                                                                                |
  |              |                         "vnfProductName": "dummy-vnfProductName-2-2",                                |
  |              |                         "versions": [                                                                |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.0",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.0",                                                           |
  |              |                                     "2.0"                                                            |
  |              |                                 ]                                                                    |
  |              |                             },                                                                       |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.1",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.1",                                                           |
  |              |                                     "2.1"                                                            |
  |              |                                 ]                                                                    |
  |              |                             }                                                                        |
  |              |                         ]                                                                            |
  |              |                     }                                                                                |
  |              |                 ]                                                                                    |
  |              |             }                                                                                        |
  |              |         ],                                                                                           |
  |              |         "vnfInstanceIds": [                                                                          |
  |              |             "dummy-vnfInstanceId-1",                                                                 |
  |              |             "dummy-vnfInstanceId-2"                                                                  |
  |              |         ],                                                                                           |
  |              |         "vnfInstanceNames": [                                                                        |
  |              |             "dummy-vnfInstanceName-1",                                                               |
  |              |             "dummy-vnfInstanceName-2"                                                                |
  |              |         ]                                                                                            |
  |              |     },                                                                                               |
  |              |     "notificationTypes": [                                                                           |
  |              |         "VnfLcmOperationOccurrenceNotification",                                                     |
  |              |         "VnfIdentifierCreationNotification",                                                         |
  |              |         "VnfLcmOperationOccurrenceNotification"                                                      |
  |              |     ],                                                                                               |
  |              |     "operationTypes": [                                                                              |
  |              |         "INSTANTIATE",                                                                               |
  |              |         "SCALE",                                                                                     |
  |              |         "TERMINATE",                                                                                 |
  |              |         "HEAL",                                                                                      |
  |              |         "MODIFY_INFO",                                                                               |
  |              |         "CHANGE_EXT_CONN"                                                                            |
  |              |     ],                                                                                               |
  |              |     "operationStates": [                                                                             |
  |              |         "COMPLETED",                                                                                 |
  |              |         "FAILED",                                                                                    |
  |              |         "FAILED_TEMP",                                                                               |
  |              |         "PROCESSING",                                                                                |
  |              |         "ROLLING_BACK",                                                                              |
  |              |         "ROLLED_BACK",                                                                               |
  |              |         "STARTING"                                                                                   |
  |              |     ]                                                                                                |
  |              | }                                                                                                    |
  | ID           | 7f18f53b-dae9-4be3-a38e-1b25e420ccfc                                                                 |
  | Links        | {                                                                                                    |
  |              |     "self": {                                                                                        |
  |              |         "href": "http://127.0.0.1:9890/vnflcm/v2/subscriptions/7f18f53b-dae9-4be3-a38e-1b25e420ccfc" |
  |              |     }                                                                                                |
  |              | }                                                                                                    |
  | verbosity    | FULL                                                                                                 |
  +--------------+------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm subsc show --os-tacker-api-version 2 --help
  usage: openstack vnflcm subsc show [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                     [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                     [--fit-width] [--print-empty]
                                     <subscription-id>

  Display Lccn Subscription details

  positional arguments:
    <subscription-id>
                          Lccn Subscription ID to display

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


20. Delete Lccn Subscription
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `LCCN_SUBSCRIPTION_ID` should be replaced with the ID of Lccn subscription.

.. code-block:: console

  $ openstack vnflcm subsc delete LCCN_SUBSCRIPTION_ID --os-tacker-api-version 2


Result:

.. code-block:: console

  Lccn Subscription '7f18f53b-dae9-4be3-a38e-1b25e420ccfc' is deleted successfully


Help:

.. code-block:: console

  $ openstack vnflcm subsc delete --os-tacker-api-version 2 --help
  usage: openstack vnflcm subsc delete [-h] <subscription-id> [<subscription-id> ...]

  Delete Lccn Subscription(s)

  positional arguments:
    <subscription-id>
                          Lccn Subscription ID(s) to delete

  options:
    -h, --help            show this help message and exit

  This command is provided by the python-tackerclient plugin.


21. Show VNF LCM API versions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnflcm versions


Result:

.. code-block:: console

  $ openstack vnflcm versions
  +-------------+--------------------------------------------------------------------------------------------+
  | Field       | Value                                                                                      |
  +-------------+--------------------------------------------------------------------------------------------+
  | uriPrefix   | /vnflcm                                                                                    |
  | apiVersions | [{'version': '1.3.0', 'isDeprecated': False}, {'version': '2.0.0', 'isDeprecated': False}] |
  +-------------+--------------------------------------------------------------------------------------------+


.. note::

  Running the command with **\-\-major-version 2** option shows v2 Tacker's version only.


.. code-block:: console

  $ openstack vnflcm versions --major-version 2
  +-------------+-----------------------------------------------+
  | Field       | Value                                         |
  +-------------+-----------------------------------------------+
  | uriPrefix   | /vnflcm/v2                                    |
  | apiVersions | [{'version': '2.0.0', 'isDeprecated': False}] |
  +-------------+-----------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm versions --help
  usage: openstack vnflcm versions [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                   [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                   [--fit-width] [--print-empty] [--major-version <major-version>]

  Show VnfLcm Api versions

  options:
    -h, --help            show this help message and exit
    --major-version <major-version>
                          Show only specify major version.

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


.. _basic_lcms_max_individual_vnfc for 2023.2 Bobcat:
  https://opendev.org/openstack/tacker/src/branch/stable/2023.2/tacker/tests/functional/sol_v2_common/samples/basic_lcms_max_individual_vnfc
.. _userdata_standard for 2023.2 Bobcat:
  https://opendev.org/openstack/tacker/src/branch/stable/2023.2/tacker/tests/functional/sol_v2_common/samples/userdata_standard
.. _userdata_standard_change_vnfpkg_nw for 2023.2 Bobcat:
  https://opendev.org/openstack/tacker/src/branch/stable/2023.2/tacker/tests/functional/sol_v2_common/samples/userdata_standard_change_vnfpkg_nw
