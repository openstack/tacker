==============
VNF Management
==============

.. TODO(yoshito-ito): add the other patterns of update.

This document describes how to manage VNF with CLI in Tacker.

Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

A default VIM should be registered according to :doc:`./cli-legacy-vim`.

CLI reference for VNF Management
--------------------------------

1. Create VNF
^^^^^^^^^^^^^

Create ``tosca-vnfd-scale.yaml`` file:

* https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnfd/tosca-vnfd-scale.yaml


Create a VNFD:

.. code-block:: console

  $ openstack vnf descriptor create --vnfd-file \
      tosca-vnfd-scale.yaml <VNFD: tosca-vnfd-scale>


Result:

.. code-block:: console

  +-----------------+---------------------------------------------------------------------------+
  | Field           | Value                                                                     |
  +-----------------+---------------------------------------------------------------------------+
  | attributes      | {                                                                         |
  |                 |     "vnfd": {                                                             |
  |                 |         "description": "sample-tosca-vnfd-scaling",                       |
  |                 |         "metadata": {                                                     |
  |                 |             "template_name": "sample-tosca-vnfd-scaling"                  |
  |                 |         },                                                                |
  |                 |         "topology_template": {                                            |
  |                 |             "node_templates": {                                           |
  |                 |                 "CP1": {                                                  |
  |                 |                     "properties": {                                       |
  |                 |                         "anti_spoofing_protection": false,                |
  |                 |                         "management": true,                               |
  |                 |                         "order": 0                                        |
  |                 |                     },                                                    |
  |                 |                     "requirements": [                                     |
  |                 |                         {                                                 |
  |                 |                             "virtualLink": {                              |
  |                 |                                 "node": "VL1"                             |
  |                 |                             }                                             |
  |                 |                         },                                                |
  |                 |                         {                                                 |
  |                 |                             "virtualBinding": {                           |
  |                 |                                 "node": "VDU1"                            |
  |                 |                             }                                             |
  |                 |                         }                                                 |
  |                 |                     ],                                                    |
  |                 |                     "type": "tosca.nodes.nfv.CP.Tacker"                   |
  |                 |                 },                                                        |
  |                 |                 "CP2": {                                                  |
  |                 |                     "properties": {                                       |
  |                 |                         "anti_spoofing_protection": false,                |
  |                 |                         "management": true,                               |
  |                 |                         "order": 0                                        |
  |                 |                     },                                                    |
  |                 |                     "requirements": [                                     |
  |                 |                         {                                                 |
  |                 |                             "virtualLink": {                              |
  |                 |                                 "node": "VL1"                             |
  |                 |                             }                                             |
  |                 |                         },                                                |
  |                 |                         {                                                 |
  |                 |                             "virtualBinding": {                           |
  |                 |                                 "node": "VDU2"                            |
  |                 |                             }                                             |
  |                 |                         }                                                 |
  |                 |                     ],                                                    |
  |                 |                     "type": "tosca.nodes.nfv.CP.Tacker"                   |
  |                 |                 },                                                        |
  |                 |                 "VDU1": {                                                 |
  |                 |                     "properties": {                                       |
  |                 |                         "availability_zone": "nova",                      |
  |                 |                         "flavor": "m1.tiny",                              |
  |                 |                         "image": "cirros-0.4.0-x86_64-disk",              |
  |                 |                         "mgmt_driver": "noop"                             |
  |                 |                     },                                                    |
  |                 |                     "type": "tosca.nodes.nfv.VDU.Tacker"                  |
  |                 |                 },                                                        |
  |                 |                 "VDU2": {                                                 |
  |                 |                     "properties": {                                       |
  |                 |                         "availability_zone": "nova",                      |
  |                 |                         "flavor": "m1.tiny",                              |
  |                 |                         "image": "cirros-0.4.0-x86_64-disk",              |
  |                 |                         "mgmt_driver": "noop"                             |
  |                 |                     },                                                    |
  |                 |                     "type": "tosca.nodes.nfv.VDU.Tacker"                  |
  |                 |                 },                                                        |
  |                 |                 "VL1": {                                                  |
  |                 |                     "properties": {                                       |
  |                 |                         "network_name": "net_mgmt",                       |
  |                 |                         "vendor": "Tacker"                                |
  |                 |                     },                                                    |
  |                 |                     "type": "tosca.nodes.nfv.VL"                          |
  |                 |                 }                                                         |
  |                 |             },                                                            |
  |                 |             "policies": [                                                 |
  |                 |                 {                                                         |
  |                 |                     "SP1": {                                              |
  |                 |                         "properties": {                                   |
  |                 |                             "cooldown": 120,                              |
  |                 |                             "default_instances": 2,                       |
  |                 |                             "increment": 1,                               |
  |                 |                             "max_instances": 3,                           |
  |                 |                             "min_instances": 1                            |
  |                 |                         },                                                |
  |                 |                         "targets": [                                      |
  |                 |                             "VDU1",                                       |
  |                 |                             "VDU2"                                        |
  |                 |                         ],                                                |
  |                 |                         "type": "tosca.policies.tacker.Scaling"           |
  |                 |                     }                                                     |
  |                 |                 }                                                         |
  |                 |             ]                                                             |
  |                 |         },                                                                |
  |                 |         "tosca_definitions_version": "tosca_simple_profile_for_nfv_1_0_0" |
  |                 |     }                                                                     |
  |                 | }                                                                         |
  | created_at      | 2020-08-12 04:20:08.908891                                                |
  | description     | sample-tosca-vnfd-scaling                                                 |
  | id              | 1001f4e6-2e62-4950-be7a-541963e7e575                                      |
  | name            | tosca-vnfd-scale                                                          |
  | project_id      | e77397d2a02c4af1b7d79cef2a406396                                          |
  | service_types   | ['vnfd']                                                                  |
  | template_source | onboarded                                                                 |
  | updated_at      | None                                                                      |
  +-----------------+---------------------------------------------------------------------------+


