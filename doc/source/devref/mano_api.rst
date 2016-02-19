*******************
Tacker API Overview
*******************

Tacker API introduces new REST API end-points based on ETSI NFV MANO
standards[#]_.
The two new resources introduced are 'vnfd' and 'vnf' for
describing the 'vnfm' extension. The resources request and response formats are
described in below sections.

API versions
============

Lists information for Tacker API version.

**GET /**

List API versions - Lists information about Tacker API version.

::


 Response:
     {
         "versions": [
             {
                 "status": "CURRENT",
                 "id": "v1.0",
                 "links": [
                     {
                         "href": "http://10.18.160.13:8888/v1.0",
                         "rel": "self"
                     }
                 ]
             }
         ]
     }

Vnfds
=====

**GET /v1.0/vnfds**

List vnfds - List vnfds stored in the VNF catalog.

::

 Response:
 {
     "vnfds": [
         {
             "service_types": [
                 {
                     "service_type": "vnfd",
                     "id": "378b774d-89f5-4634-9c65-9c49ed6f00ce"
                 }
             ],
             "description": "OpenWRT with services",
             "tenant_id": "4dd6c1d7b6c94af980ca886495bcfed0",
             "mgmt_driver": "openwrt",
             "infra_driver": "heat",
             "attributes": {
                 "vnfd": "template_name: OpenWRT\r\ndescription:
                 template_description <sample_vnfd_template>"
             },
             "id": "247b045e-d64f-4ae0-a3b4-8441b9e5892c",
             "name": "openwrt_services"
         }
     ]
 }

**GET /v1.0/vnfds/{vnfd_id}**

Show vnfd - Show information for a specified vnfd id.

::

 Response:
 {
     "vnfd": {
         "service_types": [
             {
                 "service_type": "vnfd",
                 "id": "378b774d-89f5-4634-9c65-9c49ed6f00ce"
             }
         ],
         "description": "OpenWRT with services",
         "tenant_id": "4dd6c1d7b6c94af980ca886495bcfed0",
         "mgmt_driver": "openwrt",
         "infra_driver": "heat",
         "attributes": {
             "vnfd": "template_name: OpenWRT\r\ndescription:
             template_description <sample_vnfd_template>"
         },
         "id": "247b045e-d64f-4ae0-a3b4-8441b9e5892c",
         "name": "openwrt_services"
     }
 }

**POST /v1.0/vnfds**

Create vnfd - Create a vnfd entry based on the vnfd template.

::

 Request:
     {"auth": {"tenantName": "admin", "passwordCredentials": {"username": "admin",
     "password": "devstack"}}, "vnfd": {"attributes": {"vnfd": "template_name:
     OpenWRT \r\ndescription: OpenWRT router\r\n\r\nservice_properties:\r\n  Id:
     sample-vnfd\r\n  vendor: tacker\r\n  version: 1\r\n\r\nvdus:\r\n  vdu1:\r\n
     id: vdu1\r\n    vm_image: cirros-0.3.2-x86_64-uec\r\n    instance_type:
     m1.tiny\r\n\r\n    network_interfaces:\r\n      management:\r\n        network:
      net_mgmt\r\n        management: true\r\n      pkt_in:\r\n        network:
      net0\r\n      pkt_out:\r\n        network: net1\r\n\r\n    placement_policy:
      \r\n      availability_zone: nova\r\n\r\n    auto-scaling: noop\r\n
      monitoring_policy: noop\r\n    failure_policy: noop\r\n\r\n    config:\r\n
      param0: key0\r\n      param1: key1"}, "service_types": [{"service_type":
      "vnfd"}], "mgmt_driver": "noop", "infra_driver": "heat"}}

::

 Response:
  {
     "vnfd": {
         "service_types": [
             {
                 "service_type": "vnfd",
                 "id": "336fe422-9fba-47c7-87fb-d48475c3e0ce"
             }
         ],
         "description": "OpenWRT router",
         "tenant_id": "4dd6c1d7b6c94af980ca886495bcfed0",
         "mgmt_driver": "noop",
         "infra_driver": "heat",
         "attributes": {
             "vnfd": "template_name: OpenWRT \r\ndescription:
             template_description <sample_vnfd_template>"
         },
         "id": "ab10a543-22ee-43af-a441-05a9d32a57da",
         "name": "OpenWRT"
     }
 }

**DELETE /v1.0/vnfds/{vnfd_id}**

Delete vnfd - Deletes a specified vnfd_id from the VNF catalog.

This operation does not accept a request body and does not return a response
body.

Vnfs
====

**GET /v1.0/vnfs**

List vnfs - Lists instantiated vnfs in VNF Manager

::

 Response:
     {
         "vnfs": [
             {
                 "status": "ACTIVE",
                 "name": "open_wrt",
                 "tenant_id": "4dd6c1d7b6c94af980ca886495bcfed0",
                 "instance_id": "f7c93726-fb8d-4036-8349-2e82f196e8f6",
                 "mgmt_url": "{\"vdu1\": \"192.168.120.3\"}",
                 "attributes": {
                     "service_type": "firewall",
                     "param_values": "",
                     "heat_template": "description: sample_template_description
                         type: OS::Nova::Server\n",
                     "monitoring_policy": "noop",
                     "failure_policy": "noop"
                 },
                 "id": "c9b4f5a5-d304-473a-a57e-b665b1f9eb8f",
                 "description": "OpenWRT with services"
             }
         ]
     }

**GET /v1.0/vnfs/{vnf_id}**

Show vnf - Show information for a specified vnf_id.

::

 Response:
     {
         "vnf": [
             {
                 "status": "ACTIVE",
                 "name": "open_wrt",
                 "tenant_id": "4dd6c1d7b6c94af980ca886495bcfed0",
                 "instance_id": "f7c93726-fb8d-4036-8349-2e82f196e8f6",
                 "mgmt_url": "{\"vdu1\": \"192.168.120.3\"}",
                 "attributes": {
                     "service_type": "firewall",
                     "param_values": "",
                     "heat_template": "description: OpenWRT with services\n
                     sample_template_description    type: OS::Nova::Server\n",
                     "monitoring_policy": "noop", "failure_policy": "noop"
                 },
                 "id": "c9b4f5a5-d304-473a-a57e-b665b1f9eb8f",
                 "description": "OpenWRT with services"
             }
         ]
     }

**POST /v1.0/vnfs**

Create vnf - Create a vnf based on the vnfd template id.

::

 Request:
     {"auth": {"tenantName": "admin", "passwordCredentials": {"username": "admin",
     "password": "devstack"}}, "vnf":
     {"vnfd_id": "d770ddd7-6014-4191-92d8-a2cd7a6cecd8"}}

::

 Response:
     {
         "vnf": {
             "status": "PENDING_CREATE",
             "name": "",
             "tenant_id": "4dd6c1d7b6c94af980ca886495bcfed0",
             "description": "OpenWRT with services",
             "instance_id": "4f0d6222-afa0-4f02-8e19-69e7e4fd7edc",
             "mgmt_url": null,
             "attributes": {
                 "service_type": "firewall",
                 "heat_template": "description: OpenWRT with services\n
                 <sample_heat_template> type: OS::Nova::Server\n",
                 "monitoring_policy": "noop",
                 "failure_policy": "noop"
             },
             "id": "e3158513-92f4-4587-b949-70ad0bcbb2dd",
             "vnfd_id": "247b045e-d64f-4ae0-a3b4-8441b9e5892c"
         }
     }

**PUT /v1.0/vnfs/{vnf_id}**

Update vnf - Update a vnf based on user config file or data.

::

 Request:
     {"auth": {"tenantName": "admin", "passwordCredentials": {"username": "admin",
     "password": "devstack"}}, "vnf": {"attributes": {"config": "vdus:\n  vdu1:
     <sample_vdu_config> \n\n"}}}

::

 Response:
     {
         "vnf": {
             "status": "PENDING_UPDATE",
             "name": "",
             "tenant_id": "4dd6c1d7b6c94af980ca886495bcfed0",
             "instance_id": "4f0d6222-afa0-4f02-8e19-69e7e4fd7edc",
             "mgmt_url": "{\"vdu1\": \"192.168.120.4\"}",
             "attributes": {
                 "service_type": "firewall",
                 "monitoring_policy": "noop",
                 "config": "vdus:\n  vdu1:\n    config: {<sample_vdu_config>
                  type: OS::Nova::Server\n",
                 "failure_policy": "noop"
             },
             "id": "e3158513-92f4-4587-b949-70ad0bcbb2dd",
             "description": "OpenWRT with services"
         }
     }

**DELETE /v1.0/vnfs/{vnf_id}**

Delete vnf - Deletes a specified vnf_id from the VNF list.

References
==========

.. [#] `ETSI NFV MANO <http://www.etsi.org/deliver/etsi_gs/NFV-MAN/001_099/001/01.01.01_60/gs_nfv-man001v010101p.pdf>`_
