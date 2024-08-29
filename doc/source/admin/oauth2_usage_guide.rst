==========================
Using OAuth 2.0 for Tacker
==========================

.. note::

  The content of this document has been confirmed to work
  using Tacker and Keystone 2024.1 Caracal.


Overview
~~~~~~~~

The third-party clients can access the NFV orchestration APIs that is provided
by Tacker via the Client Credentials Grant flow in
`RFC6749`_ OAuth 2.0 Authorization Framework. OAuth 2.0 Client Credentials
Grant flow is prescribed in the API specification of `ETSI NFV-SOL013 v3.4.1`_.
Tacker uses the Keystone middleware to support OAuth 2.0 Client
Credentials Grant through the Keystone identity server.


Preparations
~~~~~~~~~~~~

To use OAuth 2.0 for Tacker, it is necessary to confirm that `OAuth 2.0 client
credentials`_ is enabled in the Keystone identity server. In this example,
$keystone_host_name is the domain name used by the Keystone identity server,
and the domain name used by the tacker server is $tacker_host_name.


Guide
~~~~~

To use OAuth 2.0 Client Credentials Grant in Tacker, you should configure the
tacker-server and the Keystone middleware in the following steps.


Enable Tacker HTTPS Service
---------------------------

According to RFC6749, HTTPS must be enabled in the authorization server since
requests include sensitive information in plain text, so it should enable
Tacker to support HTTPS protocols.

1. Generate an RSA private key.

   .. code-block:: console

     $ cd /etc/tacker
     $ openssl genrsa -out tacker.key 2048


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
     Country Name (2 letter code) [AU]:.
     State or Province Name (full name) [Some-State]:.
     Locality Name (eg, city) []:.
     Organization Name (eg, company) [Internet Widgits Pty Ltd]:.
     Organizational Unit Name (eg, section) []:.
     Common Name (e.g. server FQDN or YOUR name) []:$tacker_host_name
     Email Address []:.

     Please enter the following 'extra' attributes
     to be sent with your certificate request
     A challenge password []:.
     An optional company name []:.


3. Generate a self signed certificate.

   .. code-block:: console

     $ openssl x509 -req -days 365 -in tacker.csr \
     -signkey tacker.key -out tacker.host.crt
     Certificate request self-signature ok
     subject=CN = $tacker_host_name


4. Modify the :doc:`/configuration/config` to enable SSL to implement HTTP
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

     [v2_vnfm]

     #
     # From tacker.sol_refactored.common.config
     #

     # Endpoint of VNFM (self). (string value)
     endpoint = https://$tacker_host_name:9890

     [vnf_lcm]
     # Vnflcm options group

     #
     # From tacker.conf
     #

     # endpoint_url (string value)
     endpoint_url = https://$tacker_host_name:9890/


   .. note::

     If the Keystone identity server supports the HTTPS protocol,
     set the following in tacker.conf:

     .. code-block:: console

       [keystone_authtoken]
       #cafile = /opt/stack/data/ca-bundle.pem
       cafile = /etc/keystone/keystone.host.crt
       #auth_url = http://$keystone_host_name/identity
       auth_url = https://$keystone_host_name/identity


5. Restart tacker service so that the modified configuration information takes
   effect.

   .. code-block:: console

     $ sudo systemctl restart devstack@tacker


6. Try access the Tacker APIs via HTTPS protocol to confirm that the
   service has been successfully configured.

   .. code-block:: console

     $ curl -i --cacert tacker.host.crt -X GET https://$tacker_host_name:9890/
     HTTP/1.1 200 OK
     Content-Type: application/json
     Content-Length: 122
     Date: Wed, 22 May 2024 04:57:57 GMT

     {"versions": [{"id": "v1.0", "status": "CURRENT", "links": [{"rel": "self", "href": "https://$tacker_host_name/v1.0"}]}]}


7. When Tacker is switched to HTTPS, user can not access the Tacker APIs via
   HTTP protocol.

   .. code-block:: console

     $ curl -i -X GET http://$tacker_host_name:9890/
     curl: (52) Empty reply from server


Enable OAuth 2.0 Client Credentials Authorization
-------------------------------------------------

To handle API requests using OAuth 2.0, you have to configure the Keystone
middleware which intercepts API calls from clients and verifies a client's
identity, see `Middleware Architecture`_.

