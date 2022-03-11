#!/bin/sh

sudo apt-get build-dep vagrant ruby-libvirt -y
sudo apt-get install qemu libvirt-bin ebtables dnsmasq-base -y
sudo apt-get install libxslt-dev libxml2-dev libvirt-dev zlib1g-dev ruby-dev -y

vagrant plugin install vagrant-libvirt
