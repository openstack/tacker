..
      Copyright 2014-2015 OpenStack Foundation
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

===============
Getting Started
===============

Once tacker is installed successfully, follow the steps given below to get
started with tacker and validate the installation.

i). Create a sample-vnfd.yaml file with the following content:

.. code-block:: ini

   tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0

   description: Demo example

   metadata:
     template_name: sample-tosca-vnfd

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
           image: cirros-0.3.4-x86_64-uec
           availability_zone: nova
           mgmt_driver: noop
           config: |
             param0: key1
             param1: key2

       CP1:
         type: tosca.nodes.nfv.CP.Tacker
         properties:
           management: true
           order: 0
           anti_spoofing_protection: false
         requirements:
           - virtualLink:
               node: VL1
           - virtualBinding:
               node: VDU1

       VL1:
         type: tosca.nodes.nfv.VL
         properties:
           network_name: net_mgmt
           vendor: Tacker

..

.. note::

   You can find more sample tosca templates at https://github.com/openstack/tacker/tree/master/samples/tosca-templates/vnfd

ii). Create a sample vnfd.

.. code-block:: console

   tacker vnfd-create --vnfd-file sample-vnfd.yaml <NAME>
..

iii). Create a VNF.

.. code-block:: console

   tacker vnf-create --vnfd-id <VNFD_ID> <NAME>
..

iv). Check the status.

.. code-block:: console

   tacker vim-list
   tacker vnfd-list
   tacker vnf-list
   tacker vnf-show <VNF_ID>
..
