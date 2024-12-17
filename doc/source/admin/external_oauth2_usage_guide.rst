=============================================================
Using External OAuth 2.0 Authorization Server for Tacker APIs
=============================================================

.. note::

  The content of this document has been confirmed to work using
  Tacker 2024.2 Dalmatian and Keycloak 26.0.2.


Overview
~~~~~~~~

Sometimes users may use the Client Credentials Grant flow of `RFC6749`_ OAuth
2.0 Authorization Framework provided by a third-party authorization server
(such as `Keycloak`_) for user authentication. OAuth 2.0 Client Credentials
Grant flow is prescribed in the API specification of ETSI `NFV-SOL013 v3.4.1`_.

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
server. The ``$keycloak_host_name`` is the domain name used by the `Keycloak`_
server, and the domain name used by the Tacker server is ``$tacker_host_name``.

Setup External Authorization Server
-----------------------------------

In this guide, Keycloak server will be configured and started as a docker
container by running the script. But the Keycloak server prepared in other way
can be used if user attributes mapper is setup properly.

The following is the example for running the script to setup the Keycloak
server. Before you run the script you should confirm and note at least user_id,
project_id to use in configuring the Keycloak.

.. code-block:: console

  $ openstack user show nfv_user
  +---------------------+----------------------------------+
  | Field               | Value                            |
  +---------------------+----------------------------------+
  | default_project_id  | None                             |
  | domain_id           | default                          |
  | email               | None                             |
  | enabled             | True                             |
  | id                  | 35c884d8a6544d38abce33c0003c8331 |
  | name                | nfv_user                         |
  | description         | None                             |
  | password_expires_at | None                             |
  +---------------------+----------------------------------+
  $ openstack project show nfv
  +-------------+----------------------------------+
  | Field       | Value                            |
  +-------------+----------------------------------+
  | description |                                  |
  | domain_id   | default                          |
  | enabled     | True                             |
  | id          | ce5b19a933354bdf87ac6d698494ad47 |
  | is_domain   | False                            |
  | name        | nfv                              |
  | options     | {}                               |
  | parent_id   | default                          |
  | tags        | []                               |
  +-------------+----------------------------------+


After confirming the required information, run the script file to start
Keycloak server. The script is interactive and will ask required information to
configure Keycloak server. And lastly it will output information required to
configure the Tacker server to use started Keycloak server as authorization
server and curl command to test token endpoint.

Currently, the script and Tacker APIs supports the following 5 Client
Credentials Grant flows:

* ``client_secret_post``
* ``client_secret_basic``
* ``private_key_jwt``
* ``client_secret_jwt``
* ``tls_client_auth``

In this guide, the ``client_secret_basic`` client will be used as for an
example to try external authentication.

.. note::

  You can see help by using -h or \-\-help option. And you can generate only
  Keycloak configuration and realm json only without actually starting the
  Keycloak server by providing -n or \-\-no-server option.


.. code-block:: console

  $ cd TACKER_ROOT/doc/tools/ext_oauth2_server
  $ bash ./gen_keycloak.sh
  Select the client credential grant flow type for keycloak server :
  1. client_secret_post
  2. client_secret_basic
  3. private_key_jwt
  4. client_secret_jwt
  5. tls_client_auth
  Enter your choice (1-5): 2
  You selected: client_secret_basic
  -------------------------

  Enable Oauth2 certificate-bounded token? (y/n) [default:n] :
  Oauth2 certificate-bounded token is disabled
  -------------------------

  Set auth type to client secret basic.
  -------------------------

  Enter OS username[default:nfv_user]:
  Successfully set OS username with nfv_user
  -------------------------

  Enter OS user id: 35c884d8a6544d38abce33c0003c8331
  Successfully set OS user id with 35c884d8a6544d38abce33c0003c8331
  -------------------------

  Enter OS user domain id[default:default]:
  Successfully set OS user domain id with default
  -------------------------

  Enter OS user domain name[default:Default]:
  Successfully set OS user domain name with default
  -------------------------

  Enter OS project name[default:nfv]:
  Successfully set OS project name with nfv
  -------------------------

  Enter OS project id: ce5b19a933354bdf87ac6d698494ad47
  Successfully set OS Project id with ce5b19a933354bdf87ac6d698494ad47
  -------------------------

  Enter OS project domain id[default:default]:
  Successfully set OS project domain id with default
  -------------------------

  Enter OS project domain name[default:Default]:
  Successfully set OS project domain name with default
  -------------------------

  Enter OS user roles[default:admin,member,reader]:
  Successfully set OS user roles with 'admin,member,reader'
  -------------------------

  Generating Certificate
  Certificate files already exist.
  Overwrite? (y/n) [default:n]:
  Existing file will be used
  -------------------------

  Creating Keycloak config
  -------------------------

  Starting Keycloak Server

  keycloak
  keycloak
  64e2422c88cabfae6cb65a87f167a32bd73382bd4c9693e4af9ee23a4264aebc
  Waiting Keycloak Server to start...[\]
  Keycloak server is started successfully.
  ###################################
  HTTP endpoint           : http://$keycloak_host_name:$keycloak_http_port/realms/testrealm/protocol/openid-connect/token
  HTTPS endpoint          : https://$keycloak_host_name:$keycloak_https_port/realms/testrealm/protocol/openid-connect/token
  client_id               : tacker_service, tacker_api_proj, tacker_api_domain
  client_secret           : iIK6lARLzJgoQQyMyoymNYrGTDuR0733S
  scope                   : project_scope, domain_scope
  * If you want to use other Keycloak server, import this realm.json
  realm JSON file         : SCRIPT_PATH/etc/keycloak/conf/base_realm.json
  * Use the following keys and certificates for Tacker and client
  RootCA certificate      : SCRIPT_PATH/etc/ssl/localcerts/ca.pem
  Tacker certificate      : SCRIPT_PATH/etc/ssl/localcerts/tacker.pem
  Tacker key              : SCRIPT_PATH/etc/ssl/localcerts/tacker.key
  client certificate      : SCRIPT_PATH/etc/ssl/localcerts/client.pem
  client key              : SCRIPT_PATH/etc/ssl/localcerts/client.pem
  ------------------------------------
  You can try getting a token using following command

  curl -s -X POST http://$keycloak_host_name:$keycloak_http_port/realms/testrealm/protocol/openid-connect/token \
  -d 'scope=tacker_scope' -d 'client_id=tacker_service' -d 'grant_type=client_credentials' \
  -u 'tacker_service:iIK6lARLzJgoQQyMyoymNYrGTDuR0733S'
  ###################################


