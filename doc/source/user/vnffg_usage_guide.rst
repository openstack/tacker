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

.. _ref-vnffg:

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
<https://opendev.org/openstack/tacker/src/branch/master/doc/source/contributor
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
<https://docs.openstack.org/networking-sfc/latest/>`_.

A simple example of a service chain would be one that forces all traffic
from HTTP client to HTTP server to go through VNFs that was created by
VNFFG.

Firstly, HTTP client and HTTP server must be launched.

.. code-block:: console

   net_id=$(openstack network list | grep net0 | awk '{print $2}')

   openstack server create --flavor m1.tiny --image cirros-0.4.0-x86_64-disk \
   --nic net-id=$net_id http_client

   openstack server create --flavor m1.tiny --image cirros-0.4.0-x86_64-disk \
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
          - name: block_tcp
            classifier:
              network_src_port_id: 640dfd77-c92b-45a3-b8fc-22712de480e1
              destination_port_range: 80-1024
              ip_proto: 6
              ip_dst_prefix: 192.168.1.2/24
          - name: block_udp
            classifier:
              network_src_port_id: 640dfd77-c92b-45a3-b8fc-22712de480eda
              destination_port_range: 80-1024
              ip_proto: 17
              ip_dst_prefix: 192.168.2.2/24

In above example, VNFFG will have 2 flow classifier. List flow classifiers
are defined in list of criteria.

You can get network_src_port_id, network_dest_port_id and destination IP
address through OpenStack commands like bellow:

