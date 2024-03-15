=========================
Using OAuth2.0 for Tacker
=========================

Overview
~~~~~~~~
The third-party clients can access the NFV orchestration APIs that is provided
by Tacker via the Client Credentials Grant flow in
`RFC6749`_ OAuth 2.0 Authorization Framework. OAuth2.0 Client Credentials Grant
flow is prescribed in the API specification of ETSI NFV `NFV-SOL013 v3.3.1`_.
Tacker uses the keystone middleware to support OAuth2.0 Client
Credentials Grant through the keystone identity server.

Preparations
~~~~~~~~~~~~
To use OAuth2.0 for Tacker, it is necessary to confirm that `OAuth2.0 client
credentials`_ is enabled in the Keystone identity server. In this example,
``keystone.host`` is the domain name used by the Keystone identity server, and
the domain name used by the tacker server is tacker.host.

Guide
~~~~~
To use OAuth2.0 Client Credentials Grant in Tacker, you should configure the
tacker-server and the Keystone middleware in the following steps.

.. _RFC6749: https://datatracker.ietf.org/doc/html/rfc6749
.. _NFV-SOL013 v3.3.1: https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/013/03.03.01_60/gs_nfv-sol013v030301p.pdf

Enable Tacker HTTPS Service
-------------------------------------
According to RFC6749, HTTPS must be enabled in the authorization server since
requests include sensitive information in plain text, so it should enable
Tacker to support HTTPS protocols.

1. Generate an RSA private key.

.. code-block:: console

    $ openssl genrsa -out tacker.key 2048
    Generating RSA private key, 2048 bit long modulus (2 primes)
    .........................................+++++
    .........................+++++
    e is 65537 (0x010001)

2. Create a certificate signing request.

.. code-block:: console

    $ openssl req -new -key tacker.key -out tacker.csr
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
    Organization Name (eg, company) [Internet Widgits Pty Ltd]:
    Organizational Unit Name (eg, section) []:
    Common Name (e.g. server FQDN or YOUR name) []:tacker.host
    Email Address []:

    Please enter the following 'extra' attributes
    to be sent with your certificate request
    A challenge password []:
    An optional company name []:

3. Generate a self signed certificate.

.. code-block:: console

    $ openssl x509 -req -days 365 -in tacker.csr \
    -signkey tacker.key -out tacker.host.crt
    Signature ok
    subject=C = , ST = , L = , O = , OU = , CN = tacker.host, emailAddress =
    Getting Private key

4. Modify the configuration file `tacker.conf`_ to enable SSL to implement HTTP
   support for the Tacker APIs.

.. code-block:: console

    $ vi /etc/tacker/tacker.conf
    [DEFAULT]
    # Enable SSL on the API server (boolean value)
    use_ssl = true

    # Certificate file to use when starting the server securely (string value)
    ssl_cert_file = /etc/tacker/tacker.host.crt

    # Private key file to use when starting the server securely (string value)
    ssl_key_file = /etc/tacker/tacker.key

5. Restart tacker service so that the modified configuration information takes
   effect.

.. code-block:: console

    $ sudo systemctl restart devstack@tacker

6. Try access the Tacker APIs via HTTPS protocol to confirm that the
   service has been successfully configured.

.. code-block:: console

    $ curl -sik -X GET https://tacker.host:9890/
    HTTP/1.1 200 OK
    Content-Type: application/json
    Content-Length: 118
    Date: Thu, 03 Mar 2022 08:12:56 GMT

    {"versions": [{"id": "v1.0", "status": "CURRENT", "links": [{"rel": "self", "href": "https://tacker.host:9890/v1.0"}]}]}

7. When Tacker is switched to HTTPS, user can not access the Tacker APIs via
   HTTP protocol.

.. code-block:: console

    $ curl -ik -X GET http://tacker.host:9890/
    curl: (52) Empty reply from server

.. _OAuth2.0 client credentials: https://docs.openstack.org/keystone/latest/admin/oauth2-usage-guide.html

Enable OAuth2.0 Client Credentials Authorization
------------------------------------------------
To handle API requests using OAuth2.0, you have to configure the keystone
middleware which intercepts API calls from clients and verifies a client's
identity, see `Middleware Architecture`_.

