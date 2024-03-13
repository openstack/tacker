===============================================
ETSI NFV-SOL CNF (Containerized VNF) Deployment
===============================================

This section covers how to deploy ETSI NFV-SOL containerized VNF
in Tacker v2 API using Kubernetes VIM.

Overview
--------

The following figure shows an overview of the CNF deployment.

1. Request create VNF

   A user requests tacker-server to create a VNF with tacker-client by
   uploading a VNF Package and requesting ``create VNF``. The VNF Package
   should contain ``CNF Definition`` in addition to ``VNFD``. The detailed
   explanation of ``CNF Definition`` and ``VNFD`` can be found in
   `2. Create a Kubernetes Object File`_ and `5. Create VNFD`_,
   respectively.

2. Request instantiate VNF

   A user requests tacker-server to instantiate the created VNF by requesting
   ``instantiate VNF`` with instantiate parameters.

3. Call Kubernetes API

   Upon receiving a request from tacker-client, tacker-server redirects it to
   tacker-conductor. In tacker-conductor, the request is redirected again to
   an appropriate infra-driver (in this case Kubernetes infra-driver) according
   to the contents of the instantiate parameters. Then, Kubernetes
   infra-driver calls Kubernetes APIs to create a Pod as a VNF.

4. Create a Pod

   Kubernetes Master creates a Pod according to the API calls.

.. figure:: img/deployment.svg


Prepare Kubernetes VIM
----------------------

1. Create a Config File
~~~~~~~~~~~~~~~~~~~~~~~

Before register a Kubernetes VIM to tacker, we should create config file.
The following ``vim-k8s.yaml`` file provides necessary information to
register a Kubernetes VIM.
This sample specifies the values of the ``bearer_token`` and ``ssl_ca_cert``
parameters that can be obtained from the Kubernetes Master-node.
For specific methods of obtaining "bearer_token" and "ssl_ca_cert",
please refer to :doc:`/install/kubernetes_vim_installation`.

.. code-block:: console

  $ cat vim-k8s.yaml
  auth_url: "https://192.168.56.10:6443"
  bearer_token: "eyJhbGciOiJSUzI1NiIsImtpZCI6IkdVazBPakx4Q2NsUjJjNHhsZFdaaXJMSHVQMUo4NkdMS0toamlSaENiVFUifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tazhzdmltIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQubmFtZSI6ImRlZmF1bHQiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiJhNTIzYzFhMi1jYmU5LTQ1Y2YtYTc5YS00ZDA4MDYwZDE3NmEiLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6ZGVmYXVsdDpkZWZhdWx0In0.BpKAAQLjXMIpJIjqQDsGtyh1a-Ij8e-YOVRv0md_iOGXd1KLR-qreM6xA-Ni8WFILzq3phaZU6npET8PlfhQ6csF5u20OT2SoZ7iAotHXpCcYkRdrUd2oO5KxSFTkOhasaN1pQ3pZyaFYUZbwwmLK3I31rG4Br2VbZQ7Qu8wFOXUK-syBGF48vIPZ5JQ3K00KNxpuEcGybMK5LtdSKZ25Ozp_I2oqm3KBZMPMfWwaUnvuRnyly13tsiXudPt_9H78AxLubMo3rcvECJU2y_zZLiavcZKXAz-UmHulxtz_XZ80hMu-XOpYWEYrOB0Lt0hB59ZoY1y3OvJElTfPyrwWw"
  ssl_ca_cert: "-----BEGIN CERTIFICATE-----
  MIIDBTCCAe2gAwIBAgIIa76wZDxLNAowDQYJKoZIhvcNAQELBQAwFTETMBEGA1UE
  AxMKa3ViZXJuZXRlczAeFw0yMzExMDYwMDA3MzBaFw0zMzExMDMwMDEyMzBaMBUx
  EzARBgNVBAMTCmt1YmVybmV0ZXMwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEK
  AoIBAQDd0LBXGxVexr09mVFNSXWQq3TN66IIcXCBAMbIWI4EiQ8Y0zI4hSwADdK2
  ltYSdWw7wq3/YTFHK8/YTY7Jvd9/k3UJrqkZ6kBtL20pJUPXNJVLE/hRzsqEnHHv
  cfqYZTHvTY4g7qNcMOcfl/oDUGUMfpQT2gs6xoNl0WX/1+QeQbadx1kWaD2Ii45F
  d8TR+c4wccxNaLArk3ok4h1PNeAwra4mRmBHQQ2wFjkTYGl4+ss3v1yoUJkrQjXL
  RgzLufeXaz8eRTi36HkjudGKfS3OnUeke3uBN7usW58FFJ8TdKOhuoguRm53kj6+
  TwXtZCOPzn4gNxq6xJE1Xj2hwFfpAgMBAAGjWTBXMA4GA1UdDwEB/wQEAwICpDAP
  BgNVHRMBAf8EBTADAQH/MB0GA1UdDgQWBBRdmQ4r63pXBHIO8ODqxROE7x+aizAV
  BgNVHREEDjAMggprdWJlcm5ldGVzMA0GCSqGSIb3DQEBCwUAA4IBAQBeQ/9+bzRe
  qbA02MfYnN3vycGhDObcAoiDIMIutojFTpx4hGZjqVgTRpLH5ReddwR4kkxn3NRg
  weCVkNkhzyGze64nb11qZG71olaOQRMYzyN2hYfmbq7MXSvmJQQYIr1OewaRk+xl
  TyG1XRXoD2IEaHEvG0+pQJlDerd5Z6S1fkPaKZtcRbM/E6y5VXMV6hegN4MwHZSI
  Ll1uEBTxUzzTm3dnl1KL8GDg05ajoYcyL3X/0aWsb/MFhtIlXe2CMxu5qUkLBhzy
  fCfX4cZpI5KFxMgdmAEoaGbNy7iqsGrLFtEmub2gdEBIVNr7vgOk4OeQ9Uodj6K7
  jK97z+cupc5G
  -----END CERTIFICATE-----"
  project_name: "admin"
  type: "kubernetes"


In addition to using ``bearer_token`` to authenticate with Kubernetes,
`OpenID Connect Tokens`_ is also supported. The following sample specifies
``oidc_token_url``, ``client_id``, ``client_secret``, ``username``, ``password``
instead of ``bearer_token`` for OpenID token authentication.

Before using OpenID token authentication, additional settings are required.
Please refer to :doc:`/admin/kubernetes_openid_token_auth_usage_guide`,
and how to get the values of the ``oidc_token_url``,
``client_id``, ``client_secret``, ``username``, ``password`` and ``ssl_ca_cert``
parameters is documented.

The SSL certificates of Kubernetes and OpenID provider are concatenated
in ``ssl_ca_cert``.

.. code-block:: console

  $ cat vim-k8s.yaml
  auth_url: "https://192.168.33.100:6443"
  project_name: "default"
  oidc_token_url: "https://192.168.33.100:8443/realms/oidc/protocol/openid-connect/token"
  client_id: "tacker"
  client_secret: "A93HfOUpySm6BjPug9PJdJumjEGUJMhc"
  username: "end-user"
  password: "end-user"
  ssl_ca_cert: "-----BEGIN CERTIFICATE-----
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
  -----END CERTIFICATE-----"
  type: "kubernetes"


2. Register Kubernetes VIM
~~~~~~~~~~~~~~~~~~~~~~~~~~

We could register Kubernetes VIM to tacker by running the following command:

.. code-block:: console

  $ openstack vim register --config-file CONFIG_FILE KUBERNETES_VIM_NAME --fit-width


Config file in the chapter 1 need to be input by parameter --config-file.
After successful execution, VIM information will be displayed.
For example, id.
We can also use authentication methods such as username and password to
register Kubernetes VIM. For details, please refer to the hyperlink in
the chapter 1.


