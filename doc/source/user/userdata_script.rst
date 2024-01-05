============================
UserData script (VNF LCM v2)
============================

This document describes the requirements of userdata script
how to make it for VNF LCM version 2.

Userdata script enables operators to flexibly customize VIM input parameter
in LCM operations.

If you would like to know how to deploy VNF using userdata script,
please check `ETSI NFV-SOL VNF Deployment as VM with LCM Operation User Data`_
or like to know how to make VNF packages including userdata script,
please check `VNF Package manual`_.


Requirements
============

Userdata script must be described according to the following rules.

Userdata class needs to be defined in userdata script file.
Any file name and class name are acceptable.

.. note::
 The names of the file and class have to correspond to following
 request parameters of LCM API,
 "lcm-operation-user-data", "lcm-operation-user-data-class".


userdata class must inherit "userdata_utils.AbstractUserData",
then functions have to be implemented.

Followings are requirements of methods supported by latest Tacker.

Input of all methods
--------------------

All methods can use the following input data.
The details of data types are defined in ETSI NFV SOL documents.

- req: operationParams corresponding to API request
- inst: VnfInstance
- grant_req: GrantRequest
- grant: Grants
- tmp_csar_dir: the temporary path of csar expanded by Tacker


Output of methods
-----------------

The required output is different for methods.

instantiate()
^^^^^^^^^^^^^

The method must return the following structure.
Data are for stack create API in HEAT.
The requirements of HEAT API are described in
`reference of Orchestration Service API v1
"POST /v1/{tenant_id}/stacks"`_

fields = {'template': value, 'parameters': value, 'files': value}

- template: Dump of top HOT file
- parameters: Input parameters for Heat API
- files: Dump of all nested HOT files in the package

Following shows sample output.

.. code-block:: python

 fields = {
             'template': yaml.safe_dump(top_hot),
             'parameters': {'nfv': nfv_dict},
             'files': {}
         }
         for key, value in hot_dict.get('files', {}).items():
             fields['files'][key] = yaml.safe_dump(value)

         return fields


scale()
^^^^^^^

The method must return the following structure if it is necessary to modify.
Data are for update stack API in HEAT.
The requirements of HEAT API are described in
`reference of Orchestration Service API v1
"PATCH /v1/{tenant_id}/stacks/{stack_name}/{stack_id}"`_

fields = {'parameters': {'nfv': {'VDU': new_vdus}}}

- parameters: Input parameters for Heat API

Following shows sample output.

.. code-block:: python

        fields = {'parameters': {'nfv': {'VDU': new_vdus}}}

        return fields


scale_rollback()
^^^^^^^^^^^^^^^^

The method must return the following structure if it is necessary to modify.
Data are for update stack API in HEAT.
The requirements of HEAT API are described in
`reference of Orchestration Service API v1
"PATCH /v1/{tenant_id}/stacks/{stack_name}/{stack_id}"`_

fields = {'parameters': {'nfv': {'VDU': new_vdus}}}

- parameters: Input parameters for Heat API

Following shows sample output.

.. code-block:: python

        fields = {'parameters': {'nfv': {'VDU': new_vdus}}}

        return fields


change_ext_conn()
^^^^^^^^^^^^^^^^^

The method must return the following structure.
Data are for update stack API in HEAT.
The requirements of HEAT API are described in
`reference of Orchestration Service API v1
"PATCH /v1/{tenant_id}/stacks/{stack_name}/{stack_id}"`_

fields = {'parameters': {'nfv': {'CP': new_cps}}}

- parameters: Input parameters for Heat API

Following shows sample output.

.. code-block:: python

        fields = {'parameters': {'nfv': {'CP': new_cps}}}

        return fields


change_ext_conn_rollback()
^^^^^^^^^^^^^^^^^^^^^^^^^^

The method must return the following structure.
Data are for update stack API in HEAT.
The requirements of HEAT API are described in
`reference of Orchestration Service API v1
"PATCH /v1/{tenant_id}/stacks/{stack_name}/{stack_id}"`_

fields = {'parameters': {'nfv': {'CP': new_cps}}}

- parameters: Input parameters for Heat API

Following shows sample output.

.. code-block:: python

        fields = {'parameters': {'nfv': {'CP': new_cps}}}

        return fields


heal()
^^^^^^

The method must return the following structure.
Data are for update stack API in HEAT.
The requirements of HEAT API are described in
`reference of Orchestration Service API v1
"PATCH /v1/{tenant_id}/stacks/{stack_name}/{stack_id}"`_

fields = {'parameters': {'nfv': {}}}

- parameters: Input parameters for Heat API

Following shows sample output.

.. code-block:: python

        fields = {'parameters': {'nfv': {}}}

        return fields

Sample userdata script using AutoScalingGroup
=============================================

If users do not specify the userdata in instantiate VNF request,
the default process runs according to the following script.

The script can be used as a sample for making the original userdata script.
It obtains HEAT input parameters such as
*computeFlavourId*, *vcImageId*, *locationConstraints*,
*network*, *subnet*, and *fixed_ips*
from VNFD, parameters of Instantiate request and Grant.

.. literalinclude:: ../../../tacker/sol_refactored/infra_drivers/openstack/userdata_default.py
    :language: python

The following is sample Base HOT corresponding to above sample userdata script.

**top Base HOT**

.. literalinclude:: ../../../samples/tests/functional/sol_v2_common/basic_lcms_max/contents/BaseHOT/simple/sample1.yaml
    :language: yaml

**nested Base HOT**

.. literalinclude:: ../../../samples/tests/functional/sol_v2_common/basic_lcms_max/contents/BaseHOT/simple/nested/VDU1.yaml
    :language: yaml


Sample userdata script for not using AutoScalingGroup
=====================================================

Even if OS::Heat::AutoScalingGroup is not specified in HOT,
Tacker can create the desired number of VNFC resources
as individual resources on the basis of the VNFD.
This configuration enables users to handle individual VNFC resources,
e.g. users can change images or networks of specified VNFC.

The following shows the sample userdata script
for handling VNFCs without AutoScalingGroup.

.. literalinclude:: ../../../tacker/sol_refactored/infra_drivers/openstack/userdata_standard.py

Following is the specification of the sample UserData script.

* UserData script calculates the number of VNFCs on the basis of
  the number of ``VnfInstance.instantiatedVnfInfo.vnfcResourceInfo``,
  ``Grant.addResources``, and ``Grant.removeResources``
  similar to the method of calculating desired_capacity.
  `get_param_capacity`, which is one of the utility functions
  for UserData class can be used to get the number of resources.

* UserData script describes the same number of resources
  as VNFC to adjusted HOT.

  * UserData scripts create the resource id of VNFC (e.g. VDU1-0, VDU-1-1).
  * Properties of resources are copied from BaseHOT.

* UserData script makes the input-parameter corresponding to Adjusted HOT.

.. note::
  There is a difference in scale-in operation with and without AutoScalingGroup.
  VNFCs are deleted in order from the latest in scale-in operation.
  In the case of using AutoScalingGroup, the latest resource is determined
  on the basis of the `creation_time` by OpenStack Nova.
  Since `creation_time` is updated by heal operation,
  the order of VNFCs is changed dynamically.
  On the other hand, in the case of not using AutoScalingGroup,
  the latest resource is determined by the resource-id (e.g. VDU1-0, VDU1-1).
  Thus the order of the VNFc is not changed by heal operation when not using
  AutoScalingGroup.

This userdata script creates the adjusted HOT from BaseHOT
in the VNF package and it is used as HEAT template.

The following shows a sample BaseHOT and adjusted HOT.

BaseHOT
-------

* top HOT

  .. code-block:: yaml

    heat_template_version: 2013-05-23
    description: Test Base HOT

    parameters:
      nfv:
        type: json

    resources:
      VDU1:
        type: VDU1.yaml
        properties:
          name: { get_param: [ nfv, VDU, VDU1, computeName ] }
          flavor: { get_param: [ nfv, VDU, VDU1, computeFlavourId ] }
          image: { get_param: [ nfv, VDU, VDU1, vcImageId ] }
          zone: { get_param: [ nfv, VDU, VDU1, locationConstraints] }
          net: { get_param: [ nfv, CP, VDU1_CP1, network] }

* nested HOT (VDU1.yaml specified in above top HOT)

  .. code-block:: yaml

    heat_template_version: 2013-05-23
    description: 'VDU1 HOT for Sample VNF'

    parameters:
      name:
        type: string
      flavor:
        type: string
      image:
        type: string
      zone:
        type: string
      net:
        type: string

    resources:
      VDU1:
        type: OS::Nova::Server
        properties:
          name: { get_param: name }
          flavor: { get_param: flavor }
          image: { get_param: image }
          networks:
          - port:
              get_resource: VDU1_CP1

          availability_zone: { get_param: zone }

      VDU1_CP1:
        type: OS::Neutron::Port
        properties:
          network: { get_param: net }

