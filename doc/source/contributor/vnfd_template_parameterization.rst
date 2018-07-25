VNFD Template Parameterization
==============================

Overview
--------

Parameterization allows for the ability to use a single VNFD to be deployed
multiple times with different values for the VDU parameters provided at
deploy time. In contrast, a non-parameterized VNFD has static values
for the parameters that might limit the number of concurrent VNFs that can be
deployed using a single VNFD. For example, deploying an instance of a
non-parameterized template that has fixed IP addresses specified for network
interface a second time without deleting the first instance of VNF would lead
to an error.

Non-parameterized VNFD template
-------------------------------

Find below an example of a non-parameterized VNFD where the text italicized
are the VDU parameters and text in bold are the values for those VDU
parameters that get applied to the VDU when this template is deployed.
The next section will illustrate how the below non-parameterized template
can be parameterized and re-used for deploying multiple VNFs.

Here is the sample template:

.. code-block:: yaml

   tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0

   description: VNF TOSCA template with input parameters

   metadata:
     template_name: sample-tosca-vnfd

   topology_template:

     node_templates:
       VDU1:
         type: tosca.nodes.nfv.VDU.Tacker
         properties:
           image: cirros-0.4.0-x86_64-disk
           flavor: m1.tiny
           availability_zone: nova
           mgmt_driver: noop
           config: |
             param0: key1
             param1: key2

       CP1:
         type: tosca.nodes.nfv.CP.Tacker
         properties:
           management: True
           anti_spoofing_protection: false
         requirements:
           - virtualLink:
               node: VL1
           - virtualBinding:
               node: VDU1

       CP2:
         type: tosca.nodes.nfv.CP.Tacker
         properties:
           anti_spoofing_protection: false
         requirements:
           - virtualLink:
               node: VL2
           - virtualBinding:
               node: VDU1

       CP3:
         type: tosca.nodes.nfv.CP.Tacker
         properties:
           anti_spoofing_protection: false
         requirements:
           - virtualLink:
               node: VL3
           - virtualBinding:
               node: VDU1

       VL1:
         type: tosca.nodes.nfv.VL
         properties:
           network_name: net_mgmt
           vendor: Tacker

       VL2:
         type: tosca.nodes.nfv.VL
         properties:
           network_name: net0
           vendor: Tacker

       VL3:
         type: tosca.nodes.nfv.VL
         properties:
           network_name: net1
           vendor: Tacker


Parameterized VNFD template
---------------------------
This section will walk through parameterizing the template in above section
for re-use and allow for deploying multiple VNFs with the same template.
(Note: All the parameters italicized in the above template could be
parameterized to accept values at deploy time).
For the current illustration purpose, we will assume that an end user would
want to be able to supply different values for the parameters
**image_name**, **flavor**, **network**, **management**, **pkt_in_network**,
**pkt_out_network**, **vendor**, during each deploy of the VNF.

The next step is to substitute the identified parameter values that will be
provided at deploy time with { get_input: <param_name>}. For example, the
instance_type: **cirros-0.4.0-x86_64-disk** would now be replaced as:
**image: {get_input: image_name}**. The **get_input** is a reserved
keyword in the template that indicates value will be supplied at deploy time
for the parameter instance_type. The **image_name** is the variable that will
hold the value for the parameter **image** in a parameters value file
that will be supplied at VNF deploy time.

The template in above section will look like below when parameterized for
**image_name**, **flavor**, **network**, **management** and remaining
parameters.

Here is the sample template:

.. code-block:: yaml

   tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0

   description: VNF TOSCA template with input parameters

   metadata:
     template_name: sample-tosca-vnfd

   topology_template:
     inputs:
       image_name:
         type: string
         description: Image Name

       flavor:
         type: string
         description: Flavor Information

       zone:
         type: string
         description: Zone Information

       network:
         type: string
         description: management network

       management:
         type: string
         description: management network

       pkt_in_network:
         type: string
         description: In network

       pkt_out_network:
         type: string
         description: Out network

       vendor:
         type: string
         description: Vendor information

     node_templates:
       VDU1:
         type: tosca.nodes.nfv.VDU.Tacker
         properties:
           image: { get_input: image_name}
           flavor: {get_input: flavor}
           availability_zone: { get_input: zone }
           mgmt_driver: noop
           config: |
             param0: key1
             param1: key2

       CP1:
         type: tosca.nodes.nfv.CP.Tacker
         properties:
           management: { get_input: management }
           anti_spoofing_protection: false
         requirements:
           - virtualLink:
               node: VL1
           - virtualBinding:
               node: VDU1

       CP2:
         type: tosca.nodes.nfv.CP.Tacker
         properties:
           anti_spoofing_protection: false
         requirements:
           - virtualLink:
               node: VL2
           - virtualBinding:
               node: VDU1

       CP3:
         type: tosca.nodes.nfv.CP.Tacker
         properties:
           anti_spoofing_protection: false
         requirements:
           - virtualLink:
               node: VL3
           - virtualBinding:
               node: VDU1

       VL1:
         type: tosca.nodes.nfv.VL
         properties:
           network_name: { get_input: network }
           vendor: {get_input: vendor}

       VL2:
         type: tosca.nodes.nfv.VL
         properties:
           network_name: { get_input: pkt_in_network }
           vendor: {get_input: vendor}

       VL3:
         type: tosca.nodes.nfv.VL
         properties:
           network_name: { get_input: pkt_out_network }
           vendor: {get_input: vendor}


Parameter values file at VNF deploy
-----------------------------------
The below illustrates the parameters value file to be supplied containing the
values to be substituted for the above parameterized template above during
VNF deploy.

.. code-block:: yaml

    image_name: cirros-0.4.0-x86_64-disk
    flavor: m1.tiny
    zone: nova
    network: net_mgmt
    management: True
    pkt_in_network: net0
    pkt_out_network: net1
    vendor: Tacker


.. note::

   IP address values for network interfaces should be in the below format
   in the parameters values file:

   param_name_value:
     \- xxx.xxx.xxx.xxx


Key Summary
-----------
#. Parameterize your VNFD if you want to re-use for multiple VNF deployments.
#. Identify parameters that would need to be provided values at deploy time
   and substitute value in VNFD template with {get_input: <param_value_name>},
   where 'param_value_name' is the name of the variable that holds the value
   in the parameters value file.
#. Supply a parameters value file in yaml format each time during VNF
   deployment with different values for the parameters.
#. An example of a OpenStackClient vnf creation command specifying a
   parameterized template and parameter values file would like below:

   .. code-block:: console

      openstack vnf create --vnfd-name <vnfd_name> --param-file <param_yaml_file> <vnf_name>

#. Specifying a parameter values file during VNF creation is also supported in
   Horizon UI.
#. Sample VNFD parameterized templates and parameter values files can be found
   at https://github.com/openstack/tacker/tree/master/samples/tosca-templates/vnfd.