.. code-block:: console

  $ openstack vim register --config-file vim-k8s.yaml test-vim-k8s --fit-width --is-default
  +----------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field          | Value                                                                                                                                                                                                                                     |
  +----------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | auth_cred      | {                                                                                                                                                                                                                                         |
  |                |     "bearer_token": "***",                                                                                                                                                                                                                |
  |                |     "ssl_ca_cert": "b'gAAAAABlVGfZpWGEYn2hjBEVpkFOTZ4lt8xtMagfzpmoaHNXMzCwKX8Sd8eDCBnwXnsN-whaBvcOu0qb9DCyo2BjqR8fBmtxhbOVDNUofPtbebkgmVFnwFUyacZxLBk-                                                                                    |
  |                | l8AHqQnQOK5wkIUWabsCYhZcA7r800jH9ZysLHRmW5pTRAc_n6CtSvgXoShqzL0L1AlxA5omgac2gXkrulBvJDpnKJhXSCnYkWsJyWtDTDnwTTt8IZvuec_Rh9C0b4bAFLNCmwSw2KRtJTepQcsHtL9vXRZOcS2WJcgg3J_DxNGIcxAUacAcTc8CX7MB5c_DSMOD5lrLPk93Sr-                           |
  |                | 0XzODPib4ar4C8Kzs4fiYki6BWnwWHbcmZMtXClnTZIu3iLhKDG_GNAp9dhMrRUNFX3I8HRfWzMmp7EComQGkkE0vlJ8LRavWPRspKTx92ubwkatYrfKlyVoS2uBsc8jBum94hsquERInVSoUrKwlnyNfn7ecSr2W_1M4LWo2GU8joEYBBUM6oHomV_Sl0yIdXpEofd-                                  |
  |                | kYWWP0PO7CY9KgNrJU7Iqyn4ZgKBWhH6qfL-xEmGndgE2Xt4ZKPKdWWquXXhXtz7fz51LmpQwGvZR4-qFYa9B6XEC0odvQVW0xzZl36C6nTREP4TuOodos3iMUy89iKDzk52JgLUDkU-k-MtROzdA0BwNqlLKzwslOFuaXe7P1Khf7oS7TjgG1vMdr9t_K2dacMdNhJEtwb-                              |
  |                | lTlFr6JEAbsd852EM45rUegG3_PKqxv5XgKczCrcAsJhTRW-RhxyWk_bpSS1skJGUJdMEhEvQss0ilZfnOw3TunKZXk66c-2LG9EG4e49B15nUQ6H6V-8G-POSBg0qpDVeaniIxmKSiExrQEzrh7lfR-                                                                                  |
  |                | avvGst02FuqEzsg82hojgpMbDSW643JYjGRgcSFrcFvydsYVNCPg8BJatGnXd4tqPeniDXJOOIg5qgj3_ful7PeMY08mjHfPHaiaI3xLszmJGLP1pCz-IPliaogi77ZNegvU7Z5_FtQE56J9pWF2NUZRyP92OveEKfTpQbPSLSiLUofxTq7oYoWVZfZnEOaewV0z8A-                                   |
  |                | b7VrG267kgWS7mboQb0sIeegpzQgA3HMX0wG8FCuBxqvmxyIWUf7M1rPa6QcTfv8ZBFCs5lbxjs8tNw86pCKELa1FfuIwuVu9yGPHDrAoUWH_Lq93SAl9VYEJbvVo05OxA8kxLU3qFxLP0A6DBGxoOhIDznrY5WzMLJ6K53PI1D8-ESYhhIukSHlgClcopMk0ywsF1URyF8HO4TaIf4N0-                    |
  |                | HJFq95pZArLlmtBr6WmXXrpkDuH-ASGVnObTMLp7oQuJY1kQNmktlstuo54MW5FiLvL0pod2Og0k46_UofpA3mkYGM2dE6DtajACPpOQl7DR7NFFtY-9MGzvf8s3OiOWkq7I3mZnag2fYfMERcly5_a0ipIGoTcQkNCmIn9seC8x-                                                             |
  |                | 3odxGHUwIilhr7mnuXNKvHzuVvmXrYiBVnzgwuajZ37VYKY4y9K90BeIWPEF63vZRwlXuRoDTP9WGwbojv2PJkPHHn8Tg=='",                                                                                                                                        |
  |                |     "auth_url": "https://192.168.56.10:6443",                                                                                                                                                                                             |
  |                |     "username": "None",                                                                                                                                                                                                                   |
  |                |     "key_type": "barbican_key",                                                                                                                                                                                                           |
  |                |     "secret_uuid": "***"                                                                                                                                                                                                                  |
  |                | }                                                                                                                                                                                                                                         |
  | auth_url       | https://192.168.56.10:6443                                                                                                                                                                                                                |
  | created_at     | 2023-11-15 06:40:25.544685                                                                                                                                                                                                                |
  | description    |                                                                                                                                                                                                                                           |
  | extra          |                                                                                                                                                                                                                                           |
  | id             | 290ae639-5b47-42b6-b1b0-c1623f6d856a                                                                                                                                                                                                      |
  | is_default     | True                                                                                                                                                                                                                                      |
  | name           | test-vim-k8s                                                                                                                                                                                                                              |
  | placement_attr | {                                                                                                                                                                                                                                         |
  |                |     "regions": [                                                                                                                                                                                                                          |
  |                |         "default",                                                                                                                                                                                                                        |
  |                |         "kube-node-lease",                                                                                                                                                                                                                |
  |                |         "kube-public",                                                                                                                                                                                                                    |
  |                |         "kube-system"                                                                                                                                                                                                                     |
  |                |     ]                                                                                                                                                                                                                                     |
  |                | }                                                                                                                                                                                                                                         |
  | project_id     | ebbc6cf1a03d49918c8e408535d87268                                                                                                                                                                                                          |
  | status         | ACTIVE                                                                                                                                                                                                                                    |
  | type           | kubernetes                                                                                                                                                                                                                                |
  | updated_at     | None                                                                                                                                                                                                                                      |
  | vim_project    | {                                                                                                                                                                                                                                         |
  |                |     "name": "admin"                                                                                                                                                                                                                       |
  |                | }                                                                                                                                                                                                                                         |
  +----------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


Also we can check if the status of VIM is ACTIVE by
:command:`openstack vim list` command.

.. code-block:: console

  $ openstack vim list
  +--------------------------------------+--------------+----------------------------------+------------+------------+--------+
  | ID                                   | Name         | Tenant_id                        | Type       | Is Default | Status |
  +--------------------------------------+--------------+----------------------------------+------------+------------+--------+
  | 290ae639-5b47-42b6-b1b0-c1623f6d856a | test-vim-k8s | ebbc6cf1a03d49918c8e408535d87268 | kubernetes | True       | ACTIVE |
  +--------------------------------------+--------------+----------------------------------+------------+------------+--------+


Prepare VNF Package
-------------------

As an example, you can create a VNF Package as follow.

.. code-block:: console

  $ python3 -m pip install TACKER_ROOT
  $ cd TACKER_ROOT/samples/tests/functional/sol_kubernetes_v2/test_instantiate_cnf_resources
  $ python3 pkggen.py
  $ ll
  ...
  drwxr-xr-x  6 stack stack  4096 Nov  5 23:46 contents/
  -rw-r--r--  1 stack stack  3921 Nov  5 23:46 pkggen.py
  -rw-rw-r--  1 stack stack 28783 Nov 15 07:15 test_instantiate_cnf_resources.zip
  ...


.. note::

  In this document, ``TACKER_ROOT`` is the root of tacker's repository on
  the server.


