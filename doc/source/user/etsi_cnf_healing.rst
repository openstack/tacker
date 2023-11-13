========================
ETSI NFV-SOL CNF Healing
========================

This document describes how to heal CNF in Tacker v1 API.

.. note::

  This is a document for Tacker v1 API.
  See :doc:`/user/v2/cnf/heal/index` for Tacker v2 API.


Overview
--------

The diagram below shows an overview of the CNF healing.

1. Request heal VNF

   A user requests tacker-server to heal a VNF or all VNFs with tacker-client
   by requesting ``heal VNF``.

2. Call Kubernetes API

   Upon receiving a request from tacker-client, tacker-server redirects it to
   tacker-conductor. In tacker-conductor, the request is redirected again to
   an appropriate infra-driver (in this case Kubernetes infra-driver) according
   to the contents of the instantiate parameters. Then, Kubernetes
   infra-driver calls Kubernetes APIs.

3. Re-create Pods

   Kubernetes Master re-creates Pods according to the API calls.

.. figure:: /_images/etsi_cnf_healing.png


Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

The procedure of prepare for healing operation that from "register VIM" to
"Instantiate VNF", basically refer to
:doc:`/user/etsi_containerized_vnf_usage_guide`.

This procedure uses an example using the sample VNF package.


How to Create VNF Package for Healing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Using `samples/tests/etc/samples/etsi/nfv/test_cnf_heal`_,
describe how to create VNF package for healing.

.. code-block:: console

    $ cd samples/tests/etc/samples/etsi/nfv/test_cnf_heal

Download official definition files from ETSI NFV.
ETSI GS NFV-SOL 001 [i.4] specifies the structure and format of the VNFD based
on TOSCA specifications.

.. code-block:: console

  $ cd Definitions
  $ wget https://forge.etsi.org/rep/nfv/SOL001/raw/v2.6.1/etsi_nfv_sol001_common_types.yaml
  $ wget https://forge.etsi.org/rep/nfv/SOL001/raw/v2.6.1/etsi_nfv_sol001_vnfd_types.yaml


CSAR Package should be compressed into a ZIP file for uploading.
Following commands are an example of compressing a VNF Package:

.. code-block:: console

  $ cd -
  $ zip deployment.zip -r Definitions/ Files/ TOSCA-Metadata/
  $ ls
  Definitions  deployment.zip  Files  TOSCA-Metadata


After creating a vnf package with :command:`openstack vnf package create`,
some information including ID, Links,
Onboarding State, Operational State, and Usage State will be returned.
When the Onboarding State is CREATED, the Operational State is DISABLED,
and the Usage State is NOT_IN_USE, indicate the creation is successful.


.. code-block:: console

  $ openstack vnf package create
  +-------------------+-------------------------------------------------------------------------------------------------+
  | Field             | Value                                                                                           |
  +-------------------+-------------------------------------------------------------------------------------------------+
  | ID                | 094c8abf-b5c8-45a1-9332-3952a710c65c                                                            |
  | Links             | {                                                                                               |
  |                   |     "self": {                                                                                   |
  |                   |         "href": "/vnfpkgm/v1/vnf_packages/094c8abf-b5c8-45a1-9332-3952a710c65c"                 |
  |                   |     },                                                                                          |
  |                   |     "packageContent": {                                                                         |
  |                   |         "href": "/vnfpkgm/v1/vnf_packages/094c8abf-b5c8-45a1-9332-3952a710c65c/package_content" |
  |                   |     }                                                                                           |
  |                   | }                                                                                               |
  | Onboarding State  | CREATED                                                                                         |
  | Operational State | DISABLED                                                                                        |
  | Usage State       | NOT_IN_USE                                                                                      |
  | User Defined Data | {}                                                                                              |
  +-------------------+-------------------------------------------------------------------------------------------------+


Upload the CSAR zip file to the VNF Package by running the following command
:command:`openstack vnf package upload --path <path of vnf package> <vnf package ID>`.
Here is an example of uploading VNF package:

