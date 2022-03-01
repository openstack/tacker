========================
VNF Lifecycle Management
========================

This document describes how to manage VNF Lifecycle with CLI in Tacker.

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

A default VIM should be registered according to :doc:`cli-legacy-vim`.

CLI Reference for VNF Lifecycle Management
------------------------------------------

.. note::
    Commands call version 1 vnflcm APIs by default.
    You can call the specific version of vnflcm APIs
    by using the option **\-\-os-tacker-api-version**.
    Commands with **\-\-os-tacker-api-version 2** call version 2 vnflcm APIs.

.. note::
    In Yoga release, version 2 vnflcm APIs of instantiate vnf,
    terminate vnf, scale vnf, heal vnf, change external vnf connectivity,
    rollback, retry and fail only support VNF, not CNF. CNF will be supported
    by version 2 vnflcm APIs in future releases.

1. Create VNF Identifier
^^^^^^^^^^^^^^^^^^^^^^^^

The `VNFD_ID` should be replaced with the VNFD ID in VNF Package. In the
following sample, `b1bb0ce7-ebca-4fa7-95ed-4840d70a1177` is used.

.. code-block:: console

  $ openstack vnflcm create VNFD_ID


Result:

.. code-block:: console

  +--------------------------+----------------------------------------------------------------------------------------------+
  | Field                    | Value                                                                                        |
  +--------------------------+----------------------------------------------------------------------------------------------+
  | ID                       | 725f625e-f6b7-4bcd-b1b7-7184039fde45                                                         |
  | Instantiation State      | NOT_INSTANTIATED                                                                             |
  | Links                    | instantiate=href=/vnflcm/v1/vnf_instances/725f625e-f6b7-4bcd-b1b7-7184039fde45/instantiate,  |
  |                          | self=href=/vnflcm/v1/vnf_instances/725f625e-f6b7-4bcd-b1b7-7184039fde45                      |
  | VNF Instance Description | None                                                                                         |
  | VNF Instance Name        | None                                                                                         |
  | VNF Product Name         | Sample VNF                                                                                   |
  | VNF Provider             | Company                                                                                      |
  | VNF Software Version     | 1.0                                                                                          |
  | VNFD ID                  | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177                                                         |
  | VNFD Version             | 1.0                                                                                          |
  +--------------------------+----------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm create --help
  usage: openstack vnflcm create [-h] [-f {json,shell,table,value,yaml}]
                                [-c COLUMN] [--noindent] [--prefix PREFIX]
                                [--max-width <integer>] [--fit-width]
                                [--print-empty] [--name <vnf-instance-name>]
                                [--description <vnf-instance-description>]
                                [--I <param-file>]
                                <vnfd-id>

  Create a new VNF Instance

  positional arguments:
    <vnfd-id>             Identifier that identifies the VNFD which defines the
                          VNF instance to be created.

  optional arguments:
    -h, --help            show this help message and exit
    --name <vnf-instance-name>
                          Name of the VNF instance to be created.
    --description <vnf-instance-description>
                          Description of the VNF instance to be created.
    --I <param-file>      Instantiate VNF subsequently after it's creation.
                          Specify instantiate request parameters in a json file.


2. Instantiate VNF
^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnflcm instantiate VNF_INSTANCE_ID \
       ./sample_param_file.json


Result:

.. code-block:: console

  Instantiate request for VNF Instance 725f625e-f6b7-4bcd-b1b7-7184039fde45 has been accepted.


Help:

.. code-block:: console

  $ openstack vnflcm instantiate --help
  usage: openstack vnflcm instantiate [-h] <vnf-instance> <param-file>

  Instantiate a VNF Instance

  positional arguments:
    <vnf-instance>  VNF instance ID to instantiate
    <param-file>    Specify instantiate request parameters in a json file.

  optional arguments:
    -h, --help      show this help message and exit

3. List VNF
^^^^^^^^^^^

.. code-block:: console

  $ openstack vnflcm list


Result:

