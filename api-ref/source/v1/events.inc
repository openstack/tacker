.. -*- rst -*-

==========
Events
==========

Lists and shows captured events.

Tacker currently supports events for following resource types:

- VNFD
- VNF
- VIM

List events
===========

.. rest_method::  GET /v1.0/events

Lists events of resources.

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

  - events: events
  - resource_id: event_resource_id
  - timestamp: event_timestamp
  - event_details: event_details
  - resource_state: event_resource_state
  - id: event_id
  - resource_type: event_resource_type

Response Example
----------------

.. literalinclude:: samples/events/events-list-response.json
   :language: javascript


Show event
==========

.. rest_method::  GET /v1.0/events/{event_id}

Shows information of a given event.

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

  - event_id: event_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - event: event
  - resource_id: event_resource_id
  - timestamp: event_timestamp
  - event_details: event_details
  - resource_state: event_resource_state
  - id: event_id
  - resource_type: event_resource_type

Response Example
----------------

.. literalinclude:: samples/events/events-show-response.json
   :language: javascript
