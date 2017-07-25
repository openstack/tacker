.. -*- rst -*-

==================================
Network Service Descriptors (NSD)
==================================

Manages Network Service Descriptors.

NSD is a TOSCA template that describes the deployment and behaviour of a
Network Service (NS) using a collection of VNFs. For more information, see
`NSD Usage Guide
<https://docs.openstack.org/tacker/latest/user/nsd_usage_guide.html>`_.

Create NSD
===========

.. rest_method::  POST /v1.0/nsds

Creates a NSD.

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

  - tenant_id: tenant_id
  - name: name
  - description: description_opt
  - attributes: nsd_attributes

Request Example
---------------

.. literalinclude:: samples/nsds/nsds-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - nsd: nsd
  - name: name
  - id: nsd_id
  - tenant_id: tenant_id
  - description: description
  - created_at: created_at
  - updated_at: updated_at
  - attributes: nsd_attributes

Response Example
----------------

.. literalinclude:: samples/nsds/nsds-create-response.json
   :language: javascript

List NSDs
==========

.. rest_method::  GET /v1.0/nsds

Lists NSDs.

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

  - nsds: nsds
  - name: name
  - id: nsd_id
  - tenant_id: tenant_id
  - description: description
  - created_at: created_at
  - updated_at: updated_at
  - attributes: nsd_attributes

Response Example
----------------

.. literalinclude:: samples/nsds/nsds-list-response.json
   :language: javascript

Show NSD
=========

.. rest_method::  GET /v1.0/nsds/{nsd_id}

Shows information of a given NSD.

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

  - nsd_id: nsd_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - nsds: nsds
  - name: name
  - id: nsd_id
  - tenant_id: tenant_id
  - description: description
  - created_at: created_at
  - updated_at: updated_at
  - attributes: nsd_attributes

Response Example
----------------

.. literalinclude:: samples/nsds/nsds-show-response.json
   :language: javascript

Delete NSD
===========

.. rest_method::  DELETE /v1.0/nsds/{nsd_id}

Deletes a given NSD.
Only a NSD without any associated NSs can be deleted.

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

  - nsd_id: nsd_id_path
