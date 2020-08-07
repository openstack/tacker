.. -*- rst -*-

=====================================================================
Virtualized Network Function Lifecycle Management Interface (VNF LCM)
=====================================================================

This interface manages the VNF lifecycle management operations of VNF instances.

This interface allows the NFVO to invoke VNF lifecycle management operations
of VNF instances towards the VNFM.

Creates a new VNF instance resource
===================================

.. rest_method::  POST /vnflcm/v1/vnf_instances

The POST method creates a new VNF instance resource.

As the result of successfully executing this method, a new Individual VNF
instance resource shall have been created, and the value of the
instantiationState attribute in the representation of that resource shall be
NOT_INSTANTIATED.

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

.. rest_parameters:: parameters_vnflcm.yaml

  - vnfdId: vnf_instance_create_request_vnfd_id
  - vnfInstanceName: vnf_instance_create_request_name
  - vnfInstanceDescription: vnf_instance_create_request_description
  - metadata: vnf_instance_create_request_metadata

Request Example
---------------

.. literalinclude:: samples/vnflcm/create-vnf-instance-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - id: vnf_instance_id_response
  - vnfInstanceName: vnf_instance_name
  - vnfInstanceDescription: vnf_instance_description
  - vnfdId: vnf_instance_vnfd_id
  - vnfProvider: vnf_instance_vnf_provider
  - vnfProductName: vnf_instance_vnf_product_name
  - vnfSoftwareVersion: vnf_instance_vnf_software_version
  - vnfdVersion: vnf_instance_vnfd_version
  - vnfPkgId: vnf_instance_vnf_pkg_id
  - instantiationState: vnf_instance_instantiation_state
  - _links: vnf_instance_links

Response Example
----------------

.. literalinclude:: samples/vnflcm/create-vnf-instance-response.json
   :language: javascript

Instantiate a VNF instance
==========================

.. rest_method::  POST /vnflcm/v1/vnf_instances/{vnfInstanceId}/instantiate

The POST method instantiates a VNF instance.

Once the VNFM has successfully completed the underlying VNF LCM operation
occurrence, it shall set the instantiationState attribute to the value
INSTANTIATED and the vnfState attribute to the value STARTED in the
representation of the Individual VNF instance resource.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 202

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 403
  - 404
  - 409

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - vnfInstanceId: vnf_instance_id
  - flavourId: flavour_id
  - instantiationLevelId: instantiation_level_id
  - extVirtualLinks: ext_virtual_links
  - id: ext_virtual_links_id
  - resourceId: ext_virtual_links_resource_id
  - extCps: ext_cps
  - cpdId: cpd_id
  - cpConfig: cp_config
  - cpInstanceId: cp_instance_id
  - linkPortId: link_port_id
  - cpProtocolData: cp_protocol_data
  - layerProtocol: layer_protocol
  - ipOverEthernet: ip_over_ethernet
  - macAddress: mac_address
  - ipAddresses: ip_addresses
  - type: ip_address_type
  - fixedAddresses: fixed_addresses
  - subnetId: subnet_id
  - extLinkPorts: ext_link_ports
  - id: ext_link_port_id
  - resourceHandle: ext_link_port_resource_handle
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - extManagedVirtualLinks: ext_managed_virtual_links
  - id: ext_managed_virtual_link_data_id
  - vnfVirtualLinkDescId: vnf_virtual_link_desc_id
  - resourceId: ext_managed_virtual_link_data_resource_id
  - vimConnectionInfo: vnf_instance_vim_connection_info
  - id: vim_connection_info_id
  - vimId: vim_connection_info_vim_id
  - vimType: vim_connection_info_vim_type
  - accessInfo: vim_connection_info_access_info
  - additionalParams: vnf_instance_additional_params


Request Example
---------------

.. literalinclude:: samples/vnflcm/instantiate-vnf-instance-request.json
   :language: javascript

Terminate a VNF instance
========================

.. rest_method::  POST /vnflcm/v1/vnf_instances/{vnfInstanceId}/terminate

This task resource represents the "Terminate VNF" operation. The client can
use this resource to terminate a VNF instance.

The POST method terminates a VNF instance.

Once the VNFM has successfully completed the underlying VNF LCM operation
occurrence, it shall set the instantiationState attribute in the
representation of the Individual VNF instance resource to the value
NOT_INSTANTIATED.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 202

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 403
  - 404
  - 409

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - vnfInstanceId: vnf_instance_id
  - terminationType: termination_type
  - gracefulTerminationTimeout: graceful_termination_timeout


Request Example
---------------

.. literalinclude:: samples/vnflcm/terminate-vnf-instance-request.json
   :language: javascript

Heal a VNF instance
========================

.. rest_method::  POST /vnflcm/v1/vnf_instances/{vnfInstanceId}/heal

This task resource represents the "Heal VNF" operation. The client can use
this resource to request healing a VNF instance.

The POST method requests to heal a VNF instance.



Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 202

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 403
  - 404
  - 409

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - vnfInstanceId: vnf_instance_id
  - cause: cause
  - vnfcInstanceId: vnfc_resource_info_ids


Request Example
---------------

.. literalinclude:: samples/vnflcm/heal-vnf-instance-request.json
   :language: javascript

Delete a VNF instance
=====================

.. rest_method::  DELETE /vnflcm/v1/vnf_instances/{vnfInstanceId}

This method deletes an "Individual VNF instance" resource.

As the result of successfully executing this method, the
"Individual VNF instance" resource shall not exist any longer.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 204

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 403
  - 404
  - 409

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - vnfInstanceId: vnf_instance_id

Show VNF Instance
==================

.. rest_method::  GET /vnflcm/v1/vnf_instances/{vnfInstanceId}

Show information of given individual VNF instance.

The GET method retrieves information about a VNF instance by reading
an "Individual VNF instance" resource.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 403

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - vnfInstanceId: vnf_instance_id

Response Parameters
-------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - id: vnf_instance_id
  - vnfInstanceName: vnf_instance_name
  - vnfInstanceDescription: vnf_instance_description
  - vnfdId: vnf_instance_vnfd_id
  - vnfProvider: vnf_instance_vnf_provider
  - vnfProductName: vnf_instance_vnf_product_name
  - vnfSoftwareVersion: vnf_instance_vnf_software_version
  - vnfdVersion: vnf_instance_vnfd_version
  - vnfPkgId: vnf_instance_vnf_pkg_id
  - vimConnectionInfo: vnf_instance_vim_connection_info
  - id: vim_connection_info_id
  - vimId: vim_connection_info_vim_id
  - vimType: vim_connection_info_vim_type
  - interfaceInfo: vim_connection_info_interface_info
  - endpoint: vim_connection_info_interface_info_endpoint
  - accessInfo: vim_connection_info_access_info
  - instantiationState: vnf_instance_instantiation_state
  - instantiatedVnfInfo: instantiated_vnf_info
  - flavourId: flavour_id_response
  - vnfState: vnf_state
  - scaleStatus: scale_status
  - aspectId: scale_status_aspect_id
  - scaleLevel: scale_status_scale_level
  - extCpInfo: ext_cp_info
  - id: ext_cp_info_id
  - cpdId: ext_cp_info_cpd_id
  - cpProtocolInfo: ext_cp_info_cp_protocol_info
  - layerProtocol: layer_protocol_cp_info
  - ipOverEthernet: ip_over_ethernet_cp_info
  - macAddress: mac_address_cp_info
  - ipAddresses: ip_addresses_cp_info
  - type: ip_address_type
  - addresses: fixed_addresses
  - isDynamic: is_dynamic
  - subnetId: subnet_id
  - extLinkPortId: ext_cp_info_ext_link_port_id
  - metadata: ext_cp_info_metadata
  - associatedVnfcCpId: ext_cp_info_associated_vnfc_cp_id
  - extVirtualLinkInfo: ext_virtual_link_info
  - id: ext_virtual_link_info_id
  - resourceHandle: resource_handle
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - extLinkPorts: ext_virtual_link_info_ext_link_ports
  - id: ext_virtual_link_info_ext_link_ports_id
  - resourceHandle: resource_handle
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - cpInstanceId: ext_virtual_link_info_ext_link_ports_cp_instance_id
  - extManagedVirtualLinkInfo: ext_managed_virtual_link_info
  - id: ext_managed_virtual_link_info_id
  - vnfVirtualLinkDescId: ext_managed_virtual_link_info_vnf_virtual_link_desc_id
  - networkResource: ext_managed_virtual_link_info_network_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - vnfLinkPorts: vnf_link_ports
  - id: vnf_link_port_id
  - resourceHandle: vnf_link_port_resource_handle
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - cpInstanceId: vnf_link_port_cp_instance_id
  - vnfcResourceInfo: vnfc_resource_info
  - id: vnfc_resource_info_id
  - vduId: vnfc_resource_info_vdu_id
  - computeResource: vnfc_resource_info_compute_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - storageResourceIds: vnfc_resource_info_storage_resource_ids
  - vnfcCpInfo: vnfc_resource_info_vnfc_cp_info
  - id: vnfc_cp_info_id
  - cpdId: vnfc_cp_info_cpd_id
  - vnfExtCpId: vnfc_cp_info_vnf_ext_cp_id
  - cpProtocolInfo: vnfc_cp_info_cp_protocol_info
  - layerProtocol: layer_protocol_cp_info
  - ipOverEthernet: ip_over_ethernet_cp_info
  - macAddress: mac_address_cp_info
  - ipAddresses: ip_addresses_cp_info
  - type: ip_address_type
  - addresses: fixed_addresses
  - isDynamic: is_dynamic
  - subnetId: subnet_id
  - vnfLinkPortId: vnfc_cp_info_vnf_link_port_id
  - vnfVirtualLinkResourceInfo: vnf_virtual_link_resource_info
  - id: vnf_virtual_link_resource_info_id
  - vnfVirtualLinkDescId: vnf_virtual_link_resource_info_vnf_virtual_link_desc_id
  - networkResource: vnf_virtual_link_resource_info_network_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - vnfLinkPorts: vnf_link_ports
  - id: vnf_link_port_id
  - resourceHandle: vnf_link_port_resource_handle
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - cpInstanceId: vnf_link_port_cp_instance_id
  - virtualStorageResourceInfo: virtual_storage_resource_info
  - id: virtual_storage_resource_info_id
  - virtualStorageDescId: virtual_storage_resource_info_virtual_storage_desc_id
  - storageResource: virtual_storage_resource_info_storage_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - vnfcInfo: vnfc_info
  - id: vnfc_info_id
  - vduId: vnfc_info_vdu_id
  - vnfcState: vnfc_info_vnfc_state
  - _links: vnf_instance_links

Response Example
----------------

.. literalinclude:: samples/vnflcm/show-vnf-instance-response.json
   :language: javascript

List VNF Instance
==================

.. rest_method::  GET /vnflcm/v1/vnf_instances

The GET method queries information about multiple VNF instances.
In Victoria release, added attribute-based filtering expression (for VnfInstance)
that follows clause 5.2 of ETSI GS NFV SOL13.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 403

Response Parameters
-------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - id: vnf_instance_id
  - vnfInstanceName: vnf_instance_name
  - vnfInstanceDescription: vnf_instance_description
  - vnfdId: vnf_instance_vnfd_id
  - vnfProvider: vnf_instance_vnf_provider
  - vnfProductName: vnf_instance_vnf_product_name
  - vnfSoftwareVersion: vnf_instance_vnf_software_version
  - vnfdVersion: vnf_instance_vnfd_version
  - vnfPkgId: vnf_instance_vnf_pkg_id
  - vimConnectionInfo: vnf_instance_vim_connection_info
  - id: vim_connection_info_id
  - vimId: vim_connection_info_vim_id
  - vimType: vim_connection_info_vim_type
  - interfaceInfo: vim_connection_info_interface_info
  - endpoint: vim_connection_info_interface_info_endpoint
  - accessInfo: vim_connection_info_access_info
  - instantiationState: vnf_instance_instantiation_state
  - instantiatedVnfInfo: instantiated_vnf_info
  - flavourId: flavour_id_response
  - vnfState: vnf_state
  - scaleStatus: scale_status
  - aspectId: scale_status_aspect_id
  - scaleLevel: scale_status_scale_level
  - extCpInfo: ext_cp_info
  - id: ext_cp_info_id
  - cpdId: ext_cp_info_cpd_id
  - cpProtocolInfo: ext_cp_info_cp_protocol_info
  - layerProtocol: layer_protocol_cp_info
  - ipOverEthernet: ip_over_ethernet_cp_info
  - macAddress: mac_address_cp_info
  - ipAddresses: ip_addresses_cp_info
  - type: ip_address_type
  - addresses: fixed_addresses
  - isDynamic: is_dynamic
  - subnetId: subnet_id
  - extLinkPortId: ext_cp_info_ext_link_port_id
  - metadata: ext_cp_info_metadata
  - associatedVnfcCpId: ext_cp_info_associated_vnfc_cp_id
  - extVirtualLinkInfo: ext_virtual_link_info
  - id: ext_virtual_link_info_id
  - resourceHandle: resource_handle
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - extLinkPorts: ext_virtual_link_info_ext_link_ports
  - id: ext_virtual_link_info_ext_link_ports_id
  - resourceHandle: resource_handle
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - cpInstanceId: ext_virtual_link_info_ext_link_ports_cp_instance_id
  - extManagedVirtualLinkInfo: ext_managed_virtual_link_info
  - id: ext_managed_virtual_link_info_id
  - vnfVirtualLinkDescId: ext_managed_virtual_link_info_vnf_virtual_link_desc_id
  - networkResource: ext_managed_virtual_link_info_network_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - vnfLinkPorts: vnf_link_ports
  - id: vnf_link_port_id
  - resourceHandle: vnf_link_port_resource_handle
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - cpInstanceId: vnf_link_port_cp_instance_id
  - vnfcResourceInfo: vnfc_resource_info
  - id: vnfc_resource_info_id
  - vduId: vnfc_resource_info_vdu_id
  - computeResource: vnfc_resource_info_compute_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - storageResourceIds: vnfc_resource_info_storage_resource_ids
  - vnfcCpInfo: vnfc_resource_info_vnfc_cp_info
  - id: vnfc_cp_info_id
  - cpdId: vnfc_cp_info_cpd_id
  - vnfExtCpId: vnfc_cp_info_vnf_ext_cp_id
  - cpProtocolInfo: vnfc_cp_info_cp_protocol_info
  - layerProtocol: layer_protocol_cp_info
  - ipOverEthernet: ip_over_ethernet_cp_info
  - macAddress: mac_address_cp_info
  - ipAddresses: ip_addresses_cp_info
  - type: ip_address_type
  - addresses: fixed_addresses
  - isDynamic: is_dynamic
  - subnetId: subnet_id
  - vnfLinkPortId: vnfc_cp_info_vnf_link_port_id
  - vnfVirtualLinkResourceInfo: vnf_virtual_link_resource_info
  - id: vnf_virtual_link_resource_info_id
  - vnfVirtualLinkDescId: vnf_virtual_link_resource_info_vnf_virtual_link_desc_id
  - networkResource: vnf_virtual_link_resource_info_network_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - vnfLinkPorts: vnf_link_ports
  - id: vnf_link_port_id
  - resourceHandle: vnf_link_port_resource_handle
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - cpInstanceId: vnf_link_port_cp_instance_id
  - virtualStorageResourceInfo: virtual_storage_resource_info
  - id: virtual_storage_resource_info_id
  - virtualStorageDescId: virtual_storage_resource_info_virtual_storage_desc_id
  - storageResource: virtual_storage_resource_info_storage_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - vnfcInfo: vnfc_info
  - id: vnfc_info_id
  - vduId: vnfc_info_vdu_id
  - vnfcState: vnfc_info_vnfc_state
  - _links: vnf_instance_links

