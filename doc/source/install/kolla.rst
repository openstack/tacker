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

.. note::

    This installation guide is explaining about Tacker. Other components,
    such as nova or neutron, are not covered here.

.. note::

    This installation guide contents are specific to Redhat distro.


Please refer to
`Install dependencies
<https://docs.openstack.org/kolla-ansible/latest/user/quickstart.html#install-dependencies>`_
of Kolla Ansible installation [1]_ to set up the docker environment that is
used by Kolla Ansible.

To install via Kolla Ansible, the version of Kolla Ansible should be consistent
with the target Tacker system. For example, stable/ussuri branch of
Kolla Ansible should be used to install stable/ussuri branch of Tacker.
Here the stable/ussuri branch version will be used to show how to install
Tacker with Kolla Ansible.

Kolla can be used to install multiple nodes system, but Tacker server is not
ready for multiple nodes deployment yet, so only an all-in-one Tacker is
installed in this document.


Install Kolla Ansible
---------------------

#. Get the stable/ussuri version of Kolla Ansible:

   .. code-block:: console

       $ git clone https://github.com/openstack/kolla-ansible.git -b stable/ussuri
       $ cd kolla-ansible
       $ sudo dnf install python3-devel libffi-devel gcc openssl-devel python3-libselinux
       $ sudo pip3 install -r requirements.txt
       $ sudo python3 setup.py install

   If the needed version has already been published at pypi site
   'https://pypi.org/project/kolla-ansible', the command below can be used:

   .. code-block:: console

      $ sudo pip install "kolla-ansible==5.0.0"

#. Install dependencies:

   .. code-block:: console

      $ sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
      $ sudo dnf install https://download.docker.com/linux/centos/7/x86_64/stable/Packages/containerd.io-1.2.6-3.3.el7.x86_64.rpm
      $ sudo dnf install docker-ce docker-ce-cli
      $ sudo systemctl enable docker
      $ sudo systemctl restart docker
      $ sudo pip3 install 'ansible<2.10'
      $ sudo pip3 install docker

   .. note::

      Installing docker-ce on CentOS 8 is not officially supported.


Install Tacker
--------------

#. Edit Kolla Ansible's configuration file ``/etc/kolla/globals.yml``:

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
      docker_namespace: "kolla"
      #docker_namespace: "gongysh"
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

   .. note::

      To determine version of kolla-ansible, the following commandline can be
      used:

      .. code-block:: console

         $ python -c \
           "import pbr.version; print(pbr.version.VersionInfo('kolla-ansible'))"


#. Run kolla-genpwd to generate system passwords:

   .. code-block:: console

      $ sudo cp etc/kolla/passwords.yml /etc/kolla/passwords.yml
      $ sudo kolla-genpwd

   .. note::

      If the pypi version is used to install kolla-ansible the skeleton
      passwords file maybe under
      ``/usr/share/kolla-ansible/etc_examples/kolla``.


   With this command, ``/etc/kolla/passwords.yml`` will be populated with
   generated passwords.

#. Run Kolla Ansible deploy to install tacker system:

   .. code-block:: console

      $ sudo kolla-ansible deploy


#. Run Kolla Ansible post-deploy to generate tacker access environment file:

   .. code-block:: console

      $ sudo kolla-ansible post-deploy

   With this command, ``admin-openrc.sh`` will be generated at
   ``/etc/kolla/admin-openrc.sh``.

#. Check the related containers are started and running:

   Tacker system consists of some containers. Following is a sample output.
   The containers fluentd, cron and kolla_toolbox are from kolla, please see
   Kolla Ansible documentation for their usage. Others are from Tacker system
   components.

   .. code-block:: console

      $ sudo docker ps --format "table {{.ID}}\t{{.Image}}\t{{.Names}}"
      CONTAINER ID        IMAGE                                                   NAMES
      756adb8d787f        kolla/centos-source-tacker-server:ussuri                tacker_server
      000320a1c76f        kolla/centos-source-tacker-conductor:ussuri             tacker_conductor
      11b5ccf91d86        kolla/centos-source-barbican-worker:ussuri              barbican_worker
      4a5224d14f36        kolla/centos-source-barbican-keystone-listener:ussuri   barbican_keystone_listener
      a169e7aed0b6        kolla/centos-source-barbican-api:ussuri                 barbican_api
      2b3b0341b562        kolla/centos-source-mistral-executor:ussuri             mistral_executor
      6c69bbdf6aea        kolla/centos-source-mistral-event-engine:ussuri         mistral_event_engine
      d035295fe9f0        kolla/centos-source-mistral-engine:ussuri               mistral_engine
      72f52de2fb77        kolla/centos-source-mistral-api:ussuri                  mistral_api
      07ecaad80542        kolla/centos-source-horizon:ussuri                      horizon
      7e6ac94ea505        kolla/centos-source-keystone:ussuri                     keystone
      2b16b169ed18        kolla/centos-source-keystone-fernet:ussuri              keystone_fernet
      ec80b37da07b        kolla/centos-source-keystone-ssh:ussuri                 keystone_ssh
      3e3d5c976921        kolla/centos-source-rabbitmq:ussuri                     rabbitmq
      24196bca6652        kolla/centos-source-memcached:ussuri                    memcached
      73f9873b1eac        kolla/centos-source-mariadb-clustercheck:ussuri         mariadb_clustercheck
      ceb67bd5418d        kolla/centos-source-mariadb:ussuri                      mariadb
      b82404a0400e        kolla/centos-source-chrony:ussuri                       chrony
      f70ab08ea36d        kolla/centos-source-cron:ussuri                         cron
      5bbe7eee05d4        kolla/centos-source-kolla-toolbox:ussuri                kolla_toolbox
      be73c1b5fdca        kolla/centos-source-fluentd:ussuri                      fluentd

#. Install tacker client:

   .. code-block:: console

      $ sudo pip3 install python-tackerclient
      $ sudo pip3 install python-openstackclient

#. Check the Tacker server is running well:

   .. code-block:: console

      $ sudo cat /etc/kolla/admin-openrc.sh > /tmp/admin-openrc.sh
      $ . /tmp/admin-openrc.sh
      $ openstack vim list


References
----------

.. [1] https://docs.openstack.org/kolla-ansible/latest/user/quickstart.html