Create the VNF:

.. code-block:: console

  $ openstack vnf create --vnfd-name <VNFD_NAME: tosca-vnfd-scale> \
      <NAME: vnf-scale>


Result:

.. code-block:: console

  +-----------------+---------------------------------------------------+
  | Field           | Value                                             |
  +-----------------+---------------------------------------------------+
  | attributes      | SP1_res.yaml=heat_template_version: 2013-05-23    |
  |                 | description: Scaling template                     |
  |                 | resources:                                        |
  |                 |   CP1:                                            |
  |                 |     type: OS::Neutron::Port                       |
  |                 |     properties:                                   |
  |                 |       port_security_enabled: false                |
  |                 |       network: net_mgmt                           |
  |                 |   CP2:                                            |
  |                 |     type: OS::Neutron::Port                       |
  |                 |     properties:                                   |
  |                 |       port_security_enabled: false                |
  |                 |       network: net_mgmt                           |
  |                 |   VDU1:                                           |
  |                 |     type: OS::Nova::Server                        |
  |                 |     properties:                                   |
  |                 |       flavor: m1.tiny                             |
  |                 |       user_data_format: SOFTWARE_CONFIG           |
  |                 |       availability_zone: nova                     |
  |                 |       image: cirros-0.4.0-x86_64-disk             |
  |                 |       config_drive: false                         |
  |                 |       networks:                                   |
  |                 |       - port:                                     |
  |                 |           get_resource: CP1                       |
  |                 |   VDU2:                                           |
  |                 |     type: OS::Nova::Server                        |
  |                 |     properties:                                   |
  |                 |       flavor: m1.tiny                             |
  |                 |       user_data_format: SOFTWARE_CONFIG           |
  |                 |       availability_zone: nova                     |
  |                 |       image: cirros-0.4.0-x86_64-disk             |
  |                 |       config_drive: false                         |
  |                 |       networks:                                   |
  |                 |       - port:                                     |
  |                 |           get_resource: CP2                       |
  |                 |   VL1:                                            |
  |                 |     type: OS::Neutron::Net                        |
  |                 | outputs:                                          |
  |                 |   mgmt_ip-VDU1:                                   |
  |                 |     value:                                        |
  |                 |       get_attr:                                   |
  |                 |       - CP1                                       |
  |                 |       - fixed_ips                                 |
  |                 |       - 0                                         |
  |                 |       - ip_address                                |
  |                 |   mgmt_ip-VDU2:                                   |
  |                 |     value:                                        |
  |                 |       get_attr:                                   |
  |                 |       - CP2                                       |
  |                 |       - fixed_ips                                 |
  |                 |       - 0                                         |
  |                 |       - ip_address                                |
  |                 | , heat_template=heat_template_version: 2013-05-23 |
  |                 | description: 'sample-tosca-vnfd-scaling           |
  |                 |                                                   |
  |                 |   '                                               |
  |                 | parameters: {}                                    |
  |                 | resources:                                        |
  |                 |   SP1_scale_out:                                  |
  |                 |     type: OS::Heat::ScalingPolicy                 |
  |                 |     properties:                                   |
  |                 |       auto_scaling_group_id:                      |
  |                 |         get_resource: SP1_group                   |
  |                 |       adjustment_type: change_in_capacity         |
  |                 |       scaling_adjustment: 1                       |
  |                 |       cooldown: 120                               |
  |                 |   SP1_group:                                      |
  |                 |     type: OS::Heat::AutoScalingGroup              |
  |                 |     properties:                                   |
  |                 |       min_size: 1                                 |
  |                 |       max_size: 3                                 |
  |                 |       desired_capacity: 2                         |
  |                 |       cooldown: 120                               |
  |                 |       resource:                                   |
  |                 |         type: SP1_res.yaml                        |
  |                 |   SP1_scale_in:                                   |
  |                 |     type: OS::Heat::ScalingPolicy                 |
  |                 |     properties:                                   |
  |                 |       auto_scaling_group_id:                      |
  |                 |         get_resource: SP1_group                   |
  |                 |       adjustment_type: change_in_capacity         |
  |                 |       scaling_adjustment: -1                      |
  |                 |       cooldown: 120                               |
  |                 | outputs: {}                                       |
  |                 | , scaling_group_names=b'{"SP1": "SP1_group"}'     |
  | created_at      | 2020-08-12 04:22:35.006543                        |
  | description     | sample-tosca-vnfd-scaling                         |
  | error_reason    | None                                              |
  | id              | 9b312a7c-15de-4230-85fb-27da7d37978b              |
  | instance_id     | 0e00ca75-23b7-4ff8-a90f-83c55d756d4f              |
  | mgmt_ip_address | None                                              |
  | name            | vnf-scale                                         |
  | placement_attr  | vim_name=openstack-nfv-vim                        |
  | project_id      | e77397d2a02c4af1b7d79cef2a406396                  |
  | status          | PENDING_CREATE                                    |
  | updated_at      | None                                              |
  | vim_id          | aacb3c7f-d532-44d9-b8ed-49e2b30114aa              |
  | vnfd_id         | 1001f4e6-2e62-4950-be7a-541963e7e575              |
  +-----------------+---------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf create --help
  usage: openstack vnf create [-h] [-f {json,shell,table,value,yaml}]
                              [-c COLUMN] [--noindent] [--prefix PREFIX]
                              [--max-width <integer>] [--fit-width]
                              [--print-empty] [--tenant-id TENANT_ID]
                              (--vnfd-id VNFD_ID | --vnfd-name VNFD_NAME | --vnfd-template VNFD_TEMPLATE)
                              [--vim-id VIM_ID | --vim-name VIM_NAME]
                              [--vim-region-name VIM_REGION_NAME]
                              [--config-file CONFIG_FILE]
                              [--param-file PARAM_FILE]
                              [--description DESCRIPTION]
                              NAME

  Create a new VNF

  positional arguments:
    NAME                  Set a name for the VNF

  optional arguments:
    -h, --help            show this help message and exit
    --tenant-id TENANT_ID
                          The owner tenant ID or project ID
    --vnfd-id VNFD_ID     VNFD ID to use as template to create VNF
    --vnfd-name VNFD_NAME
                          VNFD Name to use as template to create VNF
    --vnfd-template VNFD_TEMPLATE
                          VNFD file to create VNF
    --vim-id VIM_ID       VIM ID to deploy VNF on specified VIM
    --vim-name VIM_NAME   VIM name to deploy VNF on specified VIM
    --vim-region-name VIM_REGION_NAME
                          VIM Region to deploy VNF on specified VIM
    --config-file CONFIG_FILE
                          YAML file with VNF configuration
    --param-file PARAM_FILE
                          Specify parameter yaml file
    --description DESCRIPTION
                          Set description for the VNF


