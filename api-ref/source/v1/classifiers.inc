.. -*- rst -*-

===========
Classifiers
===========

Lists classifiers and shows information of a given classifier.

The classifier is a component of a NFP and defines policies to
distinguish which traffic should enter the related SFC.

List classifiers
================

.. rest_method::  GET /v1.0/classifiers

Lists classifiers.

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

  - classifiers: classifiers
  - status: classifier_status
  - nfp_id: classifier_nfp_id
  - tenant_id: tenant_id
  - chain_id: classifier_chain_id
  - instance_id: classifier_instance_id
  - id: classifier_id
  - match: classifier_match

Response Example
----------------

.. literalinclude:: samples/classifiers/classifiers-list-response.json
   :language: javascript

Show classifier
===============

.. rest_method::  GET /v1.0/classifiers/{sfc_id}

Shows information of a given classifier.

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

  - classifiers: classifiers
  - status: classifier_status
  - nfp_id: classifier_nfp_id
  - tenant_id: tenant_id
  - chain_id: classifier_chain_id
  - instance_id: classifier_instance_id
  - id: classifier_id
  - match: classifier_match

Response Example
----------------

.. literalinclude:: samples/classifiers/classifiers-show-response.json
   :language: javascript