After running the script, Keycloak server will start running. In order to
confirm the server is you can try getting token by using the command from the
output of the script as follow.

.. code-block:: console

  $ curl -s -X POST http://$keycloak_host_name:$keycloak_http_port/realms/testrealm/protocol/openid-connect/token \
  -d 'scope=tacker_scope' -d 'client_id=tacker_service' -d 'grant_type=client_credentials' \
  -u 'tacker_service:iIK6lARLzJgoQQyMyoymNYrGTDuR0733S'

  {"access_token":"$access_token","expires_in":300,"refresh_expires_in":0,
  "token_type":"Bearer","not-before-policy":0,"scope":""}


You can reference the user attributes mapping setting of the scopes and
other settings like each client details by accessing
``http://$keycloak_host_name:$keycloak_http_port/admin/master/console/#/testrealm`` after starting
the keycloak server. The realm json file can also be found in
``{SCRIPT_PATH}/etc/keycloak/conf/base_realm.json`` as you can see in output of
the script.

The Keycloak server that is configured and started by using the script has
three clients preconfigured. One of them is prepared for Tacker and the other
two are prepared for users.

.. list-table::
    :header-rows: 1
    :widths: 20 30 25 25

    * - Name
      - Description
      - Where it is used
      - How to use
    * - tacker_service
      - A client for Tacker to call the OAuth2.0 token introspection API in
        Keycloak
      - Tacker -> Keycloak
      - Write credentials to tacker.conf
    * - tacker_api_proj
      - A client for users to call Tacker API with project scoped access token
      - User -> Tacker
      - Write mapping rules in ``tacker.conf`` and set credentials in requests
        to obtain access token from Keycloak
    * - tacker_api_domain
      - A client for users to call Tacker API with domain scoped access token
      - User -> Tacker
      - Write mapping rules in ``tacker.conf`` and set credentials in requests
        to obtain access token from Keycloak

The ``tacker_service`` client is used by Tacker to perform OAuth2.0 token
introspection. For this to happen, you need to write the client's credentials
to ``tacker.conf``.

The ``tacker_api_proj`` and ``tacker_api_domain`` can be used to call Tacker
API. You can choose one of them depending on the scope of the token you need.
The ``tacker_api_proj`` will obtain the project scoped token that is privileged
to access resources in a specific project whereas ``tacker_api_domain`` will
obtain the domain scoped token that is privileged to access resources in a
specific domain (c.f., `project details`_ and `domain details`_). You also need
to write correct mapping rules described later to ``tacker.conf`` so Tacker can
correctly obtain user attributes, such as ``project_id``, ``project_name``,
etc., from access token for subsequent processes.

In this guide, the ``tacker_api_proj`` client will be used as for an example.

.. note::

  If you want to configure those clients manually, please note that if
  project's ``id`` and ``name`` claims exist in a token, Keystonemiddleware
  will authorize a client for a specific project, otherwise, a client will be
  authorized for the project domain. You can find the configured claims in
  `Mappers tab of Client scope page in the Keycloak dashboard`_.


Guide
~~~~~

To use external OAuth 2.0 authorization server for Tacker, you should configure
the Tacker server and the Keystonemiddleware in the following steps.

Enable To Use External OAuth 2.0 Authorization Server
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
     #keystone = request_id catch_errors authtoken keystonecontext extensions tackerapiapp_v1_0
     keystone = request_id catch_errors external_oauth2_token keystonecontext extensions tackerapiapp_v1_0

     [composite:vnfpkgmapi_v1]
     #keystone = request_id catch_errors authtoken keystonecontext vnfpkgmapp_v1
     keystone = request_id catch_errors external_oauth2_token keystonecontext vnfpkgmapp_v1

     [composite:vnflcm_v1]
     #keystone = request_id catch_errors authtoken keystonecontext vnflcmaapp_v1
     keystone = request_id catch_errors external_oauth2_token keystonecontext vnflcmaapp_v1

     [composite:vnflcm_v2]
     #keystone = request_id catch_errors authtoken keystonecontext vnflcmaapp_v2
     keystone = request_id catch_errors external_oauth2_token keystonecontext vnflcmaapp_v2

     [composite:vnfpm_v2]
     #keystone = request_id catch_errors authtoken keystonecontext vnfpmaapp_v2
     keystone = request_id catch_errors external_oauth2_token keystonecontext vnfpmaapp_v2

     [composite:vnflcm_versions]
     #keystone = request_id catch_errors authtoken keystonecontext vnflcm_api_versions
     keystone = request_id catch_errors external_oauth2_token keystonecontext vnflcm_api_versions

     [composite:vnffm_v1]
     #keystone = request_id catch_errors authtoken keystonecontext vnffmaapp_v1
     keystone = request_id catch_errors external_oauth2_token keystonecontext vnffmaapp_v1

     [filter:external_oauth2_token]
     paste.filter_factory = keystonemiddleware.external_oauth2_token:filter_factory


