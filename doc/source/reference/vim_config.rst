..
    Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
    All Rights Reserved.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
    License for the specific language governing permissions and limitations
    under the License.

======================================
Configuration File for Registering VIM
======================================

For registering a VIM (Virtualized Infrastructure Manager), it is required
to provide a configuration file via ``openstack`` command. Here is an example
of registering a default VIM named as ``my-default-vim``
with a configuration file.

.. code-block:: console

    $ openstack vim register --is-default --config-file vim_config.yaml \
      --description "Some message" my-default-vim


VIM Types
^^^^^^^^^

Tacker supports two types of VIM, OpenStack and Kubernetes, and understands
which type of VIM requested to register from the contents of configuration.

You can prepare the configuration file by using dedicated script. It generates
a given type of VIM configuration. The default VIM type is OpenStack.
In the example below, it generates a configuration for OpenStack with default
parameters. ``TACKER_ROOT`` is the root of tacker's repository on your server.

.. code-block:: console

  $ bash TACKER_ROOT/tools/gen_vim_config.sh
  Config for OpenStack VIM 'vim_config.yaml' generated.

This script is helpful to configure VIM, finds required parameters for
the configuration from your environment.
For OpenStack VIM, parameters are retrieved from environment variables of
OpenStack. On the other hand, for Kubernets VIM, parameters are retrieved
via ``kubectl`` command.
If you use Kubernetes VIM with default parameters, just add option
``-t k8s`` or ``-t kubernetes`` explicitly.

.. code-block:: console

  $ bash TACKER_ROOT/tools/gen_vim_config.sh -t k8s
  Config for Kubernetes VIM 'vim_config.yaml' generated.

Usage
^^^^^

You can configure all parameters with options as referred to help message.
There are three categories of options, ``Common``, ``OpenStack`` and
``Kubernetes``.

``Common`` options are applied to both of types as named.
``-o`` or ``--output`` is for the name of output file,
``-e`` or ``endpoint`` is for specifying a URL of endpoint,
and ``-p`` or ``--project`` is for the name of project.
Other options than ``Common`` for ``OpenStack`` and ``Kubernetes``
are explained in next sections.

.. code-block:: console

  $ bash tools/gen_vim_config.sh -h
  Generate config file for registering Kubernetes VIM

  usage:
    gen_vim_config.sh [-t VIM_TYPE] [-o OUTPUT_FILE] [-e ENDPOINT]
        [-p PROJCT_NAME] [-u USER_NAME] [--token TOKEN] [-c] [-h]

  options:
    All of options are optional.

    1) Common options
      -t|--type VIM_TYPE
        type of VIM.
          * 'openstack' or 'os' for OpenStack
          * 'kubernetes' or 'k8s' for Kubernetes
      -o|--output OUTPUT_FILE
        name of output file, default is 'vim_config.yaml'.
      -e|--endpoint ENDPOINT
        endpoint consists of url and port, such as 'https://127.0.0.1:6443'.
      -p|--project PROJECT_NAME
        name of project in which VIM is registered, default value is
        'admin'.
      -h|--help
        show this message.

    2) Options for OpenStack VIM
      --os-user USER_NAME
        name of OpenStack user, value of 'OS_USERNAME' is used by default.
      --os-password PASSWORD
        password of OpenStack user, value of 'OS_PASSWORD' is used by default.
      --os-project-domain PROJ_DOMAIN
        name of project domain, value of 'OS_PROJECT_DOMAIN_ID' is used by
        default.
      --os-user-domain USER_DOMAIN
        name of user domain, value of 'OS_USER_DOMAIN_ID' is used by default.
      --os-disable-cert-verify
        use this option only if you set 'cert_verify' to False to disable
        verifying against system certificates for keystone.

    3) Options for Kubernetes VIM
      --k8s-token TOKEN
        bearer token.
      --k8s-use-cert
        use SSL CA cert.


OpenStack
---------

This is an example of configuration for OpenStack VIM below
in which all required parameters are included.
It depends on your account information you have already created before
preparing the configuration file.

.. literalinclude:: ../../../samples/vim/vim_config.yaml
    :language: yaml

Auth URL
~~~~~~~~

Endpoint URL of OpenStack.

User Name
~~~~~~~~~

Name of a user for OpenStack VIM. It is usually set as ``OS_USERNAME``.

Password
~~~~~~~~

Password of OpenStack VIM. It is usually set as ``OS_PASSWORD``.

Project Domain
~~~~~~~~~~~~~~

name of project domain, value of ``OS_PROJECT_DOMAIN_ID`` is used by default.

User Domain
~~~~~~~~~~~

use this option only if you set ``cert_verify`` to False to disable verifying
against system certificates for keystone.

Cert Verify
~~~~~~~~~~~

``True`` or ``False`` for activating CERT verification.


Kubernetes
----------

You configure Kubernetes VIM with parameters retrieved from ``kubectl`` command
as described in
:doc:`/install/kubernetes_vim_installation`.
Here is an example of Kubernetes VIM configuration.

.. code-block:: yaml

  auth_url: "https://192.168.33.100:6443"
  project_name: "default"
  bearer_token: "eyJhbGciOiJSUzI1NiIsImtpZCI6IlBRVDgxQkV5VDNVR1M1WGEwUFYxSXFkZFhJWDYzNklvMEp2WklLMnNFdk0ifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJrdWJlLXN5c3RlbSIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJhZG1pbi10b2tlbi12cnpoaiIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50Lm5hbWUiOiJhZG1pbiIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6ImNhY2VmMzEzLTMzYjYtNDQ5MS1iMWUyLTg0NmQ2N2E0OTdkNSIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDprdWJlLXN5c3RlbTphZG1pbiJ9.R76VIWVZnQxa9NG02HIqux1xTJG4i7dkXsp52T4UU8bvNfsfi18kW_p3ZvaNTxw0yABBcmkYZoOBe4MNP5cTP6TtR_ERZoA5QCViasW_u36rSTBT0-MHRPbkXjJYetzYaFYUO-DlJd3194yOtVHtrxUd8D31qw0f1FlP8BHxblDjZkYlgYSjHCxcwEdwlnYaa0SiH2kl6_oCBRFg8cUfXDeTOmH9XEfdrJ6ubJ4OyqG6YjfiKDDiEHgIehy7s7vZGVwVIPy6EhT1YSOIhY5aF-G9nQSg-GK1V9LIq7petFoW_MIEt0yfNQVXy2D1tBhdJEa1bgtVsLmdlrNVf-m3uA"
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
  -----END CERTIFICATE-----"
  type: "kubernetes"

Auth URL
~~~~~~~~

Endpoint URL of Kubernetes.

Project Name
~~~~~~~~~~~~

The name of project.

Bearer Token
~~~~~~~~~~~~

Bearer token required for accessing Kubernetes APIs.

Use SSL CA Cert
~~~~~~~~~~~~~~~

The value of SSL CA Cert for X.509 client authentication. It can be ``None``.

Type
~~~~

Type of VIM to specify it explicitly as ``kubernetes``.
