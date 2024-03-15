==============================================================
Using External Authentication Server OAuth2.0 Grant for Tacker
==============================================================

Overview
~~~~~~~~
Sometimes users may use the Client Credentials Grant flow in `RFC6749`_
OAuth 2.0 Authorization Framework provided by a third-party authorization
server (such as `Keycloak`_) for user authentication. OAuth2.0 Client
Credentials Grant flow is prescribed in the API specification of ETSI
`NFV-SOL013 v3.3.1`_. Tacker uses the keystone middleware to support OAuth2.0
Client Credentials Grant through the third-party authorization server.
In addition, Tacker can also via the Client Credentials Grant flow in
`RFC6749`_ OAuth 2.0 Authorization Framework access other OpenStack services
that use the third-party authentication servers for user authentication.

Preparations
~~~~~~~~~~~~
To use external OAuth2.0 authorization server for Tacker, it is necessary
to confirm that the token filter factory ``external_oauth2_token`` is supported
in the keystone middleware. In this example, the `Keycloak`_ server is used as
the third-party authorization server, and keycloak.host is the domain name
used by the `Keycloak`_ server, and the domain name used by the Tacker server
is tacker.host.

Guide
~~~~~
To use external OAuth2.0 authorization server for Tacker, you should configure
the tacker-server and the Keystone middleware in the following steps.

.. _RFC6749: https://datatracker.ietf.org/doc/html/rfc6749
.. _Keycloak: https://www.keycloak.org/
.. _NFV-SOL013 v3.3.1: https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/013/03.03.01_60/gs_nfv-sol013v030301p.pdf

Enable To Use External OAuth2.0 Authorization Server
----------------------------------------------------
To handle API requests using external OAuth2.0 authorization server
authorization you have to configure the keystone middleware which accepts
API calls from clients and verifies a client's identity,
see `Middleware Architecture`_.

1. Add ``keystonemiddleware.external_oauth2_token:filter_factory`` to the
   configuration file ``api-paste.ini`` to enable External OAuth2.0
   Authorization Server Authorization.

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

    [composite:vnflcm_versions]
    keystone = request_id catch_errors external_oauth2_token keystonecontext vnflcm_api_versions

    [filter:external_oauth2_token]
    paste.filter_factory = keystonemiddleware.external_oauth2_token:filter_factory

