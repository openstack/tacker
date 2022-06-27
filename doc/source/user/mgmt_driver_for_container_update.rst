========================================
ETSI NFV-SOL CNF Update with Mgmt Driver
========================================

This document describes how to update CNF with Mgmt Driver in Tacker.

Overview
--------

The diagram below shows an overview of the CNF updating.

1. Request update VNF

   A user requests tacker-server to update a CNF with tacker-client
   by requesting ``update VNF`` as a Modify VNF information operation.

2. Call Kubernetes API

   Upon receiving a request from tacker-client, tacker-server redirects it to
   tacker-conductor. In tacker-conductor, the request is redirected again to
   the matching Mgmt Driver (in this case the Mgmt Driver of container update)
   according to the contents of the VNFD in the VNF Package. Then, Mgmt Driver
   calls Kubernetes APIs.

3. Update resources

   Kubernetes Master update resources according to the API calls.

.. figure:: ../_images/mgmt_driver_for_container_update.png
    :align: left

Mgmt Driver Introduction
~~~~~~~~~~~~~~~~~~~~~~~~

Mgmt Driver enables Users to configure their VNF before and/or after
its VNF Lifecycle Management operation. Users can customize the logic
of Mgmt Driver by implementing their own Mgmt Driver and these
customizations are specified by "interface" definition in
`NFV-SOL001 v2.6.1`_.

The Mgmt Driver in this user guide supports updating CNF with
``modify_information_start`` and ``modify_information_end`` operation.

Use Cases
~~~~~~~~~

In this user guide, the provided sample VNF Packages will be instantiated
and then updated. The sample Mgmt Driver will update resources on
Kubernetes during update. Update the ConfigMap and Secret, and also
update the image in the Pod and Deployment, and other resources will
not change.

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

After installing the above packages, you also need to import the sample
Mgmt Driver file. You can refer to `Set Tacker Configuration`_ in
`How to use Mgmt Driver for deploying Kubernetes Cluster`_ for usage of
Mgmt Driver file.

.. note::

    You can find sample Mgmt Driver file in the following path.
    `samples/mgmt_driver/kubernetes/container_update/container_update_mgmt.py`_

You can also refer to :doc:`./etsi_containerized_vnf_usage_guide` for the
procedure of preparation from "`Prepare Kubernetes VIM`_" to
"`Instantiate VNF`_".

How to Instantiate VNF for Updating
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use the sample VNF package below to instantiate VNF to be updated.

.. note::

    In this document, ``TACKER_ROOT`` is the root of tacker’s repository on
    the server.

.. code-block:: console

    $ cd TACKER_ROOT/tacker/tests/etc/samples/etsi/nfv/test_cnf_container_update_before

Copy the official definition files from the sample directory.
`ETSI GS NFV-SOL 001`_ specifies the structure and format of the VNFD
based on TOSCA specifications.

.. code-block:: console

    $ cd TACKER_ROOT/tacker/tests/etc/samples/etsi/nfv/test_cnf_container_update_before
    $ cp TACKER_ROOT/samples/vnf_packages/Definitions/etsi_nfv_sol001_common_types.yaml Definitions/
    $ cp TACKER_ROOT/samples/vnf_packages/Definitions/etsi_nfv_sol001_vnfd_types.yaml Definitions/

CSAR Package should be compressed into a ZIP file for uploading.
Following commands are an example of compressing a VNF Package:

.. note::

    The sample Mgmt Driver file also needs to be copied into the CSAR Package.

.. code-block:: console

    $ cd TACKER_ROOT/tacker/tests/etc/samples/etsi/nfv/test_cnf_container_update_before
    $ mkdir Scripts
    $ cp TACKER_ROOT/samples/mgmt_driver/kubernetes/container_update/container_update_mgmt.py Scripts/
    $ zip deployment.zip -r Definitions/ Files/ TOSCA-Metadata/ Scripts/

