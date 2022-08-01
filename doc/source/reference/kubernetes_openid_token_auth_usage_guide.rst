============================================
Kubernetes VIM OpenID Token Auth Usage Guide
============================================

Overview
--------
Kubernetes has multiple authentication strategies. This document describes
how Tacker use `OpenID token`_ to authenticate with Kubernetes.

The OpenID token authentication of Kubernetes relies on an external OpenID
provider, and `Keycloak`_ acts as the OpenID provider in this document.

Preparation
-----------

Prerequisites
~~~~~~~~~~~~~

The following packages should be installed:

* Kubernetes
* Docker

Start Keycloak
~~~~~~~~~~~~~~

Create a CSR config file ``csr.cnf``:

.. code-block:: cfg

   [req]
   req_extensions = v3_req
   distinguished_name = req_distinguished_name
   [req_distinguished_name]

   [ v3_req ]
   basicConstraints = CA:FALSE
   keyUsage = nonRepudiation, digitalSignature, keyEncipherment
   subjectAltName = @alt_names

   [alt_names]
   IP.1 = 127.0.0.1
   IP.2 = 192.168.2.33 # Host IP

Generate SSL certificate for Keycloak:

.. code-block:: shell

   #!/bin/bash

   req_conf=csr.cnf
   ssl_dir=/etc/keycloak/ssl
   key_file=$ssl_dir/keycloak.key
   csr_file=$ssl_dir/keycloak.csr
   crt_file=$ssl_dir/keycloak.crt

   k8s_ssl_dir=/etc/kubernetes/pki
   k8s_ca_crt=$k8s_ssl_dir/ca.crt
   k8s_ca_key=$k8s_ssl_dir/ca.key

   # make a directory for storing certificate
   mkdir -p $ssl_dir

   # generate private key
   openssl genrsa -out $key_file 2048

   # generate certificate signing request
   openssl req -new -key $key_file -out $csr_file -subj "/CN=Keycloak" \
   -config $req_conf

   # use Kubernetes's CA for issuing certificate
   openssl x509 -req -in $csr_file -CA $k8s_ca_crt -CAkey $k8s_ca_key \
   -CAcreateserial -out $crt_file -days 365 -extensions v3_req \
   -extfile $req_conf

   # add executeable permission to key file
   chmod 755 $key_file

Starts a Keycloak container with docker:

.. code-block:: console

   $ docker run -d \
     --net=host \
     -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin \
     -e KC_HTTP_PORT=8080 -e KC_HTTPS_PORT=8443 \
     -e KC_HTTPS_CERTIFICATE_FILE=/opt/keycloak/conf/keycloak.crt \
     -e KC_HTTPS_CERTIFICATE_KEY_FILE=/opt/keycloak/conf/keycloak.key \
     -v /etc/keycloak/ssl:/opt/keycloak/conf \
     quay.io/keycloak/keycloak:18.0.2 \
     start-dev

Setup Keycloak
~~~~~~~~~~~~~~

Login to the admin console

* Open the URL https://192.168.2.33:8443/admin with a browser
* Fill in the form with the following values:

  + :guilabel:`Username`: **admin**
  + :guilabel:`Password`: **admin**

Create a realm

* Click :guilabel:`Add realm`
* Fill in the :guilabel:`Name` with **oidc**
* Click :guilabel:`Create`


Create a user

* Click :guilabel:`Users` in the menu
* Click :guilabel:`Add user`
* Fill in the :guilabel:`Username` with **end-user**
* Click :guilabel:`Save`

Set user credentials

* Click :guilabel:`Credentials`
* Fill in the form with the following values:

  + :guilabel:`Password` : **end-user**
  + :guilabel:`Password Confirmation` : **end-user**

* Turn off Temporary
* Click :guilabel:`Save`

Set user attributes

* Click :guilabel:`Attributes`
* Fill in the form with the following values:

  + :guilabel:`Key` : **name**
  + :guilabel:`Value` : **end-user**

* Click :guilabel:`Add`
* Click :guilabel:`Save`

Create a client

* Click :guilabel:`Clients` in the menu
* Click :guilabel:`Create`
* Fill in the :guilabel:`Client ID` with **tacker**
* Click :guilabel:`Save`

Set client type and valid redirect URIs

* Click :guilabel:`Settings`
* Select **confidential** as the :guilabel:`Access Type`
* Fill in the :guilabel:`Valid Redirect URIs` with  **http://***
* Click :guilabel:`Save`

Set client mappers

* Click :guilabel:`Mappers`
* Click :guilabel:`Create`
* Select **User Attribute** as the :guilabel:`Mapper Type`
* Fill in the form with the following values:

  + :guilabel:`Name` : **name**
  + :guilabel:`User Attribute` : **name**
  + :guilabel:`Token Claim Name` : **name**

* Select **String** as the :guilabel:`Claim JSON Type`
* Click :guilabel:`Save`

View client secret

* Click :guilabel:`Credentials` and view the secret.

Setup Kubernetes
~~~~~~~~~~~~~~~~

Add oidc related startup parameters to kube-apiserver manifest file.