1. Add ``keystonemiddleware.oauth2_token:filter_factory`` to the configuration
   file ``api-paste.ini`` to enable OAuth2.0 Client Credentials Grant.

.. code-block:: console

    $ vi /etc/tacker/api-paste.ini
    [composite:tackerapi_v1_0]
    #keystone = request_id catch_errors authtoken keystonecontext extensions tackerapiapp_v1_0
    keystone = request_id catch_errors oauth2token keystonecontext extensions tackerapiapp_v1_0

    [composite:vnfpkgmapi_v1]
    #keystone = request_id catch_errors authtoken keystonecontext vnfpkgmapp_v1
    keystone = request_id catch_errors oauth2token keystonecontext vnfpkgmapp_v1

    [composite:vnflcm_v1]
    #keystone = request_id catch_errors authtoken keystonecontext vnflcmaapp_v1
    keystone = request_id catch_errors oauth2token keystonecontext vnflcmaapp_v1

    [composite:vnflcm_v2]
    #keystone = request_id catch_errors authtoken keystonecontext vnflcmaapp_v2
    keystone = request_id catch_errors oauth2token keystonecontext vnflcmaapp_v2

    [composite:vnflcm_versions]
    #keystone = request_id catch_errors authtoken keystonecontext vnflcm_api_versions
    keystone = request_id catch_errors oauth2token keystonecontext vnflcm_api_versions

    [filter:oauth2token]
    paste.filter_factory = keystonemiddleware.oauth2_token:filter_factory

2. Restart tacker service so that the modified configuration information takes
   effect.

.. code-block:: console

    $ sudo systemctl restart devstack@tacker

3. Obtain client credentials with application credentials API

   See the `OAuth2.0 usage guide`_ and `Application Credentials API`_ for
   information about obtaining client credentials.

4. Obtain an access token from the `OAuth2.0 Access Token API`_