2. Modify the configuration file ``tacker.conf`` to enable keystone middleware
   to access the external OAuth2.0 authorization server to verify the token
   and enable Tacker to get an access token through the external OAuth2.0
   authorization server to access other OpenStack services.

   If the external OAuth2.0 authorization server requires HTTPS communication,
   you need to set the config parameters ``cafile`` and ``insecure``. When the
   certificate specified in the config parameter ``cafile`` needs to be used
   for authentication, the config parameter ``insecure`` needs to set True.
   If the config parameter ``cafile`` is not required or the certificate
   specified by the config parameter ``cafile`` is not used for authentication,
   the config parameter ``insecure`` must be set to False. If the external
   OAuth2.0 authorization server requires mTLS communication, you need to set
   the config parameters ``certfile``, ``keyfile`` and ``cafile``.

   If the config parameter ``thumbprint_verify`` is set to true, you need to
   refer to the `OAuth2.0 mTLS usage guide`_ to enable mTLS for Tacker. Users
   accessing the Tacker APIs must use the same client certificate that they
   used when obtaining an access token from the external OAuth2.0 authorization
   server. It is also necessary to ensure that the information about the access
   token obtained through the Introspect API includes the client certificate
   thumbprint information. For the field ``cnf/x5t#S256`` used to store the
   thumbprint of the client certificate, see the subsequent sample.

   In order to ensure that Tacker can correctly obtain user information, such
   as Project ID, User ID, Roles, etc., it is necessary to set the config
   parameters that starts with ``mapping`` and ensure that all access tokens
   contain data that conforms to the specified format.

   If the config parameter ``use_ext_oauth2_auth`` is set to true, Tacker APIs
   will obtain an access token from the external OAuth2.0 authorization server
   and then access other OpenStack services such as Barbican. If the config
   parameter ``use_ext_oauth2_auth`` is set to false, Tacker APIs will keep the
   original logic, get an x-auth-token from the keystone identity server, and
   then access the other OpenStack services.

   Currently, five methods are supported: ``client_secret_basic``,
   ``client_secret_post``, ``private_key_jwt``, ``client_secret_jwt``,
   and ``tls_client_auth``, as detailed below:

   client_secret_basic:
       When the external OAuth2.0 authorization server requires to use the mTLS
       protocol and the ``client_secret_basic`` authentication method, and the
       Tacker APIs requires to use mTLS, the following configuration is
       performed:

       .. code-block:: console

        [DEFAULT]
        use_ssl=True
        ssl_ca_file=/etc/tacker/multi_ca.pem
        ssl_cert_file=/etc/tacker/tacker_host.pem
        ssl_key_file=/etc/tacker/tacker_host.key

        [ext_oauth2_auth]
        use_ext_oauth2_auth=True
        token_endpoint=https://keycloak.host:8443/realms/x509/protocol/openid-connect/token
        scope=openstack
        introspect_endpoint=https://keycloak.host:8443/realms/x509/protocol/openid-connect/token/introspect
        audience=https://keycloak.host:8443/realms/x509
        auth_method=client_secret_basic
        client_id=tacker_service
        client_secret=fsf3DkMQck5WxdLuhMSOh4e2ZLQTM4K5
        certfile=/etc/tacker/service-account-tacker_service.crt
        keyfile=/etc/tacker/service-account-tacker_service.pem
        cafile=/etc/tacker/root-ca.crt
        insecure=True
        thumbprint_verify=True
        mapping_project_id=project.id
        mapping_project_name=project.name
        mapping_project_domain_id=project.domain.id
        mapping_project_domain_name=project.domain.name
        mapping_user_id=client_id
        mapping_user_name=username
        mapping_user_domain_id=user_domain.id
        mapping_user_domain_name=user_domain.name
        mapping_roles=user_role

   client_secret_post:
       When the external OAuth2.0 authorization server requires to use the HTTP
       protocol and the ``client_secret_post`` authentication method, and the
       Tacker APIs do not require to use mTLS, the following configuration is
       performed:

       .. code-block:: console

        [DEFAULT]
        use_ssl=True
        ssl_cert_file=/etc/tacker/tacker_host.pem
        ssl_key_file=/etc/tacker/tacker_host.key

        [ext_oauth2_auth]
        use_ext_oauth2_auth=True
        token_endpoint=http://keycloak.host:8443/realms/x509/protocol/openid-connect/token
        scope=openstack
        introspect_endpoint=http://keycloak.host:8443/realms/x509/protocol/openid-connect/token/introspect
        audience=http://keycloak.host:8443/realms/x509
        auth_method=client_secret_post
        client_id=tacker_service
        client_secret=fsf3DkMQck5WxdLuhMSOh4e2ZLQTM4K5
        insecure=False
        thumbprint_verify=False
        mapping_project_id=project.id
        mapping_project_name=project.name
        mapping_project_domain_id=project.domain.id
        mapping_project_domain_name=project.domain.name
        mapping_user_id=client_id
        mapping_user_name=username
        mapping_user_domain_id=user_domain.id
        mapping_user_domain_name=user_domain.name
        mapping_roles=user_role

   private_key_jwt:
       When the external OAuth2.0 authorization server requires to use the
       HTTPS protocol and the ``private_key_jwt`` authentication method, and
       the Tacker APIs do not require to use mTLS, the following configuration
       is performed:

       .. code-block:: console

        [DEFAULT]
        use_ssl=False

        [ext_oauth2_auth]
        use_ext_oauth2_auth=True
        token_endpoint=https://keycloak.host:8443/realms/x509/protocol/openid-connect/token
        scope=openstack
        introspect_endpoint=https://keycloak.host:8443/realms/x509/protocol/openid-connect/token/introspect
        audience=https://keycloak.host:8443/realms/x509
        auth_method=private_key_jwt
        client_id=tacker_service
        cafile=/etc/tacker/root-ca.crt
        insecure=True
        jwt_key_file=/etc/tacker/service-account-tacker_service_keyjwt.key
        jwt_algorithm=RS256
        jwt_bearer_time_out=7200
        thumbprint_verify=False
        mapping_project_id=project.id
        mapping_project_name=project.name
        mapping_project_domain_id=project.domain.id
        mapping_project_domain_name=project.domain.name
        mapping_user_id=client_id
        mapping_user_name=username
        mapping_user_domain_id=user_domain.id
        mapping_user_domain_name=user_domain.name
        mapping_roles=user_role

   client_secret_jwt:
       When the external OAuth2.0 authorization server requires to use the mTLS
       protocol and the ``client_secret_jwt`` authentication method, and the
       Tacker APIs do not require to use mTLS, the following configuration is
       performed:

       .. code-block:: console

        [DEFAULT]
        use_ssl=False

        [ext_oauth2_auth]
        use_ext_oauth2_auth=True
        token_endpoint=https://keycloak.host:8443/realms/x509/protocol/openid-connect/token
        scope=openstack
        introspect_endpoint=https://keycloak.host:8443/realms/x509/protocol/openid-connect/token/introspect
        audience=https://keycloak.host:8443/realms/x509
        auth_method=client_secret_jwt
        client_id=tacker_service
        client_secret=OrGhhu8K2QGWtWABfLM9akUwqnSuwLU1
        certfile=/etc/tacker/service-account-tacker_service.crt
        keyfile=/etc/tacker/service-account-tacker_service.pem
        cafile=/etc/tacker/root-ca.crt
        insecure=True
        jwt_algorithm=HS512
        jwt_bearer_time_out=7200
        thumbprint_verify=False
        mapping_project_id=project.id
        mapping_project_name=project.name
        mapping_project_domain_id=project.domain.id
        mapping_project_domain_name=project.domain.name
        mapping_user_id=client_id
        mapping_user_name=username
        mapping_user_domain_id=user_domain.id
        mapping_user_domain_name=user_domain.name
        mapping_roles=user_role

   tls_client_auth:
       When the external OAuth2.0 authorization server requires to use the mTLS
       protocol and the ``tls_client_auth`` authentication method, and the
       Tacker APIs requires to use mTLS, the following configuration is
       performed:

       .. code-block:: console

        [DEFAULT]
        use_ssl=True
        ssl_ca_file=/etc/tacker/multi_ca.pem
        ssl_cert_file=/etc/tacker/tacker_host.pem
        ssl_key_file=/etc/tacker/tacker_host.key

        [ext_oauth2_auth]
        use_ext_oauth2_auth=True
        token_endpoint=https://keycloak.host:8443/realms/x509/protocol/openid-connect/token
        scope=openstack
        introspect_endpoint=https://keycloak.host:8443/realms/x509/protocol/openid-connect/token/introspect
        audience=https://keycloak.host:8443/realms/x509
        auth_method=tls_client_auth
        client_id=tacker_service
        client_secret=OrGhhu8K2QGWtWABfLM9akUwqnSuwLU1
        certfile=/etc/tacker/service-account-tacker_service.crt
        keyfile=/etc/tacker/service-account-tacker_service.pem
        cafile=/etc/tacker/root-ca.crt
        insecure=True
        thumbprint_verify=True
        mapping_project_id=project.id
        mapping_project_name=project.name
        mapping_project_domain_id=project.domain.id
        mapping_project_domain_name=project.domain.name
        mapping_user_id=client_id
        mapping_user_name=username
        mapping_user_domain_id=user_domain.id
        mapping_user_domain_name=user_domain.name
        mapping_roles=user_role

