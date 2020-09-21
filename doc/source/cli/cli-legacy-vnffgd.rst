===================================================
VNF Forwarding Graph Descriptor (VNFFGD) Management
===================================================

VNF Forwarding Graph (VNFFG) feature in Tacker is used to orchestrate and
manage traffic through VNFs. In short, abstract VNFFG TOSCA definitions are
rendered into Service Function Chains (SFCs) and Classifiers. The SFC makes up
an ordered list of VNFs for traffic to traverse, while the classifier decides
which traffic should go through them. Similar to how VNFs are described by
VNFDs, VNFFGs are described by VNF Forwarding Graph Descriptors (VNFFGD).

This document describes how to manage VNFFGD with CLI in Tacker.

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

CLI reference for VNFFGD Management
-----------------------------------

1. Create VNF Forwarding Graph Descriptor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create ``tosca-vnffgd-sample.yaml`` file:

* https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnffgd/tosca-vnffgd-sample.yaml

Create a VNFFGD:

.. code-block:: console

  $ openstack vnf graph descriptor create --vnffgd-file \
      tosca-vnffgd-sample.yaml <NAME: tosca-vnffgd-sample>


Result:

.. code-block:: console

  +-----------------+--------------------------------------------------------------------------------------------------------+
  | Field           | Value                                                                                                  |
  +-----------------+--------------------------------------------------------------------------------------------------------+
  | description     | Sample VNFFG template                                                                                  |
  | id              | 81d9cc7a-674d-463d-ad3d-95640e388b20                                                                   |
  | name            | tosca-vnffgd-sample                                                                                    |
  | project_id      | e77397d2a02c4af1b7d79cef2a406396                                                                       |
  | template        | {                                                                                                      |
  |                 |     "vnffgd": {                                                                                        |
  |                 |         "tosca_definitions_version": "tosca_simple_profile_for_nfv_1_0_0",                             |
  |                 |         "description": "Sample VNFFG template",                                                        |
  |                 |         "topology_template": {                                                                         |
  |                 |             "node_templates": {                                                                        |
  |                 |                 "Forwarding_path1": {                                                                  |
  |                 |                     "type": "tosca.nodes.nfv.FP.TackerV2",                                             |
  |                 |                     "description": "creates path (CP12->CP22)",                                        |
  |                 |                     "properties": {                                                                    |
  |                 |                         "id": 51,                                                                      |
  |                 |                         "policy": {                                                                    |
  |                 |                             "type": "ACL",                                                             |
  |                 |                             "criteria": [                                                              |
  |                 |                                 {                                                                      |
  |                 |                                     "name": "block_tcp",                                               |
  |                 |                                     "classifier": {                                                    |
  |                 |                                         "network_src_port_id": "14ad4f29-629f-4b97-8bc8-86e96cb49974", |
  |                 |                                         "destination_port_range": "80-1024",                           |
  |                 |                                         "ip_proto": 6,                                                 |
  |                 |                                         "ip_dst_prefix": "10.10.0.5/24"                                |
  |                 |                                     }                                                                  |
  |                 |                                 }                                                                      |
  |                 |                             ]                                                                          |
  |                 |                         },                                                                             |
  |                 |                         "path": [                                                                      |
  |                 |                             {                                                                          |
  |                 |                                 "forwarder": "VNFD1",                                                  |
  |                 |                                 "capability": "CP12",                                                  |
  |                 |                                 "sfc_encap": true                                                      |
  |                 |                             },                                                                         |
  |                 |                             {                                                                          |
  |                 |                                 "forwarder": "VNFD2",                                                  |
  |                 |                                 "capability": "CP22",                                                  |
  |                 |                                 "sfc_encap": true                                                      |
  |                 |                             }                                                                          |
  |                 |                         ]                                                                              |
  |                 |                     }                                                                                  |
  |                 |                 }                                                                                      |
  |                 |             },                                                                                         |
  |                 |             "groups": {                                                                                |
  |                 |                 "VNFFG1": {                                                                            |
  |                 |                     "type": "tosca.groups.nfv.VNFFG",                                                  |
  |                 |                     "description": "HTTP to Corporate Net",                                            |
  |                 |                     "properties": {                                                                    |
  |                 |                         "vendor": "tacker",                                                            |
  |                 |                         "version": 1.0,                                                                |
  |                 |                         "number_of_endpoints": 2,                                                      |
  |                 |                         "dependent_virtual_link": [                                                    |
  |                 |                             "VL12",                                                                    |
  |                 |                             "VL22"                                                                     |
  |                 |                         ],                                                                             |
  |                 |                         "connection_point": [                                                          |
  |                 |                             "CP12",                                                                    |
  |                 |                             "CP22"                                                                     |
  |                 |                         ],                                                                             |
  |                 |                         "constituent_vnfs": [                                                          |
  |                 |                             "VNFD1",                                                                   |
  |                 |                             "VNFD2"                                                                    |
  |                 |                         ]                                                                              |
  |                 |                     },                                                                                 |
  |                 |                     "members": [                                                                       |
  |                 |                         "Forwarding_path1"                                                             |
  |                 |                     ]                                                                                  |
  |                 |                 }                                                                                      |
  |                 |             }                                                                                          |
  |                 |         },                                                                                             |
  |                 |         "imports": [                                                                                   |
  |                 |             "/opt/stack/tacker/tacker/tosca/lib/tacker_defs.yaml",                                     |
  |                 |             "/opt/stack/tacker/tacker/tosca/lib/tacker_nfv_defs.yaml"                                  |
  |                 |         ]                                                                                              |
  |                 |     }                                                                                                  |
  |                 | }                                                                                                      |
  | template_source | onboarded                                                                                              |
  +-----------------+--------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf graph descriptor create --help
  usage: openstack vnf graph descriptor create [-h]
                                              [-f {json,shell,table,value,yaml}]
                                              [-c COLUMN] [--noindent]
                                              [--prefix PREFIX]
                                              [--max-width <integer>]
                                              [--fit-width] [--print-empty]
                                              [--tenant-id TENANT_ID]
                                              --vnffgd-file VNFFGD_FILE
                                              [--description DESCRIPTION]
                                              NAME

  Create a new VNFFGD

  positional arguments:
    NAME                  Name for VNFFGD

  optional arguments:
    -h, --help            show this help message and exit
    --tenant-id TENANT_ID
                          The owner tenant ID or project ID
    --vnffgd-file VNFFGD_FILE
                          YAML file with VNFFGD parameters
    --description DESCRIPTION
                          Set a description for the VNFFGD


