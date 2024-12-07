================================================================
Using Keystone as OAuth 2.0 Authorization Server for Tacker APIs
================================================================

.. note::

  The content of this document has been confirmed to work
  using Tacker and Keystone 2024.1 Caracal.


Overview
~~~~~~~~

The third-party clients can access the NFV orchestration APIs that is provided
by Tacker via the Client Credentials Grant flow of `RFC6749`_ OAuth 2.0
Authorization Framework. OAuth 2.0 Client Credentials Grant flow is prescribed
in the API specification of `ETSI NFV-SOL013 v3.4.1`_. And Tacker implements
OAuth 2.0 Mutual-TLS Client Authentication based on `RFC8705`_. Tacker uses the
Keystonemiddleware to support OAuth 2.0 Client Credentials Grant and OAuth 2.0
Mutual-TLS Client Authentication through the Keystone identity server.

Preparations
~~~~~~~~~~~~

According to `RFC6749`_, HTTPS must be enabled in the authorization server
since requests include sensitive information in plain text, so it should enable
Tacker to support HTTPS protocols. You can reference this guide to enable HTTPS
for Tacker APIs :doc:`/admin/configure_tls`. For keystone server, reference the
`Configure HTTPS in Identity Service`_.

.. note::

  Based on the server environment, this command may have to be run to enable
  SSL module in apache2 service when setting up HTTPS protocol for keystone
  server.

  .. code-block:: console

    $ sudo a2enmod ssl


.. note::

 If the Keystone identity server supports the HTTPS protocol, set the CA file
 and HTTPS auth url for Keystone Server in tacker.conf.

 .. code-block:: console

   [keystone_authtoken]
   #cafile = /opt/stack/data/ca-bundle.pem
   cafile = /opt/stack/certs/multi_ca.pem
   #auth_url = http://$keystone_host_name/identity
   auth_url = https://$keystone_host_name/identity


 And if CA files that signed certificates used by the Keystone identity server
 and the Tacker server are not the same, it is necessary to add CA file for
 Keystone server into ``multi_ca.pem``.

 .. code-block:: console

   $ cat keystone.host.crt >> multi_ca.pem


Guide for OAuth 2.0 Client Credentials Grant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To use OAuth 2.0 Client Credentials Grant for Tacker APIs, it is necessary to
confirm that `OAuth 2.0 client credentials`_ is enabled in the Keystone
identity server. In this example, ``$keystone_host_name`` is the domain name
used by the Keystone identity server, and the domain name used by the Tacker
server is ``$tacker_host_name``.

To use OAuth 2.0 Client Credentials Grant in Tacker, you should configure the
Tacker server and the Keystonemiddleware in the following steps.

Enable Client Credentials Grant
-------------------------------

To handle API requests using OAuth 2.0 Client Credentials Grant, you have to
configure the Keystonemiddleware which intercepts API calls from clients and
verifies a client's identity, see `Middleware Architecture`_.

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


Verify Access to Tacker APIs
----------------------------

Access to the Tacker APIs with the OAuth 2.0 access token to verify that OAuth
2.0 Client Credentials Grant flow works correctly.

1. Obtain client credentials with application credentials API

   See the `OAuth 2.0 usage guide`_ and `Application Credentials API`_ for
   information about obtaining client credentials (`$oauth2_client_id` and
   `$oauth2_client_secret`).

2. Obtain an access token from the `OAuth 2.0 Access Token API`_

   .. code-block:: console

     $ curl -i -u "$oauth2_client_id:$oauth2_client_secret" \
     -X POST https://$keystone_host_name/identity/v3/OS-OAUTH2/token \
     -H "application/x-www-form-urlencoded" \
     -d "grant_type=client_credentials" \
     --cacert multi_ca.pem
     HTTP/1.1 200 OK
     Date: Wed, 22 May 2024 05:55:21 GMT
     Server: Apache/2.4.52 (Ubuntu)
     Content-Type: application/json
     Content-Length: 264
     Vary: X-Auth-Token
     x-openstack-request-id: req-269c250e-5fc8-439b-9d40-8ba6c139a245
     Connection: close

     {"access_token":"$oauth2_access_token","expires_in":3600,"token_type":"Bearer"}


