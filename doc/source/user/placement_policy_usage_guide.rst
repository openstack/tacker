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

.. _ref-placement:

====================
VDU Placement policy
====================

OpenStack nova server groups can be used to control the affinity and
anti-affinity scheduling policy for a group of VDU's. Below placement
policies are supported::

    Affinity:
        The policy that forces Nova to hosts the concerned VDUs in a same
        hypervisor.

    Anti-Affinity:
        The policy that forces Nova to hosts the concerned VDUs each
        in a different hypervisor.

    Soft-Affinity:
        The policy that forces nova about if it is not possible to
        schedule some VDUs to the same host then the subsequent VDUs will be
        scheduled together on another host. In this way operator can express a
        good-to-have relationship between a group of VDUs.

    Soft-Anti-Affinity:
        The policy that forces nova about if it is not
        possible to schedule VDUs on different hosts then VDUs might get
        scheduled on a same host where another VDUs are running from the same
        group.


TOSCA schema for placement policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tacker defines TOSCA schema for the placement policy as given below:

.. code-block:: yaml

  tosca.policies.tacker.Placement:
    derived_from: tosca.policies.Placement
    description: Defines policy for placement of VDU's.
    properties:
      policy:
        type: string
        required: false
        default: affinity
        constraints:
          - valid_values: [ affinity, anti-affinity ]
        description: Placement policy for target VDU's.
      strict:
        type: boolean
        required: false
        default: true
        description: If the policy is not mandatory, set this flag to
        'false'. Setting this flag to 'false' allows the VDU deployment
        request to continue even if the nova-scheduler fails to assign
        compute hosts under the policy.
    targets:
        type: list
        entry_schema:
          type: string
        required: true
        description: List of VDU's on which placement policy will be applied.



Sample TOSCA with placement policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Following TOSCA snippet shows the placement policy used in VNFD, in which vdu1
and vdu2 are already defined VDUs.

**Affinity policy**

.. code-block:: yaml

     policies:
        - my_compute_placement_policy:
            type: tosca.policies.tacker.Placement
            properties:
              policy: affinity
              strict: true
            description: Apply my placement policy to my applications servers
            targets: [ VDU1, VDU2 ]

**Anti-Affinity policy**

.. code-block:: yaml

     policies:
        - my_compute_placement_policy:
            type: tosca.policies.tacker.Placement
            properties:
              policy: anti-affinity
              strict: true
            description: Apply my placement policy to my applications servers
            targets: [ VDU1, VDU2 ]

**Soft-Affinity policy**

.. code-block:: yaml

     policies:
        - my_compute_placement_policy:
            type: tosca.policies.tacker.Placement
            properties:
              policy: affinity
              strict: false
            description: Apply my placement policy to my applications servers
            targets: [ VDU1, VDU2 ]

**Soft-Anti-Affinity policy**

.. code-block:: yaml

     policies:
        - my_compute_placement_policy:
            type: tosca.policies.tacker.Placement
            properties:
              policy: anti-affinity
              strict: false
            description: Apply my placement policy to my applications servers
            targets: [ VDU1, VDU2 ]


The ``soft`` flag defines the softness of the placement policy.


Deploying placement TOSCA template using Tacker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once OpenStack/Devstack along with Tacker has been successfully installed,
deploy a sample placement policy template from location given below:
https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnfd/tosca-placement-policy-anti-affinity.yaml

Refer the 'Getting Started' link below on how to create a VNFD and deploy a
VNF:
https://docs.openstack.org/tacker/latest/install/getting_started.html
