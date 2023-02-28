=======================================================
ETSI NFV-SOL CNF Deployment using Helm (v2 VNF LCM API)
=======================================================

This section covers how to deploy ETSI NFV-SOL containerized VNF
using Helm in version 2 (v2) VNF LCM API.

.. note::

    v1 VNF LCM API also support CNF deployment using Helm and
    its requirements are different from v2 VNF LCM API.
    For details on using Helm in v1 API, please refer to
    :doc:`mgmt_driver_deploy_k8s_and_cnf_with_helm`.

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

.. figure:: ../_images/etsi_cnf_helm_v2.png
    :align: left

Prepare Helm VIM
================
1. Create a Config File
~~~~~~~~~~~~~~~~~~~~~~~

Before register a Helm VIM to tacker, we should create config file.
The following sample provides required information to
register a Helm VIM.
This sample specifies the values of the ``bearer_token`` and ``ssl_ca_cert``
parameters that can be obtained from the Kubernetes Master-node.
For specific methods of obtaining ``bearer_token`` and ``sl_ca_cert``,
please refer to [#credential]_.
It also contains the ``extra`` field.
For using Helm, ``use_helm`` in ``extra`` must be set as true.

.. code-block:: yaml

  auth_url: "https://192.168.56.10:6443"
  bearer_token: "eyJhbGciOiJSUzI1NiIsImtpZCI6ImVFRXhkM2JWM0l5d3p0aGRzUHVzSm8xd25RRXJkby1YN21uZWNiWUppd00ifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tazQ1N2MiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6Ijg5MmZiNjE1LTYxYzQtNDMzZC1hMDU2LTdkNTg5OTJiMDlhZSIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OmRlZmF1bHQifQ.frFlz-jXmOj-wqeupNe1xX1tI1_UBdESw8z3tFzjE3qZwqbP5DYYWw0CqkG8JfE-HAte59kooKt7tt8bzfTRavnpHTlF1mGCUyybFTkxC1Rd52lc-cFem_i7ZZSf9Vz0RSoPLDInOqVuSTn9XGYu3t3fyNUN0WKysyhrzYLt5LpI0_zP19u_R_fsENnHLwO5yO4djNVjtchlvKtp0KfwNxZAFwz-DAaWYLK1oDKFXahOQ_Pe026fiUoccsbRsiOhk3hKfy-FhvJN1lOyFLgHsYMmZjDqSS4eON6qHaNNDMUXduThEWpKI3JkwuekheM5ODghIrVqCrwKoeljWnRxGQ"
  ssl_ca_cert: "-----BEGIN CERTIFICATE-----
  MIIC/jCCAeagAwIBAgIBADANBgkqhkiG9w0BAQsFADAVMRMwEQYDVQQDEwprdWJl
  cm5ldGVzMB4XDTIyMDkxMjEwMDMyMloXDTMyMDkwOTEwMDMyMlowFTETMBEGA1UE
  AxMKa3ViZXJuZXRlczCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAPcx
  BVG56RA6EWNm9dUdsJhNzz2VdEHqg2q0P/YBulILMXK3CGpjfAOSJs59Z/TJ2GYx
  /3TFO5Qy/FekQnoEshI/IBSm34A8g8fiDgRiwTrv4s6LMxOZknICeIj4WrOjOsis
  VMEVp8VFPM7bMzJnQ9m/9dHkFPTKivV+K/hHH/Fa3FN7Fk8+1rv00qOLrYxpnTMa
  96hTzRYwHcXhmfVtgBl1SNnkjd1EN1NNIcAOXNEdEOaU5eBdxjB162ZUPfWxIR7l
  fDO8qLVZbXWb6rCpHxC1IfWPylNyQMnIGr/uv36yBkoq8ZHy1rUEyS2u/AoVDwfr
  cmaCJDEGXYXhFe1bIgcCAwEAAaNZMFcwDgYDVR0PAQH/BAQDAgKkMA8GA1UdEwEB
  /wQFMAMBAf8wHQYDVR0OBBYEFAieaYVCHhDnPIkEgMY1YKSofXeIMBUGA1UdEQQO
  MAyCCmt1YmVybmV0ZXMwDQYJKoZIhvcNAQELBQADggEBABmy+hKoJ+UkI3d9DOqz
  MLB8x7NbWJO50wb4KqE/nXRSJDSKObfYNcDMDYh8T7RtSGUe3kxxNpACrHVkUme6
  2vjylGkf6kOCLYowH5BjLVfYk/aPDNjWUIdULft0iefqm8MetltokpE00fAeYZ0U
  q+kFziqOorf58Bmc7TuvdqqlQdNTXMdgMWq6zCfghcDEnLHcuRE4MSgWJXMLY5mw
  zb0X3hvt3uO8OdHNwRWli/9VAyGro0r0xPgH7LanMd9KnQF17Ux1Y0bNUbqxHwqx
  xO7lMyo8RP65nIqrTvC9dwvFth8MnSmsNucn0bJhl5Ol69AacT3/TSo+9u8+IJ4G
  bYU=
  -----END CERTIFICATE-----"
  project_name: "default"
  type: "kubernetes"
  extra:
    use_helm: true

2. Register Helm VIM
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
    |                |     "ssl_ca_cert": "b'gAAAAABjH8fUWWCj7wktDlvfU4LuzJUNlWuirn2sB1DIyTmzlxNKeTA-cAinSbqjhSPjb-                                                                                                                                              |
    |                | AT65CzEBtJ21Z9czZu7gXt3JYcZhwEBUACbzbvBVd6Hs7SrepXPuc2tFjNA4gX133wWJ8vQZEENm-9_SixF2J9I3n4EheX5zEwOOBV8T_vMRMTsTBj1z9vL8gg525C1-5w85oUnAWjHAIjYLJQk9GGXdC-                                                                                |
    |                | WvVMB0hKxiPBtK_rsf6Y0LJYoYmvYhqP5vJbCLp-3VZ_-n1ZVThtTBvYjWz6L8T_RmRRt4QVmHyK8FvdwM7aq0W7FFsZeyWXnGijfuvc8Vv8q1Ha7tskFtgms582FD12xlv1OrQ6wfFhyp4AEouDGMETeoMCCaZZKFx4CPf5a9vj85oG_-                                                        |
    |                | vefsqgBjEhJKeXsPaR3BeZenEIMANEkzGS0p6jDwvWuinhpXt5gYIeLNyiUQwZPr1gjVg7mj-nCylZHzXMZb4ObMnJy7KVlQ9_qFCDl0d2W6FaoO3-YGetOiqC7XYHNvDvgOGXX0WSk9cT_eM3T3_n0wAAGp6Gm_By0KbVgq2U0k4YQ74uuO_8PBrE6dLVg1hlvB2iFoDzcN6xIflANsTfk8KSo5xUG4rcOqJg_GZ |
    |                | oNIQ_6rwvo9AUVVpmhDvrijsLhsAmQXke_NWVASELKKrbvL_lOAEETlDNcqewOGiEus-Z4pgpAN1HZU3v4lZmueEZ9T4JvJlHOaX9Y_JK19OiW19YqA2sKRcBmycOZJl-o-CCjOZaguk3u-XlQ_6uKQq-                                                                                 |
    |                | w_U3Ly5sI0Jnp_54nZl_y_CW41dIS4QWCZ0of7bc9WP05I5khv3zcnIW5qbRwUvhXUtu3stEr2xpUGegQOmuVJ0KjYXkFc9ItueQwXXTopuZAn7EJRtxMLh4MuGyWPVscRO4LcJVBsFsSK5WEQvH_gp8QBMSKYB_3gvSNVrpjZ58lpy7XESU73bZy_FTGS-tZQ-zHDCiYq1uVhbExjeKBZB8gyxDm4pZdJ693Tdlp |
    |                | HL3gIVvRIGvqBNufXyB7n4rtfUMemlttgJv8Hx57EvN4_EOo0Fv2CnBszQu1mKqatBtsZPfCpk1tPHycXHdLKqzJ2Gsen_rNOYv__iSM6133ywZTxzq7i4eelWxkoMPAdCLw1Yijg4jHcNcR3ODGVnRfriIdmKQ4xCbNohf1Rkog53x_MhlAtaCaDOM0DevjJLcqYI484wrM0bmRO3id8QBZgjUXUZlYmZ6wI9O3v |
    |                | suRqJc4RVbbh2d4qPbh0d4xR6EYH6MQiiKDlV2YA6m5fenAy8mP925nfKCPwkleIzqqQfLrHTmVSiIcSzLIx5hffqJkD0bnWiLrKo7KrvNWp3HvpzdcPfFB3rcdWdlOSYM0HC-zxcqACkf-kC78lP-FWUhvweKm_LAtIOB3csQRD33WN2Cpfa-rs__s8nDc3sZ4QTcDx-ELIesQygyBsfk_eg_ATuOaZ-         |
    |                | kYQud43JaO6pGOdr63apz8QVxk9_5XGIVbT6kRbmDf76ol8Laj_ZLrSj3rVKcPdUdfvoP'",                                                                                                                                                                  |
    |                |     "auth_url": "https://192.168.56.10:6443",                                                                                                                                                                                             |
    |                |     "username": "None",                                                                                                                                                                                                                   |
    |                |     "key_type": "barbican_key",                                                                                                                                                                                                           |
    |                |     "secret_uuid": "***"                                                                                                                                                                                                                  |
    |                | }                                                                                                                                                                                                                                         |
    | auth_url       | https://192.168.56.10:6443                                                                                                                                                                                                                |
    | created_at     | 2022-09-12 23:59:16.151696                                                                                                                                                                                                                |
    | description    |                                                                                                                                                                                                                                           |
    | extra          | use_helm=True                                                                                                                                                                                                                             |
    | id             | d0f0cef9-5890-4a68-8974-61ed71b9f5d9                                                                                                                                                                                                      |
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
    | project_id     | 5a8fb2d2043141c190f227769e06aebb                                                                                                                                                                                                          |
    | status         | PENDING                                                                                                                                                                                                                                   |
    | type           | kubernetes                                                                                                                                                                                                                                |
    | updated_at     | None                                                                                                                                                                                                                                      |
    | vim_project    | {                                                                                                                                                                                                                                         |
    |                |     "name": "default"                                                                                                                                                                                                                     |
    |                | }                                                                                                                                                                                                                                         |
    +----------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Also we can check if the status of VIM is REACHABLE by