* Input-parameter

  .. code-block:: json

    "nfv": {
      "VDU": {
        "VDU1": {
          "computeName": "VDU1",
          "computeFlavourId": "m1.tiny",
          "vcImageId": "6b8a14f0-1b40-418a-b650-ae4a0378daa5",
          "locationConstraints": "zone-x"
        }
      },
      "CP": {
        "VDU1_CP1": {
          "network": "67c837dc-c247-4a3e-ac0f-5603bfef1ba3"
        }
      }
    }

Adjusted HOT
------------

* top HOT

  .. code-block:: yaml

    heat_template_version: 2013-05-23
    description: Test Base HOT

    parameters:
      nfv:
        type: json

    resources:
      VDU1-0:
        type: VDU1.yaml
        properties:
          name: { get_param: [ nfv, VDU, VDU1-0, computeName ] }
          flavor: { get_param: [ nfv, VDU, VDU1-0, computeFlavourId ] }
          image: { get_param: [ nfv, VDU, VDU1-0, vcImageId ] }
          zone: { get_param: [ nfv, VDU, VDU1-0, locationConstraints ] }
          net: { get_param: [ nfv, CP, VDU1_CP1-0, network ] }
      VDU1-1:
        type: VDU1.yaml
        properties:
          name: { get_param: [ nfv, VDU, VDU1-1, computeName ] }
          flavor: { get_param: [ nfv, VDU,VDU1-1, computeFlavourId ] }
          image: { get_param: [ nfv, VDU,VDU1-1, vcImageId ] }
          zone: { get_param: [ nfv, VDU,VDU1-1, locationConstraints ] }
          net: { get_param: [ nfv, CP, VDU1_CP1-1,network ] }

* nested HOT

  Only the top HOT is changed to the adjusted HOT.
  Nested HOT is unchanged from BaseHOT.

* Input-parameter

  .. code-block:: json

    "nfv": {
      "VDU": {
        "VDU1-0": {
          "computeName": "VDU1-0",
          "computeFlavourId": "m1.tiny",
          "vcImageId": "6b8a14f0-1b40-418a-b650-ae4a0378daa5",
          "locationConstraints": "zone-x"
        },
        "VDU1-1": {
          "computeName": "VDU1-1",
          "computeFlavourId": "m1.large",
          "vcImageId": "0ef0597c-4aab-4235-8513-bf5d8304fe64",
          "locationConstraints": "zone-y"
        }
      },
      "CP": {
        "VDU1_CP1-0": {
          "network": "67c837dc-c247-4a3e-ac0f-5603bfef1ba3"
        },
        "VDU1_CP1-1": {
          "network": "4d8aa289-21eb-4997-86f2-49a884f78d0b"
        }
      }
    }


Utility functions for userdata class
====================================

Tacker provides the following utility functions
for the userdata script.
Following functions can be called in userdata class.


def get_vnfd(vnfd_id, csar_dir)
-------------------------------

Get vnfd in yaml format.

**vnf_id**: vnfid
, **csar_dir**: the path of csar

It returns an instance of `Vnfd class`_.


def init_nfv_dict(hot_template)
-------------------------------

Find the parameter specified by **get_param** in the HOT template
and get the dict of the nfv structure for the HEAT input parameter.

**hot_template**: HOT in yaml format.

It returns **the dict of nfv structure**.


def get_param_flavor(vdu_name, req, vnfd, grant)
------------------------------------------------

Get flavor of VDU. If Grant contains the flavor, it is returned.
Otherwise, flavor is obtained from vnfd and returned.

**vdu_name**: the name of VDU
, **req**: operationParams corresponding to API request
, **vnfd**: vnfd
, **grant**: Grants

It returns **vimFlavourId**


def get_param_image(vdu_name, req, vnfd, grant)
-----------------------------------------------

Get software image of VDU.
If Grant contains the glance-imageId corresponding to the VDU, it is returned.
Otherwise, name of software image is obtained from vnfd and returned.

**vdu_name**: the name of VDU
, **req**: operationParams corresponding to API request
, **vnfd**: vnfd
, **grant**: Grants

It returns **image ID** or **image name**.


def get_param_zone(vdu_name, grant_req, grant)
----------------------------------------------

Get zone id of VDU.

**vdu_name**: the name of VDU
, **req**: operationParams corresponding to API request
, **vnfd**: vnfd
, **grant**: Grants

It returns **zone id**.


def get_current_capacity(vdu_name, inst)
----------------------------------------

Get desired capacity.

**vdu_name**: the name of VDU
, **inst**: VnfInstance

It returns **desired capacity**.


def get_param_capacity(vdu_name, inst, grant_req)
-------------------------------------------------

