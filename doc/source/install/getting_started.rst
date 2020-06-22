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

Once Tacker is installed successfully, follow the steps given below to get
started with Tacker and validate the installation.


Registering default OpenStack VIM
---------------------------------

#. Get one account on the OpenStack VIM

   In Tacker MANO system, VNFs can be on-boarded to a target OpenStack which
   is also called as VIM. Get one account on your OpenStack, such as ``admin``
   if you deploy your OpenStack via devstack. Here is an example of a user
   named as ``nfv_user`` and has a project ``nfv`` on OpenStack for
   VIM configuration. It is described in ``vim_config.yaml`` [1]_:

   .. literalinclude:: ../../../samples/vim/vim_config.yaml
       :language: yaml

   .. note::

       In Keystone, port ``5000`` is enabled for authentication service [2]_,
       so the end users can use ``auth_url: 'http://127.0.0.1:5000/v3'`` instead
       of ``auth_url: 'http://127.0.0.1/identity'`` as above mention.

   By default, ``cert_verify`` is set as ``True``. To disable verifying SSL
   certificate, user can set ``cert_verifyi`` parameter to ``False``.

#. Register VIM

   Register the default VIM with the config file for VNF deployment.
   This will be required when the optional argument ``--vim-id`` is not
   provided by the user during VNF creation.

   .. code-block:: console

       $ openstack vim register --config-file vim_config.yaml \
              --description 'my first vim' --is-default hellovim


Onboarding sample VNF
---------------------

#. Create a ``sample-vnfd.yaml`` file with the following template

   .. code-block:: yaml

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
               image: cirros-0.4.0-x86_64-disk
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

   .. note::

       You can find several samples of tosca template for VNFD at [3]_.


#. Create a sample VNFD

   .. code-block:: console

      $ openstack vnf descriptor create --vnfd-file sample-vnfd.yaml samplevnfd

#. Create a VNF

   .. code-block:: console

      $ openstack vnf create --vnfd-name samplevnfd samplevnf

#. Some basic Tacker commands

   You can find each of VIM, VNFD and VNF created in previous steps by using
   ``list`` subcommand.

   .. code-block:: console

      $ openstack vim list
      $ openstack vnf descriptor list
      $ openstack vnf list

   If you inspect attributes of the isntances, use ``show`` subcommand with
   name or ID. For example, you can inspect the VNF named as ``samplevnf``
   as below.

   .. code-block:: console

      $ openstack vnf show samplevnf

References
----------

.. [1] https://opendev.org/openstack/tacker/src/branch/master/samples/vim/vim_config.yaml
.. [2] https://docs.openstack.org/keystoneauth/latest/using-sessions.html#sessions-for-users
.. [3] https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnfd
