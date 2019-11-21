.. -*- rst -*-

====================================
Virtualized Network Functions (VNFs)
====================================

Manages Virtualized Network Functions (VNFs) and their resources.

The VNF takes on the responsibility for handling specific network functions.

Create VNF
==========

.. rest_method::  POST /v1.0/vnfs

Creates a VNF.

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

  - vnf: vnf
  - tenant_id: tenant_id_opt
  - vnfd_id: vnfd_id
  - vim_id: vim_id_opt
  - name: name
  - description: description_opt
  - attributes: vnf_attributes_opt
  - config: vnf_config_opt
  - param_values: vnf_param_values_opt
  - placement_attr: vnf_placement_attr_opt
  - vnfd_template: vnfd_template

Request Example
---------------

.. literalinclude:: samples/vnfs/vnfs-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - vnf: vnf
  - status: vnf_status
  - description: description
  - vnfd_id: vnfd_id
  - tenant_id: tenant_id
  - created_at: vnf_created_at
  - updated_at: vnf_updated_at
  - instance_id: vnf_instance_id
  - mgmt_ip_address: vnf_mgmt_ip_address
  - vim_id: vim_id
  - placement_attr: vnf_placement_attr
  - error_reason: vnf_error_reason
  - attributes: vnf_attributes
  - config: vnf_config
  - param_values: vnf_param_values
  - monitoring_policy: vnf_monitoring_policy
  - heat_template: vnf_heat_template
  - id: vnf_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/vnfs/vnfs-create-response.json
   :language: javascript

List VNFs
=========

.. rest_method::  GET /v1.0/vnfs

Lists VNFs.

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

  - vnfs: vnfs
  - status: vnf_status
  - description: description
  - vnfd_id: vnfd_id
  - tenant_id: tenant_id
  - created_at: vnf_created_at
  - updated_at: vnf_updated_at
  - instance_id: vnf_instance_id
  - mgmt_ip_address: vnf_mgmt_ip_address
  - vim_id: vim_id
  - placement_attr: vnf_placement_attr
  - error_reason: vnf_error_reason
  - attributes: vnf_attributes
  - config: vnf_config
  - param_values: vnf_param_values
  - monitoring_policy: vnf_monitoring_policy
  - heat_template: vnf_heat_template
  - id: vnf_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/vnfs/vnfs-list-response.json
   :language: javascript

Show VNF
========

.. rest_method::  GET /v1.0/vnfs/{vnf_id}

Shows information of a given VNF.

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

  - vnf_id: vnf_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - vnf: vnf
  - status: vnf_status
  - description: description
  - vnfd_id: vnfd_id
  - tenant_id: tenant_id
  - created_at: vnf_created_at
  - updated_at: vnf_updated_at
  - instance_id: vnf_instance_id
  - mgmt_ip_address: vnf_mgmt_ip_address
  - vim_id: vim_id
  - placement_attr: vnf_placement_attr
  - error_reason: vnf_error_reason
  - attributes: vnf_attributes
  - config: vnf_config
  - param_values: vnf_param_values
  - monitoring_policy: vnf_monitoring_policy
  - heat_template: vnf_heat_template
  - id: vnf_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/vnfs/vnfs-show-response.json
   :language: javascript

Update VNF
===========

.. rest_method::  PUT /v1.0/vnfs/{vnf_id}

Updates a given VNF.

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

  - vnf_id: vnf_id_path
  - attributes: vnf_attributes_put
  - config: vnf_config_opt

Request Example
---------------

.. literalinclude:: samples/vnfs/vnfs-update-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - vnf: vnf
  - status: vnf_status
  - description: description
  - vnfd_id: vnfd_id
  - tenant_id: tenant_id
  - created_at: vnf_created_at
  - updated_at: vnf_updated_at
  - instance_id: vnf_instance_id
  - mgmt_ip_address: vnf_mgmt_ip_address
  - vim_id: vim_id
  - placement_attr: vnf_placement_attr
  - error_reason: vnf_error_reason
  - attributes: vnf_attributes
  - config: vnf_config
  - param_values: vnf_param_values
  - monitoring_policy: vnf_monitoring_policy
  - heat_template: vnf_heat_template
  - id: vnf_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/vnfs/vnfs-update-response.json
   :language: javascript

Delete VNF
==========

.. rest_method::  DELETE /v1.0/vnfs/{vnf_id}

Deletes a given VNF.

.. note::
    Non-admin users are not allowed to delete a VNF in ``PENDING_CREATE`` and
    ``PENDING_DELETE`` status. In this case, it would return 409 error. Admin
    users can delete a VNF in any status with force flag true.

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

  - vnf_id: vnf_id_path
  - attributes: vnf_force_delete_flag

Request Example
---------------

Admin user can request to delete VNF forcefully.

.. literalinclude:: samples/vnfs/vnfs-delete-request.json
   :language: javascript

List VNF resources
==================

.. rest_method::  GET /v1.0/vnfs/{vnf_id}/resources

Lists resources, such as VDU/CP, of a given VNF.

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

  - vnf_id: vnf_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - resources: vnf_resources
  - type: vnf_resource_type
  - name: vnf_resource_name
  - id: vnf_resource_id

Response Example
----------------

.. literalinclude:: samples/vnfs/vnfs-resources-list-response.json
   :language: javascript

Trigger VNF scaling
===================

.. rest_method::  POST /v1.0/vnfs/{vnf_id}/actions

Triggers VNF scaling action.

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

  - vnf_id: vnf_id_path
  - scale: vnf_scale
  - policy: vnf_scale_policy
  - type: vnf_scale_type

Request Example
---------------

.. literalinclude:: samples/vnfs/vnfs-actions-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - scale: vnf_scale
  - policy: vnf_scale_policy
  - type: vnf_scale_type

Response Example
----------------

.. literalinclude:: samples/vnfs/vnfs-actions-create-response.json
   :language: javascript
