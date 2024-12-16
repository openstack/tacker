=======================================
VNF Lifecycle Management with v1 Tacker
=======================================

This document describes how to manage VNF Lifecycle with CLI in Tacker v1 API.

.. note::

  The content of this document has been confirmed to work
  using the following VNF packages.

  * `sample_vnf_package_csar for 2024.1 Caracal`_
  * `functional5 for 2024.1 Caracal`_


.. note::

  This is a document for Tacker v1 API.
  See :doc:`/cli/v2/vnflcm` for Tacker v2 API.


Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

A default VIM should be registered according to :doc:`cli-legacy-vim`.

CLI Reference for VNF Lifecycle Management
------------------------------------------

.. note::

    Commands call version 1 VNF LCM APIs by default.
    You can also call the version 1 VNF LCM APIs specifically
    by using the option **\-\-os-tacker-api-version 1**.


1. Create VNF Identifier
^^^^^^^^^^^^^^^^^^^^^^^^

The `VNFD_ID` should be replaced with the VNFD ID in VNF Package.

.. code-block:: console

  $ openstack vnflcm create VNFD_ID


Result:

.. code-block:: console

  +-----------------------------+------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                            |
  +-----------------------------+------------------------------------------------------------------------------------------------------------------+
  | ID                          | 74c71ef9-b223-4a5f-9987-de476eab122f                                                                             |
  | Instantiation State         | NOT_INSTANTIATED                                                                                                 |
  | Links                       | {                                                                                                                |
  |                             |     "self": {                                                                                                    |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/74c71ef9-b223-4a5f-9987-de476eab122f"             |
  |                             |     },                                                                                                           |
  |                             |     "instantiate": {                                                                                             |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/74c71ef9-b223-4a5f-9987-de476eab122f/instantiate" |
  |                             |     }                                                                                                            |
  |                             | }                                                                                                                |
  | VNF Configurable Properties |                                                                                                                  |
  | VNF Instance Description    |                                                                                                                  |
  | VNF Instance Name           | vnf-74c71ef9-b223-4a5f-9987-de476eab122f                                                                         |
  | VNF Package ID              | 5ac73423-f102-4574-911e-578dad9fa8fe                                                                             |
  | VNF Product Name            | Sample VNF                                                                                                       |
  | VNF Provider                | Company                                                                                                          |
  | VNF Software Version        | 1.0                                                                                                              |
  | VNFD ID                     | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177                                                                             |
  | VNFD Version                | 1.0                                                                                                              |
  +-----------------------------+------------------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm create --help
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

The `VNF_INSTANCE_ID` and `SAMPLE_PARAM_FILE.json` should be replaced
with the ID of VNF instance and the path of parameter json file
that will be used to instantiate VNF, respectively.

.. code-block:: console

  $ openstack vnflcm instantiate VNF_INSTANCE_ID \
    SAMPLE_PARAM_FILE.json


Result:

.. code-block:: console

  Instantiate request for VNF Instance 74c71ef9-b223-4a5f-9987-de476eab122f has been accepted.


Help:

.. code-block:: console

  $ openstack vnflcm instantiate --help
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

  $ openstack vnflcm list


Result:

.. code-block:: console

  +--------------------------------------+-----------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
  | ID                                   | VNF Instance Name     | Instantiation State | VNF Provider | VNF Software Version | VNF Product Name | VNFD ID                              |
  +--------------------------------------+-----------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
  | 74c71ef9-b223-4a5f-9987-de476eab122f | Updated instance name | INSTANTIATED        | Company      | 1.0                  | Sample VNF       | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177 |
  +--------------------------------------+-----------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm list --help
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

  $ openstack vnflcm show VNF_INSTANCE_ID


Result:

.. code-block:: console

  +-----------------------------+----------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------+
  | ID                          | 74c71ef9-b223-4a5f-9987-de476eab122f                                                                                 |
  | Instantiated Vnf Info       | {                                                                                                                    |
  |                             |     "flavourId": "simple",                                                                                           |
  |                             |     "vnfState": "STARTED",                                                                                           |
  |                             |     "extCpInfo": [],                                                                                                 |
  |                             |     "vnfcResourceInfo": [                                                                                            |
  |                             |         {                                                                                                            |
  |                             |             "id": "149d21ec-02a8-456f-af0e-0a91652cc31a",                                                            |
  |                             |             "vduId": "VDU1",                                                                                         |
  |                             |             "computeResource": {                                                                                     |
  |                             |                 "vimConnectionId": "fa9fa87e-8be2-425d-85e1-08778d82d95f",                                           |
  |                             |                 "resourceId": "6508f3fc-065d-4387-893d-95366e6854a5",                                                |
  |                             |                 "vimLevelResourceType": "OS::Nova::Server"                                                           |
  |                             |             },                                                                                                       |
  |                             |             "storageResourceIds": [],                                                                                |
  |                             |             "vnfcCpInfo": [                                                                                          |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "d33ced0e-7337-44e8-b4b5-2c1cdad41a28",                                                    |
  |                             |                     "cpdId": "CP1",                                                                                  |
  |                             |                     "vnfExtCpId": null,                                                                              |
  |                             |                     "vnfLinkPortId": "06c2a88b-7cde-409e-9235-4174c49624c1"                                          |
  |                             |                 }                                                                                                    |
  |                             |             ]                                                                                                        |
  |                             |         }                                                                                                            |
  |                             |     ],                                                                                                               |
  |                             |     "vnfVirtualLinkResourceInfo": [                                                                                  |
  |                             |         {                                                                                                            |
  |                             |             "id": "2a364ed3-cfe4-40a6-ac78-79b773bddf5c",                                                            |
  |                             |             "vnfVirtualLinkDescId": "internalVL1",                                                                   |
  |                             |             "networkResource": {                                                                                     |
  |                             |                 "vimConnectionId": "fa9fa87e-8be2-425d-85e1-08778d82d95f",                                           |
  |                             |                 "resourceId": "4695aa24-a3ab-41f9-bfc3-59cd75f21e4f",                                                |
  |                             |                 "vimLevelResourceType": "OS::Neutron::Net"                                                           |
  |                             |             },                                                                                                       |
  |                             |             "vnfLinkPorts": [                                                                                        |
  |                             |                 {                                                                                                    |
  |                             |                     "id": "06c2a88b-7cde-409e-9235-4174c49624c1",                                                    |
  |                             |                     "resourceHandle": {                                                                              |
  |                             |                         "vimConnectionId": "fa9fa87e-8be2-425d-85e1-08778d82d95f",                                   |
  |                             |                         "resourceId": "7d118835-da4c-4e8f-8def-dba2377ab446",                                        |
  |                             |                         "vimLevelResourceType": "OS::Neutron::Port"                                                  |
  |                             |                     },                                                                                               |
  |                             |                     "cpInstanceId": "d33ced0e-7337-44e8-b4b5-2c1cdad41a28"                                           |
  |                             |                 }                                                                                                    |
  |                             |             ]                                                                                                        |
  |                             |         }                                                                                                            |
  |                             |     ],                                                                                                               |
  |                             |     "vnfcInfo": [                                                                                                    |
  |                             |         {                                                                                                            |
  |                             |             "id": "c1a2c1f8-60ba-4db6-aa64-416263c45801",                                                            |
  |                             |             "vduId": "VDU1",                                                                                         |
  |                             |             "vnfcState": "STARTED"                                                                                   |
  |                             |         }                                                                                                            |
  |                             |     ],                                                                                                               |
  |                             |     "additionalParams": {}                                                                                           |
  |                             | }                                                                                                                    |
  | Instantiation State         | INSTANTIATED                                                                                                         |
  | Links                       | {                                                                                                                    |
  |                             |     "self": {                                                                                                        |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/74c71ef9-b223-4a5f-9987-de476eab122f"                 |
  |                             |     },                                                                                                               |
  |                             |     "terminate": {                                                                                                   |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/74c71ef9-b223-4a5f-9987-de476eab122f/terminate"       |
  |                             |     },                                                                                                               |
  |                             |     "scale": {                                                                                                       |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/74c71ef9-b223-4a5f-9987-de476eab122f/scale"           |
  |                             |     },                                                                                                               |
  |                             |     "heal": {                                                                                                        |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/74c71ef9-b223-4a5f-9987-de476eab122f/heal"            |
  |                             |     },                                                                                                               |
  |                             |     "changeExtConn": {                                                                                               |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/74c71ef9-b223-4a5f-9987-de476eab122f/change_ext_conn" |
  |                             |     }                                                                                                                |
  |                             | }                                                                                                                    |
  | VIM Connection Info         | [                                                                                                                    |
  |                             |     {                                                                                                                |
  |                             |         "id": "e24f9796-a8e9-4cb0-85ce-5920dcddafa1",                                                                |
  |                             |         "vimId": "fa9fa87e-8be2-425d-85e1-08778d82d95f",                                                             |
  |                             |         "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_2",                                                                 |
  |                             |         "interfaceInfo": {},                                                                                         |
  |                             |         "accessInfo": {},                                                                                            |
  |                             |         "extra": {}                                                                                                  |
  |                             |     },                                                                                                               |
  |                             |     {                                                                                                                |
  |                             |         "id": "467746fa-248b-464c-ad81-3f01c4eacdf5",                                                                |
  |                             |         "vimId": "fa9fa87e-8be2-425d-85e1-08778d82d95f",                                                             |
  |                             |         "vimType": "openstack",                                                                                      |
  |                             |         "interfaceInfo": {},                                                                                         |
  |                             |         "accessInfo": {},                                                                                            |
  |                             |         "extra": {}                                                                                                  |
  |                             |     }                                                                                                                |
  |                             | ]                                                                                                                    |
  | VNF Configurable Properties |                                                                                                                      |
  | VNF Instance Description    |                                                                                                                      |
  | VNF Instance Name           | vnf-74c71ef9-b223-4a5f-9987-de476eab122f                                                                             |
  | VNF Package ID              | 5ac73423-f102-4574-911e-578dad9fa8fe                                                                                 |
  | VNF Product Name            | Sample VNF                                                                                                           |
  | VNF Provider                | Company                                                                                                              |
  | VNF Software Version        | 1.0                                                                                                                  |
  | VNFD ID                     | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177                                                                                 |
  | VNFD Version                | 1.0                                                                                                                  |
  | metadata                    | tenant=admin                                                                                                         |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm show --help
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

  $ openstack vnflcm terminate VNF_INSTANCE_ID