1. Add ``keystonemiddleware.oauth2_token:filter_factory`` to the configuration
   file ``api-paste.ini`` to enable OAuth 2.0 Client Credentials Grant.

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

     [composite:vnfpm_v2]
     #keystone = request_id catch_errors authtoken keystonecontext vnfpmaapp_v2
     keystone = request_id catch_errors oauth2token keystonecontext vnfpmaapp_v2

     [composite:vnflcm_versions]
     #keystone = request_id catch_errors authtoken keystonecontext vnflcm_api_versions
     keystone = request_id catch_errors oauth2token keystonecontext vnflcm_api_versions

     [composite:vnffm_v1]
     #keystone = request_id catch_errors authtoken keystonecontext vnffmaapp_v1
     keystone = request_id catch_errors oauth2token keystonecontext vnffmaapp_v1

     [filter:oauth2token]
     paste.filter_factory = keystonemiddleware.oauth2_token:filter_factory


2. Restart tacker service so that the modified configuration information takes
   effect.

   .. code-block:: console

     $ sudo systemctl restart devstack@tacker


3. Obtain client credentials with application credentials API

   See the `OAuth 2.0 usage guide`_ and `Application Credentials API`_ for
   information about obtaining client credentials.


4. Obtain an access token from the `OAuth 2.0 Access Token API`_

   .. code-block:: console

     $ curl -i --cacert keystone.host.crt -u "$oauth2_client_id:$oauth2_client_secret" \
     -X  POST https://$keystone_host_name/identity/v3/OS-OAUTH2/token \
     -H "application/x-www-form-urlencoded" \
     -d "grant_type=client_credentials"
     HTTP/1.1 200 OK
     Date: Wed, 22 May 2024 05:55:21 GMT
     Server: Apache/2.4.52 (Ubuntu)
     Content-Type: application/json
     Content-Length: 264
     Vary: X-Auth-Token
     x-openstack-request-id: req-269c250e-5fc8-439b-9d40-8ba6c139a245
     Connection: close

     {"access_token":"$oauth2_access_token","expires_in":3600,"token_type":"Bearer"}

     $ curl  -i --cacert tacker.host.crt -X GET "https://$tacker_host_name:9890/v1.0/vims" \
     -H "Authorization: Bearer $oauth2_access_token"
     HTTP/1.1 200 OK
     Content-Type: application/json
     Content-Length: 736
     X-Openstack-Request-Id: req-75594c93-dc19-49cd-9da5-6f8e9b7a7a03
     Date: Wed, 22 May 2024 05:59:43 GMT

     {"vims": [{"id": "84517803-0e84-401e-ad75-8f6b8ab0a3b6", "type": "openstack", "tenant_id": "d53a4605d776472d846aed35735d3494", "name": "openstack-admin-vim", "description": "", "placement_attr": {"regions": ["RegionOne"]}, "is_default": true, "created_at": "2024-06-03 14:29:08", "updated_at": null, "extra": {}, "auth_url": "https://$keystone_host_name/identity/v3", "vim_project": {"name": "nfv", "project_domain_name": "Default"}, "auth_cred": {"username": "nfv_user", "user_domain_name": "Default", "cert_verify": "False", "project_id": null, "project_name": "nfv", "project_domain_name": "Default", "auth_url": "https://keystone/identity/v3", "key_type": "barbican_key", "secret_uuid": "***", "password": "***"}, "status": "ACTIVE"}]}

     $ curl -i --cacert tacker.host.crt -X GET "https://$tacker_host_name:9890/vnfpkgm/v1/vnf_packages" \
     -H "Authorization: Bearer $oauth2_access_token"
     HTTP/1.1 200 OK
     Content-Type: application/json
     Content-Length: 498
     X-Openstack-Request-Id: req-3f5ebaad-6f66-43b7-bd0f-917a54558918
     Date: Wed, 22 May 2024 06:06:24 GMT

     [{"id": "6b02a067-848f-418b-add1-e9c020239b31", "onboardingState": "ONBOARDED", "operationalState": "ENABLED", "usageState": "IN_USE", "vnfProductName": "Sample VNF", "vnfSoftwareVersion": "1.0", "vnfdId": "b1bb0ce7-ebca-4fa7-95ed-4840d70a1177", "vnfdVersion": "1.0", "vnfProvider": "Company", "_links": {"self": {"href": "/vnfpkgm/v1/vnf_packages/6b02a067-848f-418b-add1-e9c020239b31"}, "packageContent": {"href": "/vnfpkgm/v1/vnf_packages/6b02a067-848f-418b-add1-e9c020239b31/package_content"}}}]


