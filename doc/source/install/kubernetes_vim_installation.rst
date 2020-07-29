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


===========================
Kubernetes VIM Installation
===========================

This document describes the way to install Kubernetes VIM via Devstack and
how to register Kubernetes VIM in Tacker.

To do that job, Tacker reuses the efforts from Kuryr-Kubernetes project in
creating Kubernetes cluster and setting up native Neutron-based networking
between Kubernetes and OpenStack VIMs. Features from Kuryr-Kubernetes will
bring VMs and Pods (and other Kubernetes resources) on the same network.

#. Edit local.conf file by adding the following content

   .. code-block:: console

      # Enable kuryr-kubernetes, docker, octavia
      KUBERNETES_VIM=True
      enable_plugin kuryr-kubernetes https://opendev.org/openstack/kuryr-kubernetes master
      enable_plugin octavia https://opendev.org/openstack/octavia master
      enable_plugin devstack-plugin-container https://opendev.org/openstack/devstack-plugin-container master
      KURYR_K8S_CLUSTER_IP_RANGE="10.0.0.0/24"

   The public network will be used to launched LoadBalancer for Services in
   Kubernetes. The example for setting public subnet is described in [#first]_

   For more details, users also see the same examples in [#second]_ and [#third]_.

#. Run stack.sh

   .. code-block:: console

      $ ./stack.sh

#. Get Kubernetes VIM configuration

   * After successful installation, user can get "Bearer Token":

   .. code-block:: console

      $ TOKEN=$(kubectl describe secret $(kubectl get secrets | grep default | cut -f1 -d ' ') | grep -E '^token' | cut -f2 -d':' | tr -d '\t')

   In the Hyperkube folder /yourdirectory/data/hyperkube/, user can get more
   information for authenticating to Kubernetes cluster.

   * Get ssl_ca_cert:

   .. code-block:: console

      $ sudo cat /opt/stack/data/hyperkube/ca.crt
      -----BEGIN CERTIFICATE-----
      MIIDUzCCAjugAwIBAgIJAI+laRsxtQQMMA0GCSqGSIb3DQEBCwUAMCAxHjAcBgNV
      BAMMFTE3Mi4xNy4wLjJAMTUwNzU1NTc4MzAeFw0xNzEwMDkxMzI5NDNaFw0yNzEw
      MDcxMzI5NDNaMCAxHjAcBgNVBAMMFTE3Mi4xNy4wLjJAMTUwNzU1NTc4MzCCASIw
      DQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALfJ+Lsq8VmXBfZC4OPm96Y1Ots2
      Np/fuGLEhT+JpHGCK65l4WpBf+FkcNDIb5Jn1EBr5XDEVN1hlzcPdCHu1sAvfTNB
      AJkq/4TzkenEusxiQ8TQWDnIrAo73tkYPyQMAfXHifyM20gCz/jM+Zy2IoQDArRq
      MItRdoFa+7rRJntFk56y9NZTzDqnziLFFoT6W3ZdU3BElX6oWarbLWxNNpYlVEbI
      YdfooLqKTH+25Fh3TKsMVxOdc7A5MggXRHYYkbbDgDAVln9ki9x/c6U+5bQQ9H8+
      +Lhzdova4gjq/RBJCtiISN7HvLuq+VenArFREgAqr/r/rQZckeAD/4mzQNECAwEA
      AaOBjzCBjDAdBgNVHQ4EFgQU1zZHXIHhmPDe+ajaNqsOdu5QfbswUAYDVR0jBEkw
      R4AU1zZHXIHhmPDe+ajaNqsOdu5QfbuhJKQiMCAxHjAcBgNVBAMMFTE3Mi4xNy4w
      LjJAMTUwNzU1NTc4M4IJAI+laRsxtQQMMAwGA1UdEwQFMAMBAf8wCwYDVR0PBAQD
      AgEGMA0GCSqGSIb3DQEBCwUAA4IBAQAr8ARlYpIbeML8fbxdAARuZ/dJpbKvyNHC
      GXJI/Uh4xKmj3LrdDYQjHb1tbRSV2S/gQld+En0L92XGUl/x1pG/GainDVpxpTdt
      FwA5SMG5HLHrudZBRW2Dqe1ItKjx4ofdjz+Eni17QYnI0CEdJZyq7dBInuCyeOu9
      y8BhzIOFQALYYL+K7nERKsTSDUnTwgpN7p7CkPnAGUj51zqVu2cOJe48SWoO/9DZ
      AT0UKTr/agkkjHL0/kv4x+Qhr/ICjd2JbW7ePxQBJ8af+SYuKx7IRVnubnqVMEN6
      V/kEAK/h2NAKS8OnlBgUMXIojSInmGXJfM5l1GUlQiqiBTv21Fm6
      -----END CERTIFICATE-----

   * Get basic authentication username and password:

   .. code-block:: console

      $ sudo cat /opt/stack/data/hyperkube/basic_auth.csv
      admin,admin,admin

   The basic auth file is a csv file with a minimum of 3 columns: password,
   user name, user id. If there are more than 3 columns, see the following
   example:

   .. code-block:: console

      password,user,uid,"group1,group2,group3"

   In this example, the user belongs to group1, group2 and group3.

   * Get Kubernetes server url

   By default Kubernetes server listens on https://127.0.0.1:6443 and
   https://{HOST_IP}:6443

   .. code-block:: console

      $ curl http://localhost:8080/api/
      {
        "kind": "APIVersions",
        "versions": [
          "v1"
        ],
        "serverAddressByClientCIDRs": [
          {
            "clientCIDR": "0.0.0.0/0",
            "serverAddress": "192.168.11.110:6443"
          }
        ]
      }

#. Check Kubernetes cluster installation

   By default, after set KUBERNETES_VIM=True, Devstack creates a public network
   called net-k8s, and two extra ones for the kubernetes services and pods
   under the project k8s:

   .. code-block:: console

      $ openstack network list --project admin
      +--------------------------------------+-----------------+--------------------------------------+
      | ID                                   | Name            | Subnets                              |
      +--------------------------------------+-----------------+--------------------------------------+
      | 28361f77-1875-4070-b0dc-014e26c48aeb | public          | 28c51d19-d437-46e8-9b0e-00bc392c57d6 |
      | 71c20650-6295-4462-9219-e0007120e64b | k8s-service-net | f2835c3a-f567-44f6-b006-a6f7c52f2396 |
      | 97c12aef-54f3-41dc-8b80-7f07c34f2972 | k8s-pod-net     | 7759453f-6e8a-4660-b845-964eca537c44 |
      | 9935fff9-f60c-4fe8-aa77-39ba7ac10417 | net0            | 92b2bd7b-3c14-4d32-8de3-9d3cc4d204cb |
      | c2120b78-880f-4f28-8dc1-3d33b9f3020b | net_mgmt        | fc7b3f32-5cac-4857-83ab-d3700f4efa60 |
      | ec194ffc-533e-46b3-8547-6f43d92b91a2 | net1            | 08beb9a1-cd74-4f2d-b2fa-0e5748d80c27 |
      +--------------------------------------+-----------------+--------------------------------------+

   To check Kubernetes cluster works well, please see some tests in
   kuryr-kubernetes to get more information [#fourth]_.

#. Register Kubernetes VIM

   In vim_config.yaml, project_name is fixed as "default", that will use to
   support multi tenant on Kubernetes in the future.

   Create vim_config.yaml file for Kubernetes VIM as the following examples:

   .. code-block:: console

      auth_url: "https://192.168.11.110:6443"
      bearer_token: "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tc2ZqcTQiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6IjBiMzZmYTQ2LWFhOTUtMTFlNy05M2Q4LTQwOGQ1Y2Q0ZmJmMSIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OmRlZmF1bHQifQ.MBjFA18AjD6GyXmlqsdsFpJD_tgPfst2faOimfVob-gBqnAkAU0Op2IEauiBVooFgtvzm-HY2ceArftSlZQQhLDrJGgH0yMAUmYhI8pKcFGd_hxn_Ubk7lPqwR6GIuApkGVMNIlGh7LFLoF23S_yMGvO8CHPM-UbFjpbCOECFdnoHjz-MsMqyoMfGEIF9ga7ZobWcKt_0A4ge22htL2-lCizDvjSFlAj4cID2EM3pnJ1J3GXEqu-W9DUFa0LM9u8fm_AD9hBKVz1dePX1NOWglxxjW4KGJJ8dV9_WEmG2A2B-9Jy6AKW83qqicBjYUUeAKQfjgrTDl6vSJOHYyzCYQ"
      ssl_ca_cert: "None"
      project_name: "default"
      type: "kubernetes"

   Or vim_config.yaml with ssl_ca_cert enabled:

   .. code-block:: console

      auth_url: "https://192.168.11.110:6443"
      bearer_token: "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tc2ZqcTQiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6IjBiMzZmYTQ2LWFhOTUtMTFlNy05M2Q4LTQwOGQ1Y2Q0ZmJmMSIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OmRlZmF1bHQifQ.MBjFA18AjD6GyXmlqsdsFpJD_tgPfst2faOimfVob-gBqnAkAU0Op2IEauiBVooFgtvzm-HY2ceArftSlZQQhLDrJGgH0yMAUmYhI8pKcFGd_hxn_Ubk7lPqwR6GIuApkGVMNIlGh7LFLoF23S_yMGvO8CHPM-UbFjpbCOECFdnoHjz-MsMqyoMfGEIF9ga7ZobWcKt_0A4ge22htL2-lCizDvjSFlAj4cID2EM3pnJ1J3GXEqu-W9DUFa0LM9u8fm_AD9hBKVz1dePX1NOWglxxjW4KGJJ8dV9_WEmG2A2B-9Jy6AKW83qqicBjYUUeAKQfjgrTDl6vSJOHYyzCYQ"
      ssl_ca_cert: "-----BEGIN CERTIFICATE-----
      MIIDUzCCAjugAwIBAgIJANPOjG38TA+fMA0GCSqGSIb3DQEBCwUAMCAxHjAcBgNV
      BAMMFTE3Mi4xNy4wLjJAMTUwNzI5NDI2NTAeFw0xNzEwMDYxMjUxMDVaFw0yNzEw
      MDQxMjUxMDVaMCAxHjAcBgNVBAMMFTE3Mi4xNy4wLjJAMTUwNzI5NDI2NTCCASIw
      DQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAKlPwd5Dp484Fb+SjBZeV8qF4k8s
      Z06NPdlHKuXaxz7+aReGSwz09JittlqQ/2CwSd5834Ll+btfyTyrB4bv+mr/WD3b
      jxEhnWrUK7oHObzZq0i60Ard6CuiWnv5tP0U5tVPWfNBoHEEPImVcUmgzGSAWW1m
      ZzGdcpwkqE1NznLsrqYqjT5bio7KUqySRe13WNichDrdYSqEEQwFa+b+BO1bRCvh
      IYSI0/xT1CDIlPmVucKRn/OVxpuTQ/WuVt7yIMRKIlApsZurZSt7ypR7SlQOLEx/
      xKsVTbMvhcKIMKdK8pHUJK2pk8uNPAKd7zjpiu04KMa3WsUreIJHcjat6lMCAwEA
      AaOBjzCBjDAdBgNVHQ4EFgQUxINzbfoA2RzXk584ETZ0agWDDk8wUAYDVR0jBEkw
      R4AUxINzbfoA2RzXk584ETZ0agWDDk+hJKQiMCAxHjAcBgNVBAMMFTE3Mi4xNy4w
      LjJAMTUwNzI5NDI2NYIJANPOjG38TA+fMAwGA1UdEwQFMAMBAf8wCwYDVR0PBAQD
      AgEGMA0GCSqGSIb3DQEBCwUAA4IBAQB7zNVRX++hUXs7+Fg1H2havCkSe63b/oEM
      J8LPLYWjqdFnLgC+usGq+nhJiuVCqqAIK0dIizGaoXS91hoWuuHWibSlLFRd2wF2
      Go2oL5pgC/0dKW1D6V1Dl+3mmCVYrDnExXybWGtOsvaUmsnt4ugsb+9AfUtWbCA7
      tepBsbAHS62buwNdzrzjJV+GNB6KaIEVVAdZdRx+HaZP2kytOXqxaUchIhMHZHYZ
      U0/5P0Ei56fLqIFO3WXqVj9u615VqX7cad4GQwtSW8sDnZMcQAg8mnR4VqkF8YSs
      MkFnsNNkfqE9ck/D2auMwRl1IaDPVqAFiWiYZZhw8HsG6K4BYEgk
      -----END CERTIFICATE-----"
      project_name: "default"
      type: "kubernetes"

   You can also specify username and password for Kubernetes VIM configuration:

   .. code-block:: console

      auth_url: "https://192.168.11.110:6443"
      username: "admin"
      password: "admin"
      ssl_ca_cert: "-----BEGIN CERTIFICATE-----
      MIIDUzCCAjugAwIBAgIJANPOjG38TA+fMA0GCSqGSIb3DQEBCwUAMCAxHjAcBgNV
      BAMMFTE3Mi4xNy4wLjJAMTUwNzI5NDI2NTAeFw0xNzEwMDYxMjUxMDVaFw0yNzEw
      MDQxMjUxMDVaMCAxHjAcBgNVBAMMFTE3Mi4xNy4wLjJAMTUwNzI5NDI2NTCCASIw
      DQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAKlPwd5Dp484Fb+SjBZeV8qF4k8s
      Z06NPdlHKuXaxz7+aReGSwz09JittlqQ/2CwSd5834Ll+btfyTyrB4bv+mr/WD3b
      jxEhnWrUK7oHObzZq0i60Ard6CuiWnv5tP0U5tVPWfNBoHEEPImVcUmgzGSAWW1m
      ZzGdcpwkqE1NznLsrqYqjT5bio7KUqySRe13WNichDrdYSqEEQwFa+b+BO1bRCvh
      IYSI0/xT1CDIlPmVucKRn/OVxpuTQ/WuVt7yIMRKIlApsZurZSt7ypR7SlQOLEx/
      xKsVTbMvhcKIMKdK8pHUJK2pk8uNPAKd7zjpiu04KMa3WsUreIJHcjat6lMCAwEA
      AaOBjzCBjDAdBgNVHQ4EFgQUxINzbfoA2RzXk584ETZ0agWDDk8wUAYDVR0jBEkw
      R4AUxINzbfoA2RzXk584ETZ0agWDDk+hJKQiMCAxHjAcBgNVBAMMFTE3Mi4xNy4w
      LjJAMTUwNzI5NDI2NYIJANPOjG38TA+fMAwGA1UdEwQFMAMBAf8wCwYDVR0PBAQD
      AgEGMA0GCSqGSIb3DQEBCwUAA4IBAQB7zNVRX++hUXs7+Fg1H2havCkSe63b/oEM
      J8LPLYWjqdFnLgC+usGq+nhJiuVCqqAIK0dIizGaoXS91hoWuuHWibSlLFRd2wF2
      Go2oL5pgC/0dKW1D6V1Dl+3mmCVYrDnExXybWGtOsvaUmsnt4ugsb+9AfUtWbCA7
      tepBsbAHS62buwNdzrzjJV+GNB6KaIEVVAdZdRx+HaZP2kytOXqxaUchIhMHZHYZ
      U0/5P0Ei56fLqIFO3WXqVj9u615VqX7cad4GQwtSW8sDnZMcQAg8mnR4VqkF8YSs
      MkFnsNNkfqE9ck/D2auMwRl1IaDPVqAFiWiYZZhw8HsG6K4BYEgk
      -----END CERTIFICATE-----"
      project_name: "default"
      type: "kubernetes"

   User can change the authentication like username, password, etc. Please see
   Kubernetes document [#fifth]_ to read more information about Kubernetes
   authentication.

   Run Tacker command for register vim:

   .. code-block:: console

      $ openstack vim register --config-file vim_config.yaml vim-kubernetes

      $ openstack vim list
      +--------------------------------------+----------------------------------+----------------+------------+------------+------------------------------------------------------------+-----------+
      | id                                   | tenant_id                        | name           | type       | is_default | placement_attr                                             | status    |
      +--------------------------------------+----------------------------------+----------------+------------+------------+------------------------------------------------------------+-----------+
      | 45456bde-6179-409c-86a1-d8cd93bd0c6d | a6f9b4bc9a4d439faa91518416ec0999 | vim-kubernetes | kubernetes | False      | {u'regions': [u'default', u'kube-public', u'kube-system']} | REACHABLE |
      +--------------------------------------+----------------------------------+----------------+------------+------------+------------------------------------------------------------+-----------+

   In ``placement_attr``, there are three regions: 'default', 'kube-public',
   'kube-system', that map to ``namespace`` in Kubernetes environment.

   Other related commands to Kubernetes VIM:

   .. code-block:: console

      $ cat kubernetes-VIM-update.yaml
      username: "admin"
      password: "admin"
      project_name: "default"
      ssl_ca_cert: "None"
      type: "kubernetes"


      $ tacker vim-update vim-kubernetes --config-file kubernetes-VIM-update.yaml
      $ tacker vim-show vim-kubernetes
      $ tacker vim-delete vim-kubernetes

   When update Kubernetes VIM, user can update VIM information (such as username,
   password, bearer_token and ssl_ca_cert) except auth_url and type of VIM.


References
----------

.. [#first] https://github.com/openstack-dev/devstack/blob/master/doc/source/networking.rst#shared-guest-interface
.. [#second] https://opendev.org/openstack/tacker/src/branch/master/doc/source/install/devstack.rst
.. [#third] https://opendev.org/openstack/tacker/src/branch/master/devstack/local.conf.kubernetes
.. [#fourth] https://github.com/openstack/kuryr-kubernetes/blob/master/doc/source/installation/testing_connectivity.rst
.. [#fifth] https://kubernetes.io/docs/admin/authentication