Result:

.. code-block:: console

  Terminate request for VNF Instance '74c71ef9-b223-4a5f-9987-de476eab122f' has been accepted.


Help:

.. code-block:: console

  $ openstack vnflcm terminate --help
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

  $ openstack vnflcm delete VNF_INSTANCE_ID


Result:

.. code-block:: console

  Vnf instance '74c71ef9-b223-4a5f-9987-de476eab122f' is deleted successfully


Help:

.. code-block:: console

  $ openstack vnflcm delete --help
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

  $ openstack vnflcm heal VNF_INSTANCE_ID


.. note::

    <vnf-instance> should either be given before \-\-vnfc-instance
    parameter or it should be separated with '\-\-' separator in
    order to come after \-\-vnfc-instance parameter.


Result:

.. code-block:: console

  Heal request for VNF Instance 74c71ef9-b223-4a5f-9987-de476eab122f has been accepted.


Help:

.. code-block:: console

  $ openstack vnflcm heal --help
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

The `VNF_INSTANCE_ID` and `SAMPLE_PARAM_FILE.json` should be replaced
with the ID of VNF instance and the name of parameter json file
that will be used to update VNF, respectively.

.. code-block:: console

  $ openstack vnflcm update VNF_INSTANCE_ID --I SAMPLE_PARAM_FILE.json


Result:

.. code-block:: console

  Update vnf:74c71ef9-b223-4a5f-9987-de476eab122f


Help:

.. code-block:: console

  $ openstack vnflcm update --help
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

The `VNF_INSTANCE_ID` and `WORKER_INSTANCE` should be replaced
with the ID of VNF instance and the ID of the target scaling group, respectively.
See 'How to Identify ASPECT_ID' in :doc:`/user/etsi_vnf_scaling` for details.

.. code-block:: console

  $ openstack vnflcm scale --type SCALE_OUT --aspect-id WORKER_INSTANCE \
    VNF_INSTANCE_ID


Result:

.. code-block:: console

  Scale request for VNF Instance 634825bf-6a70-47d2-b4e1-1ed9ba4c6938 has been accepted.


Help:

.. code-block:: console

  $ openstack vnflcm scale --help
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


The `VNF_INSTANCE_ID` and `SAMPLE_PARAM_FILE.json` should be replaced
with the ID of VNF instance and the path of parameter json file
that will be used to change external VNF connectivity, respectively.

.. code-block:: console

  $ openstack vnflcm change-ext-conn VNF_INSTANCE_ID \
    SAMPLE_PARAM_FILE.json


Result:

.. code-block:: console

  Change External VNF Connectivity for VNF Instance 634825bf-6a70-47d2-b4e1-1ed9ba4c6938 has been accepted.


Help:

.. code-block:: console

  $ openstack vnflcm change-ext-conn --help
  usage: openstack vnflcm change-ext-conn [-h] <vnf-instance> <param-file>

  Change External VNF Connectivity

  positional arguments:
    <vnf-instance>
                          VNF instance ID to Change External VNF Connectivity
    <param-file>  Specify change-ext-conn request parameters in a json file.

  options:
    -h, --help            show this help message and exit

  This command is provided by the python-tackerclient plugin.


11. Rollback VNF Lifecycle Management Operation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `VNF_LCM_OP_OCC_ID` should be replaced with the ID of the target
lifecycle management operation temporary failed.

.. code-block:: console

  $ openstack vnflcm op rollback VNF_LCM_OP_OCC_ID


Result:

.. code-block:: console

  Rollback request for LCM operation 9e53e4f9-2a37-4557-9259-2c0e078bd977 has been accepted


Help:

.. code-block:: console

  $ openstack vnflcm op rollback --help
  usage: openstack vnflcm op rollback [-h] <vnf-lcm-op-occ-id>

  positional arguments:
    <vnf-lcm-op-occ-id>
                          VNF lifecycle management operation occurrence ID.

  options:
    -h, --help            show this help message and exit

  This command is provided by the python-tackerclient plugin.


12. Cancel VNF Lifecycle Management Operation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `VNF_LCM_OP_OCC_ID` should be replaced with the ID of the target
lifecycle management operation currently processing.