Refer to addResources and removeResources in the grant request
and get desired capacity.

**vdu_name**: the name of VDU
, **inst**: VnfInstance
, **grant_req**: GrantRequest

It returns **desired capacity**.


def _get_fixed_ips_from_extcp(extcp)
------------------------------------

Get list of fixed address and subnet from extcp.
**extcp** is instantiateVnfRequest > extVirtualLinks > extcps
defined in `ETSI NFV SOL003`_.

It returns the list of fixed address and subnet.


def get_param_network(cp_name, grant, req)
------------------------------------------

Get network resourceId of CP.

**cp_name**: the name of CP
, **grant**: Grants
, **req**: operationParams corresponding to API request

It returns network resourceId.


def get_param_fixed_ips(cp_name, grant, req)
--------------------------------------------

Get fixed IP addresses of CP.

**cp_name**: the name of CP
, **grant**: Grants
, **req**: operationParams corresponding to API request

It returns fixed IP address of CP.


def get_param_network_from_inst(cp_name, inst)
----------------------------------------------

Get network resourceId from VnfInstance.

**cp_name**: the name of CP
, **inst**: VnfInstance

It returns network resourceId from VnfInstance.


def get_param_fixed_ips_from_inst(cp_name, inst)
------------------------------------------------

Get fixed IP address of CP from VnfInstance.

**cp_name**: the name of CP
, **inst**: VnfInstance

It returns fixed IP address of CP from VnfInstance.


def apply_ext_managed_vls(hot_dict, req, grant)
-----------------------------------------------

Modify HOT to apply externally provided extmanaged
internal virtual link (extmanagedVL).

ExtmanagedVL is created by VNFM when instantiating VNF
or externally created and specified
by Grants or InstantiateVnfRequest.
Since one HOT can correspond to only one of the cases,
this function modifies HOT for the former case to for the latter case.

The Following shows the sample HOT description.

- Input HOT

.. code-block:: yaml

 heat_template_version: 2013-05-23
 description: 'Simple Base HOT for Sample VNF'

 resources:
   VDU1:
     type: OS::Nova::Server
     properties:
       flavor: { get_param: [ nfv, VDU, VDU2, computeFlavourId ] }
       image: { get_param: [ nfv, VDU, VDU2, vcImageId] }
       networks:
       - port:
           get_resource: VDU1_CP1

   VDU1_CP1:
     type: OS::Neutron::Port
     properties:
       network: { get_resource: internalVL1 }

   internalVL1:
     type: OS::Neutron::Net

 outputs: {}

- Output HOT

.. code-block:: yaml

 heat_template_version: 2013-05-23
 description: 'Simple Base HOT for Sample VNF'

 resources:
   VDU1:
     type: OS::Nova::Server
     properties:
       flavor: { get_param: [ nfv, VDU, VDU2, computeFlavourId ] }
       image: { get_param: [ nfv, VDU, VDU2, vcImageId] }
       networks:
       - port:
           get_resource: VDU1_CP1


   VDU1_CP1:
     type: OS::Neutron::Port
     properties:
       network: network_id

 outputs: {}


vnfd.get_base_hot(flavour_id)
------------------------------

Get HOT dict.

**flavour_id**: flavour_id of vnf instance.

It returns HOT dict with the following structure.
**dict = {'template':tophot, 'Files'{file 1:, file2:...}}**


vnf_instance_utils.json_merge_patch(target, patch)
---------------------------------------------------

Get the result of json_merge_patch (IETF RFC 7396).

**target**: merge target
, **patch**: applied patch

It returns the result of json_merge_patch (IETF RFC 7396).


.. _ETSI NFV-SOL VNF Deployment as VM with LCM Operation User Data: https://docs.openstack.org/tacker/latest/user/etsi_vnf_deployment_as_vm_with_user_data.html
.. _VNF Package manual: https://docs.openstack.org/tacker/latest/user/vnf-package.html
.. _reference of Orchestration Service API v1 "POST /v1/{tenant_id}/stacks": https://docs.openstack.org/api-ref/orchestration/v1/?expanded=create-stack-detail#create-stack
.. _reference of Orchestration Service API v1 "PATCH /v1/{tenant_id}/stacks/{stack_name}/{stack_id}": https://docs.openstack.org/api-ref/orchestration/v1/?expanded=update-stack-patch-detail#update-stack-patch
.. _Vnfd class: https://github.com/openstack/tacker/blob/master/tacker/sol_refactored/common/vnfd_utils.py#L33
.. _ETSI NFV SOL003: https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/003/03.03.01_60/gs_NFV-SOL003v030301p.pdf