5. Access the OpenStack Tacker APIs with the OAuth 2.0 access token to confirm
   that OAuth 2.0 Client Credentials Grant flow works correctly

   .. code-block:: console

     $ curl -i --cacert tacker.host.crt -X GET "https://$tacker_host_name:9890/vnflcm/v1/vnf_instances" \
     -H "Authorization: Bearer $oauth2_access_token"
     HTTP/1.1 200 OK
     Content-Type: application/json
     Content-Length: 603
     X-Openstack-Request-Id: req-ceeb935f-e4af-4f46-bfa9-4fb3e83a4664
     Date: Wed, 22 May 2024 06:24:33 GMT

     [{"id": "fd25f4ca-27ac-423b-afcf-640a64544e61", "vnfInstanceName": "vnf-fd25f4ca-27ac-423b-afcf-640a64544e61", "instantiationState": "NOT_INSTANTIATED", "vnfdId": "b1bb0ce7-ebca-4fa7-95ed-4840d70a1177", "vnfProvider": "Company", "vnfProductName": "Sample VNF", "vnfSoftwareVersion": "1.0", "vnfdVersion": "1.0", "vnfPkgId": "6b02a067-848f-418b-add1-e9c020239b31", "_links": {"self": {"href": "https://$tacker_host_name:9890/vnflcm/v1/vnf_instances/fd25f4ca-27ac-423b-afcf-640a64544e61"}, "instantiate": {"href": "https://$tacker_host_name:9890/vnflcm/v1/vnf_instances/fd25f4ca-27ac-423b-afcf-640a64544e61/instantiate"}}}]


6. Confirm that a client can not access the Tacker APIs with an X-Auth-Token.

   .. code-block:: console

     $ curl -i --cacert keystone.host.crt -X POST https://$keystone_host_name/identity/v3/auth/tokens?nocatalog \
     -d '{"auth":{"identity":{"methods":["password"],"password": {"user":{"domain":{"name":"$userDomainName"},"name":"$userName","password":"$password"}}},"scope":{"project":{"domain":{"name":"$projectDomainName"},"name":"$projectName"}}}}' \
     -H 'Content-type:application/json'
     HTTP/1.1 201 CREATED
     Date: Wed, 05 Jun 2024 06:48:33 GMT
     Server: Apache/2.4.52 (Ubuntu)
     Content-Type: application/json
     Content-Length: 712
     X-Subject-Token: $x_auth_token
     Vary: X-Auth-Token
     x-openstack-request-id: req-bc85eb93-eb34-41d6-970e-1cbd776c1878
     Connection: close

     {"token": {"methods": ["password"], "user": {"domain": {"id": "default", "name": "Default"}, "id": "ee8962d8fe0d4eafbf2155eac988fce8", "name": "nfv_user", "password_expires_at": null}, "audit_ids": ["nHh38yyHSnWfPItIUnesEQ"], "expires_at": "2024-06-05T07:48:33.000000Z", "issued_at": "2024-06-05T06:48:33.000000Z", "project": {"domain": {"id": "default", "name": "Default"}, "id": "d53a4605d776472d846aed35735d3494", "name": "nfv"}, "is_domain": false, "roles": [{"id": "4f50d53ed79a42bd89105954f21d9f1d", "name": "member"}, {"id": "9c9f278da6e74c2dbdb80fc0a5ed9010", "name": "manager"}, {"id": "fcdedca5ce604c90b241bab70f85d8cc", "name": "admin"}, {"id": "42ff1a2ac70d4496a90dd6aa8985feb1", "name": "reader"}]}}

     $ curl -i --cacert tacker.host.crt -X GET "https://$tacker_host_name:9890/v1.0/vims" \
     -H "X-Auth-Token:$x_auth_token"
     HTTP/1.1 401 Unauthorized
     Content-Type: application/json
     Content-Length: 114
     Www-Authenticate: Keystone uri="https://$keystone_host_name/identity"
     X-Openstack-Request-Id: req-5ee22493-4961-4272-82c6-c44978d3ed8b
     Date: Wed, 05 Jun 2024 07:02:02 GMT

     {"error": {"code": 401, "title": "Unauthorized", "message": "The request you have made requires authentication."}}


Enable OpenStack Command through OAuth 2.0 Client Credentials Authorization
---------------------------------------------------------------------------

To use OAuth 2.0 Client Credentials Grant from OpenStack CLI, you have to use
``v3oauth2clientcredential`` as ``auth_type``.

