..
      Copyright 2014-2015 OpenStack Foundation
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

===============
Getting Started
===============

Once manual installation of tacker components are completed, follow the below
steps to get started with tacker and validate the installation.

i). Create a sample-vnfd.yml file with the following content:

.. code-block:: ini

    template_name: sample-vnfd
    description: demo-example

    service_properties:
      Id: sample-vnfd
      vendor: tacker
      version: 1

    vdus:
      vdu1:
        id: vdu1
        vm_image: <IMAGE>
        instance_type: <FLAVOR>

        network_interfaces:
          management:
            network: <NETWORK_ID>
            management: true

        placement_policy:
          availability_zone: nova

        auto-scaling: noop

        config:
          param0: key0
          param1: key1
..

ii). Create a sample vnfd.

.. code-block:: console

    tacker vnfd-create --name <NAME> --vnfd-file sample-vnfd.yml
..

iii). Create a VNF.

.. code-block:: console

    tacker vnf-create --name <NAME> --vnfd-id <VNFD_ID>
..

iv). Check the status.

.. code-block:: console

    tacker vnf-list
    tacker vnf-show <VNF_ID>
..
