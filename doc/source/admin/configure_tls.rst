======================================
Configuring HTTPS/mTLS for Tacker APIs
======================================

This document shows how to set up the HTTPS and two-way TLS as called as Mutual
TLS (mTLS) on Tacker APIs. In this guide, the ``$tacker_host_name`` will be
used as the host name for the Tacker APIs.

.. note::

  The content of this document has been confirmed to work
  using Tacker 2024.1 Caracal.

Preparations
~~~~~~~~~~~~

In order to enable TLS, it is necessary to use a private/public Certificate
Authority (CA) as a root certificate to sign certificates. Although you
typically use certificate issued by a public CA, this guide describes how to
create a private CA to test the HTTPS/mTLS functionality.

.. _Create private key and certificate:

Create a Private Certificate Authority (CA)
-------------------------------------------

If the certificate used for mTLS was issued by a public CA, skip steps 1 and 2.

1. Generate an RSA private key.

   .. code-block:: console

     $ openssl genrsa -out root_a.key 4096


2. Generate a self-signed certificate.

   .. code-block:: console

     $ openssl req -new -x509 -key root_a.key -out root_a.pem -days 365
     You are about to be asked to enter information that will be incorporated
     into your certificate request.
     What you are about to enter is what is called a Distinguished Name or a DN.
     There are quite a few fields but you can leave some blank
     For some fields there will be a default value,
     If you enter '.', the field will be left blank.
     -----
     Country Name (2 letter code) [AU]:JP
     State or Province Name (full name) [Some-State]:Tokyo
     Locality Name (eg, city) []:Musashino
     Organization Name (eg, company) [Internet Widgits Pty Ltd]:OpenstackORG
     Organizational Unit Name (eg, section) []:DevDept
     Common Name (e.g. server FQDN or YOUR name) []:root_a.openstack.host
     Email Address []:


3. If you need to support multiple root certificates, those root certificates
   should be merged and configured on the server. For example, this guide uses
   the root_a.pem created previously, and the root_b.pem created in a same way.
   When creating the root_b.pem, specify the CN as `root_b.openstack.host`.

   In this step, a new multi_ca.pem is created by concatenating two root
   certificates.

   .. code-block:: console

     $ cat root_a.pem >> multi_ca.pem
     $ cat root_b.pem >> multi_ca.pem
     $ cat multi_ca.pem
     -----BEGIN CERTIFICATE-----
     MIIF1TCCA72gAwIBAgIUBAofPmi3cxX3/xvz6n3Pi9KjPW4wDQYJKoZIhvcNAQEL
     BQAwejELMAkGA1UEBhMCSlAxDjAMBgNVBAgMBVRva3lvMRIwEAYDVQQHDAlNdXNh
     ...
     HC1PfWQYli7d+98zz1KXwUkLv9MmBOOnP83wS4upfspTpU1wBK9ZcKFAS5MkpuS6
     0x5atdhal1RlulNblqs6TR5W+uiffCJblQRzDMSLLZVzkAULhWqRRkS7PxtKnc2z
     cidL67MTrzni
     -----END CERTIFICATE-----
     -----BEGIN CERTIFICATE-----
     MIIF1TCCA72gAwIBAgIUICVkJl1df1REQOKdF9VelC3+lEAwDQYJKoZIhvcNAQEL
     BQAwejELMAkGA1UEBhMCSlAxDjAMBgNVBAgMBVRva3lvMRIwEAYDVQQHDAlNdXNh
     ...
     g+kVxAXPwbrZKTsWMvsCvD0xXs3nC/FKmlPx5VL+6smAKPTWQr9M/k+4voviboms
     V59KPLVlmxKE
     -----END CERTIFICATE-----


Create Private Key and Certificate
----------------------------------

In order to enable TLS, it is necessary to create a private key and
certificate. Although you typically use a certificate issued by a public CA,
this guide describes how to create a self-signed certificate using private CA
to test the mTLS functionality. If the certificate used for mTLS was issued by
a public CA, skip these steps.

1. Generate an RSA private key.

   .. code-block:: console

     $ openssl genrsa -out tacker_api.key 4096


2. Create a certificate signing request.

   .. code-block:: console

     $ openssl req -new -key tacker_api.key -out tacker_api.csr
     You are about to be asked to enter information that will be incorporated
     into your certificate request.
     What you are about to enter is what is called a Distinguished Name or a DN.
     There are quite a few fields but you can leave some blank
     For some fields there will be a default value,
     If you enter '.', the field will be left blank.
     -----
     Country Name (2 letter code) [AU]:JP
     State or Province Name (full name) [Some-State]:Tokyo
     Locality Name (eg, city) []:Musashino
     Organization Name (eg, company) [Internet Widgits Pty Ltd]:OpenstackORG
     Organizational Unit Name (eg, section) []:DevDept
     Common Name (e.g. server FQDN or YOUR name) []:$tacker_host_name
     Email Address []:

     Please enter the following 'extra' attributes
     to be sent with your certificate request
     A challenge password []:
     An optional company name []:


3. Use the root certificate created in previous section to self-sign the
   certificate.

   .. code-block:: console

     $ openssl x509 -req -in tacker_api.csr \
     -CA root_a.pem -CAkey root_a.key -CAcreateserial \
     -out tacker_api.pem -days 365 -sha384
     Certificate request self-signature ok
     subject=C = JP, ST = Tokyo, L = Musashino, O = OpenstackORG, OU = DevDept, CN = $tacker_host_name


Guide for Enabling HTTPS
~~~~~~~~~~~~~~~~~~~~~~~~

You can configure HTTPS in Tacker APIs by following these steps.

Configure HTTPS for Tacker APIs
-------------------------------

1. Modify the :doc:`/configuration/config` to enable SSL to implement HTTPS
   support for the Tacker APIs.

   .. code-block:: console

     $ vi /etc/tacker/tacker.conf
     [DEFAULT]

     # Enable SSL on the API server (boolean value)
     use_ssl = true

     # Certificate file to use when starting the server securely (string value)
     ssl_cert_file = /etc/tacker/tacker_api.pem

     # Private key file to use when starting the server securely (string value)
     ssl_key_file = /etc/tacker/tacker_api.key

     [v2_vnfm]

     # Endpoint of VNFM (self). (string value)
     endpoint = https://$tacker_host_name:9890

     [vnf_lcm]

     # endpoint_url (string value)
     endpoint_url = https://$tacker_host_name:9890/


2. Restart tacker service so that the modified configuration information takes
   effect.

   .. code-block:: console

     $ sudo systemctl restart devstack@tacker


Verify HTTPS access to Tacker APIs
----------------------------------

1. Try access the Tacker APIs via HTTPS protocol to confirm that the
   service has been successfully configured.

   .. code-block:: console

     $ curl -i -X GET https://$tacker_host_name:9890/ \
     --cacert multi_ca.pem
     HTTP/1.1 200 OK
     Content-Type: application/json
     Content-Length: 122
     Date: Tue, 01 Oct 2024 03:15:23 GMT

     {"versions": [{"id": "v1.0", "status": "CURRENT", "links": [{"rel": "self", "href": "https://$tacker_host_name:9890/v1.0"}]}]}


2. When Tacker is switched to HTTPS, user can not access the Tacker APIs via
   HTTP protocol.

   .. code-block:: console

     $ curl -i -X GET http://$tacker_host_name:9890/
     curl: (52) Empty reply from server


.. _openstack HTTPS:

Enable Openstack Command to Use HTTPS-enabled Tacker APIs
---------------------------------------------------------

1. You have to set environment variable of the CA certificate to verify the
   Tacker server certificate for accessing HTTPS-enabled Tacker APIs.

   .. code:: console

     $ export OS_CACERT=/opt/stack/certs/multi_ca.pem


2. Change the nfv-orchestration endpoints to access HTTPS-enabled Tacker APIs.

   .. code-block:: console

     $ openstack endpoint list --service nfv-orchestration
     +----------------------------------+-----------+--------------+-------------------+---------+-----------+--------------------------------+
     | ID                               | Region    | Service Name | Service Type      | Enabled | Interface | URL                            |
     +----------------------------------+-----------+--------------+-------------------+---------+-----------+--------------------------------+
     | 1d48e6e978c442b988f22ebc2cf2581e | RegionOne | tacker       | nfv-orchestration | True    | admin     | http://$tacker_host_name:9890/ |
     | 4d687048030942cb8dea98e84ff7d596 | RegionOne | tacker       | nfv-orchestration | True    | internal  | http://$tacker_host_name:9890/ |
     | acd08fcab9164fc89aabbc627771a499 | RegionOne | tacker       | nfv-orchestration | True    | public    | http://$tacker_host_name:9890/ |
     +----------------------------------+-----------+--------------+-------------------+---------+-----------+--------------------------------+

     $ openstack endpoint set 1d48e6e978c442b988f22ebc2cf2581e --url https://$tacker_host_name:9890/
     $ openstack endpoint set 4d687048030942cb8dea98e84ff7d596 --url https://$tacker_host_name:9890/
     $ openstack endpoint set acd08fcab9164fc89aabbc627771a499 --url https://$tacker_host_name:9890/

     $ openstack endpoint list --service nfv-orchestration
     +----------------------------------+-----------+--------------+-------------------+---------+-----------+---------------------------------+
     | ID                               | Region    | Service Name | Service Type      | Enabled | Interface | URL                             |
     +----------------------------------+-----------+--------------+-------------------+---------+-----------+---------------------------------+
     | 1d48e6e978c442b988f22ebc2cf2581e | RegionOne | tacker       | nfv-orchestration | True    | admin     | https://$tacker_host_name:9890/ |
     | 4d687048030942cb8dea98e84ff7d596 | RegionOne | tacker       | nfv-orchestration | True    | internal  | https://$tacker_host_name:9890/ |
     | acd08fcab9164fc89aabbc627771a499 | RegionOne | tacker       | nfv-orchestration | True    | public    | https://$tacker_host_name:9890/ |
     +----------------------------------+-----------+--------------+-------------------+---------+-----------+---------------------------------+


