=======================================
Service Function Chain (SFC) Management
=======================================

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

A default VIM should be registered according to :doc:`./cli-legacy-vim`.

The following VNFDs are created with the name ``VNFD1`` and ``VNFD2``
according to :doc:`./cli-legacy-vnfd`.

* `tosca-vnffg-vnfd1.yaml <https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnffgd/tosca-vnffg-vnfd1.yaml>`_
* `tosca-vnffg-vnfd2.yaml <https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnffgd/tosca-vnffg-vnfd2.yaml>`_

.. code-block:: console

  $ openstack vnf descriptor create --vnfd-file tosca-vnffg-vnfd1.yaml VNFD1
  $ openstack vnf descriptor create --vnfd-file tosca-vnffg-vnfd2.yaml VNFD2


The VNFs from the created VNFDs are deployed with the name ``VNF1`` and
``VNF2`` according to :doc:`./cli-legacy-vnf`.

.. code-block:: console

  $ openstack vnf create --vnfd-name VNFD1 VNF1
  $ openstack vnf create --vnfd-name VNFD2 VNF2


A VNFFG should be deployed according to :doc:`./cli-legacy-vnffg`. Before
deploying the VNFFG, a VNFFGD may need to be created according to
:doc:`./cli-legacy-vnffgd`.

CLI reference for SFC Management
--------------------------------

1. List Service Function Chain
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf chain list


Result:

.. code-block:: console

  +--------------------------------------+--------+--------------------------------------+
  | ID                                   | Status | NFP ID                               |
  +--------------------------------------+--------+--------------------------------------+
  | 89f99c03-a152-413b-bb39-c7618a54b23a | ACTIVE | ed450e71-345d-4dc8-8f32-69e3a697ad56 |
  +--------------------------------------+--------+--------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf chain list --help
  usage: openstack vnf chain list [-h] [-f {csv,json,table,value,yaml}]
                                  [-c COLUMN]
                                  [--quote {all,minimal,none,nonnumeric}]
                                  [--noindent] [--max-width <integer>]
                                  [--fit-width] [--print-empty]
                                  [--sort-column SORT_COLUMN] [--nfp-id NFP_ID]
                                  [--tenant-id TENANT_ID]

  List SFC(s) that belong to a given tenant.

  optional arguments:
    -h, --help            show this help message and exit
    --nfp-id NFP_ID       List SFC(s) with specific nfp id
    --tenant-id TENANT_ID
                          The owner tenant ID or project ID


2. Show Service Function Chain
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf chain show <SFC: 89f99c03-a152-413b-bb39-c7618a54b23a>


Result:

.. code-block:: console

  +-------------+----------------------------------------------------+
  | Field       | Value                                              |
  +-------------+----------------------------------------------------+
  | chain       | [                                                  |
  |             |     {                                              |
  |             |         "name": "VNF1",                            |
  |             |         "connection_points": [                     |
  |             |             "d4940639-764a-4a62-9b21-6ba2e86498eb" |
  |             |         ],                                         |
  |             |         "sfc_encap": true                          |
  |             |     },                                             |
  |             |     {                                              |
  |             |         "name": "VNF2",                            |
  |             |         "connection_points": [                     |
  |             |             "eeda565a-656b-4c86-b2da-c38683ff14e3" |
  |             |         ],                                         |
  |             |         "sfc_encap": true                          |
  |             |     }                                              |
  |             | ]                                                  |
  | id          | 89f99c03-a152-413b-bb39-c7618a54b23a               |
  | instance_id | ba0b5218-1e63-49b2-9112-aba1747f29af               |
  | nfp_id      | ed450e71-345d-4dc8-8f32-69e3a697ad56               |
  | path_id     | 51                                                 |
  | project_id  | e77397d2a02c4af1b7d79cef2a406396                   |
  | status      | ACTIVE                                             |
  | symmetrical | False                                              |
  +-------------+----------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf chain show --help
  usage: openstack vnf chain show [-h] [-f {json,shell,table,value,yaml}]
                                  [-c COLUMN] [--noindent] [--prefix PREFIX]
                                  [--max-width <integer>] [--fit-width]
                                  [--print-empty]
                                  <SFC>

  Display SFC details

  positional arguments:
    <SFC>                 SFC to display (name or ID)

  optional arguments:
    -h, --help            show this help message and exit
