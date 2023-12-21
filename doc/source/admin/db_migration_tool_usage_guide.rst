===================================
VNF version upgrading from v1 to v2
===================================

Overview
--------
Tacker supports multi-version APIs: v1 API based on `NFV-SOL003 v2.6.1`_
and v2 API based on `NFV-SOL003 v3.3.1`_.
Because of the lack of compatibility between those versions,
version upgrading usually requires re-instantiation of the VNFs.

However, by using the :command:`tacker-db-manage` command,
the information on the v1 API table can be migrated to the v2 API table,
which allows VNF version upgrades without re-instantiation.

This document describes how to upgrade VNF using
the :command:`tacker-db-manage` command.

Target tables of migration
--------------------------

Target tables to be migrated:

* VnfInstanceV2
* VnfLcmOpOccV2

Source tables to be migrated:

* vnf
* vnf_attribute
* vnf_instances
* vnf_instantiated_info
* vnf_lcm_op_occs

Pre-requisites
--------------

There is a process to retrieve information about the VIM
associated with the VNF in the migration.
The authentication information of the keystone needed for this process
must be provided from the environment variables.
The required environment variables are shown below.

* OS_AUTH_URL
* OS_PASSWORD
* OS_PROJECT_DOMAIN_ID
* OS_PROJECT_DOMAIN_NAME
* OS_PROJECT_NAME
* OS_USER_DOMAIN_ID
* OS_USER_DOMAIN_NAME
* OS_USERNAME


The method of migration
-----------------------

The following command can be used to upgrade a specified VNF from v1 to v2,
without leaving any records related to the VNF on the existing v1 table.

.. code-block:: console

        $ tacker-db-manage --config-file /path/to/tacker.conf \
        --config-file /path/to/plugin/config.ini migrate-to-v2 --vnf-id <uuid_of_target_vnf>

The following command can be used to upgrade a specified VNF from v1 to v2,
leaving records related to the VNF on the existing v1 table.

.. code-block:: console

        $ tacker-db-manage --config-file /path/to/tacker.conf \
        --config-file /path/to/plugin/config.ini migrate-to-v2 --vnf-id <uuid_of_target_vnf> --keep-orig

The following command can be used to upgrade all VNFs from v1 to v2,
without leaving any records related to the VNF on the existing v1 table.

.. code-block:: console

        $ tacker-db-manage --config-file /path/to/tacker.conf \
        --config-file /path/to/plugin/config.ini migrate-to-v2 --all

The following command can be used to upgrade all VNFs from v1 to v2,
leaving records related to the VNF on the existing v1 table.

.. code-block:: console

        $ tacker-db-manage --config-file /path/to/tacker.conf \
        --config-file /path/to/plugin/config.ini migrate-to-v2 --all --keep-orig


To complete the migration after using the ``--keep-orig`` option,
the following command can be used.
This command deletes the records for a specified VNF
left on the existing v1 table.


.. code-block:: console

        $ tacker-db-manage --config-file /path/to/tacker.conf \
        --config-file /path/to/plugin/config.ini migrate-to-v2 --vnf-id <uuid_of_target_vnf> \
        --mark-delete --api-ver v1

.. note::

       This command just updates the value of the "deleted" field to 1.
       You can delete records completely by executing the
       :command:`tacker-db-manage` command with subcommand of purge_deleted.

To rollback the migration after using the ``--keep-orig`` option,
the following command can be used.
This command deletes the records for a specified VNF on the v2 table.

.. code-block:: console

        $ tacker-db-manage --config-file /path/to/tacker.conf \
        --config-file /path/to/plugin/config.ini migrate-to-v2 --vnf-id <uuid_of_target_vnf> \
        --mark-delete --api-ver v2

.. note::

       There are no "deleted" flag in v2 tables.
       Therefore this command deletes records in v2 tables completely.

Examples of migration
---------------------

Below shows the flow of upgrading a specified VNF as an example.


Confirm the existence of instantiated VNFs on v1 API:

.. code-block:: console

        $ openstack vnflcm list
        +--------------------------------------+-----------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
        | ID                                   | VNF Instance Name     | Instantiation State | VNF Provider | VNF Software Version | VNF Product Name | VNFD ID                              |
        +--------------------------------------+-----------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
        | ab358004-739b-4aa9-8d27-734208f7c625 | test_vnf              | INSTANTIATED        | Sample       | 1.0                  | Sample           | 116aaf63-0b7c-4b1d-a2d4-af73df86787d |
        +--------------------------------------+-----------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+

Read the environment variables:

.. code-block:: console

        $ source sample.rc

Execute the migration command:

.. code-block:: console

        $ tacker-db-manage --config-file /etc/tacker/tacker.conf --config-file /etc/tacker/api-paste.ini migrate-to-v2 --vnf-id ab358004-739b-4aa9-8d27-734208f7c625

.. note::

        Verify that the prompt is returned.

Confirm that there is no VNF on v1 API:

.. code-block:: console

        $ openstack vnflcm list

.. note::

        Verify that no VNF is displayed.

Confirm the existence of VNFs on v2 API:

.. code-block:: console

        $ openstack vnflcm list --os-tacker-api-version 2
        +--------------------------------------+-----------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
        | ID                                   | VNF Instance Name     | Instantiation State | VNF Provider | VNF Software Version | VNF Product Name | VNFD ID                              |
        +--------------------------------------+-----------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
        | ab358004-739b-4aa9-8d27-734208f7c625 | test_vnf              | INSTANTIATED        | Sample       | 1.0                  | Sample           | 116aaf63-0b7c-4b1d-a2d4-af73df86787d |
        +--------------------------------------+-----------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+

.. _NFV-SOL003 v2.6.1: https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/003/02.06.01_60/gs_nfv-sol003v020601p.pdf
.. _NFV-SOL003 v3.3.1: https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/003/03.03.01_60/gs_nfv-sol003v030301p.pdf
