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

.. _ref-scale:

====================
VNF Forwarding Graph
====================

VNF Forwarding Graph or VNFFG feature in Tacker is used to orchestrate and
manage traffic through VNFs.  In short, abstract VNFFG TOSCA definitions are
rendered into Service Function Chains (SFCs) and Classifiers.  The SFC makes
up an ordered list of VNFs for traffic to traverse, while the classifier
decides which traffic should go through them.

Similar to how VNFs are described by VNFDs, VNFFGs are described by VNF
Forwarding Graph Descriptors (VNFFGD). Please see the `devref guide
<https://github.com/openstack/tacker/blob/master/doc/source/contributor
/vnffgd_template_description.rst>`_ on VNFFGD to learn more about
how a VNFFGD is defined.

VNFFG can be instantiated from VNFFGD or directly from VNFFGD template by
separate Tacker commands.  This action will build the chain and classifier
necessary to realize the VNFFG.

Prerequisites
~~~~~~~~~~~~~

VNFFG with OpenStack VIM relies on Neutron Networking-sfc to create SFC and
Classifiers.  Therefore it is required to install `networking-sfc
<https://github.com/openstack/networking-sfc>`_ project
in order to use Tacker VNFFG.  Networking-sfc also requires at least OVS 2.5
.0, so also ensure that is installed.  See the full `Networking-sfc guide
<https://wiki.openstack.org/wiki/Neutron/ServiceInsertionAndChaining>`_.

A simple example of a service chain would be one that forces all traffice
from HTTP client to HTTP server to go through VNFs that was created by
VNFFG.

Firstly, HTTP client and HTTP server must be launched.

.. code-block:: console

   net_id=$(openstack network list | grep net0 | awk '{print $2}')

   openstack server create --flavor m1.tiny --image cirros-0.3.5-x86_64-disk \
   --nic net-id=$net_id http_client

   openstack server create --flavor m1.tiny --image cirros-0.3.5-x86_64-disk \
   --nic net-id=$net_id http_server

Creating the VNFFGD
~~~~~~~~~~~~~~~~~~~

Once OpenStack/Devstack along with Tacker has been successfully installed,
deploy a sample VNFFGD template such as the one `here <https://github.com/
openstack/tacker/tree/master/samples/tosca-templates/vnffgd/
tosca-vnffgd-sample.yaml>`_.

.. note::

   A current constraint of the Forwarding Path policy match criteria is
   to include the network_src_port_id, such as:

   .. code-block:: yaml

      policy:
        type: ACL
        criteria:
        - network_src_port_id: 640dfd77-c92b-45a3-b8fc-22712de480e1
        - destination_port_range: 80-1024
        - ip_proto: 6
        - ip_dst_prefix: 192.168.1.2/24

You can get network_src_port_id and IP destination address through
OpenStack commands like bellow:

.. code-block:: console

   client_ip=$(openstack server list | grep http_client | \
    grep -Eo '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')

   network_source_port_id=$(openstack port list | grep $client_ip | awk '{print $2}')

   ip_dst=$(openstack server list | grep http_server | \
    grep -Eo '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')


This is required due to a limitation of Neutron networking-sfc and only
applies to an OpenStack VIM.

Tacker provides the following CLI to create a VNFFGD:

.. code-block:: console

   tacker vnffgd-create --vnffgd-file <vnffgd-file> <vnffgd-name>


Creating the VNFFG
~~~~~~~~~~~~~~~~~~

To create a VNFFG, you must have first created VNF instances of the same
VNFD types listed in the VNFFGD.  Failure to do so will result in error when
trying to create a VNFFG.  Note, the VNFD you define **must** include the
same Connection Point definitions as the ones you declared in your VNFFGD.

.. code-block:: console

   tacker vnfd-create --vnfd-file tosca-vnffg-vnfd1.yaml VNFD1
   tacker vnf-create --vnfd-name VNFD1 VNF1

   tacker vnfd-create --vnfd-file tosca-vnffg-vnfd2.yaml VNFD2
   tacker vnf-create --vnfd-name VNFD2 VNF2

Refer the 'Getting Started' link below on how to create a VNFD and deploy
2 VNFs: `VNF1`_ and `VNF2`_.

https://docs.openstack.org/tacker/latest/install/getting_started.html

Tacker provides the following CLI to create VNFFG from VNFFGD:

.. code-block:: console

   tacker vnffg-create --vnffgd-name <vnffgd-name> \
          --vnf-mapping <vnf-mapping> --symmetrical <boolean> <vnffg-name>

or you can create directly VNFFG from vnffgd template without initiating
VNFFGD.

.. code-block:: console

   tacker vnffg-create --vnffgd-template <vnffgd-template> \
      --vnf-mapping <vnf-mapping> --symmetrical <boolean> <vnffg-name>

