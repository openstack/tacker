=======================
ETSI NFV-SOL CNF Update
=======================

This document describes how to update CNF in Tacker.
Please refer to the :doc:`./mgmt_driver_for_container_update`
for how to update CNF with Mgmt Driver in Tacker.

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

The procedure of prepare for scaling operation that from "register VIM" to
"Instantiate VNF", basically refer to
:doc:`./etsi_containerized_vnf_usage_guide`.

This procedure uses an example using the sample VNF package.


CNF Update Procedures
---------------------

As mentioned in Prerequisites, the CNF must be created
before performing update.

Details of CLI commands are described in
:doc:`../cli/cli-etsi-vnflcm`.

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

.. note::
  The v2 update operation can change the ``vimConnectionInfo``
  associated with an existing VNF instance.
  Even if update operation specify multiple ``vimConnectionInfo``
  associated with one VNF instance, only one of them will be used for life
  cycle management operations.
  It is not possible to delete the key of registered ``vimConnectionInfo``.


How to Update CNF
~~~~~~~~~~~~~~~~~

Execute Update CLI command and check the name of VNF instance before
and after update. This is to confirm that the name of VNF instance has
changed after update.

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


You can confirm that the VNF Instance Name has been changed by the update
operation.


If the ``vnfdId`` is not changed by update operation, the current value
shall be updated using the request parameter.
The following attributes are updated by performing JSON Merge Patch with the
values set in the request parameter to the current values.

* vnfConfigurableProperties
* metadata
* extensions

If the ``vnfdId`` is requested to be changed by v1 update operation, the
following attributes of VNF instance shall be updated in addition to those
set in the request parameters.
These are updated with the values obtained from the VNFD associated with the
new vnfdId.

* vnfProvider
* vnfProductName
* vnfSoftwareVersion
* vnfdVersion

.. note::
  In the v2 update operation for CNF, if "Scale" or "Heal" is performed
  after updating ``vnfdId``, the VNF package associated with the
  ``vnfdId before the update`` shall be used.
  Therefore, in order to maintain the update of ``vnfdId``, it is necessary to
  execute "Terminate VNF" once and then "Instantiate VNF".
