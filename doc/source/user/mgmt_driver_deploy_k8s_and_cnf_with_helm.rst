=========================================================================
How to Install Helm to Kubernetes Cluster and Deploy CNF using Helm Chart
=========================================================================

Overview
--------
Tacker supports Helm chart as MCIOP (Managed Container Infrastructure Object
Package).

By following this procedures below, users can install and configure Helm
environment in the Master Nodes of Kubernetes Cluster deployed by Mgmt Driver,
and users can deploy CNF by Helm chart to the deployed Kubernetes Cluster.

.. note:: This page focuses on changes from the original documentation. If
          there are no changes, follow the original procedures.

Kubernetes Cluster and Helm Deployment
--------------------------------------
For the original documentation, see `How to use Mgmt Driver for deploying
Kubernetes Cluster`_.

Create and Upload VNF Package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
For the original documentation, see `Create and Upload VNF Package`_.
The following changes are required:

* Modify the TOSCA.meta file to install Helm
* Add Helm install script

1. Directory Structure
~~~~~~~~~~~~~~~~~~~~~~
TOSCA-Metadata/TOSCA.meta
:::::::::::::::::::::::::
To install Helm when deploying a Kubernetes Cluster, add the helm install
script information to the "TOSCA.meta" file.
The target of "helm install script information" is the script added by the
following :ref:`directory-Scripts/`.
The sample file is shown below.

TOSCA.meta

.. code-block:: console

    TOSCA-Meta-File-Version: 1.0
    Created-by: Dummy User
    CSAR-Version: 1.1
    Entry-Definitions: Definitions/sample_kubernetes_top.vnfd.yaml

    Name: Files/images/ubuntu-20.04-server-cloudimg-amd64.img
    Content-Type: application/x-iso9066-image

    Name: Scripts/install_k8s_cluster.sh
    Content-Type: application/sh
    Algorithm: SHA-256
    Hash: ec6423c8d68ff19e0d44b1437eddefa410a5ed43a434fa51ed07bde5a6d06abe

    Name: Scripts/install_helm.sh
    Content-Type: application/sh
    Algorithm: SHA-256
    Hash: 4af332b05e3e85662d403208e1e6d82e5276cbcd3b82a3562d2e3eb80d1ef714

    Name: Scripts/kubernetes_mgmt.py
    Content-Type: text/x-python
    Algorithm: SHA-256
    Hash: bf651994ca7422aadeb0a12fed179f44ab709029c2eee9b2b9c7e8cbf339a66d

.. _directory-Scripts/:

Scripts/
::::::::
Add the following helm install script to the Scripts/.

`install_helm.sh`_

.. code-block:: console

    $ ls  Scripts/
    install_helm.sh  install_k8s_cluster.sh  kubernetes_mgmt.py

.. _Deploy Kubernetes Cluster by helm:

Deploy Kubernetes Cluster
^^^^^^^^^^^^^^^^^^^^^^^^^
For the original documentation, see `Deploy Kubernetes Cluster`_.
The following change is required:

* Add script path information to install Helm

1. Multi-master Nodes
~~~~~~~~~~~~~~~~~~~~~
1. Create the Parameter File
::::::::::::::::::::::::::::
Add ``helm_installation_script_path`` as a KeyValuePairs to the definition of
`Explanation of the parameters for deploying a Kubernetes cluster`_ to install
Helm.
Along with this change, the json file should also include the above
KeyValuePairs.

.. code-block:: console

   ## Request parameter to install Helm
   +-------------------------------+-----------------------------------------------+
   | Attribute name                | Parameter description                         |
   +===============================+===============================================+
   | helm_installation_script_path | File path of the script file to install Helm. |
   +-------------------------------+-----------------------------------------------+

complex_kubernetes_param_file.json

