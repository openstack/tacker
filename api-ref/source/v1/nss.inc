.. -*- rst -*-

====================================
Network Services (NSs)
====================================

Manages Network Servicess (NSs) and their resources.

NS resources are instantiations of network services described in the
associated NSD TOSCA template.

Create NS
==========

.. rest_method::  POST /v1.0/nss

Creates a NS.

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

  - ns: ns
  - name: name
  - description: description_opt
  - nsd_id: nsd_id
  - vim_id: vim_id_opt
  - tenant_id: tenant_id_opt
  - attributes: ns_attributes_opt

Request Example
---------------

.. literalinclude:: samples/nss/nss-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - ns: ns
  - name: name
  - description: description
  - status: ns_status
  - id: ns_id
  - nsd_id: nsd_id
  - vnf_ids: vnf_ids
  - tenant_id: tenant_id
  - created_at: ns_created_at
  - updated_at: ns_updated_at
  - mgmt_ip_address: ns_mgmt_ip_address
  - vim_id: vim_id
  - error_reason: ns_error_reason
  - attributes: ns_attributes

Response Example
----------------

.. literalinclude:: samples/nss/nss-create-response.json
   :language: javascript

List NSs
=========

.. rest_method::  GET /v1.0/nss

Lists NSs.

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

  - nss: nss
  - name: name
  - description: description
  - status: ns_status
  - id: ns_id
  - nsd_id: nsd_id
  - vnf_ids: vnf_ids
  - tenant_id: tenant_id
  - created_at: ns_created_at
  - updated_at: ns_updated_at
  - mgmt_ip_address: ns_mgmt_ip_address
  - vim_id: vim_id
  - error_reason: ns_error_reason
  - attributes: ns_attributes

Response Example
----------------

.. literalinclude:: samples/nss/nss-list-response.json
   :language: javascript

Show NS
========

.. rest_method::  GET /v1.0/nss/{ns_id}

Shows information of a given NS.

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

  - ns_id: ns_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - ns: ns
  - name: name
  - description: description
  - status: ns_status
  - id: ns_id
  - nsd_id: nsd_id
  - vnf_ids: vnf_ids
  - tenant_id: tenant_id
  - created_at: ns_created_at
  - updated_at: ns_updated_at
  - mgmt_ip_address: ns_mgmt_ip_address
  - vim_id: vim_id
  - error_reason: ns_error_reason
  - attributes: ns_attributes

Response Example
----------------

.. literalinclude:: samples/nss/nss-show-response.json
   :language: javascript
