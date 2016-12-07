.. -*- rst -*-

============
API versions
============

Lists information of NFV Orchestration API versions.

List versions
=============

.. rest_method::  GET /

Lists NFV Orchestration API versions.

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

  - versions: versions
  - status: version_status
  - id: version_id
  - links: version_links
  - href: version_href
  - rel: version_rel

Response Example
----------------

.. literalinclude:: samples/versions/versions-list-response.json
   :language: javascript