.. code-block:: console

    $ curl -sik -u "$oauth2_client_id:$oauth2_client_secret" \
    -X  POST https://keystone.host/identity/v3/OS-OAUTH2/token \
    -H "application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials"
    HTTP/1.1 200 OK
    Date: Thu, 03 Mar 2022 07:08:23 GMT
    Server: Apache/2.4.41 (Ubuntu)
    Content-Type: application/json
    Content-Length: 264
    Vary: X-Auth-Token
    x-openstack-request-id: req-777d0afb-518f-4746-9c67-4e7bcab77ac7
    Connection: close

    {"access_token":"$oauth2_access_token","expires_in":3600,"token_type":"Bearer"}
    $  curl  -sik -X GET "https://tacker.host:9890/v1.0/vims" \
    -H "Authorization: Bearer $oauth2_access_token"
    HTTP/1.1 200 OK
    Content-Type: application/json
    Content-Length: 761
    X-Openstack-Request-Id: req-ce02befb-dca2-4c70-93ae-7f3df249daf7
    Date: Thu, 03 Mar 2022 08:11:38 GMT

    {"vims": [{"id": "de10a455-8752-4b47-a82e-73b29e0ef78b", "type": "openstack", "tenant_id": "e4c4650b3d404927b91c70cf94f6fa1e", "name": "vim_for_test_on_115", "description": "", "placement_attr": {"regions": ["RegionOne"]}, "is_default": true, "created_at": "2022-02-16 08:36:57", "updated_at": "2022-02-16 08:36:59", "status": "REACHABLE", "auth_url": "http://10.38.68.115/identity/v3", "vim_project": {"name": "test-project", "project_domain_name": "Default"}, "auth_cred": {"username": "admin-user", "user_domain_name": "Default", "cert_verify": "False", "project_id": null, "project_name": "test-project", "project_domain_name": "Default", "auth_url": "http://10.38.68.115/identity/v3", "key_type": "barbican_key", "secret_uuid": "***", "password": "***"}}]}
    $ curl -sik -X GET "https://tacker.host:9890/vnfpkgm/v1/vnf_packages" \
    -H "Authorization: Bearer $oauth2_access_token"
    HTTP/1.1 200 OK
    Content-Length: 1498
    Content-Type: application/json
    X-Openstack-Request-Id: req-a79d68a4-7481-4583-938a-89fa2012917b
    Date: Thu, 10 Mar 2022 05:21:02 GMT

    [{"id": "0a66fe4e-5376-4f8c-976a-4d04ce68741f", "usageState": "NOT_IN_USE", "onboardingState": "ONBOARDED", "operationalState": "ENABLED", "vnfProvider": "Company", "vnfdId": "c1bb0ce7-ebca-4fa7-95ed-4840d70a1177", "vnfSoftwareVersion": "1.0", "vnfProductName": "Sample VNF", "vnfdVersion": "1.0", "_links": {"self": {"href": "/vnfpkgm/v1/vnf_packages/0a66fe4e-5376-4f8c-976a-4d04ce68741f"}, "packageContent": {"href": "/vnfpkgm/v1/vnf_packages/0a66fe4e-5376-4f8c-976a-4d04ce68741f/package_content"}}}, {"id": "50d8802a-aa28-4bf3-a108-4e8f41d037ad", "usageState": "IN_USE", "onboardingState": "ONBOARDED", "operationalState": "ENABLED", "vnfProvider": "Company", "vnfdId": "e1bb0ce7-ebca-4fa7-95ed-4840d70a1178", "vnfSoftwareVersion": "1.0", "vnfProductName": "Sample VNF", "vnfdVersion": "1.0", "_links": {"self": {"href": "/vnfpkgm/v1/vnf_packages/50d8802a-aa28-4bf3-a108-4e8f41d037ad"}, "packageContent": {"href": "/vnfpkgm/v1/vnf_packages/50d8802a-aa28-4bf3-a108-4e8f41d037ad/package_content"}}}, {"id": "a6354198-6eda-4027-bf15-11e1fc33ebe0", "usageState": "IN_USE", "onboardingState": "ONBOARDED", "operationalState": "ENABLED", "vnfProvider": "Company", "vnfdId": "e1bb0ce7-ebca-4fa7-95ed-4840d70a1179", "vnfSoftwareVersion": "1.0", "vnfProductName": "Sample VNF", "vnfdVersion": "1.0", "_links": {"self": {"href": "/vnfpkgm/v1/vnf_packages/a6354198-6eda-4027-bf15-11e1fc33ebe0"}, "packageContent": {"href": "/vnfpkgm/v1/vnf_packages/a6354198-6eda-4027-bf15-11e1fc33ebe0/package_content"}}}]

5. Access the OpenStack Tacker APIs with the OAuth2.0 access token to confirm
   that OAuth2.0 Client Credentials Grant flow works correctly

.. code-block:: console

    $ curl -sik -X GET "https://tacker.host:9890/vnflcm/v1/vnf_instances" \
    -H "Authorization: Bearer $oauth2_access_token"
    HTTP/1.1 200 OK
    Content-Length: 1270
    Content-Type: application/json
    X-Openstack-Request-Id: req-175f12f0-8ab8-4815-a10c-33ceef06baf9
    Date: Thu, 10 Mar 2022 05:24:35 GMT

    [{"id": "0e579209-afe4-437d-87a7-e23c2f0e1bf8", "vnfInstanceName": "vnf-0e579209-afe4-437d-87a7-e23c2f0e1bf8", "vnfInstanceDescription": null, "instantiationState": "NOT_INSTANTIATED", "vnfdId": "e1bb0ce7-ebca-4fa7-95ed-4840d70a1178", "vnfProvider": "Company", "vnfProductName": "Sample VNF", "vnfSoftwareVersion": "1.0", "vnfdVersion": "1.0", "vnfPkgId": "50d8802a-aa28-4bf3-a108-4e8f41d037ad", "_links": {"self": {"href": "http://localhost:9890/vnflcm/v1/vnf_instances/0e579209-afe4-437d-87a7-e23c2f0e1bf8"}, "instantiate": {"href": "http://localhost:9890/vnflcm/v1/vnf_instances/0e579209-afe4-437d-87a7-e23c2f0e1bf8/instantiate"}}}, {"id": "d37b24f5-db19-460b-9aeb-0ccce8130591", "vnfInstanceName": "vnf-d37b24f5-db19-460b-9aeb-0ccce8130591", "vnfInstanceDescription": null, "instantiationState": "NOT_INSTANTIATED", "vnfdId": "e1bb0ce7-ebca-4fa7-95ed-4840d70a1179", "vnfProvider": "Company", "vnfProductName": "Sample VNF", "vnfSoftwareVersion": "1.0", "vnfdVersion": "1.0", "vnfPkgId": "a6354198-6eda-4027-bf15-11e1fc33ebe0", "_links": {"self": {"href": "http://localhost:9890/vnflcm/v1/vnf_instances/d37b24f5-db19-460b-9aeb-0ccce8130591"}, "instantiate": {"href": "http://localhost:9890/vnflcm/v1/vnf_instances/d37b24f5-db19-460b-9aeb-0ccce8130591/instantiate"}}}]

