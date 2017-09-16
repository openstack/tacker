..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

Enhanced Placement Awareness Usage Guide
========================================

Overview
--------

OpenStack Tacker supports TOSCA VNFD templates that allow specifying
requirements for a VNF that leverages features of a compute node such as
NUMA topology, SR-IOV, Huge pages and CPU pinning. This allows for Enhanced
Platform Awareness(EPA) placement of a VNF that has high performance and low
latency requirements.

Configuring compute nodes to be EPA nodes
-----------------------------------------

The compute nodes requires configuration in the BIOS, Hypervisor and
OpenStack to enable it be an EPA compute node for deploying high performance
VNFs.

Below table shows the configurations needed for the different features across
BIOS, Hypervisor and OpenStack.

+----------------+------+------------+-----------+
|                | BIOS | Hypervisor | OpenStack |
+----------------+------+------------+-----------+
| NUMA Topology  | X    |            | X         |
+----------------+------+------------+-----------+
| SR-IOV         | X    | X          | X         |
+----------------+------+------------+-----------+
| HyperThreading | X    |            |           |
+----------------+------+------------+-----------+
| Huge Pages     |      | X          |           |
+----------------+------+------------+-----------+
| CPU Pinning    |      | X          | X         |
+----------------+------+------------+-----------+

**NOTE**: Consult the configuration guide from the Server and NIC vendor to
enable NUMA topology, SR-IOV and HyperThreading in BIOS. Also check the
Hypervisor documentation to verify if NUMA topology is supported.

Below is a snippet of the /etc/default/grub file in Ubuntu that enables

a) CPU isolation from kernel process to be used for VMs(refer keyword
*isolcpus* in the code block below)

b) Reserving huge memory pages (refer keywords *default_hugepagesz*,
*hugepagesz* and *hugepages* in the code block below)

c) Enabling SR-IOV Virtual functions to be exposed (refer keyword
*intel_iommu* in the code block below)

.. code-block:: console

  GRUB_CMDLINE_LINUX_DEFAULT="quiet splash isolcpus=8-19 default_hugepagesz=1G hugepagesz=1G hugepages=24"

  GRUB_CMDLINE_LINUX="intel_iommu=on"

**NOTE**: The above could be different based on the Hypervisor and the
hardware architecture of the Server. Please consult the Hypervisor
documentation.

Below table shows the OpenStack related files that needs to be configured
to enable the EPA features on compute nodes.

+---------------+-----------+--------------+--------------------+
|               | nova.conf | ml2_conf.ini | ml2_conf_sriov.ini |
+---------------+-----------+--------------+--------------------+
| NUMA Topology | X         |              |                    |
+---------------+-----------+--------------+--------------------+
| SR-IOV        | X         | X            | X                  |
+---------------+-----------+--------------+--------------------+
| CPU Pinning   | X         |              |                    |
+---------------+-----------+--------------+--------------------+

The NUMA Topology feature enablement on compute nodes requires the
**NUMATopologyFilter** to be added to the scheduler_default_filters in
nova.conf file.

The SR-IOV feature enablement requires configuration on both the controller
and compute nodes. Please refer link similar to below for the appropriate
OpenStack release to setup SR-IOV:
https://docs.openstack.org/neutron/latest/admin/config-sriov.html

The CPU Pinning feature enablement requires configuring the nova.conf on
compute nodes. It requires an entry similar to below:

.. code-block:: console

  [DEFAULT]
  vcpu_pin_set = 8-19
  cpu_allocation_ratio = 1.0
  [libvirt]
  virt_type = kvm

**NOTE**: Please refer OpenStack release documentation for configuring the
above-mentioned features.

Creating availability zone using compute nodes
----------------------------------------------

Once the compute nodes have been prepared for high performance requirement
VNF deployments, the next step would be to create an 'aggregate-list' and
availability zone from the compute nodes identified for VNF deployments.
Below commands illustrates an example of creating such an aggregate-list,
availability zone and adding compute nodes.

.. code-block:: console

   openstack aggregate create --zone NFV-AZ NFV-AGG

   openstack aggregate add host NFV-AGG <NFV_HOST1>

   openstack aggregate add host NFV-AGG <NFV_HOST2>

**NOTE**: Consult http://docs.openstack.org/cli-reference/nova.html for
latest supported commands.

Specifying Availability Zone for VDU in VNFD template
-----------------------------------------------------

Find below snippet of VNFD template that specifies the EPA Availability Zone
created as part of the VDU properties using **availability_zone** property.

.. code-block:: yaml

  vdu1:
    type: tosca.nodes.nfv.VDU.Tacker
    capabilities:
      nfv_compute:
        properties:
          disk_size: 10 GB
          mem_size: 2048 MB
          num_cpus: 2
          mem_page_size: large
    properties:
      availability_zone: NFV-AZ
      image: cirros

Deploying EPA TOSCA templates using Tacker
------------------------------------------

Once OpenStack/Devstack along with Tacker has been successfully installed,
deploy a sample EPA template such as tosca-vnfd-hugepages.yaml from location
below:
https://github.com/openstack/tacker/tree/master/samples/tosca-templates/vnfd

Refer the 'Getting Started' link below on how to create a VNFD and deploy a
VNF:
https://docs.openstack.org/tacker/latest/install/getting_started.html
