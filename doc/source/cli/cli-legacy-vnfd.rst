================================
VNF Descriptor (VNFD) Management
================================

The behavioural and deployment information of a VNF in Tacker is defined in a
template known as VNF Descriptor (VNFD). The template is based on TOSCA
standards and is written in YAML.

This document describes how to manage VNFD with CLI in Tacker.

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

CLI reference for VNFD Management
---------------------------------

1. Create VNF Descriptor
^^^^^^^^^^^^^^^^^^^^^^^^

Create ``tosca-vnfd-hello-world.yaml`` file:

* https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnfd/tosca-vnfd-hello-world.yaml


Create a VNFD:

.. code-block:: console

  $ openstack vnf descriptor create --vnfd-file \
      tosca-vnfd-hello-world.yaml <NAME: tosca-vnfd-hello-world>


Result:

.. code-block:: console

  +-----------------+---------------------------------------------------------------------------+
  | Field           | Value                                                                     |
  +-----------------+---------------------------------------------------------------------------+
  | attributes      | {                                                                         |
  |                 |     "vnfd": {                                                             |
  |                 |         "description": "Demo example",                                    |
  |                 |         "metadata": {                                                     |
  |                 |             "template_name": "sample-tosca-vnfd"                          |
  |                 |         },                                                                |
  |                 |         "topology_template": {                                            |
  |                 |             "node_templates": {                                           |
  |                 |                 "CP1": {                                                  |
  |                 |                     "properties": {                                       |
  |                 |                         "anti_spoofing_protection": false,                |
  |                 |                         "management": true,                               |
  |                 |                         "order": 0                                        |
  |                 |                     },                                                    |
  |                 |                     "requirements": [                                     |
  |                 |                         {                                                 |
  |                 |                             "virtualLink": {                              |
  |                 |                                 "node": "VL1"                             |
  |                 |                             }                                             |
  |                 |                         },                                                |
  |                 |                         {                                                 |
  |                 |                             "virtualBinding": {                           |
  |                 |                                 "node": "VDU1"                            |
  |                 |                             }                                             |
  |                 |                         }                                                 |
  |                 |                     ],                                                    |
  |                 |                     "type": "tosca.nodes.nfv.CP.Tacker"                   |
  |                 |                 },                                                        |
  |                 |                 "CP2": {                                                  |
  |                 |                     "properties": {                                       |
  |                 |                         "anti_spoofing_protection": false,                |
  |                 |                         "order": 1                                        |
  |                 |                     },                                                    |
  |                 |                     "requirements": [                                     |
  |                 |                         {                                                 |
  |                 |                             "virtualLink": {                              |
  |                 |                                 "node": "VL2"                             |
  |                 |                             }                                             |
  |                 |                         },                                                |
  |                 |                         {                                                 |
  |                 |                             "virtualBinding": {                           |
  |                 |                                 "node": "VDU1"                            |
  |                 |                             }                                             |
  |                 |                         }                                                 |
  |                 |                     ],                                                    |
  |                 |                     "type": "tosca.nodes.nfv.CP.Tacker"                   |
  |                 |                 },                                                        |
  |                 |                 "CP3": {                                                  |
  |                 |                     "properties": {                                       |
  |                 |                         "anti_spoofing_protection": false,                |
  |                 |                         "order": 2                                        |
  |                 |                     },                                                    |
  |                 |                     "requirements": [                                     |
  |                 |                         {                                                 |
  |                 |                             "virtualLink": {                              |
  |                 |                                 "node": "VL3"                             |
  |                 |                             }                                             |
  |                 |                         },                                                |
  |                 |                         {                                                 |
  |                 |                             "virtualBinding": {                           |
  |                 |                                 "node": "VDU1"                            |
  |                 |                             }                                             |
  |                 |                         }                                                 |
  |                 |                     ],                                                    |
  |                 |                     "type": "tosca.nodes.nfv.CP.Tacker"                   |
  |                 |                 },                                                        |
  |                 |                 "VDU1": {                                                 |
  |                 |                     "capabilities": {                                     |
  |                 |                         "nfv_compute": {                                  |
  |                 |                             "properties": {                               |
  |                 |                                 "disk_size": "1 GB",                      |
  |                 |                                 "mem_size": "512 MB",                     |
  |                 |                                 "num_cpus": 1                             |
  |                 |                             }                                             |
  |                 |                         }                                                 |
  |                 |                     },                                                    |
  |                 |                     "properties": {                                       |
  |                 |                         "availability_zone": "nova",                      |
  |                 |                         "config": "param0: key1\nparam1: key2\n",         |
  |                 |                         "image": "cirros-0.4.0-x86_64-disk",              |
  |                 |                         "mgmt_driver": "noop"                             |
  |                 |                     },                                                    |
  |                 |                     "type": "tosca.nodes.nfv.VDU.Tacker"                  |
  |                 |                 },                                                        |
  |                 |                 "VL1": {                                                  |
  |                 |                     "properties": {                                       |
  |                 |                         "network_name": "net_mgmt",                       |
  |                 |                         "vendor": "Tacker"                                |
  |                 |                     },                                                    |
  |                 |                     "type": "tosca.nodes.nfv.VL"                          |
  |                 |                 },                                                        |
  |                 |                 "VL2": {                                                  |
  |                 |                     "properties": {                                       |
  |                 |                         "network_name": "net0",                           |
  |                 |                         "vendor": "Tacker"                                |
  |                 |                     },                                                    |
  |                 |                     "type": "tosca.nodes.nfv.VL"                          |
  |                 |                 },                                                        |
  |                 |                 "VL3": {                                                  |
  |                 |                     "properties": {                                       |
  |                 |                         "network_name": "net1",                           |
  |                 |                         "vendor": "Tacker"                                |
  |                 |                     },                                                    |
  |                 |                     "type": "tosca.nodes.nfv.VL"                          |
  |                 |                 }                                                         |
  |                 |             }                                                             |
  |                 |         },                                                                |
  |                 |         "tosca_definitions_version": "tosca_simple_profile_for_nfv_1_0_0" |
  |                 |     }                                                                     |
  |                 | }                                                                         |
  | created_at      | 2020-08-12 03:28:04.171956                                                |
  | description     | Demo example                                                              |
  | id              | 57f46bdb-c5b5-448e-bf98-df3d7d94038e                                      |
  | name            | tosca-vnfd-hello-world                                                    |
  | project_id      | e77397d2a02c4af1b7d79cef2a406396                                          |
  | service_types   | ['vnfd']                                                                  |
  | template_source | onboarded                                                                 |
  | updated_at      | None                                                                      |
  +-----------------+---------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf descriptor create --help
  usage: openstack vnf descriptor create [-h] [-f {json,shell,table,value,yaml}]
                                        [-c COLUMN] [--noindent]
                                        [--prefix PREFIX]
                                        [--max-width <integer>] [--fit-width]
                                        [--print-empty] [--tenant-id TENANT_ID]
                                        --vnfd-file VNFD_FILE
                                        [--description DESCRIPTION]
                                        NAME

  Create a new VNFD

  positional arguments:
    NAME                  Name for VNFD

  optional arguments:
    -h, --help            show this help message and exit
    --tenant-id TENANT_ID
                          The owner tenant ID or project ID
    --vnfd-file VNFD_FILE
                          YAML file with VNFD parameters
    --description DESCRIPTION
                          Set a description for the VNFD


