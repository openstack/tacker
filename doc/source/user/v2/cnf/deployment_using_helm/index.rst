======================================
ETSI NFV-SOL CNF Deployment using Helm
======================================

This section covers how to deploy ETSI NFV-SOL containerized VNF
using Helm in Tacker v2 API.

.. note::

  v1 VNF LCM API also support CNF deployment using Helm and
  its requirements are different from v2 VNF LCM API.
  For details on using Helm in v1 API, please refer to
  :doc:`/user/mgmt_driver_deploy_k8s_and_cnf_with_helm`.


Overview
--------

The following figure shows an overview of the CNF deployment.

1. Request create VNF

   A user requests tacker-server to create a VNF with tacker-client by
   uploading a VNF Package and requesting ``create VNF``. The VNF Package
   should contain ``Helm chart`` in addition to ``VNFD``.

2. Request instantiate VNF

   A user requests tacker-server to instantiate the created VNF by requesting
   ``instantiate VNF`` with instantiate parameters.

3. Execute Helm commands

   Upon receiving a request from tacker-client, tacker-server redirects it to
   tacker-conductor.  In tacker-conductor, the request is redirected again to
   an appropriate infra-driver (in this case Helm infra-driver) according
   to the contents of the instantiate parameters.
   Then, Helm infra-driver executes Helm commands.

4. Call Kubernetes API via Helm

   Helm calls Kubernetes APIs to create Pods as a VNF.

5. Create Pods

   Kubernetes Master creates Pods according to the API calls.

.. figure:: img/deployment_using_helm.svg


Prepare Helm VIM
================

1. Create a Config File
~~~~~~~~~~~~~~~~~~~~~~~

Before register a Helm VIM to tacker, we should create config file.
The following sample provides required information to
register a Helm VIM.
This sample specifies the values of the ``bearer_token`` and ``ssl_ca_cert``
parameters that can be obtained from the Kubernetes Master-node.
For specific methods of obtaining ``bearer_token`` and ``ssl_ca_cert``,
please refer to :doc:`/install/kubernetes_vim_installation`.
It also contains the ``extra`` field.
For using Helm, ``use_helm`` in ``extra`` must be set as true.


.. code-block:: yaml

  auth_url: "https://192.168.56.10:6443"
  bearer_token: "eyJhbGciOiJSUzI1NiIsImtpZCI6IkdVazBPakx4Q2NsUjJjNHhsZFdaaXJMSHVQMUo4NkdMS0toamlSaENiVFUifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tazhzdmltIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQubmFtZSI6ImRlZmF1bHQiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiJhNTIzYzFhMi1jYmU5LTQ1Y2YtYTc5YS00ZDA4MDYwZDE3NmEiLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6ZGVmYXVsdDpkZWZhdWx0In0.BpKAAQLjXMIpJIjqQDsGtyh1a-Ij8e-YOVRv0md_iOGXd1KLR-qreM6xA-Ni8WFILzq3phaZU6npET8PlfhQ6csF5u20OT2SoZ7iAotHXpCcYkRdrUd2oO5KxSFTkOhasaN1pQ3pZyaFYUZbwwmLK3I31rG4Br2VbZQ7Qu8wFOXUK-syBGF48vIPZ5JQ3K00KNxpuEcGybMK5LtdSKZ25Ozp_I2oqm3KBZMPMfWwaUnvuRnyly13tsiXudPt_9H78AxLubMo3rcvECJU2y_zZLiavcZKXAz-UmHulxtz_XZ80hMu-XOpYWEYrOB0Lt0hB59ZoY1y3OvJElTfPyrwWw"
  ssl_ca_cert: "-----BEGIN CERTIFICATE-----
  MIIDBTCCAe2gAwIBAgIIa76wZDxLNAowDQYJKoZIhvcNAQELBQAwFTETMBEGA1UE
  AxMKa3ViZXJuZXRlczAeFw0yMzExMDYwMDA3MzBaFw0zMzExMDMwMDEyMzBaMBUx
  EzARBgNVBAMTCmt1YmVybmV0ZXMwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEK
  AoIBAQDd0LBXGxVexr09mVFNSXWQq3TN66IIcXCBAMbIWI4EiQ8Y0zI4hSwADdK2
  ltYSdWw7wq3/YTFHK8/YTY7Jvd9/k3UJrqkZ6kBtL20pJUPXNJVLE/hRzsqEnHHv
  cfqYZTHvTY4g7qNcMOcfl/oDUGUMfpQT2gs6xoNl0WX/1+QeQbadx1kWaD2Ii45F
  d8TR+c4wccxNaLArk3ok4h1PNeAwra4mRmBHQQ2wFjkTYGl4+ss3v1yoUJkrQjXL
  RgzLufeXaz8eRTi36HkjudGKfS3OnUeke3uBN7usW58FFJ8TdKOhuoguRm53kj6+
  TwXtZCOPzn4gNxq6xJE1Xj2hwFfpAgMBAAGjWTBXMA4GA1UdDwEB/wQEAwICpDAP
  BgNVHRMBAf8EBTADAQH/MB0GA1UdDgQWBBRdmQ4r63pXBHIO8ODqxROE7x+aizAV
  BgNVHREEDjAMggprdWJlcm5ldGVzMA0GCSqGSIb3DQEBCwUAA4IBAQBeQ/9+bzRe
  qbA02MfYnN3vycGhDObcAoiDIMIutojFTpx4hGZjqVgTRpLH5ReddwR4kkxn3NRg
  weCVkNkhzyGze64nb11qZG71olaOQRMYzyN2hYfmbq7MXSvmJQQYIr1OewaRk+xl
  TyG1XRXoD2IEaHEvG0+pQJlDerd5Z6S1fkPaKZtcRbM/E6y5VXMV6hegN4MwHZSI
  Ll1uEBTxUzzTm3dnl1KL8GDg05ajoYcyL3X/0aWsb/MFhtIlXe2CMxu5qUkLBhzy
  fCfX4cZpI5KFxMgdmAEoaGbNy7iqsGrLFtEmub2gdEBIVNr7vgOk4OeQ9Uodj6K7
  jK97z+cupc5G
  -----END CERTIFICATE-----"
  project_name: "default"
  type: "kubernetes"
  extra:
      use_helm: true


1. Register Helm VIM
~~~~~~~~~~~~~~~~~~~~

We could register Helm VIM to tacker by running the following command:

.. code-block:: console

  $ openstack vim register --config-file CONFIG_FILE Helm_VIM_NAME --fit-width


Config file in chapter 1 need to be input by parameter --config-file.
After successful execution, VIM information will be displayed.

