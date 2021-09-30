===============================================================================
How to use Mgmt Driver for deploying Kubernetes Cluster with Persistent Volumes
===============================================================================

Overview
--------

In general, the CNF capacity deployed under the Kubernetes cluster
is small, which is not easy to manage in terms of storage, and it
is easy to lose storage content. In this user guide, we support the
deployed Kubernetes cluster VNF has a Storage server with Cinder
volume to enable users to deploy CNF which has PersistentVolumes on
it. In this way, the data in the PersistentVolumes will be stored
in the Storage server, thereby avoiding the above problems.

Instantiate Kubernetes Cluster with Persistent Volumes
------------------------------------------------------

1. Preparations
^^^^^^^^^^^^^^^
The preparations of installing Kubernetes cluster is the same as
the one in `How to use Mgmt Driver for deploying Kubernetes Cluster`_.
You can refer to it for how to set OpenStack configuration, how to
download ubuntu image, how to register Mgmt Driver and usage of VNF
Package.

VNF Package
~~~~~~~~~~~

It is basically the same as user guide
`How to use Mgmt Driver for deploying Kubernetes Cluster`_,
except for the following additions.

1. Add definitions related to the Storage server VM to the VNFD
   and Heat template(Base HOT) as the following samples.

VNFD:

.. code-block:: yaml

   node_templates:
     ...
     storage_server:
       type: tosca.nodes.nfv.Vdu.Compute
       properties:
         name: storage_server
         description: storage server compute node
         vdu_profile:
           min_number_of_instances: 1
           max_number_of_instances: 1
         sw_image_data:
           name: Image for storage server
           version: '20.04'
           checksum:
             algorithm: sha-512
             hash: fb1a1e50f9af2df6ab18a69b6bc5df07ebe8ef962b37e556ce95350ffc8f4a1118617d486e2018d1b3586aceaeda799e6cc073f330a7ad8f0ec0416cbd825452
           container_format: bare
           disk_format: qcow2
           min_disk: 0 GB
           size: 2 GB

       artifacts:
         sw_image:
           type: tosca.artifacts.nfv.SwImage
           file: ../Files/images/ubuntu-20.04-server-cloudimg-amd64.img

       capabilities:
         virtual_compute:
           properties:
             requested_additional_capabilities:
               properties:
                 requested_additional_capability_name: m1.medium
                 support_mandatory: true
                 target_performance_parameters:
                   entry_schema: test
             virtual_memory:
               virtual_mem_size: 4 GB
             virtual_cpu:
               num_virtual_cpu: 2
             virtual_local_storage:
               - size_of_storage: 45 GB

       requirements:
         - virtual_storage: storage_server_volume

     storage_server_volume:
       type: tosca.nodes.nfv.Vdu.VirtualBlockStorage
       properties:
         virtual_block_storage_data:
           size_of_storage: 5 GB

     storage_server_CP:
       type: tosca.nodes.nfv.VduCp
       properties:
         layer_protocols: [ ipv4 ]
         order: 0
       requirements:
         - virtual_binding: storage_server

Heat template(Base HOT):

.. code-block:: yaml

   resources:
     ...
     storage_server_volume:
       type: OS::Cinder::Volume
       properties:
         name: storage_server_volume
         size: 5

     storage_server_CP:
       type: OS::Neutron::Port
       properties:
         network: { get_param: [ nfv, CP, storage_server_CP, network ] }

     storage_server:
       type: OS::Nova::Server
       properties:
         flavor: { get_param: [ nfv, VDU, storage_server, flavor ] }
         name: storage_server
         image: { get_param: [ nfv, VDU, storage_server, image ] }
         block_device_mapping_v2:
         - device_name: vdb
           volume_id: { get_resource: storage_server_volume }
           boot_index: -1
         networks:
         - port: { get_resource: storage_server_CP }

2. Add nfs-pv1.yaml and nfs-pv2.yaml under Files/kubernetes.

The samples of nfs-pv1.yaml and nfs-pv2.yaml are as follows:

nfs-pv1.yaml:

.. code-block:: yaml

   apiVersion: v1
   kind: PersistentVolume
   metadata:
     name: nfs-pv1
   spec:
     capacity:
       storage: 1Gi
     persistentVolumeReclaimPolicy: Retain
     accessModes:
       - ReadWriteOnce
     nfs:
       server: 0.0.0.0
       path: "/volume/nfs/pv1"

nfs-pv2.yaml:

.. code-block:: yaml

   apiVersion: v1
   kind: PersistentVolume
   metadata:
     name: nfs-pv2
   spec:
     capacity:
       storage: 2Gi
     persistentVolumeReclaimPolicy: Retain
     accessModes:
       - ReadWriteOnce
     nfs:
       server: 0.0.0.0
       path: "/volume/nfs/pv2"

.. note::
    See `Persistent Volumes`_ for details.

2. Deploy Kubernetes Cluster
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The operation steps and methods of instantiating with PersistentVolumes
are the same as those in `Deploy Kubernetes Cluster`_ in
`How to use Mgmt Driver for deploying Kubernetes Cluster`_.
The difference is that the parameter file used in instantiate needs to add
``storage_server`` and ``pv_registration_params`` to instantiate Storage
server while instantiating Kubernetes.

Add the following attributes to ``additionalParams`` described in the user
guide `How to use Mgmt Driver for deploying Kubernetes Cluster`_.

The KeyValuePairs is shown in table below:

.. list-table:: **List of additionalParams.k8s_cluster_installation_param.storage_server(specified by user)**
   :widths: 10 10 25 10
   :header-rows: 1

   * - parameter
     - data type
     - description
     - required/optional
   * - ssh_cp_name
     - string
     - CP name that Mgmt Driver uses when SSH/SFTP access to the
       Storage server VM.
     - required
   * - nic_cp_name
     - string
     - CP name that related to Storage server VM's NIC.
     - required
   * - username
     - string
     - User name that Mgmt Driver uses when SSH/SFTP access to the
       Storage server VM.
     - required
   * - password
     - string
     - User password that Mgmt Driver uses when SSH/SFTP access to
       the Storage server VM.
     - required
   * - cinder_volume_setup_params
     - list
     - Configurations for Cinder volume directories on the Storage
       server VM.
     - required
   * - nfs_server_setup_params
     - list
     - Configurations for NFS exports on the Storage server VM.
     - required

.. list-table:: **cinder_volume_setup_params list**
   :widths: 10 10 25 10
   :header-rows: 1

   * - parameter
     - data type
     - description
     - required/optional
   * - volume_resource_id
     - string
     - The resource ID of the Cinder volume defined in the heat
       template (Base HOT). This attribute is used by the Mgmt
       Driver to identify the Cinder volume.
     - required
   * - mount_to
     - string
     - Directory path where the Cinder volume will be mounted on the
       Storage server VM.
     - required

.. list-table:: **nfs_server_setup_params list**
   :widths: 10 10 25 10
   :header-rows: 1

   * - parameter
     - data type
     - description
     - required/optional
   * - export_dir
     - string
     - Directory path to be exported over NFS.
     - required
   * - export_to
     - string
     - The network address to which the directory is exported over
       NFS.
     - required

.. list-table:: **List of additionalParams.k8s_cluster_installation_param.pv_registration_params(specified by user)**
   :widths: 10 10 25 10
   :header-rows: 1

   * - parameter
     - data type
     - description
     - required/optional
   * - pv_manifest_file_path
     - string
     - Path of manifest file for Kubernetes PersistentVolume in VNF
       Package.
     - required
   * - nfs_server_cp
     - string
     - CP name of the NFS server. If DHCP is enabled for the network
       used by NFS, the NFS server IP address in the manifest file
       for Kubernetes PersistentVolume cannot be preconfigured.
       Therefore, the NFS server IP address in the manifest file is
       replaced with the IP address of the CP specified by this
       attribute.
     - required

persistent_volumes_kubernetes_param_file.json