2. Modify the configuration file ``tacker.conf`` to enable Keystonemiddleware
   to use the external OAuth 2.0 authorization server to verify the token
   and enable Tacker to get an access token from the external OAuth 2.0
   authorization server to access other OpenStack services.

   As described before, you need to change ``tacker.conf`` as follows:

   1. Write credentials of tacker_service client
   2. Write mapping rules for tacker_api_proj client

   You can use the following sample configuration to use keycloak server
   started above section.

   .. code-block:: ini

     [DEFAULT]
     use_ssl=False

     [ext_oauth2_auth]
     use_ext_oauth2_auth=True
     token_endpoint=http://$keycloak_host_name:$keycloak_http_port/realms/testrealm/protocol/openid-connect/token
     scope=tacker_scope
     introspect_endpoint=http://$keycloak_host_name:$keycloak_http_port/realms/testrealm/protocol/openid-connect/token/introspect
     audience=http://$keycloak_host_name:$keycloak_http_port/realms/testrealm
     auth_method=client_secret_basic
     client_id=tacker_service
     client_secret=iIK6lARLzJgoQQyMyoymNYrGTDuR0733S
     insecure=True
     thumbprint_verify=False
     mapping_project_id=project_info.id
     mapping_project_name=project_info.name
     mapping_project_domain_id=project_info.domain.id
     mapping_project_domain_name=project_info.domain.name
     mapping_user_id=user.id
     mapping_user_name=user.name
     mapping_user_domain_id=user.domain.id
     mapping_user_domain_name=user.domain.name
     mapping_roles=role_info


   .. note::

     If you just want to try external authentication with Tacker, you can skip
     the rest part of this step and go to `Verify Access to Tacker APIs`_.


   If you want to configure Tacker for your specific use case, you need to
   change the above parameters appropriately. For example, if the external
   OAuth 2.0 authorization server requires HTTPS communication, you need to
   specify the CA certificate to the config parameters ``cafile`` to verify
   the external OAuth 2.0 authorization server's certificate. If the config
   parameter ``insecure`` is set to True, the CA certificate specified by the
   config parameter ``cafile`` is not used for verification.

   If the external OAuth 2.0 authorization server requires mTLS communication,
   you need to configure the config parameters ``certfile``, ``keyfile`` and
   ``cafile``.

   .. note::

     In this guide, HTTP is used in all examples except for ``tls_client_auth``
     because mTLS is necessary in ``tls_client_auth`` authentication method.
     In production environment, using HTTPS is highly recommended for security.


   If you need to enable Tacker server to use mTLS communication, you must set
   the config parameter ``use_ssl`` to True and you need to configure the
   config parameters ``ssl_cert_file``, ``ssl_key_file`` and ``ssl_ca_file``.
   For details about setting up HTTPS or mTLS in Tacker, You can refer to the
   :doc:`/admin/configure_tls`.

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

   The following parts is the sample configurations for each method.

   * client_secret_post:
      This is sample configuration of ``client_secret_post`` authentication
      method:

      .. code-block:: ini

        [DEFAULT]
        use_ssl=False

        [ext_oauth2_auth]
        use_ext_oauth2_auth=True
        token_endpoint=http://$keycloak_host_name:$keycloak_http_port/realms/testrealm/protocol/openid-connect/token
        scope=tacker_scope
        introspect_endpoint=http://$keycloak_host_name:$keycloak_http_port/realms/testrealm/protocol/openid-connect/token/introspect
        audience=http://$keycloak_host_name:$keycloak_http_port/realms/testrealm
        auth_method=client_secret_post
        client_id=tacker_service
        client_secret=iIK6lARLzJgoQQyMyoymNYrGTDuR0733S
        insecure=True
        thumbprint_verify=False
        mapping_project_id=project_info.id
        mapping_project_name=project_info.name
        mapping_project_domain_id=project_info.domain.id
        mapping_project_domain_name=project_info.domain.name
        mapping_user_id=user.id
        mapping_user_name=user.name
        mapping_user_domain_id=user.domain.id
        mapping_user_domain_name=user.domain.name
        mapping_roles=role_info


   * private_key_jwt:
      This is sample configuration of ``private_key_jwt`` authentication
      method:

      .. note::

        When getting token in ``private_key_jwt`` and ``client_secret_jwt``,
        the ``client_assertion`` of the request body is signed JWT that is
        locally created and consists of the claims like ``iss``, ``aud``, etc.
        The detailed format and claims can be referenced in
        `openid-connect 1.0 core specs`_ and `RFC7523`_, and how to create,
        encrypt and sign JWT in `RFC7519`_.


      .. code-block:: ini

        [DEFAULT]
        use_ssl=False

        [ext_oauth2_auth]
        use_ext_oauth2_auth=True
        token_endpoint=http://$keycloak_host_name:$keycloak_http_port/realms/testrealm/protocol/openid-connect/token
        scope=tacker_scope
        introspect_endpoint=http://$keycloak_host_name:$keycloak_http_port/realms/testrealm/protocol/openid-connect/token/introspect
        audience=http://$keycloak_host_name:$keycloak_http_port/realms/testrealm
        auth_method=private_key_jwt
        client_id=tacker_service
        jwt_key_file=/etc/tacker/private_key.pem
        jwt_algorithm=RS256
        jwt_bearer_time_out=7200
        insecure=True
        thumbprint_verify=False
        mapping_project_id=project_info.id
        mapping_project_name=project_info.name
        mapping_project_domain_id=project_info.domain.id
        mapping_project_domain_name=project_info.domain.name
        mapping_user_id=user.id
        mapping_user_name=user.name
        mapping_user_domain_id=user.domain.id
        mapping_user_domain_name=user.domain.name
        mapping_roles=role_info


   * client_secret_jwt:
      This sample configuration of ``client_secret_jwt`` authentication
      method:

      .. code-block:: ini

        [DEFAULT]
        use_ssl=False

        [ext_oauth2_auth]
        use_ext_oauth2_auth=True
        token_endpoint=http://$keycloak_host_name:$keycloak_http_port/realms/testrealm/protocol/openid-connect/token
        scope=tacker_scope
        introspect_endpoint=http://$keycloak_host_name:$keycloak_http_port/realms/testrealm/protocol/openid-connect/token/introspect
        audience=http://$keycloak_host_name:$keycloak_http_port/realms/testrealm
        auth_method=client_secret_jwt
        client_id=tacker_service
        client_secret=iIK6lARLzJgoQQyMyoymNYrGTDuR0733S
        jwt_algorithm=HS512
        jwt_bearer_time_out=7200
        insecure=True
        thumbprint_verify=False
        mapping_project_id=project_info.id
        mapping_project_name=project_info.name
        mapping_project_domain_id=project_info.domain.id
        mapping_project_domain_name=project_info.domain.name
        mapping_user_id=user.id
        mapping_user_name=user.name
        mapping_user_domain_id=user.domain.id
        mapping_user_domain_name=user.domain.name
        mapping_roles=role_info


   * tls_client_auth:
      This sample configuration of ``tls_client_auth`` authentication method:

      .. note::

        Unlike mTLS is optional in the other authentication methods, mTLS is
        necessary when ``tls_client_auth`` is being used for authentication.


      .. code-block:: ini

        [DEFAULT]
        use_ssl=True
        ssl_ca_file=/etc/tacker/multi_ca.pem
        ssl_cert_file=/etc/tacker/tacker_api.pem
        ssl_key_file=/etc/tacker/tacker_api.key

        [ext_oauth2_auth]
        use_ext_oauth2_auth=True
        token_endpoint=https://$keycloak_host_name:$keycloak_https_port/realms/testrealm/protocol/openid-connect/token
        scope=tacker_scope
        introspect_endpoint=https://$keycloak_host_name:$keycloak_https_port/realms/testrealm/protocol/openid-connect/token/introspect
        audience=https://$keycloak_host_name:$keycloak_https_port/realms/testrealm
        auth_method=tls_client_auth
        client_id=tacker_service
        certfile=/etc/tacker/tacker_client.pem
        keyfile=/etc/tacker/tacker_client.key
        cafile=/etc/tacker/ca.pem
        insecure=False
        thumbprint_verify=True
        mapping_project_id=project_info.id
        mapping_project_name=project_info.name
        mapping_project_domain_id=project_info.domain.id
        mapping_project_domain_name=project_info.domain.name
        mapping_user_id=user.id
        mapping_user_name=user.name
        mapping_user_domain_id=user.domain.id
        mapping_user_domain_name=user.domain.name
        mapping_roles=role_info


