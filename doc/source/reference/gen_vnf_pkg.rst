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

.. code-block:: console

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

This tool supports the following VIM Types:

* ETSINFV.OPENSTACK_KEYSTONE.V_3
* ETSINFV.KUBERNETES.V_1
* ETSINFV.HELM.V_3

Refer to help message for the usage.

.. note::

  In this document, ``TACKER_ROOT`` is the root of tacker's repository on
  the server.

.. code-block:: console

  $ cd TACKER_ROOT/tools
  $ python3 gen_vnf_pkg.py -h
  usage: gen_vnf_pkg.py [-h] -t VIM_TYPE [-c VIM_CONF] [--vim-id VIM_ID] [--vim-name VIM_NAME]

  Create VNF Package zip and parameter files

  options:
    -h, --help            show this help message and exit
    -t VIM_TYPE, --type VIM_TYPE
                          vim type (lowercase is also available)
                          * ETSINFV.OPENSTACK_KEYSTONE.V_3
                          * ETSINFV.KUBERNETES.V_1
                          * ETSINFV.HELM.V_3
    -c VIM_CONF, --vim-config VIM_CONF
                          Path of VIM config file for specifying the VIM
    --vim-id VIM_ID       VIM ID (Only for OpenStack and overwrittenby `--vim-config`)
    --vim-name VIM_NAME   Name of VIM (Only for OpenStack and overwrittenby `--vim-config`)


.. note::

  This tool requires some Tacker modules, so you need to run it in
  an environment where Tacker is installed.

  You can run the tool from virtual environment if you've setup Tacker
  with devstack. Activate it as follows before using the tool.

  .. code-block:: console

    $ source ~/data/venv/bin/activate
    (venv) $ python3 $TACKER_ROOT/tools/gen_vnf_pkg.py -h

  Or run the tool from tox which is defined as tox's environment
  ``gen-pkg`` without devstack environment.

  .. code-block:: console

    $ tox -e gen-pkg -- -h


Examples of output for three types showing generated zip and request files,
and list of file names included in the generated zip file.

.. code-block:: console

  $ python3 gen_vnf_pkg.py -t ETSINFV.OPENSTACK_KEYSTONE.V_3
  Generating package and request files in './output/userdata_standard/' ...
  VNF package: userdata_standard.zip
  Request files: create_req, terminate_req, instantiate_req, scale_out_req, scale_in_req, heal_req, change_ext_conn_req, update_req
  Contents of the VNF package:
  File Name                                             Modified             Size
  BaseHOT/                                       2024-08-28 05:36:20            0
  Definitions/                                   2025-01-29 10:58:48            0
  Files/                                         2025-01-29 10:58:48            0
  Scripts/                                       2024-08-28 05:36:20            0
  TOSCA-Metadata/                                2024-08-28 05:36:20            0
  UserData/                                      2025-01-29 10:58:48            0
  BaseHOT/simple/                                2024-08-28 05:36:20            0
  BaseHOT/simple/nested/                         2024-08-28 05:36:20            0
  BaseHOT/simple/sample3.yaml                    2024-08-28 05:36:20         1694
  BaseHOT/simple/nested/VDU1.yaml                2024-08-28 05:36:20         1179
  BaseHOT/simple/nested/VDU2.yaml                2024-08-28 05:36:20         1725
  UserData/userdata_standard.py                  2025-01-29 10:58:48        20805
  Files/images/                                  2025-01-29 10:58:48            0
  Files/images/cirros-0.5.2-x86_64-disk.img      2025-01-29 10:58:48     16300544
  Scripts/coordinate_vnf.py                      2024-08-28 05:36:20         2785
  Scripts/sample_script.py                       2024-08-28 05:36:20         1964
  Definitions/etsi_nfv_sol001_common_types.yaml  2025-01-29 10:58:48         9093
  Definitions/etsi_nfv_sol001_vnfd_types.yaml    2025-01-29 10:58:48        67046
  Definitions/v2_sample3_types.yaml              2025-01-29 10:58:48         1630
  Definitions/v2_sample3_top.vnfd.yaml           2025-01-29 10:58:48          887
  Definitions/v2_sample3_df_simple.yaml          2025-01-29 10:58:48        10149
  TOSCA-Metadata/TOSCA.meta                      2024-08-28 05:36:20          133

