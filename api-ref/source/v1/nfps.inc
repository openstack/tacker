.. -*- rst -*-

===============================
Network Forwarding Paths (NFPs)
===============================

Lists Network Forwarding Paths (NFPs) and shows information of a given NFP.

The NFP is a component of VNFFG and contains a Service Function Chain (SFC)
and a classifier.

List NFPs
=========

.. rest_method::  GET /v1.0/nfps

Lists NFPs.

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

  - nfps: nfps
  - status: nfp_status
  - name: name
  - tenant_id: tenant_id
  - chain_id: sfc_id
  - path_id: sfc_path_id
  - symmetrical: symmetrical
  - classifier_id: classifier_id
  - id: nfp_id

Response Example
----------------

.. literalinclude:: samples/nfps/nfps-list-response.json
   :language: javascript

Show NFP
========

.. rest_method::  GET /v1.0/nfps/{nfp_id}

Shows information of a given NFP.

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

  - nfp_id: nfp_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - nfp: nfp
  - status: nfp_status
  - name: name
  - tenant_id: tenant_id
  - chain_id: sfc_id
  - path_id: sfc_path_id
  - symmetrical: symmetrical
  - classifier_id: classifier_id
  - id: nfp_id

Response Example
----------------

.. literalinclude:: samples/nfps/nfps-show-response.json
   :language: javascript