.. code-block:: console

   $ cat /etc/kubernetes/manifests/kube-apiserver.yaml

   spec:
     containers:
     - command:
       - kube-apiserver
       - --oidc-issuer-url=https://192.168.2.33:8443/realms/oidc
       - --oidc-client-id=tacker
       - --oidc-username-claim=name
       - --oidc-username-prefix=-
       - --oidc-ca-file=/etc/kubernetes/ssl/ca.crt

.. note::
   After modifying kube-apiserver manifest file, the kube-apiserver will be restarted.

Create a cluster role binding to grant end users permissions to manipulate
Kubernetes resources.

* Create a cluster role binding file ``cluster_role_binding.yaml``:

  .. code-block:: yaml

     kind: ClusterRoleBinding
     apiVersion: rbac.authorization.k8s.io/v1
     metadata:
       name: oidc-cluster-admin-binding
     roleRef:
       kind: ClusterRole
       name: cluster-admin
       apiGroup: rbac.authorization.k8s.io
     subjects:
     - kind: User
       name: end-user

* Create cluster role binding:

  .. code-block:: console

     $ kubectl create -f cluster_role_binding.yaml


Verify
~~~~~~

Get token endpoint from Keycloak:

.. code-block:: console

   $ curl -ks -X GET https://192.168.2.33:8443/realms/oidc/.well-known/openid-configuration | jq -r .token_endpoint

Result:

.. code-block:: console

   https://192.168.2.33:8443/realms/oidc/protocol/openid-connect/token

Get a OpenID token from Keycloak:

.. code-block:: console

   $ ID_TOKEN=$(curl -ks -X POST https://192.168.2.33:8443/realms/oidc/protocol/openid-connect/token \
     -d grant_type=password -d scope=openid  -d username=end-user -d password=end-user \
     -d client_id=tacker -d client_secret=A93HfOUpySm6BjPug9PJdJumjEGUJMhc | jq -r .id_token)
   $ echo $ID_TOKEN

Result:

.. code-block:: console

   eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICIxbC1RMy1KanQ1eHVrNzhYbUVkZDU2Mko4YXRRVF95MU1zS0JDUTBBcklnIn0.eyJleHAiOjE2NjAxMjExNTUsImlhdCI6MTY2MDEyMDg1NSwiYXV0aF90aW1lIjowLCJqdGkiOiIwZjdkNDE2My05Njk1LTQ3MGMtYmE1OC02MWI4NDM4YTU4MzQiLCJpc3MiOiJodHRwczovLzE5Mi4xNjguMi4zMzo4NDQzL3JlYWxtcy9vaWRjIiwiYXVkIjoidGFja2VyIiwic3ViIjoiOGZlZDVhYzctZDY4OS00NWM1LWE5NmQtYTlmN2M3Y2QxZTJjIiwidHlwIjoiSUQiLCJhenAiOiJ0YWNrZXIiLCJzZXNzaW9uX3N0YXRlIjoiNzhiYzhmNDEtMjc4NC00YTU5LWJjOTUtNjNkZDM5YTQ5NjNiIiwiYXRfaGFzaCI6Ik9WczJ3Q29VclU0QWxZaml0dGNQLXciLCJhY3IiOiIxIiwic2lkIjoiNzhiYzhmNDEtMjc4NC00YTU5LWJjOTUtNjNkZDM5YTQ5NjNiIiwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJlbmQtdXNlciJ9.SAncMlpRCLY8JlRUZ7YwirmYs5Qc-5qrvJYmyCZSiRgHyn-7cuqNan3vyVGO46Iv9Da51_Im3L5HaVJTcReeCZ2fhuzgei3yOquPugcfaqKKZEujA042Cc0pFTLS_dPl1xX3XINEcN4nGYGhGtLi8CBH0iANi-IY_VEdxogTyc9MlKgjP9Ca8eYNUPhop49GwLC-ph5vMShS9O834ywtQargb51zokQsoXAYrGBJMTWr37uMxP7UWXpYAQa82OyX3fElpueurd5WGEzGT1AhN1Ad4uIAxgD6dxFsiQYOHRSH-sByV0IwMdZoqIm4GFS6NHLj5usr6PSA5U9QpgCI7Q

Get all namespaces with OpenID token from Kubernetes:

.. code-block:: console

   curl -ks -H "Authorization: Bearer $ID_TOKEN" https://192.168.2.33:6443/api/v1/namespaces

Result:

.. code-block:: console

   {
     "kind": "NamespaceList",
     "apiVersion": "v1",
     ...omit...

View certificates
~~~~~~~~~~~~~~~~~

View Kubernetes CA certificate:

.. code-block:: console

   $ cat /etc/kubernetes/pki/ca.crt
   -----BEGIN CERTIFICATE-----
   MIICwjCCAaqgAwIBAgIBADANBgkqhkiG9w0BAQsFADASMRAwDgYDVQQDEwdrdWJl
   LWNhMB4XDTIwMDgyNjA5MzIzMVoXDTMwMDgyNDA5MzIzMVowEjEQMA4GA1UEAxMH
   a3ViZS1jYTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALxkeE16lPAd
   pfJj5GJMvZJFcX/CD6EB/LUoKwGmqVoOUQPd3b/NGy+qm+3bO9EU73epUPsVaWk2
   Lr+Z1ua7u+iib/OMsfsSXMZ5OEPgd8ilrTGhXOH8jDkif9w1NtooJxYSRcHEwxVo
   +aXdIJhqKdw16NVP/elS9KODFdRZDfQ6vU5oHSg3gO49kgv7CaxFdkF7QEHbchsJ
   0S1nWMPAlUhA5b8IAx0+ecPlMYUGyGQIQgjgtHgeawJebH3PWy32UqfPhkLPzxsy
   TSxk6akiXJTg6mYelscuxPLSe9UqNvHRIUoad3VnkF3+0CJ1z0qvfWIrzX3w92/p
   YsDBZiP6vi8CAwEAAaMjMCEwDgYDVR0PAQH/BAQDAgKkMA8GA1UdEwEB/wQFMAMB
   Af8wDQYJKoZIhvcNAQELBQADggEBAIbv2ulEcQi019jKz4REy7ZyH8+ExIUBBuIz
   InAkfxNNxV83GkdyA9amk+LDoF/IFLMltAMM4b033ZKO5RPrHoDKO+xCA0yegYqU
   BViaUiEXIvi/CcDpT9uh2aNO8wX5T/B0WCLfWFyiK+rr9qcosFYxWSdU0kFeg+Ln
   YAaeFY65ZWpCCyljGpr2Vv11MAq1Tws8rEs3rg601SdKhBmkgcTAcCzHWBXR1P8K
   rfzd6h01HhIomWzM9xrP2/2KlYRvExDLpp9qwOdMSanrszPDuMs52okXgfWnEqlB
   2ZrqgOcTmyFzFh9h2dj1DJWvCvExybRmzWK1e8JMzTb40MEApyY=
   -----END CERTIFICATE-----

View Keycloak certificate:

.. code-block:: console

   $ cat /etc/keycloak/ssl/keycloak.crt
   -----BEGIN CERTIFICATE-----
   MIIC7TCCAdWgAwIBAgIUQK2k5uNvlRLx43LI/t3a2/A/3iQwDQYJKoZIhvcNAQEL
   BQAwFTETMBEGA1UEAxMKa3ViZXJuZXRlczAeFw0yMjA4MDQwNjIwNTFaFw0yMzA4
   MDQwNjIwNTFaMBMxETAPBgNVBAMMCEtleWNsb2FrMIIBIjANBgkqhkiG9w0BAQEF
   AAOCAQ8AMIIBCgKCAQEAni7HWLn2IpUImGO1sbBf/XuqATkXSeIIRuQuFymwYPoX
   BP7RowzrbfF9KUwdIKlz9IXjqb1hplumiqNy1Sc7MmrTY9Fj87MNAMlnCIvyWkjE
   XVXWxGef49mqc85P2K1iuAsr2R7sDrv7SC0ch+lHclOjGDmCjKOk8qF3kD1LATWg
   zf42aXb4nNF9kyIOPEbI+jX4PWhAQpEz5nIG+xIRjTHGfacjpeg0+XOK21wLAuQB
   fqebJ6GxX4OzB37ZtLLgrKyBYWaWuYkWbexVRM3wEvQu8ENkvhV017iPuPHSxNWx
   Y8z072XMs9j8XRQD65EVqObXyizotPRJF4slEJ9qMQIDAQABozcwNTAJBgNVHRME
   AjAAMAsGA1UdDwQEAwIF4DAbBgNVHREEFDAShwR/AAABhwTAqAIhhwQKCgCMMA0G
   CSqGSIb3DQEBCwUAA4IBAQBebjmNHd8sJXjvPQc3uY/3KSDpk9AYfYzhUZvcvLNg
   z0llFqXHaFlMqHTsz1tOH4Ns4PDKKoRT0JIKC1FkvjzqgL+X2jWFS0NRoNyd3W3B
   yHLEL7MdQqDR+tZX02EGfaGXjuy8GHIU4J2hXhohmpn6ntfiRONfY8jaEjIecPFS
   IwZWXNhsDESa1zuDe0PatES/Ati8bAUpN2rb/7rsE/AeM5GXpQfOKV0XxdIeBZ82
   Vf5cUDWPipvq2Q9KS+yrTvEObGtA6gKhQ4bpz3MieU3N8AtQpEKtROH7mJWMHyl2
   roD1k8KeJlfvR/XcVTGFcgIdNLfKIdd99Xfi4gSaIKuw
   -----END CERTIFICATE-----

Deploy CNF with OpenID token
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Please refer to `CNF usage guide`_ to deploy CNF with OpenID token.

.. _OpenID token : https://kubernetes.io/docs/reference/access-authn-authz/authentication/#openid-connect-tokens
.. _Keycloak: https://www.keycloak.org
.. _CNF usage guide: https://docs.openstack.org/tacker/latest/user/etsi_containerized_vnf_usage_guide.html