After you have done the above, you will have the sample VNF package
`test_instantiate_cnf_resources.zip`.

You can also create a VNF Package manually by following the steps.


1. Create Directories of VNF Package
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TOSCA YAML CSAR file is an archive file using the ZIP file format whose
structure complies with the TOSCA Simple Profile YAML v1.2 Specification.
Here is a sample of building a VNF Package CSAR directory:

.. code-block:: console

  $ mkdir -p deployment/{TOSCA-Metadata,Definitions,Files/kubernetes}


2. Create a Kubernetes Object File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A CSAR VNF package shall have a object file that defines Kubernetes resources
to be deployed.
The file name shall have an extension of ".yaml".
Different Kubernetes api resources can be created according to the content of
different yaml files.

.. note::

  Please refer to `Kubernetes API resource`_ for an example yaml file
  of each resource.


The following is a simple example of ``deployment`` resource.

.. code-block:: console

  $ cat ./deployment/Files/kubernetes/deployment.yaml
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: vdu1
    namespace: default
  spec:
    replicas: 2
    selector:
      matchLabels:
        app: webserver
    template:
      metadata:
        labels:
          app: webserver
      spec:
        containers:
        - name: nginx
          image: nginx
          resources:
            limits:
              memory: "200Mi"
            requests:
              memory: "100Mi"
          imagePullPolicy: IfNotPresent
          ports:
          - containerPort: 80
            protocol: TCP
    strategy:
      type: RollingUpdate


.. note::

  ``metadata.name`` in this file should be the same as
  ``properties.name`` of the corresponding VDU in the deployment flavor
  definition file.
  For the example in this procedure, ``metadata.name`` is same as
  ``topology_template.node_templates.VDU1.properties.name``
  in the sample_cnf_df_simple.yaml file.


3. Create a TOSCA.meta File
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The TOSCA.meta file contains version information for the TOSCA.meta file, CSAR,
Definitions file, and artifact file.
Name, content-Type, encryption method, and hash value of the Artifact file are
required in the TOSCA.meta file.
Here is an example of a TOSCA.meta file:

.. code-block:: console

  $ cat ./deployment/TOSCA-Metadata/TOSCA.meta
  TOSCA-Meta-File-Version: 1.0
  Created-by: dummy_user
  CSAR-Version: 1.1
  Entry-Definitions: Definitions/sample_cnf_top.vnfd.yaml

  Name: Files/kubernetes/deployment.yaml
  Content-Type: test-data
  Algorithm: SHA-256
  Hash: 36cab1efa2e3e0fb983816010450dbccf491ae905ba4012778a351cc73b420a7


4. Download ETSI Definition File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download official documents.
ETSI GS NFV-SOL 001 [i.4] specifies the structure and format of the VNFD based
on TOSCA specifications.

.. code-block:: console

  $ cd deployment/Definitions
  $ wget https://forge.etsi.org/rep/nfv/SOL001/raw/v2.6.1/etsi_nfv_sol001_common_types.yaml
  $ wget https://forge.etsi.org/rep/nfv/SOL001/raw/v2.6.1/etsi_nfv_sol001_vnfd_types.yaml


5. Create VNFD
~~~~~~~~~~~~~~

How to create VNFD composed of plural deployment flavours is described in
VNF Descriptor (VNFD) based on ETSI NFV-SOL001,
please refer to :doc:`/user/vnfd-sol001`.

VNFD will not contain any Kubernetes resource information such as VDU,
Connection points, Virtual links because all required components of CNF will be
specified in Kubernetes resource files.

Following is an example of a VNFD file includes the definition of VNF.

.. code-block:: console

  $ cat sample_cnf_top.vnfd.yaml
  tosca_definitions_version: tosca_simple_yaml_1_2

  description: Sample VNF

  imports:
    - etsi_nfv_sol001_common_types.yaml
    - etsi_nfv_sol001_vnfd_types.yaml
    - sample_cnf_types.yaml
    - sample_cnf_df_simple.yaml

  topology_template:
    inputs:
      selected_flavour:
        type: string
        description: VNF deployment flavour selected by the consumer. It is provided in the API

    node_templates:
      VNF:
        type: company.provider.VNF
        properties:
          flavour_id: { get_input: selected_flavour }
          descriptor_id: b1bb0ce7-ebca-4fa7-95ed-4840d7000000
          provider: Company
          product_name: Sample VNF
          software_version: '1.0'
          descriptor_version: '1.0'
          vnfm_info:
            - Tacker
        requirements:
          #- virtual_link_external # mapped in lower-level templates
          #- virtual_link_internal # mapped in lower-level templates


The ``sample_cnf_types.yaml`` file defines the parameter types and default
values of the VNF.

