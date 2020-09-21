=======================================
VNF Forwarding Graph (VNFFG) Management
=======================================

.. TODO(yoshito-ito): Update "Update VNFFG" operation after fixing the bug:
  * https://bugs.launchpad.net/python-tackerclient/+bug/1892152

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

A default VIM should be registered according to :doc:`./cli-legacy-vim`.

The following VNFDs are created with the name ``VNFD1`` and ``VNFD2``
according to :doc:`./cli-legacy-vnfd`.

* `tosca-vnffg-vnfd1.yaml <https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnffgd/tosca-vnffg-vnfd1.yaml>`_
* `tosca-vnffg-vnfd2.yaml <https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnffgd/tosca-vnffg-vnfd2.yaml>`_

.. code-block:: console

  $ openstack vnf descriptor create --vnfd-file tosca-vnffg-vnfd1.yaml VNFD1
  $ openstack vnf descriptor create --vnfd-file tosca-vnffg-vnfd2.yaml VNFD2


The VNFs from the created VNFDs are deployed with the name ``VNF1`` and
``VNF2`` according to :doc:`./cli-legacy-vnf`.

.. code-block:: console

  $ openstack vnf create --vnfd-name VNFD1 VNF1
  $ openstack vnf create --vnfd-name VNFD2 VNF2


CLI reference for VNFFG Management
----------------------------------

1. Create VNF Forwarding Graph
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Check the source port ID ``CP12`` of VNF1:

.. code-block:: console

  $ openstack port list -c ID -c Name | grep CP12
  | d4940639-764a-4a62-9b21-6ba2e86498eb | VNF1_4ffb436f-7f2c-4df1-96c4-38e9208261fd-CP12-pj3nwzbv2wt2                 |


Create and update `tosca-vnffgd-sample.yaml <https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnffgd/tosca-vnffgd-sample.yaml>`_:

.. code-block:: console

  (Before)
  network_src_port_id: 14ad4f29-629f-4b97-8bc8-86e96cb49974

  (After)
  network_src_port_id: <ID: d4940639-764a-4a62-9b21-6ba2e86498eb>


.. note:: The appropriate port ID should be used according to your environment.

Create the VNFFGD:

.. code-block:: console

  $ openstack vnf graph descriptor create --vnffgd-file \
      tosca-vnffgd-sample.yaml <NAME: tosca-vnffgd-sample>


Create the VNFFG:

.. code-block:: console

  $ openstack vnf graph create --vnffgd-name <VNFFGD: tosca-vnffgd-sample> \
      <NAME: tosca-vnffg-sample>


Result:

