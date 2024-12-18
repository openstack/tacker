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


====================
Install via Devstack
====================

.. note::

  The content of this document has been confirmed to work
  using Tacker 2024.2 Dalmatian.


Overview
--------

Devstack based installation requires ``local.conf`` file.
This file contains different configuration options required for
installation.

Tacker provides some sample ``local.conf`` templates which can be
used for Devstack based Tacker installation.
You can find them in ``${TACKER_ROOT}/devstack`` directory in the
tacker repository.

Devstack supports installation from different code branches by
specifying branch name in your ``local.conf``.

* For latest version installation, use ``master`` branch.
* For specific release based installation, use corresponding branch name.
  For ex, to install ``2024.2 Dalmatian`` release, use ``stable/2024.2``.

For installation, ``stack.sh`` script in Devstack should be run as a
non-root user with sudo enabled.
Add a separate user ``stack`` and granting relevant privileges is a
good way to install via `Devstack`_.

Hardware Requirements
~~~~~~~~~~~~~~~~~~~~~

We recommend that your system meets the following hardware requirements:

.. note::

  These are reference values to install ``Openstack and Kubernetes as VIM``
  which generally requires the most resources. In reality, more parameters
  affect required resources.


.. list-table::
  :widths: 20 80
  :header-rows: 1

  * - Criteria
    - Recommended
  * - CPU
    - 4 cores or more
  * - RAM
    - 16 GB or more
  * - Storage
    - 80 GB or more


.. note::

  We recommend that you run DevStack in a VM, rather than on your bare-metal
  server. If you have to run devstack on a bare-metal server, It is recommended
  to use a server that has `at least two network interfaces`_.


Operation System
~~~~~~~~~~~~~~~~

If you do not have a preference, we recommend to
use a clean and minimal install of latest LTS version of ``Ubuntu``.

DevStack attempts to support the two latest LTS releases of Ubuntu.
For details, please refer to `Devstack`_.

Install
-------

Devstack installation script ``stack.sh`` expects ``local.conf``.

So the first step of installing tacker is to clone Devstack and prepare your
``local.conf``.

#. Download DevStack

   Get Devstack via git, with specific branch optionally if you prefer,
   and go down to the directory.

   .. code-block:: console

     $ git clone https://opendev.org/openstack/devstack -b <branch-name>
     $ cd devstack


#. Enable tacker related Devstack plugins in ``local.conf`` file

   The ``local.conf`` can be created manually, or copied from `Tacker
   repo`_. If you copied from repo, rename it as ``local.conf``.

   We have two choices for configuration basically:

   #. All-in-one mode

      All-in-one mode installs full Devstack environment including
      Tacker in one machine.

      .. note::

        ``TACKER_MODE="all"`` is set in local.conf for all-in-one mode.
        If TACKER_MODE is omitted in local.conf, ``TACKER_MODE="all"``
        is set by default.


      There are two examples for ``all-in-one`` mode:

      #. OpenStack as VIM.

         The example ``local.conf`` file for all-in-one mode with OpenStack
         is available at ``${TACKER_ROOT}/devstack/local.conf.example``.

         Refer below the contents of ``local.conf.example``:

         .. literalinclude:: ../../../devstack/local.conf.example
           :language: ini


      #. Openstack and Kubernetes as VIM.

         The difference between all-in-one mode with Kubernetes is
         to deploy devstack-plugin-container.

         The example ``local.conf`` for all-in-one mode with Kubernetes is
         available at ``${TACKER_ROOT}/devstack/local.conf.kubernetes``

         Refer below the contents of ``local.conf.kubernetes``

         .. literalinclude:: ../../../devstack/local.conf.kubernetes
             :language: ini
             :emphasize-lines: 54-64


         .. note::

             The above local.conf.kubernetes only works on Ubuntu.
             Because Devstack-plugin-container only supports building
             Kubernetes clusters on Ubuntu.


   #. Standalone mode

      Standalone mode installs only Tacker environment with some mandatory
      OpenStack services.

      .. note::

        ``TACKER_MODE="standalone"`` is set in local.conf for
        standalone mode.


      The example ``local.conf`` for standalone mode is available at
      ``${TACKER_ROOT}/devstack/local.conf.standalone``

      Refer below the contents of ``local.conf.standalone``

      .. literalinclude:: ../../../devstack/local.conf.standalone
        :language: ini


      .. note::

        Standalone mode is used in Zuul environments that run FT.
        For more information about FT, see
        :doc:`/contributor/tacker_functional_test` or the local.conf
        used in each Zuul environment.


#. Execute installation script

   After saving the ``local.conf``, we can run ``stack.sh`` in the terminal
   to start installation.

   .. code-block:: console

     $ ./stack.sh


Use PostgreSQL as Tacker database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When installing via Devstack, MySQL is used as Tacker database backend
by default.

To use PostgreSQL as Tacker database backend, execute the following command.

#. Install PostgreSQL and login.

   .. code-block:: console

     $ sudo apt install postgresql postgresql-contrib
     $ sudo -i -u postgres
     $ psql


#. Create PostgreSQL database and user.

   .. code-block::

     CREATE DATABASE tacker;
     CREATE ROLE tacker WITH CREATEDB LOGIN PASSWORD '<TACKERDB_PASSWORD>';
     exit;


#. Modify ``postgresql.conf`` and restart PostgreSQL server.

   .. note::

     The location of ``postgresql.conf`` is different for each distribution.
     For Ubuntu distribution, modify
     ``/etc/postgresql/{POSTGRESQL_VERSION}/main/postgresql.conf``.


   Insert ``escape`` as the value of ``bytea_output`` in ``postgresql.conf``.

   .. code-block:: ini

     bytea_output = 'escape'


   Restart PostgreSQL server.

   .. code-block:: console

     $ sudo systemctl restart postgresql.service


#. Modify ``tacker.conf`` for PostgreSQL and restart Tacker server.

   Edit the configuration of [database] in ``/etc/tacker/tacker.conf``
   as follows.

   .. code-block:: ini

     [database]
     connection = postgresql://tacker:<POSTGRES_PASSWORD>@<POSTGRES_IP>/tacker?client_encoding=utf8


   Restart Tacker server.

   .. code-block:: console

     $ sudo systemctl restart devstack@tacker.service
     $ sudo systemctl restart devstack@tacker-conductor.service


#. Activate the python virtual environment for Openstack and populate Tacker
   database.

   .. note::

     The ``psycopg2`` python library may need to be installed based on your
     environment after activating the virtual environment. You can find the
     version of the library in `Requirements of OpenStack`_.


   .. code-block:: console

     $ source /opt/stack/data/venv/bin/activate
     (venv) $ tacker-db-manage --config-file /etc/tacker/tacker.conf upgrade head


.. _Devstack: https://docs.openstack.org/devstack/latest/
.. _at least two network interfaces: https://docs.openstack.org/devstack/latest/networking.html
.. _Tacker repo: https://opendev.org/openstack/tacker/src/branch/master/devstack
.. _Requirements of OpenStack: https://opendev.org/openstack/requirements/src/branch/master/upper-constraints.txt