Response Example
----------------

.. literalinclude:: samples/vnflcm/list-vnf-instance-response.json
   :language: javascript

Create a new subscription
=========================

.. rest_method::  POST /vnflcm/v1/subscriptions

The POST method creates a new subscription.

As the result of successfully executing this method, a new "Individual subscription" resource
shall have been created. This method shall not trigger any notification.

Creation of two "Individual subscription" resources with the same callbackURI and the same filter can result in
performance degradation and will provide duplicates of notifications to the NFVO, and might make sense only in very
rare use cases. Consequently, the VNFM may either allow creating an "Individual subscription" resource if another
Individual subscription resource with the same filter and callbackUri already exists (in which case it shall return the
201 Created response code), or may decide to not create a duplicate "Individual subscription" resource (in which case
it shall return a "303 See Other" response code referencing the existing "Individual subscription" resource with the same
filter and callbackUri).

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 201

.. rest_status_code:: error status.yaml

  - 303
  - 400
  - 401
  - 403

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - filter: filter
  - notificationTypes: filter_notification_types
  - operationTypes: filter_operation_types
  - callbackUri : callback_uri
  - authentication: authentication
  - authType: authentication_auth_type
  - paramsBasic: authentication_params_basic
  - userName: authentication_params_basic_user_name
  - password: authentication_params_basic_password
  - paramsOauth2ClientCredentials: authentication_params_oauth2_client_credentials
  - clientId: authentication_params_oauth2_client_credentials_client_id
  - clientPassword: authentication_params_oauth2_client_credentials_client_password
  - tokenEndpoint: authentication_params_oauth2_client_credentials_token_endpoint

Request Example
---------------

.. literalinclude:: samples/vnflcm/create-subscription-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - id: subscription_id_response
  - filter: filter
  - notificationTypes: filter_notification_types
  - operationTypes: filter_operation_types
  - callbackUri: callback_uri
  - _links: vnf_instance_links

Response Example
----------------

.. literalinclude:: samples/vnflcm/create-subscription-response.json
   :language: javascript

Delete a subscription
=========================

.. rest_method::  DELETE /vnflcm/v1/subscriptions/{subscriptionId}

The DELETE method terminates an individual subscription.

As the result of successfully executing this method, the "Individual subscription" resource shall not exist any longer.
This means that no notifications for that subscription shall be sent to the formerly-subscribed API consumer.

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

.. rest_parameters:: parameters_vnflcm.yaml

  - subscriptionId: subscription_id

Show subscription
=================

.. rest_method::  GET /vnflcm/v1/subscriptions/{subscriptionId}

The GET method retrieves information about a subscription by reading an "Individual subscription" resource.

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

.. rest_parameters:: parameters_vnflcm.yaml

  - subscriptionId: subscription_id

Response Parameters
-------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - id: subscription_id_response
  - filter: filter
  - notificationTypes: filter_notification_types
  - operationTypes: filter_operation_types
  - callbackUri: callback_uri
  - _links: vnf_instance_links

Response Example
----------------

.. literalinclude:: samples/vnflcm/show-subscription-response.json
   :language: javascript

List subscription
=================

.. rest_method::  GET /vnflcm/v1/subscriptions

The GET method queries the list of active subscriptions of the functional block that invokes the method.
It can be used e.g. for resynchronization after error situations.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 403

Response Parameters
-------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - id: subscription_id_response
  - filter: filter
  - notificationTypes: filter_notification_types
  - operationTypes: filter_operation_types
  - callbackUri: callback_uri
  - _links: vnf_instance_links

Response Example
----------------

.. literalinclude:: samples/vnflcm/list-subscription-response.json
   :language: javascript
