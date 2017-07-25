.. -*- rst -*-

==========================================
VNF Forwarding Graph Descriptors (VNFFGDs)
==========================================

Manages VNF Forwarding Graph Descriptors (VNFFGDs).

The VNFFGD is a template which describes information about deployment and
behavior of VNF Forwarding Graphs (VNFFGs). For more information, see
`VNFFG Descriptor Template Guide
<https://docs.openstack.org/tacker/latest/contributor/vnffgd_template_description.html>`_.


Create VNFFGD
=============

.. rest_method::  POST /v1.0/vnffgds

Creates a VNFFGD.

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
  - template: vnffgd_template
  - description: description_opt

Request Example
---------------

.. literalinclude:: samples/vnffgds/vnffgds-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - vnffgd: vnffgd
  - tenant_id: tenant_id
  - name: name
  - template: vnffgd_template
  - description: description

Response Example
----------------

.. literalinclude:: samples/vnffgds/vnffgds-create-response.json
   :language: javascript

List VNFFGDs
============

.. rest_method::  GET /v1.0/vnffgds

Lists VNFFGDs.

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

  - vnffgds: vnffgds
  - description: description
  - tenant_id: tenant_id
  - id: vnffgd_id
  - name: name


Response Example
----------------

.. literalinclude:: samples/vnffgds/vnffgds-list-response.json
   :language: javascript

Show VNFFGD
===========

.. rest_method::  GET /v1.0/vnffgds/{vnffgd_id}

Shows information of a given VNFFGD.

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

  - vnffgd_id: vnffgd_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - vnffgd: vnffgd
  - description: description
  - tenant_id: tenant_id
  - id: vnffgd_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/vnffgds/vnffgds-show-response.json
   :language: javascript

Delete VNFFGD
=============

.. rest_method::  DELETE /v1.0/vnffgds/{vnffgd_id}

Deletes a given VNFFGD.
Only a VNFFGD without any associated VNFFGs can be deleted.

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

  - vnffgd_id: vnffgd_id_path
