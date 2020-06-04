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

.. rest_parameters:: parameters_vnf_packages.yaml

  - userDefinedData: user_defined_data_opt

Request Example
---------------

.. literalinclude:: samples/vnf_packages/vnf-packages-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters_vnf_packages.yaml

  - id: vnf_package_id
  - _links: vnf_pkg_links
  - onboardingState: onboarding_state
  - operationalState: operational_state
  - usageState: usage_state
  - userDefinedData: user_defined_data

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

.. rest_parameters:: parameters_vnf_packages.yaml

  - id: vnf_package_id
  - vnfdId: vnf_pkg_vnfd_id
  - vnfProvider: vnf_provider
  - vnfProductName: vnf_product_name
  - vnfSoftwareVersion: vnf_software_version
  - vnfdVersion: vnfd_version
  - softwareImages: software_images
  - onboardingState: onboarding_state
  - operationalState: operational_state
  - usageState: usage_state
  - userDefinedData: user_defined_data
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

.. rest_parameters:: parameters_vnf_packages.yaml

  - vnf_package_id: vnf_package_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters_vnf_packages.yaml

  - id: vnf_package_id
  - vnfdId: vnf_pkg_vnfd_id
  - vnfProvider: vnf_provider
  - vnfProductName: vnf_product_name
  - vnfSoftwareVersion: vnf_software_version
  - vnfdVersion: vnfd_version
  - softwareImages: software_images
  - onboardingState: onboarding_state
  - operationalState: operational_state
  - usageState: usage_state
  - userDefinedData: user_defined_data
  - _links: vnf_pkg_links

Response Example
----------------

.. literalinclude:: samples/vnf_packages/vnf-packages-show-response.json
   :language: javascript

Delete VNF Package
==================

.. rest_method::  DELETE /vnfpkgm/v1/vnf_packages/{vnf_package_id}

Deletes a given VNF Package.

**Preconditions**

The vnf package ``operationalState`` value must be ``DISABLED`` and it's
``usageState`` value must be ``NOT_IN_USE``.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 204

.. rest_status_code:: error status.yaml

  - 401
  - 403
  - 404
  - 409

Request Parameters
------------------

.. rest_parameters:: parameters_vnf_packages.yaml

  - vnf_package_id: vnf_package_id_path

Upload VNF Package from content
===============================

.. rest_method::  PUT /vnfpkgm/v1/vnf_packages/{vnf_package_id}/package_content

Upload a given VNF Package from content.

.. note::
    Please refer `Hashing algorithm for software image checksum`_ section
    for more information about software image checksum.

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

.. rest_parameters:: parameters_vnf_packages.yaml

  - vnf_package_id: vnf_package_id_path
  - vnf_package_content: vnf_pkg_content

Upload VNF Package from uri
===========================

.. rest_method::  POST /vnfpkgm/v1/vnf_packages/{vnf_package_id}/package_content/upload_from_uri

Upload a given VNF Package from content.

.. note::
    Please refer `Hashing algorithm for software image checksum`_ section
    for more information about software image checksum.

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

.. rest_parameters:: parameters_vnf_packages.yaml

  - vnf_package_id: vnf_package_id_path
  - addressInformation: address_information
  - userName: user_name
  - password: password

Update VNF Package Information
==============================

.. rest_method::  PATCH /vnfpkgm/v1/vnf_packages/{vnf_package_id}

Updates the information of a VNF package.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 403
  - 404
  - 409

Request Parameters
------------------

.. rest_parameters:: parameters_vnf_packages.yaml

  - vnf_package_id: vnf_package_id_path
  - operationalState: update_operational_state
  - userDefinedData: update_user_defined_data

.. note::
    At least one of the "operationalState" or "userDefinedData" parameters
    shall be present. If the VNF package is not on-boarded, the operation is
    used only to update existing or add additional user defined data using the
    "userDefinedData" attribute. If user passes existing user defined data
    with exact same key/values pairs, then it would return 400 error.

Request Example
---------------

.. literalinclude:: samples/vnf_packages/vnf-packages-patch-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters_vnf_packages.yaml

  - operationalState: updated_operational_state
  - userDefinedData: updated_user_defined_data

Response Example
----------------

.. literalinclude:: samples/vnf_packages/vnf-packages-patch-response.json
   :language: javascript

Read VNFD of an individual VNF package
======================================

.. rest_method::  GET /vnfpkgm/v1/vnf_packages/{vnf_package_id}/vnfd

Read VNFD of an on-boarded VNF package.

The VNFD can be implemented as a single file or as a collection of multiple
files. If the VNFD is implemented in the form of multiple files, a ZIP file
embedding these files shall be returned. If the VNFD is implemented as a
single file, either that file or a ZIP file embedding that file shall be
returned. The selection of the format is controlled by the "Accept" HTTP
header passed in the GET request.

If the "Accept" header contains only "text/plain" and the VNFD is implemented
as a single file, the file shall be returned; otherwise, an error message shall
be returned.
If the "Accept" header contains only "application/zip", the single file or
the multiple files that make up the VNFD shall be returned embedded in a ZIP
file.
If the "Accept" header contains both "text/plain" and "application/zip", it
is up to the NFVO to choose the format to return for a single-file VNFD; for a
multi-file VNFD, a ZIP file shall be returned.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 403
  - 404
  - 406
  - 409
  - 500

Request Parameters
------------------

.. rest_parameters:: parameters_vnf_packages.yaml

  - vnf_package_id: vnf_package_id_path
  - Accept: content_type

Response
--------

.. rest_parameters:: parameters_vnf_packages.yaml

  - Content-Type: content_type

Fetch an on-boarded VNF package with HTTP_RANGE
================================================

.. rest_method::  GET /vnfpkgm/v1/vnf_packages/{vnf_package_id}/package_content

Fetch an on-boarded VNF package with HTTP_RANGE.

The GET method fetches the content of a VNF package identified by
the VNF package identifier allocated by the NFVO.

The 'HTTP_RANGE' header is inspected for a valid value.
If it is present and valid, then the package content within
the range is fetched. If not present the entire content is
fetched.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200
  - 206

.. rest_status_code:: error status.yaml

  - 403
  - 404
  - 409
  - 416
  - 500

Request Parameters
------------------

.. rest_parameters:: parameters_vnf_packages.yaml

  - vnf_package_id: vnf_package_id_path
  - Accept: fetch_content_type
  - Range: range

Response
--------

.. rest_parameters:: parameters_vnf_packages.yaml

  - Content-Type: fetch_content_type

Reference
---------

.. _ETSI_GS_NFV_SOL_004 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/004/02.06.01_60/gs_NFV-SOL004v020601p.pdf

Hashing algorithm for software image checksum
=============================================

While adding software images in VNF descriptors of VNF packages,
it is recommended to use ``algorithm`` as defined in `ETSI_GS_NFV_SOL_004`_
and it must also match with the ``hashing_algorithm`` config option
set by ``Glance`` service otherwise it will fail to verify
checksum during instantiation of VNF. The default ``hashing_algorithm``
configured in ``Glance`` service is ``sha512`` and an operator can
override the default with any of these algorithms sha3_384, sha224,
md5, sha512, blake2b, sha3_512, blake2s, sha384, sha1, shake_256,
sha256, shake_128 and sha3_256.