.. code-block:: console

  +--------------------------------------+-------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
  | ID                                   | VNF Instance Name | Instantiation State | VNF Provider | VNF Software Version | VNF Product Name | VNFD ID                              |
  +--------------------------------------+-------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
  | 725f625e-f6b7-4bcd-b1b7-7184039fde45 | None              | INSTANTIATED        | Company      | 1.0                  | Sample VNF       | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177 |
  +--------------------------------------+-------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm list --help
  usage: openstack vnflcm list [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN]
                              [--quote {all,minimal,none,nonnumeric}]
                              [--noindent] [--max-width <integer>]
                              [--fit-width] [--print-empty]
                              [--sort-column SORT_COLUMN]

  List VNF Instance

  optional arguments:
    -h, --help            show this help message and exit


4. Show VNF
^^^^^^^^^^^

.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID


Result:

.. code-block:: console

  +--------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field                    | Value                                                                                                                                                       |
  +--------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | ID                       | 725f625e-f6b7-4bcd-b1b7-7184039fde45                                                                                                                        |
  | Instantiated Vnf Info    | , extCpInfo='[]', flavourId='simple', vnfState='STARTED', vnfVirtualLinkResourceInfo='[{'id': '0163cea3-af88-4ef8-ae43-ef3e5e7e827d',                       |
  |                          | 'vnfVirtualLinkDescId': 'internalVL1', 'networkResource': {'resourceId': '073c74b9-670d-4764-a933-6fe4f2f991c1', 'vimLevelResourceType':                    |
  |                          | 'OS::Neutron::Net'}, 'vnfLinkPorts': [{'id': '3b667826-336c-4919-889e-e6c63d959ee6', 'resourceHandle': {'resourceId':                                       |
  |                          | '5d3255b5-e9fb-449f-9c5f-5242049ce2fa', 'vimLevelResourceType': 'OS::Neutron::Port'}, 'cpInstanceId': '3091f046-de63-44c8-ad23-f86128409b27'}]}]',          |
  |                          | vnfcResourceInfo='[{'id': '2a66f545-c90d-49e7-8f17-fb4e57b19c92', 'vduId': 'VDU1', 'computeResource': {'resourceId':                                        |
  |                          | '6afc547d-0e19-46fc-b171-a3d9a0a80513', 'vimLevelResourceType': 'OS::Nova::Server'}, 'storageResourceIds': [], 'vnfcCpInfo': [{'id':                        |
  |                          | '3091f046-de63-44c8-ad23-f86128409b27', 'cpdId': 'CP1', 'vnfExtCpId': None, 'vnfLinkPortId': '3b667826-336c-4919-889e-e6c63d959ee6'}]}]'                    |
  | Instantiation State      | INSTANTIATED                                                                                                                                                |
  | Links                    | heal=href=/vnflcm/v1/vnf_instances/725f625e-f6b7-4bcd-b1b7-7184039fde45/heal, self=href=/vnflcm/v1/vnf_instances/725f625e-f6b7-4bcd-b1b7-7184039fde45,      |
  |                          | terminate=href=/vnflcm/v1/vnf_instances/725f625e-f6b7-4bcd-b1b7-7184039fde45/terminate,                                                                     |
  |                          | changeExtConn=href=/vnflcm/v1/vnf_instances/725f625e-f6b7-4bcd-b1b7-7184039fde45/change_ext_conn                                                            |
  | VIM Connection Info      | []                                                                                                                                                          |
  | VNF Instance Description | None                                                                                                                                                        |
  | VNF Instance Name        | None                                                                                                                                                        |
  | VNF Product Name         | Sample VNF                                                                                                                                                  |
  | VNF Provider             | Company                                                                                                                                                     |
  | VNF Software Version     | 1.0                                                                                                                                                         |
  | VNFD ID                  | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177                                                                                                                        |
  | VNFD Version             | 1.0                                                                                                                                                         |
  +--------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnflcm show --help
  usage: openstack vnflcm show [-h] [-f {json,shell,table,value,yaml}]
                              [-c COLUMN] [--noindent] [--prefix PREFIX]
                              [--max-width <integer>] [--fit-width]
                              [--print-empty]
                              <vnf-instance>

  Display VNF instance details

  positional arguments:
    <vnf-instance>        VNF instance ID to display

  optional arguments:
    -h, --help            show this help message and exit


5. Terminate VNF
^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnflcm terminate VNF_INSTANCE_ID


Result:

.. code-block:: console

  Terminate request for VNF Instance '725f625e-f6b7-4bcd-b1b7-7184039fde45' has been accepted.


Help:

.. code-block:: console

  $ openstack vnflcm terminate --help
  usage: openstack vnflcm terminate [-h] [--termination-type <termination-type>]
                                    [--graceful-termination-timeout <graceful-termination-timeout>]
                                    [--D]
                                    <vnf-instance>

  Terminate a VNF instance

  positional arguments:
    <vnf-instance>        VNF instance ID to terminate

  optional arguments:
    -h, --help            show this help message and exit
    --termination-type <termination-type>
                          Termination type can be 'GRACEFUL' or 'FORCEFUL'.
                          Default is 'GRACEFUL'
    --graceful-termination-timeout <graceful-termination-timeout>
                          This attribute is only applicable in case of graceful
                          termination. It defines the time to wait for the VNF
                          to be taken out of service before shutting down the
                          VNF and releasing the resources. The unit is seconds.
    --D                   Delete VNF Instance subsequently after it's
                          termination


6. Delete VNF Identifier
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnflcm delete VNF_INSTANCE_ID


Result:

.. code-block:: console

  Vnf instance '725f625e-f6b7-4bcd-b1b7-7184039fde45' deleted successfully


Help:

.. code-block:: console

  $ openstack vnflcm delete --help
  usage: openstack vnflcm delete [-h] <vnf-instance> [<vnf-instance> ...]

  Delete VNF Instance(s)

  positional arguments:
    <vnf-instance>  VNF instance ID(s) to delete

  optional arguments:
    -h, --help      show this help message and exit


7. Heal VNF
^^^^^^^^^^^

.. code-block:: console

  $ openstack vnflcm heal VNF_INSTANCE_ID

.. note::
    <vnf-instance> should either be given before --vnfc-instance
    parameter or it should be separated with '--' separator in
    order to come after --vnfc-instance parameter.


Result:

.. code-block:: console

  Heal request for VNF Instance 725f625e-f6b7-4bcd-b1b7-7184039fde45 has been accepted.

Help:

.. code-block:: console

  $ openstack vnflcm heal --help
  usage: openstack vnflcm heal [-h] [--cause CAUSE]
                               [--vnfc-instance <vnfc-instance-id> [<vnfc-instance-id> ...]]
                               -- <vnf-instance>

  Heal VNF Instance

  positional arguments:
    <vnf-instance>        VNF instance ID to heal

  optional arguments:
    -h, --help            show this help message and exit
    --cause CAUSE         Specify the reason why a healing procedure is
                          required.
    --vnfc-instance <vnfc-instance-id> [<vnfc-instance-id> ...]
                          List of VNFC instances requiring a healing action.


8. Update VNF
^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnflcm update VNF_INSTANCE_ID --I sample_param_file.json


Result:

.. code-block:: console

  Update vnf:725f625e-f6b7-4bcd-b1b7-7184039fde45


Help:

.. code-block:: console

  $ openstack vnflcm update --help
  usage: openstack vnflcm update [-h] [--I <param-file>] <vnf-instance>

  Update VNF Instance

  positional arguments:
    <vnf-instance>
                          VNF instance ID to update.

  optional arguments:
    -h, --help            show this help message and exit
    --I <param-file>
                          Specify update request parameters in a json file.

  This command is provided by the python-tackerclient plugin.


9. Scale VNF
^^^^^^^^^^^^

The `worker_instance` is the ID for the target scaling group.
See `About aspect id`_ for details.

.. code-block:: console

  $ openstack vnflcm scale --type SCALE_OUT --aspect-id worker_instance \
       VNF_INSTANCE_ID


Result:

.. code-block:: console

  Scale request for VNF Instance 725f625e-f6b7-4bcd-b1b7-7184039fde45 has been accepted.


Help:

.. code-block:: console

  $ openstack vnflcm scale --help
  usage: openstack vnflcm scale [-h] [--number-of-steps <number-of-steps>]
                                [--additional-param-file <additional-param-file>]
                                --type <type> --aspect-id <aspect-id>
                                <vnf-instance>

  Scale a VNF Instance

  positional arguments:
    <vnf-instance>        VNF instance ID to scale

  optional arguments:
    -h, --help            show this help message and exit
    --number-of-steps <number-of-steps>
                          Number of scaling steps to be executed as part of this Scale VNF operation.
    --additional-param-file <additional-param-file>
                          Additional parameters passed by the NFVO as input to the scaling process.

  require arguments:
    --type <type>         SCALE_OUT or SCALE_IN for type of scale operation.
    --aspect-id <aspect-id>
                          Identifier of the scaling aspect.


10. Change External VNF Connectivity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnflcm change_ext_conn VNF_INSTANCE_ID \
       ./sample_param_file.json


Result:

.. code-block:: console

  Change External VNF Connectivity for VNF Instance 725f625e-f6b7-4bcd-b1b7-7184039fde45 has been accepted.


Help:

.. code-block:: console

  $ openstack vnflcm change_ext_conn --help
  usage: openstack vnflcm change_ext_conn [-h] <vnf-instance> <param-file>

  Change External VNF Connectivity

  positional arguments:
    <vnf-instance>  VNF instance ID to Change External VNF Connectivity
    <param-file>    Specify change_ext_conn request parameters in a json file.

  optional arguments:
    -h, --help      show this help message and exit


11. Rollback VNF Lifecycle Management Operation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `VNF_LCM_OP_OCC_ID` is the ID for the target lifecycle temporary failed.

.. code-block:: console

  $ openstack vnflcm op rollback VNF_LCM_OP_OCC_ID


Result:

.. code-block:: console

  Rollback request for LCM operation 304538dd-d754-4661-9f17-5496dab9693d has been accepted


Help:

.. code-block:: console

  $ openstack vnflcm op rollback -h
  usage: openstack vnflcm op rollback [-h] <vnf-lcm-op-occ-id>

  positional arguments:
    <vnf-lcm-op-occ-id>  VNF lifecycle management operation occurrence ID.

  optional arguments:
    -h, --help           show this help message and exit


12. Retry
^^^^^^^^^

The `VNF_LCM_OP_OCC_ID` is the ID for the target lifecycle temporary failed.

.. code-block:: console

  $ openstack vnflcm op retry VNF_LCM_OP_OCC_ID


Result:

.. code-block:: console

  Retry request for LCM operation 304538dd-d754-4661-9f17-5496dab9693d has been accepted.


Help:

.. code-block:: console

  $ openstack vnflcm op retry --help
  usage: openstack vnflcm op retry [-h] <vnf-lcm-op-occ-id>

  Retry

  positional arguments:
    <vnf-lcm-op-occ-id>  VNF lifecycle management operation occurrence ID.

  optional arguments:
    -h, --help           show this help message and exit


13. Fail
^^^^^^^^

The `VNF_LCM_OP_OCC_ID` is the ID for the target lifecycle temporary failed.

.. code-block:: console

  $ openstack vnflcm op fail VNF_LCM_OP_OCC_ID


Result:

.. code-block:: console

  +-------------------------+-------------------------------------------------------------------------------+
  | Field                   | Value                                                                         |
  +-------------------------+-------------------------------------------------------------------------------+
  | Error                   | {                                                                             |
  |                         |     "title": "",                                                              |
  |                         |     "status": 500,                                                            |
  |                         |     "detail": "ProblemDetails(created_at=<?>,deleted=False,deleted_at=<?>,    |
  |                         | detail='Vnf instantiation wait failed for vnf 725f625e-f6b7-4bcd-b1b7-7184039 |
  |                         | fde45, error: VNF Create Stack DELETE started',status=500,title='',updated_at |
  |                         | =<?>)"                                                                        |
  |                         | }                                                                             |
  | ID                      | 303a5d45-9186-4c6f-bed2-54d5bcd49cee                                          |
  | Is Automatic Invocation | False                                                                         |
  | Is Cancel Pending       | False                                                                         |
  | Links                   | {                                                                             |
  |                         |     "self": {                                                                 |
  |                         |         "href": "http://localhost:9890//vnflcm/v1/vnf_lcm_op_occs/303a5d45-91 |
  |                         | 86-4c6f-bed2-54d5bcd49cee"                                                    |
  |                         |     },                                                                        |
  |                         |     "vnfInstance": {                                                          |
  |                         |         "href": "http://localhost:9890//vnflcm/v1/vnf_instances/725f625e-f6b7 |
  |                         | -4bcd-b1b7-7184039fde45                                                       |
  |                         | "                                                                             |
  |                         |     },                                                                        |
  |                         |     "retry": {                                                                |
  |                         |         "href": "http://localhost:9890//vnflcm/v1/vnf_lcm_op_occs/303a5d45-91 |
  |                         | 86-4c6f-bed2-54d5bcd49cee/retry"                                              |
  |                         |     },                                                                        |
  |                         |     "rollback": {                                                             |
  |                         |         "href": "http://localhost:9890//vnflcm/v1/vnf_lcm_op_occs/303a5d45-91 |
  |                         | 86-4c6f-bed2-54d5bcd49cee/rollback"                                           |
  |                         |     },                                                                        |
  |                         |     "grant": {                                                                |
  |                         |         "href": "http://localhost:9890//vnflcm/v1/vnf_lcm_op_occs/303a5d45-91 |
  |                         | 86-4c6f-bed2-54d5bcd49cee/grant"                                              |
  |                         |     },                                                                        |
  |                         |     "fail": {                                                                 |
  |                         |         "href": "http://localhost:9890//vnflcm/v1/vnf_lcm_op_occs/303a5d45-91 |
  |                         |86-4c6f-bed2-54d5bcd49cee/fail"                                                |
  |                         |     }                                                                         |
  |                         | }                                                                             |
  | Operation               | INSTANTIATE                                                                   |
  | Operation State         | FAILED                                                                        |
  | Start Time              | 2021-04-11 23:55:00+00:00                                                     |
  | State Entered Time      | 2021-04-12 00:00:00.700855+00:00                                              |
  | VNF Instance ID         | 725f625e-f6b7-4bcd-b1b7-7184039fde45                                          |
  | grantId                 | None                                                                          |
  | operationParams         | "{\"flavourId\": \"simple\", \"instantiationLevelId\":                        |
  |                         | \"instantiation_level_1\", \"extVirtualLinks\": [{\"id\":                     |
  |                         | \"0b12944d-c04c-4ff9-aa4f-b2092e9048d2\", \"resourceId\":                     |
  |                         | \"5e0e451c-4c9a-4406-9ded-4007fd488e6c\", \"extCps\": [{\"cpdId\":            |
  |                         | \"VDU1_CP1\", \"cpConfig\": [{\"linkPortId\":                                 |
  |                         | \"0f862451-3943-4b04-8621-49b491da97f2\"}]},                                  |
  |                         | {\"cpdId\": \"VDU2_CP1\", \"cpConfig\": [{\"linkPortId\":                     |
  |                         | \"6c77dd1d-e37d-4371-9ad3-1b4db2ac8543\"}]}], \"extLinkPorts\": [{\"id\":     |
  |                         | \"0f862451-3943-4b04-8621-49b491da97f2\",                                     |
  |                         | \"resourceHandle\": {\"vimConnectionId\":                                     |
  |                         | \"2217719b-9dd6-4e38-be00-ec92511199cc\", \"resourceId\":                     |
  |                         | \"27b6edbe-9e2d-4d74-a538-f7c1e9b6af5f\"}},                                   |
  |                         | {\"id\": \"6c77dd1d-e37d-4371-9ad3-1b4db2ac8543\",                            |
  |                         | \"resourceHandle\": {\"vimConnectionId\":                                     |
  |                         | \"2217719b-9dd6-4e38-be00-ec92511199cc\", \"resourceId\":                     |
  |                         | \"05d11117-ce0b-4886-a867-4ebf035e976c\"}}]},                                 |
  |                         | {\"id\": \"a3e37a7d-fe6c-42f3-ba37-09ff8b73ddf3\", \"resourceId\":            |
  |                         | \"a3fdc55b-b6e4-403e-a1a1-d25c345594f8\",                                     |
  |                         | \"extCps\": [{\"cpdId\": \"VDU1_CP2\", \"cpConfig\": [{\"cpProtocolData\":    |
  |                         | [{\"layerProtocol\": \"IP_OVER_ETHERNET\",                                    |
  |                         | \"ipOverEthernet\": {\"ipAddresses\": [{\"type\":                             |
  |                         | \"IPV4\", \"fixedAddresses\": [\"22.22.1.10\"], \"subnetId\":                 |
  |                         | \"4d95f793-145e-404b-a7a7-4fea4f5ef131\"}]}}]}]},                             |
  |                         | {\"cpdId\": \"VDU2_CP2\", \"cpConfig\": [{\"cpProtocolData\":                 |
  |                         | [{\"layerProtocol\": \"IP_OVER_ETHERNET\", \"ipOverEthernet\":                |
  |                         | {\"ipAddresses\": [{\"type\": \"IPV4\",                                       |
  |                         | \"fixedAddresses\": [\"22.22.1.20\"],                                         |
  |                         | \"subnetId\": \"4d95f793-145e-404b-a7a7-4fea4f5ef1                            |
  |                         | 31\"}]}}]}]}]}], \"extManagedVirtualLinks\": [{\"id\":                        |
  |                         | \"620e4251-90c5-49e2-9eaa-4dc25af4ac56\",                                     |
  |                         | \"vnfVirtualLinkDescId\": \"internalVL1\", \"resourceId\":                    |
  |                         | \"a0a5272c-e46a-4f0f-b00e-986af9e659b4\"},                                    |
  |                         | {\"id\": \"9ee38c81-414b-46ab-ada7-659e85fa05ee\",                            |
  |                         | \"vnfVirtualLinkDescId\": \"internalVL2\", \"resourceId\":                    |
  |                         | \"598a30f9-7183-4cb1-a100-ca40fe031517\"}], \"vimConnectionInfo\": [{\"id\":  |
  |                         | \"2217719b-9dd6-4e38-be00-ec92511199cc\",                                     |
  |                         | \"vimType\": \"ETSINFV.OPENSTACK_KEYSTONE.v_2\", \"vimConnectionId\":         |
  |                         | \"2217719b-9dd6-4e38-be00-ec92511199cc\", \"interfaceInfo\": {\"endpoint\":   |
  |                         | \"http://127.0.0.1/identity\"}, \"accessInfo\": {\"username\": \"nfv_user\",  |
  |                         | \"region\":, \"RegionOne\", \"password\": \"devstack\",                       |
  |                         | \"tenant\": \"6bdc3a89b3ee4cef9ff1676a22ae7f3b\"}}],                          |
  |                         | \"additionalParams\": {\"lcm-operation-user-data\":                           |
  |                         | \"./UserData/lcm_user_data.py\", \"lcm-operation-user-data-class\":           |
  |                         | \"SampleUserData\"}}"                                                         |
  | resourceChanges         | {}                                                                            |
  +-------------------------+-------------------------------------------------------------------------------+

Help:

.. code-block:: console

  $ openstack vnflcm op fail --help
  usage: openstack vnflcm op fail [-h] [-f {json,shell,table,value,yaml}]
                                  [-c COLUMN] [--noindent] [--prefix PREFIX]
                                  [--max-width <integer>] [--fit-width]
                                  [--print-empty]
                                  <vnf-lcm-op-occ-id>

  Fail

  positional arguments:
    <vnf-lcm-op-occ-id>  VNF lifecycle management operation occurrence ID.

  optional arguments:
    -h, --help           show this help message and exit


14. List LCM Operation Occurrences
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnflcm op list

Result:

.. code-block:: console

  +--------------------------------------+-------------------+--------------------------------------+-------------+
  | id                                   | operationState    |            vnfInstanceId             |  operation  |
  +--------------------------------------+-------------------+--------------------------------------+-------------+
  | 304538dd-d754-4661-9f17-5496dab9693d | STARTING          | 725f625e-f6b7-4bcd-b1b7-7184039fde45 | INSTANTIATE |
  +--------------------------------------+-------------------+--------------------------------------+-------------+

Help:

.. code-block:: console

  $ openstack vnflcm op list --help
  usage: openstack vnflcm op list [-h] [-f {csv,json,table,value,yaml}]
                                  [-c COLUMN]
                                  [--quote {all,minimal,none,nonnumeric}]
                                  [--noindent] [--max-width <integer>]
                                  [--fit-width] [--print-empty]
                                  [--sort-column SORT_COLUMN]
                                  [--filter <filter>]
                                  [--all_fields | --fields <fields> | --exclude-fields <exclude-fields>]
                                  [--exclude_default]

  List LCM Operation Occurrences

  optional arguments:
    -h, --help            show this help message and exit
    --filter <filter>     Attribute-based-filtering parameters
    --all_fields          Include all complex attributes in the response
    --fields <fields>     Complex attributes to be included into the response
    --exclude-fields <exclude-fields>
                          Complex attributes to be excluded from the response
    --exclude_default     Indicates to exclude all complex attributes from the
                          response. This argument can be used alone or with
                          --fields and --filter. For all other combinations
                          tacker server will throw bad request error


15. Show LCM Operation Occurrence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnflcm op show VNF_LCM_OP_OCC_ID


Result:

.. code-block:: console

  +------------------------+--------------------------------------------------------------------------------+
  | Field                  | Value                                                                          |
  +------------------------+--------------------------------------------------------------------------------+
  | cancelMode             |                                                                                |
  | changedExtConnectivity | ""                                                                             |
  | changedInfo            | {                                                                              |
  |                        |     "vnfdVersion": "1.0",                                                      |
  |                        |     "vnfProvider": "Company",                                                  |
  |                        |     "vnfSoftwareVersion": "1.0",                                               |
  |                        |     "vnfdId": b1bb0ce7-ebca-4fa7-95ed-4840d70a1177,                            |
  |                        |     "vnfcInfoModificationsDeleteIds": null,                                    |
  |                        |     "vnfInstanceName": "helloworld3_modify",                                   |
  |                        |     "vnfProductName": "Sample VNF",                                            |
  |                        |     "vnfInstanceDescription": "Sample VNF Modify"                              |
  |                        | }                                                                              |
  | error                  | ""                                                                             |
  | grantId                |                                                                                |
  | id                     | 304538dd-d754-4661-9f17-5496dab9693d                                           |
  | isAutomaticInvocation  | False                                                                          |
  | isCancelPending        | False                                                                          |
  | _links                 | self=href=/vnflcm/v1/vnf_lcm_op_occs/304538dd-d754-4661-9f17-5496dab9693d,     |
  |                        | vnfInstance=href=/vnflcm/v1/vnf_instances/725f625e-f6b7-4bcd-b1b7-7184039fde45 |
  | operation              | MODIFY_INFO                                                                    |
  | operationParams        | "{\"vnfInstanceName\": \"helloworld3_modify\"}"                                |
  | operationState         | COMPLETED                                                                      |
  | resourceChanges        | ""                                                                             |
  | startTime              | 2021-04-15 23:59:00+00:00                                                      |
  | stateEnteredTime       | 2021-04-16 00:00:00+00:00                                                      |
  | vnfInstanceId          | 725f625e-f6b7-4bcd-b1b7-7184039fde45                                           |
  +------------------------+--------------------------------------------------------------------------------+

Help:

.. code-block:: console

  $ openstack vnflcm op show --help
  usage: openstack vnflcm op show [-h] [-f {json,shell,table,value,yaml}]
                                  [-c COLUMN] [--noindent] [--prefix PREFIX]
                                  [--max-width <integer>] [--fit-width]
                                  [--print-empty]
                                  <vnf-lcm-op-occ-id>


  Display Operation Occurrence details

  positional arguments:
    <vnf-lcm-op-occ-id>  VNF lifecycle management operation occurrence ID.

  optional arguments:
    -h, --help           show this help message and exit


16. Show VNF LCM API versions
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
    The command with **\-\-major-version** narrows down the
    obtained major versions to show.


.. code-block:: console

  $ openstack vnflcm versions --major-version 1
  +-------------+-----------------------------------------------+
  | Field       | Value                                         |
  +-------------+-----------------------------------------------+
  | uriPrefix   | /vnflcm/v1                                    |
  | apiVersions | [{'version': '1.3.0', 'isDeprecated': False}] |
  +-------------+-----------------------------------------------+

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

  optional arguments:
    -h, --help          show this help message and exit
    --major-version <major-version>
                        Show only specify major version.

.. _About aspect id : https://docs.openstack.org/tacker/latest/user/etsi_vnf_scaling.html#how-to-identify-aspect-id