If you use a parameterized vnffg template:

.. code-block:: console

   tacker vnffg-create --vnffgd-name <vnffgd-name> \
      --param-file <param-file> --vnf-mapping <vnf-mapping> \
      --symmetrical <boolean> <vnffg-name>

Here,

* vnffgd-name - VNFFGD to use to instantiate this VNFFG
* param-file  - Parameter file in Yaml.
* vnf-mapping - Allows a list of logical VNFD to VNF instance mapping
* symmetrical - True/False

VNF Mapping is used to declare which exact VNF instance to be used for
each VNF in the Forwarding Path. The following command would list VNFs
in Tacker and then map each VNFD defined in the VNFFGD Forwarding Path
to the desired VNF instance:

.. code-block:: console

   tacker vnf-list

   +--------------------------------------+------+---------------------------+--------+--------------------------------------+--------------------------------------+
   | id                                   | name | mgmt_url                  | status | vim_id                               | vnfd_id                              |
   +--------------------------------------+------+---------------------------+--------+--------------------------------------+--------------------------------------+
   | 7168062e-9fa1-4203-8cb7-f5c99ff3ee1b | VNF2 | {"VDU1": "192.168.1.5"}   | ACTIVE | 0e70ec23-6f32-420a-a039-2cdb2c20c329 | ea842879-5a7a-4f29-a8b0-528b2ad3b027 |
   | 91e32c20-6d1f-47a4-9ba7-08f5e5effe07 | VNF1 | {"VDU1": "192.168.1.7"}   | ACTIVE | 0e70ec23-6f32-420a-a039-2cdb2c20c329 | 27795330-62a7-406d-9443-2daad76e674b |
   +--------------------------------------+------+---------------------------+--------+--------------------------------------+--------------------------------------+

   tacker vnffg-create --vnffgd-name myvnffgd --vnf-mapping \
      VNFD1:'91e32c20-6d1f-47a4-9ba7-08f5e5effe07',VNF2:'7168062e-9fa1-4203-8cb7-f5c99ff3ee1b' myvnffg

Alternatively, if no vnf-mapping is provided then Tacker VNFFG will attempt
to search for VNF instances derived from the given VNFDs in the VNFFGD.  If
multiple VNF instances exist for a given VNFD, the VNF instance chosen to be
used in the VNFFG is done at random.

The symmetrical argument is used to indicate if reverse traffic should also
flow through the path.  This creates an extra classifier to ensure return
traffic flows through the chain in a reverse path, otherwise this traffic
routed normally and does not enter the VNFFG.

.. note::

   Enabling symmetrical is not currently supported by the OpenStack VIM
   driver

Parameters for VNFFGD template
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Similar to TOSCA VNFD template, any value of VNFFGD template can be
parameterized. Once parameterized different values can be passed while
instantiating the forwarding graph using the same VNFFGD template.
The value of a parameterized attribute can be specified like *{get_input foo}*
in the TOSCA VNFFGD template. The corresponding param-file in the following
YAML format can be provided in the vnffg-create command,

.. code-block:: console

  {
    foo: bar
  }

VNFFG command with parameter file:


.. code-block:: console

   tacker vnffg-create --vnffgd-name vnffgd-param --vnf-mapping VNFD1:'91e32c20-6d1f-47a4-9ba7-08f5e5effe07',\
   VNFD2:'7168062e-9fa1-4203-8cb7-f5c99ff3ee1b' --param-file vnffg-param-file.yaml myvnffg


See `VNFFGD template samples with parameter support <https://github.com/
openstack/tacker/tree/master/samples/tosca-templates/vnffgd>`_.

Viewing a VNFFG
~~~~~~~~~~~~~~~

A VNFFG once created is instantiated as multiple sub-components.  These
components include the VNFFG itself, which relies on a Network Forwarding
Path (NFP).  The NFP is then composed of a Service Function Chain (SFC) and
a Classifier.  The main command to view a VNFFG is 'tacker vnffg-show,
however there are several commands available in order to view the
sub-components for a rendered VNFFG:

.. code-block:: console

   tacker nfp-list
   tacker nfp-show <nfp id>
   tacker chain-list
   tacker chain-show <chain id>
   tacker classifier-list
   tacker classifier-show <classifier id>

Known Issues and Limitations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Match criteria requires 'network_src_port_id'
- Only one Forwarding Path allowed per VNFFGD
- Matching on criteria with postfix 'name' does not work, for example
  'network_name'
- NSH attributes not yet supported
- Symmetrical is not supported by driver yet

.. _VNF1: https://github.com/openstack/tacker/blob/master/samples/tosca-templates/vnffgd/tosca-vnffg-vnfd1.yaml
.. _VNF2: https://github.com/openstack/tacker/blob/master/samples/tosca-templates/vnffgd/tosca-vnffg-vnfd2.yaml
