==============================================================
Using External Authorization Server OAuth 2.0 Grant for Tacker
==============================================================

.. note::

  The content of this document has been confirmed to work using
  Tacker 2024.1 Caracal and Keystone 25.0.4.


Overview
~~~~~~~~

Sometimes users may use the Client Credentials Grant flow of `RFC6749`_ OAuth
2.0 Authorization Framework provided by a third-party authorization server
(such as `Keycloak`_) for user authentication. OAuth 2.0 Client Credentials
Grant flow is prescribed in the API specification of ETSI `NFV-SOL013 v3.3.1`_.

Tacker uses the Keystonemiddleware to support OAuth 2.0 Client Credentials
Grant provided by the external OAuth 2.0 authorization server. In addition,
Tacker can also access other OpenStack services that use the external OAuth 2.0
authorization server, using the Client Credentials Grant flow for user
authentication.

Preparations
~~~~~~~~~~~~

To use external OAuth 2.0 authorization server for Authenticating Tacker API,
it is necessary to confirm that the token filter factory
``external_oauth2_token`` is supported in the Keystonemiddleware. In this
example, the `Keycloak`_ server is used as the external OAuth 2.0 authorization
server. The `keycloak.host` is the domain name used by the `Keycloak`_ server,
and the domain name used by the Tacker server is `tacker.host`.

Guide
~~~~~

To use external OAuth 2.0 authorization server for Tacker, you should configure
the Tacker server and the Keystonemiddleware in the following steps.

Enable To Use external OAuth 2.0 authorization server
-----------------------------------------------------

To authenticate API requests using external OAuth 2.0 authorization server,
you have to configure the Keystonemiddleware which accepts API calls from
clients and verifies a client's identity. For detail, see
`Middleware Architecture`_.

1. Add ``keystonemiddleware.external_oauth2_token:filter_factory`` to the
   configuration file ``api-paste.ini`` to enable external OAuth 2.0
   authorization Server authentication.

   .. code-block:: console

    $ vi /etc/tacker/api-paste.ini
    [composite:tackerapi_v1_0]
    keystone = request_id catch_errors external_oauth2_token keystonecontext extensions tackerapiapp_v1_0

    [composite:vnfpkgmapi_v1]
    keystone = request_id catch_errors external_oauth2_token keystonecontext vnfpkgmapp_v1

    [composite:vnflcm_v1]
    keystone = request_id catch_errors external_oauth2_token keystonecontext vnflcmaapp_v1

    [composite:vnflcm_v2]
    keystone = request_id catch_errors external_oauth2_token keystonecontext vnflcmaapp_v2

    [composite:vnfpm_v2]
    keystone = request_id catch_errors external_oauth2_token keystonecontext vnfpmaapp_v2

    [composite:vnflcm_versions]
    keystone = request_id catch_errors external_oauth2_token keystonecontext vnflcm_api_versions

    [composite:vnffm_v1]
    keystone = request_id catch_errors external_oauth2_token keystonecontext vnffmaapp_v1

    [filter:external_oauth2_token]
    paste.filter_factory = keystonemiddleware.external_oauth2_token:filter_factory