.. code-block:: console

  $ openstack vim register --config-file vim-k8s.yaml test-vim-helm --fit-width
  +----------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field          | Value                                                                                                                                                                                                                                     |
  +----------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | auth_cred      | {                                                                                                                                                                                                                                         |
  |                |     "bearer_token": "***",                                                                                                                                                                                                                |
  |                |     "ssl_ca_cert": "b'gAAAAABlcTEl6uPnFB4aCDCpRI8fuMI7r9K6lBC2nW0IiYpd3HifxUsXI20wxuTRpOVRSVasev_NuxfZxLneAfgwCF_FYed9cj0vng-Q32v2RM8EMziTfzNjV8qnESgMOtcsb10h80917tYSIoJOWhPdcLUPDKKL-Or3vJWzudRFnltI13GnK40ytVOaN4gF-wAE8zEL7gOq7iyC2L4 |
  |                | oVmZeb2VVAnp71KvJPMAe3hM0IPF2dgpqSEfImG8ipmzLnc_JGG40ybiaNG7lDjwSMDnjrEjiX32iTmsifOSr02mBhrrn7hoG7mbbcTfhCymjSjoutQKuXMBflAM8ytgBk6C70HtIBQJgNLIYGHrTMyEH6kPynM79EMxfENJVSxfmLzwwnw6YWc01oVIqW5GuK6cZDho4pbb8r-CxZk2XU0DOKRqSSju-         |
  |                | B8wBoeI4EaKSAKhOVtQrsM6sQoz0yOF5NNH8tcebZsUFYO8jp6-xk8w91GhK6CFVL39_vuoyiAS-zQH0S_GA3tl8pTpufAIr_TShq6Jc7hac1cBWaeqsuofC-Ny6jhdN5-AMx0EsVzx_3tkOD_pA2wP8PkFO8gxC4egjdNVdOdU_ggXElcnsJJeBP5ljTmisu3sn_fqFMxpJeqdus-bquX8ErLPfGBjCy-        |
  |                | cWDIRmc1XaLHZ88Ju2zqjDMfjotNXJeK_iYeBiEMNwburTy-VAmucPS6bdI8Y1dPWcT-V6Nk-                                                                                                                                                                 |
  |                | jMl1ydUHptX42NXrxO83NjTIb5KDZQ8-AD7eQ1Bq2H6AkhZIw24qzLme6KTupzo-9CuzF3HElmwuy0NtyjvXhn4X36xlYJk-y9LYPV6KyvYPmND9uzskemDma0VCRbbIgdfar0AER0wDZlwv7Ra0G12CUKbxZVSXowS9nl-                                                                   |
  |                | FC5ApT7NAGhKAP8BfyUnjxMqA641Yk8DVLXmyztYYYYSoQ-6OcKKfTEvbYvfDSeHH50IGzHfMkx5YkNExqGREjjYkVwjO0ZW1odRoXISXtfop0Xfpqkun_ckJXNYCXKEn6bc9q3EnSaIxI2NOyhsjZ3eDF-VHFo8K_H_5iBrqoqWOUwx-uWm4xKZ7GtOUhPL4_w9XSiBFcMSf0uCtvbcWsu_B00itWYMipPUbYWD- |
  |                | Un9p5ESmaFbPW4B9912sszjbJzQyawqV_LYoW6MPgLYEd46Oqn9RkxGqdj8DKJpUfBb_DKC3G29OiStaW6IWLBNmsNqb9xCy5UsF_sM_fLEbbAR76LEAau2Fhb5DTzHr27h_Ri8GsXfTWX8r61pseh41hZAmwpyAW4-WAxhx158gR14hPBrjecPuPSs_vB-                                           |
  |                | 6lJkuu7NFQIlj2uQBSP_gkaJ4mg3tIzcVfQeyTcE5KhfJWy2TdyI7pIe1vthjzI8pgWxO_dUAkkIPA6emA01QxzzKNCHa0KCYGi_noTwnasb_vwDL0sqjd6eUwFjCzeEuhPex3aQkYxrg2wxWFxg58bLb_it8U1wqHEWfiCH4a5XE4TCnBbPF2DiRZ9KHkRgdAcz2Wo-                                  |
  |                | iNx0ghJ0u25Phi6nHuxbtEOghHZH7cgx6KaZ300ilA1g=='",                                                                                                                                                                                         |
  |                |     "auth_url": "https://192.168.56.10:6443",                                                                                                                                                                                             |
  |                |     "username": "None",                                                                                                                                                                                                                   |
  |                |     "key_type": "barbican_key",                                                                                                                                                                                                           |
  |                |     "secret_uuid": "***"                                                                                                                                                                                                                  |
  |                | }                                                                                                                                                                                                                                         |
  | auth_url       | https://192.168.56.10:6443                                                                                                                                                                                                                |
  | created_at     | 2023-12-07 02:42:46.328344                                                                                                                                                                                                                |
  | description    |                                                                                                                                                                                                                                           |
  | extra          | use_helm=True                                                                                                                                                                                                                             |
  | id             | 9c37f36f-f569-4259-b388-d550e55dd65c                                                                                                                                                                                                      |
  | is_default     | False                                                                                                                                                                                                                                     |
  | name           | test-vim-helm                                                                                                                                                                                                                             |
  | placement_attr | {                                                                                                                                                                                                                                         |
  |                |     "regions": [                                                                                                                                                                                                                          |
  |                |         "default",                                                                                                                                                                                                                        |
  |                |         "kube-node-lease",                                                                                                                                                                                                                |
  |                |         "kube-public",                                                                                                                                                                                                                    |
  |                |         "kube-system"                                                                                                                                                                                                                     |
  |                |     ]                                                                                                                                                                                                                                     |
  |                | }                                                                                                                                                                                                                                         |
  | project_id     | ebbc6cf1a03d49918c8e408535d87268                                                                                                                                                                                                          |
  | status         | ACTIVE                                                                                                                                                                                                                                    |
  | type           | kubernetes                                                                                                                                                                                                                                |
  | updated_at     | None                                                                                                                                                                                                                                      |
  | vim_project    | {                                                                                                                                                                                                                                         |
  |                |     "name": "default"                                                                                                                                                                                                                     |
  |                | }                                                                                                                                                                                                                                         |
  +----------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


Also we can check if the status of VIM is ACTIVE by
:command:`openstack vim list` command.

.. code-block:: console

  $ openstack vim list
  +--------------------------------------+---------------+----------------------------------+------------+------------+--------+
  | ID                                   | Name          | Tenant_id                        | Type       | Is Default | Status |
  +--------------------------------------+---------------+----------------------------------+------------+------------+--------+
  | 9c37f36f-f569-4259-b388-d550e55dd65c | test-vim-helm | ebbc6cf1a03d49918c8e408535d87268 | kubernetes | False      | ACTIVE |
  +--------------------------------------+---------------+----------------------------------+------------+------------+--------+


.. note::

    In the return of vim list,
    ``Type`` is shown as kubernetes for both Helm VIM and Kubernetes VIM.


Prepare VNF Package
===================

1. Create Directories of VNF Package
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TOSCA YAML CSAR file is an archive file using the ZIP file format whose
structure complies with the TOSCA Simple Profile YAML v1.2 Specification.
Here is a sample of building a VNF Package CSAR directory:

.. code-block:: console

  $ mkdir -p deployment/{TOSCA-Metadata,Definitions,Files/kubernetes}


2. Create a Helm chart
~~~~~~~~~~~~~~~~~~~~~~

