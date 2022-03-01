.. -*- rst -*-

=====================================================================
Virtualized Network Function Lifecycle Management Interface (VNF LCM)
=====================================================================

This interface manages the VNF lifecycle management operations of VNF instances.

This interface allows the NFVO to invoke VNF lifecycle management operations
of VNF instances towards the VNFM.

Create a new VNF instance resource (v2)
=======================================

.. rest_method::  POST /vnflcm/v2/vnf_instances

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
  - 406
  - 422

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
  - vnfConfigurableProperties: vnf_instance_vnf_configurable_properties
  - instantiationState: vnf_instance_instantiation_state
  - metadata: vnf_instance_metadata
  - extensions: vnf_instance_extensions
  - _links: vnf_instance_links

Response Example
----------------

.. literalinclude:: samples/vnflcm/create-vnf-instance-response.json
   :language: javascript

Instantiate a VNF instance (v2)
===============================

.. rest_method::  POST /vnflcm/v2/vnf_instances/{vnfInstanceId}/instantiate

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
  - 404
  - 406
  - 409

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - vnfInstanceId: vnf_instance_id
  - flavourId: flavour_id
  - instantiationLevelId: instantiation_level_id
  - extVirtualLinks: ext_virtual_links
  - id: ext_virtual_links_id
  - vimConnectionId: vim_connection_id
  - resourceProviderId: resource_provider_id
  - resourceId: ext_virtual_links_resource_id
  - extCps: ext_cps
  - cpdId: cpd_id
  - cpConfig: cp_config
  - parentCpConfigId: parent_cp_config_id
  - linkPortId: link_port_id
  - cpProtocolData: cp_protocol_data
  - layerProtocol: layer_protocol
  - ipOverEthernet: ip_over_ethernet
  - macAddress: mac_address
  - segmentationId: segmentation_id
  - ipAddresses: ip_addresses
  - type: ip_address_type
  - fixedAddresses: fixed_addresses
  - numDynamicAddresses: num_dynamic_addresses
  - addressRange: address_range
  - minAddress: min_address
  - maxAddress: max_address
  - subnetId: subnet_id
  - extLinkPorts: ext_link_ports
  - id: ext_link_port_id
  - resourceHandle: ext_link_port_resource_handle
  - vimConnectionId: vim_connection_id
  - resourceProviderId: resource_provider_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - extManagedVirtualLinks: ext_managed_virtual_links
  - id: ext_managed_virtual_link_data_id
  - vnfVirtualLinkDescId: vnf_virtual_link_desc_id
  - vimConnectionId: vim_connection_id
  - resourceProviderId: resource_provider_id
  - resourceId: ext_managed_virtual_link_data_resource_id
  - vnfLinkPort: ext_managed_virtual_link_data_vnf_link_port
  - vnfLinkPortId: vnf_link_port_id
  - resourceHandle: vnf_link_port_resource_handle
  - vimConnectionId: vim_connection_id
  - resourceProviderId: resource_provider_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - extManagedMultisiteVirtualLinkId: ext_managed_multisite_virtual_link_id
  - vimConnectionInfo: vnf_instance_vim_connection_info
  - vimId: vim_connection_info_vim_id
  - vimType: vim_connection_info_vim_type
  - interfaceInfo: vim_connection_info_interface_info
  - accessInfo: vim_connection_info_access_info
  - extra: vim_connection_info_extra
  - localizationLanguage: localization_language
  - additionalParams: vnf_instance_additional_params
  - extensions: vnf_instance_extensions
  - vnfConfigurableProperties: vnf_instance_vnf_configurable_properties


Request Example
---------------

.. literalinclude:: samples/vnflcm/instantiate-vnf-instance-request.json
   :language: javascript

Terminate a VNF instance (v2)
=============================

.. rest_method::  POST /vnflcm/v2/vnf_instances/{vnfInstanceId}/terminate

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
  - 404
  - 406
  - 409

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - vnfInstanceId: vnf_instance_id
  - terminationType: termination_type
  - gracefulTerminationTimeout: graceful_termination_timeout
  - additionalParams: vnf_instance_terminate_request_additional_params


Request Example
---------------

.. literalinclude:: samples/vnflcm/terminate-vnf-instance-request.json
   :language: javascript

Heal a VNF instance (v2)
========================

.. rest_method::  POST /vnflcm/v2/vnf_instances/{vnfInstanceId}/heal

This task resource represents the "Heal VNF" operation. The client can use
this resource to request healing a VNF instance.

The POST method heals a VNF instance.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 202

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404
  - 406
  - 409
  - 422

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - vnfInstanceId: vnf_instance_id
  - cause: cause
  - additionalParams: heal_additional_params
  - all: all
  - vnfcInstanceId: vnfc_resource_info_ids

Request Example
---------------

