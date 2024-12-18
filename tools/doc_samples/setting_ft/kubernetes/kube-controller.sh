#!/bin/sh
# kube-controller.sh

### Open Virtual Switch (OVS)
# sudo ovs-vsctl show
sudo ovs-vsctl add-port br-ex eth1
sudo ovs-vsctl show

# echo "End shell script ${0}"