.. code-block:: console

  $ python3 gen_vnf_pkg.py -t ETSINFV.KUBERNETES.V_1
  Generating package and request files in './output/test_instantiate_cnf_resources/' ...
  VNF package: test_instantiate_cnf_resources.zip
  Request files: create_req, max_sample_instantiate, max_sample_terminate, max_sample_scale_out, max_sample_scale_in, max_sample_heal
  Contents of the VNF package:
  File Name                                             Modified             Size
  Definitions/                                   2025-01-29 11:02:26            0
  Files/                                         2024-08-28 05:36:20            0
  Scripts/                                       2024-08-28 05:36:20            0
  TOSCA-Metadata/                                2024-12-19 07:57:02            0
  Files/kubernetes/                              2024-12-19 07:57:02            0
  Files/kubernetes/limit-range.yaml              2024-08-28 05:36:20          165
  Files/kubernetes/storage-class_pv_pvc.yaml     2024-08-28 05:36:20          697
  Files/kubernetes/job.yaml                      2024-12-19 07:57:02          554
  Files/kubernetes/controller-revision.yaml      2024-08-28 05:36:20          127
  Files/kubernetes/subject-access-review.yaml    2024-08-28 05:36:20          188
  Files/kubernetes/replicaset_service_secret.yaml 2024-08-28 05:36:20          950
  Files/kubernetes/bindings.yaml                 2024-08-28 05:36:20          150
  Files/kubernetes/namespace.yaml                2024-08-28 05:36:20           54
  Files/kubernetes/deployment_fail_test.yaml     2024-08-28 05:36:20          537
  Files/kubernetes/statefulset.yaml              2024-08-28 05:36:20          825
  Files/kubernetes/config-map.yaml               2024-08-28 05:36:20          120
  Files/kubernetes/horizontal-pod-autoscaler.yaml 2024-08-28 05:36:20          280
  Files/kubernetes/persistent-volume-0.yaml      2024-08-28 05:36:20          281
  Files/kubernetes/token-review.yaml             2024-08-28 05:36:20          291
  Files/kubernetes/persistent-volume-1.yaml      2024-08-28 05:36:20          285
  Files/kubernetes/pod-template.yaml             2024-12-19 07:57:02          923
  Files/kubernetes/deployment.yaml               2024-08-28 05:36:20          536
  Files/kubernetes/local-subject-access-review.yaml 2024-08-28 05:36:20          224
  Files/kubernetes/self-subject-access-review_and_self-subject-rule-review.yaml 2024-08-28 05:36:20          275
  Files/kubernetes/resource-quota.yaml           2024-08-28 05:36:20          158
  Files/kubernetes/clusterrole_clusterrolebinding_SA.yaml 2024-08-28 05:36:20          578
  Files/kubernetes/storage-class.yaml            2024-08-28 05:36:20          153
  Files/kubernetes/role_rolebinding_SA.yaml      2024-08-28 05:36:20          559
  Files/kubernetes/multiple_yaml_priority-class.yaml 2024-08-28 05:36:20          155
  Files/kubernetes/pod.yaml                      2024-12-19 07:57:02          291
  Files/kubernetes/multiple_yaml_lease.yaml      2024-08-28 05:36:20          155
  Files/kubernetes/daemon-set.yaml               2024-08-28 05:36:20          417
  Files/kubernetes/multiple_yaml_network-policy.yaml 2024-08-28 05:36:20          277
  Scripts/sample_script.py                       2024-08-28 05:36:20         1964
  Definitions/etsi_nfv_sol001_common_types.yaml  2025-01-29 11:02:26         9093
  Definitions/sample_cnf_types.yaml              2025-01-29 11:02:26         1538
  Definitions/etsi_nfv_sol001_vnfd_types.yaml    2025-01-29 11:02:26        67046
  Definitions/sample_cnf_df_simple.yaml          2025-01-29 11:02:26         6771
  Definitions/sample_cnf_top.vnfd.yaml           2025-01-29 11:02:26          887
  TOSCA-Metadata/TOSCA.meta                      2024-12-19 07:57:02         4661