6. Confirm that a client can not access the Tacker APIs with an X-Auth-Token.

.. code-block:: console

    $ curl -si -X POST http://keystone.host/identity/v3/auth/tokens?nocatalog \
    -d '{"auth":{"identity":{"methods":["password"],"password": {"user":{"domain":{"name":"$userDomainName"},"name":"$userName","password":"$password"}}},"scope":{"project":{"domain":{"name":"$projectDomainName"},"name":"$projectName"}}}}' \
    -H 'Content-type:application/json'
    HTTP/1.1 201 CREATED
    Date: Tue, 08 Mar 2022 00:58:50 GMT
    Server: Apache/2.4.41 (Ubuntu)
    Content-Type: application/json
    Content-Length: 648
    X-Subject-Token: $x_auth_token
    Vary: X-Auth-Token
    x-openstack-request-id: req-d2136f50-c16b-49d3-8ed1-98ae1ea128ae
    Connection: close

    {"token": {"methods": ["password"], "user": {"domain": {"id": "default", "name": "Default"}, "id": "eb98b8bbb2174aa5acd6cf57b0bf64c6", "name": "admin", "password_expires_at": null}, "audit_ids": ["JCeU8IlITWiwRGNCUMJDYQ"], "expires_at": "2022-03-08T01:58:50.000000Z", "issued_at": "2022-03-08T00:58:50.000000Z", "project": {"domain": {"id": "default", "name": "Default"}, "id": "83808bea957a4ce1aa612aef63b24d1c", "name": "admin"}, "is_domain": false, "roles": [{"id": "c30201abb78848a6919f582d0cd74f84", "name": "admin"}, {"id": "54ee344bb009472c8223d4d76d9b1246", "name": "reader"}, {"id": "459dcf48c6794731b700fc6aa1cad669", "name": "member"}]}}
    $ curl  -sik -X GET "https://tacker.host:9890/v1.0/vims" \
    -H "X-Auth-Token:$x_auth_token"
    HTTP/1.1 401 Unauthorized
    Content-Type: application/json
    Content-Length: 114
    Www-Authenticate: Keystone uri="http://keystone.host/identity"
    X-Openstack-Request-Id: req-83a8de0a-e4c2-435d-91b7-f0471d156eef
    Date: Tue, 08 Mar 2022 01:01:55 GMT

    {"error": {"code": 401, "title": "Unauthorized", "message": "The request you have made requires authentication."}}

.. _OAuth2.0 usage guide: https://docs.openstack.org/keystone/latest/admin/oauth2-usage-guide.html
.. _Application Credentials API: https://docs.openstack.org/api-ref/identity/v3/index.html#application-credentials
.. _OAuth2.0 Access Token API: https://docs.openstack.org/api-ref/identity/v3-ext/index.html#os-oauth2-api
.. _Middleware Architecture: https://docs.openstack.org/keystonemiddleware/latest/middlewarearchitecture.html

Enable OpenStack Command through OAuth2.0 Client Credentials Authorization
--------------------------------------------------------------------------
To use OAuth2.0 Client Credentials Grant from OpenStack CLI, you have to use
``v3oauth2clientcredential`` as ``auth_type``.

