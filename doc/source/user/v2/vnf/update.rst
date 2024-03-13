=======================
ETSI NFV-SOL VNF Update
=======================

This document describes how to update VNF in Tacker v2 API.

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

Execute before "Create VNF" or "Instantiate VNF" in the procedure of
:doc:`/user/v2/vnf/deployment_with_user_data/index`.


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
  The Update operation can update the following.

  * vnfInstanceName
  * vnfInstanceDescription
  * vnfId
  * vnfConfigurableProperties
  * metadata
  * extensions
  * vnfcInfoModifications
  * vimConnectionInfo


.. note::

  The update operation can change the ``vimConnectionInfo``
  associated with an existing VNF instance.
  Even if update operation specify multiple ``vimConnectionInfo``
  associated with one VNF instance, only one of them will be used for life
  cycle management operations.
  It is not possible to delete the key of registered ``vimConnectionInfo``.


How to Update VNF
~~~~~~~~~~~~~~~~~

Execute Update CLI command and check the name of VNF instance before
and after update. This is to confirm that the name of VNF instance has
changed after update.
See `Heat CLI reference`_. for details on Heat CLI commands.

VNF instance name before update:

.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID \
    -c 'VNF Instance Name' --os-tacker-api-version 2


Result:

.. code-block:: console

  +-------------------+-------+
  | Field             | Value |
  +-------------------+-------+
  | VNF Instance Name |       |
  +-------------------+-------+


Update VNF can be executed by the following CLI command.

.. code-block:: console

  $ openstack vnflcm update VNF_INSTANCE_ID \
    --I sample_param_file.json --os-tacker-api-version 2


Result:

.. code-block:: console

  Update vnf:df9150a0-8679-4b14-8cbc-9d2d6606ca7c


VNF instance name after operation:

.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID \
    -c 'VNF Instance Name' --os-tacker-api-version 2


Result:

.. code-block:: console

  +-------------------+--------+
  | Field             | Value  |
  +-------------------+--------+
  | VNF Instance Name | sample |
  +-------------------+--------+


You can confirm that the VNF Instance Name has been changed by the update
operation.

The following attributes are updated by performing JSON Merge Patch with the
values set in the request parameter to the current values.

* vnfConfigurableProperties
* metadata
* extensions

If the ``vnfdId`` is requested to be changed by update operation, the
following attributes of VNF instance shall be updated in addition to those
set in the request parameters.
These are updated with the values obtained from the VNFD associated with the
new vnfdId.

* vnfProvider
* vnfProductName
* vnfSoftwareVersion
* vnfdVersion

.. note::

  If the vnfdId of a VNF Instance is updated after "Instantiation",
  the actual resources will not be updated until "Scale" or "Heal" is performed.


History of Checks
-----------------

The content of this document has been confirmed to work
using the following VNF Package.

* `basic_lcms_max_individual_vnfc for 2023.2 Bobcat`_


.. _Heat CLI reference: https://docs.openstack.org/python-openstackclient/latest/cli/plugin-commands/heat.html
.. _basic_lcms_max_individual_vnfc for 2023.2 Bobcat:
  https://opendev.org/openstack/tacker/src/branch/stable/2023.2/tacker/tests/functional/sol_v2_common/samples/basic_lcms_max_individual_vnfc