3. Access the OpenStack Tacker APIs with the OAuth 2.0 access token to confirm
   that OAuth 2.0 Client Credentials Grant flow works correctly

   .. code-block:: console

     $ curl -i -X GET "https://$tacker_host_name:9890/v1.0/vims" \
     -H "Authorization: Bearer $oauth2_access_token" \
     --cacert multi_ca.pem
     HTTP/1.1 200 OK
     Content-Type: application/json
     Content-Length: 736
     X-Openstack-Request-Id: req-75594c93-dc19-49cd-9da5-6f8e9b7a7a03
     Date: Wed, 22 May 2024 05:59:43 GMT

     {"vims": [{"id": "84517803-0e84-401e-ad75-8f6b8ab0a3b6", "type": "openstack", "tenant_id": "d53a4605d776472d846aed35735d3494", "name": "openstack-admin-vim", "description": "", "placement_attr": {"regions": ["RegionOne"]}, "is_default": true, "created_at": "2024-06-03 14:29:08", "updated_at": null, "extra": {}, "auth_url": "https://$keystone_host_name/identity/v3", "vim_project": {"name": "nfv", "project_domain_name": "Default"}, "auth_cred": {"username": "nfv_user", "user_domain_name": "Default", "cert_verify": "False", "project_id": null, "project_name": "nfv", "project_domain_name": "Default", "auth_url": "https://$keystone_host_name/identity/v3", "key_type": "barbican_key", "secret_uuid": "***", "password": "***"}, "status": "ACTIVE"}]}

     $ curl -i -X GET "https://$tacker_host_name:9890/vnfpkgm/v1/vnf_packages" \
     -H "Authorization: Bearer $oauth2_access_token" \
     --cacert multi_ca.pem
     HTTP/1.1 200 OK
     Content-Type: application/json
     Content-Length: 498
     X-Openstack-Request-Id: req-3f5ebaad-6f66-43b7-bd0f-917a54558918
     Date: Wed, 22 May 2024 06:06:24 GMT

     [{"id": "6b02a067-848f-418b-add1-e9c020239b31", "onboardingState": "ONBOARDED", "operationalState": "ENABLED", "usageState": "IN_USE", "vnfProductName": "Sample VNF", "vnfSoftwareVersion": "1.0", "vnfdId": "b1bb0ce7-ebca-4fa7-95ed-4840d70a1177", "vnfdVersion": "1.0", "vnfProvider": "Company", "_links": {"self": {"href": "/vnfpkgm/v1/vnf_packages/6b02a067-848f-418b-add1-e9c020239b31"}, "packageContent": {"href": "/vnfpkgm/v1/vnf_packages/6b02a067-848f-418b-add1-e9c020239b31/package_content"}}}]

     $ curl -i -X GET "https://$tacker_host_name:9890/vnflcm/v1/vnf_instances" \
     -H "Authorization: Bearer $oauth2_access_token" \
     --cacert multi_ca.pem
     HTTP/1.1 200 OK
     Content-Type: application/json
     Content-Length: 603
     X-Openstack-Request-Id: req-ceeb935f-e4af-4f46-bfa9-4fb3e83a4664
     Date: Wed, 22 May 2024 06:24:33 GMT

     [{"id": "fd25f4ca-27ac-423b-afcf-640a64544e61", "vnfInstanceName": "vnf-fd25f4ca-27ac-423b-afcf-640a64544e61", "instantiationState": "NOT_INSTANTIATED", "vnfdId": "b1bb0ce7-ebca-4fa7-95ed-4840d70a1177", "vnfProvider": "Company", "vnfProductName": "Sample VNF", "vnfSoftwareVersion": "1.0", "vnfdVersion": "1.0", "vnfPkgId": "6b02a067-848f-418b-add1-e9c020239b31", "_links": {"self": {"href": "https://$tacker_host_name:9890/vnflcm/v1/vnf_instances/fd25f4ca-27ac-423b-afcf-640a64544e61"}, "instantiate": {"href": "https://$tacker_host_name:9890/vnflcm/v1/vnf_instances/fd25f4ca-27ac-423b-afcf-640a64544e61/instantiate"}}}]