A CSAR VNF package shall have Helm chart
that defines Kubernetes resources to be deployed.
The file name shall have an extension of ".yaml" and
all chart files shall be compressed to ".tgz".

To map Kubernetes resources defined in Helm chart
to VDUs defined by VNFD,
the metadata.name in Helm chart shall be described
in compliance with the following rules.

``metadata.name`` must be set as
"properties.name defiend in VNFD"+"-"
+"Unique string in the release (e.g. release name)".
"Unique string in the release" must not include "-".

The following shows the sample description.

.. code-block:: yaml

  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: vdu1-{{ .Release.Name }}
    labels:
      {{- include "localhelm.labels" . | nindent 4 }
  spec:
    {{- if not .Values.autoscaling.enabled }}
    replicas: {{ .Values.replicaCountVdu1 }}
    {{- end }}


.. note::

  In this sample, the value of ``replicas`` is specified as
  ``replicaCountVdu1`` with the helm commands.
  Such a parameter name needs to be provided as ``helm_value_names``
  in the instantiate request parameter.
  A sample instantiate request parameter
  is described in :ref:`helm_request`.


.. note::

  Since version 1 VNF LCM API supports using external repositories,
  a chart file may be contained within the VNF package
  or contained in external repositories.
  On the other hand, version 2 VNF LCM API requires
  Helm chart file to be contained in the VNF package.


3. Create a TOSCA.meta File
~~~~~~~~~~~~~~~~~~~~~~~~~~~
The TOSCA.Meta file contains version information for the TOSCA.Meta file, CSAR,
Definitions file, and artifact file.
Name, content-Type, encryption method, and hash value of the Artifact file are
required in the TOSCA.Meta file.
Here is an example of a TOSCA.meta file:

.. code-block:: yaml

  TOSCA-Meta-File-Version: 1.0
  Created-by: dummy_user
  CSAR-Version: 1.1
  Entry-Definitions: Definitions/sample_cnf_top.vnfd.yaml

  Name: Files/kubernetes/test-chart-0.1.0.tgz
  Content-Type: test-data
  Algorithm: SHA-256
  Hash: fa05dd35f45adb43ff1c6c77675ac82c477c5a55a3ad14a87a6b542c21cf4f7c


4. Download ETSI Definition File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download official documents.
ETSI GS NFV-SOL 001 [i.4] specifies the structure and format of the VNFD based
on TOSCA specifications.

.. code-block:: console

  $ cd deployment/Definitions
  $ wget https://forge.etsi.org/rep/nfv/SOL001/raw/v2.6.1/etsi_nfv_sol001_common_types.yaml
  $ wget https://forge.etsi.org/rep/nfv/SOL001/raw/v2.6.1/etsi_nfv_sol001_vnfd_types.yaml


5. Create VNFD
~~~~~~~~~~~~~~

How to create VNFD composed of plural deployment flavours is described in
:doc:`/user/vnfd-sol001`.

VNFD will not contain any Kubernetes resource information such as
Connection points, Virtual links because all required components of CNF will be
specified in Kubernetes resource files.

Following is an example of a VNFD file includes the definition of VNF.

.. code-block:: yaml

  tosca_definitions_version: tosca_simple_yaml_1_2
  description: Sample VNF
  imports:
    - etsi_nfv_sol001_common_types.yaml
    - etsi_nfv_sol001_vnfd_types.yaml
    - sample_cnf_types.yaml
    - sample_cnf_df_simple.yaml
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
          descriptor_id: b1bb0ce7-ebca-4fa7-95ed-4840d7000000
          provider: Company
          product_name: Sample VNF
          software_version: '1.0'
          descriptor_version: '1.0'
          vnfm_info:
            - Tacker
        requirements:
          #- virtual_link_external # mapped in lower-level templates
          #- virtual_link_internal # mapped in lower-level templates


The ``sample_cnf_types.yaml`` file defines the parameter types
and default values of the VNF.

.. code-block:: yaml

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
          constraints: [ valid_values: [ b1bb0ce7-ebca-4fa7-95ed-4840d7000000 ] ]
          default: b1bb0ce7-ebca-4fa7-95ed-4840d7000000
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
          constraints: [ valid_values: [ simple,complex ] ]
          default: simple
        flavour_description:
          type: string
          default: ""
      requirements:
        - virtual_link_external:
            capability: tosca.capabilities.nfv.VirtualLinkable
        - virtual_link_internal:
            capability: tosca.capabilities.nfv.VirtualLinkable
      interfaces:
        Vnflcm:
          type: tosca.interfaces.nfv.Vnflcm


``sample_cnf_df_simple.yaml`` defines the parameter type of VNF input.

.. code-block:: yaml

  tosca_definitions_version: tosca_simple_yaml_1_2
  description: Simple deployment flavour for Sample VNF
  imports:
    - etsi_nfv_sol001_common_types.yaml
    - etsi_nfv_sol001_vnfd_types.yaml
    - sample_cnf_types.yaml
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
        interfaces:
          Vnflcm:
            instantiate_start:
              implementation: sample-script
            instantiate_end:
              implementation: sample-script
            terminate_start:
              implementation: sample-script
            terminate_end:
              implementation: sample-script
            scale_start:
              implementation: sample-script
            scale_end:
              implementation: sample-script
            heal_start:
              implementation: sample-script
            heal_end:
              implementation: sample-script
            modify_information_start:
              implementation: sample-script
            modify_information_end:
              implementation: sample-script
        artifacts:
          sample-script:
            description: Sample script
            type: tosca.artifacts.Implementation.Python
            file: ../Scripts/sample_script.py
      VDU1:
        type: tosca.nodes.nfv.Vdu.Compute
        properties:
          name: vdu1
          description: VDU1 compute node
          vdu_profile:
            min_number_of_instances: 1
            max_number_of_instances: 3
      VDU2:
        type: tosca.nodes.nfv.Vdu.Compute
        properties:
          name: vdu2
          description: VDU2 compute node
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
              vdu2_aspect:
                name: vdu2_aspect
                description: vdu2 scaling aspect
                max_scale_level: 2
                step_deltas:
                  - delta_1
      - VDU1_initial_delta:
          type: tosca.policies.nfv.VduInitialDelta
          properties:
            initial_delta:
              number_of_instances: 1
          targets: [ VDU1 ]
      - VDU1_scaling_aspect_deltas:
          type: tosca.policies.nfv.VduScalingAspectDeltas
          properties:
            aspect: vdu1_aspect
            deltas:
              delta_1:
                number_of_instances: 1
          targets: [ VDU1 ]
      - VDU2_initial_delta:
          type: tosca.policies.nfv.VduInitialDelta
          properties:
            initial_delta:
              number_of_instances: 1
          targets: [ VDU2 ]
      - VDU2_scaling_aspect_deltas:
          type: tosca.policies.nfv.VduScalingAspectDeltas
          properties:
            aspect: vdu2_aspect
            deltas:
              delta_1:
                number_of_instances: 1
          targets: [ VDU2 ]
      - instantiation_levels:
          type: tosca.policies.nfv.InstantiationLevels
          properties:
            levels:
              instantiation_level_1:
                description: Smallest size
                scale_info:
                  vdu1_aspect:
                    scale_level: 0
                  vdu2_aspect:
                    scale_level: 0
              instantiation_level_2:
                description: Largest size
                scale_info:
                  vdu1_aspect:
                    scale_level: 2
                  vdu2_aspect:
                    scale_level: 2
            default_level: instantiation_level_1
      - VDU1_instantiation_levels:
          type: tosca.policies.nfv.VduInstantiationLevels
          properties:
            levels:
              instantiation_level_1:
                number_of_instances: 1
              instantiation_level_2:
                number_of_instances: 3
          targets: [ VDU1 ]
      - VDU2_instantiation_levels:
          type: tosca.policies.nfv.VduInstantiationLevels
          properties:
            levels:
              instantiation_level_1:
                number_of_instances: 1
              instantiation_level_2:
                number_of_instances: 3
          targets: [ VDU2 ]


1. Compress VNF Package
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

An empty VNF package could be created by command
:command:`openstack vnf package create`.
After create a VNF Package successfully, some information including ID, Links,
Onboarding State, Operational State, and Usage State will be returned.
When the Onboarding State is CREATED, the Operational State is DISABLED,
and the Usage State is NOT_IN_USE, indicate the creation is successful.

.. code-block:: console

  $ openstack vnf package create
  +-------------------+-------------------------------------------------------------------------------------------------+
  | Field             | Value                                                                                           |
  +-------------------+-------------------------------------------------------------------------------------------------+
  | ID                | 88d490b1-7145-4bb8-accc-74ea13dccfa0                                                            |
  | Links             | {                                                                                               |
  |                   |     "self": {                                                                                   |
  |                   |         "href": "/vnfpkgm/v1/vnf_packages/88d490b1-7145-4bb8-accc-74ea13dccfa0"                 |
  |                   |     },                                                                                          |
  |                   |     "packageContent": {                                                                         |
  |                   |         "href": "/vnfpkgm/v1/vnf_packages/88d490b1-7145-4bb8-accc-74ea13dccfa0/package_content" |
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
following command :command:`openstack vnf package upload --path
<path of vnf package> <vnf package ID>`.
Here is an example of upload VNF package:

.. code-block:: console

  $ openstack vnf package upload --path test_helm_instantiate.zip 88d490b1-7145-4bb8-accc-74ea13dccfa0
  Upload request for VNF package 88d490b1-7145-4bb8-accc-74ea13dccfa0 has been accepted.


3. Check VNF Package Status
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check the VNF Package Status by :command:`openstack vnf package list` command.
Find the item which the id is same as the created vnf package id, when the
Onboarding State is ONBOARDED, and the Operational State is ENABLED, and the
Usage State is NOT_IN_USE, indicate the VNF Package is uploaded successfully.

.. code-block:: console

  $ openstack vnf package list
  +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
  | Id                                   | Vnf Product Name | Onboarding State | Usage State | Operational State | Links                                                                                           |
  +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+
  | 88d490b1-7145-4bb8-accc-74ea13dccfa0 | Sample VNF       | ONBOARDED        | NOT_IN_USE  | ENABLED           | {                                                                                               |
  |                                      |                  |                  |             |                   |     "self": {                                                                                   |
  |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/88d490b1-7145-4bb8-accc-74ea13dccfa0"                 |
  |                                      |                  |                  |             |                   |     },                                                                                          |
  |                                      |                  |                  |             |                   |     "packageContent": {                                                                         |
  |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/88d490b1-7145-4bb8-accc-74ea13dccfa0/package_content" |
  |                                      |                  |                  |             |                   |     }                                                                                           |
  |                                      |                  |                  |             |                   | }                                                                                               |
  +--------------------------------------+------------------+------------------+-------------+-------------------+-------------------------------------------------------------------------------------------------+


Create VNF
==========

1. Get VNFD ID
~~~~~~~~~~~~~~

The VNFD ID of a uploaded vnf package could be found by
:command:`openstack vnf package show <VNF package ID>` command.
Here is an example of checking VNFD-ID value:

.. code-block:: console

  $ openstack vnf package show 954df00a-8b14-485d-bfd8-8fc5df0197cb
  +----------------------+-------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field                | Value                                                                                                                                           |
  +----------------------+-------------------------------------------------------------------------------------------------------------------------------------------------+
  | Additional Artifacts | [                                                                                                                                               |
  |                      |     {                                                                                                                                           |
  |                      |         "artifactPath": "Files/kubernetes/test-chart-0.1.0.tgz",                                                                                |
  |                      |         "checksum": {                                                                                                                           |
  |                      |             "algorithm": "SHA-256",                                                                                                             |
  |                      |             "hash": "fa05dd35f45adb43ff1c6c77675ac82c477c5a55a3ad14a87a6b542c21cf4f7c"                                                          |
  |                      |         },                                                                                                                                      |
  |                      |         "metadata": {}                                                                                                                          |
  |                      |     }                                                                                                                                           |
  |                      | ]                                                                                                                                               |
  | Checksum             | {                                                                                                                                               |
  |                      |     "hash": "ac970df4d0c0583c5e152babcf74f72d15d31c92707e700dfd91a5ec9d742afcdf63baaa1e08d5a71f34f06043c1f0be1a49e42ab5693860528f7a382bcc0a76", |
  |                      |     "algorithm": "sha512"                                                                                                                       |
  |                      | }                                                                                                                                               |
  | ID                   | 88d490b1-7145-4bb8-accc-74ea13dccfa0                                                                                                            |
  | Links                | {                                                                                                                                               |
  |                      |     "self": {                                                                                                                                   |
  |                      |         "href": "/vnfpkgm/v1/vnf_packages/88d490b1-7145-4bb8-accc-74ea13dccfa0"                                                                 |
  |                      |     },                                                                                                                                          |
  |                      |     "packageContent": {                                                                                                                         |
  |                      |         "href": "/vnfpkgm/v1/vnf_packages/88d490b1-7145-4bb8-accc-74ea13dccfa0/package_content"                                                 |
  |                      |     }                                                                                                                                           |
  |                      | }                                                                                                                                               |
  | Onboarding State     | ONBOARDED                                                                                                                                       |
  | Operational State    | ENABLED                                                                                                                                         |
  | Software Images      |                                                                                                                                                 |
  | Usage State          | NOT_IN_USE                                                                                                                                      |
  | User Defined Data    | {}                                                                                                                                              |
  | VNF Product Name     | Sample VNF                                                                                                                                      |
  | VNF Provider         | Company                                                                                                                                         |
  | VNF Software Version | 1.0                                                                                                                                             |
  | VNFD ID              | 330f36dd-8398-4d2c-98c1-bc6c626e88b2                                                                                                            |
  | VNFD Version         | 1.0                                                                                                                                             |
  +----------------------+-------------------------------------------------------------------------------------------------------------------------------------------------+


2. Execute Create VNF Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We could create VNF by running
:command:`openstack vnflcm create <VNFD ID> --os-tacker-api-version 2`.
After the command is executed, the generated ID is ``VNF instance ID``.


.. code-block:: console

  $ openstack vnflcm create 330f36dd-8398-4d2c-98c1-bc6c626e88b2 --os-tacker-api-version 2
  +-----------------------------+------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                            |
  +-----------------------------+------------------------------------------------------------------------------------------------------------------+
  | ID                          | f082149a-c20f-43df-bc71-1fde035a1197                                                                             |
  | Instantiation State         | NOT_INSTANTIATED                                                                                                 |
  | Links                       | {                                                                                                                |
  |                             |     "self": {                                                                                                    |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/f082149a-c20f-43df-bc71-1fde035a1197"             |
  |                             |     },                                                                                                           |
  |                             |     "instantiate": {                                                                                             |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/f082149a-c20f-43df-bc71-1fde035a1197/instantiate" |
  |                             |     }                                                                                                            |
  |                             | }                                                                                                                |
  | VNF Configurable Properties |                                                                                                                  |
  | VNF Instance Description    |                                                                                                                  |
  | VNF Instance Name           |                                                                                                                  |
  | VNF Product Name            | Sample VNF                                                                                                       |
  | VNF Provider                | Company                                                                                                          |
  | VNF Software Version        | 1.0                                                                                                              |
  | VNFD ID                     | 330f36dd-8398-4d2c-98c1-bc6c626e88b2                                                                             |
  | VNFD Version                | 1.0                                                                                                              |
  +-----------------------------+------------------------------------------------------------------------------------------------------------------+


Instantiate VNF
===============

.. _helm_request:

1. Set the Value to the Request Parameter File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get the ID of target VIM.

.. code-block:: console

  $ openstack vim list
  +--------------------------------------+---------------+----------------------------------+------------+------------+--------+
  | ID                                   | Name          | Tenant_id                        | Type       | Is Default | Status |
  +--------------------------------------+---------------+----------------------------------+------------+------------+--------+
  | 9c37f36f-f569-4259-b388-d550e55dd65c | test-vim-helm | ebbc6cf1a03d49918c8e408535d87268 | kubernetes | False      | ACTIVE |
  +--------------------------------------+---------------+----------------------------------+------------+------------+--------+


A json file which includes Helm VIM information
and additionalParams should be provided
for instantiating a containerized VNF.

The following shows a sample json file.

.. code-block:: json

  {
    "flavourId": "simple",
    "vimConnectionInfo": {
      "vim1": {
        "vimId": " 9c37f36f-f569-4259-b388-d550e55dd65c",
        "vimType": "ETSINFV.HELM.V_3"
      }
    },
    "additionalParams": {
      "helm_chart_path": "Files/kubernetes/test-chart-0.1.0.tgz",
      "helm_parameters": {
        "service.port": 8081,
        "service.type": "NodePort"
      },
      "helm_value_names": {
        "VDU1": {
          "replica": "replicaCountVdu1"
        },
        "VDU2": {
          "replica": "replicaCountVdu2"
        }
      },
      "namespace": "default"
    }
  }


In the case of specifying ``vimId`` in the ``vimConnectionInfo``,
vim information is complemented by registered vim information.

.. note::

  When using Helm, ``vimType`` shall be set as ``ETSINFV.KUBERNETES.V_1``.
  It is treated as Helm VIM inside tacker on the basis of
  the value of ``extra.use_helm``.


Optionally, you can specify the full set of ``vimConnectionInfo``,
instead of registering VIM.
The following shows the sample json.

.. code-block:: json

  "vimConnectionInfo": {
    "vim1": {
      "vimId": "vim_id_1",
      "vimType": "ETSINFV.HELM.V_3",
      "interfaceInfo": {
        "endpoint": "auth_url",
        "ssl_ca_cert": "ssl_ca_cert"
      },
      "accessInfo": {
        "bearer_token": "bearer_token"
      }
    }
  }


.. note::

  Even if this operation specify multiple ``vimConnectionInfo``
  associated with one VNF instance, only one of them will be used for
  life cycle management operations.


Also, a json file must include some parameters for Helm
as additional parameters.
The following shows the additional parameters
for deploying CNF by Helm chart.

.. list-table:: additionalParams
  :widths: 15 10 30
  :header-rows: 1

  * - Attribute name
    - Data type
    - Parameter description
  * - helm_chart_path
    - String
    - File path of helm_chart. This parameter must be set.
  * - namespace
    - String
    - Namespace to deploy Kubernetes resources. If absent, the value in Helm chart is used as default.
  * - helm_parameters
    - Dict
    - Parameters of KeyValuePairs, which is specified during Helm installation.
  * - helm_value_names
    - Dict
    - This parameter specifies the parameter name to be set as Helm install parameter.
  * - > replica
    - KeyValuePairs
    - The parameter mapped to the number of Pods.


.. note::

  The ``namespace`` for the VNF instantiation is determined by the
  following priority.

  1. If a ``namespace`` is specified in the additionalParams
     of the instantiate request, the specified ``namespace`` is used.
  2. If a ``namespace`` is not specified,
     the default namespace called ``default`` is used.


.. warning::

  If the multiple namespaces are specified in the manifest by the
  method described in 2, the VNF instantiation will fail.


2. Execute the Instantiation Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run :command:`openstack vnflcm instantiate <VNF instance ID> <json file>
--os-tacker-api-version 2` to instantiate a VNF.

The ``VNF instance ID`` is the ID generated after the
:command:`openstack vnflcm create`
command is executed. We can find it in the [2. Execute Create VNF command]
chapter.

.. code-block:: console

  $ openstack vnflcm instantiate f082149a-c20f-43df-bc71-1fde035a1197 helm_instantiate_req --os-tacker-api-version 2
  Instantiate request for VNF Instance f082149a-c20f-43df-bc71-1fde035a1197 has been accepted.


3. Check the Instantiation State
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We could check the Instantiation State by running the following command.
When the Instantiation State is INSTANTIATED, indicate the instantiation is
successful.

.. code-block:: console

  $ openstack vnflcm show f082149a-c20f-43df-bc71-1fde035a1197 --os-tacker-api-version 2 --fit-width
  +-----------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field                       | Value                                                                                                                                                                                                                        |
  +-----------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | ID                          | f082149a-c20f-43df-bc71-1fde035a1197                                                                                                                                                                                         |
  | Instantiated Vnf Info       | {                                                                                                                                                                                                                            |
  |                             |     "flavourId": "simple",                                                                                                                                                                                                   |
  |                             |     "vnfState": "STARTED",                                                                                                                                                                                                   |
  |                             |     "scaleStatus": [                                                                                                                                                                                                         |
  |                             |         {                                                                                                                                                                                                                    |
  |                             |             "aspectId": "vdu1_aspect",                                                                                                                                                                                       |
  |                             |             "scaleLevel": 0                                                                                                                                                                                                  |
  |                             |         },                                                                                                                                                                                                                   |
  |                             |         {                                                                                                                                                                                                                    |
  |                             |             "aspectId": "vdu2_aspect",                                                                                                                                                                                       |
  |                             |             "scaleLevel": 0                                                                                                                                                                                                  |
  |                             |         }                                                                                                                                                                                                                    |
  |                             |     ],                                                                                                                                                                                                                       |
  |                             |     "maxScaleLevels": [                                                                                                                                                                                                      |
  |                             |         {                                                                                                                                                                                                                    |
  |                             |             "aspectId": "vdu1_aspect",                                                                                                                                                                                       |
  |                             |             "scaleLevel": 2                                                                                                                                                                                                  |
  |                             |         },                                                                                                                                                                                                                   |
  |                             |         {                                                                                                                                                                                                                    |
  |                             |             "aspectId": "vdu2_aspect",                                                                                                                                                                                       |
  |                             |             "scaleLevel": 2                                                                                                                                                                                                  |
  |                             |         }                                                                                                                                                                                                                    |
  |                             |     ],                                                                                                                                                                                                                       |
  |                             |     "vnfcResourceInfo": [                                                                                                                                                                                                    |
  |                             |         {                                                                                                                                                                                                                    |
  |                             |             "id": "vdu1-vnff082149ac20f43dfbc711fde035a1197-659966c5fb-nngts",                                                                                                                                               |
  |                             |             "vduId": "VDU1",                                                                                                                                                                                                 |
  |                             |             "computeResource": {                                                                                                                                                                                             |
  |                             |                 "resourceId": "vdu1-vnff082149ac20f43dfbc711fde035a1197-659966c5fb-nngts",                                                                                                                                   |
  |                             |                 "vimLevelResourceType": "Deployment"                                                                                                                                                                         |
  |                             |             },                                                                                                                                                                                                               |
  |                             |             "metadata": {}                                                                                                                                                                                                   |
  |                             |         },                                                                                                                                                                                                                   |
  |                             |         {                                                                                                                                                                                                                    |
  |                             |             "id": "vdu2-vnff082149ac20f43dfbc711fde035a1197-66bbcfdc84-p2tr8",                                                                                                                                               |
  |                             |             "vduId": "VDU2",                                                                                                                                                                                                 |
  |                             |             "computeResource": {                                                                                                                                                                                             |
  |                             |                 "resourceId": "vdu2-vnff082149ac20f43dfbc711fde035a1197-66bbcfdc84-p2tr8",                                                                                                                                   |
  |                             |                 "vimLevelResourceType": "Deployment"                                                                                                                                                                         |
  |                             |             },                                                                                                                                                                                                               |
  |                             |             "metadata": {}                                                                                                                                                                                                   |
  |                             |         }                                                                                                                                                                                                                    |
  |                             |     ],                                                                                                                                                                                                                       |
  |                             |     "vnfcInfo": [                                                                                                                                                                                                            |
  |                             |         {                                                                                                                                                                                                                    |
  |                             |             "id": "VDU1-vdu1-vnff082149ac20f43dfbc711fde035a1197-659966c5fb-nngts",                                                                                                                                          |
  |                             |             "vduId": "VDU1",                                                                                                                                                                                                 |
  |                             |             "vnfcResourceInfoId": "vdu1-vnff082149ac20f43dfbc711fde035a1197-659966c5fb-nngts",                                                                                                                               |
  |                             |             "vnfcState": "STARTED"                                                                                                                                                                                           |
  |                             |         },                                                                                                                                                                                                                   |
  |                             |         {                                                                                                                                                                                                                    |
  |                             |             "id": "VDU2-vdu2-vnff082149ac20f43dfbc711fde035a1197-66bbcfdc84-p2tr8",                                                                                                                                          |
  |                             |             "vduId": "VDU2",                                                                                                                                                                                                 |
  |                             |             "vnfcResourceInfoId": "vdu2-vnff082149ac20f43dfbc711fde035a1197-66bbcfdc84-p2tr8",                                                                                                                               |
  |                             |             "vnfcState": "STARTED"                                                                                                                                                                                           |
  |                             |         }                                                                                                                                                                                                                    |
  |                             |     ],                                                                                                                                                                                                                       |
  |                             |     "metadata": {                                                                                                                                                                                                            |
  |                             |         "namespace": "default",                                                                                                                                                                                              |
  |                             |         "tenant": "default",                                                                                                                                                                                                 |
  |                             |         "vdu_reses": {                                                                                                                                                                                                       |
  |                             |             "VDU1": {                                                                                                                                                                                                        |
  |                             |                 "apiVersion": "apps/v1",                                                                                                                                                                                     |
  |                             |                 "kind": "Deployment",                                                                                                                                                                                        |
  |                             |                 "metadata": {                                                                                                                                                                                                |
  |                             |                     "name": "vdu1-vnff082149ac20f43dfbc711fde035a1197",                                                                                                                                                      |
  |                             |                     "labels": {                                                                                                                                                                                              |
  |                             |                         "helm.sh/chart": "test-chart-0.1.0",                                                                                                                                                                 |
  |                             |                         "app.kubernetes.io/name": "test-chart",                                                                                                                                                              |
  |                             |                         "app.kubernetes.io/instance": "vnff082149ac20f43dfbc711fde035a1197",                                                                                                                                 |
  |                             |                         "app.kubernetes.io/version": "1.16.0",                                                                                                                                                               |
  |                             |                         "app.kubernetes.io/managed-by": "Helm"                                                                                                                                                               |
  |                             |                     },                                                                                                                                                                                                       |
  |                             |                     "namespace": "default"                                                                                                                                                                                   |
  |                             |                 },                                                                                                                                                                                                           |
  |                             |                 "spec": {                                                                                                                                                                                                    |
  |                             |                     "replicas": 1,                                                                                                                                                                                           |
  |                             |                     "selector": {                                                                                                                                                                                            |
  |                             |                         "matchLabels": {                                                                                                                                                                                     |
  |                             |                             "app.kubernetes.io/name": "test-chart",                                                                                                                                                          |
  |                             |                             "app.kubernetes.io/instance": "vnff082149ac20f43dfbc711fde035a1197"                                                                                                                              |
  |                             |                         }                                                                                                                                                                                                    |
  |                             |                     },                                                                                                                                                                                                       |
  |                             |                     "template": {                                                                                                                                                                                            |
  |                             |                         "metadata": {                                                                                                                                                                                        |
  |                             |                             "labels": {                                                                                                                                                                                      |
  |                             |                                 "app.kubernetes.io/name": "test-chart",                                                                                                                                                      |
  |                             |                                 "app.kubernetes.io/instance": "vnff082149ac20f43dfbc711fde035a1197"                                                                                                                          |
  |                             |                             }                                                                                                                                                                                                |
  |                             |                         },                                                                                                                                                                                                   |
  |                             |                         "spec": {                                                                                                                                                                                            |
  |                             |                             "serviceAccountName": "vnff082149ac20f43dfbc711fde035a1197-test-chart",                                                                                                                          |
  |                             |                             "securityContext": {},                                                                                                                                                                           |
  |                             |                             "containers": [                                                                                                                                                                                  |
  |                             |                                 {                                                                                                                                                                                            |
  |                             |                                     "name": "test-chart",                                                                                                                                                                    |
  |                             |                                     "securityContext": {},                                                                                                                                                                   |
  |                             |                                     "image": "nginx:1.16.0",                                                                                                                                                                 |
  |                             |                                     "imagePullPolicy": "IfNotPresent",                                                                                                                                                       |
  |                             |                                     "ports": [                                                                                                                                                                               |
  |                             |                                         {                                                                                                                                                                                    |
  |                             |                                             "name": "http",                                                                                                                                                                  |
  |                             |                                             "containerPort": 80,                                                                                                                                                             |
  |                             |                                             "protocol": "TCP"                                                                                                                                                                |
  |                             |                                         }                                                                                                                                                                                    |
  |                             |                                     ],                                                                                                                                                                                       |
  |                             |                                     "resources": {}                                                                                                                                                                          |
  |                             |                                 }                                                                                                                                                                                            |
  |                             |                             ]                                                                                                                                                                                                |
  |                             |                         }                                                                                                                                                                                                    |
  |                             |                     }                                                                                                                                                                                                        |
  |                             |                 }                                                                                                                                                                                                            |
  |                             |             },                                                                                                                                                                                                               |
  |                             |             "VDU2": {                                                                                                                                                                                                        |
  |                             |                 "apiVersion": "apps/v1",                                                                                                                                                                                     |
  |                             |                 "kind": "Deployment",                                                                                                                                                                                        |
  |                             |                 "metadata": {                                                                                                                                                                                                |
  |                             |                     "name": "vdu2-vnff082149ac20f43dfbc711fde035a1197",                                                                                                                                                      |
  |                             |                     "labels": {                                                                                                                                                                                              |
  |                             |                         "helm.sh/chart": "test-chart-0.1.0",                                                                                                                                                                 |
  |                             |                         "app.kubernetes.io/name": "test-chart",                                                                                                                                                              |
  |                             |                         "app.kubernetes.io/instance": "vnff082149ac20f43dfbc711fde035a1197",                                                                                                                                 |
  |                             |                         "app.kubernetes.io/version": "1.16.0",                                                                                                                                                               |
  |                             |                         "app.kubernetes.io/managed-by": "Helm"                                                                                                                                                               |
  |                             |                     },                                                                                                                                                                                                       |
  |                             |                     "namespace": "default"                                                                                                                                                                                   |
  |                             |                 },                                                                                                                                                                                                           |
  |                             |                 "spec": {                                                                                                                                                                                                    |
  |                             |                     "replicas": 1,                                                                                                                                                                                           |
  |                             |                     "selector": {                                                                                                                                                                                            |
  |                             |                         "matchLabels": {                                                                                                                                                                                     |
  |                             |                             "app.kubernetes.io/name": "test-chart",                                                                                                                                                          |
  |                             |                             "app.kubernetes.io/instance": "vnff082149ac20f43dfbc711fde035a1197"                                                                                                                              |
  |                             |                         }                                                                                                                                                                                                    |
  |                             |                     },                                                                                                                                                                                                       |
  |                             |                     "template": {                                                                                                                                                                                            |
  |                             |                         "metadata": {                                                                                                                                                                                        |
  |                             |                             "labels": {                                                                                                                                                                                      |
  |                             |                                 "app.kubernetes.io/name": "test-chart",                                                                                                                                                      |
  |                             |                                 "app.kubernetes.io/instance": "vnff082149ac20f43dfbc711fde035a1197"                                                                                                                          |
  |                             |                             }                                                                                                                                                                                                |
  |                             |                         },                                                                                                                                                                                                   |
  |                             |                         "spec": {                                                                                                                                                                                            |
  |                             |                             "serviceAccountName": "vnff082149ac20f43dfbc711fde035a1197-test-chart",                                                                                                                          |
  |                             |                             "securityContext": {},                                                                                                                                                                           |
  |                             |                             "containers": [                                                                                                                                                                                  |
  |                             |                                 {                                                                                                                                                                                            |
  |                             |                                     "name": "test-chart",                                                                                                                                                                    |
  |                             |                                     "securityContext": {},                                                                                                                                                                   |
  |                             |                                     "image": "nginx",                                                                                                                                                                        |
  |                             |                                     "imagePullPolicy": "IfNotPresent",                                                                                                                                                       |
  |                             |                                     "ports": [                                                                                                                                                                               |
  |                             |                                         {                                                                                                                                                                                    |
  |                             |                                             "name": "http",                                                                                                                                                                  |
  |                             |                                             "containerPort": 80,                                                                                                                                                             |
  |                             |                                             "protocol": "TCP"                                                                                                                                                                |
  |                             |                                         }                                                                                                                                                                                    |
  |                             |                                     ],                                                                                                                                                                                       |
  |                             |                                     "resources": {}                                                                                                                                                                          |
  |                             |                                 }                                                                                                                                                                                            |
  |                             |                             ]                                                                                                                                                                                                |
  |                             |                         }                                                                                                                                                                                                    |
  |                             |                     }                                                                                                                                                                                                        |
  |                             |                 }                                                                                                                                                                                                            |
  |                             |             }                                                                                                                                                                                                                |
  |                             |         },                                                                                                                                                                                                                   |
  |                             |         "helm_chart_path": "Files/kubernetes/test-chart-0.1.0.tgz",                                                                                                                                                          |
  |                             |         "helm_value_names": {                                                                                                                                                                                                |
  |                             |             "VDU1": {                                                                                                                                                                                                        |
  |                             |                 "replica": "replicaCountVdu1"                                                                                                                                                                                |
  |                             |             },                                                                                                                                                                                                               |
  |                             |             "VDU2": {                                                                                                                                                                                                        |
  |                             |                 "replica": "replicaCountVdu2"                                                                                                                                                                                |
  |                             |             }                                                                                                                                                                                                                |
  |                             |         },                                                                                                                                                                                                                   |
  |                             |         "release_name": "vnff082149ac20f43dfbc711fde035a1197",                                                                                                                                                               |
  |                             |         "revision": "1"                                                                                                                                                                                                      |
  |                             |     }                                                                                                                                                                                                                        |
  |                             | }                                                                                                                                                                                                                            |
  | Instantiation State         | INSTANTIATED                                                                                                                                                                                                                 |
  | Links                       | {                                                                                                                                                                                                                            |
  |                             |     "self": {                                                                                                                                                                                                                |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/f082149a-c20f-43df-bc71-1fde035a1197"                                                                                                                         |
  |                             |     },                                                                                                                                                                                                                       |
  |                             |     "terminate": {                                                                                                                                                                                                           |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/f082149a-c20f-43df-bc71-1fde035a1197/terminate"                                                                                                               |
  |                             |     },                                                                                                                                                                                                                       |
  |                             |     "scale": {                                                                                                                                                                                                               |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/f082149a-c20f-43df-bc71-1fde035a1197/scale"                                                                                                                   |
  |                             |     },                                                                                                                                                                                                                       |
  |                             |     "heal": {                                                                                                                                                                                                                |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/f082149a-c20f-43df-bc71-1fde035a1197/heal"                                                                                                                    |
  |                             |     },                                                                                                                                                                                                                       |
  |                             |     "changeExtConn": {                                                                                                                                                                                                       |
  |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/f082149a-c20f-43df-bc71-1fde035a1197/change_ext_conn"                                                                                                         |
  |                             |     }                                                                                                                                                                                                                        |
  |                             | }                                                                                                                                                                                                                            |
  | VIM Connection Info         | {                                                                                                                                                                                                                            |
  |                             |     "vim1": {                                                                                                                                                                                                                |
  |                             |         "vimId": "9c37f36f-f569-4259-b388-d550e55dd65c",                                                                                                                                                                     |
  |                             |         "vimType": "ETSINFV.HELM.V_3",                                                                                                                                                                                       |
  |                             |         "interfaceInfo": {                                                                                                                                                                                                   |
  |                             |             "endpoint": "https://192.168.56.10:6443",                                                                                                                                                                        |
  |                             |             "ssl_ca_cert": "-----BEGIN CERTIFICATE----- MIIDBTCCAe2gAwIBAgIIa76wZDxLNAowDQYJKoZIhvcNAQELBQAwFTETMBEGA1UE AxMKa3ViZXJuZXRlczAeFw0yMzExMDYwMDA3MzBaFw0zMzExMDMwMDEyMzBaMBUx                                    |
  |                             | EzARBgNVBAMTCmt1YmVybmV0ZXMwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEK AoIBAQDd0LBXGxVexr09mVFNSXWQq3TN66IIcXCBAMbIWI4EiQ8Y0zI4hSwADdK2 ltYSdWw7wq3/YTFHK8/YTY7Jvd9/k3UJrqkZ6kBtL20pJUPXNJVLE/hRzsqEnHHv                           |
  |                             | cfqYZTHvTY4g7qNcMOcfl/oDUGUMfpQT2gs6xoNl0WX/1+QeQbadx1kWaD2Ii45F d8TR+c4wccxNaLArk3ok4h1PNeAwra4mRmBHQQ2wFjkTYGl4+ss3v1yoUJkrQjXL RgzLufeXaz8eRTi36HkjudGKfS3OnUeke3uBN7usW58FFJ8TdKOhuoguRm53kj6+                           |
  |                             | TwXtZCOPzn4gNxq6xJE1Xj2hwFfpAgMBAAGjWTBXMA4GA1UdDwEB/wQEAwICpDAP BgNVHRMBAf8EBTADAQH/MB0GA1UdDgQWBBRdmQ4r63pXBHIO8ODqxROE7x+aizAV BgNVHREEDjAMggprdWJlcm5ldGVzMA0GCSqGSIb3DQEBCwUAA4IBAQBeQ/9+bzRe                           |
  |                             | qbA02MfYnN3vycGhDObcAoiDIMIutojFTpx4hGZjqVgTRpLH5ReddwR4kkxn3NRg weCVkNkhzyGze64nb11qZG71olaOQRMYzyN2hYfmbq7MXSvmJQQYIr1OewaRk+xl TyG1XRXoD2IEaHEvG0+pQJlDerd5Z6S1fkPaKZtcRbM/E6y5VXMV6hegN4MwHZSI                           |
  |                             | Ll1uEBTxUzzTm3dnl1KL8GDg05ajoYcyL3X/0aWsb/MFhtIlXe2CMxu5qUkLBhzy fCfX4cZpI5KFxMgdmAEoaGbNy7iqsGrLFtEmub2gdEBIVNr7vgOk4OeQ9Uodj6K7 jK97z+cupc5G -----END CERTIFICATE-----"                                                    |
  |                             |         },                                                                                                                                                                                                                   |
  |                             |         "accessInfo": {},                                                                                                                                                                                                    |
  |                             |         "extra": {                                                                                                                                                                                                           |
  |                             |             "use_helm": true                                                                                                                                                                                                 |
  |                             |         }                                                                                                                                                                                                                    |
  |                             |     }                                                                                                                                                                                                                        |
  |                             | }                                                                                                                                                                                                                            |
  | VNF Configurable Properties |                                                                                                                                                                                                                              |
  | VNF Instance Description    |                                                                                                                                                                                                                              |
  | VNF Instance Name           |                                                                                                                                                                                                                              |
  | VNF Product Name            | Sample VNF                                                                                                                                                                                                                   |
  | VNF Provider                | Company                                                                                                                                                                                                                      |
  | VNF Software Version        | 1.0                                                                                                                                                                                                                          |
  | VNFD ID                     | 330f36dd-8398-4d2c-98c1-bc6c626e88b2                                                                                                                                                                                         |
  | VNFD Version                | 1.0                                                                                                                                                                                                                          |
  +-----------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


4. Check the Deployment in Kubernetes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We can check the deployed release by running the following command.
Release is an instance of a chart running on a Kubernetes cluster.

.. code-block:: console

  $ helm list
  NAME                               	NAMESPACE	REVISION	UPDATED                                	STATUS  	CHART           	APP VERSION
  vnff082149ac20f43dfbc711fde035a1197	default  	1       	2023-12-07 05:12:00.368610985 +0000 UTC	deployed	test-chart-0.1.0	1.16.0


Also, we can check a deployed containerized VNF
by running the following command.
When the READY is 1/1, indicate the deployment is created successfully.

.. code-block:: console

  $ kubectl get deploy
  NAME                                       READY   UP-TO-DATE   AVAILABLE   AGE
  vdu1-vnff082149ac20f43dfbc711fde035a1197   1/1     1            1           6m13s
  vdu2-vnff082149ac20f43dfbc711fde035a1197   1/1     1            1           6m13s


If we want to check whether the resource is deployed in the default namespace,
we can append ``-A`` to the command line.

.. code-block:: console

  $ kubectl get deploy -A
  NAMESPACE     NAME                                       READY   UP-TO-DATE   AVAILABLE   AGE
  default       vdu1-vnff082149ac20f43dfbc711fde035a1197   1/1     1            1           6m42s
  default       vdu2-vnff082149ac20f43dfbc711fde035a1197   1/1     1            1           6m42s
  kube-system   kuryr-controller                           1/1     1            1           31d


.. note::

  If a value other than ``default`` is specified for the namespace
  during instantiate, the deployed resources will be instantiated
  in the corresponding namespace.


Supported versions
------------------

Tacker Antelope release

- Helm: 3.10

Tacker Bobcat release

- Helm: 3.11


History of Checks
-----------------

The content of this document has been confirmed to work
using the following VNF Package.

* `test_helm_instantiate for 2023.2 Bobcat`_


.. _test_helm_instantiate for 2023.2 Bobcat:
  https://opendev.org/openstack/tacker/src/branch/stable/2023.2/tacker/tests/functional/sol_kubernetes_v2/samples/test_helm_instantiate
