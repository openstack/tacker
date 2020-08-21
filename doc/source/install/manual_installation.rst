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

.. note::

   User is supposed to install on Ubuntu. Some examples are invalid on other
   distirbutions. For example, you should replace ``/usr/local/bin/`` with
   ``/usr/bin/`` on CentOS.

Pre-requisites
--------------

#. Install required components.

   Ensure that OpenStack components, Keystone, Mistral, Barbican and
   Horizon are installed. Refer the list below for installation of
   these OpenStack projects on different Operating Systems.

   * https://docs.openstack.org/keystone/latest/install/index.html
   * https://docs.openstack.org/mistral/latest/admin/install/index.html
   * https://docs.openstack.org/barbican/latest/install/install.html
   * https://docs.openstack.org/horizon/latest/install/index.html

#. Create ``admin-openrc.sh`` for env variables.

   .. code-block:: shell

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


Installing Tacker Server
------------------------

.. note::

   The ``<branch_name>`` in command examples is replaced with specific branch
   name, such as ``stable/ussuri``.

#. Create MySQL database and user.

   .. code-block:: console

       $ mysql -uroot -p

   Create database ``tacker`` and grant provileges for ``tacker`` user with
   password ``<TACKERDB_PASSWORD>`` on all tables.

   .. code-block::

       CREATE DATABASE tacker;
       GRANT ALL PRIVILEGES ON tacker.* TO 'tacker'@'localhost' \
           IDENTIFIED BY '<TACKERDB_PASSWORD>';
       GRANT ALL PRIVILEGES ON tacker.* TO 'tacker'@'%' \
           IDENTIFIED BY '<TACKERDB_PASSWORD>';
       exit;

#. Create OpenStack user, role and endpoint.

   #. Set admin credentials to gain access to admin-only CLI commands.

      .. code-block:: console

         $ . admin-openrc.sh

   #. Create ``tacker`` user with admin privileges.

      .. code-block:: console

         $ openstack user create --domain default --password <PASSWORD> tacker
         $ openstack role add --project service --user tacker admin

      .. note::

          Project name can be ``service`` or ``services`` depending on your
          OpenStack distribution.

   #. Create ``tacker`` service.

      .. code-block:: console

         $ openstack service create --name tacker \
             --description "Tacker Project" nfv-orchestration

   #. Provide an endpoint to tacker service.

      For keystone v3:

      .. code-block:: console

         $ openstack endpoint create --region RegionOne nfv-orchestration \
                    public http://<TACKER_NODE_IP>:9890/
         $ openstack endpoint create --region RegionOne nfv-orchestration \
                    internal http://<TACKER_NODE_IP>:9890/
         $ openstack endpoint create --region RegionOne nfv-orchestration \
                    admin http://<TACKER_NODE_IP>:9890/

      Or keystone v2:

      .. code-block:: console

         $ openstack endpoint create --region RegionOne \
              --publicurl 'http://<TACKER_NODE_IP>:9890/' \
              --adminurl 'http://<TACKER_NODE_IP>:9890/' \
              --internalurl 'http://<TACKER_NODE_IP>:9890/' <SERVICE-ID>

#. Clone tacker repository.

   You can use ``-b`` for specific release optionally.

   .. code-block:: console

      $ cd ${HOME}
      $ git clone https://opendev.org/openstack/tacker.git -b <branch_name>

#. Install required packages and tacker itself.

   .. code-block:: console

      $ cd ${HOME}/tacker
      $ sudo pip3 install -r requirements.txt
      $ sudo python3 setup.py install

#. Create directories for tacker.

   Directories log, VNF packages and csar files are required.

   .. code-block:: console

      $ sudo mkdir -p /var/log/tacker \
          /var/lib/tacker/vnfpackages \
          /var/lib/tacker/csar_files

   .. note::

      In case of multi node deployment, we recommend to configure
      ``/var/lib/tacker/csar_files`` on a shared storage.

