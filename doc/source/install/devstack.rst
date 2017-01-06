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

2. Enable both heat and tacker devstack plugins in ``local.conf`` file::

    [[local|localrc]]
    enable_plugin heat https://git.openstack.org/openstack/heat
    enable_plugin tacker https://git.openstack.org/openstack/tacker

3. Run ``stack.sh``::

    $ ./stack.sh

Install from stable branch
~~~~~~~~~~~~~~~~~~~~~~~~~~
Choose the required stable branch name from the git repository and use it in
place of branch-name as given below:

1. Download DevStack stable branch::

    $ git clone -b stable/<branch-name> https://git.openstack.org/openstack-dev/devstack
    $ cd devstack


2. Add this repo as an external repository into your ``local.conf`` file::

    [[local|localrc]]
    enable_plugin tacker https://git.openstack.org/openstack/tacker stable/<branch-name>


3. Run ``stack.sh``::

    $ ./stack.sh

Standalone mode installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, the tacker devstack plugin will install the tacker and
other OpenStack services together. By setting TACKER_MODE=standalone
in local.conf, we will install a standalone tacker environment with
some mandatory OpenStack services, such as KeyStone.
After this installation, a default VIM must be registered manually.