3. Execute a tacker command to confirm that OpenStack command can access the
   Tacker APIs successfully.

   .. code-block:: console

     $ openstack vim list
     +--------------------------------------+--------------+----------------------------------+------------+------------+--------+
     | ID                                   | Name         | Tenant_id                        | Type       | Is Default | Status |
     +--------------------------------------+--------------+----------------------------------+------------+------------+--------+
     | ce04bbe5-3ffe-449f-ba2a-69c0a747b9ad | test-vim-k8s | 2e189ea6c1df4e4ba6d89de254b3a534 | kubernetes | True       | ACTIVE |
     +--------------------------------------+--------------+----------------------------------+------------+------------+--------+
     $ openstack vnf package list
     +--------------------------------------+------------------+------------------+-------------+-------------------+---------------------------------------------------------+
     | Id                                   | Vnf Product Name | Onboarding State | Usage State | Operational State | Links                                                   |
     +--------------------------------------+------------------+------------------+-------------+-------------------+---------------------------------------------------------+
     | 718e94a6-dfbf-48a4-8c6f-eaa541063a1b | Sample VNF       | ONBOARDED        | IN_USE      | ENABLED           | {                                                       |
     |                                      |                  |                  |             |                   |     "self": {                                           |
     |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/718e94a6-     |
     |                                      |                  |                  |             |                   | dfbf-48a4-8c6f-eaa541063a1b"                            |
     |                                      |                  |                  |             |                   |     },                                                  |
     |                                      |                  |                  |             |                   |     "packageContent": {                                 |
     |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/718e94a6-     |
     |                                      |                  |                  |             |                   | dfbf-48a4-8c6f-eaa541063a1b/package_content"            |
     |                                      |                  |                  |             |                   |     }                                                   |
     |                                      |                  |                  |             |                   | }                                                       |
     +--------------------------------------+------------------+------------------+-------------+-------------------+---------------------------------------------------------+
     $ openstack vnflcm list --os-tacker-api-version 2
     +--------------------------------------+-------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
     | ID                                   | VNF Instance Name | Instantiation State | VNF Provider | VNF Software Version | VNF Product Name | VNFD ID                              |
     +--------------------------------------+-------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
     | 703148ca-addc-4226-bee8-ef73d81dbbbf |                   | INSTANTIATED        | Company      | 1.0                  | Sample VNF       | eb37da52-9d03-4544-a1b5-ff5664c7687d |
     +--------------------------------------+-------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+


Guide for Enabling Two-way TLS/mTLS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Two-way TLS as called as mTLS is contemporary versions of TLS `RFC5246`_
`RFC8446`_, that requires not only the server but also the client to send the
Certificate along with CertificateVerify messages during the handshake and for
the server to verify the CertificateVerify and Finished messages. The following
steps describes how to set up mTLS in Tacker APIs.

Configure mTLS for Tacker APIs
------------------------------

.. note::

 In OAuth 2.0 Mutual-TLS client authentication by tls client certificate, you
 have to create the client certificate with the specific Subject Distinguished
 Names, eg: Common Name(CN), that is required by authorization server.


1. Modify the :doc:`/configuration/config` to enable mTLS support for the
   Tacker APIs.

   .. code-block:: console

     $ vi /etc/tacker/tacker.conf
     [DEFAULT]

     # Enable SSL on the API server (boolean value)
     use_ssl = true

     # Certificate file to use when starting the server securely (string value)
     ssl_cert_file = /etc/tacker/tacker_api.pem

     # Private key file to use when starting the server securely (string value)
     ssl_key_file = /etc/tacker/tacker_api.key

     # CA certificate file to use to verify connecting clients (string value)
     ssl_ca_file = /etc/tacker/multi_ca.pem

     [v2_vnfm]

     # Endpoint of VNFM (self). (string value)
     endpoint = https://$tacker_host_name:9890

     [vnf_lcm]

     # endpoint_url (string value)
     endpoint_url = https://$tacker_host_name:9890/


