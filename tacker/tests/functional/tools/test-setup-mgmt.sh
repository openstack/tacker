#!/bin/bash -xe

# The purpose of this script is to copy the MgmtDriver
# of container update in the sample folder to the
# tacker code and run it.

# Copy the MgmtDriver of container_update to the tacker.
sudo cp /opt/stack/tacker/samples/mgmt_driver/kubernetes/container_update/\
container_update_mgmt.py /opt/stack/tacker/tacker/vnfm/mgmt_drivers/
sudo chown stack:stack /opt/stack/tacker/tacker/vnfm/mgmt_drivers/\
container_update_mgmt.py

# In the configuration file of the tacker,
# add the MgmtDriver of container_update.
sudo sed -i "/VnflcmMgmtNoop/a \ \ \ \ mgmt-container-update = \
tacker.vnfm.mgmt_drivers.container_update_mgmt:ContainerUpdateMgmtDriver" \
/opt/stack/tacker/setup.cfg
sudo sed -i "/vnflcm_mgmt_driver = vnflcm_noop/a vnflcm_mgmt_driver = \
vnflcm_noop,mgmt-container-update" /etc/tacker/tacker.conf

# Reload the tacker configuration file.
cd /opt/stack/tacker/
sudo python3 setup.py build
sudo chown -R stack:stack /opt/stack/tacker/

# Restart the tacker service for the
# configuration file to take effect.
sudo systemctl restart devstack@tacker-conductor
sleep 10s