.. code-block:: json

    {
        "flavourId": "complex",
        "vimConnectionInfo": [{
            "id": "3cc2c4ff-525c-48b4-94c9-29247223322f",
            "vimId": "8343f55f-6bdf-4c5f-91c4-f6dd145c616d",
            "vimType": "openstack"
        }],
        "additionalParams": {
            "k8s_cluster_installation_param": {
                "script_path": "Scripts/install_k8s_cluster.sh",
                "vim_name": "kubernetes_vim_complex_helm",
                "master_node": {
                    "aspect_id": "master_instance",
                    "ssh_cp_name": "masterNode_CP1",
                    "nic_cp_name": "masterNode_CP1",
                    "username": "ubuntu",
                    "password": "ubuntu",
                    "cluster_cp_name": "vip_CP"
                },
                "worker_node": {
                    "aspect_id": "worker_instance",
                    "ssh_cp_name": "workerNode_CP2",
                    "nic_cp_name": "workerNode_CP2",
                    "username": "ubuntu",
                    "password": "ubuntu"
                },
                "proxy": {
                    "http_proxy": "http://user1:password1@host1:port1",
                    "https_proxy": "http://user1:password1@host1:port1",
                    "k8s_node_cidr": "10.10.0.0/24"
                },
                "helm_installation_script_path": "Scripts/install_helm.sh"
            },
            "lcm-operation-user-data": "./UserData/k8s_cluster_user_data.py",
            "lcm-operation-user-data-class": "KubernetesClusterUserData"
        },
        "extVirtualLinks": [{
            "id": "net0_master",
            "resourceId": "9015848b-8b11-40bd-a918-01138313afa5",
            "extCps": [{
                "cpdId": "masterNode_CP1",
                "cpConfig": [{
                    "linkPortId": "ed802cb7-15a4-4942-bf42-21511c888e21"
                }]
            }]
        }, {
            "id": "net0_worker",
            "resourceId": "9015848b-8b11-40bd-a918-01138313afa5",
            "extCps": [{
                "cpdId": "workerNode_CP2",
                "cpConfig": [{
                    "linkPortId": "ed802cb7-15a4-4942-bf42-21511c888e33"
                }]
            }]
        }]
    }

2. Check Results of Instantiation Operations
::::::::::::::::::::::::::::::::::::::::::::
Make sure that VIM with extra field is added to vimConnectionInfo.

.. code-block:: console

    $ openstack vnflcm show 7131268c-68ca-4cbe-a881-de4fc339303e --column "VIM Connection Info"
    +---------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field               | Value                                                                                                                                                    |
    +---------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------+
    | VIM Connection Info | [                                                                                                                                                        |
    |                     |     {                                                                                                                                                    |
    |                     |         "id": "3cc2c4ff-525c-48b4-94c9-29247223322f",                                                                                                    |
    |                     |         "vimId": "8343f55f-6bdf-4c5f-91c4-f6dd145c616d",                                                                                                 |
    |                     |         "vimType": "openstack",                                                                                                                          |
    |                     |         "interfaceInfo": {},                                                                                                                             |
    |                     |         "accessInfo": {},                                                                                                                                |
    |                     |         "extra": {}                                                                                                                                      |
    |                     |     },                                                                                                                                                   |
    |                     |     {                                                                                                                                                    |
    |                     |         "id": "7829ce55-86cc-4d02-98a5-4d6ed9214bcb",                                                                                                    |
    |                     |         "vimId": "690edc6b-7581-48d8-9ac9-910c2c3d7c02",                                                                                                 |
    |                     |         "vimType": "kubernetes",                                                                                                                         |
    |                     |         "interfaceInfo": null,                                                                                                                           |
    |                     |         "accessInfo": {                                                                                                                                  |
    |                     |             "authUrl": "https://10.10.0.91:16443"                                                                                                        |
    |                     |         },                                                                                                                                               |
    |                     |         "extra": {                                                                                                                                       |
    |                     |             "helmInfo": "{'masternode_ip': ['10.10.0.35', '10.10.0.63', '10.10.0.4'], 'masternode_username': 'ubuntu', 'masternode_password': 'ubuntu'}" |
    |                     |         }                                                                                                                                                |
    |                     |     }                                                                                                                                                    |
    |                     | ]                                                                                                                                                        |
    +---------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------+