:command:`openstack vim list` command.

.. code-block:: console

    $ openstack vim list
    +--------------------------------------+---------------+----------------------------------+------------+------------+-----------+
    | ID                                   | Name          | Tenant_id                        | Type       | Is Default | Status    |
    +--------------------------------------+---------------+----------------------------------+------------+------------+-----------+
    | d0f0cef9-5890-4a68-8974-61ed71b9f5d9 | test-vim-helm | 5a8fb2d2043141c190f227769e06aebb | kubernetes | False      | REACHABLE |
    +--------------------------------------+---------------+----------------------------------+------------+------------+-----------+

.. note::

    In the return of vim list,
    ``Type`` is shown as kuberneters for both Helm VIM and Kubernetes VIM.

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
  Hash: 511df66c2d34bc2d3b1ea80118c4ad3c61ad7816a45bfadbb223d172b8503d30

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
VNF Descriptor (VNFD) based on ETSI NFV-SOL001 [#vnfd]_.

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
    | ID                | 954df00a-8b14-485d-bfd8-8fc5df0197cb                                                            |
    | Links             | {                                                                                               |
    |                   |     "self": {                                                                                   |
    |                   |         "href": "/vnfpkgm/v1/vnf_packages/954df00a-8b14-485d-bfd8-8fc5df0197cb"                 |
    |                   |     },                                                                                          |
    |                   |     "packageContent": {                                                                         |
    |                   |         "href": "/vnfpkgm/v1/vnf_packages/954df00a-8b14-485d-bfd8-8fc5df0197cb/package_content" |
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
:command:`openstack vnf package upload --path <path of vnf package>
<vnf package ID>`
Here is an example of upload VNF package:

.. code-block:: console

  $ openstack vnf package upload --path test_helm_instantiate.zip 954df00a-8b14-485d-bfd8-8fc5df0197cb
  Upload request for VNF package 954df00a-8b14-485d-bfd8-8fc5df0197cb has been accepted.

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
    | 954df00a-8b14-485d-bfd8-8fc5df0197cb | Sample VNF       | ONBOARDED        | NOT_IN_USE  | ENABLED           | {                                                                                               |
    |                                      |                  |                  |             |                   |     "self": {                                                                                   |
    |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/954df00a-8b14-485d-bfd8-8fc5df0197cb"                 |
    |                                      |                  |                  |             |                   |     },                                                                                          |
    |                                      |                  |                  |             |                   |     "packageContent": {                                                                         |
    |                                      |                  |                  |             |                   |         "href": "/vnfpkgm/v1/vnf_packages/954df00a-8b14-485d-bfd8-8fc5df0197cb/package_content" |
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
    |                      |             "hash": "511df66c2d34bc2d3b1ea80118c4ad3c61ad7816a45bfadbb223d172b8503d30"                                                          |
    |                      |         },                                                                                                                                      |
    |                      |         "metadata": {}                                                                                                                          |
    |                      |     }                                                                                                                                           |
    |                      | ]                                                                                                                                               |
    | Checksum             | {                                                                                                                                               |
    |                      |     "hash": "091ed6ef0e23a7893eb5349bfbe3d6bf7d5667ff01f3d51aeb80e651bf750bcbfe8a90ce20a4a754806309ddfa3f148d07c752c7c49c8910cf10c84b7eca31f2", |
    |                      |     "algorithm": "sha512"                                                                                                                       |
    |                      | }                                                                                                                                               |
    | ID                   | 954df00a-8b14-485d-bfd8-8fc5df0197cb                                                                                                            |
    | Links                | {                                                                                                                                               |
    |                      |     "self": {                                                                                                                                   |
    |                      |         "href": "/vnfpkgm/v1/vnf_packages/954df00a-8b14-485d-bfd8-8fc5df0197cb"                                                                 |
    |                      |     },                                                                                                                                          |
    |                      |     "packageContent": {                                                                                                                         |
    |                      |         "href": "/vnfpkgm/v1/vnf_packages/954df00a-8b14-485d-bfd8-8fc5df0197cb/package_content"                                                 |
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
    | VNFD ID              | 339f9eb3-ed61-443e-8801-e7cf2474c72a                                                                                                            |
    | VNFD Version         | 1.0                                                                                                                                             |
    +----------------------+-------------------------------------------------------------------------------------------------------------------------------------------------+

2. Execute Create VNF Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
We could create VNF by running
:command:`openstack vnflcm create <VNFD ID> --os-tacker-api-version 2`.
After the command is executed, the generated ID is ``VNF instance ID``.

.. code-block:: console

    $ openstack vnflcm create 339f9eb3-ed61-443e-8801-e7cf2474c72a --os-tacker-api-version 2
    +-----------------------------+------------------------------------------------------------------------------------------------------------------+
    | Field                       | Value                                                                                                            |
    +-----------------------------+------------------------------------------------------------------------------------------------------------------+
    | ID                          | e959ab43-133c-4c50-bb00-e2aadc66e498                                                                             |
    | Instantiation State         | NOT_INSTANTIATED                                                                                                 |
    | Links                       | {                                                                                                                |
    |                             |     "self": {                                                                                                    |
    |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/e959ab43-133c-4c50-bb00-e2aadc66e498"             |
    |                             |     },                                                                                                           |
    |                             |     "instantiate": {                                                                                             |
    |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/e959ab43-133c-4c50-bb00-e2aadc66e498/instantiate" |
    |                             |     }                                                                                                            |
    |                             | }                                                                                                                |
    | VNF Configurable Properties |                                                                                                                  |
    | VNF Instance Description    |                                                                                                                  |
    | VNF Instance Name           |                                                                                                                  |
    | VNF Product Name            | Sample VNF                                                                                                       |
    | VNF Provider                | Company                                                                                                          |
    | VNF Software Version        | 1.0                                                                                                              |
    | VNFD ID                     | 339f9eb3-ed61-443e-8801-e7cf2474c72a                                                                             |
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
    +--------------------------------------+---------------+----------------------------------+------------+------------+-----------+
    | ID                                   | Name          | Tenant_id                        | Type       | Is Default | Status    |
    +--------------------------------------+---------------+----------------------------------+------------+------------+-----------+
    | d0f0cef9-5890-4a68-8974-61ed71b9f5d9 | test-vim-helm | 5a8fb2d2043141c190f227769e06aebb | kubernetes | False      | REACHABLE |
    +--------------------------------------+---------------+----------------------------------+------------+------------+-----------+

A json file which includes Helm VIM information
and additionalParams should be provided
for instantiating a containerized VNF.

The following shows a sample json file.

.. code-block:: json

  {
      "flavourId": "simple",
      "vimConnectionInfo": {
          "vim1": {
              "vimId": "d0f0cef9-5890-4a68-8974-61ed71b9f5d9",
              "vimType": "ETSINFV.KUBERNETES.V_1"
          }
      },
      "additionalParams": {
          "helm_chart_path": "Files/kubernetes/test-chart-0.1.0.tgz",
          "helm_parameters": {
              "service.port": 8081
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

  {
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
  }

.. note::
      Even if this operation specify multiple ``vimConnectionInfo``
      associated with one VNF instance, only one of them will be used for
      life cycle management operations.

Also, a json file must include some parameters for Helm
as additional parameters
The following shows the additional parameters
for deploying CNF by Helm chart.

.. code-block:: console

    +----------------------------+--------------+-----------------------------------------------------------+
    | Attribute name             | Data type    | Parameter description                                     |
    +============================+==============+===========================================================+
    |helm_chart_path             | String       | File path of helm_chart.                                  |
    |                            |              | This parameter must be set                                |
    +----------------------------+--------------+-----------------------------------------------------------+
    |namespace                   | String       | Namespace to deploy Kubernetes resources.                 |
    |                            |              | If absent, the value in Helm chart is used as default.    |
    +----------------------------+--------------+-----------------------------------------------------------+
    |helm_parameters             | Dict         | Parameters of KeyValuePairs,                              |
    |                            |              | which is specified during Helm installation.              |
    +----------------------------+--------------+-----------------------------------------------------------+
    |helm_value_names            | Dict         | This parameter specifies the parameter name to be set     |
    |                            |              | as Helm install parameter.                                |
    +----------------------------+--------------+-----------------------------------------------------------+
    |>replica                    | KeyValuePairs| The parameter mapped to the number of Pods.               |
    |                            |              |                                                           |
    +----------------------------+--------------+-----------------------------------------------------------+

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
--os-tacker-api-version 2`
to instantiate a VNF.

The ``VNF instance ID`` is the ID generated after the
:command:`openstack vnflcm create`
command is executed. We can find it in the [2. Execute Create VNF command]
chapter.

.. code-block:: console

    $ openstack vnflcm instantiate e959ab43-133c-4c50-bb00-e2aadc66e498 helm_instantiate_req --os-tacker-api-version 2
    Instantiate request for VNF Instance e959ab43-133c-4c50-bb00-e2aadc66e498 has been accepted.

3. Check the Instantiation State
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
We could check the Instantiation State by running the following command.
When the Instantiation State is INSTANTIATED, indicate the instantiation is
successful.

.. code-block:: console

    $ openstack vnflcm show e959ab43-133c-4c50-bb00-e2aadc66e498 --os-tacker-api-version 2 --fit-width
    +-----------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field                       | Value                                                                                                                                                                                                                        |
    +-----------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | ID                          | e959ab43-133c-4c50-bb00-e2aadc66e498                                                                                                                                                                                         |
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
    |                             |             "id": "vdu1-vnfe959ab43133c4c50bb00e2aadc66e498-587c564878-r972z",                                                                                                                                         |
    |                             |             "vduId": "VDU1",                                                                                                                                                                                                 |
    |                             |             "computeResource": {                                                                                                                                                                                             |
    |                             |                 "resourceId": "vdu1-vnfe959ab43133c4c50bb00e2aadc66e498-587c564878-r972z",                                                                                                                             |
    |                             |                 "vimLevelResourceType": "Deployment"                                                                                                                                                                         |
    |                             |             },                                                                                                                                                                                                               |
    |                             |             "metadata": {}                                                                                                                                                                                                   |
    |                             |         },                                                                                                                                                                                                                   |
    |                             |         {                                                                                                                                                                                                                    |
    |                             |             "id": "vdu2-vnfe959ab43133c4c50bb00e2aadc66e498-7669fcfbf4-dhhn2",                                                                                                                                         |
    |                             |             "vduId": "VDU2",                                                                                                                                                                                                 |
    |                             |             "computeResource": {                                                                                                                                                                                             |
    |                             |                 "resourceId": "vdu2-vnfe959ab43133c4c50bb00e2aadc66e498-7669fcfbf4-dhhn2",                                                                                                                             |
    |                             |                 "vimLevelResourceType": "Deployment"                                                                                                                                                                         |
    |                             |             },                                                                                                                                                                                                               |
    |                             |             "metadata": {}                                                                                                                                                                                                   |
    |                             |         }                                                                                                                                                                                                                    |
    |                             |     ],                                                                                                                                                                                                                       |
    |                             |     "vnfcInfo": [                                                                                                                                                                                                            |
    |                             |         {                                                                                                                                                                                                                    |
    |                             |             "id": "VDU1-vdu1-vnfe959ab43133c4c50bb00e2aadc66e498-587c564878-r972z",                                                                                                                                    |
    |                             |             "vduId": "VDU1",                                                                                                                                                                                                 |
    |                             |             "vnfcResourceInfoId": "vdu1-vnfe959ab43133c4c50bb00e2aadc66e498-587c564878-r972z",                                                                                                                         |
    |                             |             "vnfcState": "STARTED"                                                                                                                                                                                           |
    |                             |         },                                                                                                                                                                                                                   |
    |                             |         {                                                                                                                                                                                                                    |
    |                             |             "id": "VDU2-vdu2-vnfe959ab43133c4c50bb00e2aadc66e498-7669fcfbf4-dhhn2",                                                                                                                                    |
    |                             |             "vduId": "VDU2",                                                                                                                                                                                                 |
    |                             |             "vnfcResourceInfoId": "vdu2-vnfe959ab43133c4c50bb00e2aadc66e498-7669fcfbf4-dhhn2",                                                                                                                         |
    |                             |             "vnfcState": "STARTED"                                                                                                                                                                                           |
    |                             |         }                                                                                                                                                                                                                    |
    |                             |     ],                                                                                                                                                                                                                       |
    |                             |     "metadata": {                                                                                                                                                                                                            |
    |                             |         "namespace": "default",                                                                                                                                                                                              |
    |                             |         "vdu_reses": {                                                                                                                                                                                                       |
    |                             |             "VDU1": {                                                                                                                                                                                                        |
    |                             |                 "apiVersion": "apps/v1",                                                                                                                                                                                     |
    |                             |                 "kind": "Deployment",                                                                                                                                                                                        |
    |                             |                 "metadata": {                                                                                                                                                                                                |
    |                             |                     "name": "vdu1-vnfe959ab43133c4c50bb00e2aadc66e498",                                                                                                                                      |
    |                             |                     "labels": {                                                                                                                                                                                              |
    |                             |                         "helm.sh/chart": "test-chart-0.1.0",                                                                                                                                                                 |
    |                             |                         "app.kubernetes.io/name": "test-chart",                                                                                                                                                              |
    |                             |                         "app.kubernetes.io/instance": "vnfe959ab43133c4c50bb00e2aadc66e498",                                                                                                                            |
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
    |                             |                             "app.kubernetes.io/instance": "vnfe959ab43133c4c50bb00e2aadc66e498"                                                                                                                         |
    |                             |                         }                                                                                                                                                                                                    |
    |                             |                     },                                                                                                                                                                                                       |
    |                             |                     "template": {                                                                                                                                                                                            |
    |                             |                         "metadata": {                                                                                                                                                                                        |
    |                             |                             "labels": {                                                                                                                                                                                      |
    |                             |                                 "app.kubernetes.io/name": "test-chart",                                                                                                                                                      |
    |                             |                                 "app.kubernetes.io/instance": "vnfe959ab43133c4c50bb00e2aadc66e498"                                                                                                                     |
    |                             |                             }                                                                                                                                                                                                |
    |                             |                         },                                                                                                                                                                                                   |
    |                             |                         "spec": {                                                                                                                                                                                            |
    |                             |                             "serviceAccountName": "vnfe959ab43133c4c50bb00e2aadc66e498-test-chart",                                                                                                                     |
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
    |                             |                     "name": "vdu2-vnfe959ab43133c4c50bb00e2aadc66e498",                                                                                                                                      |
    |                             |                     "labels": {                                                                                                                                                                                              |
    |                             |                         "helm.sh/chart": "test-chart-0.1.0",                                                                                                                                                                 |
    |                             |                         "app.kubernetes.io/name": "test-chart",                                                                                                                                                              |
    |                             |                         "app.kubernetes.io/instance": "vnfe959ab43133c4c50bb00e2aadc66e498",                                                                                                                            |
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
    |                             |                             "app.kubernetes.io/instance": "vnfe959ab43133c4c50bb00e2aadc66e498"                                                                                                                         |
    |                             |                         }                                                                                                                                                                                                    |
    |                             |                     },                                                                                                                                                                                                       |
    |                             |                     "template": {                                                                                                                                                                                            |
    |                             |                         "metadata": {                                                                                                                                                                                        |
    |                             |                             "labels": {                                                                                                                                                                                      |
    |                             |                                 "app.kubernetes.io/name": "test-chart",                                                                                                                                                      |
    |                             |                                 "app.kubernetes.io/instance": "vnfe959ab43133c4c50bb00e2aadc66e498"                                                                                                                     |
    |                             |                             }                                                                                                                                                                                                |
    |                             |                         },                                                                                                                                                                                                   |
    |                             |                         "spec": {                                                                                                                                                                                            |
    |                             |                             "serviceAccountName": "vnfe959ab43133c4c50bb00e2aadc66e498-test-chart",                                                                                                                     |
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
    |                             |         "release_name": "vnfe959ab43133c4c50bb00e2aadc66e498",                                                                                                                                                          |
    |                             |         "revision": "1"                                                                                                                                                                                                      |
    |                             |     }                                                                                                                                                                                                                        |
    |                             | }                                                                                                                                                                                                                            |
    | Instantiation State         | INSTANTIATED                                                                                                                                                                                                                 |
    | Links                       | {                                                                                                                                                                                                                            |
    |                             |     "self": {                                                                                                                                                                                                                |
    |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/e959ab43-133c-4c50-bb00-e2aadc66e498"                                                                                                                         |
    |                             |     },                                                                                                                                                                                                                       |
    |                             |     "terminate": {                                                                                                                                                                                                           |
    |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/e959ab43-133c-4c50-bb00-e2aadc66e498/terminate"                                                                                                               |
    |                             |     },                                                                                                                                                                                                                       |
    |                             |     "scale": {                                                                                                                                                                                                               |
    |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/e959ab43-133c-4c50-bb00-e2aadc66e498/scale"                                                                                                                   |
    |                             |     },                                                                                                                                                                                                                       |
    |                             |     "heal": {                                                                                                                                                                                                                |
    |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/e959ab43-133c-4c50-bb00-e2aadc66e498/heal"                                                                                                                    |
    |                             |     },                                                                                                                                                                                                                       |
    |                             |     "changeExtConn": {                                                                                                                                                                                                       |
    |                             |         "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/e959ab43-133c-4c50-bb00-e2aadc66e498/change_ext_conn"                                                                                                         |
    |                             |     }                                                                                                                                                                                                                        |
    |                             | }                                                                                                                                                                                                                            |
    | VIM Connection Info         | {                                                                                                                                                                                                                            |
    |                             |     "vim1": {                                                                                                                                                                                                                |
    |                             |         "vimId": "d0f0cef9-5890-4a68-8974-61ed71b9f5d9",                                                                                                                                                                     |
    |                             |         "vimType": "ETSINFV.HELM.V_3",                                                                                                                                                                                       |
    |                             |         "interfaceInfo": {                                                                                                                                                                                                   |
    |                             |             "endpoint": "https://192.168.56.10:6443",                                                                                                                                                                        |
    |                             |             "ssl_ca_cert": "-----BEGIN CERTIFICATE----- MIIC/jCCAeagAwIBAgIBADANBgkqhkiG9w0BAQsFADAVMRMwEQYDVQQDEwprdWJl cm5ldGVzMB4XDTIyMDkxMjEwMDMyMloXDTMyMDkwOTEwMDMyMlowFTETMBEGA1UE                                    |
    |                             | AxMKa3ViZXJuZXRlczCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAPcx BVG56RA6EWNm9dUdsJhNzz2VdEHqg2q0P/YBulILMXK3CGpjfAOSJs59Z/TJ2GYx /3TFO5Qy/FekQnoEshI/IBSm34A8g8fiDgRiwTrv4s6LMxOZknICeIj4WrOjOsis                           |
    |                             | VMEVp8VFPM7bMzJnQ9m/9dHkFPTKivV+K/hHH/Fa3FN7Fk8+1rv00qOLrYxpnTMa 96hTzRYwHcXhmfVtgBl1SNnkjd1EN1NNIcAOXNEdEOaU5eBdxjB162ZUPfWxIR7l fDO8qLVZbXWb6rCpHxC1IfWPylNyQMnIGr/uv36yBkoq8ZHy1rUEyS2u/AoVDwfr                           |
    |                             | cmaCJDEGXYXhFe1bIgcCAwEAAaNZMFcwDgYDVR0PAQH/BAQDAgKkMA8GA1UdEwEB /wQFMAMBAf8wHQYDVR0OBBYEFAieaYVCHhDnPIkEgMY1YKSofXeIMBUGA1UdEQQO MAyCCmt1YmVybmV0ZXMwDQYJKoZIhvcNAQELBQADggEBABmy+hKoJ+UkI3d9DOqz                           |
    |                             | MLB8x7NbWJO50wb4KqE/nXRSJDSKObfYNcDMDYh8T7RtSGUe3kxxNpACrHVkUme6 2vjylGkf6kOCLYowH5BjLVfYk/aPDNjWUIdULft0iefqm8MetltokpE00fAeYZ0U q+kFziqOorf58Bmc7TuvdqqlQdNTXMdgMWq6zCfghcDEnLHcuRE4MSgWJXMLY5mw                           |
    |                             | zb0X3hvt3uO8OdHNwRWli/9VAyGro0r0xPgH7LanMd9KnQF17Ux1Y0bNUbqxHwqx xO7lMyo8RP65nIqrTvC9dwvFth8MnSmsNucn0bJhl5Ol69AacT3/TSo+9u8+IJ4G bYU= -----END CERTIFICATE-----"                                                            |
    |                             |         },                                                                                                                                                                                                                   |
    |                             |         "accessInfo": {                                                                                                                                                                                                      |
    |                             |             "bearer_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6ImVFRXhkM2JWM0l5d3p0aGRzUHVzSm8xd25RRXJkby1YN21uZWNiWUppd00ifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2Ui |
    |                             | OiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tazQ1N2MiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291 |
    |                             | bnQvc2VydmljZS1hY2NvdW50LnVpZCI6Ijg5MmZiNjE1LTYxYzQtNDMzZC1hMDU2LTdkNTg5OTJiMDlhZSIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OmRlZmF1bHQifQ.frFlz-jXmOj-wqeupNe1xX1tI1_UBdESw8z3tFzjE3qZwqbP5DYYWw0CqkG8JfE-          |
    |                             | HAte59kooKt7tt8bzfTRavnpHTlF1mGCUyybFTkxC1Rd52lc-cFem_i7ZZSf9Vz0RSoPLDInOqVuSTn9XGYu3t3fyNUN0WKysyhrzYLt5LpI0_zP19u_R_fsENnHLwO5yO4djNVjtchlvKtp0KfwNxZAFwz-DAaWYLK1oDKFXahOQ_Pe026fiUoccsbRsiOhk3hKfy-                      |
    |                             | FhvJN1lOyFLgHsYMmZjDqSS4eON6qHaNNDMUXduThEWpKI3JkwuekheM5ODghIrVqCrwKoeljWnRxGQ"                                                                                                                                             |
    |                             |         }                                                                                                                                                                                                                    |
    |                             |     }                                                                                                                                                                                                                        |
    |                             | }                                                                                                                                                                                                                            |
    | VNF Configurable Properties |                                                                                                                                                                                                                              |
    | VNF Instance Description    |                                                                                                                                                                                                                              |
    | VNF Instance Name           |                                                                                                                                                                                                                              |
    | VNF Product Name            | Sample VNF                                                                                                                                                                                                                   |
    | VNF Provider                | Company                                                                                                                                                                                                                      |
    | VNF Software Version        | 1.0                                                                                                                                                                                                                          |
    | VNFD ID                     | 339f9eb3-ed61-443e-8801-e7cf2474c72a                                                                                                                                                                                         |
    | VNFD Version                | 1.0                                                                                                                                                                                                                          |
    +-----------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

4. Check the Deployment in Kubernetes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We can check the deployed release by running the following command.
Release is an instance of a chart running on a Kubernetes cluster.

.. code-block:: console

    $ helm list
    NAME                                    NAMESPACE       REVISION        UPDATED                                 STATUS          CHART                   APP VERSION
    vnfe959ab43133c4c50bb00e2aadc66e498     default         1               2022-09-13 02:14:32.389689049 +0000 UTC deployed        test-chart-0.1.0        1.16.0

Also, we can check a deployed containerized VNF
by running the following command.
When the READY is 1/1, indicate the deployment is created successfully.

.. code-block:: console

    $ kubectl get deploy
    NAME                                       READY   UP-TO-DATE   AVAILABLE   AGE
    vdu1-vnfe959ab43133c4c50bb00e2aadc66e498   1/1     1            1           5m40s
    vdu2-vnfe959ab43133c4c50bb00e2aadc66e498   1/1     1            1           5m40s

If we want to check whether the resource is deployed in the default namespace,
we can append ``-A`` to the command line.

.. code-block:: console

    $ kubectl get deploy -A
    NAMESPACE     NAME                                       READY   UP-TO-DATE   AVAILABLE   AGE
    default       vdu1-vnfe959ab43133c4c50bb00e2aadc66e498   1/1     1            1           6m
    default       vdu2-vnfe959ab43133c4c50bb00e2aadc66e498   1/1     1            1           6m
    kube-system   kuryr-controller                           1/1     1            1           16h

.. note::

    If a value other than ``default`` is specified for the namespace
    during instantiate, the deployed resources will be instantiated
    in the corresponding namespace.

Supported versions
------------------

Tacker Antelope release

- Helm: 3.10

References
==========
.. [#credential] https://docs.openstack.org/tacker/latest/install/kubernetes_vim_installation.html
.. [#vnfd] https://docs.openstack.org/tacker/latest/user/vnfd-sol001.html