1. Before executing the command, you should remove the variables that affect
   the OpenStack command from the OS environment, then set the variables that
   required by OAuth2.0 client credentials authorization to the OS environment.

.. code-block:: console

    $ unset OS_USERNAME
    $ unset OS_USER_ID
    $ unset OS_USER_DOMAIN_ID
    $ unset OS_USER_DOMAIN_NAME
    $ unset OS_TOKEN
    $ unset OS_PASSCODE
    $ unset OS_REAUTHENTICATE
    $ unset OS_TENANT_ID
    $ unset OS_TENANT_NAME
    $ unset OS_PROJECT_ID
    $ unset OS_PROJECT_NAME
    $ unset OS_PROJECT_DOMAIN_ID
    $ unset OS_PROJECT_DOMAIN_NAME
    $ unset OS_DOMAIN_ID
    $ unset OS_DOMAIN_NAME
    $ unset OS_SYSTEM_SCOPE
    $ unset OS_TRUST_ID
    $ unset OS_DEFAULT_DOMAIN_ID
    $ unset OS_DEFAULT_DOMAIN_NAME
    $ export OS_AUTH_URL=https://keystone.host/identity
    $ export OS_IDENTITY_API_VERSION=3
    $ export OS_REGION_NAME="RegionOne"
    $ export OS_INTERFACE=public

.. code-block:: console

    $ export OS_OAUTH2_ENDPOINT=https://keystone.host/identity/v3/OS-OAUTH2/token
    $ export OS_OAUTH2_CLIENT_ID=$oauth2_client_id
    $ export OS_OAUTH2_CLIENT_SECRET=$oauth2_client_secret
    $ export OS_AUTH_TYPE=v3oauth2clientcredential
    $ export OS_CACERT=/etc/keystone/keystone.host.crt

2. Change the tacker endpoints to use the HTTPS protocol to access the tacker
   API.

.. code-block:: console

    $ openstack endpoint list --service nfv-orchestration
    +----------------------------------+-----------+--------------+-------------------+---------+-----------+--------------------------+
    | ID                               | Region    | Service Name | Service Type      | Enabled | Interface | URL                      |
    +----------------------------------+-----------+--------------+-------------------+---------+-----------+--------------------------+
    | 435d13489c5d4744b152d233a2c6ce02 | RegionOne | tacker       | nfv-orchestration | True    | admin     | http://tacker.host:9890/ |
    | 5ea35d8101e147e3a7f78e19b986c4e5 | RegionOne | tacker       | nfv-orchestration | True    | internal  | http://tacker.host:9890/ |
    | 6982b25bb8734d8080e5017e64eecfb1 | RegionOne | tacker       | nfv-orchestration | True    | public    | http://tacker.host:9890/ |
    +----------------------------------+-----------+--------------+-------------------+---------+-----------+--------------------------+
    $ openstack endpoint set 435d13489c5d4744b152d233a2c6ce02 --url https://tacker.host:9890/
    $ openstack endpoint set 5ea35d8101e147e3a7f78e19b986c4e5 --url https://tacker.host:9890/
    $ openstack endpoint set 6982b25bb8734d8080e5017e64eecfb1 --url https://tacker.host:9890/
    $ openstack endpoint list --service nfv-orchestration
    +----------------------------------+-----------+--------------+-------------------+---------+-----------+---------------------------+
    | ID                               | Region    | Service Name | Service Type      | Enabled | Interface | URL                       |
    +----------------------------------+-----------+--------------+-------------------+---------+-----------+---------------------------+
    | 435d13489c5d4744b152d233a2c6ce02 | RegionOne | tacker       | nfv-orchestration | True    | admin     | https://tacker.host:9890/ |
    | 5ea35d8101e147e3a7f78e19b986c4e5 | RegionOne | tacker       | nfv-orchestration | True    | internal  | https://tacker.host:9890/ |
    | 6982b25bb8734d8080e5017e64eecfb1 | RegionOne | tacker       | nfv-orchestration | True    | public    | https://tacker.host:9890/ |
    +----------------------------------+-----------+--------------+-------------------+---------+-----------+---------------------------+

