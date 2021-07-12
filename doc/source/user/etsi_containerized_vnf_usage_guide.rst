===================================================================
ETSI NFV-SOL CNF (Containerized VNF) Deployment
===================================================================

This section covers how to deploy ETSI NFV-SOL containerized VNF
in Tacker using Kubernetes VIM.

Overview
--------

The following figure shows an overview of the CNF deployment.

1. Request create VNF

   A user requests tacker-server to create a VNF with tacker-client by
   uploading a VNF Package and requesting ``create VNF``.  The VNF Package
   should contain ``CNF Definition`` in addition to ``VNFD``.  The detailed
   explanation of ``CNF Definition`` and ``VNFD`` can be found in :ref:`Create
   a Kubernetes Object File` and :ref:`Create VNFD`, respectively.

2. Request instantiate VNF

   A user requests tacker-server to instantiate the created VNF by requesting
   ``instantiate VNF`` with instantiate parameters.

3. Call Kubernetes API

   Upon receiving a request from tacker-client, tacker-server redirects it to
   tacker-conductor.  In tacker-conductor, the request is redirected again to
   an appropriate infra-driver (in this case Kubernetes infra-driver) according
   to the contents of the instantiate parameters.  Then, Kubernetes
   infra-driver calls Kubernetes APIs to create a Pod as a VNF.

4. Create a Pod

   Kubernetes Master creates a Pod according to the API calls.

.. figure:: ../_images/etsi_containerized_vnf_usage_guide.png
    :align: left

