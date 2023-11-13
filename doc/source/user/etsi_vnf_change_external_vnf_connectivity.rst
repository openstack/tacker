=============================================
ETSI NFV-SOL Change External VNF Connectivity
=============================================

This document describes how to change external VNF connectivity
in Tacker v1 API.

.. note::

  This is a document for Tacker v1 API.
  See :doc:`/user/v2/vnf/chg_ext_conn` for Tacker v2 API.


Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

A default VIM should be registered according to
:doc:`/cli/cli-legacy-vim`.

The VNF Package(sample_vnf_package_csar.zip) used below is prepared
by referring to :doc:`/user/vnf-package`.

The procedure of prepare for scaling operation that from "register VIM" to
"Instantiate VNF", basically refer to
:doc:`/user/etsi_vnf_deployment_as_vm_with_user_data`.

This procedure uses an example using the sample VNF package.


Change External VNF Connectivity
--------------------------------

As mentioned in Prerequisites, the VNF must be created
before performing change external connectivity.

Assuming that the following VNF instance exists,
this instance will be changed.

Details of CLI commands are described in
:doc:`/cli/cli-etsi-vnflcm`.

For changing external VNF connectivity, you need to prepare a JSON-formatted
definition file before running command for changing the connectivity.


.. code-block:: json

  {
      "extVirtualLinks": [
          {
              "id": "a96d2f5b-c01a-48e1-813c-76132965042c",
              "resourceId": "3019b1e7-99d8-4748-97ac-104922bc78d9",
              "vimConnectionId": "79a97d01-e5f3-4eaa-b2bc-8f513ecb8a56",
              "extCps": [
                  {
                      "cpdId": "VDU1_CP2",
                      "cpConfig": [
                          {
                              "cpProtocolData": [
                                  {
                                      "layerProtocol": "IP_OVER_ETHERNET",
                                      "ipOverEthernet": {
                                          "ipAddresses": [
                                              {
                                                  "type": "IPV4",
                                                  "subnetId": "43c8f5fa-fefd-4bd4-a0df-f985b6969339"
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
              "id": "79a97d01-e5f3-4eaa-b2bc-8f513ecb8a56",
              "vimType": "ETSINFV.OPENSTACK_KEYSTONE.v_2",
              "vimConnectionId": "79a97d01-e5f3-4eaa-b2bc-8f513ecb8a56",
              "interfaceInfo": {
                  "endpoint": "http://127.0.0.1/identity"
              },
              "accessInfo": {
                  "username": "nfv_user",
                  "region": "RegionOne",
                  "password": "devstack",
                  "tenant": "1994d69783d64c00aadab564038c2fd7"
              }
          }
      ],
      "additionalParams": {
          "lcm-operation-user-data": "./UserData/lcm_user_data.py",
          "lcm-operation-user-data-class": "SampleUserData"
      }
  }


.. note::

  sample_param_file.json contains all the data of port resource information.
  If no setting is contained, it is treated as a change in information.


.. note::

  The change external VNF Connectivity operation can change the
  ``vimConnectionInfo`` associated with an existing VNF instance.
  Even if change external VNF Connectivity operation specify multiple
  ``vimConnectionInfo`` associated with one VNF instance, only one of
  them will be used for life cycle management operations.
  It is not possible to delete the key of registered ``vimConnectionInfo``.


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


Port information before operation:

.. code-block:: console

  $ openstack port list --name PORT_NAME
  +--------------------------------------+-------------------------------------------------------------------------------------------+-------------------+---------------------------------------------------------------------------+--------+
  | ID                                   | Name                                                                                      | MAC Address       | Fixed IP Addresses                                                        | Status |
  +--------------------------------------+-------------------------------------------------------------------------------------------+-------------------+---------------------------------------------------------------------------+--------+
  | 0988d9dc-97ba-43be-944d-185e316785f9 | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a-VDU1_scale-3x6qwnzbj6ep-                      | fa:16:3e:fb:f9:87 | ip_address='22.22.1.16', subnet_id='d290cae3-0dbc-44a3-a043-1a50ded04a64' | ACTIVE |
  |                                      | gfrxqjt6nfqb-2ufs4pbsedui-VDU1_CP2-riva4ygcbnyz                                           |                   |                                                                           |        |
  +--------------------------------------+-------------------------------------------------------------------------------------------+-------------------+---------------------------------------------------------------------------+--------+

  $ openstack stack resource list e9d4576f-950c-4076-a54d-35b5cf43ebdd -n 2 --filter name=VDU1_CP2
  +---------------+--------------------------------------+-------------------+-----------------+----------------------+-----------------------------------------------------------------------------------------------+
  | resource_name | physical_resource_id                 | resource_type     | resource_status | updated_time         | stack_name                                                                                    |
  +---------------+--------------------------------------+-------------------+-----------------+----------------------+-----------------------------------------------------------------------------------------------+
  | VDU1_CP2      | 0988d9dc-97ba-43be-944d-185e316785f9 | OS::Neutron::Port | CREATE_COMPLETE | 2023-12-28T02:32:04Z | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a-VDU1_scale-3x6qwnzbj6ep-gfrxqjt6nfqb-2ufs4pbsedui |
  +---------------+--------------------------------------+-------------------+-----------------+----------------------+-----------------------------------------------------------------------------------------------+
  $ openstack stack resource show \
    vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a-VDU1_scale-3x6qwnzbj6ep-gfrxqjt6nfqb-2ufs4pbsedui \
    VDU1_CP2 -f json | jq .attributes.fixed_ips
  [
    {
      "subnet_id": "d290cae3-0dbc-44a3-a043-1a50ded04a64",
      "ip_address": "22.22.1.16"
    }
  ]


See `Heat CLI reference`_ for details on Heat CLI commands.

Change External VNF Connectivity execution of the entire VNF:

.. code-block:: console

  $ openstack vnflcm change-ext-conn VNF_INSTANCE_ID \
    ./sample_param_file.json


Result:

.. code-block:: console

  Change External VNF Connectivity for VNF Instance 0c3644ff-b207-4a6a-9d3a-d1295cda153a has been accepted.


.. note::

  Create a parameter file that describes the resource information to be changed in advance.


Stack information after operation:

.. code-block:: console

  $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'


Result:

.. code-block:: console

  +--------------------------------------+---------------------------------------------+-----------------+
  | ID                                   | Stack Name                                  | Stack Status    |
  +--------------------------------------+---------------------------------------------+-----------------+
  | e9d4576f-950c-4076-a54d-35b5cf43ebdd | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a | UPDATE_COMPLETE |
  +--------------------------------------+---------------------------------------------+-----------------+


.. note::

  'Stack Status' transitions to UPDATE_COMPLETE.


Stack resource information:

.. code-block:: console

  $ openstack stack resource list e9d4576f-950c-4076-a54d-35b5cf43ebdd \
    -n 2 --filter name=VDU1


Result:

.. code-block:: console

  +---------------+--------------------------------------+------------------+-----------------+----------------------+-----------------------------------------------------------------------------------------------+
  | resource_name | physical_resource_id                 | resource_type    | resource_status | updated_time         | stack_name                                                                                    |
  +---------------+--------------------------------------+------------------+-----------------+----------------------+-----------------------------------------------------------------------------------------------+
  | VDU1          | f32848eb-598f-4158-8896-5ea9479456de | OS::Nova::Server | UPDATE_COMPLETE | 2023-12-28T07:12:36Z | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a-VDU1_scale-3x6qwnzbj6ep-gfrxqjt6nfqb-2ufs4pbsedui |
  +---------------+--------------------------------------+------------------+-----------------+----------------------+-----------------------------------------------------------------------------------------------+


Port resource information:

.. code-block:: console

  $ openstack port list --name PORT_NAME
  +--------------------------------------+-------------------------------------------------------------------------------------------+-------------------+----------------------------------------------------------------------------+--------+
  | ID                                   | Name                                                                                      | MAC Address       | Fixed IP Addresses                                                         | Status |
  +--------------------------------------+-------------------------------------------------------------------------------------------+-------------------+----------------------------------------------------------------------------+--------+
  | 8fcc7ddf-45cb-4ff6-a17f-4b18b9ab6a63 | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a-VDU1_scale-3x6qwnzbj6ep-                      | fa:16:3e:75:50:e8 | ip_address='10.10.0.136', subnet_id='43c8f5fa-fefd-4bd4-a0df-f985b6969339' | ACTIVE |
  |                                      | gfrxqjt6nfqb-2ufs4pbsedui-VDU1_CP2-gy4cxuefplkg                                           |                   |                                                                            |        |
  +--------------------------------------+-------------------------------------------------------------------------------------------+-------------------+----------------------------------------------------------------------------+--------+

  $ openstack stack resource list e9d4576f-950c-4076-a54d-35b5cf43ebdd -n 2 --filter name=VDU1_CP2
  +---------------+--------------------------------------+-------------------+-----------------+----------------------+-----------------------------------------------------------------------------------------------+
  | resource_name | physical_resource_id                 | resource_type     | resource_status | updated_time         | stack_name                                                                                    |
  +---------------+--------------------------------------+-------------------+-----------------+----------------------+-----------------------------------------------------------------------------------------------+
  | VDU1_CP2      | 8fcc7ddf-45cb-4ff6-a17f-4b18b9ab6a63 | OS::Neutron::Port | CREATE_COMPLETE | 2023-12-28T07:12:35Z | vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a-VDU1_scale-3x6qwnzbj6ep-gfrxqjt6nfqb-2ufs4pbsedui |
  +---------------+--------------------------------------+-------------------+-----------------+----------------------+-----------------------------------------------------------------------------------------------+
  $ openstack stack resource show \
    vnflcm_0c3644ff-b207-4a6a-9d3a-d1295cda153a-VDU1_scale-3x6qwnzbj6ep-gfrxqjt6nfqb-2ufs4pbsedui \
    VDU1_CP2 -f json | jq .attributes.fixed_ips
  [
    {
      "subnet_id": "43c8f5fa-fefd-4bd4-a0df-f985b6969339",
      "ip_address": "10.10.0.136"
    }
  ]


.. note::

  'subnet_id' has been changed from 'd290cae3-0dbc-44a3-a043-1a50ded04a64'
  to '43c8f5fa-fefd-4bd4-a0df-f985b6969339'.
  'ip_address' has been changed from '22.22.1.16' to '10.10.0.136'.


.. _NFV-SOL002 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/002/02.06.01_60/gs_NFV-SOL002v020601p.pdf
.. _Heat CLI reference : https://docs.openstack.org/python-openstackclient/latest/cli/plugin-commands/heat.html
