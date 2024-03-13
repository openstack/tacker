============================================================================
How to use ETSI NFV-SOL VNF LCM coordination API in the coordinateVNF script
============================================================================

This document describes how to use the sample coordinateVNF
script for ETSI NFV-SOL VNF LCM coordination API
in the ChangeCurrentVNFPackage v2 API.


Overview
--------

1. The sample coordinateVNF script for ETSI NFV-SOL VNF coordination API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The sample coordinateVNF script of
`ETSI NFV-SOL VNF LCM coordination API`
is designed for users who want to communicate with
external management systems (e.g., Operations
Support Systems (OSS) / Element Manager (EM))
as the client.
You can know how to use it in this user guide.

.. warning::

  The sample script implements the client function
  in the ChangeCurrentVNFPackage API only,
  not formal support for the VNF LCM Coordination
  API itself since Tacker is based on ETSI-NFV SOL 002
  v3.3.1 that do not support the VNF LCM Coordination API.
  The sample implements the VNF LCM Coordination
  API version: 1.0.0 based ETSI-NFV SOL 002 v3.6.1.


2. Use Case
^^^^^^^^^^^^
In this sample, the use case focuses on
the client function of the VNF LCM Coordination API
in the Coordinate VNF script when performing
the RollingUpdate with external management systems
in the ChangeCurrentVNFPackage API.
VNFM acts as a client and the external management system
like EM acts as a server in the use case.
The following operations are provided
in the sample scripts.

* Request a coordination action
  (POST /lcmcoord/v1/coordinations)
* Read the result of a coordination action
  (GET /lcmcoord/v1/coordinations/{coordinationId})

If you want to know `ETSI NFV-SOL VNF Coordinate API`
in detail, please see `ETSI NFV-SOL 002 v3.6.1`_.

If you want to know how to use `the Coordinate VNF script`,
please see the following documents of
ChangeCurrentVNFPackage API.

* :doc:`/user/v2/vnf/chg_vnfpkg/index`
* :doc:`/user/v2/vnf/chg_vnfpkg_with_standard/index`


Usage example
-------------

Flow of VNF update
^^^^^^^^^^^^^^^^^^

The following diagram shows the rolling update
using the Coordinate VNF script as the client of
the VNF LCM Coordination API.

.. code-block::

                                                             +---------+
                                                             |  VNFD   |
                                                             |         |
                                                             +----+----+
                                                                  |
                                        (Script is included       v       +-------------------+
                +--------------------+  in the package)     +----------+  | Change current    |
  +------------>| CoordinateVNF      +--------------------->|          |  | VNF Package       |
  |             | script             |                      |   CSAR   |  | Request with      |
  |   +---------+                    |                      |          |  | Additional Params |
  |   |         +-------+------------+                      +-----+----+  +--+----------------+
  |   |                 |    ^                                    |          | 1. Change current VNF Package
  |   |                 |    |                              +-----v----------v------------------------------+
  |   |  7. Coordination|    | Coordination                 |  +-----------------------+              VNFM  |
  |   |     request     |    | Result                       |  |   Tacker-server       |                    |
  |   |                 |    |                              |  +--+--------------------+                    |
  |   |                 v    |                              |     |  2. Change current VNF Package request  |
  |   |         +------------+-------+                      |     v                                         |
  |   |         |    External        |                      |  +-----------------------------------------+  |
  |   |         |    management      |                      |  |                                         |  |
  |   |         |    system (EM)     |                      |  |   +-------------------+                 |  |
  |   |         +--------------------+                      |  |   | VnfLcmDriver      |                 |  |
  |   |                                                     |  |   |                   |                 |  |
  |   |                                                     |  |   |                   |                 |  |
  |   |                                                     |  |   |                   |                 |  |
  |   |                                                     |  |   |                   |                 |  |
  |   |                                                     |  |   |                   |                 |  |
  |   |  6. Coordinate                                      |  |   +-+-----------------+                 |  |
  |   |     resource                                        |  |     |                                   |  |
  |   |         +--------------------+                      |  |     v                                   |  |
  |   |         |                    | 3. Get stack resource|  |   +-------------------+                 |  |
  |   |         |  +--------------+  |    to update         |  |   | InfraDriver       | 8. Repeat steps |  |
  |   |         |  | Resource     |<-+----------------------+--+---+                   |    4 through 7  |  |
  |   +---------+->|              |  | 4. Update VNFC       |  |   |                   |    for each VNFC|  |
  |             |  |              |<-+----------------------+--+---+                   +--------+        |  |
  |             |  +--------------+  |                      |  |   |                   |        |        |  |
  |             | VNF                |                      |  |   |                   |<-------+        |  |
  |             +--------------------+                      |  |   |                   |                 |  |
  |                        5. Execute CoordinateVNF script  |  |   |                   |                 |  |
  +---------------------------------------------------------+--+---+                   |                 |  |
                                                            |  |   +-------------------+                 |  |
                                                            |  |    Tacker-conductor                     |  |
                +--------------------+                      |  +-----------------------------------------+  |
                | Hardware Resources |                      |                                               |
                +--------------------+                      +-----------------------------------------------+


