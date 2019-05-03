#!/bin/bash

VNFC_IMAGE=/tmp/tacker_vnfc_images
rm -rf $VNFC_IMAGE
mkdir $VNFC_IMAGE

pip install diskimage-builder
pip install dib-utils
CURRENT_DIR=`pwd`
cd $VNFC_IMAGE
git clone https://opendev.org/openstack/tripleo-image-elements.git
git clone https://opendev.org/openstack/heat-templates.git

export ELEMENTS_PATH=tripleo-image-elements/elements:heat-templates/hot/software-config/elements
disk-image-create vm \
  fedora selinux-permissive \
  os-collect-config \
  os-refresh-config \
  os-apply-config \
  heat-config \
  heat-config-ansible \
  heat-config-cfn-init \
  heat-config-puppet \
  heat-config-salt \
  heat-config-script \
  -o fedora-software-config.qcow2