Prepare Kubernetes VIM
=======================
1. Create a Config File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before register a Kubernetes VIM to tacker, we should create config file.
The following ``vim-k8s.yaml`` file provides necessary information to
register a Kubernetes VIM.
This sample specifies the values of the ``bearer_token`` and ``ssl_ca_cert``
parameters that can be obtained from the Kubernetes Master-node.
For specific methods of obtaining "bearer_token" and "ssl_ca_cert",
please refer to [#first]_.

.. code-block:: console

    $ cat vim-k8s.yaml
    auth_url: "https://192.168.33.100:6443"
    project_name: "default"
    bearer_token: "eyJhbGciOiJSUzI1NiIsImtpZCI6IlBRVDgxQkV5VDNVR1M1WGEwUFYxSXFkZFhJWDYzNklvMEp2WklLMnNFdk0ifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJrdWJlLXN5c3RlbSIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJhZG1pbi10b2tlbi12cnpoaiIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50Lm5hbWUiOiJhZG1pbiIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6ImNhY2VmMzEzLTMzYjYtNDQ5MS1iMWUyLTg0NmQ2N2E0OTdkNSIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDprdWJlLXN5c3RlbTphZG1pbiJ9.R76VIWVZnQxa9NG02HIqux1xTJG4i7dkXsp52T4UU8bvNfsfi18kW_p3ZvaNTxw0yABBcmkYZoOBe4MNP5cTP6TtR_ERZoA5QCViasW_u36rSTBT0-MHRPbkXjJYetzYaFYUO-DlJd3194yOtVHtrxUd8D31qw0f1FlP8BHxblDjZkYlgYSjHCxcwEdwlnYaa0SiH2kl6_oCBRFg8cUfXDeTOmH9XEfdrJ6ubJ4OyqG6YjfiKDDiEHgIehy7s7vZGVwVIPy6EhT1YSOIhY5aF-G9nQSg-GK1V9LIq7petFoW_MIEt0yfNQVXy2D1tBhdJEa1bgtVsLmdlrNVf-m3uA"
    ssl_ca_cert: "-----BEGIN CERTIFICATE-----
    MIICwjCCAaqgAwIBAgIBADANBgkqhkiG9w0BAQsFADASMRAwDgYDVQQDEwdrdWJl
    LWNhMB4XDTIwMDgyNjA5MzIzMVoXDTMwMDgyNDA5MzIzMVowEjEQMA4GA1UEAxMH
    a3ViZS1jYTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALxkeE16lPAd
    pfJj5GJMvZJFcX/CD6EB/LUoKwGmqVoOUQPd3b/NGy+qm+3bO9EU73epUPsVaWk2
    Lr+Z1ua7u+iib/OMsfsSXMZ5OEPgd8ilrTGhXOH8jDkif9w1NtooJxYSRcHEwxVo
    +aXdIJhqKdw16NVP/elS9KODFdRZDfQ6vU5oHSg3gO49kgv7CaxFdkF7QEHbchsJ
    0S1nWMPAlUhA5b8IAx0+ecPlMYUGyGQIQgjgtHgeawJebH3PWy32UqfPhkLPzxsy
    TSxk6akiXJTg6mYelscuxPLSe9UqNvHRIUoad3VnkF3+0CJ1z0qvfWIrzX3w92/p
    YsDBZiP6vi8CAwEAAaMjMCEwDgYDVR0PAQH/BAQDAgKkMA8GA1UdEwEB/wQFMAMB
    Af8wDQYJKoZIhvcNAQELBQADggEBAIbv2ulEcQi019jKz4REy7ZyH8+ExIUBBuIz
    InAkfxNNxV83GkdyA9amk+LDoF/IFLMltAMM4b033ZKO5RPrHoDKO+xCA0yegYqU
    BViaUiEXIvi/CcDpT9uh2aNO8wX5T/B0WCLfWFyiK+rr9qcosFYxWSdU0kFeg+Ln
    YAaeFY65ZWpCCyljGpr2Vv11MAq1Tws8rEs3rg601SdKhBmkgcTAcCzHWBXR1P8K
    rfzd6h01HhIomWzM9xrP2/2KlYRvExDLpp9qwOdMSanrszPDuMs52okXgfWnEqlB
    2ZrqgOcTmyFzFh9h2dj1DJWvCvExybRmzWK1e8JMzTb40MEApyY=
    -----END CERTIFICATE-----"
    type: "kubernetes"

2. Register Kubernetes VIM
~~~~~~~~~~~~~~~~~~~~~~~~~~
We could register Kubernetes VIM to tacker by running the following command:

.. code-block:: console

    $ openstack vim register --config-file CONFIG_FILE KUBERNETES_VIM_NAME --fit-width

Config file in chapter 1 need to be input by parameter --config-file.
After successful execution, VIM information will be displayed.
For example, id.
We can also use authentication methods such as username and password to
register Kubernetes VIM. For details, please refer to the hyperlink in
the [1. Create a config file] chapter.


.. code-block:: console

    $ openstack vim register --config-file vim-k8s.yaml test-vim-k8s --fit-width
    +----------------+-----------------------------------------------------------------------------------------------------------------+
    | Field          | Value                                                                                                           |
    +----------------+-----------------------------------------------------------------------------------------------------------------+
    | auth_cred      | {                                                                                                               |
    |                |     "bearer_token": "***",                                                                                      |
    |                |     "ssl_ca_cert": "b'gAAAAABfknE_feCVMPWTYZsvrifP0C3j-OQAy17n1CQ8CuTNsg1zGdHKSGW-YmOtHaRvma3pib3gLPjYlrybWxm_W |
    |                | IEtXedP1M11TJb1NbNJclbNgw8-anW3RTO3gahXNvt5yU6iD3XOnG_PtrXydDtcoVBqa3Ry4MhK3bbMMD92PN-                          |
    |                | veqQV_pV2xza1WJdE8YhAWevsEWaQPaxjxDdS9PWGg-_n5DtVulCrxGJNmEIi8p8cqnFiFuC4I1b1I0MjDt5f5khE1uKtGvhqBf8RpWS_tvZUo4 |
    |                | TCkeqCeh6TxU1q2xDLZM5T8wWXaHDviYt4qmUVQhPsEi2LoO4kipoR2j7cBfOtr6H82HRpaRyiMM46g6BubTylW-qFaxAmX6SuQzJhjwmXM-62r |
    |                | w8pmUvpDO1RKkyGj76XjcsaDwNUkrl3IVFPVsJAaMgDX3-R4adDqmfVSzXRiA0aF91PAuiOlaAMQY8xFjRxqwZKkXq7rN9uKLo8lH0yBPhWgpq7 |
    |                | 6kZpXprlGaHrgKRnswrnMbBqew3W0sTrTW1hm39-jcVrMomNcXLe0b3Ebru-VKfRloW1c6_jDHZ3lKUo6xNg_2Wy52mrryrRqK3xN9itAuXFM5P |
    |                | Cm2bYXIyb4XfQGR4f6fuJU-6j_lEImjr9xY7bXylNDYKjt9c6AUJSPAxGCraPNrjNjmeXSbI3di_yfqzbzk78XaD4u7vcPNUyiWJj5jJB5tOWIZ |
    |                | gnNPdB5mM4H0-sE2eCwDnrZDRqGCskLTnXHpssROZiZYXGkPaRFQS9XAnswL2oTP5I9kOdVlmI89c63bIJwtgPZmUnIdoy9VyDsACO7cf_b4lMr |
    |                | kZYY1VmQRIhJ0pGY_CbZHrwP1V41g9xQAWDar-ezxFypI_lQqjlcaPA0W1ZDNmoJDVrGQJbqprRGW76JhU2qdZR_GRG-                    |
    |                | DnyWPpmAHjIjtG_6d9d_CGtGs24UTL-Di2B2aLCVaHTGd6ugW7av15ymPgXsXaTox4NVBrU-4l4GgiUN9oE65NF3xfvZ3b2t_bTAxXgCd9gVMgm |
    |                | NGyp8DbdgN9yUuLCBfA2x_KYIBDyQIQv0pevTDaDO3Mfntsq5_KQ0y4A07EKtXkQ7b4qbKoDpksKqlhLJmDm5qsjx3QcybaGXAJ8CTmg0F3vMV8 |
    |                | _mOIkwgj1zegjyUhm0oO-MUr-abuuKg-prejLOzDQpNTYzEnmuvUY4_l4Y3zYm1OlkGoU2yzWOd8vTV7GW9IFSZ76RG9IrrsFLNEXdVlt5ASPaV |
    |                | 1q5CUcsv8mttAEs9HaQe1hPM0Eyigd1xF4u3yPh--                                                                       |
    |                | kYlMFNJkNS8m8vtjPMY7oBfVE0KCeIx7SldYTI_xHuadD6n6w0hBSzS4_F_MujKkysmxZ3rq3WOkDdDaNk80IaT1CfYjiSPpXVPqKgJAPK0ChB- |
    |                | JGkN8vDQfkYLuxypOZBXJt3Q=='",                                                                                   |
    |                |     "auth_url": "https://192.168.33.100:6443",                                                                  |
    |                |     "username": "None",                                                                                         |
    |                |     "key_type": "barbican_key",                                                                                 |
    |                |     "secret_uuid": "***",                                                                                       |
    |                |     "password": "***"                                                                                           |
    |                | }                                                                                                               |
    | auth_url       | https://192.168.33.100:6443                                                                                     |
    | created_at     | 2020-10-19 08:08:12.116040                                                                                      |
    | description    |                                                                                                                 |
    | id             | 8d8373fe-6977-49ff-83ac-7756572ed186                                                                            |
    | is_default     | False                                                                                                           |
    | name           | test-vim-k8s                                                                                                    |
    | placement_attr | {                                                                                                               |
    |                |     "regions": [                                                                                                |
    |                |         "default",                                                                                              |
    |                |         "kube-node-lease",                                                                                      |
    |                |         "kube-public",                                                                                          |
    |                |         "kube-system"                                                                                           |
    |                |     ]                                                                                                           |
    |                | }                                                                                                               |
    | project_id     | 2a505a8efb7a4569af73594bd9904834                                                                                |
    | status         | PENDING                                                                                                         |
    | type           | kubernetes                                                                                                      |
    | updated_at     | None                                                                                                            |
    | vim_project    | {                                                                                                               |
    |                |     "name": "default"                                                                                           |
    |                | }                                                                                                               |
    +----------------+-----------------------------------------------------------------------------------------------------------------+

Also we can check if the status of VIM is REACHABLE by
`openstack vim list` command.

.. code-block:: console

    $ openstack vim list
    +--------------------------------------+----------------+----------------------------------+------------+------------+-----------+
    | ID                                   | Name           | Tenant_id                        | Type       | Is Default | Status    |
    +--------------------------------------+----------------+----------------------------------+------------+------------+-----------+
    | 8d8373fe-6977-49ff-83ac-7756572ed186 | test-vim-k8s   | 2a505a8efb7a4569af73594bd9904834 | kubernetes | False      | REACHABLE |
    +--------------------------------------+----------------+----------------------------------+------------+------------+-----------+

Prepare VNF Package
===================
1. Create Directories of VNF Package
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
TOSCA YAML CSAR file is an archive file using the ZIP file format whose
structure complies with the TOSCA Simple Profile YAML v1.2 Specification.
Here is a sample of building a VNF Package CSAR directory:

.. code-block:: console

    $ mkdir -p deployment/{TOSCA-Metadata,Definitions,Files/kubernetes}

.. _Create a Kubernetes Object File:

2. Create a Kubernetes Object File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A CSAR VNF package shall have a object file that defines Kubernetes resources
to be deployed.
The file name shall have an extension of ".yaml".
Different Kubernetes api resources can be created according to the content of
different yaml files.

.. note:: Please refer to Kubernetes api resource [#second]_ for an example yaml file of
          each resource.

For the types of resources that can be deployed in Victoria, please refer to
following link Kubernetes resource kind support [#third]_.

The following is a simple example of `deployment` resource.

.. code-block:: console

    $ cat ./deployment/Files/kubernetes/deployment.yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: curry-probe-test001
      namespace: default
    spec:
      replicas: 1
      selector:
        matchLabels:
          selector: curry-probe-test001
      template:
        metadata:
          labels:
            selector: curry-probe-test001
            app: webserver
        spec:
          containers:
          - name: nginx-liveness-probe
            image: nginx
            imagePullPolicy: IfNotPresent
            ports:
            - containerPort: 80
              protocol: TCP
          - image: celebdor/kuryr-demo
            imagePullPolicy: IfNotPresent
            name: kuryr-demo-readiness-probe
            ports:
            - containerPort: 8080
              protocol: TCP

.. note:: `metadata.name` in this file should be the same as
          `properties.name` of the corresponding VDU in the deployment flavor
          definition file.
          For the example in this procedure, `metadata.name` is same as
          `topology_template.node_templates.VDU1.properties.name`
          in the helloworld3_df_simple.yaml file.

3. Create a TOSCA.meta File
~~~~~~~~~~~~~~~~~~~~~~~~~~~
The TOSCA.Meta file contains version information for the TOSCA.Meta file, CSAR,
Definitions file, and artifact file.
Name, content-Type, encryption method, and hash value of the Artifact file are
required in the TOSCA.Meta file.
Here is an example of a TOSCA.meta file:

.. code-block:: console

    $ cat ./deployment/TOSCA-Metadata/TOSCA.meta
    TOSCA-Meta-File-Version: 1.0
    Created-by: dummy_user
    CSAR-Version: 1.1
    Entry-Definitions: Definitions/helloworld3_top.vnfd.yaml

    Name: Files/kubernetes/deployment.yaml
    Content-Type: application/yaml
    Algorithm: SHA-256
    Hash: 6a40dfb06764394fb604ae807d1198bc2e2ee8aece3b9483dfde48e53f316a58

4. Download ETSI Definition File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Download official documents.
ETSI GS NFV-SOL 001 [i.4] specifies the structure and format of the VNFD based
on TOSCA specifications.

.. code-block:: console

    $ cd deployment/Definitions
    $ wget https://forge.etsi.org/rep/nfv/SOL001/raw/v2.6.1/etsi_nfv_sol001_common_types.yaml
    $ wget https://forge.etsi.org/rep/nfv/SOL001/raw/v2.6.1/etsi_nfv_sol001_vnfd_types.yaml

.. _Create VNFD:

5. Create VNFD
~~~~~~~~~~~~~~
How to create VNFD composed of plural deployment flavours is described in
VNF Descriptor (VNFD) based on ETSI NFV-SOL001 [#fourth]_.

VNFD will not contain any Kubernetes resource information such as VDU,
Connection points, Virtual links because all required components of CNF will be
specified in Kubernetes resource files.

Following is an example of a VNFD file includes the definition of VNF.

.. code-block:: console

    $ cat helloworld3_top.vnfd.yaml
    tosca_definitions_version: tosca_simple_yaml_1_2

    description: Sample VNF

    imports:
      - etsi_nfv_sol001_common_types.yaml
      - etsi_nfv_sol001_vnfd_types.yaml
      - helloworld3_types.yaml
      - helloworld3_df_simple.yaml

    topology_template:
      inputs:
        selected_flavour:
          type: string
          description: VNF deployment flavour selected by the consumer. It is provided in the API

      node_templates:
        VNF:
          type: company.provider.VNF
          properties:
            flavour_id: { get_input: selected_flavour }
            descriptor_id: b1bb0ce7-ebca-4fa7-95ed-4840d7000003
            provider: Company
            product_name: Sample VNF
            software_version: '1.0'
            descriptor_version: '1.0'
            vnfm_info:
              - Tacker
          requirements:
            #- virtual_link_external # mapped in lower-level templates
            #- virtual_link_internal # mapped in lower-level templates

The `helloworld3_types.yaml` file defines the parameter types and default
values of the VNF.

.. code-block:: console

    $ cat helloworld3_types.yaml
    tosca_definitions_version: tosca_simple_yaml_1_2

    description: VNF type definition

    imports:
      - etsi_nfv_sol001_common_types.yaml
      - etsi_nfv_sol001_vnfd_types.yaml

    node_types:
      company.provider.VNF:
        derived_from: tosca.nodes.nfv.VNF
        properties:
          descriptor_id:
            type: string
            constraints: [ valid_values: [ b1bb0ce7-ebca-4fa7-95ed-4840d7000003 ] ]
            default: b1bb0ce7-ebca-4fa7-95ed-4840d7000003
          descriptor_version:
            type: string
            constraints: [ valid_values: [ '1.0' ] ]
            default: '1.0'
          provider:
            type: string
            constraints: [ valid_values: [ 'Company' ] ]
            default: 'Company'
          product_name:
            type: string
            constraints: [ valid_values: [ 'Sample VNF' ] ]
            default: 'Sample VNF'
          software_version:
            type: string
            constraints: [ valid_values: [ '1.0' ] ]
            default: '1.0'
          vnfm_info:
            type: list
            entry_schema:
              type: string
              constraints: [ valid_values: [ Tacker ] ]
            default: [ Tacker ]
          flavour_id:
            type: string
            constraints: [ valid_values: [ simple ] ]
            default: simple
          flavour_description:
            type: string
            default: "falvour"
        requirements:
          - virtual_link_external:
              capability: tosca.capabilities.nfv.VirtualLinkable
          - virtual_link_internal:
              capability: tosca.capabilities.nfv.VirtualLinkable

`helloworld3_df_simple.yaml` defines the parameter type of VNF input.

.. code-block:: console

    $ cat helloworld3_df_simple.yaml
    tosca_definitions_version: tosca_simple_yaml_1_2

    description: Simple deployment flavour for Sample VNF

    imports:
      - etsi_nfv_sol001_common_types.yaml
      - etsi_nfv_sol001_vnfd_types.yaml
      - helloworld3_types.yaml

    topology_template:
      inputs:
        descriptor_id:
          type: string
        descriptor_version:
          type: string
        provider:
          type: string
        product_name:
          type: string
        software_version:
          type: string
        vnfm_info:
          type: list
          entry_schema:
            type: string
        flavour_id:
          type: string
        flavour_description:
          type: string

      substitution_mappings:
        node_type: company.provider.VNF
        properties:
          flavour_id: simple
        requirements:
          virtual_link_external: []

      node_templates:
        VNF:
          type: company.provider.VNF
          properties:
            flavour_description: A simple flavour

        VDU1:
          type: tosca.nodes.nfv.Vdu.Compute
          properties:
            name: curry-probe-test001
            description: kubernetes controller resource as VDU
            vdu_profile:
              min_number_of_instances: 1
              max_number_of_instances: 3

      policies:
        - scaling_aspects:
            type: tosca.policies.nfv.ScalingAspects
            properties:
              aspects:
                vdu1_aspect:
                  name: vdu1_aspect
                  description: vdu1 scaling aspect
                  max_scale_level: 2
                  step_deltas:
                    - delta_1

        - vdu1_initial_delta:
            type: tosca.policies.nfv.VduInitialDelta
            properties:
              initial_delta:
                number_of_instances: 1
            targets: [ VDU1 ]

        - vdu1_scaling_aspect_deltas:
            type: tosca.policies.nfv.VduScalingAspectDeltas
            properties:
              aspect: vdu1_aspect
              deltas:
                delta_1:
                  number_of_instances: 1
            targets: [ VDU1 ]

        - instantiation_levels:
            type: tosca.policies.nfv.InstantiationLevels
            properties:
              levels:
                instantiation_level_1:
                  description: Smallest size
                  scale_info:
                    vdu1_aspect:
                      scale_level: 0
                instantiation_level_2:
                  description: Largest size
                  scale_info:
                    vdu1_aspect:
                      scale_level: 2
              default_level: instantiation_level_1

        - vdu1_instantiation_levels:
            type: tosca.policies.nfv.VduInstantiationLevels
            properties:
              levels:
                instantiation_level_1:
                  number_of_instances: 1
                instantiation_level_2:
                  number_of_instances: 3
            targets: [ VDU1 ]

.. note:: `VDU1.properties.name` should be same as `metadata.name` that
          defined in Kubernetes object file.
          Therefore, `VDU1.properties.name` should be followed naming rules of
          Kubernetes resource name. About detail of naming rules, please
          refer to Kubernetes document [#fifth]_.

6. Compress VNF Package
~~~~~~~~~~~~~~~~~~~~~~~
CSAR Package should be compressed into a ZIP file for uploading.
Following commands are an example of compressing a VNF Package:

.. code-block:: console

    $ cd -
    $ cd ./deployment
    $ zip deployment.zip -r Definitions/ Files/ TOSCA-Metadata/
    $ ls deployment
    deployment.zip    Definitions    Files    TOSCA-Metadata

Create and Upload VNF Package
=============================
We need to create an empty VNF package object in tacker and upload compressed
VNF package created in previous section.

1. Create VNF Package
~~~~~~~~~~~~~~~~~~~~~
An empty vnf package could be created by command
`openstack vnf package create`.
After create a VNF Package successfully, some information including ID, Links,
Onboarding State, Operational State, and Usage State will be returned.
When the Onboarding State is CREATED, the Operational State is DISABLED,
and the Usage State is NOT_IN_USE, indicate the creation is successful.

.. code-block:: console

    $ openstack vnf package create
    +-------------------+-------------------------------------------------------------------------------------------------+
    | Field             | Value                                                                                           |
    +-------------------+-------------------------------------------------------------------------------------------------+
    | ID                | 08d00a5c-e8aa-4219-9412-411458eaa7d2                                                            |
    | Links             | {                                                                                               |
    |                   |     "self": {                                                                                   |
    |                   |         "href": "/vnfpkgm/v1/vnf_packages/08d00a5c-e8aa-4219-9412-411458eaa7d2"                 |
    |                   |     },                                                                                          |
    |                   |     "packageContent": {                                                                         |
    |                   |         "href": "/vnfpkgm/v1/vnf_packages/08d00a5c-e8aa-4219-9412-411458eaa7d2/package_content" |
    |                   |     }                                                                                           |
    |                   | }                                                                                               |
    | Onboarding State  | CREATED                                                                                         |
    | Operational State | DISABLED                                                                                        |
    | Usage State       | NOT_IN_USE                                                                                      |
    | User Defined Data | {}                                                                                              |
    +-------------------+-------------------------------------------------------------------------------------------------+

2. Upload VNF Package
~~~~~~~~~~~~~~~~~~~~~
Upload the VNF package created above in to the VNF Package by running the
following command
`openstack vnf package upload --path <path of vnf package> <vnf package ID>`
Here is an example of upload VNF package:

.. code-block:: console

  $ openstack vnf package upload --path deployment.zip 08d00a5c-e8aa-4219-9412-411458eaa7d2
  Upload request for VNF package 08d00a5c-e8aa-4219-9412-411458eaa7d2 has been accepted.

3. Check VNF Package Status
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Check the VNF Package Status by `openstack vnf package list` command.
Find the item which the id is same as the created vnf package id, when the
Onboarding State is ONBOARDED, and the Operational State is ENABLED, and the
Usage State is NOT_IN_USE, indicate the VNF Package is uploaded successfully.

.. code-block:: console

    $ openstack vnf package list
    +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
    | Id                                   | Vnf Product Name | Onboarding State | Usage State | Operational State | Links                                                                                           |
    +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
    | 08d00a5c-e8aa-4219-9412-411458eaa7d2 | Sample VNF       | ONBOARDED        | NOT_IN_USE  | ENABLED           | {                                                                                               |
    |                                      |                  |                  |             |                   |     "self": {                                                                                   |
    |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/08d00a5c-e8aa-4219-9412-411458eaa7d2"                 |
    |                                      |                  |                  |             |                   |     },                                                                                          |
    |                                      |                  |                  |             |                   |     "packageContent": {                                                                         |
    |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/08d00a5c-e8aa-4219-9412-411458eaa7d2/package_content" |
    |                                      |                  |                  |             |                   |     }                                                                                           |
    |                                      |                  |                  |             |                   | }                                                                                               |
    +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+

Create VNF
===========
1. Get VNFD ID
~~~~~~~~~~~~~~

The VNFD ID of a uploaded vnf package could be found by
`openstack vnf package show <VNF package ID>` command.
Here is an example of checking VNFD-ID value:

.. code-block:: console

    $ openstack vnf package show 08d00a5c-e8aa-4219-9412-411458eaa7d2
    +----------------------+------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field                | Value                                                                                                                                          |
    +----------------------+------------------------------------------------------------------------------------------------------------------------------------------------+
    | Additional Artifacts | [                                                                                                                                              |
    |                      |     {                                                                                                                                          |
    |                      |         "artifactPath": "Files/kubernetes/deployment.yaml",                                                                                    |
    |                      |         "checksum": {                                                                                                                          |
    |                      |             "algorithm": "SHA-256",                                                                                                            |
    |                      |             "hash": "6a40dfb06764394fb604ae807d1198bc2e2ee8aece3b9483dfde48e53f316a58"                                                         |
    |                      |         },                                                                                                                                     |
    |                      |         "metadata": {}                                                                                                                         |
    |                      |     }                                                                                                                                          |
    |                      | ]                                                                                                                                              |
    | Checksum             | {                                                                                                                                              |
    |                      |     "algorithm": "sha512",                                                                                                                     |
    |                      |     "hash": "f51de874f4dd831986aff19b4d74b8e30009681683ff2d25b2969a2c679ae3a78f6bd79cc131d00e92a5e264cd8df02e2decb8b3f2acc6e877161977cdbdd304" |
    |                      | }                                                                                                                                              |
    | ID                   | 08d00a5c-e8aa-4219-9412-411458eaa7d2                                                                                                           |
    | Links                | {                                                                                                                                              |
    |                      |     "self": {                                                                                                                                  |
    |                      |         "href": "/vnfpkgm/v1/vnf_packages/08d00a5c-e8aa-4219-9412-411458eaa7d2"                                                                |
    |                      |     },                                                                                                                                         |
    |                      |     "packageContent": {                                                                                                                        |
    |                      |         "href": "/vnfpkgm/v1/vnf_packages/08d00a5c-e8aa-4219-9412-411458eaa7d2/package_content"                                                |
    |                      |     }                                                                                                                                          |
    |                      | }                                                                                                                                              |
    | Onboarding State     | ONBOARDED                                                                                                                                      |
    | Operational State    | ENABLED                                                                                                                                        |
    | Software Images      |                                                                                                                                                |
    | Usage State          | NOT_IN_USE                                                                                                                                     |
    | User Defined Data    | {}                                                                                                                                             |
    | VNF Product Name     | Sample VNF                                                                                                                                     |
    | VNF Provider         | Company                                                                                                                                        |
    | VNF Software Version | 1.0                                                                                                                                            |
    | VNFD ID              | b1bb0ce7-ebca-4fa7-95ed-4840d7000003                                                                                                           |
    | VNFD Version         | 1.0                                                                                                                                            |
    +----------------------+------------------------------------------------------------------------------------------------------------------------------------------------+

2. Execute Create VNF Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
We could create VNF by running `openstack vnflcm create <VNFD ID>`.
After the command is executed, the generated ID is `VNF instance ID`.

.. code-block:: console

    $ openstack vnflcm create b1bb0ce7-ebca-4fa7-95ed-4840d7000003
    +--------------------------+---------------------------------------------------------------------------------------------+
    | Field                    | Value                                                                                       |
    +--------------------------+---------------------------------------------------------------------------------------------+
    | ID                       | 92cf0ccb-e575-46e2-9c0d-30c67e75aaf6                                                        |
    | Instantiation State      | NOT_INSTANTIATED                                                                            |
    | Links                    | {                                                                                           |
    |                          |     "self": {                                                                               |
    |                          |         "href": "/vnflcm/v1/vnf_instances/92cf0ccb-e575-46e2-9c0d-30c67e75aaf6"             |
    |                          |     },                                                                                      |
    |                          |     "instantiate": {                                                                        |
    |                          |         "href": "/vnflcm/v1/vnf_instances/92cf0ccb-e575-46e2-9c0d-30c67e75aaf6/instantiate" |
    |                          |     }                                                                                       |
    |                          | }                                                                                           |
    | VNF Instance Description | None                                                                                        |
    | VNF Instance Name        | None                                                                                        |
    | VNF Product Name         | Sample VNF                                                                                  |
    | VNF Provider             | Company                                                                                     |
    | VNF Software Version     | 1.0                                                                                         |
    | VNFD ID                  | b1bb0ce7-ebca-4fa7-95ed-4840d7000003                                                        |
    | VNFD Version             | 1.0                                                                                         |
    +--------------------------+---------------------------------------------------------------------------------------------+

Instantiate VNF
===============
1. Set the Value to the Request Parameter File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Get the ID of target VIM.

.. code-block:: console

    $ openstack vim list
    +--------------------------------------+----------------+----------------------------------+------------+------------+-----------+
    | ID                                   | Name           | Tenant_id                        | Type       | Is Default | Status    |
    +--------------------------------------+----------------+----------------------------------+------------+------------+-----------+
    | 8d8373fe-6977-49ff-83ac-7756572ed186 | test-vim-k8s   | 2a505a8efb7a4569af73594bd9904834 | kubernetes | False      | REACHABLE |
    +--------------------------------------+----------------+----------------------------------+------------+------------+-----------+

A json file includes path of Kubernetes resource definition file and Kubernetes
VIM information should be provided while instantiating a containerized VNF.
Here is an example of json file:

`additionalParams` includes path of Kubernetes resource definition file,
notice that `lcm-kubernetes-def-files` should be a list.
The vimConnectionInfo includes id whose value can be defined autonomously,
vimId and vimType.

.. code-block:: console

    $ cat ./instance_kubernetes.json
    {
      "flavourId": "simple",
      "additionalParams": {
        "lcm-kubernetes-def-files": [
          "Files/kubernetes/deployment.yaml"
        ]
      },
      "vimConnectionInfo": [
        {
          "id": "8a3adb69-0784-43c7-833e-aab0b6ab4470",
          "vimId": "8d8373fe-6977-49ff-83ac-7756572ed186",
          "vimType": "kubernetes"
        }
      ]
    }

2. Execute the Instantiation Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Run `openstack vnflcm instantiate <VNF instance ID> <json file>` to instantiate
a VNF.

The `VNF instance ID` is the ID generated after the `openstack vnflcm create`
command is executed. We can find it in the [2. Execute Create VNF command]
chapter.

.. code-block:: console

    $ openstack vnflcm instantiate 92cf0ccb-e575-46e2-9c0d-30c67e75aaf6 instance_kubernetes.json
    Instantiate request for VNF Instance 92cf0ccb-e575-46e2-9c0d-30c67e75aaf6 has been accepted.

3. Check the Instantiation State
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
We could check the Instantiation State by running the following command.
When the Instantiation State is INSTANTIATED, indicate the instantiation is
successful.

.. code-block:: console

    $ openstack vnflcm show 92cf0ccb-e575-46e2-9c0d-30c67e75aaf6
    +--------------------------+-------------------------------------------------------------------------------------------+
    | Field                    | Value                                                                                     |
    +--------------------------+-------------------------------------------------------------------------------------------+
    | ID                       | 92cf0ccb-e575-46e2-9c0d-30c67e75aaf6                                                      |
    | Instantiated Vnf Info    | {                                                                                         |
    |                          |     "flavourId": "simple",                                                                |
    |                          |     "vnfState": "STARTED",                                                                |
    |                          |     "scaleStatus": [                                                                      |
    |                          |         {                                                                                 |
    |                          |             "aspectId": "vdu1_aspect",                                                    |
    |                          |             "scaleLevel": 0                                                               |
    |                          |         }                                                                                 |
    |                          |     ],                                                                                    |
    |                          |     "extCpInfo": [],                                                                      |
    |                          |     "vnfcResourceInfo": [                                                                 |
    |                          |         {                                                                                 |
    |                          |             "id": "686b356f-8096-4e24-99e5-3c81d36341be",                                 |
    |                          |             "vduId": "VDU1",                                                              |
    |                          |             "computeResource": {                                                          |
    |                          |                 "vimConnectionId": null,                                                  |
    |                          |                 "resourceId": "curry-probe-test001-766bdd79bf-wgc7m",                     |
    |                          |                 "vimLevelResourceType": "Deployment"                                      |
    |                          |             },                                                                            |
    |                          |             "storageResourceIds": []                                                      |
    |                          |         }                                                                                 |
    |                          |     ],                                                                                    |
    |                          |     "additionalParams": {}                                                                |
    |                          | }                                                                                         |
    | Instantiation State      | INSTANTIATED                                                                              |
    | Links                    | {                                                                                         |
    |                          |     "self": {                                                                             |
    |                          |         "href": "/vnflcm/v1/vnf_instances/92cf0ccb-e575-46e2-9c0d-30c67e75aaf6"           |
    |                          |     },                                                                                    |
    |                          |     "terminate": {                                                                        |
    |                          |         "href": "/vnflcm/v1/vnf_instances/92cf0ccb-e575-46e2-9c0d-30c67e75aaf6/terminate" |
    |                          |     },                                                                                    |
    |                          |     "heal": {                                                                             |
    |                          |         "href": "/vnflcm/v1/vnf_instances/92cf0ccb-e575-46e2-9c0d-30c67e75aaf6/heal"      |
    |                          |     }                                                                                     |
    |                          | }                                                                                         |
    | VIM Connection Info      | [                                                                                         |
    |                          |     {                                                                                     |
    |                          |         "id": "8a3adb69-0784-43c7-833e-aab0b6ab4470",                                     |
    |                          |         "vimId": "8d8373fe-6977-49ff-83ac-7756572ed186",                                  |
    |                          |         "vimType": "kubernetes",                                                          |
    |                          |         "interfaceInfo": {},                                                              |
    |                          |         "accessInfo": {}                                                                  |
    |                          |     }                                                                                     |
    |                          | ]                                                                                         |
    | VNF Instance Description | None                                                                                      |
    | VNF Instance Name        | None                                                                                      |
    | VNF Product Name         | Sample VNF                                                                                |
    | VNF Provider             | Company                                                                                   |
    | VNF Software Version     | 1.0                                                                                       |
    | VNFD ID                  | b1bb0ce7-ebca-4fa7-95ed-4840d7000003                                                      |
    | VNFD Version             | 1.0                                                                                       |
    +--------------------------+-------------------------------------------------------------------------------------------+

4. Check the Deployment in Kubernetes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To test a containerized VNF is running in target Kubernetes VIM environment,
we can check by running the following command.
When the READY is 1/1, indicate the deployment is created successfully.

.. code-block:: console

    $ kubectl get deploy
    NAME                  READY   UP-TO-DATE   AVAILABLE   AGE
    curry-probe-test001   1/1     1            1           8m43s

References
==========
.. [#first] https://docs.openstack.org/tacker/latest/install/kubernetes_vim_installation.html
.. [#second] https://opendev.org/openstack/tacker/src/branch/master/tacker/tests/unit/vnfm/infra_drivers/kubernetes/kubernetes_api_resource
.. [#third] https://specs.openstack.org/openstack/tacker-specs/specs/victoria/container-network-function.html#kubernetes-resource-kind-support
.. [#fourth] https://docs.openstack.org/tacker/latest/user/vnfd-sol001.html
.. [#fifth] https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#dns-subdomain-names