.. literalinclude:: samples/vnflcm/heal-vnf-instance-request.json
   :language: javascript

Delete a VNF instance (v2)
==========================

.. rest_method::  DELETE /vnflcm/v2/vnf_instances/{vnfInstanceId}

This method deletes an "Individual VNF instance" resource.

As the result of successfully executing this method, the
"Individual VNF instance" resource shall not exist any longer.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 204

.. rest_status_code:: error status.yaml

  - 401
  - 404
  - 406
  - 409

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - vnfInstanceId: vnf_instance_id

Show VNF instance (v2)
======================

.. rest_method::  GET /vnflcm/v2/vnf_instances/{vnfInstanceId}

Show information of given individual VNF instance.

The GET method retrieves information about a VNF instance by reading
an "Individual VNF instance" resource.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 401
  - 404
  - 406

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
  - vnfConfigurableProperties: vnf_instance_vnf_configurable_properties
  - vimConnectionInfo: vnf_instance_vim_connection_info
  - vimId: vim_connection_info_vim_id
  - vimType: vim_connection_info_vim_type
  - interfaceInfo: vim_connection_info_interface_info
  - accessInfo: vim_connection_info_access_info
  - instantiationState: vnf_instance_instantiation_state
  - instantiatedVnfInfo: instantiated_vnf_info
  - flavourId: flavour_id_response
  - vnfState: vnf_state
  - extCpInfo: ext_cp_info
  - id: ext_cp_info_id
  - cpdId: ext_cp_info_cpd_id
  - cpConfigId: ext_cp_info_cp_config_id
  - cpProtocolInfo: ext_cp_info_cp_protocol_info
  - layerProtocol: layer_protocol_cp_info
  - ipOverEthernet: ip_over_ethernet_cp_info
  - ipAddresses: ip_addresses_cp_info
  - type: ip_address_type
  - addresses: fixed_addresses
  - subnetId: subnet_id
  - extLinkPortId: ext_cp_info_ext_link_port_id
  - associatedVnfcCpId: ext_cp_info_associated_vnfc_cp_id
  - extVirtualLinkInfo: ext_virtual_link_info
  - id: ext_virtual_link_info_id
  - resourceHandle: resource_handle
  - resourceId: resource_handle_resource_id
  - extLinkPorts: ext_virtual_link_info_ext_link_ports
  - id: ext_virtual_link_info_ext_link_ports_id
  - resourceHandle: resource_handle
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - cpInstanceId: ext_virtual_link_info_ext_link_ports_cp_instance_id
  - currentVnfExtCpData: current_vnf_ext_cp_data
  - cpdId: cpd_id
  - cpConfig: cp_config
  - cpProtocolData: cp_protocol_data
  - layerProtocol: layer_protocol
  - ipOverEthernet: ip_over_ethernet
  - ipAddresses: ip_addresses
  - type: ip_address_type
  - numDynamicAddresses: num_dynamic_addresses
  - extManagedVirtualLinkInfo: ext_managed_virtual_link_info
  - id: ext_managed_virtual_link_info_id
  - vnfVirtualLinkDescId: ext_managed_virtual_link_info_vnf_virtual_link_desc_id
  - networkResource: ext_managed_virtual_link_info_network_resource
  - resourceId: resource_handle_resource_id
  - vnfLinkPorts: vnf_link_ports
  - id: vnf_link_port_id
  - resourceHandle: vnf_link_port_resource_handle
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - cpInstanceId: vnf_link_port_cp_instance_id
  - cpInstanceType: vnf_link_port_cp_instance_type
  - vnfcResourceInfo: vnfc_resource_info
  - id: vnfc_resource_info_id
  - vduId: vnfc_resource_info_vdu_id
  - computeResource: vnfc_resource_info_compute_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - vnfcCpInfo: vnfc_resource_info_vnfc_cp_info
  - id: vnfc_cp_info_id
  - cpdId: vnfc_cp_info_cpd_id
  - vnfExtCpId: vnfc_cp_info_vnf_ext_cp_id
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
  - cpInstanceType: vnf_link_port_cp_instance_type
  - virtualStorageResourceInfo: virtual_storage_resource_info
  - id: virtual_storage_resource_info_id
  - virtualStorageDescId: virtual_storage_resource_info_virtual_storage_desc_id
  - storageResource: virtual_storage_resource_info_storage_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - metadata: vnf_instance_metadata
  - vnfcInfo: vnfc_info
  - id: vnfc_info_id
  - vduId: vnfc_info_vdu_id
  - vnfcResourceInfoId: vnfc_resource_info_id
  - vnfcState: vnfc_info_vnfc_state
  - _links: vnf_instance_links

Response Example
----------------

.. literalinclude:: samples/vnflcm/show-vnf-instance-response.json
   :language: javascript

