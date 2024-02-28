..
      Copyright (C) 2024 NEC, Corp.
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

==========================
Install via Openstack-helm
==========================

Overview
--------

This document specifies procedure for installing tacker service with
OpenStack-helm. The goal of OpenStack-helm is to provide a collection
of Helm charts that simply, resiliently, and flexibly deploy OpenStack
and related services on Kubernetes.

Pre-Requisites for Tacker installation with openstack-helm
----------------------------------------------------------

Pre-requisite for tacker installation are below:

#. Clone OpenStack-helm and openstack-helm-infra code in home directory.

   .. code-block:: console

       $ git clone https://opendev.org/openstack/openstack-helm.git
       $ git clone https://opendev.org/openstack/openstack-helm-infra.git
       $ cd openstack-helm

#. Setup Kubernetes.

   Please refer to install dependencies of Kubernetes Installation [1]_.

#. Create namespace with name openstack and provide label to node.

   .. code-block:: console

       $ kubectl create ns openstack
       $ kubectl label node <node-name> openstack-control-plane=enabled

#. Setup OpenStack.

   Please refer to install following dependencies of OpenStack Installation:

   * Deploy ingress controller [2]_.

   * Deploy OpenStack backend [3]_.

   * Deploy OpenStack [4]_.

   Here you can see how to install OpenStack and it's dependencies using
   openstack-helm.

.. note::

  Barbican must be installed. Although not documented in Deploy OpenStack [4]_,
  you must install Barbican using similar procedure. Execute the following
  script to install Barbican.

  .. code-block:: console

      $ cd ~/openstack-helm
      $ ./tools/deployment/component/barbican/barbican.sh

Install Tacker
--------------

#. Tacker installation with OpenStack-helm will use script tacker.sh.

   Use script tacker.sh to install tacker.

   .. code-block:: console

       $ cd ~/openstack-helm
       $ ./tools/deployment/component/tacker/tacker.sh

#. Validate tacker-conductor and tacker-server pods are running and
   deployment status of helm release is deployed.

   .. code-block:: console

       $ kubectl get pods -A | grep tacker
       openstack          tacker-conductor-654fc7478-wt242                                1/1     Running     0             58m
       openstack          tacker-db-init-nxd7c                                            0/1     Completed   0             58m
       openstack          tacker-db-sync-kmf27                                            0/1     Completed   0             58m
       openstack          tacker-ks-endpoints-hbwnh                                       0/3     Completed   0             58m
       openstack          tacker-ks-service-7t8pm                                         0/1     Completed   0             58m
       openstack          tacker-ks-user-8blcj                                            0/1     Completed   0             58m
       openstack          tacker-rabbit-init-tlbj8                                        0/1     Completed   0             58m
       openstack          tacker-server-55fcdfdc5d-gj844                                  1/1     Running     0             58m

       $ helm ls -A | grep tacker
       tacker                  openstack       1               2024-01-05 13:02:43.337535539 +0000 UTC deployed        tacker-0.1.2            v1.0.0s

#. Validate Tacker api is working properly.

   .. code-block:: console

       $ TACKER_SERVER_POD=tacker-server-55fcdfdc5d-gj844
       $ kubectl exec -n openstack -it $TACKER_SERVER_POD \
          -- curl -i -X POST -H "Content-Type: application/json" \
          -d '{"auth":{"identity":{"methods":["password"],"password":{"user":{"domain":{"name":"default"},"name":"admin","password":"password"}}},"scope":{"project":{"domain":{"name":"default"},"name":"admin"}}}}' \
          http://keystone-api.openstack.svc.cluster.local:5000/v3/auth/tokens
       Defaulted container "tacker-server" out of: tacker-server, init (init)
       HTTP/1.1 201 CREATED
       Date: Mon, 08 Jan 2024 11:22:50 GMT
       Server: Apache
       Content-Length: 7264
       X-Subject-Token: gAAAAABlm9sKwC-dJi_yWI8ea7HmEM-Xv3RisrODnAc6Qebqhg9OOuCPBcddk5P8qdSyIAJnMOZwVYgXyYPXLIwr7Zrn5eCCnYJ-YxnVS6nj_8DQLExTFfiFRrwz93LeULzLTKLmjWoo8QslBpk1cuz-uXf7rtny784duFjhUAOjoDYfv16aebI
       Vary: X-Auth-Token
       x-openstack-request-id: req-425da814-d3c7-4e7f-ad2f-ec19159fcbb0
       Content-Type: application/json

       $ TOKEN=gAAAAABlm9sKwC-dJi_yWI8ea7HmEM-Xv3RisrODnAc6Qebqhg9OOuCPBcddk5P8qdSyIAJnMOZwVYgXyYPXLIwr7Zrn5eCCnYJ-YxnVS6nj_8DQLExTFfiFRrwz93LeULzLTKLmjWoo8QslBpk1cuz-uXf7rtny784duFjhUAOjoDYfv16aebI

   API request to the Tacker API endpoint for retrieving list vnf instances.

   .. code-block:: console

       $ kubectl get pods -A -o wide | grep tacker-server
       openstack          tacker-server-55fcdfdc5d-gj844                                  1/1     Running     0             15d    192.168.219.119   master   <none>           <none>

       $ curl -X GET http://192.168.219.119:9890/vnflcm/v2/vnf_instances -H "X-Auth-Token:$TOKEN" -H "Version: 2.0.0"
       []


References
----------

.. [1] https://docs.openstack.org/openstack-helm/latest/install/deploy_kubernetes.html
.. [2] https://docs.openstack.org/openstack-helm/latest/install/deploy_ingress_controller.html
.. [3] https://docs.openstack.org/openstack-helm/latest/install/deploy_openstack_backend.html
.. [4] https://docs.openstack.org/openstack-helm/latest/install/deploy_openstack.html