3. When the self signed certificates used by the keystone identity server and
   the Tacker server are not the same, it is necessary to merge multiple
   certificates into a single file and then set the path to the file to the OS
   environment variable.

.. code-block:: console

    $ cat keystone.host.crt >> openstack_client.crt
    $ cat tacker.host.crt >> openstack_client.crt
    $ cat openstack_client.crt
    -----BEGIN CERTIFICATE-----
    MIIDhTCCAm0CFCVKt8eYhOMvOCtQQPfjXTbIux8aMA0GCSqGSIb3DQEBCwUAMH8x
    CzAJBgNVBAYTAkNOMRAwDgYDVQQIDAdKaWFuZ3N1MQ8wDQYDVQQHDAZTdXpob3Ux
    DTALBgNVBAoMBEpmdHQxDDAKBgNVBAsMA0RldjEWMBQGA1UEAwwNa2V5c3RvbmUu
    aG9zdDEYMBYGCSqGSIb3DQEJARYJdGVzdEBqZnR0MB4XDTIyMDMwODAxNTA1NloX
    DTIzMDMwODAxNTA1NlowfzELMAkGA1UEBhMCQ04xEDAOBgNVBAgMB0ppYW5nc3Ux
    DzANBgNVBAcMBlN1emhvdTENMAsGA1UECgwESmZ0dDEMMAoGA1UECwwDRGV2MRYw
    FAYDVQQDDA1rZXlzdG9uZS5ob3N0MRgwFgYJKoZIhvcNAQkBFgl0ZXN0QGpmdHQw
    ggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQCyFCA2S7yrOzSgWaPte9rh
    /XX7S6TTOHRoH3OI75hY2bMA3sfVaq5be6XHa6K5b9sNz1sjgxM5sffBLA8VbawT
    Tz+ZUGhpOs1bQuye7ayDg6g/8YUvBth+MHl9c58dDVYudKag8Vcanlztda8LYJSe
    1sJKekfXZDG692R1lihGWrgVl+DV9elxK54knplvAqPzmt3KF+wra0s0QgySXA/D
    HTBQRJtNqG0ofPDfmCT0SwQSBpdiX2XQ9CGZXVHvUaM4RgPNIHCXi4laDXlSKc53
    Pyxk68R1jm9lodMj+oJdyl+CYydDbm2T2rJFByCxTd+BeWt31UBN7e3UJPI6uyZT
    AgMBAAEwDQYJKoZIhvcNAQELBQADggEBAAEJRVuhCWsdP4DA/gjPixWuVaTvdArh
    4HAK0WOsuXX1uLUTqXUrt86Ao5yudr5mSs/rSwIzW3Lggk2yrcR/NutecdHFZXln
    LFzArhkX/FeW2LddPOmJhVXFnHVc3woWdrUtgp5TjZRt+PrGUWjM2z9QrLeAp/PP
    qBJ3BNjizM+Jz5KMKeXU0zWS6y/0dcwruOwa8loZ2FiG3f/UubOyNGUgLodFrxhQ
    vIaeHkaYZw3CHBSYjs7eJiwZNjMrb+eL0CFoJd0UF+30PptUfews61KuIQTk0od1
    5aZoXdQ/YHWorLJoluUFrNqZUykDfFm7JLBjubuHglvVUTSJ1mbDGto=
    -----END CERTIFICATE-----
    -----BEGIN CERTIFICATE-----
    MIIDgTCCAmkCFBkaTpj6Fm1yuBJrOI7OF1ZxEKbOMA0GCSqGSIb3DQEBCwUAMH0x
    CzAJBgNVBAYTAkNOMRAwDgYDVQQIDAdKaWFuZ3N1MQ8wDQYDVQQHDAZTdXpob3Ux
    DTALBgNVBAoMBGpmdHQxDDAKBgNVBAsMA2RldjEUMBIGA1UEAwwLdGFja2VyLmhv
    c3QxGDAWBgkqhkiG9w0BCQEWCXRlc3RAamZ0dDAeFw0yMjAzMDgwMjQ2MDZaFw0y
    MzAzMDgwMjQ2MDZaMH0xCzAJBgNVBAYTAkNOMRAwDgYDVQQIDAdKaWFuZ3N1MQ8w
    DQYDVQQHDAZTdXpob3UxDTALBgNVBAoMBGpmdHQxDDAKBgNVBAsMA2RldjEUMBIG
    A1UEAwwLdGFja2VyLmhvc3QxGDAWBgkqhkiG9w0BCQEWCXRlc3RAamZ0dDCCASIw
    DQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALIUIDZLvKs7NKBZo+172uH9dftL
    pNM4dGgfc4jvmFjZswDex9Vqrlt7pcdrorlv2w3PWyODEzmx98EsDxVtrBNPP5lQ
    aGk6zVtC7J7trIODqD/xhS8G2H4weX1znx0NVi50pqDxVxqeXO11rwtglJ7Wwkp6
    R9dkMbr3ZHWWKEZauBWX4NX16XErniSemW8Co/Oa3coX7CtrSzRCDJJcD8MdMFBE
    m02obSh88N+YJPRLBBIGl2JfZdD0IZldUe9RozhGA80gcJeLiVoNeVIpznc/LGTr
    xHWOb2Wh0yP6gl3KX4JjJ0NubZPaskUHILFN34F5a3fVQE3t7dQk8jq7JlMCAwEA
    ATANBgkqhkiG9w0BAQsFAAOCAQEAH0B2qgwKjWje0UfdQOb1go8EKsktHOvIDK5+
    dXz2wNFJpKCekvSGK4/2KEp1McTTDj0w8nlWcGZgaOcvjuq8ufWrggjdADa2xJHr
    4pfxNMQrQXCFZ5ikCoLDx9QKDyN81b12GWpr1yPYIanSghbhx4AW7BkVQwtELun8
    d6nHGTixkqxljbEB9qM/wOrQMlm/9oJvyU4Po7weav8adPVyx8zFh9UCH2qXKUlo
    3e5D8BKkBpo4DtoXGPaYBuNt/lI7emhfikcZ2ZbeytIGdC4InoooYMKJkfjMxyim
    DSqhxuyffTmmMmEx1GK9PYLy7uPJkfn/mn9K9VL71p4QnJQt7g==
    -----END CERTIFICATE-----
    $ export OS_CACERT=/etc/ssl/certs/openstack_client.crt