4. Confirm that a client can not access the Tacker APIs with an X-Auth-Token.

   .. code-block:: console

     $ curl -i -X POST https://$keystone_host_name/identity/v3/auth/tokens?nocatalog \
     -d '{"auth":{"identity":{"methods":["password"],"password": {"user":{"domain":{"name":"$userDomainName"},"name":"$userName","password":"$password"}}},"scope":{"project":{"domain":{"name":"$projectDomainName"},"name":"$projectName"}}}}' \
     -H 'Content-type:application/json' \
     --cacert multi_ca.pem
     HTTP/1.1 201 CREATED
     Date: Wed, 05 Jun 2024 06:48:33 GMT
     Server: Apache/2.4.52 (Ubuntu)
     Content-Type: application/json
     Content-Length: 712
     X-Subject-Token: $x_auth_token
     Vary: X-Auth-Token
     x-openstack-request-id: req-bc85eb93-eb34-41d6-970e-1cbd776c1878
     Connection: close

     {"token": {"methods": ["password"], "user": {"domain": {"id": "$userDomainId" , "name": "$userDomainName"}, "id": "$userId", "name": "$userName", "password_expires_at": null}, "audit_ids": ["nHh38yyHSnWfPItIUnesEQ"], "expires_at": "2024-06-05T07:48:33.000000Z", "issued_at": "2024-06-05T06:48:33.000000Z", "project": {"domain": {"id": "$projectDomainId", "name": "$projectDomainName"}, "id": "$projectId", "name": "$projectName"}, "is_domain": false, "roles": [{"id": "4f50d53ed79a42bd89105954f21d9f1d", "name": "member"}, {"id": "9c9f278da6e74c2dbdb80fc0a5ed9010", "name": "manager"}, {"id": "fcdedca5ce604c90b241bab70f85d8cc", "name": "admin"}, {"id": "42ff1a2ac70d4496a90dd6aa8985feb1", "name": "reader"}]}}

     $ curl -i -X GET "https://$tacker_host_name:9890/v1.0/vims" \
     -H "X-Auth-Token:$x_auth_token" \
     --cacert multi_ca.pem
     HTTP/1.1 401 Unauthorized
     Content-Type: application/json
     Content-Length: 114
     Www-Authenticate: Keystone uri="https://$keystone_host_name/identity"
     X-Openstack-Request-Id: req-5ee22493-4961-4272-82c6-c44978d3ed8b
     Date: Wed, 05 Jun 2024 07:02:02 GMT

     {"error": {"code": 401, "title": "Unauthorized", "message": "The request you have made requires authentication."}}


Enable OpenStack Command through Client Credentials Grant
---------------------------------------------------------

To use OAuth 2.0 Client Credentials Grant from OpenStack CLI, you have to use
``v3oauth2clientcredential`` as ``auth_type``.

1. Before executing the command, you should remove the variables that affect
   the OpenStack command from the OS environment, then set the variables that
   required by OAuth 2.0 Client Credentials Grant to the OS
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


   .. code-block:: console

     $ export OS_AUTH_URL=https://$keystone_host_name/identity
     $ export OS_IDENTITY_API_VERSION=3
     $ export OS_REGION_NAME="RegionOne"
     $ export OS_INTERFACE=public
     $ export OS_OAUTH2_ENDPOINT=https://$keystone_host_name/identity/v3/OS-OAUTH2/token
     $ export OS_OAUTH2_CLIENT_ID=$oauth2_client_id
     $ export OS_OAUTH2_CLIENT_SECRET=$oauth2_client_secret
     $ export OS_AUTH_TYPE=v3oauth2clientcredential
     $ export OS_CACERT=/opt/stack/certs/multi_ca.pem


2. Execute a tacker command to confirm that OpenStack command can access the
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


Guide for OAuth 2.0 Mutual-TLS Client Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To use OAuth 2.0 Mutual-TLS Client Authentication in Tacker, you should
configure the Tacker server, the Keystone identity server and the Keystone
middleware in the following steps.

.. TODO(Kyaw Myo Thant): delete this part and change to referencing the
   Keystone document after the following patch is merged
   https://review.opendev.org/c/openstack/keystone/+/860928