1. Execute Change current VNF Package operation

   User sends a ChangeCurrentVNFPackage request
   to the "Individual VNF instance" resource with
   Additional Params.

   .. code-block:: console

     $ openstack vnflcm change-vnfpkg VNF_INSTANCE_ID \
       ./sample_param_file_for_coordination.json \
       --os-tacker-api-version 2


   Tacker-server calls Tacker-conductor, then Tacker-conductor fetches
   an on-boarded VNF package and calls VnfLcmDriver.

   You can set following parameter in additionalParams
   in the ChangeCurrentVnfPkgRequest to specify
   the information of the external coordination server.

   * additionalParams

     .. list-table::
       :widths: 15 10 30
       :header-rows: 1

       * - Attribute name
         - Cardinality
         - Parameter description
       * - upgrade_type
         - 1
         - Type of file update operation method. Specify Blue-Green or Rolling update.
       * - lcm-operation-coordinate-old-vnf
         - 1
         - The file path of the script that simulates the behavior of CoordinateVNF for old VNF.
       * - lcm-operation-coordinate-new-vnf
         - 1
         - The file path of the script that simulates the behavior of CoordinateVNF for new VNF.
       * - vdu_params
         - 0..N
         - VDU information of target VDU to update.
           Specifying a vdu_params is required for OpenStack VIM and not required for Kubernetes VIM.
       * - > vdu_id
         - 1
         - VDU name of target VDU to update.
       * - > old_vnfc_param
         - 0..1
         - Old VNFC connection information.
           Required for ssh connection in CoordinateVNF operation for application configuration to VNFC.
       * - >> cp_name
         - 1
         - Connection point name of old VNFC to update.
       * - >> username
         - 1
         - User name of old VNFC to update.
       * - >> password
         - 1
         - Password of old VNFC to update.
       * - >> endpoint
         - 1
         - Endpoint URL of coordination server.
       * - >> authentication
         - 0..1
         - Authentication parameters to configure the use of Authorization
           when connecting to coordination server.
       * - \>>> authType
         - 1..N
         - Defines the types of Authentication/Authorization
           which the API consumer is willing to accept
           when receiving a notification. Permitted values:

           * ``BASIC``: use HTTP Basic authentication
             with the client credentials.
           * ``OAUTH2_CLIENT_CREDENTIALS``: use an OAuth 2.0
             token, obtained using the client credentials
             grant type after authenticating using client
             identifier and client password.
           * ``OAUTH2_CLIENT_CERT``:  use an OAuth 2.0 token,
             obtained using the client credentials grant type
             after mutually authenticating using client
             identifier and X.509 certificates.
       * - \>>> paramsBasic
         - 0..1
         - Parameters for authentication/authorization
           using authType ``BASIC``.
       * - >>>> userName
         - 0..1
         - Username to be used in HTTP Basic authentication.
       * - >>>> password
         - 0..1
         - Password to be used in HTTP Basic authentication.
       * - \>>> paramsOauth2ClientCredentials
         - 0..1
         - Parameters for authentication/authorization using
           authType ``OAUTH2_CLIENT_CREDENTIALS``.
       * - >>>> clientId
         - 0..1
         - Client identifier to be used in the access token
           request of the OAuth 2.0 client credentials
           grant type.
       * - >>>> clientPassword
         - 0..1
         - Client password to be used in the access token
           request of the OAuth 2.0 client credentials
           grant type.
       * - >>>> tokenEndpoint
         - 0..1
         - The token endpoint from which the access token
           can be obtained.
       * - \>>> paramsOauth2ClientCert
         - 0..1
         - Parameters for authentication/authorization using
           authType ``OAUTH2_CLIENT_CERT``.
       * - >>>> clientId
         - 1
         - Client identifier to be used in the access token
           request of the OAuth 2.0 client credentials
           grant type.
       * - >>>> certificateRef
         - 1
         - Fingerprint of the client certificate.
           The hash function shall use SHA256 or higher.
       * - >>>>> type
         - 1
         - The type of the fingerprint. Permitted values:

           * ``x5t#S256``: The SHA-256 thumbprint of the X.509 certificate
             as defined in section 4.1.8 of IETF RFC 7515.
       * - >>>>> value
         - 1
         - The fingerprint value as defined by the type.
       * - >>>> tokenEndpoint
         - 1
         - The token endpoint from which the access token
           can be obtained.
       * - >> coordination_server_param
         - 0..1
         - Information to access coordination server.
           It is required when using coordinateVNF script which calling Coordination API.
       * - >> timeout
         - 0..1
         - Timeout seconds for resending requests to Coordination API.
       * - > new_vnfc_param
         - 0..1
         - New VNFC connection information.
           Required for ssh connection in CoordinateVNF operation for application configuration to VNFC.
       * - >> cp_name
         - 1
         - Connection point name of new VNFC to update.
       * - >> username
         - 1
         - User name of new VNFC to update.
       * - >> password
         - 1
         - Password of new VNFC to update.
       * - >> endpoint
         - 1
         - Endpoint URL of coordination server.
       * - >> authentication
         - 0..1
         - Authentication parameters to configure the use of Authorization
           when connecting to coordination server.
       * - \>>> authType
         - 1..N
         - Defines the types of Authentication/Authorization
           which the API consumer is willing to accept
           when receiving a notification. Permitted values:

           * ``BASIC``: use HTTP Basic authentication
             with the client credentials.
           * ``OAUTH2_CLIENT_CREDENTIALS``: use an OAuth 2.0
             token, obtained using the client credentials
             grant type after authenticating using client
             identifier and client password.
           * ``OAUTH2_CLIENT_CERT``:  use an OAuth 2.0 token,
             obtained using the client credentials grant type
             after mutually authenticating using client
             identifier and X.509 certificates.
       * - \>>> paramsBasic
         - 0..1
         - Parameters for authentication/authorization
           using authType ``BASIC``.
       * - >>>> userName
         - 0..1
         - Username to be used in HTTP Basic authentication.
       * - >>>> password
         - 0..1
         - Password to be used in HTTP Basic authentication.
       * - \>>> paramsOauth2ClientCredentials
         - 0..1
         - Parameters for authentication/authorization using
           authType ``OAUTH2_CLIENT_CREDENTIALS``.
       * - >>>> clientId
         - 0..1
         - Client identifier to be used in the access token
           request of the OAuth 2.0 client credentials
           grant type.
       * - >>>> clientPassword
         - 0..1
         - Client password to be used in the access token
           request of the OAuth 2.0 client credentials
           grant type.
       * - >>>> tokenEndpoint
         - 0..1
         - The token endpoint from which the access token
           can be obtained.
       * - \>>> paramsOauth2ClientCert
         - 0..1
         - Parameters for authentication/authorization using
           authType ``OAUTH2_CLIENT_CERT``.
       * - >>>> clientId
         - 1
         - Client identifier to be used in the access token
           request of the OAuth 2.0 client credentials
           grant type.
       * - >>>> certificateRef
         - 1
         - Fingerprint of the client certificate.
           The hash function shall use SHA256 or higher.
       * - >>>>> type
         - 1
         - The type of the fingerprint. Permitted values:

           * ``x5t#S256``: The SHA-256 thumbprint of the X.509 certificate
             as defined in section 4.1.8 of IETF RFC 7515.
       * - >>>>> value
         - 1
         - The fingerprint value as defined by the type.
       * - >>>> tokenEndpoint
         - 1
         - The token endpoint from which the access token
           can be obtained.
       * - >> coordination_server_param
         - 0..1
         - Information to access coordination server.
           It is required when using coordinateVNF script which calling Coordination API.
       * - >> timeout
         - 0..1
         - Timeout seconds for resending requests to Coordination API.
       * - external_lb_param
         - 0..1
         - Load balancer information that requires configuration changes.
           Required only for the Blue-Green deployment process of OpenStack VIM.
       * - > ip_address
         - 1
         - IP address of load balancer server.
       * - > username
         - 1
         - User name of load balancer server.
       * - > password
         - 1
         - Password of load balancer server.

   The example of the request of additionalParams as below.

   .. code-block:: json

     "additionalParams": {
       "upgrade_type": "RollingUpdate",
       "lcm-operation-coordinate-new-vnf": "./Scripts/coordinate_vnf.py",
       "lcm-operation-coordinate-old-vnf": "./Scripts/coordinate_vnf.py",
       "vdu_params": [{
         "vdu_id": "VDU1",
         "old_vnfc_param": {
           "cp_name": "VDU1_CP1",
           "username": "ubuntu",
           "password": "ubuntu",
           "endpoint": "http://127.0.0.1:6789",
           "authentication": {
             "authType": [
               "BASIC"
             ],
             "paramsBasic": {
               "userName": "tacker",
               "password": "tacker"
             }
           },
           "timeout": 30
         },
         "new_vnfc_param": {
           "cp_name": "VDU1_CP1",
           "username": "ubuntu",
           "password": "ubuntu",
           "endpoint": "http://127.0.0.1:6789",
           "authentication": {
             "authType": [
               "BASIC"
             ],
             "paramsBasic": {
               "userName": "tacker",
               "password": "tacker"
             }
           },
           "timeout": 30
         }
       },
       {
         "vdu_id": "VDU2",
         "old_vnfc_param": {
           "cp_name": "VDU2_CP1",
           "username": "ubuntu",
           "password": "ubuntu",
           "endpoint": "http://127.0.0.1:6789",
           "authentication": {
             "authType": [
               "BASIC"
             ],
             "paramsBasic": {
               "userName": "tacker",
               "password": "tacker"
             }
           },
           "timeout": 30
         },
         "new_vnfc_param": {
           "cp_name": "VDU2_CP1",
           "username": "ubuntu",
           "password": "ubuntu",
           "endpoint": "http://127.0.0.1:6789",
           "authentication": {
             "authType": [
               "BASIC"
             ],
             "paramsBasic": {
               "userName": "tacker",
               "password": "tacker"
             }
           },
           "timeout": 30
         }
       }]
     }

