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

.. TODO(yoshito-ito): add heal CLI reference.

.. TODO(yoshito-ito): add scale CLI reference.

1. Create VNF Identifier
^^^^^^^^^^^^^^^^^^^^^^^^

The `<VNFD_ID>` should be replaced with the VNFD ID in VNF Package. In the
following sample, `b1bb0ce7-ebca-4fa7-95ed-4840d70a1177` is used.

.. code-block:: console

  $ openstack vnflcm create <VNFD_ID>


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

  $ openstack vnflcm instantiate <ID: 725f625e-f6b7-4bcd-b1b7-7184039fde45> \
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

4. List VNF
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


5. Show VNF
^^^^^^^^^^^

.. code-block:: console

  $ openstack vnflcm show <ID: 725f625e-f6b7-4bcd-b1b7-7184039fde45>


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
  |                          | terminate=href=/vnflcm/v1/vnf_instances/725f625e-f6b7-4bcd-b1b7-7184039fde45/terminate                                                                      |
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


6. Terminate VNF
^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnflcm terminate <ID: 725f625e-f6b7-4bcd-b1b7-7184039fde45>


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


7. Delete VNF Identifier
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnflcm delete <ID: 725f625e-f6b7-4bcd-b1b7-7184039fde45>


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