3. Restart Tacker service so that the modified configuration information takes
   effect.

   .. code-block:: console

    $ sudo systemctl restart devstack@tacker.service
    $ sudo systemctl restart devstack@tacker-conductor.service

4. Access the Tacker APIs with the OAuth2.0 access token to confirm
   that OAuth2.0 Client Credentials Grant flow works correctly.

   The current Tacker APIs can receive OAuth2.0 access tokens obtained through
   the following 5 methods: ``client_secret_basic``, ``client_secret_post``,
   ``private_key_jwt``, ``client_secret_jwt``, and ``tls_client_auth``.
   Different external OAuth2.0 authorization servers will have different
   methods to obtain OAuth2.0 access tokens. The following example is only
   applicable to scenarios where `Keycloak`_ is used as the OAuth2.0
   authentication server.

   client_secret_basic:
       When the `Keycloak`_ server requires to use the mTLS protocol and
       the ``client_secret_basic`` authentication method, The following example
       is used to get an access token and use the access token to access
       Tacker APIs.

       There are three steps:

       1. Execute the Get token API
          (/realms/x509/protocol/openid-connect/token) provided by keycloak.

       2. Execute the List VIM API (/v1.0/vims) provided by tacker using the
          token obtained from keycloak.

       3. Check the results of the introspect API provided by keycloak from the
          Tacker server logs.

       .. code-block:: console

        $ curl -i -X POST https://keycloak.host:8443/realms/x509/protocol/openid-connect/token \
        -u test_user:L3gOqrORqoIZIgrZUZsCFY9AdnFvxLDm  \
        -d "scope=tacker" \
        -d "grant_type=client_credentials" \
        --cacert /etc/tacker/root-ca.crt \
        --key /home/user/service-account-test_user.key \
        --cert /home/user/service-account-test_user.crt
        HTTP/2 200
        content-type: application/json

        {"access_token":"eyJhbG...LxZhfUdmoztnsJGr0mB7hvg",
        "expires_in":1800,"refresh_expires_in":0,"token_type":"Bearer",
        "not-before-policy":0,"scope":"tacker"}

        $ curl  -i -X GET https://tacker.host:9890/v1.0/vims \
        -H "Authorization: Bearer eyJhbG...LxZhfUdmoztnsJGr0mB7hvg"  \
        --cacert /etc/tacker/root-ca.crt \
        --key /home/user/service-account-test_user.key \
        --cert /home/user/service-account-test_user.crt
        HTTP/2 200
        content-type: application/json

        {"vims": []}

        $ tail -f /opt/stack/log/tacker-server.log
        2023-02-17 06:45:50.249 DEBUG keystonemiddleware.external_oauth2_token [-] The introspect API response:
        {'exp': 1676618506, 'iat': 1676616706, 'jti': '7e4a7d26-e8f4-4065-bcfb-2d9c6fc40681',
        'iss': 'https://keycloak.host:8443/realms/x509', 'aud': 'account',
        'sub': '9ffa28c0-b325-4cb7-9a87-ea76ce3dcc6d', 'typ': 'Bearer', 'azp': 'test_user', 'acr': '1',
        'realm_access': {'roles': ['offline_access', 'uma_authorization', 'default-roles-x509']},
        'resource_access': {'test_user': {'roles': ['member', 'admin']},
        'account': {'roles': ['manage-account', 'manage-account-links', 'view-profile']}},
        'cnf': {'x5t#S256': 'uwsXk4-tc62mdRMQ8o-gNyTj9HVH6YQKApXfOSdtjVo'},
        'scope': 'tacker',
        'user_role': 'admin',
        'user_domain': {'id': 'default', 'name': 'Default'},
        'project': {'id': '781381c76b2144f3a72ba2ec1ceda585', 'name': 'x509_demo', 'domain': {'id': 'default', 'name': 'Default'}},
        'client_id': 'test_user', 'username': 'service-account-test_user', 'active': True}
        from (pid=3757068) _fetch_token /usr/local/lib/python3.8/dist-packages/keystonemiddleware/external_oauth2_token.py:572

   client_secret_post:
       When the `Keycloak`_ server requires to use the HTTP protocol and
       the ``client_secret_post`` authentication method, The following example
       is used to get an access token and use the access token to access Tacker
       APIs.

       .. code-block:: console

        $ curl -i -X POST http://keycloak.host:8443/realms/x509/protocol/openid-connect/token \
        -d "client_id=test_user"  -d "client_secret=L3gOqrORqoIZIgrZUZsCFY9AdnFvxLDm" \
        -d "scope=tacker" \
        -d "grant_type=client_credentials"
        HTTP/2 200
        content-type: application/json

        {"access_token":"eyJhbGciOiJSUz...6liLqohYVEdda1SKPykV4RtG11V8r9kme_KTwzw",
        "expires_in":1800,"refresh_expires_in":0,"token_type":"Bearer",
        "not-before-policy":0,"scope":"tacker"}

        $ curl  -i -X GET http://tacker.host:9890/v1.0/vims \
        -H "Authorization: Bearer eyJhbGciOiJSUz...6liLqohYVEdda1SKPykV4RtG11V8r9kme_KTwzw"
        HTTP/2 200
        content-type: application/json

        {"vims": []}

        $ tail -f /opt/stack/log/tacker-server.log
        2023-02-17 06:38:12.073 DEBUG keystonemiddleware.external_oauth2_token [-] The introspect API response:
        {'exp': 1676618048, 'iat': 1676616248, 'jti': '97e38dc8-191c-4ace-b9c0-3e81baf4bfc1',
        'iss': 'http://keycloak.host:8443/realms/x509', 'aud': 'account',
        'sub': '9ffa28c0-b325-4cb7-9a87-ea76ce3dcc6d', 'typ': 'Bearer', 'azp': 'test_user', 'acr': '1',
        'realm_access': {'roles': ['offline_access', 'uma_authorization', 'default-roles-x509']},
        'resource_access': {'test_user': {'roles': ['member', 'admin']},
        'account': {'roles': ['manage-account', 'manage-account-links', 'view-profile']}},
        'scope': 'tacker',
        'user_role': 'admin',
        'user_domain': {'id': 'default', 'name': 'Default'},
        'project': {'id': '781381c76b2144f3a72ba2ec1ceda585', 'name': 'x509_demo', 'domain': {'id': 'default', 'name': 'Default'}},
        'client_id': 'test_user', 'username': 'service-account-test_user', 'active': True}
        from (pid=3757068) _fetch_token /usr/local/lib/python3.8/dist-packages/keystonemiddleware/external_oauth2_token.py:572

   private_key_jwt:
       When the `Keycloak`_ server requires to use the HTTPS protocol and
       the ``private_key_jwt`` authentication method, The following example is
       used to get an access token and use the access token to access Tacker
       APIs.

       .. code-block:: console

        $ curl -i -X POST https://keycloak.host:8443/realms/x509/protocol/openid-connect/token \
        -d "client_id=keyjwt_client" \
        -d "client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer" \
        -d "client_assertion=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI2ZG...VcCRHxhuc" \
        -d "grant_type=client_credentials" \
        --cacert /etc/tacker/root-ca.crt \
        HTTP/2 200
        content-type: application/json

        {"access_token":"eyJhbG...wNL5LpRfkaYQ",
        "expires_in":300,"refresh_expires_in":0,"token_type":"Bearer",
        "not-before-policy":0,"scope":"tacker"}

        $ curl  -i -X GET https://tacker.host:9890/v1.0/vims \
        -H "Authorization: Bearer eyJhbG...wNL5LpRfkaYQ"  \
        --cacert /etc/tacker/root-ca.crt \
        HTTP/2 200
        content-type: application/json

        {"vims": []}

        $ tail -f /opt/stack/log/tacker-server.log
        2023-02-17 07:27:43.125 DEBUG keystonemiddleware.external_oauth2_token [-] The introspect API response:
        {'exp': 1676619519, 'iat': 1676619219, 'jti': '44f439a6-ba0a-4f40-95a8-783cfe883ded',
        'iss': 'https://keycloak.host:8443/realms/x509', 'aud': 'account',
        'sub': '571cf4a0-1f9b-40e6-b1d9-a82699ef2408', 'typ': 'Bearer', 'azp': 'keyjwt_client',
        'preferred_username': 'service-account-keyjwt_client', 'email_verified': False, 'acr': '1',
        'realm_access': {'roles': ['offline_access', 'uma_authorization', 'default-roles-x509']},
        'resource_access': {'account': {'roles': ['manage-account', 'manage-account-links', 'view-profile']}},
        'scope': 'tacker',
        'user_role': 'member,reader,admin',
        'user_domain': {'id': 'default', 'name': 'Default'},
        'project': {'id': '781381c76b2144f3a72ba2ec1ceda585', 'name': 'x509_demo', 'domain': {'id': 'default', 'name': 'Default'}},
        'client_id': 'keyjwt_client', 'username': 'service-account-keyjwt_client', 'active': True}
        from (pid=3757068) _fetch_token /usr/local/lib/python3.8/dist-packages/keystonemiddleware/external_oauth2_token.py:572

   client_secret_jwt:
       When the `Keycloak`_ server requires to use the mTLS protocol and
       the ``client_secret_jwt`` authentication method, The following example
       is used to get an access token and use the access token to access Tacker
       APIs.

       .. code-block:: console

        $ curl -i -X POST https://keycloak.host:8443/realms/x509/protocol/openid-connect/token \
        -d "client_id=test_user" \
        -d "client_secret=Lc2r8g4dyLhkko1U1SnascZd0OBKywXl" \
        -d "client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer" \
        -d "client_assertion=eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJqdGkiOi...wOSJ9.tJ77ruMcWv0...18LyfLA" \
        -d "grant_type=client_credentials"  \
        --cacert /etc/tacker/root-ca.crt \
        --key /home/user/service-account-test_user.key \
        --cert /home/user/service-account-test_user.crt
        HTTP/2 200
        content-type: application/json

        {"access_token":"eyJhbGciOiJSU...F3QiGVd3XP_NWpaG5CssLQFK2A",
        "expires_in":300,"refresh_expires_in":0,"token_type":"Bearer",
        "not-before-policy":0,"scope":"tacker"}

        $ curl  -i -X GET https://tacker.host:9890/v1.0/vims \
        -H "Authorization: Bearer eyJhbGciOiJSU...F3QiGVd3XP_NWpaG5CssLQFK2A"  \
        --cacert /etc/tacker/root-ca.crt
        HTTP/2 200
        content-type: application/json

        {"vims": []}

        $ tail -f /opt/stack/log/tacker-server.log
        2023-02-17 07:13:49.616 DEBUG keystonemiddleware.external_oauth2_token [-] The introspect API response:
        {'exp': 1676618686, 'iat': 1676618386, 'jti': '25355211-b55c-408e-8434-51c32ab349a5',
        'iss': 'https://keycloak.host:8443/realms/x509', 'aud': 'account',
        'sub': '181fefcc-88f4-4124-bebf-efb1471c8696', 'typ': 'Bearer', 'azp': 'test_user',
        'preferred_username': 'service-account-test_user', 'email_verified': False, 'acr': '1',
        'realm_access': {'roles': ['offline_access', 'uma_authorization', 'default-roles-x509']},
        'resource_access': {'account': {'roles': ['manage-account', 'manage-account-links', 'view-profile']}},
        'cnf': {'x5t#S256': 'Kv2q-GjkXjVm7-IJfBBw9yBeeFuR7zk7akcTs-9pErU'},
        'scope': 'tacker',
        'user_role': 'admin,member,reader',
        'user_domain': {'id': 'default', 'name': 'Default'},
        'project': {'id': '781381c76b2144f3a72ba2ec1ceda585', 'name': 'x509_demo', 'domain': {'id': 'default', 'name': 'Default'}},
        'client_id': 'test_user', 'username': 'service-account-test_user', 'active': True}
        from (pid=3757068) _fetch_token /usr/local/lib/python3.8/dist-packages/keystonemiddleware/external_oauth2_token.py:572

   tls_client_auth:
       When the `Keycloak`_ server requires to use the mTLS protocol and
       the ``tls_client_auth`` authentication method, The following example is
       used to get an access token and use the access token to access Tacker
       APIs.

       .. code-block:: console

        $ curl -i -X POST https://keycloak.host:8443/realms/x509/protocol/openid-connect/token \
        -d "client_id=test_user"  \
        -d "scope=tacker" \
        -d "grant_type=client_credentials" \
        --cacert /etc/tacker/root-ca.crt \
        --key /home/user/service-account-test_user.key \
        --cert /home/user/service-account-test_user.crt
        HTTP/2 200
        content-type: application/json

        {"access_token":"eyJhbGciOiJSU...oNCJB1FlDaKSvoVW2pw",
        "expires_in":300,"refresh_expires_in":0,"token_type":"Bearer",
        "not-before-policy":0,"scope":"tacker"}

        $ curl  -i -X GET https://tacker.host:9890/v1.0/vims \
        -H "Authorization: Bearer eyJhbGciOiJSU...oNCJB1FlDaKSvoVW2pw"  \
        --cacert /etc/tacker/root-ca.crt \
        --key /home/user/service-account-test_user.key \
        --cert /home/user/service-account-test_user.crt
        HTTP/2 200
        content-type: application/json

        $ tail -f /opt/stack/log/tacker-server.log
        2023-02-17 06:51:10.813 DEBUG keystonemiddleware.external_oauth2_token [-] The introspect API response:
        {'exp': 1676617327, 'iat': 1676617027, 'jti': 'eb00125b-d735-4b6e-881f-09a6a7f5e239',
        'iss': 'https://keycloak.host:8443/realms/x509', 'aud': 'account',
        'sub': '46988f24-6206-4389-8f49-f42d9fad0053', 'typ': 'Bearer', 'azp': 'test_user',
        'preferred_username': 'service-account-test_user', 'email_verified': False, 'acr': '1',
        'realm_access': {'roles': ['offline_access', 'uma_authorization', 'default-roles-x509']},
        'resource_access': {'account': {'roles': ['manage-account', 'manage-account-links', 'view-profile']}},
        'cnf': {'x5t#S256': 'n3SavmAthh5FtxtrdCLb9hHBIHgimDbsB4vaSRAD1UU'},
        'scope': 'tacker',
        'user_role': 'member,reader,admin',
        'user_domain': {'id': 'default', 'name': 'Default'},
        'project': {'id': '781381c76b2144f3a72ba2ec1ceda585', 'name': 'x509_demo', 'domain': {'id': 'default', 'name': 'Default'}},
        'client_id': 'test_user', 'username': 'service-account-test_user', 'active': True}
        from (pid=3757068) _fetch_token /usr/local/lib/python3.8/dist-packages/keystonemiddleware/external_oauth2_token.py:572

.. _OAuth2.0 mTLS usage guide: https://docs.openstack.org/tacker/latest/admin/oauth2_mtls_usage_guide.html
.. _Middleware Architecture: https://docs.openstack.org/keystonemiddleware/latest/middlewarearchitecture.html

About OpenStack Command
-----------------------
When using an external OAuth2.0 authorization server, the current version of
OpenStack Command is not supported.

.. _tacker.conf: https://docs.openstack.org/tacker/latest/configuration/config.html