.. code-block:: console

  $ openstack vnf package upload --path deployment.zip 094c8abf-b5c8-45a1-9332-3952a710c65c
  Upload request for VNF package 094c8abf-b5c8-45a1-9332-3952a710c65c has been accepted.


Create VNF instance by running :command:`openstack vnflcm create <VNFD ID>`.

Here is an example of creating VNF :

.. code-block:: console

  $ openstack vnflcm create b1bb0ce7-ebca-4fa7-95ed-4840d70a1177
  +-----------------------------+------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                            |
  +-----------------------------+------------------------------------------------------------------------------------------------------------------+
  | ID                          | 2a9a1197-953b-4f0a-b510-5ab4ab979959                                                                             |
  | Instantiation State         | NOT_INSTANTIATED                                                                                                 |
  | Links                       | {                                                                                                                |
  |                             |     "self": {                                                                                                    |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/2a9a1197-953b-4f0a-b510-5ab4ab979959"             |
  |                             |     },                                                                                                           |
  |                             |     "instantiate": {                                                                                             |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/2a9a1197-953b-4f0a-b510-5ab4ab979959/instantiate" |
  |                             |     }                                                                                                            |
  |                             | }                                                                                                                |
  | VNF Configurable Properties |                                                                                                                  |
  | VNF Instance Description    |                                                                                                                  |
  | VNF Instance Name           | vnf-2a9a1197-953b-4f0a-b510-5ab4ab979959                                                                         |
  | VNF Product Name            | Sample VNF                                                                                                       |
  | VNF Provider                | Company                                                                                                          |
  | VNF Software Version        | 1.0                                                                                                              |
  | VNFD ID                     | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177                                                                             |
  | VNFD Version                | 1.0                                                                                                              |
  | vnfPkgId                    |                                                                                                                  |
  +-----------------------------+------------------------------------------------------------------------------------------------------------------+


After the command is executed, instantiate VNF.
Instantiate VNF by running the following command
:command:`openstack vnflcm instantiate <VNF instance ID> <json file>`.

The following example shows a json file that deploys the Kubernetes resources
described in ``deployment_heal_simple.yaml``. Please note that ``additionalParams``
includes path of Kubernetes resource definition file and that
``lcm-kubernetes-def-files`` should be a list.


.. code-block:: console

  $ cat ./instance_kubernetes.json
  {
    "flavourId": "simple",
    "additionalParams": {
      "lcm-kubernetes-def-files": [
        "Files/kubernetes/deployment_heal_simple.yaml"
      ]
    },
    "vimConnectionInfo": [
      {
        "id": "8a3adb69-0784-43c7-833e-aab0b6ab4470",
        "vimId": "43176042-ca97-4954-9bd5-0a9c054885e1",
        "vimType": "kubernetes"
      }
    ]
  }
  $ openstack vnflcm instantiate 2a9a1197-953b-4f0a-b510-5ab4ab979959 instance_kubernetes.json
  Instantiate request for VNF Instance 2a9a1197-953b-4f0a-b510-5ab4ab979959 has been accepted.


CNF Healing Procedure
---------------------

As mentioned in Prerequisites and Healing target VNF instance, the VNF must be
instantiated before healing.

Details of CLI commands are described in :doc:`/cli/cli-etsi-vnflcm`.

There are two main methods for CNF healing.

* Healing of the entire VNF

  Heal entire VNF instance by termination and instantiation of the VNF.

* Healing specified with VNFC instances

  Heal Pod (mapped as VNFC) that is singleton or created using controller
  resources of Kubernetes such as Deployment, DaemonSet, StatefulSet and
  ReplicaSet.

.. note::

  A VNFC is a 'VNF Component', and one VNFC basically corresponds to
  one VDU in the VNF. For more information on VNFC, see
  `NFV-SOL002 v2.6.1`_.


Healing Target VNF Instance
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Assuming that the following VNF instance exists. VNF Instance is made by using
`samples/tests/etc/samples/etsi/nfv/test_cnf_heal`_.
This instance will be healed.

