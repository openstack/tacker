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

The devstack supports installation from different code branch by specifying
<branch-name> below. If there is no preference, it is recommended to install
Tacker from master branch, i.e. the <branch-name> is master. If pike branch
is the target branch, the <branch-name> is stable/pike.

1. Download DevStack::

    $ git clone https://git.openstack.org/openstack-dev/devstack -b <branch-name>
    $ cd devstack

2. Enable tacker related devstack plugins in ``local.conf`` file::

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
    GIT_BASE=${GIT_BASE:-git://git.openstack.org}

    TACKER_MODE=standalone
    USE_BARBICAN=True
    TACKER_BRANCH=<branch-name>
    enable_plugin networking-sfc ${GIT_BASE}/openstack/networking-sfc $TACKER_BRANCH
    enable_plugin barbican ${GIT_BASE}/openstack/barbican $TACKER_BRANCH
    enable_plugin mistral ${GIT_BASE}/openstack/mistral $TACKER_BRANCH
    enable_plugin tacker ${GIT_BASE}/openstack/tacker $TACKER_BRANCH

3. Run ``stack.sh``::

    $ ./stack.sh