2. Restart tacker service so that the modified configuration information takes
   effect.

   .. code-block:: console

     $ sudo systemctl restart devstack@tacker


Verify mTLS access to Tacker APIs
---------------------------------

1. Try access the Tacker APIs via mTLS protocol to confirm that the service has
   been successfully configured. To access Tacker APIs via mTLS, it is required
   to create a private key and certificate also for the client. You can follow
   the same step in the previous section of :ref:`Create private key and
   certificate` to create the client private key and certificate. In this
   example, private key ``client.key`` and certificate ``client.pem`` is
   created with the root CA which CN is `root_b.openstack.host`.

   .. code-block:: console

     $ curl -i -X GET https://$tacker_host_name:9890/ \
     --cacert multi_ca.pem \
     --cert client.pem \
     --key client.key
     HTTP/1.1 200 OK
     Content-Type: application/json
     Content-Length: 120
     Date: Tue, 01 Oct 2024 05:46:05 GMT

     {"versions": [{"id": "v1.0", "status": "CURRENT", "links": [{"rel": "self", "href": "https://$tacker_host_name:9890/v1.0"}]}]}


2. When Tacker is switched to mTLS, user can not access the Tacker APIs via
   HTTPS protocol meaning without sending client certificate.

   .. code-block:: console

     $ curl -i -X GET https://$tacker_host_name:9890/ \
     --cacert multi_ca.pem
     curl: (56) OpenSSL SSL_read: error:0A00045C:SSL routines::tlsv13 alert certificate required, errno 0


Enable Openstack Command to Use mTLS-enabled Tacker APIs
--------------------------------------------------------

1. For using openstack command to access mTLS-enabled Tacker APIs, addition to
   CA certificate, the client private key and certificate that send to the
   server for verifying the client have to be set in environment variables.

   .. code-block:: console

     $ export OS_CACERT=/opt/stack/certs/multi_ca.pem
     $ export OS_KEY=/opt/stack/certs/client.key
     $ export OS_CERT=/opt/stack/certs/client.pem


2. Change the nfv-orchestration endpoints to access HTTPS-enabled Tacker APIs.

   See :ref:`openstack HTTPS` for details on how to change the endpoints.

3. Execute a tacker command to confirm that OpenStack command can access the
   Tacker APIs successfully.

   .. code-block:: console

     $ openstack vim list
     +--------------------------------------+--------------+----------------------------------+------------+------------+--------+
     | ID                                   | Name         | Tenant_id                        | Type       | Is Default | Status |
     +--------------------------------------+--------------+----------------------------------+------------+------------+--------+
     | ce04bbe5-3ffe-449f-ba2a-69c0a747b9ad | test-vim-k8s | 2e189ea6c1df4e4ba6d89de254b3a534 | kubernetes | True       | ACTIVE |
     +--------------------------------------+--------------+----------------------------------+------------+------------+--------+
     $ openstack vnf package list
     +--------------------------------------+------------------+------------------+-------------+-------------------+---------------------------------------------------------+
     | Id                                   | Vnf Product Name | Onboarding State | Usage State | Operational State | Links                                                   |
     +--------------------------------------+------------------+------------------+-------------+-------------------+---------------------------------------------------------+
     | 718e94a6-dfbf-48a4-8c6f-eaa541063a1b | Sample VNF       | ONBOARDED        | IN_USE      | ENABLED           | {                                                       |
     |                                      |                  |                  |             |                   |     "self": {                                           |
     |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/718e94a6-     |
     |                                      |                  |                  |             |                   | dfbf-48a4-8c6f-eaa541063a1b"                            |
     |                                      |                  |                  |             |                   |     },                                                  |
     |                                      |                  |                  |             |                   |     "packageContent": {                                 |
     |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/718e94a6-     |
     |                                      |                  |                  |             |                   | dfbf-48a4-8c6f-eaa541063a1b/package_content"            |
     |                                      |                  |                  |             |                   |     }                                                   |
     |                                      |                  |                  |             |                   | }                                                       |
     +--------------------------------------+------------------+------------------+-------------+-------------------+---------------------------------------------------------+
     $ openstack vnflcm list --os-tacker-api-version 2
     +--------------------------------------+-------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
     | ID                                   | VNF Instance Name | Instantiation State | VNF Provider | VNF Software Version | VNF Product Name | VNFD ID                              |
     +--------------------------------------+-------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
     | 703148ca-addc-4226-bee8-ef73d81dbbbf |                   | INSTANTIATED        | Company      | 1.0                  | Sample VNF       | eb37da52-9d03-4544-a1b5-ff5664c7687d |
     +--------------------------------------+-------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+


.. _`RFC5246`: https://datatracker.ietf.org/doc/html/rfc5246
.. _`RFC8446`: https://datatracker.ietf.org/doc/html/rfc8446
