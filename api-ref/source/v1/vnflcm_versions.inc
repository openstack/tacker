.. -*- rst -*-

==============================================================
Virtualized Network Function Lifecycle Management API Versions
==============================================================

List VNFLCM API versions
========================

.. rest_method::  GET /vnflcm/api_versions

This method retrieves the list of all supported versions for
VNF LCM API.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401


Request Example
---------------

.. literalinclude:: samples/vnflcm/create-vnf-instance-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters_vnflcm_versions.yaml

  - uriPrefix: uriPrefix
  - apiVersions: api_Versions
  - \>version: version
  - \>isDeprecated: isDeprecated
  - \>retirementDate: retirementDate


Response Example
----------------

.. literalinclude:: samples/vnflcm_versions/list-vnflcm-version-response.json
   :language: javascript

Show VNFLCM API versions
========================

.. rest_method::  GET /vnflcm/{apiMajorVersion}/api_versions

This method retrieves the list of supported versions for
VNF LCM API corresponding to the {apiMajorVersion}.

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm_versions.yaml

  - apiMajorVersion: api_Major_Version

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401


Response Parameters
-------------------

.. rest_parameters:: parameters_vnflcm_versions.yaml

  - uriPrefix: uriPrefix
  - apiVersions: api_Versions
  - \>version: version
  - \>isDeprecated: isDeprecated
  - \>retirementDate: retirementDate


Response Example
----------------

.. literalinclude:: samples/vnflcm_versions/show-vnflcm-version-response.json
   :language: javascript