.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID


Result:

.. code-block:: console

  +-----------------------------+----------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------+
  | ID                          | 2a9a1197-953b-4f0a-b510-5ab4ab979959                                                                                 |
  | Instantiated Vnf Info       | {                                                                                                                    |
  |                             |     "flavourId": "simple",                                                                                           |
  |                             |     "vnfState": "STARTED",                                                                                           |
  |                             |     "scaleStatus": [                                                                                                 |
  |                             |         {                                                                                                            |
  |                             |             "aspectId": "vdu1_aspect",                                                                               |
  |                             |             "scaleLevel": 0                                                                                          |
  |                             |         }                                                                                                            |
  |                             |     ],                                                                                                               |
  |                             |     "extCpInfo": [],                                                                                                 |
  |                             |     "vnfcResourceInfo": [                                                                                            |
  |                             |         {                                                                                                            |
  |                             |             "id": "da087f50-521a-4f71-a3e4-3464a196d4e6",                                                            |
  |                             |             "vduId": "VDU1",                                                                                         |
  |                             |             "computeResource": {                                                                                     |
  |                             |                 "vimConnectionId": null,                                                                             |
  |                             |                 "resourceId": "vdu1-heal-simple-6d649fd6f7-dcjpn",                                                   |
  |                             |                 "vimLevelResourceType": "Deployment"                                                                 |
  |                             |             },                                                                                                       |
  |                             |             "storageResourceIds": []                                                                                 |
  |                             |         },                                                                                                           |
  |                             |         {                                                                                                            |
  |                             |             "id": "4e66f5d3-a4c5-4025-8ad8-6ad21414cffa",                                                            |
  |                             |             "vduId": "VDU1",                                                                                         |
  |                             |             "computeResource": {                                                                                     |
  |                             |                 "vimConnectionId": null,                                                                             |
  |                             |                 "resourceId": "vdu1-heal-simple-6d649fd6f7-hmsbh",                                                   |
  |                             |                 "vimLevelResourceType": "Deployment"                                                                 |
  |                             |             },                                                                                                       |
  |                             |             "storageResourceIds": []                                                                                 |
  |                             |         }                                                                                                            |
  |                             |     ],                                                                                                               |
  |                             |     "additionalParams": {                                                                                            |
  |                             |         "lcm-kubernetes-def-files": [                                                                                |
  |                             |             "Files/kubernetes/deployment_heal_simple.yaml"                                                           |
  |                             |         ]                                                                                                            |
  |                             |     }                                                                                                                |
  |                             | }                                                                                                                    |
  | Instantiation State         | INSTANTIATED                                                                                                         |
  | Links                       | {                                                                                                                    |
  |                             |     "self": {                                                                                                        |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/2a9a1197-953b-4f0a-b510-5ab4ab979959"                 |
  |                             |     },                                                                                                               |
  |                             |     "terminate": {                                                                                                   |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/2a9a1197-953b-4f0a-b510-5ab4ab979959/terminate"       |
  |                             |     },                                                                                                               |
  |                             |     "heal": {                                                                                                        |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/2a9a1197-953b-4f0a-b510-5ab4ab979959/heal"            |
  |                             |     },                                                                                                               |
  |                             |     "changeExtConn": {                                                                                               |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/2a9a1197-953b-4f0a-b510-5ab4ab979959/change_ext_conn" |
  |                             |     }                                                                                                                |
  |                             | }                                                                                                                    |
  | VIM Connection Info         | [                                                                                                                    |
  |                             |     {                                                                                                                |
  |                             |         "id": "8a3adb69-0784-43c7-833e-aab0b6ab4470",                                                                |
  |                             |         "vimId": "43176042-ca97-4954-9bd5-0a9c054885e1",                                                             |
  |                             |         "vimType": "kubernetes",                                                                                     |
  |                             |         "interfaceInfo": {},                                                                                         |
  |                             |         "accessInfo": {},                                                                                            |
  |                             |         "extra": {}                                                                                                  |
  |                             |     },                                                                                                               |
  |                             |     {                                                                                                                |
  |                             |         "id": "f1e70f72-0e1f-427e-a672-b447d45ee52e",                                                                |
  |                             |         "vimId": "43176042-ca97-4954-9bd5-0a9c054885e1",                                                             |
  |                             |         "vimType": "kubernetes",                                                                                     |
  |                             |         "interfaceInfo": {},                                                                                         |
  |                             |         "accessInfo": {},                                                                                            |
  |                             |         "extra": {}                                                                                                  |
  |                             |     }                                                                                                                |
  |                             | ]                                                                                                                    |
  | VNF Configurable Properties |                                                                                                                      |
  | VNF Instance Description    |                                                                                                                      |
  | VNF Instance Name           | vnf-2a9a1197-953b-4f0a-b510-5ab4ab979959                                                                             |
  | VNF Product Name            | Sample VNF                                                                                                           |
  | VNF Provider                | Company                                                                                                              |
  | VNF Software Version        | 1.0                                                                                                                  |
  | VNFD ID                     | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177                                                                                 |
  | VNFD Version                | 1.0                                                                                                                  |
  | metadata                    | namespace=default, tenant=default                                                                                    |
  | vnfPkgId                    |                                                                                                                      |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------+


