..
  Licensed under the Apache License, Version 2.0 (the "License"); you may
  not use this file except in compliance with the License. You may obtain
  a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
  License for the specific language governing permissions and limitations
  under the License.

.. _ref-multisite:

===================
Multisite VIM Usage
===================

A single Tacker controller node can be used to manage multiple OpenStack sites
without having the need to deploy Tacker server on each of these sites. Tacker
allows users to deploy VNFs in multiple OpenStack sites using the multisite VIM
feature. OpenStack versions starting from Kilo are supported with this feature.


Preparing the OpenStack site
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Create a new 'nfv' project and admin privileged 'nfv' user on the remote
   OpenStack site.
2. Create the required neutron networks for management, packet in and packet
   out networks that will be used by VNFs.

Register a new OpenStack VIM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To register a new OpenStack VIM inside Tacker.

::

 $ openstack vim register --description 'OpenStack Liberty' --config-file vim_config.yaml Site1
 Created a new vim:
 +----------------+----------------------------------------------------------------------------------------------------------------------------------------------------------+
 | Field          | Value                                                                                                                                                    |
 +----------------+----------------------------------------------------------------------------------------------------------------------------------------------------------+
 | auth_cred      | {"username": "nfv_user", "password": "***", "project_name": "nfv", "user_id": "", "user_domain_name": "default", "auth_url":                               |
 |                | "http://127.0.0.1/identity", "project_id": "", "project_domain_name": "default"}                                                                        |
 | auth_url       | http://127.0.0.1/identity                                                                                                                             |
 | description    | OpenStack Liberty                                                                                                                                        |
 | id             | 3f3c51c5-8bda-4bd3-adb3-5ae62eae65c3                                                                                                                     |
 | name           | Site1                                                                                                                                                    |
 | placement_attr | {"regions": ["RegionOne", "RegionTwo"]}                                                                                                                  |
 | tenant_id      | 8907bae480c0414d98c3519acbad1b06                                                                                                                         |
 | type           | openstack                                                                                                                                                |
 | vim_project    | {"id": "", "name": "nfv"}                                                                                                                                |
 +----------------+----------------------------------------------------------------------------------------------------------------------------------------------------------+

In the above command, config.yaml contains VIM specific parameters as below:

::

 auth_url: 'http://127.0.0.1/identity'
 username: 'nfv_user'
 password: 'devstack'
 project_name: 'nfv'

The parameter auth_url points to the keystone service authorization URL of the
remote OpenStack site.

.. note::

    In Keystone, port `5000` is enabled for authentication service [1]_, so the
    end users can use `auth_url: 'http://127.0.0.1:5000/v3` instead of
    `auth_url: 'http://127.0.0.1/identity'` as above mention.

Default VIM configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

The default vim needs to be registered. This is required when the optional
argument --vim-id is not provided during vnf creation. Refer to steps described
in `manual installation`_ to register default vim.

.. _manual installation: https://docs.openstack.org/tacker/latest/install/manual_installation.html#registering-default-vim


Onboard a VNFD
~~~~~~~~~~~~~~

::

 $ openstack vnf descriptor create --description "Openwrt VNFD" --vnfd-file vnfd1.yaml openwrt-vnfd1
 Created a new vnfd:
 +-----------------+--------------------------------------+
 | Field           | Value                                |
 +-----------------+--------------------------------------+
 | created_at      | 2018-06-20 05:37:57.589182           |
 | description     | Openwrt VNFD                         |
 | id              | c3cbf0c0-a492-49e3-9541-945e49e7ed7e |
 | name            | openwrt-vnfd1                        |
 | service_types   | vnfd                                 |
 | template_source | onboarded                            |
 | tenant_id       | a5346a4d3c464b4f8776ee2f4bfb86af     |
 | updated_at      |                                      |
 +-----------------+--------------------------------------+

Deploying a new VNF on registered VIM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 $ openstack vnf create --description 'Openwrt VNF on Site1' --vnfd-id c3cbf0c0-a492-49e3-9541-945e49e7ed7e --vim-name Site1 openwrt_VNF
 Created a new vnf:
 +----------------+--------------------------------------+
 | Field          | Value                                |
 +----------------+--------------------------------------+
 | description    | Openwrt tosca template               |
 | id             | 159ed8a5-a5a7-4f7a-be50-0f5f86603e3a |
 | instance_id    | 7b4ab046-d977-4781-9f0c-1ee9dcce01c6 |
 | mgmt_ip_address|                                      |
 | name           | openwrt_VNF                          |
 | placement_attr | {"vim_name": "Site1"}                |
 | status         | PENDING_CREATE                       |
 | tenant_id      | 8907bae480c0414d98c3519acbad1b06     |
 | vim_id         | 3f3c51c5-8bda-4bd3-adb3-5ae62eae65c3 |
 | vnfd_id        | c3cbf0c0-a492-49e3-9541-945e49e7ed7e |
 +----------------+--------------------------------------+

The --vim-id/--vim-name argument is optional during vnf creation. If
--vim-id/--vim-name is not specified, the default vim will
be used to deploy VNF on the default site. We can create default vim
by specifying --is-default option with vim-register command.

User can optionally provide --vim-region-name during vnf creation to deploy the
VNF in a specify region within that VIM.

Updating a VIM
~~~~~~~~~~~~~~

Tacker allows for updating VIM authorization parameters such as 'username',
'password' and 'project_name' and 'ids' after it has been registered. To update
'username' and password' for a given VIM user within Tacker:

::

 $ openstack vim set VIM0 --config-file update.yaml

update.yaml in above command will contain:

::

 username: 'new_user'
 password: 'new_pw'

Note that 'auth_url' parameter of a VIM is not allowed to be updated as
'auth_url' uniquely identifies a given 'vim' resource.


Deleting a VIM
~~~~~~~~~~~~~~
To delete a VIM :

::

 $ openstack vim delete VIM1
 Deleted vim: VIM1

Features
~~~~~~~~
* Tacker support multi-tenancy, that means a VIM registered by one tenant can
  not be shared with other.
* Pluggable driver module framework allowing Tacker to interact with multiple
  VIM types.
* Compatible for OpenStack versions starting from Kilo.
* Supports keystone versions v2.0 and v3.

Limitations
~~~~~~~~~~~
* Fernet keys for password encryption and decryption is stored on file systems.
  This is a limitation when multiple servers are serving behind a load balancer
  server and the keys need to be synced across tacker server systems.

References
==========

.. [1] https://docs.openstack.org/keystoneauth/latest/using-sessions.html#sessions-for-users