.. code-block:: console

  $ python3 gen_vnf_pkg.py -t ETSINFV.HELM.V_3
  Generating package and request files into './output/helm_instantiate/' ...
  VNF package: test_helm_instantiate.zip
  Request files: create_req, helm_instantiate_req, helm_terminate_req, helm_scale_out, helm_scale_in, helm_heal
  Contents of the VNF package:
  File Name                                             Modified             Size
  Definitions/                                   2025-01-29 11:11:48            0
  Files/                                         2024-08-28 05:36:20            0
  Scripts/                                       2024-08-28 05:36:20            0
  TOSCA-Metadata/                                2024-08-28 05:36:20            0
  Files/kubernetes/                              2024-08-28 05:36:20            0
  Files/kubernetes/test-chart/                   2024-08-28 05:36:20            0
  Files/kubernetes/test-chart-0.1.0.tgz          2024-08-28 05:36:20         2882
  Files/kubernetes/test-chart/templates/         2024-08-28 05:36:20            0
  Files/kubernetes/test-chart/values.yaml        2024-08-28 05:36:20         1409
  Files/kubernetes/test-chart/.helmignore        2024-08-28 05:36:20          349
  Files/kubernetes/test-chart/Chart.yaml         2024-08-28 05:36:20          125
  Files/kubernetes/test-chart/templates/NOTES.txt 2024-08-28 05:36:20         1554
  Files/kubernetes/test-chart/templates/serviceaccount.yaml 2024-08-28 05:36:20          326
  Files/kubernetes/test-chart/templates/deployment_vdu2.yaml 2024-08-28 05:36:20         1519
  Files/kubernetes/test-chart/templates/deployment_vdu1.yaml 2024-08-28 05:36:20         1598
  Files/kubernetes/test-chart/templates/_helpers.tpl 2024-08-28 05:36:20         1812
  Files/kubernetes/test-chart/templates/service.yaml 2024-08-28 05:36:20          370
  Scripts/sample_script.py                       2024-08-28 05:36:20         1964
  Definitions/etsi_nfv_sol001_common_types.yaml  2025-01-29 11:11:48         9093
  Definitions/sample_cnf_types.yaml              2025-01-29 11:11:48         1538
  Definitions/etsi_nfv_sol001_vnfd_types.yaml    2025-01-29 11:11:48        67046
  Definitions/sample_cnf_df_simple.yaml          2025-01-29 11:11:48         4770
  Definitions/sample_cnf_top.vnfd.yaml           2025-01-29 11:11:48          887
  TOSCA-Metadata/TOSCA.meta                      2024-08-28 05:36:20          285


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
``bearer_token`` need to be changed by your own k8s cluster information,
or replaced with params VIM config file specified with ``-c`` option.

* max_sample_instantiate for ETSINFV.KUBERNETES.V_1
* helm_instantiate_req for ETSINFV.HELM.V_3

.. note::

  ``ssl_ca_cert`` needs to be on one line as shown below.

  .. code-block:: json

    "ssl_ca_cert": "-----BEGIN CERTIFICATE-----\nMIIDB...BH\n3bkddspNikO1\n-----END CERTIFICATE-----\n"

  Please note that line breaks are changed to '``\n``'.


You can also set your own k8s cluster information to ``auth_url``,
``bearer_token``, and ``ssl_ca_cert`` in gen_vnf_pkg.py before running this
tool.

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