.. code-block:: json


    {
      "flavourId": "simple",
      "additionalParams": {
        "k8s_cluster_installation_param": {
          "script_path": "Scripts/install_k8s_cluster.sh",
          "vim_name": "kubernetes_vim",
          "master_node": {
            "aspect_id": "master_instance",
            "ssh_cp_name": "masterNode_CP1",
            "nic_cp_name": "masterNode_CP1",
            "username": "ubuntu",
            "password": "ubuntu",
            "pod_cidr": "192.168.3.0/16",
            "cluster_cidr": "10.199.187.0/24",
            "cluster_cp_name": "masterNode_CP1"
          },
          "worker_node": {
            "aspect_id": "worker_instance",
            "ssh_cp_name": "workerNode_CP2",
            "nic_cp_name": "workerNode_CP2",
            "username": "ubuntu",
            "password": "ubuntu"
          },
          "proxy": {
            "http_proxy": "http://user1:password1@host1:port1",
            "https_proxy": "https://user2:password2@host2:port2",
            "no_proxy": "192.168.246.0/24,10.0.0.1",
            "k8s_node_cidr": "10.10.0.0/24"
          },
          "storage_server": {
            "ssh_cp_name": "storage_server_CP",
            "nic_cp_name": "storage_server_CP",
            "username": "ubuntu",
            "password": "ubuntu",
            "cinder_volume_setup_params": [
              {
                "volume_resource_id": "storage_server_volume",
                "mount_to": "/volume"
              }
            ],
            "nfs_server_setup_params": [
              {
                "export_dir": "/volume/nfs/pv1",
                "export_to": "10.10.0.0/24"
              },
              {
                "export_dir": "/volume/nfs/pv2",
                "export_to": "10.10.0.0/24"
              }
            ]
          },
          "pv_registration_params": [
            {
              "pv_manifest_file_path": "Files/kubernetes/nfs-pv1.yaml",
              "nfs_server_cp": "storage_server_CP"
            },
            {
              "pv_manifest_file_path": "Files/kubernetes/nfs-pv2.yaml",
              "nfs_server_cp": "storage_server_CP"
            }
          ]
        },
        "lcm-operation-user-data": "./UserData/k8s_cluster_user_data.py",
        "lcm-operation-user-data-class": "KubernetesClusterUserData"
      },
      "extVirtualLinks": [
        {
          "id": "net0_master",
          "resourceId": "f0c82461-36b5-4d86-8322-b0bc19cda65f",
          "extCps": [
            {
              "cpdId": "masterNode_CP1",
              "cpConfig": [
                {
                  "cpProtocolData": [
                    {
                      "layerProtocol": "IP_OVER_ETHERNET"
                    }
                  ]
                }
              ]
            }
          ]
        },
        {
          "id": "net0_worker",
          "resourceId": "f0c82461-36b5-4d86-8322-b0bc19cda65f",
          "extCps": [
            {
              "cpdId": "workerNode_CP2",
              "cpConfig": [
                {
                  "cpProtocolData": [
                    {
                      "layerProtocol": "IP_OVER_ETHERNET"
                    }
                  ]
                }
              ]
            }
          ]
        },
        {
          "id": "net0_storage",
          "resourceId": "f0c82461-36b5-4d86-8322-b0bc19cda65f",
          "extCps": [
            {
              "cpdId": "storage_server_CP",
              "cpConfig": [
                {
                  "cpProtocolData": [
                    {
                      "layerProtocol": "IP_OVER_ETHERNET"
                    }
                  ]
                }
              ]
            }
          ]
        }
      ],
      "vimConnectionInfo": [
        {
          "id": "8a3adb69-0784-43c7-833e-aab0b6ab4470",
          "vimId": "8d8373fe-6977-49ff-83ac-7756572ed186",
          "vimType": "openstack"
        }
      ]
    }

1. Confirm the Instantiate Operation is Successful on Storage server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To confirm that instantiating Kubernetes cluster with PersistentVolumes
is successful, you need to confirm the following.

1. Confirm that Cinder volume is exposed as NFS shared directories in
   the Storage server.
2. Confirm that NFS shared directories is registered as Kubernetes
   PersistentVolumes.

After instantiating, the following command can check confirmation
points 1 and 2.

volume information in Storage server VM

.. code-block:: console

    $ ssh ubuntu@10.10.0.45
    $ df -h
    Filesystem      Size  Used Avail Use% Mounted on
    udev            978M     0  978M   0% /dev
    tmpfs           199M  940K  198M   1% /run
    /dev/vda1       9.6G  1.5G  8.1G  16% /
    tmpfs           994M     0  994M   0% /dev/shm
    tmpfs           5.0M     0  5.0M   0% /run/lock
    tmpfs           994M     0  994M   0% /sys/fs/cgroup
    /dev/vda15      105M  3.9M  101M   4% /boot/efi
    /dev/loop0       68M   68M     0 100% /snap/lxd/18150
    /dev/loop2       32M   32M     0 100% /snap/snapd/10707
    /dev/loop1       56M   56M     0 100% /snap/core18/1944
    /dev/vdb        4.9G   21M  4.6G   1% /volume
    tmpfs           199M     0  199M   0% /run/user/1000
    $ sudo exportfs -v
    /volume/nfs/pv1
                10.10.0.0/24(rw,wdelay,insecure,root_squash,all_squash,no_subtree_check,sec=sys,rw,insecure,root_squash,all_squash)
    /volume/nfs/pv2
                10.10.0.0/24(rw,wdelay,insecure,root_squash,all_squash,no_subtree_check,sec=sys,rw,insecure,root_squash,all_squash)

.. note::
    Confirm "/dev/vdb" is mounted on "/volume" in the result
    of ``df -h`` command, and confirm "/volume/nfs/pv1" and
    "/volume/nfs/pv2" is displayed in the result of
    ``sudo exportfs -v`` command.

volume information in Kubernetes cluster

.. code-block:: console

    $ ssh ubuntu@10.10.0.84
    $ kubectl get pv
    NAME      CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS      CLAIM   STORAGECLASS   REASON   AGE
    nfs-pv1   1Gi        RWO            Retain           Available                                   14h
    nfs-pv2   2Gi        RWO            Retain           Available                                   14h

.. note::
    Confirm "nfs-pv*" can be seen in column "NAME" and
    "STATUS" of "nfs-pv1" and "nfs-pv2" is "Available"
    in the result of ``kubectl get pv`` command.

If you want to log in to the Storage server VM,
query the IP address in the following way with Heat CLI.

.. code-block:: console

    $ openstack stack resource show \
      vnflcm_0c11bf51-353a-41be-af47-d06783413495 storage_server_CP \
      --fit-width -c attributes -f yaml | grep ip_address
    - ip_address: 10.10.0.45


3. Heal Entire Kubernetes Cluster With PersistentVolumes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The parameter file for healing entire Kubernetes cluster used here has
no change with the one used in
`How to use Mgmt Driver for deploying Kubernetes Cluster`_.

The operation steps and methods of entire Kubernetes cluster with
PersistentVolumes are the same as those in ``Heal the Entire
Kubernetes Cluster`` of ``Heal Kubernetes Master/Worker Nodes``
in `How to use Mgmt Driver for deploying Kubernetes Cluster`_.

1. Confirm the Healing Operation is Successful on Storage server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To confirm that entire Kubernetes cluster is successful, you need
to confirm the following.

1. Confirm that Cinder volume is exposed as NFS shared directories
   in the respawned Storage server.
2. Confirm that NFS shared directories is registered as Kubernetes
   PersistentVolumes.

After healing, the following command can check confirmation
points 1 and 2.

volume information in Storage server VM

.. code-block:: console

    $ ssh ubuntu@10.10.0.45
    $ df -h
    Filesystem      Size  Used Avail Use% Mounted on
    udev            978M     0  978M   0% /dev
    tmpfs           199M  940K  198M   1% /run
    /dev/vda1       9.6G  1.5G  8.1G  16% /
    tmpfs           994M     0  994M   0% /dev/shm
    tmpfs           5.0M     0  5.0M   0% /run/lock
    tmpfs           994M     0  994M   0% /sys/fs/cgroup
    /dev/vda15      105M  3.9M  101M   4% /boot/efi
    /dev/loop0       68M   68M     0 100% /snap/lxd/18150
    /dev/loop2       32M   32M     0 100% /snap/snapd/10707
    /dev/loop1       56M   56M     0 100% /snap/core18/1944
    /dev/vdb        4.9G   21M  4.6G   1% /volume
    tmpfs           199M     0  199M   0% /run/user/1000
    $ sudo exportfs -v
    /volume/nfs/pv1
                10.10.0.0/24(rw,wdelay,insecure,root_squash,all_squash,no_subtree_check,sec=sys,rw,insecure,root_squash,all_squash)
    /volume/nfs/pv2
                10.10.0.0/24(rw,wdelay,insecure,root_squash,all_squash,no_subtree_check,sec=sys,rw,insecure,root_squash,all_squash)

.. note::
    Confirm "/dev/vdb" is mounted on "/volume" in the result
    of ``df -h`` command, and confirm "/volume/nfs/pv1" and
    "/volume/nfs/pv2" is displayed in the result of
    ``sudo exportfs -v`` command.

volume information in Kubernetes cluster

.. code-block:: console

    $ ssh ubuntu@10.10.0.84
    $ kubectl get pv
    NAME      CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS      CLAIM   STORAGECLASS   REASON   AGE
    nfs-pv1   1Gi        RWO            Retain           Available                                   12s
    nfs-pv2   2Gi        RWO            Retain           Available                                   12s

.. note::
    Confirm "nfs-pv*" can be seen in column "NAME" and
    "STATUS" of "nfs-pv1" and "nfs-pv2" is "Available"
    in the result of ``kubectl get pv`` command.

4. Heal Storage server VM
^^^^^^^^^^^^^^^^^^^^^^^^^

The operation steps and methods of healing Storage server VM
are basically the same as those in ``Heal a Worker Node`` of
``Heal Kubernetes Master/Worker Nodes`` in
`How to use Mgmt Driver for deploying Kubernetes Cluster`_.