2. Single Master Node
~~~~~~~~~~~~~~~~~~~~~
1. Create the Parameter File
::::::::::::::::::::::::::::
As in the case of "Multi Master Node", add ``helm_installation_script_path`` as
a KeyValuePairs to the definition of
`Explanation of the parameters for deploying a Kubernetes cluster`_.
In addition, you should include KeyValuePairs in the json file.

2. Check Results of Instantiation Operations
::::::::::::::::::::::::::::::::::::::::::::
Verify that Helm has been successfully installed.
As in the case of "Multi Master Node", make sure that VIM with extra field is
added to vimConnectionInfo.


ETSI NFV-SOL CNF Deployment by Helm chart
-----------------------------------------
For the original documentation, see `ETSI NFV-SOL CNF (Containerized VNF)
Deployment`_.

Prepare Kubernetes VIM
^^^^^^^^^^^^^^^^^^^^^^
The following change is required from original section `Prepare Kubernetes
VIM`_:

* Skip the VIM registration procedure

1. Create a Config File
~~~~~~~~~~~~~~~~~~~~~~~
This step is not required because it is performed in conjunction with the VIM
registration during the Helm installation procedure.
After completing the procedures in this chapter, execute the following
:ref:`Register Kubernetes VIM by helm charts` instead of conventional procedure
(`2. Register Kubernetes VIM`_).

.. _Register Kubernetes VIM by helm charts:

2. Register Kubernetes VIM
~~~~~~~~~~~~~~~~~~~~~~~~~~
If Helm is used, no new registration is required because
:ref:`Deploy Kubernetes Cluster by helm` registers VIM when Kubernetes Cluster
is deployed.
For the registered VIM information, confirm that the VIM registered in
:ref:`Deploy Kubernetes Cluster by helm` exists and the Status is "REACHABLE".

.. code-block:: console

    $ openstack vim list
    +--------------------------------------+-----------------------------+----------------------------------+------------+------------+-------------+
    | ID                                   | Name                        | Tenant_id                        | Type       | Is Default | Status      |
    +--------------------------------------+-----------------------------+----------------------------------+------------+------------+-------------+
    | 690edc6b-7581-48d8-9ac9-910c2c3d7c02 | kubernetes_vim_complex_helm | 7e757a0cfea940dab100216036212a65 | kubernetes | False      | REACHABLE   |
    | 8343f55f-6bdf-4c5f-91c4-f6dd145c616d | VIM0                        | 7e757a0cfea940dab100216036212a65 | openstack  | True       | REACHABLE   |
    +--------------------------------------+-----------------------------+----------------------------------+------------+------------+-------------+

Prepare VNF Package
^^^^^^^^^^^^^^^^^^^
The following changes are required from original section `Prepare VNF
Package`_:

* Skip Kubernetes object file creation
* Prepare to use a local Helm chart file
* Verify VNFD constraints

1. Create a Kubernetes Object File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If you use Helm, this step is not required because the deployment
uses Helm chart instead of the deployment.yaml file.