How to Heal of the Entire VNF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute Heal of the entire CNF with CLI command and check the name and age of
pod information before and after healing.
This is to confirm that the name has changed and age has been new after heal.

Pod information before heal:

.. code-block:: console

  $ kubectl get pod
  NAME                                READY   STATUS    RESTARTS   AGE
  vdu1-heal-simple-6d649fd6f7-dcjpn   1/1     Running   0          11m
  vdu1-heal-simple-6d649fd6f7-hmsbh   1/1     Running   0          11m


Heal entire VNF can be executed by the following CLI command.

.. code-block:: console

  $ openstack vnflcm heal VNF_INSTANCE_ID


Result:

.. code-block:: console

  Heal request for VNF Instance 2a9a1197-953b-4f0a-b510-5ab4ab979959 has been accepted.


Pod information after heal:

.. code-block:: console

  $ kubectl get pod
  NAME                                READY   STATUS    RESTARTS   AGE
  vdu1-heal-simple-6d649fd6f7-2wvxj   1/1     Running   0          17s
  vdu1-heal-simple-6d649fd6f7-tj4vx   1/1     Running   0          17s


All ``vnfcResourceInfo`` in ``Instantiated Vnf Info`` will be updated from
the VNF Instance displayed in `Healing Target VNF Instance`_.

.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID


Result:

