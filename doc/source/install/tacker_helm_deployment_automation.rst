..
      Copyright (C) 2025 NEC, Corp.
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

=================================
Tacker Helm Deployment Automation
=================================

Overview
--------

Installing Tacker via OpenStack-Helm involves multiple manual steps, including
the setup of system prerequisites, environment configuration, and deployment
of various components. This process can be error-prone and time-consuming,
especially for new users.

To simplify this, a Python-based automation script is introduced that
simplifies and streamlines the installation of Tacker using OpenStack-Helm
by handling the setup of all prerequisites and deployment steps.

The Automation Script is available is Tacker repository:

.. code-block:: console

       tacker/tools/tacker_helm_deployment_automation_script

This document provides the steps and guidelines for using the automation
script for Helm based installation of Tacker.

Prerequisites
-------------

#. All nodes must be able to access openstack repositories.
   The repositories will automatically be downloaded during the
   execution of the script.

   .. code-block:: console

      $ git clone https://opendev.org/openstack/openstack-helm.git
      $ git clone https://opendev.org/zuul/zuul-jobs.git


#. All participating nodes should have connectivity with each other.

Configuration changes
---------------------

#. Edit ``k8s_env/inventory.yaml`` for k8s deployment

   1. Add following for running ansible:

      .. code-block:: console

         # ansible user for running the playbook
         ansible_user: <USERNAME>
         ansible_ssh_private_key_file: <PATH_TO_SSH_KEY_FOR_USER>
         ansible_ssh_extra_args: -o StrictHostKeyChecking=no

   2. Add user and group for running the kubectl and helm commands.

      .. code-block:: console

         # The user and group that will be used to run Kubectl and Helm commands.
         kubectl:
           user: <USERNAME>
           group: <USERGROUP>
         # The user and group that will be used to run Docker commands.
         docker_users:
           - <USERNAME>

   3. Add user details which will be used for communication between the master
      and worker nodes. This user must be configured with passwordless ssh on
      all the nodes.

      .. code-block:: console

         # to connect to the k8s master node via ssh without a password.
         client_ssh_user: <USERNAME>
         cluster_ssh_user: <USER_GROUP>

   4. Enable MetalLB if using bare-metal servers for load balancing.

      .. code-block:: console

         # MetalLB controllr is used for bare-metal loadbalancer.
         metallb_setup: true

   5. If deploying CEPH cluster enable the loopback device config to be used by CEPH

      .. code-block:: console

         # Loopback devices will be created on all cluster nodes which then can be used
         # to deploy a Ceph cluster which requires block devices to be provided.
         # Please use loopback devices only for testing purposes. They are not suitable
         # for production due to performance reasons.
         loopback_setup: true
         loopback_device: /dev/loop100
         loopback_image: /var/lib/openstack-helm/ceph-loop.img
         loopback_image_size: 12G

   6. Add the primary node where the Kubectl and Helm will be installed.

      .. code-block:: console

         children:
         # The primary node where Kubectl and Helm will be installed. If it is
         # the only node then it must be a member of the groups k8s_cluster and
         # k8s_control_plane. If there are more nodes then the wireguard tunnel
         # will be established between the primary node and the k8s_control_plane
           node.
         primary:
           hosts:
             primary:
               ansible_host: <PRIMARY_NODE_IP>

  7. Add node where the Kubernetes cluster will be deployed. If there only 1 node,
     then mention it here

     .. code-block:: console

        # The nodes where the Kubernetes components will be installed.
        k8s_cluster:
          hosts:
           primary:
             ansible_host: <IP_ADDRESS>
           node-2:
             ansible_host: <IP_ADDRESS>
           node-3:
             ansible_host: <IP_ADDRESS>

  8. Add control-plane node in the section

     .. code-block:: console

        # The control plane node where the Kubernetes control plane components
          will be installed.
        # It must be the only node in the group k8s_control_plane.
        k8s_control_plane:
          hosts:
            primary:
              ansible_host: <IP_ADDRESS>

  9. Add worker nodes in the k8s_nodes section, If its single node installation
     then leave the section empty

     .. code-block:: console

        # These are Kubernetes worker nodes. There could be zero such nodes.
        # In this case the Openstack workloads will be deployed on the control
          plane node.
        k8s_nodes:
          hosts:
            node-2:
              ansible_host: <IP_ADDRESS>
            node-3:
              ansible_host: <IP_ADDRESS>

   You can find whole of examples of ``inventory.yaml`` in [1]_.


#. Edit ``TACKER_NODE`` in ``config/config.yaml`` with the
   hostname of the master node to label it as control-plane
   node

   .. code-block:: console

      NODES:
       TACKER_NODE: <CONTROL-PLANE_NODE_HOSTNAME>



Script execution
----------------

#. Ensure that the user has permission to execute the script


   .. code-block:: console

      $ ls -la Tacker_Install.py
       -rwxr-xr-x 1 root root 21923 Jul 22 10:00 Tacker_Install.py

#. Execute the command to run the script


   .. code-block:: console

      $ sudo python3 Tacker_install.py

#. Execute the command to run the script

  .. code-block:: console

     $ kubectl get pods -n openstack | grep -i  Tacker
       tacker-conductor-d7595d756-6k8wp            1/1     Running     0          24h
       tacker-db-init-mxwwf                        0/1     Completed   0          24h
       tacker-db-sync-4xnhx                        0/1     Completed   0          24h
       tacker-ks-endpoints-4nbqb                   0/3     Completed   0          24h
       tacker-ks-service-c8s2m                     0/1     Completed   0          24h
       tacker-ks-user-z2cq7                        0/1     Completed   0          24h
       tacker-rabbit-init-fxggv                    0/1     Completed   0          24h
       tacker-server-6f578bcf6c-z7z2c              1/1     Running     0          24h

 For details refer to the document in [2]_.

References
----------

.. [1] https://docs.openstack.org/openstack-helm/latest/install/kubernetes.html
.. [2] https://docs.openstack.org/tacker/latest/install/openstack_helm.html