3. Restart Tacker service so that the modified configuration information takes
   effect.

   .. code-block:: console

     $ sudo systemctl restart devstack@tacker.service
     $ sudo systemctl restart devstack@tacker-conductor.service


.. _Verify Access to Tacker APIs:

Verify Access to Tacker APIs
----------------------------

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

The requests for the verification are different depending on the authentication
methods. As Keycloak is configured to use ``client_secret_basic`` in this
guide, you can use the following example.

.. code-block:: console

  $ curl -i -X POST http://$keycloak_host_name:$keycloak_http_port/realms/testrealm/protocol/openid-connect/token \
  -u "tacker_api_proj:iIK6lARLzJgoQQyMyoymNYrGTDuR0733S" \
  -d "scope=project_scope" -d "grant_type=client_credentials"
  HTTP/1.1 200 OK
  Cache-Control: no-store
  Pragma: no-cache
  content-length: 1773
  Content-Type: application/json
  Referrer-Policy: no-referrer
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  X-Content-Type-Options: nosniff
  X-Frame-Options: SAMEORIGIN
  X-XSS-Protection: 1; mode=block

  {"access_token":"$access_token","expires_in":300,"refresh_expires_in":0,
  "token_type":"Bearer","not-before-policy":0,"scope":"email profile"}


  $ curl -i -X GET http://$tacker_host_name:9890/v1.0/vims \
  -H "Authorization: Bearer $access_token"
  HTTP/1.1 200 OK
  Content-Type: application/json
  Content-Length: 743
  X-Openstack-Request-Id: req-2f954ee7-e6fd-4d53-ac31-bf8c7d9245d7
  Date: Tue, 17 Dec 2024 06:27:24 GMT

  {"vims": [{"id": "a99189da-bf72-4af7-884c-36d157f00571",
  "type": "openstack", "tenant_id": "2cc02f60acf34fdda7bc5e9af9a7032b",
  "name": "openstack", "description": "", "placement_attr": {
  "regions": ["RegionOne"]}, "is_default": true,
  "created_at": "2024-11-07 02:04:46", "updated_at": "2024-11-07 02:10:18",
  "extra": {}, "auth_url": "http://192.168.56.11/identity/v3",
  "vim_project": {"name": "admin", "project_domain_name": "default"},
  "auth_cred": {"username": "admin", "user_domain_name": "default",
  "cert_verify": "True", "project_id": null, "project_name": "admin",
  "project_domain_name": "default", "auth_url": "http://192.168.56.11/identity/v3",
  "key_type": "barbican_key", "secret_uuid": "***", "password": "***"}, "status": "ACTIVE"}]}

  $ tail -f /opt/stack/log/tacker-server.log
  Dec 17 05:45:25 controller-tacker tacker-server[835]:
  DEBUG keystonemiddleware.external_oauth2_token [-] The introspect API response: {
  'exp': 1734414535, 'iat': 1734414235, 'jti': '49458c8f-507d-4d08-a81f-c3a6ee484190',
  'iss': 'http://$keycloak_host_name:$keycloak_http_port/realms/testrealm', 'aud': 'account', 'sub': '7d3e5929-4bbe-4ef4-90e3-8fd4b445ed7f',
  'typ': 'Bearer', 'azp': 'tacker_api_proj', 'acr': '1', 'allowed-origins': ['/*'],
  'realm_access': {'roles': ['offline_access', 'uma_authorization', 'default-roles-testrealm']},
  'resource_access': {'account': {'roles': ['manage-account', 'manage-account-links', 'view-profile']}},
  'scope': 'email profile', 'email_verified': False, 'role_info': 'admin,member,reader',
  'preferred_username': 'service-account-tacker_api_proj', 'user': {'domain': {'name': 'default', 'id': 'default'},
  'name': 'nfv_user', 'id': '35c884d8a6544d38abce33c0003c8331'}, 'project_info': {'domain': {'id': 'default', 'name': 'Default'},
  'id': 'ce5b19a933354bdf87ac6d698494ad47', 'name': 'nfv'}, 'client_id': 'tacker_api_proj',
  'username': 'service-account-tacker_api_proj', 'token_type': 'Bearer', 'active': True}
  {{(pid=835) _fetch_token /opt/stack/data/venv/lib/python3.10/site-packages/keystonemiddleware/external_oauth2_token.py:731}}