2. Modify the configuration file ``tacker.conf`` to enable Keystonemiddleware
   to use the external OAuth 2.0 authorization server to verify the token
   and enable Tacker to get an access token from the external OAuth 2.0
   authorization server to access other OpenStack services.

   If the external OAuth 2.0 authorization server requires HTTPS communication,
   you need to specify the CA certificate to the config parameters ``cafile``
   to verify the external OAuth 2.0 authorization server's certificate. If the
   config parameter ``insecure`` is set to True, the CA certificate specified
   by the config parameter ``cafile`` is not used for verification.

   If the external OAuth 2.0 authorization server requires mTLS communication,
   you need to configure the config parameters ``certfile``, ``keyfile`` and
   ``cafile``.

   If you need to enable Tacker server to use mTLS communication, you must set
   the config parameter ``use_ssl`` to True and you need to configure the
   config parameters ``ssl_cert_file``, ``ssl_key_file`` and ``ssl_ca_file``.
   You can refer to the `OAuth 2.0 mTLS usage guide`_ to generating the
   client/server certificates for mTLS.

   If the config parameter ``thumbprint_verify`` is set to True, the token will
   be verified against the client certificate that used to obtain access token.
   So, to access Tacker APIs, you need to use the same client certificate that
   is used to obtain access token from the external OAuth 2.0 authorization
   server. It is also necessary to ensure that the external OAuth 2.0
   authorization server is configured to include the client certificate
   thumbprint information in access token. For the claim used to store the
   thumbprint of the client certificate ``cnf/x5t#S256``, see the subsequent
   samples.

   In order to enable Tacker to able to obtain user information, such
   as Project ID, User ID, Roles, etc., it is necessary to set the config
   parameters that starts with ``mapping_`` and ensure that all access tokens
   contain data that conforms to the specified format.

   If the config parameter ``use_ext_oauth2_auth`` is set to True, Tacker APIs
   will obtain an access token from the external OAuth 2.0 authorization server
   and then access other OpenStack services such as Barbican. If the config
   parameter ``use_ext_oauth2_auth`` is set to False, Tacker APIs will keep the
   original logic, get an x-auth-token from the Keystone identity server, and
   then access the other OpenStack services.

   The current Tacker APIs supports the following 5 Client Credentials Grant
   flows:

   * ``client_secret_basic``
   * ``client_secret_post``
   * ``private_key_jwt``
   * ``client_secret_jwt``
   * ``tls_client_auth``


   The following parts is the sample configurations for each method.

   * client_secret_basic:
      This is sample configuration of ``client_secret_basic`` authentication
      method with these requirements:

      * Tacker APIs requires mTLS
      * External 0Auth 2.0 authorization server requires mTLS
      * Token thumbprint confirmation is required

      .. code-block:: console

       [DEFAULT]
       use_ssl=True
       ssl_ca_file=/etc/tacker/ca.pem
       ssl_cert_file=/etc/tacker/tacker_server.pem
       ssl_key_file=/etc/tacker/tacker_server.key

       [ext_oauth2_auth]
       use_ext_oauth2_auth=True
       token_endpoint=https://keycloak.host:8443/realms/testrealm/protocol/openid-connect/token
       scope=openstack
       introspect_endpoint=https://keycloak.host:8443/realms/testrealm/protocol/openid-connect/token/introspect
       audience=https://keycloak.host:8443/realms/testrealm
       auth_method=client_secret_basic
       client_id=tacker_service
       client_secret=sPocbjFjQCmrPPAXY9IUOVNJ9Cw3rDw5
       certfile=/etc/tacker/tacker_client.pem
       keyfile=/etc/tacker/tacker_client.key
       cafile=/etc/tacker/ca.pem
       insecure=False
       thumbprint_verify=True
       mapping_project_id=project.id
       mapping_project_name=project.name
       mapping_project_domain_id=project.domain.id
       mapping_project_domain_name=project.domain.name
       mapping_user_id=user.id
       mapping_user_name=user.name
       mapping_user_domain_id=user.domain.id
       mapping_user_domain_name=user.domain.name
       mapping_roles=user.roles


   * client_secret_post:
      This is sample configuration of ``client_secret_post`` authentication
      method with these requirements:

      * Tacker APIs requires HTTPS
      * External 0Auth 2.0 authorization server doesn't require HTTPS
      * Token thumbprint confirmation is not required

      .. code-block:: console

       [DEFAULT]
       use_ssl=True
       ssl_cert_file=/etc/tacker/tacker_server.pem
       ssl_key_file=/etc/tacker/tacker_server.key

       [ext_oauth2_auth]
       use_ext_oauth2_auth=True
       token_endpoint=http://keycloak.host:8080/realms/testrealm/protocol/openid-connect/token
       scope=openstack
       introspect_endpoint=http://keycloak.host:8080/realms/testrealm/protocol/openid-connect/token/introspect
       audience=http://keycloak.host:8080/realms/testrealm
       auth_method=client_secret_post
       client_id=tacker_service
       client_secret=sPocbjFjQCmrPPAXY9IUOVNJ9Cw3rDw5
       insecure=True
       thumbprint_verify=False
       mapping_project_id=project.id
       mapping_project_name=project.name
       mapping_project_domain_id=project.domain.id
       mapping_project_domain_name=project.domain.name
       mapping_user_id=user.id
       mapping_user_name=user.name
       mapping_user_domain_id=user.domain.id
       mapping_user_domain_name=user.domain.name
       mapping_roles=user.roles

   * private_key_jwt:
      This is sample configuration of ``private_key_jwt`` authentication
      method with these requirements:

      * Tacker APIs doesn't require HTTPS
      * External 0Auth 2.0 authorization requires HTTPS
      * Token thumbprint confirmation is not required

      .. code-block:: console

       [DEFAULT]
       use_ssl=False

       [ext_oauth2_auth]
       use_ext_oauth2_auth=True
       token_endpoint=https://keycloak.host:8443/realms/testrealm/protocol/openid-connect/token
       scope=openstack
       introspect_endpoint=https://keycloak.host:8443/realms/testrealm/protocol/openid-connect/token/introspect
       audience=https://keycloak.host:8443/realms/testrealm
       auth_method=private_key_jwt
       client_id=tacker_service
       jwt_key_file=/etc/tacker/private_jwt.key
       jwt_algorithm=RS256
       jwt_bearer_time_out=7200
       cafile=/etc/tacker/ca.pem
       insecure=False
       thumbprint_verify=False
       mapping_project_id=project.id
       mapping_project_name=project.name
       mapping_project_domain_id=project.domain.id
       mapping_project_domain_name=project.domain.name
       mapping_user_id=user.id
       mapping_user_name=user.name
       mapping_user_domain_id=user.domain.id
       mapping_user_domain_name=user.domain.name
       mapping_roles=user.roles


   * client_secret_jwt:
      This sample configuration of ``client_secret_jwt`` authentication
      method with these requirements:

      * Tacker APIs doesn't require HTTPS
      * External 0Auth 2.0 authorization server requires mTLS
      * Token thumbprint confirmation is not required

      .. code-block:: console

       [DEFAULT]
       use_ssl=False

       [ext_oauth2_auth]

       use_ext_oauth2_auth=True
       token_endpoint=https://keycloak.host:8443/realms/testrealm/protocol/openid-connect/token
       scope=openstack
       introspect_endpoint=https://keycloak.host:8443/realms/testrealm/protocol/openid-connect/token/introspect
       audience=https://keycloak.host:8443/realms/testrealm
       auth_method=client_secret_jwt
       client_id=tacker_service
       client_secret=gLQnfhNWrDMk6cKMKgKSALDcpiB2Hk7k
       certfile=/etc/tacker/tacker_client.pem
       keyfile=/etc/tacker/tacker_client.key
       jwt_algorithm=HS512
       jwt_bearer_time_out=7200
       cafile=/etc/tacker/ca.pem
       insecure=False
       thumbprint_verify=False
       mapping_project_id=project.id
       mapping_project_name=project.name
       mapping_project_domain_id=project.domain.id
       mapping_project_domain_name=project.domain.name
       mapping_user_id=user.id
       mapping_user_name=user.name
       mapping_user_domain_id=user.domain.id
       mapping_user_domain_name=user.domain.name
       mapping_roles=user.roles


   * tls_client_auth:
      This sample configuration of ``tls_client_auth`` authentication method
      with these requirements:

      * Tacker APIs requires mTLS
      * External 0Auth 2.0 authorization server requires mTLS
      * Token thumbprint confirmation is required

      .. note::

       Unlike mTLS is optional in the other authentication methods, mTLS is
       necessary when ``tls_client_auth`` is being used for authentication.


      .. code-block:: console

       [DEFAULT]
       use_ssl=True
       ssl_ca_file=/etc/tacker/ca.pem
       ssl_cert_file=/etc/tacker/tacker_server.pem
       ssl_key_file=/etc/tacker/tacker_server.key

       [ext_oauth2_auth]
       use_ext_oauth2_auth=True
       token_endpoint=https://keycloak.host:8443/realms/testrealm/protocol/openid-connect/token
       scope=openstack
       introspect_endpoint=https://keycloak.host:8443/realms/testrealm/protocol/openid-connect/token/introspect
       audience=https://keycloak.host:8443/realms/testrealm
       auth_method=tls_client_auth
       client_id=tacker_service
       certfile=/etc/tacker/tacker_client.pem
       keyfile=/etc/tacker/tacker_client.key
       cafile=/etc/tacker/ca.pem
       insecure=False
       thumbprint_verify=True
       mapping_project_id=project.id
       mapping_project_name=project.name
       mapping_project_domain_id=project.domain.id
       mapping_project_domain_name=project.domain.name
       mapping_user_id=user.id
       mapping_user_name=user.name
       mapping_user_domain_id=user.domain.id
       mapping_user_domain_name=user.domain.name
       mapping_roles=user.roles


