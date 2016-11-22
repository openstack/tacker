.. -*- rst -*-

==========================================
Virtualized Infrastructure Managers (VIMs)
==========================================

Manages Virtualized Infrastructure Managers (VIMs).

The VIM is responsible for controlling and managing Network Function
Virtualization Infrastructure (NFVI) which provides VNFs with the
resources they need.

Register VIM
============

.. rest_method::  POST /v1.0/vims

Registers a VIM.

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

  - vim: vim
  - tenant_id: tenant_id_opt
  - type: vim_type
  - auth_url: vim_auth_url
  - auth_cred: vim_auth_cred
  - vim_project: vim_project
  - name: name
  - description: description_opt
  - is_default: vim_is_default_opt

Request Example
---------------

.. literalinclude:: samples/vims/vims-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - vim: vim
  - status: vim_status
  - description: description
  - tenant_id: tenant_id
  - created_at: vim_created_at
  - vim_project: vim_project
  - updated_at: vim_updated_at
  - is_default: vim_is_default
  - auth_url: vim_auth_url
  - placement_attr: vim_placement_attr
  - auth_cred: vim_auth_cred_output
  - type: vim_type
  - id: vim_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/vims/vims-create-response.json
   :language: javascript

List VIMs
=========

.. rest_method::  GET /v1.0/vims

Lists VIMs.

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

  - vims: vims
  - status: vim_status
  - description: description
  - tenant_id: tenant_id
  - created_at: vim_created_at
  - vim_project: vim_project
  - updated_at: vim_updated_at
  - is_default: vim_is_default
  - auth_url: vim_auth_url
  - placement_attr: vim_placement_attr
  - auth_cred: vim_auth_cred_output
  - type: vim_type
  - id: vim_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/vims/vims-list-response.json
   :language: javascript

Show VIM
========

.. rest_method::  GET /v1.0/vims/{vim_id}

Shows information of a given VIM.

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

  - vim_id: vim_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - vim: vim
  - status: vim_status
  - description: description
  - tenant_id: tenant_id
  - created_at: vim_created_at
  - vim_project: vim_project
  - updated_at: vim_updated_at
  - is_default: vim_is_default
  - auth_url: vim_auth_url
  - placement_attr: vim_placement_attr
  - auth_cred: vim_auth_cred_output
  - type: vim_type
  - id: vim_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/vims/vims-show-response.json
   :language: javascript

Update VIM
==========

.. rest_method::  PUT /v1.0/vims/{vim_id}

Updates a given VIM.
Only a VIM without any associated VNFs can be updated.

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

  - vim_id: vim_id_path
  - vim: vim
  - auth_cred: vim_auth_cred
  - vim_project: vim_project_opt
  - name: name_opt
  - description: description_opt
  - is_default: vim_is_default_opt

Request Example
---------------

.. literalinclude:: samples/vims/vims-update-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - vim: vim
  - status: vim_status
  - description: description
  - tenant_id: tenant_id
  - created_at: vim_created_at
  - vim_project: vim_project
  - updated_at: vim_updated_at
  - is_default: vim_is_default
  - auth_url: vim_auth_url
  - placement_attr: vim_placement_attr
  - auth_cred: vim_auth_cred_output
  - type: vim_type
  - id: vim_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/vims/vims-update-response.json
   :language: javascript

Delete VIM
==========

.. rest_method::  DELETE /v1.0/vims/{vim_id}

Deletes a given VIM.
Only a VIM without any associated VNFs can be deleted.

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

  - vim_id: vim_id_path
