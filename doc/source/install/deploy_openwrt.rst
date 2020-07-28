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

#. Ensure Glance already contains OpenWRT image.

   Normally, Tacker tries to add OpenWRT image to Glance while installing
   via devstack. By running ``openstack image list`` to check OpenWRT image
   if exists.

   .. code-block:: console
       :emphasize-lines: 5

       $ openstack image list
       +--------------------------------------+--------------------------+--------+
       | ID                                   | Name                     | Status |
       +--------------------------------------+--------------------------+--------+
       | 8cc2aaa8-5218-49e7-9a57-ddb97dc68d98 | OpenWRT                  | active |
       | 32f875b0-9e24-4971-b82d-84d6ec620136 | cirros-0.4.0-x86_64-disk | active |
       | ab0abeb8-f73c-467b-9743-b17083c02093 | cirros-0.5.1-x86_64-disk | active |
       +--------------------------------------+--------------------------+--------+

   If not, you can get the customized image of OpenWRT 15.05.1 in your tacker repository,
   or download the image from [#f1]_. Unzip the file by using the command below:

   .. code-block:: console

      $ cd /path/to/tacker/samples/images/
      $ gunzip openwrt-x86-kvm_guest-combined-ext4.img.gz

   Then upload the image into Glance by using command below:

   .. code-block:: console

      $ openstack image create OpenWRT --disk-format qcow2 \
            --container-format bare \
            --file /path/to/openwrt-x86-kvm_guest-combined-ext4.img \
            --public

#. Configure OpenWRT

   The example below shows how to create the OpenWRT-based Firewall VNF.
   First, we have a yaml template which contains the configuration of
   OpenWRT as shown below:

   *tosca-vnfd-openwrt.yaml* [#f2]_

   .. literalinclude:: ../../../samples/tosca-templates/vnfd/tosca-vnfd-openwrt.yaml
       :language: yaml


   We also have another configuration yaml template with some firewall rules of
   OpenWRT.

   *tosca-config-openwrt-firewall.yaml* [#f3]_

   .. literalinclude:: ../../../samples/tosca-templates/vnfd/tosca-config-openwrt-firewall.yaml
       :language: yaml

   In this template file, we specify the ``mgmt_driver: openwrt`` which means
   this VNFD is managed by openwrt driver [#f4]_. This driver can inject
   firewall rules which defined in VNFD into OpenWRT instance by using SSH
   protocol. We can run ``cat /etc/config/firewall`` to confirm the firewall
   rules if inject succeed.

#. Create a sample vnfd

   .. code-block:: console

       $ openstack vnf descriptor create \
           --vnfd-file tosca-vnfd-openwrt.yaml <VNFD_NAME>

#. Create a VNF

   .. code-block:: console

      $ openstack vnf create --vnfd-name <VNFD_NAME> \
            --config-file tosca-config-openwrt-firewall.yaml <NAME>

#. Check the status

   .. code-block:: console

       $ openstack vnf list
       $ openstack vnf show <VNF_ID>

   We can replace the firewall rules configuration file with
   tosca-config-openwrt-vrouter.yaml [#f5]_, tosca-config-openwrt-dnsmasq.yaml
   [#f6]_, or tosca-config-openwrt-qos.yaml [#f7]_ to deploy the router, DHCP,
   DNS, or QoS VNFs. The openwrt VNFM management driver will do the same way to
   inject the desired service rules into the OpenWRT instance. You can also do the
   same to check if the rules are injected successful: **cat /etc/config/network**
   to check vrouter, **cat /etc/config/dhcp** to check DHCP and DNS, and
   **cat /etc/config/qos** to check the QoS rules.

#. Notes

   #. OpenWRT user and password

      The user account is 'root' and password is '', which means there is no
      password for root account.

   #. Procedure to customize the OpenWRT image

      The OpenWRT is modified based on KVM OpenWRT 15.05.1 to be suitable
      for Tacker. The procedure is following as below:

      .. code-block:: console

          $ cd ~
          $ wget https://archive.openwrt.org/chaos_calmer/15.05.1/x86/kvm_guest/openwrt-15.05.1-x86-kvm_guest-combined-ext4.img.gz \
                  -O openwrt-x86-kvm_guest-combined-ext4.img.gz
          $ gunzip openwrt-x86-kvm_guest-combined-ext4.img.gz

          $ mkdir -p imgroot

          $ sudo kpartx -av openwrt-x86-kvm_guest-combined-ext4.img

          # Replace the loopXp2 with the result of above command, e.g., loop0p2
          $ sudo mount -o loop /dev/mapper/loopXp2 imgroot
          $ sudo chroot imgroot /bin/ash

          # Set password of this image to blank, type follow command and then enter two times
          $ passwd

          # Set DHCP for the network of OpenWRT so that the VNF can be ping
          $ uci set network.lan.proto=dhcp; uci commit
          $ exit

          $ sudo umount imgroot
          $ sudo kpartx -dv openwrt-x86-kvm_guest-combined-ext4.img


.. rubric:: Footnotes

.. [#] https://opendev.org/openstack/tacker/src/branch/master/samples/images/openwrt-x86-kvm_guest-combined-ext4.img.gz
.. [#] https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnfd/tosca-vnfd-openwrt.yaml
.. [#] https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnfd/tosca-config-openwrt-firewall.yaml
.. [#] https://opendev.org/openstack/tacker/src/branch/master/tacker/vnfm/mgmt_drivers/openwrt/openwrt.py
.. [#] https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnfd/tosca-config-openwrt-vrouter.yaml
.. [#] https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnfd/tosca-config-openwrt-dnsmasq.yaml
.. [#] https://opendev.org/openstack/tacker/src/branch/master/samples/tosca-templates/vnfd/tosca-config-openwrt-qos.yaml
