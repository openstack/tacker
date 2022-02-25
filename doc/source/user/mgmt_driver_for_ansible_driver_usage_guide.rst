=========================================
How to use Mgmt Driver for Ansible Driver
=========================================

Overview
--------


1. Ansible Mgmt Driver Introduction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Mgmt Driver enables Users to configure their VNF before and/or after
its VNF Lifecycle Management operation. Users can customize the logic
of Mgmt Driver by implementing their own Mgmt Driver and these
customizations are specified by "interface" definition in
`NFV-SOL001 v2.6.1`_.

In the current community code, there is no Mgmt Driver that utilizes
Ansible for VNF Configuration. Ansible is a general purpose
configuration management tool when supported will benefit more users.

This user guide aims to provide users the information and procedures
necessary to be able to use Ansible in Mgmt Driver.

.. code-block:: console

    +------------------------------------------+
    | Tacker                                   |
    | +--------------------------------------+ |
    | |     Tacker-Server                    | |
    | +--------------------------------------+ |
    |                                          |
    | +--------------------------------------+ |
    | |   Tacker-Conductor                   | |
    | |                                      | |
    | | +----------------------------------+ | |
    | | |         OpenStack Driver         | | |
    | | +----------------------------------+ | |
    | | +----------------------------------+ | |
    | | | Ansible Driver                   | | |
    | | |                                  | | |
    | | |  +------------------+            | | |
    | | |  |  Config Parser   |            | | |     1. Get VDU Resources
    | | |  +--------|---------+            ------------------------------------
    | | |           |                      | | |                              |
    | | |           |2. VDU/Config/Command | | |                              |
    | | |           |   Order Processing   | | |                              |
    | | |           |                      | | |                              |
    | | |  +--------V---------+            | | |                              |
    | | |  |     Executor     |            | | |                 +------------|-------------+
    | | |  +--------|---------+            | | |                 | Heat       |             |
    | | +-----------|----------------------+ | |                 | +----------v-----------+ |
    | +-------------|------------------------+ |                 | |    OpenStack Heat    | |
    |               |                          |                 | +----------------------+ |
    +---------------|--------------------------+                 +------------|-------------+
                    |                                                         |
                    |3. Execute Playbook                                      |
                    |                                                         |
                    |                                                         |
       +------------V-------------+                                           |
       |VNF                       |                                           |
       |     +--------------+     |                                           |
       |     |     VDU1     |     |                                           |
       |     +--------------+     |                                           |
       |                          <--------------------------------------------
       |     +--------------+     |
       |     |     VDU2     |     |
       |     +--------------+     |
       +--------------------------+


2. Use Case
^^^^^^^^^^^
* dynamic mgmt address: The IP is generated via DHCP.
* static mgmt address: Static IP is specified.


1. VDU Configuration at dynamic mgmt address
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In ``helloworld3_df_default.yaml``, ``dhcp_enabled`` value should be ``true``.

.. code-block:: yaml

    tosca_definitions_version: tosca_simple_yaml_1_2
    description: Simple deployment flavour for Sample VNF
    imports:
      - etsi_nfv_sol001_common_types.yaml
      - etsi_nfv_sol001_vnfd_types.yaml
      - helloworld3_types.yaml
    topology_template:
    ...
        internalNW_1:
          type: tosca.nodes.nfv.VnfVirtualLink
          properties:
          ...
              virtual_link_protocol_data:
                - associated_layer_protocol: ipv4
                  l2_protocol_data:
                    network_type: vlan
                  l3_protocol_data:
                    ip_version: ipv4
                    cidr: '192.168.0.0/24'
                    dhcp_enabled: true


2. VDU Configuration at static mgmt address
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In ``helloworld3_df_default.yaml``, ``dhcp_enabled`` should not be present.

.. code-block:: yaml

    tosca_definitions_version: tosca_simple_yaml_1_2
    description: Simple deployment flavour for Sample VNF
    imports:
      - etsi_nfv_sol001_common_types.yaml
      - etsi_nfv_sol001_vnfd_types.yaml
      - helloworld3_types.yaml
    topology_template:
    ...
        internalNW_1:
          type: tosca.nodes.nfv.VnfVirtualLink
          properties:
          ...
              virtual_link_protocol_data:
                - associated_layer_protocol: ipv4
                  l3_protocol_data:
                    ip_version: ipv4
                    cidr: '192.168.0.0/24'

