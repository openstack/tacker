==========================
Flow Classifier Management
==========================

Flow Classifier (FC) is a part of Network Forwarding Path (NFP) in VNF
Forwarding Graph (VNFFG).

This document describes how to manage FC with CLI in Tacker.

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


VNFFG should be deployed according to :doc:`./cli-legacy-vnffg`. Before
deploying the VNFFG, a VNFFGD may need to be created according to
:doc:`./cli-legacy-vnffgd`.

CLI reference for FC Management
-------------------------------

1. List Flow Classifier
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf classifier list


Result:

.. code-block:: console

  +--------------------------------------+-----------+--------+--------------------------------------+--------------------------------------+
  | ID                                   | Name      | Status | NFP ID                               | Chain ID                             |
  +--------------------------------------+-----------+--------+--------------------------------------+--------------------------------------+
  | 31268b39-27d3-4108-9552-73490125d29a | block_tcp | ACTIVE | ed450e71-345d-4dc8-8f32-69e3a697ad56 | 89f99c03-a152-413b-bb39-c7618a54b23a |
  +--------------------------------------+-----------+--------+--------------------------------------+--------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf classifier list --help
  usage: openstack vnf classifier list [-h] [-f {csv,json,table,value,yaml}]
                                      [-c COLUMN]
                                      [--quote {all,minimal,none,nonnumeric}]
                                      [--noindent] [--max-width <integer>]
                                      [--fit-width] [--print-empty]
                                      [--sort-column SORT_COLUMN]
                                      [--nfp-id NFP_ID] [--tenant-id TENANT_ID]

  List flow classifier(s) that belong to a given tenant.

  optional arguments:
    -h, --help            show this help message and exit
    --nfp-id NFP_ID       List flow classifier(s) with specific nfp id
    --tenant-id TENANT_ID
                          The owner tenant ID or project ID


2. Show Flow Classifier
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf classifier show <ID: 31268b39-27d3-4108-9552-73490125d29a>


Result:

.. code-block:: console

  +-------------+--------------------------------------------------------------------+
  | Field       | Value                                                              |
  +-------------+--------------------------------------------------------------------+
  | chain_id    | 89f99c03-a152-413b-bb39-c7618a54b23a                               |
  | id          | 31268b39-27d3-4108-9552-73490125d29a                               |
  | instance_id | 566e6760-9f0b-4b5e-a6e5-d8deab00efd3                               |
  | match       | {                                                                  |
  |             |     "ip_dst_prefix": "10.10.0.5/24",                               |
  |             |     "ip_proto": 6,                                                 |
  |             |     "destination_port_min": 80,                                    |
  |             |     "destination_port_max": 1024,                                  |
  |             |     "network_src_port_id": "d4940639-764a-4a62-9b21-6ba2e86498eb", |
  |             |     "tenant_id": "e77397d2a02c4af1b7d79cef2a406396"                |
  |             | }                                                                  |
  | name        | block_tcp                                                          |
  | nfp_id      | ed450e71-345d-4dc8-8f32-69e3a697ad56                               |
  | project_id  | e77397d2a02c4af1b7d79cef2a406396                                   |
  | status      | ACTIVE                                                             |
  +-------------+--------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf classifier show --help
  usage: openstack vnf classifier show [-h] [-f {json,shell,table,value,yaml}]
                                      [-c COLUMN] [--noindent]
                                      [--prefix PREFIX] [--max-width <integer>]
                                      [--fit-width] [--print-empty]
                                      <Classifier ID>

  Display flow classifier details

  positional arguments:
    <Classifier ID>       Flow Classifier to display (name or ID)

  optional arguments:
    -h, --help            show this help message and exit