.. code-block:: console

  +------------------+--------------------------------------------------------------------------------------------------------+
  | Field            | Value                                                                                                  |
  +------------------+--------------------------------------------------------------------------------------------------------+
  | attributes       | {                                                                                                      |
  |                  |     "vnffgd": {                                                                                        |
  |                  |         "tosca_definitions_version": "tosca_simple_profile_for_nfv_1_0_0",                             |
  |                  |         "description": "Sample VNFFG template",                                                        |
  |                  |         "topology_template": {                                                                         |
  |                  |             "node_templates": {                                                                        |
  |                  |                 "Forwarding_path1": {                                                                  |
  |                  |                     "type": "tosca.nodes.nfv.FP.TackerV2",                                             |
  |                  |                     "description": "creates path (CP12->CP22)",                                        |
  |                  |                     "properties": {                                                                    |
  |                  |                         "id": 51,                                                                      |
  |                  |                         "policy": {                                                                    |
  |                  |                             "type": "ACL",                                                             |
  |                  |                             "criteria": [                                                              |
  |                  |                                 {                                                                      |
  |                  |                                     "name": "block_tcp",                                               |
  |                  |                                     "classifier": {                                                    |
  |                  |                                         "network_src_port_id": "d4940639-764a-4a62-9b21-6ba2e86498eb", |
  |                  |                                         "destination_port_range": "80-1024",                           |
  |                  |                                         "ip_proto": 6,                                                 |
  |                  |                                         "ip_dst_prefix": "10.10.0.5/24"                                |
  |                  |                                     }                                                                  |
  |                  |                                 }                                                                      |
  |                  |                             ]                                                                          |
  |                  |                         },                                                                             |
  |                  |                         "path": [                                                                      |
  |                  |                             {                                                                          |
  |                  |                                 "forwarder": "VNFD1",                                                  |
  |                  |                                 "capability": "CP12",                                                  |
  |                  |                                 "sfc_encap": true                                                      |
  |                  |                             },                                                                         |
  |                  |                             {                                                                          |
  |                  |                                 "forwarder": "VNFD2",                                                  |
  |                  |                                 "capability": "CP22",                                                  |
  |                  |                                 "sfc_encap": true                                                      |
  |                  |                             }                                                                          |
  |                  |                         ]                                                                              |
  |                  |                     }                                                                                  |
  |                  |                 }                                                                                      |
  |                  |             },                                                                                         |
  |                  |             "groups": {                                                                                |
  |                  |                 "VNFFG1": {                                                                            |
  |                  |                     "type": "tosca.groups.nfv.VNFFG",                                                  |
  |                  |                     "description": "HTTP to Corporate Net",                                            |
  |                  |                     "properties": {                                                                    |
  |                  |                         "vendor": "tacker",                                                            |
  |                  |                         "version": 1.0,                                                                |
  |                  |                         "number_of_endpoints": 2,                                                      |
  |                  |                         "dependent_virtual_link": [                                                    |
  |                  |                             "VL12",                                                                    |
  |                  |                             "VL22"                                                                     |
  |                  |                         ],                                                                             |
  |                  |                         "connection_point": [                                                          |
  |                  |                             "CP12",                                                                    |
  |                  |                             "CP22"                                                                     |
  |                  |                         ],                                                                             |
  |                  |                         "constituent_vnfs": [                                                          |
  |                  |                             "VNFD1",                                                                   |
  |                  |                             "VNFD2"                                                                    |
  |                  |                         ]                                                                              |
  |                  |                     },                                                                                 |
  |                  |                     "members": [                                                                       |
  |                  |                         "Forwarding_path1"                                                             |
  |                  |                     ]                                                                                  |
  |                  |                 }                                                                                      |
  |                  |             }                                                                                          |
  |                  |         },                                                                                             |
  |                  |         "imports": [                                                                                   |
  |                  |             "/opt/stack/tacker/tacker/tosca/lib/tacker_defs.yaml",                                     |
  |                  |             "/opt/stack/tacker/tacker/tosca/lib/tacker_nfv_defs.yaml"                                  |
  |                  |         ]                                                                                              |
  |                  |     }                                                                                                  |
  |                  | }                                                                                                      |
  | description      | Sample VNFFG template                                                                                  |
  | forwarding_paths | fc518827-eb74-4cd5-972b-943f80720065                                                                   |
  | id               | b6669b6a-1a3c-40b6-a8c2-28ce3f0bd9bb                                                                   |
  | name             | tosca-vnffg-sample                                                                                     |
  | ns_id            | None                                                                                                   |
  | project_id       | e77397d2a02c4af1b7d79cef2a406396                                                                       |
  | status           | PENDING_CREATE                                                                                         |
  | vnf_mapping      | VNFD1=4ffb436f-7f2c-4df1-96c4-38e9208261fd, VNFD2=83fb8124-b475-400f-b0eb-f2b6741eeedc                 |
  | vnffgd_id        | f19a36f9-3768-4846-8972-84960d328156                                                                   |
  +------------------+--------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf graph create --help
  usage: openstack vnf graph create [-h] [-f {json,shell,table,value,yaml}]
                                    [-c COLUMN] [--noindent] [--prefix PREFIX]
                                    [--max-width <integer>] [--fit-width]
                                    [--print-empty] [--tenant-id TENANT_ID]
                                    (--vnffgd-id VNFFGD_ID | --vnffgd-name VNFFGD_NAME | --vnffgd-template VNFFGD_TEMPLATE)
                                    [--vnf-mapping VNF_MAPPING] [--symmetrical]
                                    [--param-file PARAM_FILE]
                                    [--description DESCRIPTION]
                                    NAME

  Create a new VNFFG.

  positional arguments:
    NAME                  Set a name for the VNFFG

  optional arguments:
    -h, --help            show this help message and exit
    --tenant-id TENANT_ID
                          The owner tenant ID
    --vnffgd-id VNFFGD_ID
                          VNFFGD ID to use as template to create VNFFG
    --vnffgd-name VNFFGD_NAME
                          VNFFGD Name to use as template to create VNFFG
    --vnffgd-template VNFFGD_TEMPLATE
                          VNFFGD file to create VNFFG
    --vnf-mapping VNF_MAPPING
                          List of logical VNFD name to VNF instance name
                          mapping. Example: VNF1:my_vnf1,VNF2:my_vnf2
    --symmetrical         Should a reverse path be created for the NFP (True or
                          False)
    --param-file PARAM_FILE
                          YAML file with specific VNFFG parameters
    --description DESCRIPTION
                          Set a description for the VNFFG


