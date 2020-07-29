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

=========================================
VNF Forwarding Graph Advanced Usage Guide
=========================================

This section cover some examples about advanced VNFFG usage guide in Tacker.
Users should have some basic knowledge about VNFFG [#f1]_, before following
this document.

Two VNFFGs go through one VNF
=============================

This scenario describes an example, where 2 VNFFGs go through one virtual
network functions (VNFs). The VNFFG1 creates the chain from VNF1 and VNF2, and
VNFFG2 creates the chain from VNF1. VNF1 belongs to both of VNFFGs.

Bellow example is the template of VNFFG1 [#f2]_, in **properties** of
Forwarding_path1, the **path** shows that VNFFG1 will go through VNF1 and VNF2.

.. code-block:: yaml

  tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0

  description: Sample VNFFG template

  topology_template:

    node_templates:

      Forwarding_path1:
        type: tosca.nodes.nfv.FP.TackerV2
        description: creates path (CP12->CP22)
        properties:
          id: 51
          policy:
            type: ACL
            criteria:
              - name: block_tcp
                classifier:
                  network_src_port_id: 640dfd77-c92b-45a3-b8fc-22712de480e1
                  destination_port_range: 80-1024
                  ip_proto: 6
                  ip_dst_prefix: 192.168.1.2/24
          path:
            - forwarder: VNFD1
              capability: CP12
            - forwarder: VNFD2
              capability: CP22

    groups:
      VNFFG1:
        type: tosca.groups.nfv.VNFFG
        description: HTTP to Corporate Net
        properties:
          vendor: tacker
          version: 1.0
          number_of_endpoints: 2
          dependent_virtual_link: [VL12,VL22]
          connection_point: [CP12,CP22]
          constituent_vnfs: [VNFD1,VNFD2]
        members: [Forwarding_path1]

Similar to the above example, VNFFG2 template [#f3]_ only create a chain that
goes through VNF1.

.. code-block:: yaml

  tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0

  description: Sample VNFFG template

  topology_template:

    node_templates:

      Forwarding_path1:
        type: tosca.nodes.nfv.FP.TackerV2
        description: creates path (CP12->CP22)
        properties:
          id: 51
          policy:
            type: ACL
            criteria:
              - name: block_tcp
                classifier:
                  network_src_port_id: 640dfd77-c92b-45a3-b8fc-22712de480e1
                  destination_port_range: 8080-8080
                  ip_proto: 6
                  ip_dst_prefix: 192.168.1.2/24
          path:
            - forwarder: VNFD1
              capability: CP12

    groups:
      VNFFG1:
        type: tosca.groups.nfv.VNFFG
        description: HTTP to Corporate Net
        properties:
          vendor: tacker
          version: 1.0
          number_of_endpoints: 1
          dependent_virtual_link: [VL12]
          connection_point: [CP12]
          constituent_vnfs: [VNFD1]
        members: [Forwarding_path1]

For testing VNF Forwarding graph feature, we create 2 servers, **http_client**
and **http_server**. The example uses **net0** to create VNFFG on that network.

.. code-block:: console

  $ net_id=$(openstack network list | grep net0 | awk '{print $2}')
  $ openstack server create --flavor m1.tiny --image cirros-0.4.0-x86_64-disk --nic net-id=$net_id http_client
  $ openstack server create --flavor m1.tiny --image cirros-0.4.0-x86_64-disk --nic net-id=$net_id http_server

To get information about neutron ports of **http_client** and **http_server**
that are used for classifying traffics, user can use openstack commands to
get these information.

.. code-block:: console

  $ client_ip=$(openstack server list | grep http_client | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
  $ network_source_port_id=$(openstack port list | grep $client_ip | awk '{print $2}')
  $ ip_dst=$(openstack server list | grep http_server | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')

.. note::

  Please update parameters in **classifier** such as **network_src_port_id**,
  **destination_port_range**, **ip_proto**, **ip_dst_prefix** to meet your
  environment, which is described in VNFFG usage guide [#f4]_. Classifiers
  must be different to each others.

  We assume that **http_server** and **http_client** are already created.
  VNF1 and VNF2 templates are shown in [#f5]_ and [#f6]_.

Once the OpenStack VIM is ready, firstly we can create VNFs (VNF1 and VNF2)
from VNFD templates. For easily, we put all VNFD templates and VNFFGD templates
in [#f7]_.

.. code-block:: console

  $ openstack vnf descriptor create --vnfd-file tosca-vnffg-vnfd1.yaml VNFD1
  $ openstack vnf create --vnfd-name VNFD1 --vim-name VIM0 VNF1
  $ openstack vnf descriptor create --vnfd-file tosca-vnffg-vnfd2.yaml VNFD2
  $ openstack vnf create --vnfd-name VNFD2 --vim-name VIM0 VNF2

To create VNFFG, we should get the **vnf id** for VNF1 and VNF2:

.. code-block:: console

  $ openstack vnf list --fit-width
  +-------------------------------+------+---------------------------+--------+-------------------------------+----------------------------------+
  | ID                            | Name | Mgmt Url                  | Status | VIM ID                        | VNFD ID                          |
  +-------------------------------+------+---------------------------+--------+-------------------------------+----------------------------------+
  | 2ea1b577-89c1-478e-bedd-      | VNF2 | {"VDU1": "192.168.120.5"} | ACTIVE | 45fecf6f-9080-4e8b-953c-      | 69a4d2d4-9329-4807-9c59-09cb8d95 |
  | 76f69951e840                  |      |                           |        | d9556e6ad2cb                  | c612                             |
  | 45c6c5ee-517e-                | VNF1 | {"VDU1": "192.168.120.9"} | ACTIVE | 45fecf6f-9080-4e8b-953c-      | f4cb1509-c216-47a1-b76e-         |
  | 4fc3-ad41-6e86c38d1a63        |      |                           |        | d9556e6ad2cb                  | e419f8ae6534                     |
  +-------------------------------+------+---------------------------+--------+-------------------------------+----------------------------------+

Then we can create VNFFG1 that goes through VNF1, VNF2 and VNFFG2 that only
goes through VNF1. We need to record **vnf id** to provide them in create
VNFFG commands.

.. code-block:: console

  $ openstack vnf graph descriptor create --vnffgd-file tosca-vnffgd-sample.yaml VNFFGD1
  $ openstack vnf graph descriptor create --vnffgd-file tosca-vnffgd-sample-VNF1.yaml VNFFGD2
  $ openstack vnf graph create --vnffgd-name VNFFGD1 --vnf-mapping VNFD1:45c6c5ee-517e-4fc3-ad41-6e86c38d1a63,VNFD2:2ea1b577-89c1-478e-bedd-76f69951e840 VNFFG1
  $ openstack vnf graph create --vnffgd-name VNFFGD2 --vnf-mapping VNFD1:45c6c5ee-517e-4fc3-ad41-6e86c38d1a63 VNFFG2

To check the VNFFG works fine, we can use list VNFFG and neutron port chain
list to see what happens.

.. code-block:: console

  $ openstack vnf graph list
  +--------------------------------------+--------+--------------------------------------+--------+
  | ID                                   | Name   | VNFFGD ID                            | Status |
  +--------------------------------------+--------+--------------------------------------+--------+
  | 097dcd5d-b329-44da-9693-8e56ff3612e3 | VNFFG1 | 75f53d50-f79b-446b-b9bd-48e26c3a87d0 | ACTIVE |
  | e33bc531-e124-432a-abf3-bec4f66ec15b | VNFFG2 | ead1a94f-2bf9-41fd-b543-8446cdbaac83 | ACTIVE |
  +--------------------------------------+--------+--------------------------------------+--------+

  $ openstack sfc port chain list --fit-width
  +----------------------------+-------------------+----------------------------+----------------------------+----------------------------+----------+
  | ID                         | Name              | Port Pair Groups           | Flow Classifiers           | Chain Parameters           | Chain ID |
  +----------------------------+-------------------+----------------------------+----------------------------+----------------------------+----------+
  | 03ca4afb-8fc9-4337-94a3-98 | VNFFG1-port-chain | [u'1f71e5b1-b8f2-4f1b-     | [u'46fd7fac-29f9-49cd-8959 | {u'symmetric': False,      |        1 |
  | c90c5511a8                 |                   | 9c85-6a6f31cf9906',        | -42078d873487']            | u'correlation': u'mpls'}   |          |
  |                            |                   | u'8be115b1-7422-417b-      |                            |                            |          |
  |                            |                   | abc0-49b194d432cf']        |                            |                            |          |
  | 24cbfa45-4033-4f95-aaa0-dd | VNFFG2-port-chain | [u'1f71e5b1-b8f2-4f1b-     | [u'6c94dd78-9cda-4891-ad71 | {u'symmetric': False,      |        2 |
  | 690ee1e9af                 |                   | 9c85-6a6f31cf9906']        | -81a46354356e']            | u'correlation': u'mpls'}   |          |
  +----------------------------+-------------------+----------------------------+----------------------------+----------------------------+----------+

We can see that, both of port chain will go through port pair group with the id
**1f71e5b1-b8f2-4f1b-9c85-6a6f31cf9906**, that is created from neutron port of
VNF1.

If user delete VNFFG1, the VNFFG2 is not affected because the port pair group
**1f71e5b1-b8f2-4f1b-9c85-6a6f31cf9906** is not deleted.

.. code-block:: console

  $ openstack vnf graph delete VNFFG1
  All specified vnffg(s) deleted successfully
  $ openstack vnf graph list
  +--------------------------------------+--------+--------------------------------------+--------+
  | ID                                   | Name   | VNFFGD ID                            | Status |
  +--------------------------------------+--------+--------------------------------------+--------+
  | e33bc531-e124-432a-abf3-bec4f66ec15b | VNFFG2 | ead1a94f-2bf9-41fd-b543-8446cdbaac83 | ACTIVE |
  +--------------------------------------+--------+--------------------------------------+--------+
  $ openstack sfc port chain list --fit-width
  +----------------------------+-------------------+----------------------------+----------------------------+----------------------------+----------+
  | ID                         | Name              | Port Pair Groups           | Flow Classifiers           | Chain Parameters           | Chain ID |
  +----------------------------+-------------------+----------------------------+----------------------------+----------------------------+----------+
  | 24cbfa45-4033-4f95-aaa0-dd | VNFFG2-port-chain | [u'1f71e5b1-b8f2-4f1b-     | [u'6c94dd78-9cda-4891-ad71 | {u'symmetric': False,      |        2 |
  | 690ee1e9af                 |                   | 9c85-6a6f31cf9906']        | -81a46354356e']            | u'correlation': u'mpls'}   |          |
  +----------------------------+-------------------+----------------------------+----------------------------+----------------------------+----------+


.. rubric:: Footnotes

.. [#f1] https://docs.openstack.org/tacker/latest/user/vnffg_usage_guide.html
.. [#f2] https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnffgd/tosca-vnffgd-sample.yaml
.. [#f3] https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnffgd/tosca-vnffgd-sample-VNF1.yaml
.. [#f4] https://docs.openstack.org/tacker/latest/user/vnffg_usage_guide.html
.. [#f5] https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnffgd/tosca-vnffg-vnfd1.yaml
.. [#f6] https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnffgd/tosca-vnffg-vnfd2.yaml
.. [#f7] https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnffgd
