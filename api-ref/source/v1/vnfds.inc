.. -*- rst -*-

================================================
Virtualized Network Function Descriptors (VNFDs)
================================================

Manages Virtualized Network Function Descriptors (VNFDs).

The VNFD is a template which describes information about deployment
and behavior of Virtualized Network Functions (VNFs). For more information, see
`VNF Descriptor Template Guide
<https://docs.openstack.org/tacker/latest/contributor/vnfd_template_description.html>`_.

Create VNFD
===========

.. rest_method::  POST /v1.0/vnfds

Creates a VNFD.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 201

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 500

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - tenant_id: tenant_id_opt
  - name: name
  - description: description_opt
  - service_types: service_types
  - attributes: vnfd_attributes

Request Example
---------------

.. literalinclude:: samples/vnfds/vnfds-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - vnfd: vnfd
  - service_types: service_types
  - description: description
  - tenant_id: tenant_id
  - created_at: created_at
  - updated_at: updated_at
  - attributes: vnfd_attributes
  - id: vnfd_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/vnfds/vnfds-create-response.json
   :language: javascript

List VNFDs
==========

.. rest_method::  GET /v1.0/vnfds

Lists VNFDs.

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

  - vnfds: vnfds
  - service_types: service_types
  - description: description
  - tenant_id: tenant_id
  - created_at: created_at
  - updated_at: updated_at
  - attributes: vnfd_attributes
  - id: vnfd_id
  - name: name
  - template_source: vnfd_template_source


Response Example
----------------

.. literalinclude:: samples/vnfds/vnfds-list-response.json
   :language: javascript

Show VNFD
=========

.. rest_method::  GET /v1.0/vnfds/{vnfd_id}

Shows information of a given VNFD.

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

  - vnfd_id: vnfd_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - vnfd: vnfd
  - service_types: service_types
  - description: description
  - tenant_id: tenant_id
  - created_at: created_at
  - updated_at: updated_at
  - attributes: vnfd_attributes
  - id: vnfd_id
  - name: name
  - template_source: vnfd_template_source

Response Example
----------------

.. literalinclude:: samples/vnfds/vnfds-show-response.json
   :language: javascript

Update VNFD
===========

.. rest_method::  PUT /v1.0/vnfds/{vnfd_id}

Updates a given VNFD.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404
  - 409
  - 500

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - vnfd_id: vnfd_id_path
  - name: name_opt
  - description: description_opt

Request Example
---------------

.. literalinclude:: samples/vnfds/vnfds-update-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - vnfd: vnfd
  - service_types: service_types
  - description: description
  - tenant_id: tenant_id
  - created_at: created_at
  - updated_at: updated_at
  - attributes: vnfd_attributes
  - id: vnfd_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/vnfds/vnfds-update-response.json
   :language: javascript

Delete VNFD
===========

.. rest_method::  DELETE /v1.0/vnfds/{vnfd_id}

Deletes a given VNFD.
Only a VNFD without any associated VNFs can be deleted.

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

  - vnfd_id: vnfd_id_path
