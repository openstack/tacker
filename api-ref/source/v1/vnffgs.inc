.. -*- rst -*-

==============================
VNF Forwarding Graphs (VNFFGs)
==============================

Manages VNF Forwarding Graphs (VNFFGs).

The VNFFG feature is used to orchestrate and manage traffic through VNFs.
For more information about VNFFG, see
`VNF Forwarding Graph
<https://docs.openstack.org/tacker/latest/user/vnffg_usage_guide.html>`_.

Create VNFFG
============

.. rest_method::  POST /v1.0/vnffgs

Creates a VNFFG.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 201

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404
  - 500

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - tenant_id: tenant_id_opt
  - vnffgd_id: vnffgd_id
  - name: name
  - vnf_mapping: vnf_mapping_opt
  - symmetrical: symmetrical_opt

Request Example
---------------

.. literalinclude:: samples/vnffgs/vnffgs-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - vnffg: vnffg
  - forwarding_paths: vnffg_forwarding_paths
  - status: vnffg_status
  - description: description
  - tenant_id: tenant_id
  - vnffgd_id: vnffgd_id
  - vnf_mapping: vnf_mapping
  - id: vnffg_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/vnffgs/vnffgs-create-response.json
   :language: javascript

List VNFFGs
===========

.. rest_method::  GET /v1.0/vnffgs

Lists VNFFGs.

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

  - vnffgs: vnffgs
  - forwarding_paths: vnffg_forwarding_paths
  - status: vnffg_status
  - description: description
  - tenant_id: tenant_id
  - vnffgd_id: vnffgd_id
  - vnf_mapping: vnf_mapping
  - id: vnffg_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/vnffgs/vnffgs-list-response.json
   :language: javascript

Show VNFFG
==========

.. rest_method::  GET /v1.0/vnffgs/{vnffg_id}

Shows information of a given VNFFG.

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

  - vnffg_id: vnffg_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - vnffg: vnffg
  - forwarding_paths: vnffg_forwarding_paths
  - status: vnffg_status
  - description: description
  - tenant_id: tenant_id
  - vnffgd_id: vnffgd_id
  - vnf_mapping: vnf_mapping
  - id: vnffg_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/vnffgs/vnffgs-show-response.json
   :language: javascript

Delete VNFFG
============

.. rest_method::  DELETE /v1.0/vnffgs/{vnffg_id}

Deletes a given VNFFG.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 204

.. rest_status_code:: error status.yaml

  - 401
  - 404
  - 409
  - 500

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - vnffg_id: vnffg_id_path
