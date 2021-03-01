=======================================================
How to use Mgmt Driver for deploying Kubernetes Cluster
=======================================================

Overview
--------

1. Mgmt Driver Introduction
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Mgmt Driver enables Users to configure their VNF before and/or after
its VNF Lifecycle Management operation. Users can customize the logic
of Mgmt Driver by implementing their own Mgmt Driver and these
customizations are specified by "interface" definition in
`NFV-SOL001 v2.6.1`_.
This user guide aims to deploy Kubernetes cluster via
Mgmt Driver which is customized by user.

2. Use Cases
^^^^^^^^^^^^
In the present user guide, two cases are supported with the sample Mgmt Driver
and VNF Package providing two deployment flavours in VNFD:

* simple: Deploy one master node with worker nodes. In this
  case, it supports to scale worker node and heal worker node.
* complex: Deploy three(or more) master nodes with worker nodes. In
  this case, it supports to scale worker node and heal worker
  node and master node.

In all the above cases, ``kubeadm`` is used for deploying Kubernetes in
the sample script.

1. Simple : Single Master Node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The simple Kubernetes cluster contains one master node as controller node.
You can deploy it use the sample script we provided. The diagram below shows
simple Kubernetes cluster architecture:

.. code-block:: console

    +-------------------------------+
    |      Kubernetes cluster       |
    |       +---------------+       |
    |       |  +---------+  |       |
    |       |  | k8s-api |  |       |
    |       |  +---------+  |       |
    |       |  +---------+  |       |
    |       |  |  etcd   |  |       |
    |       |  +---------+  |       |
    |       |   Master VM   |       |
    |       +---------------+       |
    |                               |
    |                               |
    |  +----------+   +----------+  |
    |  | +------+ |   | +------+ |  |
    |  | | Pod  | |   | | Pod  | |  |
    |  | +------+ |   | +------+ |  |
    |  | Worker VM|   | Worker VM|  |
    |  +----------+   +----------+  |
    |                               |
    +-------------------------------+

2. Complex : High Availability(HA) Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kubernetes is known for its resilience and reliability. This is possible
by ensuring that the cluster does not have any single points of failure.
Because of this, to have a highly availability(HA) cluster, you need to have
multiple master nodes. We provide the sample script which can be used to
deploy an HA Kubernetes cluster. The diagram below shows HA Kubernetes
cluster architecture:

.. code-block:: console

     +-----------------------------------------------------------+
     |             High availability(HA) Kubernetes cluster      |
     | +-------------------------------------+                   |
     | |                                     |                   |
     | | +---------------+      +---------+  |                   |
     | | | VIP - Active  |      | HAProxy |  |                   |
     | | |               |----->| (Active)|------+               |
     | | |(keep - alived)|      +---------+  |   | +-----------+ |
     | | |               |      +---------+  |   | |           | |
     | | +---------------+      | k8s-api |<-----+ |           | |
     | |            ^           +---------+  |   | |           | |
     | |            |           +---------+  |   | |           | |
     | |   VRRP     |      +--->|  etcd   |  |   | |           | |
     | |            |      |    +---------+  |   | |           | |
     | |            |      |     Master01 VM |   | |           | |
     | +------------|------|-----------------+   | |           | |
     |              |      |                     | |           | |
     | +------------|------|-----------------+   | |           | |
     | |            v      |                 |   | |Worker01 VM| |
     | | +---------------+ |    +---------+  |   | |           | |
     | | | VIP - Standby | |    | HAProxy |  |   | +-----------+ |
     | | |               | |    |(Standby)|  |   |               |
     | | |(keep - alived)| |    +---------+  |   |               |
     | | |               | |    +---------+  |   |               |
     | | +---------------+ |    | k8s-api |<-----+               |
     | |            ^      |    +---------+  |   |               |
     | |            |      |    +---------+  |   |               |
     | |   VRRP     |      +--->|  etcd   |  |   | +-----------+ |
     | |            |      |    +---------+  |   | |           | |
     | |            |      |     Master02 VM |   | |           | |
     | +------------|------|-----------------+   | |           | |
     |              |      |                     | |           | |
     | +------------|------|-----------------+   | |           | |
     | |            v      |                 |   | |           | |
     | | +---------------+ |    +---------+  |   | |           | |
     | | | VIP - Standby | |    | HAProxy |  |   | |           | |
     | | |               | |    |(Standby)|  |   | |           | |
     | | |(keep - alived)| |    +---------+  |   | |           | |
     | | |               | |    +---------+  |   | |Worker02 VM| |
     | | +---------------+ |    | k8s-api |<-----+ |           | |
     | |                   |    +---------+  |     +-----------+ |
     | |                   |    +---------+  |                   |
     | |                   +--->|  etcd   |  |                   |
     | |                        +---------+  |                   |
     | |                         Master03 VM |                   |
     | +-------------------------------------+                   |
     +-----------------------------------------------------------+

Mgmt Driver supports the construction of an HA master node through the
``instantiate_end`` process as follows:

1. Identify the VMs created by OpenStackInfraDriver(which is
   used to create OpenStack resources).
2. Invoke the script to configure for HAProxy_ (a reliable solution
   offering high availability, load balancing, and proxying for
   TCP and HTTP-based applications) to start signal distribution
   to Master nodes.
3. Install all Master-nodes first, followed by Worker-nodes by
   invoking the script setting up the new Kubernetes cluster.

Preparations
------------
If you use the sample script to deploy your Kubernetes cluster, you need
to ensure that the virtual machine(VM) you created on the OpenStack can
access the external network. If you installed the tacker
service through ``devstack``, the following is an optional way to set the
network configuration.

.. note::
    In case of installed using ``devstack``, please execute all the
    following commands under the ``stack`` user. You can use
    ``sudo su stack`` command to change your user.

1. OpenStack Router
^^^^^^^^^^^^^^^^^^^

1. Create an OpenStack Router
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To ensure your VMs can access the external network, a router between
public network and internal network may be required. It can be created
by OpenStack dashboard or cli command. The following steps will
create a router between the ``public`` network and the internal ``net0``
network. The cli command is shown below:

.. code-block:: console

    $ openstack router create router-net0
    +-------------------------+--------------------------------------+
    | Field                   | Value                                |
    +-------------------------+--------------------------------------+
    | admin_state_up          | UP                                   |
    | availability_zone_hints |                                      |
    | availability_zones      |                                      |
    | created_at              | 2021-02-17T04:49:09Z                 |
    | description             |                                      |
    | distributed             | False                                |
    | external_gateway_info   | null                                 |
    | flavor_id               | None                                 |
    | ha                      | False                                |
    | id                      | 66fcada3-e101-4136-ad5a-ed4f0f2a7ac1 |
    | name                    | router-net0                          |
    | project_id              | 4e7c90a9c086427fbfc817ed6b372d97     |
    | revision_number         | 1                                    |
    | routes                  |                                      |
    | status                  | ACTIVE                               |
    | tags                    |                                      |
    | updated_at              | 2021-02-17T04:49:09Z                 |
    +-------------------------+--------------------------------------+
    $ openstack router set --external-gateway public router-net0
    $ openstack router show router-net0
    +-------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field                   | Value                                                                                                                                                                                                                           |
    +-------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | admin_state_up          | UP                                                                                                                                                                                                                              |
    | availability_zone_hints |                                                                                                                                                                                                                                 |
    | availability_zones      | nova                                                                                                                                                                                                                            |
    | created_at              | 2021-02-17T04:49:09Z                                                                                                                                                                                                            |
    | description             |                                                                                                                                                                                                                                 |
    | distributed             | False                                                                                                                                                                                                                           |
    | external_gateway_info   | {"network_id": "70459da3-e4ba-44a1-959c-ee1540bf532f", "external_fixed_ips": [{"subnet_id": "0fe68555-8d3a-4fcb-83e2-602744eab106", "ip_address": "192.168.10.4"}, {"subnet_id": "d1bebebe-dde4-486a-8bca-eb9939aec972",        |
    |                         | "ip_address": "2001:db8::2f0"}], "enable_snat": true}                                                                                                                                                                           |
    | flavor_id               | None                                                                                                                                                                                                                            |
    | ha                      | False                                                                                                                                                                                                                           |
    | id                      | 66fcada3-e101-4136-ad5a-ed4f0f2a7ac1                                                                                                                                                                                            |
    | interfaces_info         | []                                                                                                                                                                                                                              |
    | name                    | router-net0                                                                                                                                                                                                                     |
    | project_id              | 4e7c90a9c086427fbfc817ed6b372d97                                                                                                                                                                                                |
    | revision_number         | 3                                                                                                                                                                                                                               |
    | routes                  |                                                                                                                                                                                                                                 |
    | status                  | ACTIVE                                                                                                                                                                                                                          |
    | tags                    |                                                                                                                                                                                                                                 |
    | updated_at              | 2021-02-17T04:51:59Z                                                                                                                                                                                                            |
    +-------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    $ openstack router add subnet router-net0 subnet0
    $ openstack router show router-net0
    +-------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field                   | Value                                                                                                                                                                                                                           |
    +-------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | admin_state_up          | UP                                                                                                                                                                                                                              |
    | availability_zone_hints |                                                                                                                                                                                                                                 |
    | availability_zones      | nova                                                                                                                                                                                                                            |
    | created_at              | 2021-02-17T04:49:09Z                                                                                                                                                                                                            |
    | description             |                                                                                                                                                                                                                                 |
    | distributed             | False                                                                                                                                                                                                                           |
    | external_gateway_info   | {"network_id": "70459da3-e4ba-44a1-959c-ee1540bf532f", "external_fixed_ips": [{"subnet_id": "0fe68555-8d3a-4fcb-83e2-602744eab106", "ip_address": "192.168.10.4"}, {"subnet_id": "d1bebebe-dde4-486a-8bca-eb9939aec972",        |
    |                         | "ip_address": "2001:db8::2f0"}], "enable_snat": true}                                                                                                                                                                           |
    | flavor_id               | None                                                                                                                                                                                                                            |
    | ha                      | False                                                                                                                                                                                                                           |
    | id                      | 66fcada3-e101-4136-ad5a-ed4f0f2a7ac1                                                                                                                                                                                            |
    | interfaces_info         | [{"port_id": "0d2abb5d-7b01-4227-b5b4-325d153dfe4a", "ip_address": "10.10.0.1", "subnet_id": "70e60dee-b654-49ee-9692-147de8f07844"}]                                                                                           |
    | name                    | router-net0                                                                                                                                                                                                                     |
    | project_id              | 4e7c90a9c086427fbfc817ed6b372d97                                                                                                                                                                                                |
    | revision_number         | 4                                                                                                                                                                                                                               |
    | routes                  |                                                                                                                                                                                                                                 |
    | status                  | ACTIVE                                                                                                                                                                                                                          |
    | tags                    |                                                                                                                                                                                                                                 |
    | updated_at              | 2021-02-17T04:54:35Z                                                                                                                                                                                                            |
    +-------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Through the above command, you can get the gateway ip between the internal
net0 network and the external network. Here is ``192.168.10.4`` in the
``external_gateway_info``. The ``net0`` network's cidr is ``10.10.0.0/24``.

2. Set Route Rule in Controller Node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

According to the gateway ip obtained in step 1., you should add a route
rule in controller node of OpenStack. The command is shown below:

.. code-block:: console

    $ sudo route add -net 10.10.0.0/24 gw 192.168.10.4

3. Set the Security Group
~~~~~~~~~~~~~~~~~~~~~~~~~

In order to access the k8s cluster, you need to set the security group rules.
You can create a new security group or add the rules to
the ``default`` security group. The minimum settings are shown below using
cli command:

- get the nfv project's default security group id

.. code-block:: console

    $ auth='--os-username nfv_user --os-project-name nfv --os-password devstack  --os-auth-url http://127.0.0.1/identity --os-project-domain-name Default --os-user-domain-name Default'
    $ nfv_project_id=`openstack project list $auth | grep -w '| nfv' | awk '{print $2}'`
    $ default_id=`openstack security group list $auth | grep -w 'default' | grep $nfv_project_id | awk '{print $2}'`

- add new security group rule into default security group using the id above

.. code-block:: console

    #ssh 22 port
    $ openstack security group rule create --protocol tcp --dst-port 22 $default_id $auth
    #all tcp
    $ openstack security group rule create --protocol tcp $default_id $auth
    #all icmp
    $ openstack security group rule create --protocol icmp $default_id $auth
    #all udp
    $ openstack security group rule create --protocol udp $default_id $auth
    #dns 53 port
    $ openstack security group rule create --protocol tcp --dst-port 53 $default_id $auth
    #k8s port
    $ openstack security group rule create --protocol tcp --dst-port 6443 $default_id $auth
    $ openstack security group rule create --protocol tcp --dst-port 16443 $default_id $auth
    $ openstack security group rule create --protocol tcp --dst-port 2379:2380 $default_id $auth
    $ openstack security group rule create --protocol tcp --dst-port 10250:10255 $default_id $auth
    $ openstack security group rule create --protocol tcp --dst-port 30000:32767 $default_id $auth

2. Ubuntu Image
^^^^^^^^^^^^^^^

In this user guide, Ubuntu image is used for master/worker node.
To ensure that Mgmt Driver can access to VMs via SSH,
some configurations are required.

1. Download Ubuntu Image
~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can download the ubuntu image(version 20.04) from the official website.
The command is shown below:

.. code-block:: console

    $ wget -P /opt/stack/tacker/samples/mgmt_driver https://cloud-images.ubuntu.com/releases/focal/release/ubuntu-20.04-server-cloudimg-amd64.img

2. Install the libguestfs-tools
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you use the sample script to deploy the Kubernetes cluster, you need
to ensure the VM created by your image allows you to login using username
and password via SSH. However, the VM created by the ubuntu image downloaded
from official website does not allow you to login using username and
password via SSH. So you need to modify the ubuntu image. The following
is a way to modify the image using guestfish tool or you can modify
it using your own way. The way to install the tool is shown below:

.. code-block:: console

    $ sudo apt-get install libguestfs-tools
    $ guestfish --version
      guestfish 1.36.13