If you configure Keycloak with another authentication method, please see
examples below.

* client_secret_post:

  .. code-block:: console

    $ curl -i -X POST http://$keycloak_host_name:$keycloak_http_port/realms/testrealm/protocol/openid-connect/token \
    -d "client_id=tacker_api_proj" -d "client_secret=iIK6lARLzJgoQQyMyoymNYrGTDuR0733S" \
    -d "scope=project_scope" -d "grant_type=client_credentials"
    HTTP/1.1 200 OK
    Cache-Control: no-store
    Pragma: no-cache
    content-length: 1773
    Content-Type: application/json
    Referrer-Policy: no-referrer
    Strict-Transport-Security: max-age=31536000; includeSubDomains
    X-Content-Type-Options: nosniff
    X-Frame-Options: SAMEORIGIN
    X-XSS-Protection: 1; mode=block

    {"access_token":"$access_token","expires_in":300,"refresh_expires_in":0,
    "token_type":"Bearer","not-before-policy":0,"scope":"email profile"}

    $ curl -i -X GET http://$tacker_host_name:9890/v1.0/vims \
    -H "Authorization: Bearer $access_token"
    HTTP/1.1 200 OK
    Content-Type: application/json
    Content-Length: 743
    X-Openstack-Request-Id: req-2cb42224-8293-4deb-b772-9aeff5354922
    Date: Fri, 06 Dec 2024 08:56:38 GMT

    {"vims": [{"id": "a99189da-bf72-4af7-884c-36d157f00571",
    "type": "openstack", "tenant_id": "2cc02f60acf34fdda7bc5e9af9a7032b",
    "name": "openstack", "description": "", "placement_attr": {
    "regions": ["RegionOne"]}, "is_default": true,
    "created_at": "2024-11-07 02:04:46", "updated_at": "2024-11-07 02:10:18",
    "extra": {}, "auth_url": "http://192.168.56.11/identity/v3",
    "vim_project": {"name": "admin", "project_domain_name": "default"},
    "auth_cred": {"username": "admin", "user_domain_name": "default",
    "cert_verify": "True", "project_id": null, "project_name": "admin",
    "project_domain_name": "default", "auth_url": "http://192.168.56.11/identity/v3",
    "key_type": "barbican_key", "secret_uuid": "***", "password": "***"}, "status": "ACTIVE"}]}

    $ tail -f /opt/stack/log/tacker-server.log
    Dec 06 08:56:38 controller-tacker tacker-server[20354]:
    DEBUG keystonemiddleware.external_oauth2_token [-] The introspect API response: {
    'exp': 1733475612, 'iat': 1733475312, 'jti': '946ef21c-17c2-4416-ac6a-37d9ef9f5739',
    'iss': 'http://$keycloak_host_name:$keycloak_http_port/realms/testrealm', 'aud': 'account', 'sub': '7d3e5929-4bbe-4ef4-90e3-8fd4b445ed7f',
    'typ': 'Bearer', 'azp': 'tacker_api_proj', 'acr': '1', 'allowed-origins': ['/*'],
    'realm_access': {'roles': ['offline_access', 'uma_authorization', 'default-roles-testrealm']},
    'resource_access': {'account': {'roles': ['manage-account', 'manage-account-links', 'view-profile']}},
    'scope': 'email profile', 'email_verified': False, 'role_info': 'admin,member,reader',
    'preferred_username': 'service-account-tacker_api_proj', 'user': {'domain': {'name': 'default', 'id': 'default'},
    'name': 'nfv_user', 'id': '35c884d8a6544d38abce33c0003c8331'}, 'project_info': {'domain': {
    'id': 'default', 'name': 'Default'}, 'id': 'ce5b19a933354bdf87ac6d698494ad47', 'name': 'nfv'},
    'client_id': 'tacker_api_proj', 'username': 'service-account-tacker_api_proj', 'token_type': 'Bearer', 'active': True}
    {{(pid=20354) _fetch_token /opt/stack/data/venv/lib/python3.10/site-packages/keystonemiddleware/external_oauth2_token.py:731}}


