..
  Licensed under the Apache License, Version 2.0 (the "License"); you may
  not use this file except in compliance with the License. You may obtain
  a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
  License for the specific language governing permissions and limitations
  under the License.

====================================================================
Orchestrating VNFs and VNFFG using Network Services Descriptor (NSD)
====================================================================

To enable dynamic composition of network services, NFV introduces Network
Service Descriptors (NSDs) that specify the network service to be created.
In Network Function Virtualization (NFV), Network Service (NS) is a set of
network functions, that includes virtual network functions (VNFs), physical
network functions (PNFs), and  VNF forwarding graph (VNFFG) that defines
connection between NFs [#f1]_, [#f2]_.

.. code-block:: console

                       TOSCA                                        NFV
      +------------------------------------------+         +--------------------+
      |                                          |         |                    |
      |           Service Template  <------------------------+ Network Service  |
      |                                          |         |   Descriptor (NSD) |
      | +-------------------+                    |         |                    |
      | | Topology template |   +-------------+  |         |     +----------+   |
      | |  +---------+      |   | Node types  <------------------+   VNFD   |   |
      | |  |  Node   <----------+substitutable|  |         |     +----------+   |
      | |  | Template|      |   +-------------+  |         |                    |
      | |  +---------+      |                    |         |     +----------+   |
      | |  +---------+      |   +-------------+  |      +--------+   VLD    |   |
      | |  |  Node   <----------+ Node types  <---------+  |     +----------+   |
      | |  | Template|      |   +-------------+  |         |                    |
      | |  +---------+      |                    |         |     +----------+   |
      | |  +---------+      |   +-------------+  |      +--------+  VNFFGD  |   |
      | |  |  Node   <----------+ Group types <---------+  |     +----------+   |
      | |  | Template|      |   +-------------+  |         |                    |
      | |  +---------+      |                    |         |     +----------+   |
      | |  +---------+      |                    |      +--------+   PNFD   |   |
      | |  |  Node   |      |   +-------------+  |      |  |     +----------+   |
      | |  | Template<----------+ Node types  <---------+  |                    |
      | |  +---------+      |   +-------------+  |         +--------------------+
      | |                   |                    |
      | +-------------------+                    |
      |                                          |
      +------------------------------------------+

NSD in Ocata can be used for creating multiple (related) VNFs in one shot
using a single TOSCA template.

In Rocky version, Tacker add VNFFG support in NSD. That lets users can use
NSD to create VNFs and VNFFGs.

.. note::

  For current implementation, Tacker does not support creating VLs/neutron
  networks using NSD (to support inter-VNF private VL).


This usage guide describes lifecycle of Network service descriptors and
services.

Network Service creation procedure
==================================

Tacker uses Mistral to call actions to create Network Service. Firstly, Tacker
extracts VNFDs from NSD template to create VNFs. When creating VNF tasks is
on-success state (VNFs are in **RUNNING** state), nested VNFFGD template in
NSD template is extracted and **create_vnffg** task is called to create VNFFGs.

When NSD does not have nested VNFFG template, Tacker does not invoke creating
VNFFGs, only VNFs are created. Users can find detail implementation in [#f3]_

.. code-block:: console

                 +------------------------+
                 |                        |
                 |      NSD template      |
                 |                        |
                 |                        |
                 +------------------------+
                             | extract templates
         +-------------------v---------------+
         |                                   |
    +----v------------+            +---------v------+
    |                 |            |                |
    | VNFFGD templates|            |      VNFDs     |
    |                 |            |                |
    +----+------------+            +---------+------+
         |                                   |    create VNFs
         |                +-----------+------+-----------------+
         |                |           |                        |
         |                |           |                        |
         |           +----v---+   +---v----+              +----v---+
         |           |  VNF1  |   |  VNF2  |              |  VNFn  |
         |           +----+---+   +---+----+              +----+---+
         |                |           |                        |
         |                | +---------+                        |
         |                | | +--------------------------------+
         |                | | |
         |                | | |on-success
         |                | | |
         |            +---v-v-v---------+
         |            |      VNFFGs     |
         +------------>    (optional)   |
        create VNFFGs |                 |
                      +-----------------+

Network Service examples
========================

With NS, Tacker can use NSD template to create VNFs and VNFFGs to make a chain
between VNFs. In this document, we provide two NS examples:

1. Deploy VNFs

In this scenario, users can use NSD template to create VNFs. There are no
VNFFGs created. Templates are located in tacker/samples/tosca-templates/nsd.

2. Deploy VNFs and VNFFG between 2 HTTP servers

In the second scenario, users can use NSD template to create 2 VNFs and
2 VNFFGs. Templates are located in tacker/samples/tosca-templates/vnffg-nsd.

The below diagram describes the second scenario, NSD is used to create VNF1,
VNF2, VNFFG1 and VNFFG2. VNFFG1 will chain traffic from http_client to
http_server go through VNF1 and VNF2, while VNFFG2 only route traffic go
through VNF1.

.. code-block:: console

                           +------------+        +------------+
                           |    VNF1    |        |    VNF2    |
                           |            |        |            |
                           |    CP12    |        |    CP22    |
                           +--^-+---^-+-+        +----^--+----+
                              | |   | |               |  |
                              | |   | |               |  |
    +-------------+ VNFFG1    | |   | |               |  |               +-------------+
    |             +-----------+ +---------------------+  +--------------->             |
    | http_client |                 | |                                  | http_server |
    |             +-----------------+ +---------------------------------->             |
    +-------------+ VNFFG2                                               +-------------+



.. note::
  VNF1 and VNF2 are just a name, that can be changed.

Users can look at document about VNF [#f4]_ and VNFFG [#f5]_ [#f6]_ usage guide
to know more detail about this scenarios.

Setup experiment environment
============================

To support users easily create testing environment, Tacker provides some bash
scripts to create **http_client**, **http_server** servers and default VIM0.
Tacker also update information in **ns_param.yaml** file.

Users can go to **contrib/tacker-config/**, then run **ns-config.sh** script:

.. code-block:: console

  $ cd ~/tacker/contrib/tacker-config
  $ ./ns-config.sh

After ns-config.sh is deployed, if there are no error, 2 new servers and
a new default VIM will be launched and **ns_param.yaml** will be updated.

.. code-block:: console

  $ openstack server list
  $ openstack vim list
  $ cat ../../samples/tosca-templates/nsd/ns_param.yaml
  $ cat ../../samples/tosca-templates/vnffg-nsd/ns_param.yaml

1. Using NSD to create VNFs
===========================

Once OpenStack along with Tacker has been successfully installed, deploying
sample VNFD templates using **sample-tosca-vnfd1.yaml** [#f7]_ and
**sample-tosca-vnfd2.yaml** [#f8]_.

.. code-block:: console

  $ cd ~/tacker/samples/tosca-templates/nsd
  $ openstack vnf descriptor create --vnfd-file sample-tosca-vnfd1.yaml sample-tosca-vnfd1
  $ openstack vnf descriptor create --vnfd-file sample-tosca-vnfd2.yaml sample-tosca-vnfd2

The following code represents sample NSD which instantiates the above VNFs.

.. note::

  VNF descriptor names must be same as values in **imports** part in NSD
  template.

.. code-block:: console

    tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0

    description: Import VNFDs(already on-boarded) with input parameters
    imports:
        - sample-tosca-vnfd1
        - sample-tosca-vnfd2

    topology_template:
      inputs:
        vl1_name:
          type: string
          description: name of VL1 virtuallink
          default: net_mgmt
        vl2_name:
          type: string
          description: name of VL2 virtuallink
          default: net0
      node_templates:
          VNF1:
            type: tosca.nodes.nfv.VNF1
            requirements:
              - virtualLink1: VL1
              - virtualLink2: VL2

          VNF2:
            type: tosca.nodes.nfv.VNF2

          VL1:
            type: tosca.nodes.nfv.VL
            properties:
              network_name: {get_input: vl1_name}
              vendor: tacker

          VL2:
            type: tosca.nodes.nfv.VL
            properties:
              network_name: {get_input: vl2_name}
              vendor: tacker

In above NSD template VL1 and VL2 are substituting the virtual links of VNF1.

To create Network Service, users can use two ways:

1. Onboard the above  NSD, then create NS from NSD.

.. code-block:: console

  $ openstack ns descriptor create --nsd-file sample-tosca-nsd.yaml NSD-template
  $ openstack ns create --nsd-name NSD-template --param-file ns_param.yaml NS1

2. Create NS directly from NSD

.. code-block:: console

  $ openstack ns create --nsd-template sample-tosca-nsd.yaml --param-file ns_param.yaml NS1

2. Using NSD to create VNFs and VNFFG
=====================================

In this scenario, in the same way with above scenario, firstly, users need to
create vnf descriptors, which is defined in NSD template.

.. code-block:: console

  $ cd ~/tacker/samples/tosca-templates/vnffg-nsd
  $ openstack vnf descriptor create --vnfd-file tosca-vnfd1-sample.yaml sample-vnfd1
  $ openstack vnf descriptor create --vnfd-file tosca-vnfd2-sample.yaml sample-vnfd2

The following code represents sample NSD which instantiates the above VNFs and
VNFFG.

.. code-block:: yaml

    tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0

    description: Import VNFDs(already on-boarded) with input parameters
    imports:
        - sample-vnfd1
        - sample-vnfd2

    topology_template:
      inputs:
        vl1_name:
          type: string
          description: name of VL1 virtuallink
          default: net_mgmt
        vl2_name:
          type: string
          description: name of VL2 virtuallink
          default: net0
        net_src_port_id:
          type: string
          description: neutron port id of source port
        ip_dest_prefix:
          type: string
          description: IP prefix of destination port

      node_templates:
        VNF1:
          type: tosca.nodes.nfv.VNF1
          requirements:
            - virtualLink1: VL1

        VNF2:
          type: tosca.nodes.nfv.VNF2

        VL1:
          type: tosca.nodes.nfv.VL
          properties:
            network_name: {get_input: vl1_name}
            vendor: tacker

        VL2:
          type: tosca.nodes.nfv.VL
          properties:
            network_name: {get_input: vl2_name}
            vendor: tacker

        Forwarding_path1:
          type: tosca.nodes.nfv.FP.TackerV2
          description: creates path inside ns (src_port->CP12->CP22->dst_port)
          properties:
            id: 51
            symmetrical: true
            policy:
              type: ACL
              criteria:
                - name: block_tcp
                  classifier:
                    network_src_port_id: {get_input: net_src_port_id}
                    destination_port_range: 80-1024
                    ip_proto: 6
                    ip_dst_prefix: {get_input: ip_dest_prefix}
            path:
              - forwarder: sample-vnfd1
                capability: CP12
              - forwarder: sample-vnfd2
                capability: CP22

        Forwarding_path2:
          type: tosca.nodes.nfv.FP.TackerV2
          description: creates path inside ns (src_port->CP12->CP22->dst_port)
          properties:
            id: 52
            symmetrical: false
            policy:
              type: ACL
              criteria:
                - name: block_tcp
                  classifier:
                    network_src_port_id: {get_input: net_src_port_id}
                    destination_port_range: 8080-8080
                    ip_proto: 6
                    ip_dst_prefix: {get_input: ip_dest_prefix}
            path:
              - forwarder: sample-vnfd1
                capability: CP12

      groups:

        VNFFG1:
          type: tosca.groups.nfv.VNFFG
          description: HTTP to Corporate Net
          properties:
            vendor: tacker
            version: 1.0
            number_of_endpoints: 2
            dependent_virtual_link: [VL1, VL2]
            connection_point: [CP12, CP22]
            constituent_vnfs: [sample-vnfd1, sample-vnfd2]
          members: [Forwarding_path1]

        VNFFG2:
          type: tosca.groups.nfv.VNFFG
          description: HTTP to Corporate Net
          properties:
            vendor: tacker
            version: 1.0
            number_of_endpoints: 1
            dependent_virtual_link: [VL1]
            connection_point: [CP12]
            constituent_vnfs: [sample-vnfd1]
          members: [Forwarding_path2]

To create Network Service, users can use two ways:

1. Onboard the above  NSD, then create NS from NSD.

.. code-block:: console

  $ openstack ns descriptor create --nsd-file tosca-multiple-vnffg-nsd.yaml NSD-VNFFG-template
  $ openstack ns create --nsd-name NSD-VNFFG-template --param-file ns_param.yaml NS2

2. Create NS directly from NSD

.. code-block:: console

  $ openstack ns create --nsd-template tosca-multiple-vnffg-nsd.yaml --param-file ns_param.yaml NS2

Result
======

The following commands shows the result of launching NS in second scenario. If
users run the first scenario, some information about VNFFG is not listed, such
as VNFFG ID and can not see any VNFFG is created.

.. code-block:: console

    $ openstack ns list --fit-width
    +------------------+------+------------------+------------------+------------------+--------------------+----------------+
    | ID               | Name | NSD ID           | VNF IDs          | VNFFG IDs        | Mgmt Urls          | Status         |
    +------------------+------+------------------+------------------+------------------+--------------------+----------------+
    | 23380f92-3e0a-45 | NS2  | 7ff1c49a-4e89-4b | {'VNF2': 'f92aad | {'VNFFG2':       | {'VNF2': {'VDU1':  | ACTIVE         |
    | 39-877c-         |      | 66-9413-810715b8 | a2-c194-4906-b58 | '24f03f01-7a6d-  | '192.168.120.12'}, |                |
    | b421dc8960b6     |      | 470e             | 5-e6c8201f0010', | 44ba-b8b8-086ab7 | 'VNF1': {'VDU1':   |                |
    |                  |      |                  | 'VNF1':          | bd2f21',         | '192.168.120.3'}}  |                |
    |                  |      |                  | '25686357-ebdf-  | 'VNFFG1': '3ccad |                    |                |
    |                  |      |                  | 4b8e-ab04-7b34a5 | c6e-5702-4516    |                    |                |
    |                  |      |                  | 66e21f'}         | -babd-           |                    |                |
    |                  |      |                  |                  | 1013e9afffbf'}   |                    |                |
    +------------------+------+------------------+------------------+------------------+--------------------+----------------+

    $ openstack vnf graph list --fit-width
    +------------------------------------+------------------------------------+-------------------------------------+--------+
    | ID                                 | Name                               | VNFFGD ID                           | Status |
    +------------------------------------+------------------------------------+-------------------------------------+--------+
    | 24f03f01-7a6d-44ba-                | NS2_VNFFG2_a7f77e11-d847-4090-aa79 | 1f2bdd92-c313-4f1d-a423-51e66bc6f1d | ACTIVE |
    | b8b8-086ab7bd2f21                  | -496610c522bf                      | 1                                   |        |
    | 3ccadc6e-5702-4516-babd-           | NS2_VNFFG1_a7f77e11-d847-4090-aa79 | 9923e4ab-19d4-4ff5-b07b-            | ACTIVE |
    | 1013e9afffbf                       | -496610c522bf                      | 0e82a61e2268                        |        |
    +------------------------------------+------------------------------------+-------------------------------------+--------+

    $ openstack vnf list --fit-width
    +---------------------+---------------------+---------------------+--------+---------------------+-----------------------+
    | ID                  | Name                | Mgmt Url            | Status | VIM ID              | VNFD ID               |
    +---------------------+---------------------+---------------------+--------+---------------------+-----------------------+
    | 25686357-ebdf-4b8e- | NS2_VNF_183c3dba-70 | {"VDU1":            | ACTIVE | 3ec1a3f0-058a-40e7- | 183c3dba-7090-4984-bb |
    | ab04-7b34a566e21f   | 90-4984-bb57-e0dd11 | "192.168.120.3"}    |        | 83d2-cc8dd24af0ca   | 57-e0dd11045563       |
    |                     | 045563_a7f77e11-d84 |                     |        |                     |                       |
    |                     | 7-4090-aa79-496610c |                     |        |                     |                       |
    |                     | 522bf               |                     |        |                     |                       |
    | f92aada2-c194-4906- | NS2_VNF_3762c695-08 | {"VDU1":            | ACTIVE | 3ec1a3f0-058a-40e7- | 3762c695-08f1-4247    |
    | b585-e6c8201f0010   | f1-4247-bfda-56d2f5 | "192.168.120.12"}   |        | 83d2-cc8dd24af0ca   | -bfda-56d2f565e8b7    |
    |                     | 65e8b7_a7f77e11-d84 |                     |        |                     |                       |
    |                     | 7-4090-aa79-496610c |                     |        |                     |                       |
    |                     | 522bf               |                     |        |                     |                       |
    +---------------------+---------------------+---------------------+--------+---------------------+-----------------------+

    $ openstack vnf network forwarding path list
    +--------------------------------------+------------------+--------+--------------------------------------+---------+
    | ID                                   | Name             | Status | VNFFG ID                             | Path ID |
    +--------------------------------------+------------------+--------+--------------------------------------+---------+
    | 3d24b870-fe0d-4af9-a03f-9e0811859256 | Forwarding_path2 | ACTIVE | a601e938-a37b-493c-a48c-2c90aba73a77 | 52      |
    | a2ca3a24-f02e-4629-b12c-54256886c050 | Forwarding_path1 | ACTIVE | 1f48603b-6740-4b94-a981-15de8c5c0fb3 | 51      |
    +--------------------------------------+------------------+--------+--------------------------------------+---------+

    $ openstack sfc port chain list --fit-width
    +---------------------+---------------------+---------------------+---------------------+---------------------+----------+
    | ID                  | Name                | Port Pair Groups    | Flow Classifiers    | Chain Parameters    | Chain ID |
    +---------------------+---------------------+---------------------+---------------------+---------------------+----------+
    | 2950fa88-d98f-4812  | NS2_VNFFG2_a7f77e11 | [u'e92feb43-4906-45 | [u'3eff5973-c612-43 | {u'symmetric':      |       51 |
    | -830a-ae15452a8c08  | -d847-4090-aa79     | 21-852f-            | 83-aee2-d1eb05c832e | False,              |          |
    |                     | -496610c522bf-port- | 1940c2f344a6']      | e']                 | u'correlation':     |          |
    |                     | chain               |                     |                     | u'mpls'}            |          |
    | 61c938f9-15a1-4ec8  | NS2_VNFFG1_a7f77e11 | [u'e92feb43-4906-45 | [u'b4cb5575-cb3c-41 | {u'symmetric':      |       52 |
    | -8dec-44e5f8af70ff  | -d847-4090-aa79     | 21-852f-            | a3-8649-c69e0cd48db | False,              |          |
    |                     | -496610c522bf-port- | 1940c2f344a6', u'82 | e']                 | u'correlation':     |          |
    |                     | chain               | dab526-540e-4047    |                     | u'mpls'}            |          |
    |                     |                     | -ba8a-              |                     |                     |          |
    |                     |                     | c97c4cdbaef1']      |                     |                     |          |
    +---------------------+---------------------+---------------------+---------------------+---------------------+----------+

After deployment is finished, users can clean resources (NS, VNFD, http client
and server) with **ns-clean.sh** script.

.. code-block:: console

  $ cd ~/tacker/contrib/tacker-config
  $ ./ns-clean.sh

Reference
=========

.. [#f1] https://www.etsi.org/deliver/etsi_gs/NFV-IFA/001_099/014/02.01.01_60/gs_NFV-IFA014v020101p.pdf
.. [#f2] https://wiki.onap.org/display/DW/ONAP+Release+1+modeling+specification?preview=%2F13599755%2F13599839%2FNSD+Specification.pdf
.. [#f3] https://opendev.org/openstack/tacker/src/branch/master/tacker/nfvo/drivers/workflow/workflow_generator.py
.. [#f4] https://docs.openstack.org/tacker/latest/install/deploy_openwrt.html
.. [#f5] https://docs.openstack.org/tacker/latest/user/vnffg_usage_guide.html
.. [#f6] https://docs.openstack.org/tacker/latest/user/vnffg_usage_guide_advanced.html
.. [#f7] https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/nsd/sample-tosca-vnfd1.yaml
.. [#f8] https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/nsd/sample-tosca-vnfd2.yaml