.. code-block:: console

  +-----------------------------+----------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------+
  | ID                          | 2a9a1197-953b-4f0a-b510-5ab4ab979959                                                                                 |
  | Instantiated Vnf Info       | {                                                                                                                    |
  |                             |     "flavourId": "simple",                                                                                           |
  |                             |     "vnfState": "STARTED",                                                                                           |
  |                             |     "scaleStatus": [                                                                                                 |
  |                             |         {                                                                                                            |
  |                             |             "aspectId": "vdu1_aspect",                                                                               |
  |                             |             "scaleLevel": 0                                                                                          |
  |                             |         }                                                                                                            |
  |                             |     ],                                                                                                               |
  |                             |     "extCpInfo": [],                                                                                                 |
  |                             |     "vnfcResourceInfo": [                                                                                            |
  |                             |         {                                                                                                            |
  |                             |             "id": "63a16aa7-ab36-4bfb-a6e3-724636155c4f",                                                            |
  |                             |             "vduId": "VDU1",                                                                                         |
  |                             |             "computeResource": {                                                                                     |
  |                             |                 "vimConnectionId": null,                                                                             |
  |                             |                 "resourceId": "vdu1-heal-simple-6d649fd6f7-2wvxj",                                                   |
  |                             |                 "vimLevelResourceType": "Deployment"                                                                 |
  |                             |             },                                                                                                       |
  |                             |             "storageResourceIds": []                                                                                 |
  |                             |         },                                                                                                           |
  |                             |         {                                                                                                            |
  |                             |             "id": "ca211f05-2509-4abf-b6f2-a553d18a6863",                                                            |
  |                             |             "vduId": "VDU1",                                                                                         |
  |                             |             "computeResource": {                                                                                     |
  |                             |                 "vimConnectionId": null,                                                                             |
  |                             |                 "resourceId": "vdu1-heal-simple-6d649fd6f7-tj4vx",                                                   |
  |                             |                 "vimLevelResourceType": "Deployment"                                                                 |
  |                             |             },                                                                                                       |
  |                             |             "storageResourceIds": []                                                                                 |
  |                             |         }                                                                                                            |
  |                             |     ],                                                                                                               |
  |                             |     "additionalParams": {                                                                                            |
  |                             |         "lcm-kubernetes-def-files": [                                                                                |
  |                             |             "Files/kubernetes/deployment_heal_simple.yaml"                                                           |
  |                             |         ]                                                                                                            |
  |                             |     }                                                                                                                |
  |                             | }                                                                                                                    |
  | Instantiation State         | INSTANTIATED                                                                                                         |
  | Links                       | {                                                                                                                    |
  |                             |     "self": {                                                                                                        |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/2a9a1197-953b-4f0a-b510-5ab4ab979959"                 |
  |                             |     },                                                                                                               |
  |                             |     "terminate": {                                                                                                   |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/2a9a1197-953b-4f0a-b510-5ab4ab979959/terminate"       |
  |                             |     },                                                                                                               |
  |                             |     "heal": {                                                                                                        |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/2a9a1197-953b-4f0a-b510-5ab4ab979959/heal"            |
  |                             |     },                                                                                                               |
  |                             |     "changeExtConn": {                                                                                               |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/2a9a1197-953b-4f0a-b510-5ab4ab979959/change_ext_conn" |
  |                             |     }                                                                                                                |
  |                             | }                                                                                                                    |
  | VIM Connection Info         | [                                                                                                                    |
  |                             |     {                                                                                                                |
  |                             |         "id": "8a3adb69-0784-43c7-833e-aab0b6ab4470",                                                                |
  |                             |         "vimId": "43176042-ca97-4954-9bd5-0a9c054885e1",                                                             |
  |                             |         "vimType": "kubernetes",                                                                                     |
  |                             |         "interfaceInfo": {},                                                                                         |
  |                             |         "accessInfo": {},                                                                                            |
  |                             |         "extra": {}                                                                                                  |
  |                             |     },                                                                                                               |
  |                             |     {                                                                                                                |
  |                             |         "id": "f1e70f72-0e1f-427e-a672-b447d45ee52e",                                                                |
  |                             |         "vimId": "43176042-ca97-4954-9bd5-0a9c054885e1",                                                             |
  |                             |         "vimType": "kubernetes",                                                                                     |
  |                             |         "interfaceInfo": {},                                                                                         |
  |                             |         "accessInfo": {},                                                                                            |
  |                             |         "extra": {}                                                                                                  |
  |                             |     }                                                                                                                |
  |                             | ]                                                                                                                    |
  | VNF Configurable Properties |                                                                                                                      |
  | VNF Instance Description    |                                                                                                                      |
  | VNF Instance Name           | vnf-2a9a1197-953b-4f0a-b510-5ab4ab979959                                                                             |
  | VNF Product Name            | Sample VNF                                                                                                           |
  | VNF Provider                | Company                                                                                                              |
  | VNF Software Version        | 1.0                                                                                                                  |
  | VNFD ID                     | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177                                                                                 |
  | VNFD Version                | 1.0                                                                                                                  |
  | metadata                    | namespace=default, tenant=default                                                                                    |
  | vnfPkgId                    |                                                                                                                      |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------+


