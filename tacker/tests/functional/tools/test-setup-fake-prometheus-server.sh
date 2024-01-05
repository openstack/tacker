#!/bin/bash -xe

# This script is used to set up a fake prometheus server
# for functional testing.
#

cd /opt/stack/tacker/samples/tests/functional/sol_kubernetes_v2/tacker-monitoring-test

sudo docker build -t tacker-monitoring-test .
sudo docker run -v ${PWD}/src:/work/src -v ${PWD}/rules:/etc/prometheus/rules \
    -p 55555:55555 -p 50022:22 -e TEST_REMOTE_URI="http://0.0.0.0" -d \
    -it tacker-monitoring-test