4. Execute a tacker command to confirm that OpenStack command can access the
   Tacker APIs successfully.

.. code-block:: console

    $ openstack vim list
    +--------------------------------------+---------------------+----------------------------------+-----------+------------+-----------+
    | ID                                   | Name                | Tenant_id                        | Type      | Is Default | Status    |
    +--------------------------------------+---------------------+----------------------------------+-----------+------------+-----------+
    | de10a455-8752-4b47-a82e-73b29e0ef78b | vim_for_test_on_115 | e4c4650b3d404927b91c70cf94f6fa1e | openstack | True       | REACHABLE |
    +--------------------------------------+---------------------+----------------------------------+-----------+------------+-----------+
    $ openstack vnf package list
    +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
    | Id                                   | Vnf Product Name | Onboarding State | Usage State | Operational State | Links                                                                                           |
    +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
    | 0a66fe4e-5376-4f8c-976a-4d04ce68741f | Sample VNF       | ONBOARDED        | NOT_IN_USE  | ENABLED           | {                                                                                               |
    |                                      |                  |                  |             |                   |     "self": {                                                                                   |
    |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/0a66fe4e-5376-4f8c-976a-4d04ce68741f"                 |
    |                                      |                  |                  |             |                   |     },                                                                                          |
    |                                      |                  |                  |             |                   |     "packageContent": {                                                                         |
    |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/0a66fe4e-5376-4f8c-976a-4d04ce68741f/package_content" |
    |                                      |                  |                  |             |                   |     }                                                                                           |
    |                                      |                  |                  |             |                   | }                                                                                               |
    | a6354198-6eda-4027-bf15-11e1fc33ebe0 | Sample VNF       | ONBOARDED        | IN_USE      | ENABLED           | {                                                                                               |
    |                                      |                  |                  |             |                   |     "self": {                                                                                   |
    |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/a6354198-6eda-4027-bf15-11e1fc33ebe0"                 |
    |                                      |                  |                  |             |                   |     },                                                                                          |
    |                                      |                  |                  |             |                   |     "packageContent": {                                                                         |
    |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/a6354198-6eda-4027-bf15-11e1fc33ebe0/package_content" |
    |                                      |                  |                  |             |                   |     }                                                                                           |
    |                                      |                  |                  |             |                   | }                                                                                               |
    +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
    $ openstack vnflcm list
    +--------------------------------------+------------------------------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
    | ID                                   | VNF Instance Name                        | Instantiation State | VNF Provider | VNF Software Version | VNF Product Name | VNFD ID                              |
    +--------------------------------------+------------------------------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
    | 0e579209-afe4-437d-87a7-e23c2f0e1bf8 | vnf-0e579209-afe4-437d-87a7-e23c2f0e1bf8 | NOT_INSTANTIATED    | Company      | 1.0                  | Sample VNF       | e1bb0ce7-ebca-4fa7-95ed-4840d70a1178 |
    | d37b24f5-db19-460b-9aeb-0ccce8130591 | vnf-d37b24f5-db19-460b-9aeb-0ccce8130591 | NOT_INSTANTIATED    | Company      | 1.0                  | Sample VNF       | e1bb0ce7-ebca-4fa7-95ed-4840d70a1179 |
    +--------------------------------------+------------------------------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+

