#!/bin/sh
# openstack-controller.sh

DATABASE_PASSWORD="secretdatabase"

### Open Virtual Switch (OVS)
sudo ovs-vsctl add-port br-ex eth1
sudo ovs-vsctl show

### multi-node, MySQL
cd "${HOME}" || exit
mysql -p --password="${DATABASE_PASSWORD}" << END_OF_INPUT_1
use nova_cell1
select host,hypervisor_hostname, mapped, uuid from compute_nodes;
quit
END_OF_INPUT_1
/bin/rm -f "./settings-compute-nodes.sh"
cat << EOF > "./settings-compute-nodes.sh"
#!/bin/sh
${SHELL} --rcfile /dev/fd/3 3<< END_OF_SHELL
        source data/venv/bin/activate
        nova-manage cell_v2 discover_hosts
        mysql -p --password="${DATABASE_PASSWORD}" << END_OF_INPUT_2
        use nova_cell1
        select host,hypervisor_hostname, mapped, uuid from compute_nodes;
        quit
END_OF_INPUT_2
        deactivate
        exit
END_OF_SHELL
EOF
# source "./settings-compute-nodes.sh"
. "./settings-compute-nodes.sh"
/bin/rm -f "./settings-compute-nodes.sh"

# echo "End shell script ${0}"
