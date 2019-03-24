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

The Devstack supports installation from different code branch by specifying
<branch-name> below. If there is no preference, it is recommended to install
Tacker from master branch, i.e. the <branch-name> is master. If pike branch
is the target branch, the <branch-name> is stable/pike.
Devstack should be run as a non-root with sudo enabled(standard logins to
cloud images such as "ubuntu" or "cloud-user" are usually fine). Creating a
separate user and granting relevant privileges please refer [#f0]_.

1. Download DevStack:

.. code-block:: console

    $ git clone https://git.openstack.org/openstack-dev/devstack -b <branch-name>
    $ cd devstack

..

2. Enable tacker related Devstack plugins in **local.conf** file:

First, the **local.conf** file needs to be created by manual or copied from
Tacker Repo [#f1]_ and renamed to **local.conf**. We have two Tacker
configuration installation files. First, it is the all-in-one mode that
installs full Devstack environment including Tacker in one PC or Laptop.
Second, it is the standalone mode which only will install a standalone
Tacker environment with some mandatory OpenStack services.

2.1. All-in-one mode

The **local.conf** file of all-in-one mode from [#f2]_ is shown as below:

.. code-block:: ini

    [[local|localrc]]
    ############################################################
    # Customize the following HOST_IP based on your installation
    ############################################################
    HOST_IP=127.0.0.1

    ADMIN_PASSWORD=devstack
    MYSQL_PASSWORD=devstack
    RABBIT_PASSWORD=devstack
    SERVICE_PASSWORD=$ADMIN_PASSWORD
    SERVICE_TOKEN=devstack

    ############################################################
    # Customize the following section based on your installation
    ############################################################

    # Pip
    PIP_USE_MIRRORS=False
    USE_GET_PIP=1

    #OFFLINE=False
    #RECLONE=True

    # Logging
    LOGFILE=$DEST/logs/stack.sh.log
    VERBOSE=True
    ENABLE_DEBUG_LOG_LEVEL=True
    ENABLE_VERBOSE_LOG_LEVEL=True

    # Neutron ML2 with OpenVSwitch
    Q_PLUGIN=ml2
    Q_AGENT=openvswitch

    # Disable security groups
    Q_USE_SECGROUP=False
    LIBVIRT_FIREWALL_DRIVER=nova.virt.firewall.NoopFirewallDriver

    # Enable heat, networking-sfc, barbican and mistral
    enable_plugin heat https://git.openstack.org/openstack/heat master
    enable_plugin networking-sfc https://git.openstack.org/openstack/networking-sfc master
    enable_plugin barbican https://git.openstack.org/openstack/barbican master
    enable_plugin mistral https://git.openstack.org/openstack/mistral master

    # Ceilometer
    #CEILOMETER_PIPELINE_INTERVAL=300
    enable_plugin ceilometer https://git.openstack.org/openstack/ceilometer master
    enable_plugin aodh https://git.openstack.org/openstack/aodh master

    # Blazar
    enable_plugin blazar https://github.com/openstack/blazar.git master

    # Tacker
    enable_plugin tacker https://git.openstack.org/openstack/tacker master

    enable_service n-novnc
    enable_service n-cauth

    disable_service tempest

    # Enable Kubernetes and kuryr-kubernetes
    KUBERNETES_VIM=True
    NEUTRON_CREATE_INITIAL_NETWORKS=False
    enable_plugin kuryr-kubernetes https://git.openstack.org/openstack/kuryr-kubernetes master
    enable_plugin neutron-lbaas https://git.openstack.org/openstack/neutron-lbaas master
    enable_plugin devstack-plugin-container https://git.openstack.org/openstack/devstack-plugin-container master

    [[post-config|/etc/neutron/dhcp_agent.ini]]
    [DEFAULT]
    enable_isolated_metadata = True

..


2.2. Standalone mode

The **local.conf** file of standalone mode from [#f3]_ is shown as below:

.. code-block:: ini

    [[local|localrc]]
    ############################################################
    # Customize the following HOST_IP based on your installation
    ############################################################
    HOST_IP=127.0.0.1
    SERVICE_HOST=127.0.0.1
    SERVICE_PASSWORD=devstack
    ADMIN_PASSWORD=devstack
    SERVICE_TOKEN=devstack
    DATABASE_PASSWORD=root
    RABBIT_PASSWORD=password
    ENABLE_HTTPD_MOD_WSGI_SERVICES=True
    KEYSTONE_USE_MOD_WSGI=True

    # Logging
    LOGFILE=$DEST/logs/stack.sh.log
    VERBOSE=True
    ENABLE_DEBUG_LOG_LEVEL=True
    ENABLE_VERBOSE_LOG_LEVEL=True
    GIT_BASE=${GIT_BASE:-https://git.openstack.org}

    TACKER_MODE=standalone
    USE_BARBICAN=True
    TACKER_BRANCH=<branch-name>
    enable_plugin networking-sfc ${GIT_BASE}/openstack/networking-sfc $TACKER_BRANCH
    enable_plugin barbican ${GIT_BASE}/openstack/barbican $TACKER_BRANCH
    enable_plugin mistral ${GIT_BASE}/openstack/mistral $TACKER_BRANCH
    enable_plugin tacker ${GIT_BASE}/openstack/tacker $TACKER_BRANCH

..

3. Installation

After saving the **local.conf**, we can run **stack.sh** in the terminal
to start setting up:

.. code-block:: console

    $ ./stack.sh

..

.. rubric:: Footnotes

.. [#f0] https://docs.openstack.org/devstack/latest/
.. [#f1] https://github.com/openstack/tacker/tree/master/devstack
.. [#f2] https://github.com/openstack/tacker/blob/master/devstack/local.conf.example
.. [#f3] https://github.com/openstack/tacker/blob/master/devstack/local.conf.standalone