.. code-block:: console

  openstack vnflcm op cancel VNF_LCM_OP_OCC_ID


Result:

.. code-block:: console

  Cancel request for LCM operation 998d949f-73a6-42f6-b8cd-f8f1009b0ece has been accepted


Help:

.. code-block:: console

  $ openstack vnflcm op cancel --help
  usage: openstack vnflcm op cancel [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                    [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                    [--fit-width] [--print-empty] [--cancel-mode <cancel-mode>]
                                    <vnf-lcm-op-occ-id>

  Cancel VNF Instance

  positional arguments:
    <vnf-lcm-op-occ-id>
                          VNF lifecycle management operation occurrence ID.

  options:
    -h, --help            show this help message and exit
    --cancel-mode <cancel-mode>
                          Cancel mode can be 'GRACEFUL' or 'FORCEFUL'. Default is 'GRACEFUL'

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


13. Retry VNF Lifecycle Management Operation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `VNF_LCM_OP_OCC_ID` should be replaced with the ID of the target
lifecycle management operation temporary failed.

.. code-block:: console

  $ openstack vnflcm op retry VNF_LCM_OP_OCC_ID


Result:

.. code-block:: console

  Retry request for LCM operation f2c0e013-fa36-4239-b6e9-f320632944c2 has been accepted


Help:

.. code-block:: console

  $ openstack vnflcm op retry --help
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

  $ openstack vnflcm op fail VNF_LCM_OP_OCC_ID


Result:

.. code-block:: console

  +-------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field                   | Value                                                                                                                                                                        |
  +-------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Error                   | {                                                                                                                                                                            |
  |                         |     "title": "",                                                                                                                                                             |
  |                         |     "status": 500,                                                                                                                                                           |
  |                         |     "detail": "ProblemDetails(created_at=<?>,deleted=0,deleted_at=<?>,detail='The sample-script specified in the VNFD is inconsistent with the MgmtDriver in the             |
  |                         | configuration file.',status=500,title='',updated_at=<?>)"                                                                                                                    |
  |                         | }                                                                                                                                                                            |
  | ID                      | f2c0e013-fa36-4239-b6e9-f320632944c2                                                                                                                                         |
  | Is Automatic Invocation | False                                                                                                                                                                        |
  | Is Cancel Pending       | False                                                                                                                                                                        |
  | Links                   | {                                                                                                                                                                            |
  |                         |     "self": {                                                                                                                                                                |
  |                         |         "href": "http://localhost:9890/vnflcm/v1/vnf_lcm_op_occs/f2c0e013-fa36-4239-b6e9-f320632944c2"                                                                       |
  |                         |     },                                                                                                                                                                       |
  |                         |     "vnfInstance": {                                                                                                                                                         |
  |                         |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/5f65bf54-cb06-4e9a-ac4f-b2ff0862c5f0"                                                                         |
  |                         |     },                                                                                                                                                                       |
  |                         |     "retry": {                                                                                                                                                               |
  |                         |         "href": "http://localhost:9890/vnflcm/v1/vnf_lcm_op_occs/f2c0e013-fa36-4239-b6e9-f320632944c2/retry"                                                                 |
  |                         |     },                                                                                                                                                                       |
  |                         |     "rollback": {                                                                                                                                                            |
  |                         |         "href": "http://localhost:9890/vnflcm/v1/vnf_lcm_op_occs/f2c0e013-fa36-4239-b6e9-f320632944c2/rollback"                                                              |
  |                         |     },                                                                                                                                                                       |
  |                         |     "grant": {                                                                                                                                                               |
  |                         |         "href": "http://localhost:9890/vnflcm/v1/vnf_lcm_op_occs/f2c0e013-fa36-4239-b6e9-f320632944c2/grant"                                                                 |
  |                         |     },                                                                                                                                                                       |
  |                         |     "fail": {                                                                                                                                                                |
  |                         |         "href": "http://localhost:9890/vnflcm/v1/vnf_lcm_op_occs/f2c0e013-fa36-4239-b6e9-f320632944c2/fail"                                                                  |
  |                         |     }                                                                                                                                                                        |
  |                         | }                                                                                                                                                                            |
  | Operation               | INSTANTIATE                                                                                                                                                                  |
  | Operation State         | FAILED                                                                                                                                                                       |
  | Start Time              | 2024-05-15 07:07:04+00:00                                                                                                                                                    |
  | State Entered Time      | 2024-05-15 07:09:20.964769+00:00                                                                                                                                             |
  | VNF Instance ID         | 5f65bf54-cb06-4e9a-ac4f-b2ff0862c5f0                                                                                                                                         |
  | grantId                 | None                                                                                                                                                                         |
  | operationParams         | "{\"flavourId\": \"simple\", \"instantiationLevelId\": \"instantiation_level_1\", \"extVirtualLinks\": [{\"id\": \"073b1b7d-fed9-48c2-8515-f07f36e0fac6\",                   |
  |                         | \"vimConnectionId\": \"6bb975f4-387f-44d3-8cea-596b065c47c8\", \"resourceProviderId\": \"Company\", \"resourceId\": \"3ee73151-4382-4bee-9344-1ee829b32969\", \"extCps\":    |
  |                         | [{\"cpdId\": \"VDU1_CP1\", \"cpConfig\": [{\"VDU1_CP1\": {\"parentCpConfigId\": \"b06c86c9-dfa8-4e3c-848c-928667d7155b\", \"cpProtocolData\": [{\"layerProtocol\":           |
  |                         | \"IP_OVER_ETHERNET\", \"ipOverEthernet\": {\"ipAddresses\": [{\"type\": \"IPV4\", \"numDynamicAddresses\": 1, \"subnetId\":                                                  |
  |                         | \"41b13a15-558c-4022-91c4-2702e3af3266\"}]}}]}}]}]}, {\"id\": \"876050f5-86a8-42de-957d-65750c72c94c\", \"vimConnectionId\": \"6bb975f4-387f-44d3-8cea-596b065c47c8\",       |
  |                         | \"resourceProviderId\": \"Company\", \"resourceId\": \"c0bcd736-d5b1-43f5-89f6-e9cfe0015fd9\", \"extCps\": [{\"cpdId\": \"VDU1_CP2\", \"cpConfig\": [{\"VDU1_CP2\":          |
  |                         | {\"parentCpConfigId\": \"08e2a40f-26f1-45e6-adec-682006c8c02a\", \"cpProtocolData\": [{\"layerProtocol\": \"IP_OVER_ETHERNET\", \"ipOverEthernet\": {\"ipAddresses\":        |
  |                         | [{\"type\": \"IPV4\", \"numDynamicAddresses\": 1, \"subnetId\": \"a7a1552b-c78b-403c-b1eb-7f98446a24d2\"}]}}]}}]}, {\"cpdId\": \"VDU2_CP2\", \"cpConfig\": [{\"VDU2_CP2\":   |
  |                         | {\"parentCpConfigId\": \"bd74eb08-2165-4921-9bbd-967ede4c9f1f\", \"cpProtocolData\": [{\"layerProtocol\": \"IP_OVER_ETHERNET\", \"ipOverEthernet\": {\"macAddress\":         |
  |                         | \"fa:16:3e:fa:22:75\", \"ipAddresses\": [{\"type\": \"IPV4\", \"fixedAddresses\": [\"100.100.100.11\"], \"subnetId\": \"a7a1552b-c78b-403c-b1eb-7f98446a24d2\"}, {\"type\":  |
  |                         | \"IPV6\", \"numDynamicAddresses\": 1, \"subnetId\": \"70129667-f3e9-4b3f-9e4f-bff5c3887d7f\"}]}}]}}]}]}], \"extManagedVirtualLinks\": [{\"id\":                              |
  |                         | \"97d23d57-a375-4727-ab43-8df097251cd2\", \"vnfVirtualLinkDescId\": \"internalVL1\", \"vimConnectionId\": \"6bb975f4-387f-44d3-8cea-596b065c47c8\", \"resourceProviderId\":  |
  |                         | \"Company\", \"resourceId\": \"53a2b530-d2dd-407f-b103-4828a53118d5\", \"extManagedMultisiteVirtualLinkId\": \"15d0159d-01dd-4b73-a78b-a1f20e615f76\"}, {\"id\":             |
  |                         | \"4947006f-4941-4c55-94b0-ee1081c00fab\", \"vnfVirtualLinkDescId\": \"internalVL2\", \"vimConnectionId\": \"6bb975f4-387f-44d3-8cea-596b065c47c8\", \"resourceProviderId\":  |
  |                         | \"Company\", \"resourceId\": \"6ab1c324-947c-4e1c-8590-7d9e301d68bc\", \"extManagedMultisiteVirtualLinkId\": \"ec853a00-395a-488e-aa88-7c1a545cd8a5\"}],                     |
  |                         | \"localizationLanguage\": \"ja\", \"additionalParams\": {\"lcm-operation-user-data\": \"./UserData/userdata_standard.py\", \"lcm-operation-user-data-class\":                |
  |                         | \"StandardUserData\"}, \"extensions\": {\"dummy-key\": \"dummy-val\"}, \"vnfConfigurableProperties\": {\"dummy-key\": \"dummy-val\"}}"                                       |
  | resourceChanges         | {}                                                                                                                                                                           |
  +-------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm op fail --help
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

  $ openstack vnflcm op list


Result:

.. code-block:: console

  +--------------------------------------+-----------------+--------------------------------------+-------------+
  | ID                                   | Operation State | VNF Instance ID                      | Operation   |
  +--------------------------------------+-----------------+--------------------------------------+-------------+
  | 78ad4bed-02f3-480a-a0ee-9bd07589b092 | COMPLETED       | 74c71ef9-b223-4a5f-9987-de476eab122f | INSTANTIATE |
  +--------------------------------------+-----------------+--------------------------------------+-------------+


Help:

.. code-block:: console

  $ openstack vnflcm op list --help
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

  $ openstack vnflcm op show VNF_LCM_OP_OCC_ID


Result:

.. code-block:: console

  +-------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field                         | Value                                                                                                                                                                  |
  +-------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Cancel Mode                   |                                                                                                                                                                        |
  | Changed External Connectivity |                                                                                                                                                                        |
  | Changed Info                  |                                                                                                                                                                        |
  | Error                         | {                                                                                                                                                                      |
  |                               |     "title": "",                                                                                                                                                       |
  |                               |     "status": 500,                                                                                                                                                     |
  |                               |     "detail": "The sample-script specified in the VNFD is inconsistent with the MgmtDriver in the configuration file."                                                 |
  |                               | }                                                                                                                                                                      |
  | Grant ID                      | None                                                                                                                                                                   |
  | ID                            | f2c0e013-fa36-4239-b6e9-f320632944c2                                                                                                                                   |
  | Is Automatic Invocation       | False                                                                                                                                                                  |
  | Is Cancel Pending             | False                                                                                                                                                                  |
  | Links                         | {                                                                                                                                                                      |
  |                               |     "self": {                                                                                                                                                          |
  |                               |         "href": "http://localhost:9890/vnflcm/v1/vnf_lcm_op_occs/f2c0e013-fa36-4239-b6e9-f320632944c2"                                                                 |
  |                               |     },                                                                                                                                                                 |
  |                               |     "vnfInstance": {                                                                                                                                                   |
  |                               |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/5f65bf54-cb06-4e9a-ac4f-b2ff0862c5f0"                                                                   |
  |                               |     },                                                                                                                                                                 |
  |                               |     "retry": {                                                                                                                                                         |
  |                               |         "href": "http://localhost:9890/vnflcm/v1/vnf_lcm_op_occs/f2c0e013-fa36-4239-b6e9-f320632944c2/retry"                                                           |
  |                               |     },                                                                                                                                                                 |
  |                               |     "rollback": {                                                                                                                                                      |
  |                               |         "href": "http://localhost:9890/vnflcm/v1/vnf_lcm_op_occs/f2c0e013-fa36-4239-b6e9-f320632944c2/rollback"                                                        |
  |                               |     },                                                                                                                                                                 |
  |                               |     "grant": {                                                                                                                                                         |
  |                               |         "href": "http://localhost:9890/vnflcm/v1/vnf_lcm_op_occs/f2c0e013-fa36-4239-b6e9-f320632944c2/grant"                                                           |
  |                               |     },                                                                                                                                                                 |
  |                               |     "fail": {                                                                                                                                                          |
  |                               |         "href": "http://localhost:9890/vnflcm/v1/vnf_lcm_op_occs/f2c0e013-fa36-4239-b6e9-f320632944c2/fail"                                                            |
  |                               |     }                                                                                                                                                                  |
  |                               | }                                                                                                                                                                      |
  | Operation                     | INSTANTIATE                                                                                                                                                            |
  | Operation Parameters          | "{\"flavourId\": \"simple\", \"instantiationLevelId\": \"instantiation_level_1\", \"extVirtualLinks\": [{\"id\": \"073b1b7d-fed9-48c2-8515-f07f36e0fac6\",             |
  |                               | \"vimConnectionId\": \"6bb975f4-387f-44d3-8cea-596b065c47c8\", \"resourceProviderId\": \"Company\", \"resourceId\": \"3ee73151-4382-4bee-9344-1ee829b32969\",          |
  |                               | \"extCps\": [{\"cpdId\": \"VDU1_CP1\", \"cpConfig\": [{\"VDU1_CP1\": {\"parentCpConfigId\": \"b06c86c9-dfa8-4e3c-848c-928667d7155b\", \"cpProtocolData\":              |
  |                               | [{\"layerProtocol\": \"IP_OVER_ETHERNET\", \"ipOverEthernet\": {\"ipAddresses\": [{\"type\": \"IPV4\", \"numDynamicAddresses\": 1, \"subnetId\":                       |
  |                               | \"41b13a15-558c-4022-91c4-2702e3af3266\"}]}}]}}]}]}, {\"id\": \"876050f5-86a8-42de-957d-65750c72c94c\", \"vimConnectionId\": \"6bb975f4-387f-44d3-8cea-596b065c47c8\", |
  |                               | \"resourceProviderId\": \"Company\", \"resourceId\": \"c0bcd736-d5b1-43f5-89f6-e9cfe0015fd9\", \"extCps\": [{\"cpdId\": \"VDU1_CP2\", \"cpConfig\": [{\"VDU1_CP2\":    |
  |                               | {\"parentCpConfigId\": \"08e2a40f-26f1-45e6-adec-682006c8c02a\", \"cpProtocolData\": [{\"layerProtocol\": \"IP_OVER_ETHERNET\", \"ipOverEthernet\": {\"ipAddresses\":  |
  |                               | [{\"type\": \"IPV4\", \"numDynamicAddresses\": 1, \"subnetId\": \"a7a1552b-c78b-403c-b1eb-7f98446a24d2\"}]}}]}}]}, {\"cpdId\": \"VDU2_CP2\", \"cpConfig\":             |
  |                               | [{\"VDU2_CP2\": {\"parentCpConfigId\": \"bd74eb08-2165-4921-9bbd-967ede4c9f1f\", \"cpProtocolData\": [{\"layerProtocol\": \"IP_OVER_ETHERNET\", \"ipOverEthernet\":    |
  |                               | {\"macAddress\": \"fa:16:3e:fa:22:75\", \"ipAddresses\": [{\"type\": \"IPV4\", \"fixedAddresses\": [\"100.100.100.11\"], \"subnetId\":                                 |
  |                               | \"a7a1552b-c78b-403c-b1eb-7f98446a24d2\"}, {\"type\": \"IPV6\", \"numDynamicAddresses\": 1, \"subnetId\": \"70129667-f3e9-4b3f-9e4f-bff5c3887d7f\"}]}}]}}]}]}],        |
  |                               | \"extManagedVirtualLinks\": [{\"id\": \"97d23d57-a375-4727-ab43-8df097251cd2\", \"vnfVirtualLinkDescId\": \"internalVL1\", \"vimConnectionId\":                        |
  |                               | \"6bb975f4-387f-44d3-8cea-596b065c47c8\", \"resourceProviderId\": \"Company\", \"resourceId\": \"53a2b530-d2dd-407f-b103-4828a53118d5\",                               |
  |                               | \"extManagedMultisiteVirtualLinkId\": \"15d0159d-01dd-4b73-a78b-a1f20e615f76\"}, {\"id\": \"4947006f-4941-4c55-94b0-ee1081c00fab\", \"vnfVirtualLinkDescId\":          |
  |                               | \"internalVL2\", \"vimConnectionId\": \"6bb975f4-387f-44d3-8cea-596b065c47c8\", \"resourceProviderId\": \"Company\", \"resourceId\":                                   |
  |                               | \"6ab1c324-947c-4e1c-8590-7d9e301d68bc\", \"extManagedMultisiteVirtualLinkId\": \"ec853a00-395a-488e-aa88-7c1a545cd8a5\"}], \"localizationLanguage\": \"ja\",          |
  |                               | \"additionalParams\": {\"lcm-operation-user-data\": \"./UserData/userdata_standard.py\", \"lcm-operation-user-data-class\": \"StandardUserData\"}, \"extensions\":     |
  |                               | {\"dummy-key\": \"dummy-val\"}, \"vnfConfigurableProperties\": {\"dummy-key\": \"dummy-val\"}}"                                                                        |
  | Operation State               | FAILED_TEMP                                                                                                                                                            |
  | Resource Changes              |                                                                                                                                                                        |
  | Start Time                    | 2024-05-15 07:07:04+00:00                                                                                                                                              |
  | State Entered Time            | 2024-05-15 07:07:04+00:00                                                                                                                                              |
  | VNF Instance ID               | 5f65bf54-cb06-4e9a-ac4f-b2ff0862c5f0                                                                                                                                   |
  +-------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm op show --help
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

The `SAMPLE_PARAM_FILE.json` should be replaced with the path of
parameter json file that will be used to create Lccn subscription.

.. code-block:: console

  $ openstack vnflcm subsc create SAMPLE_PARAM_FILE.json


Result:

.. code-block:: console

  +--------------+------------------------------------------------------------------------------------------------------+
  | Field        | Value                                                                                                |
  +--------------+------------------------------------------------------------------------------------------------------+
  | Callback URI | http://localhost:9990/notification/callback/test                                                     |
  | Filter       | {                                                                                                    |
  |              |     "vnfInstanceSubscriptionFilter": {                                                               |
  |              |         "vnfProductsFromProviders": [                                                                |
  |              |             {                                                                                        |
  |              |                 "vnfProvider": "Company",                                                            |
  |              |                 "vnfProducts": [                                                                     |
  |              |                     {                                                                                |
  |              |                         "vnfProductName": "Sample VNF",                                              |
  |              |                         "versions": [                                                                |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.0",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.0"                                                            |
  |              |                                 ]                                                                    |
  |              |                             }                                                                        |
  |              |                         ]                                                                            |
  |              |                     }                                                                                |
  |              |                 ]                                                                                    |
  |              |             }                                                                                        |
  |              |         ]                                                                                            |
  |              |     },                                                                                               |
  |              |     "notificationTypes": [                                                                           |
  |              |         "VnfLcmOperationOccurrenceNotification",                                                     |
  |              |         "VnfIdentifierCreationNotification",                                                         |
  |              |         "VnfIdentifierDeletionNotification"                                                          |
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
  |              |         "STARTING"                                                                                   |
  |              |     ]                                                                                                |
  |              | }                                                                                                    |
  | ID           | 9926b5a9-9ae7-4068-a77d-20c108d7b91d                                                                 |
  | Links        | {                                                                                                    |
  |              |     "self": {                                                                                        |
  |              |         "href": "http://localhost:9890/vnflcm/v1/subscriptions/9926b5a9-9ae7-4068-a77d-20c108d7b91d" |
  |              |     }                                                                                                |
  |              | }                                                                                                    |
  +--------------+------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm subsc create --help
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

  $ openstack vnflcm subsc list


Result:

.. code-block:: console

  +--------------------------------------+--------------------------------------------------+
  | ID                                   | Callback URI                                     |
  +--------------------------------------+--------------------------------------------------+
  | 9926b5a9-9ae7-4068-a77d-20c108d7b91d | http://localhost:9990/notification/callback/test |
  +--------------------------------------+--------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm subsc list --help
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

  $ openstack vnflcm subsc show LCCN_SUBSCRIPTION_ID


Result:

.. code-block:: console

  +--------------+------------------------------------------------------------------------------------------------------+
  | Field        | Value                                                                                                |
  +--------------+------------------------------------------------------------------------------------------------------+
  | Callback URI | http://localhost:9990/notification/callback/test                                                     |
  | Filter       | {                                                                                                    |
  |              |     "operationTypes": [                                                                              |
  |              |         "INSTANTIATE",                                                                               |
  |              |         "SCALE",                                                                                     |
  |              |         "TERMINATE",                                                                                 |
  |              |         "HEAL",                                                                                      |
  |              |         "MODIFY_INFO",                                                                               |
  |              |         "CHANGE_EXT_CONN"                                                                            |
  |              |     ],                                                                                               |
  |              |     "operationStates": [                                                                             |
  |              |         "STARTING"                                                                                   |
  |              |     ],                                                                                               |
  |              |     "notificationTypes": [                                                                           |
  |              |         "VnfLcmOperationOccurrenceNotification",                                                     |
  |              |         "VnfIdentifierCreationNotification",                                                         |
  |              |         "VnfIdentifierDeletionNotification"                                                          |
  |              |     ],                                                                                               |
  |              |     "vnfInstanceSubscriptionFilter": {                                                               |
  |              |         "vnfProductsFromProviders": [                                                                |
  |              |             {                                                                                        |
  |              |                 "vnfProvider": "Company",                                                            |
  |              |                 "vnfProducts": [                                                                     |
  |              |                     {                                                                                |
  |              |                         "vnfProductName": "Sample VNF",                                              |
  |              |                         "versions": [                                                                |
  |              |                             {                                                                        |
  |              |                                 "vnfSoftwareVersion": "1.0",                                         |
  |              |                                 "vnfdVersions": [                                                    |
  |              |                                     "1.0"                                                            |
  |              |                                 ]                                                                    |
  |              |                             }                                                                        |
  |              |                         ]                                                                            |
  |              |                     }                                                                                |
  |              |                 ]                                                                                    |
  |              |             }                                                                                        |
  |              |         ]                                                                                            |
  |              |     }                                                                                                |
  |              | }                                                                                                    |
  | ID           | 9926b5a9-9ae7-4068-a77d-20c108d7b91d                                                                 |
  | Links        | {                                                                                                    |
  |              |     "self": {                                                                                        |
  |              |         "href": "http://localhost:9890/vnflcm/v1/subscriptions/9926b5a9-9ae7-4068-a77d-20c108d7b91d" |
  |              |     }                                                                                                |
  |              | }                                                                                                    |
  +--------------+------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm subsc show --help
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

  $ openstack vnflcm delete LCCN_SUBSCRIPTION_ID


Result:

.. code-block:: console

  Lccn Subscription '9926b5a9-9ae7-4068-a77d-20c108d7b91d' is deleted successfully


Help:

.. code-block:: console

  $ openstack vnflcm subsc delete --help
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

    Running the command with **\-\-major-version 1** option shows v1 Tacker's version only.


.. code-block:: console

  $ openstack vnflcm versions --major-version 1
  +-------------+-----------------------------------------------+
  | Field       | Value                                         |
  +-------------+-----------------------------------------------+
  | uriPrefix   | /vnflcm/v1                                    |
  | apiVersions | [{'version': '1.3.0', 'isDeprecated': False}] |
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


.. _sample_vnf_package_csar for 2024.1 Caracal:
  https://opendev.org/openstack/tacker/src/branch/stable/2024.1/samples/etsi_getting_started/tosca/sample_vnf_package_csar
.. _functional5 for 2024.1 Caracal:
  https://opendev.org/openstack/tacker/src/branch/stable/2024.1/samples/tests/etc/samples/etsi/nfv/functional5
