.. -*- rst -*-

==========
Extensions
==========

Lists extensions and shows information of a given extension.

Extensions introduce features to the API.

List extensions
===============

.. rest_method::  GET /v1.0/extensions

Lists available extensions.

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

  - extensions: extensions
  - updated: extension_updated_at
  - name: name
  - links: links
  - alias: alias
  - description: description

Response Example
----------------

.. literalinclude:: samples/extensions/extensions-list-response.json
   :language: javascript

Show extension
==============

.. rest_method::  GET /v1.0/extensions/{alias}

Shows information of a given extension.

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

  - alias: alias_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - extension: extensions
  - updated: extension_updated_at
  - name: name
  - links: links
  - alias: alias
  - description: description

Response Example
----------------

.. literalinclude:: samples/extensions/extensions-show-response.json
   :language: javascript
