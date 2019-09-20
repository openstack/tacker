.. -*- rst -*-

====================================================
Virtualized Network Function Packages (VNF packages)
====================================================

Manages Virtualized Network Function Packages (VNF Packages) and their resources.

A VNF Package is a tar-archive containing all the information required for managing
the lifecycle of a VNF.

Create VNF Package
==================

.. rest_method::  POST /vnfpkgm/v1/vnf_packages

Creates a VNF Package.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 201

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 403

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - userDefinedData: userDefinedData

Request Example
---------------

.. literalinclude:: samples/vnf_packages/vnf-packages-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - id: vnf_package_id
  - _links: vnf_pkg_links
  - onboardingState: onboardingState
  - operationalState: operationalState
  - usageState: usageState
  - userDefinedData: userDefinedData

Response Example
----------------

.. literalinclude:: samples/vnf_packages/vnf-packages-create-response.json
   :language: javascript

List VNF Packages
=================

.. rest_method::  GET /vnfpkgm/v1/vnf_packages

Lists VNF Packages.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 401
  - 403

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - id: vnf_package_id
  - vnfdId: vnf_pkg_vnfd_id
  - vnfProvider: vnf_provider
  - vnfProductName: vnf_product_name
  - vnfSoftwareVersion: vnf_software_version
  - vnfdVersion: vnfd_version
  - softwareImages: software_images
  - onboardingState: onboardingState
  - operationalState: operationalState
  - usageState: usageState
  - userDefinedData: userDefinedData
  - _links: vnf_pkg_links

Response Example
----------------

.. literalinclude:: samples/vnf_packages/vnf-packages-list-response.json
   :language: javascript

Show VNF Package
=================

.. rest_method::  GET /vnfpkgm/v1/vnf_packages/{vnf_package_id}

Shows information of a given VNF Package.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 401
  - 403
  - 404

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - vnf_package_id: vnf_package_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - id: vnf_package_id
  - vnfdId: vnf_pkg_vnfd_id
  - vnfProvider: vnf_provider
  - vnfProductName: vnf_product_name
  - vnfSoftwareVersion: vnf_software_version
  - vnfdVersion: vnfd_version
  - softwareImages: software_images
  - onboardingState: onboardingState
  - operationalState: operationalState
  - usageState: usageState
  - userDefinedData: userDefinedData
  - _links: vnf_pkg_links

Response Example
----------------

.. literalinclude:: samples/vnf_packages/vnf-packages-show-response.json
   :language: javascript

Delete VNF Package
==================

.. rest_method::  DELETE /vnfpkgm/v1/vnf_packages/{vnf_package_id}

Deletes a given VNF Package.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 204

.. rest_status_code:: error status.yaml

  - 401
  - 403
  - 404

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - vnf_package_id: vnf_package_id_path

Upload VNF Package from content
===============================

.. rest_method::  PUT /vnfpkgm/v1/vnf_packages/{vnf_package_id}/package_content

Upload a given VNF Package from content.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 202

.. rest_status_code:: error status.yaml

  - 401
  - 403
  - 404
  - 409

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - vnf_package_id: vnf_package_id_path
  - vnf_package_content: vnf_pkg_content

Upload VNF Package from uri
===========================

.. rest_method::  POST /vnf_packages/{vnf_package_id}/package_content/upload_from_uri

Upload a given VNF Package from content.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 202

.. rest_status_code:: error status.yaml

  - 401
  - 400
  - 403
  - 404
  - 409

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - vnf_package_id: vnf_package_id_path
  - addressInformation: addressInformation
  - userName: userName
  - password: password