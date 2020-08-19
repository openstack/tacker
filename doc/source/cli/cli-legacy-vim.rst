==============
VIM Management
==============

This document describes how to manage VIM with CLI in Tacker.

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

CLI reference for VIM Management
--------------------------------

1. Register VIM
^^^^^^^^^^^^^^^

Create ``vim_config.yaml`` file for OpenStack VIM:

* https://opendev.org/openstack/tacker/src/branch/master/devstack/vim_config.yaml


Register default OpenStack VIM:

.. code-block:: console

  $ openstack vim register --config-file ./vim_config.yaml --is-default \
      --description <DESCRIPTION: 'vim for nfv_user in nfv'> \
      <NAME: openstack-nfv-vim>


Result:

.. code-block:: console

  +----------------+-------------------------------------------------+
  | Field          | Value                                           |
  +----------------+-------------------------------------------------+
  | auth_cred      | {                                               |
  |                |     "username": "nfv_user",                     |
  |                |     "user_domain_name": "Default",              |
  |                |     "cert_verify": "False",                     |
  |                |     "project_id": null,                         |
  |                |     "project_name": "nfv",                      |
  |                |     "project_domain_name": "Default",           |
  |                |     "auth_url": "http://localhost/identity/v3", |
  |                |     "key_type": "barbican_key",                 |
  |                |     "secret_uuid": "***",                       |
  |                |     "password": "***"                           |
  |                | }                                               |
  | auth_url       | http://localhost/identity/v3                    |
  | created_at     | 2020-08-12 02:28:22.470813                      |
  | description    | vim for nfv_user in nfv                         |
  | id             | aacb3c7f-d532-44d9-b8ed-49e2b30114aa            |
  | is_default     | True                                            |
  | name           | openstack-nfv-vim                               |
  | placement_attr | {                                               |
  |                |     "regions": [                                |
  |                |         "RegionOne"                             |
  |                |     ]                                           |
  |                | }                                               |
  | project_id     | e77397d2a02c4af1b7d79cef2a406396                |
  | status         | PENDING                                         |
  | type           | openstack                                       |
  | updated_at     | None                                            |
  | vim_project    | {                                               |
  |                |     "name": "nfv",                              |
  |                |     "project_domain_name": "Default"            |
  |                | }                                               |
  +----------------+-------------------------------------------------+


Find the IP address of Kubernetes API:

.. code-block:: console

  $ curl http://localhost:8080/api/

  {
    "kind": "APIVersions",
    "versions": [
      "v1"
    ],
    "serverAddressByClientCIDRs": [
      {
        "clientCIDR": "0.0.0.0/0",
        "serverAddress": "<IP address: 10.0.2.15>:6443"
      }
    ]
  }


Create ``vim_config_k8s.yaml`` file for Kubernetes VIM:

.. code-block:: yaml

  auth_url: "https://<IP_ADDRESS: 10.0.2.15>:6443"
  username: "admin"
  password: "admin"
  project_name: "default"
  ssl_ca_cert: None
  type: "kubernetes"


Register Kubernetes VIM:

.. code-block:: console

  $ openstack vim register --config-file ./vim_config_k8s.yaml \
      --description <DESCRIPTION: 'k8s vim for nfv_user in nfv'> \
      <NAME: kubernetes-nfv-vim>


Result:

.. code-block:: console

  +----------------+-------------------------------------------+
  | Field          | Value                                     |
  +----------------+-------------------------------------------+
  | auth_cred      | {                                         |
  |                |     "username": "admin",                  |
  |                |     "ssl_ca_cert": "None",                |
  |                |     "auth_url": "https://10.0.2.15:6443", |
  |                |     "key_type": "barbican_key",           |
  |                |     "secret_uuid": "***",                 |
  |                |     "password": "***"                     |
  |                | }                                         |
  | auth_url       | https://10.0.2.15:6443                    |
  | created_at     | 2020-08-16 04:36:43.579859                |
  | description    | k8s vim for nfv_user in nfv               |
  | id             | fd821c54-a60f-4afe-b131-3cfb76b7df8a      |
  | is_default     | False                                     |
  | name           | kubernetes-nfv-vim                        |
  | placement_attr | {                                         |
  |                |     "regions": [                          |
  |                |         "default",                        |
  |                |         "kube-node-lease",                |
  |                |         "kube-public",                    |
  |                |         "kube-system"                     |
  |                |     ]                                     |
  |                | }                                         |
  | project_id     | a0f24742eb0e4764a76a09e30bf7b0dd          |
  | status         | PENDING                                   |
  | type           | kubernetes                                |
  | updated_at     | None                                      |
  | vim_project    | {                                         |
  |                |     "name": "default"                     |
  |                | }                                         |
  +----------------+-------------------------------------------+


Help:

.. code-block:: console

  $ openstack vim register --help
  usage: openstack vim register [-h] [-f {json,shell,table,value,yaml}]
                                [-c COLUMN] [--noindent] [--prefix PREFIX]
                                [--max-width <integer>] [--fit-width]
                                [--print-empty] [--tenant-id TENANT_ID]
                                --config-file CONFIG_FILE
                                [--description DESCRIPTION] [--is-default]
                                NAME

  Register a new VIM

  positional arguments:
    NAME                  Set a name for the VIM

  optional arguments:
    -h, --help            show this help message and exit
    --tenant-id TENANT_ID
                          The owner tenant ID or project ID
    --config-file CONFIG_FILE
                          YAML file with VIM configuration parameters
    --description DESCRIPTION
                          Set a description for the VIM
    --is-default          Set as default VIM


2. List VIMs
^^^^^^^^^^^^

.. code-block:: console

  $ openstack vim list


Result:

.. code-block:: console

  +--------------------------------------+--------------------+----------------------------------+------------+------------+-----------+
  | ID                                   | Name               | Tenant_id                        | Type       | Is Default | Status    |
  +--------------------------------------+--------------------+----------------------------------+------------+------------+-----------+
  | aacb3c7f-d532-44d9-b8ed-49e2b30114aa | openstack-nfv-vim  | e77397d2a02c4af1b7d79cef2a406396 | openstack  | True       | REACHABLE |
  +--------------------------------------+--------------------+----------------------------------+------------+------------+-----------+
  | fd821c54-a60f-4afe-b131-3cfb76b7df8a | kubernetes-nfv-vim | a0f24742eb0e4764a76a09e30bf7b0dd | kubernetes | False      | REACHABLE |
  +--------------------------------------+--------------------+----------------------------------+------------+------------+-----------+


Help:

.. code-block:: console

  $ openstack vim list --help
  usage: openstack vim list [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN]
                            [--quote {all,minimal,none,nonnumeric}] [--noindent]
                            [--max-width <integer>] [--fit-width]
                            [--print-empty] [--sort-column SORT_COLUMN] [--long]

  List VIMs that belong to a given tenant.

  optional arguments:
    -h, --help            show this help message and exit
    --long                List additional fields in output


3. Show VIM
^^^^^^^^^^^

.. code-block:: console

  $ openstack vim show <VIM: openstack-nfv-vim>


Result:

.. code-block:: console

  +----------------+-------------------------------------------------+
  | Field          | Value                                           |
  +----------------+-------------------------------------------------+
  | auth_cred      | {                                               |
  |                |     "username": "nfv_user",                     |
  |                |     "user_domain_name": "Default",              |
  |                |     "cert_verify": "False",                     |
  |                |     "project_id": null,                         |
  |                |     "project_name": "nfv",                      |
  |                |     "project_domain_name": "Default",           |
  |                |     "auth_url": "http://localhost/identity/v3", |
  |                |     "key_type": "barbican_key",                 |
  |                |     "secret_uuid": "***",                       |
  |                |     "password": "***"                           |
  |                | }                                               |
  | auth_url       | http://localhost/identity/v3                    |
  | created_at     | 2020-08-12 02:28:22                             |
  | description    | vim for nfv_user in nfv                         |
  | id             | aacb3c7f-d532-44d9-b8ed-49e2b30114aa            |
  | is_default     | True                                            |
  | name           | openstack-nfv-vim                               |
  | placement_attr | {                                               |
  |                |     "regions": [                                |
  |                |         "RegionOne"                             |
  |                |     ]                                           |
  |                | }                                               |
  | project_id     | e77397d2a02c4af1b7d79cef2a406396                |
  | status         | REACHABLE                                       |
  | type           | openstack                                       |
  | updated_at     | 2020-08-12 02:28:23                             |
  | vim_project    | {                                               |
  |                |     "name": "nfv",                              |
  |                |     "project_domain_name": "Default"            |
  |                | }                                               |
  +----------------+-------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vim show --help
  usage: openstack vim show [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                            [--noindent] [--prefix PREFIX]
                            [--max-width <integer>] [--fit-width]
                            [--print-empty]
                            <VIM>

  Display VIM details

  positional arguments:
    <VIM>                 VIM to display (name or ID)

  optional arguments:
    -h, --help            show this help message and exit


4. Update VIM
^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vim set --description \
      <DESCRIPTION: 'new description of vim for nfv_user in nfv'> \
      <VIM: openstack-nfv-vim>


Result:

.. code-block:: console

  +----------------+-------------------------------------------------+
  | Field          | Value                                           |
  +----------------+-------------------------------------------------+
  | auth_cred      | {                                               |
  |                |     "username": "nfv_user",                     |
  |                |     "user_domain_name": "Default",              |
  |                |     "cert_verify": "False",                     |
  |                |     "project_id": null,                         |
  |                |     "project_name": "nfv",                      |
  |                |     "project_domain_name": "Default",           |
  |                |     "auth_url": "http://localhost/identity/v3", |
  |                |     "key_type": "barbican_key",                 |
  |                |     "secret_uuid": "***",                       |
  |                |     "password": "***"                           |
  |                | }                                               |
  | auth_url       | http://localhost/identity/v3                    |
  | created_at     | 2020-08-12 02:28:22                             |
  | description    | new description of vim for nfv_user in nfv      |
  | id             | aacb3c7f-d532-44d9-b8ed-49e2b30114aa            |
  | is_default     | True                                            |
  | name           | openstack-nfv-vim                               |
  | placement_attr | {                                               |
  |                |     "regions": [                                |
  |                |         "RegionOne"                             |
  |                |     ]                                           |
  |                | }                                               |
  | project_id     | e77397d2a02c4af1b7d79cef2a406396                |
  | status         | REACHABLE                                       |
  | type           | openstack                                       |
  | updated_at     | 2020-08-12 02:40:39.800778                      |
  | vim_project    | {                                               |
  |                |     "name": "nfv",                              |
  |                |     "project_domain_name": "Default"            |
  |                | }                                               |
  +----------------+-------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vim set --help
  usage: openstack vim set [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                          [--noindent] [--prefix PREFIX]
                          [--max-width <integer>] [--fit-width] [--print-empty]
                          [--config-file CONFIG_FILE] [--name NAME]
                          [--description DESCRIPTION]
                          [--is-default {True,False}]
                          VIM

  Update VIM.

  positional arguments:
    VIM                   ID or name of vim to update

  optional arguments:
    -h, --help            show this help message and exit
    --config-file CONFIG_FILE
                          YAML file with VIM configuration parameters
    --name NAME           New name for the VIM
    --description DESCRIPTION
                          New description for the VIM
    --is-default {True,False}
                          Indicate whether the VIM is used as default


5. Delete VIM
^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vim delete <VIM: openstack-nfv-vim>


Result:

.. code-block:: console

  All specified vim(s) deleted successfully


Help:

.. code-block:: console

  $ openstack vim delete --help
  usage: openstack vim delete [-h] <VIM> [<VIM> ...]

  Delete VIM(s).

  positional arguments:
    <VIM>       VIM(s) to delete (name or ID)

  optional arguments:
    -h, --help  show this help message and exit
