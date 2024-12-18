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

.. note::

  The content of this document has been confirmed to work
  using Tacker 2024.2 Dalmatian.


.. note::

  This installation guide contents are specific to Ubuntu.
  Some steps in this installation guide may be invalid for other distributions.


This document describes how to install and run Tacker manually.

Pre-requisites
--------------

#. Install required components.

   Ensure that all minimum OpenStack components that is required by Tacker
   such as Keystone and Barbican are installed. Refer the list below
   for installation of required OpenStack components.

   * `Aodh`_
   * `Barbican`_
   * `Cinder`_
   * `Glance`_
   * `Heat`_
   * `Keystone`_
   * `Neutron`_
   * `Nova`_
   * `Placement`_

#. Create ``admin-openrc`` for environment variables.

   .. code-block:: console

     $ vi admin-openrc
     export OS_PROJECT_DOMAIN_ID=default
     export OS_USER_DOMAIN_ID=default
     export OS_PROJECT_NAME=admin
     export OS_USERNAME=admin
     export OS_PASSWORD=<ADMIN_PASSWORD>
     export OS_AUTH_URL=http://<KEYSTONE_IP>/identity
     export OS_INTERFACE=public
     export OS_IDENTITY_API_VERSION=3
     export OS_REGION_NAME=RegionOne


Guide
-----

Installing Tacker Server
~~~~~~~~~~~~~~~~~~~~~~~~

.. note::

  If you would like to use PostgreSQL, please reference
  :doc:`/install/devstack` document.


#. Create MySQL database and user.

   .. code-block:: console

     $ mysql -uroot -p


   Create database ``tacker`` and grant privileges to ``tacker`` user with
   password ``<TACKERDB_PASSWORD>`` on all tables.

   .. code-block:: console

     mysql> CREATE DATABASE tacker;
     Query OK, 1 row affected (0.30 sec)

     mysql> CREATE USER 'tacker'@'localhost' IDENTIFIED BY '<TACKERDB_PASSWORD>';
     Query OK, 0 rows affected (0.58 sec)

     mysql> GRANT ALL PRIVILEGES ON tacker.* TO 'tacker'@'localhost';
     Query OK, 0 rows affected (0.18 sec)

     mysql> CREATE USER 'tacker'@'%' IDENTIFIED BY '<TACKERDB_PASSWORD>';
     Query OK, 0 rows affected (0.21 sec)

     mysql> GRANT ALL PRIVILEGES ON tacker.* TO 'tacker'@'%';
     Query OK, 0 rows affected (0.28 sec)

     mysql> FLUSH PRIVILEGES;
     Query OK, 0 rows affected (0.18 sec)

     mysql> exit;
     bye


