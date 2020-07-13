..
  Licensed under the Apache License, Version 2.0 (the "License"); you may
  not use this file except in compliance with the License. You may obtain
  a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
  License for the specific language governing permissions and limitations
  under the License.

.. _ref-mistral:

============================
Mistral workflows for Tacker
============================

OpenStack Mistral already integrated with Tacker. The Tenant User or Operator
can make use of tacker actions to create custom Mistral Workflows. This
document describes the usage of OpenStackClient CLI to validate, create
and executing Tacker workflows.


References
~~~~~~~~~~

- `Mistral workflow samples   <https://github.com/openstack/tacker/tree/master/samples/mistral/workflows>`_.
- `Mistral Client / CLI Guide <https://docs.openstack.org/mistral/latest/admin/install/mistralclient_guide.html>`_.

Workflow definition file validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Validate workflow definition files before registering with Mistral.

::

  usage: openstack workflow validate <definition>

::

  $ openstack workflow validate create_vnf.yaml

  +-------+-------+
  | Field | Value |
  +-------+-------+
  | Valid | True  |
  | Error | None  |
  +-------+-------+

  $ openstack workflow validate create_vnfd.yaml

  +-------+-------+
  | Field | Value |
  +-------+-------+
  | Valid | True  |
  | Error | None  |
  +-------+-------+

  $ openstack workflow validate delete_vnf.yaml

  +-------+-------+
  | Field | Value |
  +-------+-------+
  | Valid | True  |
  | Error | None  |
  +-------+-------+

  $ openstack workflow validate delete_vnfd.yaml

  +-------+-------+
  | Field | Value |
  +-------+-------+
  | Valid | True  |
  | Error | None  |
  +-------+-------+

Registering Tacker workflows with Mistral
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To create std.create_vnf, std.create_vnfd, std.delete_vnfd and
std.delete_vnf workflows in Mistral.

::

  usage: openstack workflow create <definition> --public

::

  $ openstack workflow create create_vnf.yaml --public

  +--------------------------------------+----------------+----------------------------------+--------+-------+----------------------------+------------+
  | ID                                   | Name           | Project ID                       | Tags   | Input | Created at                 | Updated at |
  +--------------------------------------+----------------+----------------------------------+--------+-------+----------------------------+------------+
  | 445e165a-3654-4996-aad4-c6fea65e95d5 | std.create_vnf | bde60e557de840a8a837733aaa96e42e | <none> | body  | 2016-07-29 15:08:45.585192 | None       |
  +--------------------------------------+----------------+----------------------------------+--------+-------+----------------------------+------------+

  $ openstack workflow create create_vnfd.yaml --public

  +--------------------------------------+-----------------+----------------------------------+--------+-------+----------------------------+------------+
  | ID                                   | Name            | Project ID                       | Tags   | Input | Created at                 | Updated at |
  +--------------------------------------+-----------------+----------------------------------+--------+-------+----------------------------+------------+
  | 926caa3e-ee59-4ca0-ac1b-cae03538e389 | std.create_vnfd | bde60e557de840a8a837733aaa96e42e | <none> | body  | 2016-07-29 15:08:54.933874 | None       |
  +--------------------------------------+-----------------+----------------------------------+--------+-------+----------------------------+------------+

  $ openstack workflow create delete_vnfd.yaml --public

  +--------------------------------------+-----------------+----------------------------------+--------+---------+----------------------------+------------+
  | ID                                   | Name            | Project ID                       | Tags   | Input   | Created at                 | Updated at |
  +--------------------------------------+-----------------+----------------------------------+--------+---------+----------------------------+------------+
  | f15b7402-ce31-4369-98d4-818125191564 | std.delete_vnfd | bde60e557de840a8a837733aaa96e42e | <none> | vnfd_id | 2016-08-14 20:01:00.135104 | None       |
  +--------------------------------------+-----------------+----------------------------------+--------+---------+----------------------------+------------+

  $ openstack workflow create delete_vnf.yaml --public
  +--------------------------------------+----------------+----------------------------------+--------+--------+----------------------------+------------+
  | ID                                   | Name           | Project ID                       | Tags   | Input  | Created at                 | Updated at |
  +--------------------------------------+----------------+----------------------------------+--------+--------+----------------------------+------------+
  | d6451b4e-6448-4a26-aa33-ac5e18c7a412 | std.delete_vnf | bde60e557de840a8a837733aaa96e42e | <none> | vnf_id | 2016-08-14 20:01:08.088654 | None       |
  +--------------------------------------+----------------+----------------------------------+--------+--------+----------------------------+------------+