2. List VNF Descriptors
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf descriptor list


Result:

.. code-block:: console

  +--------------------------------------+------------------------+-----------------+--------------+
  | ID                                   | Name                   | Template_Source | Description  |
  +--------------------------------------+------------------------+-----------------+--------------+
  | 57f46bdb-c5b5-448e-bf98-df3d7d94038e | tosca-vnfd-hello-world | onboarded       | Demo example |
  +--------------------------------------+------------------------+-----------------+--------------+


Help:

.. code-block:: console

  $ openstack vnf descriptor list --help
  usage: openstack vnf descriptor list [-h] [-f {csv,json,table,value,yaml}]
                                      [-c COLUMN]
                                      [--quote {all,minimal,none,nonnumeric}]
                                      [--noindent] [--max-width <integer>]
                                      [--fit-width] [--print-empty]
                                      [--sort-column SORT_COLUMN]
                                      [--template-source TEMPLATE_SOURCE]

  List (VNFD)s that belong to a given tenant.

  optional arguments:
    -h, --help            show this help message and exit
    --template-source TEMPLATE_SOURCE
                          List VNFD with specified template source. Available
                          options are 'onboarded' (default), 'inline' or 'all'


3. Show VNF Descriptor
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf descriptor show <VNFD: tosca-vnfd-hello-world>