3. Restart Tacker service so that the modified configuration information takes
   effect.

   .. code-block:: console

    $ sudo systemctl restart devstack@tacker.service
    $ sudo systemctl restart devstack@tacker-conductor.service


Verifying Access to Tacker APIs Using External Authorization Server
-------------------------------------------------------------------

Access to the Tacker APIs with the OAuth 2.0 access token to verify
that OAuth 2.0 Client Credentials Grant flow works correctly.

Using different external OAuth 2.0 authorization servers will need different
methods of obtaining access tokens. The following examples are only applicable
to scenarios where `Keycloak`_ is used as the external authorization server.

There are three steps to verify access to Tacker APIs using `Keycloak`_ as
external OAuth 2.0 Authentication server:

1. Execute the Get token API
   (/realms/{realm_name}/protocol/openid-connect/token) provided by
   `Keycloak`_.
2. Execute the Tacker APIs using the access token obtained from `Keycloak`_.
   For example, List VIM API (/v1.0/vims) provided by Tacker is used in this
   document.
3. Check the access token of the introspect API provided by `Keycloak`_ from
   the Tacker server logs.

The following parts is the examples for each of the 5 authentication methods.
The Tacker configuration used for each example can be referred to previous
chapter.

* client_secret_basic:
   When the `Keycloak`_ server requires to use the mTLS protocol and
   the ``client_secret_basic`` authentication method:

   .. code-block:: console

    $ curl -i -X POST https://keycloak.host:8443/realms/testrealm/protocol/openid-connect/token \
    -u tacker_service:sPocbjFjQCmrPPAXY9IUOVNJ9Cw3rDw5 \
    -d "scope=openstack" \
    -d "grant_type=client_credentials" \
    --cacert /opt/stack/certs/ca.pem \
    --key /opt/stack/certs/client.key \
    --cert /opt/stack/certs/client.pem
    HTTP/2 200
    cache-control: no-store
    pragma: no-cache
    content-length: 1873
    content-type: application/json
    referrer-policy: no-referrer
    strict-transport-security: max-age=31536000; includeSubDomains
    x-content-type-options: nosniff
    x-frame-options: SAMEORIGIN
    x-xss-protection: 1; mode=block
    {"access_token":"eyJhbGciOiJ.....MkgZ_T0dzJZg",
    "expires_in":300,"refresh_expires_in":0,
    "token_type":"Bearer","not-before-policy":0,
    "scope":"openstack"}

    $ curl  -i -X GET https://tacker.host:9890/v1.0/vims \
    -H "Authorization: Bearer eyJhbGciOiJ.....MkgZ_T0dzJZg"  \
    --cacert /opt/stack/certs/ca.pem \
    --key /opt/stack/certs/client.key \
    --cert /opt/stack/certs/client.pem
    HTTP/1.1 200 OK
    Content-Type: application/json
    Content-Length: 2182
    X-Openstack-Request-Id: req-7c1abeac-2179-4dde-b3e7-639b16853ca3
    Date: Mon, 09 Sep 2024 01:30:59 GMT
    {"vims": [{"id": "ce04bbe5-3ffe-449f-ba2a-69c0a747b9ad", "type": "kubernetes",
    "tenant_id": "2e189ea6c1df4e4ba6d89de254b3a534", "name": "test-vim-k8s",
    "description": "", "placement_attr": {"regions": ["default", "kube-node-lease",
    "kube-public", "kube-system"]}, "is_default": true, "created_at": "2024-07-04 09:07:56",
    "updated_at": null, "extra": {}, "auth_url": "https://10.0.2.15:6443",
    "vim_project": {"name": "nfv"}, "auth_cred": {"bearer_token": "***",
    "ssl_ca_cert": "gAAAAABmhm.....oN2Ps5SOO6yhOF_4w==", "auth_url":
    "https://10.0.2.15:6443", "username": "None", "key_type": "barbican_key",
    "secret_uuid": "***"}, "status": "ACTIVE"}]}

    $ tail -f /opt/stack/log/tacker-server.log
    DEBUG keystonemiddleware.external_oauth2_token [-] The introspect API response:
    {'exp': 1725845511, 'iat': 1725845211, 'jti': '79c8bc7b-b29e-484a-afde-1bab169ce482',
    'iss': 'https://keycloak.host:8443/realms/testrealm', 'aud': 'account',
    'sub': '7e3c5cb5-48a4-460c-b206-b8dca2ea0c36', 'typ': 'Bearer',
    'azp': 'tacker_service', 'acr': '1', 'allowed-origins': ['https://127.0.0.1:9890/'],
    'realm_access': {'roles': ['offline_access', 'uma_authorization', 'default-roles-testrealm']},
    'resource_access': {'tacker_service': {'roles': ['uma_protection']},
    'account': {'roles': ['manage-account', 'manage-account-links', 'view-profile']}},
    'cnf': {'x5t#S256': 'YGhr3eS01OTAAxAeksVwNc22gDnB-SSJPL7Y1BuqKvo'}, 'scope': 'openstack',
    'project': {'domain': {'name': 'Default', 'id': 'default'},
    'name': 'nfv', 'id': '2e189ea6c1df4e4ba6d89de254b3a534'},
    'preferred_username': 'service-account-tacker_service',
    'user': {'domain': {'name': 'Default', 'id': 'default'},
    'roles': 'admin', 'name': 'nfv_user', 'id': '173c59254d3040969e359e5df0a3b475'},
    'client_id': 'tacker_service', 'username': 'service-account-tacker_service',
    'token_type': 'Bearer', 'active': True} _fetch_token /opt/stack/data/venv/lib/python3.10/site-packages/keystonemiddleware/external_oauth2_token.py:732

