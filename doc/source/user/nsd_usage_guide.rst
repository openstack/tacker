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

.. _ref-nsd:

==========================================================
Orchestrating VNFs using Network Services Descriptor (NSD)
==========================================================

To enable dynamic composition of network services, NFV introduces Network
Service Descriptors (NSDs) that specify the network service to be created.
This usage guide describes lifecycle of Network service descriptors and
services.

NSD in Ocata can be used for creating multiple (related) VNFs in one shot
using a single TOSCA template. This is a first (big) step into NSD, few
follow-on enhancements like:
1) Creating VLs / neutron networks using NSD (to support inter-VNF private VL)
2) VNFFGD support in NSD.

Creating the NSD
~~~~~~~~~~~~~~~~

Once OpenStack along with Tacker has been successfully installed,
deploy a sample VNFD templates using vnf1.yaml and vnf2.yaml as mentioned in
reference section.

::

  tacker vnfd-create --vnfd-file vnfd1.yaml VNFD1

  tacker vnfd-create --vnfd-file vnfd2.yaml VNFD2

The following code represents sample NSD which instantiates the above VNFs

::

    tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0
    imports:
      - VNFD1
      - VNFD2
    topology_template:
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
          network_name: net0
          vendor: tacker
        VL2:
          type: tosca.nodes.nfv.VL
          properties:
              network_name: net_mgmt
              vendor: tacker

In above NSD template VL1 and VL2 are substituting the virtuallinks of VNF1.
To onboard the above  NSD:

::

   tacker nsd-create --nsd-file <nsd-file> <nsd-name>

Creating the NS
~~~~~~~~~~~~~~~~

To create a NS, you must have onboarded corresponding NSD and
VNFDS(which NS is substituting)

Tacker provides the following CLI to create NS:

::

    tacker ns-create --nsd-id <nsd-id> <ns-name>

Or you can create directly a NS without creating onboarded NSD before by
following CLI command:

::

    tacker ns-create --nsd-template <nsd-file> <ns-name>

Reference
~~~~~~~~~

VNF1 sample template for nsd named vnfd1.yaml:

::

 tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0
 description: Demo example
 node_types:
   tosca.nodes.nfv.VNF1:
     requirements:
       - virtualLink1:
           type: tosca.nodes.nfv.VL
           required: true
       - virtualLink2:
           type: tosca.nodes.nfv.VL
           required: true
     capabilities:
       forwarder1:
         type: tosca.capabilities.nfv.Forwarder
       forwarder2:
         type: tosca.capabilities.nfv.Forwarder

 topology_template:
   substitution_mappings:
     node_type: tosca.nodes.nfv.VNF1
     requirements:
       virtualLink1: [CP11, virtualLink]
       virtualLink2: [CP14, virtualLink]
     capabilities:
       forwarder1: [CP11, forwarder]
       forwarder2: [CP14, forwarder]
   node_templates:
     VDU1:
       type: tosca.nodes.nfv.VDU.Tacker
       properties:
         image: cirros-0.3.5-x86_64-disk
         flavor: m1.tiny
         availability_zone: nova
         mgmt_driver: noop
         config: |
           param0: key1
           param1: key2
     CP11:
       type: tosca.nodes.nfv.CP.Tacker
       properties:
         management: true
         anti_spoofing_protection: false
       requirements:
         - virtualBinding:
             node: VDU1

     VDU2:
       type: tosca.nodes.nfv.VDU.Tacker
       properties:
         image: cirros-0.3.5-x86_64-disk
         flavor: m1.medium
         availability_zone: nova
         mgmt_driver: noop
         config: |
           param0: key1
           param1: key2
     CP13:
       type: tosca.nodes.nfv.CP.Tacker
       properties:
         management: true
         anti_spoofing_protection: false
       requirements:
         - virtualLink:
             node: VL1
         - virtualBinding:
             node: VDU2
     CP14:
       type: tosca.nodes.nfv.CP.Tacker
       properties:
         management: true
         anti_spoofing_protection: false
       requirements:
         - virtualBinding:
             node: VDU2
     VL1:
       type: tosca.nodes.nfv.VL
       properties:
         network_name: net_mgmt
         vendor: Tacker
     VL2:
       type: tosca.nodes.nfv.VL
       properties:
         network_name: net0
         vendor: Tacker

VNF2 sample template for nsd named vnfd2.yaml:

::

  tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0
  description: Demo example

  node_types:
    tosca.nodes.nfv.VNF2:
      capabilities:
        forwarder1:
          type: tosca.capabilities.nfv.Forwarder
  topology_template:
    substitution_mappings:
      node_type: tosca.nodes.nfv.VNF2
      capabilities:
        forwarder1: [CP21, forwarder]
    node_templates:
      VDU1:
        type: tosca.nodes.nfv.VDU.Tacker
        properties:
          image: cirros-0.3.5-x86_64-disk
          flavor: m1.tiny
          availability_zone: nova
          mgmt_driver: noop
          config: |
            param0: key1
            param1: key2
      CP21:
        type: tosca.nodes.nfv.CP.Tacker
        properties:
          management: true
          anti_spoofing_protection: false
        requirements:
          - virtualLink:
              node: VL1
          - virtualBinding:
              node: VDU1
      VDU2:
        type: tosca.nodes.nfv.VDU.Tacker
        properties:
          image: cirros-0.3.5-x86_64-disk
          flavor: m1.medium
          availability_zone: nova
          mgmt_driver: noop
      CP22:
        type: tosca.nodes.nfv.CP.Tacker
        properties:
          management: true
          anti_spoofing_protection: false
        requirements:
          - virtualLink:
              node: VL2
          - virtualBinding:
              node: VDU2
      VL1:
        type: tosca.nodes.nfv.VL
        properties:
          network_name: net_mgmt
          vendor: Tacker
      VL2:
        type: tosca.nodes.nfv.VL
        properties:
          network_name: net0
          vendor: Tacker


