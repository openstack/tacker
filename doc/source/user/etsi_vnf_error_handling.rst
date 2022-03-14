===============================
ETSI NFV-SOL VNF error-handling
===============================

This document describes how to error-handling VNF in Tacker.

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

A default VIM should be registered according to
:doc:`../cli/cli-legacy-vim`.

The VNF Package(sample_vnf_pkg.zip) used below is prepared
by referring to :doc:`./vnf-package`.

Execute up to "Instantiate VNF" in the procedure of
:doc:`./etsi_vnf_deployment_as_vm_with_tosca`.
In other words, the procedure after "Terminate VNF" is not executed.


VNF Error-handling Procedures
-----------------------------

As mentioned in Prerequisites, the VNF must be created
before performing error-handling.

Details of CLI commands are described in
:doc:`../cli/cli-etsi-vnflcm`.

There are some operations to error-handling VNF.

* Rollback VNF lifecycle management operation
* Fail VNF lifecycle management operation
* Retry VNF lifecycle management operation

In order to execute error-handling, it is necessary to specify
VNF_LCM_OP_OCC_ID, which is the ID for the target LCM operation.
First, the method of specifying the ID will be described.


Identify VNF_LCM_OP_OCC_ID
~~~~~~~~~~~~~~~~~~~~~~~~~~

To identify the VNF_LCM_OP_OCC_ID, you can get with the following ways.

* to check with CLI
* to check with notification API body

You can choose both ways.

This case uses openstack CLI:

Details of CLI commands are described in
:doc:`../cli/cli-etsi-vnflcm`.

Before checking the "VNF_LCM_OP_OCC_ID", you should get VNF_INSTANCE_ID first.

.. code-block:: console

  $ openstack vnflcm op list


Result:

.. code-block:: console

  +--------------------------------------+-----------------+--------------------------------------+-----------------+
  | ID                                   | Operation State | VNF Instance ID                      | Operation       |
  +--------------------------------------+-----------------+--------------------------------------+-----------------+
  | 304538dd-d754-4661-9f17-5496dab9693d | FAILED_TEMP     | 3aa5c054-c162-4d5e-9808-0bc30f92a4c7 | INSTANTIATE     |
  +--------------------------------------+-----------------+--------------------------------------+-----------------+


For this case, check notification API body:

In checking with Notification API, you should execute the following steps:

* Create a new subscription
* Execute LCM operations, such as 'Creates a new VNF instance resource'.

The procedure for executing the API using the curl command is shown below.

First, the method of generating Keystone-tokens will be described.
See `Keystone API reference`_. for details on Keystone APIs.
For **<username>** and **<password>**, **<project_name>**,
set values according to your environment.

Prepare get_token.json file to get token:

.. code-block:: json

  {
    "auth": {
      "identity": {
        "methods": [
          "password"
        ],
        "password": {
          "user": {
            "name": "<username>",
            "password": "<password>",
            "domain": {
              "name": "Default"
            }
          }
        }
      },
      "scope": {
        "project": {
          "name": "<project_name>",
          "domain": {
            "name": "Default"
          }
        }
      }
    }
  }


Get token:

.. code-block:: console

  $ curl -i -X POST -H "Content-Type: application/json" -d @./get_token.json  "$OS_AUTH_URL/v3/auth/tokens"


Result:

.. code-block:: console

  HTTP/1.1 201 CREATED
  Date: Tue, 17 Nov 2020 08:01:44 GMT
  Server: Apache/2.4.41 (Ubuntu)
  Content-Type: application/json
  Content-Length: 7187
  X-Subject-Token: gAAAAABfs4No8WVYIPagnJvnnImNHq_918oLgOiJwSXqXGJKfv_FEcgfeZajIl0NCk7Pr6YMn1Sa96ZhOnWioKGrOxBSEGVxgYqBFx3bFfKAHVmzgoEaN6zfHZvbm1QJgoeg1QV5i-VjfeeQRWZptYqd3yWMLzrWSfVBER9pL-nRi0CvMXJM0yE
  Vary: X-Auth-Token
  x-openstack-request-id: req-6b19a1ee-0eb0-4aa8-97e7-c54d750c9b64
  Connection: close
  ...snip response-body...