Result:

.. code-block:: console

  +-----------------+---------------------------------------------------------------------------+
  | Field           | Value                                                                     |
  +-----------------+---------------------------------------------------------------------------+
  | attributes      | {                                                                         |
  |                 |     "vnfd": {                                                             |
  |                 |         "description": "Demo example",                                    |
  |                 |         "metadata": {                                                     |
  |                 |             "template_name": "sample-tosca-vnfd"                          |
  |                 |         },                                                                |
  |                 |         "topology_template": {                                            |
  |                 |             "node_templates": {                                           |
  |                 |                 "CP1": {                                                  |
  |                 |                     "properties": {                                       |
  |                 |                         "anti_spoofing_protection": false,                |
  |                 |                         "management": true,                               |
  |                 |                         "order": 0                                        |
  |                 |                     },                                                    |
  |                 |                     "requirements": [                                     |
  |                 |                         {                                                 |
  |                 |                             "virtualLink": {                              |
  |                 |                                 "node": "VL1"                             |
  |                 |                             }                                             |
  |                 |                         },                                                |
  |                 |                         {                                                 |
  |                 |                             "virtualBinding": {                           |
  |                 |                                 "node": "VDU1"                            |
  |                 |                             }                                             |
  |                 |                         }                                                 |
  |                 |                     ],                                                    |
  |                 |                     "type": "tosca.nodes.nfv.CP.Tacker"                   |
  |                 |                 },                                                        |
  |                 |                 "CP2": {                                                  |
  |                 |                     "properties": {                                       |
  |                 |                         "anti_spoofing_protection": false,                |
  |                 |                         "order": 1                                        |
  |                 |                     },                                                    |
  |                 |                     "requirements": [                                     |
  |                 |                         {                                                 |
  |                 |                             "virtualLink": {                              |
  |                 |                                 "node": "VL2"                             |
  |                 |                             }                                             |
  |                 |                         },                                                |
  |                 |                         {                                                 |
  |                 |                             "virtualBinding": {                           |
  |                 |                                 "node": "VDU1"                            |
  |                 |                             }                                             |
  |                 |                         }                                                 |
  |                 |                     ],                                                    |
  |                 |                     "type": "tosca.nodes.nfv.CP.Tacker"                   |
  |                 |                 },                                                        |
  |                 |                 "CP3": {                                                  |
  |                 |                     "properties": {                                       |
  |                 |                         "anti_spoofing_protection": false,                |
  |                 |                         "order": 2                                        |
  |                 |                     },                                                    |
  |                 |                     "requirements": [                                     |
  |                 |                         {                                                 |
  |                 |                             "virtualLink": {                              |
  |                 |                                 "node": "VL3"                             |
  |                 |                             }                                             |
  |                 |                         },                                                |
  |                 |                         {                                                 |
  |                 |                             "virtualBinding": {                           |
  |                 |                                 "node": "VDU1"                            |
  |                 |                             }                                             |
  |                 |                         }                                                 |
  |                 |                     ],                                                    |
  |                 |                     "type": "tosca.nodes.nfv.CP.Tacker"                   |
  |                 |                 },                                                        |
  |                 |                 "VDU1": {                                                 |
  |                 |                     "capabilities": {                                     |
  |                 |                         "nfv_compute": {                                  |
  |                 |                             "properties": {                               |
  |                 |                                 "disk_size": "1 GB",                      |
  |                 |                                 "mem_size": "512 MB",                     |
  |                 |                                 "num_cpus": 1                             |
  |                 |                             }                                             |
  |                 |                         }                                                 |
  |                 |                     },                                                    |
  |                 |                     "properties": {                                       |
  |                 |                         "availability_zone": "nova",                      |
  |                 |                         "config": "param0: key1\nparam1: key2\n",         |
  |                 |                         "image": "cirros-0.4.0-x86_64-disk",              |
  |                 |                         "mgmt_driver": "noop"                             |
  |                 |                     },                                                    |
  |                 |                     "type": "tosca.nodes.nfv.VDU.Tacker"                  |
  |                 |                 },                                                        |
  |                 |                 "VL1": {                                                  |
  |                 |                     "properties": {                                       |
  |                 |                         "network_name": "net_mgmt",                       |
  |                 |                         "vendor": "Tacker"                                |
  |                 |                     },                                                    |
  |                 |                     "type": "tosca.nodes.nfv.VL"                          |
  |                 |                 },                                                        |
  |                 |                 "VL2": {                                                  |
  |                 |                     "properties": {                                       |
  |                 |                         "network_name": "net0",                           |
  |                 |                         "vendor": "Tacker"                                |
  |                 |                     },                                                    |
  |                 |                     "type": "tosca.nodes.nfv.VL"                          |
  |                 |                 },                                                        |
  |                 |                 "VL3": {                                                  |
  |                 |                     "properties": {                                       |
  |                 |                         "network_name": "net1",                           |
  |                 |                         "vendor": "Tacker"                                |
  |                 |                     },                                                    |
  |                 |                     "type": "tosca.nodes.nfv.VL"                          |
  |                 |                 }                                                         |
  |                 |             }                                                             |
  |                 |         },                                                                |
  |                 |         "tosca_definitions_version": "tosca_simple_profile_for_nfv_1_0_0" |
  |                 |     }                                                                     |
  |                 | }                                                                         |
  | created_at      | 2020-08-12 03:28:04                                                       |
  | description     | Demo example                                                              |
  | id              | 57f46bdb-c5b5-448e-bf98-df3d7d94038e                                      |
  | name            | tosca-vnfd-hello-world                                                    |
  | project_id      | e77397d2a02c4af1b7d79cef2a406396                                          |
  | service_types   | ['vnfd']                                                                  |
  | template_source | onboarded                                                                 |
  | updated_at      | None                                                                      |
  +-----------------+---------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf descriptor show --help
  usage: openstack vnf descriptor show [-h] [-f {json,shell,table,value,yaml}]
                                      [-c COLUMN] [--noindent]
                                      [--prefix PREFIX] [--max-width <integer>]
                                      [--fit-width] [--print-empty]
                                      <VNFD>

  Display VNFD details

  positional arguments:
    <VNFD>                VNFD to display (name or ID)

  optional arguments:
    -h, --help            show this help message and exit


