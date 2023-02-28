.. -*- rst -*-

================================================================
Virtualized Network Function Fault Management Interface (VNF FM)
================================================================

This interface manages the VNF fault management operations of VNF instances.

This interface allows the NFVO to invoke VNF fault management operations of
VNF instances towards the VNFM. The detail of this interface is described in
SOL002 v3.3.1 clause 7. The parameters of some specific standards need
reference SOL013 v3.4.1 clause 5.

Get all alarms (v1)
===================

.. rest_method::  GET /vnffm/v1/alarms

The GET method gets all alarms, Allow users to filter out alarms based on query
parameter in the request.

If the API consumer intends to query all alarms, it sends a GET request to the
"Alarms" resource. The VNFM returns a "200 OK" response to the API consumer, and
includes zero or more data structures of type "Alarm" in the payload body.

An attribute selector allows the API consumer to choose which attributes it
wants to be contained in the response. *all_fields*, *fields*, *exclude_fields*
and *exclude_default* can be set as query parameters.

Attribute-based filtering expression. The following attribute names shall be
supported by the Tacker in the attribute-based filtering expression: id,
managedObjectId, rootCauseFaultyResource/faultyResourceType, eventType,
perceivedSeverity, probableCause.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 406

Response Parameters
-------------------

.. rest_parameters:: parameters_vnffm.yaml

  - id: alarm_id
  - managedObjectId: managed_object_id
  - vnfcInstanceIds: vnfc_instance_ids
  - rootCauseFaultyResource: faulty_resource_info
  - faultyResource: faulty_resource
  - vimConnectionId: faulty_resource_vim_connection_id
  - resourceProviderId: faulty_resource_provider_id
  - resourceId: faulty_resource_id
  - vimLevelResourceType: faulty_resource_vim_level_resource_type
  - faultyResourceType: faulty_resource_type
  - alarmRaisedTime: alarm_raised_time
  - alarmChangedTime: alarm_changed_time
  - alarmClearedTime: alarm_cleared_time
  - alarmAcknowledgedTime: alarm_acknowledged_time
  - ackState: ack_state
  - perceivedSeverity: perceived_severity
  - eventTime: event_time
  - eventType: event_type
  - faultType: fault_type
  - probableCause: probable_cause
  - isRootCause: is_root_cause
  - correlatedAlarmIds: correlated_alarm_ids
  - faultDetails: fault_details
  - _links: alarm_links
  - self: alarm_self
  - objectInstance: object_instance

Response Example
----------------

.. literalinclude:: samples/vnffm/list-vnffm-alarm-response.json
   :language: javascript

Get the individual alarm (v1)
=============================

.. rest_method::  GET /vnffm/v1/alarms/{alarmId}

The GET method gets the alarm specified in the Tacker.

If the API consumer intends to read a particular alarm, it sends a GET request
to the "Individual alarm" resource, addressed by the appropriate alarm
identifier in its resource URI.
The VNFM returns a "200 OK" response to the API consumer,
and includes the data structure of type "Alarm" in the payload body.
In case of failure, appropriate error
information is provided in the response.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404
  - 406

Request Parameters
------------------

.. rest_parameters:: parameters_vnffm.yaml

  - alarmId: alarm_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters_vnffm.yaml

  - id: alarm_id
  - managedObjectId: managed_object_id
  - vnfcInstanceIds: vnfc_instance_ids
  - rootCauseFaultyResource: faulty_resource_info
  - faultyResource: faulty_resource
  - vimConnectionId: faulty_resource_vim_connection_id
  - resourceProviderId: faulty_resource_provider_id
  - resourceId: faulty_resource_id
  - vimLevelResourceType: faulty_resource_vim_level_resource_type
  - faultyResourceType: faulty_resource_type
  - alarmRaisedTime: alarm_raised_time
  - alarmChangedTime: alarm_changed_time
  - alarmClearedTime: alarm_cleared_time
  - alarmAcknowledgedTime: alarm_acknowledged_time
  - ackState: ack_state
  - perceivedSeverity: perceived_severity
  - eventTime: event_time
  - eventType: event_type
  - faultType: fault_type
  - probableCause: probable_cause
  - isRootCause: is_root_cause
  - correlatedAlarmIds: correlated_alarm_ids
  - faultDetails: fault_details
  - _links: alarm_links
  - self: alarm_self
  - objectInstance: object_instance


Response Example
----------------

.. literalinclude:: samples/vnffm/show-vnffm-alarm-response.json
   :language: javascript

Modify the confirmation status (v1)
===================================

.. rest_method::  PATCH /vnffm/v1/alarms/{alarmId}

The PATCH method modifies the confirmation status of the alarm specified in the
Tacker.

The API consumer sends a PATCH request to the individual alarm. The VNFM
returns a "200 OK" response to the API consumer, and includes a data structure
of type "AlarmModifications" in the payload body. In case of failure,
appropriate error information is provided in the response.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404
  - 406
  - 409

Request Parameters
------------------

.. rest_parameters:: parameters_vnffm.yaml

  - alarmId: alarm_id_path
  - ackState: ack_state

Request Example
---------------

.. literalinclude:: samples/vnffm/modify-vnffm-alarm-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters_vnffm.yaml

  - ackState: ack_state

Response Example
----------------

.. literalinclude:: samples/vnffm/modify-vnffm-alarm-response.json
   :language: javascript

Create a subscription (v1)
==========================

.. rest_method::  POST /vnffm/v1/subscriptions

The POST method creates a new VNF FM-Subscription.

As the result of successfully executing this method, a new VNF FM-Subscription
shall have been created, and return detailed FM subscription data. In case of
failure, including an invalid notification endpoint, appropriate error
information is provided in the response.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 201

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 406
  - 422

Request Parameters
------------------

.. rest_parameters:: parameters_vnffm.yaml

  - filter: fm_notification_filter
  - vnfInstanceSubscriptionFilter: filter_subscription_filter
  - vnfdIds: subscription_filter_vnfd_ids
  - vnfProductsFromProviders: subscription_filter_vnf_products_from_providers
  - vnfProvider: vnf_products_from_providers_vnf_provider
  - vnfProducts: vnf_products_from_providers_vnf_products
  - vnfProductName: products_vnf_product_name
  - versions: products_versions
  - vnfSoftwareVersion: versions_vnf_software_version
  - vnfdVersions: versions_vnfd_versions
  - vnfInstanceIds: subscription_filter_vnf_instance_ids
  - vnfInstanceNames: subscription_filter_vnf_instance_names
  - notificationTypes: filter_notification_types
  - faultyResourceTypes: filter_faulty_resource_types
  - perceivedSeverities: filter_perceived_severities
  - eventTypes: filter_event_types
  - probableCauses: filter_probable_causes
  - callbackUri: callback_uri
  - authentication: authentication

Request Example
---------------

.. literalinclude:: samples/vnffm/create-vnffm-subscription-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters_vnffm.yaml

  - id: subscription_id
  - filter: fm_notification_filter
  - vnfInstanceSubscriptionFilter: filter_subscription_filter
  - vnfdIds: subscription_filter_vnfd_ids
  - vnfProductsFromProviders: subscription_filter_vnf_products_from_providers
  - vnfProvider: vnf_products_from_providers_vnf_provider
  - vnfProducts: vnf_products_from_providers_vnf_products
  - vnfProductName: products_vnf_product_name
  - versions: products_versions
  - vnfSoftwareVersion: versions_vnf_software_version
  - vnfdVersions: versions_vnfd_versions
  - vnfInstanceIds: subscription_filter_vnf_instance_ids
  - vnfInstanceNames: subscription_filter_vnf_instance_names
  - notificationTypes: filter_notification_types
  - faultyResourceTypes: filter_faulty_resource_types
  - perceivedSeverities: filter_perceived_severities
  - eventTypes: filter_event_types
  - probableCauses: filter_probable_causes
  - callbackUri: callback_uri
  - _links: subscription_links
  - self: subscription_self

Response Example
----------------

.. literalinclude:: samples/vnffm/create-vnffm-subscription-response.json
   :language: javascript

Get all subscriptions (v1)
==========================

.. rest_method::  GET  /vnffm/v1/subscriptions

The GET method allows users to filter out subscriptions based on query parameter
in the request.