3. Set the Image's Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The guestfish tool can modify image's configuration using its own command.
The command is shown below:

.. code-block:: console

    $ cd /opt/stack/tacker/samples/mgmt_driver
    $ sudo guestfish -a ubuntu-20.04-server-cloudimg-amd64.img -i sh "sed -i 's/lock\_passwd\: True/lock\_passwd\: false/g' /etc/cloud/cloud.cfg"
    $ sudo guestfish -a ubuntu-20.04-server-cloudimg-amd64.img -i sh "sed -i '/[ ][ ][ ][ ][ ]lock\_passwd\: false/a\     plain\_text\_passwd\: ubuntu' /etc/cloud/cloud.cfg"
    $ sudo guestfish -a ubuntu-20.04-server-cloudimg-amd64.img -i sh "sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config"
    $ sha512sum ubuntu-20.04-server-cloudimg-amd64.img
    fb1a1e50f9af2df6ab18a69b6bc5df07ebe8ef962b37e556ce95350ffc8f4a1118617d486e2018d1b3586aceaeda799e6cc073f330a7ad8f0ec0416cbd825452

.. note::
    The hash of the ubuntu image is different after modifying, so you
    should calculate it by yourself. And the value should be written
    into the ``sample_kubernetes_df_simple.yaml`` and
    ``sample_kubernetes_df_complex.yaml`` defined in
    ``Create and Upload VNF Package``.

3. Set Tacker Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^

First, copy the sample script that was stored in
``tacker/samples/mgmt_driver/kubernetes_mgmt.py`` into the directory of
``tacker/tacker/vnfm/mgmt_drivers``.

.. code-block:: console

    $ cp /opt/stack/tacker/samples/mgmt_driver/kubernetes_mgmt.py /opt/stack/tacker/tacker/vnfm/mgmt_drivers/

1. Set the setup.cfg
~~~~~~~~~~~~~~~~~~~~

You have to register ``kubernetes_mgmt.py`` in the operation environment
of the tacker.
The sample script(``kubernetes_mgmt.py``) uses the
``mgmt-drivers-kubernetes`` field to register in Mgmt Driver.

.. code-block:: console

    $ vi /opt/stack/tacker/setup.cfg
    ...
    tacker.tacker.mgmt.drivers =
    noop = tacker.vnfm.mgmt_drivers.noop:VnfMgmtNoop
    openwrt = tacker.vnfm.mgmt_drivers.openwrt.openwrt:VnfMgmtOpenWRT
    vnflcm_noop = tacker.vnfm.mgmt_drivers.vnflcm_noop:VnflcmMgmtNoop
    mgmt-drivers-kubernetes = tacker.vnfm.mgmt_drivers.kubernetes_mgmt:KubernetesMgmtDriver
    ...

2. Set the tacker.conf
~~~~~~~~~~~~~~~~~~~~~~

Then find the ``vnflcm_mgmt_driver`` field in the ``tacker.conf``.
Add the ``mgmt-drivers-kubernetes`` defined in step 1 to it,
and separate by commas.

.. code-block:: console

    $ vi /etc/tacker/tacker.conf
    ...
    [tacker]
    ...
    vnflcm_mgmt_driver = vnflcm_noop,mgmt-drivers-kubernetes
    ...

3. Update the tacker.egg-info
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After the above two steps, the configuration has
not yet taken effect.
You also need to execute the ``setup.py`` script to regenerate
the contents of the ``tacker.egg-info`` directory.

.. code-block:: console

    $ cd /opt/stack/tacker/
    $ python setup.py build
    running build
    running build_py
    running egg_info
    writing requirements to tacker.egg-info/requires.txt
    writing tacker.egg-info/PKG-INFO
    writing top-level names to tacker.egg-info/top_level.txt
    writing dependency_links to tacker.egg-info/dependency_links.txt
    writing entry points to tacker.egg-info/entry_points.txt
    writing pbr to tacker.egg-info/pbr.json
    [pbr] Processing SOURCES.txt
    [pbr] In git context, generating filelist from git
    warning: no files found matching 'AUTHORS'
    warning: no files found matching 'ChangeLog'
    warning: no previously-included files matching '*.pyc' found anywhere in distribution
    writing manifest file 'tacker.egg-info/SOURCES.txt'

Then you can use Mgmt Driver to deploy Kubernetes cluster after
restarting the service of ``tacker`` and ``tacker-conductor``.

.. code-block:: console

    $ sudo systemctl stop devstack@tacker
    $ sudo systemctl restart devstack@tacker-conductor
    $ sudo systemctl start devstack@tacker

Create and Upload VNF Package
-----------------------------

VNF Package is a ZIP file including VNFD, software images for VM, and other
artifact resources such as scripts and config files. The directory structure
and file contents are defined in `NFV-SOL004 v2.6.1`_.
According to `NFV-SOL004 v2.6.1`_, VNF Package should be the ZIP file format
with the `TOSCA-Simple-Profile-YAML-v1.2`_ Specifications.
In this user guide, the CSAR with TOSCA-Metadata directory is used to deploy
Kubernetes cluster.

.. note::

    For more detailed definitions of VNF Package, you can see `VNF Package`_.

1. Directory Structure
^^^^^^^^^^^^^^^^^^^^^^
The sample structure of VNF Package for both simple case and complex case
is shown below.

.. note::

    You can also find them in the ``samples/mgmt_driver/kubernetes_vnf_package/`` directory of the tacker.

The directory structure:

* **TOSCA-Metadata/TOSCA.meta**
* **Definitions/**
* **Files/images/**
* **Scripts/**
* **BaseHOT/**
* **UserData/**

.. code-block:: console

  !----TOSCA-Metadata
          !---- TOSCA.meta
  !----Definitions
          !---- etsi_nfv_sol001_common_types.yaml
          !---- etsi_nfv_sol001_vnfd_types.yaml
          !---- sample_kubernetes_top.vnfd.yaml
          !---- sample_kubernetes_types.yaml
          !---- sample_kubernetes_df_simple.yaml
          !---- sample_kubernetes_df_complex.yaml
  !----Files
          !---- images
                  !---- ubuntu-20.04-server-cloudimg-amd64.img
  !----Scripts
          !---- install_k8s_cluster.sh
          !---- kubernetes_mgmt.py
  !----BaseHOT
          !---- simple
                  !---- nested
                          !---- simple_nested_master.yaml
                          !---- simple_nested_worker.yaml
                  !---- simple_hot_top.yaml
          !---- complex
                  !---- nested
                          !---- complex_nested_master.yaml
                          !---- complex_nested_worker.yaml
                  !---- complex_hot_top.yaml
  !----UserData
          !---- __init__.py
          !---- k8s_cluster_user_data.py

TOSCA-Metadata/TOSCA.meta
~~~~~~~~~~~~~~~~~~~~~~~~~

According to `TOSCA-Simple-Profile-YAML-v1.2`_ specifications, the
``TOSCA.meta`` metadata file is described in `TOSCA-1.0-specification`_.
The files under ``Scripts`` directory are artifact files, therefore, you
should add their location and digest into ``TOSCA.meta`` metadata file.
The sample file is shown below:

* `TOSCA.meta`_

Definitions/
~~~~~~~~~~~~
All VNFD YAML files are located here. In this guide, there are two types
of definition files, ETSI NFV types definition file and User defined types
definition file.

ETSI NFV provides two types of definition files [#f1]_ which
contain all defined type definitions in `NFV-SOL001 v2.6.1`_.
You can download them from official website.

* `etsi_nfv_sol001_common_types.yaml`_
* `etsi_nfv_sol001_vnfd_types.yaml`_

You can extend their own types definition from `NFV-SOL001 v2.6.1`_. In most
cases, you need to extend ``tosca.nodes.nfv.VNF`` to define your VNF node
types. In this guide, ``sample_kubernetes_df_simple.yaml`` is used in simple
case, ``sample_kubernetes_df_complex.yaml`` is used in complex case. The two
files can be distinguished by ``deployment_flavour``. The sample files are
shown below:

* `sample_kubernetes_top.vnfd.yaml`_

* `sample_kubernetes_types.yaml`_

* `sample_kubernetes_df_simple.yaml`_

* `sample_kubernetes_df_complex.yaml`_

Files/images/
~~~~~~~~~~~~~

VNF Software Images are located here. These files are also described in
``TOSCA.meta``. The image used for deploying Kubernetes cluster is
``ubuntu-20.04-server-cloudimg-amd64.img`` downloaded in
``Download Image``.

Scripts/
~~~~~~~~

There are two script files for deploying Kubernetes cluster.
``install_k8s_cluster.sh`` is used to install k8s cluster on
VM created by tacker. ``kubernetes_mgmt.py`` is a Mgmt Driver
file to be executed before or after instantiate, terminate,
scale and heal. You can obtain these scripts in the directory
at the same level as this guide.

* `install_k8s_cluster.sh`_
* `kubernetes_mgmt.py`_

BaseHOT/
~~~~~~~~

Base HOT file is a Native cloud orchestration template, HOT in this context,
which is commonly used for LCM operations in different VNFs. It is the
responsibility of the user to prepare this file, and it is necessary to make
it consistent with VNFD placed under the **Definitions/** directory.

In this guide, you must use user data to deploy the Kubernetes cluster, so the
BaseHot directory must be included.

You must place the directory corresponding to **deployment_flavour** stored in
the **Definitions/** under the **BaseHOT/** directory, and store the
Base HOT files in it.

In this guide, there are two cases(simple and complex) in this VNF Package, so
there are two directories under **BaseHOT/** directory. The sample files are
shown below:

simple
::::::

* `nested/simple_nested_master.yaml`_

* `nested/simple_nested_worker.yaml`_

* `simple_hot_top.yaml`_

complex
:::::::

* `nested/complex_nested_master.yaml`_

* `nested/complex_nested_worker.yaml`_

* `complex_hot_top.yaml`_

UserData/
~~~~~~~~~

LCM operation user data is a script that returns key/value data as
Heat input parameters used for Base HOT. The sample file is shown below:

* `k8s_cluster_user_data.py`_

2. Create VNF Package
^^^^^^^^^^^^^^^^^^^^^

Execute the following CLI command to create VNF Package.

.. code-block:: console

    $ openstack vnf package create


Result:

.. code-block:: console

    $ openstack vnf package create
    +-------------------+-------------------------------------------------------------------------------------------------+
    | Field             | Value                                                                                           |
    +-------------------+-------------------------------------------------------------------------------------------------+
    | ID                | 03a8eb3e-a981-434e-a548-82d9b90161d7                                                            |
    | Links             | {                                                                                               |
    |                   |     "self": {                                                                                   |
    |                   |         "href": "/vnfpkgm/v1/vnf_packages/03a8eb3e-a981-434e-a548-82d9b90161d7"                 |
    |                   |     },                                                                                          |
    |                   |     "packageContent": {                                                                         |
    |                   |         "href": "/vnfpkgm/v1/vnf_packages/03a8eb3e-a981-434e-a548-82d9b90161d7/package_content" |
    |                   |     }                                                                                           |
    |                   | }                                                                                               |
    | Onboarding State  | CREATED                                                                                         |
    | Operational State | DISABLED                                                                                        |
    | Usage State       | NOT_IN_USE                                                                                      |
    | User Defined Data | {}                                                                                              |
    +-------------------+-------------------------------------------------------------------------------------------------+

3. Upload VNF Package
^^^^^^^^^^^^^^^^^^^^^

Before you instantiate VNF, you must create a zip file of VNF Package
and upload it.

Execute the following command to make a zip file.

.. code-block:: console

    $ zip sample_kubernetes_csar.zip -r Definitions/ Files/ TOSCA-Metadata/ BaseHOT/ UserData/ Scripts/

Execute the following CLI command to upload VNF Package.

.. code-block:: console

    $ openstack vnf package upload --path ./sample_kubernetes_csar.zip 03a8eb3e-a981-434e-a548-82d9b90161d7


Result:

.. code-block:: console

    Upload request for VNF package 03a8eb3e-a981-434e-a548-82d9b90161d7 has been accepted.


After that, execute the following CLI command and confirm that
VNF Package uploading was successful.

* Confirm that the 'Onboarding State' is 'ONBOARDED'.
* Confirm that the 'Operational State' is 'ENABLED'.
* Confirm that the 'Usage State' is 'NOT_IN_USE'.
* Take a note of the 'VNFD ID' because you will need it in the next
  'Deploy Kubernetes cluster'.

.. code-block:: console

    $ openstack vnf package show 03a8eb3e-a981-434e-a548-82d9b90161d7
    +----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field                | Value                                                                                                                                                  |
    +----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Additional Artifacts | [                                                                                                                                                      |
    |                      |     {                                                                                                                                                  |
    |                      |         "artifactPath": "Scripts/install_k8s_cluster.sh",                                                                                              |
    |                      |         "checksum": {                                                                                                                                  |
    |                      |             "algorithm": "SHA-256",                                                                                                                    |
    |                      |             "hash": "7f1f4518a3db7b386a473aebf0aa2561eaa94073ac4c95b9d3e7b3fb5bba3017"                                                                 |
    |                      |         },                                                                                                                                             |
    |                      |         "metadata": {}                                                                                                                                 |
    |                      |     },                                                                                                                                                 |
    |                      |     {                                                                                                                                                  |
    |                      |         "artifactPath": "Scripts/kubernetes_mgmt.py",                                                                                                  |
    |                      |         "checksum": {                                                                                                                                  |
    |                      |             "algorithm": "SHA-256",                                                                                                                    |
    |                      |             "hash": "3d8fc578cca5eec0fb625fc3f5eeaa67c34c2a5f89329ed9307f343cfc25cdc4"                                                                 |
    |                      |         },                                                                                                                                             |
    |                      |         "metadata": {}                                                                                                                                 |
    |                      |     }                                                                                                                                                  |
    |                      | ]                                                                                                                                                      |
    | Checksum             | {                                                                                                                                                      |
    |                      |     "hash": "d853ca27df5ad5270516adc8ec3cef6ebf982f09f2291eb150c677691d2c793e454e0feb61f211a2b4b8b6df899ab2f2c808684ae1f9100081e5375f8bfcec3d",        |
    |                      |     "algorithm": "sha512"                                                                                                                              |
    |                      | }                                                                                                                                                      |
    | ID                   | 03a8eb3e-a981-434e-a548-82d9b90161d7                                                                                                                   |
    | Links                | {                                                                                                                                                      |
    |                      |     "self": {                                                                                                                                          |
    |                      |         "href": "/vnfpkgm/v1/vnf_packages/03a8eb3e-a981-434e-a548-82d9b90161d7"                                                                        |
    |                      |     },                                                                                                                                                 |
    |                      |     "packageContent": {                                                                                                                                |
    |                      |         "href": "/vnfpkgm/v1/vnf_packages/03a8eb3e-a981-434e-a548-82d9b90161d7/package_content"                                                        |
    |                      |     }                                                                                                                                                  |
    |                      | }                                                                                                                                                      |
    | Onboarding State     | ONBOARDED                                                                                                                                              |
    | Operational State    | ENABLED                                                                                                                                                |
    | Software Images      | [                                                                                                                                                      |
    |                      |     {                                                                                                                                                  |
    |                      |         "size": 2000000000,                                                                                                                            |
    |                      |         "version": "20.04",                                                                                                                            |
    |                      |         "name": "Image for masterNode kubernetes",                                                                                                     |
    |                      |         "createdAt": "2021-02-18 08:49:39+00:00",                                                                                                      |
    |                      |         "id": "masterNode",                                                                                                                            |
    |                      |         "containerFormat": "bare",                                                                                                                     |
    |                      |         "minDisk": 0,                                                                                                                                  |
    |                      |         "imagePath": "",                                                                                                                               |
    |                      |         "minRam": 0,                                                                                                                                   |
    |                      |         "diskFormat": "qcow2",                                                                                                                         |
    |                      |         "provider": "",                                                                                                                                |
    |                      |         "checksum": {                                                                                                                                  |
    |                      |             "algorithm": "sha-512",                                                                                                                    |
    |                      |             "hash": "fb1a1e50f9af2df6ab18a69b6bc5df07ebe8ef962b37e556ce95350ffc8f4a1118617d486e2018d1b3586aceaeda799e6cc073f330a7ad8f0ec0416cbd825452" |
    |                      |         },                                                                                                                                             |
    |                      |         "userMetadata": {}                                                                                                                             |
    |                      |     },                                                                                                                                                 |
    |                      |     {                                                                                                                                                  |
    |                      |         "size": 2000000000,                                                                                                                            |
    |                      |         "version": "20.04",                                                                                                                            |
    |                      |         "name": "Image for workerNode kubernetes",                                                                                                     |
    |                      |         "createdAt": "2021-02-18 08:49:40+00:00",                                                                                                      |
    |                      |         "id": "workerNode",                                                                                                                            |
    |                      |         "containerFormat": "bare",                                                                                                                     |
    |                      |         "minDisk": 0,                                                                                                                                  |
    |                      |         "imagePath": "",                                                                                                                               |
    |                      |         "minRam": 0,                                                                                                                                   |
    |                      |         "diskFormat": "qcow2",                                                                                                                         |
    |                      |         "provider": "",                                                                                                                                |
    |                      |         "checksum": {                                                                                                                                  |
    |                      |             "algorithm": "sha-512",                                                                                                                    |
    |                      |             "hash": "fb1a1e50f9af2df6ab18a69b6bc5df07ebe8ef962b37e556ce95350ffc8f4a1118617d486e2018d1b3586aceaeda799e6cc073f330a7ad8f0ec0416cbd825452" |
    |                      |         },                                                                                                                                             |
    |                      |         "userMetadata": {}                                                                                                                             |
    |                      |     },                                                                                                                                                 |
    |                      |     {                                                                                                                                                  |
    |                      |         "size": 2000000000,                                                                                                                            |
    |                      |         "version": "20.04",                                                                                                                            |
    |                      |         "name": "Image for workerNode kubernetes",                                                                                                     |
    |                      |         "createdAt": "2021-02-18 08:49:39+00:00",                                                                                                      |
    |                      |         "id": "workerNode",                                                                                                                            |
    |                      |         "containerFormat": "bare",                                                                                                                     |
    |                      |         "minDisk": 0,                                                                                                                                  |
    |                      |         "imagePath": "",                                                                                                                               |
    |                      |         "minRam": 0,                                                                                                                                   |
    |                      |         "diskFormat": "qcow2",                                                                                                                         |
    |                      |         "provider": "",                                                                                                                                |
    |                      |         "checksum": {                                                                                                                                  |
    |                      |             "algorithm": "sha-512",                                                                                                                    |
    |                      |             "hash": "fb1a1e50f9af2df6ab18a69b6bc5df07ebe8ef962b37e556ce95350ffc8f4a1118617d486e2018d1b3586aceaeda799e6cc073f330a7ad8f0ec0416cbd825452" |
    |                      |         },                                                                                                                                             |
    |                      |         "userMetadata": {}                                                                                                                             |
    |                      |     },                                                                                                                                                 |
    |                      |     {                                                                                                                                                  |
    |                      |         "size": 2000000000,                                                                                                                            |
    |                      |         "version": "20.04",                                                                                                                            |
    |                      |         "name": "Image for masterNode kubernetes",                                                                                                     |
    |                      |         "createdAt": "2021-02-18 08:49:39+00:00",                                                                                                      |
    |                      |         "id": "masterNode",                                                                                                                            |
    |                      |         "containerFormat": "bare",                                                                                                                     |
    |                      |         "minDisk": 0,                                                                                                                                  |
    |                      |         "imagePath": "",                                                                                                                               |
    |                      |         "minRam": 0,                                                                                                                                   |
    |                      |         "diskFormat": "qcow2",                                                                                                                         |
    |                      |         "provider": "",                                                                                                                                |
    |                      |         "checksum": {                                                                                                                                  |
    |                      |             "algorithm": "sha-512",                                                                                                                    |
    |                      |             "hash": "fb1a1e50f9af2df6ab18a69b6bc5df07ebe8ef962b37e556ce95350ffc8f4a1118617d486e2018d1b3586aceaeda799e6cc073f330a7ad8f0ec0416cbd825452" |
    |                      |         },                                                                                                                                             |
    |                      |         "userMetadata": {}                                                                                                                             |
    |                      |     }                                                                                                                                                  |
    |                      | ]                                                                                                                                                      |
    | Usage State          | NOT_IN_USE                                                                                                                                             |
    | User Defined Data    | {}                                                                                                                                                     |
    | VNF Product Name     | Sample VNF                                                                                                                                             |
    | VNF Provider         | Company                                                                                                                                                |
    | VNF Software Version | 1.0                                                                                                                                                    |
    | VNFD ID              | b1db0ce7-ebca-1fb7-95ed-4840d70a1163                                                                                                                   |
    | VNFD Version         | 1.0                                                                                                                                                    |
    +----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+

Deploy Kubernetes Cluster
-------------------------

1. Single Master Node
^^^^^^^^^^^^^^^^^^^^^

A single master Kubernetes cluster can be installed and set up in
"instantiate_end" operation, which allows you to execute any
scripts after its instantiation, and it's enabled with Mgmt Driver
support. The instantiated Kubernetes cluster only supports one
master node and multiple worker nodes. The instantiated Kubernetes
cluster will be automatically registered as VIM. Then you can use
the VIM to deploy CNF.

If you want to deploy a single master Kubernetes cluster, you can
use VNF Package with 'simple' flavour created in
``Create and Upload VNF Package``.
The most important thing is that you must create the parameter file which
is used to instantiate correctly. The following are the methods of creating
the parameter file and cli commands of OpenStack.

1. Create the Parameter File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a ``simple_kubernetes_param_file.json`` file with the following format.
This is the file that defines the parameters for an instantiate request.
These parameters will be set in the body of the instantiate request.

Required parameter:

* flavourId
* additionalParams

.. note::
    [This is UserData specific part]
    additionalParams is a parameter that can be described by KeyValuePairs.
    By setting the following two parameters in this parameter,
    instantiate using LCM operation user data becomes possible.
    For file_name.py and class_name, set the file name and class name
    described in Prerequisites.

    * lcm-operation-user-data: ./UserData/file_name.py
    * lcm-operation-user-data-class: class_name

Optional parameters:

* instantiationLevelId
* extVirtualLinks
* extManagedVirtualLinks
* vimConnectionInfo

In this guide, the VMs need to have extCPs to be accessed via SSH by Tacker.
Therefore, ``extVirtualLinks`` parameter is required. You can skip
``vimConnectionInfo`` only when you have the default VIM described in
`cli-legacy-vim`_.

**Explanation of the parameters for deploying a Kubernetes cluster**

For deploying Kubernetes cluster, you must set the
``k8s_cluster_installation_param`` key in additionalParams.
The KeyValuePairs is shown in table below:

.. code-block::

    ## List of additionalParams.k8s_cluster_installation_param(specified by user)
    +------------------+-----------+---------------------------------------------+-------------------+
    | parameter        | data type | description                                 | required/optional |
    +------------------+-----------+---------------------------------------------+-------------------+
    | script_path      | String    | The path where the Kubernetes installation  | required          |
    |                  |           | script stored in the VNF Package            |                   |
    +------------------+-----------+---------------------------------------------+-------------------+
    | vim_name         | String    | The vim name of deployed Kubernetes cluster | optional          |
    |                  |           | registered by tacker                        |                   |
    +------------------+-----------+---------------------------------------------+-------------------+
    | master_node      | dict      | Information for the VM of the master node   | required          |
    |                  |           | group                                       |                   |
    +------------------+-----------+---------------------------------------------+-------------------+
    | worker_node      | dict      | Information for the VM of the worker node   | required          |
    |                  |           | group                                       |                   |
    +------------------+-----------+---------------------------------------------+-------------------+
    | proxy            | dict      | Information for proxy setting on VM         | optional          |
    +------------------+-----------+---------------------------------------------+-------------------+

    ## master_node dict
    +------------------+-----------+---------------------------------------------+-------------------+
    | parameter        | data type | description                                 | required/optional |
    +------------------+-----------+---------------------------------------------+-------------------+
    | aspect_id        | String    | The resource name of the master node group, | optional          |
    |                  |           | and is same as the `aspect` in `vnfd`. If   |                   |
    |                  |           | you use user data, it must be set           |                   |
    +------------------+-----------+---------------------------------------------+-------------------+
    | ssh_cp_name      | String    | Resource name of port corresponding to the  | required          |
    |                  |           | master node's ssh ip                        |                   |
    +------------------+-----------+---------------------------------------------+-------------------+
    | nic_cp_name      | String    | Resource name of port corresponding to the  | required          |
    |                  |           | master node's nic ip(which used for         |                   |
    |                  |           | deploying Kubernetes cluster)               |                   |
    +------------------+-----------+---------------------------------------------+-------------------+
    | username         | String    | Username for VM access                      | required          |
    +------------------+-----------+---------------------------------------------+-------------------+
    | password         | String    | Password for VM access                      | required          |
    +------------------+-----------+---------------------------------------------+-------------------+
    | pod_cidr         | String    | CIDR for pod                                | optional          |
    +------------------+-----------+---------------------------------------------+-------------------+
    | cluster_cidr     | String    | CIDR for service                            | optional          |
    +------------------+-----------+---------------------------------------------+-------------------+
    | cluster_cp_name  | String    | Resource name of the Port corresponding to  | required          |
    |                  |           | cluster ip                                  |                   |
    +------------------+-----------+---------------------------------------------+-------------------+
    | cluster_fip_name | String    | Resource name of the Port corresponding to  | optional          |
    |                  |           | cluster ip used for reigstering vim. If you |                   |
    |                  |           | use floating ip as ssh ip, it must be set   |                   |
    +------------------+-----------+---------------------------------------------+-------------------+

    ## worker_node dict
    +------------------+-----------+---------------------------------------------+-------------------+
    | parameter        | data type | description                                 | required/optional |
    +------------------+-----------+---------------------------------------------+-------------------+
    | aspect_id        | String    | The resource name of the worker node group, | optional          |
    |                  |           | and is same as the `aspect` in `vnfd`. If   |                   |
    |                  |           | you use user data, it must be set           |                   |
    +------------------+-----------+---------------------------------------------+-------------------+
    | ssh_cp_name      | String    | Resource name of port corresponding to the  | required          |
    |                  |           | worker node's ssh ip                        |                   |
    +------------------+-----------+---------------------------------------------+-------------------+
    | nic_cp_name      | String    | Resource name of port corresponding to the  | required          |
    |                  |           | worker node's nic ip(which used for         |                   |
    |                  |           | deploying Kubernetes cluster)               |                   |
    +------------------+-----------+---------------------------------------------+-------------------+
    | username         | String    | Username for VM access                      | required          |
    +------------------+-----------+---------------------------------------------+-------------------+
    | password         | String    | Password for VM access                      | required          |
    +------------------+-----------+---------------------------------------------+-------------------+

    ## proxy dict
    +------------------+-----------+---------------------------------------------+-------------------+
    | parameter        | data type | description                                 | required/optional |
    +------------------+-----------+---------------------------------------------+-------------------+
    | http_proxy       | string    | Http proxy server address                   | optional          |
    +------------------+-----------+---------------------------------------------+-------------------+
    | https_proxy      | string    | Https proxy server address                  | optional          |
    +------------------+-----------+---------------------------------------------+-------------------+
    | no_proxy         | string    | User-customized, proxy server-free IP       | optional          |
    |                  |           | address or segment                          |                   |
    +------------------+-----------+---------------------------------------------+-------------------+
    | k8s_node_cidr    | string    | CIDR for Kubernetes node, all its ip will be| optional          |
    |                  |           | set into no_proxy                           |                   |
    +------------------+-----------+---------------------------------------------+-------------------+

simple_kubernetes_param_file.json

.. code-block::


    {
        "flavourId": "simple",
        "vimConnectionInfo": [{
            "id": "3cc2c4ff-525c-48b4-94c9-29247223322f",
            "vimId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496", #Set the uuid of the VIM to use
            "vimType": "openstack"
        }],
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
                }
            },
            "lcm-operation-user-data": "./UserData/k8s_cluster_user_data.py",
            "lcm-operation-user-data-class": "KubernetesClusterUserData"
        },
        "extVirtualLinks": [{
            "id": "net0_master",
            "resourceId": "71a3fbd1-f31e-4c2c-b0e2-26267d64a9ee",  #Set the uuid of the network to use
            "extCps": [{
                "cpdId": "masterNode_CP1",
                "cpConfig": [{
                    "cpProtocolData": [{
                        "layerProtocol": "IP_OVER_ETHERNET"
                    }]
                }]
            }]
        }, {
            "id": "net0_worker",
            "resourceId": "71a3fbd1-f31e-4c2c-b0e2-26267d64a9ee",  #Set the uuid of the network to use
            "extCps": [{
                "cpdId": "workerNode_CP2",
                "cpConfig": [{
                    "cpProtocolData": [{
                        "layerProtocol": "IP_OVER_ETHERNET"
                    }]
                }]
            }]
        }]
    }


2. Execute the Instantiation Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute the following CLI command to instantiate the VNF instance.

.. code-block:: console

    $ openstack vnflcm create b1db0ce7-ebca-1fb7-95ed-4840d70a1163
    +--------------------------+---------------------------------------------------------------------------------------------+
    | Field                    | Value                                                                                       |
    +--------------------------+---------------------------------------------------------------------------------------------+
    | ID                       | 3f32428d-e8ce-4d6a-9be9-4c7f3a02ac72                                                        |
    | Instantiation State      | NOT_INSTANTIATED                                                                            |
    | Links                    | {                                                                                           |
    |                          |     "self": {                                                                               |
    |                          |         "href": "/vnflcm/v1/vnf_instances/3f32428d-e8ce-4d6a-9be9-4c7f3a02ac72"             |
    |                          |     },                                                                                      |
    |                          |     "instantiate": {                                                                        |
    |                          |         "href": "/vnflcm/v1/vnf_instances/3f32428d-e8ce-4d6a-9be9-4c7f3a02ac72/instantiate" |
    |                          |     }                                                                                       |
    |                          | }                                                                                           |
    | VNF Instance Description | None                                                                                        |
    | VNF Instance Name        | vnf-3f32428d-e8ce-4d6a-9be9-4c7f3a02ac72                                                    |
    | VNF Product Name         | Sample VNF                                                                                  |
    | VNF Provider             | Company                                                                                     |
    | VNF Software Version     | 1.0                                                                                         |
    | VNFD ID                  | b1db0ce7-ebca-1fb7-95ed-4840d70a1163                                                        |
    | VNFD Version             | 1.0                                                                                         |
    | vnfPkgId                 |                                                                                             |
    +--------------------------+---------------------------------------------------------------------------------------------+
    $ openstack vnflcm instantiate 3f32428d-e8ce-4d6a-9be9-4c7f3a02ac72 ./simple_kubernetes_param_file.json
    Instantiate request for VNF Instance 3f32428d-e8ce-4d6a-9be9-4c7f3a02ac72 has been accepted.
    $ openstack vnflcm show 3f32428d-e8ce-4d6a-9be9-4c7f3a02ac72
    +--------------------------+-------------------------------------------------------------------------------------------+
    | Field                    | Value                                                                                     |
    +--------------------------+-------------------------------------------------------------------------------------------+
    | ID                       | 3f32428d-e8ce-4d6a-9be9-4c7f3a02ac72                                                      |
    | Instantiated Vnf Info    | {                                                                                         |
    |                          |     "flavourId": "simple",                                                                |
    |                          |     "vnfState": "STARTED",                                                                |
    |                          |     "scaleStatus": [                                                                      |
    |                          |         {                                                                                 |
    |                          |             "aspectId": "master_instance",                                                |
    |                          |             "scaleLevel": 0                                                               |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "aspectId": "worker_instance",                                                |
    |                          |             "scaleLevel": 0                                                               |
    |                          |         }                                                                                 |
    |                          |     ],                                                                                    |
    |                          |     "extCpInfo": [                                                                        |
    |                          |         {                                                                                 |
    |                          |             "id": "d6ed7fd0-c26e-4e1e-81ab-71dc8c6d8293",                                 |
    |                          |             "cpdId": "masterNode_CP1",                                                    |
    |                          |             "extLinkPortId": null,                                                        |
    |                          |             "associatedVnfcCpId": "1f830544-57ef-4f93-bdb5-b59e465f58d8",                 |
    |                          |             "cpProtocolInfo": [                                                           |
    |                          |                 {                                                                         |
    |                          |                     "layerProtocol": "IP_OVER_ETHERNET"                                   |
    |                          |                 }                                                                         |
    |                          |             ]                                                                             |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "ba0f7de5-32b3-48dd-944d-341990ede0cb",                                 |
    |                          |             "cpdId": "workerNode_CP2",                                                    |
    |                          |             "extLinkPortId": null,                                                        |
    |                          |             "associatedVnfcCpId": "9244012d-ad53-4685-912b-f6413ae38493",                 |
    |                          |             "cpProtocolInfo": [                                                           |
    |                          |                 {                                                                         |
    |                          |                     "layerProtocol": "IP_OVER_ETHERNET"                                   |
    |                          |                 }                                                                         |
    |                          |             ]                                                                             |
    |                          |         }                                                                                 |
    |                          |     ],                                                                                    |
    |                          |     "extVirtualLinkInfo": [                                                               |
    |                          |         {                                                                                 |
    |                          |             "id": "b396126a-6a95-4a24-94ae-67b58f5bd9c2",                                 |
    |                          |             "resourceHandle": {                                                           |
    |                          |                 "vimConnectionId": null,                                                  |
    |                          |                 "resourceId": "71a3fbd1-f31e-4c2c-b0e2-26267d64a9ee",                     |
    |                          |                 "vimLevelResourceType": null                                              |
    |                          |             }                                                                             |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "10dfbb44-a8ff-435b-98f8-70539e71af8c",                                 |
    |                          |             "resourceHandle": {                                                           |
    |                          |                 "vimConnectionId": null,                                                  |
    |                          |                 "resourceId": "71a3fbd1-f31e-4c2c-b0e2-26267d64a9ee",                     |
    |                          |                 "vimLevelResourceType": null                                              |
    |                          |             }                                                                             |
    |                          |         }                                                                                 |
    |                          |     ],                                                                                    |
    |                          |     "vnfcResourceInfo": [                                                                 |
    |                          |         {                                                                                 |
    |                          |             "id": "1f830544-57ef-4f93-bdb5-b59e465f58d8",                                 |
    |                          |             "vduId": "masterNode",                                                        |
    |                          |             "computeResource": {                                                          |
    |                          |                 "vimConnectionId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",                |
    |                          |                 "resourceId": "a0eccaee-ff7b-4c70-8c11-ba79c8d4deb6",                     |
    |                          |                 "vimLevelResourceType": "OS::Nova::Server"                                |
    |                          |             },                                                                            |
    |                          |             "storageResourceIds": [],                                                     |
    |                          |             "vnfcCpInfo": [                                                               |
    |                          |                 {                                                                         |
    |                          |                     "id": "9fe655ab-1d35-4d22-a6f3-9a07fa797884",                         |
    |                          |                     "cpdId": "masterNode_CP1",                                            |
    |                          |                     "vnfExtCpId": null,                                                   |
    |                          |                     "vnfLinkPortId": "e66a44a4-965f-49dd-b168-ff4cc2485c34",              |
    |                          |                     "cpProtocolInfo": [                                                   |
    |                          |                         {                                                                 |
    |                          |                             "layerProtocol": "IP_OVER_ETHERNET"                           |
    |                          |                         }                                                                 |
    |                          |                     ]                                                                     |
    |                          |                 }                                                                         |
    |                          |             ]                                                                             |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "9244012d-ad53-4685-912b-f6413ae38493",                                 |
    |                          |             "vduId": "workerNode",                                                        |
    |                          |             "computeResource": {                                                          |
    |                          |                 "vimConnectionId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",                |
    |                          |                 "resourceId": "5b3ff765-7a9f-447a-a06d-444e963b74c9",                     |
    |                          |                 "vimLevelResourceType": "OS::Nova::Server"                                |
    |                          |             },                                                                            |
    |                          |             "storageResourceIds": [],                                                     |
    |                          |             "vnfcCpInfo": [                                                               |
    |                          |                 {                                                                         |
    |                          |                     "id": "59176610-fc1c-4abe-9648-87a9b8b79640",                         |
    |                          |                     "cpdId": "workerNode_CP2",                                            |
    |                          |                     "vnfExtCpId": null,                                                   |
    |                          |                     "vnfLinkPortId": "977b8775-350d-4ef0-95e5-552c4c4099f3",              |
    |                          |                     "cpProtocolInfo": [                                                   |
    |                          |                         {                                                                 |
    |                          |                             "layerProtocol": "IP_OVER_ETHERNET"                           |
    |                          |                         }                                                                 |
    |                          |                     ]                                                                     |
    |                          |                 }                                                                         |
    |                          |             ]                                                                             |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "974a4b98-5d07-44d4-9e13-a8ed21805111",                                 |
    |                          |             "vduId": "workerNode",                                                        |
    |                          |             "computeResource": {                                                          |
    |                          |                 "vimConnectionId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",                |
    |                          |                 "resourceId": "63402e5a-67c9-4f5c-b03f-b21f4a88507f",                     |
    |                          |                 "vimLevelResourceType": "OS::Nova::Server"                                |
    |                          |             },                                                                            |
    |                          |             "storageResourceIds": [],                                                     |
    |                          |             "vnfcCpInfo": [                                                               |
    |                          |                 {                                                                         |
    |                          |                     "id": "523b1328-9704-4ac1-986f-99c9b46ee1c4",                         |
    |                          |                     "cpdId": "workerNode_CP2",                                            |
    |                          |                     "vnfExtCpId": null,                                                   |
    |                          |                     "vnfLinkPortId": "eba708c4-14de-4d96-bc82-ed0abd95780b",              |
    |                          |                     "cpProtocolInfo": [                                                   |
    |                          |                         {                                                                 |
    |                          |                             "layerProtocol": "IP_OVER_ETHERNET"                           |
    |                          |                         }                                                                 |
    |                          |                     ]                                                                     |
    |                          |                 }                                                                         |
    |                          |             ]                                                                             |
    |                          |         }                                                                                 |
    |                          |     ],                                                                                    |
    |                          |     "vnfVirtualLinkResourceInfo": [                                                       |
    |                          |         {                                                                                 |
    |                          |             "id": "96d15ae5-a1d8-4867-aaee-a4372de8bc0e",                                 |
    |                          |             "vnfVirtualLinkDescId": "b396126a-6a95-4a24-94ae-67b58f5bd9c2",               |
    |                          |             "networkResource": {                                                          |
    |                          |                 "vimConnectionId": null,                                                  |
    |                          |                 "resourceId": "71a3fbd1-f31e-4c2c-b0e2-26267d64a9ee",                     |
    |                          |                 "vimLevelResourceType": "OS::Neutron::Net"                                |
    |                          |             },                                                                            |
    |                          |             "vnfLinkPorts": [                                                             |
    |                          |                 {                                                                         |
    |                          |                     "id": "e66a44a4-965f-49dd-b168-ff4cc2485c34",                         |
    |                          |                     "resourceHandle": {                                                   |
    |                          |                         "vimConnectionId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",        |
    |                          |                         "resourceId": "b5ed388b-de4e-4de8-a24a-f1b70c5cce94",             |
    |                          |                         "vimLevelResourceType": "OS::Neutron::Port"                       |
    |                          |                     },                                                                    |
    |                          |                     "cpInstanceId": "9fe655ab-1d35-4d22-a6f3-9a07fa797884"                |
    |                          |                 }                                                                         |
    |                          |             ]                                                                             |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "c67b6f41-fd7a-45b2-b69a-8de9623dc16b",                                 |
    |                          |             "vnfVirtualLinkDescId": "10dfbb44-a8ff-435b-98f8-70539e71af8c",               |
    |                          |             "networkResource": {                                                          |
    |                          |                 "vimConnectionId": null,                                                  |
    |                          |                 "resourceId": "71a3fbd1-f31e-4c2c-b0e2-26267d64a9ee",                     |
    |                          |                 "vimLevelResourceType": "OS::Neutron::Net"                                |
    |                          |             },                                                                            |
    |                          |             "vnfLinkPorts": [                                                             |
    |                          |                 {                                                                         |
    |                          |                     "id": "977b8775-350d-4ef0-95e5-552c4c4099f3",                         |
    |                          |                     "resourceHandle": {                                                   |
    |                          |                         "vimConnectionId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",        |
    |                          |                         "resourceId": "0002bba0-608b-4e2c-bd4d-23f1717f017c",             |
    |                          |                         "vimLevelResourceType": "OS::Neutron::Port"                       |
    |                          |                     },                                                                    |
    |                          |                     "cpInstanceId": "59176610-fc1c-4abe-9648-87a9b8b79640"                |
    |                          |                 },                                                                        |
    |                          |                 {                                                                         |
    |                          |                     "id": "eba708c4-14de-4d96-bc82-ed0abd95780b",                         |
    |                          |                     "resourceHandle": {                                                   |
    |                          |                         "vimConnectionId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",        |
    |                          |                         "resourceId": "facc9eae-6f2d-4cfb-89c2-27841eea771c",             |
    |                          |                         "vimLevelResourceType": "OS::Neutron::Port"                       |
    |                          |                     },                                                                    |
    |                          |                     "cpInstanceId": "523b1328-9704-4ac1-986f-99c9b46ee1c4"                |
    |                          |                 }                                                                         |
    |                          |             ]                                                                             |
    |                          |         }                                                                                 |
    |                          |     ],                                                                                    |
    |                          |     "vnfcInfo": [                                                                         |
    |                          |         {                                                                                 |
    |                          |             "id": "1405984c-b174-4f33-8cfa-851d54ab95ce",                                 |
    |                          |             "vduId": "masterNode",                                                        |
    |                          |             "vnfcState": "STARTED"                                                        |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "08b3f00e-a133-4262-8edb-03e2484ce870",                                 |
    |                          |             "vduId": "workerNode",                                                        |
    |                          |             "vnfcState": "STARTED"                                                        |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "027502d6-d072-4819-a502-cb7cc688ec16",                                 |
    |                          |             "vduId": "workerNode",                                                        |
    |                          |             "vnfcState": "STARTED"                                                        |
    |                          |         }                                                                                 |
    |                          |     ],                                                                                    |
    |                          |     "additionalParams": {                                                                 |
    |                          |         "lcm-operation-user-data": "./UserData/k8s_cluster_user_data.py",                 |
    |                          |         "lcm-operation-user-data-class": "KubernetesClusterUserData",                     |
    |                          |         "k8sClusterInstallationParam": {                                                  |
    |                          |             "vimName": "kubernetes_vim",                                                 |
    |                          |             "proxy": {                                                                    |
    |                          |                 "noProxy": "192.168.246.0/24,10.0.0.1",                                   |
    |                          |                 "httpProxy": "http://user1:password1@host1:port1",                        |
    |                          |                 "httpsProxy": "https://user2:password2@host2:port2",                      |
    |                          |                 "k8sNodeCidr": "10.10.0.0/24"                                             |
    |                          |             },                                                                            |
    |                          |             "masterNode": {                                                               |
    |                          |                 "password": "ubuntu",                                                     |
    |                          |                 "podCidr": "192.168.3.0/16",                                              |
    |                          |                 "username": "ubuntu",                                                     |
    |                          |                 "aspectId": "master_instance",                                            |
    |                          |                 "nicCpName": "masterNode_CP1",                                            |
    |                          |                 "sshCpName": "masterNode_CP1",                                            |
    |                          |                 "clusterCidr": "10.199.187.0/24",                                         |
    |                          |                 "clusterCpName": "masterNode_CP1"                                         |
    |                          |             },                                                                            |
    |                          |             "scriptPath": "Scripts/install_k8s_cluster.sh",                               |
    |                          |             "workerNode": {                                                               |
    |                          |                 "password": "ubuntu",                                                     |
    |                          |                 "username": "ubuntu",                                                     |
    |                          |                 "aspectId": "worker_instance",                                            |
    |                          |                 "nicCpName": "workerNode_CP2",                                            |
    |                          |                 "sshCpName": "workerNode_CP2"                                             |
    |                          |             }                                                                             |
    |                          |         }                                                                                 |
    |                          |     }                                                                                     |
    |                          | }                                                                                         |
    | Instantiation State      | INSTANTIATED                                                                              |
    | Links                    | {                                                                                         |
    |                          |     "self": {                                                                             |
    |                          |         "href": "/vnflcm/v1/vnf_instances/3f32428d-e8ce-4d6a-9be9-4c7f3a02ac72"           |
    |                          |     },                                                                                    |
    |                          |     "terminate": {                                                                        |
    |                          |         "href": "/vnflcm/v1/vnf_instances/3f32428d-e8ce-4d6a-9be9-4c7f3a02ac72/terminate" |
    |                          |     },                                                                                    |
    |                          |     "heal": {                                                                             |
    |                          |         "href": "/vnflcm/v1/vnf_instances/3f32428d-e8ce-4d6a-9be9-4c7f3a02ac72/heal"      |
    |                          |     }                                                                                     |
    |                          | }                                                                                         |
    | VIM Connection Info      | [                                                                                         |
    |                          |     {                                                                                     |
    |                          |         "id": "9ab53adf-ca70-47b2-8877-1858cfb53618",                                     |
    |                          |         "vimId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",                                  |
    |                          |         "vimType": "openstack",                                                           |
    |                          |         "interfaceInfo": {},                                                              |
    |                          |         "accessInfo": {}                                                                  |
    |                          |     },                                                                                    |
    |                          |     {                                                                                     |
    |                          |         "id": "ef2c6b0c-c930-4d6c-9fe4-7c143e80ad94",                                     |
    |                          |         "vimId": "2aeef9af-6a5b-4122-8510-21dbc71bc7cb",                                  |
    |                          |         "vimType": "kubernetes",                                                          |
    |                          |         "interfaceInfo": null,                                                            |
    |                          |         "accessInfo": {                                                                   |
    |                          |             "authUrl": "https://10.10.0.35:6443"                                          |
    |                          |         }                                                                                 |
    |                          |     }                                                                                     |
    |                          | ]                                                                                         |
    | VNF Instance Description | None                                                                                      |
    | VNF Instance Name        | vnf-3f32428d-e8ce-4d6a-9be9-4c7f3a02ac72                                                  |
    | VNF Product Name         | Sample VNF                                                                                |
    | VNF Provider             | Company                                                                                   |
    | VNF Software Version     | 1.0                                                                                       |
    | VNFD ID                  | b1db0ce7-ebca-1fb7-95ed-4840d70a1163                                                      |
    | VNFD Version             | 1.0                                                                                       |
    | vnfPkgId                 |                                                                                           |
    +--------------------------+-------------------------------------------------------------------------------------------+

2. Multi-master Nodes
^^^^^^^^^^^^^^^^^^^^^

When you install the Kubernetes cluster in an HA configuration,
at least three Master nodes are configured in the Kubernetes cluster.
On each Master node, a load balancer (HAProxy) and etcd will be built.
Those described above are performed by "instantiate_end" operation with Mgmt Driver.

If you want to deploy a multi-master Kubernetes cluster, you can
use VNF Package with ``complex`` flavour created in
``Create and Upload VNF Package``.
The following are the methods of creating
the parameter file and cli commands of OpenStack.

1. Create the Parameter File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The parameters in parameter file are the same as those in
``1. Single master node``. It should be noted that
since you need to create a group (at least three) master nodes, you
must set the ``aspect_id``. At the same time, HA cluster needs a representative
IP to access, so the ``cluster_cp_name`` must be set to the port name of the
virtual ip created in BaseHot. In this guide,
``cluster_cp_name`` is ``vip_CP``. The ``complex_kubernetes_param_file.json``
is shown below.

complex_kubernetes_param_file.json

.. code-block::


    {
        "flavourId": "complex",
        "vimConnectionInfo": [{
            "id": "3cc2c4ff-525c-48b4-94c9-29247223322f",
            "vimId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496", #Set the uuid of the VIM to use
            "vimType": "openstack"
        }],
        "additionalParams": {
            "k8s_cluster_installation_param": {
                "script_path": "Scripts/install_k8s_cluster.sh",
                "vim_name": "kubernetes_vim_complex",
                "master_node": {
                    "aspect_id": "master_instance",
                    "ssh_cp_name": "masterNode_CP1",
                    "nic_cp_name": "masterNode_CP1",
                    "username": "ubuntu",
                    "password": "ubuntu",
                    "pod_cidr": "192.168.3.0/16",
                    "cluster_cidr": "10.199.187.0/24",
                    "cluster_cp_name": "vip_CP"
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
                }
            },
            "lcm-operation-user-data": "./UserData/k8s_cluster_user_data.py",
            "lcm-operation-user-data-class": "KubernetesClusterUserData"
        },
        "extVirtualLinks": [{
            "id": "net0_master",
            "resourceId": "71a3fbd1-f31e-4c2c-b0e2-26267d64a9ee",  #Set the uuid of the network to use
            "extCps": [{
                "cpdId": "masterNode_CP1",
                "cpConfig": [{
                    "cpProtocolData": [{
                        "layerProtocol": "IP_OVER_ETHERNET"
                    }]
                }]
            }]
        }, {
            "id": "net0_worker",
            "resourceId": "71a3fbd1-f31e-4c2c-b0e2-26267d64a9ee",  #Set the uuid of the network to use
            "extCps": [{
                "cpdId": "workerNode_CP2",
                "cpConfig": [{
                    "cpProtocolData": [{
                        "layerProtocol": "IP_OVER_ETHERNET"
                    }]
                }]
            }]
        }]
    }

2. Execute the Instantiation Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The VNF Package has been uploaded in
``Create and Upload VNF Package``.
So you just execute the following cli command on OpenStack Controller Node.

.. code-block:: console

    $ openstack vnflcm create b1db0ce7-ebca-1fb7-95ed-4840d70a1163
    +--------------------------+---------------------------------------------------------------------------------------------+
    | Field                    | Value                                                                                       |
    +--------------------------+---------------------------------------------------------------------------------------------+
    | ID                       | c5215213-af4b-4080-95ab-377920474e1a                                                        |
    | Instantiation State      | NOT_INSTANTIATED                                                                            |
    | Links                    | {                                                                                           |
    |                          |     "self": {                                                                               |
    |                          |         "href": "/vnflcm/v1/vnf_instances/c5215213-af4b-4080-95ab-377920474e1a"             |
    |                          |     },                                                                                      |
    |                          |     "instantiate": {                                                                        |
    |                          |         "href": "/vnflcm/v1/vnf_instances/c5215213-af4b-4080-95ab-377920474e1a/instantiate" |
    |                          |     }                                                                                       |
    |                          | }                                                                                           |
    | VNF Instance Description | None                                                                                        |
    | VNF Instance Name        | vnf-c5215213-af4b-4080-95ab-377920474e1a                                                    |
    | VNF Product Name         | Sample VNF                                                                                  |
    | VNF Provider             | Company                                                                                     |
    | VNF Software Version     | 1.0                                                                                         |
    | VNFD ID                  | b1db0ce7-ebca-1fb7-95ed-4840d70a1163                                                        |
    | VNFD Version             | 1.0                                                                                         |
    | vnfPkgId                 |                                                                                             |
    +--------------------------+---------------------------------------------------------------------------------------------+

    $ openstack vnflcm instantiate c5215213-af4b-4080-95ab-377920474e1a ./complex_kubernetes_param_file.json
    Instantiate request for VNF Instance c5215213-af4b-4080-95ab-377920474e1a has been accepted.
    $ openstack vnflcm show c5215213-af4b-4080-95ab-377920474e1a
    +--------------------------+-------------------------------------------------------------------------------------------+
    | Field                    | Value                                                                                     |
    +--------------------------+-------------------------------------------------------------------------------------------+
    | ID                       | c5215213-af4b-4080-95ab-377920474e1a                                                      |
    | Instantiated Vnf Info    | {                                                                                         |
    |                          |     "flavourId": "complex",                                                               |
    |                          |     "vnfState": "STARTED",                                                                |
    |                          |     "scaleStatus": [                                                                      |
    |                          |         {                                                                                 |
    |                          |             "aspectId": "master_instance",                                                |
    |                          |             "scaleLevel": 0                                                               |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "aspectId": "worker_instance",                                                |
    |                          |             "scaleLevel": 0                                                               |
    |                          |         }                                                                                 |
    |                          |     ],                                                                                    |
    |                          |     "extCpInfo": [                                                                        |
    |                          |         {                                                                                 |
    |                          |             "id": "a36f667a-f0f8-4ac8-a120-b19569d7bd72",                                 |
    |                          |             "cpdId": "masterNode_CP1",                                                    |
    |                          |             "extLinkPortId": null,                                                        |
    |                          |             "associatedVnfcCpId": "bbce9656-f051-434f-8c4a-660ac23e91f6",                 |
    |                          |             "cpProtocolInfo": [                                                           |
    |                          |                 {                                                                         |
    |                          |                     "layerProtocol": "IP_OVER_ETHERNET"                                   |
    |                          |                 }                                                                         |
    |                          |             ]                                                                             |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "67f38bd4-ae0b-4257-82eb-09a3c2dfd470",                                 |
    |                          |             "cpdId": "workerNode_CP2",                                                    |
    |                          |             "extLinkPortId": null,                                                        |
    |                          |             "associatedVnfcCpId": "b4af0652-74b8-47bd-bcf6-94769bdbf756",                 |
    |                          |             "cpProtocolInfo": [                                                           |
    |                          |                 {                                                                         |
    |                          |                     "layerProtocol": "IP_OVER_ETHERNET"                                   |
    |                          |                 }                                                                         |
    |                          |             ]                                                                             |
    |                          |         }                                                                                 |
    |                          |     ],                                                                                    |
    |                          |     "extVirtualLinkInfo": [                                                               |
    |                          |         {                                                                                 |
    |                          |             "id": "24e3e9ae-0df4-49d6-9ee4-e21dfe359baf",                                 |
    |                          |             "resourceHandle": {                                                           |
    |                          |                 "vimConnectionId": null,                                                  |
    |                          |                 "resourceId": "71a3fbd1-f31e-4c2c-b0e2-26267d64a9ee",                     |
    |                          |                 "vimLevelResourceType": null                                              |
    |                          |             }                                                                             |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "2283b96d-64f8-4403-9b21-643aa1058e86",                                 |
    |                          |             "resourceHandle": {                                                           |
    |                          |                 "vimConnectionId": null,                                                  |
    |                          |                 "resourceId": "71a3fbd1-f31e-4c2c-b0e2-26267d64a9ee",                     |
    |                          |                 "vimLevelResourceType": null                                              |
    |                          |             }                                                                             |
    |                          |         }                                                                                 |
    |                          |     ],                                                                                    |
    |                          |     "vnfcResourceInfo": [                                                                 |
    |                          |         {                                                                                 |
    |                          |             "id": "bbce9656-f051-434f-8c4a-660ac23e91f6",                                 |
    |                          |             "vduId": "masterNode",                                                        |
    |                          |             "computeResource": {                                                          |
    |                          |                 "vimConnectionId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",                |
    |                          |                 "resourceId": "a0eccaee-ff7b-4c70-8c11-ba79c8d4deb6",                     |
    |                          |                 "vimLevelResourceType": "OS::Nova::Server"                                |
    |                          |             },                                                                            |
    |                          |             "storageResourceIds": [],                                                     |
    |                          |             "vnfcCpInfo": [                                                               |
    |                          |                 {                                                                         |
    |                          |                     "id": "9fe655ab-1d35-4d22-a6f3-9a07fa797884",                         |
    |                          |                     "cpdId": "masterNode_CP1",                                            |
    |                          |                     "vnfExtCpId": null,                                                   |
    |                          |                     "vnfLinkPortId": "e66a44a4-965f-49dd-b168-ff4cc2485c34",              |
    |                          |                     "cpProtocolInfo": [                                                   |
    |                          |                         {                                                                 |
    |                          |                             "layerProtocol": "IP_OVER_ETHERNET"                           |
    |                          |                         }                                                                 |
    |                          |                     ]                                                                     |
    |                          |                 }                                                                         |
    |                          |             ]                                                                             |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "8bee8301-eb14-4c5c-bab8-a1b244d4d954",                                 |
    |                          |             "vduId": "masterNode",                                                        |
    |                          |             "computeResource": {                                                          |
    |                          |                 "vimConnectionId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",                |
    |                          |                 "resourceId": "4a40d65c-3440-4c44-858a-72a66324a11a",                     |
    |                          |                 "vimLevelResourceType": "OS::Nova::Server"                                |
    |                          |             },                                                                            |
    |                          |             "storageResourceIds": [],                                                     |
    |                          |             "vnfcCpInfo": [                                                               |
    |                          |                 {                                                                         |
    |                          |                     "id": "65c9f35a-08a2-4875-bd85-af419f26b19d",                         |
    |                          |                     "cpdId": "masterNode_CP1",                                            |
    |                          |                     "vnfExtCpId": null,                                                   |
    |                          |                     "vnfLinkPortId": "26fa4b33-ad07-4982-ad97-18b66abba541",              |
    |                          |                     "cpProtocolInfo": [                                                   |
    |                          |                         {                                                                 |
    |                          |                             "layerProtocol": "IP_OVER_ETHERNET"                           |
    |                          |                         }                                                                 |
    |                          |                     ]                                                                     |
    |                          |                 }                                                                         |
    |                          |             ]                                                                             |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "28ac0cb9-3bc1-4bc2-8be2-cf60f51b7b7a",                                 |
    |                          |             "vduId": "masterNode",                                                        |
    |                          |             "computeResource": {                                                          |
    |                          |                 "vimConnectionId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",                |
    |                          |                 "resourceId": "12708197-9724-41b8-b48c-9eb6862331dc",                     |
    |                          |                 "vimLevelResourceType": "OS::Nova::Server"                                |
    |                          |             },                                                                            |
    |                          |             "storageResourceIds": [],                                                     |
    |                          |             "vnfcCpInfo": [                                                               |
    |                          |                 {                                                                         |
    |                          |                     "id": "d51f3b54-a9ed-46be-8ffe-64b5d07d1a7b",                         |
    |                          |                     "cpdId": "masterNode_CP1",                                            |
    |                          |                     "vnfExtCpId": null,                                                   |
    |                          |                     "vnfLinkPortId": "b71dc885-8e3e-4ccd-ac6f-feff332fd395",              |
    |                          |                     "cpProtocolInfo": [                                                   |
    |                          |                         {                                                                 |
    |                          |                             "layerProtocol": "IP_OVER_ETHERNET"                           |
    |                          |                         }                                                                 |
    |                          |                     ]                                                                     |
    |                          |                 }                                                                         |
    |                          |             ]                                                                             |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "b4af0652-74b8-47bd-bcf6-94769bdbf756",                                 |
    |                          |             "vduId": "workerNode",                                                        |
    |                          |             "computeResource": {                                                          |
    |                          |                 "vimConnectionId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",                |
    |                          |                 "resourceId": "5b3ff765-7a9f-447a-a06d-444e963b74c9",                     |
    |                          |                 "vimLevelResourceType": "OS::Nova::Server"                                |
    |                          |             },                                                                            |
    |                          |             "storageResourceIds": [],                                                     |
    |                          |             "vnfcCpInfo": [                                                               |
    |                          |                 {                                                                         |
    |                          |                     "id": "59176610-fc1c-4abe-9648-87a9b8b79640",                         |
    |                          |                     "cpdId": "workerNode_CP2",                                            |
    |                          |                     "vnfExtCpId": null,                                                   |
    |                          |                     "vnfLinkPortId": "977b8775-350d-4ef0-95e5-552c4c4099f3",              |
    |                          |                     "cpProtocolInfo": [                                                   |
    |                          |                         {                                                                 |
    |                          |                             "layerProtocol": "IP_OVER_ETHERNET"                           |
    |                          |                         }                                                                 |
    |                          |                     ]                                                                     |
    |                          |                 }                                                                         |
    |                          |             ]                                                                             |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "974a4b98-5d07-44d4-9e13-a8ed21805111",                                 |
    |                          |             "vduId": "workerNode",                                                        |
    |                          |             "computeResource": {                                                          |
    |                          |                 "vimConnectionId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",                |
    |                          |                 "resourceId": "63402e5a-67c9-4f5c-b03f-b21f4a88507f",                     |
    |                          |                 "vimLevelResourceType": "OS::Nova::Server"                                |
    |                          |             },                                                                            |
    |                          |             "storageResourceIds": [],                                                     |
    |                          |             "vnfcCpInfo": [                                                               |
    |                          |                 {                                                                         |
    |                          |                     "id": "523b1328-9704-4ac1-986f-99c9b46ee1c4",                         |
    |                          |                     "cpdId": "workerNode_CP2",                                            |
    |                          |                     "vnfExtCpId": null,                                                   |
    |                          |                     "vnfLinkPortId": "eba708c4-14de-4d96-bc82-ed0abd95780b",              |
    |                          |                     "cpProtocolInfo": [                                                   |
    |                          |                         {                                                                 |
    |                          |                             "layerProtocol": "IP_OVER_ETHERNET"                           |
    |                          |                         }                                                                 |
    |                          |                     ]                                                                     |
    |                          |                 }                                                                         |
    |                          |             ]                                                                             |
    |                          |         }                                                                                 |
    |                          |     ],                                                                                    |
    |                          |     "vnfVirtualLinkResourceInfo": [                                                       |
    |                          |         {                                                                                 |
    |                          |             "id": "96d15ae5-a1d8-4867-aaee-a4372de8bc0e",                                 |
    |                          |             "vnfVirtualLinkDescId": "24e3e9ae-0df4-49d6-9ee4-e21dfe359baf",               |
    |                          |             "networkResource": {                                                          |
    |                          |                 "vimConnectionId": null,                                                  |
    |                          |                 "resourceId": "71a3fbd1-f31e-4c2c-b0e2-26267d64a9ee",                     |
    |                          |                 "vimLevelResourceType": "OS::Neutron::Net"                                |
    |                          |             },                                                                            |
    |                          |             "vnfLinkPorts": [                                                             |
    |                          |                 {                                                                         |
    |                          |                     "id": "e66a44a4-965f-49dd-b168-ff4cc2485c34",                         |
    |                          |                     "resourceHandle": {                                                   |
    |                          |                         "vimConnectionId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",        |
    |                          |                         "resourceId": "b5ed388b-de4e-4de8-a24a-f1b70c5cce94",             |
    |                          |                         "vimLevelResourceType": "OS::Neutron::Port"                       |
    |                          |                     },                                                                    |
    |                          |                     "cpInstanceId": "9fe655ab-1d35-4d22-a6f3-9a07fa797884"                |
    |                          |                 },                                                                        |
    |                          |                 {                                                                         |
    |                          |                     "id": "26fa4b33-ad07-4982-ad97-18b66abba541",                         |
    |                          |                     "resourceHandle": {                                                   |
    |                          |                         "vimConnectionId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",        |
    |                          |                         "resourceId": "dfab524f-dec9-4247-973c-a0e22475f950",             |
    |                          |                         "vimLevelResourceType": "OS::Neutron::Port"                       |
    |                          |                     },                                                                    |
    |                          |                     "cpInstanceId": "65c9f35a-08a2-4875-bd85-af419f26b19d"                |
    |                          |                 },                                                                        |
    |                          |                 {                                                                         |
    |                          |                     "id": "b71dc885-8e3e-4ccd-ac6f-feff332fd395",                         |
    |                          |                     "resourceHandle": {                                                   |
    |                          |                         "vimConnectionId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",        |
    |                          |                         "resourceId": "45733936-0a9e-4eaa-a71f-3a77cb034581",             |
    |                          |                         "vimLevelResourceType": "OS::Neutron::Port"                       |
    |                          |                     },                                                                    |
    |                          |                     "cpInstanceId": "d51f3b54-a9ed-46be-8ffe-64b5d07d1a7b"                |
    |                          |                 }                                                                         |
    |                          |             ]                                                                             |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "c67b6f41-fd7a-45b2-b69a-8de9623dc16b",                                 |
    |                          |             "vnfVirtualLinkDescId": "2283b96d-64f8-4403-9b21-643aa1058e86",               |
    |                          |             "networkResource": {                                                          |
    |                          |                 "vimConnectionId": null,                                                  |
    |                          |                 "resourceId": "71a3fbd1-f31e-4c2c-b0e2-26267d64a9ee",                     |
    |                          |                 "vimLevelResourceType": "OS::Neutron::Net"                                |
    |                          |             },                                                                            |
    |                          |             "vnfLinkPorts": [                                                             |
    |                          |                 {                                                                         |
    |                          |                     "id": "977b8775-350d-4ef0-95e5-552c4c4099f3",                         |
    |                          |                     "resourceHandle": {                                                   |
    |                          |                         "vimConnectionId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",        |
    |                          |                         "resourceId": "0002bba0-608b-4e2c-bd4d-23f1717f017c",             |
    |                          |                         "vimLevelResourceType": "OS::Neutron::Port"                       |
    |                          |                     },                                                                    |
    |                          |                     "cpInstanceId": "59176610-fc1c-4abe-9648-87a9b8b79640"                |
    |                          |                 },                                                                        |
    |                          |                 {                                                                         |
    |                          |                     "id": "eba708c4-14de-4d96-bc82-ed0abd95780b",                         |
    |                          |                     "resourceHandle": {                                                   |
    |                          |                         "vimConnectionId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",        |
    |                          |                         "resourceId": "facc9eae-6f2d-4cfb-89c2-27841eea771c",             |
    |                          |                         "vimLevelResourceType": "OS::Neutron::Port"                       |
    |                          |                     },                                                                    |
    |                          |                     "cpInstanceId": "523b1328-9704-4ac1-986f-99c9b46ee1c4"                |
    |                          |                 }                                                                         |
    |                          |             ]                                                                             |
    |                          |         }                                                                                 |
    |                          |     ],                                                                                    |
    |                          |     "vnfcInfo": [                                                                         |
    |                          |         {                                                                                 |
    |                          |             "id": "3ca607b9-f270-4077-8af8-d5d244f8893b",                                 |
    |                          |             "vduId": "masterNode",                                                        |
    |                          |             "vnfcState": "STARTED"                                                        |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "c2b19ef1-f748-4175-9f3a-6792a9ee7a62",                                 |
    |                          |             "vduId": "masterNode",                                                        |
    |                          |             "vnfcState": "STARTED"                                                        |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "59f5fd29-d20f-426f-a1a6-526757205cb4",                                 |
    |                          |             "vduId": "masterNode",                                                        |
    |                          |             "vnfcState": "STARTED"                                                        |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "08b3f00e-a133-4262-8edb-03e2484ce870",                                 |
    |                          |             "vduId": "workerNode",                                                        |
    |                          |             "vnfcState": "STARTED"                                                        |
    |                          |         },                                                                                |
    |                          |         {                                                                                 |
    |                          |             "id": "027502d6-d072-4819-a502-cb7cc688ec16",                                 |
    |                          |             "vduId": "workerNode",                                                        |
    |                          |             "vnfcState": "STARTED"                                                        |
    |                          |         }                                                                                 |
    |                          |     ],                                                                                    |
    |                          |     "additionalParams": {                                                                 |
    |                          |         "lcm-operation-user-data": "./UserData/k8s_cluster_user_data.py",                 |
    |                          |         "lcm-operation-user-data-class": "KubernetesClusterUserData",                     |
    |                          |         "k8sClusterInstallationParam": {                                                  |
    |                          |             "vimName": "kubernetes_vim_complex",                                          |
    |                          |             "proxy": {                                                                    |
    |                          |                 "noProxy": "192.168.246.0/24,10.0.0.1",                                   |
    |                          |                 "httpProxy": "http://user1:password1@host1:port1",                        |
    |                          |                 "httpsProxy": "https://user2:password2@host2:port2",                      |
    |                          |                 "k8sNodeCidr": "10.10.0.0/24"                                             |
    |                          |             },                                                                            |
    |                          |             "masterNode": {                                                               |
    |                          |                 "password": "ubuntu",                                                     |
    |                          |                 "podCidr": "192.168.3.0/16",                                              |
    |                          |                 "username": "ubuntu",                                                     |
    |                          |                 "aspectId": "master_instance",                                            |
    |                          |                 "nicCpName": "masterNode_CP1",                                            |
    |                          |                 "sshCpName": "masterNode_CP1",                                            |
    |                          |                 "clusterCidr": "10.199.187.0/24",                                         |
    |                          |                 "clusterCpName": "vip_CP"                                                 |
    |                          |             },                                                                            |
    |                          |             "scriptPath": "Scripts/install_k8s_cluster.sh",                               |
    |                          |             "workerNode": {                                                               |
    |                          |                 "password": "ubuntu",                                                     |
    |                          |                 "username": "ubuntu",                                                     |
    |                          |                 "aspectId": "worker_instance",                                            |
    |                          |                 "nicCpName": "workerNode_CP2",                                            |
    |                          |                 "sshCpName": "workerNode_CP2"                                             |
    |                          |             }                                                                             |
    |                          |         }                                                                                 |
    |                          |     }                                                                                     |
    |                          | }                                                                                         |
    | Instantiation State      | INSTANTIATED                                                                              |
    | Links                    | {                                                                                         |
    |                          |     "self": {                                                                             |
    |                          |         "href": "/vnflcm/v1/vnf_instances/c5215213-af4b-4080-95ab-377920474e1a"           |
    |                          |     },                                                                                    |
    |                          |     "terminate": {                                                                        |
    |                          |         "href": "/vnflcm/v1/vnf_instances/c5215213-af4b-4080-95ab-377920474e1a/terminate" |
    |                          |     },                                                                                    |
    |                          |     "heal": {                                                                             |
    |                          |         "href": "/vnflcm/v1/vnf_instances/c5215213-af4b-4080-95ab-377920474e1a/heal"      |
    |                          |     }                                                                                     |
    |                          | }                                                                                         |
    | VIM Connection Info      | [                                                                                         |
    |                          |     {                                                                                     |
    |                          |         "id": "9ab53adf-ca70-47b2-8877-1858cfb53618",                                     |
    |                          |         "vimId": "05ef7ca5-7e32-4a6b-a03d-52f811f04496",                                  |
    |                          |         "vimType": "openstack",                                                           |
    |                          |         "interfaceInfo": {},                                                              |
    |                          |         "accessInfo": {}                                                                  |
    |                          |     },                                                                                    |
    |                          |     {                                                                                     |
    |                          |         "id": "2e56da35-f343-4f9e-8f04-7722f8edbe7a",                                     |
    |                          |         "vimId": "3e04bb8e-2dbd-4c32-9575-d2937f3aa931",                                  |
    |                          |         "vimType": "kubernetes",                                                          |
    |                          |         "interfaceInfo": null,                                                            |
    |                          |         "accessInfo": {                                                                   |
    |                          |             "authUrl": "https://10.10.0.80:16443"                                         |
    |                          |         }                                                                                 |
    |                          |     }                                                                                     |
    |                          | ]                                                                                         |
    | VNF Instance Description | None                                                                                      |
    | VNF Instance Name        | vnf-c5215213-af4b-4080-95ab-377920474e1a                                                  |
    | VNF Product Name         | Sample VNF                                                                                |
    | VNF Provider             | Company                                                                                   |
    | VNF Software Version     | 1.0                                                                                       |
    | VNFD ID                  | b1db0ce7-ebca-1fb7-95ed-4840d70a1163                                                      |
    | VNFD Version             | 1.0                                                                                       |
    | vnfPkgId                 |                                                                                           |
    +--------------------------+-------------------------------------------------------------------------------------------+

Scale Kubernetes Worker Nodes
-----------------------------

According to `NFV-SOL001 v2.6.1`_, `scale_start` and `scale_end`
operation allows users to execute any scripts in the scale
operation, and scaling operations on the worker nodes in
Kubernetes cluster is supported with Mgmt Driver.

After instantiating a Kubernetes cluster,
if you want to delete one or more worker node in Kubernetes cluster,
you can execute `scale in` operation. If you want to add new worker
nodes in Kubernetes cluster, you can execute `scale out` operation.
The following are the methods of creating
the parameter file and cli commands of OpenStack.

1. Create the Parameter File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The following is scale parameter to "POST /vnf_instances/{id}/scale" as
``ScaleVnfRequest`` data type in ETSI `NFV-SOL003 v2.6.1`_:

.. code-block::

    +------------------+---------------------------------------------------------+
    | Attribute name   | Parameter description                                   |
    +------------------+---------------------------------------------------------+
    | type             | User specify scaling operation type:                    |
    |                  | "SCALE_IN" or "SCALE_OUT"                               |
    +------------------+---------------------------------------------------------+
    | aspectId         | User specify target aspectId, aspectId is defined in    |
    |                  | above VNFD and user can know by                         |
    |                  | ``InstantiatedVnfInfo.ScaleStatus`` that contained in   |
    |                  | the response of "GET /vnf_instances/{id}"               |
    +------------------+---------------------------------------------------------+
    | numberOfSteps    | Number of scaling steps                                 |
    +------------------+---------------------------------------------------------+
    | additionalParams | Not needed                                              |
    +------------------+---------------------------------------------------------+

Following are two samples of scaling request body:

.. code-block:: console

    {
        "type": "SCALE_OUT",
        "aspectId": "worker_instance",
        "numberOfSteps": "1"
    }

.. code-block:: console

    {
        "type": "SCALE_IN",
        "aspectId": "worker_instance",
        "numberOfSteps": "1"
    }

.. note::
    Only the worker node can be scaled out(in). The current function does
    not support scale master node.

2. Execute the Scale Operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before you execute `scale` command, you must ensure that your VNF instance
is already instantiated.
The VNF Package should be uploaded in ``Create and Upload VNF Package``
and the Kubernetes cluster should be deployed with the process in
``Deploy Kubernetes Cluster``.

When executing the scale operation of worker nodes, the following Heat API
is called from Tacker.

* stack update

The steps to confirm whether scaling is successful are shown below:

1. Execute Heat CLI command and check the number of resource list in
'worker_instance' of the stack
before and after scaling.

2. Login to master node of Kubernetes cluster and check the number of
worker nodes before and after scaling.

To confirm the number of worker nodes after scaling, you can find the
increased or decreased number of stack resource with Heat CLI. Also
the number of registered worker nodes in the Kubernetes cluster
should be updated.
See `Heat CLI reference`_ for details on Heat CLI commands.

Stack information before scaling:

.. code-block:: console

    $ openstack stack resource list vnf-c5215213-af4b-4080-95ab-377920474e1a -n 2 --filter type=base_hot_nested_worker.yaml -c resource_name -c physical_resource_id -c resource_type -c resource_status
    +---------------+--------------------------------------+-----------------------------+-----------------+
    | resource_name | physical_resource_id                 | resource_type               | resource_status |
    +---------------+--------------------------------------+-----------------------------+-----------------+
    | lwljovool2wg  | 07b79bbe-d0b2-4df0-8775-6202142b6054 | base_hot_nested_worker.yaml | CREATE_COMPLETE |
    | n6nnjta4f4rv  | 56c9ec6f-5e52-44db-9d0d-57e3484e763f | base_hot_nested_worker.yaml | CREATE_COMPLETE |
    +---------------+--------------------------------------+-----------------------------+-----------------+

worker node in Kubernetes cluster before scaling:

.. code-block:: console

    $ ssh ubuntu@10.10.0.80
    $ kubectl get node
    NAME       STATUS   ROLES                  AGE     VERSION
    master59   Ready    control-plane,master   1h25m   v1.20.4
    master78   Ready    control-plane,master   1h1m    v1.20.4
    master31   Ready    control-plane,master   35m     v1.20.4
    worker18   Ready    <none>                 10m     v1.20.4
    worker20   Ready    <none>                 4m      v1.20.4

Scaling out execution of the vnf_instance:

.. code-block:: console

  $ openstack vnflcm scale --type "SCALE_OUT" --aspect-id worker_instance --number-of-steps 1 c5215213-af4b-4080-95ab-377920474e1a
    Scale request for VNF Instance c5215213-af4b-4080-95ab-377920474e1a has been accepted.

Stack information after scaling out:

.. code-block:: console

    $ openstack stack resource list vnf-c5215213-af4b-4080-95ab-377920474e1a -n 2 --filter type=base_hot_nested_worker.yaml -c resource_name -c physical_resource_id -c resource_type -c resource_status
    +---------------+--------------------------------------+-----------------------------+-----------------+
    | resource_name | physical_resource_id                 | resource_type               | resource_status |
    +---------------+--------------------------------------+-----------------------------+-----------------+
    | lwljovool2wg  | 07b79bbe-d0b2-4df0-8775-6202142b6054 | base_hot_nested_worker.yaml | UPDATE_COMPLETE |
    | n6nnjta4f4rv  | 56c9ec6f-5e52-44db-9d0d-57e3484e763f | base_hot_nested_worker.yaml | UPDATE_COMPLETE |
    | z5nky6qcodlq  | f9ab73ff-3ad7-40d2-830a-87bd0c45af32 | base_hot_nested_worker.yaml | CREATE_COMPLETE |
    +---------------+--------------------------------------+-----------------------------+-----------------+

worker node in Kubernetes cluster after scaling out:

.. code-block:: console

    $ ssh ubuntu@10.10.0.80
    $ kubectl get node
    NAME       STATUS   ROLES                  AGE     VERSION
    master59   Ready    control-plane,master   1h35m   v1.20.4
    master78   Ready    control-plane,master   1h11m   v1.20.4
    master31   Ready    control-plane,master   45m     v1.20.4
    worker18   Ready    <none>                 20m     v1.20.4
    worker20   Ready    <none>                 14m     v1.20.4
    worker45   Ready    <none>                 4m      v1.20.4

Scaling in execution of the vnf_instance:

.. code-block:: console

    $ openstack vnflcm scale --type "SCALE_IN" --aspect-id worker_instance --number-of-steps 1 c5215213-af4b-4080-95ab-377920474e1a
    Scale request for VNF Instance c5215213-af4b-4080-95ab-377920474e1a has been accepted.

.. note::
    This example shows the output of "SCALE_IN" after its "SCALE_OUT" operation.

Stack information after scaling in:

.. code-block:: console

    $ openstack stack resource list vnf-c5215213-af4b-4080-95ab-377920474e1a -n 2 --filter type=base_hot_nested_worker.yaml -c resource_name -c physical_resource_id -c resource_type -c resource_status
    +---------------+--------------------------------------+-----------------------------+-----------------+
    | resource_name | physical_resource_id                 | resource_type               | resource_status |
    +---------------+--------------------------------------+-----------------------------+-----------------+
    | n6nnjta4f4rv  | 56c9ec6f-5e52-44db-9d0d-57e3484e763f | base_hot_nested_worker.yaml | UPDATE_COMPLETE |
    | z5nky6qcodlq  | f9ab73ff-3ad7-40d2-830a-87bd0c45af32 | base_hot_nested_worker.yaml | UPDATE_COMPLETE |
    +---------------+--------------------------------------+-----------------------------+-----------------+

worker node in Kubernetes cluster after scaling in:

.. code-block:: console

    $ ssh ubuntu@10.10.0.80
    $ kubectl get node
    NAME       STATUS   ROLES                  AGE     VERSION
    master59   Ready    control-plane,master   1h38m   v1.20.4
    master78   Ready    control-plane,master   1h14m   v1.20.4
    master31   Ready    control-plane,master   48m     v1.20.4
    worker20   Ready    <none>                 17m     v1.20.4
    worker45   Ready    <none>                 7m      v1.20.4

Heal Kubernetes Master/Worker Nodes
-----------------------------------

According to `NFV-SOL001 v2.6.1`_, `heal_start` and `heal_end`
operation allows users to execute any scripts in the heal
operation, and healing operations on the master nodes and
worker nodes in Kubernetes cluster is supported
with Mgmt Driver.

After instantiating a Kubernetes cluster,
if one of your node in Kubernetes cluster is not running properly,
you can heal it. The healing of entire Kubernetes cluster is also
supported. The following are the methods of creating
the parameter file and cli commands of OpenStack.

1. Create the Parameter File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following is heal parameter to "POST /vnf_instances/{id}/heal" as
``HealVnfRequest`` data type. It is not the same in SOL002 and SOL003.

In `NFV-SOL002 v2.6.1`_:

.. code-block::

    +------------------+---------------------------------------------------------+
    | Attribute name   | Parameter description                                   |
    +------------------+---------------------------------------------------------+
    | vnfcInstanceId   | User specify heal target, user can know "vnfcInstanceId"|
    |                  | by ``InstantiatedVnfInfo.vnfcResourceInfo`` that        |
    |                  | contained in the response of "GET /vnf_instances/{id}". |
    +------------------+---------------------------------------------------------+
    | cause            | Not needed                                              |
    +------------------+---------------------------------------------------------+
    | additionalParams | Not needed                                              |
    +------------------+---------------------------------------------------------+
    | healScript       | Not needed                                              |
    +------------------+---------------------------------------------------------+

In `NFV-SOL003 v2.6.1`_:

.. code-block::

    +------------------+---------------------------------------------------------+
    | Attribute name   | Parameter description                                   |
    +------------------+---------------------------------------------------------+
    | cause            | Not needed                                              |
    +------------------+---------------------------------------------------------+
    | additionalParams | Not needed                                              |
    +------------------+---------------------------------------------------------+


``cause``, and ``additionalParams``
are supported for both of SOL002 and SOL003.

If the vnfcInstanceId parameter is null, this means that healing operation is
required for the entire Kubernetes cluster, which is the case in SOL003.

Following is a sample of healing request body for SOL002:


.. code-block::

    {
        "vnfcInstanceId": "bbce9656-f051-434f-8c4a-660ac23e91f6"
    }

.. note::
    In chapter of ``Deploy Kubernetes cluster``, the result of VNF instance
    instantiated has shown in CLI command `openstack vnflcm show VNF INSTANCE ID`.

    You can get the vnfcInstanceId from ``Instantiated Vnf Info`` in above result.
    The ``vnfcResourceInfo.id`` is vnfcInstanceId.

    The ``physical_resource_id`` mentioned below is
    the same as ``vnfcResourceInfo.computeResource.resourceId``.

2. Execute the Heal Operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Heal a Master Node
~~~~~~~~~~~~~~~~~~~~~

When healing specified with VNFC instances,
Heat APIs are called from Tacker.

* stack resource mark unhealthy
* stack update

The steps to confirm whether healing is successful are shown below:

1. Execute Heat CLI command and check physical_resource_id and
resource_status of master node before and after healing.

2. Login to master node of Kubernetes cluster and check the age
of master node before and after healing.

To confirm that healing the master node is successful, you can find
the physical_resource_id of this resource of
'master_instance resource list' has changed with Heat CLI. Also
the age of master node healed should be updated in Kubernetes cluster.

.. note::
    Note that 'vnfc-instance-id' managed by Tacker and
    'physical-resource-id' managed by Heat are different.

master node information before healing:

.. code-block:: console

    $ openstack stack resource list vnf-c5215213-af4b-4080-95ab-377920474e1a -n 2 --filter type=OS::Nova::Server -c resource_name -c physical_resource_id -c resource_type -c resource_status
    +---------------+--------------------------------------+------------------+-----------------+
    | resource_name | physical_resource_id                 | resource_type    | resource_status |
    +---------------+--------------------------------------+------------------+-----------------+
    | workerNode    | 5b3ff765-7a9f-447a-a06d-444e963b74c9 | OS::Nova::Server | CREATE_COMPLETE |
    | workerNode    | 63402e5a-67c9-4f5c-b03f-b21f4a88507f | OS::Nova::Server | CREATE_COMPLETE |
    | masterNode    | a0eccaee-ff7b-4c70-8c11-ba79c8d4deb6 | OS::Nova::Server | CREATE_COMPLETE |
    | masterNode    | 4a40d65c-3440-4c44-858a-72a66324a11a | OS::Nova::Server | CREATE_COMPLETE |
    | masterNode    | 12708197-9724-41b8-b48c-9eb6862331dc | OS::Nova::Server | CREATE_COMPLETE |
    +---------------+--------------------------------------+------------------+-----------------+

master node in Kubernetes cluster before healing:

.. code-block:: console

    $ ssh ubuntu@10.10.0.80
    $ kubectl get node
    NAME       STATUS   ROLES                  AGE     VERSION
    master59   Ready    control-plane,master   1h38m   v1.20.4
    master78   Ready    control-plane,master   1h14m   v1.20.4
    master31   Ready    control-plane,master   48m     v1.20.4
    worker20   Ready    <none>                 17m     v1.20.4
    worker45   Ready    <none>                 7m      v1.20.4

We heal the master node with ``physical_resource_id``
``a0eccaee-ff7b-4c70-8c11-ba79c8d4deb6``, its ``vnfc_instance_id``
is ``bbce9656-f051-434f-8c4a-660ac23e91f6``.

Healing master node execution of the vnf_instance:

.. code-block:: console

    $ openstack vnflcm heal c5215213-af4b-4080-95ab-377920474e1a --vnfc-instance bbce9656-f051-434f-8c4a-660ac23e91f6
    Heal request for VNF Instance 9e086f34-b3c9-4986-b5e5-609a5ac4c1f9 has been accepted.

master node information after healing:

.. code-block:: console

    $ openstack stack resource list vnf-c5215213-af4b-4080-95ab-377920474e1a -n 2 --filter type=OS::Nova::Server -c resource_name -c physical_resource_id -c resource_type -c resource_status
    +---------------+--------------------------------------+------------------+-----------------+
    | resource_name | physical_resource_id                 | resource_type    | resource_status |
    +---------------+--------------------------------------+------------------+-----------------+
    | workerNode    | 5b3ff765-7a9f-447a-a06d-444e963b74c9 | OS::Nova::Server | CREATE_COMPLETE |
    | workerNode    | 63402e5a-67c9-4f5c-b03f-b21f4a88507f | OS::Nova::Server | CREATE_COMPLETE |
    | masterNode    | aaecc9b4-8ce5-4f1c-a90b-3571fd4bfb5f | OS::Nova::Server | CREATE_COMPLETE |
    | masterNode    | 4a40d65c-3440-4c44-858a-72a66324a11a | OS::Nova::Server | CREATE_COMPLETE |
    | masterNode    | 12708197-9724-41b8-b48c-9eb6862331dc | OS::Nova::Server | CREATE_COMPLETE |
    +---------------+--------------------------------------+------------------+-----------------+

master node in Kubernetes cluster after healing:

.. code-block:: console

    $ ssh ubuntu@10.10.0.80
    $ kubectl get node
    NAME       STATUS   ROLES                  AGE     VERSION
    master78   Ready    control-plane,master   1h36m   v1.20.4
    master31   Ready    control-plane,master   1h10m   v1.20.4
    worker20   Ready    <none>                 39m     v1.20.4
    worker45   Ready    <none>                 29m     v1.20.4
    master59   Ready    control-plane,master   2m      v1.20.4

2. Heal a Worker Node
~~~~~~~~~~~~~~~~~~~~~

Healing a worker node is the same as Healing a master node.
You just replace the vnfc_instance_id in healing command.

worker node information before healing:

.. code-block:: console

    $ openstack stack resource list vnf-c5215213-af4b-4080-95ab-377920474e1a -n 2 --filter type=OS::Nova::Server -c resource_name -c physical_resource_id -c resource_type -c resource_status
    +---------------+--------------------------------------+------------------+-----------------+
    | resource_name | physical_resource_id                 | resource_type    | resource_status |
    +---------------+--------------------------------------+------------------+-----------------+
    | workerNode    | 5b3ff765-7a9f-447a-a06d-444e963b74c9 | OS::Nova::Server | CREATE_COMPLETE |
    | workerNode    | 63402e5a-67c9-4f5c-b03f-b21f4a88507f | OS::Nova::Server | CREATE_COMPLETE |
    | masterNode    | aaecc9b4-8ce5-4f1c-a90b-3571fd4bfb5f | OS::Nova::Server | CREATE_COMPLETE |
    | masterNode    | 4a40d65c-3440-4c44-858a-72a66324a11a | OS::Nova::Server | CREATE_COMPLETE |
    | masterNode    | 12708197-9724-41b8-b48c-9eb6862331dc | OS::Nova::Server | CREATE_COMPLETE |
    +---------------+--------------------------------------+------------------+-----------------+

worker node in Kubernetes cluster before healing:

.. code-block:: console

    $ ssh ubuntu@10.10.0.80
    $ kubectl get node
    NAME       STATUS   ROLES                  AGE     VERSION
    master78   Ready    control-plane,master   1h36m   v1.20.4
    master31   Ready    control-plane,master   1h10m   v1.20.4
    worker20   Ready    <none>                 39m     v1.20.4
    worker45   Ready    <none>                 29m     v1.20.4
    master59   Ready    control-plane,master   2m      v1.20.4

We heal the worker node with ``physical_resource_id``
``5b3ff765-7a9f-447a-a06d-444e963b74c9``, its ``vnfc_instance_id``
is ``b4af0652-74b8-47bd-bcf6-94769bdbf756``.

Healing worker node execution of the vnf_instance:

.. code-block:: console

  $ openstack vnflcm heal c5215213-af4b-4080-95ab-377920474e1a --vnfc-instance b4af0652-74b8-47bd-bcf6-94769bdbf756
  Heal request for VNF Instance 9e086f34-b3c9-4986-b5e5-609a5ac4c1f9 has been accepted.

worker node information after healing:

.. code-block:: console

    $ openstack stack resource list vnf-c5215213-af4b-4080-95ab-377920474e1a -n 2 --filter type=OS::Nova::Server -c resource_name -c physical_resource_id -c resource_type -c resource_status
    +---------------+--------------------------------------+------------------+-----------------+
    | resource_name | physical_resource_id                 | resource_type    | resource_status |
    +---------------+--------------------------------------+------------------+-----------------+
    | workerNode    | 5b3ff765-7a9f-447a-a06d-444e963b74c9 | OS::Nova::Server | CREATE_COMPLETE |
    | workerNode    | c94f8952-bf2e-4a08-906e-67cee771112b | OS::Nova::Server | CREATE_COMPLETE |
    | masterNode    | aaecc9b4-8ce5-4f1c-a90b-3571fd4bfb5f | OS::Nova::Server | CREATE_COMPLETE |
    | masterNode    | 4a40d65c-3440-4c44-858a-72a66324a11a | OS::Nova::Server | CREATE_COMPLETE |
    | masterNode    | 12708197-9724-41b8-b48c-9eb6862331dc | OS::Nova::Server | CREATE_COMPLETE |
    +---------------+--------------------------------------+------------------+-----------------+

worker node in Kubernetes cluster after healing:

.. code-block:: console

    $ ssh ubuntu@10.10.0.80
    $ kubectl get node
    NAME       STATUS   ROLES                  AGE     VERSION
    master78   Ready    control-plane,master   1h46m   v1.20.4
    master31   Ready    control-plane,master   1h20m   v1.20.4
    worker45   Ready    <none>                 39m     v1.20.4
    master59   Ready    control-plane,master   10m     v1.20.4
    worker20   Ready    <none>                 2m      v1.20.4

3. Heal the Entire Kubernetes Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When healing of the entire VNF, the following APIs are executed
from Tacker to Heat.

* stack delete
* stack create

1. Execute Heat CLI command and check 'ID' and 'Stack Status' of the stack
before and after healing.

2. All the information of Kubernetes cluster will be
changed.

This is to confirm that stack 'ID' has changed
before and after healing.

Stack information before healing:

.. code-block:: console

    $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'
    +--------------------------------------+------------------------------------------+-----------------+
    | ID                                   | Stack Name                               | Stack Status    |
    +--------------------------------------+------------------------------------------+-----------------+
    | f485f3f2-8181-4ed5-b927-e582b5aa9b14 | vnf-c5215213-af4b-4080-95ab-377920474e1a | CREATE_COMPLETE |
    +--------------------------------------+------------------------------------------+-----------------+

Kubernetes cluster information before healing:

.. code-block:: console

    $ ssh ubuntu@10.10.0.80
    $ kubectl get node
    NAME       STATUS   ROLES                  AGE     VERSION
    master59   Ready    control-plane,master   1h38m   v1.20.4
    master78   Ready    control-plane,master   1h14m   v1.20.4
    master31   Ready    control-plane,master   48m     v1.20.4
    worker20   Ready    <none>                 17m     v1.20.4
    worker45   Ready    <none>                 7m      v1.20.4

Healing execution of the entire VNF:

.. code-block:: console

    $ openstack vnflcm heal c5215213-af4b-4080-95ab-377920474e1a
    Heal request for VNF Instance c5215213-af4b-4080-95ab-377920474e1a has been accepted.

Stack information after healing:

.. code-block:: console

    $ openstack stack list -c 'ID' -c 'Stack Name' -c 'Stack Status'
    +--------------------------------------+------------------------------------------+-----------------+
    | ID                                   | Stack Name                               | Stack Status    |
    +--------------------------------------+------------------------------------------+-----------------+
    | 03aaadbe-bf5a-44a0-84b0-8f2a18f8a844 | vnf-c5215213-af4b-4080-95ab-377920474e1a | CREATE_COMPLETE |
    +--------------------------------------+------------------------------------------+-----------------+

Kubernetes cluster information after healing:

.. code-block:: console

    $ ssh ubuntu@10.10.0.93
    $ kubectl get node
    NAME       STATUS   ROLES                  AGE     VERSION
    master46   Ready    control-plane,master   1h25m   v1.20.4
    master37   Ready    control-plane,master   1h1m    v1.20.4
    master14   Ready    control-plane,master   35m     v1.20.4
    worker101  Ready    <none>                 10m     v1.20.4
    worker214  Ready    <none>                 4m      v1.20.4

Limitations
-----------
1. If you deploy a single master node Kubernetes cluster,
   you cannot heal the master node.
2. This user guide provides a VNF Package in format of UserData.
   You can also use TOSCA based VNF Package in the manner of SOL001
   v2.6.1, but it only supports single master case and the scaling
   operation is not supported.

Reference
---------

.. [#f1] https://forge.etsi.org/rep/nfv/SOL001
.. _TOSCA-Simple-Profile-YAML-v1.2 : http://docs.oasis-open.org/tosca/TOSCA-Simple-Profile-YAML/v1.2/TOSCA-Simple-Profile-YAML-v1.2.html
.. _VNF Package: https://docs.openstack.org/tacker/latest/user/vnf-package.html
.. _TOSCA-1.0-specification : http://docs.oasis-open.org/tosca/TOSCA/v1.0/os/TOSCA-v1.0-os.pdf
.. _NFV-SOL001 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/001/02.06.01_60/gs_NFV-SOL001v020601p.pdf
.. _NFV-SOL002 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/002/02.06.01_60/gs_NFV-SOL002v020601p.pdf
.. _NFV-SOL003 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/003/02.06.01_60/gs_NFV-SOL003v020601p.pdf
.. _NFV-SOL004 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/004/02.06.01_60/gs_NFV-SOL004v020601p.pdf
.. _etsi_nfv_sol001_common_types.yaml : https://forge.etsi.org/rep/nfv/SOL001/raw/v2.6.1/etsi_nfv_sol001_common_types.yaml
.. _etsi_nfv_sol001_vnfd_types.yaml : https://forge.etsi.org/rep/nfv/SOL001/raw/v2.6.1/etsi_nfv_sol001_vnfd_types.yaml
.. _cli-legacy-vim : https://docs.openstack.org/tacker/latest/cli/cli-legacy-vim.html#register-vim
.. _HAProxy: https://www.haproxy.org/
.. _Heat CLI reference : https://docs.openstack.org/python-openstackclient/latest/cli/plugin-commands/heat.html
.. _TOSCA.meta: https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes_vnf_package/TOSCA-Metadata/TOSCA.meta
.. _sample_kubernetes_top.vnfd.yaml: https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes_vnf_package/Definitions/sample_kubernetes_top.vnfd.yaml
.. _sample_kubernetes_types.yaml: https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes_vnf_package/Definitions/sample_kubernetes_types.yaml
.. _sample_kubernetes_df_simple.yaml: https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes_vnf_package/Definitions/sample_kubernetes_df_simple.yaml
.. _sample_kubernetes_df_complex.yaml: https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes_vnf_package/Definitions/sample_kubernetes_df_complex.yaml
.. _install_k8s_cluster.sh: https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/install_k8s_cluster.sh
.. _kubernetes_mgmt.py: https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes_mgmt.py
.. _nested/simple_nested_master.yaml: https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes_vnf_package/BaseHOT/simple/nested/simple_nested_master.yaml
.. _nested/simple_nested_worker.yaml: https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes_vnf_package/BaseHOT/simple/nested/simple_nested_worker.yaml
.. _simple_hot_top.yaml: https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes_vnf_package/BaseHOT/simple/simple_hot_top.yaml
.. _nested/complex_nested_master.yaml: https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes_vnf_package/BaseHOT/complex/nested/complex_nested_master.yaml
.. _nested/complex_nested_worker.yaml: https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes_vnf_package/BaseHOT/complex/nested/complex_nested_worker.yaml
.. _complex_hot_top.yaml: https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes_vnf_package/BaseHOT/complex/complex_hot_top.yaml
.. _k8s_cluster_user_data.py: https://opendev.org/openstack/tacker/src/branch/master/samples/mgmt_driver/kubernetes_vnf_package/UserData/k8s_cluster_user_data.py