List VNF instance (v2)
======================

.. rest_method::  GET /vnflcm/v2/vnf_instances

The GET method queries information about multiple VNF instances.
It supports attribute-based filtering and
attribute selectors defined in ETSI NFV SOL013 v3.4.1.
The detail of attribute-based filtering is described in
SOL013 v3.4.1 clause 5.2.

An attribute selector allows the API consumer to choose
which attributes it wants to be contained in the response.
*all_fields*, *fields*, *exclude_fields* and *exclude_default*
can be set as query parameters.

The following attributes shall be excluded
from the VnfInstance structure in the
response body if this parameter is provided,
or none of the parameters "all_fields",
"fields", "exclude_fields", "exclude_default" are provided:
- vnfConfigurableProperties
- vimConnectionInfo
- instantiatedVnfInfo
- metadata
- extensionsby default

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

.. rest_parameters:: parameters_vnflcm.yaml

  - id: vnf_instance_id
  - vnfInstanceName: vnf_instance_name
  - vnfInstanceDescription: vnf_instance_description
  - vnfdId: vnf_instance_vnfd_id
  - vnfProvider: vnf_instance_vnf_provider
  - vnfProductName: vnf_instance_vnf_product_name
  - vnfSoftwareVersion: vnf_instance_vnf_software_version
  - vnfdVersion: vnf_instance_vnfd_version
  - vnfConfigurableProperties: vnf_instance_vnf_configurable_properties
  - vimConnectionInfo: vnf_instance_vim_connection_info
  - vimId: vim_connection_info_vim_id
  - vimType: vim_connection_info_vim_type
  - interfaceInfo: vim_connection_info_interface_info
  - accessInfo: vim_connection_info_access_info
  - instantiationState: vnf_instance_instantiation_state
  - instantiatedVnfInfo: instantiated_vnf_info
  - flavourId: flavour_id_response
  - vnfState: vnf_state
  - extCpInfo: ext_cp_info
  - id: ext_cp_info_id
  - cpdId: ext_cp_info_cpd_id
  - cpConfigId: ext_cp_info_cp_config_id
  - cpProtocolInfo: ext_cp_info_cp_protocol_info
  - layerProtocol: layer_protocol_cp_info
  - ipOverEthernet: ip_over_ethernet_cp_info
  - ipAddresses: ip_addresses_cp_info
  - type: ip_address_type
  - addresses: fixed_addresses
  - subnetId: subnet_id
  - extLinkPortId: ext_cp_info_ext_link_port_id
  - associatedVnfcCpId: ext_cp_info_associated_vnfc_cp_id
  - extVirtualLinkInfo: ext_virtual_link_info
  - id: ext_virtual_link_info_id
  - resourceHandle: resource_handle
  - resourceId: resource_handle_resource_id
  - extLinkPorts: ext_virtual_link_info_ext_link_ports
  - id: ext_virtual_link_info_ext_link_ports_id
  - resourceHandle: resource_handle
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - cpInstanceId: ext_virtual_link_info_ext_link_ports_cp_instance_id
  - currentVnfExtCpData: current_vnf_ext_cp_data
  - cpdId: cpd_id
  - cpConfig: cp_config
  - cpProtocolData: cp_protocol_data
  - layerProtocol: layer_protocol
  - ipOverEthernet: ip_over_ethernet
  - ipAddresses: ip_addresses
  - type: ip_address_type
  - numDynamicAddresses: num_dynamic_addresses
  - extManagedVirtualLinkInfo: ext_managed_virtual_link_info
  - id: ext_managed_virtual_link_info_id
  - vnfVirtualLinkDescId: ext_managed_virtual_link_info_vnf_virtual_link_desc_id
  - networkResource: ext_managed_virtual_link_info_network_resource
  - resourceId: resource_handle_resource_id
  - vnfLinkPorts: vnf_link_ports
  - id: vnf_link_port_id
  - resourceHandle: vnf_link_port_resource_handle
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - cpInstanceId: vnf_link_port_cp_instance_id
  - cpInstanceType: vnf_link_port_cp_instance_type
  - vnfcResourceInfo: vnfc_resource_info
  - id: vnfc_resource_info_id
  - vduId: vnfc_resource_info_vdu_id
  - computeResource: vnfc_resource_info_compute_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - vnfcCpInfo: vnfc_resource_info_vnfc_cp_info
  - id: vnfc_cp_info_id
  - cpdId: vnfc_cp_info_cpd_id
  - vnfExtCpId: vnfc_cp_info_vnf_ext_cp_id
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
  - cpInstanceType: vnf_link_port_cp_instance_type
  - virtualStorageResourceInfo: virtual_storage_resource_info
  - id: virtual_storage_resource_info_id
  - virtualStorageDescId: virtual_storage_resource_info_virtual_storage_desc_id
  - storageResource: virtual_storage_resource_info_storage_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - metadata: vnf_instance_metadata
  - vnfcInfo: vnfc_info
  - id: vnfc_info_id
  - vduId: vnfc_info_vdu_id
  - vnfcResourceInfoId: vnfc_resource_info_id
  - vnfcState: vnfc_info_vnfc_state
  - _links: vnf_instance_links

