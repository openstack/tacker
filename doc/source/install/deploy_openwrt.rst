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

========================
Deploying OpenWRT as VNF
========================

Once tacker is installed successfully, follow the steps given below to get
started with deploying OpenWRT as VNF.

1. Ensure Glance already contains OpenWRT image. Normally, Tacker tries
to add OpenWRT image to Glance while installing via devstack. By running
**openstack image list** to check OpenWRT image if exists. If not, download
the image from
`OpenWRT official site
<https://downloads.openwrt.org/chaos_calmer/15.05.1/x86/generic/>`_.
And upload this image into Glance by using the command specified below:

.. code-block:: console

   openstack image create OpenWRT --disk-format qcow2 \
                                  --container-format bare \
                                  --file /path_to_image/openwrt-x86-kvm_guest-combined-ext4.img \
                                  --public
..

2. Create a yaml template named tosca-vnfd-openwrt-with-firewall-rules.yaml
which contains basic configuration of OpenWRT and some firewall rules of
OpenWRT. All contents of the template file shows below:

.. code-block:: ini

   tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0

   description: OpenWRT with services

   metadata:
     template_name: OpenWRT

   topology_template:
     node_templates:
       VDU1:
         type: tosca.nodes.nfv.VDU.Tacker
         capabilities:
           nfv_compute:
             properties:
               num_cpus: 1
               mem_size: 512 MB
               disk_size: 1 GB
         properties:
           image: OpenWRT
           config:
             firewall: |
               package firewall

               config defaults
                   option syn_flood '1'
                   option input 'ACCEPT'
                   option output 'ACCEPT'
                   option forward 'REJECT'

               config zone
                   option name 'lan'
                   list network 'lan'
                   option input 'ACCEPT'
                   option output 'ACCEPT'
                   option forward 'ACCEPT'

               config zone
                   option name 'wan'
                   list network 'wan'
                   list network 'wan6'
                   option input 'REJECT'
                   option output 'ACCEPT'
                   option forward 'REJECT'
                   option masq '1'
                   option mtu_fix '1'

               config forwarding
                   option src 'lan'
                   option dest 'wan'

               config rule
                   option name 'Allow-DHCP-Renew'
                   option src 'wan'
                   option proto 'udp'
                   option dest_port '68'
                   option target 'ACCEPT'
                   option family 'ipv4'

               config rule
                   option name 'Allow-Ping'
                   option src 'wan'
                   option proto 'icmp'
                   option icmp_type 'echo-request'
                   option family 'ipv4'
                   option target 'ACCEPT'
           mgmt_driver: openwrt
           monitoring_policy:
             name: ping
             parameters:
               count: 3
               interval: 10
             actions:
               failure: respawn

       CP1:
         type: tosca.nodes.nfv.CP.Tacker
         properties:
           management: true
           anti_spoofing_protection: false
         requirements:
           - virtualLink:
               node: VL1
           - virtualBinding:
               node: VDU1

       VL1:
         type: tosca.nodes.nfv.VL
         properties:
           network_name: net_mgmt
           vendor: Tacker

..

The above template file comes from two files. One is `tosca-vnfd-openwrt.yaml
<https://github.com/openstack/tacker/blob/master/samples/tosca-templates/
vnfd/tosca-vnfd-openwrt.yaml>`_ and other one is
`tosca-config-openwrt-with-firewall.yaml
<https://github.com/openstack/tacker/blob/master/samples/tosca-templates/
vnfd/tosca-config-openwrt-with-firewall.yaml>`_.
In this template file, we specify the **mgmt_driver: openwrt** which means
this VNFD is managed by `openwrt driver
<https://github.com/openstack/tacker/blob/master/tacker/
vnfm/mgmt_drivers/openwrt/openwrt.py>`_. This driver can inject firewall rules
which defined in VNFD into OpenWRT instance by using SSH protocol. We can
run **cat /etc/config/firewall** to confirm the firewall rules if inject
succeed.

3.Create a sample vnfd:

.. code-block:: console

    tacker vnfd-create \
                       --vnfd-file tosca-vnfd-openwrt-with-firewall-rules.yaml \
                       <VNFD_NAME>
..

4.Create a VNF:

.. code-block:: console

    tacker vnf-create --vnfd-name <VNFD_NAME> <NAME>
..

This VNF will contains all the firewall rules that VNFD contains
by using 'cat /etc/config/firewall' in VNF.


5.Check the status:

.. code-block:: console

    tacker vnf-list
    tacker vnf-show <VNF_ID>
..