2. List VNF Forwarding Graph Descriptors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf graph descriptor list


Result:

.. code-block:: console

  +--------------------------------------+---------------------+-----------------+-----------------------+
  | ID                                   | Name                | Template_Source | Description           |
  +--------------------------------------+---------------------+-----------------+-----------------------+
  | 81d9cc7a-674d-463d-ad3d-95640e388b20 | tosca-vnffgd-sample | onboarded       | Sample VNFFG template |
  +--------------------------------------+---------------------+-----------------+-----------------------+


Help:

.. code-block:: console

  $ openstack vnf graph descriptor list --help
  usage: openstack vnf graph descriptor list [-h]
                                            [-f {csv,json,table,value,yaml}]
                                            [-c COLUMN]
                                            [--quote {all,minimal,none,nonnumeric}]
                                            [--noindent]
                                            [--max-width <integer>]
                                            [--fit-width] [--print-empty]
                                            [--sort-column SORT_COLUMN]
                                            [--template-source TEMPLATE_SOURCE]

  List (VNFFGD)s that belong to a given tenant.

  optional arguments:
    -h, --help            show this help message and exit
    --template-source TEMPLATE_SOURCE
                          List VNFFGD with specified template source. Available
                          options are 'onboarded' (default), 'inline' or 'all'


3. Show VNF Forwarding Graph Descriptor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf graph descriptor show <VNFFGD: tosca-vnffgd-sample>


Result:

.. code-block:: console

  +-----------------+--------------------------------------------------------------------------------------------------------+
  | Field           | Value                                                                                                  |
  +-----------------+--------------------------------------------------------------------------------------------------------+
  | description     | Sample VNFFG template                                                                                  |
  | id              | 81d9cc7a-674d-463d-ad3d-95640e388b20                                                                   |
  | name            | tosca-vnffgd-sample                                                                                    |
  | project_id      | e77397d2a02c4af1b7d79cef2a406396                                                                       |
  | template        | {                                                                                                      |
  |                 |     "vnffgd": {                                                                                        |
  |                 |         "tosca_definitions_version": "tosca_simple_profile_for_nfv_1_0_0",                             |
  |                 |         "description": "Sample VNFFG template",                                                        |
  |                 |         "topology_template": {                                                                         |
  |                 |             "node_templates": {                                                                        |
  |                 |                 "Forwarding_path1": {                                                                  |
  |                 |                     "type": "tosca.nodes.nfv.FP.TackerV2",                                             |
  |                 |                     "description": "creates path (CP12->CP22)",                                        |
  |                 |                     "properties": {                                                                    |
  |                 |                         "id": 51,                                                                      |
  |                 |                         "policy": {                                                                    |
  |                 |                             "type": "ACL",                                                             |
  |                 |                             "criteria": [                                                              |
  |                 |                                 {                                                                      |
  |                 |                                     "name": "block_tcp",                                               |
  |                 |                                     "classifier": {                                                    |
  |                 |                                         "network_src_port_id": "14ad4f29-629f-4b97-8bc8-86e96cb49974", |
  |                 |                                         "destination_port_range": "80-1024",                           |
  |                 |                                         "ip_proto": 6,                                                 |
  |                 |                                         "ip_dst_prefix": "10.10.0.5/24"                                |
  |                 |                                     }                                                                  |
  |                 |                                 }                                                                      |
  |                 |                             ]                                                                          |
  |                 |                         },                                                                             |
  |                 |                         "path": [                                                                      |
  |                 |                             {                                                                          |
  |                 |                                 "forwarder": "VNFD1",                                                  |
  |                 |                                 "capability": "CP12",                                                  |
  |                 |                                 "sfc_encap": true                                                      |
  |                 |                             },                                                                         |
  |                 |                             {                                                                          |
  |                 |                                 "forwarder": "VNFD2",                                                  |
  |                 |                                 "capability": "CP22",                                                  |
  |                 |                                 "sfc_encap": true                                                      |
  |                 |                             }                                                                          |
  |                 |                         ]                                                                              |
  |                 |                     }                                                                                  |
  |                 |                 }                                                                                      |
  |                 |             },                                                                                         |
  |                 |             "groups": {                                                                                |
  |                 |                 "VNFFG1": {                                                                            |
  |                 |                     "type": "tosca.groups.nfv.VNFFG",                                                  |
  |                 |                     "description": "HTTP to Corporate Net",                                            |
  |                 |                     "properties": {                                                                    |
  |                 |                         "vendor": "tacker",                                                            |
  |                 |                         "version": 1.0,                                                                |
  |                 |                         "number_of_endpoints": 2,                                                      |
  |                 |                         "dependent_virtual_link": [                                                    |
  |                 |                             "VL12",                                                                    |
  |                 |                             "VL22"                                                                     |
  |                 |                         ],                                                                             |
  |                 |                         "connection_point": [                                                          |
  |                 |                             "CP12",                                                                    |
  |                 |                             "CP22"                                                                     |
  |                 |                         ],                                                                             |
  |                 |                         "constituent_vnfs": [                                                          |
  |                 |                             "VNFD1",                                                                   |
  |                 |                             "VNFD2"                                                                    |
  |                 |                         ]                                                                              |
  |                 |                     },                                                                                 |
  |                 |                     "members": [                                                                       |
  |                 |                         "Forwarding_path1"                                                             |
  |                 |                     ]                                                                                  |
  |                 |                 }                                                                                      |
  |                 |             }                                                                                          |
  |                 |         },                                                                                             |
  |                 |         "imports": [                                                                                   |
  |                 |             "/opt/stack/tacker/tacker/tosca/lib/tacker_defs.yaml",                                     |
  |                 |             "/opt/stack/tacker/tacker/tosca/lib/tacker_nfv_defs.yaml"                                  |
  |                 |         ]                                                                                              |
  |                 |     }                                                                                                  |
  |                 | }                                                                                                      |
  | template_source | onboarded                                                                                              |
  +-----------------+--------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf graph descriptor show --help
  usage: openstack vnf graph descriptor show [-h]
                                            [-f {json,shell,table,value,yaml}]
                                            [-c COLUMN] [--noindent]
                                            [--prefix PREFIX]
                                            [--max-width <integer>]
                                            [--fit-width] [--print-empty]
                                            <VNFFGD>

  Display VNFFGD details

  positional arguments:
    <VNFFGD>              VNFFGD to display (name or ID)

  optional arguments:
    -h, --help            show this help message and exit


4. Show template VNF Forwarding Graph Descriptor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf graph descriptor template show <VNFFGD: tosca-vnffgd-sample>


Result:

.. code-block:: console

  +----------+--------------------------------------------------------------------------------------------------------+
  | Field    | Value                                                                                                  |
  +----------+--------------------------------------------------------------------------------------------------------+
  | template | {                                                                                                      |
  |          |     "vnffgd": {                                                                                        |
  |          |         "tosca_definitions_version": "tosca_simple_profile_for_nfv_1_0_0",                             |
  |          |         "description": "Sample VNFFG template",                                                        |
  |          |         "topology_template": {                                                                         |
  |          |             "node_templates": {                                                                        |
  |          |                 "Forwarding_path1": {                                                                  |
  |          |                     "type": "tosca.nodes.nfv.FP.TackerV2",                                             |
  |          |                     "description": "creates path (CP12->CP22)",                                        |
  |          |                     "properties": {                                                                    |
  |          |                         "id": 51,                                                                      |
  |          |                         "policy": {                                                                    |
  |          |                             "type": "ACL",                                                             |
  |          |                             "criteria": [                                                              |
  |          |                                 {                                                                      |
  |          |                                     "name": "block_tcp",                                               |
  |          |                                     "classifier": {                                                    |
  |          |                                         "network_src_port_id": "14ad4f29-629f-4b97-8bc8-86e96cb49974", |
  |          |                                         "destination_port_range": "80-1024",                           |
  |          |                                         "ip_proto": 6,                                                 |
  |          |                                         "ip_dst_prefix": "10.10.0.5/24"                                |
  |          |                                     }                                                                  |
  |          |                                 }                                                                      |
  |          |                             ]                                                                          |
  |          |                         },                                                                             |
  |          |                         "path": [                                                                      |
  |          |                             {                                                                          |
  |          |                                 "forwarder": "VNFD1",                                                  |
  |          |                                 "capability": "CP12",                                                  |
  |          |                                 "sfc_encap": true                                                      |
  |          |                             },                                                                         |
  |          |                             {                                                                          |
  |          |                                 "forwarder": "VNFD2",                                                  |
  |          |                                 "capability": "CP22",                                                  |
  |          |                                 "sfc_encap": true                                                      |
  |          |                             }                                                                          |
  |          |                         ]                                                                              |
  |          |                     }                                                                                  |
  |          |                 }                                                                                      |
  |          |             },                                                                                         |
  |          |             "groups": {                                                                                |
  |          |                 "VNFFG1": {                                                                            |
  |          |                     "type": "tosca.groups.nfv.VNFFG",                                                  |
  |          |                     "description": "HTTP to Corporate Net",                                            |
  |          |                     "properties": {                                                                    |
  |          |                         "vendor": "tacker",                                                            |
  |          |                         "version": 1.0,                                                                |
  |          |                         "number_of_endpoints": 2,                                                      |
  |          |                         "dependent_virtual_link": [                                                    |
  |          |                             "VL12",                                                                    |
  |          |                             "VL22"                                                                     |
  |          |                         ],                                                                             |
  |          |                         "connection_point": [                                                          |
  |          |                             "CP12",                                                                    |
  |          |                             "CP22"                                                                     |
  |          |                         ],                                                                             |
  |          |                         "constituent_vnfs": [                                                          |
  |          |                             "VNFD1",                                                                   |
  |          |                             "VNFD2"                                                                    |
  |          |                         ]                                                                              |
  |          |                     },                                                                                 |
  |          |                     "members": [                                                                       |
  |          |                         "Forwarding_path1"                                                             |
  |          |                     ]                                                                                  |
  |          |                 }                                                                                      |
  |          |             }                                                                                          |
  |          |         },                                                                                             |
  |          |         "imports": [                                                                                   |
  |          |             "/opt/stack/tacker/tacker/tosca/lib/tacker_defs.yaml",                                     |
  |          |             "/opt/stack/tacker/tacker/tosca/lib/tacker_nfv_defs.yaml"                                  |
  |          |         ]                                                                                              |
  |          |     }                                                                                                  |
  |          | }                                                                                                      |
  +----------+--------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf graph descriptor template show --help
  usage: openstack vnf graph descriptor template show [-h]
                                                      [-f {json,shell,table,value,yaml}]
                                                      [-c COLUMN] [--noindent]
                                                      [--prefix PREFIX]
                                                      [--max-width <integer>]
                                                      [--fit-width]
                                                      [--print-empty]
                                                      <VNFFGD>

  Display VNFFGD Template details

  positional arguments:
    <VNFFGD>              VNFFGD to display (name or ID)

  optional arguments:
    -h, --help            show this help message and exit


5. Delete VNF Forwarding Graph Descriptors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf graph descriptor delete <VNFFGD: tosca-vnffgd-sample>


.. code-block:: console

  All specified vnffgd(s) deleted successfully


Help:

.. code-block:: console

  $ openstack vnf graph descriptor delete --help
  usage: openstack vnf graph descriptor delete [-h] <VNFFGD> [<VNFFGD> ...]

  Delete VNFFGD(s).

  positional arguments:
    <VNFFGD>    VNFFGD(s) to delete (name or ID)

  optional arguments:
    -h, --help  show this help message and exit