Response Example
----------------

.. literalinclude:: samples/vnflcm/list-vnf-instance-response.json
   :language: javascript

Scale a VNF instance (v2)
=========================

.. rest_method::  POST /vnflcm/v2/vnf_instances/{vnfInstanceId}/scale

This task resource represents the "Scale VNF" operation. The client can use
this resource to request scaling a VNF instance.

The POST method scales a VNF instance.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 202

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404
  - 406
  - 409
  - 422

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - vnfInstanceId: vnf_instance_id
  - type: scale_type
  - aspectId: aspect_id
  - numberOfSteps: number_of_steps
  - additionalParams: scale_additional_params

Request Example
---------------

.. literalinclude:: samples/vnflcm/scale-vnf-instance-request.json
   :language: javascript

Update a VNF instance (v2)
==========================

.. rest_method::  PATCH vnflcm/v2/vnf_instances/{vnfInstanceId}

Changes to the VNF configurable properties are applied to the configuration
in the VNF instance, and are reflected in the representation of this resource.
Other changes are applied to the VNF instance information managed by the VNFM,
and are reflected in the representation of this resource.

According to the ETSI NFV SOL document, there is no API request/response
specification for Etag yet, and transactions using Etag are not defined
by standardization. Therefore, the Yoga release does not support
`Error Code: 412 Precondition Failed`. Once a standard specification
for this is established, it will be installed on the tacker.

This method modifies an "Individual VNF instance".

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 202

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404
  - 406
  - 409
  - 422

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - vnfInstanceId: vnf_instance_id
  - vnfInstanceName: vnf_instance_update_request_name
  - vnfInstanceDescription: vnf_instance_update_request_description
  - vnfdId: vnf_instance_update_request_vnfd_id
  - vnfConfigurableProperties: vnf_instance_update_configurable_properties
  - metadata: vnf_instance_update_request_metadata
  - extensions: vnf_instance_update_extensions
  - vimConnectionInfo: vnf_instance_vim_connection_info
  - vimId: vim_connection_info_vim_id
  - vimType: vim_connection_info_vim_type
  - interfaceInfo: vim_connection_info_interface_info
  - accessInfo: vim_connection_info_access_info
  - extra: vim_connection_info_extra
  - vnfcInfoModifications: vnfc_info_modifications
  - id: vnfc_info_modifications_id
  - vnfcConfigurableProperties: vnfc_configurable_properties

.. note::
    All attribute does not support "null" in JSON Merge Patch.
    For attribute whose Type is "key value pairs", the key is deleted by
    specifying null. (The attribute itself cannot be deleted.)

Request Example
---------------

.. literalinclude:: samples/vnflcm/update-vnf-instance-request.json
   :language: javascript

Change External VNF Connectivity (v2)
=====================================

.. rest_method::  POST /vnflcm/v2/vnf_instances/{vnfInstanceId}/change_ext_conn

This task resource represents the "Change external VNF connectivity" operation.
The client can use this resource to change the external connectivity of a VNF instance.

The POST method changes the external connectivity of a VNF instance.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 202

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404
  - 406
  - 409
  - 422

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - vnfInstanceId: vnf_instance_id
  - extVirtualLinks: change_ext_vnf_connectivity_ext_virtual_links
  - id: ext_virtual_links_id
  - vimConnectionId: vim_connection_id
  - resourceProviderId: resource_provider_id
  - resourceId: ext_virtual_links_resource_id
  - extCps: ext_cps
  - cpdId: cpd_id
  - cpConfig: cp_config
  - parentCpConfigId: parent_cp_config_id
  - linkPortId: link_port_id
  - cpProtocolData: cp_protocol_data
  - layerProtocol: layer_protocol
  - ipOverEthernet: ip_over_ethernet
  - macAddress: mac_address
  - segmentationId: segmentation_id
  - ipAddresses: ip_addresses
  - type: ip_address_type
  - fixedAddresses: fixed_addresses
  - numDynamicAddresses: num_dynamic_addresses
  - addressRange: address_range
  - minAddress: min_address
  - maxAddress: max_address
  - subnetId: subnet_id
  - extLinkPorts: ext_link_ports
  - id: ext_link_port_id
  - resourceHandle: ext_link_port_resource_handle
  - vimConnectionId: vim_connection_id
  - resourceProviderId: resource_provider_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - vimConnectionInfo: vnf_instance_vim_connection_info
  - vimId: vim_connection_info_vim_id
  - vimType: vim_connection_info_vim_type
  - interfaceInfo: vim_connection_info_interface_info
  - accessInfo: vim_connection_info_access_info
  - extra: vim_connection_info_extra
  - additionalParams: change_ext_vnf_connectivity_additional_params