The Heal Storage server VM operation will delete the Storage
server VM and rebuild it, the Cinder volume attached to the
Storage server VM will also be rebuilt, and the data stored
in the volume will be initialized.

.. note::

    Note that PersistentVolumes must not be used before executing
    Heal operation. Otherwise, it will fail.

1. Confirm Volume Usage Before Heal on Kubernetes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before healing, you need to confirm the following.

1. Confirm that all registered PersistentVolumes in the Kubernetes
   cluster are not in use.

The following command can check confirmation points 1.

volume information in Kubernetes cluster

.. code-block:: console

    $ ssh ubuntu@10.10.0.84
    $ kubectl get pv
    NAME      CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS      CLAIM   STORAGECLASS   REASON   AGE
    nfs-pv1   1Gi        RWO            Retain           Available                                   14h
    nfs-pv2   2Gi        RWO            Retain           Available                                   14h

.. note::
    Confirm "STATUS" of "nfs-pv1" and "nfs-pv2" is "Available"
    in the result of ``kubectl get pv`` command. If the status
    of PV is "Bound", the PV is in use.

2. Confirm the Healing Operation is Successful on Storage server VM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To confirm that healing Storage server VM is successful, you need
to confirm the following.

1. Confirm that Cinder volume is exposed as NFS shared directories
   in the respawned Storage server.
2. Confirm that NFS shared directories is registered as Kubernetes
   PersistentVolumes.

After healing, the following command can check confirmation
points 1 and 2.

volume information in Storage server VM

.. code-block:: console

    $ ssh ubuntu@10.10.0.45
    $ df -h
    Filesystem      Size  Used Avail Use% Mounted on
    udev            978M     0  978M   0% /dev
    tmpfs           199M  940K  198M   1% /run
    /dev/vda1       9.6G  1.5G  8.1G  16% /
    tmpfs           994M     0  994M   0% /dev/shm
    tmpfs           5.0M     0  5.0M   0% /run/lock
    tmpfs           994M     0  994M   0% /sys/fs/cgroup
    /dev/vda15      105M  3.9M  101M   4% /boot/efi
    /dev/loop0       68M   68M     0 100% /snap/lxd/18150
    /dev/loop2       32M   32M     0 100% /snap/snapd/10707
    /dev/loop1       56M   56M     0 100% /snap/core18/1944
    /dev/vdb        4.9G   21M  4.6G   1% /volume
    tmpfs           199M     0  199M   0% /run/user/1000
    $ sudo exportfs -v
    /volume/nfs/pv1
                10.10.0.0/24(rw,wdelay,insecure,root_squash,all_squash,no_subtree_check,sec=sys,rw,insecure,root_squash,all_squash)
    /volume/nfs/pv2
                10.10.0.0/24(rw,wdelay,insecure,root_squash,all_squash,no_subtree_check,sec=sys,rw,insecure,root_squash,all_squash)

.. note::
    Confirm "/dev/vdb" is mounted on "/volume1" in the result
    of ``df -h`` command, and confirm "/volume/nfs/pv1" and
    "/volume/nfs/pv2" is displayed in the result of
    ``sudo exportfs -v`` command.

volume information in Kubernetes cluster

.. code-block:: console

    $ ssh ubuntu@10.10.0.84
    $ kubectl get pv
    NAME      CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS      CLAIM   STORAGECLASS   REASON   AGE
    nfs-pv1   1Gi        RWO            Retain           Available                                   12s
    nfs-pv2   2Gi        RWO            Retain           Available                                   12s

.. note::
    Confirm "nfs-pv*" can be seen in column "NAME" and
    "STATUS" of "nfs-pv1" and "nfs-pv2" is "Available"
    in the result of ``kubectl get pv`` command.

Limitations
-----------
1. Scale operation for the Storage server VM is not supported.
2. If PersistentVolumes is in use before executing Heal Storage
   server VM operation, the operation will fail.
3. Healing Storage server VM will cause the data stored in the volume
   to be initialized.

.. _Heal Kubernetes Master/Worker Nodes: https://docs.openstack.org/tacker/wallaby/user/mgmt_driver_deploy_k8s_usage_guide.html#deploy-kubernetes-cluster
.. _How to use Mgmt Driver for deploying Kubernetes Cluster: https://docs.openstack.org/tacker/wallaby/user/mgmt_driver_deploy_k8s_usage_guide.html
.. _Persistent Volumes: https://kubernetes.io/docs/concepts/storage/persistent-volumes/
.. _Deploy Kubernetes Cluster: https://docs.openstack.org/tacker/wallaby/user/mgmt_driver_deploy_k8s_usage_guide.html#deploy-kubernetes-cluster