.. code-block:: console

  $ cat sample_cnf_types.yaml
  tosca_definitions_version: tosca_simple_yaml_1_2

  description: VNF type definition

  imports:
    - etsi_nfv_sol001_common_types.yaml
    - etsi_nfv_sol001_vnfd_types.yaml

  node_types:
    company.provider.VNF:
      derived_from: tosca.nodes.nfv.VNF
      properties:
        descriptor_id:
          type: string
          constraints: [ valid_values: [ b1bb0ce7-ebca-4fa7-95ed-4840d7000000 ] ]
          default: b1bb0ce7-ebca-4fa7-95ed-4840d7000000
        descriptor_version:
          type: string
          constraints: [ valid_values: [ '1.0' ] ]
          default: '1.0'
        provider:
          type: string
          constraints: [ valid_values: [ 'Company' ] ]
          default: 'Company'
        product_name:
          type: string
          constraints: [ valid_values: [ 'Sample VNF' ] ]
          default: 'Sample VNF'
        software_version:
          type: string
          constraints: [ valid_values: [ '1.0' ] ]
          default: '1.0'
        vnfm_info:
          type: list
          entry_schema:
            type: string
            constraints: [ valid_values: [ Tacker ] ]
          default: [ Tacker ]
        flavour_id:
          type: string
          constraints: [ valid_values: [ simple,complex ] ]
          default: simple
        flavour_description:
          type: string
          default: ""
      requirements:
        - virtual_link_external:
            capability: tosca.capabilities.nfv.VirtualLinkable
        - virtual_link_internal:
            capability: tosca.capabilities.nfv.VirtualLinkable
      interfaces:
        Vnflcm:
          type: tosca.interfaces.nfv.Vnflcm


``sample_cnf_df_simple.yaml`` defines the parameter type of VNF input.

.. code-block:: console

  $ cat sample_cnf_df_simple.yaml
  tosca_definitions_version: tosca_simple_yaml_1_2

  description: Simple deployment flavour for Sample VNF

  imports:
    - etsi_nfv_sol001_common_types.yaml
    - etsi_nfv_sol001_vnfd_types.yaml
    - sample_cnf_types.yaml

  topology_template:
    inputs:
      descriptor_id:
        type: string
      descriptor_version:
        type: string
      provider:
        type: string
      product_name:
        type: string
      software_version:
        type: string
      vnfm_info:
        type: list
        entry_schema:
          type: string
      flavour_id:
        type: string
      flavour_description:
        type: string

    substitution_mappings:
      node_type: company.provider.VNF
      properties:
        flavour_id: simple
      requirements:
        virtual_link_external: []

    node_templates:
      VNF:
        type: company.provider.VNF
        properties:
          flavour_description: A simple flavour

      VDU1:
        type: tosca.nodes.nfv.Vdu.Compute
        properties:
          name: vdu1
          description: VDU1 compute node
          vdu_profile:
            min_number_of_instances: 1
            max_number_of_instances: 3

    policies:
      - scaling_aspects:
          type: tosca.policies.nfv.ScalingAspects
          properties:
            aspects:
              vdu1_aspect:
                name: vdu1_aspect
                description: vdu1 scaling aspect
                max_scale_level: 2
                step_deltas:
                  - delta_1

      - VDU1_initial_delta:
          type: tosca.policies.nfv.VduInitialDelta
          properties:
            initial_delta:
              number_of_instances: 2
          targets: [ VDU1 ]

      - VDU1_scaling_aspect_deltas:
          type: tosca.policies.nfv.VduScalingAspectDeltas
          properties:
            aspect: vdu1_aspect
            deltas:
              delta_1:
                number_of_instances: 1
          targets: [ VDU1 ]

      - instantiation_levels:
          type: tosca.policies.nfv.InstantiationLevels
          properties:
            levels:
              instantiation_level_1:
                description: Smallest size
                scale_info:
                  vdu1_aspect:
                    scale_level: 1
              instantiation_level_2:
                description: Largest size
                scale_info:
                  vdu1_aspect:
                    scale_level: 2
            default_level: instantiation_level_1

      - VDU1_instantiation_levels:
          type: tosca.policies.nfv.VduInstantiationLevels
          properties:
            levels:
              instantiation_level_1:
                number_of_instances: 2
              instantiation_level_2:
                number_of_instances: 3
          targets: [ VDU1 ]


.. note::

  ``VDU1.properties.name`` should be same as ``metadata.name`` that
  defined in Kubernetes object file.
  Therefore, ``VDU1.properties.name`` should be followed naming rules
  of Kubernetes resource name. About detail of naming rules, please
  refer to Kubernetes document `DNS Subdomain Names`_.


6. Compress VNF Package
~~~~~~~~~~~~~~~~~~~~~~~

CSAR Package should be compressed into a ZIP file for uploading.
Following commands are an example of compressing a VNF Package:

.. code-block:: console

  $ cd -
  $ cd ./deployment
  $ zip deployment.zip -r Definitions/ Files/ TOSCA-Metadata/
  adding: Definitions/ (stored 0%)
  adding: Definitions/sample_cnf_top.vnfd.yaml (deflated 54%)
  adding: Definitions/sample_cnf_df_simple.yaml (deflated 76%)
  adding: Definitions/etsi_nfv_sol001_vnfd_types.yaml (deflated 83%)
  adding: Definitions/etsi_nfv_sol001_common_types.yaml (deflated 76%)
  adding: Definitions/sample_cnf_types.yaml (deflated 70%)
  adding: Files/ (stored 0%)
  adding: Files/kubernetes/ (stored 0%)
  adding: Files/kubernetes/deployment.yaml (deflated 50%)
  adding: TOSCA-Metadata/ (stored 0%)
  adding: TOSCA-Metadata/TOSCA.meta (deflated 23%)
  $ ls deployment
  deployment.zip    Definitions    Files    TOSCA-Metadata