Request Example
---------------

.. literalinclude:: samples/vnflcm/change-ext-conn-request.json
   :language: javascript

Show VNF LCM operation occurrence (v2)
======================================

.. rest_method::  GET /vnflcm/v2/vnf_lcm_op_occs/{vnfLcmOpOccId}

The client can use this method to retrieve status information about a VNF lifecycle management operation occurrence
by reading an "Individual VNF LCM operation occurrence" resource.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 401
  - 404
  - 406

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - vnfLcmOpOccId: vnf_lcm_op_occ_id

Response Parameters
-------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - id: vnf_lcm_op_occ_id_response
  - operationState: operation_state
  - stateEnteredTime: state_entered_time
  - startTime: start_time
  - vnfInstanceId: vnf_lcm_vnf_instance_id
  - grantId: grant_id
  - operation: operation
  - isAutomaticInvocation: is_automatic_invocation
  - operationParams: operation_params
  - isCancelPending: is_cancel_pending
  - error: error
  - title: error_title
  - status: error_status
  - detail: error_detail
  - resourceChanges: resource_changes
  - affectedVnfcs: affected_vnfcs
  - id: affected_vnfcs_id
  - vduId: affected_vnfcs_vdu_id
  - changeType: affected_vnfcs_change_type
  - computeResource: vnfc_resource_info_compute_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - affectedVnfcCpIds: affected_vnfc_cp_ids
  - addedStorageResourceIds: added_storage_resource_ids
  - removedStorageResourceIds: removed_storage_resource_ids
  - affectedVirtualLinks: affected_virtual_links
  - id: affected_virtual_links_id
  - vnfVirtualLinkDescId: vnf_virtual_link_resource_info_vnf_virtual_link_desc_id
  - changeType: affected_virtual_links_change_type
  - networkResource: vnf_virtual_link_resource_info_network_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - vnfLinkPortIds: vnf_link_port_ids
  - affectedVirtualStorages: affected_virtual_storages
  - id: affected_virtual_storages_id
  - virtualStorageDescId: affected_virtual_storages_virtual_storage_desc_id
  - changeType: affected_virtual_storages_change_type
  - storageResource: virtual_storage_resource_info_storage_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - changedInfo: changed_info
  - vnfInstanceName: changed_info_vnf_instance_name
  - vnfInstanceDescription: changed_info_vnf_instance_description
  - vnfConfigurableProperties: changed_info_vnf_configurable_properties
  - metadata: changed_info_metadata
  - extensions: changed_info_extensions
  - vimConnectionInfo: changed_info_vim_connection_info
  - vimId: vim_connection_info_vim_id
  - vimType: vim_connection_info_vim_type
  - interfaceInfo: vim_connection_info_interface_info
  - accessInfo: vim_connection_info_access_info
  - extra: vim_connection_info_extra
  - vnfdId: changed_info_vnfd_id
  - vnfProvider: changed_info_vnf_provider
  - vnfProductName: changed_info_vnf_product_name
  - vnfSoftwareVersion: changed_info_vnf_software_version
  - vnfdVersion: changed_info_vnfd_version
  - vnfcInfoModifications: vnfc_info_modifications
  - id: vnfc_info_modifications_id
  - vnfcConfigurableProperties: vnfc_configurable_properties
  - changedExtConnectivity: changed_ext_connectivity
  - id: changed_ext_connectivity_id
  - resourceHandle: resource_handle
  - vimConnectionId: vim_connection_id
  - resourceProviderId: resource_provider_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - extLinkPorts: ext_link_ports
  - id: ext_link_port_id
  - resourceHandle: resource_handle
  - vimConnectionId: vim_connection_id
  - resourceProviderId: resource_provider_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - cpInstanceId: cp_instance_id
  - currentVnfExtCpData: current_vnf_ext_cp_data
  - cpdId: cpd_id
  - cpConfig: cp_config
  - parentCpConfigId: parent_cp_config_id
  - linkPortId: link_port_id
  - cpProtocolData: cp_protocol_data
  - layerProtocol: layer_protocol
  - ipOverEthernet: ip_over_ethernet
  - macAddress: mac_address
  - segmentationId: segmentation_id
  - ipAddresses: ip_addresses
  - type: ip_address_type
  - fixedAddresses: fixed_addresses
  - numDynamicAddresses: num_dynamic_addresses
  - addressRange: address_range
  - minAddress: min_address
  - maxAddress: max_address
  - subnetId: subnet_id
  - _links: vnf_instance_links