Subscribe to Notifications that need OAuth2.0 Client Credentials Grant
----------------------------------------------------------------------
If the certification of the notification authorization server is not trusted,
the configuration file `tacker.conf`_ can be modified to set the
``verify_oauth2_ssl`` to false, then the backend no longer verify the
certification when it obtains the OAuth2.0 access token.
If the certification of the notification callback API is not trusted, the
configuration file `tacker.conf`_ can be modified to set the
``verify_notification_ssl`` to false, then the backend no longer verify the
certification when it sends a notification.

1. Modify the configuration file as needed.

.. code-block:: console

    $ vi /etc/tacker/tacker.conf
    [vnf_lcm]
    verify_notification_ssl = false
    [authentication]
    verify_oauth2_ssl = false

2. Subscribe to a notification that requires OAuth2.0 client authorization to
   confirm that the backend can send a notification successfully.

.. code-block:: console

    $ curl -ik -X POST https://tacker.host:9890/vnflcm/v1/subscriptions \
    -H "Authorization: Bearer $oauth2_access_token" \
    -H "Content-Type: application/json" \
    -d '{"filter": {"vnfInstanceSubscriptionFilter":{"vnfdIds":["20faf7bc-0e24-4ab7-adf3-870d0b4c873f"]}},"callbackUri":"$callback_url","authentication":{"authType":"OAUTH2_CLIENT_CREDENTIALS","paramsOauth2ClientCredentials":{"clientId":"$notification_oauth2_client_id","clientPassword":"$notification_oauth2_client_secret","tokenEndpoint":"$notification_oauth2_token_endpoint"}}}'
    HTTP/1.1 201 Created
    Content-Length: 322
    Location: https://tacker.host:9890/vnflcm/v1/subscriptions/76425044-53e2-4bbd-9b8b-170559fda80c
    Content-Type: application/json
    X-Openstack-Request-Id: req-9f01e0b1-8e03-458e-a9d1-9f09bb0020b1
    Date: Thu, 03 Mar 2022 07:26:34 GMT

    {"id": "76425044-53e2-4bbd-9b8b-170559fda80c", "filter": {"vnfInstanceSubscriptionFilter": {"vnfdIds": ["20faf7bc-0e24-4ab7-adf3-870d0b4c873f"]}}, "callbackUri": "https://10.10.0.56:29000/mock_oauth2/test", "_links": {"self": {"href": "http://localhost:9890/vnflcm/v1/subscriptions/76425044-53e2-4bbd-9b8b-170559fda80c"}}}

.. _tacker.conf: https://docs.openstack.org/tacker/latest/configuration/config.html