Create and Upload VNF Package
-----------------------------

We need to create an empty VNF package object in tacker and upload compressed
VNF package created in previous section.

1. Create VNF Package
~~~~~~~~~~~~~~~~~~~~~

An empty vnf package could be created by command
:command:`openstack vnf package create`.
After create a VNF Package successfully, some information including ID, Links,
Onboarding State, Operational State, and Usage State will be returned.
When the Onboarding State is CREATED, the Operational State is DISABLED,
and the Usage State is NOT_IN_USE, indicate the creation is successful.

.. code-block:: console

  $ openstack vnf package create
  +-------------------+-------------------------------------------------------------------------------------------------+
  | Field             | Value                                                                                           |
  +-------------------+-------------------------------------------------------------------------------------------------+
  | ID                | ea4d29b3-bf2c-437c-a4a2-69b37208d21a                                                            |
  | Links             | {                                                                                               |
  |                   |     "self": {                                                                                   |
  |                   |         "href": "/vnfpkgm/v1/vnf_packages/ea4d29b3-bf2c-437c-a4a2-69b37208d21a"                 |
  |                   |     },                                                                                          |
  |                   |     "packageContent": {                                                                         |
  |                   |         "href": "/vnfpkgm/v1/vnf_packages/ea4d29b3-bf2c-437c-a4a2-69b37208d21a/package_content" |
  |                   |     }                                                                                           |
  |                   | }                                                                                               |
  | Onboarding State  | CREATED                                                                                         |
  | Operational State | DISABLED                                                                                        |
  | Usage State       | NOT_IN_USE                                                                                      |
  | User Defined Data | {}                                                                                              |
  +-------------------+-------------------------------------------------------------------------------------------------+


2. Upload VNF Package
~~~~~~~~~~~~~~~~~~~~~

Upload the VNF package created above in to the VNF Package by running the
following command
:command:`openstack vnf package upload --path <path of vnf package>
<vnf package ID>`
Here is an example of upload VNF package:

.. code-block:: console

  $ openstack vnf package upload --path deployment.zip VNF_PACKAGE_ID
  Upload request for VNF package ea4d29b3-bf2c-437c-a4a2-69b37208d21a has been accepted.


3. Check VNF Package Status
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check the VNF Package Status by :command:`openstack vnf package list` command.
Find the item which the id is same as the created vnf package id, when the
Onboarding State is ONBOARDED, and the Operational State is ENABLED, and the
Usage State is NOT_IN_USE, indicate the VNF Package is uploaded successfully.

.. code-block:: console

  $ openstack vnf package list
  +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
  | Id                                   | Vnf Product Name | Onboarding State | Usage State | Operational State | Links                                                                                           |
  +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
  | ea4d29b3-bf2c-437c-a4a2-69b37208d21a | Sample VNF       | ONBOARDED        | NOT_IN_USE  | ENABLED           | {                                                                                               |
  |                                      |                  |                  |             |                   |     "self": {                                                                                   |
  |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/ea4d29b3-bf2c-437c-a4a2-69b37208d21a"                 |
  |                                      |                  |                  |             |                   |     },                                                                                          |
  |                                      |                  |                  |             |                   |     "packageContent": {                                                                         |
  |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/ea4d29b3-bf2c-437c-a4a2-69b37208d21a/package_content" |
  |                                      |                  |                  |             |                   |     }                                                                                           |
  |                                      |                  |                  |             |                   | }                                                                                               |
  +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+


Create VNF
----------

1. Get VNFD ID
~~~~~~~~~~~~~~

The VNFD ID of a uploaded vnf package could be found by
:command:`openstack vnf package show <VNF package ID>` command.
Here is an example of checking VNFD-ID value:

.. code-block:: console

  $ openstack vnf package show VNF_PACKAGE_ID
  +----------------------+-------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field                | Value                                                                                                                                           |
  +----------------------+-------------------------------------------------------------------------------------------------------------------------------------------------+
  | Additional Artifacts | [                                                                                                                                               |
  |                      |     {                                                                                                                                           |
  |                      |         "artifactPath": "Files/kubernetes/deployment.yaml",                                                                                     |
  |                      |         "checksum": {                                                                                                                           |
  |                      |             "algorithm": "SHA-256",                                                                                                             |
  |                      |             "hash": "36cab1efa2e3e0fb983816010450dbccf491ae905ba4012778a351cc73b420a7"                                                          |
  |                      |         },                                                                                                                                      |
  |                      |         "metadata": {}                                                                                                                          |
  |                      |     }                                                                                                                                           |
  |                      | ]                                                                                                                                               |
  | Checksum             | {                                                                                                                                               |
  |                      |     "hash": "3ab4ea9ee8c125b52dd1fd1cb656a17668173b18a9f1d7fe18146e310e940851cddc2a07a9d081cf8a2a239b4d3b8025d4d328951b87e535d3f8fc788f15d6ea", |
  |                      |     "algorithm": "sha512"                                                                                                                       |
  |                      | }                                                                                                                                               |
  | ID                   | ea4d29b3-bf2c-437c-a4a2-69b37208d21a                                                                                                            |
  | Links                | {                                                                                                                                               |
  |                      |     "self": {                                                                                                                                   |
  |                      |         "href": "/vnfpkgm/v1/vnf_packages/ea4d29b3-bf2c-437c-a4a2-69b37208d21a"                                                                 |
  |                      |     },                                                                                                                                          |
  |                      |     "packageContent": {                                                                                                                         |
  |                      |         "href": "/vnfpkgm/v1/vnf_packages/ea4d29b3-bf2c-437c-a4a2-69b37208d21a/package_content"                                                 |
  |                      |     }                                                                                                                                           |
  |                      | }                                                                                                                                               |
  | Onboarding State     | ONBOARDED                                                                                                                                       |
  | Operational State    | ENABLED                                                                                                                                         |
  | Software Images      |                                                                                                                                                 |
  | Usage State          | NOT_IN_USE                                                                                                                                      |
  | User Defined Data    | {}                                                                                                                                              |
  | VNF Product Name     | Sample VNF                                                                                                                                      |
  | VNF Provider         | Company                                                                                                                                         |
  | VNF Software Version | 1.0                                                                                                                                             |
  | VNFD ID              | b1bb0ce7-ebca-4fa7-95ed-4840d7000000                                                                                                            |
  | VNFD Version         | 1.0                                                                                                                                             |
  +----------------------+-------------------------------------------------------------------------------------------------------------------------------------------------+


2. Execute Create VNF Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We could create VNF by running :command:`openstack vnflcm create <VNFD ID>`.
After the command is executed, the generated ID is ``VNF instance ID``.

.. code-block:: console

  $ openstack vnflcm create VNFD_ID --os-tacker-api-version 2
  +-----------------------------+------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                            |
  +-----------------------------+------------------------------------------------------------------------------------------------------------------+
  | ID                          | 431b94b5-d7ba-4d1c-aa26-ecec65d7ee53                                                                             |
  | Instantiation State         | NOT_INSTANTIATED                                                                                                 |
  | Links                       | {                                                                                                                |
  |                             |     "self": {                                                                                                    |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/431b94b5-d7ba-4d1c-aa26-ecec65d7ee53"             |
  |                             |     },                                                                                                           |
  |                             |     "instantiate": {                                                                                             |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/431b94b5-d7ba-4d1c-aa26-ecec65d7ee53/instantiate" |
  |                             |     }                                                                                                            |
  |                             | }                                                                                                                |
  | VNF Configurable Properties |                                                                                                                  |
  | VNF Instance Description    |                                                                                                                  |
  | VNF Instance Name           |                                                                                                                  |
  | VNF Product Name            | Sample VNF                                                                                                       |
  | VNF Provider                | Company                                                                                                          |
  | VNF Software Version        | 1.0                                                                                                              |
  | VNFD ID                     | b1bb0ce7-ebca-4fa7-95ed-4840d7000000                                                                             |
  | VNFD Version                | 1.0                                                                                                              |
  +-----------------------------+------------------------------------------------------------------------------------------------------------------+


Instantiate VNF
---------------

1. Set the Value to the Request Parameter File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get the ID of target VIM.

.. code-block:: console

  $ openstack vim list
  +--------------------------------------+--------------+----------------------------------+------------+------------+--------+
  | ID                                   | Name         | Tenant_id                        | Type       | Is Default | Status |
  +--------------------------------------+--------------+----------------------------------+------------+------------+--------+
  | 290ae639-5b47-42b6-b1b0-c1623f6d856a | test-vim-k8s | ebbc6cf1a03d49918c8e408535d87268 | kubernetes | True       | ACTIVE |
  +--------------------------------------+--------------+----------------------------------+------------+------------+--------+


A json file includes path of Kubernetes resource definition file and Kubernetes
VIM information should be provided while instantiating a containerized VNF.
Here is an example of json file:

``additionalParams`` includes path of Kubernetes resource definition file,
notice that ``lcm-kubernetes-def-files`` should be a list. A user can also
specify the ``namespace`` where the resource needs to be deployed.

.. note::

  The ``namespace`` for the VNF instantiation is determined by the
  following priority.

  1. If a ``namespace`` is specified in the additionalParams
     of the instantiate request, the specified ``namespace`` is used.
  2. If a ``namespace`` is not specified by the method described
     in 1, a ``namespace`` under metadata defined in
     `2. Create a Kubernetes Object File`_ is used.
  3. If a ``namespace`` is not specified by the method described in 2,
     the default namespace called ``default`` is used.


.. warning::

  If the multiple namespaces are specified in the manifest by the
  method described in 2, the VNF instantiation will fail.


The vimConnectionInfo includes id whose value can be defined autonomously,
vimId and vimType.

.. code-block:: console

  $ cat ./instance_kubernetes.json
  {
    "flavourId": "simple",
    "vimConnectionInfo": {
      "vim1": {
        "vimId": "290ae639-5b47-42b6-b1b0-c1623f6d856a",
        "vimType": "ETSINFV.KUBERNETES.V_1"
      }
    },
    "additionalParams": {
      "lcm-kubernetes-def-files": [
        "Files/kubernetes/deployment.yaml"
      ]
    }
  }


