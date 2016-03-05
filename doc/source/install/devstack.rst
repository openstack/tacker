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

If there is no preference, it is recommended to install Tacker from master
branch.

Install from master
~~~~~~~~~~~~~~~~~~~

1. Download DevStack::

    $ git clone https://git.openstack.org/openstack-dev/devstack
    $ cd devstack

2. Add this repo as an external repository into your ``local.conf`` file::

    [[local|localrc]]
    enable_plugin tacker https://git.openstack.org/openstack/tacker

3. Run ``stack.sh``::

    $ stack.sh

Install from Liberty
~~~~~~~~~~~~~~~~~~~~

1. Download DevStack liberty branch::

    $ git clone -b stable/liberty https://git.openstack.org/openstack-dev/devstack
    $ cd devstack

2. Add this repo as an external repository into your ``local.conf`` file::

    [[local|localrc]]
    enable_plugin tacker https://git.openstack.org/openstack/tacker stable/liberty

3. Run ``stack.sh``::

    $ stack.sh

Multi Node Environment
~~~~~~~~~~~~~~~~~~~~~~

In a multi-node devstack environment where controller, network and compute
nodes are separate, some neutron agents should not be installed in the
controller node. In such cases, use the following local.conf setting to disable
neutron agents in the controller node::

    [[local|localrc]]
    TACKER_NEUTRON_AGENTS=''