2. Request Change current VNF Package Process to InfraDriver

   VnfLcmDriver sends a request to the InfraDriver to change vnfpkg process.

3. Get stack resource to update

   InfraDriver sends a request to the VIM to get stack resource to update.

4. Update VNFC

   InfraDriver sends a request to the VIM to update stack.

5. Execute CoordinateVNF script

   InfraDriver runs CoordinateVNF script.
   The script is included in the VNF package
   and you can modify them for your environments.

   The sample class for Coordination API and
   main methods in the  CoordinateVNF script
   ``coordinate_vnf.py`` as below.

   .. code-block:: console

      class CoordScript(object):
          def __init__(self, vnfc_param):
              self.vnfc_param = vnfc_param

          def run(self):
              coord_req = self.vnfc_param['LcmCoordRequest']
              coord_req['coordinationActionName'] = (
                  "prv.tacker_organization.coordination_test")
              endpoint = self.vnfc_param.get('endpoint')
              authentication = self.vnfc_param.get('authentication')
              timeout = self.vnfc_param.get('timeout')

              input_params = self.vnfc_param.get('inputParams')
              if input_params is not None:
                  coord_req['inputParams'] = input_params

              if endpoint is None:
                  raise Exception('endpoint must be specified.')
              if authentication is None:
                  raise Exception('authentication must be specified.')

              # Reload "tacker.conf" when using OAUTH2_CLIENT_CERT
              # for authentication.
              args = ["--config-file", "/etc/tacker/tacker.conf"]
              config.init(args)

              coord = coord_client.create_coordination(
                  endpoint, authentication, coord_req, timeout)
              if coord['coordinationResult'] != "CONTINUE":
                  raise Exception(
                      f"coordinationResult is {coord['coordinationResult']}")

      def main():
          vnfc_param = pickle.load(sys.stdin.buffer)
          script = CoordScript(vnfc_param)
          script.run()


   .. note::

     According to ETSI-NFV SOL 002 v3.6.1, the coordination
     action `coordinationActionName` is defined to be declared
     in the VNFD. However, the CoordinateVNF script does not
     refer to the VNFD, it must be described in the script.
     (e.g., "prv.tacker_organization.coordination_test")