* private_key_jwt:

  .. code-block:: console

    $ curl -i -X POST http://$keycloak_host_name:$keycloak_http_port/realms/testrealm/protocol/openid-connect/token \
    -d "client_id=tacker_api_proj" -d "scope=project_scope" -d "grant_type=client_credentials" \
    -d "client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer" \
    -d "client_assertion=$client_assertion"
    HTTP/1.1 200 OK
    Cache-Control: no-store
    Pragma: no-cache
    content-length: 1774
    Content-Type: application/json
    Referrer-Policy: no-referrer
    Strict-Transport-Security: max-age=31536000; includeSubDomains
    X-Content-Type-Options: nosniff
    X-Frame-Options: SAMEORIGIN
    X-XSS-Protection: 1; mode=block

    {"access_token":"$access_token","expires_in":300,"refresh_expires_in":0,
    "token_type":"Bearer","not-before-policy":0,"scope":"email profile"}

    $ curl -i -X GET http://$tacker_host_name:9890/v1.0/vims \
    -H "Authorization: Bearer $access_token"
    HTTP/1.1 200 OK
    Content-Type: application/json
    Content-Length: 743
    X-Openstack-Request-Id: req-b4c07ca6-49c8-4c12-be51-248c507183b9
    Date: Fri, 06 Dec 2024 09:15:07 GMT

    {"vims": [{"id": "a99189da-bf72-4af7-884c-36d157f00571",
    "type": "openstack", "tenant_id": "2cc02f60acf34fdda7bc5e9af9a7032b",
    "name": "openstack", "description": "", "placement_attr": {
    "regions": ["RegionOne"]}, "is_default": true,
    "created_at": "2024-11-07 02:04:46", "updated_at": "2024-11-07 02:10:18",
    "extra": {}, "auth_url": "http://192.168.56.11/identity/v3",
    "vim_project": {"name": "admin", "project_domain_name": "default"},
    "auth_cred": {"username": "admin", "user_domain_name": "default",
    "cert_verify": "True", "project_id": null, "project_name": "admin",
    "project_domain_name": "default", "auth_url": "http://192.168.56.11/identity/v3",
    "key_type": "barbican_key", "secret_uuid": "***", "password": "***"}, "status": "ACTIVE"}]}

    $ tail -f /opt/stack/log/tacker-server.log
    Dec 06 09:15:07 controller-tacker tacker-server[21835]:
    DEBUG keystonemiddleware.external_oauth2_token [-] The introspect API response: {
    'exp': 1733476670, 'iat': 1733476370, 'jti': '8c9cf64f-f0f3-4d74-8b15-a6bda7036f07',
    'iss': 'http://$keycloak_host_name:$keycloak_http_port/realms/testrealm', 'aud': 'account', 'sub': '7d3e5929-4bbe-4ef4-90e3-8fd4b445ed7f',
    'typ': 'Bearer', 'azp': 'tacker_api_proj', 'acr': '1', 'allowed-origins': ['/*'], 'realm_access': {
    'roles': ['offline_access', 'uma_authorization', 'default-roles-testrealm']}, 'resource_access': {'account': {
    'roles': ['manage-account', 'manage-account-links', 'view-profile']}}, 'scope': 'email profile',
    'email_verified': False, 'role_info': 'admin,member,reader', 'preferred_username': 'service-account-tacker_api_proj',
    'user': {'domain': {'name': 'default', 'id': 'default'}, 'name': 'nfv_user', 'id': '35c884d8a6544d38abce33c0003c8331'},
    'project_info': {'domain': {'id': 'default', 'name': 'Default'}, 'id': 'ce5b19a933354bdf87ac6d698494ad47', 'name': 'nfv'},
    'client_id': 'tacker_api_proj', 'username': 'service-account-tacker_api_proj', 'token_type': 'Bearer', 'active': True}
    {{(pid=21835) _fetch_token /opt/stack/data/venv/lib/python3.10/site-packages/keystonemiddleware/external_oauth2_token.py:731}}


* client_secret_jwt:

  .. code-block:: console

    $ curl -i -X POST http://$keycloak_host_name:$keycloak_https_port/realms/testrealm/protocol/openid-connect/token \
    -d "client_id=tacker_api_proj" -d "scope=project_scope" -d "grant_type=client_credentials" \
    -d "client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer" \
    -d "client_assertion=$client_assertion"
    HTTP/1.1 200 OK
    Cache-Control: no-store
    Pragma: no-cache
    content-length: 1774
    Content-Type: application/json
    Referrer-Policy: no-referrer
    Strict-Transport-Security: max-age=31536000; includeSubDomains
    X-Content-Type-Options: nosniff
    X-Frame-Options: SAMEORIGIN
    X-XSS-Protection: 1; mode=block

    {"access_token":"$access_token","expires_in":300,"refresh_expires_in":0,
    "token_type":"Bearer","not-before-policy":0,"scope":"email profile"}

    $ curl -i -X GET http://$tacker_host_name:9890/v1.0/vims \
    -H "Authorization: Bearer $access_token"
    HTTP/1.1 200 OK
    Content-Type: application/json
    Content-Length: 743
    X-Openstack-Request-Id: req-4c2e2c76-672e-4517-ac2e-0a79a48b9122
    Date: Fri, 06 Dec 2024 09:28:24 GMT

    {"vims": [{"id": "a99189da-bf72-4af7-884c-36d157f00571",
    "type": "openstack", "tenant_id": "2cc02f60acf34fdda7bc5e9af9a7032b",
    "name": "openstack", "description": "", "placement_attr": {
    "regions": ["RegionOne"]}, "is_default": true,
    "created_at": "2024-11-07 02:04:46", "updated_at": "2024-11-07 02:10:18",
    "extra": {}, "auth_url": "http://192.168.56.11/identity/v3",
    "vim_project": {"name": "admin", "project_domain_name": "default"},
    "auth_cred": {"username": "admin", "user_domain_name": "default",
    "cert_verify": "True", "project_id": null, "project_name": "admin",
    "project_domain_name": "default", "auth_url": "http://192.168.56.11/identity/v3",
    "key_type": "barbican_key", "secret_uuid": "***", "password": "***"}, "status": "ACTIVE"}]}

    $ tail -f /opt/stack/log/tacker-server.log
    Dec 06 09:28:23 controller-tacker tacker-server[22701]:
    DEBUG keystonemiddleware.external_oauth2_token [-] The introspect API response: {
    'exp': 1733477523, 'iat': 1733477223, 'jti': '7c07a9ac-3af8-44c7-a243-f2faed10cac0',
    'iss': 'http://$keycloak_host_name:$keycloak_http_port/realms/testrealm', 'aud': 'account', 'sub': '7d3e5929-4bbe-4ef4-90e3-8fd4b445ed7f',
    'typ': 'Bearer', 'azp': 'tacker_api_proj', 'acr': '1', 'allowed-origins': ['/*'], 'realm_access': {
    'roles': ['offline_access', 'uma_authorization', 'default-roles-testrealm']}, 'resource_access': {'account': {
    'roles': ['manage-account', 'manage-account-links', 'view-profile']}}, 'scope': 'email profile',
    'email_verified': False, 'role_info': 'admin,member,reader', 'preferred_username': 'service-account-tacker_api_proj',
    'user': {'domain': {'name': 'default', 'id': 'default'}, 'name': 'nfv_user', 'id': '35c884d8a6544d38abce33c0003c8331'},
    'project_info': {'domain': {'id': 'default', 'name': 'Default'}, 'id': 'ce5b19a933354bdf87ac6d698494ad47', 'name': 'nfv'},
    'client_id': 'tacker_api_proj', 'username': 'service-account-tacker_api_proj', 'token_type': 'Bearer', 'active': True}
    {{(pid=22701) _fetch_token /opt/stack/data/venv/lib/python3.10/site-packages/keystonemiddleware/external_oauth2_token.py:731}}


