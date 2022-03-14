=======================
ETSI NFV-SOL VNF Update
=======================

This document describes how to update VNF in Tacker.

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

A default VIM should be registered according to
:doc:`../cli/cli-legacy-vim`.

The VNF Package(sample_vnf_pkg.zip) used below is prepared
by referring to :doc:`./vnf-package`.

Execute before "Instantiate VNF" in the procedure of
:doc:`./etsi_vnf_deployment_as_vm_with_tosca`.


VNF Update Procedures
---------------------

As mentioned in Prerequisites, the VNF must be created
before performing update.

Details of CLI commands are described in
:doc:`../cli/cli-etsi-vnflcm`.

For update VNF instance, you need to prepare a JSON-formatted definition file.

.. code-block:: json

  {
    "vnfInstanceName": "sample"
  }

.. note:: sample_param_file.json contains the VNF name as an example.


How to Update VNF
~~~~~~~~~~~~~~~~~

Execute Update CLI command and check the name of VNF instance before
and after update. This is to confirm that the name of VNF instance has
changed after update.
See `Heat CLI reference`_. for details on Heat CLI commands.

VNF instance name before update:

.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID -c 'VNF Instance Name'


Result:

.. code-block:: console

  +-------------------+-------+
  | Field             | Value |
  +-------------------+-------+
  | VNF Instance Name | None  |
  +-------------------+-------+


Update VNF can be executed by the following CLI command.

.. code-block:: console

  $ openstack vnflcm update VNF_INSTANCE_ID --I sample_param_file.json


Result:

.. code-block:: console

  Update vnf:c64ea0fd-a90c-4754-95f4-dc0751db519d

.. note::
  Create a parameter file that describes the resource information to be
  changed in advance.

.. note::
  If the *vnfdId* is not changed by update operation, the current value
  shall be updated using the request parameter.
  If the *vnfdId* is requested to be changed by update operation, the
  current values of *metadata*, *extension*, and *vnfConfigurableProperties*
  are cleared and the changed request parameters are applied.
  Current Tacker only refers *metadata*, *extension* and
  *vnfConfigurableProperties* specified in the API request. It means that
  Tacker does not refer the value of these parameters specified in VNFD.

.. note::
  The update operation can change the vimConnectionInfo associated with an
  existing VNF instance.
  Even if instantiate operation and update operation specify multiple
  vimConnectionInfo associated with one VNF instance, only one of them will
  be used for life cycle management operations.
  It is not possible to delete the key of registered vimConnectionInfo.


VNF instance name after operation:

.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID -c 'VNF Instance Name'


Result:

.. code-block:: console

  +-------------------+---------+
  | Field             | Value   |
  +-------------------+---------+
  | VNF Instance Name | sample  |
  +-------------------+---------+


You can confirm that the VNF Instance Name has been changed
by the update operation.


.. _Heat CLI reference : https://docs.openstack.org/python-openstackclient/latest/cli/plugin-commands/heat.html