If desired, e.g. to recover from an error situation, the API consumer can query
information about its subscriptions by sending a GET request to the
"Subscriptions" resource. In that case, the VNFM returns a "200 OK" response
that contains the list of representations of all existing subscriptions that
were created by the API consumer, and includes zero or more data structures
of type "FmSubscription" in the payload body.

An attribute selector allows the API consumer to choose which attributes it
wants to be contained in the response. *all_fields*, *fields*, *exclude_fields*
and *exclude_default* can be set as query parameters.

Attribute-based filtering expression. The following attribute names shall be
supported by the Tacker in the attribute-based filtering expression. All
attribute names that appear in the FmSubscription and in data types referenced
from it shall be supported by the VNFM in the filter expression. For example,
below URI query parameter will match alarms with perceivedSeverity=WARNING

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404
  - 406

Response Parameters
-------------------

.. rest_parameters:: parameters_vnffm.yaml

  - id: subscription_id
  - filter: fm_notification_filter
  - vnfInstanceSubscriptionFilter: filter_subscription_filter
  - vnfdIds: subscription_filter_vnfd_ids
  - vnfProductsFromProviders: subscription_filter_vnf_products_from_providers
  - vnfProvider: vnf_products_from_providers_vnf_provider
  - vnfProducts: vnf_products_from_providers_vnf_products
  - vnfProductName: products_vnf_product_name
  - versions: products_versions
  - vnfSoftwareVersion: versions_vnf_software_version
  - vnfdVersions: versions_vnfd_versions
  - vnfInstanceIds: subscription_filter_vnf_instance_ids
  - vnfInstanceNames: subscription_filter_vnf_instance_names
  - notificationTypes: filter_notification_types
  - faultyResourceTypes: filter_faulty_resource_types
  - perceivedSeverities: filter_perceived_severities
  - eventTypes: filter_event_types
  - probableCauses: filter_probable_causes
  - callbackUri: callback_uri
  - _links: subscription_links
  - self: subscription_self

Response Example
----------------

.. literalinclude:: samples/vnffm/list-vnffm-subscription-response.json
   :language: javascript

Get a subscription (v1)
=======================

.. rest_method::  GET /vnffm/v1/subscriptions/{subscriptionId}

The GET method gets the subscription in the Tacker.

If desired, e.g. to recover from an error situation, the API consumer can read
information about a particular subscription by sending a GET request to the
resource representing that individual subscription. In that case, the VNFM
returns a "200 OK" response that contains a representation of that individual
subscription.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404
  - 406

Request Parameters
------------------

.. rest_parameters:: parameters_vnffm.yaml

  - subscriptionId: subscription_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters_vnffm.yaml

  - id: subscription_id
  - filter: fm_notification_filter
  - vnfInstanceSubscriptionFilter: filter_subscription_filter
  - vnfdIds: subscription_filter_vnfd_ids
  - vnfProductsFromProviders: subscription_filter_vnf_products_from_providers
  - vnfProvider: vnf_products_from_providers_vnf_provider
  - vnfProducts: vnf_products_from_providers_vnf_products
  - vnfProductName: products_vnf_product_name
  - versions: products_versions
  - vnfSoftwareVersion: versions_vnf_software_version
  - vnfdVersions: versions_vnfd_versions
  - vnfInstanceIds: subscription_filter_vnf_instance_ids
  - vnfInstanceNames: subscription_filter_vnf_instance_names
  - notificationTypes: filter_notification_types
  - faultyResourceTypes: filter_faulty_resource_types
  - perceivedSeverities: filter_perceived_severities
  - eventTypes: filter_event_types
  - probableCauses: filter_probable_causes
  - callbackUri: callback_uri
  - _links: subscription_links
  - self: subscription_self

Request Example
---------------

.. literalinclude:: samples/vnffm/show-vnffm-subscription-response.json
   :language: javascript

Delete a subscription (v1)
==========================

.. rest_method::  DELETE /vnffm/v1/subscriptions/{subscriptionId}

The DELETE method deletes the subscription in the Tacker

When the API consumer does not need the subscription anymore, it terminates the
subscription by sending a DELETE request to the resource that represents the
individual subscription. The VNFM acknowledges the successful termination of
the subscription by returning a "204 No Content" response.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 204

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404
  - 406
  - 409

Request Parameters
------------------

.. rest_parameters:: parameters_vnffm.yaml

  - subscriptionId: subscription_id_path
