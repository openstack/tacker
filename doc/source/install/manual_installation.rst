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

This document describes how to install and run Tacker manually.

Pre-requisites
==============

1). Ensure that OpenStack components Keystone, Mistral, Barbican and
Horizon are installed. Refer the list below for installation of
these OpenStack projects on different Operating Systems.

* https://docs.openstack.org/keystone/latest/install/index.html
* https://docs.openstack.org/mistral/latest/install/index.html
* https://docs.openstack.org/barbican/latest/install/install.html
* https://docs.openstack.org/horizon/latest/install/index.html

2). one admin-openrc.sh file is generated. one sample admin-openrc.sh file
is like the below:

.. code-block:: ini

    export OS_PROJECT_DOMAIN_NAME=Default
    export OS_USER_DOMAIN_NAME=Default
    export OS_PROJECT_NAME=admin
    export OS_TENANT_NAME=admin
    export OS_USERNAME=admin
    export OS_PASSWORD=KTskN5eUMTpeHLKorRcZBBbH0AM96wdvgQhwENxY
    export OS_AUTH_URL=http://localhost:5000/identity
    export OS_INTERFACE=internal
    export OS_IDENTITY_API_VERSION=3
    export OS_REGION_NAME=RegionOne


Installing Tacker server
========================

.. note::

   The paths we are using for configuration files in these steps are with reference to
   Ubuntu Operating System. The paths may vary for other Operating Systems.

   The branch_name which is used in commands, specify the branch_name as
   "stable/<branch>" for any stable branch installation.
   For eg: stable/ocata, stable/newton. If unspecified the default will be
   "master" branch.


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

   cd ~/
   git clone https://github.com/openstack/tacker -b <branch_name>
..

4). Install all requirements.

.. code-block:: console

   cd tacker
   sudo pip install -r requirements.txt
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
    or 'tox -e config-gen' command. Rename the "tacker.conf.sample" file at
    "etc/tacker/" to tacker.conf. Then edit it to ensure the below entries:

.. note::

   Ignore any warnings generated while using the
   "generate_config_file_sample.sh".

..

.. note::

   project_name can be "service" or "services" depending on your
   OpenStack distribution in the keystone_authtoken section.
..

.. note::

   The path of tacker-rootwrap varies according to the operating system,
   e.g. it is /usr/bin/tacker-rootwrap for CentOS, therefore the configuration for
   [agent] should be like:

   .. code-block:: ini

      [agent]
      root_helper = sudo /usr/bin/tacker-rootwrap /usr/local/etc/tacker/rootwrap.conf
   ..
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

   [nfvo_vim]
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
   auth_url = http://<KEYSTONE_IP>:5000
   www_authenticate_uri = http://<KEYSTONE_IP>:5000
   ...

   [agent]
   root_helper = sudo /usr/local/bin/tacker-rootwrap /usr/local/etc/tacker/rootwrap.conf
   ...

   [database]
   connection = mysql+pymysql://tacker:<TACKERDB_PASSWORD>@<MYSQL_IP>:3306/tacker?charset=utf8
   ...

   [tacker]
   monitor_driver = ping,http_ping

..

8). Copy the tacker.conf file to "/usr/local/etc/tacker/" directory

.. code-block:: console

   sudo su
   cp etc/tacker/tacker.conf /usr/local/etc/tacker/

..

9). Populate Tacker database:

.. note::

   The path of tacker-db-manage varies according to the operating system,
   e.g. it is /usr/bin/tacker-bin-manage for CentOS

..

.. code-block:: console

   /usr/local/bin/tacker-db-manage --config-file /usr/local/etc/tacker/tacker.conf upgrade head

..

10). To support systemd, copy tacker.service and tacker-conductor.service file to
     "/etc/systemd/system/" directory, and restart systemctl daemon.

.. code-block:: console

   sudo su
   cp etc/systemd/system/tacker.service /etc/systemd/system/
   cp etc/systemd/system/tacker-conductor.service /etc/systemd/system/
   systemctl daemon-reload

..

.. note::

   Needs systemd support.
   By default Ubuntu16.04 onward is supported.
..


Install Tacker client
=====================

1). Clone tacker-client repository.

.. code-block:: console

   cd ~/
   git clone https://github.com/openstack/python-tackerclient -b <branch_name>
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
   git clone https://github.com/openstack/tacker-horizon -b <branch_name>
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

.. note::

   The path of tacker-server varies according to the operating system,
   e.g. it is /usr/bin/tacker-server for CentOS

..

.. code-block:: console

   sudo python /usr/local/bin/tacker-server \
       --config-file /usr/local/etc/tacker/tacker.conf \
       --log-file /var/log/tacker/tacker.log
..

Starting Tacker conductor
=========================

1).Open a new console and launch tacker-conductor. A separate terminal is
required because the console will be locked by a running process.

.. note::

   The path of tacker-conductor varies according to the operating system,
   e.g. it is /usr/bin/tacker-conductor for CentOS

..

.. code-block:: console

   sudo python /usr/local/bin/tacker-conductor \
       --config-file /usr/local/etc/tacker/tacker.conf \
       --log-file /var/log/tacker/tacker-conductor.log
..
