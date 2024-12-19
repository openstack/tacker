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

Tacker uses devstack-plugin-container to deploy a Kubernetes cluster.

#. Edit ``local.conf`` for Kubernetes

   Add following plugin configurations for devstack-plugin-container.

   .. code-block:: console

     # Enable devstack-plugin-container, crio
     KUBERNETES_VIM=True

     # It is necessary to specify the patch version
     # because it is the version used when executing "apt-get install" command.
     K8S_VERSION="1.30.5"
     K8S_TOKEN="9agf12.zsu5uh2m4pzt3qba"
     CONTAINER_ENGINE="crio"
     CRIO_VERSION="1.30.5"

     enable_plugin devstack-plugin-container https://opendev.org/openstack/devstack-plugin-container master

   Public network is used to launch LoadBalancer for Services in Kubernetes.
   Setting public subnet is described in [#first]_.

   You can find whole of examples of ``local.conf`` in [#second]_ and [#third]_.

#. In CentOS environment install Kubernetes packages and start ovn services
   before executing stack.sh.

   **Command:**

   .. code-block:: console

      $ sudo cat <<EOF > /etc/yum.repos.d/kubernetes.repo
        [kubernetes]
        name=Kubernetes
        baseurl=https://packages.cloud.google.com/yum/repos/kubernetes-el7-x86_64
        enabled=1
        gpgcheck=1
        repo_gpgcheck=1
        gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
        EOF
      $ sudo chmod 755 /etc/yum.repos.d/kubernetes.repo
      $ sudo dnf install kubeadm -y
      $ sudo yum install -y centos-release-openstack-victoria
      $ sudo yum install -y openvswitch
      $ sudo yum install -y openvswitch-ovn-common
      $ sudo yum install -y openvswitch-ovn-central
      $ sudo yum install -y openvswitch-ovn-host
      $ sudo systemctl start ovn-northd.service
      $ sudo systemctl start ovn-controller.service
      $ sudo systemctl start ovs-vswitchd.service
      $ sudo systemctl start ovsdb-server.service

#. Run devstack installation

   **Command:**

   .. code-block:: console

         $ ./stack.sh

#. Setup Kubernetes VIM configuration

   Now you are ready to register Kubernetes VIM if you complete devstack
   installation.
   You can setup configuration file for Kubernetes VIM by using a dedicated
   script for the job or editing it from scratch.

   The first way is to run ``gen_vim_config.sh`` with options for generating
   the configuration file as described in :doc:`here </reference/vim_config>`.
   Go to ``TACKER_ROOT`` directory which is the root of tacker's repository.
   You need to add ``-t k8s`` at least for Kubernetes, or it generates
   configurations for OpenStack. You can skip steps below before the section
   ``Register Kubernetes VIM``.

   .. code-block:: console

     $ cd TACKER_ROOT
     $ bash tools/gen_vim_config.sh -t k8s

   This script tries to get all required parameters from your environment
   although you can give any of parameters with specific options.
   Refer the usages in help message, ``-h`` option, for the details.

   On the other hand, you're required to get required parameters with
   ``kubectl`` command if you edit the configuration from scratch.

   * Create Secret

     First, you can check whether a Secret containing a bearer token already
     exists. If it does not exist, you can create a Secret according to the
     following file. If it already exists, skip this step and start with
     |get_token|_.

     .. code-block:: console

         $ cat default-token.yaml
         apiVersion: v1
         kind: Secret
         metadata:
           name: default-token-cfx5m
           namespace: default
           annotations:
             kubernetes.io/service-account.name: "default"
         type: kubernetes.io/service-account-token

     Use ``default-token.yaml`` to create a Secret.

     **Command:**

     .. code-block:: console

         $ kubectl apply -f default-token.yaml

     **Result:**

     .. code-block:: console

         secret/default-token-cfx5m created

   .. |get_token| replace:: Get "Bearer Token"
   .. _get_token:

   * Get "Bearer Token"

     You have to confirm Kubernetes Secret name which contains
     bearer token.

     **Command:**

     .. code-block:: console

         $ kubectl get secret

     **Result:**

     .. code-block:: console

         NAME                  TYPE                                  DATA   AGE
         default-token-cfx5m   kubernetes.io/service-account-token   3      94m

     Then, you can get the bearer token.

     **Command:**

     .. code-block:: console

         $ TOKEN=$(kubectl get secret default-token-cfx5m -o jsonpath="{.data.token}" | base64 --decode) && echo $TOKEN

     **Result:**

     .. code-block:: console

         eyJhbGciOiJSUzI1NiIsImtpZCI6ImdTeGhkUlBNRkJwemo0eXdpMmxxT2Y1aWkzYUhwRERCTWlxMzZFemFKSkUifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tY2Z4NW0iLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6IjNhOTNiNjA0LTJjY2EtNDllZi05ODMwLWI5NDZhZjI2OTAyNyIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OmRlZmF1bHQifQ.yWmZMKuCRn_9Hw07wzee2Gr072NcexuKkaG2HaBamd3BOOAaypb7a12UiKcjqQYsDq32jVGMswSroTJOJtm7xccVbU2lz6CMhTRtDbPKOQm7DLyYdpBoRAoqE8fpy4aF5agqpFYmhYHBoz2VC-sgTwWjuY5XkJ81X9rZWlTCj9p3QkanH2z77lLXo-muthDOOuNm_J05FyR_J1epYXm8JbEpTrj1upaQoKZ9hoKKQrd1crW0stqymcyiLxfPGtSW8dO6GZS4v1vTiIhAEBg3kyQsOPz_nEmDxuYXrcMJxQV8MxWvm3uLOu7wN6-MPsSdw1CQdOfjycTh0D9rG4pxUw

     .. note::

         In Kubernetes data model, values contained under ``.data`` is encoded with
         Base64 format, thus you must decode it with ``base64 --decode`` or
         ``base64 -d`` command to use it as a bearer token.

     Before using this token, users have to apply administrator role to this token.

     **Command:**

     .. code-block:: console

         $ kubectl create clusterrolebinding cluster-admin-binding \
         --clusterrole cluster-admin --serviceaccount=default:default

     **Result:**

     .. code-block:: console

         clusterrolebinding.rbac.authorization.k8s.io/cluster-admin-binding created

   * Get ssl_ca_cert:

     Users can get more information for authenticating to Kubernetes cluster.

     **Command:**

     .. code-block:: console

         $ kubectl get secrets default-token-cfx5m -o jsonpath="{.data.ca\.crt}" | base64 --decode

     **Result:**

     .. code-block:: console

         -----BEGIN CERTIFICATE-----
         MIIC5zCCAc+gAwIBAgIBADANBgkqhkiG9w0BAQsFADAVMRMwEQYDVQQDEwprdWJl
         cm5ldGVzMB4XDTIxMDkwOTA0MDc0NFoXDTMxMDkwNzA0MDc0NFowFTETMBEGA1UE
         AxMKa3ViZXJuZXRlczCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAN7H
         /ttxemXTrCDCvN59+g22wwWr5GWUEBxQQz04OPXz1GxBY0H2h3fToRdSs3+snD2h
         6bZ8uryxvXTAlml0IBue/nBxKVRMCRTfqEHEPeNo1yHL2thWGYDfKwEZr9Eg72F5
         mxu9wYdfQS61wg9b4kLmHCIjA58wBDv8Osccs+28BpxJaBd1oG25JWZhcCFRTQur
         URy6d1885ahvaqP9L9mhR8zVzVkAr2noNrCo4/bVMIea8n3yQPBKe3ND1UcxpoCk
         UrfWCrrFsG93RtiivLFJjG8UgUkUhzRfTFoMnTX51Qm2/q/5GZqXSd6z+nU7Bp47
         DHa0hNSPpKnRnP2WwdECAwEAAaNCMEAwDgYDVR0PAQH/BAQDAgKkMA8GA1UdEwEB
         /wQFMAMBAf8wHQYDVR0OBBYEFICl4EHfUar/PBfVTfgymIYXe/z5MA0GCSqGSIb3
         DQEBCwUAA4IBAQA8i+HhuNIJZheNfLgZ+svxmpa1AtdPv8QTrkXTn5OvBJ6l2A2e
         23fVG+8Eolmd0pwuWCMGv4UKAQ45hCMFKMkuKNs2akYueujTxTLwsIu+1EAVnzWp
         E5n+RAhgkAZ18VAGW0otrP/T2zFvci9o3pnEYnQ9Es1mFX7GkBbiI/4qYqx5ysZr
         i5We9jMO//ouJxliJAemRCHMjdqrooMb3k0QyT2lN/1O0TXj0a96pTxoAyivllwk
         LYnc2CoRegU81LeUPSNJRe5+A6kdXixL12F1182/LQgXWkdRnYwoMypyEUDEr9kf
         eGr2fBQ+2ywKH7Ho/HVRW+WcJbXt5nfMX5NK
         -----END CERTIFICATE-----

   * Get Kubernetes server url

     By default Kubernetes API server listens on https://127.0.0.1:6443 and
     https://{HOST_IP}:6443. Users can get this information through
     ``kubectl cluster-info`` command and try to access API server with
     the bearer token described in the previous step.

     First, you have to confirm the API endpoint that your Kubernetes cluster exposes.

     **Command:**

     .. code-block:: console

         $ kubectl cluster-info

     **Result:**

     .. code-block:: console

         Kubernetes control plane is running at https://172.30.202.39:6443

         To further debug and diagnose cluster problems, use 'kubectl cluster-info dump'.

     Then, you can confirm the API endpoint and your bearer token are available.

     **Command:**

     .. code-block:: console

         $ curl -k https://172.30.202.39:6443/api/ -H "Authorization: Bearer $TOKEN"

     **Result:**

     .. code-block:: console

         {
            "kind": "APIVersions",
            "versions": [
            "v1"
            ],
            "serverAddressByClientCIDRs": [
               {
                  "clientCIDR": "0.0.0.0/0",
                  "serverAddress": "172.30.202.39:6443"
               }
            ]
         }

     .. note::

         Because SSL certificate used in Kubernetes API server is self-signed,
         curl returns SSL certificate problem in the response. Users can use
         ``-k`` or ``--insecure`` option to ignore SSL certificate warnings, or
         ``--cacert <path/to/ssl_ca_cert_file>`` option to use ssl_ca_cert
         in the verification of API server's SSL certificate.

#. Register Kubernetes VIM

   In ``vim_config.yaml``, project_name is fixed as "default", that will use
   to support multi tenant on Kubernetes in the future.

   Create ``vim_config.yaml`` file for Kubernetes VIM as following examples:

   .. code-block:: console

         auth_url: "https://172.30.202.39:6443"
         bearer_token: "eyJhbGciOiJSUzI1NiIsImtpZCI6ImdTeGhkUlBNRkJwemo0eXdpMmxxT2Y1aWkzYUhwRERCTWlxMzZFemFKSkUifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tY2Z4NW0iLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6IjNhOTNiNjA0LTJjY2EtNDllZi05ODMwLWI5NDZhZjI2OTAyNyIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OmRlZmF1bHQifQ.yWmZMKuCRn_9Hw07wzee2Gr072NcexuKkaG2HaBamd3BOOAaypb7a12UiKcjqQYsDq32jVGMswSroTJOJtm7xccVbU2lz6CMhTRtDbPKOQm7DLyYdpBoRAoqE8fpy4aF5agqpFYmhYHBoz2VC-sgTwWjuY5XkJ81X9rZWlTCj9p3QkanH2z77lLXo-muthDOOuNm_J05FyR_J1epYXm8JbEpTrj1upaQoKZ9hoKKQrd1crW0stqymcyiLxfPGtSW8dO6GZS4v1vTiIhAEBg3kyQsOPz_nEmDxuYXrcMJxQV8MxWvm3uLOu7wN6-MPsSdw1CQdOfjycTh0D9rG4pxUw"
         ssl_ca_cert: "None"
         project_name: "default"
         type: "kubernetes"

   Or ``vim_config.yaml`` with ``ssl_ca_cert`` enabled:

   .. code-block:: console

         auth_url: "https://172.30.202.39:6443"
         bearer_token: "eyJhbGciOiJSUzI1NiIsImtpZCI6ImdTeGhkUlBNRkJwemo0eXdpMmxxT2Y1aWkzYUhwRERCTWlxMzZFemFKSkUifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tY2Z4NW0iLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6IjNhOTNiNjA0LTJjY2EtNDllZi05ODMwLWI5NDZhZjI2OTAyNyIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OmRlZmF1bHQifQ.yWmZMKuCRn_9Hw07wzee2Gr072NcexuKkaG2HaBamd3BOOAaypb7a12UiKcjqQYsDq32jVGMswSroTJOJtm7xccVbU2lz6CMhTRtDbPKOQm7DLyYdpBoRAoqE8fpy4aF5agqpFYmhYHBoz2VC-sgTwWjuY5XkJ81X9rZWlTCj9p3QkanH2z77lLXo-muthDOOuNm_J05FyR_J1epYXm8JbEpTrj1upaQoKZ9hoKKQrd1crW0stqymcyiLxfPGtSW8dO6GZS4v1vTiIhAEBg3kyQsOPz_nEmDxuYXrcMJxQV8MxWvm3uLOu7wN6-MPsSdw1CQdOfjycTh0D9rG4pxUw"
         ssl_ca_cert: "-----BEGIN CERTIFICATE-----
         MIIC5zCCAc+gAwIBAgIBADANBgkqhkiG9w0BAQsFADAVMRMwEQYDVQQDEwprdWJl
         cm5ldGVzMB4XDTIxMDkwOTA0MDc0NFoXDTMxMDkwNzA0MDc0NFowFTETMBEGA1UE
         AxMKa3ViZXJuZXRlczCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAN7H
         /ttxemXTrCDCvN59+g22wwWr5GWUEBxQQz04OPXz1GxBY0H2h3fToRdSs3+snD2h
         6bZ8uryxvXTAlml0IBue/nBxKVRMCRTfqEHEPeNo1yHL2thWGYDfKwEZr9Eg72F5
         mxu9wYdfQS61wg9b4kLmHCIjA58wBDv8Osccs+28BpxJaBd1oG25JWZhcCFRTQur
         URy6d1885ahvaqP9L9mhR8zVzVkAr2noNrCo4/bVMIea8n3yQPBKe3ND1UcxpoCk
         UrfWCrrFsG93RtiivLFJjG8UgUkUhzRfTFoMnTX51Qm2/q/5GZqXSd6z+nU7Bp47
         DHa0hNSPpKnRnP2WwdECAwEAAaNCMEAwDgYDVR0PAQH/BAQDAgKkMA8GA1UdEwEB
         /wQFMAMBAf8wHQYDVR0OBBYEFICl4EHfUar/PBfVTfgymIYXe/z5MA0GCSqGSIb3
         DQEBCwUAA4IBAQA8i+HhuNIJZheNfLgZ+svxmpa1AtdPv8QTrkXTn5OvBJ6l2A2e
         23fVG+8Eolmd0pwuWCMGv4UKAQ45hCMFKMkuKNs2akYueujTxTLwsIu+1EAVnzWp
         E5n+RAhgkAZ18VAGW0otrP/T2zFvci9o3pnEYnQ9Es1mFX7GkBbiI/4qYqx5ysZr
         i5We9jMO//ouJxliJAemRCHMjdqrooMb3k0QyT2lN/1O0TXj0a96pTxoAyivllwk
         LYnc2CoRegU81LeUPSNJRe5+A6kdXixL12F1182/LQgXWkdRnYwoMypyEUDEr9kf
         eGr2fBQ+2ywKH7Ho/HVRW+WcJbXt5nfMX5NK
         -----END CERTIFICATE-----"
         project_name: "default"
         type: "kubernetes"

   Run Tacker command for register VIM:

   **Command:**

   .. code-block:: console

         $ openstack vim register --config-file vim_config.yaml vim-kubernetes

   **Result:**

   .. code-block:: console

         +----------------+-----------------------------------------------+
         | Field          | Value                                         |
         +----------------+-----------------------------------------------+
         | auth_cred      | {                                             |
         |                |     "bearer_token": "***",                    |
         |                |     "ssl_ca_cert": "None",                    |
         |                |     "auth_url": "https://172.30.202.39:6443", |
         |                |     "username": "None",                       |
         |                |     "key_type": "barbican_key",               |
         |                |     "secret_uuid": "***",                     |
         |                |     "password": "***"                         |
         |                | }                                             |
         | auth_url       | https://172.30.202.39:6443                    |
         | created_at     | 2021-09-17 01:26:28.372552                    |
         | description    |                                               |
         | id             | 884ec305-c8ca-47ef-8cba-fafceabeda30          |
         | is_default     | False                                         |
         | name           | vim-kubernetes                                |
         | placement_attr | {                                             |
         |                |     "regions": [                              |
         |                |         "default",                            |
         |                |         "kube-node-lease",                    |
         |                |         "kube-public",                        |
         |                |         "kube-system"                         |
         |                |     ]                                         |
         |                | }                                             |
         | project_id     | 8cd3cc798ae14227a84f7b50c5ef984a              |
         | status         | ACTIVE                                        |
         | type           | kubernetes                                    |
         | updated_at     | None                                          |
         | vim_project    | {                                             |
         |                |     "name": "default"                         |
         |                | }                                             |
         +----------------+-----------------------------------------------+

   In ``placement_attr``, there are four regions: 'default', 'kube-node-lease',
   'kube-public' and 'kube-system', that map to ``namespace`` in Kubernetes environment.

   After the successful installation of VIM, you can get VIM information as follows:

   **Command:**

   .. code-block:: console

         $ openstack vim list

   **Result:**

   .. code-block:: console

         +--------------------------------------+----------------+----------------------------------+------------+------------+--------+
         | ID                                   | Name           | Tenant_id                        | Type       | Is Default | Status |
         +--------------------------------------+----------------+----------------------------------+------------+------------+--------+
         | 884ec305-c8ca-47ef-8cba-fafceabeda30 | vim-kubernetes | 8cd3cc798ae14227a84f7b50c5ef984a | kubernetes | False      | ACTIVE |
         +--------------------------------------+----------------+----------------------------------+------------+------------+--------+

   You can update those VIM information with :command:`openstack vim set`:

   **Command:**

   .. code-block:: console

         $ openstack vim set --config-file path/to/updated/config 884ec305-c8ca-47ef-8cba-fafceabeda30

   When updating Kubernetes VIM, you can update VIM information (such as bearer_token
   and ssl_ca_cert) except auth_url and type of VIM.

   You can get the detail of VIM information with :command:`openstack vim show`:

   **Command:**

   .. code-block:: console

         $ openstack vim show 884ec305-c8ca-47ef-8cba-fafceabeda30

   If you no longer use the Kubernetes VIM, you can delete it with :command:`openstack vim delete`:

   **Command:**

   .. code-block:: console

         $ openstack vim delete 884ec305-c8ca-47ef-8cba-fafceabeda30


References
----------

.. [#first] https://github.com/openstack-dev/devstack/blob/master/doc/source/networking.rst#shared-guest-interface
.. [#second] https://docs.openstack.org/tacker/latest/install/devstack.html
.. [#third] https://opendev.org/openstack/tacker/src/branch/master/devstack/local.conf.kubernetes
