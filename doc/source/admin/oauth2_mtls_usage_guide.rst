==============================
Using OAuth2.0 mTLS for Tacker
==============================

Overview
~~~~~~~~
OAuth2.0 Mutual-TLS (mTLS) Client Authentication based on `RFC8705`_ is
implemented as an extension of Tacker. As an API client, Tacker can use an
mTLS connection to access the LCM Notification server, External Monitoring
tool server and External NFVO server.

.. _RFC8705: https://datatracker.ietf.org/doc/html/rfc8705

Guide
~~~~~
Enable Tacker server to support mTLS Client Authentication by the
following steps in this guide. In this example, ``tacker.host`` is the domain
name used by the Tacker server.


Create a private/public Certificate Authority (CA)
--------------------------------------------------
In order to use mTLS, it is necessary to create a private/public Certificate
Authority (CA) as a root certificate that will be used to sign client and
Tacker certificates. Although you typically use certificate issued by a public
CA, this guide describes how to create a private CA to test the mTLS
functionality. If the certificate used for mTLS authentication was issued by a
public CA, skip steps 1 and 2.

1. Generate an RSA private key.
   The ``oenssl genrsa`` command creates a private key. The options are:.

   * -out keyfile

     - Output the private key to the path specified by keyflie.

   * number

     - Create a key with the key length (bits) specified by number.

   .. code-block:: console

      $ openssl genrsa -out root_a.key 4096
      Generating RSA private key, 4096 bit long modulus (2 primes)
      .++++
      .........................++++
      e is 65537 (0x010001)

2. Generate a self-signed certificate.
   The ``openssl req`` command creates a certificate signing request (CSR).
   The options are:.

   * -new

     - Create a new CSR.

   * -x509

     - Create a CSR in x 509 format.

   * -key keyfile

     - Use keyflie as input for CSR creation.

   * -out csrfile

     - Output the CSR to the path specified by csrflie.

   * -days n

     - Set the certificate to expire in n days.

   .. code-block:: console

      $ openssl req -new -x509 -key root_a.key -out root_a.pem -days 365
      You are about to be asked to enter information that will be incorporated
      into your certificate request.
      What you are about to enter is what is called a Distinguished Name or a DN.
      There are quite a few fields but you can leave some blank
      For some fields there will be a default value,
      If you enter '.', the field will be left blank.
      -----
      Country Name (2 letter code) [AU]:
      State or Province Name (full name) [Some-State]:
      Locality Name (eg, city) []:
      Organization Name (eg, company) [Internet Widgits Pty Ltd]: IssuingORG
      Organizational Unit Name (eg, section) []: CertDept
      Common Name (e.g. server FQDN or YOUR name) []: root_a.openstack.host
      Email Address []: root_a@issuing.org
      Please enter the following 'extra' attributes
      to be sent with your certificate request
      A challenge password []:
      An optional company name []:

3. If you need to support multiple root certificates, these root certificates
   should be merged and configured on the server. As multiple root
   certificates, this guide uses the root_a.pem created in the previous
   procedure and the root_b.pem created in a same way. When creating the
   root_b.pem, specify the CN as "root_b.openstack.host".

   A new multi_ca.pem is created in this step. When two "BEGIN ... END"
   sections are displayed using the cat command, you can see that the creation
   has succeeded.

   .. code-block:: console

      $ cat root_a.pem >> multi_ca.pem
      $ cat root_b.pem >> multi_ca.pem
      $ cat multi_ca.pem
      -----BEGIN CERTIFICATE-----
      MIIF1TCCA72gAwIBAgIUN7d0MTiikDjDMLxUQ8SJcV97Nz8wDQYJKoZIhvcNAQEL
      BQAwejELMAkGA1UEBhMCSlAxEDAOBgNVBAgMB2ppYW5nc3UxDzANBgNVBAcMBnN1
      ...
      K/k00vZmrZXONglaf/OeMalhiRaOTsK2CzEvg6Xgu1zOjtNshm6qnSEXDYxzJue2
      FPLDGEMKSCLb
      -----END CERTIFICATE-----
      -----BEGIN CERTIFICATE-----
      MIIF1TCCA72gAwIBAgIUOiAEZWTheMS5wFA661G6bushkg4wDQYJKoZIhvcNAQEL
      BQAwejELMAkGA1UEBhMCY24xEDAOBgNVBAgMB2ppYW5nc3UxDzANBgNVBAcMBnN1
      ...
      UzvplIZcNZKzgOLLrSkk42/yqxdTZnc3BeBiVsA5T6aapNbY8D6ZpPU2cYYSxrfK
      VpOanJoJy22J
      -----END CERTIFICATE-----

Create private key and client certificate
-----------------------------------------
In order to use mTLS, it is necessary to create a private key and client
certificate. Although you typically use a certificate issued by a public CA,
this guide describes how to create a self-signed certificate to test the mTLS
functionality. If the certificate used for mTLS authentication was issued by a
public CA, skip steps 1 to 3.

1. Generate an RSA private key.

   .. code-block:: console

      $ openssl genrsa -out tacker_priv.key 4096
      Generating RSA private key, 4096 bit long modulus (2 primes)
      .........................................+++++
      .........................+++++
      e is 65537 (0x010001)