6. Coordinate resource

   CoordinateVNF script sends a request to the VNF to Coordinate VNF.

7. Coordination request to the external management system (EM)

   CoordinateVNF script sends a Coordination request to
   the external management system (EM). The endpoint URL of EM is
   obtained from the ChangeCurrentVNFPackage request.
   The target VNFC obtained from Tacker is specified as inputParams
   in the LcmCoordRequest. (e.g. it is specified by vnfcInstanceId).

   Tacker can use 2 operations of VNF LCM Coordination API supported in
   utility functions ``tacker/sol_refactored/common/coord_client.py``.
   You can use them via the CoordinateVNF script.

   * Request a coordination action
     (POST /lcmcoord/v1/coordinations)

     VNFM requests Coordination actions
     to the Coordination API Server (e.g. EM).

     An example request body is below.

     .. code-block:: json

       {
          "vnfInstanceId": "b18a8a15-8973-4202-a2f0-a67a109fc461",
          "vnfLcmOpOccId": "2cae986e-7fea-4aeb-9b22-f81b35800838",
          "coordinationActionName": "prv.tacker_organization.coordination_test",
          "lcmOperationType": "CHANGE_VNFPKG",
          "_links": {
            "vnfLcmOpOcc": {
              "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_lcm_op_occs/2cae986e-7fea-4aeb-9b22-f81b35800838"
            },
            "vnfInstance": {
              "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/b18a8a15-8973-4202-a2f0-a67a109fc461"
            }
          }
        }


   * Read the result of a coordination action
     (GET /lcmcoord/v1/coordinations/{coordinationId})

     VNFM requests the result of a coordination action
     to the Coordination API Server (e.g. EM).

   The process after receiving Coordination response diverges
   depending on whether the Synchronous or Asynchronous mode.

   .. note::

     | According to ETSI-NFV SOL 002 v3.6.1, the Coordination interface supports
       Synchronous and Asynchronous modes.
       API server decides the mode, and API client can know it by the API response.
       Thus, since VNFM cannot control the mode, Tacker will support both modes.
       In both modes, the timeout seconds for resending requests can be specified
       with "timeout" in additionalParams.
       The following shows the Coordination processes of VNFM.
     |
     | Synchronous mode: The EM returns to the Tacker a "201 Created" response
       with a "LcmCoord" data structure in the body
       and then VNFM continues the process on the basis of the result.
       Alternatively, EM returns a "503 Service Unavailable" response with
       a "ProblemDetails" data structure in the body and a "Retry-After"
       HTTP header that indicates the length of a delay after which a retry
       of the coordination is suggested.
       After the delay interval has passed, the VNFM sends coordination request again.
     |
     | Asynchronous mode: The EM returns to the Tacker a "202 Accepted" response
       with an empty body and a "Location" HTTP header that indicates
       the URI of the "Individual coordination action" resource.
       Tacker waits for a certain time interval
       (as indicated in the Retry-After header of the previous 202 response if signalled,
       or determined by other means otherwise) before the next iteration of the loop.
       Tacker polls the status of the coordination by sending a GET request to the EM,
       using the URI that was returned in the "Location" header.
       After obtaining the coordination result, Tacker continues the process on the basis of it.