.. code-block:: console

   client_ip=$(openstack server list | grep http_client | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')

   network_source_port_id=$(openstack port list | grep $client_ip | awk '{print $2}')

   ip_dst=$(openstack server list | grep http_server | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')

   network_dest_port_id=$(openstack port list | grep $ip_dst | awk '{print $2}')

This is required due to a limitation of Neutron networking-sfc and only
applies to an OpenStack VIM.

Two "network_dst_port_id" and "ip_dst_prefix" parameters must be set when you
want to create VNFFG with "symmetrical" feature. If you want to create VNFFG
without "symmetrical", you can omit "network_dst_port_id" and "ip_dst_prefix".

.. code-block:: yaml

    Forwarding_path1:
      type: tosca.nodes.nfv.FP.TackerV2
      description: creates path (CP12->CP22)
      properties:
        id: 51
        symmetrical: true
        correlation: nsh
        policy:
          type: ACL
          criteria:
            - name: block_tcp
              classifier:
                network_src_port_id: 640dfd77-c92b-45a3-b8fc-22712de480e1
                network_dst_port_id: ea206bba-7083-4364-a9f1-c0b7fdf61b6e
                ip_dst_prefix: 192.168.1.2/24
                destination_port_range: 80-1024
                ip_proto: 6
        path:
          - forwarder: VNFD1
            capability: CP12
            sfc_encap: True
          - forwarder: VNFD2
            capability: CP22
            sfc_encap: False

In above template, users can set **symmetrical** in properties of a forwarding
path create symmetrical VNFFG. If this property is not set, **symmetrical**
will be specified by **--symmetrical** in create VNFFG command (default value
is False).

In other hand, by setting **correlation** in properties let users can choose
SFC encapsulation between MPLS or NSH (default: MPLS). If sfc_encap is True,
port pair's correlation is set to same value with **correlation** to make use
of **correlation** that SFC Encapsulation provides, otherwise port pair's
correlation is set to None to install SFC proxy `SFC_PROXY`_. Detailed
information about SFC encapsulation can be found in Networking-SFC project
`SFC_ENCAPSULATION`_

You can use the sample VNFFGD template for symmetrical feature (in port chain)
such as this `link <https://github.com/openstack/tacker/tree/master/samples/
tosca-templates/vnffgd/tosca-vnffgd-symmetrical-sample.yaml>`_.

The symmetrical argument is used to indicate if reverse traffic should also
flow through the path.  This creates an extra classifier to ensure return
traffic flows through the chain in a reverse path, otherwise this traffic
routed normally and does not enter the VNFFG.

Tacker provides the following OpenStackClient CLI to create a VNFFGD:

.. code-block:: console

   openstack vnf graph descriptor create --vnffgd-file <vnffgd-file> <vnffgd-name>


Creating the VNFFG
~~~~~~~~~~~~~~~~~~

To create a VNFFG, you must have first created VNF instances of the same
VNFD types listed in the VNFFGD.  Failure to do so will result in error when
trying to create a VNFFG.  Note, the VNFD you define **must** include the
same Connection Point definitions as the ones you declared in your VNFFGD.

.. code-block:: console

   openstack vnf descriptor create --vnfd-file tosca-vnffg-vnfd1.yaml VNFD1
   openstack vnf create --vnfd-name VNFD1 VNF1

   openstack vnf descriptor create --vnfd-file tosca-vnffg-vnfd2.yaml VNFD2
   openstack vnf create --vnfd-name VNFD2 VNF2

Refer the 'Getting Started' link below on how to create a VNFD and deploy
2 VNFs: `VNF1`_ and `VNF2`_.

https://docs.openstack.org/tacker/latest/install/getting_started.html

Tacker provides the following OpenStackClient CLI to create VNFFG from VNFFGD:

.. code-block:: console

   openstack vnf graph create --vnffgd-name <vnffgd-name> --vnf-mapping <vnf-mapping> --symmetrical <vnffg-name>

or you can create directly VNFFG from vnffgd template without initiating
VNFFGD.

.. code-block:: console

   openstack vnf graph create --vnffgd-template <vnffgd-template> --vnf-mapping <vnf-mapping> \
   --symmetrical <vnffg-name>

If you use a parameterized vnffg template:

.. code-block:: console

   openstack vnf graph create --vnffgd-name <vnffgd-name> --param-file <param-file> --vnf-mapping <vnf-mapping> \
   --symmetrical <vnffg-name>

Here,

* vnffgd-name - VNFFGD to use to instantiate this VNFFG
* param-file  - Parameter file in Yaml.
* vnf-mapping - Allows a list of logical VNFD to VNF instance mapping
* symmetrical - If --symmetrical is present, symmetrical is True
  (default: False - The **symmectical** is set in template has higher priority)

VNF Mapping is used to declare which exact VNF instance to be used for
each VNF in the Forwarding Path. The following command would list VNFs
in Tacker and then map each VNFD defined in the VNFFGD Forwarding Path
to the desired VNF instance:

.. code-block:: console

   openstack vnf list

   +--------------------------------------+------+---------------------------+--------+--------------------------------------+--------------------------------------+
   | id                                   | name | mgmt_ip_address           | status | vim_id                               | vnfd_id                              |
   +--------------------------------------+------+---------------------------+--------+--------------------------------------+--------------------------------------+
   | 7168062e-9fa1-4203-8cb7-f5c99ff3ee1b | VNF2 | {"VDU1": "192.168.1.5"}   | ACTIVE | 0e70ec23-6f32-420a-a039-2cdb2c20c329 | ea842879-5a7a-4f29-a8b0-528b2ad3b027 |
   | 91e32c20-6d1f-47a4-9ba7-08f5e5effe07 | VNF1 | {"VDU1": "192.168.1.7"}   | ACTIVE | 0e70ec23-6f32-420a-a039-2cdb2c20c329 | 27795330-62a7-406d-9443-2daad76e674b |
   +--------------------------------------+------+---------------------------+--------+--------------------------------------+--------------------------------------+

   openstack vnf graph create --vnffgd-name myvnffgd --vnf-mapping \
   VNFD1:'91e32c20-6d1f-47a4-9ba7-08f5e5effe07',VNFD2:'7168062e-9fa1-4203-8cb7-f5c99ff3ee1b' --symmetrical myvnffg

Alternatively, if no vnf-mapping is provided then Tacker VNFFG will attempt
to search for VNF instances derived from the given VNFDs in the VNFFGD.  If
multiple VNF instances exist for a given VNFD, the VNF instance chosen to be
used in the VNFFG is done at random.

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

   openstack vnf graph create --vnffgd-name vnffgd-param --vnf-mapping VNFD1:'91e32c20-6d1f-47a4-9ba7-08f5e5effe07',\
   VNFD2:'7168062e-9fa1-4203-8cb7-f5c99ff3ee1b' --param-file vnffg-param-file.yaml myvnffg


See `VNFFGD template samples with parameter support <https://github.com/
openstack/tacker/tree/master/samples/tosca-templates/vnffgd>`_.

Viewing a VNFFG
~~~~~~~~~~~~~~~

A VNFFG once created is instantiated as multiple sub-components.  These
components include the VNFFG itself, which relies on a Network Forwarding
Path (NFP).  The NFP is then composed of a Service Function Chain (SFC) and
a Classifier.  The main command to view a VNFFG is 'openstack vnf graph show',
however there are several commands available in order to view the
sub-components for a rendered VNFFG:

.. code-block:: console

   openstack vnf network forwarding path list
   openstack vnf network forwarding path show <nfp id>
   openstack vnf chain list
   openstack vnf chain show <chain id>
   openstack vnf classifier list
   openstack vnf classifier show <classifier id>

Updating the VNFFG
~~~~~~~~~~~~~~~~~~

To update an already created VNFFG template the user needs to locate the VNFFG
which wants to update. To do so the following command is getting executed:

Using the below command query the list of existing VNFFG templates.

.. code-block:: console

    openstack vnf graph list

    +--------------------+---------+--------+-------------------------------------+
    |    ID              | Name    | Status | VNFFGD ID                           |
    +--------------------+------------------+-------------------------------------+
    | f4438511-e33d-43df-|         |        |                                     |
    | 95d9-0199253db72e  | myvnffg | ACTIVE | bd7829bf-85de-4f3b-960a-8482028bfb34|
    +--------------------+---------+--------+-------------+--------+--------------+

To verify result, user can get information of port chain in networking-sfc:

.. code-block:: console

    $ openstack sfc port chain list --fit-width

    +-----------------------+-------------------+-----------------------+-----------------------+-----------------------+----------+
    | ID                    | Name              | Port Pair Groups      | Flow Classifiers      | Chain Parameters      | Chain ID |
    +-----------------------+-------------------+-----------------------+-----------------------+-----------------------+----------+
    | 60d1a3ee-8455-415e-   | VNFFG1-port-chain | [u'87d7d4c2-d2d1-4a99 | [u'02fa422c-9f40-4092 | {u'symmetric': False, |       51 |
    | 8ff1-e0b6b9f9f277     |                   | -81fb-f3d5f51dd919',  | -a8b0-c04355116e5e']  | u'correlation':       |          |
    |                       |                   | u'81213b4c-0e5e-445d- |                       | u'nsh'}               |          |
    |                       |                   | add6-dea2bf55078f']   |                       |                       |          |
    +-----------------------+-------------------+-----------------------+-----------------------+-----------------------+----------+

After the user located the VNFFG the subsequent action is to update it.
Based on the appropriate choice, update VNFFG template.
Currently two choices are supported for the update of an existing VNFFG.
The first choice is the use of the vnf-mapping parameter.
The user needs to use a VNF which is actually derived from the VNFD which
is going to be used in the vnf-mapping parameter.
If the user is not sure which VNF was used for the mapping during the time
of the VNFFG creation he can execute:

Execute the below command to query the VNF that was used in mapping at the time
of VNFFG creation.

.. code-block:: console

   openstack vnf graph show myvnffg

After user determined which VNF is used and which VNF is going to be used
in the update procedure he can execute:

To update the VNF mappings to VNFFG, execute the below command

.. code-block:: console

   openstack vnf graph set --vnf-mapping VNFD1:vnf1,VNFD2:vnf2 myvnffg

   Updated vnffg: myvnffg

The second choice is the use of the vnffgd-template parameter.
The aforementioned parameter provides the ability to use a vnffgd formated yaml
template which contains all the elements and their parameters that Tacker is
going to apply to its ecosystem.

Below there is an example usage of updating an existing VNFFG:

Assuming that the existing VNFFG in the system that we want to update is
derived from the following VNFFGD template.

.. code-block:: yaml

   tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0

   description: Sample VNFFG template

   topology_template:

     node_templates:

       Forwarding_path1:
         type: tosca.nodes.nfv.FP.TackerV2
         description: creates path (CP1)
         properties:
           id: 51
           symmetrical: false
           policy:
             type: ACL
             criteria:
               - name: block_udp
                 classifier:
                   destination_port_range: 80-1024
                   ip_proto: 17
           path:
             - forwarder: VNFD3
               capability: CP1

     groups:
       VNFFG1:
         type: tosca.groups.nfv.VNFFG
         description: UDP to Corporate Net
         properties:
           vendor: tacker
           version: 1.0
           number_of_endpoints: 1
           dependent_virtual_link: [VL1]
           connection_point: [CP1]
           constituent_vnfs: [VNFD3]
         members: [Forwarding_path1]

By using the below VNFFGD template we can update the existing VNFFG.

.. code-block:: yaml

   tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0

   description: Sample VNFFG template

   topology_template:

     node_templates:

       Forwarding_path2:
         type: tosca.nodes.nfv.FP.TackerV2
         description: creates path (CP1->CP2)
         properties:
           id: 52
           symmetrical: false
           correlation: nsh
           policy:
             type: ACL
             criteria:
               - name: block_tcp
                 classifier:
                   network_src_port_id: 640dfd77-c92b-45a3-b8fc-22712de480e1
                   destination_port_range: 22-28
                   ip_proto: 6
                   ip_dst_prefix: 192.168.1.2/24
           path:
             - forwarder: VNFD1
               capability: CP1
               sfc_encap: True
             - forwarder: VNFD2
               capability: CP2
               sfc_encap: False

     groups:
       VNFFG1:
         type: tosca.groups.nfv.VNFFG
         description: SSH to Corporate Net
         properties:
           vendor: tacker
           version: 1.0
           number_of_endpoints: 2
           dependent_virtual_link: [VL1,VL2]
           connection_point: [CP1,CP2]
           constituent_vnfs: [VNFD1,VNFD2]
         members: [Forwarding_path2]

The above template informs Tacker to update the current classifier,NFP and
path (chain) with the ones that are described in that template. After the
completion of the update procedure the new NFP will be named 'Forwarding_path2'
with an id of '52',the classifier in that NFP will be named 'block_tcp'
and will have the corresponding match criteria and the updated chain will
be consisted by two NVFs which are derived from VNFD1,VNFD2 VNFDs.

To update the existing VNFFG through the vnffgd-template parameter, execute the
below command:

.. code-block:: console

   openstack vnf graph set --vnffgd-template myvnffgd.yaml myvnffg

   Updated vnffg: myvnffg

Of course the above update VNFFG's choices can be combined in a single command.

.. code-block:: console

   openstack vnf graph set --vnf-mapping VNFD1:vnf1,VNFD2:vnf2 --vnffgd-template myvnffgd.yaml myvnffg

   Updated vnffg: myvnffg

Known Issues and Limitations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Match criteria requires 'network_src_port_id'
- Only one Forwarding Path allowed per VNFFGD
- Matching on criteria with postfix 'name' does not work, for example
  'network_name'
- NSH attributes not yet supported
- n-sfc Bug: https://bugs.launchpad.net/networking-sfc/+bug/1746686

.. _VNF1: https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnffgd/tosca-vnffg-vnfd1.yaml
.. _VNF2: https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnffgd/tosca-vnffg-vnfd2.yaml
.. _SFC_PROXY: https://tools.ietf.org/html/rfc8300
.. _SFC_ENCAPSULATION: https://docs.openstack.org/networking-sfc/latest/contributor/ietf_sfc_encapsulation.html
