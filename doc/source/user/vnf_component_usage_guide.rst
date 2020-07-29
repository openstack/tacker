========================
VNF Component in Tacker
========================

This section will cover how to deploy `vnf component` in Tacker with the
examples of how to write VNF descriptors.


Sample TOSCA with vnfc
=======================

The following example shows vnfc resource using TOSCA template.
The target (VDU1) of the 'firewall_vnfc' in this example need to be
described firstly like other TOSCA templates in Tacker.

.. code-block:: yaml

     topology_template:
       node_templates:
         firewall_vnfc:
           type: tosca.nodes.nfv.VNFC.Tacker
           requirements:
             - host: VDU1
           interfaces:
             Standard:
               create: install_vnfc.sh

Every vnfc node must be of type 'tosca.nodes.nfv.VNFC.Tacker'. It takes
two parameters:

1) requirements: This node will accept list of hosts on which VNFC has to be
   installed.
2) interfaces: This node will accept the absolute path of shell script to be run
   on the VDUs. This shell script should reside in the machine where tacker
   server is running.


How to setup environment
~~~~~~~~~~~~~~~~~~~~~~~~~
To make use of VNFC in Tacker, we have to upload the image to the glance in
which heat-config and heat-config agents are installed. The installation steps
can be referred `here <https://docs.openstack.org/heat-agents/latest/
install/building_image.html>`_. The tool
'tools/vnfc/build_image.sh' can be used to generate such a kind of image.

Currently VNFC feature works by using `heat software config <https://docs.openstack.org/heat/latest/
template_guide/software_deployment.html#software-config-resources>`_  which
makes use of heat API.

So the glance images which has heat-config agents installed are only to be
passed to VDU.

Known Limitations
~~~~~~~~~~~~~~~~~
1) Only one VNFC is supported for one VDU. Multiple VNFC per VDU will
   be introduced in future.
2) The shell script for vnfc has to be placed in the machine where tacker
   server is running.
