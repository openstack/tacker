=============================================
ETSI NFV-SOL Change External VNF Connectivity
=============================================

This document describes how to change external VNF connectivity in Tacker.

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

A default VIM should be registered according to
:doc:`../cli/cli-legacy-vim`.

The VNF Package(sample_vnf_pkg.zip) used below is prepared
by referring to :doc:`./vnf-package`.

Execute before "Terminate VNF" in the procedure of
:doc:`./etsi_vnf_deployment_as_vm_with_tosca`.


Change External VNF Connectivity
--------------------------------

As mentioned in Prerequisites, the VNF must be created
before performing change external connectivity.

Assuming that the following VNF instance exists,
this instance will be changed.

Details of CLI commands are described in
:doc:`../cli/cli-etsi-vnflcm`.

For changing external VNF connectivity, you need to prepare a JSON-formatted
definition file before running command for changing the connectivity.


.. code-block:: json

  {
    "extVirtualLinks": [
      {
        "id": "ce38f1e7-4aec-4325-bb78-9c4411f113b5",
        "resourceId": "1a4054c8-dd6b-444b-9604-7a8fc8c1cc0c",
        "extCps": [
          {
            "cpdId": "VDU2_CP2",
            "cpConfig": [
              {
                "cpProtocolData": [
                  {
                    "layerProtocol": "IP_OVER_ETHERNET",
                    "ipOverEthernet":
                      {
                        "ipAddresses": [
                          {
                            "type": "IPV4",
                            "fixedAddresses": ["22.22.2.200"],
                            "subnetId": "25f4a13f-0c20-4fff-85aa-5349fc4efee8"
                          }
                        ]
                      }
                  }
                ]
              }
            ]
          }
        ]
      }
    ],
    "vimConnectionInfo": [
      {
        "id": "4405b1a4-d967-4f72-9bd5-12f2852bd56b",
        "vimType": "ETSINFV.OPENSTACK_KEYSTONE.v_2",
        "vimConnectionId": "4405b1a4-d967-4f72-9bd5-12f2852bd56b",
        "interfaceInfo":
          {
            "endpoint": "http://127.0.0.1/identity"
          },
        "accessInfo":
          {
            "username": "nfv_user",
            "region": "RegionOne",
            "password": "devstack",
            "tenant": "6bdc3a89b3ee4cef9ff1676a22ae7f3b"
          }
      }
    ]
  }

.. note:: sample_param_file.json contains all the data of port resource information.
          if no setting is contained, it is treated as a change in information.


How to Change the Specific Port Setting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute Change External VNF Connectivity CLI command and check 'ID' and
'Stack Status' of the stack before and after operation.
This is to confirm that stack 'ID' has no change before and after operation,
and that the Stack update has been completed successfully.
See `Heat CLI reference`_. for details on Heat CLI commands.

Stack information before operation:

.. code-block:: console

  $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'


Result:

.. code-block:: console

  +--------------------------------------+------------------------------------------+-----------------+
  | ID                                   | Stack Name                               | Stack Status    |
  +--------------------------------------+------------------------------------------+-----------------+
  | 5322e9c4-b5ac-439e-8ed4-d0710816f318 | vnf-9e086f34-b3c9-4986-b5e5-609a5ac4c1f9 | CREATE_COMPLETE |
  +--------------------------------------+------------------------------------------+-----------------+


Change External VNF Connectivity execution of the entire VNF:

.. code-block:: console

  $ openstack vnflcm change_ext_conn VNF_INSTANCE_ID \
       ./sample_param_file.json


Result:

.. code-block:: console

  Change External VNF Connectivity for VNF Instance 725f625e-f6b7-4bcd-b1b7-7184039fde45 has been accepted.

.. note::
  Create a parameter file that describes the resource information to be changed in advance.


Stack information after operation:

.. code-block:: console

  $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'


Result:

.. code-block:: console

  +--------------------------------------+------------------------------------------+-----------------+
  | ID                                   | Stack Name                               | Stack Status    |
  +--------------------------------------+------------------------------------------+-----------------+
  | ad077101-b093-4785-9ca5-cc7c1379bb10 | vnf-9e086f34-b3c9-4986-b5e5-609a5ac4c1f9 | UPDATE_COMPLETE |
  +--------------------------------------+------------------------------------------+-----------------+

.. note::
       'Stack Status' transitions to UPDATE_COMPLETE.


Stack resource information:

.. code-block:: console

  $ openstack stack resource list ad077101-b093-4785-9ca5-cc7c1379bb10 -n 2


Result:

.. code-block:: console

  +----------------------+--------------------------------------+----------------------------+-----------------+----------------------+-----------------------------------------------------------------------------------------------------+
  | resource_name        | physical_resource_id                 | resource_type              | resource_status | updated_time         | stack_name                                                                                          |
  +----------------------+--------------------------------------+----------------------------+-----------------+----------------------+-----------------------------------------------------------------------------------------------------+
  | 6mvcg7rftabt         | 29f94441-bc14-4342-92f3-01eed02babb1 | VDU1.yaml                  | UPDATE_COMPLETE | 2021-03-25T06:02:42Z | vnflcm_8f054b70-93e9-46d5-a3bb-6404b99f91fb-VDU1_scale_group-gjwwa6637ur2                           |
  | ijarluromf6z         | 42b84c3e-c017-4386-9dfa-f366bef5f42b | VDU2.yaml                  | UPDATE_COMPLETE | 2021-03-25T06:03:23Z | vnflcm_8f054b70-93e9-46d5-a3bb-6404b99f91fb-VDU2_scale_group-kjap6b2asrne                           |
  | xmexppdgpb3d         | 2a534d04-2f6a-4dd8-ba05-d79e0ced46e8 | VDU2.yaml                  | UPDATE_COMPLETE | 2021-03-25T06:03:24Z | vnflcm_8f054b70-93e9-46d5-a3bb-6404b99f91fb-VDU2_scale_group-kjap6b2asrne                           |
  +----------------------+--------------------------------------+----------------------------+-----------------+----------------------+-----------------------------------------------------------------------------------------------------+


Stack resource detailed information:

.. code-block:: console

  $ openstack stack resource show 42b84c3e-c017-4386-9dfa-f366bef5f42b VDU2_CP2 --fit-width


Result:

.. code-block:: console

  +------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field                  | Value                                                                                                                                                                                                            |
  +------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | attributes             | {'id': '958d4fd4-f579-4936-8898-04b6ec521a56', 'name': 'vnflcm_8f054b70-93e9-46d5-a3bb-6404b99f91fb-VDU2_scale_group-kjap6b2asrne-ijarluromf6z-zci6ve7ul27n-VDU2_CP2-i2k7w5mbvt7h', 'network_id':                |
  |                        | 'b6cd5128-4dd8-4564-89b4-879db6e12ada', 'tenant_id': 'f76fec29816c470e92c9d88c529802b9', 'mac_address': 'fa:16:3e:f1:c9:93', 'admin_state_up': True, 'status': 'ACTIVE', 'device_id': '0edf0aa8-be46-41af-       |
  |                        | abd6-6ba8440f1247', 'device_owner': 'compute:nova', 'fixed_ips': [{'subnet_id': '25f4a13f-0c20-4fff-85aa-5349fc4efee8', 'ip_address': '22.22.2.200'}], 'allowed_address_pairs': [], 'extra_dhcp_opts': [],       |
  |                        | 'security_groups': ['20f992ca-ad73-4d41-a503-0ad5866f6a84'], 'description': '', 'binding:vnic_type': 'normal', 'binding:profile': {}, 'binding:host_id': 'tackerhost', 'binding:vif_type': 'ovs',          |
  |                        | 'binding:vif_details': {'connectivity': 'l2', 'port_filter': True, 'ovs_hybrid_plug': False, 'datapath_type': 'system', 'bridge_name': 'tacker_bridge'}, 'port_security_enabled': True, 'qos_policy_id': None,          |
  |                        | 'qos_network_policy_id': None, 'resource_request': None, 'tags': [], 'created_at': '2021-04-12T00:05:00Z', 'updated_at': '2021-04-12T00:10:00Z', 'revision_number': 4, 'project_id':                             |
  |                        | 'f76fec29816c470e92c9d88c529802b9'}                                                                                                                                                                              |
  +------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

.. note:: you can check "fixed_ips" in attributes field.


Another way to check is by using "openstack port" command.

.. code-block:: console

  $ openstack port list --sort-column Name --fit-width


Result:

.. code-block:: console

  +--------------------------------------+-----------------------------------------------------------------------------------+-------------------+-----------------------------------------------------------------------------------+--------+
  | ID                                   | Name                                                                              | MAC Address       | Fixed IP Addresses                                                                | Status |
  +--------------------------------------+-----------------------------------------------------------------------------------+-------------------+-----------------------------------------------------------------------------------+--------+
  | 958d4fd4-f579-4936-8898-04b6ec521a56 | vnflcm_8f054b70-93e9-46d5-a3bb-6404b99f91fb-VDU2_scale_group-kjap6b2asrne-        | fa:16:3e:f1:c9:93 | ip_address='22.22.2.200', subnet_id='25f4a13f-0c20-4fff-85aa-5349fc4efee8'        | ACTIVE |
  |                                      | ijarluromf6z-zci6ve7ul27n-VDU2_CP2-i2k7w5mbvt7h                                   |                   |                                                                                   |        |
  +--------------------------------------+-----------------------------------------------------------------------------------+-------------------+-----------------------------------------------------------------------------------+--------+


See `Heat CLI reference`_. for details on Heat CLI commands.


.. _NFV-SOL002 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/002/02.06.01_60/gs_NFV-SOL002v020601p.pdf
.. _Change External VNF Connectivity API reference : https://docs.openstack.org/api-ref/orchestration/v1/index.html
.. _Heat CLI reference : https://docs.openstack.org/python-openstackclient/latest/cli/plugin-commands/heat.html