2. Create a certificate signing request.

   .. code-block:: console

      $ openssl req -new -key tacker_priv.key -out tacker_csr.csr
      You are about to be asked to enter information that will be incorporated
      into your certificate request.
      What you are about to enter is what is called a Distinguished Name or a DN.
      There are quite a few fields but you can leave some blank
      For some fields there will be a default value,
      If you enter '.', the field will be left blank.
      -----
      Country Name (2 letter code) [AU]:
      State or Province Name (full name) [Some-State]:
      Locality Name (eg, city) []:
      Organization Name (eg, company) [Internet Widgits Pty Ltd]: OpenstackORG
      Organizational Unit Name (eg, section) []: DevDept
      Common Name (e.g. server FQDN or YOUR name) []:tacker.host
      Email Address []: dev@tacker.host
      Please enter the following 'extra' attributes
      to be sent with your certificate request
      A challenge password []:
      An optional company name []:

3. Use the root certificate to generate a self-signed certificate.
   The ``oenssl x509`` command creates a certificate file. The options are:

   * -req

     - Use CSR as an input.

   * -in csrfile

     - Use csrflie as input for certificate creation.

   * -CA cafile

     - Use cafile as the certificate of the signing CA.

   * -CAkey keyfile

     - Use keyfile as the CA private key.

   * -CAcreateserial

     - Generate serial numbers automatically.

   * -out certfile

     - Output the certificate to the path specified by certflie.

   * -days n

     - Set the certificate to expire in n days.

   * -sha384

     - Use the sha 384 algorithm to create a message digest of the certificate.

   .. code-block:: console

      $ openssl x509 -req -in tacker_csr.csr \
      -CA root_a.pem -CAkey root_a.key -CAcreateserial \
      -out tacker_ca.pem -days 365 -sha384
      Signature ok
      subject=C = JP, ST = Tokyo, L = Chiyoda-ku, O = OpenstackORG, OU = DevDept, CN = tacker.host, emailAddress = dev@tacker.host
      Getting CA Private Key

4. Merge the key and certificate into a single file. When two "BEGIN ... END"
   sections are displayed using the cat command, you can see that the merge
   has succeeded.

   .. code-block:: console

      $ cat tacker_ca.pem >> tacker_cert_and_key.pem
      $ cat tacker_priv.key >> tacker_cert_and_key.pem
      $ cat tacker_cert_and_key.pem
      -----BEGIN CERTIFICATE-----
      MIIEdzCCAl8CFGfZSo8q0f0AkmFHrDYAgOygq+X0MA0GCSqGSIb3DQEBCwUAMFYx
      CzAJBgNVBAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRl
      ...
      kMgBy0mLyN84vqY2GItKdYrBsEUWSif6i3tVTDa1r0gpf2o4PPOHUAaelStm3eqU
      KFoR418Y432RaxCEPrDOh11PAY80A/xDBhKPYM5XdRlRNtaMmdM4R2p2vw==
      -----END CERTIFICATE-----
      -----BEGIN RSA PRIVATE KEY-----
      MIIEpAIBAAKCAQEAt82fxcWknYkcXUuBZkk1f4M93peFh7PAgpXPMAcknp8dzm97
      0veZnyh8a4PP7NBGPoKbuBERsVbd6O6HKn4qd8SYehyQ5oYbUVg5n1YsBnPHVq40
      ...
      4CmYegzdMh+VcDkN5vQu1wUSucqCXvzIVgNnbvmxbE7ZuDhCAHNhOvs5jPc1sh79
      qAEY3/z0kZ3muKc3y9GqjdVzn6JgysXzUZ5bb3LvFe+nTYXsAU9gJw==
      -----END RSA PRIVATE KEY-----

Enable Tacker to support mTLS for access to Notification server
---------------------------------------------------------------
The following parts describe steps to enable mTLS only for access to
Notification server and External Monitoring Tool server.

1. Modify the configuration file ``tacker.conf`` to enable SSL to implement
   HTTP support for the Tacker APIs. For the settings, specify the path where
   the certificate file created in the previous chapter is stored. The
   following settings are examples, and the certificate should be saved in a
   directory with appropriate authority.

   .. code-block:: console

      $ vi /etc/tacker/tacker.conf
      [v2_vnfm]
      notification_mtls_ca_cert_file = /etc/tacker/multi_ca.pem
      notification_mtls_client_cert_file = /etc/tacker/tacker_cert_and_key.pem

2. Restart Tacker service so that the modified configuration information takes
   effect.

   .. code-block:: console

      $ sudo systemctl restart devstack@tacker

Enable Tacker to support mTLS for access to External NFVO server
----------------------------------------------------------------
The following parts describe steps to enable mTLS only for access to
External NFVO server.

1. Modify the configuration file ``tacker.conf`` to enable SSL to implement
   HTTP support for the Tacker APIs. The client_id must be obtained from the
   authentication server used by the external NFVO. If you are using Keystone
   as the authentication server, you can use user_id as the client_id for mTLS
   authentication.

   .. code-block:: console

      $ vi /etc/tacker/tacker.conf
      [v2_nfvo]
      use_external_nfvo = True
      endpoint = https://endpoint.host
      token_endpoint = https://token_endpoint.host/identity/v3/OS-OAUTH2
      client_id = 4241794bcc7349b68b1f7312d60bd835
      mtls_ca_cert_file = /etc/tacker/multi_ca.pem
      mtls_client_cert_file = /etc/tacker/tacker_cert_and_key.pem

2. Restart Tacker service so that the modified configuration information takes
   effect.

   .. code-block:: console

      $ sudo systemctl restart devstack@tacker

Verifying that Access to Each Server Uses mTLS
----------------------------------------------
Access to external NFVO and notification servers is not output to the Tacker
log. Therefore, check the access log of the external NFVO server and
notification server when executing lcm operation, or use the packet capture
software to confirm that the access to each server is the mTLS communication.
If the packet capture shows that the client and server are sending certificates
to each other during the handshake, you can verify that mTLS is enabled.
