..
      Copyright 2014-2017 OpenStack Foundation
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


=========================
Install via Kolla Ansible
=========================

Please refer to "Install dependencies" part of kolla ansible quick start at
https://docs.openstack.org/kolla-ansible/latest/user/quickstart.html to set
up the docker environment that is used by kolla ansible.

To install via Kolla Ansible, the version of Kolla Ansible should be consistent
with the target Tacker system. For example, stable/pike branch of Kolla Ansible
should be used to install stable/pike branch of Tacker. Here the stable/pike
branch version will be used to show how to install Tacker with Kolla Ansible.

Kolla can be used to install multiple nodes system, but Tacker server is not
ready for multiple nodes deployment yet, so only an all-in-one Tacker is
installed in this document.


Install Kolla Ansible
~~~~~~~~~~~~~~~~~~~~~

1. Get the stable/pike version of kolla ansible:

.. code-block:: console

    $ git clone https://github.com/openstack/kolla-ansible.git -b stable/pike
    $ cd kolla-ansible
    $ sudo yum install python-devel libffi-devel gcc openssl-devel libselinux-python
    $ sudo pip install -r requirements.txt
    $ sudo python setup.py install

..


If the needed version has already been published at pypi site
'https://pypi.org/project/kolla-ansible', the command below can be used:

.. code-block:: console

    $ sudo pip install "kolla-ansible==5.0.0"

..


Install Tacker
~~~~~~~~~~~~~~

1. Edit kolla ansible's configuration file /etc/kolla/globals.yml:

.. code-block:: ini

    ---
    kolla_install_type: "source"
    # openstack_release can be determined by version of kolla-ansible tool.
    # But if needed, it can be specified.
    #openstack_release: 5.0.0
    kolla_internal_vip_address: <one IP address of local nic interface>
    # The Public address used to communicate with OpenStack as set in the
    # public_url for the endpoints that will be created. This DNS name
    # should map to kolla_external_vip_address.
    #kolla_external_fqdn: "{{ kolla_external_vip_address }}"
    # define your own registry if needed
    #docker_registry: "127.0.0.1:4000"
    # If needed OpenStack kolla images are published, docker_namespace should be
    # kolla
    #docker_namespace: "kolla"
    docker_namespace: "gongysh"
    enable_glance: "no"
    enable_haproxy: "no"
    enable_keystone: "yes"
    enable_mariadb: "yes"
    enable_memcached: "yes"
    enable_neutron: "no"
    enable_nova: "no"
    enable_barbican: "yes"
    enable_mistral: "yes"
    enable_tacker: "yes"
    enable_heat: "no"
    enable_openvswitch: "no"
    enable_horizon: "yes"
    enable_horizon_tacker: "{{ enable_tacker | bool }}"

..

.. note::

    To determine version of kolla-ansible, the following commandline can be
    used:

    $ python -c "import pbr.version; print(pbr.version.VersionInfo('kolla-ansible'))"


2. Run kolla-genpwd to generate system passwords:

.. code-block:: console

    $ sudo cp etc/kolla/passwords.yml /etc/kolla/passwords.yml
    $ sudo kolla-genpwd

..

.. note::

    If the pypi version is used to install kolla-ansible the skeleton passwords
    file maybe under '/usr/share/kolla-ansible/etc_examples/kolla'.


With this command, /etc/kolla/passwords.yml will be populated with
generated passwords.


3. Run kolla ansible deploy to install tacker system:

.. code-block:: console

    $ sudo kolla-ansible deploy

..


4. Run kolla ansible post-deploy to generate tacker access environment file:

.. code-block:: console

    $ sudo kolla-ansible post-deploy

..

With this command, the "admin-openrc.sh" will be generated at
/etc/kolla/admin-openrc.sh.


5. Check the related containers are started and running:

Tacker system consists of some containers. Following is a sample output.
The containers fluentd, cron and kolla_toolbox are from kolla, please see
kolla ansible documentation for their usage. Others are from Tacker system
components.

.. code-block:: console

    $ sudo docker ps --format "table {{.ID}}\t{{.Image}}\t{{.Names}}"
    CONTAINER ID        IMAGE                                                    NAMES
    78eafed848a8        gongysh/centos-source-tacker-server:5.0.0                tacker_server
    00bbecca5950        gongysh/centos-source-tacker-conductor:5.0.0             tacker_conductor
    19eddccf8e8f        gongysh/centos-source-barbican-worker:5.0.0              barbican_worker
    6434b1d8236e        gongysh/centos-source-barbican-keystone-listener:5.0.0   barbican_keystone_listener
    48be088643f8        gongysh/centos-source-barbican-api:5.0.0                 barbican_api
    50b9a9a0e542        gongysh/centos-source-mistral-executor:5.0.0             mistral_executor
    07c28d845311        gongysh/centos-source-mistral-engine:5.0.0               mistral_engine
    196bbcc592a4        gongysh/centos-source-mistral-api:5.0.0                  mistral_api
    d5511b195a58        gongysh/centos-source-horizon:5.0.0                      horizon
    62913ec7c056        gongysh/centos-source-keystone:5.0.0                     keystone
    552b95e82f98        gongysh/centos-source-rabbitmq:5.0.0                     rabbitmq
    4d57d7735514        gongysh/centos-source-mariadb:5.0.0                      mariadb
    4e1142ff158d        gongysh/centos-source-cron:5.0.0                         cron
    000ba4ca1974        gongysh/centos-source-kolla-toolbox:5.0.0                kolla_toolbox
    0fe21b1ad18c        gongysh/centos-source-fluentd:5.0.0                      fluentd
    a13e45fc034f        gongysh/centos-source-memcached:5.0.0                    memcached

..


6. Install tacker client:

.. code-block:: console

    $ sudo pip install python-tackerclient

..


7. Check the Tacker server is running well:

.. code-block:: console

    $ . /etc/kolla/admin-openrc.sh
    $ openstack vim list

..