How to Heal Specified with VNFC Instances
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute Heal of the partial CNF CLI command and check the name and age of pod
information before and after healing.
This is to confirm that the name has changed and age has been new after heal.

Pod information before heal:

.. code-block:: console

  $ kubectl get pod
  NAME                                READY   STATUS    RESTARTS   AGE
  vdu1-heal-simple-6d649fd6f7-dcjpn   1/1     Running   0          22m
  vdu1-heal-simple-6d649fd6f7-hmsbh   1/1     Running   0          22m


Heal specified with VNFC instances can be executed by running
:command:`openstack vnflcm heal VNF_INSTANCE_ID --vnfc-instance VNFC_INSTANCE_ID`.

In the example of this procedure, specify the ID
``da087f50-521a-4f71-a3e4-3464a196d4e6`` of the first ``vnfcResourceInfo`` as
``VNFC_INSTANCE_ID``.


.. code-block:: console

  $ openstack vnflcm heal 2a9a1197-953b-4f0a-b510-5ab4ab979959 --vnfc-instance da087f50-521a-4f71-a3e4-3464a196d4e6


Result:

.. code-block:: console

  Heal request for VNF Instance 2a9a1197-953b-4f0a-b510-5ab4ab979959 has been accepted.


Pod information after heal:

.. code-block:: console

  $ kubectl get pod
  NAME                                READY   STATUS    RESTARTS   AGE
  vdu1-heal-simple-6d649fd6f7-2wvxj   1/1     Running   0          13s
  vdu1-heal-simple-6d649fd6f7-hmsbh   1/1     Running   0          22m


Only the ``resourceId`` of target ``vnfcResourceInfo`` in
``Instantiated Vnf Info`` will be updated from the VNF Instance displayed in
`Healing Target VNF Instance`_.

.. code-block:: console

  $ openstack vnflcm show VNF_INSTANCE_ID


Result:

.. code-block:: console

  +-----------------------------+----------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------+
  | ID                          | 2a9a1197-953b-4f0a-b510-5ab4ab979959                                                                                 |
  | Instantiated Vnf Info       | {                                                                                                                    |
  |                             |     "flavourId": "simple",                                                                                           |
  |                             |     "vnfState": "STARTED",                                                                                           |
  |                             |     "scaleStatus": [                                                                                                 |
  |                             |         {                                                                                                            |
  |                             |             "aspectId": "vdu1_aspect",                                                                               |
  |                             |             "scaleLevel": 0                                                                                          |
  |                             |         }                                                                                                            |
  |                             |     ],                                                                                                               |
  |                             |     "extCpInfo": [],                                                                                                 |
  |                             |     "vnfcResourceInfo": [                                                                                            |
  |                             |         {                                                                                                            |
  |                             |             "id": "da087f50-521a-4f71-a3e4-3464a196d4e6",                                                            |
  |                             |             "vduId": "VDU1",                                                                                         |
  |                             |             "computeResource": {                                                                                     |
  |                             |                 "vimConnectionId": null,                                                                             |
  |                             |                 "resourceId": "vdu1-heal-simple-6d649fd6f7-2wvxj",                                                   |
  |                             |                 "vimLevelResourceType": "Deployment"                                                                 |
  |                             |             },                                                                                                       |
  |                             |             "storageResourceIds": []                                                                                 |
  |                             |         },                                                                                                           |
  |                             |         {                                                                                                            |
  |                             |             "id": "4e66f5d3-a4c5-4025-8ad8-6ad21414cffa",                                                            |
  |                             |             "vduId": "VDU1",                                                                                         |
  |                             |             "computeResource": {                                                                                     |
  |                             |                 "vimConnectionId": null,                                                                             |
  |                             |                 "resourceId": "vdu1-heal-simple-6d649fd6f7-hmsbh",                                                   |
  |                             |                 "vimLevelResourceType": "Deployment"                                                                 |
  |                             |             },                                                                                                       |
  |                             |             "storageResourceIds": []                                                                                 |
  |                             |         }                                                                                                            |
  |                             |     ],                                                                                                               |
  |                             |     "additionalParams": {                                                                                            |
  |                             |         "lcm-kubernetes-def-files": [                                                                                |
  |                             |             "Files/kubernetes/deployment_heal_simple.yaml"                                                           |
  |                             |         ]                                                                                                            |
  |                             |     }                                                                                                                |
  |                             | }                                                                                                                    |
  | Instantiation State         | INSTANTIATED                                                                                                         |
  | Links                       | {                                                                                                                    |
  |                             |     "self": {                                                                                                        |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/2a9a1197-953b-4f0a-b510-5ab4ab979959"                 |
  |                             |     },                                                                                                               |
  |                             |     "terminate": {                                                                                                   |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/2a9a1197-953b-4f0a-b510-5ab4ab979959/terminate"       |
  |                             |     },                                                                                                               |
  |                             |     "heal": {                                                                                                        |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/2a9a1197-953b-4f0a-b510-5ab4ab979959/heal"            |
  |                             |     },                                                                                                               |
  |                             |     "changeExtConn": {                                                                                               |
  |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/2a9a1197-953b-4f0a-b510-5ab4ab979959/change_ext_conn" |
  |                             |     }                                                                                                                |
  |                             | }                                                                                                                    |
  | VIM Connection Info         | [                                                                                                                    |
  |                             |     {                                                                                                                |
  |                             |         "id": "8a3adb69-0784-43c7-833e-aab0b6ab4470",                                                                |
  |                             |         "vimId": "43176042-ca97-4954-9bd5-0a9c054885e1",                                                             |
  |                             |         "vimType": "kubernetes",                                                                                     |
  |                             |         "interfaceInfo": {},                                                                                         |
  |                             |         "accessInfo": {},                                                                                            |
  |                             |         "extra": {}                                                                                                  |
  |                             |     },                                                                                                               |
  |                             |     {                                                                                                                |
  |                             |         "id": "f1e70f72-0e1f-427e-a672-b447d45ee52e",                                                                |
  |                             |         "vimId": "43176042-ca97-4954-9bd5-0a9c054885e1",                                                             |
  |                             |         "vimType": "kubernetes",                                                                                     |
  |                             |         "interfaceInfo": {},                                                                                         |
  |                             |         "accessInfo": {},                                                                                            |
  |                             |         "extra": {}                                                                                                  |
  |                             |     }                                                                                                                |
  |                             | ]                                                                                                                    |
  | VNF Configurable Properties |                                                                                                                      |
  | VNF Instance Description    |                                                                                                                      |
  | VNF Instance Name           | vnf-2a9a1197-953b-4f0a-b510-5ab4ab979959                                                                             |
  | VNF Product Name            | Sample VNF                                                                                                           |
  | VNF Provider                | Company                                                                                                              |
  | VNF Software Version        | 1.0                                                                                                                  |
  | VNFD ID                     | b1bb0ce7-ebca-4fa7-95ed-4840d70a1177                                                                                 |
  | VNFD Version                | 1.0                                                                                                                  |
  | metadata                    | namespace=default, tenant=default                                                                                    |
  | vnfPkgId                    |                                                                                                                      |
  +-----------------------------+----------------------------------------------------------------------------------------------------------------------+


History of Checks
-----------------

The content of this document has been confirmed to work
using the following VNF Package.

* `test_cnf_heal for 2023.2 Bobcat`_


.. _samples/tests/etc/samples/etsi/nfv/test_cnf_heal:
  https://opendev.org/openstack/tacker/src/branch/master/samples/tests/etc/samples/etsi/nfv/test_cnf_heal
.. _NFV-SOL002 v2.6.1: https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/002/02.06.01_60/gs_nfv-sol002v020601p.pdf
.. _test_cnf_heal for 2023.2 Bobcat:
  https://opendev.org/openstack/tacker/src/branch/stable/2023.2/tacker/tests/etc/samples/etsi/nfv/test_cnf_heal