Set the value of **X-Subject-Token** included in the above result to
the environment variable **$OS_AUTH_TOKEN**.

.. code-block:: console

  $ export OS_AUTH_TOKEN="gAAAAABfs4No8WVYIPagnJvnnImNHq_918oLgOiJwSXqXGJKfv_FEcgfeZajIl0NCk7Pr6YMn1Sa96ZhOnWioKGrOxBSEGVxgYqBFx3bFfKAHVmzgoEaN6zfHZvbm1QJgoeg1QV5i-VjfeeQRWZptYqd3yWMLzrWSfVBER9pL-nRi0CvMXJM0yE"


Create subscription:

.. code-block:: console

  $ curl -g -i -X POST http://127.0.0.1:9890/vnflcm/v1/subscriptions \
    -H "Accept: application/json" \
    -H "Content-Type: application/json" \
    -H "X-Auth-Token: $OS_AUTH_TOKEN" \
    -d '{"callbackUri": "http://127.0.0.1/"}'


Result:

.. code-block:: console

  HTTP/1.1 201 Created
  Content-Length: 199
  Location: http://localhost:9890//vnflcm/v1/subscriptions/5bd3b81d-a6e9-45e7-922e-adc26328322d
  Content-Type: application/json
  X-Openstack-Request-Id: req-5f98782d-ca47-4144-a413-bd9641302f77
  Date: Mon, 21 Dec 2020 08:21:47 GMT

  {"id": "5bd3b81d-a6e9-45e7-922e-adc26328322d", "callbackUri": "http://127.0.0.1/", "_links": {"self": {"href": "http://localhost:9890//vnflcm/v1/subscriptions/5bd3b81d-a6e9-45e7-922e-adc26328322d"}}}


Show subscription:

.. code-block:: console

  $ curl -g -i -X GET http://127.0.0.1:9890/vnflcm/v1/subscriptions/{subscriptionId} \
    -H "Accept: application/json" \
    -H "X-Auth-Token: $OS_AUTH_TOKEN"


Result:

.. code-block:: console

  HTTP/1.1 200 OK
  Content-Length: 213
  Content-Type: application/json
  X-Openstack-Request-Id: req-2d7503dc-1f75-40de-9d75-7c01180aee89
  Date: Mon, 21 Dec 2020 08:22:59 GMT

  {"id": "5bd3b81d-a6e9-45e7-922e-adc26328322d", "filter": {}, "callbackUri": "http://127.0.0.1/", "_links": {"self": {"href": "http://localhost:9890//vnflcm/v1/subscriptions/5bd3b81d-a6e9-45e7-922e-adc26328322d"}}}


Show VNF LCM operation occurrence:

.. code-block:: console

  $ curl -g -i -X GET http://127.0.0.1:9890/vnflcm/v1/vnf_lcm_op_occs/{vnfLcmOpOccId} \
    -H "Accept: application/json" \
    -H "X-Auth-Token: $OS_AUTH_TOKEN"


Result:

.. code-block:: console

  HTTP/1.1 200 OK
  Content-Length: 3082
  Content-Type: application/json
  X-Openstack-Request-Id: req-d0720ffc-e7ee-4ee2-af61-a9a4a91c67cb
  Date: Mon, 21 Dec 2020 08:30:25 GMT

  {"id": "e3dc7530-e699-46ed-b65e-32911af1e414", "operationState": "FAILED_TEMP", "stateEnteredTime": "2020-12-21 06:52:06+00:00",
  ...snip response-body...


Error-handling can be executed only when **operationState** is **FAILED_TMP**.

With the above LCM operation trigger, 'Notification' is sent to
the **callbackUri** set in 'Create a new subscription'.

**vnfLcmOpOccId** included in this 'Notification' corresponds
to VNF_LCM_OP_OCC_ID.

See `VNF LCM v1 API`_ and `VNF LCM v2 API`_
for details on the APIs used here.


Rollback VNF LCM Operation
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
    Rollback of Scale-Out has a difference in operation result between v1 and v2.
    In v1, the oldest VNFc(VM) is deleted. In v2, the newest VNFc(VM) is deleted.

.. list-table::
   :widths: 10 40 15 15 10 10
   :header-rows: 1

   * - LCM Operation
     - Description of Rollback
     - Precondition
     - Postcondition
     - Support in v1
     - Support in v2
   * - Instantiate
     - | VNFM removes all VMs and resources.
       | e.g. Tacker executes Heat stack-delete for deletion of the target VM.
     - FAILED_TEMP
     - ROLLED_BACK or FAILED_TEMP
     - X
     - X
   * - Scale-out
     - | VNFM reverts changes of VMs and resources specified in the middle of scale-out operation.
       | There are differences in the operation results of v1 and v2. See note.
       | e.g. Tacker reverts desired_capacity and executes Heat stack-update.
     - FAILED_TEMP
     - ROLLED_BACK or FAILED_TEMP
     - X
     - X
   * - Modify
     - VNFM reverts the update of the VNF instance information.
     - FAILED_TEMP
     - ROLLED_BACK or FAILED_TEMP
     -
     - X
   * - Change external connectivity
     - | VNFM reverts changes of the external connectivity for VNF instances.
       | e.g. Tacker reverts stack parameters and executes Heat stack-update.
     - FAILED_TEMP
     - ROLLED_BACK or FAILED_TEMP
     -
     - X

.. note::
    | In some cases, Rollback of Change external connectivity cannot recover
      the IP address and Port Id of virtual resources.
    | If the operation fails before performing VIM processing: updating stack,
      the IP address and Port Id will be recovered by its rollback operation.
    | Otherwise, dynamic IP address and Port Id are not recovered
      by rollback operation.

This manual describes the following operations as use cases for
rollback operations.

* "Instantiate VNF" fails
* Rollback VNF lifecycle management operation
* Delete VNF

As shown below, if "Instantiate VNF" fails, "Delete VNF" cannot be executed
without executing "Rollback VNF lifecycle management operation".

.. code-block:: console

  $ openstack vnflcm delete VNF_INSTANCE_ID


Result:

.. code-block:: console

  Failed to delete vnf instance with ID '3aa5c054-c162-4d5e-9808-0bc30f92a4c7': Vnf 3aa5c054-c162-4d5e-9808-0bc30f92a4c7 in status ERROR. Cannot delete while the vnf is in this state.


Therefore, "Rollback VNF lifecycle management operation" with
the following CLI command.

.. code-block:: console

  $ openstack vnflcm op rollback VNF_LCM_OP_OCC_ID


Result:

.. code-block:: console

  Rollback request for LCM operation 304538dd-d754-4661-9f17-5496dab9693d has been accepted


If "Rollback VNF lifecycle management operation" is successful,
then "Delete VNF" is also successful.

.. code-block:: console

  $ openstack vnflcm delete VNF_INSTANCE_ID


Result:

.. code-block:: console

  Vnf instance '3aa5c054-c162-4d5e-9808-0bc30f92a4c7' deleted successfully


Fail VNF LCM Operation
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 10 40 15 15 10 10
   :header-rows: 1

   * - LCM Operation
     - Description of Fail
     - Precondition
     - Postcondition
     - Support in v1
     - Support in v2
   * - Instantiate
     - Tacker simply changes LCM operation state to "FAILED" on Tacker-DB.
     - FAILED_TEMP
     - FAILED
     - X
     - X
   * - Terminate
     - Tacker simply changes LCM operation state to "FAILED" on Tacker-DB.
     - FAILED_TEMP
     - FAILED
     - X
     - X
   * - Heal
     - Tacker simply changes LCM operation state to "FAILED" on Tacker-DB.
     - FAILED_TEMP
     - FAILED
     - X
     - X
   * - Scale
     - Tacker simply changes LCM operation state to "FAILED" on Tacker-DB.
     - FAILED_TEMP
     - FAILED
     - X
     - X
   * - Modify
     - Tacker simply changes LCM operation state to "FAILED" on Tacker-DB.
     - FAILED_TEMP
     - FAILED
     - X
     - X
   * - Change external connectivity
     - Tacker simply changes LCM operation state to "FAILED" on Tacker-DB.
     - FAILED_TEMP
     - FAILED
     - X
     - X

This manual describes the following operations as use cases for
fail operations.

* "Instantiate VNF" fails
* Fail VNF lifecycle management operation
* Delete VNF

As shown below, if "Instantiate VNF" fails, "Delete VNF" cannot be executed
after executing "Fail VNF lifecycle management operation".

.. code-block:: console

  $ openstack vnflcm delete VNF_INSTANCE_ID


Result:

.. code-block:: console

  Failed to delete vnf instance with ID '3aa5c054-c162-4d5e-9808-0bc30f92a4c7': Vnf 3aa5c054-c162-4d5e-9808-0bc30f92a4c7 in status ERROR. Cannot delete while the vnf is in this state.


Therefore, "Fail VNF lifecycle management operation" with
the following CLI command.

.. code-block:: console

  $ openstack vnflcm op fail VNF_LCM_OP_OCC_ID


Result:

.. code-block:: console

  Fail request for LCM operation 304538dd-d754-4661-9f17-5496dab9693d has been accepted


If "Fail VNF lifecycle management operation" is successful,
then "Delete VNF" is also successful.

.. code-block:: console

  $ openstack vnflcm delete VNF_INSTANCE_ID


Result:

.. code-block:: console

  Vnf instance '3aa5c054-c162-4d5e-9808-0bc30f92a4c7' deleted successfully


Retry VNF LCM Operation
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 10 40 15 15 10 10
   :header-rows: 1

   * - LCM Operation
     - Description of Fail
     - Precondition
     - Postcondition
     - Support in v1
     - Support in v2
   * - Instantiate
     - VNFM retries a Instantiate operation.
     - FAILED_TEMP
     - COMPLETED or FAILED_TEMP
     - X
     - X
   * - Terminate
     - VNFM retries a Terminate operation.
     - FAILED_TEMP
     - COMPLETED or FAILED_TEMP
     - X
     - X
   * - Heal
     - VNFM retries a Heal operation.
     - FAILED_TEMP
     - COMPLETED or FAILED_TEMP
     - X
     - X
   * - Scale
     - VNFM retries a Scale operation.
     - FAILED_TEMP
     - COMPLETED or FAILED_TEMP
     - X
     - X
   * - Modify
     - VNFM retries a Modify operation.
     - FAILED_TEMP
     - COMPLETED or FAILED_TEMP
     - X
     - X
   * - Change external connectivity
     - VNFM retries a Change external connectivity operation.
     - FAILED_TEMP
     - COMPLETED or FAILED_TEMP
     - X
     - X

This manual describes the following operations as use cases for
retry operations.

* "Instantiate VNF" fails
* Retry VNF lifecycle management operation

As shown below, if "Instantiate VNF" fails, If you want re-execute
previous(failed) operation , you execute "Retry" operation.

Therefore, "Retry VNF lifecycle management operation" with
the following CLI command.

.. code-block:: console

  $ openstack vnflcm op retry VNF_LCM_OP_OCC_ID


Result:

.. code-block:: console

  Retry request for LCM operation 304538dd-d754-4661-9f17-5496dab9693d has been accepted


If "Retry VNF lifecycle management operation" is successful,
then another LCM can be operational.

.. _VNF LCM v1 API : https://docs.openstack.org/api-ref/nfv-orchestration/v1/vnflcm.html
.. _VNF LCM v2 API : https://docs.openstack.org/api-ref/nfv-orchestration/v2/vnflcm.html
.. _Keystone API reference : https://docs.openstack.org/api-ref/identity/v3/#password-authentication-with-scoped-authorization