* client_secret_post:
   When the `Keycloak`_ server requires to use the HTTP protocol and
   the ``client_secret_post`` authentication method:

   .. code-block:: console

    $ curl -i -X POST http://keycloak.host:8080/realms/testrealm/protocol/openid-connect/token \
    -d "client_id=tacker_service" -d "client_secret=sPocbjFjQCmrPPAXY9IUOVNJ9Cw3rDw5" \
    -d "scope=openstack" \
    -d "grant_type=client_credentials"
    HTTP/1.1 200 OK
    Cache-Control: no-store
    Pragma: no-cache
    content-length: 1785
    Content-Type: application/json
    Referrer-Policy: no-referrer
    Strict-Transport-Security: max-age=31536000; includeSubDomains
    X-Content-Type-Options: nosniff
    X-Frame-Options: SAMEORIGIN
    X-XSS-Protection: 1; mode=block
    {"access_token":"eyJhbGciOiJ.....dLL5j7v9DkI7g",
    "expires_in":300,"refresh_expires_in":0,
    "token_type":"Bearer","not-before-policy":0,
    "scope":"openstack"}

    $ curl  -i -X GET https://tacker.host:9890/v1.0/vims \
    -H "Authorization: Bearer eyJhbGciOiJ.....dLL5j7v9DkI7g" \
    --cacert /opt/stack/certs/ca.pem
    HTTP/1.1 200 OK
    Content-Type: application/json
    Content-Length: 2182
    X-Openstack-Request-Id: req-1960f278-82db-4ccf-81a1-be0839c024d2
    Date: Mon, 09 Sep 2024 02:02:59 GMT
    {"vims": [{"id": "ce04bbe5-3ffe-449f-ba2a-69c0a747b9ad", "type": "kubernetes",
    "tenant_id": "2e189ea6c1df4e4ba6d89de254b3a534", "name": "test-vim-k8s",
    "description": "", "placement_attr": {"regions": ["default", "kube-node-lease",
    "kube-public", "kube-system"]}, "is_default": true, "created_at": "2024-07-04 09:07:56",
    "updated_at": null, "extra": {}, "auth_url": "https://10.0.2.15:6443",
    "vim_project": {"name": "nfv"}, "auth_cred": {"bearer_token": "***",
    "ssl_ca_cert": "gAAAAABmhm.....oN2Ps5SOO6yhOF_4w==", "auth_url":
    "https://10.0.2.15:6443", "username": "None", "key_type": "barbican_key",
    "secret_uuid": "***"}, "status": "ACTIVE"}]}

    $ tail -f /opt/stack/log/tacker-server.log
    DEBUG keystonemiddleware.external_oauth2_token [-] The introspect API response:
    {'exp': 1725847413, 'iat': 1725847113, 'jti': 'db3bb08e-3b78-4c5b-9a62-6c382401d31a',
    'iss': 'http://keycloak.host:8080/realms/testrealm', 'aud': 'account',
    'sub': '7e3c5cb5-48a4-460c-b206-b8dca2ea0c36', 'typ': 'Bearer',
    'azp': 'tacker_service', 'acr': '1', 'allowed-origins': ['https://127.0.0.1:9890/'],
    'realm_access': {'roles': ['offline_access', 'uma_authorization', 'default-roles-testrealm']},
    'resource_access': {'tacker_service': {'roles': ['uma_protection']},
    'account': {'roles': ['manage-account', 'manage-account-links', 'view-profile']}},
    'scope': 'openstack', 'project': {'domain': {'name': 'Default', 'id': 'default'},
    'name': 'nfv', 'id': '2e189ea6c1df4e4ba6d89de254b3a534'}, 'preferred_username':
    'service-account-tacker_service', 'user': {'domain': {'name': 'Default', 'id': 'default'},
    'roles': 'admin', 'name': 'nfv_user', 'id': '173c59254d3040969e359e5df0a3b475'},
    'client_id': 'tacker_service', 'username': 'service-account-tacker_service',
    'token_type': 'Bearer', 'active': True} _fetch_token /opt/stack/data/venv/lib/python3.10/site-packages/keystonemiddleware/external_oauth2_token.py:732