2. List VNF Forwarding Graphs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf graph list


Result:

.. code-block:: console

  +--------------------------------------+--------------------+-------+--------------------------------------+--------+
  | ID                                   | Name               | NS ID | VNFFGD ID                            | Status |
  +--------------------------------------+--------------------+-------+--------------------------------------+--------+
  | b6669b6a-1a3c-40b6-a8c2-28ce3f0bd9bb | tosca-vnffg-sample | None  | f19a36f9-3768-4846-8972-84960d328156 | ACTIVE |
  +--------------------------------------+--------------------+-------+--------------------------------------+--------+


Help:

.. code-block:: console

  $ openstack vnf graph list --help
  usage: openstack vnf graph list [-h] [-f {csv,json,table,value,yaml}]
                                  [-c COLUMN]
                                  [--quote {all,minimal,none,nonnumeric}]
                                  [--noindent] [--max-width <integer>]
                                  [--fit-width] [--print-empty]
                                  [--sort-column SORT_COLUMN] [--long]

  List VNFFG(s) that belong to a given tenant.

  optional arguments:
    -h, --help            show this help message and exit
    --long                List additional fields in output

  output formatters:
    output formatter options

    -f {csv,json,table,value,yaml}, --format {csv,json,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to
                          show multiple columns
    --sort-column SORT_COLUMN
                          specify the column(s) to sort the data (columns
                          specified first have a priority, non-existing columns
                          are ignored), can be repeated


3. Show VNF Forwarding Graph
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf graph show <VNFFG: tosca-vnffg-sample>


Result:

.. code-block:: console

  +------------------+--------------------------------------------------------------------------------------------------------+
  | Field            | Value                                                                                                  |
  +------------------+--------------------------------------------------------------------------------------------------------+
  | attributes       | {                                                                                                      |
  |                  |     "vnffgd": {                                                                                        |
  |                  |         "tosca_definitions_version": "tosca_simple_profile_for_nfv_1_0_0",                             |
  |                  |         "description": "Sample VNFFG template",                                                        |
  |                  |         "topology_template": {                                                                         |
  |                  |             "node_templates": {                                                                        |
  |                  |                 "Forwarding_path1": {                                                                  |
  |                  |                     "type": "tosca.nodes.nfv.FP.TackerV2",                                             |
  |                  |                     "description": "creates path (CP12->CP22)",                                        |
  |                  |                     "properties": {                                                                    |
  |                  |                         "id": 51,                                                                      |
  |                  |                         "policy": {                                                                    |
  |                  |                             "type": "ACL",                                                             |
  |                  |                             "criteria": [                                                              |
  |                  |                                 {                                                                      |
  |                  |                                     "name": "block_tcp",                                               |
  |                  |                                     "classifier": {                                                    |
  |                  |                                         "network_src_port_id": "d4940639-764a-4a62-9b21-6ba2e86498eb", |
  |                  |                                         "destination_port_range": "80-1024",                           |
  |                  |                                         "ip_proto": 6,                                                 |
  |                  |                                         "ip_dst_prefix": "10.10.0.5/24"                                |
  |                  |                                     }                                                                  |
  |                  |                                 }                                                                      |
  |                  |                             ]                                                                          |
  |                  |                         },                                                                             |
  |                  |                         "path": [                                                                      |
  |                  |                             {                                                                          |
  |                  |                                 "forwarder": "VNFD1",                                                  |
  |                  |                                 "capability": "CP12",                                                  |
  |                  |                                 "sfc_encap": true                                                      |
  |                  |                             },                                                                         |
  |                  |                             {                                                                          |
  |                  |                                 "forwarder": "VNFD2",                                                  |
  |                  |                                 "capability": "CP22",                                                  |
  |                  |                                 "sfc_encap": true                                                      |
  |                  |                             }                                                                          |
  |                  |                         ]                                                                              |
  |                  |                     }                                                                                  |
  |                  |                 }                                                                                      |
  |                  |             },                                                                                         |
  |                  |             "groups": {                                                                                |
  |                  |                 "VNFFG1": {                                                                            |
  |                  |                     "type": "tosca.groups.nfv.VNFFG",                                                  |
  |                  |                     "description": "HTTP to Corporate Net",                                            |
  |                  |                     "properties": {                                                                    |
  |                  |                         "vendor": "tacker",                                                            |
  |                  |                         "version": 1.0,                                                                |
  |                  |                         "number_of_endpoints": 2,                                                      |
  |                  |                         "dependent_virtual_link": [                                                    |
  |                  |                             "VL12",                                                                    |
  |                  |                             "VL22"                                                                     |
  |                  |                         ],                                                                             |
  |                  |                         "connection_point": [                                                          |
  |                  |                             "CP12",                                                                    |
  |                  |                             "CP22"                                                                     |
  |                  |                         ],                                                                             |
  |                  |                         "constituent_vnfs": [                                                          |
  |                  |                             "VNFD1",                                                                   |
  |                  |                             "VNFD2"                                                                    |
  |                  |                         ]                                                                              |
  |                  |                     },                                                                                 |
  |                  |                     "members": [                                                                       |
  |                  |                         "Forwarding_path1"                                                             |
  |                  |                     ]                                                                                  |
  |                  |                 }                                                                                      |
  |                  |             }                                                                                          |
  |                  |         },                                                                                             |
  |                  |         "imports": [                                                                                   |
  |                  |             "/opt/stack/tacker/tacker/tosca/lib/tacker_defs.yaml",                                     |
  |                  |             "/opt/stack/tacker/tacker/tosca/lib/tacker_nfv_defs.yaml"                                  |
  |                  |         ]                                                                                              |
  |                  |     }                                                                                                  |
  |                  | }                                                                                                      |
  | description      | Sample VNFFG template                                                                                  |
  | forwarding_paths | fc518827-eb74-4cd5-972b-943f80720065                                                                   |
  | id               | b6669b6a-1a3c-40b6-a8c2-28ce3f0bd9bb                                                                   |
  | name             | tosca-vnffg-sample                                                                                     |
  | ns_id            | None                                                                                                   |
  | project_id       | e77397d2a02c4af1b7d79cef2a406396                                                                       |
  | status           | ACTIVE                                                                                                 |
  | vnf_mapping      | VNFD1=4ffb436f-7f2c-4df1-96c4-38e9208261fd, VNFD2=83fb8124-b475-400f-b0eb-f2b6741eeedc                 |
  | vnffgd_id        | f19a36f9-3768-4846-8972-84960d328156                                                                   |
  +------------------+--------------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf graph show --help
  usage: openstack vnf graph show [-h] [-f {json,shell,table,value,yaml}]
                                  [-c COLUMN] [--noindent] [--prefix PREFIX]
                                  [--max-width <integer>] [--fit-width]
                                  [--print-empty]
                                  <VNFFG>

  Display VNFFG details

  positional arguments:
    <VNFFG>               VNFFG to display (name or ID)

  optional arguments:
    -h, --help            show this help message and exit


4. Update VNF Forwarding Graph
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a new VNF ``VNF3`` according to :doc:`./cli-legacy-vnfd` with the
following template:

.. code-block:: yaml

  tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0

  description: Demo example

  metadata:
    template_name: sample-tosca-vnfd3

  topology_template:
    node_templates:
      VDU1:
        type: tosca.nodes.nfv.VDU.Tacker
        capabilities:
          nfv_compute:
            properties:
              num_cpus: 1
              mem_size: 512 MB
              disk_size: 1 GB
        properties:
          image: cirros-0.4.0-x86_64-disk
          availability_zone: nova
          mgmt_driver: noop
          config: |
            param0: key1
            param1: key2
          user_data_format: RAW
          user_data: |
            #!/bin/sh
            echo 1 > /proc/sys/net/ipv4/ip_forward
            cat << EOF >> /etc/network/interfaces
            auto eth1
            iface eth1 inet dhcp
            auto eth2
            iface eth2 inet dhcp
            EOF
            ifup eth1
            ifup eth2

      CP31:
        type: tosca.nodes.nfv.CP.Tacker
        properties:
          management: true
          order: 0
          anti_spoofing_protection: false
        requirements:
          - virtualLink:
              node: VL31
          - virtualBinding:
              node: VDU1

      CP32:
        type: tosca.nodes.nfv.CP.Tacker
        properties:
          order: 1
          anti_spoofing_protection: false
        requirements:
          - virtualLink:
              node: VL32
          - virtualBinding:
              node: VDU1

      CP33:
        type: tosca.nodes.nfv.CP.Tacker
        properties:
          order: 2
          anti_spoofing_protection: false
        requirements:
          - virtualLink:
              node: VL33
          - virtualBinding:
              node: VDU1

      VL31:
        type: tosca.nodes.nfv.VL
        properties:
          network_name: net_mgmt
          vendor: Tacker

      VL32:
        type: tosca.nodes.nfv.VL
        properties:
          network_name: net0
          vendor: Tacker

      VL33:
        type: tosca.nodes.nfv.VL
        properties:
          network_name: net1
          vendor: Tacker


Create the VNFD and VNF:

.. code-block:: console

  openstack vnf descriptor create --vnfd-file tosca-vnffg-vnfd2.yaml VNFD3
  openstack vnf create --vnfd-name VNFD3 VNF3

Create the updated VNFD file ``tosca-vnffgd-sample-update.yaml``:

.. code-block:: console

  VNFD2 -> VNFD3
  CP22 -> CP32
  VL22 -> VL32


Update the VNFFG:

.. code-block:: console

  $ openstack vnf graph set --vnffgd-template tosca-vnffgd-sample-update.yaml \
      --description <DESCRIPTION: 'New description for Sample VNFFG template'> \
      <VNFFG: tosca-vnffg-sample>


Result:

.. code-block:: console

  'Namespace' object has no attribute 'param_file'


Help:

.. code-block:: console

  $ openstack vnf graph set --help
  usage: openstack vnf graph set [-h] [-f {json,shell,table,value,yaml}]
                                [-c COLUMN] [--noindent] [--prefix PREFIX]
                                [--max-width <integer>] [--fit-width]
                                [--print-empty]
                                [--vnffgd-template VNFFGD_TEMPLATE]
                                [--vnf-mapping VNF_MAPPING] [--symmetrical]
                                [--description DESCRIPTION]
                                <VNFFG>

  Update VNFFG.

  positional arguments:
    <VNFFG>               VNFFG to update (name or ID)

  optional arguments:
    -h, --help            show this help message and exit
    --vnffgd-template VNFFGD_TEMPLATE
                          VNFFGD file to update VNFFG
    --vnf-mapping VNF_MAPPING
                          List of logical VNFD name to VNF instance name
                          mapping. Example: VNF1:my_vnf1,VNF2:my_vnf2
    --symmetrical         Should a reverse path be created for the NFP
    --description DESCRIPTION
                          Set a description for the VNFFG


5. Delete VNF Forwarding Graph
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf graph delete <VNFFG: tosca-vnffg-sample>


.. code-block:: console

  All specified vnffg(s) deleted successfully


Help:

.. code-block:: console

  $ openstack vnf graph delete --help
  usage: openstack vnf graph delete [-h] <VNFFG> [<VNFFG> ...]

  Delete VNFFG(s).

  positional arguments:
    <VNFFG>     VNFFG(s) to delete (name or ID)

  optional arguments:
    -h, --help  show this help message and exit