After creating a VNF package with :command:`openstack vnf package create`,
When the Onboarding State is CREATED, the Operational
State is DISABLED, and the Usage State is NOT_IN_USE, indicate the creation is
successful.

.. code-block:: console

  $ openstack vnf package create
    +-------------------+-------------------------------------------------------------------------------------------------+
    | Field             | Value                                                                                           |
    +-------------------+-------------------------------------------------------------------------------------------------+
    | ID                | d80b1025-7309-4dbc-8310-f51a24045b08                                                            |
    | Links             | {                                                                                               |
    |                   |     "self": {                                                                                   |
    |                   |         "href": "/vnfpkgm/v1/vnf_packages/d80b1025-7309-4dbc-8310-f51a24045b08"                 |
    |                   |     },                                                                                          |
    |                   |     "packageContent": {                                                                         |
    |                   |         "href": "/vnfpkgm/v1/vnf_packages/d80b1025-7309-4dbc-8310-f51a24045b08/package_content" |
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

  $ openstack vnf package upload --path deployment.zip d80b1025-7309-4dbc-8310-f51a24045b08
    Upload request for VNF package d80b1025-7309-4dbc-8310-f51a24045b08 has been accepted.

Create VNF instance by running :command:`openstack vnflcm create <VNFD ID>`.

.. note::

    The VNFD ID could be found by
    :command:`openstack vnf package show <vnf package ID>` command.

Here is an example of creating VNF :

.. code-block:: console

  $ openstack vnflcm create b1bb0ce7-ebca-4fa7-95ed-4840d70a7774
    +-----------------------------+------------------------------------------------------------------------------------------------------------------+
    | Field                       | Value                                                                                                            |
    +-----------------------------+------------------------------------------------------------------------------------------------------------------+
    | ID                          | f21814f0-3e00-4651-a9ac-ec10f3248c19                                                                             |
    | Instantiation State         | NOT_INSTANTIATED                                                                                                 |
    | Links                       | {                                                                                                                |
    |                             |     "self": {                                                                                                    |
    |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/f21814f0-3e00-4651-a9ac-ec10f3248c19"             |
    |                             |     },                                                                                                           |
    |                             |     "instantiate": {                                                                                             |
    |                             |         "href": "http://localhost:9890/vnflcm/v1/vnf_instances/f21814f0-3e00-4651-a9ac-ec10f3248c19/instantiate" |
    |                             |     }                                                                                                            |
    |                             | }                                                                                                                |
    | VNF Configurable Properties |                                                                                                                  |
    | VNF Instance Description    | None                                                                                                             |
    | VNF Instance Name           | vnf-f21814f0-3e00-4651-a9ac-ec10f3248c19                                                                         |
    | VNF Product Name            | Sample VNF                                                                                                       |
    | VNF Provider                | Company                                                                                                          |
    | VNF Software Version        | 1.0                                                                                                              |
    | VNFD ID                     | b1bb0ce7-ebca-4fa7-95ed-4840d70a7774                                                                             |
    | VNFD Version                | 1.0                                                                                                              |
    | vnfPkgId                    |                                                                                                                  |
    +-----------------------------+------------------------------------------------------------------------------------------------------------------+

The following example shows the yaml files that deploys the Kubernetes
resources.
You can see resource definition files are included as a value of
``lcm-kubernetes-def-files`` in ``additionalParams`` here.

.. code-block:: console

    $ cat ./instance_kubernetes.json
      {
        "flavourId": "simple",
        "additionalParams": {
          "lcm-kubernetes-def-files": [
            "Files/kubernetes/configmap_1.yaml",
            "Files/kubernetes/deployment.yaml",
            "Files/kubernetes/pod_env.yaml",
            "Files/kubernetes/pod_volume.yaml",
            "Files/kubernetes/replicaset.yaml",
            "Files/kubernetes/secret_1.yaml"
          ],
          "namespace": "default"
        },
        "vimConnectionInfo": [
          {
            "id": "8a3adb69-0784-43c7-833e-aab0b6ab4470",
            "vimId": "143897f4-7ab3-4fc5-9a5b-bbff09bdb92f",
            "vimType": "kubernetes"
          }
        ]
      }

Instantiate VNF by running the following command
:command:`openstack vnflcm instantiate <VNF instance ID> <json file>`,
after the command above is executed.

.. code-block:: console

    $ openstack vnflcm instantiate f21814f0-3e00-4651-a9ac-ec10f3248c19 instance_kubernetes.json
      Instantiate request for VNF Instance f21814f0-3e00-4651-a9ac-ec10f3248c19 has been accepted.

CNF Updating Procedure
-----------------------

As mentioned in Prerequisites, the VNF must be instantiated before performing
updating.

Next, the user can use the original vnf package as a template to make a new
vnf package, in which the yaml of ConfigMap, Secret, Pod and Deployment can
be changed.

.. note::

    * The yaml of ConfigMap and Secret can be changed. The kind, namespace
      and name cannot be changed, but the file name and file path can
      be changed.
    * The yaml of Pod and Deployment can also be changed, but only the
      image field can be changed, and no other fields can be changed.
    * No other yaml is allowed to be changed.

      * If changes other than images are made to the yaml of Pod and
        Deployment, those will not take effect. However, if heal entire
        VNF at this time, the resource will be based on the new yaml
        during the instantiation, and all changes will take effect.

Then after creating and uploading the new vnf package, you can perform the
update operation.
After the update, the Mgmt Driver will restart the pod to update and
recreate the deployment to update.

.. note::

    This document provides the new vnf package, the path is
    `tacker/tests/etc/samples/etsi/nfv/test_cnf_container_update_after`_

Details of CLI commands are described in :doc:`../cli/cli-etsi-vnflcm`.

How to Update CNF
~~~~~~~~~~~~~~~~~

Execute Update CLI command and check the status of the resources
before and after updating.

This is to confirm that the resources deployed in Kubernetes are updated
after update CNF.
The following is an example of the entire process.
The resources information before update:

* ConfigMap

  .. code-block:: console

    $ kubectl get configmaps
      NAME               DATA   AGE
      cm-data            1      3h55m
      kube-root-ca.crt   1      23h
    $
    $ kubectl describe configmaps cm-data
      Name:         cm-data
      Namespace:    default
      Labels:       <none>
      Annotations:  <none>

      Data
      ====
      cmKey1.txt:
      ----
      configmap data
      foo
      bar
      Events:  <none>

* Secret

  .. code-block:: console

    $ kubectl get secrets
      NAME                  TYPE                                  DATA   AGE
      default-token-ctq4p   kubernetes.io/service-account-token   3      23h
      secret-data           Opaque                                2      3h55m
    $
    $ kubectl describe secrets secret-data
      Name:         secret-data
      Namespace:    default
      Labels:       <none>
      Annotations:  <none>

      Type:  Opaque

      Data
      ====
      password:     15 bytes
      secKey1.txt:  15 bytes

* Pod

  .. code-block:: console

    $ kubectl get pod -o wide
      NAME                    READY   STATUS    RESTARTS   AGE     IP            NODE    NOMINATED NODE   READINESS GATES
      env-test                1/1     Running   0          4h28m   10.233.96.4   node2   <none>           <none>
      vdu1-85dd489b89-w72dr   1/1     Running   0          4h28m   10.233.96.5   node2   <none>           <none>
      vdu2-mfn78              1/1     Running   0          4h28m   10.233.96.2   node2   <none>           <none>
      volume-test             1/1     Running   0          4h28m   10.233.96.3   node2   <none>           <none>
    $
    $ kubectl describe pod volume-test
      Name:         volume-test
      Namespace:    default
      ...
      Containers:
        nginx:
          Container ID:   docker://01273fa7cd595b49d866b755ea6cc2707d90cca70ecb9f5a86c4db3eacad2dde
          Image:          nginx
          Image ID:       docker-pullable://nginx@sha256:e9712bdfa40c19cc2cee4f06e5b1215138926250165e26fe69822a9ddc525eaf
      ...
      Volumes:
        cm-volume:
          Type:      ConfigMap (a volume populated by a ConfigMap)
          Name:      cm-data
          Optional:  false
        sec-volume:
          Type:        Secret (a volume populated by a Secret)
          SecretName:  secret-data
          Optional:    false
      ...

* Deployment

  .. code-block:: console

    $ kubectl get deployments.apps -o wide
      NAME   READY   UP-TO-DATE   AVAILABLE   AGE     CONTAINERS   IMAGES   SELECTOR
      vdu1   1/1     1            1           4h29m   nginx        nginx    app=webserver
    $
    $ kubectl describe pod vdu1-85dd489b89-w72dr
      Name:         vdu1-85dd489b89-w72dr
      Namespace:    default
      ...
      Containers:
        nginx:
          Container ID:   docker://5efe65493ac13ff539f9de30db7c624405ff390df8f5f2e23f22fc0f8b6ad68a
          Image:          nginx
          Image ID:       docker-pullable://nginx@sha256:e9712bdfa40c19cc2cee4f06e5b1215138926250165e26fe69822a9ddc525eaf
      ...
          Environment Variables from:
            cm-data      ConfigMap with prefix 'CM_'  Optional: false
            secret-data  Secret with prefix 'SEC_'    Optional: false
          Environment:
            CMENV:   <set to the key 'cmKey1.txt' of config map 'cm-data'>  Optional: false
            SECENV:  <set to the key 'password' in secret 'secret-data'>    Optional: false
      ...
      Volumes:
        default-token-ctq4p:
          Type:        Secret (a volume populated by a Secret)
          SecretName:  default-token-ctq4p
          Optional:    false
      ...

Update CNF can be executed by the following CLI command.

.. code-block:: console

  $ openstack vnflcm update VNF_INSTANCE_ID --I sample_param_file.json

The content of the sample sample_param_file.json in this document is
as follows:

.. code-block:: console

  {
    "vnfdId": "b1bb0ce7-ebca-4fa7-95ed-4840d70a8883",
    "vnfInstanceName": "update_vnf_after",
    "metadata": {
      "configmap_secret_paths": [
        "Files/kubernetes/configmap_2.yaml",
        "Files/kubernetes/secret_2.yaml"
      ]
    }
  }

.. note::

    If you want to update ConfigMap and Secret, not only need to update
    their yaml, but also need to specify the updated yaml file path in
    the metadata field of the request input parameter.

Here is an example of updating CNF:

.. code-block:: console

  $ openstack vnflcm update 9d2bd0d7-4248-445d-a70f-a14cf57d6f96 --I sample_param_file.json
    Update vnf:9d2bd0d7-4248-445d-a70f-a14cf57d6f96

The resources information after update:

* ConfigMap

  .. code-block:: console

    $ kubectl describe configmaps cm-data
      Name:         cm-data
      Namespace:    default
      Labels:       <none>
      Annotations:  <none>

      Data
      ====
      cmKey1.txt:
      ----
      configmap2 data2
      foo2
      bar2
      Events:  <none>

* Secret

  .. code-block:: console

    $ kubectl describe secrets secret-data
      Name:         secret-data
      Namespace:    default
      Labels:       <none>
      Annotations:  <none>

      Type:  Opaque

      Data
      ====
      password:     16 bytes
      secKey1.txt:  18 bytes

* Pod

  .. code-block:: console

    $ kubectl get pod -o wide
      NAME                    READY   STATUS    RESTARTS   AGE     IP            NODE    NOMINATED NODE   READINESS GATES
      env-test                1/1     Running   1          5h45m   10.233.96.4   node2   <none>           <none>
      vdu1-5974f79c95-xs48r   1/1     Running   0          5m17s   10.233.96.7   node2   <none>           <none>
      vdu2-mfn78              1/1     Running   0          5h45m   10.233.96.2   node2   <none>           <none>
      volume-test             1/1     Running   1          5h45m   10.233.96.3   node2   <none>           <none>
    $ kubectl describe pod volume-test
      Name:         volume-test
      Namespace:    default
      ...
      Containers:
        nginx:
          Container ID:   docker://d3b101bff4863eef62c7a89cb07268d236a72c5b47cc46f167a1dbdf7900220f
          Image:          cirros
          Image ID:       docker-pullable://cirros@sha256:1e695eb2772a2b511ccab70091962d1efb9501fdca804eb1d52d21c0933e7f47
      ...
      Volumes:
        cm-volume:
          Type:      ConfigMap (a volume populated by a ConfigMap)
          Name:      cm-data
          Optional:  false
        sec-volume:
          Type:        Secret (a volume populated by a Secret)
          SecretName:  secret-data
          Optional:    false
      ...

* Deployment

  .. code-block:: console

    $ kubectl get deployments.apps -o wide
      NAME   READY   UP-TO-DATE   AVAILABLE   AGE     CONTAINERS   IMAGES   SELECTOR
      vdu1   1/1     1            1           5h50m   nginx        cirros   app=webserver
    $ kubectl describe pod vdu1-5974f79c95-xs48r
      Name:         vdu1-5974f79c95-xs48r
      Namespace:    default
      ...
      Containers:
        nginx:
          Container ID:   docker://6cad9f692f839d08b53fae58fe2ab06f576271d15aae8744ac0ce57c34510fe0
          Image:          cirros
          Image ID:       docker-pullable://cirros@sha256:1e695eb2772a2b511ccab70091962d1efb9501fdca804eb1d52d21c0933e7f47
      ...
          Environment Variables from:
            cm-data      ConfigMap with prefix 'CM_'  Optional: false
            secret-data  Secret with prefix 'SEC_'    Optional: false
          Environment:
            CMENV:   <set to the key 'cmKey1.txt' of config map 'cm-data'>  Optional: false
            SECENV:  <set to the key 'password' in secret 'secret-data'>    Optional: false
      ...
      Volumes:
        default-token-ctq4p:
          Type:        Secret (a volume populated by a Secret)
          SecretName:  default-token-ctq4p
          Optional:    false
      ...

You can see that the ConfigMap and Secret are updated, as are the images in
the Pod and Deployment.

.. _NFV-SOL001 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/001/02.06.01_60/gs_NFV-SOL001v020601p.pdf
.. _Set Tacker Configuration : https://docs.openstack.org/tacker/latest/user/mgmt_driver_deploy_k8s_usage_guide.html#set-tacker-configuration
.. _How to use Mgmt Driver for deploying Kubernetes Cluster : https://docs.openstack.org/tacker/latest/user/mgmt_driver_deploy_k8s_usage_guide.html#mgmt-driver-introduction
.. _samples/mgmt_driver/kubernetes/container_update/container_update_mgmt.py : https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes/container_update/container_update_mgmt.py
.. _tacker/tests/etc/samples/etsi/nfv/test_cnf_container_update_before : https://opendev.org/openstack/tacker/src/branch/master/tacker/tests/etc/samples/etsi/nfv/test_cnf_container_update_before
.. _tacker/tests/etc/samples/etsi/nfv/test_cnf_container_update_after : https://opendev.org/openstack/tacker/src/branch/master/tacker/tests/etc/samples/etsi/nfv/test_cnf_container_update_after
.. _ETSI GS NFV-SOL 001 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/001/02.06.01_60/gs_nfv-sol001v020601p.pdf
.. _Prepare Kubernetes VIM : https://docs.openstack.org/tacker/latest/user/etsi_containerized_vnf_usage_guide.html#prepare-kubernetes-vim
.. _Instantiate VNF : https://docs.openstack.org/tacker/latest/user/etsi_containerized_vnf_usage_guide.html#instantiate-vnf
