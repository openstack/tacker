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

======================
VNF Manager User Guide
======================

Tacker VNF Manager (VNFM) component manages the life-cycle of a Virtual Network
Function (VNF). VNFM takes care of deployment, monitoring, updating, scaling
and removal of VNFs on a Virtual Infrastructure Manager (VIM).


Onboarding VNF
==============

TOSCA VNFD templates can be onboarded to Tacker VNFD Catalog using following
command:

.. code-block:: console

   openstack vnf descriptor create --vnfd-file <yaml file path> <VNFD-NAME>

.. note::

   Users can find various sample TOSCA templates at https://github.com/openstack/tacker/tree/master/samples/tosca-templates/vnfd

Deploying VNF
=============

There are two ways to create a VNF in Tacker.

#. Using Tacker Catalog
#. Direct VNF Instantiation

Using Tacker Catalog
--------------------

In this method, a TOSCA VNFD template is first onboarded into Tacker VNFD
catalog. This VNFD is then used to create VNF. This is most common way of
creating VNFs in Tacker.

   i). Onboard a TOSCA VNFD template.

.. code-block:: console

   openstack vnf descriptor create --vnfd-file <yaml file path> <VNFD-NAME>
..

  ii). Create a VNF.

.. code-block:: console

   openstack vnf create --vnfd-name <VNFD-FILE-NAME> <VNF-NAME>


Example
~~~~~~~

.. code-block:: console

    openstack vnf descriptor create --vnfd-file sample-vnfd-hello-world.yaml hello-world-vnfd
    openstack vnf create --vnfd-name hello-world-vnfd hw-vnf

Direct VNF Instantiation
------------------------

In this method, VNF is created directly from the TOSCA template without
onboarding the template into Tacker VNFD Catalog.

.. code-block:: console

   openstack vnf create --vnfd-template <VNFD-FILE-NAME> <VNF-NAME>

This method is recommended when NFV Catalog is maintained outside Tacker and
Tacker is primarily used as a NFV workflow engine.

Example
~~~~~~~

.. code-block:: console

    openstack vnf create --vnfd-template sample-vnfd-hello-world.yaml hw-vnf

.. note ::

    vnfd-list command will show only the onboarded VNFDs. To list the VNFDs
    created internally for direct VNF instantiation, use
    '--template-source inline' flag. To list both onboarded and inline VNFDs,
    use '--template-source all' flag. The default flag for vnfd-list command
    is '--template-source onboarded'.

    .. code-block:: console

      openstack vnf descriptor list --template-source inline
      openstack vnf descriptor list --template-source all

Finding VNFM Status
===================

Status of various VNFM resources can be checked by following commands.

.. code-block:: console

   openstack vim list
   openstack vnf descriptor list
   openstack vnf list
   openstack vnf show <VNF_ID>
   openstack vnf descriptor show <VNFD_ID>

..

Updating VNF
============

VNFs can be updated as shown below.
--config, --config-file and --param-file can not be specified together.

.. code-block:: console

   openstack vnf set --config <CONFIG-DATA> <VNF_ID/NAME>
   openstack vnf set --config-file <CONFIG-FILE-NAME> <VNF_ID/NAME>
   openstack vnf set --param-file <PARAMETER-FILE-NAME> <VNF_ID/NAME>
..

Deleting VNF and VNFD
=====================

VNFs and VNFDs can be deleted as shown below.

.. code-block:: console

   openstack vnf delete <VNF_ID/NAME>
   openstack vnf descriptor delete <VNFD_ID/NAME>
..