The BaseHOT file will get the IP from the request body. This is done by
defining the management IP parameter and getting its value under the
properties of the resource.

.. code-block:: yaml

    parameters:
      nfv:
        type: json

      mgmt_ip_vm0_0:
        type: string
        label: Management Network IPv4 Address
        description: Management Network IPv4 Address
      mgmt_ip_vm1_0:
        type: string
        label: Management Network IPv4 Address
        description: Management Network IPv4 Address

    resources:
      VDU1:
        type: OS::Heat::AutoScalingGroup
        properties:
          min_size: 1
          max_size: 3
          desired_capacity: 1
          resource:
            type: VDU1.yaml
            properties:
              flavor: { get_param: [ nfv, VDU, VDU1, flavor ] }
              image: { get_param: [ nfv, VDU, VirtualStorage, image ] }
              name: vdu1
              testnet: { get_resource: internalNW_1 }
              mgmt_ip_a: { get_param: mgmt_ip_vm0_0 }
              mgmt_ip_b: { get_param: mgmt_ip_vm1_0 }

The sample above shows the BaseHOT file getting the static IP from
the request body using ``mgmt_ip_vm0_0`` and ``mgmt_ip_vm1_0`` parameters and
assigned to ``mgmt_ip_a`` and ``mgmt_ip_b`` respectively.

The nested BaseHot file will then use the values acquired in the BaseHOT file
to set the management IP of the resource.

.. code-block:: yaml

    parameters:
      flavor:
        type: string
      image:
        type: string
      name:
        type: string
      testnet:
        type: string
      mgmt_ip_a:
        type: string
        label: Management Network IPv4 Address
        description: Management Network IPv4 Address
      mgmt_ip_b:
        type: string
        label: Management Network IPv4 Address
        description: Management Network IPv4 Address

    resources:
      VDU1:
        type: OS::Nova::Server
        properties:
          ...
      CP1:
        type: OS::Neutron::Port
        properties:
          network: { get_param: testnet }
          fixed_ips:
          - ip_address: { get_param:  mgmt_ip_a }

      CP2:
        type: OS::Neutron::Port
        properties:
          network: { get_param: testnet }
          fixed_ips:
          - ip_address: { get_param:  mgmt_ip_b }
      ...

The sample above shows the nested file of BaseHOT where the value of the IP
address acquired from the BaseHOT file is being assigned to the port.

Set the static IP in the json request parameter for ``Instantiation`` under
``additionalParams``.

.. code-block:: yaml

    {
        "flavourId": "default",
        ...
        "additionalParams": {
            "lcm-operation-user-data": "./UserData/lcm_user_data.py",
            "lcm-operation-user-data-class": "SampleUserData",
            "mgmt_ip_vm0_0": "10.1.1.20",
            "mgmt_ip_vm1_0": "10.1.1.24"
        }
    }


Ordering Options
----------------



1. VDU Order
^^^^^^^^^^^^

The order of VDU is based on the ``order`` keyword after ``config`` in the
``config.yaml`` file.

Sample:

.. code-block::

  vdus:
    VDU1:
      config:
        order: 1
        vm_app_config:
          ...

    VDU2:
      config:
        order: 0
        vm_app_config:
          ...

In the sample above, ``VDU2`` is processed before ``VDU1`` because
of the value of the ``order``.

.. note::

    Should they have the same order, they will be executed randomly.


2. Command Order
^^^^^^^^^^^^^^^^

The command order is necessary if you have multiple commands to be executed
in a single configuration.

Sample:

.. code-block::

  vdus:
    VDU1:
      config:
        order: 1
        vm_app_config:
          type: ansible
          instantiation:
            - path: _VAR_vnf_package_path/Scripts/default/sample_start-1.yaml
              params:
                ansible_password: password
              order: 1
            - path: _VAR_vnf_package_path/Scripts/default/sample_start-2.yaml
              params:
                ansible_password: password
              order: 2
            - path: _VAR_vnf_package_path/Scripts/default/sample_start-3.yaml
              params:
                ansible_password: password
              order: 0

In the above example, the order of the command execution is as follows:
  - Scripts/default/sample_start-3.yaml
  - Scripts/default/sample_start-1.yaml
  - Scripts/default/sample_start-2.yaml

This is due to the order value of each commands.



Ansible Driver Usage
--------------------