1. Before executing the command, you should remove the variables that affect
   the OpenStack command from the OS environment, then set the variables that
   required by OAuth 2.0 client credentials authorization to the OS
   environment.

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
     $ export OS_AUTH_URL=https://$keystone_host_name/identity
     $ export OS_IDENTITY_API_VERSION=3
     $ export OS_REGION_NAME="RegionOne"
     $ export OS_INTERFACE=public


   .. code-block:: console

     $ export OS_OAUTH2_ENDPOINT=https://$keystone_host_name/identity/v3/OS-OAUTH2/token
     $ export OS_OAUTH2_CLIENT_ID=$oauth2_client_id
     $ export OS_OAUTH2_CLIENT_SECRET=$oauth2_client_secret
     $ export OS_AUTH_TYPE=v3oauth2clientcredential
     $ export OS_CACERT=/etc/keystone/keystone.host.crt


2. Change the tacker endpoints to use the HTTPS protocol to access the tacker
   API.

   .. code-block:: console

     $ openstack endpoint list --service nfv-orchestration
     +----------------------------------+-----------+--------------+-------------------+---------+-----------+--------------------------------+
     | ID                               | Region    | Service Name | Service Type      | Enabled | Interface | URL                            |
     +----------------------------------+-----------+--------------+-------------------+---------+-----------+--------------------------------+
     | 4729bdacd3ff486394142e663561dddd | RegionOne | tacker       | nfv-orchestration | True    | public    | http://$tacker_host_name:9890/ |
     | 9152dd2790fa4a25aa9884685534c8cd | RegionOne | tacker       | nfv-orchestration | True    | internal  | http://$tacker_host_name:9890/ |
     | f868f32d84dc4087bc4322c854413912 | RegionOne | tacker       | nfv-orchestration | True    | admin     | http://$tacker_host_name:9890/ |
     +----------------------------------+-----------+--------------+-------------------+---------+-----------+--------------------------------+
     $ openstack endpoint set 4729bdacd3ff486394142e663561dddd --url https://$tacker_host_name:9890/
     $ openstack endpoint set 9152dd2790fa4a25aa9884685534c8cd --url https://$tacker_host_name:9890/
     $ openstack endpoint set f868f32d84dc4087bc4322c854413912 --url https://$tacker_host_name:9890/
     $ openstack endpoint list --service nfv-orchestration
     +----------------------------------+-----------+--------------+-------------------+---------+-----------+---------------------------------+
     | ID                               | Region    | Service Name | Service Type      | Enabled | Interface | URL                             |
     +----------------------------------+-----------+--------------+-------------------+---------+-----------+---------------------------------+
     | 4729bdacd3ff486394142e663561dddd | RegionOne | tacker       | nfv-orchestration | True    | public    | https://$tacker_host_name:9890/ |
     | 9152dd2790fa4a25aa9884685534c8cd | RegionOne | tacker       | nfv-orchestration | True    | internal  | https://$tacker_host_name:9890/ |
     | f868f32d84dc4087bc4322c854413912 | RegionOne | tacker       | nfv-orchestration | True    | admin     | https://$tacker_host_name:9890/ |
     +----------------------------------+-----------+--------------+-------------------+---------+-----------+---------------------------------+


3. When the self signed certificates used by the Keystone identity server and
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
     $ export OS_CACERT=/etc/openstack/openstack_client.crt


4. Execute a tacker command to confirm that OpenStack command can access the
   Tacker APIs successfully.

   .. code-block:: console

     $ openstack vim list
     +--------------------------------------+---------------------+----------------------------------+-----------+------------+--------+
     | ID                                   | Name                | Tenant_id                        | Type      | Is Default | Status |
     +--------------------------------------+---------------------+----------------------------------+-----------+------------+--------+
     | 84517803-0e84-401e-ad75-8f6b8ab0a3b6 | openstack-admin-vim | d53a4605d776472d846aed35735d3494 | openstack | True       | ACTIVE |
     +--------------------------------------+---------------------+----------------------------------+-----------+------------+--------+
     $ openstack vnf package list
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
     | Id                                   | Vnf Product Name | Onboarding State | Usage State | Operational State | Links                                                                                           |
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
     | 6b02a067-848f-418b-add1-e9c020239b31 | Sample VNF       | ONBOARDED        | IN_USE      | ENABLED           | {                                                                                               |
     |                                      |                  |                  |             |                   |     "self": {                                                                                   |
     |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/6b02a067-848f-418b-add1-e9c020239b31"                 |
     |                                      |                  |                  |             |                   |     },                                                                                          |
     |                                      |                  |                  |             |                   |     "packageContent": {                                                                         |
     |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/6b02a067-848f-418b-add1-e9c020239b31/package_content" |
     |                                      |                  |                  |             |                   |     }                                                                                           |
     |                                      |                  |                  |             |                   | }                                                                                               |
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
     $ openstack vnflcm list
     +--------------------------------------+------------------------------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
     | ID                                   | VNF Instance Name                        | Instantiation State | VNF Provider | VNF Software Version | VNF Product Name | VNFD ID                              |
     +--------------------------------------+------------------------------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
     | fd25f4ca-27ac-423b-afcf-640a64544e61 | vnf-fd25f4ca-27ac-423b-afcf-640a64544e61 | NOT_INSTANTIATED    | Company      | 1.0                  | Sample VNF       | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177 |
     +--------------------------------------+------------------------------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+