Enable Keystone to Support Mutual-TLS Client Authentication
-----------------------------------------------------------

1. Modify the apache configuration file and add options to implement mutual TLS
   support for the Keystone service. You can reference
   :doc:`/admin/configure_tls` to create Private root CA, private key and
   certificate that will be required in this guide. And the certificate and key
   files should be stored where the apache service can access.

   .. note::

     If HTTPS protocol has been enabled for keystone server in previous
     section by referencing `Configure HTTPS in Identity Service`_, that
     configuration must be disabled by unlinking or removing the symlinked
     configuration file before enabling mTLS.

     .. code-block:: console

       $ sudo unlink /etc/apache2/sites-enabled/000-default.conf


   .. code-block:: console

     $ sudo vi /etc/apache2/sites-enabled/keystone-wsgi-public.conf
     ProxyPass "/identity" "unix:/var/run/uwsgi/keystone-wsgi-public.socket|uwsgi://uwsgi-uds-keystone-wsgi-public" retry=0
     <IfModule mod_ssl.c>
      <VirtualHost _default_:443>
       ServerAdmin webmaster@localhost
       ErrorLog ${APACHE_LOG_DIR}/error.log
       CustomLog ${APACHE_LOG_DIR}/access.log combined
       SSLEngine on
       SSLCertificateFile      /etc/ssl/certs/keystone.pem
       SSLCertificateKeyFile   /etc/ssl/private/keystone.key
       SSLCACertificateFile    /etc/ssl/certs/multi_ca.pem
       <Location /identity/v3/OS-OAUTH2/token>
         SSLVerifyClient require
         SSLOptions +ExportCertData
         SSLOptions +StdEnvVars
         SSLRequireSSL
       </Location>
      </VirtualHost>
     </IfModule>


2. Restart apache service so that the modified configuration information takes
   effect.

   .. code-block:: console

     $ sudo systemctl restart apache2.service


3. Modify the ``keystone.conf`` to enable the os-oauth2-api to use TLS
   certificates for user authentication.

   .. code-block:: console

     $ vi /etc/keystone/keystone.conf
     [oauth2]
     oauth2_authn_method=certificate
     oauth2_cert_dn_mapping_id=oauth2_mapping


4. Restart Keystone service so that the modified configuration information
   takes effect.

   .. code-block:: console

     $ sudo systemctl restart devstack@keystone


Enable Mutual-TLS Client Authentication
---------------------------------------

1. Enable mTLS (aka., two-way TLS) for Tacker APIs to use Oauth 2.0 Mutual-TLS
   client authentication.

   See :doc:`/admin/configure_tls` for detailed steps, to enable mTLS for
   Tacker APIs.

2. Add ``keystonemiddleware.oauth2_mtls_token:filter_factory`` to the
   configuration file ``api-paste.ini`` to enable OAuth 2.0 Mutual-TLS client
   authentication.

   .. code-block:: console

     $ vi /etc/tacker/api-paste.ini
     [composite:tackerapi_v1_0]
     #keystone = request_id catch_errors authtoken keystonecontext extensions tackerapiapp_v1_0
     keystone = request_id catch_errors oauth2_mtls_token keystonecontext extensions tackerapiapp_v1_0

     [composite:vnfpkgmapi_v1]
     #keystone = request_id catch_errors authtoken keystonecontext vnfpkgmapp_v1
     keystone = request_id catch_errors oauth2_mtls_token keystonecontext vnfpkgmapp_v1

     [composite:vnflcm_v1]
     #keystone = request_id catch_errors authtoken keystonecontext vnflcmaapp_v1
     keystone = request_id catch_errors oauth2_mtls_token keystonecontext vnflcmaapp_v1

     [composite:vnflcm_v2]
     #keystone = request_id catch_errors authtoken keystonecontext vnflcmaapp_v2
     keystone = request_id catch_errors oauth2_mtls_token keystonecontext vnflcmaapp_v2

     [composite:vnfpm_v2]
     #keystone = request_id catch_errors authtoken keystonecontext vnfpmaapp_v2
     keystone = request_id catch_errors oauth2_mtls_token keystonecontext vnfpmaapp_v2

     [composite:vnflcm_versions]
     #keystone = request_id catch_errors authtoken keystonecontext vnflcm_api_versions
     keystone = request_id catch_errors oauth2_mtls_token keystonecontext vnflcm_api_versions

     [composite:vnffm_v1]
     #keystone = request_id catch_errors authtoken keystonecontext vnffmaapp_v1
     keystone = request_id catch_errors oauth2_mtls_token keystonecontext vnffmaapp_v1

     [filter:oauth2_mtls_token]
     paste.filter_factory = keystonemiddleware.oauth2_mtls_token:filter_factory


