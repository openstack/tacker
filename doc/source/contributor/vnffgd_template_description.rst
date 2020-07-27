VNFFG Descriptor Template Guide
===============================
Overview
--------

This document explains VNFFGD template structure and its various fields based
on TOSCA standards V1.0 [#f1]_.

For VNFFG usage, please refer to the document available at [#f6]_.

The behavioural and deployment information of a VNFFG in Tacker is defined in a
template known as VNFFG Descriptor (VNFFGD). The template is based on TOSCA
standards and is written in YAML. It is on-boarded in a VNFFG catalog.

Each VNFFGD template will have below fields:

.. code-block:: yaml

    tosca_definitions_version:
       This defines the TOSCA definition version on which the template is based.
       The current version being tosca_simple_profile_for_nfv_1_0_0.

    tosca_default_namespace:
       This is optional. It mentions default namespace which includes schema,
       types version etc.

    description:
       A short description about the template.

    metadata:
       template_name: A name to be given to the template.

    topology_template:
       Describes the topology of the VNFFG under node_template field.
       node_template:
           Describes node types of a VNFFG.
           FP:
               Describes properties and path of a Forwarding Path.
       groups:
           Describes groupings of nodes that have an implied relationship.
           VNFFG:
               Describes properties and members of a VNF Forwarding Graph.

..

For examples, please refer sample VNFFGD templates available at GitHub [#f2]_.

Node types
----------
For Tacker purposes a VNFFGD only includes **Forwarding Path**. In a full
Network Services Descriptor (NSD), it would include information about each
VNFD as well. However until that implementation, VNFD is described in a
separate template. Only a single Forwarding Path is currently supported.
**node_templates** is a child of **topology_template**.

Forwarding Path
---------------
Forwarding Path is a required entry in a VNFFGD. It describes the chain as
well as the classifier that will eventually be created to form a path
through a set of VNFs.

:type:
    tosca.nodes.nfv.FP.Tacker
:properties:
    Describes the properties of a FP. These include id (path ID), policy
    (traffic match policy to flow through the path), and path (chain of
    VNFs/Connection Points). A complete list of VNFFG properties currently
    supported by Tacker are listed here [#f3]_ under **properties** section of
    **tosca.nodes.nfv.FP.TackerV2** field.

Specifying FP properties
^^^^^^^^^^^^^^^^^^^^^^^^
An example FP shown below:

.. code-block:: yaml

  node_templates:

    Forwarding_path1:
      type: tosca.nodes.nfv.FP.TackerV2
      description: creates path (CP12->CP22)
      properties:
        id: 51
        policy:
          type: ACL
          criteria:
            - name: block_tcp
              classifier:
                network_src_port_id: 640dfd77-c92b-45a3-b8fc-22712de480e1
                destination_port_range: 80-1024
                ip_proto: 6
                ip_dst_prefix: 192.168.1.2/24
          path:
            - forwarder: VNFD1
              capability: CP12
            - forwarder: VNFD2
              capability: CP22

..

Or, you can add more named classifiers like below since the current Tacker's
TOSCA template support multiple named classifiers

.. code-block:: yaml

  node_templates:

    Forwarding_path1:
      type: tosca.nodes.nfv.FP.TackerV2
      description: creates path (CP12->CP22)
      properties:
        id: 51
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
          path:
            - forwarder: VNFD1
              capability: CP12
            - forwarder: VNFD2
              capability: CP22

..

id
""
ID from the above example is used to identify the path. This path ID will
be used in future implementations of Network Service Header (NSH) to
identify paths via the Service Path Identifier (SPI) attribute.

policy
""""""
Policy defines the type of match policy that will be used to distinguish
which traffic should enter this Forwarding Path. The only currently
supported type is ACL (access-list).
Please reference tosca.nfv.datatypes.aclType [#f4]_ under **properties**
section for more information on supported match criteria.

path
""""
Path defines an ordered list of nodes to traverse in a Forwarding Path. Each
node is really a logical port, which is defined in the path as a Connection
Point (CP) belonging to a specific VNFD. It is not necessary at VNFFGD
creation time to have predefined these VNFDs used in the path. They may be
created later. Up to 2 CPs may be listed (in order) per VNFD. If 2 are
listed, the first will be considered the ingress port for traffic and the
second will be the egress. If only one port is provided, then it will be
interpreted as both the ingress and egress port for traffic.


Groups
------
In Tacker and TOSCA, the VNFFG itself is described in this section. There
may only be a single VNFFG described in each VNFFGD under this section.

VNFFG
-----
VNFFG maps the Forwarding Path to other node types defined in the properties
section.

:type:
    tosca.groups.nfv.VNFFG
:properties:
    Describes the properties of a VNFFG. These include vendor, version,
    dependent_virtual_link, connection_points, constituent_vnfs.
    . A complete list of VNFFG properties currently
    supported by Tacker are listed in TOSCA [#f5]_.
:members:
    A list of Forwarding Paths which belong to this VNFFG. At the moment
    only one is supported.

Specifying VNFFG properties and members
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
An example VNFFG shown below:

.. code-block:: yaml

  groups:
    VNFFG1:
      type: tosca.groups.nfv.VNFFG
      description: HTTP to Corporate Net
      properties:
        vendor: tacker
        version: 1.0
        number_of_endpoints: 2
        dependent_virtual_link: [VL1,VL2,VL3]
        connection_point: [CP1,CP2]
        constituent_vnfs: [VNF1,VNF2]
      members: [Forwarding_path1]

..

number_of_endpoints
"""""""""""""""""""
Number of CPs included in this VNFFG.

dependent_virtual_link
""""""""""""""""""""""
The Virtual Link Descriptors (VLD) that connect each VNF/CP in this
Forwarding Graph.

connection_point
""""""""""""""""
List of Connection Points defined in the Forwarding Path.

constituent_vnfs
""""""""""""""""
List of VNFD names used in this Forwarding Graph (also defined in Forwarding
Path).

Summary
-------
To summarize VNFFGD is written in YAML and describes a VNFFG topology. It is
composed of a Forwarding Path and a VNFFG. A full VNFFGD is shown below:

.. code-block:: yaml

   tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0

   description: Sample VNFFG template

   topology_template:

     node_templates:

       Forwarding_path1:
         type: tosca.nodes.nfv.FP.TackerV2
         description: creates path (CP12->CP22)
         properties:
           id: 51
           policy:
             type: ACL
             criteria:
               - name: block_tcp
                 classifier:
                   network_src_port_id: 640dfd77-c92b-45a3-b8fc-22712de480e1
                   destination_port_range: 80-1024
                   ip_proto: 6
                   ip_dst_prefix: 192.168.1.2/24
           path:
             - forwarder: VNFD1
               capability: CP12
             - forwarder: VNFD2
               capability: CP22

     groups:
       VNFFG1:
         type: tosca.groups.nfv.VNFFG
         description: HTTP to Corporate Net
         properties:
           vendor: tacker
           version: 1.0
           number_of_endpoints: 2
           dependent_virtual_link: [VL12,VL22]
           connection_point: [CP12,CP22]
           constituent_vnfs: [VNFD1,VNFD2]
         members: [Forwarding_path1]

..

.. rubric:: Footnotes

.. [#f1] http://docs.oasis-open.org/tosca/tosca-nfv/v1.0/tosca-nfv-v1.0.html
.. [#f2] https://github.com/openstack/tacker/tree/master/samples/tosca-templates/vnffgd
.. [#f3] https://opendev.org/openstack/tacker/src/branch/master/tacker/tosca/lib/tacker_nfv_defs.yaml
.. [#f4] https://opendev.org/openstack/tacker/src/branch/master/tacker/tosca/lib/tacker_nfv_defs.yaml
.. [#f5] http://docs.oasis-open.org/tosca/tosca-nfv/v1.0/csd03/tosca-nfv-v1.0-csd03.html#_Toc447714727
.. [#f6] https://docs.openstack.org/tacker/latest/user/vnffg_usage_guide.html
