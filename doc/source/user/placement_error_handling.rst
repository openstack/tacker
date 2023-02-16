============================
VDU Placement error-handling
============================

This document describes how to error-handling VDU placement errors
due to insufficient availability zone's resources.

VDU Placement error due to insufficient resources
-------------------------------------------------

The placement constraints are defined in `ETSI NFV-SOL 003 v3.3.1`_ and
that VNFM sends to NFVO in order to the resource placement decision.
In VNF Lifecycle Management (LCM), there are some error cases that VDUs
are not deployed due to insufficient availability zone's resources.

When stack create/update fails, it can be detected from `Show stack
details`_ of Heat-API response whether the failure is due to
insufficient resources.
The error message that indicates insufficient resources is extracted
from the parameter "stack_status_reason" in the response.

.. note::
  In the case of insufficient resources, the error occurs after stack
  create/update returns an acceptance response, so the "Show stack
  details" response can be used to detect the cause.

The following are examples of an error message stored in
"stack_status_reason" when resources are insufficient.

+ ex1) Set the flavor defined in "OS::Nova::Server" to a large value
  that cannot be deployed (not enough storage/not enough vcpu/not enough
  memory).

  + Resource CREATE failed: ResourceInError: resources.<VDU-name>: Went
    to status ERROR due to “Message: No valid host was found. , Code:
    500”

+ ex2) Specifies an extra-spec that cannot be assigned for the flavor
  defined in "OS::Nova::Server."

  + Resource CREATE failed: ResourceInError: resources.<VDU-name>: Went
    to status ERROR due to “Message: Exceeded maximum number of retries.
    Exhausted all hosts available for retrying build failures for
    instance <server-UUID>., Code: 500”

Availability zone reselection
-----------------------------

If VDU placement errors due to insufficient availability zone's
resources occur, availability zone reselection is possible as
error-handling.

The VNF LCM v2 API (instantiate/heal/scale for VNF) process can change
the availability zone to be used from the one notified by the NFVO if
necessary.
If the availability zone notified by the NFVO has insufficient
resources, the VNF is re-created/updated in a different availability
zone.
The availability zone is reselected and the VNF is re-created/updated
until there are no more candidates.

Settings
~~~~~~~~

The settings for performing availability zone reselection are following.

+ Using StandardUserData as the UserData class

+ Set `placement_fallback_best_effort = True` in the ``tacker.conf`` file

.. note::
  Maximum number of retries for reselection of availability zone is
  unlimited by default.
  If the retry limit needs to be set, set the limit number to
  `placement_az_select_retry` in ``tacker.conf``.
  (Default value ``0`` means unlimited number of retries.)

.. note::
  Regular expression for detecting insufficient resource error is
  following by default.

  ``Resource CREATE failed: ResourceInError: resources\.(.*)\.(.*): (.*)
  | Resource UPDATE failed: resources\.(.*): Resource CREATE failed:
  ResourceInError: resources\.(.*): (.*)``

  If the detection condition for insufficient resource error needs to be
  changed, set regular expression to `placement_az_resource_error` in
  ``tacker.conf``.

  It is out of community support if you change `placement_az_resource_error`
  from the default, so please do it at your own risk.

Policy
~~~~~~
Availability zones in error are excluded from the reselection
candidates, and are reselected preferentially from unselected
availability zones.

.. note::
  Affinity/Anti-Affinity of PlacementConstraint and resource states of
  availability zones are not considered during reselection.

The availability zone in error can be identified in the following way.

1. Call Heat-API "Show stack details" after an error occurs in "stack
   create/update"
2. Identify the VDU where the error occurred due to insufficient resource
   by the stack_status_reason in the response of 1.
3. Identify the availability zone by the VDU identified in 2.

.. note::
  Insufficient resources in availability zones that once failed during
  reselection attempts may be resolved, but the availability zones will
  not be reselected.
  In Scale/Heal operations, VDUs that have already been deployed will
  not be re-created.

Availability zone reselection for each VNF LCM v2 API
(instantiate/heal/scale for VNF) is as follows.

Precondition: availability zones AZ-1/AZ-2/AZ-3/AZ-4/AZ-5 exist and VNFs
VDU1-0/VDU1-1/VDU2-0/VDU2-1 are deployed

