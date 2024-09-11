===========================
VNF Package Generation Tool
===========================

For upload VNF Package, it is required to provide a zip file
via ``openstack`` command.
Here is an example of uploading a VNF Package named as
``sample_vnf_package_csar.zip`` with a zip file.

.. code-block:: console

    $ openstack vnf package upload \
      --path ./sample_vnf_package_csar/sample_vnf_package_csar.zip \
      6e6b7a6d-0ebe-4085-96c2-b34269d837f9

You can prepare a zip file using a dedicated tool.


Prerequisites
-------------

This tool uses the following networks:

* ``net0`` network
* ``subnet0`` subnetwork for net0
* ``net1`` network
* ``subnet1`` subnetwork for net1
* ``net_mgmt`` network

These networks are created by default when you install Tacker
via devstack.
If these networks do not exist in your OpenStack environment,
please create them manually before running this tool.

You can check the networks with the following command.

.. code-block:: console

  $ openstack net list
  +--------------------------------------+-----------------+----------------------------------------------------------------------------+
  | ID                                   | Name            | Subnets                                                                    |
  +--------------------------------------+-----------------+----------------------------------------------------------------------------+
  | 348d1921-0cca-4730-815a-cc58c503ee65 | public          | 64290109-665b-442f-83d4-0a98b8301af8, d963ddfd-3ab1-4320-9efd-311049d92575 |
  | 3b069dc1-4247-4063-89dd-0898efa04384 | private         | 69f64379-e72f-433d-be01-ff6723e8e955, 9e0c260c-78f7-4f15-9157-40f823433449 |
  | 41ebfff9-df23-4690-bef9-a0e76f618947 | net1            | e24618bb-c7bc-4771-a9d8-eba53db3c0ae                                       |
  | ab598736-9fc9-470d-b894-b0a4d2f9d46c | lb-mgmt-net     | b21032be-c681-46ac-b249-8d3be320f830                                       |
  | d9fc27d5-d881-4cf2-9023-d9cff9df64ed | k8s-pod-net     | cd4269f6-9152-4707-95d4-825b722edcf0                                       |
  | dbe64c96-1334-4983-9f60-a90905af6ff0 | net0            | 23737d05-5e3f-4af8-8c4d-83221f794787                                       |
  | eeb398f0-818b-4c75-9573-8f50fa5de501 | net_mgmt        | bfa8e9d2-039d-4e59-85a2-8a9801d90cfd                                       |
  | ef55ac46-bb38-4abe-bdf7-2b9d3be02266 | k8s-service-net | 0d98b3b8-a6fd-4044-8acf-f0630755f956                                       |
  +--------------------------------------+-----------------+----------------------------------------------------------------------------+
  $ openstack subnet list
  +--------------------------------------+-------------------------+--------------------------------------+---------------------+
  | ID                                   | Name                    | Network                              | Subnet              |
  +--------------------------------------+-------------------------+--------------------------------------+---------------------+
  | 0d98b3b8-a6fd-4044-8acf-f0630755f956 | k8s-service-subnet-IPv4 | ef55ac46-bb38-4abe-bdf7-2b9d3be02266 | 10.0.0.128/26       |
  | 23737d05-5e3f-4af8-8c4d-83221f794787 | subnet0                 | dbe64c96-1334-4983-9f60-a90905af6ff0 | 10.10.0.0/24        |
  | 64290109-665b-442f-83d4-0a98b8301af8 | ipv6-public-subnet      | 348d1921-0cca-4730-815a-cc58c503ee65 | 2001:db8::/64       |
  | 69f64379-e72f-433d-be01-ff6723e8e955 | private-subnet          | 3b069dc1-4247-4063-89dd-0898efa04384 | 10.0.0.0/26         |
  | 9e0c260c-78f7-4f15-9157-40f823433449 | ipv6-private-subnet     | 3b069dc1-4247-4063-89dd-0898efa04384 | fd5f:5cb9:4f13::/64 |
  | b21032be-c681-46ac-b249-8d3be320f830 | lb-mgmt-subnet          | ab598736-9fc9-470d-b894-b0a4d2f9d46c | 192.168.0.0/24      |
  | bfa8e9d2-039d-4e59-85a2-8a9801d90cfd | subnet_mgmt             | eeb398f0-818b-4c75-9573-8f50fa5de501 | 192.168.120.0/24    |
  | cd4269f6-9152-4707-95d4-825b722edcf0 | k8s-pod-subnet-IPv4     | d9fc27d5-d881-4cf2-9023-d9cff9df64ed | 10.0.0.64/26        |
  | d963ddfd-3ab1-4320-9efd-311049d92575 | public-subnet           | 348d1921-0cca-4730-815a-cc58c503ee65 | 172.24.4.0/24       |
  | e24618bb-c7bc-4771-a9d8-eba53db3c0ae | subnet1                 | 41ebfff9-df23-4690-bef9-a0e76f618947 | 10.10.1.0/24        |
  +--------------------------------------+-------------------------+--------------------------------------+---------------------+