VNFD resource creation with std.create_vnfd workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To create VNFD tacker resource based on the VNFD workflow input file.

Create new execution for VNFD creation.

::

  usage: openstack workflow execution create <workflow_name> [<workflow_input>] [<params>]

::

  $ openstack workflow execution create std.create_vnfd create_vnfd.json

  +-------------------+--------------------------------------+
  | Field             | Value                                |
  +-------------------+--------------------------------------+
  | ID                | 31f086aa-a3c9-4f44-b8b2-bec560e32653 |
  | Workflow ID       | 926caa3e-ee59-4ca0-ac1b-cae03538e389 |
  | Workflow name     | std.create_vnfd                      |
  | Description       |                                      |
  | Task Execution ID | <none>                               |
  | State             | RUNNING                              |
  | State info        | None                                 |
  | Created at        | 2016-07-29 15:11:19.485722           |
  | Updated at        | 2016-07-29 15:11:19.491694           |
  +-------------------+--------------------------------------+

Gather execution details based on execution id.

::

  usage: openstack workflow execution show <id>

::

  $ openstack workflow execution show 31f086aa-a3c9-4f44-b8b2-bec560e32653

  +-------------------+--------------------------------------+
  | Field             | Value                                |
  +-------------------+--------------------------------------+
  | ID                | 31f086aa-a3c9-4f44-b8b2-bec560e32653 |
  | Workflow ID       | 926caa3e-ee59-4ca0-ac1b-cae03538e389 |
  | Workflow name     | std.create_vnfd                      |
  | Description       |                                      |
  | Task Execution ID | <none>                               |
  | State             | SUCCESS                              |
  | State info        | None                                 |
  | Created at        | 2016-07-29 15:11:19                  |
  | Updated at        | 2016-07-29 15:11:21                  |
  +-------------------+--------------------------------------+

.. note:: Wait until execution state become as SUCCESS.

Gather VNFD ID from execution output data.

::

   usage: openstack workflow execution output show <id>

::

  $ openstack workflow execution output show 31f086aa-a3c9-4f44-b8b2-bec560e32653

  Response:

  {
    "vnfd_id": "fb164b77-5e24-402d-b5f4-c6596352cabe"
  }