#. Create OpenStack user, role and endpoint.

   #. Set admin credentials to gain access to admin-only CLI commands.

      .. code-block:: console

        $ source admin-openrc


   #. Create ``tacker`` user and set admin role of ``service`` project.

      .. note::

        Project name can be ``service`` or ``services`` depending on your
        OpenStack distribution.


      .. code-block:: console

        $ openstack user create --domain default \
        --password <TACKER_SERVICE_USER_PASSWORD> tacker
        +---------------------+----------------------------------+
        | Field               | Value                            |
        +---------------------+----------------------------------+
        | default_project_id  | None                             |
        | domain_id           | default                          |
        | email               | None                             |
        | enabled             | True                             |
        | id                  | 60c2c54a22db42e2936dc45704760067 |
        | name                | tacker                           |
        | description         | None                             |
        | password_expires_at | None                             |
        +---------------------+----------------------------------+
        $ openstack role add --project service --user tacker admin


   #. Create ``tacker`` service.

      .. code-block:: console

        $ openstack service create --name tacker \
        --description "Tacker Project" nfv-orchestration
        +-------------+----------------------------------+
        | Field       | Value                            |
        +-------------+----------------------------------+
        | id          | 88c795ad82da450eb642747efabb6594 |
        | name        | tacker                           |
        | type        | nfv-orchestration                |
        | enabled     | True                             |
        | description | Tacker Project                   |
        +-------------+----------------------------------+


   #. Provide an endpoint to ``tacker`` service.

      .. code-block:: console

        $ openstack endpoint create --region RegionOne nfv-orchestration \
        public http://<TACKER_NODE_IP>:9890/
        +--------------+----------------------------------+
        | Field        | Value                            |
        +--------------+----------------------------------+
        | enabled      | True                             |
        | id           | 94b7c6175cdd4f51a26bb61676e9afea |
        | interface    | public                           |
        | region       | RegionOne                        |
        | region_id    | RegionOne                        |
        | service_id   | 644e7c170eac450f90cddc9ac3c6a6b1 |
        | service_name | tacker                           |
        | service_type | nfv-orchestration                |
        | url          | http://<TACKER_NODE_IP>:9890     |
        +--------------+----------------------------------+
        $ openstack endpoint create --region RegionOne nfv-orchestration \
        internal http://<TACKER_NODE_IP>:9890/
        +--------------+----------------------------------+
        | Field        | Value                            |
        +--------------+----------------------------------+
        | enabled      | True                             |
        | id           | 8c9ede5c124a4afb9cc9da12486538cb |
        | interface    | internal                         |
        | region       | RegionOne                        |
        | region_id    | RegionOne                        |
        | service_id   | 644e7c170eac450f90cddc9ac3c6a6b1 |
        | service_name | tacker                           |
        | service_type | nfv-orchestration                |
        | url          | http://<TACKER_NODE_IP>:9890     |
        +--------------+----------------------------------+
        $ openstack endpoint create --region RegionOne nfv-orchestration \
        admin http://<TACKER_NODE_IP>:9890/
        +--------------+----------------------------------+
        | Field        | Value                            |
        +--------------+----------------------------------+
        | enabled      | True                             |
        | id           | 519c22404027446cba4bd9399f72cc54 |
        | interface    | admin                            |
        | region       | RegionOne                        |
        | region_id    | RegionOne                        |
        | service_id   | 644e7c170eac450f90cddc9ac3c6a6b1 |
        | service_name | tacker                           |
        | service_type | nfv-orchestration                |
        | url          | http://<TACKER_NODE_IP>:9890     |
        +--------------+----------------------------------+


#. Clone Tacker repository.

   .. note::

     You should install Tacker with the user that you installed the other
     Openstack components. Make sure to change the user before Installing.
     If you had specific python environment for openstack components, make sure
     to change python environment, too.


   .. note::

     Replace the ``<branch_name>`` in command with specific branch name, such
     as ``stable/2024.2``.


   .. code-block:: console

     $ cd ~
     $ git clone https://opendev.org/openstack/tacker.git -b <branch_name>


#. Install Tacker server.

   .. code-block:: console

     $ pip3 install ./tacker


#. Create directories for Tacker.

   Directories for storing logs and extracted CSAR files are required.

   .. note::

     In case of multi node deployment, ``csar_files`` directory should
     be configured on a shared storage.


   .. code-block:: console

     $ mkdir -p log/tacker \
     data/tacker/vnfpackages \
     data/tacker/csar_files


#. Generate the sample Tacker configuration file and edit as necessary.

   .. note::

     You can reference how to generate sample Tacker configuration file also in
     `README of etc/tacker`_.


   .. note::

     Ignore any warnings generated while using the
     ``generate_config_file_sample.sh``.


   .. code-block:: console

     $ cd tacker/
     $ bash tools/generate_config_file_sample.sh


   .. note::

     The path of ``tacker-rootwrap`` varies according to the operating system.
     You can find the path of ``tacker-rootwrap`` by the following command.

     .. code-block:: ini

       $ which tacker-rootwrap


   Minimum configurations shown below should be in Tacker configuration file.

   .. code-block:: console

      $ sudo vi etc/tacker/tacker.conf.sample

      [DEFAULT]
      auth_strategy = keystone
      debug = True
      use_syslog = False
      log_dir = <HOME_DIR>/log/tacker
      state_path = <HOME_DIR>/data/tacker
      transport_url = rabbit://<RABBIT_USERID>:<RABBIT_PASSWORD>@<TACKER_NODE_IP>:5672/
      ...

      [keystone_authtoken]
      memcached_servers = <TACKER_NODE_IP>:11211
      region_name = RegionOne
      project_domain_name = Default
      project_name = service
      user_domain_name = Default
      password = <TACKER_SERVICE_USER_PASSWORD>
      username = tacker
      auth_url = http://<KEYSTONE_IP>/identity
      interface = public
      auth_type = password
      ...

      [glance_store]
      default_backend = file
      filesystem_store_datadir = <HOME_DIR>/data/tacker/csar_files
      ...

      [vnf_package]
      vnf_package_csar_path = <HOME_DIR>/data/tacker/vnfpackages
      ...

      [agent]
      root_helper = sudo <PATH_TO_TACKER_ROOTWRAP>/tacker-rootwrap /etc/tacker/rootwrap.conf
      ...

      [database]
      connection = mysql+pymysql://tacker:<TACKERDB_PASSWORD>@<MYSQL_IP>:3306/tacker?charset=utf8


