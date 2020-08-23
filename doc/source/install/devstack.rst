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

Tacker provides some examples, or templates, of ``local.conf`` used for
Devstack. You can find them in ``${TACKER_ROOT}/devstack`` directory in the
tacker repository.

Devstack supports installation from different code branch by specifying
branch name in your ``local.conf`` as described in below.
If you install the latest version, use ``master`` branch.
On the other hand, if you install specific release, suppose ``ussuri``
in this case, branch name must be ``stable/ussuri``.

For installation, ``stack.sh`` script in Devstack should be run as a
non-root user with sudo enabled.
Add a separate user ``stack`` and granting relevant privileges is a good way
to install via Devstack [#f0]_.

Install
-------

Devstack expects to be provided ``local.conf`` before running install script.
The first step of installing tacker is to clone Devstack and prepare your
``local.conf``.

#. Download DevStack

   Get Devstack via git, with specific branch optionally if you prefer,
   and go down to the directory.

   .. code-block:: console

       $ git clone https://opendev.org/openstack-dev/devstack -b <branch-name>
       $ cd devstack

#. Enable tacker related Devstack plugins in ``local.conf`` file

   ``local.conf`` needs to be created by manual, or copied from Tacker
   repo [#f1]_ renamed as ``local.conf``. We have two choices for
   configuration basically. First one is the ``all-in-one`` mode that
   installs full Devstack environment including Tacker in one PC or Laptop.
   Second, it is ``standalone`` mode which only will install only Tacker
   environment with some mandatory OpenStack services. Nova, Neutron or other
   essential components are not included in this mode.

   #. All-in-one mode

      There are two examples for ``all-in-one`` mode, targetting OpenStack
      or Kubernetes as VIM.

      ``local.conf`` for ``all-in-one`` mode with OpenStack [#f2]_
      is shown as below.

      .. literalinclude:: ../../../devstack/local.conf.example
          :language: ini

      The difference between ``all-in-one`` mode with Kubernetes [#f3]_ is
      to deploy kuryr-kubernetes and octavia.

      .. literalinclude:: ../../../devstack/local.conf.kubernetes
          :language: ini
          :emphasize-lines: 60-65

      .. note::

          The above local.conf.kubernetes does not work on CentOS8.
          Because docker-ce is not supported on CentOS8.

   #. Standalone mode

      The ``local.conf`` file of standalone mode from [#f4]_ is shown as below.

      .. literalinclude:: ../../../devstack/local.conf.standalone
          :language: ini

#. Installation

   After saving the ``local.conf``, we can run ``stack.sh`` in the terminal
   to start setting up.

   .. code-block:: console

       $ ./stack.sh

.. rubric:: Footnotes

.. [#f0] https://docs.openstack.org/devstack/latest/
.. [#f1] https://opendev.org/openstack/tacker/src/branch/master/devstack
.. [#f2]
   https://opendev.org/openstack/tacker/src/branch/master/devstack/local.conf.example
.. [#f3]
   https://opendev.org/openstack/tacker/src/branch/master/devstack/local.conf.kubernetes
.. [#f4]
   https://opendev.org/openstack/tacker/src/branch/master/devstack/local.conf.standalone