* private_key_jwt:
   When the `Keycloak`_ server requires to use the HTTPS protocol and
   the ``private_key_jwt`` authentication method:

   .. code-block:: console

    $ curl -i -X POST https://keycloak.host:8443/realms/testrealm/protocol/openid-connect/token \
    -d "client_id=tacker_service" \
    -d "client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer" \
    -d "client_assertion=eyJhbGciOiJS.....EOr5ndYF4I6qg" \
    -d "grant_type=client_credentials" \
    --cacert /opt/stack/certs/ca.pem
    HTTP/2 200
    cache-control: no-store
    pragma: no-cache
    content-length: 1786
    content-type: application/json
    referrer-policy: no-referrer
    strict-transport-security: max-age=31536000; includeSubDomains
    x-content-type-options: nosniff
    x-frame-options: SAMEORIGIN
    x-xss-protection: 1; mode=block
    {"access_token":"eyJhbGciOiJSUz.....AQC1ms_YuUUgc8A",
    "expires_in":300,"refresh_expires_in":0,
    "token_type":"Bearer","not-before-policy":0,
    "scope":"openstack"}

    $ curl  -i -X GET http://tacker.host:9890/v1.0/vims \
    -H "Authorization: Bearer eyJhbGciOiJSUz.....AQC1ms_YuUUgc8A"  \
    HTTP/1.1 200 OK
    Content-Type: application/json
    Content-Length: 2182
    X-Openstack-Request-Id: req-9c287081-bd0b-4e43-ae80-06acfa1ca3a2
    Date: Mon, 09 Sep 2024 03:17:02 GMT
    {"vims": [{"id": "ce04bbe5-3ffe-449f-ba2a-69c0a747b9ad", "type": "kubernetes",
    "tenant_id": "2e189ea6c1df4e4ba6d89de254b3a534", "name": "test-vim-k8s",
    "description": "", "placement_attr": {"regions": ["default", "kube-node-lease",
    "kube-public", "kube-system"]}, "is_default": true, "created_at": "2024-07-04 09:07:56",
    "updated_at": null, "extra": {}, "auth_url": "https://10.0.2.15:6443",
    "vim_project": {"name": "nfv"}, "auth_cred": {"bearer_token": "***",
    "ssl_ca_cert": "gAAAAABmhm.....oN2Ps5SOO6yhOF_4w==", "auth_url":
    "https://10.0.2.15:6443", "username": "None", "key_type": "barbican_key",
    "secret_uuid": "***"}, "status": "ACTIVE"}]}

     $ tail -f /opt/stack/log/tacker-server.log
     DEBUG keystonemiddleware.external_oauth2_token [-] The introspect API response:
     {'exp': 1725852092, 'iat': 1725851792, 'jti': '3e61de0d-dc23-4a96-a08f-cce233e5a205',
     'iss': 'https://keycloak.host:8443/realms/testrealm', 'aud': 'account',
     'sub': '7e3c5cb5-48a4-460c-b206-b8dca2ea0c36', 'typ': 'Bearer',
     'azp': 'tacker_service', 'acr': '1', 'allowed-origins': ['https://127.0.0.1:9890/'],
     'realm_access': {'roles': ['offline_access', 'uma_authorization', 'default-roles-testrealm']},
     'resource_access': {'tacker_service': {'roles': ['uma_protection']},
     'account': {'roles': ['manage-account', 'manage-account-links', 'view-profile']}},
     'scope': 'openstack', 'project': {'domain': {'name': 'Default', 'id': 'default'},
     'name': 'nfv', 'id': '2e189ea6c1df4e4ba6d89de254b3a534'},
     'preferred_username': 'service-account-tacker_service',
     'user': {'domain': {'name': 'Default', 'id': 'default'}, 'roles': 'admin',
     'name': 'nfv_user', 'id': '173c59254d3040969e359e5df0a3b475'}, 'client_id': 'tacker_service',
     'username': 'service-account-tacker_service', 'token_type': 'Bearer',
     'active': True} _fetch_token /opt/stack/data/venv/lib/python3.10/site-packages/keystonemiddleware/external_oauth2_token.py:732


