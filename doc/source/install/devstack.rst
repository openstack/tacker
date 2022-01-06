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
  For ex, to install ``wallaby`` release, use ``stable/wallaby``.

For installation, ``stack.sh`` script in Devstack should be run as a
non-root user with sudo enabled.
Add a separate user ``stack`` and granting relevant privileges is a
good way to install via Devstack [#f0]_.

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
  to use a server that has at least two network interfaces [#f1]_.

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

   The ``local.conf`` can be created manually, or copied from Tacker
   repo [#f2]_. If copied, rename it as ``local.conf``.

   We have two choices for configuration basically:

   #. All-in-one mode

      All-in-one mode installs full Devstack environment including
      Tacker in one PC or Laptop.

      There are two examples for ``all-in-one`` mode:

      #. OpenStack as VIM.

         The example ``local.conf`` file for all-in-one mode with OpenStack
         is available at ``${TACKER_ROOT}/devstack/local.conf.example``.

         Refer below the contents of ``local.conf.example``:

         .. literalinclude:: ../../../devstack/local.conf.example
             :language: ini


      #. Openstack and Kubernetes as VIM.

         The difference between all-in-one mode with Kubernetes is
         to deploy kuryr-kubernetes and octavia.

         The example ``local.conf`` for all-in-one mode with Kubernetes is
         available at ``${TACKER_ROOT}/devstack/local.conf.kubernetes``

         Refer below the contents of ``local.conf.kubernetes``

         .. literalinclude:: ../../../devstack/local.conf.kubernetes
             :language: ini
             :emphasize-lines: 60-65

         .. note::

             The above local.conf.kubernetes does not work on CentOS8.
             Because docker-ce is not supported on CentOS8.

   #. Standalone mode

      Standalone mode installs only Tacker environment with some
      mandatory OpenStack services. Nova, Neutron or other essential
      components are not included in this mode.


      The example ``local.conf`` for standalone mode is available at
      ``${TACKER_ROOT}/devstack/local.conf.standalone``

      Refer below the contents of ``local.conf.standalone``

      .. literalinclude:: ../../../devstack/local.conf.standalone
          :language: ini

#. In CentOS environment install and start ovn services before executing
   stack.sh.

   .. code-block:: console

       $ sudo yum install -y centos-release-openstack-victoria
       $ sudo yum install -y openvswitch
       $ sudo yum install -y openvswitch-ovn-common
       $ sudo yum install -y openvswitch-ovn-central
       $ sudo yum install -y openvswitch-ovn-host
       $ sudo systemctl start ovn-northd.service
       $ sudo systemctl start ovn-controller.service
       $ sudo systemctl start ovs-vswitchd.service
       $ sudo systemctl start ovsdb-server.service

#. Execute installation script

   After saving the ``local.conf``, we can run ``stack.sh`` in the terminal
   to start installation.

   .. code-block:: console

       $ ./stack.sh

.. rubric:: Footnotes

.. [#f0] https://docs.openstack.org/devstack/latest/
.. [#f1] https://docs.openstack.org/devstack/latest/networking.html
.. [#f2] https://opendev.org/openstack/tacker/src/branch/master/devstack
