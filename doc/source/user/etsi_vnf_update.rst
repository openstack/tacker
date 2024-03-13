=======================
ETSI NFV-SOL VNF Update
=======================

This document describes how to update VNF in Tacker v1 API.

.. note::

  This is a document for Tacker v1 API.
  See :doc:`/user/v2/vnf/update` for Tacker v2 API.


Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

A default VIM should be registered according to
:doc:`/cli/cli-legacy-vim`.

The VNF Package(sample_vnf_package_csar.zip) used below is prepared
by referring to :doc:`/user/vnf-package`.

Execute before "Instantiate VNF" in the procedure of
:doc:`/user/etsi_vnf_deployment_as_vm_with_tosca`.


VNF Update Procedures
---------------------

As mentioned in Prerequisites, the VNF must be created
before performing update.

Details of CLI commands are described in
:doc:`/cli/cli-etsi-vnflcm`.

For update VNF instance, you need to prepare a JSON-formatted definition file.

.. code-block:: json

  {
    "vnfInstanceName": "sample"
  }


.. note::

  sample_param_file.json contains the VNF name as an example.
  For v1 update operation, the following attributes of
  ``VnfInfoModificationRequest`` are not supported.

  * vnfConfigurableProperties
  * metadata
  * extensions
  * vnfcInfoModifications
  * vimConnectionInfo


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

  +-------------------+------------------------------------------+
  | Field             | Value                                    |
  +-------------------+------------------------------------------+
  | VNF Instance Name | vnf-810d8c9b-e467-4b06-9265-ac9dce015fce |
  +-------------------+------------------------------------------+


Update VNF can be executed by the following CLI command.

.. code-block:: console

  $ openstack vnflcm update VNF_INSTANCE_ID --I sample_param_file.json


Result:

.. code-block:: console

  Update vnf:810d8c9b-e467-4b06-9265-ac9dce015fce


.. note::

  Create a parameter file that describes the resource information to be
  changed in advance.


VNF instance name after operation:

.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID -c 'VNF Instance Name'


Result:

.. code-block:: console

  +-------------------+--------+
  | Field             | Value  |
  +-------------------+--------+
  | VNF Instance Name | sample |
  +-------------------+--------+


You can confirm that the VNF Instance Name has been changed by the update
operation.

If the ``vnfdId`` is not changed by update operation, the current value
shall be updated using the request parameter.

If the ``vnfdId`` is requested to be changed by v1 update operation, the
following attributes of VNF instance shall be updated in addition to those
set in the request parameters.
These are updated with the values obtained from the VNFD associated with the
new vnfdId.

* vnfProvider
* vnfProductName
* vnfSoftwareVersion
* vnfdVersion


.. _Heat CLI reference : https://docs.openstack.org/python-openstackclient/latest/cli/plugin-commands/heat.html
