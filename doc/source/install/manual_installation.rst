..
      Copyright 2015-2016 Brocade Communications Systems Inc
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.


===================
Manual Installation
===================

This document describes how to install and run Tacker manually on the
controller node.

Pre-requisites
==============

1). Ensure that OpenStack components Keystone, Glance, Nova, Neutron, Heat and
Horizon are installed. Refer http://docs.openstack.org/ for installation of
OpenStack on different Operating Systems.

2). Create client environment scripts "admin-openrc.sh" and "demo-openrc.sh"
for the admin and demo projects. Sample instructions for Ubuntu can be found
at link below:

http://docs.openstack.org/newton/install-guide-ubuntu/keystone-openrc.html#creating-the-scripts

3). Ensure that the below required packages are installed on the system.

.. code-block:: console

   sudo apt-get install python-pip git

..

4). Ensure entry for extensions drivers in ml2_conf.ini. Restart neutron
services after the below entry has been added.

.. code-block:: console

   [ml2]
   extension_drivers = port_security

..

5). Modify heat's policy.json file under /etc/heat/policy.json file to allow
users in non-admin projects with 'admin' roles to create flavors.

.. code-block:: ini

   "resource_types:OS::Nova::Flavor": "role:admin"
..

Installing Tacker server
========================

.. note::

   The paths we are using for configuration files in these steps are with reference to
   Ubuntu Operating System. The paths may vary for other Operating Systems.

1). Create MySQL database and user.

.. code-block:: console

   mysql -uroot -p
   CREATE DATABASE tacker;
   GRANT ALL PRIVILEGES ON tacker.* TO 'tacker'@'localhost' \
       IDENTIFIED BY '<TACKERDB_PASSWORD>';
   GRANT ALL PRIVILEGES ON tacker.* TO 'tacker'@'%' \
       IDENTIFIED BY '<TACKERDB_PASSWORD>';
   exit;
..

.. note::

   Replace ``TACKERDB_PASSWORD`` with your password.

2). Create users, roles and endpoints:

a). Source the admin credentials to gain access to admin-only CLI commands:

.. code-block:: console

   . admin-openrc.sh
..

b). Create tacker user with admin privileges.

.. note::

   Project_name can be "service" or "services" depending on your
   OpenStack distribution.
..

.. code-block:: console

   openstack user create --domain default --password <PASSWORD> tacker
   openstack role add --project service --user tacker admin
..

c). Create tacker service.

.. code-block:: console

   openstack service create --name tacker \
       --description "Tacker Project" nfv-orchestration
..

d). Provide an endpoint to tacker service.

If you are using keystone v3 then,

.. code-block:: console

   openstack endpoint create --region RegionOne nfv-orchestration \
              public http://<TACKER_NODE_IP>:9890/
   openstack endpoint create --region RegionOne nfv-orchestration \
              internal http://<TACKER_NODE_IP>:9890/
   openstack endpoint create --region RegionOne nfv-orchestration \
              admin http://<TACKER_NODE_IP>:9890/
..

If you are using keystone v2 then,

.. code-block:: console

   openstack endpoint create --region RegionOne \
        --publicurl 'http://<TACKER_NODE_IP>:9890/' \
        --adminurl 'http://<TACKER_NODE_IP>:9890/' \
        --internalurl 'http://<TACKER_NODE_IP>:9890/' <SERVICE-ID>
..

3). Clone tacker repository.

.. code-block:: console

   git clone https://github.com/openstack/tacker
..

4). Install all requirements.

.. code-block:: console

   cd tacker
   sudo pip install -r requirements.txt

..

.. note::

   If OpenStack components mentioned in pre-requisites section have been
   installed, the below command would be sufficient.

.. code-block:: console

   cd tacker
   sudo pip install tosca-parser

..


5). Install tacker.

.. code-block:: console

   sudo python setup.py install
..

..

6). Create 'tacker' directory in '/var/log'.

.. code-block:: console

   sudo mkdir /var/log/tacker

..

7). Generate the tacker.conf.sample using tools/generate_config_file_sample.sh
    or 'tox -e config-gen' command and rename it to tacker.conf. Then edit it
    to ensure the below entries:

.. note::

   project_name can be "service" or "services" depending on your
   OpenStack distribution in the keystone_authtoken section.
..

.. code-block:: ini

   [DEFAULT]
   auth_strategy = keystone
   policy_file = /usr/local/etc/tacker/policy.json
   debug = True
   use_syslog = False
   bind_host = <TACKER_NODE_IP>
   bind_port = 9890
   service_plugins = nfvo,vnfm

   state_path = /var/lib/tacker
   ...

   [nfvo]
   vim_drivers = openstack

   [keystone_authtoken]
   memcached_servers = 11211
   region_name = RegionOne
   auth_type = password
   project_domain_name = <DOMAIN_NAME>
   user_domain_name = <DOMAIN_NAME>
   username = <TACKER_USER_NAME>
   project_name = service
   password = <TACKER_SERVICE_USER_PASSWORD>
   auth_url = http://<KEYSTONE_IP>:35357
   auth_uri = http://<KEYSTONE_IP>:5000
   ...

   [agent]
   root_helper = sudo /usr/local/bin/tacker-rootwrap /usr/local/etc/tacker/rootwrap.conf
   ...

   [database]
   connection = mysql://tacker:<TACKERDB_PASSWORD>@<MYSQL_IP>:3306/tacker?charset=utf8
   ...

   [tacker]
   monitor_driver = ping,http_ping

..

8). Populate Tacker database:

.. code-block:: console

   /usr/local/bin/tacker-db-manage --config-file /usr/local/etc/tacker/tacker.conf upgrade head

..


Install Tacker client
=====================

1). Clone tacker-client repository.

.. code-block:: console

   cd ~/
   git clone https://github.com/openstack/python-tackerclient
..

2). Install tacker-client.

.. code-block:: console

   cd python-tackerclient
   sudo python setup.py install
..

Install Tacker horizon
======================


1). Clone tacker-horizon repository.

.. code-block:: console

   cd ~/
   git clone https://github.com/openstack/tacker-horizon
..

2). Install horizon module.

.. code-block:: console

   cd tacker-horizon
   sudo python setup.py install
..

3). Enable tacker horizon in dashboard.

.. code-block:: console

   sudo cp tacker_horizon/enabled/* \
       /usr/share/openstack-dashboard/openstack_dashboard/enabled/
..

4). Restart Apache server.

.. code-block:: console

   sudo service apache2 restart
..

Starting Tacker server
======================

1).Open a new console and launch tacker-server. A separate terminal is
required because the console will be locked by a running process.

.. code-block:: console

   sudo python /usr/local/bin/tacker-server \
       --config-file /usr/local/etc/tacker/tacker.conf \
       --log-file /var/log/tacker/tacker.log
..

Registering default VIM
=======================

1.) Register the VIM that will be used as a default VIM for VNF deployments.
This will be required when the optional argument --vim-id is not provided by
the user during vnf-create.

.. code-block:: console

   tacker vim-register --is-default --config-file config.yaml \
          --description <Default VIM description> <Default VIM Name>
..

2.) The config.yaml will contain VIM specific parameters as below:

.. code-block:: ini

   auth_url: http://<keystone_public_endpoint_url>:5000
   username: <Tacker service username>
   password: <Tacker service password>
   project_name: <project_name>

Add following parameters to config.yaml if VIM is using keystone v3:

.. code-block:: ini

   project_domain_name: <domain_name>
   user_domain_name: <domain_name>

.. note::

   Here username must point to the user having 'admin' and 'advsvc' role on the
   project that will be used for deploying VNFs.