* client_secret_jwt:
   When the `Keycloak`_ server requires to use the mTLS protocol and
   the ``client_secret_jwt`` authentication method:

   .. code-block:: console

    $ curl -i -X POST https://keycloak.host:8443/realms/testrealm/protocol/openid-connect/token \
    -d "client_id=tacker_service" \
    -d "client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer" \
    -d "client_assertion=eyJhbGciOiJIUzUx.....UVZ11WvcKg" \
    -d "grant_type=client_credentials" \
    --cacert /opt/stack/certs/ca.pem \
    --key /opt/stack/certs/client.key \
    --cert /opt/stack/certs/client.pem
    HTTP/2 200
    cache-control: no-store
    pragma: no-cache
    content-length: 1786
    content-type: application/json
    referrer-policy: no-referrer
    strict-transport-security: max-age=31536000; includeSubDomains
    x-content-type-options: nosniff
    x-frame-options: SAMEORIGIN
    x-xss-protection: 1; mode=block
    {"access_token":"eyJhbGciOiJ.....m3tUXO7h22A",
    "expires_in":300,"refresh_expires_in":0,
    "token_type":"Bearer","not-before-policy":0,
    "scope":"openstack"}

    $ curl  -i -X GET http://tacker.host:9890/v1.0/vims \
    -H "Authorization: Bearer eyJhbGciOiJ.....m3tUXO7h22A"  \
    HTTP/1.1 200 OK
    Content-Type: application/json
    Content-Length: 2182
    X-Openstack-Request-Id: req-777f61b4-e9ea-40b8-90ef-ad1a628070eb
    Date: Mon, 09 Sep 2024 05:19:48 GMT
    {"vims": [{"id": "ce04bbe5-3ffe-449f-ba2a-69c0a747b9ad", "type": "kubernetes",
    "tenant_id": "2e189ea6c1df4e4ba6d89de254b3a534", "name": "test-vim-k8s",
    "description": "", "placement_attr": {"regions": ["default", "kube-node-lease",
    "kube-public", "kube-system"]}, "is_default": true, "created_at": "2024-07-04 09:07:56",
    "updated_at": null, "extra": {}, "auth_url": "https://10.0.2.15:6443",
    "vim_project": {"name": "nfv"}, "auth_cred": {"bearer_token": "***",
    "ssl_ca_cert": "gAAAAABmhm.....oN2Ps5SOO6yhOF_4w==", "auth_url":
    "https://10.0.2.15:6443", "username": "None", "key_type": "barbican_key",
    "secret_uuid": "***"}, "status": "ACTIVE"}]}

    $ tail -f /opt/stack/log/tacker-server.log
    DEBUG keystonemiddleware.external_oauth2_token [-] The introspect API response:
    {'exp': 1725859285, 'iat': 1725858985, 'jti': '9b93e2db-f948-48c3-bd75-acae1da70861',
    'iss': 'https://keycloak.host:8443/realms/testrealm', 'aud': 'account',
    'sub': '7e3c5cb5-48a4-460c-b206-b8dca2ea0c36', 'typ': 'Bearer',
    'azp': 'tacker_service', 'acr': '1', 'allowed-origins': ['https://127.0.0.1:9890/'],
    'realm_access': {'roles': ['offline_access', 'uma_authorization', 'default-roles-testrealm']},
    'resource_access': {'tacker_service': {'roles': ['uma_protection']},
    'account': {'roles': ['manage-account', 'manage-account-links', 'view-profile']}},
    'scope': 'openstack', 'project': {'domain': {'name': 'Default', 'id': 'default'},
    'name': 'nfv', 'id': '2e189ea6c1df4e4ba6d89de254b3a534'}, 'preferred_username': 'service-account-tacker_service',
    'user': {'domain': {'name': 'Default', 'id': 'default'},
    'roles': 'admin', 'name': 'nfv_user', 'id': '173c59254d3040969e359e5df0a3b475'},
    'client_id': 'tacker_service', 'username': 'service-account-tacker_service',
    'token_type': 'Bearer', 'active': True} _fetch_token /opt/stack/data/venv/lib/python3.10/site-packages/keystonemiddleware/external_oauth2_token.py:732


