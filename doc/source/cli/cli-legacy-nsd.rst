=====================================
Network Service Descriptor Management
=====================================

To enable dynamic composition of network services, NFV introduces Network
Service Descriptors (NSDs) that specify the network service to be created.

This document describes how to manage NSD with CLI in Tacker.

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

A default VIM should be registered according to :doc:`./cli-legacy-vim`.

The following VNFDs are created according to :doc:`./cli-legacy-vnfd`.

* `sample-tosca-vnfd1.yaml <https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/nsd/sample-tosca-vnfd1.yaml>`_
* `sample-tosca-vnfd2.yaml <https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/nsd/sample-tosca-vnfd2.yaml>`_

CLI reference for NSD Management
--------------------------------

1. Create Network Service Descriptor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create ``sample-tosca-nsd.yaml`` file:

* https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/nsd/sample-tosca-nsd.yaml


Create a NSD:

.. code-block:: console

  $ openstack ns descriptor create --nsd-file \
      sample-tosca-nsd.yaml <NAME: sample-tosca-nsd>


Result:

.. code-block:: console

  +-----------------+----------------------------------------------------------------------------------+
  | Field           | Value                                                                            |
  +-----------------+----------------------------------------------------------------------------------+
  | attributes      | {                                                                                |
  |                 |     "nsd": {                                                                     |
  |                 |         "description": "Import VNFDs(already on-boarded) with input parameters", |
  |                 |         "imports": [                                                             |
  |                 |             "sample-tosca-vnfd1",                                                |
  |                 |             "sample-tosca-vnfd2"                                                 |
  |                 |         ],                                                                       |
  |                 |         "topology_template": {                                                   |
  |                 |             "inputs": {                                                          |
  |                 |                 "vl1_name": {                                                    |
  |                 |                     "default": "net_mgmt",                                       |
  |                 |                     "description": "name of VL1 virtuallink",                    |
  |                 |                     "type": "string"                                             |
  |                 |                 },                                                               |
  |                 |                 "vl2_name": {                                                    |
  |                 |                     "default": "net0",                                           |
  |                 |                     "description": "name of VL2 virtuallink",                    |
  |                 |                     "type": "string"                                             |
  |                 |                 }                                                                |
  |                 |             },                                                                   |
  |                 |             "node_templates": {                                                  |
  |                 |                 "VL1": {                                                         |
  |                 |                     "properties": {                                              |
  |                 |                         "network_name": {                                        |
  |                 |                             "get_input": "vl1_name"                              |
  |                 |                         },                                                       |
  |                 |                         "vendor": "tacker"                                       |
  |                 |                     },                                                           |
  |                 |                     "type": "tosca.nodes.nfv.VL"                                 |
  |                 |                 },                                                               |
  |                 |                 "VL2": {                                                         |
  |                 |                     "properties": {                                              |
  |                 |                         "network_name": {                                        |
  |                 |                             "get_input": "vl2_name"                              |
  |                 |                         },                                                       |
  |                 |                         "vendor": "tacker"                                       |
  |                 |                     },                                                           |
  |                 |                     "type": "tosca.nodes.nfv.VL"                                 |
  |                 |                 },                                                               |
  |                 |                 "VNF1": {                                                        |
  |                 |                     "requirements": [                                            |
  |                 |                         {                                                        |
  |                 |                             "virtualLink1": "VL1"                                |
  |                 |                         },                                                       |
  |                 |                         {                                                        |
  |                 |                             "virtualLink2": "VL2"                                |
  |                 |                         }                                                        |
  |                 |                     ],                                                           |
  |                 |                     "type": "tosca.nodes.nfv.VNF1"                               |
  |                 |                 },                                                               |
  |                 |                 "VNF2": {                                                        |
  |                 |                     "type": "tosca.nodes.nfv.VNF2"                               |
  |                 |                 }                                                                |
  |                 |             }                                                                    |
  |                 |         },                                                                       |
  |                 |         "tosca_definitions_version": "tosca_simple_profile_for_nfv_1_0_0"        |
  |                 |     }                                                                            |
  |                 | }                                                                                |
  | created_at      | 2020-08-12 07:16:42.297675                                                       |
  | description     | Import VNFDs(already on-boarded) with input parameters                           |
  | id              | 99a25f74-1bb9-4985-a548-f171060d00fd                                             |
  | name            | sample-tosca-nsd                                                                 |
  | project_id      | e77397d2a02c4af1b7d79cef2a406396                                                 |
  | template_source | onboarded                                                                        |
  | updated_at      | None                                                                             |
  +-----------------+----------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack ns descriptor create --help
  usage: openstack ns descriptor create [-h] [-f {json,shell,table,value,yaml}]
                                        [-c COLUMN] [--noindent]
                                        [--prefix PREFIX]
                                        [--max-width <integer>] [--fit-width]
                                        [--print-empty] [--tenant-id TENANT_ID]
                                        --nsd-file NSD_FILE
                                        [--description DESCRIPTION]
                                        NAME

  Create a new NSD.

  positional arguments:
    NAME                  Name for NSD

  optional arguments:
    -h, --help            show this help message and exit
    --tenant-id TENANT_ID
                          The owner tenant ID or project ID
    --nsd-file NSD_FILE   YAML file with NSD parameters
    --description DESCRIPTION
                          Set a description for the NSD