* tls_client_auth:

  .. code-block:: console

    $ curl -i -X POST https://$keycloak_host_name:$keycloak_https_port/realms/testrealm/protocol/openid-connect/token \
    -d "client_id=tacker_api_proj" -d "scope=project_scope" -d "grant_type=client_credentials" \
    --cacert ca.pem \
    --cert client.pem \
    --key client.key
    HTTP/2 200
    cache-control: no-store
    pragma: no-cache
    content-length: 1861
    content-type: application/json
    referrer-policy: no-referrer
    strict-transport-security: max-age=31536000; includeSubDomains
    x-content-type-options: nosniff
    x-frame-options: SAMEORIGIN
    x-xss-protection: 1; mode=block

    {"access_token":"$access_token","expires_in":300,"refresh_expires_in":0,
    "token_type":"Bearer","not-before-policy":0,"scope":"email profile"}

    $ curl -i -X GET https://$tacker_host_name:9890/v1.0/vims \
    -H "Authorization: Bearer $access_token" \
    --cacert ca.pem \
    --cert client.pem \
    --key client.key
    HTTP/1.1 200 OK
    Content-Type: application/json
    Content-Length: 743
    X-Openstack-Request-Id: req-80b670f0-910f-4d53-9859-6d430f4ba7db
    Date: Fri, 06 Dec 2024 09:42:36 GMT

    {"vims": [{"id": "a99189da-bf72-4af7-884c-36d157f00571",
    "type": "openstack", "tenant_id": "2cc02f60acf34fdda7bc5e9af9a7032b",
    "name": "openstack", "description": "", "placement_attr": {
    "regions": ["RegionOne"]}, "is_default": true,
    "created_at": "2024-11-07 02:04:46", "updated_at": "2024-11-07 02:10:18",
    "extra": {}, "auth_url": "http://192.168.56.11/identity/v3",
    "vim_project": {"name": "admin", "project_domain_name": "default"},
    "auth_cred": {"username": "admin", "user_domain_name": "default",
    "cert_verify": "True", "project_id": null, "project_name": "admin",
    "project_domain_name": "default", "auth_url": "http://192.168.56.11/identity/v3",
    "key_type": "barbican_key", "secret_uuid": "***", "password": "***"}, "status": "ACTIVE"}]}

    $ tail -f /opt/stack/log/tacker-server.log
    Dec 06 09:42:36 controller-tacker tacker-server[25048]:
    DEBUG keystonemiddleware.external_oauth2_token [-] The introspect API response: {
    'exp': 1733478427, 'iat': 1733478127, 'jti': 'a51dbc9c-45b0-46ef-953e-71278b09c9d4',
    'iss': 'https://$keycloak_host_name:$keycloak_https_port/realms/testrealm', 'aud': 'account', 'sub': '7d3e5929-4bbe-4ef4-90e3-8fd4b445ed7f',
    'typ': 'Bearer', 'azp': 'tacker_api_proj', 'acr': '1', 'allowed-origins': ['/*'], 'realm_access': {
    'roles': ['offline_access', 'uma_authorization', 'default-roles-testrealm']}, 'resource_access': {'account': {
    'roles': ['manage-account', 'manage-account-links', 'view-profile']}},
    'cnf': {'x5t#S256': 'dAHdSS_CN-KNN9jgE8brrkFEDC2uWAKnMslE84CBB38'}, 'scope': 'email profile',
    'email_verified': False, 'role_info': 'admin,member,reader', 'preferred_username': 'service-account-tacker_api_proj',
    'user': {'domain': {'name': 'default', 'id': 'default'}, 'name': 'nfv_user', 'id': '35c884d8a6544d38abce33c0003c8331'},
    'project_info': {'domain': {'id': 'default', 'name': 'Default'}, 'id': 'ce5b19a933354bdf87ac6d698494ad47', 'name': 'nfv'},
    'client_id': 'tacker_api_proj', 'username': 'service-account-tacker_api_proj', 'token_type': 'Bearer', 'active': True}
    {{(pid=25048) _fetch_token /opt/stack/data/venv/lib/python3.10/site-packages/keystonemiddleware/external_oauth2_token.py:731}}


Using Tacker API
----------------

When using an external OAuth 2.0 authorization server, the current version of
OpenStack Command is not supported.

Instead, you can use `tacker_cli.sh`_, a wrapper of ``curl``. For example, you
can call ``v1.0/vims`` API as follows.