* tls_client_auth:
   When the `Keycloak`_ server requires to use the mTLS protocol and
   the ``tls_client_auth`` authentication method:

   .. code-block:: console

    $ curl -i -X POST https://keycloak.host:8443/realms/testrealm/protocol/openid-connect/token \
    -d "client_id=tacker_service" \
    -d "scope=openstack" \
    -d "grant_type=client_credentials" \
    --cacert /opt/stack/certs/ca.pem \
    --key /opt/stack/certs/client.key \
    --cert /opt/stack/certs/client.pem
    HTTP/2 200
    cache-control: no-store
    pragma: no-cache
    content-length: 1786
    content-type: application/json
    referrer-policy: no-referrer
    strict-transport-security: max-age=31536000; includeSubDomains
    x-content-type-options: nosniff
    x-frame-options: SAMEORIGIN
    x-xss-protection: 1; mode=block
    {"access_token":"eyJhbGciOiJ.....KS05dgQbXQm4FosedDw",
    "expires_in":300,"refresh_expires_in":0,
    "token_type":"Bearer","not-before-policy":0,
    "scope":"openstack"}

    $ curl -i -X GET https://tacker.host:9890/v1.0/vims \
    -H "Authorization: Bearer eyJhbGciOiJ.....KS05dgQbXQm4FosedDw" \
    --cacert /opt/stack/certs/ca.pem \
    --key /opt/stack/certs/client.key \
    --cert /opt/stack/certs/client.pem
    HTTP/1.1 200 OK
    Content-Type: application/json
    Content-Length: 2182
    X-Openstack-Request-Id: req-10d08c2c-acc1-4d77-8029-4718381ce704
    Date: Mon, 09 Sep 2024 05:47:39 GMT
    {"vims": [{"id": "ce04bbe5-3ffe-449f-ba2a-69c0a747b9ad", "type": "kubernetes",
    "tenant_id": "2e189ea6c1df4e4ba6d89de254b3a534", "name": "test-vim-k8s",
    "description": "", "placement_attr": {"regions": ["default", "kube-node-lease",
    "kube-public", "kube-system"]}, "is_default": true, "created_at": "2024-07-04 09:07:56",
    "updated_at": null, "extra": {}, "auth_url": "https://10.0.2.15:6443",
    "vim_project": {"name": "nfv"}, "auth_cred": {"bearer_token": "***",
    "ssl_ca_cert": "gAAAAABmhm.....oN2Ps5SOO6yhOF_4w==", "auth_url":
    "https://10.0.2.15:6443", "username": "None", "key_type": "barbican_key",
    "secret_uuid": "***"}, "status": "ACTIVE"}]}

    $ tail -f /opt/stack/log/tacker-server.log
    DEBUG keystonemiddleware.external_oauth2_token [-] The introspect API response:
    {'exp': 1725861128, 'iat': 1725860828, 'jti': '72d45cb4-ee3c-4c00-b137-be603612761f',
    'iss': 'https://keycloak.host:8443/realms/testrealm', 'aud': 'account',
    'sub': '7e3c5cb5-48a4-460c-b206-b8dca2ea0c36', 'typ': 'Bearer',
    'azp': 'tacker_service', 'acr': '1', 'allowed-origins': ['https://127.0.0.1:9890/'],
    'realm_access': {'roles': ['offline_access', 'uma_authorization', 'default-roles-testrealm']},
    'resource_access': {'tacker_service': {'roles': ['uma_protection']},
    'account': {'roles': ['manage-account', 'manage-account-links', 'view-profile']}},
    'cnf': {'x5t#S256': 'YGhr3eS01OTAAxAeksVwNc22gDnB-SSJPL7Y1BuqKvo'}, 'scope': 'openstack',
    'project': {'domain': {'name': 'Default', 'id': 'default'},
    'name': 'nfv', 'id': '2e189ea6c1df4e4ba6d89de254b3a534'},
    'preferred_username': 'service-account-tacker_service',
    'user': {'domain': {'name': 'Default', 'id': 'default'},
    'roles': 'admin', 'name': 'nfv_user', 'id': '173c59254d3040969e359e5df0a3b475'},
    'client_id': 'tacker_service', 'username': 'service-account-tacker_service', 'token_type': 'Bearer',
    'active': True} _fetch_token /opt/stack/data/venv/lib/python3.10/site-packages/keystonemiddleware/external_oauth2_token.py:732


About OpenStack Command
-----------------------

When using an external OAuth 2.0 authorization server, the current version of
OpenStack Command is not supported.

.. _tacker.conf: https://docs.openstack.org/tacker/latest/configuration/config.html
.. _RFC6749: https://datatracker.ietf.org/doc/html/rfc6749
.. _Keycloak: https://www.keycloak.org/
.. _NFV-SOL013 v3.3.1: https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/013/03.03.01_60/gs_nfv-sol013v030301p.pdf
.. _OAuth 2.0 mTLS usage guide: https://docs.openstack.org/tacker/latest/admin/oauth2_mtls_usage_guide.html
.. _Middleware Architecture: https://docs.openstack.org/keystonemiddleware/latest/middlewarearchitecture.html
