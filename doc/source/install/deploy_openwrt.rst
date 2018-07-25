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

1.Ensure Glance already contains OpenWRT image. Normally, Tacker tries
to add OpenWRT image to Glance while installing via devstack. By running
**openstack image list** to check OpenWRT image if exists. If not, download
the customized image of OpenWRT 15.05.1 [#f1]_. Unzip the file by using
the command below:

.. code-block:: console

   gunzip openwrt-x86-kvm_guest-combined-ext4.img.gz

..

And then upload this image into Glance by using the command specified below:

.. code-block:: console

   openstack image create OpenWRT --disk-format qcow2 \
                                  --container-format bare \
                                  --file /path_to_image/openwrt-x86-kvm_guest-combined-ext4.img \
                                  --public
..

2.The below example shows how to create the OpenWRT-based Firewall VNF.
First, we have a yaml template which contains the configuration of
OpenWRT as shown below:

*tosca-vnfd-openwrt.yaml* [#f2]_

.. code-block:: yaml

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
           config: |
             param0: key1
             param1: key2
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
           order: 0
           anti_spoofing_protection: false
         requirements:
           - virtualLink:
              node: VL1
           - virtualBinding:
               node: VDU1

        CP2:
         type: tosca.nodes.nfv.CP.Tacker
         properties:
           order: 1
           anti_spoofing_protection: false
         requirements:
           - virtualLink:
               node: VL2
           - virtualBinding:
               node: VDU1

        CP3:
         type: tosca.nodes.nfv.CP.Tacker
         properties:
           order: 2
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
           vendor: Tacker firewall

..

We also have another configuration yaml template with some firewall rules of
OpenWRT.

*tosca-config-openwrt-firewall.yaml* [#f3]_

.. code-block:: yaml

   vdus:
     VDU1:
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
           config rule
               option name 'Allow-IGMP'
               option src 'wan'
               option proto 'igmp'
               option family 'ipv4'
               option target 'ACCEPT'
           config rule
               option name 'Allow-DHCPv6'
               option src 'wan'
               option proto 'udp'
               option src_ip 'fe80::/10'
               option src_port '547'
               option dest_ip 'fe80::/10'
               option dest_port '546'
               option family 'ipv6'
               option target 'ACCEPT'
           config rule
               option name 'Allow-MLD'
               option src 'wan'
               option proto 'icmp'
               option src_ip 'fe80::/10'
               list icmp_type '130/0'
               list icmp_type '131/0'
               list icmp_type '132/0'
               list icmp_type '143/0'
               option family 'ipv6'
               option target 'ACCEPT'
           config rule
               option name 'Allow-ICMPv6-Input'
               option src 'wan'
               option proto 'icmp'
               list icmp_type 'echo-request'
               list icmp_type 'echo-reply'
               list icmp_type 'destination-unreachable'
               list icmp_type 'packet-too-big'
               list icmp_type 'time-exceeded'
               list icmp_type 'bad-header'
               list icmp_type 'unknown-header-type'
               list icmp_type 'router-solicitation'
               list icmp_type 'neighbour-solicitation'
               list icmp_type 'router-advertisement'
               list icmp_type 'neighbour-advertisement'
               option limit '190/sec'
               option family 'ipv6'
               option target 'REJECT'

..

In this template file, we specify the **mgmt_driver: openwrt** which means
this VNFD is managed by openwrt driver [#f4]_. This driver can inject
firewall rules which defined in VNFD into OpenWRT instance by using SSH
protocol. We can run**cat /etc/config/firewall** to confirm the firewall
rules if inject succeed.

3.Create a sample vnfd:

.. code-block:: console

    openstack vnf descriptor create --vnfd-file tosca-vnfd-openwrt.yaml <VNFD_NAME>
..

4.Create a VNF:

.. code-block:: console

    openstack vnf create --vnfd-name <VNFD_NAME> \
                      --config-file tosca-config-openwrt-firewall.yaml <NAME>
..

5.Check the status:

.. code-block:: console

    openstack vnf list
    openstack vnf show <VNF_ID>
..

We can replace the firewall rules configuration file with
tosca-config-openwrt-vrouter.yaml [#f5]_, tosca-config-openwrt-dnsmasq.yaml
[#f6]_, or tosca-config-openwrt-qos.yaml [#f7]_ to deploy the router, DHCP,
DNS, or QoS VNFs. The openwrt VNFM management driver will do the same way to
inject the desired service rules into the OpenWRT instance. You can also do the
same to check if the rules are injected successful: **cat /etc/config/network**
to check vrouter, **cat /etc/config/dhcp** to check DHCP and DNS, and
**cat /etc/config/qos** to check the QoS rules.

6.Notes
6.1.OpenWRT user and password
The user account is 'root' and password is '', which means there is no
password for root account.

6.2.Procedure to customize the OpenWRT image
The OpenWRT is modified based on KVM OpenWRT 15.05.1 to be suitable forTacker.
The procedure is following as below:

.. code-block:: console

    cd ~
    wget https://archive.openwrt.org/chaos_calmer/15.05.1/x86/kvm_guest/openwrt-15.05.1-x86-kvm_guest-combined-ext4.img.gz \
            -O openwrt-x86-kvm_guest-combined-ext4.img.gz
    gunzip openwrt-x86-kvm_guest-combined-ext4.img.gz

    mkdir -p imgroot

    sudo kpartx -av openwrt-x86-kvm_guest-combined-ext4.img

    # Replace the loopXp2 with the result of above command, e.g., loop0p2
    sudo mount -o loop /dev/mapper/loopXp2 imgroot
    sudo chroot imgroot /bin/ash

    # Set password of this image to blank, type follow command and then enter two times
    passwd

    # Set DHCP for the network of OpenWRT so that the VNF can be ping
    uci set network.lan.proto=dhcp; uci commit
    exit

    sudo umount imgroot
    sudo kpartx -dv openwrt-x86-kvm_guest-combined-ext4.img

..

.. rubric:: Footnotes

.. [#] https://anda.ssu.ac.kr/~openwrt/openwrt-x86-kvm_guest-combined-ext4.img.gz
.. [#] https://github.com/openstack/tacker/blob/master/samples/tosca-templates/vnfd/tosca-vnfd-openwrt.yaml
.. [#] https://github.com/openstack/tacker/blob/master/samples/tosca-templates/vnfd/tosca-config-openwrt-firewall.yaml
.. [#] https://github.com/openstack/tacker/blob/master/tacker/vnfm/mgmt_drivers/openwrt/openwrt.py
.. [#] https://github.com/openstack/tacker/blob/master/samples/tosca-templates/vnfd/tosca-config-openwrt-vrouter.yaml
.. [#] https://github.com/openstack/tacker/blob/master/samples/tosca-templates/vnfd/tosca-config-openwrt-dnsmasq.yaml
.. [#] https://github.com/openstack/tacker/blob/master/samples/tosca-templates/vnfd/tosca-config-openwrt-qos.yaml