Subscribe to Notifications that need OAuth 2.0 Client Credentials Grant
-----------------------------------------------------------------------

If the certification of the notification authorization server is not trusted,
the configuration file :doc:`/configuration/config` can be modified to set the
``verify_oauth2_ssl`` to false, then the backend no longer verify the
certification when it obtains the OAuth 2.0 access token.
If the certification of the notification callback API is not trusted, the
configuration file :doc:`/configuration/config` can be modified to set the
``verify_notification_ssl`` to false, then the backend no longer verify the
certification when it sends a notification.

1. Modify the configuration file as needed.

   .. code-block:: console

     $ vi /etc/tacker/tacker.conf
     [vnf_lcm]
     verify_notification_ssl = false
     [authentication]
     verify_oauth2_ssl = false


2. Subscribe to a notification that requires OAuth 2.0 client authorization to
   confirm that the backend can send a notification successfully.

   .. code-block:: console

     $ cat subsc_create_req.json
     {
         "filter": {
             "vnfInstanceSubscriptionFilter":{
                 "vnfdIds": [
                     "108135bb-8f21-4b91-a548-4aad3cf72a87"
                 ]
             }
         },
         "callbackUri" : "$callback_uri",
         "authentication": {
             "authType":["OAUTH2_CLIENT_CREDENTIALS"],
             "paramsOauth2ClientCredentials": {
                 "clientId": "$notification_oauth2_client_id",
                     "clientPassword": "$notification_oauth2_client_secret",
                     "tokenEndpoint": "$notification_oauth2_token_endpoint"
             }
         }
     }
     $ openstack vnflcm subsc create subsc_create_req.json --os-tacker-api-version 2
     +--------------+----------------------------------------------------------------------------------------------------------+
     | Field        | Value                                                                                                    |
     +--------------+----------------------------------------------------------------------------------------------------------+
     | Callback URI | $callback_uri                                                                                            |
     | Filter       | {                                                                                                        |
     |              |     "vnfInstanceSubscriptionFilter": {                                                                   |
     |              |         "vnfdIds": [                                                                                     |
     |              |             "108135bb-8f21-4b91-a548-4aad3cf72a87"                                                       |
     |              |         ]                                                                                                |
     |              |     }                                                                                                    |
     |              | }                                                                                                        |
     | ID           | b25c2d6f-6de4-450a-a25d-321868d3ed83                                                                     |
     | Links        | {                                                                                                        |
     |              |     "self": {                                                                                            |
     |              |         "href": "https://$tacker_host_name/vnflcm/v2/subscriptions/b25c2d6f-6de4-450a-a25d-321868d3ed83" |
     |              |     }                                                                                                    |
     |              | }                                                                                                        |
     | verbosity    | FULL                                                                                                     |
     +--------------+----------------------------------------------------------------------------------------------------------+


.. _RFC6749: https://datatracker.ietf.org/doc/html/rfc6749
.. _ETSI NFV-SOL013 v3.4.1:
  https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/013/03.04.01_60/gs_nfv-sol013v030401p.pdf
.. _OAuth 2.0 client credentials:
  https://docs.openstack.org/keystone/latest/admin/oauth2-usage-guide.html
.. _Middleware Architecture:
  https://docs.openstack.org/keystonemiddleware/latest/middlewarearchitecture.html
.. _OAuth 2.0 usage guide:
  https://docs.openstack.org/keystone/latest/admin/oauth2-usage-guide.html
.. _Application Credentials API:
  https://docs.openstack.org/api-ref/identity/v3/index.html#application-credentials
.. _OAuth 2.0 Access Token API:
  https://docs.openstack.org/api-ref/identity/v3-ext/index.html#os-oauth2-api
