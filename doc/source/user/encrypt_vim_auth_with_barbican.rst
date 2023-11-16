Save VIM credentials into Barbican
==================================

Overview
--------

This document shows how to operate vims which use barbican to save
vim key in devstack environment.

The brief code workflow is described as following:

When creating a vim:
We use fernet to encrypt the VIM password, then use the tacker service tenant
configured in the tacker.conf to save the fernet key to the barbican as
a secret. barbican will return **secret_uuid**.
then save encrypted into vim db's field **password**, and save the secret uuid
into vim db field **secret_uuid**.

Tacker service tenant configured in the tacker.conf as follows:

.. code-block:: ini

    [keystone_authtoken]
    memcached_servers = localhost:11211
    signing_dir = /var/cache/tacker
    cafile = /opt/stack/data/ca-bundle.pem
    project_domain_name = <DOMAIN_NAME>
    project_name = service
    user_domain_name = <DOMAIN_NAME>
    username = <TACKER_USER_NAME>
    password = <TACKER_SERVICE_USER_PASSWORD>
    auth_url = http://127.0.0.1/identity
    auth_type = password

When retrieving vim password:
We use the tacker service tenant configured in the tacker.conf and
**secret_uuid** to get the fernet key from barbican, and decode
with **password** using fernet.

When deleting a vim:
We use the tacker service tenant configured in the tacker.conf to delete
the secret by the **secret_uuid** in vim db from barbican.


How to test
-----------

We need enable barbican in devstack localrc file:

.. code-block:: bash

    enable_plugin barbican https://opendev.org/openstack/barbican
    enable_plugin tacker https://opendev.org/openstack/tacker
    USE_BARBICAN=True

.. note::

    Please make sure the barbican plugin is enabled before tacker plugin.
    We set USE_BARBICAN=True to use barbican .

Create a vim and verify it works:

.. code-block:: bash

   $ . openrc-admin.sh
   $ openstack project create test
   $ openstack user create --password a test
   $ openstack role add --project test --user test admin

   $ cat vim-test.yaml
   auth_url: 'http://127.0.0.1/identity'
   username: 'test'
   password: 'Passw0rd'
   project_name: 'test'
   project_domain_name: 'Default'
   user_domain_name: 'Default'

   $ cat openrc-test.sh
   export LC_ALL='en_US.UTF-8'
   export OS_NO_CACHE='true'
   export OS_USERNAME=test
   export OS_PASSWORD=Passw0rd
   export OS_PROJECT_NAME=test
   export OS_USER_DOMAIN_NAME=Default
   export OS_PROJECT_DOMAIN_NAME=Default
   export OS_AUTH_URL=http://127.0.0.1/identity
   export OS_IDENTITY_API_VERSION=3
   export OS_IMAGE_API_VERSION=2
   export OS_NETWORK_API_VERSION=2

   $ source openrc-test.sh
   $ openstack secret list

   $ openstack vim register --config-file vim-test.yaml vim-test
   Created a new vim:
   +----------------+---------------------------------------------------------+
   | Field          | Value                                                   |
   +----------------+---------------------------------------------------------+
   | auth_cred      | {"username": "test", "password": "***", "project_name": |
   |                | "test", "user_domain_name": "Default", "key_type":      |
   |                | "barbican_key", "secret_uuid": "***", "auth_url":       |
   |                | "http://127.0.0.1/identity/v3", "project_id": null,     |
   |                | "project_domain_name": "Default"}                       |
   | auth_url       | http://127.0.0.1/identity/v3                            |
   | created_at     | 2017-06-20 14:56:05.622612                              |
   | description    |                                                         |
   | id             | 7c0b73c7-554b-46d3-a35c-c368019716a0                    |
   | is_default     | False                                                   |
   | name           | vim-test                                                |
   | placement_attr | {"regions": ["RegionOne"]}                              |
   | status         | REACHABLE                                               |
   | tenant_id      | 28a525feaf5e4d05b4ab9f7090837964                        |
   | type           | openstack                                               |
   | updated_at     |                                                         |
   | vim_project    | {"name": "test", "project_domain_name": "Default"}      |
   +----------------+---------------------------------------------------------+

   $ openstack secret list
   +-------------------------------------------+------+---------------------------+--------+-------------------------------------------+-----------+------------+-------------+------+------------+
   | Secret href                               | Name | Created                   | Status | Content types                             | Algorithm | Bit length | Secret type | Mode | Expiration |
   +-------------------------------------------+------+---------------------------+--------+-------------------------------------------+-----------+------------+-------------+------+------------+
   | http://127.0.0.1:9311/v1/secrets/d379f561 | None | 2017-06-20T14:56:06+00:00 | ACTIVE | {u'default': u'application/octet-stream'} | None      | None       | opaque      | None | None       |
   | -7073-40ea-822d-9d7bcb594e1a              |      |                           |        |                                           |           |            |             |      |            |
   +-------------------------------------------+------+---------------------------+--------+-------------------------------------------+-----------+------------+-------------+------+------------+

We can found that the **key_type** in auth_cred is **barbican_key**,
the **secret_uuid** exists with masked value, and the fernet key is
saved in barbican as a secret.

Now we create a vnf to verify it works:

.. code-block:: bash

   $ openstack vnf create --vnfd-template vnfd-sample.yaml \
     --vim-name vim-test --vim-region-name RegionOne vnf-test
   Created a new vnf:
   +----------------+-------------------------------------------------------+
   | Field          | Value                                                 |
   +----------------+-------------------------------------------------------+
   | created_at     | 2017-06-20 15:08:43.267694                            |
   | description    | Demo example                                          |
   | error_reason   |                                                       |
   | id             | 71d3eef7-6b53-4495-b210-78786cb28ba4                  |
   | instance_id    | 08d0ce6f-69bc-4ff0-87b0-52686a01ce3e                  |
   | mgmt_ip_address|                                                       |
   | name           | vnf-test                                              |
   | placement_attr | {"region_name": "RegionOne", "vim_name": "vim-test"}  |
   | status         | PENDING_CREATE                                        |
   | tenant_id      | 28a525feaf5e4d05b4ab9f7090837964                      |
   | updated_at     |                                                       |
   | vim_id         | 0d1e1cc4-445d-41bd-b3e9-739acb987231                  |
   | vnfd_id        | dc68ccfd-fd7c-4ef6-8fed-f097d036c722                  |
   +----------------+-------------------------------------------------------+

   $ openstack vnf delete vnf-test

We can found that vnf create successfully.

Now we delete the vim to verify the secret can be deleted.

.. code-block:: bash

   $ openstack vim delete vim-test
   All vim(s) deleted successfully
   $ openstack secret list

We can found that the secret is deleted from barbican.