8. Repeat steps 4 through 7 for each VNFC

   Each VNFC is executed starting with the higher value of
   the vnfcResourceInfo index in the StandardUserData
   (or newer in the DefaultUserData).

9. Finish VNF LCM coordination API operation

   When finish VNF LCM coordination API operation via the CoordinateVNF script,
   Change current VNF Package operation will finish successfully.


History of Checks
-----------------

The contents of this document are written with reference to the following
sample script and request for 2023.2 Bobcat.

* `coordinate_vnf.py of userdata_standard for 2023.2 Bobcat`_
* `sample4_change_vnfpkg of userdata_standard_change_vnfpkg for 2023.2 Bobcat`_


.. _ETSI NFV-SOL 002 v3.6.1: https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/002/03.06.01_60/gs_nfv-sol002v030601p.pdf
.. _coordinate_vnf.py of userdata_standard for 2023.2 Bobcat:
  https://opendev.org/openstack/tacker/src/branch/stable/2023.2/tacker/tests/functional/sol_v2_common/samples/userdata_standard/contents/Scripts/coordinate_vnf.py
.. _sample4_change_vnfpkg of userdata_standard_change_vnfpkg for 2023.2 Bobcat:
  https://opendev.org/openstack/tacker/src/branch/stable/2023.2/tacker/tests/functional/sol_v2_common/paramgen.py#L1190-L1257
