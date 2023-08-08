==========================================
VNF Lifecycle Operation Granting interface
==========================================

Grainting interface for giving VNFM a permission from NFVO to enable to run VNF
lifecycle operations and its configurations
as defined in ETSI `NFV-SOL 003 v2.6.1`_ for so called
v1 APIs, or `NFV-SOL 003 v3.3.1`_ for v2 APIs.

Granting Interface Support
==========================

No all the APIs of v1 and v2 have been implemented in Tacker's granting
interface yet.
The purpose of this section is to show the progress of implementation of the
APIs.

* | **Name**: Grants
  | **Description**: Request a grant
  | **Method type**: POST
  | **URL for the resource**: /grant/v1/grants
  | **Request**:

  +--------------+-------------+--------------------------------------------+
  | Data type    | Cardinality | Description                                |
  +==============+=============+============================================+
  | GrantRequest | 1           | Parameters for requesting Grants resource. |
  +--------------+-------------+--------------------------------------------+


  .. list-table::
     :header-rows: 1

     * - Attribute name
       - Data type
       - Cardinality
       - Support in v1 API
       - Support in v2 API
     * - vnfInstanceId
       - Identifier
       - 1
       - Yes
       - Yes
     * - vnfLcmOpOccId
       - Identifier
       - 1
       - Yes
       - Yes
     * - vnfdId
       - Identifier
       - 1
       - Yes
       - Yes
     * - dstVnfdId
       - Identifier
       - 0..1
       - No
       - Yes
     * - flavourId
       - Identifier
       - 0..1
       - Yes
       - Yes
     * - operation
       - GrantedLcmOperationType
       - 1
       - Yes
       - Yes
     * - isAutomaticInvocation
       - Boolean
       - 1
       - Yes
       - Yes
     * - instantiationLevelId
       - Identifier
       - 0..1
       - No
       - Yes
     * - addResources
       - ResourceDefinition
       - 0..N
       - Yes
       - Yes
     * - tempResources
       - ResourceDefinition
       - 0..N
       - No
       - No
     * - removeResources
       - ResourceDefinition
       - 0..N
       - Yes
       - Yes
     * - updateResources
       - ResourceDefinition
       - 0..N
       - No
       - Yes
     * - placementConstraints
       - PlacementConstraint
       - 0..N
       - Yes
       - Yes
     * - vimConstraints
       - VimConstraint
       - 0..N
       - No
       - No
     * - additionalParams
       - KeyValuePairs
       - 0..1
       - No
       - Yes
     * - _links
       - Structure
       - 1
       - Yes
       - Yes
     * - >vnfLcmOpOcc
       - Link
       - 1
       - Yes
       - Yes
     * - >vnfInstance
       - Link
       - 1
       - Yes
       - Yes

  | **Response**:

  .. list-table::
     :widths: 10 10 20 50
     :header-rows: 1

     * - Data type
       - Cardinality
       - Response Codes
       - Description
     * - Grant
       - 1
       - | Success 201
         | Error 400 401 403
       - The grant has been created successfully (synchronous mode).

  .. list-table::
     :header-rows: 1

     * - Attributename
       - Datatype
       - Cardinality
       - Support in v1 API
       - Support in v2 API
     * - id
       - Identifier
       - 1
       - Yes
       - Yes
     * - vnfInstanceId
       - Identifier
       - 1
       - Yes
       - Yes
     * - vnfLcmOpOccId
       - Identifier
       - 1
       - Yes
       - Yes
     * - vimConnections
       - VimConnectionInfo
       - 0..N
       - Yes
       - No
     * - vimConnectionInfo
       - map(VimConnectionInfo)
       - 0..N
       - No
       - Yes
     * - zones
       - ZoneInfo
       - 0..N
       - Yes
       - Yes
     * - zoneGroups
       - ZoneGroupInfo
       - 0..N
       - No
       - No
     * - addResources
       - GrantInfo
       - 0..N
       - Yes
       - Yes
     * - tempResources
       - GrantInfo
       - 0..N
       - No
       - No
     * - removeResources
       - GrantInfo
       - 0..N
       - Yes
       - Yes
     * - updateResources
       - GrantInfo
       - 0..N
       - No
       - Yes
     * - vimAssets
       - Structure
       - 0..1
       - Yes
       - Yes
     * - >computeResourceFlavours
       - VimComputeResourceFlavour
       - 0..N
       - Yes
       - Yes
     * - >softwareImages
       - VimSoftwareImage
       - 0..N
       - Yes
       - Yes
     * - >snapshotResources
       - VimSnapshotResource
       - 0..N
       - No
       - No
     * - extVirtualLinks
       - ExtVirtualLinkData
       - 0..N
       - No
       - Yes
     * - extManagedVirtualLinks
       - ExtManagedVirtualLinkData
       - 0..N
       - No
       - Yes
     * - additionalParams
       - KeyValuePairs
       - 0..1
       - Yes
       - Yes
     * - _links
       - Structure
       - 1
       - Yes
       - Yes
     * - >self
       - Link
       - 1
       - Yes
       - Yes
     * - >vnfLcmOpOcc
       - Link
       - 1
       - Yes
       - Yes
     * - >vnfInstance
       - Link
       - 1
       - Yes
       - Yes

.. _NFV-SOL 003 v2.6.1: https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/003/02.06.01_60/gs_nfv-sol003v020601p.pdf
.. _NFV-SOL 003 v3.3.1: https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/003/03.03.01_60/gs_nfv-sol003v030301p.pdf