#. Generate the ``tacker.conf.sample`` using
   ``tools/generate_config_file_sample.sh`` or ``tox -e config-gen`` command.
   Rename the ``tacker.conf.sample`` file at ``etc/tacker/`` to
   ``tacker.conf``. Then edit it to ensure the below entries:

   .. note::

      Ignore any warnings generated while using the
      "generate_config_file_sample.sh".

   .. note::

      project_name can be "service" or "services" depending on your
      OpenStack distribution in the keystone_authtoken section.

   .. note::

      The path of tacker-rootwrap varies according to the operating system,
      e.g. it is /usr/bin/tacker-rootwrap for CentOS, therefore the configuration for
      [agent] should be like:

      .. code-block:: ini

         [agent]
         root_helper = sudo /usr/bin/tacker-rootwrap /etc/tacker/rootwrap.conf

   .. code-block:: ini

      [DEFAULT]
      auth_strategy = keystone
      policy_file = /etc/tacker/policy.json
      debug = True
      use_syslog = False
      bind_host = <TACKER_NODE_IP>
      bind_port = 9890
      service_plugins = nfvo,vnfm

      state_path = /var/lib/tacker
      transport_url = rabbit://<RABBIT_USERID>:<RABBIT_PASSWORD>@<TACKER_NODE_IP>:5672/
      ...

      [nfvo_vim]
      vim_drivers = openstack

      [keystone_authtoken]
      memcached_servers = <TACKER_NODE_IP>:11211
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
      root_helper = sudo /usr/local/bin/tacker-rootwrap /etc/tacker/rootwrap.conf
      ...

      [database]
      connection = mysql+pymysql://tacker:<TACKERDB_PASSWORD>@<MYSQL_IP>:3306/tacker?charset=utf8
      ...

      [tacker]
      monitor_driver = ping,http_ping

#. Copy the ``tacker.conf`` to ``/etc/tacker/`` directory.

   .. code-block:: console

      $ sudo cp etc/tacker/tacker.conf /etc/tacker/

#. Populate Tacker database.

   .. code-block:: console

      $ /usr/local/bin/tacker-db-manage \
          --config-file /etc/tacker/tacker.conf \
          upgrade head

#. To make tacker be controlled from systemd, copy ``tacker.service`` and
   ``tacker-conductor.service`` file to ``/etc/systemd/system/`` directory,
   and restart ``systemctl`` daemon.

   .. code-block:: console

      $ sudo cp etc/systemd/system/tacker.service /etc/systemd/system/
      $ sudo cp etc/systemd/system/tacker-conductor.service /etc/systemd/system/
      $ sudo systemctl daemon-reload

Install Tacker Client
---------------------

#. Clone ``tacker-client`` repository.

   .. code-block:: console

      $ cd ~/
      $ git clone https://opendev.org/openstack/python-tackerclient.git -b <branch_name>

#. Install ``tacker-client``.

   .. code-block:: console

      $ cd ${HOME}/python-tackerclient
      $ sudo python3 setup.py install

Install Tacker horizon
----------------------

#. Clone ``tacker-horizon`` repository.

   .. code-block:: console

      $ cd ~/
      $ git clone https://opendev.org/openstack/tacker-horizon.git -b <branch_name>

#. Install horizon module.

   .. code-block:: console

      $ cd ${HOME}/tacker-horizon
      $ sudo python3 setup.py install

#. Enable tacker horizon in dashboard.

   .. code-block:: console

      $ sudo cp tacker_horizon/enabled/* \
          /usr/share/openstack-dashboard/openstack_dashboard/enabled/

#. Restart Apache server.

   .. code-block:: console

      $ sudo service apache2 restart

Starting Tacker server
----------------------

Open a new console and launch ``tacker-server``. A separate terminal is
required because the console will be locked by a running process.

.. code-block:: console

   $ sudo systemctl start tacker.service

Starting Tacker conductor
-------------------------

Open a new console and launch tacker-conductor. A separate terminal is
required because the console will be locked by a running process.

.. code-block:: console

   $ sudo systemctl start tacker-conductor.service