2. List Network Service Descriptor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack ns descriptor list


Result:

.. code-block:: console

  +--------------------------------------+------------------+-----------------+------------------------------+
  | ID                                   | Name             | Template_Source | Description                  |
  +--------------------------------------+------------------+-----------------+------------------------------+
  | 99a25f74-1bb9-4985-a548-f171060d00fd | sample-tosca-nsd | onboarded       | Import VNFDs(already on-b... |
  +--------------------------------------+------------------+-----------------+------------------------------+


Help:

.. code-block:: console

  $ openstack ns descriptor list --help
  usage: openstack ns descriptor list [-h] [-f {csv,json,table,value,yaml}]
                                      [-c COLUMN]
                                      [--quote {all,minimal,none,nonnumeric}]
                                      [--noindent] [--max-width <integer>]
                                      [--fit-width] [--print-empty]
                                      [--sort-column SORT_COLUMN]
                                      [--template-source TEMPLATE_SOURCE]

  List (NSD)s that belong to a given tenant.

  optional arguments:
    -h, --help            show this help message and exit
    --template-source TEMPLATE_SOURCE
                          List NSD with specified template source. Available
                          options are 'onboared' (default), 'inline' or 'all'


3. Show Network Service Descriptor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack ns descriptor show <NSD: sample-tosca-nsd>


Result:

.. code-block:: console

  +-----------------+----------------------------------------------------------------------------------+
  | Field           | Value                                                                            |
  +-----------------+----------------------------------------------------------------------------------+
  | attributes      | {                                                                                |
  |                 |     "nsd": {                                                                     |
  |                 |         "description": "Import VNFDs(already on-boarded) with input parameters", |
  |                 |         "imports": [                                                             |
  |                 |             "sample-tosca-vnfd1",                                                |
  |                 |             "sample-tosca-vnfd2"                                                 |
  |                 |         ],                                                                       |
  |                 |         "topology_template": {                                                   |
  |                 |             "inputs": {                                                          |
  |                 |                 "vl1_name": {                                                    |
  |                 |                     "default": "net_mgmt",                                       |
  |                 |                     "description": "name of VL1 virtuallink",                    |
  |                 |                     "type": "string"                                             |
  |                 |                 },                                                               |
  |                 |                 "vl2_name": {                                                    |
  |                 |                     "default": "net0",                                           |
  |                 |                     "description": "name of VL2 virtuallink",                    |
  |                 |                     "type": "string"                                             |
  |                 |                 }                                                                |
  |                 |             },                                                                   |
  |                 |             "node_templates": {                                                  |
  |                 |                 "VL1": {                                                         |
  |                 |                     "properties": {                                              |
  |                 |                         "network_name": {                                        |
  |                 |                             "get_input": "vl1_name"                              |
  |                 |                         },                                                       |
  |                 |                         "vendor": "tacker"                                       |
  |                 |                     },                                                           |
  |                 |                     "type": "tosca.nodes.nfv.VL"                                 |
  |                 |                 },                                                               |
  |                 |                 "VL2": {                                                         |
  |                 |                     "properties": {                                              |
  |                 |                         "network_name": {                                        |
  |                 |                             "get_input": "vl2_name"                              |
  |                 |                         },                                                       |
  |                 |                         "vendor": "tacker"                                       |
  |                 |                     },                                                           |
  |                 |                     "type": "tosca.nodes.nfv.VL"                                 |
  |                 |                 },                                                               |
  |                 |                 "VNF1": {                                                        |
  |                 |                     "requirements": [                                            |
  |                 |                         {                                                        |
  |                 |                             "virtualLink1": "VL1"                                |
  |                 |                         },                                                       |
  |                 |                         {                                                        |
  |                 |                             "virtualLink2": "VL2"                                |
  |                 |                         }                                                        |
  |                 |                     ],                                                           |
  |                 |                     "type": "tosca.nodes.nfv.VNF1"                               |
  |                 |                 },                                                               |
  |                 |                 "VNF2": {                                                        |
  |                 |                     "type": "tosca.nodes.nfv.VNF2"                               |
  |                 |                 }                                                                |
  |                 |             }                                                                    |
  |                 |         },                                                                       |
  |                 |         "tosca_definitions_version": "tosca_simple_profile_for_nfv_1_0_0"        |
  |                 |     }                                                                            |
  |                 | }                                                                                |
  | created_at      | 2020-08-12 07:16:42                                                              |
  | description     | Import VNFDs(already on-boarded) with input parameters                           |
  | id              | 99a25f74-1bb9-4985-a548-f171060d00fd                                             |
  | name            | sample-tosca-nsd                                                                 |
  | project_id      | e77397d2a02c4af1b7d79cef2a406396                                                 |
  | template_source | onboarded                                                                        |
  | updated_at      | None                                                                             |
  +-----------------+----------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack ns descriptor show --help
  usage: openstack ns descriptor show [-h] [-f {json,shell,table,value,yaml}]
                                      [-c COLUMN] [--noindent] [--prefix PREFIX]
                                      [--max-width <integer>] [--fit-width]
                                      [--print-empty]
                                      <NSD>

  Display NSD details

  positional arguments:
    <NSD>                 NSD to display (name or ID)

  optional arguments:
    -h, --help            show this help message and exit


4. Show template Network Service Descriptor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  openstack ns descriptor template show <name or ID of NSD: sample-tosca-nsd>

Result:

.. code-block:: console

  +------------+----------------------------------------------------------------------------------+
  | Field      | Value                                                                            |
  +------------+----------------------------------------------------------------------------------+
  | attributes | {                                                                                |
  |            |     "nsd": {                                                                     |
  |            |         "description": "Import VNFDs(already on-boarded) with input parameters", |
  |            |         "imports": [                                                             |
  |            |             "sample-tosca-vnfd1",                                                |
  |            |             "sample-tosca-vnfd2"                                                 |
  |            |         ],                                                                       |
  |            |         "topology_template": {                                                   |
  |            |             "inputs": {                                                          |
  |            |                 "vl1_name": {                                                    |
  |            |                     "default": "net_mgmt",                                       |
  |            |                     "description": "name of VL1 virtuallink",                    |
  |            |                     "type": "string"                                             |
  |            |                 },                                                               |
  |            |                 "vl2_name": {                                                    |
  |            |                     "default": "net0",                                           |
  |            |                     "description": "name of VL2 virtuallink",                    |
  |            |                     "type": "string"                                             |
  |            |                 }                                                                |
  |            |             },                                                                   |
  |            |             "node_templates": {                                                  |
  |            |                 "VL1": {                                                         |
  |            |                     "properties": {                                              |
  |            |                         "network_name": {                                        |
  |            |                             "get_input": "vl1_name"                              |
  |            |                         },                                                       |
  |            |                         "vendor": "tacker"                                       |
  |            |                     },                                                           |
  |            |                     "type": "tosca.nodes.nfv.VL"                                 |
  |            |                 },                                                               |
  |            |                 "VL2": {                                                         |
  |            |                     "properties": {                                              |
  |            |                         "network_name": {                                        |
  |            |                             "get_input": "vl2_name"                              |
  |            |                         },                                                       |
  |            |                         "vendor": "tacker"                                       |
  |            |                     },                                                           |
  |            |                     "type": "tosca.nodes.nfv.VL"                                 |
  |            |                 },                                                               |
  |            |                 "VNF1": {                                                        |
  |            |                     "requirements": [                                            |
  |            |                         {                                                        |
  |            |                             "virtualLink1": "VL1"                                |
  |            |                         },                                                       |
  |            |                         {                                                        |
  |            |                             "virtualLink2": "VL2"                                |
  |            |                         }                                                        |
  |            |                     ],                                                           |
  |            |                     "type": "tosca.nodes.nfv.VNF1"                               |
  |            |                 },                                                               |
  |            |                 "VNF2": {                                                        |
  |            |                     "type": "tosca.nodes.nfv.VNF2"                               |
  |            |                 }                                                                |
  |            |             }                                                                    |
  |            |         },                                                                       |
  |            |         "tosca_definitions_version": "tosca_simple_profile_for_nfv_1_0_0"        |
  |            |     }                                                                            |
  |            | }                                                                                |
  +------------+----------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack ns descriptor template show --help
  usage: openstack ns descriptor template show [-h]
                                              [-f {json,shell,table,value,yaml}]
                                              [-c COLUMN] [--noindent]
                                              [--prefix PREFIX]
                                              [--max-width <integer>]
                                              [--fit-width] [--print-empty]
                                              <NSD>

  Display NSD Template details

  positional arguments:
    <NSD>                 NSD to display (name or ID)

  optional arguments:
    -h, --help            show this help message and exit


5. Delete Network Service Descriptor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack ns descriptor delete <NSD: sample-tosca-nsd>


Result:

  All specified nsd(s) deleted successfully


Help:

  $ openstack ns descriptor delete --help
  usage: openstack ns descriptor delete [-h] <NSD> [<NSD> ...]

  Delete NSD(s).

  positional arguments:
    <NSD>       NSD(s) to delete (name or ID)

  optional arguments:
    -h, --help  show this help message and exit
