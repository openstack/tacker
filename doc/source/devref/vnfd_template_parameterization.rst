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


template_name: cirros_user_data

description: Cirros image

service_properties:
  Id: cirros

  vendor: ACME

  version: 1

  type:

    \- router

    \- firewall

vdus:
  vdu1:
    id: vdu1

    *vm_image*: **cirros-0.3.4-x86_64-uec**

    *instance_type*: **m1.tiny**

    *service_type*: **firewall**

    *mgmt_driver*: **noop**

    *user_data*: |
        **#!/bin/sh**

        **echo "my hostname is `hostname`" > /tmp/hostname**

        **df -h > /home/cirros/diskinfo**

    *user_data_format*: **RAW**

    network_interfaces:
      management:
        *network*: **net_mgmt**

        management: **True**

        addresses:
          \- 192.168.120.11
      pkt_in:
        *network*: **net0**
      pkt_out:
        *network*: **net1**

    placement_policy:
      *availability_zone*: **nova**

    *auto-scaling*: **noop**

    *monitoring_policy*: **noop**

    *failure_policy*: **noop**

    config:
      *param0*: **key0**

      *param1*: **key1**

Parameterized VNFD template
---------------------------
This section will walk through parameterizing the template in above section
for re-use and allow for deploying multiple VNFs with the same template.
(Note: All the parameters italicized in the above template could be
parameterized to accept values at deploy time).
For the current illustration purpose, we will assume that an end user would
want to be able to supply different values for the parameters
**instance_type**, **user_data**, **user_data_format** and management
interface IP **addresses** during each deploy of the VNF.

The next step is to substitute the identified parameter values that will be
provided at deploy time with { get_input: <param_name>}. For example, the
instance_type: **m1.tiny** would now be replaced as
**instance_type: {get_input: flavor}**. The **get_input** is a reserved
keyword in the template that indicates value will be supplied at deploy time
for the parameter instance_type. The **flavor** is the variable that will
hold the value for the parameter **instance_type** in a parameters value file
that will be supplied at VNF deploy time.

The template in above section will look like below when parameterized for
**instance_type**, **user_data**, **user_data_format** and management
interface IP **addresses**


template_name: cirros_user_data

description: Cirros image

service_properties:
  Id: cirros

  vendor: ACME

  version: 1

  type:

    \- router

    \- firewall

vdus:
  vdu1:
    id: vdu1

    *vm_image*: **cirros-0.3.4-x86_64-uec**

    *instance_type*: **{get_input: flavor }**

    *service_type*: **firewall**

    *mgmt_driver*: **noop**

    *user_data*: **{get_input: user_data_value}**

    *user_data_format*: **{get_input: user_data_format_value}**

    network_interfaces:
      management:
        *network*: **net_mgmt**

        management: **True**

        addresses: **{ get_input: mgmt_ip}**
      pkt_in:
        *network*: **net0**
      pkt_out:
        *network*: **net1**

    placement_policy:
      *availability_zone*: **nova**

    *auto-scaling*: **noop**

    *monitoring_policy*: **noop**

    *failure_policy*: **noop**

    config:
      *param0*: **key0**

      *param1*: **key1**


Parameter values file at VNF deploy
-----------------------------------
The below illustrates the parameters value file to be supplied containing the
values to be substituted for the above parameterized template above during
VNF deploy. Note that the structure of the parameters file follows closely
the structure of the VNFD template. The section below the keyword 'param'
contains the variables and their values that will be substituted in the VNFD
template. Not specifying the keyword 'param' as illustrated below would
result in VNF failing to deploy.


vdus:
  vdu1:
    param:

      flavor: m1.tiny

      mgmt_ip:
        \- 192.168.120.11

      user_data_format_value: RAW

      user_data_value: |
        #!/bin/sh
        echo "my hostname is `hostname`" > /tmp/hostname
        df -h > /home/cirros/diskinfo

Key Summary
-----------
- Parameterize your VNFD if you want to re-use for multiple VNF deployments.
- Identify parameters that would need to be provided values at deploy time
  and substitute value in VNFD template with {get_input: <param_value_name>},
  where 'param_value_name' is the name of the variable that holds the value
  in the parameters value file.
- Supply a parameters value file in yaml format each time during VNF
  deployment with different values for the parameters.
- NOTE:IP address values for network interfaces should be in the below format
  in the parameters values file:

  param_name_value:
    \- xxx.xxx.xxx.xxx
- An example of a vnf-create python-tackerclient command specifying a
  parameterized template and parameter values file would like below:
  "tacker vnf-create --vnfd-name <vnfd_name> --param-file <param_yaml_file>
  --name <vnf_name>"
- Specifying a parameter values file during VNF creation is also supported in
  Horizon UI.
- Sample VNFD parameterized templates and parameter values files can be found
  at https://github.com/openstack/tacker/tree/master/devstack/samples