2. List VNFs
^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf list


Result (CREATING):

.. code-block:: console

  +--------------------------------------+-----------+-----------------+----------------+--------------------------------------+--------------------------------------+
  | ID                                   | Name      | Mgmt Ip Address | Status         | VIM ID                               | VNFD ID                              |
  +--------------------------------------+-----------+-----------------+----------------+--------------------------------------+--------------------------------------+
  | 9b312a7c-15de-4230-85fb-27da7d37978b | vnf-scale | None            | PENDING_CREATE | aacb3c7f-d532-44d9-b8ed-49e2b30114aa | 1001f4e6-2e62-4950-be7a-541963e7e575 |
  +--------------------------------------+-----------+-----------------+----------------+--------------------------------------+--------------------------------------+


Result (CREATED):

.. code-block:: console

  +--------------------------------------+-----------+-----------------------------------------------------------------------------------------------+--------+--------------------------------------+--------------------------------------+
  | ID                                   | Name      | Mgmt Ip Address                                                                               | Status | VIM ID                               | VNFD ID                              |
  +--------------------------------------+-----------+-----------------------------------------------------------------------------------------------+--------+--------------------------------------+--------------------------------------+
  | 9b312a7c-15de-4230-85fb-27da7d37978b | vnf-scale | {"VDU2": ["192.168.120.250", "192.168.120.41"], "VDU1": ["192.168.120.69", "192.168.120.92"]} | ACTIVE | aacb3c7f-d532-44d9-b8ed-49e2b30114aa | 1001f4e6-2e62-4950-be7a-541963e7e575 |
  +--------------------------------------+-----------+-----------------------------------------------------------------------------------------------+--------+--------------------------------------+--------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf list --help
  usage: openstack vnf list [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN]
                            [--quote {all,minimal,none,nonnumeric}] [--noindent]
                            [--max-width <integer>] [--fit-width]
                            [--print-empty] [--sort-column SORT_COLUMN]
                            [--template-source TEMPLATE_SOURCE]
                            [--vim-id VIM_ID | --vim-name VIM_NAME]
                            [--vnfd-id VNFD_ID | --vnfd-name VNFD_NAME]
                            [--tenant-id TENANT_ID] [--long]

  List VNF(s) that belong to a given tenant.

  optional arguments:
    -h, --help            show this help message and exit
    --template-source TEMPLATE_SOURCE
                          List VNF with specified template source. Available
                          options are 'onboarded' (default), 'inline' or 'all'
    --vim-id VIM_ID       List VNF(s) that belong to a given VIM ID
    --vim-name VIM_NAME   List VNF(s) that belong to a given VIM Name
    --vnfd-id VNFD_ID     List VNF(s) that belong to a given VNFD ID
    --vnfd-name VNFD_NAME
                          List VNF(s) that belong to a given VNFD Name
    --tenant-id TENANT_ID
                          The owner tenant ID or project ID
    --long                List additional fields in output


3. Show VNF
^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf show  <VNF: vnf-scale>


Result:

.. code-block:: console

  +-----------------+-----------------------------------------------------------------------------------------------+
  | Field           | Value                                                                                         |
  +-----------------+-----------------------------------------------------------------------------------------------+
  | attributes      | SP1_res.yaml=heat_template_version: 2013-05-23                                                |
  |                 | description: Scaling template                                                                 |
  |                 | resources:                                                                                    |
  |                 |   CP1:                                                                                        |
  |                 |     type: OS::Neutron::Port                                                                   |
  |                 |     properties:                                                                               |
  |                 |       port_security_enabled: false                                                            |
  |                 |       network: net_mgmt                                                                       |
  |                 |   CP2:                                                                                        |
  |                 |     type: OS::Neutron::Port                                                                   |
  |                 |     properties:                                                                               |
  |                 |       port_security_enabled: false                                                            |
  |                 |       network: net_mgmt                                                                       |
  |                 |   VDU1:                                                                                       |
  |                 |     type: OS::Nova::Server                                                                    |
  |                 |     properties:                                                                               |
  |                 |       flavor: m1.tiny                                                                         |
  |                 |       user_data_format: SOFTWARE_CONFIG                                                       |
  |                 |       availability_zone: nova                                                                 |
  |                 |       image: cirros-0.4.0-x86_64-disk                                                         |
  |                 |       config_drive: false                                                                     |
  |                 |       networks:                                                                               |
  |                 |       - port:                                                                                 |
  |                 |           get_resource: CP1                                                                   |
  |                 |   VDU2:                                                                                       |
  |                 |     type: OS::Nova::Server                                                                    |
  |                 |     properties:                                                                               |
  |                 |       flavor: m1.tiny                                                                         |
  |                 |       user_data_format: SOFTWARE_CONFIG                                                       |
  |                 |       availability_zone: nova                                                                 |
  |                 |       image: cirros-0.4.0-x86_64-disk                                                         |
  |                 |       config_drive: false                                                                     |
  |                 |       networks:                                                                               |
  |                 |       - port:                                                                                 |
  |                 |           get_resource: CP2                                                                   |
  |                 |   VL1:                                                                                        |
  |                 |     type: OS::Neutron::Net                                                                    |
  |                 | outputs:                                                                                      |
  |                 |   mgmt_ip-VDU1:                                                                               |
  |                 |     value:                                                                                    |
  |                 |       get_attr:                                                                               |
  |                 |       - CP1                                                                                   |
  |                 |       - fixed_ips                                                                             |
  |                 |       - 0                                                                                     |
  |                 |       - ip_address                                                                            |
  |                 |   mgmt_ip-VDU2:                                                                               |
  |                 |     value:                                                                                    |
  |                 |       get_attr:                                                                               |
  |                 |       - CP2                                                                                   |
  |                 |       - fixed_ips                                                                             |
  |                 |       - 0                                                                                     |
  |                 |       - ip_address                                                                            |
  |                 | , heat_template=heat_template_version: 2013-05-23                                             |
  |                 | description: 'sample-tosca-vnfd-scaling                                                       |
  |                 |                                                                                               |
  |                 |   '                                                                                           |
  |                 | parameters: {}                                                                                |
  |                 | resources:                                                                                    |
  |                 |   SP1_scale_out:                                                                              |
  |                 |     type: OS::Heat::ScalingPolicy                                                             |
  |                 |     properties:                                                                               |
  |                 |       auto_scaling_group_id:                                                                  |
  |                 |         get_resource: SP1_group                                                               |
  |                 |       adjustment_type: change_in_capacity                                                     |
  |                 |       scaling_adjustment: 1                                                                   |
  |                 |       cooldown: 120                                                                           |
  |                 |   SP1_group:                                                                                  |
  |                 |     type: OS::Heat::AutoScalingGroup                                                          |
  |                 |     properties:                                                                               |
  |                 |       min_size: 1                                                                             |
  |                 |       max_size: 3                                                                             |
  |                 |       desired_capacity: 2                                                                     |
  |                 |       cooldown: 120                                                                           |
  |                 |       resource:                                                                               |
  |                 |         type: SP1_res.yaml                                                                    |
  |                 |   SP1_scale_in:                                                                               |
  |                 |     type: OS::Heat::ScalingPolicy                                                             |
  |                 |     properties:                                                                               |
  |                 |       auto_scaling_group_id:                                                                  |
  |                 |         get_resource: SP1_group                                                               |
  |                 |       adjustment_type: change_in_capacity                                                     |
  |                 |       scaling_adjustment: -1                                                                  |
  |                 |       cooldown: 120                                                                           |
  |                 | outputs: {}                                                                                   |
  |                 | , scaling_group_names={"SP1": "SP1_group"}                                                    |
  | created_at      | 2020-08-12 04:22:35                                                                           |
  | description     | sample-tosca-vnfd-scaling                                                                     |
  | error_reason    | None                                                                                          |
  | id              | 9b312a7c-15de-4230-85fb-27da7d37978b                                                          |
  | instance_id     | 0e00ca75-23b7-4ff8-a90f-83c55d756d4f                                                          |
  | mgmt_ip_address | {"VDU2": ["192.168.120.250", "192.168.120.41"], "VDU1": ["192.168.120.69", "192.168.120.92"]} |
  | name            | vnf-scale                                                                                     |
  | placement_attr  | vim_name=openstack-nfv-vim                                                                    |
  | project_id      | e77397d2a02c4af1b7d79cef2a406396                                                              |
  | status          | ACTIVE                                                                                        |
  | updated_at      | None                                                                                          |
  | vim_id          | aacb3c7f-d532-44d9-b8ed-49e2b30114aa                                                          |
  | vnfd_id         | 1001f4e6-2e62-4950-be7a-541963e7e575                                                          |
  +-----------------+-----------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf show --help
  usage: openstack vnf show [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                            [--noindent] [--prefix PREFIX]
                            [--max-width <integer>] [--fit-width]
                            [--print-empty]
                            <VNF>

  Display VNF details

  positional arguments:
    <VNF>                 VNF to display (name or ID)

  optional arguments:
    -h, --help            show this help message and exit


4. List VNF resource
^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf resource list <VNF: vnf-scale>


Result:

.. code-block:: console

  +--------------------------------------+---------------+----------------------------+
  | ID                                   | Name          | Type                       |
  +--------------------------------------+---------------+----------------------------+
  | 4abedc36da294bb0a0fa8aaa7f4c01f4     | SP1_scale_out | OS::Heat::ScalingPolicy    |
  | 0060aff7150d43c5ace293e3cac4552a     | SP1_scale_in  | OS::Heat::ScalingPolicy    |
  | 141c0279-1dfb-42a3-b947-4caa3765b27f | SP1_group     | OS::Heat::AutoScalingGroup |
  | 9f65c3d6-e5ce-4611-8589-82fab1a32d6e | qf4qc4l6qk7o  | SP1_res.yaml               |
  | 9a01d98e-9c01-4e55-ba86-571b61e4ea74 | edilzqp2htvv  | SP1_res.yaml               |
  | 0abc3f38-647e-4b47-8376-06d2e56c4217 | VDU2          | OS::Nova::Server           |
  | a6374222-ecbc-4eee-96e6-9fe601807c9d | CP2           | OS::Neutron::Port          |
  | 8d2fc2d9-33ee-440d-9e02-db6083cd5cb6 | VL1           | OS::Neutron::Net           |
  | 84c78850-8a06-41ab-98a7-371224125beb | VDU1          | OS::Nova::Server           |
  | 5462f8c1-3292-44af-8661-39e1a7474859 | CP1           | OS::Neutron::Port          |
  +--------------------------------------+---------------+----------------------------+


Help:

.. code-block:: console

  $ openstack vnf resource list --help
  usage: openstack vnf resource list [-h] [-f {csv,json,table,value,yaml}]
                                    [-c COLUMN]
                                    [--quote {all,minimal,none,nonnumeric}]
                                    [--noindent] [--max-width <integer>]
                                    [--fit-width] [--print-empty]
                                    [--sort-column SORT_COLUMN]
                                    <VNF>

  List resources of a VNF like VDU, CP, etc.

  positional arguments:
    <VNF>                 VNF to display (name or ID)

  optional arguments:
    -h, --help            show this help message and exit


5. Update VNF
^^^^^^^^^^^^^

Create ``vnf-config.yaml``:

.. code-block:: console

  vdus:
    VDU1:
      config:
        foo: 'bar'


Update VNF with the config file ``vnf-config.yaml``:

.. code-block:: console

  $ openstack vnf set --config-file vnf-config.yaml <VNF: vnf-scale>


Result (Updating):

.. code-block:: console

  +-----------------+-----------------------------------------------------------------------------------------------+
  | Field           | Value                                                                                         |
  +-----------------+-----------------------------------------------------------------------------------------------+
  | attributes      | SP1_res.yaml=heat_template_version: 2013-05-23                                                |
  |                 | description: Scaling template                                                                 |
  |                 | resources:                                                                                    |
  |                 |   CP1:                                                                                        |
  |                 |     type: OS::Neutron::Port                                                                   |
  |                 |     properties:                                                                               |
  |                 |       port_security_enabled: false                                                            |
  |                 |       network: net_mgmt                                                                       |
  |                 |   CP2:                                                                                        |
  |                 |     type: OS::Neutron::Port                                                                   |
  |                 |     properties:                                                                               |
  |                 |       port_security_enabled: false                                                            |
  |                 |       network: net_mgmt                                                                       |
  |                 |   VDU1:                                                                                       |
  |                 |     type: OS::Nova::Server                                                                    |
  |                 |     properties:                                                                               |
  |                 |       flavor: m1.tiny                                                                         |
  |                 |       user_data_format: SOFTWARE_CONFIG                                                       |
  |                 |       availability_zone: nova                                                                 |
  |                 |       image: cirros-0.4.0-x86_64-disk                                                         |
  |                 |       config_drive: false                                                                     |
  |                 |       networks:                                                                               |
  |                 |       - port:                                                                                 |
  |                 |           get_resource: CP1                                                                   |
  |                 |   VDU2:                                                                                       |
  |                 |     type: OS::Nova::Server                                                                    |
  |                 |     properties:                                                                               |
  |                 |       flavor: m1.tiny                                                                         |
  |                 |       user_data_format: SOFTWARE_CONFIG                                                       |
  |                 |       availability_zone: nova                                                                 |
  |                 |       image: cirros-0.4.0-x86_64-disk                                                         |
  |                 |       config_drive: false                                                                     |
  |                 |       networks:                                                                               |
  |                 |       - port:                                                                                 |
  |                 |           get_resource: CP2                                                                   |
  |                 |   VL1:                                                                                        |
  |                 |     type: OS::Neutron::Net                                                                    |
  |                 | outputs:                                                                                      |
  |                 |   mgmt_ip-VDU1:                                                                               |
  |                 |     value:                                                                                    |
  |                 |       get_attr:                                                                               |
  |                 |       - CP1                                                                                   |
  |                 |       - fixed_ips                                                                             |
  |                 |       - 0                                                                                     |
  |                 |       - ip_address                                                                            |
  |                 |   mgmt_ip-VDU2:                                                                               |
  |                 |     value:                                                                                    |
  |                 |       get_attr:                                                                               |
  |                 |       - CP2                                                                                   |
  |                 |       - fixed_ips                                                                             |
  |                 |       - 0                                                                                     |
  |                 |       - ip_address                                                                            |
  |                 | , config=vdus:                                                                                |
  |                 |   VDU1:                                                                                       |
  |                 |     config:                                                                                   |
  |                 |       foo: bar                                                                                |
  |                 | , heat_template=heat_template_version: 2013-05-23                                             |
  |                 | description: 'sample-tosca-vnfd-scaling                                                       |
  |                 |                                                                                               |
  |                 |   '                                                                                           |
  |                 | parameters: {}                                                                                |
  |                 | resources:                                                                                    |
  |                 |   SP1_scale_out:                                                                              |
  |                 |     type: OS::Heat::ScalingPolicy                                                             |
  |                 |     properties:                                                                               |
  |                 |       auto_scaling_group_id:                                                                  |
  |                 |         get_resource: SP1_group                                                               |
  |                 |       adjustment_type: change_in_capacity                                                     |
  |                 |       scaling_adjustment: 1                                                                   |
  |                 |       cooldown: 120                                                                           |
  |                 |   SP1_group:                                                                                  |
  |                 |     type: OS::Heat::AutoScalingGroup                                                          |
  |                 |     properties:                                                                               |
  |                 |       min_size: 1                                                                             |
  |                 |       max_size: 3                                                                             |
  |                 |       desired_capacity: 2                                                                     |
  |                 |       cooldown: 120                                                                           |
  |                 |       resource:                                                                               |
  |                 |         type: SP1_res.yaml                                                                    |
  |                 |   SP1_scale_in:                                                                               |
  |                 |     type: OS::Heat::ScalingPolicy                                                             |
  |                 |     properties:                                                                               |
  |                 |       auto_scaling_group_id:                                                                  |
  |                 |         get_resource: SP1_group                                                               |
  |                 |       adjustment_type: change_in_capacity                                                     |
  |                 |       scaling_adjustment: -1                                                                  |
  |                 |       cooldown: 120                                                                           |
  |                 | outputs: {}                                                                                   |
  |                 | , scaling_group_names={"SP1": "SP1_group"}                                                    |
  | created_at      | 2020-08-12 04:22:35                                                                           |
  | description     | sample-tosca-vnfd-scaling                                                                     |
  | error_reason    | None                                                                                          |
  | id              | 9b312a7c-15de-4230-85fb-27da7d37978b                                                          |
  | instance_id     | 0e00ca75-23b7-4ff8-a90f-83c55d756d4f                                                          |
  | mgmt_ip_address | {"VDU2": ["192.168.120.250", "192.168.120.41"], "VDU1": ["192.168.120.69", "192.168.120.92"]} |
  | name            | vnf-scale                                                                                     |
  | placement_attr  | vim_name=openstack-nfv-vim                                                                    |
  | project_id      | e77397d2a02c4af1b7d79cef2a406396                                                              |
  | status          | PENDING_UPDATE                                                                                |
  | updated_at      | None                                                                                          |
  | vim_id          | aacb3c7f-d532-44d9-b8ed-49e2b30114aa                                                          |
  | vnfd_id         | 1001f4e6-2e62-4950-be7a-541963e7e575                                                          |
  +-----------------+-----------------------------------------------------------------------------------------------+


Result (Updated):

.. code-block:: console

  +-----------------+-----------------------------------------------------------------------------------------------+
  | Field           | Value                                                                                         |
  +-----------------+-----------------------------------------------------------------------------------------------+
  | attributes      | SP1_res.yaml=heat_template_version: 2013-05-23                                                |
  |                 | description: Scaling template                                                                 |
  |                 | resources:                                                                                    |
  |                 |   CP1:                                                                                        |
  |                 |     type: OS::Neutron::Port                                                                   |
  |                 |     properties:                                                                               |
  |                 |       port_security_enabled: false                                                            |
  |                 |       network: net_mgmt                                                                       |
  |                 |   CP2:                                                                                        |
  |                 |     type: OS::Neutron::Port                                                                   |
  |                 |     properties:                                                                               |
  |                 |       port_security_enabled: false                                                            |
  |                 |       network: net_mgmt                                                                       |
  |                 |   VDU1:                                                                                       |
  |                 |     type: OS::Nova::Server                                                                    |
  |                 |     properties:                                                                               |
  |                 |       flavor: m1.tiny                                                                         |
  |                 |       user_data_format: SOFTWARE_CONFIG                                                       |
  |                 |       availability_zone: nova                                                                 |
  |                 |       image: cirros-0.4.0-x86_64-disk                                                         |
  |                 |       config_drive: false                                                                     |
  |                 |       networks:                                                                               |
  |                 |       - port:                                                                                 |
  |                 |           get_resource: CP1                                                                   |
  |                 |   VDU2:                                                                                       |
  |                 |     type: OS::Nova::Server                                                                    |
  |                 |     properties:                                                                               |
  |                 |       flavor: m1.tiny                                                                         |
  |                 |       user_data_format: SOFTWARE_CONFIG                                                       |
  |                 |       availability_zone: nova                                                                 |
  |                 |       image: cirros-0.4.0-x86_64-disk                                                         |
  |                 |       config_drive: false                                                                     |
  |                 |       networks:                                                                               |
  |                 |       - port:                                                                                 |
  |                 |           get_resource: CP2                                                                   |
  |                 |   VL1:                                                                                        |
  |                 |     type: OS::Neutron::Net                                                                    |
  |                 | outputs:                                                                                      |
  |                 |   mgmt_ip-VDU1:                                                                               |
  |                 |     value:                                                                                    |
  |                 |       get_attr:                                                                               |
  |                 |       - CP1                                                                                   |
  |                 |       - fixed_ips                                                                             |
  |                 |       - 0                                                                                     |
  |                 |       - ip_address                                                                            |
  |                 |   mgmt_ip-VDU2:                                                                               |
  |                 |     value:                                                                                    |
  |                 |       get_attr:                                                                               |
  |                 |       - CP2                                                                                   |
  |                 |       - fixed_ips                                                                             |
  |                 |       - 0                                                                                     |
  |                 |       - ip_address                                                                            |
  |                 | , config=vdus:                                                                                |
  |                 |   VDU1:                                                                                       |
  |                 |     config:                                                                                   |
  |                 |       foo: bar                                                                                |
  |                 | , heat_template=heat_template_version: 2013-05-23                                             |
  |                 | description: 'sample-tosca-vnfd-scaling                                                       |
  |                 |                                                                                               |
  |                 |   '                                                                                           |
  |                 | parameters: {}                                                                                |
  |                 | resources:                                                                                    |
  |                 |   SP1_scale_out:                                                                              |
  |                 |     type: OS::Heat::ScalingPolicy                                                             |
  |                 |     properties:                                                                               |
  |                 |       auto_scaling_group_id:                                                                  |
  |                 |         get_resource: SP1_group                                                               |
  |                 |       adjustment_type: change_in_capacity                                                     |
  |                 |       scaling_adjustment: 1                                                                   |
  |                 |       cooldown: 120                                                                           |
  |                 |   SP1_group:                                                                                  |
  |                 |     type: OS::Heat::AutoScalingGroup                                                          |
  |                 |     properties:                                                                               |
  |                 |       min_size: 1                                                                             |
  |                 |       max_size: 3                                                                             |
  |                 |       desired_capacity: 2                                                                     |
  |                 |       cooldown: 120                                                                           |
  |                 |       resource:                                                                               |
  |                 |         type: SP1_res.yaml                                                                    |
  |                 |   SP1_scale_in:                                                                               |
  |                 |     type: OS::Heat::ScalingPolicy                                                             |
  |                 |     properties:                                                                               |
  |                 |       auto_scaling_group_id:                                                                  |
  |                 |         get_resource: SP1_group                                                               |
  |                 |       adjustment_type: change_in_capacity                                                     |
  |                 |       scaling_adjustment: -1                                                                  |
  |                 |       cooldown: 120                                                                           |
  |                 | outputs: {}                                                                                   |
  |                 | , scaling_group_names={"SP1": "SP1_group"}                                                    |
  | created_at      | 2020-08-12 04:22:35                                                                           |
  | description     | sample-tosca-vnfd-scaling                                                                     |
  | error_reason    | None                                                                                          |
  | id              | 9b312a7c-15de-4230-85fb-27da7d37978b                                                          |
  | instance_id     | 0e00ca75-23b7-4ff8-a90f-83c55d756d4f                                                          |
  | mgmt_ip_address | {"VDU2": ["192.168.120.250", "192.168.120.41"], "VDU1": ["192.168.120.69", "192.168.120.92"]} |
  | name            | vnf-scale                                                                                     |
  | placement_attr  | vim_name=openstack-nfv-vim                                                                    |
  | project_id      | e77397d2a02c4af1b7d79cef2a406396                                                              |
  | status          | ACTIVE                                                                                        |
  | updated_at      | 2020-08-12 05:06:13                                                                           |
  | vim_id          | aacb3c7f-d532-44d9-b8ed-49e2b30114aa                                                          |
  | vnfd_id         | 1001f4e6-2e62-4950-be7a-541963e7e575                                                          |
  +-----------------+-----------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vnf set --help
  usage: openstack vnf set [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                          [--noindent] [--prefix PREFIX]
                          [--max-width <integer>] [--fit-width] [--print-empty]
                          (--config-file CONFIG_FILE | --config CONFIG | --param-file PARAM_FILE)
                          <VNF>

  Update a given VNF.

  positional arguments:
    <VNF>                 VNF to update (name or ID)

  optional arguments:
    -h, --help            show this help message and exit
    --config-file CONFIG_FILE
                          YAML file with VNF configuration
    --config CONFIG       YAML data with VNF configuration
    --param-file PARAM_FILE
                          YAML file with VNF parameter


.. note:: When the update VNF operation executed, Tacker ask Heat to update
          the stack and the change is reflected immediately, and the VMs may
          reboot.


6. Scale VNF
^^^^^^^^^^^^

Scale out the VNF:

.. code-block:: console

  $ openstack vnf scale --scaling-policy-name <SCALING_POLICY_NAME: SP1> \
      --scaling-type out <VNF: vnf-scale>


Check the VMs scaled out:

.. code-block:: console

  $ openstack server list
  +--------------------------------------+-------------------------------------------------------+--------+--------------------------+--------------------------+---------+
  | ID                                   | Name                                                  | Status | Networks                 | Image                    | Flavor  |
  +--------------------------------------+-------------------------------------------------------+--------+--------------------------+--------------------------+---------+
  | dfb04024-666c-4b82-94eb-12766851cfb7 | vn-6okzhe-k6n2umsyoizd-ex2uwxma2tlt-VDU2-ljontrce3bd7 | ACTIVE | net_mgmt=192.168.120.8   | cirros-0.4.0-x86_64-disk | m1.tiny |
  | e48999e8-5f65-43e4-b8a5-e81e358e2e21 | vn-6okzhe-k6n2umsyoizd-ex2uwxma2tlt-VDU1-3dcglaxrwyzl | ACTIVE | net_mgmt=192.168.120.82  | cirros-0.4.0-x86_64-disk | m1.tiny |
  | 0abc3f38-647e-4b47-8376-06d2e56c4217 | vn-6okzhe-edilzqp2htvv-ibfssgztffjf-VDU2-43gjj46b2nrr | ACTIVE | net_mgmt=192.168.120.41  | cirros-0.4.0-x86_64-disk | m1.tiny |
  | 43840dde-1ec3-4da6-aeab-afca96299a9f | vn-6okzhe-qf4qc4l6qk7o-tukln5mwcokq-VDU2-zd7nq3smgjdr | ACTIVE | net_mgmt=192.168.120.250 | cirros-0.4.0-x86_64-disk | m1.tiny |
  | 84c78850-8a06-41ab-98a7-371224125beb | vn-6okzhe-edilzqp2htvv-ibfssgztffjf-VDU1-qvv2vv37f65t | ACTIVE | net_mgmt=192.168.120.92  | cirros-0.4.0-x86_64-disk | m1.tiny |
  | 9318b9fe-d655-4088-9910-b5f7481ed059 | vn-6okzhe-qf4qc4l6qk7o-tukln5mwcokq-VDU1-omaexvftqjee | ACTIVE | net_mgmt=192.168.120.69  | cirros-0.4.0-x86_64-disk | m1.tiny |
  +--------------------------------------+-------------------------------------------------------+--------+--------------------------+--------------------------+---------+


Scale in the VNF:

.. code-block:: console

  $ openstack vnf scale --scaling-policy-name <SCALING_POLICY_NAME: SP1> \
      --scaling-type in <VNF: vnf-scale>


Check the VMs scaled in:

.. code-block:: console

  $ openstack server list
  +--------------------------------------+-------------------------------------------------------+--------+--------------------------+--------------------------+---------+
  | ID                                   | Name                                                  | Status | Networks                 | Image                    | Flavor  |
  +--------------------------------------+-------------------------------------------------------+--------+--------------------------+--------------------------+---------+
  | dfb04024-666c-4b82-94eb-12766851cfb7 | vn-6okzhe-k6n2umsyoizd-ex2uwxma2tlt-VDU2-ljontrce3bd7 | ACTIVE | net_mgmt=192.168.120.8   | cirros-0.4.0-x86_64-disk | m1.tiny |
  | e48999e8-5f65-43e4-b8a5-e81e358e2e21 | vn-6okzhe-k6n2umsyoizd-ex2uwxma2tlt-VDU1-3dcglaxrwyzl | ACTIVE | net_mgmt=192.168.120.82  | cirros-0.4.0-x86_64-disk | m1.tiny |
  | 43840dde-1ec3-4da6-aeab-afca96299a9f | vn-6okzhe-qf4qc4l6qk7o-tukln5mwcokq-VDU2-zd7nq3smgjdr | ACTIVE | net_mgmt=192.168.120.250 | cirros-0.4.0-x86_64-disk | m1.tiny |
  | 9318b9fe-d655-4088-9910-b5f7481ed059 | vn-6okzhe-qf4qc4l6qk7o-tukln5mwcokq-VDU1-omaexvftqjee | ACTIVE | net_mgmt=192.168.120.69  | cirros-0.4.0-x86_64-disk | m1.tiny |
  +--------------------------------------+-------------------------------------------------------+--------+--------------------------+--------------------------+---------+


Help:

.. code-block:: console

  $ openstack vnf scale --help
  usage: openstack vnf scale [-h] [--scaling-policy-name SCALING_POLICY_NAME]
                            [--scaling-type SCALING_TYPE]
                            <VNF>

  Scale a VNF.

  positional arguments:
    <VNF>                 VNF to scale (name or ID)

  optional arguments:
    -h, --help            show this help message and exit
    --scaling-policy-name SCALING_POLICY_NAME
                          VNF policy name used to scale
    --scaling-type SCALING_TYPE
                          VNF scaling type, it could be either "out" or "in"


7. Delete VNFs
^^^^^^^^^^^^^^

.. code-block:: console

  $ openstack vnf delete <VNF: vnf-scale>


Result:

.. code-block:: console

  All specified vnf(s) deleted successfully


Help:

.. code-block:: console

  $ openstack vnf delete --help
  usage: openstack vnf delete [-h] [--force] <VNF> [<VNF> ...]

  Delete VNF(s).

  positional arguments:
    <VNF>       VNF(s) to delete (name or ID)

  optional arguments:
    -h, --help  show this help message and exit
    --force     Force delete VNF instance