#. Setting rootwrap for Tacker.

   .. code-block:: console

     $ echo "$USER ALL=(root) NOPASSWD: $(which tacker-rootwrap) \
     /etc/tacker/rootwrap.conf *" > temp_file
     $ chmod 0440 temp_file
     $ sudo chown root:root temp_file
     $ sudo mv temp_file /etc/sudoers.d/tacker-rootwrap


#. Create the ``/etc/tacker/`` directory and copy the contents of
   ``etc/tacker`` to created directory.

   .. code-block:: console

     $ sudo install -d -o $USER /etc/tacker
     $ cp etc/tacker/tacker.conf.sample /etc/tacker/tacker.conf
     $ cp etc/tacker/api-paste.ini /etc/tacker/
     $ cp etc/tacker/rootwrap.conf /etc/tacker/
     $ cp -r etc/tacker/rootwrap.d/ /etc/tacker/
     $ cp etc/tacker/prometheus-plugin.yaml /etc/tacker/


#. Populate Tacker database.

   .. code-block:: console

     $ tacker-db-manage --config-file /etc/tacker/tacker.conf upgrade head


#. To make Tacker be controlled from systemd, edit and copy ``tacker.service``
   and ``tacker-conductor.service`` file to ``/etc/systemd/system/`` directory,
   and restart ``systemctl`` daemon. Before copying to system folder, be sure
   to add user used to install Tacker to service user and be sure to change the
   path of Tacker-server and Tacker-conductor to correct path.

   .. code-block:: console

     $ sed -i "/^\[Service\]/a User = $USER" \
     etc/systemd/system/tacker.service
     $ sed -i "s|/usr/local/bin/tacker-server|$(which tacker-server)|g" \
     etc/systemd/system/tacker.service
     $ sudo cp etc/systemd/system/tacker.service /etc/systemd/system/

     $ sed -i "/^\[Service\]/a User = $USER" \
     etc/systemd/system/tacker-conductor.service
     $ sed -i "s|/usr/local/bin/tacker-conductor|$(which tacker-conductor)|g" \
     etc/systemd/system/tacker-conductor.service
     $ sudo cp etc/systemd/system/tacker-conductor.service /etc/systemd/system/

     $ sudo systemctl daemon-reload


#. Start Tacker server. And enable Tacker server to start Tacker server every
   time system is restarted.

   .. code-block:: console

     $ sudo systemctl start tacker.service
     $ sudo systemctl start tacker-conductor.service

     $ sudo systemctl enable tacker.service
     $ sudo systemctl enable tacker-conductor.service


   .. note::

     When using openstack commands to access Tacker APIs, the openrc file for
     Tacker should be created with the user created above. And see
     :doc:`/cli/index` for how to use openstack commands for Tacker.


     .. code-block:: console

       $ vi tacker-openrc
       export OS_PROJECT_DOMAIN_ID=default
       export OS_USER_DOMAIN_ID=default
       export OS_PROJECT_NAME=service
       export OS_USERNAME=tacker
       export OS_PASSWORD=<TACKER_SERVICE_USER_PASSWORD>
       export OS_AUTH_URL=http://<KEYSTONE_IP>/identity
       export OS_INTERFACE=public
       export OS_IDENTITY_API_VERSION=3
       export OS_REGION_NAME=RegionOne


.. _Aodh: https://docs.openstack.org/aodh/latest/install/
.. _Barbican: https://docs.openstack.org/barbican/latest/install/
.. _Cinder: https://docs.openstack.org/cinder/latest/install/
.. _Glance: https://docs.openstack.org/glance/latest/install/
.. _Heat: https://docs.openstack.org/heat/latest/install/
.. _Keystone: https://docs.openstack.org/keystone/latest/install/
.. _Neutron: https://docs.openstack.org/neutron/latest/install/
.. _Nova: https://docs.openstack.org/nova/latest/install/
.. _Placement: https://docs.openstack.org/placement/latest/install/
.. _README of etc/tacker: https://opendev.org/openstack/tacker/src/branch/master/etc/tacker/README.txt