Response Example
----------------

.. literalinclude:: samples/vnflcm/show-vnflcm-operation-occurrence-response.json
   :language: javascript

List VNF LCM operation occurrence (v2)
======================================

.. rest_method::  GET /vnflcm/v2/vnf_lcm_op_occs

The API consumer can use this method to query status information about multiple VNF lifecycle management operation
occurrences.

It supports attribute-based filtering and
attribute selectors defined in ETSI NFV SOL013 v3.4.1.
The detail of attribute-based filtering is described in
SOL013 v3.4.1 clause 5.2.

An attribute selector allows the API consumer to choose
which attributes it wants to be contained in the response.
*all_fields*, *fields*, *exclude_fields* and *exclude_default*
can be set as query parameters.

The following attributes shall be excluded from the VnfLcmOpOcc structure in the
response body if this parameter is provided, or none of the parameters "all_fields,"
"fields", "exclude_fields", "exclude_default" are provided:
- operationParams
- error
- resourceChanges
- changedInfo
- changedExtConnectivity.

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

.. rest_parameters:: parameters_vnflcm.yaml

  - id: vnf_lcm_op_occ_id_response
  - operationState: operation_state
  - stateEnteredTime: state_entered_time
  - startTime: start_time
  - vnfInstanceId: vnf_lcm_vnf_instance_id
  - grantId: grant_id
  - operation: operation
  - isAutomaticInvocation: is_automatic_invocation
  - operationParams: operation_params
  - isCancelPending: is_cancel_pending
  - error: error
  - title: error_title
  - status: error_status
  - detail: error_detail
  - resourceChanges: resource_changes
  - affectedVnfcs: affected_vnfcs
  - id: affected_vnfcs_id
  - vduId: affected_vnfcs_vdu_id
  - changeType: affected_vnfcs_change_type
  - computeResource: vnfc_resource_info_compute_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - affectedVnfcCpIds: affected_vnfc_cp_ids
  - addedStorageResourceIds: added_storage_resource_ids
  - removedStorageResourceIds: removed_storage_resource_ids
  - affectedVirtualLinks: affected_virtual_links
  - id: affected_virtual_links_id
  - vnfVirtualLinkDescId: vnf_virtual_link_resource_info_vnf_virtual_link_desc_id
  - changeType: affected_virtual_links_change_type
  - networkResource: vnf_virtual_link_resource_info_network_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - vnfLinkPortIds: vnf_link_port_ids
  - affectedVirtualStorages: affected_virtual_storages
  - id: affected_virtual_storages_id
  - virtualStorageDescId: affected_virtual_storages_virtual_storage_desc_id
  - changeType: affected_virtual_storages_change_type
  - storageResource: virtual_storage_resource_info_storage_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - changedInfo: changed_info
  - vnfInstanceName: changed_info_vnf_instance_name
  - vnfInstanceDescription: changed_info_vnf_instance_description
  - vnfConfigurableProperties: changed_info_vnf_configurable_properties
  - metadata: changed_info_metadata
  - extensions: changed_info_extensions
  - vimConnectionInfo: changed_info_vim_connection_info
  - vimId: vim_connection_info_vim_id
  - vimType: vim_connection_info_vim_type
  - interfaceInfo: vim_connection_info_interface_info
  - accessInfo: vim_connection_info_access_info
  - extra: vim_connection_info_extra
  - vnfdId: changed_info_vnfd_id
  - vnfProvider: changed_info_vnf_provider
  - vnfProductName: changed_info_vnf_product_name
  - vnfSoftwareVersion: changed_info_vnf_software_version
  - vnfdVersion: changed_info_vnfd_version
  - vnfcInfoModifications: vnfc_info_modifications
  - id: vnfc_info_modifications_id
  - vnfcConfigurableProperties: vnfc_configurable_properties
  - changedExtConnectivity: changed_ext_connectivity
  - id: changed_ext_connectivity_id
  - resourceHandle: resource_handle
  - vimConnectionId: vim_connection_id
  - resourceProviderId: resource_provider_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - extLinkPorts: ext_link_ports
  - id: ext_link_port_id
  - resourceHandle: resource_handle
  - vimConnectionId: vim_connection_id
  - resourceProviderId: resource_provider_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - cpInstanceId: cp_instance_id
  - currentVnfExtCpData: current_vnf_ext_cp_data
  - cpdId: cpd_id
  - cpConfig: cp_config
  - parentCpConfigId: parent_cp_config_id
  - linkPortId: link_port_id
  - cpProtocolData: cp_protocol_data
  - layerProtocol: layer_protocol
  - ipOverEthernet: ip_over_ethernet
  - macAddress: mac_address
  - segmentationId: segmentation_id
  - ipAddresses: ip_addresses
  - type: ip_address_type
  - fixedAddresses: fixed_addresses
  - numDynamicAddresses: num_dynamic_addresses
  - addressRange: address_range
  - minAddress: min_address
  - maxAddress: max_address
  - subnetId: subnet_id
  - _links: vnf_instance_links

Response Example
----------------

.. literalinclude:: samples/vnflcm/list-vnflcm-operation-occurrence-response.json
   :language: javascript

Retry a VNF LCM operation occurrence (v2)
=========================================

.. rest_method::  POST /vnflcm/v2/vnf_lcm_op_occs/{vnfLcmOpOccId}/retry

The POST method starts retrying a VNF lifecycle operation if that operation
has experienced a temporary failure, i.e. the related
"Individual VNF LCM operation occurrence" resource is in "FAILED_TEMP" state.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 202

.. rest_status_code:: error status.yaml

  - 401
  - 404
  - 409
  - 422

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - vnfLcmOpOccId: vnf_lcm_op_occ_id

Fail a VNF LCM operation occurrence (v2)
========================================

.. rest_method::  POST /vnflcm/v2/vnf_lcm_op_occs/{vnfLcmOpOccId}/fail

The POST method marks a VNF lifecycle management operation occurrence
as "finally failed" if that operation occurrence is in "FAILED_TEMP" state.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 401
  - 404
  - 406
  - 409
  - 422

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - vnfLcmOpOccId: vnf_lcm_op_occ_id

Response Parameters
-------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - id: vnf_lcm_op_occ_id_response
  - operationState: operation_state
  - stateEnteredTime: state_entered_time
  - startTime: start_time
  - vnfInstanceId: vnf_instance_id
  - grantId: grant_id
  - operation: operation
  - isAutomaticInvocation: is_automatic_invocation
  - operationParams: operation_params
  - isCancelPending: is_cancel_pending
  - error: error
  - title: error_title
  - status: error_status
  - detail: error_detail
  - resourceChanges: resource_changes
  - affectedVnfcs: affected_vnfcs
  - id: affected_vnfcs_id
  - vduId: affected_vnfcs_vdu_id
  - changeType: affected_vnfcs_change_type
  - computeResource: vnfc_resource_info_compute_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - affectedVnfcCpIds: affected_vnfc_cp_ids
  - addedStorageResourceIds: added_storage_resource_ids
  - removedStorageResourceIds: removed_storage_resource_ids
  - affectedVirtualLinks: affected_virtual_links
  - id: affected_virtual_links_id
  - vnfVirtualLinkDescId: vnf_virtual_link_resource_info_vnf_virtual_link_desc_id
  - changeType: affected_virtual_links_change_type
  - networkResource: vnf_virtual_link_resource_info_network_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - affectedVirtualStorages: affected_virtual_storages
  - id: affected_virtual_storages_id
  - virtualStorageDescId: affected_virtual_storages_virtual_storage_desc_id
  - changeType: affected_virtual_storages_change_type
  - storageResource: virtual_storage_resource_info_storage_resource
  - vimConnectionId: vim_connection_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - changedInfo: changed_info
  - vnfInstanceName: changed_info_vnf_instance_name
  - vnfInstanceDescription: changed_info_vnf_instance_description
  - vnfConfigurableProperties: changed_info_vnf_configurable_properties
  - metadata: changed_info_metadata
  - extensions: changed_info_extensions
  - vimConnectionInfo: changed_info_vim_connection_info
  - vimId: vim_connection_info_vim_id
  - vimType: vim_connection_info_vim_type
  - interfaceInfo: vim_connection_info_interface_info
  - accessInfo: vim_connection_info_access_info
  - extra: vim_connection_info_extra
  - vnfdId: changed_info_vnfd_id
  - vnfProvider: changed_info_vnf_provider
  - vnfProductName: changed_info_vnf_product_name
  - vnfSoftwareVersion: changed_info_vnf_software_version
  - vnfdVersion: changed_info_vnfd_version
  - vnfcInfoModifications: vnfc_info_modifications
  - id: vnfc_info_modifications_id
  - vnfcConfigurableProperties: vnfc_configurable_properties
  - changedExtConnectivity: changed_ext_connectivity
  - id: changed_ext_connectivity_id
  - resourceHandle: resource_handle
  - vimConnectionId: vim_connection_id
  - resourceProviderId: resource_provider_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - extLinkPorts: ext_link_ports
  - id: ext_link_port_id
  - resourceHandle: resource_handle
  - vimConnectionId: vim_connection_id
  - resourceProviderId: resource_provider_id
  - resourceId: resource_handle_resource_id
  - vimLevelResourceType: resource_handle_vim_level_resource_type
  - cpInstanceId: cp_instance_id
  - currentVnfExtCpData: current_vnf_ext_cp_data
  - cpdId: cpd_id
  - cpConfig: cp_config
  - parentCpConfigId: parent_cp_config_id
  - linkPortId: link_port_id
  - cpProtocolData: cp_protocol_data
  - layerProtocol: layer_protocol
  - ipOverEthernet: ip_over_ethernet
  - macAddress: mac_address
  - segmentationId: segmentation_id
  - ipAddresses: ip_addresses
  - type: ip_address_type
  - fixedAddresses: fixed_addresses
  - numDynamicAddresses: num_dynamic_addresses
  - addressRange: address_range
  - minAddress: min_address
  - maxAddress: max_address
  - subnetId: subnet_id
  - _links: vnf_instance_links