4. Show VNF Descriptor template
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf descriptor template show <VNFD: tosca-vnfd-hello-world>


Result:

.. code-block:: console

  +------------+---------------------------------------------------------------------------+
  | Field      | Value                                                                     |
  +------------+---------------------------------------------------------------------------+
  | attributes | {                                                                         |
  |            |     "vnfd": {                                                             |
  |            |         "description": "Demo example",                                    |
  |            |         "metadata": {                                                     |
  |            |             "template_name": "sample-tosca-vnfd"                          |
  |            |         },                                                                |
  |            |         "topology_template": {                                            |
  |            |             "node_templates": {                                           |
  |            |                 "CP1": {                                                  |
  |            |                     "properties": {                                       |
  |            |                         "anti_spoofing_protection": false,                |
  |            |                         "management": true,                               |
  |            |                         "order": 0                                        |
  |            |                     },                                                    |
  |            |                     "requirements": [                                     |
  |            |                         {                                                 |
  |            |                             "virtualLink": {                              |
  |            |                                 "node": "VL1"                             |
  |            |                             }                                             |
  |            |                         },                                                |
  |            |                         {                                                 |
  |            |                             "virtualBinding": {                           |
  |            |                                 "node": "VDU1"                            |
  |            |                             }                                             |
  |            |                         }                                                 |
  |            |                     ],                                                    |
  |            |                     "type": "tosca.nodes.nfv.CP.Tacker"                   |
  |            |                 },                                                        |
  |            |                 "CP2": {                                                  |
  |            |                     "properties": {                                       |
  |            |                         "anti_spoofing_protection": false,                |
  |            |                         "order": 1                                        |
  |            |                     },                                                    |
  |            |                     "requirements": [                                     |
  |            |                         {                                                 |
  |            |                             "virtualLink": {                              |
  |            |                                 "node": "VL2"                             |
  |            |                             }                                             |
  |            |                         },                                                |
  |            |                         {                                                 |
  |            |                             "virtualBinding": {                           |
  |            |                                 "node": "VDU1"                            |
  |            |                             }                                             |
  |            |                         }                                                 |
  |            |                     ],                                                    |
  |            |                     "type": "tosca.nodes.nfv.CP.Tacker"                   |
  |            |                 },                                                        |
  |            |                 "CP3": {                                                  |
  |            |                     "properties": {                                       |
  |            |                         "anti_spoofing_protection": false,                |
  |            |                         "order": 2                                        |
  |            |                     },                                                    |
  |            |                     "requirements": [                                     |
  |            |                         {                                                 |
  |            |                             "virtualLink": {                              |
  |            |                                 "node": "VL3"                             |
  |            |                             }                                             |
  |            |                         },                                                |
  |            |                         {                                                 |
  |            |                             "virtualBinding": {                           |
  |            |                                 "node": "VDU1"                            |
  |            |                             }                                             |
  |            |                         }                                                 |
  |            |                     ],                                                    |
  |            |                     "type": "tosca.nodes.nfv.CP.Tacker"                   |
  |            |                 },                                                        |
  |            |                 "VDU1": {                                                 |
  |            |                     "capabilities": {                                     |
  |            |                         "nfv_compute": {                                  |
  |            |                             "properties": {                               |
  |            |                                 "disk_size": "1 GB",                      |
  |            |                                 "mem_size": "512 MB",                     |
  |            |                                 "num_cpus": 1                             |
  |            |                             }                                             |
  |            |                         }                                                 |
  |            |                     },                                                    |
  |            |                     "properties": {                                       |
  |            |                         "availability_zone": "nova",                      |
  |            |                         "config": "param0: key1\nparam1: key2\n",         |
  |            |                         "image": "cirros-0.4.0-x86_64-disk",              |
  |            |                         "mgmt_driver": "noop"                             |
  |            |                     },                                                    |
  |            |                     "type": "tosca.nodes.nfv.VDU.Tacker"                  |
  |            |                 },                                                        |
  |            |                 "VL1": {                                                  |
  |            |                     "properties": {                                       |
  |            |                         "network_name": "net_mgmt",                       |
  |            |                         "vendor": "Tacker"                                |
  |            |                     },                                                    |
  |            |                     "type": "tosca.nodes.nfv.VL"                          |
  |            |                 },                                                        |
  |            |                 "VL2": {                                                  |
  |            |                     "properties": {                                       |
  |            |                         "network_name": "net0",                           |
  |            |                         "vendor": "Tacker"                                |
  |            |                     },                                                    |
  |            |                     "type": "tosca.nodes.nfv.VL"                          |
  |            |                 },                                                        |
  |            |                 "VL3": {                                                  |
  |            |                     "properties": {                                       |
  |            |                         "network_name": "net1",                           |
  |            |                         "vendor": "Tacker"                                |
  |            |                     },                                                    |
  |            |                     "type": "tosca.nodes.nfv.VL"                          |
  |            |                 }                                                         |
  |            |             }                                                             |
  |            |         },                                                                |
  |            |         "tosca_definitions_version": "tosca_simple_profile_for_nfv_1_0_0" |
  |            |     }                                                                     |
  |            | }                                                                         |
  +------------+---------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf descriptor template show --help
  usage: openstack vnf descriptor template show [-h]
                                                [-f {json,shell,table,value,yaml}]
                                                [-c COLUMN] [--noindent]
                                                [--prefix PREFIX]
                                                [--max-width <integer>]
                                                [--fit-width] [--print-empty]
                                                <VNFD>

  Display VNFD Template details

  positional arguments:
    <VNFD>                VNFD to display (name or ID)

  optional arguments:
    -h, --help            show this help message and exit


5. Delete VNF Descriptors
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf descriptor delete <VNFD: tosca-vnfd-hello-world>


Result:

.. code-block:: console

  All specified vnfd(s) deleted successfully


Help:

.. code-block:: console

  $ openstack vnf descriptor delete --help
  usage: openstack vnf descriptor delete [-h] <VNFD> [<VNFD> ...]

  Delete VNFD(s).

  positional arguments:
    <VNFD>      VNFD(s) to delete (name or ID)

  optional arguments:
    -h, --help  show this help message and exit
