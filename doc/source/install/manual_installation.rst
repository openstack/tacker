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
controller node

Pre-requisites
==============

1). Ensure that OpenStack components Keystone, Glance, Nova, Neutron, Heat and
Horizon are installed. Refer http://docs.openstack.org/ for installation of
OpenStack on different Operating Systems.

2). Create client environment scripts "admin-openrc.sh" and "demo-openrc.sh"
for the admin and demo projects. Sample instructions for Ubuntu can be found
at link below:
http://docs.openstack.org/liberty/install-guide-ubuntu/keystone-openrc.html#creating-the-scripts

3).Ensure that the below required packages are installed on the system.

.. code-block:: console

    sudo apt-get install python-pip git

..

4). Ensure entry for extensions drivers in ml2_conf.ini. Restart neutron
services after the below entry has been added.

.. code-block:: console

    [ml2]
    extension_drivers = port_security

..

Installing Tacker server
========================

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

2). Create users, roles and endpoints

a). Source the admin credentials to gain access to admin-only CLI commands:

.. code-block:: console

    source admin-openrc.sh
..

b). Create tacker user with admin privileges.

.. note::

        Project_name can be "service" or "services" depending on your
        OpenStack distribution.
..

.. code-block:: console

    openstack user create --password <PASSWORD> tacker
    openstack role add --project services --user tacker admin
..

c). Create tacker service.

.. code-block:: console

    openstack service create --name tacker --description "Tacker Project" nfv
    -orchestration
..

d). Provide an endpoint to tacker service.

.. code-block:: console

    openstack endpoint create --region RegionOne \
        --publicurl 'http://<TACKER_NODE_IP>:8888/' \
        --adminurl 'http://<TACKER_NODE_IP>:8888/' \
        --internalurl 'http://<TACKER_NODE_IP>:8888/' <SERVICE-ID>
..


3). Clone tacker repository.

.. code-block:: console

    git clone https://github.com/openstack/tacker
..

4). Install all requirements.

.. code-block:: console

    cd tacker
    sudo  pip install -r requirements.txt

..

.. note::

        If OpenStack components mentioned in pre-requisites section have been
        installed, the below command would be sufficient.

.. code-block:: console

    cd tacker
    sudo  pip install tosca-parser

..


5). Install tacker.

.. code-block:: console

    sudo python setup.py install
..

..

6). Create 'tacker' directory in '/var/log'

.. note::

        The above referenced path '/var/log' is for Ubuntu and may be
        different for other Operating Systems.

.. code-block:: console

    sudo mkdir /var/log/tacker

..

7). Edit tacker.conf to ensure the below entries:

.. note::

        In Ubuntu 14.04, the tacker.conf is located at /usr/local/etc/tacker/
        and below ini sample is for Ubuntu and directory paths referred in
        ini may be different for other Operating Systems.

.. note::

        Project_name can be "service" or "services" depending on your
        OpenStack distribution in the keystone_authtoken section.
..
.. code-block:: ini

    [DEFAULT]
    auth_strategy = keystone
    policy_file = /usr/local/etc/tacker/policy.json
    debug = True
    verbose = True
    use_syslog = False
    state_path = /var/lib/tacker
    ...
    [keystone_authtoken]
    project_name = service
    password = <TACKER_SERVICE_USER_PASSWORD>
    auth_url = http://<KEYSTONE_IP>:35357
    #identity_uri = http://<KEYSTONE_IP>:5000
    auth_uri = http://<KEYSTONE_IP>:5000
    ...
    [agent]
    root_helper = sudo /usr/local/bin/tacker-rootwrap /usr/local/etc/tacker/r
    ootwrap.conf
    ...
    [DATABASE]
    connection = mysql://tacker:<TACKERDB_PASSWORD>@<MYSQL_IP>:3306/tacker?ch
    arset=utf8
    ...
    [tacker_nova]
    password = <NOVA_SERVICE_USER_PASSWORD>
    auth_url = http://<NOVA_IP>:35357
    ...
    [tacker_heat]
    heat_uri = http://<HEAT_IP>:8004/v1
..

8). Populate Tacker database:

.. note::

       The below command is for Ubuntu Operating System

.. code-block:: console

    /usr/local/bin/tacker-db-manage --config-file /etc/tacker/tacker.conf upgrade head

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

.. note::

        The below destination path referred is for Ubuntu 14.04 and may
        change for other Operating Systems.

.. code-block:: console

    sudo cp openstack_dashboard_extensions/* /usr/share/openstack-dashboard/o
    penstack_dashboard/enabled/
..

4). Restart Apache server

.. code-block:: console

    sudo service apache2 restart
..

Starting Tacker server
======================

1).Open a new console and launch tacker-server. A separate terminal is
required because the console will be locked by a running process.

.. note::
        Ensure that ml2_conf.ini as per Step 4 from the pre-requisites
        section has been configured.

.. code-block:: console

    sudo python /usr/local/bin/tacker-server --config-file /usr/local/etc/tac
    cker/tacker.conf --log-file /var/log/tacker/tacker.log
..

Registering default VIM
=======================
1). Register the VIM that will be used as a default VIM for VNF deployments.
This will be required when the optional argument --vim-id is not provided by
the user during vnf-create.

.. code-block:: console

    tacker vim-register --config-file config.yaml --name <Default VIM name>
    --description <Default VIM description>
..

config.yaml will contain VIM specific parameters as below:

.. code-block:: ini

    auth_url: http://<keystone ip>:5000
    username: <username>
    password: <password>
    project_name: <project_name>

.. note::
   Here username must point to the user having 'admin' and 'advsvc' role on the
   project that will be used for deploying VNFs.

2). Add the VIM name registered in step 1 in /etc/tacker/tacker.conf under
[nfvo_vim] section:

.. code-block:: ini

   default_vim = <Default VIM Name>

3). Restart tacker server
