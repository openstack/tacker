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
<https://github.com/openstack/tacker/tree/doc/source/devref
/vnffgd_template_description.rst>`_ on VNFFGD to learn more about
how a VNFFGD is defined.

After creating a VNFFGD, a VNFFG is instantiated by a separate Tacker
command.  This action will build the chain and classifier necessary to
realize the VNFFG.

Prerequisites
~~~~~~~~~~~~~

VNFFG with OpenStack VIM relies on Neutron Networking-sfc to create SFC and
Classifiers.  Therefore it is required to install `networking-sfc
<https://github.com/openstack/networking-sfc>`_ project
in order to use Tacker VNFFG.  Networking-sfc also requires at least OVS 2.5
.0, so also ensure that is installed.  See the full `Networking-sfc guide
<https://wiki.openstack.org/wiki/Neutron/ServiceInsertionAndChaining>`_.

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


This is required due to a limitation of Neutron networking-sfc and only
applies to an OpenStack VIM.

Tacker provides the following CLI to create a VNFFGD:

.. code-block:: console

   tacker vnffgd-create --vnffgd-file <vnffgd file> <vnffgd name>


Creating the VNFFG
~~~~~~~~~~~~~~~~~~

To create a VNFFG, you must have first created VNF instances of the same
VNFD types listed in the VNFFGD.  Failure to do so will result in error when
trying to create a VNFFG.  Note, the VNFD you define **must** include the
same Connection Point definitions as the ones you declared in your VNFFGD.

Refer the 'Getting Started' link below on how to create a VNFD and deploy a
VNF:
http://docs.openstack.org/developer/tacker/install/getting_started.html

Tacker provides the following CLI to create VNFFG:

.. code-block:: console

   tacker vnffg-create --vnffgd-name <vnffgd name> \
          --vnf-mapping <vnf mapping> --symmetrical <boolean>

If you use a parameterized vnffg template:

.. code-block:: console

   tacker vnffg-create --vnffgd-name <vnffgd name> \
     --param-file <param file> --vnf-mapping <vnf mapping> \
     --symmetrical <boolean>

Here,

* vnffgd-name - VNFFGD to use to instantiate this VNFFG
* param-file  - Parameter file in Yaml.
* vnf-mapping - Allows a list of logical VNFD to VNF instance mapping
* symmetrical - True/False

VNF Mapping is used to declare which exact VNF instance to be used for
each VNF in the Forwarding Path.  For example, imagine a Forwarding Path
'path' which includes VNF1 and VNF2 VNFDs.  Two VNF instances already exist
(one from each VNFD): '91e32c20-6d1f-47a4-9ba7-08f5e5effe07',
'7168062e-9fa1-4203-8cb7-f5c99ff3ee1b'.  The following command would then
map each VNFD defined in the VNFFGD Forwarding Path to the desired VNF
instance:

.. code-block:: console

   tacker vnffg-create --vnffgd-name myvnffgd \
   --vnf-mapping VNF1:'91e32c20-6d1f-47a4-9ba7-08f5e5effe07', \
   VNF2:'7168062e-9fa1-4203-8cb7-f5c99ff3ee1b'

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

::

  {
    foo: bar
  }

VNFFG command with parameter file:

  **tacker vnffg-create --vnffgd-name myvnffgd**
  **--vnf-mapping VNF1:'91e32c20-6d1f-47a4-9ba7-08f5e5effe07',**
  **VNF2:'7168062e-9fa1-4203-8cb7-f5c99ff3ee1b'**
  **--param-file cust-site-x-param.yaml**


See `VNFFGD template samples with paramter support <https://github.com/
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