.. note::
  VNFs in VDU1 are in the same availability zone (Affinity), and VNFs in
  VDU2 and VDU1/VDU2 are in different availability zones (Anti-Affinity).

+ Instantiate

  + Before reselection, the following attempts to deploy failed (AZ-1
    and AZ-2 have insufficient resource)

    + VDU1-0: AZ-1
    + VDU1-1: AZ-1
    + VDU2-0: AZ-2
    + VDU2-1: AZ-3

  + VDU1-0/1: Reselect the following (except AZ-1/AZ-2/AZ-3, select AZ-4
    or AZ-5)

    + VDU1-0: AZ-4
    + VDU1-1: AZ-4
    + VDU2-0: AZ-2
    + VDU2-1: AZ-3

  + VDU2-0: Reselect the following (except AZ-2/AZ-3/AZ-4, select AZ-1 or
    AZ-5)

    + VDU1-0: AZ-4
    + VDU1-1: AZ-4
    + VDU2-0: AZ-5
    + VDU2-1: AZ-3

    .. note::
      The above is an example, and the reselection target is randomly
      selected from unselected availability zones.

+ Heal (VDU1-1/VDU2-0)

  + Before reselection, the following attempts to deploy failed (AZ-1
    and AZ-2 have insufficient resource)

    + VDU1-0: AZ-1
    + VDU1-1: AZ-1
    + VDU2-0: AZ-2
    + VDU2-1: AZ-3

  + VDU1-1: Reselect the following (except AZ-1/AZ-2/AZ-3, select AZ-4
    or AZ-5)

    + VDU1-0: AZ-1
    + VDU1-1: AZ-4
    + VDU2-0: AZ-2
    + VDU2-1: AZ-3

    .. note::
      Only Heal target VNFs are targeted for availability zone
      reselection.
      Therefore, Affinity may not be satisfied due to the operation of
      reselection.

  + VDU2-0: Reselect the following (except AZ-1/AZ-2/AZ-3/AZ-4, select
    AZ-5)

    + VDU1-0: AZ-1
    + VDU1-1: AZ-4
    + VDU2-0: AZ-5
    + VDU2-1: AZ-3

+ Scale out (add VDU1-2/VDU1-3)

  + Before reselection, VDU1-3 deploy failed (AZ-1 has insufficient
    resource)

    + VDU1-0: AZ-1
    + VDU1-1: AZ-1
    + VDU1-2: AZ-1
    + VDU1-3: AZ-1
    + VDU2-0: AZ-2
    + VDU2-1: AZ-3

  + VDU1-2/3: Reselect the following (except AZ-1/AZ-2/AZ-3, select AZ-4
    or AZ-5)

    + VDU1-0: AZ-1
    + VDU1-1: AZ-1
    + VDU1-2: AZ-4
    + VDU1-3: AZ-4
    + VDU2-0: AZ-2
    + VDU2-1: AZ-3

    .. note::
      In the case of Affinity, even if VDU1-2 has been successfully
      deployed, both VDU1-2/VDU1-3 availability zones will be reselected.
      Existing VDU1-0/VDU1-1 will not be reselected, so all VDUs may not
      be in the same availability zone even in Affinity case.

+ Scale out (add VDU2-2/VDU2-3)

  + Before reselection, VDU2-3 deploy failed (AZ-5 has insufficient
    resource)

    + VDU1-0: AZ-1
    + VDU1-1: AZ-1
    + VDU2-0: AZ-2
    + VDU2-1: AZ-3
    + VDU2-2: AZ-4
    + VDU2-3: AZ-5

  + VDU2-3: Reselect the following (except AZ-5, select AZ-1 or AZ-2 or
    AZ-3 or AZ-4)

    + VDU1-0: AZ-1
    + VDU1-1: AZ-1
    + VDU2-0: AZ-2
    + VDU2-1: AZ-3
    + VDU2-2: AZ-4
    + VDU2-3: AZ-1

    .. note::
      If there are no unselected availability zones left, randomly select
      a reselection target from the selected availability zones.
      In this case, Anti-Affinity cannot be satisfied.

.. _ETSI NFV-SOL 003 v3.3.1: https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/003/03.03.01_60/gs_nfv-sol003v030301p.pdf

.. _Show stack details: https://docs.openstack.org/api-ref/orchestration/v1/index.html?expanded=show-stack-details-detail#show-stack-details