Usage
-----

By specifying the VIM Type as an option, a sample of the corresponding
VNF Package for Tacker v2 API is generated.

This tool support the following VIM Types:

* ETSINFV.OPENSTACK_KEYSTONE.V_3
* ETSINFV.KUBERNETES.V_1
* ETSINFV.HELM.V_3

In this document, TACKER_ROOT is the root of tacker's repository.

.. code-block:: console

  $ python3 -m pip install TAKCER_ROOT
  $ export PYTHONPATH=TAKCER_ROOT
  $ cd TAKCER_ROOT/tools
  $ python3 gen_vnf_pkg.py -h
  usage: gen_vnf_pkg.py [-h] -t VIM_TYPE

  Create VNF Package zip and parameter files

  options:
    -h, --help            show this help message and exit
    -t VIM_TYPE, --type VIM_TYPE
                          specify the vim type
                            * ETSINFV.OPENSTACK_KEYSTONE.V_3
                            * ETSINFV.KUBERNETES.V_1
                            * ETSINFV.HELM.V_3


The output of this tool is as follows:

* Specified VIM Type
* Generated zip file name
* List of file names included in the generated zip file

.. code-block:: console

  $ python3 gen_vnf_pkg.py -t ETSINFV.OPENSTACK_KEYSTONE.V_3
  VIM type = ETSINFV.OPENSTACK_KEYSTONE.V_3
  Zip file: userdata_standard.zip
  --------------------------------------------------
  BaseHOT/
  Definitions/
  Files/
  Scripts/
  TOSCA-Metadata/
  UserData/
  Files/images/
  Files/images/cirros-0.5.2-x86_64-disk.img
  Scripts/coordinate_vnf.py
  Scripts/sample_script.py
  TOSCA-Metadata/TOSCA.meta
  UserData/userdata_standard.py
  BaseHOT/simple/
  BaseHOT/simple/nested/
  BaseHOT/simple/sample3.yaml
  BaseHOT/simple/nested/VDU1.yaml
  BaseHOT/simple/nested/VDU2.yaml
  Definitions/v2_sample3_types.yaml
  Definitions/v2_sample3_top.vnfd.yaml
  Definitions/etsi_nfv_sol001_vnfd_types.yaml
  Definitions/etsi_nfv_sol001_common_types.yaml
  Definitions/v2_sample3_df_simple.yaml
  --------------------------------------------------

  $ python3 gen_vnf_pkg.py -t ETSINFV.KUBERNETES.V_1
  VIM type: ETSINFV.KUBERNETES.V_1
  Zip file: test_instantiate_cnf_resources.zip
  --------------------------------------------------
  Definitions/
  Files/
  Scripts/
  TOSCA-Metadata/
  Files/kubernetes/
  Files/kubernetes/controller-revision.yaml
  Files/kubernetes/role_rolebinding_SA.yaml
  Files/kubernetes/pod-template.yaml
  Files/kubernetes/deployment.yaml
  Files/kubernetes/statefulset.yaml
  Files/kubernetes/multiple_yaml_priority-class.yaml
  Files/kubernetes/persistent-volume-0.yaml
  Files/kubernetes/storage-class_pv_pvc.yaml
  Files/kubernetes/multiple_yaml_network-policy.yaml
  Files/kubernetes/subject-access-review.yaml
  Files/kubernetes/self-subject-access-review_and_self-subject-rule-review.yaml
  Files/kubernetes/bindings.yaml
  Files/kubernetes/pod.yaml
  Files/kubernetes/daemon-set.yaml
  Files/kubernetes/job.yaml
  Files/kubernetes/persistent-volume-1.yaml
  Files/kubernetes/horizontal-pod-autoscaler.yaml
  Files/kubernetes/multiple_yaml_lease.yaml
  Files/kubernetes/namespace.yaml
  Files/kubernetes/clusterrole_clusterrolebinding_SA.yaml
  Files/kubernetes/storage-class.yaml
  Files/kubernetes/limit-range.yaml
  Files/kubernetes/local-subject-access-review.yaml
  Files/kubernetes/replicaset_service_secret.yaml
  Files/kubernetes/resource-quota.yaml
  Files/kubernetes/deployment_fail_test.yaml
  Files/kubernetes/token-review.yaml
  Files/kubernetes/config-map.yaml
  Scripts/sample_script.py
  TOSCA-Metadata/TOSCA.meta
  Definitions/sample_cnf_df_simple.yaml
  Definitions/etsi_nfv_sol001_vnfd_types.yaml
  Definitions/etsi_nfv_sol001_common_types.yaml
  Definitions/sample_cnf_top.vnfd.yaml
  Definitions/sample_cnf_types.yaml
  --------------------------------------------------

  $ python3 gen_vnf_pkg.py -t ETSINFV.HELM.V_3
  VIM type = ETSINFV.HELM.V_3
  Zip file: test_helm_instantiate.zip
  --------------------------------------------------
  Definitions/
  Files/
  Scripts/
  TOSCA-Metadata/
  Files/kubernetes/
  Files/kubernetes/test-chart/
  Files/kubernetes/test-chart-0.1.0.tgz
  Files/kubernetes/test-chart/templates/
  Files/kubernetes/test-chart/Chart.yaml
  Files/kubernetes/test-chart/values.yaml
  Files/kubernetes/test-chart/.helmignore
  Files/kubernetes/test-chart/templates/service.yaml
  Files/kubernetes/test-chart/templates/deployment_vdu2.yaml
  Files/kubernetes/test-chart/templates/NOTES.txt
  Files/kubernetes/test-chart/templates/serviceaccount.yaml
  Files/kubernetes/test-chart/templates/_helpers.tpl
  Files/kubernetes/test-chart/templates/deployment_vdu1.yaml
  Scripts/sample_script.py
  TOSCA-Metadata/TOSCA.meta
  Definitions/sample_cnf_df_simple.yaml
  Definitions/etsi_nfv_sol001_vnfd_types.yaml
  Definitions/etsi_nfv_sol001_common_types.yaml
  Definitions/sample_cnf_top.vnfd.yaml
  Definitions/sample_cnf_types.yaml
  --------------------------------------------------


