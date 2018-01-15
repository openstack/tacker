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


Registering default OpenStack VIM
=================================
1.) Get one account on the OpenStack VIM.

In Tacker MANO system, the VNF can be onboarded to one target OpenStack, which
is also called VIM. Get one account on this OpenStack. For example, the below
is the account information collected in file vim-config.yaml::

    auth_url: 'https://10.1.0.5:5000'
    username: 'nfv_user'
    password: 'mySecretPW'
    project_name: 'nfv'
    project_domain_name: 'Default'
    user_domain_name: 'Default'
    cert_verify: 'True'

By default, cert_verify is set as 'True'. To disable verifying SSL certificate,
user can set cert_verify parameter to 'False'.


2.) Register the VIM that will be used as a default VIM for VNF deployments.
This will be required when the optional argument --vim-id is not provided by
the user during vnf-create.

.. code-block:: console

   tacker vim-register --is-default --config-file vim-config.yaml \
          --description 'my first vim' hellovim
..



Onboarding sample VNF
=====================

1). Create a sample-vnfd.yaml file with the following content:

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
           image: cirros-0.3.5-x86_64-disk
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

   You can find more sample tosca templates at
   https://github.com/openstack/tacker/tree/master/samples/tosca-templates/vnfd.


2). Create a sample vnfd.

.. code-block:: console

   tacker vnfd-create --vnfd-file sample-vnfd.yaml samplevnfd
..

3). Create a VNF.

.. code-block:: console

   tacker vnf-create --vnfd-name samplevnfd samplevnf
..

5). Check the status.

.. code-block:: console

   tacker vim-list
   tacker vnfd-list
   tacker vnf-list
   tacker vnf-show samplevnf
..