In case Ansible is not yet installed, please refer to the `Ansible Installation
Guide`_.

1. Copy Ansible Folder
^^^^^^^^^^^^^^^^^^^^^^

First, copy the sample script that was stored in
``tacker/samples/mgmt_driver/ansible`` into the directory of
``tacker/tacker/vnfm/mgmt_drivers``.

.. code-block:: console

    $ cp -pfr /opt/stack/tacker/samples/mgmt_driver/ansible /opt/stack/tacker/tacker/vnfm/mgmt_drivers/


Environment Configuration
-------------------------



1. Set the setup.cfg
^^^^^^^^^^^^^^^^^^^^

You have to register ``ansible_driver`` in the operation environment
of the tacker.

.. code-block:: console

    $ vi /opt/stack/tacker/setup.cfg
    ...
    tacker.tacker.mgmt.drivers =
    noop = tacker.vnfm.mgmt_drivers.noop:VnfMgmtNoop
    openwrt = tacker.vnfm.mgmt_drivers.openwrt.openwrt:VnfMgmtOpenWRT
    vnflcm_noop = tacker.vnfm.mgmt_drivers.vnflcm_noop:VnflcmMgmtNoop
    ansible_driver = tacker.vnfm.mgmt_drivers.ansible.ansible:DeviceMgmtAnsible

2. Set the tacker.conf
^^^^^^^^^^^^^^^^^^^^^^

Then find the ``vnflcm_mgmt_driver`` field in the ``tacker.conf``.
Add the ``ansible_driver`` defined in step 2 to it,
and separate by commas.

.. code-block:: console

    $ vi /etc/tacker/tacker.conf
    ...
    [tacker]
    ...
    vnflcm_mgmt_driver = vnflcm_noop,ansible_driver
    ...

3. Update the tacker.egg-info
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After the above two steps, the configuration has
not yet taken effect. You also need to execute the ``setup.py`` script
to regenerate the contents of the ``tacker.egg-info`` directory.

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

Then you can use Mgmt Driver to deploy Ansible  Driver after
restarting the service of ``tacker`` and ``tacker-conductor``.

.. code-block:: console

    $ sudo systemctl stop devstack@tacker
    $ sudo systemctl restart devstack@tacker-conductor
    $ sudo systemctl start devstack@tacker


VNF Package Creation
--------------------




1. VNF Package Structure
^^^^^^^^^^^^^^^^^^^^^^^^

The sample structure of VNF Package is shown below.

.. note::

    You can also find them in the
    ``samples/mgmt_driver/ansible/ansible_vnf_package/`` directory
    of the tacker.


The directory structure:

* **TOSCA-Metadata/TOSCA.meta**
* **Definitions/**
* **Files/images/**
* **ScriptANSIBLE/**
* **Scripts/**
* **BaseHOT/**
* **UserData/**

.. code-block:: console

  !----TOSCA-Metadata
          !---- TOSCA.meta
  !----Definitions
          !---- etsi_nfv_sol001_common_types.yaml
          !---- etsi_nfv_sol001_vnfd_types.yaml
          !---- helloworld3_top.vnfd.yaml
          !---- helloworld3_types.yaml
          !---- helloworld3_df_default.yaml
  !----Files
          !---- images
                  !---- cirros-0.5.2-x86_64-disk.img
  !----ScriptANSIBLE
          !---- config.yaml
  !----Scripts
          !---- default
                  !---- sample.yaml
  !----BaseHOT
          !---- default
                  !---- nested
                          !---- VDU1.yaml
                  !---- VNF-hot.yaml
  !----UserData
          !---- __init__.py
          !---- lcm_user_data.py

2. ScriptANSIBLE
^^^^^^^^^^^^^^^^

This directory contains the settings for running Ansible Script. This includes
the path to the Ansible Playbook that each LCM runs, and the orders that
should be executed according to each VDU, etc. It is mandatory to have a
``config.yaml`` file in this directory (as shown in the directory structure).
This file is the one being parsed by the driver.

The ``configurable_properties`` in ``config.yaml`` file is a mandatory
parameter. It can be used to define key-value pairs that can be used during
VNF Configuration. The format of the ``key`` must start with ``_VAR_``.
So when the ``key`` is used in ``vm_app_config``, then it will be replaced
by the set value.

.. code-block:: console

    configurable_properties:
      _VAR_password: 'password'

    vdus:
     VDU1:
       config:
         order: 1
         vm_app_config:
           type: ansible
           instantiation:
             - path: _VAR_vnf_package_path/Scripts/default/sample_start-1.yaml
               params:
                 ansible_password: _VAR_password
               order: 0

The example above shows that we have a key ``_VAR_password`` with a value
``password``. It will replace the ``_VAR_password`` used in the
``vm_app_config``.

.. note::

    The ``_VAR_vnf_package_path/`` variable is mandatory for the path of the
    Ansible Playbook. This value is replaced by the actual vnf package path
    during runtime.


3. Scripts
^^^^^^^^^^

This directory contains the user-defined Ansible Playbook to run on each LCM.
The Playbook is executed based on the config.yaml definition under
ScriptANSIBLE. The Sample Ansible Driver utilizes Ansible to run the Playbooks.

.. code-block::

 # This playbook prints a simple debug message
 - name: Echo
   hosts: all
   remote_user: root

   tasks:
   - name: Creates a file
     remote_user: some_user
     become: yes
     become_method: sudo
     file:
       path:  "/tmp/sample.txt"
       state: touch


4. BaseHOT
^^^^^^^^^^

Base HOT file is a Native cloud orchestration template, HOT in this context,
which is commonly used for LCM operations in different VNFs. It is the
responsibility of the user to prepare this file, and it is necessary to make
it consistent with VNFD placed under the **Definitions/** directory.

Here are the following that is needed to check in these files:
 - Under ``resources``, there should be no ``_group`` in the name

.. code-block::

 heat_template_version: 2013-05-23
 description: 'default deployment flavour for Sample VNF'

 parameters:
   nfv:
     type: json

 resources:
   VDU1:
     type: OS::Heat::AutoScalingGroup

All yaml files must have the ``outputs`` part. This is necessary in order
to generate the mgmt_ip address. The format of the ``outputs`` part is
as follows:

.. code-block::

 mgmt_ip-<VDU_NAME>:
   value:
     get_attr:
       - <VDU_CP>
       - fixed_ips
       - 0
       - ip_address


Example Ansible Driver LCM
--------------------------

1. VNF Package create/upload
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before you instantiate VNF, you must create a zip file of VNF Package
and upload it.

Please refer to the procedure in Section `Create and Upload VNF Package`_.

.. note::

    Please do not forget the following folders to include
    in creating the zip file:

    * Files/
    * ScriptANSIBLE/
    * Scripts/

    Please get the contents of the ``Files`` folder from the
    ``tacker/tests/etc/samples/etsi/nfv/common/Files/``.


2. VNF Create/Instantiate
^^^^^^^^^^^^^^^^^^^^^^^^^

Please refer to the procedure in Section `Create & Instantiate VNF`_.

.. note::

    Please see the ``tacker-conductor.log`` for the Ansible Playbook Play
    results.


3. VNF Heal
^^^^^^^^^^^

Please refer to the procedure in Section `VNF Healing`_.

.. note::

    Please see the ``tacker-conductor.log`` for the Ansible Playbook Play
    results.


4. VNF Scale
^^^^^^^^^^^^

Please refer to the procedure in Section `VNF Scaling`_.

.. note::

    Please see the ``tacker-conductor.log`` for the Ansible Playbook Play
    results.


5. VNF Terminate/Delete
^^^^^^^^^^^^^^^^^^^^^^^

Please refer to the procedure in Section `Termination and Delete`_.

.. note::

    Please see the ``tacker-conductor.log`` for the Ansible Playbook Play
    results.



.. _NFV-SOL001 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/001/02.06.01_60/gs_NFV-SOL001v020601p.pdf
.. _Ansible Installation Guide : https://docs.ansible.com/ansible/2.9/installation_guide/index.html
.. _Create and Upload VNF Package : https://docs.openstack.org/tacker/latest/install/etsi_getting_started.html#create-and-upload-vnf-package
.. _Create & Instantiate VNF : https://docs.openstack.org/tacker/latest/install/etsi_getting_started.html#create-instantiate-vnf
.. _Termination and Delete : https://docs.openstack.org/tacker/latest/install/etsi_getting_started.html#terminate-delete-vnf
.. _VNF Healing : https://docs.openstack.org/tacker/latest/user/etsi_vnf_healing.html
.. _VNF Scaling : https://docs.openstack.org/tacker/latest/user/etsi_vnf_scaling.html