Create Mapping Rules for Validating TLS Certificates
----------------------------------------------------

Because different root certificates have different ways of authenticating TLS
certificates provided by client, the relevant mapping rules need to be set in
the system.

1. Create a mapping rule file. When using Subject Distinguished Names,
   the "SSL_CLIENT_SUBJECT_DN_*" format must be used. When using Issuer
   Distinguished Names, the "SSL_CLIENT_ISSUER_DN_*" format must be used.
   The "*" part is the key of the attribute for Distinguished Names converted
   to uppercase. For more information about the attribute types for
   Distinguished Names, see the relevant RFC documentation such as: `RFC1779`_,
   `RFC2985`_, `RFC4519`_, etc. In this example, 4 Subject Distinguished Names
   is mapped for user identity. You can map other Distinguished Names like
   email. For detail, reference `Mapping Combinations`_.

   .. code-block:: console

     $ vi oauth2_mapping.json
     [
         {
             "local": [
                 {
                     "user": {
                         "name": "{0}",
                         "id": "{1}",
                         "domain": {
                             "name": "{2}",
                             "id": "{3}"
                         }
                     }
                 }
             ],
             "remote": [
                 {
                     "type": "SSL_CLIENT_SUBJECT_DN_CN"
                 },
                 {
                     "type": "SSL_CLIENT_SUBJECT_DN_UID"
                 },
                 {
                     "type": "SSL_CLIENT_SUBJECT_DN_O"
                 },
                 {
                     "type": "SSL_CLIENT_SUBJECT_DN_DC"
                 },
                 {
                     "type": "SSL_CLIENT_ISSUER_DN_CN",
                     "any_one_of": [
                         "root_b.openstack.host"
                     ]
                 }
             ]
         }
     ]


2. Use the mapping file to create the oauth2_mapping rule in keystone.

   .. code-block:: console

     $ openstack mapping create --rules oauth2_mapping.json oauth2_mapping
     +----------------+-------------------------------------------------------------------------------------------------------------------------------------------------------+
     | Field          | Value                                                                                                                                                 |
     +----------------+-------------------------------------------------------------------------------------------------------------------------------------------------------+
     | id             | oauth2_mapping                                                                                                                                        |
     | rules          | [{'local': [{'user': {'name': '{0}', 'id': '{1}', 'domain': {'name': '{2}', 'id': '{3}'}}}], 'remote': [{'type': 'SSL_CLIENT_SUBJECT_DN_CN'},         |
     |                | {'type': 'SSL_CLIENT_SUBJECT_DN_UID'}, {'type': 'SSL_CLIENT_SUBJECT_DN_O'}, {'type': 'SSL_CLIENT_SUBJECT_DN_DC'}, {'type': 'SSL_CLIENT_ISSUER_DN_CN', |
     |                | 'any_one_of': ['root_b.openstack.host']}]}]                                                                                                           |
     | schema_version | 1.0                                                                                                                                                   |
     +----------------+-------------------------------------------------------------------------------------------------------------------------------------------------------+


3. If it already exists, use the file to update the mapping rule in keystone.

   .. code-block:: console

     $ openstack mapping set --rules oauth2_mapping.json oauth2_mapping