Verify VNFD details using OpenStackClient CLI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

  $ openstack vnf descriptor show "fb164b77-5e24-402d-b5f4-c6596352cabe"

  +---------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field         | Value                                                                                                                                                                     |
  +---------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | attributes    | {"vnfd": "tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0\n\ndescription: Demo example\n\nmetadata:\n  template_name: sample-tosca-                         |
  |               | vnfd\n\ntopology_template:\n  node_templates:\n    VDU1:\n      type: tosca.nodes.nfv.VDU.Tacker\n      properties:\n        image: cirros-0.4.0-x86_64-disk\n             |
  |               | flavor: m1.tiny\n        availability_zone: nova\n        mgmt_driver: noop\n        config: |\n          param0: key1\n          param1: key2\n\n    CP1:\n      type:   |
  |               | tosca.nodes.nfv.CP.Tacker\n      properties:\n        management: true\n        anti_spoofing_protection: false\n      requirements:\n        - virtualLink:\n            |
  |               | node: VL1\n        - virtualBinding:\n            node: VDU1\n\n    CP2:\n      type: tosca.nodes.nfv.CP.Tacker\n      properties:\n        anti_spoofing_protection:     |
  |               | false\n      requirements:\n        - virtualLink:\n            node: VL2\n        - virtualBinding:\n            node: VDU1\n\n    CP3:\n      type:                     |
  |               | tosca.nodes.nfv.CP.Tacker\n      properties:\n        anti_spoofing_protection: false\n      requirements:\n        - virtualLink:\n            node: VL3\n        -      |
  |               | virtualBinding:\n            node: VDU1\n\n    VL1:\n      type: tosca.nodes.nfv.VL\n      properties:\n        network_name: net_mgmt\n        vendor: Tacker\n\n        |
  |               | VL2:\n      type: tosca.nodes.nfv.VL\n      properties:\n        network_name: net0\n        vendor: Tacker\n\n    VL3:\n      type: tosca.nodes.nfv.VL\n                 |
  |               | properties:\n        network_name: net1\n        vendor: Tacker\n"}                                                                                                       |
  | description   | Demo example                                                                                                                                                              |
  | id            | fb164b77-5e24-402d-b5f4-c6596352cabe                                                                                                                                      |
  | infra_driver  | openstack                                                                                                                                                                      |
  | mgmt_driver   | noop                                                                                                                                                                      |
  | name          | tacker-create-vnfd                                                                                                                                                        |
  | service_types | {"service_type": "vnfd", "id": "db7c5077-7bbf-4bd3-87d5-e3c52daba255"}                                                                                                    |
  | tenant_id     | bde60e557de840a8a837733aaa96e42e                                                                                                                                          |
  +---------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

VNF resource creation with std.create_vnf workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Update the vnfd_id from the output of above execution in create_vnf.json

Create new execution for VNF creation.

::

  $ openstack workflow execution create std.create_vnf create_vnf.json

  +-------------------+--------------------------------------+
  | Field             | Value                                |
  +-------------------+--------------------------------------+
  | ID                | 3bf2051b-ac2e-433b-8f18-23f57f32f184 |
  | Workflow ID       | 445e165a-3654-4996-aad4-c6fea65e95d5 |
  | Workflow name     | std.create_vnf                       |
  | Description       |                                      |
  | Task Execution ID | <none>                               |
  | State             | RUNNING                              |
  | State info        | None                                 |
  | Created at        | 2016-07-29 15:16:13.066555           |
  | Updated at        | 2016-07-29 15:16:13.072436           |
  +-------------------+--------------------------------------+

Gather execution details based on execution id.

::

  $ openstack workflow execution show 3bf2051b-ac2e-433b-8f18-23f57f32f184

  +-------------------+--------------------------------------+
  | Field             | Value                                |
  +-------------------+--------------------------------------+
  | ID                | 3bf2051b-ac2e-433b-8f18-23f57f32f184 |
  | Workflow ID       | 445e165a-3654-4996-aad4-c6fea65e95d5 |
  | Workflow name     | std.create_vnf                       |
  | Description       |                                      |
  | Task Execution ID | <none>                               |
  | State             | SUCCESS                              |
  | State info        | None                                 |
  | Created at        | 2016-07-29 15:16:13                  |
  | Updated at        | 2016-07-29 15:16:45                  |
  +-------------------+--------------------------------------+

Gather VNF ID from execution output data.

::

  $ openstack workflow execution output show 3bf2051b-ac2e-433b-8f18-23f57f32f184

  Response:

  {
    "status": "ACTIVE",
    "mgmt_ip_address": "{\"VDU1\": \"192.168.120.7\"}",
    "vim_id": "22ac5ce6-1415-460c-badf-40ffc5091f94",
    "vnf_id": "1c349534-a539-4d5a-b854-033f98036cd5"
  }

Verify VNF details using OpenStackClient CLI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
::

  $ openstack vnf show "1c349534-a539-4d5a-b854-033f98036cd5"

  +----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field          | Value                                                                                                                                                                 |
  +----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | attributes     | {"heat_template": "heat_template_version: 2013-05-23\ndescription: 'Demo example\n\n  '\nparameters: {}\nresources:\n  VDU1:\n    type: OS::Nova::Server\n            |
  |                | properties:\n      availability_zone: nova\n      config_drive: false\n      flavor: m1.tiny\n      image: cirros-0.4.0-x86_64-disk\n      networks:\n      - port:\n  |
  |                | get_resource: CP1\n      - port:\n          get_resource: CP2\n      - port:\n          get_resource: CP3\n      user_data_format: SOFTWARE_CONFIG\n  CP1:\n    type: |
  |                | OS::Neutron::Port\n    properties:\n      network: net_mgmt\n      port_security_enabled: false\n  CP2:\n    type: OS::Neutron::Port\n    properties:\n      network: |
  |                | net0\n      port_security_enabled: false\n  CP3:\n    type: OS::Neutron::Port\n    properties:\n      network: net1\n      port_security_enabled: false\noutputs:\n   |
  |                | mgmt_ip-VDU1:\n    value:\n      get_attr: [CP1, fixed_ips, 0, ip_address]\n", "monitoring_policy": "{\"vdus\": {}}"}                                                 |
  | description    | Demo example                                                                                                                                                          |
  | error_reason   |                                                                                                                                                                       |
  | id             | 1c349534-a539-4d5a-b854-033f98036cd5                                                                                                                                  |
  | instance_id    | 771c53df-9f41-454c-a719-7eccd3a4eba9                                                                                                                                  |
  | mgmt_ip_address| {"VDU1": "192.168.120.7"}                                                                                                                                             |
  | name           | tacker-create-vnf                                                                                                                                                     |
  | placement_attr | {"vim_name": "VIM0"}                                                                                                                                                  |
  | status         | ACTIVE                                                                                                                                                                |
  | tenant_id      | bde60e557de840a8a837733aaa96e42e                                                                                                                                      |
  | vim_id         | 22ac5ce6-1415-460c-badf-40ffc5091f94                                                                                                                                  |
  +----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------+

VNF resource deletion with std.delete_vnf workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Update the vnf_id from the output of above execution in delete_vnf.json

Create new execution for VNF deletion.

::

  $ openstack workflow execution create std.delete_vnf delete_vnf.json

  +-------------------+--------------------------------------+
  | Field             | Value                                |
  +-------------------+--------------------------------------+
  | ID                | 677c7bab-18ee-4a34-b1e6-a305e98ba887 |
  | Workflow ID       | d6451b4e-6448-4a26-aa33-ac5e18c7a412 |
  | Workflow name     | std.delete_vnf                       |
  | Description       |                                      |
  | Task Execution ID | <none>                               |
  | State             | RUNNING                              |
  | State info        | None                                 |
  | Created at        | 2016-08-14 20:48:00.333116           |
  | Updated at        | 2016-08-14 20:48:00.340124           |
  +-------------------+--------------------------------------+

Gather execution details based on execution id.

::

  $ openstack workflow execution show 677c7bab-18ee-4a34-b1e6-a305e98ba887

  +-------------------+--------------------------------------+
  | Field             | Value                                |
  +-------------------+--------------------------------------+
  | ID                | 677c7bab-18ee-4a34-b1e6-a305e98ba887 |
  | Workflow ID       | d6451b4e-6448-4a26-aa33-ac5e18c7a412 |
  | Workflow name     | std.delete_vnf                       |
  | Description       |                                      |
  | Task Execution ID | <none>                               |
  | State             | SUCCESS                              |
  | State info        | None                                 |
  | Created at        | 2016-08-14 20:48:00                  |
  | Updated at        | 2016-08-14 20:48:03                  |
  +-------------------+--------------------------------------+


Gather execution output data from execution id.

::

  $ openstack workflow execution output show 677c7bab-18ee-4a34-b1e6-a305e98ba887

  Response:

  {
    "openstack": {
        "project_name": "demo",
        "user_id": "f39a28fa574848dfa950b50329c1309b",
        "roles": [
            "anotherrole",
            "Member"
        ],
        "www_authenticate_uri": "http://192.168.122.250:5000/v3",
        "auth_cacert": null,
        "auth_token": "2871049fae3643ca84f44f7e17f809a0",
        "is_trust_scoped": false,
        "service_catalog": "[{\"endpoints\": [{\"adminURL\": \"http://192.168.122.250/identity_v2_admin\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250/identity\", \"publicURL\": \"http://192.168.122.250/identity\"}], \"type\": \"identity\", \"name\": \"keystone\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:9292\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:9292\", \"publicURL\": \"http://192.168.122.250:9292\"}], \"type\": \"image\", \"name\": \"glance\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8774/v2.1\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8774/v2.1\", \"publicURL\": \"http://192.168.122.250:8774/v2.1\"}], \"type\": \"compute\", \"name\": \"nova\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8776/v2/bde60e557de840a8a837733aaa96e42e\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8776/v2/bde60e557de840a8a837733aaa96e42e\", \"publicURL\": \"http://192.168.122.250:8776/v2/bde60e557de840a8a837733aaa96e42e\"}], \"type\": \"volumev2\", \"name\": \"cinderv2\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8776/v1/bde60e557de840a8a837733aaa96e42e\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8776/v1/bde60e557de840a8a837733aaa96e42e\", \"publicURL\": \"http://192.168.122.250:8776/v1/bde60e557de840a8a837733aaa96e42e\"}], \"type\": \"volume\", \"name\": \"cinder\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:9494\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:9494\", \"publicURL\": \"http://192.168.122.250:9494\"}], \"type\": \"artifact\", \"name\": \"glare\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8004/v1/bde60e557de840a8a837733aaa96e42e\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8004/v1/bde60e557de840a8a837733aaa96e42e\", \"publicURL\": \"http://192.168.122.250:8004/v1/bde60e557de840a8a837733aaa96e42e\"}], \"type\": \"orchestration\", \"name\": \"heat\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8774/v2/bde60e557de840a8a837733aaa96e42e\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8774/v2/bde60e557de840a8a837733aaa96e42e\", \"publicURL\": \"http://192.168.122.250:8774/v2/bde60e557de840a8a837733aaa96e42e\"}], \"type\": \"compute_legacy\", \"name\": \"nova_legacy\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:9890/\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:9890/\", \"publicURL\": \"http://192.168.122.250:9890/\"}], \"type\": \"nfv-orchestration\", \"name\": \"tacker\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8989/v2\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8989/v2\", \"publicURL\": \"http://192.168.122.250:8989/v2\"}], \"type\": \"workflowv2\", \"name\": \"mistral\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:9696/\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:9696/\", \"publicURL\": \"http://192.168.122.250:9696/\"}], \"type\": \"network\", \"name\": \"neutron\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8776/v3/bde60e557de840a8a837733aaa96e42e\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8776/v3/bde60e557de840a8a837733aaa96e42e\", \"publicURL\": \"http://192.168.122.250:8776/v3/bde60e557de840a8a837733aaa96e42e\"}], \"type\": \"volumev3\", \"name\": \"cinderv3\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8082\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8082\", \"publicURL\": \"http://192.168.122.250:8082\"}], \"type\": \"application-catalog\", \"name\": \"murano\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8779/v1.0/bde60e557de840a8a837733aaa96e42e\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8779/v1.0/bde60e557de840a8a837733aaa96e42e\", \"publicURL\": \"http://192.168.122.250:8779/v1.0/bde60e557de840a8a837733aaa96e42e\"}], \"type\": \"database\", \"name\": \"trove\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8000/v1\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8000/v1\", \"publicURL\": \"http://192.168.122.250:8000/v1\"}], \"type\": \"cloudformation\", \"name\": \"heat-cfn\"}]",
        "project_id": "bde60e557de840a8a837733aaa96e42e",
        "user_name": "demo"
    },
    "vnf_id": "f467e215-43a3-4083-8bbb-ce49d9c70443",
    "__env": {},
    "__execution": {
        "input": {
            "vnf_id": "f467e215-43a3-4083-8bbb-ce49d9c70443"
        },
        "params": {},
        "id": "677c7bab-18ee-4a34-b1e6-a305e98ba887",
        "spec": {
            "tasks": {
                "delete_vnf": {
                    "action": "tacker.delete_vnf vnf=<% $.vnf_id %>",
                    "version": "2.0",
                    "type": "direct",
                    "description": "Request to delete a VNF.",
                    "name": "delete_vnf"
                }
            },
            "description": "Delete a VNF.\n",
            "version": "2.0",
            "input": [
                "vnf_id"
            ],
            "type": "direct",
            "name": "std.delete_vnf"
        }
      }
  }


VNFD resource deletion with std.delete_vnfd workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Update the vnfd_id from the output of above execution in delete_vnfd.json

Create new execution for VNF deletion.

::

  $ openstack workflow execution create std.delete_vnfd delete_vnfd.json

  +-------------------+--------------------------------------+
  | Field             | Value                                |
  +-------------------+--------------------------------------+
  | ID                | 1e0340c0-bee8-4ca4-8150-ac6e5eb58c99 |
  | Workflow ID       | f15b7402-ce31-4369-98d4-818125191564 |
  | Workflow name     | std.delete_vnfd                      |
  | Description       |                                      |
  | Task Execution ID | <none>                               |
  | State             | RUNNING                              |
  | State info        | None                                 |
  | Created at        | 2016-08-14 20:57:06.500941           |
  | Updated at        | 2016-08-14 20:57:06.505780           |
  +-------------------+--------------------------------------+

Gather execution details based on execution id.

::

  $ openstack workflow execution show 1e0340c0-bee8-4ca4-8150-ac6e5eb58c99

  +-------------------+--------------------------------------+
  | Field             | Value                                |
  +-------------------+--------------------------------------+
  | ID                | 1e0340c0-bee8-4ca4-8150-ac6e5eb58c99 |
  | Workflow ID       | f15b7402-ce31-4369-98d4-818125191564 |
  | Workflow name     | std.delete_vnfd                      |
  | Description       |                                      |
  | Task Execution ID | <none>                               |
  | State             | SUCCESS                              |
  | State info        | None                                 |
  | Created at        | 2016-08-14 20:57:06                  |
  | Updated at        | 2016-08-14 20:57:07                  |
  +-------------------+--------------------------------------+



Gather execution output data from execution id.

::

  $ openstack workflow execution output show 1e0340c0-bee8-4ca4-8150-ac6e5eb58c99

  Response:

  {
    "openstack": {
        "project_name": "demo",
        "user_id": "f39a28fa574848dfa950b50329c1309b",
        "roles": [
            "anotherrole",
            "Member"
        ],
        "www_authenticate_uri": "http://192.168.122.250:5000/v3",
        "auth_cacert": null,
        "auth_token": "176c9b5ebd9d40fb9fb0a8db921609eb",
        "is_trust_scoped": false,
        "service_catalog": "[{\"endpoints\": [{\"adminURL\": \"http://192.168.122.250/identity_v2_admin\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250/identity\", \"publicURL\": \"http://192.168.122.250/identity\"}], \"type\": \"identity\", \"name\": \"keystone\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:9292\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:9292\", \"publicURL\": \"http://192.168.122.250:9292\"}], \"type\": \"image\", \"name\": \"glance\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8774/v2.1\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8774/v2.1\", \"publicURL\": \"http://192.168.122.250:8774/v2.1\"}], \"type\": \"compute\", \"name\": \"nova\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8776/v2/bde60e557de840a8a837733aaa96e42e\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8776/v2/bde60e557de840a8a837733aaa96e42e\", \"publicURL\": \"http://192.168.122.250:8776/v2/bde60e557de840a8a837733aaa96e42e\"}], \"type\": \"volumev2\", \"name\": \"cinderv2\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8776/v1/bde60e557de840a8a837733aaa96e42e\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8776/v1/bde60e557de840a8a837733aaa96e42e\", \"publicURL\": \"http://192.168.122.250:8776/v1/bde60e557de840a8a837733aaa96e42e\"}], \"type\": \"volume\", \"name\": \"cinder\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:9494\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:9494\", \"publicURL\": \"http://192.168.122.250:9494\"}], \"type\": \"artifact\", \"name\": \"glare\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8004/v1/bde60e557de840a8a837733aaa96e42e\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8004/v1/bde60e557de840a8a837733aaa96e42e\", \"publicURL\": \"http://192.168.122.250:8004/v1/bde60e557de840a8a837733aaa96e42e\"}], \"type\": \"orchestration\", \"name\": \"heat\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8774/v2/bde60e557de840a8a837733aaa96e42e\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8774/v2/bde60e557de840a8a837733aaa96e42e\", \"publicURL\": \"http://192.168.122.250:8774/v2/bde60e557de840a8a837733aaa96e42e\"}], \"type\": \"compute_legacy\", \"name\": \"nova_legacy\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:9890/\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:9890/\", \"publicURL\": \"http://192.168.122.250:9890/\"}], \"type\": \"nfv-orchestration\", \"name\": \"tacker\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8989/v2\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8989/v2\", \"publicURL\": \"http://192.168.122.250:8989/v2\"}], \"type\": \"workflowv2\", \"name\": \"mistral\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:9696/\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:9696/\", \"publicURL\": \"http://192.168.122.250:9696/\"}], \"type\": \"network\", \"name\": \"neutron\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8776/v3/bde60e557de840a8a837733aaa96e42e\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8776/v3/bde60e557de840a8a837733aaa96e42e\", \"publicURL\": \"http://192.168.122.250:8776/v3/bde60e557de840a8a837733aaa96e42e\"}], \"type\": \"volumev3\", \"name\": \"cinderv3\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8082\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8082\", \"publicURL\": \"http://192.168.122.250:8082\"}], \"type\": \"application-catalog\", \"name\": \"murano\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8779/v1.0/bde60e557de840a8a837733aaa96e42e\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8779/v1.0/bde60e557de840a8a837733aaa96e42e\", \"publicURL\": \"http://192.168.122.250:8779/v1.0/bde60e557de840a8a837733aaa96e42e\"}], \"type\": \"database\", \"name\": \"trove\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.122.250:8000/v1\", \"region\": \"RegionOne\", \"internalURL\": \"http://192.168.122.250:8000/v1\", \"publicURL\": \"http://192.168.122.250:8000/v1\"}], \"type\": \"cloudformation\", \"name\": \"heat-cfn\"}]",
        "project_id": "bde60e557de840a8a837733aaa96e42e",
        "user_name": "demo"
      },
      "vnfd_id": "fb164b77-5e24-402d-b5f4-c6596352cabe",
      "__env": {},
      "__execution": {
        "input": {
            "vnfd_id": "fb164b77-5e24-402d-b5f4-c6596352cabe"
        },
        "params": {},
        "id": "1e0340c0-bee8-4ca4-8150-ac6e5eb58c99",
        "spec": {
            "tasks": {
                "delete_vnfd": {
                    "action": "tacker.delete_vnfd vnfd=<% $.vnfd_id %>",
                    "version": "2.0",
                    "type": "direct",
                    "description": "Request to delete a VNFD.",
                    "name": "delete_vnfd"
                }
            },
            "description": "Delete a VNFD.\n",
            "version": "2.0",
            "input": [
                "vnfd_id"
            ],
            "type": "direct",
            "name": "std.delete_vnfd"
          }
      }
  }