.. code-block:: shell

  $ export TACKER_AUTH_URL="http://$keycloak_host_name:$keycloak_http_port/realms/testrealm/protocol/openid-connect/token"
  $ export TACKER_CLIENT_ID="tacker_api_proj"
  $ export TACKER_CLIENT_SECRET="iIK6lARLzJgoQQyMyoymNYrGTDuR0733S"
  $ export TACKER_AUTH_TYPE="client_secret_basic"
  $ export TACKER_OAUTH2_SCOPE="tacker_scope"
  $ export TACKER_URL=http://127.0.0.1:9890
  $ ./tacker_cli.sh vim list

  {"vims": [{"id": "a99189da-bf72-4af7-884c-36d157f00571",
  "type": "openstack", "tenant_id": "2cc02f60acf34fdda7bc5e9af9a7032b",
  "name": "openstack", "description": "", "placement_attr": {
  "regions": ["RegionOne"]}, "is_default": true,
  "created_at": "2024-11-07 02:04:46", "updated_at": "2024-11-07 02:10:18",
  "extra": {}, "auth_url": "http://192.168.56.11/identity/v3",
  "vim_project": {"name": "admin", "project_domain_name": "default"},
  "auth_cred": {"username": "admin", "user_domain_name": "default",
  "cert_verify": "True", "project_id": null, "project_name": "admin",
  "project_domain_name": "default", "auth_url": "http://192.168.56.11/identity/v3",
  "key_type": "barbican_key", "secret_uuid": "***", "password": "***"}, "status": "ACTIVE"}]}

You can also find other subcommands corresponding to Tacker APIs.

.. code-block:: shell

  $ ./tacker_cli.sh -h

  Usage: tacker_cli.sh <command> [<args>]

  Options:
    -h, --help      show this help message and exit
    -v, --version   print version

  Commands:
    vim
    vnfpkgm
    vnflcm
    vnffm
    vnfpm

``tacker_cli`` uses a similar authentication scheme as the OpenStack project
CLIs, with the credential information as environment variables beginning with
the prefix ``TACKER``. Full examples of each authentication method are provided
below.

.. code-block:: shell

  # client_secret_basic
  export TACKER_AUTH_URL="http://<keycloak_host>:<keycloak_port>/realms/testrealm/protocol/openid-connect/token"
  export TACKER_CLIENT_ID="tacker_api_proj"
  export TACKER_CLIENT_SECRET="<secret>"
  export TACKER_AUTH_TYPE="client_secret_basic"
  export TACKER_OAUTH2_SCOPE="tacker_scope"
  export TACKER_URL=http://<tacker_host>:<tacker_port>

  # client_secret_post
  export TACKER_AUTH_URL="http://<keycloak_host>:<keycloak_port>/realms/testrealm/protocol/openid-connect/token"
  export TACKER_CLIENT_ID="tacker_api_proj"
  export TACKER_CLIENT_SECRET="<secret>"
  export TACKER_AUTH_TYPE="client_secret_post"
  export TACKER_OAUTH2_SCOPE="tacker_scope"
  export TACKER_URL=http://<tacker_host>:<tacker_port>

  # private_key_jwt
  export TACKER_AUTH_URL="http://<keycloak_host>:<keycloak_port>/realms/testrealm/protocol/openid-connect/token"
  export TACKER_CLIENT_ID="tacker_api_proj"
  export TACKER_JWT_KEY="path/to/private_key.pem"
  export TACKER_AUTH_TYPE="private_key_jwt"
  export TACKER_OAUTH2_SCOPE="tacker_scope"
  export TACKER_URL=http://<tacker_host>:<tacker_port>

  # client_secret_jwt
  export TACKER_AUTH_URL="http://<keycloak_host>:<keycloak_port>/realms/testrealm/protocol/openid-connect/token"
  export TACKER_CLIENT_ID="tacker_api_proj"
  export TACKER_CLIENT_SECRET="<secret>"
  export TACKER_AUTH_TYPE="client_secret_jwt"
  export TACKER_OAUTH2_SCOPE="tacker_scope"
  export TACKER_URL=http://<tacker_host>:<tacker_port>

  # tls_client_auth
  export TACKER_AUTH_URL="https://<keycloak_host>:<keycloak_port>/realms/testrealm/protocol/openid-connect/token"
  export TACKER_CLIENT_ID="tacker_api_proj"
  export TACKER_AUTH_TYPE="tls_client_auth"
  export TACKER_OAUTH2_SCOPE="tacker_scope"
  export TACKER_CACERT="path/to/ca.pem"
  export TACKER_CLIENT_CERT="path/to/client.pem"
  export TACKER_CLIENT_KEY="path/to/client.key"
  export TACKER_URL=https://<tacker_host>:<tacker_port>

.. note::

  Please note that this script only supports `the version 2 VNF LCM APIs`_.

Cleaning Up
-----------

When the testing Keycloak environment is no longer is needed as the testing had
finished, Keycloak docker container can be removed by simply running the
following command.

.. code-block:: console

  $ docker stop keycloak && docker rm keycloak


.. _RFC6749: https://datatracker.ietf.org/doc/html/rfc6749
.. _Keycloak: https://www.keycloak.org/
.. _NFV-SOL013 v3.4.1: https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/013/03.04.01_60/gs_nfv-sol013v030401p.pdf
.. _Middleware Architecture: https://docs.openstack.org/keystonemiddleware/latest/middlewarearchitecture.html
.. _openid-connect 1.0 core specs: https://openid.net/specs/openid-connect-core-1_0.html#ClientAuthentication
.. _RFC7523: https://www.rfc-editor.org/rfc/rfc7523#section-3.2
.. _RFC7519: https://www.rfc-editor.org/rfc/rfc7519
.. _project details: https://docs.openstack.org/keystone/latest/admin/cli-manage-projects-users-and-roles.html
.. _domain details: https://docs.openstack.org/security-guide/identity/domains.html
.. _Mappers tab of Client scope page in the Keycloak dashboard: https://www.keycloak.org/docs/latest/server_admin/#protocol
.. _tacker_cli.sh: https://opendev.org/openstack/tacker/src/branch/master/doc/tools/tacker_cli.sh
.. _the version 2 VNF LCM APIs: https://docs.openstack.org/api-ref/nfv-orchestration/v2/vnflcm.html
