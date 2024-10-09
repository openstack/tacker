======================================
Configuring Tacker as OAuth 2.0 Client
======================================

.. note::

  The content of this document has been confirmed to work
  using Tacker 2024.1 Caracal.


Overview
~~~~~~~~

As an API client, Tacker can use Oauth 2.0 Client Credentials Grant flow and
OAuth 2.0 Mutual-TLS Client Authentication to access the Notification server
and the External NFVO server. The OAuth 2.0 Client Credentials Grant flow of
`RFC6749`_ OAuth 2.0 Authorization Framework is prescribed in the API
specification of `ETSI NFV-SOL013 v3.4.1`_. And Tacker implements OAuth 2.0
Mutual-TLS Client Authentication based on `RFC8705`_.

Guide for OAuth 2.0 Client Credentials Grant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can enable Tacker as OAuth 2.0 Client Credentials Grant by following this
guide.

Enable Client Credentials Grant for Access to Notification Server
-----------------------------------------------------------------

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


2. Restart Tacker service so that the modified configuration information takes
   effect.

   .. code-block:: console

     $ sudo systemctl restart devstack@tacker.service


Verify that Access Uses Client Credentials Grant
------------------------------------------------

Subscribe to a notification that requires OAuth 2.0 Client Credentials
Grant to confirm that Tacker can send a notification successfully to
Notification Server.

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


Guide for OAuth 2.0 Mutual-TLS Client Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To use Tacker as mTLS OAuth 2.0 client, client private key and certificate will
be necessary. You can reference :doc:`/admin/configure_tls` to create private
root CA, private key and certificate that will be required in this guide.
Because different authorization servers have different ways of authenticating
TLS certificates provided by client, the relevant Subject Distinguished Names
such as Common Name need to be set when creating client certificate according
to the authorization server. The ``tacker_cert_and_key.pem`` file that is used
in this guide, can be created by concatenating the client certificate file and
client private key file.

.. code-block:: console

  $ cat tacker_client.pem tacker_client.key >> tacker_cert_and_key.pem


You can enable Tacker as a mTLS OAuth 2.0 client by the following steps in this
guide.

Enable Mutual-TLS Client Authentication for Access to Notification server
-------------------------------------------------------------------------

The following parts describe steps to enable mTLS only for access to the
Notification server.

1. Modify the configuration file ``tacker.conf`` to enable SSL to implement
   mTLS support. The following settings are examples, and the certificate
   should be saved in a directory with appropriate access permission.

   .. code-block:: console

     $ vi /etc/tacker/tacker.conf
     [v2_vnfm]
     notification_mtls_ca_cert_file = /etc/tacker/multi_ca.pem
     notification_mtls_client_cert_file = /etc/tacker/tacker_cert_and_key.pem


2. Restart Tacker service so that the modified configuration information takes
   effect.

   .. code-block:: console

     $ sudo systemctl restart devstack@tacker


Enable Mutual-TLS Client Authentication for Access to External NFVO server
--------------------------------------------------------------------------

The following parts describe steps to enable mTLS only for access to the
External NFVO server.

1. Modify the configuration file ``tacker.conf`` to enable SSL to implement
   mTLS support. The `client_id` and `client_password` must be obtained from
   the authentication server used by the External NFVO server.
   If you are using Keystone as the authentication server, you can use user_id
   as the client_id for mTLS authentication.

   .. code-block:: console

     $ vi /etc/tacker/tacker.conf
     [v2_nfvo]
     use_external_nfvo = True
     endpoint = https://endpoint.host
     token_endpoint = https://token_endpoint.host/token
     client_id = client_id
     client_password = client_password
     mtls_ca_cert_file = /etc/tacker/multi_ca.pem
     mtls_client_cert_file = /etc/tacker/tacker_cert_and_key.pem


2. Restart Tacker service so that the modified configuration information takes
   effect.

   .. code-block:: console

     $ sudo systemctl restart devstack@tacker


Verify that Access Uses Mutual-TLS Client Authentication
--------------------------------------------------------

Access to the External NFVO server and the Notification server is not outputted
to the Tacker log. Therefore, check the access log of the External NFVO server
and the Notification server when executing lcm operations, or use the packet
capture software to confirm that the access to each server is the mTLS
communication. If the packet capture shows that the client and the server are
sending certificates to each other during the handshake, you can verify that
mTLS is enabled.

.. _RFC8705: https://datatracker.ietf.org/doc/html/rfc8705
.. _RFC6749: https://datatracker.ietf.org/doc/html/rfc6749
.. _ETSI NFV-SOL013 v3.4.1: https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/013/03.04.01_60/gs_nfv-sol013v030401p.pdf
