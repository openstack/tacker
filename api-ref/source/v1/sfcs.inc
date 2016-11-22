.. -*- rst -*-

==============================
Service Function Chains (SFCs)
==============================

Lists Service Function Chains (SFCs) and shows information of a given SFC.

The SFC is a component of a NFP and forms a path which traffics flow through.

List SFCs
=========

.. rest_method::  GET /v1.0/sfcs

Lists SFCs.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 401
  - 500

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - sfcs: sfcs
  - status: sfc_status
  - path_id: sfc_path_id
  - nfp_id: sfc_nfp_id
  - chain: sfc_chain
  - tenant_id: tenant_id
  - instance_id: sfc_instance_id
  - symmetrical: symmetrical
  - id: sfc_id

Response Example
----------------

.. literalinclude:: samples/sfcs/sfcs-list-response.json
   :language: javascript

Show SFC
========

.. rest_method::  GET /v1.0/sfcs/{sfc_id}

Shows information of a given SFC.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 401
  - 404
  - 500

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - sfc_id: sfc_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - sfc: sfc
  - status: sfc_status
  - path_id: sfc_path_id
  - nfp_id: sfc_nfp_id
  - chain: sfc_chain
  - tenant_id: tenant_id
  - instance_id: sfc_instance_id
  - symmetrical: symmetrical
  - id: sfc_id

Response Example
----------------

.. literalinclude:: samples/sfcs/sfcs-show-response.json
   :language: javascript