2. Deploy a local Helm chart file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
When using a local Helm chart file, place the chart file you want to use
in "Files/Kubernetes".
If you use external repositories, you do not need to store chart files.
Please refer to [#Helm-Create]_ and [#Helm-Package]_ for how to create and
package a Helm chart file and points to be aware of when creating it.

.. code-block:: console

    $ ls Files/kubernetes/
    localhelm-0.1.0.tgz

.. _Create a TOSCA.meta File:

3. Create a TOSCA.meta File
~~~~~~~~~~~~~~~~~~~~~~~~~~~
For the original documentation, see `3. Create a TOSCA.meta File`_.
If you use a local Helm chart file, enter the relevant information for the
chart file instead of "deployment.yaml".

.. code-block:: console

    $ cat TOSCA-Metadata/TOSCA.meta
    TOSCA-Meta-File-Version: 1.0
    Created-by: dummy_user
    CSAR-Version: 1.1
    Entry-Definitions: Definitions/sample_vnfd_top.yaml

    Name: Files/kubernetes/localhelm-0.1.0.tgz
    Content-Type: application/tar+gzip
    Algorithm: SHA-256
    Hash: 837fcfb73e5fc58572851a80a0143373d9d28ec37bd3bdf52c4d7d34b97592d5

4. Create VNFD
~~~~~~~~~~~~~~
For the original documentation, see `5. Create VNFD`_.
To deploy CNF using Helm chart, modify the
``topology_template.node_templates.VDUxx.properties.name`` value in
"helloworld3_df_simple.yaml".
The following is an example of setting when using an external repository and a
local Helm chart file.
Refer to :ref:`Set the Value to the Request Parameter File for Helm chart` for
the correspondence between the set value and the parameter.

If you are using a chart file stored in external repository, the
``topology_template.node_templates.VDUxx.properties.name`` value should be
"<helmreleasename> - <helmchartname>".

.. note:: If this value is not set as above, scale operation will not work.
          This limitation will be removed in the future by modifying
          additionalParams.

The following shows the relationship between
``topology_template.node_templates.VDUxx.properties.name`` when using an
external repository and the resource definition file created in the step
`Instantiate VNF`_.

.. code-block:: console

    $ cat instance_helm.json
    {
            "helmreleasename": "vdu1",
            "helmchartname": "externalhelm",
    }

    $ cat Definitions/helloworld3_df_simple.yaml
    topology_template:
      node_templates:
        VDU1:
          properties:
            name: vdu1-externalhelm

If you are using local Helm chart file,
``topology_template.node_templates.VDUxx.properties.name`` value should be
"<helmreleasename> - <part of helmchartfile_path>".

.. note:: "part of helmchart_path" is the part of file name without
          "-<version>.tgz" at the end. In the following example, it is
          "localhelm".

.. note:: If this value is not set as above, scale operation will not work.
          This limitation will be removed in the future by modifying
          additionalParams.

The following shows the relationship between
``topology_template.node_templates.VDUxx.properties.name`` when using an
external repository and the resource definition file created in the step
`Instantiate VNF`_.

.. code-block:: console

    $ cat instance_helm.json
    {
            "helmreleasename": "vdu1",
            "helmchartfile_path": "Files/kubernetes/localhelm-0.1.0.tgz"
    }

    $ cat Definitions/helloworld3_df_simple.yaml
    topology_template:
      node_templates:
        VDU1:
          properties:
            name: vdu1-localhelm

Instantiate VNF
^^^^^^^^^^^^^^^
For the original documentation, see `Instantiate VNF`_.
The following changes are required:

* Add parameters for deploying CNF to the json definition file
* Verify CNF deployment results

.. _Set the Value to the Request Parameter File for Helm chart:

1. Set the Value to the Request Parameter File for Helm chart
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
For the original documentation, see `1. Set the Value to the Request Parameter
File`_.
After verifying the identity of the VIM according to the procedure, add the
following parameter to the json definition file to deploy CNF by Helm chart.

.. code-block:: console

    ## List of additional parameters for deploying CNF by Helm chart
    +----------------------------+-----------+-----------------------------------------------------------+
    | Attribute name             | Data type | Parameter description                                     |
    +============================+===========+===========================================================+
    |namespace                   | String    | Namespace to deploy Kubernetes resources.                 |
    |                            |           | If absent, the value in Helm chart is used as default.    |
    +----------------------------+-----------+-----------------------------------------------------------+
    |use_helm                    | Boolean   | If "true", Kubernetes InfraDriver utilizes Helm client,   |
    |                            |           | otherwise, Kubernetes Python client is used.              |
    |                            |           | true: with Helm, false: without Helm                      |
    +----------------------------+-----------+-----------------------------------------------------------+
    |using_helm_install_param    | Array     | Parameters for the step related to Helm chart.            |
    |                            |           | Shall be present if "use_helm" is "true".                 |
    +----------------------------+-----------+-----------------------------------------------------------+
    |> exthelmchart              | Boolean   | If true, Helm chart is not in VNF Package.                |
    |                            |           | true: external Helm chart, false: in VNF Package          |
    +----------------------------+-----------+-----------------------------------------------------------+
    |> helmchartfile_path        | String    | Path of Helm chart files in VNF Package.                  |
    |                            |           | Shall be present if "exthelmchart" is "false".            |
    |                            |           |                                                           |
    |                            |           | Note: The "part of helmchartfile_path" that is noted      |
    |                            |           | above must be unique for VIM.                             |
    +----------------------------+-----------+-----------------------------------------------------------+
    |> helmreleasename           | String    | Name of release as instance of Helm chart.                |
    |                            |           |                                                           |
    |                            |           | Note: This parameter must be unique for VIM.              |
    +----------------------------+-----------+-----------------------------------------------------------+
    |> helmparameter             | Array     | Parameters of KeyValuePairs,                              |
    |                            |           | which is specified during Helm installation.              |
    +----------------------------+-----------+-----------------------------------------------------------+
    |> helmrepostitoryname       | String    | Helm repository name.                                     |
    |                            |           | Shall be present if "exthelmchart" is "true".             |
    +----------------------------+-----------+-----------------------------------------------------------+
    |> helmchartname             | String    | Helm chart name.                                          |
    |                            |           | Shall be present if "exthelmchart" is "true".             |
    |                            |           |                                                           |
    |                            |           | Note: This parameter must be unique for VIM.              |
    +----------------------------+-----------+-----------------------------------------------------------+
    |> exthelmrepo_url           | String    | URL of external Helm repository.                          |
    |                            |           | Shall be present if "exthelmchart" is "true".             |
    |                            |           |                                                           |
    |                            |           | Note: Don't specify a different exthelmrepo_url for an    |
    |                            |           | already registered helmrepositoryname in VIM.             |
    +----------------------------+-----------+-----------------------------------------------------------+
    |helm_replica_values         | Dict      | Parameters for the number of replicas for each aspectId   |
    |                            |           | used during scale operation.                              |
    |                            |           | Shall be present if "use_helm" is "true".                 |
    |                            |           |                                                           |
    |                            |           | key: "aspectId" defined in VNFD and specified during      |
    |                            |           |      scale operation.                                     |
    |                            |           | value: Parameter for the number of replicas defined in    |
    |                            |           |        Helm values.                                       |
    +----------------------------+-----------+-----------------------------------------------------------+

If you are deploying using a chart file stored in external repository, set
``additionalParams.using_helm_install_param.exthelmchart`` to ``true``
and set other parameters.
The following is a sample of json definition file for deployment using
a chart file stored in an external repository.

.. code-block:: console

    $ cat instance_helm.json
    {
      "flavourId": "simple",
      "additionalParams": {
        "namespace": "default",
        "use_helm": "true",
        "using_helm_install_param": [
          {
            "exthelmchart": "true",
            "helmreleasename": "vdu1",
            "helmparameter": [
              "key1=value1",
              "key2=value2"
              ],
            "helmrepositoryname": "mychart",
            "helmchartname": "externalhelm",
            "exthelmrepo_url": "http://helmrepo.example.com/sample-charts"
          }
        ],
        "helm_replica_values": {
          "vdu1_aspect": "replicaCount"
        }
      },
      "vimConnectionInfo": [
        {
          "id": "817954e4-c321-4a31-ae06-cedcc4ddb85c",
          "vimId": "690edc6b-7581-48d8-9ac9-910c2c3d7c02",
          "vimType": "kubernetes"
        }
      ]
    }

.. note:: The "helmreleasename" and "helmchartname" in the json file must
          match the ``topology_template.node_templates.VDUxx.properties.name``
          value set in the VNFD.

If you are deploying using a local Helm chart file, set
``additionalParams.using_helm_install_param.exthelmchart`` to "false"
and set other parameters.
The following is a sample of json definition file for deployment using
a local Helm chart file.

.. code-block:: console

    $ cat instance_helm.json
    {
      "flavourId": "simple",
      "additionalParams": {
        "namespace": "default",
        "use_helm": "true",
        "using_helm_install_param": [
          {
            "exthelmchart": "false",
            "helmreleasename": "vdu1",
            "helmparameter": [
              "key1=value1",
              "key2=value2"
              ],
            "helmchartfile_path": "Files/kubernetes/localhelm-0.1.0.tgz"
          }
        ],
        "helm_replica_values": {
          "vdu1_aspect": "replicaCount"
        }
      },
      "vimConnectionInfo": [
        {
          "id": "817954e4-c321-4a31-ae06-cedcc4ddb85c",
          "vimId": "690edc6b-7581-48d8-9ac9-910c2c3d7c02",
          "vimType": "kubernetes"
        }
      ]
    }

.. note:: The "helmreleasename" and "helmchartfile_path" in the json file must
          match the ``topology_template.node_templates.VDUxx.properties.name``
          value set in the VNFD.

2. Check the Deployment in Kubernetes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
For the original documentation, see `4. Check the Deployment in Kubernetes`_ .
In addition to checkpoints before modifying the procedure, ensure that the NAME
of the deployed CNF matches the value of
``topology_template.node_templates.VDUxx.properties.name`` in the VNFD.

.. code-block:: console

    $ kubectl get deploy
    NAME                  READY   UP-TO-DATE   AVAILABLE   AGE
    vdu1-localhelm        1/1     1            1           5m1s

.. _3. Check the Deployment in Helm:

3. Check the Deployment in Helm
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Run the following command to verify that it is deployed by the Helm chart.
If NAME matches "helmreleasename" then deployment is succeeded.

.. code-block:: console

    $ helm list --all
    NAME            NAMESPACE       REVISION        UPDATED                                 STATUS          CHART           APP VERSION
    vdu1            default         1               2021-09-10 09:26:02.091007332 +0000 UTC deployed        localhelm-0.1.0 1.16.0


Reference
---------

.. _How to use Mgmt Driver for deploying Kubernetes Cluster : https://docs.openstack.org/tacker/latest/user/mgmt_driver_deploy_k8s_usage_guide.html
.. _Create and Upload VNF Package : https://docs.openstack.org/tacker/latest/user/mgmt_driver_deploy_k8s_usage_guide.html#create-and-upload-vnf-package
.. _TOSCA.meta : https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes/kubernetes_vnf_package/TOSCA-Metadata/TOSCA.meta
.. _install_helm.sh : https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes/install_helm.sh
.. _Deploy Kubernetes Cluster : https://docs.openstack.org/tacker/latest/user/mgmt_driver_deploy_k8s_usage_guide.html#deploy-kubernetes-cluster
.. _Explanation of the parameters for deploying a Kubernetes cluster : https://docs.openstack.org/tacker/latest/user/mgmt_driver_deploy_k8s_usage_guide.html#single-master-node
.. _ETSI NFV-SOL CNF (Containerized VNF) Deployment : https://docs.openstack.org/tacker/latest/user/etsi_containerized_vnf_usage_guide.html
.. _Prepare Kubernetes VIM : https://docs.openstack.org/tacker/latest/user/etsi_containerized_vnf_usage_guide.html#prepare-kubernetes-vim
.. _Prepare VNF Package : https://docs.openstack.org/tacker/latest/user/etsi_containerized_vnf_usage_guide.html#prepare-vnf-package
.. _5. Create VNFD : https://docs.openstack.org/tacker/latest/user/etsi_containerized_vnf_usage_guide.html#create-vnfd
.. _Instantiate VNF : https://docs.openstack.org/tacker/latest/user/etsi_containerized_vnf_usage_guide.html#set-the-value-to-the-request-parameter-file
.. _1. Set the Value to the Request Parameter File : https://docs.openstack.org/tacker/latest/user/etsi_containerized_vnf_usage_guide.html#set-the-value-to-the-request-parameter-file
.. _4. Check the Deployment in Kubernetes : https://docs.openstack.org/tacker/latest/user/etsi_containerized_vnf_usage_guide.html#check-the-deployment-in-kubernetes

.. [#Helm-Create] : https://helm.sh/docs/helm/helm_create/
.. [#Helm-Package] : https://helm.sh/docs/helm/helm_package/