This tool generates a VNF Package zip file and a sample request file
for each VIM Type under the output directory.

.. code-block:: console

  $ ls output/
  helm_instantiate  test_instantiate_cnf_resources  userdata_standard

  $ ls output/userdata_standard/
  change_ext_conn_req  create_req  heal_req  instantiate_req  scale_in_req
  scale_out_req  terminate_req  update_req  userdata_standard.zip

  $ ls output/test_instantiate_cnf_resources/
  create_req  max_sample_heal  max_sample_instantiate  max_sample_scale_in
  max_sample_scale_out  max_sample_terminate  test_instantiate_cnf_resources.zip

  $ ls output/helm_instantiate
  create_req  helm_heal  helm_instantiate_req  helm_scale_in  helm_scale_out
  helm_terminate_req  test_helm_instantiate.zip


For the following request files, ``endpoint``, ``ssl_ca_cert`` and
``bearer_token`` need to be changed by your own k8s cluster information.

* max_sample_instantiate for ETSINFV.KUBERNETES.V_1
* helm_instantiate_req for ETSINFV.HELM.V_3

.. note::

  ``ssl_ca_cert`` needs to be on one line as shown below.

  .. code-block:: json

    "ssl_ca_cert": "-----BEGIN CERTIFICATE-----\nMIIDB...BH\n3bkddspNikO1\n-----END CERTIFICATE-----\n"

  Please note that line breaks are changed to '``\n``'.


You can also set your own k8s cluster information to ``auth_url``,
``barere_token``, and ``ssl_ca_cert`` in gen_vnf_pkg.py before running this tool.

.. note::

  If you use a VIM that is already registered,
  modify vimConnectionInfo as follows.

  .. code-block:: json

    "vimConnectionInfo": {
      "vim1": {
        "vimId": "REGISTERED_VIM_ID",
        "vimType": "VIM_TYPE"
      }
    }


For the following request files, ``vnfcInstanceId`` need
to be changed with target vnfcInfo id.

* heal_req for ETSINFV.OPENSTACK_KEYSTONE.V_3
* max_sample_heal for ETSINFV.KUBERNETES.V_1
* helm_heal for ETSINFV.HELM.V_3


And for the following request file, ``vnfdId`` need
to be changed with target VNFD id.

* update_req for ETSINFV.OPENSTACK_KEYSTONE.V_3


.. note::

  This tool generates a zip file and a request file based on the following
  used in FT as a sample VNF Package.

  * ETSINFV.OPENSTACK_KEYSTONE.V_3:
    `samples/tests/functional/sol_v2_common/userdata_standard`_
  * ETSINFV.KUBERNETES.V_1:
    `samples/tests/functional/sol_kubernetes_v2/test_instantiate_cnf_resources`_
  * ETSINFV.HELM.V_3:
    `samples/tests/functional/sol_kubernetes_v2/test_helm_instantiate`_

  Please note that if FT is changed, the output of this tool may also change.


.. _samples/tests/functional/sol_v2_common/userdata_standard:
  https://opendev.org/openstack/tacker/src/branch/master/samples/tests/functional/sol_v2_common/userdata_standard
.. _samples/tests/functional/sol_kubernetes_v2/test_instantiate_cnf_resources:
  https://opendev.org/openstack/tacker/src/branch/master/samples/tests/functional/sol_kubernetes_v2/test_instantiate_cnf_resources
.. _samples/tests/functional/sol_kubernetes_v2/test_helm_instantiate:
  https://opendev.org/openstack/tacker/src/branch/master/samples/tests/functional/sol_kubernetes_v2/test_helm_instantiate