4. To use ``oauth2_mtls_token`` Keystonemiddleware, default project of the user
   must be set. In this example, the default project of ``nfv_user`` user is
   set to ``nfv`` project that is in the ``default`` project domain.

   .. code-block:: console

     $ openstack user show nfv_user
     +---------------------+----------------------------------+
     | Field               | Value                            |
     +---------------------+----------------------------------+
     | default_project_id  | None                             |
     | domain_id           | default                          |
     | email               | None                             |
     | enabled             | True                             |
     | id                  | 173c59254d3040969e359e5df0a3b475 |
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
     | id          | 2e189ea6c1df4e4ba6d89de254b3a534 |
     | is_domain   | False                            |
     | name        | nfv                              |
     | options     | {}                               |
     | parent_id   | default                          |
     | tags        | []                               |
     +-------------+----------------------------------+


   .. code-block:: console

     $ openstack user set 173c59254d3040969e359e5df0a3b475 \
     --project 2e189ea6c1df4e4ba6d89de254b3a534 \
     --project-domain default


Verify Access to Tacker APIs
----------------------------

Access to the Tacker APIs with client certificate to verify that OAuth 2.0
Mutual-TLS Client Authenticating works correctly.

1. To use OAuth 2.0 Mutual-TLS Client Authentication, the client private key
   and certificate is necessary. Create a certificate signing request based on
   the mapping rule created in previous section. For this guide, 4 Subject
   Distinguished Names mapped in oauth2 mapping rule have to be included.

   .. code-block:: console

     $ openssl genrsa -out nfv_user.key 4096
     $ openssl req -new -key nfv_user.key -out nfv_user.csr \
     -subj "/UID=173c59254d3040969e359e5df0a3b475/O=Default/DC=default/CN=nfv_user"


2. Use the root certificate to generate a self-signed certificate for the user.
   Because the Issuer Common Names is mapped to be ``root_b.openstack.host`` in
   previous section, the client certificate has to be signed with root_b which
   CN is ``root_b.openstack.host``. Root certificate can be created by
   referencing :doc:`/admin/configure_tls`.

   .. code-block:: console

     $ openssl x509 -req -in nfv_user.csr \
     -CA root_b.pem -CAkey root_b.key -CAcreateserial -out \
     nfv_user.pem -days 180 -sha256
     Certificate request self-signature ok
     subject=UID = 173c59254d3040969e359e5df0a3b475, O = Default, DC = default, CN = nfv_user


3. Obtain OAuth 2.0 Certificate-Bound access tokens through OAuth 2.0
   Mutual-TLS Client Authentication.

   .. code-block:: console

     $ curl -i -X POST https://$keystone_host_name/identity/v3/OS-OAUTH2/token \
     -H "application/x-www-form-urlencoded" \
     -d "grant_type=client_credentials&client_id=173c59254d3040969e359e5df0a3b475" \
     --cacert multi_ca.pem \
     --key nfv_user.key \
     --cert nfv_user.pem
     HTTP/1.1 200 OK
     Date: Mon, 30 Sep 2024 05:31:07 GMT
     Server: Apache/2.4.52 (Ubuntu)
     Content-Type: application/json
     Content-Length: 307
     Vary: X-Auth-Token
     x-openstack-request-id: req-11c95e0e-4b3f-4150-8ce9-b82f047c6906
     Connection: close

     {"access_token":"$oauth2_mtls_access_token","expires_in":3600,"token_type":"Bearer"}