Response Example
----------------

.. literalinclude:: samples/vnflcm/fail-vnflcm-operation-occurrence-response.json
   :language: javascript

Rollback a VNF LCM operation occurrence (v2)
============================================

.. rest_method::  POST /vnflcm/v2/vnf_lcm_op_occs/{vnfLcmOpOccId}/rollback

The POST method starts rolling back a VNF lifecycle operation if that operation
has experienced a temporary failure, i.e. the related
"Individual VNF LCM operation occurrence" resource is in "FAILED_TEMP" state.
In case of rolling back an occurrence of the "InstantiateVnf" operation,
the VNFM shall request to the VIM the release of the virtualised
resources that were allocated for the related VNF instance.
The "rollback" task shall be supported by the VNFM for any VNF LCM operation occurrence
that represents an "InstantiateVnf" operation in FAILED_TEMP state.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 202

.. rest_status_code:: error status.yaml

  - 401
  - 404
  - 409
  - 422

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - vnfLcmOpOccId: vnf_lcm_op_occ_id

Create a new subscription (v2)
==============================

.. rest_method::  POST /vnflcm/v2/subscriptions

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

  - 401
  - 406
  - 422

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - filter: filter
  - vnfInstanceSubscriptionFilter: vnf_instance_subscription_filter
  - vnfdIds: vnfd_ids
  - vnfProductsFromProviders: vnf_products_from_providers
  - vnfProvider: vnf_provider
  - vnfProducts: vnf_products
  - vnfProductName: vnf_product_name
  - versions: vnf_product_versions
  - vnfSoftwareVersion: vnf_product_vnf_software_version
  - vnfdVersions: vnfd_versions
  - vnfInstanceIds: vnf_instance_ids
  - vnfInstanceName: vnf_instance_names
  - notificationTypes: filter_notification_types
  - operationTypes: filter_operation_types
  - operationStates: filter_operation_states
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
  - verbosity: vnf_subscription_create_request_verbosity

Request Example
---------------

.. literalinclude:: samples/vnflcm/create-subscription-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - id: subscription_id_response
  - callbackUri: callback_uri
  - verbosity: verbosity
  - _links: vnf_instance_links

Response Example
----------------

.. literalinclude:: samples/vnflcm/create-subscription-response.json
   :language: javascript

Delete a subscription
=========================

.. rest_method::  DELETE /vnflcm/v2/subscriptions/{subscriptionId}

The DELETE method terminates an individual subscription.

As the result of successfully executing this method, the "Individual subscription" resource shall not exist any longer.
This means that no notifications for that subscription shall be sent to the formerly-subscribed API consumer.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 204

.. rest_status_code:: error status.yaml

  - 401
  - 404
  - 406

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - subscriptionId: subscription_id

Show subscription (v2)
======================

.. rest_method::  GET /vnflcm/v2/subscriptions/{subscriptionId}

The GET method retrieves information about a subscription by reading an "Individual subscription" resource.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 401
  - 404
  - 406

Request Parameters
------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - subscriptionId: subscription_id

Response Parameters
-------------------

.. rest_parameters:: parameters_vnflcm.yaml

  - id: subscription_id_response
  - callbackUri: callback_uri
  - verbosity: verbosity
  - _links: vnf_instance_links

Response Example
----------------

.. literalinclude:: samples/vnflcm/show-subscription-response.json
   :language: javascript

List subscription (v2)
======================

.. rest_method::  GET /vnflcm/v2/subscriptions

The GET method queries the list of active subscriptions of the functional block that invokes the method.
It can be used e.g. for resynchronization after error situations.

It supports attribute-based filtering in ETSI NFV SOL013 v3.4.1.
The detail of attribute-based filtering is described in
SOL013 v3.4.1 clause 5.2.


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

.. rest_parameters:: parameters_vnflcm.yaml

  - id: subscription_id_response
  - callbackUri: callback_uri
  - verbosity: verbosity
  - _links: vnf_instance_links

Response Example
----------------

.. literalinclude:: samples/vnflcm/list-subscription-response.json
   :language: javascript