.. note::

  This operation can specify the ``vimConnectionInfo``
  for the VNF instance.
  Even if this operation specify multiple ``vimConnectionInfo``
  associated with one VNF instance, only one of them will be used for
  life cycle management operations.


.. note::

  The resources are created in the order of `lcm-kubernetes-def-files` list.
  Therefore, users are required to specify the `lcm-kubernetes-def-files`
  list in the correct order.


2. Execute the Instantiation Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute the following CLI command to instantiate the VNF instance.

.. code-block:: console

  $ openstack vnflcm instantiate VNF_INSTANCE_ID \
    instance_kubernetes.json --os-tacker-api-version 2
  Instantiate request for VNF Instance 431b94b5-d7ba-4d1c-aa26-ecec65d7ee53 has been accepted.


The ``VNF_INSTANCE_ID`` is the ID generated after the create command
is executed.
We can find it in the `2. Execute Create VNF Command`_ chapter.


3. Check the Instantiation State
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We could check the Instantiation State by running the following command.
When the Instantiation State is INSTANTIATED, indicate the instantiation is
successful.

.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID \
    -c 'Instantiation State' --os-tacker-api-version 2
  +---------------------+--------------+
  | Field               | Value        |
  +---------------------+--------------+
  | Instantiation State | INSTANTIATED |
  +---------------------+--------------+


4. Check the Deployment in Kubernetes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To test a containerized VNF is running in target Kubernetes VIM environment,
we can check by running the following command.
When the READY is 2/2, indicate the deployment is created successfully.

.. code-block:: console

  $ kubectl get deploy
  NAME   READY   UP-TO-DATE   AVAILABLE   AGE
  vdu1   2/2     2            2           7m35s


If we want to check whether the resource is deployed in the default namespace,
we can append ``-A`` to the command line.

.. code-block:: console

  $ kubectl get deploy -A
  NAMESPACE     NAME               READY   UP-TO-DATE   AVAILABLE   AGE
  default       vdu1               2/2     2            2           8m46s
  kube-system   kuryr-controller   1/1     1            1           10d


.. note::

  If a value other than ``default`` is specified for the namespace
  during instantiate, the deployed resources will be instantiated
  in the corresponding namespace.


Terminate VNF
-------------

1. Execute the Termination Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute the following CLI command to terminate the VNF instance.

.. code-block:: console

  $ openstack vnflcm terminate VNF_INSTANCE_ID --os-tacker-api-version 2
  Terminate request for VNF Instance '431b94b5-d7ba-4d1c-aa26-ecec65d7ee53' has been accepted.


2. Check the Instantiation State
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We could check the Instantiation State by running the following command.
When the Instantiation State is NOT_INSTANTIATED, indicate the termination
is successful.

.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID \
    -c 'Instantiation State' --os-tacker-api-version 2
  +---------------------+------------------+
  | Field               | Value            |
  +---------------------+------------------+
  | Instantiation State | NOT_INSTANTIATED |
  +---------------------+------------------+


Delete VNF Identifier
---------------------

1. Execute the Delete Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute the following CLI command to delete the VNF instance.

.. code-block:: console

  $ openstack vnflcm delete VNF_INSTANCE_ID --os-tacker-api-version 2
  Vnf instance '431b94b5-d7ba-4d1c-aa26-ecec65d7ee53' is deleted successfully


2. Check the State
~~~~~~~~~~~~~~~~~~

Execute the following CLI command and confirm that
VNF instance deletion is successful.

* Confirm that the 'Usage State' of VNF Package is 'NOT_IN_USE'.
* Confirm that the VNF instance is not found.

.. code-block:: console

  $ openstack vnf package show VNF_PACKAGE_ID -c 'Usage State'
  +-------------+------------+
  | Field       | Value      |
  +-------------+------------+
  | Usage State | NOT_IN_USE |
  +-------------+------------+


.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID --os-tacker-api-version 2
  VnfInstance 431b94b5-d7ba-4d1c-aa26-ecec65d7ee53 not found.


Supported versions
------------------

Tacker Antelope release

- Kubernetes: 1.25

Tacker Bobcat release

- Kubernetes: 1.26


History of Checks
-----------------

The content of this document has been confirmed to work
using the following VNF Package.

* `test_instantiate_cnf_resources for 2023.2 Bobcat`_


.. _Kubernetes API resource: https://opendev.org/openstack/tacker/src/branch/master/tacker/tests/unit/vnfm/infra_drivers/kubernetes/kubernetes_api_resource
.. _DNS Subdomain Names: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#dns-subdomain-names
.. _OpenID Connect Tokens: https://kubernetes.io/docs/reference/access-authn-authz/authentication/#openid-connect-tokens
.. _test_instantiate_cnf_resources for 2023.2 Bobcat:
  https://opendev.org/openstack/tacker/src/branch/stable/2023.2/tacker/tests/functional/sol_kubernetes_v2/samples/test_instantiate_cnf_resources