4. Access Tacker APIs using obtained OAuth 2.0 Certificate-Bound access tokens.

   .. code-block:: console

     $ curl -i "https://$tacker_host_name:9890/v1.0/vims" \
     -H "Authorization: Bearer $oauth2_mtls_access_token" \
     -H "application/json" \
     --cert nfv_user.pem \
     --key nfv_user.key \
     --cacert multi_ca.pem
     HTTP/1.1 200 OK
     Content-Type: application/json
     Content-Length: 2182
     X-Openstack-Request-Id: req-9c39a83a-c123-4857-ac8c-ac0ada066ab1
     Date: Wed, 02 Oct 2024 00:23:17 GMT

     {"vims": [{"id": "ce04bbe5-3ffe-449f-ba2a-69c0a747b9ad", "type": "kubernetes", "tenant_id": "2e189ea6c1df4e4ba6d89de254b3a534", "name": "test-vim-k8s", "description": "", "placement_attr": {"regions": ["default", "kube-node-lease", "kube-public", "kube-system"]}, "is_default": true, "created_at": "2024-07-04 09:07:56", "updated_at": null, "extra": {}, "auth_url": "https://10.0.2.15:6443", "vim_project": {"name": "nfv"}, "auth_cred": {"bearer_token": "***", "ssl_ca_cert": "$ssl_ca_cert", "auth_url": "https://10.0.2.15:6443", "username": "None", "key_type": "barbican_key", "secret_uuid": "***"}, "status": "ACTIVE"}]}

     $ curl -i "https://$tacker_host_name:9890/vnfpkgm/v1/vnf_packages" \
     -H "Authorization: Bearer $oauth2_mtls_access_token" \
     -H "application/json" \
     --cert nfv_user.pem \
     --key nfv_user.key \
     --cacert multi_ca.pem
     HTTP/1.1 200 OK
     Content-Type: application/json
     Content-Length: 498
     X-Openstack-Request-Id: req-32628f18-a8e6-49cc-8ac6-b2e49d961a42
     Date: Wed, 02 Oct 2024 00:24:25 GMT

     [{"usageState": "IN_USE", "operationalState": "ENABLED", "id": "718e94a6-dfbf-48a4-8c6f-eaa541063a1b", "onboardingState": "ONBOARDED", "vnfProductName": "Sample VNF", "vnfProvider": "Company", "vnfSoftwareVersion": "1.0", "vnfdId": "eb37da52-9d03-4544-a1b5-ff5664c7687d", "vnfdVersion": "1.0", "_links": {"self": {"href": "/vnfpkgm/v1/vnf_packages/718e94a6-dfbf-48a4-8c6f-eaa541063a1b"}, "packageContent": {"href": "/vnfpkgm/v1/vnf_packages/718e94a6-dfbf-48a4-8c6f-eaa541063a1b/package_content"}}}

     $ curl -i "https://$tacker_host_name:9890/vnflcm/v2/vnf_instances" \
     -H "Authorization: Bearer $oauth2_mtls_access_token" \
     -H "application/json" \
     -H "Version:2.0.0"
     --cert nfv_user.pem \
     --key nfv_user.key \
     --cacert multi_ca.pem
     HTTP/1.1 200 OK
     Content-Length: 829
     Version: 2.0.0
     Accept-Ranges: none
     Content-Type: application/json
     X-Openstack-Request-Id: req-adcc7680-8491-413d-806e-47906d2601fa
     Date: Wed, 02 Oct 2024 00:36:24 GMT

     [{"id": "703148ca-addc-4226-bee8-ef73d81dbbbf", "vnfdId": "eb37da52-9d03-4544-a1b5-ff5664c7687d", "vnfProvider": "Company", "vnfProductName": "Sample VNF", "vnfSoftwareVersion": "1.0", "vnfdVersion": "1.0", "instantiationState": "INSTANTIATED", "_links": {"self": {"href": "http://$tacker_host_name:9890/vnflcm/v2/vnf_instances/703148ca-addc-4226-bee8-ef73d81dbbbf"}, "terminate": {"href": "http://$tacker_host_name:9890/vnflcm/v2/vnf_instances/703148ca-addc-4226-bee8-ef73d81dbbbf/terminate"}, "scale": {"href": "http://$tacker_host_name:9890/vnflcm/v2/vnf_instances/703148ca-addc-4226-bee8-ef73d81dbbbf/scale"}, "heal": {"href": "http://$tacker_host_name:9890/vnflcm/v2/vnf_instances/703148ca-addc-4226-bee8-ef73d81dbbbf/heal"}, "changeExtConn": {"href": "http://$tacker_host_name:9890/vnflcm/v2/vnf_instances/703148ca-addc-4226-bee8-ef73d81dbbbf/change_ext_conn"}}}]


Enable OpenStack Command through Mutual-TLS Client Authentication
-----------------------------------------------------------------

To use OAuth 2.0 Mutual-TLS Client Authentication from OpenStack CLI, you have
to use ``v3oauth2mtlsclientcredential`` as ``auth_type``.

1. Before executing the command, you should remove the variables that affect
   the OpenStack command from the OS environment, then set the variables that
   required by OAuth 2.0 Mutual-TLS Client Authentication to the OS
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


   .. code-block:: console

     $ export OS_AUTH_TYPE=v3oauth2mtlsclientcredential
     $ export OS_KEY=/opt/stack/certs/nfv_user.key
     $ export OS_CERT=/opt/stack/certs/nfv_user.pem
     $ export OS_CACERT=/opt/stack/certs/multi_ca.pem
     $ export OS_OAUTH2_CLIENT_ID=173c59254d3040969e359e5df0a3b475
     $ export OS_OAUTH2_ENDPOINT=https://$keystone_host_name/identity/v3/OS-OAUTH2/token
     $ export OS_INTERFACE=public
     $ export OS_REGION_NAME="RegionOne"
     $ export OS_IDENTITY_API_VERSION=3
     $ export OS_AUTH_URL=https://$keystone_host_name/identity


2. Execute Tacker commands to confirm that OpenStack command can access the
   Tacker APIs successfully.

   .. code-block:: console

     $ openstack vim list
     +--------------------------------------+--------------+----------------------------------+------------+------------+--------+
     | ID                                   | Name         | Tenant_id                        | Type       | Is Default | Status |
     +--------------------------------------+--------------+----------------------------------+------------+------------+--------+
     | ce04bbe5-3ffe-449f-ba2a-69c0a747b9ad | test-vim-k8s | 2e189ea6c1df4e4ba6d89de254b3a534 | kubernetes | True       | ACTIVE |
     +--------------------------------------+--------------+----------------------------------+------------+------------+--------+
     $ openstack vnf package list
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
     | Id                                   | Vnf Product Name | Onboarding State | Usage State | Operational State | Links                                                                                           |
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
     | 718e94a6-dfbf-48a4-8c6f-eaa541063a1b | Sample VNF       | ONBOARDED        | IN_USE      | ENABLED           | {                                                                                               |
     |                                      |                  |                  |             |                   |     "self": {                                                                                   |
     |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/718e94a6-dfbf-48a4-8c6f-eaa541063a1b"                 |
     |                                      |                  |                  |             |                   |     },                                                                                          |
     |                                      |                  |                  |             |                   |     "packageContent": {                                                                         |
     |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/718e94a6-dfbf-48a4-8c6f-eaa541063a1b/package_content" |
     |                                      |                  |                  |             |                   |     }                                                                                           |
     |                                      |                  |                  |             |                   | }                                                                                               |
     +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
     $ openstack vnflcm list --os-tacker-api-version 2
     +--------------------------------------+-------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
     | ID                                   | VNF Instance Name | Instantiation State | VNF Provider | VNF Software Version | VNF Product Name | VNFD ID                              |
     +--------------------------------------+-------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+
     | 703148ca-addc-4226-bee8-ef73d81dbbbf |                   | INSTANTIATED        | Company      | 1.0                  | Sample VNF       | eb37da52-9d03-4544-a1b5-ff5664c7687d |
     +--------------------------------------+-------------------+---------------------+--------------+----------------------+------------------+--------------------------------------+


.. _RFC6749: https://datatracker.ietf.org/doc/html/rfc6749
.. _ETSI NFV-SOL013 v3.4.1: https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/013/03.04.01_60/gs_nfv-sol013v030401p.pdf
.. _OAuth 2.0 client credentials: https://docs.openstack.org/keystone/latest/admin/oauth2-usage-guide.html
.. _Middleware Architecture: https://docs.openstack.org/keystonemiddleware/latest/middlewarearchitecture.html
.. _OAuth 2.0 usage guide: https://docs.openstack.org/keystone/latest/admin/oauth2-usage-guide.html
.. _Application Credentials API: https://docs.openstack.org/api-ref/identity/v3/index.html#application-credentials
.. _OAuth 2.0 Access Token API: https://docs.openstack.org/api-ref/identity/v3-ext/index.html#os-oauth2-api
.. _RFC1779: https://datatracker.ietf.org/doc/html/rfc1779
.. _RFC2985: https://datatracker.ietf.org/doc/html/rfc2985
.. _RFC4519: https://datatracker.ietf.org/doc/html/rfc4519
.. _RFC8705: https://datatracker.ietf.org/doc/html/rfc8705
.. _Configure HTTPS in Identity Service: https://docs.openstack.org/keystone/latest/admin/configure-https.html
.. _Mapping Combinations: https://docs.openstack.org/keystone/latest/admin/federation/mapping_combinations.html
